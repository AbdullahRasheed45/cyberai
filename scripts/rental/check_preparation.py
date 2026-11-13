"""Read-only rental preparation report. Does not provision or start Docker."""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml

from rental.freeze import validate_freeze


def main():
    freeze = Path(os.environ.get("FREEZE", "scripts/rental/FREEZE.yaml"))
    blockers = validate_freeze(yaml.safe_load(freeze.read_text(encoding="utf-8")))
    required = ["MODEL_PATH", "EVIDENCE_EXPORT_DIR", "RENTAL_STOP_UTC"]
    commands = ["docker"]
    domain = os.environ.get("WORKLOAD_DOMAIN", "web")
    if domain == "web":
        required.append("LAB_SSH_HOST")
        commands.append("ssh")  # only the live web lab is reached over SSH
    elif domain != "detection":
        blockers.append("WORKLOAD_DOMAIN must be web or detection")
    for command in commands:
        if not shutil.which(command):
            blockers.append(f"{command} unavailable on this host")
    for key in required:
        if not os.environ.get(key):
            blockers.append(f"configure {key}")
    for key in ("MODEL_PATH", "EVIDENCE_EXPORT_DIR"):
        if os.environ.get(key) and not Path(os.environ[key]).is_dir():
            blockers.append(f"{key} directory does not exist")
    deadline = os.environ.get("RENTAL_STOP_UTC")
    if deadline:
        try:
            parsed = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed <= datetime.now(UTC):
                raise ValueError("deadline must be timezone-aware and in the future")
        except ValueError as exc:
            blockers.append(f"invalid RENTAL_STOP_UTC: {exc}")
    print(
        json.dumps(
            {
                "status": "NOT_READY" if blockers else "CONFIGURED_UNVERIFIED",
                "blockers": blockers,
                "pending_checks": [
                    "separate-host SSH lab rehearsal",
                    "export restore receipt",
                    "GPU compatibility and measurements",
                ],
            },
            indent=2,
        )
    )
    raise SystemExit(2 if blockers else 0)


if __name__ == "__main__":
    main()
