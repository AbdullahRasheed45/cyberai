"""Cooperative trial lock, not the future privileged authorization broker.

One Linux user's checkout copies share the lock. Keep the inode after release.
Processes that bypass this wrapper are outside this operational protection.
"""

import contextlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def default_lock_path():
    identity = str(os.getuid()) if hasattr(os, "getuid") else "windows"
    return Path(tempfile.gettempdir()) / f"cyberai-trial-{identity}.lock"


@contextlib.contextmanager
def trial_lock(path=None):
    path = Path(path or default_lock_path())
    with path.open("a+b") as handle:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            if path.stat().st_size == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)

            def acquire():
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

            def release():
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            def acquire():
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            def release():
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        try:
            acquire()
        except OSError as exc:
            raise RuntimeError("another trial operation holds the GPU lifecycle lock") from exc
        try:
            yield
        finally:
            release()


def main():
    command = sys.argv[1:]
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        raise SystemExit("usage: python -m rental.exclusive -- COMMAND [ARG ...]")
    with trial_lock():
        raise SystemExit(subprocess.call(command))


if __name__ == "__main__":
    main()
