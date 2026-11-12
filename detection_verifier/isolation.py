"""Process separation with timeout enforcement for UNTRUSTED candidate evaluation.

This is NOT a security sandbox. A forked child inherits substantial parent state
and this boundary does not restrict filesystem, network, or credential access; it
bounds wall-clock and isolates crashes. A real sandbox (seccomp/container/user
namespace) is a separate, later control.

Round-9 fixes:
  * No join-before-drain deadlock (Astra #1): the parent receives the bounded
    result via a Pipe with poll(deadline), then reaps the child. Queue.empty() is
    not used as a decision mechanism.
  * Bounded result size: the child sends a small 'toobig' marker instead of a
    huge blob, so a large valid result never looks like a timeout.
  * Bounded cleanup/escalation (Astra #2): terminate -> bounded join -> kill ->
    bounded join; finite timeout validated; IPC closed in finally.
  * Typed outcomes: timeout / result-too-large / child exception / crash-without-
    result are distinct.
"""

from __future__ import annotations

import contextlib
import math
import multiprocessing as mp
import pickle

MAX_RESULT_BYTES = 1 << 20  # 1 MiB cap on a candidate's returned result
_TERM_GRACE_S = 1.0


class CandidateTimeout(Exception):
    """Candidate exceeded its wall-clock budget (process killed)."""


class ResultTooLarge(Exception):
    """Candidate returned a result larger than MAX_RESULT_BYTES."""


class CandidateError(Exception):
    """Candidate crashed without a result, or an IPC/serialisation failure."""


def _worker(send_conn, func, args, kwargs):
    try:
        result = func(*args, **kwargs)
        try:
            blob = pickle.dumps(result)
        except Exception as e:
            send_conn.send(("serr", f"result not picklable: {type(e).__name__}: {e}"))
            return
        if len(blob) > MAX_RESULT_BYTES:
            send_conn.send(("toobig", len(blob)))
        else:
            send_conn.send(("ok", blob))
    except BaseException as e:  # propagate the child's exception by type
        try:
            send_conn.send(("exc", pickle.dumps(e)))
        except Exception:
            send_conn.send(("serr", f"uncatchable child error: {type(e).__name__}: {e}"))
    finally:
        with contextlib.suppress(Exception):
            send_conn.close()


def run_isolated(func, args=(), kwargs=None, *, timeout_s: float):
    """Run func(*args, **kwargs) in a child process under a hard wall-clock
    timeout. Returns the result; re-raises the child's exception by type when
    picklable; raises CandidateTimeout / ResultTooLarge / CandidateError.
    func, args, kwargs, result, and any raised exception must be picklable."""
    if (
        not isinstance(timeout_s, (int, float))
        or math.isnan(timeout_s)
        or math.isinf(timeout_s)
        or timeout_s <= 0
    ):
        raise ValueError("timeout_s must be a positive finite number")
    ctx = mp.get_context("fork" if "fork" in mp.get_all_start_methods() else "spawn")
    recv_conn, send_conn = ctx.Pipe(duplex=False)
    p = ctx.Process(target=_worker, args=(send_conn, func, args, kwargs or {}))
    p.start()
    send_conn.close()  # parent holds only the receiving end

    tag = payload = None
    timed_out = False
    exitcode = None
    try:
        if recv_conn.poll(timeout_s):  # wait for data OR deadline (drains, no join-first)
            try:
                tag, payload = recv_conn.recv()
            except (EOFError, OSError):
                tag = None  # child closed the pipe without sending
        else:
            timed_out = p.is_alive()
    finally:
        with contextlib.suppress(Exception):
            recv_conn.close()
        # bounded termination: terminate -> join(grace) -> kill -> join(grace)
        if p.is_alive():
            p.terminate()
            p.join(_TERM_GRACE_S)
        if p.is_alive():
            p.kill()
            p.join(_TERM_GRACE_S)
        exitcode = p.exitcode
        with contextlib.suppress(Exception):
            p.close()

    if tag is None:
        if timed_out:
            raise CandidateTimeout(f"candidate exceeded {timeout_s}s (process killed)")
        raise CandidateError(f"worker exited without a result (exitcode={exitcode})")

    if tag == "ok":
        try:
            return pickle.loads(payload)
        except Exception as e:
            raise CandidateError(f"result deserialisation failed: {e}") from e
    if tag == "toobig":
        raise ResultTooLarge(f"result {payload} bytes > MAX_RESULT_BYTES={MAX_RESULT_BYTES}")
    if tag == "serr":
        raise CandidateError(payload)
    if tag == "exc":
        try:
            child_error = pickle.loads(payload)
        except (pickle.UnpicklingError, TypeError, AttributeError) as e:
            raise CandidateError(f"child raised an unpicklable exception: {e}") from e
        raise child_error
    raise CandidateError(f"unknown worker tag {tag!r}")
