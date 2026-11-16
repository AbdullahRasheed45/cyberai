import importlib.util
import json
from pathlib import Path


def measure_module():
    path = Path(__file__).parents[1] / "scripts/rental/20_measure_inference.py"
    spec = importlib.util.spec_from_file_location("clock_measure", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stream_wall_time_uses_monotonic_clock(monkeypatch):
    module = measure_module()
    values = iter([100.0, 102.0])
    monkeypatch.setattr(module.time, "monotonic", lambda: next(values))
    monkeypatch.setattr(module.time, "time", lambda: 1_700_000_000.0)
    monkeypatch.setattr(
        module,
        "_post",
        lambda *a, **k: {
            "first_content_t": 100.25,
            "decode_tok_s": 4.0,
            "completion_tokens": 8,
        },
    )
    result = module.post_stream("url", "model", "prompt")
    assert result["wall_s"] == 2.0
    assert result["ttft_s"] == 0.25


def test_matrix_retains_actual_error_details(monkeypatch):
    module = measure_module()

    def epoch_clock_forbidden():
        raise AssertionError("elapsed measurements must use monotonic")

    monkeypatch.setattr(module.time, "time", epoch_clock_forbidden)
    monkeypatch.setattr(module, "grow_to_target", lambda *a: ("prompt", 10))
    monkeypatch.setattr(module, "prefill_estimate", lambda *a: {})

    def post(*args, **kwargs):
        if args[3] == 1:
            return {"completion_tokens": 1}
        raise RuntimeError("backend failed")

    monkeypatch.setattr(module, "_post", post)
    result = module.run_matrix("url", "model", contexts=(10,), concurrencies=(1,))
    assert result["matrix"]["ctx10_conc1_cold"]["failures"] == ["RuntimeError: backend failed"]
    assert result["matrix"]["ctx10_conc1_warm_primed"]["aggregate_output_tok_s"] is None


def test_main_writes_failure_artifact_and_stops_sampler(monkeypatch, tmp_path):
    module = measure_module()
    monkeypatch.setenv("VLLM_URL", "http://unused")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    captured = {}

    class Thread:
        def __init__(self, target, args, **kw):
            captured["state"] = args[0]

        def start(self):
            pass

        def join(self, timeout):
            pass

    monkeypatch.setattr(module.threading, "Thread", Thread)
    monkeypatch.setattr(module, "post_stream", lambda *a, **k: {"ok": True})

    def crash(*a):
        raise RuntimeError("matrix exploded")

    monkeypatch.setattr(module, "run_matrix", crash)
    assert module.main() == 1
    artifact = json.loads((tmp_path / "inference_measurements.json").read_text(encoding="utf-8"))
    assert artifact["passed"] is False
    assert "matrix exploded" in artifact["error"]
    assert captured["state"]["run"] is False


def test_matrix_failures_are_data_not_a_lifecycle_abort(monkeypatch, tmp_path):
    module = measure_module()
    monkeypatch.setenv("VLLM_URL", "http://unused")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("MEASURE_CONTEXTS", "100")
    monkeypatch.setenv("MEASURE_CONCURRENCIES", "2")
    monkeypatch.setattr(module, "_sampler", lambda state: None)
    monkeypatch.setattr(module, "post_stream", lambda *a, **k: {"ok": True})
    seen = {}

    def matrix(url, model, contexts, concurrencies):
        seen["grid"] = (contexts, concurrencies)
        return {"matrix": {"c": {"n_failed": 1}}, "context_errors": {}}

    monkeypatch.setattr(module, "run_matrix", matrix)
    assert module.main() == 0  # server works; a slow/failed cell must not stop training
    artifact = json.loads((tmp_path / "inference_measurements.json").read_text(encoding="utf-8"))
    assert artifact["passed"] is False and artifact["server_functional"] is True
    assert seen["grid"] == ((100,), (2,))
    assert artifact["settings"]["contexts"] == [100]


def test_unusable_server_still_stops_lifecycle(monkeypatch, tmp_path):
    module = measure_module()
    monkeypatch.setenv("VLLM_URL", "http://unused")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setattr(module, "_sampler", lambda state: None)

    def down(*a, **k):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(module, "post_stream", down)
    monkeypatch.setattr(module, "run_matrix", lambda *a, **k: {"matrix": {}, "context_errors": {}})
    assert module.main() == 1


def test_one_failing_context_does_not_erase_the_others(monkeypatch):
    module = measure_module()

    def grow(url, model, ctx):
        if ctx == 20:
            raise RuntimeError("context too long")
        return "prompt", ctx

    monkeypatch.setattr(module, "grow_to_target", grow)
    monkeypatch.setattr(module, "prefill_estimate", lambda *a: {})
    monkeypatch.setattr(module, "_post", lambda *a, **k: {"completion_tokens": 1})
    out = module.run_matrix("u", "m", contexts=(10, 20), concurrencies=(1,))
    assert "ctx10_conc1_cold" in out["matrix"]
    assert "context too long" in out["context_errors"]["20"]
