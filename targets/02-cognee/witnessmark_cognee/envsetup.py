"""The environment a Cognee process runs in (target blueprint sections 3 and 4).

Everything here runs before ``import cognee``:

- telemetry off (``TELEMETRY_DISABLED``, read by ``send_telemetry`` and by dlt's switch);
- every model call to the local stub endpoint, with a dummy key;
- litellm's model-cost map read locally, Hugging Face offline;
- tiktoken's cache pointed at a copy of the encodings litellm bundles, with CRLF line
  endings turned back into LF: the Windows wheel ships them with CRLF, tiktoken's hash
  check then fails, it deletes the file and downloads a fresh one;
- a socket guard that refuses every connection and DNS lookup that is not loopback.
"""

from __future__ import annotations

import hashlib
import os
import socket
import sys
from pathlib import Path

LOOPBACK = {"127.0.0.1", "::1", "localhost", None}

# sha256 of the LF-normalised encodings, as tiktoken expects them (tiktoken_ext/openai_public.py)
TIKTOKEN_FILES = {
    "9b5ad71b2ce5302211f9c61530b329a4922fc6a4": "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7",
}

BLOCKED: list[str] = []
_installed = False

# The matrix rows (target blueprint section 3)
ROWS = {
    "R1": {"GRAPH_DATABASE_PROVIDER": "ladybug", "GRAPH_DATABASE_SUBPROCESS_ENABLED": "true",
           "VECTOR_DB_PROVIDER": "lancedb", "DB_PROVIDER": "sqlite"},
    "R1i": {"GRAPH_DATABASE_PROVIDER": "ladybug", "GRAPH_DATABASE_SUBPROCESS_ENABLED": "false",
            "VECTOR_DB_PROVIDER": "lancedb", "DB_PROVIDER": "sqlite"},
    "R2": {"GRAPH_DATABASE_PROVIDER": "neo4j", "GRAPH_DATABASE_URL": "bolt://127.0.0.1:17687",
           "GRAPH_DATABASE_USERNAME": "neo4j", "GRAPH_DATABASE_PASSWORD": "witnessmark",
           "VECTOR_DB_PROVIDER": "lancedb", "DB_PROVIDER": "sqlite"},
    "R3": {"GRAPH_DATABASE_PROVIDER": "falkor", "GRAPH_DATABASE_URL": "127.0.0.1", "GRAPH_DATABASE_PORT": "16380",
           "VECTOR_DB_PROVIDER": "falkor", "VECTOR_DB_URL": "127.0.0.1", "VECTOR_DB_PORT": "16380",
           "DB_PROVIDER": "sqlite"},
}


def build_env(row: str, root: Path, stub_url: str, dim: int, access_control: str) -> dict:
    """The variables one Cognee process needs; nothing secret, the key is a dummy."""
    if row not in ROWS:
        raise ValueError(f"row must be one of {sorted(ROWS)}")
    env = {
        "TELEMETRY_DISABLED": "1",
        "LITELLM_LOCAL_MODEL_COST_MAP": "True",
        "LITELLM_LOG": "ERROR",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "COGNEE_LOG_FILE": "false",
        "LLM_PROVIDER": "openai",
        "LLM_ENDPOINT": stub_url,
        "LLM_MODEL": "openai/witnessmark-stub",
        "LLM_API_KEY": "witnessmark-stub",
        "EMBEDDING_PROVIDER": "openai_compatible",
        "EMBEDDING_ENDPOINT": stub_url,
        "EMBEDDING_MODEL": "witnessmark-embed",
        "EMBEDDING_DIMENSIONS": str(dim),
        "SYSTEM_ROOT_DIRECTORY": str(root / "system"),
        "DATA_ROOT_DIRECTORY": str(root / "data"),
        "TIKTOKEN_CACHE_DIR": str(root.parent / "tiktoken"),
        "CUSTOM_TIKTOKEN_CACHE_DIR": str(root.parent / "tiktoken"),  # litellm otherwise resets it on import
        **ROWS[row],
    }
    if access_control == "off":
        env["ENABLE_BACKEND_ACCESS_CONTROL"] = "false"
    elif access_control != "default":
        raise ValueError("access_control must be default or off")
    return env


def prepare_tiktoken(cache_dir: Path) -> None:
    """Copy litellm's bundled encodings with LF line endings, and check the hash tiktoken expects."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    bundled = Path(sys.prefix) / "Lib" / "site-packages" / "litellm" / "litellm_core_utils" / "tokenizers"
    if not bundled.is_dir():
        bundled = next(Path(sys.prefix).glob("lib/python*/site-packages/litellm/litellm_core_utils/tokenizers"))
    for name, expected in TIKTOKEN_FILES.items():
        target = cache_dir / name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            continue
        data = (bundled / name).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError(f"litellm's bundled encoding {name} does not match tiktoken's hash")
        tmp = target.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)


def install_guard() -> None:
    """Refuse any connection or DNS lookup that leaves the machine (target blueprint section 4)."""
    global _installed
    if _installed:
        return
    real_connect, real_connect_ex, real_gai = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo

    def _check(address) -> None:
        host = address[0] if isinstance(address, tuple) else address
        if isinstance(host, str) and host not in LOOPBACK and not host.startswith("127."):
            BLOCKED.append(str(address))
            raise OSError(f"witnessmark: outbound connection to {address!r} refused (loopback only)")

    def connect(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            _check(address)
        return real_connect(self, address)

    def connect_ex(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            _check(address)
        return real_connect_ex(self, address)

    def getaddrinfo(host, *args, **kwargs):
        name = host.decode() if isinstance(host, bytes) else host
        if name not in LOOPBACK and not (isinstance(name, str) and name.startswith("127.")):
            BLOCKED.append(f"dns:{name}")
            raise OSError(f"witnessmark: DNS lookup of {name!r} refused (loopback only)")
        return real_gai(host, *args, **kwargs)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.getaddrinfo = getaddrinfo
    _installed = True


def enter(env: dict) -> None:
    """Make this process a Cognee process: environment, tokenizer cache, guard. Call before importing cognee."""
    if "cognee" in sys.modules:
        raise RuntimeError("cognee was imported before its environment was set")
    os.environ.update(env)
    prepare_tiktoken(Path(env["TIKTOKEN_CACHE_DIR"]))
    install_guard()


def assert_telemetry_off() -> None:
    """Refuse to run unless Cognee's own switch is set, and check the switch in its source still reads it."""
    import inspect

    from cognee.shared import utils

    if not os.getenv("TELEMETRY_DISABLED"):
        raise RuntimeError("TELEMETRY_DISABLED is not set; refusing to run")
    if 'os.getenv("TELEMETRY_DISABLED")' not in inspect.getsource(utils.send_telemetry):
        raise RuntimeError("send_telemetry no longer reads TELEMETRY_DISABLED; refusing to run")
