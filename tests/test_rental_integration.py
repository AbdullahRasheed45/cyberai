"""Round-11: validate the ACTUAL trial workflow, not just helpers.
Streaming client, config-driven freeze, export-from-archive, mocked lifecycle,
and the documented commands in a clean environment (Astra #1-#6)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import threading as _th
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from rental.clients import InferenceError, parse_stream_events
from rental.freeze import validate_freeze
from rental.report import arcname, build_manifest, verify_archive, write_archive

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- #2: streaming must reject errors / missing usage / no content -----------


def _ev(*lines):
    return [(float(i), line) for i, line in enumerate(lines)]


def test_stream_rejects_error_event():
    with pytest.raises(InferenceError):
        parse_stream_events(_ev('data: {"error":{"message":"broken stream"}}', "data: [DONE]"))


def test_stream_rejects_missing_usage():
    with pytest.raises(InferenceError):
        parse_stream_events(_ev('data: {"choices":[{"delta":{"content":"hi"}}]}', "data: [DONE]"))


def test_stream_rejects_incomplete():
    with pytest.raises(InferenceError):
        parse_stream_events(_ev('data: {"choices":[{"delta":{"content":"hi"}}]}'))  # no [DONE]


def test_stream_rejects_no_content():
    with pytest.raises(InferenceError):
        parse_stream_events(_ev('data: {"usage":{"completion_tokens":5}}', "data: [DONE]"))


def test_stream_valid_uses_usage_not_chunks():
    ev = _ev(
        'data: {"choices":[{"delta":{"content":"a"}}]}',
        'data: {"choices":[{"delta":{"content":"b"}}]}',
        'data: {"usage":{"completion_tokens":12}}',
        "data: [DONE]",
    )
    r = parse_stream_events(ev)
    assert r["completion_tokens"] == 12 and r["content_chunks"] == 2  # tokens != chunks


def test_stream_separates_reasoning_tokens():
    ev = _ev(
        'data: {"choices":[{"delta":{"reasoning":"think"}}]}',
        'data: {"choices":[{"delta":{"content":"ans"}}]}',
        'data: {"usage":{"completion_tokens":20,"reasoning_tokens":15}}',
        "data: [DONE]",
    )
    r = parse_stream_events(ev)
    assert r["visible_content_tokens"] == 5 and r["reasoning_tokens"] == 15


# --- #3: freeze rejects placeholder dependency + missing deps ----------------


def test_freeze_rejects_placeholder_dependency():
    errs = validate_freeze({"dependencies": ["transformers==FILL"]})
    assert any("no concrete pinned version" in e for e in errs)


def test_freeze_rejects_missing_dependency_list():
    errs = validate_freeze({"dependencies": ["transformers==5.0.0"]})
    assert any("missing required dependencies" in e for e in errs)


# --- #6: export hashes recomputed from ARCHIVED contents ---------------------


def test_export_archive_roundtrip_and_tamper(tmp_path):
    f = tmp_path / "m.json"
    f.write_text('{"x":1}')
    man = build_manifest([str(f)], [str(tmp_path / "adapter.safetensors")])
    assert man["evidence_complete"] and man["inference_artifacts"]["missing"]
    tar = tmp_path / "bundle.tar.gz"
    extra = {"MANIFEST.json": json.dumps(man).encode()}
    write_archive(str(tar), [str(f)], extra)
    ok, mism = verify_archive(str(tar), {arcname(str(f)): man["evidence"]["present"][str(f)]})
    assert ok, mism
    # tamper detection: wrong expected hash -> mismatch
    ok2, mism2 = verify_archive(str(tar), {arcname(str(f)): "0" * 64})
    assert not ok2 and any("hash mismatch" in m for m in mism2)


# --- #1: the DOCUMENTED command runs in a clean env (no PYTHONPATH) -----------


def test_documented_preflight_runs_clean_env():
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    r = subprocess.run(
        [sys.executable, "scripts/rental/00_preflight.py"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert "ModuleNotFoundError" not in r.stderr, r.stderr
    assert '"preflight"' in r.stdout  # reached the JSON report (fail-closed on no GB10)


# --- #2: the ACTUAL post_stream() exercised against a mock SSE server ---------


def _load_measure():
    spec = importlib.util.spec_from_file_location(
        "measure_mod", os.path.join(ROOT, "scripts", "rental", "20_measure_inference.py")
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _SSE(BaseHTTPRequestHandler):
    mode = "valid"

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        if _SSE.mode == "error":
            lines = ['data: {"error":{"message":"broken stream"}}', "data: [DONE]"]
        else:
            lines = [
                'data: {"choices":[{"delta":{"content":"a"}}]}',
                'data: {"choices":[{"delta":{"content":"b"}}]}',
                'data: {"usage":{"completion_tokens":7}}',
                "data: [DONE]",
            ]
        self.wfile.write(("\n".join(lines) + "\n").encode())

    def log_message(self, *a):
        pass


def _serve():
    srv = HTTPServer(("127.0.0.1", 0), _SSE)
    _th.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/v1/chat/completions"


def test_post_stream_rejects_error_stream():
    m = _load_measure()
    _SSE.mode = "error"
    srv, url = _serve()
    try:
        with pytest.raises(InferenceError):
            m.post_stream(url, "qwen3", "hi", max_tokens=8)
    finally:
        srv.shutdown()
        srv.server_close()


def test_post_stream_valid_uses_usage_tokens():
    m = _load_measure()
    _SSE.mode = "valid"
    srv, url = _serve()
    try:
        r = m.post_stream(url, "qwen3", "hi", max_tokens=8)
        assert r["ok"] and r["completion_tokens"] == 7  # usage, not 2 chunks, not max_tokens
    finally:
        srv.shutdown()
        srv.server_close()


# --- #1 applied to workload + export: documented commands, clean env ---------


@pytest.mark.parametrize("script", ["scripts/rental/40_workload.py", "scripts/rental/50_export.py"])
def test_documented_scripts_no_module_error_clean_env(script):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    r = subprocess.run([sys.executable, script], cwd=ROOT, env=env, capture_output=True, text=True)
    assert "ModuleNotFoundError" not in r.stderr, (
        r.stderr
    )  # package resolves; runtime may fail otherwise
