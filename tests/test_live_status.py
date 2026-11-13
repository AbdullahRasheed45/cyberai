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
