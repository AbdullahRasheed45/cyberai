import json
import os
import subprocess
import sys

from rental.probe import compare_versions


def test_image_dependency_pins_are_exact_not_prefixes():
    assert compare_versions({"trl": "1.20"}, {"trl": "1.2"}, ["trl"])


def test_partial_export_preserves_bundle_but_exits_unsuccessfully(tmp_path):
    output = tmp_path / "evidence"
    result = subprocess.run(
        [sys.executable, "scripts/rental/50_export.py"],
        env={**os.environ, "ARTIFACT_DIR": str(output), "SMOKE_OUT": str(tmp_path / "missing")},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 2
    record = json.loads(result.stdout)
    assert record["verified_against_archived_hashes"]
    assert not record["evidence_complete"]
    assert record["missing_inference_artifacts"]
    assert list(output.glob("*.tar.gz"))
