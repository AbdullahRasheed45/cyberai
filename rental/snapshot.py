"""Exact checkpoint identity via a materialised snapshot + file manifest (Astra #1).

Structural checks (rental.checkpoint) are a sanity gate; EXACT identity is this:
download the declared repo@immutable-commit, record a hash manifest, and verify the
local serving files match it. The download needs the hub (rental-setup); the
manifest build + verify are pure and tested offline.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


MANIFEST_NAME = "SNAPSHOT_MANIFEST.json"
_EXCLUDE_DIRS = {".cache", ".huggingface", ".git"}
_EXCLUDE_SUFFIX = (".lock", ".incomplete", ".metadata")


def build_manifest(local_dir: str) -> dict:
    """{relpath: sha256} over the snapshot's model files only — EXCLUDES the
    manifest itself and transient download metadata so a rerun cannot self-mismatch."""
    out = {}
    for root, dirs, files in os.walk(local_dir):
        dirs[:] = [d for d in dirs if d not in _EXCLUDE_DIRS]
        for fn in sorted(files):
            if fn == MANIFEST_NAME or fn.endswith(_EXCLUDE_SUFFIX):
                continue
            full = os.path.join(root, fn)
            out[os.path.relpath(full, local_dir)] = _sha256(full)
    if not out:
        raise ValueError(f"empty manifest: no model files found under {local_dir!r}")
    return out


def verify_against_manifest(local_dir: str, manifest: dict) -> list[str]:
    """Return errors where local files are missing or hash-mismatch the manifest."""
    errs = []
    for rel, want in manifest.items():
        p = os.path.join(local_dir, rel)
        if not os.path.isfile(p):
            errs.append(f"missing snapshot file: {rel}")
        elif _sha256(p) != want:
            errs.append(f"hash mismatch: {rel}")
    return errs


def materialise(repo: str, commit: str, dest: str) -> dict:  # pragma: no cover - needs hub
    """Download repo@commit (immutable), write manifest.json beside it, return it."""
    import re

    from huggingface_hub import snapshot_download

    if not re.fullmatch(r"[0-9a-f]{40}", commit or ""):
        raise ValueError("commit must be a 40-hex immutable revision, not a branch")
    path = snapshot_download(repo, revision=commit, local_dir=dest)
    man = build_manifest(path)
    Path(os.path.join(dest, "SNAPSHOT_MANIFEST.json")).write_text(
        json.dumps({"repo": repo, "commit": commit, "manifest": man}, indent=2), encoding="utf-8"
    )
    return man
