"""An OpenAI-compatible stub endpoint, shared by every worker process (master blueprint section 8).

Libraries that run their pipelines in several OS processes cannot share an
in-process stub, so this module serves the stub over HTTP on 127.0.0.1:

- ``POST /v1/chat/completions``: the target's handler picks the answer; the
  answer is validated against the JSON schema the library sent, either in
  ``response_format.json_schema`` or as a fenced ```json block in the system
  prompt, before it is returned;
- ``POST /v1/embeddings``: deterministic vectors from ``stubs.embed``, with the
  configured dimension;
- ``GET /v1/models``;
- ``GET /_wm/ledger`` (``?drain=1`` empties it) and ``GET /_wm/health``.

A prompt the handler does not know is answered with HTTP 400 and recorded with
``decision.error``, so the run can refuse to count the trial: the stub fails
loudly rather than guessing. Every call, answered or not, goes in the ledger.

Standard library only (principle P6). The fixture handlers live in the target
packages; this module knows nothing about any target.
"""

from __future__ import annotations

import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from .stubs import embed, sha256_text
from .timing import stamp

_FENCED_JSON = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


class UnknownPrompt(Exception):
    """The handler has no fixture answer for this prompt."""


class SchemaError(ValueError):
    pass


# --- a small JSON-schema validator (the subset Pydantic emits) -------------------------------------------------


def _resolve(schema: dict, root: dict) -> dict:
    seen = 0
    while isinstance(schema, dict) and "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise SchemaError(f"unsupported $ref {ref!r}")
        node: Any = root
        for part in ref[2:].split("/"):
            node = node[part]
        schema = node
        seen += 1
        if seen > 64:
            raise SchemaError("$ref cycle")
    return schema


