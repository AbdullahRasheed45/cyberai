"""The Stage-1 baseline report is built only from recorded results, never invented."""

import importlib.util
import json
import subprocess
import sys


def _module():
    spec = importlib.util.spec_from_file_location("summarise", "scripts/rental/summarise_trial.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _trial(tmp_path):
    art, runs = tmp_path / "artifacts", tmp_path / "runs"
    run = art / "run_r1"
    run.mkdir(parents=True)
    (run / "receipt.json").write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "phases": ["preflight", "export"],
                "releases": [{"release": "confirmed"}],
            }
        )
    )
    (run / "orchestration.json").write_text(
        json.dumps(
            {"memory_telemetry": "host /proc/meminfo", "docker_runtime": {"gpu_mode": "runtime"}}
        )
    )
    (run / "inference_measurements.json").write_text(
        json.dumps(
            {
                "passed": False,
                "single_stream": {"ttft_s_mean": 0.41, "decode_tok_s_mean": 55.2},
                "matrix": {
                    "ctx8000_conc8_cold": {"n": 8, "n_ok": 7, "aggregate_output_tok_s": 210.5}
                },
                "context_errors": {"16000": "TimeoutError: slow"},
            }
        )
    )
    for name, precision, rate in (("r1", "qlora_4bit", 1000.0), ("r2", "bf16", 2000.0)):
        d = runs / name
        d.mkdir(parents=True)
        (d / "train_meta.json").write_text(
            json.dumps(
                {
                    "precision": precision,
                    "steady_state_tok_s": rate,
                    "training_config": {"max_seq_length": 2048, "batch_size": 1},
                    "processed_sequence_length_histogram": {"300": 5, "912": 2},
                }
            )
        )
    (runs / "r1" / "reload_result.json").write_text(
        json.dumps({"smoke_reload": "PASSED", "logit_match": "exact"})
    )
    return art, runs


def test_report_uses_recorded_values_and_marks_gaps(tmp_path):
    art, runs = _trial(tmp_path)
    report = _module().build(art, runs)
    assert "COMPLETED" in report and "runtime" in report and "host /proc/meminfo" in report
    assert "55.2" in report and "210.5" in report and "7/8" in report
    assert "TimeoutError: slow" in report  # failures are shown, not hidden
    assert "qlora_4bit" in report and "bf16" in report and "PASSED / exact" in report
    assert "912" in report  # longest sequence actually seen
    assert "not measured" in report  # e.g. peak memory absent from the fixture
    assert "Not computed" in report  # no extrapolation without real inputs
    assert "BUY / DO NOT BUY" in report  # the verdict is left to the owner


def test_extrapolation_is_plain_arithmetic_on_measured_rates(tmp_path):
    art, runs = _trial(tmp_path)
    report = _module().build(art, runs, round_tokens=7_200_000, hourly_rate=0.85)
    assert "| r1 | qlora_4bit | 1000.0 | 2.0 | 1.7 |" in report  # 7.2M / 1000 tok/s = 2 h
    assert "| r2 | bf16 | 2000.0 | 1.0 | 0.85 |" in report


def test_empty_trial_and_no_overwrite(tmp_path):
    out = tmp_path / "baseline.md"
    cmd = [sys.executable, "scripts/rental/summarise_trial.py", "--artifacts", str(tmp_path / "a")]
    cmd += ["--runs", str(tmp_path / "r"), "--out", str(out)]
    assert subprocess.run(cmd, capture_output=True, text=True).returncode == 0
    assert "not measured" in out.read_text(encoding="utf-8")
    assert subprocess.run(cmd, capture_output=True, text=True).returncode == 2  # refuses overwrite


def test_report_includes_web_failures_usage_and_baseline(tmp_path):
    art, runs = _trial(tmp_path)
    run = art / "run_r1"
    (run / "baseline").mkdir()
    (run / "baseline" / "workload_result.json").write_text(
        json.dumps(
            {
                "task_success": True,
                "model_usage": {"prompt_tokens": 123, "completion_tokens": 12},
                "model_calls": 4,
                "action_attempts": 4,
                "action_count": 4,
                "complete_runtime_s": 11.5,
            }
        )
    )
    (run / "workload_result.json").write_text(
        json.dumps(
            {
                "task_success": False,
                "failure_category": "TIMEOUT",
            }
        )
    )
    report = _module().build(art, runs)
    assert "FAILED: TIMEOUT" in report
    assert "| base | VERIFIED WORKFLOW | 123 | 12 | 4 | 4 | 4 | 11.5 |" in report
