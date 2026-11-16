"""Bound stdin before JSON parsing; terminate idle and partial-line sessions."""

import os
import queue
import threading
import time

MAX_ACTION_BYTES = 8192
MAX_ACTIONS = 16
SESSION_SECONDS = 300


class ProtocolEnd(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def action_lines(fd, idle_timeout, partial_timeout=10):
    lines = queue.Queue(maxsize=1)

    def read():
        pending = bytearray()
        try:
            while True:
                chunk = os.read(fd, 1024)
                if not chunk:
                    lines.put(ProtocolEnd("EOF"))
                    return
                for byte in chunk:
                    if not pending:
                        lines.put(("line_started", time.monotonic()))
                    pending.append(byte)
                    if len(pending) > MAX_ACTION_BYTES:
                        lines.put(ProtocolEnd("INPUT_TOO_LARGE"))
                        return
                    if byte == 10:
                        lines.put(bytes(pending))
                        pending.clear()
        except OSError:
            lines.put(ProtocolEnd("INPUT_ERROR"))

    # Raw os.read avoids holding a Python buffered-stream lock on shutdown.
    threading.Thread(target=read, daemon=True).start()
    deadline = time.monotonic() + SESSION_SECONDS
    line_deadline = min(deadline, time.monotonic() + idle_timeout)
    while True:
        remaining = line_deadline - time.monotonic()
        if remaining <= 0:
            raise ProtocolEnd("TIMEOUT")
        try:
            line = lines.get(timeout=remaining)
        except queue.Empty as exc:
            raise ProtocolEnd("TIMEOUT") from exc
        if isinstance(line, ProtocolEnd):
            raise line
        if isinstance(line, tuple):
            line_deadline = min(line_deadline, line[1] + partial_timeout)
            continue
        yield line
        line_deadline = min(deadline, time.monotonic() + idle_timeout)


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON key")
        result[name] = value
    return result
