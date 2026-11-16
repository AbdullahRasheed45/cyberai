import json
import os
import subprocess
import sys
import tarfile

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


def test_export_includes_selected_freeze_and_live_trajectory(tmp_path):
    output = tmp_path / "evidence"
    output.mkdir()
    for name in (
        "preflight.json",
        "inference_measurements.json",
        "workload_result.json",
        "orchestration.json",
        "web_offensive_trajectories.jsonl",
    ):
        (output / name).write_text("{}", encoding="utf-8")
    training = tmp_path / "training"
    adapter = training / "adapter"
    adapter.mkdir(parents=True)
    (training / "train_meta.json").write_text("{}", encoding="utf-8")
    (adapter / "adapter_config.json").write_text("{}", encoding="utf-8")
    (adapter / "adapter_model.safetensors").write_bytes(b"test-only")
    freeze = tmp_path / "actual-run-freeze.yaml"
    freeze.write_text("run: actual", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/rental/50_export.py"],
        env={
            **os.environ,
            "ARTIFACT_DIR": str(output),
            "SMOKE_OUT": str(training),
            "FREEZE": str(freeze),
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    with tarfile.open(next(output.glob("*.tar.gz"))) as archive:
        names = archive.getnames()
        assert any(name.endswith("actual-run-freeze.yaml") for name in names)
        assert any(name.endswith("web_offensive_trajectories.jsonl") for name in names)
