import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

from rental.live_status import server, snapshot


def test_tracker_publishes_running_state_before_process_finishes(tmp_path):
    output = tmp_path / "tracked.json"
    process = subprocess.Popen(
        [
            sys.executable,
            "scripts/rental/track_command.py",
            "--out",
            str(output),
            "--",
            sys.executable,
            "-c",
            "import time; time.sleep(2)",
        ]
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if output.exists():
                try:
                    value = json.loads(output.read_text())
                    if value["state"] == "RUNNING":
                        assert process.poll() is None
                        break
                except (ValueError, PermissionError):
                    pass
            time.sleep(0.05)
        else:
            pytest.fail("no live RUNNING state published")
        process.wait(timeout=10)
        assert json.loads(output.read_text())["state"] == "COMPLETED"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_live_api_is_read_only_and_returns_real_progress(tmp_path):
    root, runs = tmp_path / "artifacts", tmp_path / "runs"
    root.mkdir()
    step = runs / "run1"
    step.mkdir(parents=True)
    (step / "step_measurements.jsonl").write_text(
        '{"completed_step":1,"seconds":2,"nonpadding_tokens":100}\n'
    )
    (step / "training_logs.jsonl").write_text('{"step":1,"metrics":{"loss":0.75}}\n')
    http = server(root, runs, 0)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        base = f"http://127.0.0.1:{http.server_port}"
        with opener.open(base + "/api/state", timeout=5) as response:
            value = json.load(response)
        assert value["training"][0]["recent_steps"][0]["nonpadding_tokens"] == 100
        assert value["training"][0]["recent_training_logs"][0]["metrics"]["loss"] == 0.75
        with opener.open(base, timeout=5) as response:
            assert b"DGX Spark live tracker" in response.read()
        with pytest.raises(urllib.error.HTTPError) as exc:
            opener.open(base + "/../secret", timeout=5)
        assert exc.value.code == 404
        exc.value.close()
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=5)


def test_dashboard_does_not_invent_missing_gpu_values(tmp_path):
    (tmp_path / "tracked.json").write_text(
        json.dumps(
            {
                "state": "RUNNING",
                "sample_count": 1,
                "samples": [{"gpu_error": "unavailable", "host_memory_kib": None}],
            }
        )
    )
    value = snapshot(tmp_path, tmp_path / "runs")
    assert "GPU_TELEMETRY_UNAVAILABLE" in value["trackers"][0]["signals"]


def test_dashboard_shows_lifecycle_phase_and_serving_console(tmp_path):
    root, runs = tmp_path / "artifacts", tmp_path / "runs"
    run = root / "run_r1"
    run.mkdir(parents=True)
    runs.mkdir()
    (run / "phase.json").write_text(
        json.dumps({"run_id": "r1", "phase": "wait_base", "phases": ["preflight", "wait_base"]})
    )
    log_bytes = b"x" * 9000 + b"\nCUDA graph capture done\n"  # bytes: no CRLF translation
    (run / "cyberai_serve_base.console.log").write_bytes(log_bytes)
    state = snapshot(root, runs)
    assert state["lifecycle"][0]["phase"] == "wait_base"
    assert state["lifecycle"][0]["artifact_dir"] == "run_r1"
    log = state["service_logs"][0]
    assert log["file"] == "run_r1/cyberai_serve_base.console.log"
    assert log["tail"].endswith("CUDA graph capture done\n") and len(log["tail"]) == 8192


def test_dashboard_tolerates_null_measurements():
    from rental.live_status import PAGE

    # every numeric render goes through a null-safe formatter; a raw .toFixed on a
    # possibly-null field would break the whole refresh loop mid-trial
    assert "s.runtime_s.toFixed" not in PAGE and "s.seconds.toFixed" not in PAGE
    assert "const fx=" in PAGE


def test_check_preparation_detection_scope_needs_no_ssh(tmp_path, monkeypatch):
    import os

    model, export = tmp_path / "m", tmp_path / "e"
    model.mkdir()
    export.mkdir()
    env = {
        **os.environ,
        "WORKLOAD_DOMAIN": "detection",
        "MODEL_PATH": str(model),
        "EVIDENCE_EXPORT_DIR": str(export),
        "RENTAL_STOP_UTC": "2999-01-01T00:00:00Z",
        "PATH": "",  # neither docker nor ssh resolvable
    }
    result = subprocess.run(
        [sys.executable, "scripts/rental/check_preparation.py"],
        capture_output=True,
        text=True,
        env=env,
    )
    blockers = json.loads(result.stdout)["blockers"]
    assert "docker unavailable on this host" in blockers
    assert not any("ssh" in b for b in blockers)
    assert not any("LAB_SSH_HOST" in b for b in blockers)
