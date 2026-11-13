"""A minimal RESP2 client: enough for FalkorDB's GRAPH.* commands (standard library only)."""

from __future__ import annotations

import socket


class RespError(Exception):
    """The server answered with an error reply."""


class RespErrorReply:
    """An error element nested inside an array reply."""

    def __init__(self, message: str):
        self.message = message

    def __repr__(self) -> str:
        return f"RespErrorReply({self.message!r})"


def encode_command(*args) -> bytes:
    parts = [b"*%d\r\n" % len(args)]
    for arg in args:
        data = arg if isinstance(arg, bytes) else str(arg).encode("utf-8")
        parts.append(b"$%d\r\n%s\r\n" % (len(data), data))
    return b"".join(parts)


def read_reply(stream):
    """Read one reply from a binary file-like object."""
    line = stream.readline()
    if not line:
        raise ConnectionError("connection closed by the server")
    if not line.endswith(b"\r\n"):
        raise ConnectionError("truncated reply")
    kind, body = line[:1], line[1:-2]
    if kind == b"+":
        return body.decode("utf-8", "replace")
    if kind == b"-":
        return RespErrorReply(body.decode("utf-8", "replace"))
    if kind == b":":
        return int(body)
    if kind == b"$":
        size = int(body)
        if size < 0:
            return None
        data = stream.read(size + 2)
        if len(data) != size + 2:
            raise ConnectionError("truncated bulk string")
        return data[:-2].decode("utf-8", "replace")
    if kind == b"*":
        size = int(body)
        if size < 0:
            return None
        return [read_reply(stream) for _ in range(size)]
    raise ConnectionError(f"unsupported RESP type {kind!r}")


class RespConnection:
    def __init__(self, host: str, port: int, timeout: float):
        self._sock = socket.create_connection((host, port), timeout=timeout)
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._stream = self._sock.makefile("rb")

    def call(self, *args):
        self._sock.sendall(encode_command(*args))
        reply = read_reply(self._stream)
        if isinstance(reply, RespErrorReply):
            raise RespError(reply.message)
        return reply

    def close(self) -> None:
        try:
            self._stream.close()
        finally:
            self._sock.close()
