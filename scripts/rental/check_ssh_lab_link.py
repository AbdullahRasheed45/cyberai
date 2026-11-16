#!/usr/bin/env python3
"""Rehearse the real two-machine SSH link (Astra finding 23).

`scripts/run_live_web_reference.py` is explicitly local-only (its own
docstring: "generate... locally, without model tokens") — it always spawns
`lab.web_workflow.worker` as an in-process subprocess and never reads
LAB_SSH_HOST, so pointing a "does the link work" rehearsal at it would pass
even if the lab laptop were completely unreachable. This script is the one
that actually goes over SSH: it mirrors the exact SSH invocation
`scripts/rental/46_live_web_workflow.py` uses for the real web workload, but
drives the worker with a scripted action sequence instead of a served model,
so it needs no vLLM endpoint — only the link and the lab checkout.

It also fails loudly, not just silently, if the worker it talked to turns out
to be local: the worker reports its own hostname in its readiness line
(lab/web_workflow/worker.py), and this script refuses to call that a passed
rehearsal unless that hostname is NOT the machine this script is running on.

Usage (from the Spark, LAB_SSH_HOST set to the configured alias):
    uv run python scripts/rental/check_ssh_lab_link.py --out artifacts/link_rehearsal.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
from pathlib import Path

from rental.live_web import LabSession, run_loop, ssh_worker_argv, validate_remote_worker

HOST_ALIAS_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")


class LinkNotExercisedError(RuntimeError):
    """Raised when the "remote" worker turns out to have run locally — the
    exact false-pass finding 23 identified in the local-only reference script."""


def validate_host_alias(host: str) -> str:
    if not HOST_ALIAS_RE.fullmatch(host or ""):
        raise ValueError("LAB_SSH_HOST must be a configured SSH alias")
    return host


def ssh_argv(host: str) -> list[str]:
    """The exact SSH invocation, identical in shape to 46_live_web_workflow.py's,
    so a passing rehearsal here is evidence about the SAME transport the real
    web workload will use."""
    return ssh_worker_argv(host)


def verify_remote(
    remote_host: str | None, local_host: str, expected_host: str | None = None
) -> str:
    """Return remote_host if it genuinely identifies a different machine; raise
    LinkNotExercisedError otherwise. Pure — no I/O, directly unit-testable."""
    if not remote_host or remote_host == local_host:
        raise LinkNotExercisedError(
            f"worker reported host={remote_host!r}; expected a remote host distinct "
            f"from this machine ({local_host!r}) — the SSH link was not actually exercised"
        )
    if expected_host is not None and remote_host != expected_host:
        raise LinkNotExercisedError("worker identity does not match configured expected host")
    return remote_host


def scripted_actions():
    actions = iter(["discover", "read_owner", "read_other", "finish"])

    def complete(messages):
        return {
            "content": json.dumps({"kind": next(actions)}),
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }

    return complete


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-host", default=os.environ.get("LAB_EXPECTED_HOSTNAME"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    try:
        host = validate_host_alias(os.environ.get("LAB_SSH_HOST", ""))
        if not args.expected_host:
            raise ValueError("LAB_EXPECTED_HOSTNAME or --expected-host is required")
    except ValueError as exc:
        print(json.dumps({"rehearsal": "ABORTED", "reason": str(exc)}), file=sys.stderr)
        return 1

    local_host = socket.gethostname()
    session = None
    remote_host = None
    try:
        session = LabSession(ssh_argv(host))
        remote_host = verify_remote(session.ready_info.get("host"), local_host, args.expected_host)
        validate_remote_worker(session.ready_info, args.expected_host)
        record = run_loop(session, scripted_actions())
    except Exception as exc:
        record = {
            "task_success": False,
            "failure_category": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        if session:
            session.close()

    record["provenance"] = {
        "source": "scripted_ssh_link_rehearsal",
        "scenario": "owned-http-authz-v1",
        "lab_ssh_host_alias": host,
        "remote_host": remote_host,
        "local_host": local_host,
        "expected_host": args.expected_host,
        "isolation_verified": False,
        "model_executed": False,
    }
    args.out.write_text(json.dumps(record) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    if not remote_host or not record.get("task_success"):
        return 1
    print(f"SSH link rehearsal PASSED: worker ran on {remote_host!r}, reached from {local_host!r}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
