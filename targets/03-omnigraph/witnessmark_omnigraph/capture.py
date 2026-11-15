"""Evidence for Omnigraph operations outside the core thread runner."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import threading
from pathlib import Path

from witnessmark.evidence import RunDir, redact
from witnessmark.history import FAIL, OK, UNKNOWN, Op
from witnessmark.timing import stamp

from .client import OmnigraphClient, Outcome

STATE_CAP = 5 * 1024 * 1024
LOG_CAP = 64 * 1024
SENSITIVE_KEY = re.compile(r"(?i)(?:authorization|password|secret|credential|access[_-]?key|root[_-]?user|"
                           r"root[_-]?pass|bearer|token)")
KEY_VALUE = re.compile(
    r"""(?i)((?:authorization|password|secret|credential|access[_-]?key|root[_-]?user|root[_-]?pass|"""
    r"""bearer|token)[\w-]*['"]?\s*[:=]\s*)"""
    r"""(?:"[^"]*"|'[^']*'|(?:Bearer\s+)?[^\s,;}]+)"""
)


def redact_text(value: str, repo: Path) -> str:
    value = redact(value)
    for spelling in (str(repo), repo.as_posix(), str(repo).replace("\\", "\\\\")):
        value = value.replace(spelling, "<repo>")
    value = re.sub(r"""(?i)(?:[A-Z]:)?[/\\]+Users[/\\]+[^/\\\s"']+(?:[/\\]+App""" r"""Data[^\s"']*)?""",
                   "<user-home>", value)
    value = value.replace("witnessmark-local-only", "<redacted>")
    return KEY_VALUE.sub(r"\1<redacted>", value)


def safe(value, repo: Path):
    if isinstance(value, str):
        return redact_text(value, repo)
    if isinstance(value, dict):
        return {key: ("<redacted>" if SENSITIVE_KEY.search(key) else safe(item, repo))
                for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(item, repo) for item in value]
    return value


def repro_command(repo: Path, argv: list[str]) -> str:
    root = repo.as_posix().rstrip("/") + "/"
    args = [arg.replace("\\", "/").removeprefix(root) for arg in argv]
    return shlex.join(["python", "targets/03-omnigraph/wm_omnigraph.py",
                       *(redact_text(arg, repo) for arg in args)])


class OperationCapture:
    def __init__(self, repo: Path, run_id: str, emit):
        self.repo = repo
        self.run_id = run_id
        self.emit = emit
        self.lock = threading.Lock()
        self.sequence = 0
        self.k = 0
        self.phase = "setup"

    def trial(self, k: int, phase: str = "race") -> None:
        self.k, self.phase = k, phase

    def record(self, client, kind, inputs, inv, ret, outcome, *, result=None,
               error=None, token=None, phase=None) -> None:
        with self.lock:
            self.sequence += 1
            op = Op(self.run_id, self.k, phase or self.phase, f"{self.k}-{client}-{self.sequence}",
                    client, kind, safe(inputs, self.repo), inv, ret if outcome != UNKNOWN else None, outcome,
                    result=safe(result, self.repo), error=safe(error, self.repo), token=token)
            self.emit(op)

    def client(self, endpoint: str, graph: str = "witnessmark", *, timeout: float = 60,
               label: str = "c00", bearer_token: str | None = None) -> OmnigraphClient:
        def observed(method, path, body, inv, ret, reply):
            data = reply.data if isinstance(reply.data, dict) else {}
            commit = data.get("commit") or {}
            token = data.get("graph_commit_id") or (commit.get("graph_commit_id") if isinstance(commit, dict) else None)
            request = {"method": method, "path": path}
            if isinstance(body, dict):
                request["body"] = body
            elif isinstance(body, bytes):
                request.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
            error = None
            if not reply.ok:
                error = {"type": reply.kind or "http_error", "message": reply.message or "request failed"}
                if reply.status is not None:
                    error["code"] = reply.status
            outcome = {Outcome.OK: OK, Outcome.REFUSAL: FAIL, Outcome.UNKNOWN: UNKNOWN}[reply.outcome]
            self.record(label, (body.get("name") if isinstance(body, dict) else None) or method.lower(),
                        request, inv, ret, outcome, result=reply.data, error=error,
                        token=str(token) if token is not None else None)

        return OmnigraphClient(endpoint, graph, timeout=timeout, observed=observed, bearer_token=bearer_token)

    def action(self, kind: str, target: str, invoke, *, phase: str = "nemesis", decode=None, **inputs):
        inv = stamp()
        try:
            result = invoke()
            ret = stamp()
            code = result.returncode
            output = decode(result.stdout) if code == 0 and decode else None
        except Exception as exc:
            self.record("nemesis", kind, {"target": target, **inputs}, inv, stamp(), UNKNOWN,
                        error={"type": type(exc).__name__, "message": str(exc)}, phase=phase)
            raise
        self.record("nemesis", kind, {"target": target, **inputs}, inv, ret, OK if code == 0 else FAIL,
                    result={"exit": code, **({"output": output} if decode else {})}, phase=phase)
        return output if decode and code == 0 else result


class RunCapture(OperationCapture):
    def __init__(self, repo: Path, evidence: Path, manifest: dict, command: str):
        super().__init__(repo, manifest["run_id"], self._append)
        component = manifest["components"][0]
        self.storage = component["config"]["backend"]
        scenario = manifest["scenario"]
        self.directory = RunDir(evidence, f"omnigraph/{component['version']}.{self.storage}",
                                f"{scenario['id']}.{scenario['mode']}", self.run_id)
        self.path = self.directory.path
        self.command = command
        self.write_repro(manifest)
        self.write_manifest(manifest)
        self.history = (self.path / "history.jsonl").open("w", encoding="utf-8", newline="\n")

    def write_repro(self, manifest: dict) -> None:
        harness = manifest["harness"]
        component = manifest["components"][0]
        images = "\n".join(f"- {part['name']}: `{part.get('image', 'unknown')}` "
                           f"(`{part.get('digest', 'unknown')}`)" for part in manifest["components"])
        self.directory.write_repro(
            f"# Reproduce run {self.run_id}\n\n"
            "From the repository root, use the pinned images and run:\n\n"
            f"```bash\n{self.command}\n```\n\n"
            f"- Harness commit: `{harness['commit']}` (dirty: {str(harness['dirty']).lower()})\n"
            f"- Build: `{component['version']}`\n- Storage: `{self.storage}`\n{images}\n"
        )

    def _append(self, op: Op) -> None:
        self.history.write(json.dumps(op.to_json(), ensure_ascii=False, separators=(",", ":")) + "\n")

    def write_manifest(self, manifest: dict) -> None:
        # Preserve schema field names (including the normal operation token).
        self.directory.write_manifest(self._manifest_value(manifest))

    def _manifest_value(self, value):
        if isinstance(value, dict):
            return {key: ("<redacted>" if key != "token" and SENSITIVE_KEY.search(key) else
                          self._manifest_value(item)) for key, item in value.items()}
        if isinstance(value, list):
            return [self._manifest_value(item) for item in value]
        return redact_text(value, self.repo) if isinstance(value, str) else value

    def final_state(self, trial: dict, state: dict) -> None:
        trial["k"] = self.k
        trial["state_file"] = self.directory.write_state(self.k, safe(state, self.repo), max_bytes=STATE_CAP)

    def write_log(self, service: str, text: str) -> str:
        relative = f"logs/{self.k}-{service}.log"
        path = self.path / relative
        path.parent.mkdir(exist_ok=True)
        cleaned = redact_text(text, self.repo).encode("utf-8")
        if len(cleaned) > LOG_CAP:
            prefix = b"[earlier log output omitted]\n"
            tail = cleaned[-(LOG_CAP - len(prefix)):].decode("utf-8", errors="ignore")
            cleaned = prefix + tail.encode("utf-8")
        path.write_bytes(cleaned)
        return relative

    def close(self) -> None:
        with self.lock:
            self.history.close()
