#!/usr/bin/env python3
"""Export development-only pilot JSONL; never reads acceptance/challenge data."""

import argparse
import json
from pathlib import Path

from rental.pilot import build_pilot_examples
from rental.web_pilot import build_web_offensive_pilot_examples, build_web_pilot_examples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", choices=["web", "detection"], default="web")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--context-stress",
        action="store_true",
        help="include repeated-context stress data; not representative learning data",
    )
    parser.add_argument(
        "--trajectories", type=Path, help="development-only verified live reference JSONL"
    )
    args = parser.parse_args()
    builder = build_web_pilot_examples if args.domain == "web" else build_pilot_examples
    rows = builder(f"fixtures/{args.domain}")
    if args.domain == "web" and args.context_stress:
        rows += build_web_offensive_pilot_examples()
    if args.trajectories:
        for line in args.trajectories.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record.get("provenance", {}).get("split") != "development":
                raise ValueError("only development trajectories can select training targets")
            if (
                record.get("offensive_verdict") == "VERIFIED"
                and record.get("defensive_verdict") == "REMEDIATED"
                and record.get("task_success") is True
            ):
                # Final observation contains verifier decisions; exclude it from
                # supervised model messages so the agent never impersonates a gate.
                rows.append({"messages": record["messages"][:-1], "metadata": record["provenance"]})
    evidence = "; ".join(
        ("development-only fixture/reference plumbing", "no learning or acceptance claim")
    )
    with args.out.open("x", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row) + "\n")
    print(
        json.dumps(
            {
                "file": str(args.out),
                "examples": len(rows),
                "domain": args.domain,
                "evidence": evidence,
            }
        )
    )


if __name__ == "__main__":
    main()
