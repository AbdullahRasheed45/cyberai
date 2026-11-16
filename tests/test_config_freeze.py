"""Round-15: probe robustness, snapshot manifest, and the task-relevant pilot
(Astra #2/#1/#5). Pure/offline."""

from __future__ import annotations

import json
import os
import subprocess as _sp
import sys as _sys
from pathlib import Path

import pytest
import yaml

from detection_verifier.checker import check_rule
from rental import plan as _plan
from rental.pilot import build_pilot_examples
from rental.plan import FreezeInvalid as _FI
from rental.probe import MARKER, PROBE_SRC, compare_versions, extract_probe, probe_argv
from rental.snapshot import build_manifest, verify_against_manifest

FX = Path(__file__).resolve().parents[1] / "fixtures" / "detection"


# --- #2: probe parsing tolerates banners; compares per-image ------------------


def test_extract_probe_ignores_banner_lines():
    stdout = (
        "==NGC banner==\nWARNING: something\n"
        + MARKER
        + json.dumps({"versions": {"torch": "2.10.0"}, "cuda": True})
        + "\n"
    )
    p = extract_probe(stdout)
    assert p and p["cuda"] and p["versions"]["torch"] == "2.10.0"


def test_extract_probe_none_when_absent():
    assert extract_probe("no json here\njust text") is None


def test_compare_versions_reports_mismatch_and_import_fail():
    found = {"torch": "2.10.0", "transformers": "IMPORT_FAIL:ModuleNotFoundError"}
    errs = compare_versions(
        found, {"torch": "2.9", "transformers": "5.0.0"}, ["torch", "transformers", "peft"]
    )
    assert any("torch 2.10.0 != pinned 2.9" in e for e in errs)
    assert any("transformers failed to import" in e for e in errs)
    assert any("peft not reported" in e for e in errs)


# --- #1: snapshot manifest build + verify + tamper ---------------------------


def test_snapshot_manifest_roundtrip_and_tamper(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"hello")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.json").write_text("{}")
    man = build_manifest(str(tmp_path))
    assert set(man) == {"a.bin", os.path.join("sub", "b.json")}
    assert verify_against_manifest(str(tmp_path), man) == []
    (tmp_path / "a.bin").write_bytes(b"tampered")
    errs = verify_against_manifest(str(tmp_path), man)
    assert any("hash mismatch: a.bin" in e for e in errs)
    man["missing.bin"] = "0" * 64
    assert any("missing snapshot file" in e for e in verify_against_manifest(str(tmp_path), man))


# --- #5: pilot targets are known-good rules that VERIFY -----------------------


