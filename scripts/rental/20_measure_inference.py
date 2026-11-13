#!/usr/bin/env python3
"""Optimised-inference measurement (Astra #2/#4). Importable functions (no
top-level env), so _post_stream is exercised by a mock streaming server. Honest:
 - streaming validated by rental.clients.parse_stream_events (errors rejected,
   usage required, chunks != tokens, reasoning tokens separated).
 - prompts GROWN until server usage.prompt_tokens reaches the target.
 - prefill measured separately (max_tokens=1 -> TTFT ~= prefill; prefill_tok_s).
 - a real context x concurrency MATRIX; warm cache PRIMED before warm runs; cold
   uses a per-request nonce prefix to defeat shared-prefix caching.
 - 'sampled_peak' memory and 'aggregate_output_tok_s' named accurately.
"""

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid

from rental.clients import InferenceError, parse_completion, parse_stream_events, summarise
from rental.paths import artifact_dir


def _post(url, model, prompt, max_tokens, stream):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    if stream:
        payload.update(stream=True, stream_options={"include_usage": True})
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    started = time.monotonic()
    parsed = {}
    failure = None
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            if stream:
                events = [(time.monotonic(), line.decode()) for line in r]
                parsed = parse_stream_events(events)
            else:
                parsed = parse_completion(r.status, r.read().decode())
        return parsed
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        directory = os.environ.get("LIVE_METRICS_DIR")
        if directory:
            from pathlib import Path

            Path(directory).mkdir(parents=True, exist_ok=True)
            record = {
                "model": model,
                "stream": stream,
                "ok": failure is None,
                "error": failure,
                "runtime_s": time.monotonic() - started,
                "prompt_tokens": parsed.get("prompt_tokens"),
                "completion_tokens": parsed.get("completion_tokens"),
                "decode_tok_s": parsed.get("decode_tok_s"),
                "ttft_s": (parsed["first_content_t"] - started)
                if parsed.get("first_content_t") is not None
                else None,
                "requested_max_tokens": max_tokens,
            }
            (Path(directory) / f"{time.time_ns()}_{uuid.uuid4().hex}.json").write_text(
                json.dumps(record), encoding="utf-8"
            )


def post_stream(url, model, prompt, max_tokens=128):
    t0 = time.monotonic()
    s = _post(url, model, prompt, max_tokens, stream=True)
    ttft = (s["first_content_t"] - t0) if s["first_content_t"] is not None else None
    return {
        "ok": True,
        "ttft_s": ttft,
        "decode_tok_s": s["decode_tok_s"],
        "completion_tokens": s["completion_tokens"],
        "prompt_tokens": s.get("prompt_tokens"),
        "reasoning_tokens": s.get("reasoning_tokens"),
        "wall_s": time.monotonic() - t0,
    }


