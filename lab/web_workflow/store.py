from __future__ import annotations

import json
from pathlib import Path

from .reference import WorkflowRecord


class TrajectoryStore:
    """Append-only JSONL evidence store; acceptance data is never read here."""

    def __init__(self, path: Path):
        self.path = path

    def append(self, record: WorkflowRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
