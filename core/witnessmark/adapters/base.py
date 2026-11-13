"""The engine adapter contract (master blueprint section 4.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class EngineError(Exception):
    """A definite refusal: the SUT did not apply the operation."""

    def __init__(self, type_: str, message: str, code: str | None = None):
        super().__init__(message)
        self.type = type_
        self.message = message
        self.code = code

    def to_json(self) -> dict:
        record = {"type": self.type, "message": self.message}
        if self.code is not None:
            record["code"] = self.code
        return record


class EngineUnavailable(Exception):
    """No definite answer (timeout, lost connection): the operation may have applied."""

    def __init__(self, type_: str, message: str):
        super().__init__(message)
        self.type = type_
        self.message = message

    def to_json(self) -> dict:
        return {"type": f"unavailable.{self.type}", "message": self.message}


@dataclass
class Reply:
    columns: list[str]
    rows: list[list]
    token: str | None = None
    stats: dict = field(default_factory=dict)

    def scalar(self, default=None):
        """The first value of the first row."""
        if self.rows and self.rows[0]:
            return self.rows[0][0]
        return default


class Session(ABC):
    """One client's connection. Sessions are never shared between threads."""

    @abstractmethod
    def run(self, query: str, params: dict | None = None, *, write: bool = True) -> Reply: ...

    @abstractmethod
    def ping(self) -> None:
        """One no-op round trip, so setup never falls inside the race."""

    @abstractmethod
    def close(self) -> None: ...


class Engine(ABC):
    name: str
    repo: str

    @abstractmethod
    def session(self, timeout: float = 60.0) -> Session: ...

    @abstractmethod
    def reset(self, session: Session) -> None:
        """Remove everything the harness may have written."""

    @abstractmethod
    def health(self) -> dict:
        """{"ok": bool, ...}"""

    @abstractmethod
    def describe(self) -> dict:
        """A component record for run.json: name, version, image, digest, config."""