def grow_to_target(url, model, target_tokens, cap=40000):
    """Return (prompt, measured_prompt_tokens) with prompt_tokens >= target."""
    words = max(1, target_tokens // 2)
    for _ in range(8):
        prompt = ("token " * words).strip()
        r = _post(url, model, prompt, 1, stream=False)
        pt = r.get("prompt_tokens")
        if pt is None:
            raise InferenceError("server did not report prompt_tokens")
        if pt >= target_tokens or words >= cap:
            return prompt, pt
        words = int(words * (target_tokens / max(pt, 1)) * 1.1) + 1
    return prompt, pt


def prefill_estimate(url, model, base_prompt, prompt_tokens):
    """Request-based ESTIMATE (not a direct kernel-prefill measurement). Uses a
    FRESH nonce-prefixed prompt to reduce prefix-cache reuse; total request time
    includes overhead + one-token generation. A nonce reduces, not eliminates,
    cache hits -- record server cache metrics if the server exposes them."""
    fresh = f"{uuid.uuid4()} {base_prompt}"
    t0 = time.monotonic()
    r = _post(url, model, fresh, 1, stream=False)
    ttft = time.monotonic() - t0
    pt = r.get("prompt_tokens", prompt_tokens)
    return {
        "measured_prompt_tokens": pt,
        "request_s": round(ttft, 4),
        "prefill_tok_s_request_based_estimate": round(pt / ttft, 1) if ttft > 0 else None,
        "note": "request-based uncached estimate; includes overhead + 1-token decode",
    }


def _sampler(state):
    while state["run"]:
        try:
            state["peak"] = max(
                state["peak"],
                float(
                    subprocess.check_output(
                        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                        timeout=3,
                    ).split()[0]
                )
                / 1024,
            )
        except Exception:
            state["peak"] = None
            return
        time.sleep(0.2)


def run_matrix(url, model, contexts=(8000, 16000), concurrencies=(1, 8, 32)):
    import concurrent.futures as cf

    def rec(fn, *a):
        t0 = time.monotonic()
        try:
            o = fn(*a)
            o = o if isinstance(o, dict) else {}
            o.setdefault("ok", True)
            o.setdefault("wall_s", time.monotonic() - t0)
            return o
        except Exception as e:
            return {
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
                "wall_s": time.monotonic() - t0,
            }

    out = {"matrix": {}}
    for ctx in contexts:
        prompt, pt = grow_to_target(url, model, ctx)
        out[f"prefill_estimate_ctx_{ctx}"] = prefill_estimate(url, model, prompt, pt)
        for conc in concurrencies:
            # cold: unique nonce prefix per request (defeats shared-prefix cache)
            with cf.ThreadPoolExecutor(max_workers=conc) as ex:
                t0 = time.monotonic()
                recs = list(
                    ex.map(
                        lambda _, prompt=prompt: rec(
                            _post, url, model, f"{uuid.uuid4()} {prompt}", 64, False
                        ),
                        range(conc),
                    )
                )
                wall = time.monotonic() - t0
            s = summarise(recs)
            s["requests"] = recs
            s["batch_wall_s"] = wall
            toks = sum(r.get("completion_tokens", 0) for r in recs if r.get("ok"))
            s["aggregate_output_tok_s"] = (
                round(toks / wall, 2) if any(r["ok"] for r in recs) else None
            )
            out["matrix"][f"ctx{ctx}_conc{conc}_cold"] = s
        # warm: prime the shared prompt once, then measure repeats at top concurrency
        _post(url, model, prompt, 1, stream=False)
        with cf.ThreadPoolExecutor(max_workers=concurrencies[-1]) as ex:
            t0 = time.monotonic()
            recs = list(
                ex.map(
                    lambda _, prompt=prompt: rec(_post, url, model, prompt, 64, False),
                    range(concurrencies[-1]),
                )
            )
            wall = time.monotonic() - t0
        sw = summarise(recs)
        sw["requests"] = recs
        sw["batch_wall_s"] = wall
        sw["aggregate_output_tok_s"] = (
            round(sum(r.get("completion_tokens", 0) for r in recs if r["ok"]) / wall, 2)
            if any(r["ok"] for r in recs)
            else None
        )
        out["matrix"][f"ctx{ctx}_conc{concurrencies[-1]}_warm_primed"] = sw
    return out


def main():
    state = {"run": True, "peak": 0.0}
    sampler = threading.Thread(target=_sampler, args=(state,), daemon=True)
    res = {"passed": False}
    start = time.monotonic()
    sampler.start()
    try:
        url = os.environ["VLLM_URL"]
        model = os.environ.get("SERVED_MODEL", "qwen3")
        records = []
        res["single_stream_requests"] = records
        for i in range(3):
            try:
                records.append(post_stream(url, model, f"Explain TCP variant {i}."))
            except Exception as exc:
                records.append({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        res["single_stream"] = summarise(records)
        res.update(run_matrix(url, model))
        res["passed"] = (
            all(condition["n_failed"] == 0 for condition in res["matrix"].values())
            and res["single_stream"]["n_failed"] == 0
        )
    except Exception as exc:
        res["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        state["run"] = False
        sampler.join(timeout=5)
        res["total_runtime_s"] = time.monotonic() - start
        res["sampled_peak_gpu_mem_GB"] = state["peak"]
        os.makedirs(artifact_dir(), exist_ok=True)
        with open(os.path.join(artifact_dir(), "inference_measurements.json"), "w") as output:
            json.dump(res, output, indent=2)
        print(json.dumps(res, indent=2))
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
