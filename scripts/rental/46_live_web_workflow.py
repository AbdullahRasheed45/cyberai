#!/usr/bin/env python3
"""Iterative Qwen execution against the separate owned lab via SSH."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path

from rental.clients import parse_completion
from rental.live_web import LabSession, run_loop
from rental.paths import artifact_dir


def main():
    output = Path(artifact_dir())
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    record = {"task_success": False, "failure_category": "SETUP_FAILED"}
    session = None
    try:
        host = os.environ["LAB_SSH_HOST"]
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", host):
            raise ValueError("LAB_SSH_HOST must be a configured SSH alias")
        session = LabSession(
            [
                "ssh",
                "-T",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                "-o",
                "StrictHostKeyChecking=yes",
                host,
                "python3",
                "-m",
                "lab.web_workflow.worker",
            ]
        )

        def complete(messages):
            request = urllib.request.Request(
                os.environ["VLLM_URL"],
                data=json.dumps(
                    {
                        "model": os.environ["SERVED_MODEL"],
                        "messages": messages,
                        "max_tokens": 512,
                        "temperature": 0,
                    }
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=120) as response:
                return parse_completion(response.status, response.read().decode())

        record = run_loop(session, complete)
        record["source"] = "qwen_live_http_lab"
    except Exception as exc:
        record.update(error=str(exc), failure_category=type(exc).__name__)
    finally:
        if session:
            session.close()
        record["complete_runtime_s"] = time.monotonic() - started
        record["acceptance_data_read"] = False
        (output / "workload_result.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        with (output / "web_offensive_trajectories.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")
    print(json.dumps(record, indent=2))
    if not record.get("task_success"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
