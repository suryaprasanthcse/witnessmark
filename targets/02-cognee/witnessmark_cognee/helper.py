"""A Cognee process the coordinator drives over a pipe (target blueprint section 4).

The coordinator never imports cognee. Ladybug holds an exclusive lock on its
store file for as long as a process has it open, so a coordinator that had
opened the store itself would keep worker processes out of it. Instead the
coordinator starts a helper, sends it calls, and stops it before every
process-mode race; the next call starts a fresh helper.

Calls run concurrently inside the helper's event loop, so an ``asyncio`` race
driven from the coordinator is still a race inside one Cognee process.
"""

from __future__ import annotations

import asyncio
import itertools
import multiprocessing
import threading
import traceback


class HelperDied(RuntimeError):
    def __init__(self, exitcode):
        super().__init__(f"the Cognee helper process exited (exit code {exitcode})")
        self.exitcode = exitcode


def helper_main(env: dict, row: str, inbox, outbox) -> None:
    from . import envsetup

    envsetup.enter(env)
    from .engine import CogneeEngine
    from witnessmark.stubs import CURRENT_OP

    engine = CogneeEngine(row)
    send_lock = threading.Lock()

    def reply(message) -> None:
        with send_lock:
            outbox.send(message)

    async def handle(call_id, method, args, context) -> None:
        token = CURRENT_OP.set(context) if context else None
        try:
            result = await getattr(engine, method)(*args)
            reply((call_id, True, result))
        except BaseException as exc:  # noqa: BLE001 - every failure goes back to the caller
            from .engine import _error_text

            reply((call_id, False, {"type": type(exc).__name__, "message": _error_text(exc),
                                     "trace": traceback.format_exc()[-4000:]}))
        finally:
            if token is not None:
                CURRENT_OP.reset(token)

    async def serve() -> None:
        loop = asyncio.get_running_loop()
        stop = asyncio.Event()
        tasks: set = set()

        def reader() -> None:
            while True:
                try:
                    message = inbox.recv()
                except (EOFError, OSError):
                    message = None
                if message is None:
                    loop.call_soon_threadsafe(stop.set)
                    return

                def start(message=message):
                    task = loop.create_task(handle(*message))
                    tasks.add(task)
                    task.add_done_callback(tasks.discard)

                loop.call_soon_threadsafe(start)

        threading.Thread(target=reader, daemon=True).start()
        await stop.wait()
        if tasks:
            await asyncio.wait(tasks, timeout=60)

    asyncio.run(serve())
    outbox.close()


class HelperClient:
    """The coordinator's side: ``await client.call("dump", group)``."""

    def __init__(self, env: dict, row: str):
        context = multiprocessing.get_context("spawn")
        child_inbox, self._outbox = context.Pipe(duplex=False)
        self._inbox, child_outbox = context.Pipe(duplex=False)
        self.process = context.Process(target=helper_main, args=(env, row, child_inbox, child_outbox), daemon=False)
        self.process.start()
        child_inbox.close()
        child_outbox.close()
        self._ids = itertools.count()
        self._pending: dict[int, tuple[asyncio.AbstractEventLoop, asyncio.Future]] = {}
        self._lock = threading.Lock()
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self) -> None:
        while True:
            try:
                call_id, ok, value = self._inbox.recv()
            except (EOFError, OSError):
                break
            with self._lock:
                loop, future = self._pending.pop(call_id, (None, None))
            if future is not None:
                loop.call_soon_threadsafe(_settle, future, ok, value)
        self.process.join(5)
        with self._lock:
            pending, self._pending = self._pending, {}
        for loop, future in pending.values():
            loop.call_soon_threadsafe(_fail, future, HelperDied(self.process.exitcode))

    async def call(self, method: str, *args, context: dict | None = None):
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        call_id = next(self._ids)
        with self._lock:
            if not self._reader.is_alive():
                raise HelperDied(self.process.exitcode)
            self._pending[call_id] = (loop, future)
            self._outbox.send((call_id, method, args, context))
        return await future

    def stop(self, timeout: float = 60) -> int | None:
        if self.process.is_alive():
            try:
                with self._lock:
                    self._outbox.send(None)
            except (OSError, ValueError):
                pass
            self.process.join(timeout)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(10)
        self._outbox.close()
        return self.process.exitcode


class RemoteError(RuntimeError):
    def __init__(self, value: dict):
        super().__init__(f"{value.get('type')}: {value.get('message')}")
        self.value = value


def _settle(future: asyncio.Future, ok: bool, value) -> None:
    if future.done():
        return
    if ok:
        future.set_result(value)
    else:
        future.set_exception(RemoteError(value))


def _fail(future: asyncio.Future, exc: Exception) -> None:
    if not future.done():
        future.set_exception(exc)
