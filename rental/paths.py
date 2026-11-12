"""One artifact directory per run (Astra #2): stale measurements/adapters from a
previous trial cannot be mistaken for current evidence."""

from __future__ import annotations

import os


def artifact_dir() -> str:
    return os.environ.get("ARTIFACT_DIR", "artifacts")
