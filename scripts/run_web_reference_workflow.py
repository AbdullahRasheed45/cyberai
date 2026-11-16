#!/usr/bin/env python3
"""Execute deterministic owned-lab web reference cases and export JSONL evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab.web_workflow.reference import run_reference_case
from lab.web_workflow.store import TrajectoryStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=["all", "success", "failed", "pre_satisfied", "patched_control"],
        default="all",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    cases = (
        ["success", "failed", "pre_satisfied", "patched_control"]
        if args.case == "all"
        else [args.case]
    )
    store = TrajectoryStore(args.out)
    records = [run_reference_case(case) for case in cases]
    for record in records:
        store.append(record)
    print(json.dumps([record.to_dict() for record in records], indent=2))


if __name__ == "__main__":
    main()
