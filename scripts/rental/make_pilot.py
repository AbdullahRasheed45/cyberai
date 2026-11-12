#!/usr/bin/env python3
"""Export development-only pilot JSONL; never reads acceptance/challenge data."""

import argparse
import json
from pathlib import Path

from rental.pilot import build_pilot_examples
from rental.web_pilot import build_web_pilot_examples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", choices=["web", "detection"], default="web")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    builder = build_web_pilot_examples if args.domain == "web" else build_pilot_examples
    rows = builder(f"fixtures/{args.domain}")
    with args.out.open("x", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row) + "\n")
    print(
        json.dumps(
            {
                "file": str(args.out),
                "examples": len(rows),
                "domain": args.domain,
                "evidence": "public fixture plumbing; no learning or offensive-outcome claim",
            }
        )
    )


if __name__ == "__main__":
    main()