_TYPES: dict[str, Callable[[Any], bool]] = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def validate(instance: Any, schema: dict, root: dict | None = None, path: str = "$") -> None:
    """Raise SchemaError if ``instance`` does not satisfy ``schema``.

    Covers type, enum, const, properties, required, additionalProperties, items,
    minItems, maxItems, anyOf, oneOf, allOf and local $ref / $defs: what Pydantic
    v2 emits for plain models. Formats and string patterns are not checked.
    """
    root = schema if root is None else root
    schema = _resolve(schema, root)
    if schema is True or schema == {}:
        return
    if schema is False:
        raise SchemaError(f"{path}: no value is allowed here")
    for key in ("anyOf", "oneOf"):
        if key in schema:
            passed = 0
            errors = []
            for option in schema[key]:
                try:
                    validate(instance, option, root, path)
                    passed += 1
                except SchemaError as exc:
                    errors.append(str(exc))
            if passed == 0 or (key == "oneOf" and passed > 1):
                raise SchemaError(f"{path}: matches {passed} of the {key} options ({'; '.join(errors[:3])})")
    for option in schema.get("allOf", []):
        validate(instance, option, root, path)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_TYPES[t](instance) for t in types):
            raise SchemaError(f"{path}: expected {'/'.join(types)}, got {type(instance).__name__}")
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaError(f"{path}: {instance!r} is not one of {schema['enum']}")
    if "const" in schema and instance != schema["const"]:
        raise SchemaError(f"{path}: {instance!r} is not {schema['const']!r}")
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in instance:
                raise SchemaError(f"{path}: missing required property {name!r}")
        extra = schema.get("additionalProperties", True)
        for name, value in instance.items():
            if name in properties:
                validate(value, properties[name], root, f"{path}.{name}")
            elif extra is False:
                raise SchemaError(f"{path}: unexpected property {name!r}")
            elif isinstance(extra, dict):
                validate(value, extra, root, f"{path}.{name}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            raise SchemaError(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SchemaError(f"{path}: more than {schema['maxItems']} items")
        if isinstance(schema.get("items"), dict):
            for index, value in enumerate(instance):
                validate(value, schema["items"], root, f"{path}[{index}]")


def request_schema(body: dict) -> dict | None:
    """The JSON schema a chat request asks for, wherever the library put it."""
    response_format = body.get("response_format") or {}
    if isinstance(response_format, dict) and response_format.get("type") == "json_schema":
        schema = (response_format.get("json_schema") or {}).get("schema")
        if isinstance(schema, dict):
            return schema
    for message in body.get("messages", []):
        if message.get("role") == "system":
            match = _FENCED_JSON.search(_text(message.get("content")))
            if match:
                return json.loads(match.group(1))
    return None


def _text(content: Any) -> str:
    """Message content as text: a string, or the text parts of a content list."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


def message_text(body: dict, role: str) -> str:
    return "\n".join(_text(m.get("content")) for m in body.get("messages", []) if m.get("role") == role)


# --- the server ------------------------------------------------------------------------------------------------


class StubServer:
    """``handler(body, schema) -> (answer, decision)``; ``answer`` is a JSON value, or a str for plain text.

    The handler raises UnknownPrompt when it has no fixture answer.
    """

    def __init__(self, handler: Callable[[dict, dict | None], tuple[Any, dict]], dim: int = 1024,
                 model: str = "witnessmark-stub", embedding_model: str = "witnessmark-embed",
                 host: str = "127.0.0.1", port: int = 0):
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("the stub binds to loopback only")
        self.handler, self.dim, self.model, self.embedding_model = handler, dim, model, embedding_model
        self._lock = threading.Lock()
        self._calls: list[dict] = []
        self.unknown = 0
        stub = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args) -> None:  # quiet: the ledger is the log
                return

            def _send(self, status: int, payload: dict) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:  # noqa: N802 - http.server's naming
                url = urlparse(self.path)
                if url.path == "/_wm/ledger":
                    drain = parse_qs(url.query).get("drain", ["0"])[0] == "1"
                    self._send(200, {"calls": stub.ledger(drain)})
                elif url.path == "/_wm/health":
                    self._send(200, {"ok": True, "unknown": stub.unknown})
                elif url.path.rstrip("/").endswith("/models"):
                    self._send(200, {"object": "list", "data": [
                        {"id": stub.model, "object": "model"}, {"id": stub.embedding_model, "object": "model"}]})
                else:
                    self._send(404, {"error": {"message": f"no route {url.path}"}})

            def do_POST(self) -> None:  # noqa: N802
                inv = stamp()
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    self._send(400, {"error": {"message": "witnessmark stub: the body is not JSON"}})
                    return
                path = urlparse(self.path).path.rstrip("/")
                if path.endswith("/chat/completions"):
                    status, payload = stub.chat(body, raw, inv)
                elif path.endswith("/embeddings"):
                    status, payload = stub.embeddings(body, raw, inv)
                else:
                    status, payload = 404, {"error": {"message": f"no route {path}"}}
                self._send(status, payload)

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._server.daemon_threads = True
        self._thread: threading.Thread | None = None

    # --- lifecycle -------------------------------------------------------------------------------------------

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/v1"

    def start(self) -> "StubServer":
        self._thread = threading.Thread(target=self._server.serve_forever, name="witnessmark-stub", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    # --- ledger ----------------------------------------------------------------------------------------------

    def _record(self, kind: str, prompt: str, raw: str, response: Any, decision: dict, inv) -> None:
        with self._lock:
            self._calls.append({
                "kind": kind, "prompt": prompt, "client": None, "op_id": None,
                "inv": inv.to_json(), "ret": stamp().to_json(),
                "request_sha256": sha256_text(raw),
                "response_sha256": sha256_text(json.dumps(response, sort_keys=True, default=str)),
                "decision": decision,
            })

    def ledger(self, drain: bool = False) -> list[dict]:
        with self._lock:
            calls = list(self._calls)
            if drain:
                self._calls.clear()
        return calls

    # --- routes ----------------------------------------------------------------------------------------------

    def chat(self, body: dict, raw: str, inv) -> tuple[int, dict]:
        schema = request_schema(body)
        try:
            answer, decision = self.handler(body, schema)
        except UnknownPrompt as exc:
            with self._lock:
                self.unknown += 1
            decision = {"error": f"unknown prompt: {exc}"}
            self._record("llm", "unknown", raw, None, decision, inv)
            return 400, {"error": {"message": f"witnessmark stub: unknown prompt ({exc})", "type": "invalid_request_error"}}
        if schema is not None and not isinstance(answer, str):
            try:
                validate(answer, schema)
            except SchemaError as exc:  # the fixture is wrong, never the library: fail loudly
                with self._lock:
                    self.unknown += 1
                decision = {**decision, "error": f"the fixture answer breaks the request's schema: {exc}"}
                self._record("llm", decision.get("prompt", "?"), raw, answer, decision, inv)
                return 500, {"error": {"message": f"witnessmark stub: {decision['error']}"}}
        content = answer if isinstance(answer, str) else json.dumps(answer, sort_keys=True)
        self._record("llm", decision.get("prompt", "?"), raw, answer, decision, inv)
        return 200, {
            "id": "wm-" + sha256_text(raw)[:16], "object": "chat.completion", "created": int(time.time()),
            "model": body.get("model", self.model),
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": len(raw) // 4, "completion_tokens": len(content) // 4,
                      "total_tokens": (len(raw) + len(content)) // 4},
        }

    def embeddings(self, body: dict, raw: str, inv) -> tuple[int, dict]:
        inputs = body.get("input", [])
        inputs = [inputs] if isinstance(inputs, str) else list(inputs)
        asked = body.get("dimensions")
        if asked is not None and int(asked) != self.dim:
            decision = {"error": f"dimension {asked} requested, the stub serves {self.dim}"}
            self._record("embed", "embed", raw, None, decision, inv)
            with self._lock:
                self.unknown += 1
            return 400, {"error": {"message": f"witnessmark stub: {decision['error']}"}}
        if any(not isinstance(text, str) for text in inputs):
            return 400, {"error": {"message": "witnessmark stub: token-id inputs are not supported"}}
        data = [{"object": "embedding", "index": i, "embedding": embed(text, self.dim)} for i, text in enumerate(inputs)]
        self._record("embed", "embed", raw, {"count": len(data)}, {"texts": len(inputs)}, inv)
        return 200, {"object": "list", "data": data, "model": body.get("model", self.embedding_model),
                     "usage": {"prompt_tokens": sum(len(t) for t in inputs) // 4,
                               "total_tokens": sum(len(t) for t in inputs) // 4}}
