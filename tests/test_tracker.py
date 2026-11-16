import importlib.util
import json
import subprocess
import sys


def test_command_tracker_preserves_failure_and_output(tmp_path):
    output = tmp_path / "command.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/rental/track_command.py",
            "--out",
            str(output),
            "--",
            sys.executable,
            "-c",
            "print('reference-output'); raise SystemExit(3)",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 3
    record = json.loads(output.read_text())
    assert record["exit_code"] == 3
    assert record["elapsed_s"] > 0
    assert "reference-output" in output.with_suffix(".log").read_text()
    assert record["samples"]


def test_command_tracker_timeout_is_not_a_success(tmp_path):
    output = tmp_path / "command.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/rental/track_command.py",
            "--out",
            str(output),
            "--timeout",
            "0.5",
            "--",
            sys.executable,
            "-c",
            "import time; time.sleep(20)",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode != 0
    assert json.loads(output.read_text())["timed_out"]


def test_stream_request_preserves_prompt_usage(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "measure", "scripts/rental/20_measure_inference.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module,
        "_post",
        lambda *a, **k: {
            "first_content_t": None,
            "decode_tok_s": None,
            "completion_tokens": 4,
            "prompt_tokens": 123,
            "reasoning_tokens": None,
        },
    )
    assert module.post_stream("url", "model", "prompt")["prompt_tokens"] == 123


def test_completed_request_is_published_with_actual_usage(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "live_measure", "scripts/rental/20_measure_inference.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps(
                {
                    "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 2},
                }
            ).encode()

    monkeypatch.setenv("LIVE_METRICS_DIR", str(tmp_path))
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **k: Response())
    module._post("http://unused.local", "test", "prompt", 100, False)
    value = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert value["completion_tokens"] == 2
    assert value["prompt_tokens"] == 12
    assert value["requested_max_tokens"] == 100
    assert value["ok"] is True
