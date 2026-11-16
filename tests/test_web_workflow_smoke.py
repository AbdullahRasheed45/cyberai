import importlib.util
import json
from pathlib import Path


def test_web_workload_wires_model_output_to_isolated_schema_check(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / "scripts/rental/40_workload.py"
    spec = importlib.util.spec_from_file_location("web_workload_smoke", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rule = Path("fixtures/web/rules/good.yml").read_text(encoding="utf-8")

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps(
                {
                    "choices": [{"message": {"content": f"<rule>{rule}</rule>"}}],
                    "usage": {"completion_tokens": 100},
                }
            ).encode()

    monkeypatch.setenv("VLLM_URL", "http://unused.test/v1/chat/completions")
    monkeypatch.setenv("WORKLOAD_DOMAIN", "web")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *a, **k: Response())
    module.main()
    evidence = json.loads((tmp_path / "workload_result.json").read_text(encoding="utf-8"))
    assert evidence["domain"] == "web"
    assert evidence["outcome"] == "VERDICT_VERIFIED"
    assert evidence["kind"] == "integration_smoke"
