"""Tests for rental benchmark honesty, freeze validation, export manifest, and a
mocked-server dry run (Astra #1/#2/#5/#8). Pure Python; no GPU."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from rental.clients import InferenceError, parse_completion, summarise, timing_from_stream
from rental.freeze import validate_freeze, validate_lineage
from rental.report import build_manifest

# --- #1: errors never become throughput -------------------------------------


def test_http_error_raises():
    with pytest.raises(InferenceError):
        parse_completion(404, json.dumps({"error": {"message": "model not found", "code": 404}}))


def test_200_with_error_body_raises():
    with pytest.raises(InferenceError):
        parse_completion(200, json.dumps({"error": {"message": "model not found"}}))


def test_malformed_json_raises():
    with pytest.raises(InferenceError):
        parse_completion(200, "{not json")


def test_missing_usage_raises_not_invented():
    body = json.dumps({"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}]})
    with pytest.raises(InferenceError):
        parse_completion(200, body)  # must NOT substitute max_tokens


def test_empty_completion_raises():
    body = json.dumps(
        {"choices": [{"message": {"content": ""}}], "usage": {"completion_tokens": 0}}
    )
    with pytest.raises(InferenceError):
        parse_completion(200, body)


def test_truncated_flagged():
    body = json.dumps(
        {
            "choices": [{"message": {"content": "x"}, "finish_reason": "length"}],
            "usage": {"completion_tokens": 128, "prompt_tokens": 10},
        }
    )
    r = parse_completion(200, body)
    assert r["truncated"] is True and r["completion_tokens"] == 128


def test_summarise_excludes_failures():
    recs = [
        {"ok": True, "wall_s": 1.0, "completion_tokens": 100},
        {"ok": False, "error": "http 404"},
        {"ok": False, "error": "malformed json"},
    ]
    s = summarise(recs)
    assert s["n_ok"] == 1 and s["n_failed"] == 2 and s["e2e_tok_s_mean"] == 100.0
    assert len(s["failures"]) == 2


# --- #2: distinct metrics ----------------------------------------------------


def test_timing_distinguishes_ttft_decode_e2e():
    t = timing_from_stream(request_t=0.0, first_token_t=0.5, last_token_t=2.5, n_tokens=21)
    assert t["ttft_s"] == 0.5
    assert abs(t["decode_tok_s"] - 10.0) < 1e-9  # 20 tokens / 2.0s generation phase
    assert t["e2e_s"] == 2.5


def test_timing_unknowns_are_none_not_faked():
    t = timing_from_stream(0.0, None, None, 0)
    assert t["ttft_s"] is None and t["decode_tok_s"] is None and t["e2e_s"] is None


# --- #5: freeze validation ---------------------------------------------------


def test_freeze_rejects_placeholders():
    cfg = {
        "reference_candidate": "Qwen/Qwen3-30B-A3B",
        "trainable_base_commit": "FILL",
        "dependencies": ["transformers>=5.0.0"],
    }
    errs = validate_freeze(cfg)
    assert any("placeholder" in e for e in errs)
    assert any("unpinned dependency" in e for e in errs)
    assert any("missing/empty" in e for e in errs)


def test_freeze_accepts_fully_pinned():
    sha = "a" * 40
    dig = "repo@sha256:" + "b" * 64
    cfg = {
        "reference_candidate": "Qwen3-30B-A3B",
        "trainable_base_repo": "unsloth/Qwen3-30B-A3B",
        "trainable_base_commit": sha,
        "tokenizer_identity": "unsloth/Qwen3-30B-A3B",
        "serving_base_repo": "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8",
        "serving_base_commit": sha,
        "serving_quantisation": "FP8",
        "serving_quant_provenance": "official Qwen FP8 release",
        "vllm_image": dig,
        "unsloth_image": dig,
        "adapter_targets": ["q_proj", "v_proj"],
        "trainable_serving_relation_attested": True,
        "dependencies": [
            "transformers==5.0.0",
            "unsloth==2025.11.1",
            "peft==0.17.0",
            "trl==0.12.0",
            "bitsandbytes==0.45.0",
        ],
    }
    assert validate_freeze(cfg) == []


def test_lineage_mismatch_detected():
    errs = validate_lineage(
        "unsloth/Qwen3-30B-A3B", "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8", "a" * 40
    )
    assert any("adapter base" in e for e in errs)


# --- #8: export manifest -----------------------------------------------------


def test_export_manifest_hashes_and_lists_missing(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}")
    man = build_manifest([str(p), str(tmp_path / "absent.json")], [str(tmp_path / "adapter")])
    assert str(p) in man["evidence"]["present"]
    assert str(tmp_path / "absent.json") in man["evidence"]["missing"]
    assert man["evidence_complete"] is False
    assert str(tmp_path / "adapter") in man["inference_artifacts"]["missing"]
    assert len(man["evidence"]["present"][str(p)]) == 64  # sha256 hex


# --- mocked-server DRY RUN (Astra's "local dry run with mocked servers") ------


class _Mock(BaseHTTPRequestHandler):
    seq = [
        (404, {"error": {"message": "model not found"}}),
        (
            200,
            {
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"completion_tokens": 50, "prompt_tokens": 7},
            },
        ),
        (200, {"choices": [{"message": {"content": "no usage"}, "finish_reason": "stop"}]}),
    ]
    i = 0

    def do_POST(self):
        code, body = _Mock.seq[_Mock.i % len(_Mock.seq)]
        _Mock.i += 1
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *a):
        pass


def test_dry_run_against_mock_server():
    import urllib.error
    import urllib.request

    _Mock.i = 0
    srv = HTTPServer(("127.0.0.1", 0), _Mock)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/v1/chat/completions"
    records = []
    try:
        for _ in range(3):
            t0 = time.time()
            req = urllib.request.Request(
                url, data=b"{}", headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    status, text = resp.status, resp.read().decode()
            except urllib.error.HTTPError as he:
                status, text = he.code, he.read().decode()
            try:
                r = parse_completion(status, text)
                records.append(
                    {
                        "ok": True,
                        "wall_s": time.time() - t0,
                        "completion_tokens": r["completion_tokens"],
                    }
                )
            except InferenceError as e:
                records.append({"ok": False, "error": str(e)})
    finally:
        srv.shutdown()
        srv.server_close()
    s = summarise(records)
    assert s["n_ok"] == 1 and s["n_failed"] == 2  # 404 + missing-usage excluded
    # the one valid request reported 50 real tokens, never the requested 128
    assert all(r.get("completion_tokens") != 128 for r in records if r.get("ok"))


# --- checkpoint verification rejects the wrong model (Astra #2) ---------------


def test_checkpoint_rejects_small_non_moe(tmp_path):
    import json as _j

    from rental.checkpoint import verify_local_checkpoint

    (tmp_path / "model.safetensors").write_bytes(b"x")
    (tmp_path / "config.json").write_text(
        _j.dumps(
            {"model_type": "qwen3", "architectures": ["Qwen3ForCausalLM"], "num_hidden_layers": 28}
        )
    )
    errs = verify_local_checkpoint(str(tmp_path), "FP8")
    assert any("MoE" in e for e in errs) and any("FP8" in e for e in errs)


def test_checkpoint_accepts_moe_fp8(tmp_path):
    import json as _j

    from rental.checkpoint import verify_local_checkpoint

    (tmp_path / "model.safetensors").write_bytes(b"x")
    (tmp_path / "config.json").write_text(
        _j.dumps(
            {
                "model_type": "qwen3_moe",
                "num_experts": 128,
                "num_hidden_layers": 48,
                "quantization_config": {"quant_method": "fp8"},
            }
        )
    )
    assert verify_local_checkpoint(str(tmp_path), "FP8") == []


def test_checkpoint_rejects_missing_weights(tmp_path):
    import json as _j

    from rental.checkpoint import verify_local_checkpoint

    (tmp_path / "config.json").write_text(
        _j.dumps({"model_type": "qwen3_moe", "num_experts": 128, "num_hidden_layers": 48})
    )
    assert any("weight files" in e for e in verify_local_checkpoint(str(tmp_path), "bf16"))
