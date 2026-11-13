"""Export: an EVIDENCE bundle (hashed) separate from INFERENCE artifacts (adapter
weights). Adapter weights support inference or a fresh-optimiser restart — NOT
faithful training resumption; we label exactly that and add no checkpoint
machinery for a 10-step smoke (Astra #6). Hashes are recomputed from the ARCHIVED
bytes, paths are archive-relative and consistent, missing items are explicit, and
a partial bundle is preserved on failure.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tarfile
from pathlib import Path


def arcname(path: str) -> str:
    """Consistent archive-relative name (tarfile strips leading '/')."""
    return path.replace("\\", "/").split(":", 1)[-1].lstrip("/")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_verified_bundle(source: str, destination: str) -> dict:
    """Copy to an existing mounted export directory and verify read-back bytes.

    A successful receipt proves this filesystem copy, not that the mount is
    physically off-instance; the operator must establish that separately.
    """
    src, directory = Path(source).resolve(), Path(destination).resolve()
    if not directory.is_dir() or directory == src.parent or directory.is_relative_to(src.parent):
        raise ValueError("export destination must exist outside the run directory")
    target = directory / src.name
    with target.open("xb") as output, src.open("rb") as incoming:
        shutil.copyfileobj(incoming, output)
        output.flush()
        os.fsync(output.fileno())
    expected = sha256_file(str(src))
    if sha256_file(str(target)) != expected:
        raise ValueError("export read-back hash mismatch")
    return {"destination": str(target), "sha256": expected, "readback_verified": True}


def build_manifest(evidence: list[str], inference_artifacts: list[str]) -> dict:
    def scan(paths):
        present, missing = {}, []
        for p in paths:
            (present.__setitem__(p, sha256_file(p)) if os.path.isfile(p) else missing.append(p))
        return present, missing

    ev_p, ev_m = scan(evidence)
    ia_p, ia_m = scan(inference_artifacts)
    return {
        "evidence": {"present": ev_p, "missing": ev_m},
        "inference_artifacts": {
            "present": ia_p,
            "missing": ia_m,
            "note": "adapter weights: inference / fresh-optimiser restart only, "
            "NOT faithful training resume",
        },
        "evidence_complete": not ev_m,
    }


def write_archive(tar_path: str, files: list[str], extra_members: dict[str, bytes]) -> None:
    """Archive files under their given archive-relative paths (consistent, not
    basenames); add in-memory members (e.g. MANIFEST.json, resolved config)."""
    import io

    with tarfile.open(tar_path, "w:gz") as t:
        for p in files:
            if os.path.isfile(p):
                t.add(p, arcname=arcname(p))  # consistent archive-relative path
        for name, data in extra_members.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))


def verify_archive(tar_path: str, expected: dict[str, str]) -> tuple[bool, list[str]]:
    """Recompute sha256 from the ARCHIVED file contents and compare to expected
    {arcname: sha256}. Returns (ok, mismatches)."""
    mismatches = []
    with tarfile.open(tar_path, "r:gz") as t:
        members = {m.name: m for m in t.getmembers()}
        for name, want in expected.items():
            if name not in members:
                mismatches.append(f"missing in archive: {name}")
                continue
            h = hashlib.sha256()
            f = t.extractfile(members[name])
            if f is None:
                mismatches.append(f"unreadable in archive: {name}")
                continue
            with f:
                while chunk := f.read(65536):
                    h.update(chunk)
            if h.hexdigest() != want:
                mismatches.append(f"hash mismatch: {name}")
    return (not mismatches, mismatches)
