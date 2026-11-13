"""Integration tests for scripts/bench/run_benchmark.py against a fake
streaming vLLM server (http.server, not vLLM). These are harness tests —
they prove the benchmark harness's own accounting, bounding, and failure
handling, NOT any real serving performance. Every report produced here has
`harness_test=True, evidence=EvidenceKind.MOCKED`.
"""

from __future__ import annotations

import http.server
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_BENCHMARK = REPO_ROOT / "scripts" / "bench" / "run_benchmark.py"
HARNESS_TEST_CONFIG = REPO_ROOT / "configs" / "benchmark.harness-test.yaml"


class _FakeStreamingVllmHandler(http.server.BaseHTTPRequestHandler):
    n_chunks = 4
    delay_per_chunk_s = 0.01
    fail_status: int | None = None
    hang_s: float | None = None

    def _send_json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)  # drain the request body

        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": "not found"})
            return
        if _FakeStreamingVllmHandler.hang_s is not None:
            time.sleep(_FakeStreamingVllmHandler.hang_s)
        if _FakeStreamingVllmHandler.fail_status is not None:
            self._send_json(_FakeStreamingVllmHandler.fail_status, {"error": "boom"})
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for i in range(_FakeStreamingVllmHandler.n_chunks):
            chunk = {"choices": [{"delta": {"content": f"tok{i} "}}]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.flush()
            time.sleep(_FakeStreamingVllmHandler.delay_per_chunk_s)
        final = {
            "choices": [],
            "usage": {"prompt_tokens": 32, "completion_tokens": _FakeStreamingVllmHandler.n_chunks},
        }
        self.wfile.write(f"data: {json.dumps(final)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, fmt, *args):  # silence default stderr logging
        pass


@pytest.fixture
def fake_server():
    _FakeStreamingVllmHandler.n_chunks = 4
    _FakeStreamingVllmHandler.delay_per_chunk_s = 0.01
    _FakeStreamingVllmHandler.fail_status = None
    _FakeStreamingVllmHandler.hang_s = None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _FakeStreamingVllmHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _run_harness(
    port: int, tmp_path: Path, extra_args: list[str] | None = None
) -> tuple[int, dict, str, str]:
    out_json = tmp_path / "report.json"
    out_report = tmp_path / "report.md"
    args = [
        sys.executable,
        str(RUN_BENCHMARK),
        "--benchmark-config",
        str(HARNESS_TEST_CONFIG),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--served-model-name",
        "qwen3",
        "--host-env",
        "ci",
        "--evidence",
        "mocked",
        "--harness-test",
        "--out-json",
        str(out_json),
        "--out-report",
        str(out_report),
    ]
    result = subprocess.run(args + (extra_args or []), capture_output=True, text=True, timeout=60)
    report = json.loads(out_json.read_text(encoding="utf-8")) if out_json.exists() else {}
    report_md = out_report.read_text(encoding="utf-8") if out_report.exists() else ""
    return result.returncode, report, report_md, result.stderr


def test_successful_sweep_produces_a_clearly_labelled_harness_report(fake_server, tmp_path):
    port = fake_server.server_address[1]
    returncode, report, report_md, stderr = _run_harness(port, tmp_path)
    assert returncode == 0, stderr
    assert report["harness_test"] is True
    assert report["evidence"] == "mocked"
    assert report["host"] == "ci"
    assert len(report["points"]) > 0
    sweep_points = [p for p in report["points"] if p["spec"]["kind"] == "sweep"]
    assert all(p["error_rate"] == 0.0 for p in sweep_points)
    assert "HARNESS TEST" in report_md
    assert "not a GPU performance result" in report_md
    # evidence != hardware -> no recommendation is ever computed.
    assert report["recommended_operating_configuration"] is None
    assert "no authorised hardware endpoint" in report["recommendation_pending_reason"]


def test_prefix_cache_probe_runs_and_is_reported(fake_server, tmp_path):
    port = fake_server.server_address[1]
    _, report, report_md, stderr = _run_harness(port, tmp_path)
    probe_points = [p for p in report["points"] if p["spec"]["kind"] == "prefix_cache_probe"]
    assert len(probe_points) == 1
    assert probe_points[0]["n_requests"] >= 2  # cold + at least one repeat
    assert "Prefix-cache" in report_md


def test_server_errors_are_captured_not_crashed_on(fake_server, tmp_path):
    _FakeStreamingVllmHandler.fail_status = 500
    port = fake_server.server_address[1]
    returncode, report, _, stderr = _run_harness(port, tmp_path)
    assert returncode == 0  # harness-test runs don't fail CI by exit code
    sweep_points = [p for p in report["points"] if p["spec"]["kind"] == "sweep"]
    assert sweep_points
    assert all(p["error_rate"] == 1.0 for p in sweep_points)
    assert all(p["n_errors"] == p["n_requests"] for p in sweep_points)


def test_slow_server_produces_timeouts_within_the_configured_timeout(fake_server, tmp_path):
    # harness-test config sets request_timeout_s: 3; hang well past that.
    _FakeStreamingVllmHandler.hang_s = 4.0
    port = fake_server.server_address[1]
    _, report, _, stderr = _run_harness(port, tmp_path)
    sweep_points = [p for p in report["points"] if p["spec"]["kind"] == "sweep"]
    assert sweep_points
    assert all(p["n_timeouts"] > 0 for p in sweep_points)


def test_max_requests_total_bound_is_never_exceeded(fake_server, tmp_path):
    port = fake_server.server_address[1]
    # A bound tighter than the full plan would need forces truncation.
    _, report, _, stderr = _run_harness(
        port, tmp_path, extra_args=["--benchmark-config", str(HARNESS_TEST_CONFIG)]
    )
    total_requests = sum(p["n_requests"] for p in report["points"])
    cfg_bound = report["benchmark_config_snapshot"]["max_requests_total"]
    assert total_requests <= cfg_bound


def test_harness_test_flag_refused_with_hardware_evidence(tmp_path):
    args = [
        sys.executable,
        str(RUN_BENCHMARK),
        "--benchmark-config",
        str(HARNESS_TEST_CONFIG),
        "--host",
        "127.0.0.1",
        "--port",
        "1",
        "--host-env",
        "gb10_cloud",
        "--evidence",
        "hardware",
        "--harness-test",
    ]
    result = subprocess.run(args, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert "REFUSED" in result.stderr