def test_pilot_examples_are_task_relevant_and_verify():
    ex = build_pilot_examples(str(FX))
    assert ex and all(len(e["messages"]) == 2 for e in ex)
    # the target rule embedded in every example actually passes the verifier
    pres = [
        json.loads(line)
        for line in (FX / "behaviour_present.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    absent = [
        json.loads(line)
        for line in (FX / "behaviour_absent.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    target = ex[0]["messages"][1]["content"]
    rule_yaml = target.split("<rule>")[1].split("</rule>")[0]
    v = check_rule(yaml.safe_load(rule_yaml), pres, absent)
    assert v.outcome == "VERIFIED"  # the pilot teaches a rule that is actually correct


# --- R16: test the ACTUAL probe source (compiles + executes), not hand output -


def test_probe_source_compiles():
    compile(PROBE_SRC, "accelerator_probe", "exec")  # Astra: this previously raised SyntaxError


def test_probe_source_executes_with_marker_even_if_imports_fail():
    prefix = (
        "import importlib\nfrom unittest.mock import patch\n"
        "def blocked(name, *a, **k):\n    raise ImportError(name)\n"
        "with patch.object(importlib, 'import_module', blocked):\n"
    )
    source = prefix + "\n".join("    " + line for line in PROBE_SRC.splitlines())
    r = _sp.run([_sys.executable, "-c", source], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    parsed = extract_probe(r.stdout)
    assert parsed is not None and "versions" in parsed
    assert isinstance(parsed["cuda"], bool)  # portable across CPU/GPU hosts
    assert parsed["versions"]["torch"].startswith(
        "IMPORT_FAIL"
    )  # optional import failed, probe survived


def test_probe_argv_passes_source_as_one_arg():
    a = probe_argv("img@sha256:" + "a" * 64)
    assert a[:3] == ["docker", "run", "--rm"] and "--gpus" in a
    # source travels as ONE env value; the login shell matches the training command
    assert a[a.index("-e") + 1] == "CYBERAI_PROBE_SRC=" + PROBE_SRC
    assert a[-3:] == ["bash", "-lc", 'exec python -c "$CYBERAI_PROBE_SRC"']
    assert a.index("img@sha256:" + "a" * 64) == len(a) - 4  # image precedes the command


def test_probe_runs_through_same_login_shell_as_training():
    from rental import plan as _p

    rc = _p.ResolvedConfig(
        vllm_image="v@sha256:" + "a" * 64,
        unsloth_image="u@sha256:" + "b" * 64,
        host_repo="/repo",
        host_model_path="/m",
        host_adapter_path="/repo/runs/r/adapter",
        train_repo="unsloth/Qwen3-30B-A3B-Instruct-2507",
        train_commit="c" * 40,
        serving_repo="s",
        serving_commit="d" * 40,
        serving_quant="FP8",
        serving_provenance="p",
        dependencies=(),
        run_id="r",
    )
    train = _p.train_argv(rc)
    assert train[-3:-1] == ["bash", "-lc"] and probe_argv("x")[-3:-1] == ["bash", "-lc"]


# --- R16: the pilot is forwarded into Docker; missing requested pilot fails ---


def _good_freeze2():
    f = yaml.safe_load(Path("scripts/rental/FREEZE.yaml").read_text(encoding="utf-8"))
    sha = "a" * 40
    dig = "x@sha256:" + "b" * 64
    f.update(
        trainable_base_commit=sha,
        serving_base_commit=sha,
        serving_quant_provenance="official FP8",
        vllm_image=dig,
        unsloth_image=dig,
        trainable_serving_relation_attested=True,
        dependencies=[
            "transformers==5.0.0",
            "unsloth==2025.11.1",
            "peft==0.17.0",
            "trl==0.12.0",
            "bitsandbytes==0.45.0",
        ],
    )
    return f


def test_pilot_forwarded_into_docker():
    rc = _plan.resolve(
        _good_freeze2(),
        env={
            "MODEL_PATH": "/m",
            "RUN_ID": "r1",
            "TRAIN_MODE": "pilot",
            "PILOT_DATA": "pyproject.toml",
        },
    )
    argv = _plan.train_argv(rc)
    assert "-e" in argv and "PILOT_DATA=pyproject.toml" in argv and "TRAIN_MODE=pilot" in argv


def test_requested_pilot_missing_file_rejected():
    with pytest.raises(_FI):
        _plan.resolve(
            _good_freeze2(),
            env={"MODEL_PATH": "/m", "TRAIN_MODE": "pilot", "PILOT_DATA": "nope.jsonl"},
        )


def test_pilot_mode_requires_pilot_data():
    with pytest.raises(_FI):
        _plan.resolve(_good_freeze2(), env={"MODEL_PATH": "/m", "TRAIN_MODE": "pilot"})


def test_pingpong_is_explicit_default():
    rc = _plan.resolve(_good_freeze2(), env={"MODEL_PATH": "/m", "RUN_ID": "r1"})
    assert rc.train_mode == "pingpong"
    assert "TRAIN_MODE=pingpong" in _plan.train_argv(rc)


# --- R16: snapshot manifest is rerun-safe (excludes itself) -------------------
def test_build_manifest_excludes_itself_and_rejects_empty(tmp_path):
    from rental.snapshot import MANIFEST_NAME, build_manifest

    (tmp_path / "model.safetensors").write_bytes(b"w")
    (tmp_path / MANIFEST_NAME).write_text('{"stale":true}')
    (tmp_path / "x.lock").write_text("lock")
    man = build_manifest(str(tmp_path))
    assert MANIFEST_NAME not in man and "x.lock" not in man and "model.safetensors" in man
    import pytest as _pt

    with _pt.raises(ValueError):
        build_manifest(str(tmp_path / "nonexistent_empty"))
