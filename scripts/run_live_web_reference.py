"""Generate real HTTP/process reference evidence locally, without model tokens."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rental.live_web import LabSession, run_loop


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as output:
        for label in ("success", "failed", "pre_satisfied", "patched_control", "long_context"):
            case = "success" if label == "long_context" else label
            session = LabSession(
                [
                    sys.executable,
                    "-m",
                    "lab.web_workflow.worker",
                    "--case",
                    case,
                    "--background-requests",
                    "128" if label == "long_context" else "0",
                ]
            )
            actions = iter(
                ["discover", "read_owner"]
                + (["read_activity"] if label == "long_context" else [])
                + ([] if case == "failed" else ["read_other"])
                + ["finish"]
            )

            def scripted(messages, actions=actions):
                return {
                    "content": json.dumps({"kind": next(actions)}),
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                }

            try:
                record = run_loop(session, scripted)
            finally:
                session.close()
            record["provenance"] = {
                "split": "development",
                "source": "scripted_live_http_reference",
                "scenario": "owned-http-authz-v1",
                "case": case,
                "verifier_version": "http-response-sqlite-audit-v1",
                "model_executed": False,
                "context_profile": label,
                "background_requests": 128 if label == "long_context" else 0,
            }
            output.write(json.dumps(record) + "\n")
            print(label, record.get("offensive_verdict"), record.get("defensive_verdict"))


if __name__ == "__main__":
    main()
