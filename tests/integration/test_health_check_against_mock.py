"""Integration test for scripts/gb10/health_check.py against a fake vLLM
server (http.server, not vLLM) — proves the three-tier check logic and its
EvidenceRecord output work, without needing GPU/GB10 hardware. This is
EvidenceKind.MOCKED by construction: nothing here claims to confirm real
vLLM/GB10 behaviour, only that this repo's health-check script correctly
reports liveness/readiness/inference against *something* on the wire.
"""

from __future__ import annotations

import http.server
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HEALTH_CHECK = REPO_ROOT / "scripts" / "gb10" / "health_check.py"


class _FakeVllmHandler(http.server.BaseHTTPRequestHandler):
    healthy = True
    model_id = "qwen3"
    reply_text = "OK"

    def _send_json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802 - stdlib-mandated name
        if self.path == "/health":
            self._send_json(200 if self.healthy else 500, {})
        elif self.path == "/v1/models":
            self._send_json(200, {"data": [{"id": self.model_id}]})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path == "/v1/chat/completions":
            self._send_json(
                200,
                {"choices": [{"message": {"content": self.reply_text}}]},
            )
        else:
            self._send_json(404, {"error": "not found"})

    def log_message(self, fmt, *args):  # silence default stderr logging
        pass


@pytest.fixture
def fake_server():
    _FakeVllmHandler.healthy = True
    _FakeVllmHandler.model_id = "qwen3"
    _FakeVllmHandler.reply_text = "OK"
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _FakeVllmHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _run_health_check(port: int, model_name: str = "qwen3") -> tuple[int, dict]:
    result = subprocess.run(
        [
            sys.executable,
            str(HEALTH_CHECK),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--served-model-name",
            model_name,
            "--evidence",
            "mocked",
            "--host-env",
            "ci",
            "--timeout",
            "5",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    # health_check.py prints exactly one JSON document (the EvidenceRecord)
    # to stdout; any failure messages go to stderr.
    record = json.loads(result.stdout)
    return result.returncode, record


def test_all_tiers_pass_against_a_healthy_mock(fake_server):
    port = fake_server.server_address[1]
    returncode, record = _run_health_check(port)
    assert returncode == 0
    assert record["passed"] is True
    assert record["evidence"] == "mocked"
    assert record["host"] == "ci"
    assert record["result"]["liveness"]["status_code"] == 200
    assert record["result"]["readiness"]["ready"] is True
    assert record["result"]["inference"]["response_text"] == "OK"


def test_liveness_failure_is_reported_and_skips_inference(fake_server):
    _FakeVllmHandler.healthy = False
    port = fake_server.server_address[1]
    returncode, record = _run_health_check(port)
    assert returncode == 1
    assert record["passed"] is False
    assert record["result"]["liveness"]["status_code"] == 500
    assert record["result"]["inference"] == {"skipped": "liveness/readiness failed"}


def test_readiness_failure_when_expected_model_not_loaded(fake_server):
    _FakeVllmHandler.model_id = "some-other-model"
    port = fake_server.server_address[1]
    returncode, record = _run_health_check(port, model_name="qwen3")
    assert returncode == 1
    assert record["passed"] is False
    assert record["result"]["readiness"]["ready"] is False
    assert record["result"]["readiness"]["models"] == ["some-other-model"]
