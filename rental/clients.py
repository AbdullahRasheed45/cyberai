"""Inference-response parsing + metric helpers for the rental benchmark.

Honesty rules (Astra #1/#2): never invent token counts; an HTTP/structure error
is a FAILED request recorded separately, never throughput; TTFT, generation-phase
decode speed, and end-to-end are distinct quantities.
"""

from __future__ import annotations

import json
import statistics


class InferenceError(Exception):
    pass


def parse_completion(status_code: int, body: str) -> dict:
    """Validate an OpenAI-style chat completion. Raise InferenceError on any
    HTTP/structure problem. Never substitute a requested max for missing usage."""
    if status_code != 200:
        raise InferenceError(f"http {status_code}")
    try:
        obj = json.loads(body)
    except (json.JSONDecodeError, TypeError) as e:
        raise InferenceError(f"malformed json: {e}") from e
    if not isinstance(obj, dict):
        raise InferenceError("response is not an object")
    if "error" in obj:
        raise InferenceError(f"api error: {obj['error']}")
    choices = obj.get("choices")
    if not isinstance(choices, list) or not choices:
        raise InferenceError("no choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str) or content == "":
        raise InferenceError("empty completion")
    usage = obj.get("usage")
    if not isinstance(usage, dict) or not isinstance(usage.get("completion_tokens"), int):
        raise InferenceError("missing/invalid usage.completion_tokens")
    fr = choices[0].get("finish_reason")
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage["completion_tokens"],
        "content": content,
        "finish_reason": fr,
        "truncated": fr == "length",
    }


def timing_from_stream(
    request_t: float, first_token_t: float | None, last_token_t: float | None, n_tokens: int
) -> dict:
    """Distinct metrics from a streamed response. Unknowns are None, not faked."""
    ttft = (first_token_t - request_t) if first_token_t is not None else None
    decode = None
    if (
        first_token_t is not None
        and last_token_t is not None
        and last_token_t > first_token_t
        and n_tokens > 1
    ):
        decode = (n_tokens - 1) / (last_token_t - first_token_t)  # generation phase only
    e2e = (last_token_t - request_t) if last_token_t is not None else None
    return {"ttft_s": ttft, "decode_tok_s": decode, "e2e_s": e2e, "completion_tokens": n_tokens}


def summarise(records: list[dict]) -> dict:
    """Aggregate per-condition. FAILED requests are counted and listed, never
    folded into throughput (Astra #1)."""
    ok = [r for r in records if r.get("ok")]
    failed = [r for r in records if not r.get("ok")]
    out = {
        "n": len(records),
        "n_ok": len(ok),
        "n_failed": len(failed),
        "failures": [r.get("error") for r in failed],
    }
    e2e = [
        r["completion_tokens"] / r["wall_s"]
        for r in ok
        if r.get("wall_s") and r.get("completion_tokens")
    ]
    if e2e:
        out["e2e_tok_s_mean"] = round(statistics.mean(e2e), 2)
    decode = [r["decode_tok_s"] for r in ok if r.get("decode_tok_s")]
    if decode:
        out["decode_tok_s_mean"] = round(statistics.mean(decode), 2)
    ttft = [r["ttft_s"] for r in ok if r.get("ttft_s")]
    if ttft:
        out["ttft_s_mean"] = round(statistics.mean(ttft), 4)
    return out


def parse_stream_events(events: list[tuple[float, str]]) -> dict:
    """Validate a streamed completion independently (Astra #2).

    events: list of (timestamp, raw_sse_line). Rejects API error events, a stream
    with no [DONE], missing/invalid final usage, and no generated content. NEVER
    substitutes stream-chunk count for token count. Reasoning-only deltas (if the
    server exposes a 'reasoning'/'reasoning_content' field) are timed separately
    from visible content so decode rate is not inflated.
    """
    import json as _json

    done = False
    usage = None
    first_content_t = last_content_t = None
    content_chunks = 0
    reasoning_chunks = 0
    for ts, raw in events:
        line = raw.strip()
        if not line.startswith("data:"):
            continue
        data = line[len("data:") :].strip()
        if data == "[DONE]":
            done = True
            break
        try:
            obj = _json.loads(data)
        except (ValueError, TypeError) as e:
            raise InferenceError(f"malformed stream event: {e}") from e
        if isinstance(obj, dict) and obj.get("error"):
            raise InferenceError(f"api error event: {obj['error']}")
        if isinstance(obj, dict) and obj.get("usage"):
            usage = obj["usage"]
        delta = (obj.get("choices") or [{}])[0].get("delta", {}) if isinstance(obj, dict) else {}
        if delta.get("content"):
            content_chunks += 1
            first_content_t = first_content_t if first_content_t is not None else ts
            last_content_t = ts
        if delta.get("reasoning") or delta.get("reasoning_content"):
            reasoning_chunks += 1
    if not done:
        raise InferenceError("incomplete stream (no [DONE])")
    if not isinstance(usage, dict) or not isinstance(usage.get("completion_tokens"), int):
        raise InferenceError("missing/invalid final usage.completion_tokens")
    if content_chunks == 0:
        raise InferenceError("no generated content in stream")
    completion_tokens = usage["completion_tokens"]  # authoritative; not chunk count
    # reasoning-token count may be top-level OR nested under completion_tokens_details
    reasoning_tokens = usage.get("reasoning_tokens")
    if not isinstance(reasoning_tokens, int):
        details = usage.get("completion_tokens_details")
        if isinstance(details, dict):
            reasoning_tokens = details.get("reasoning_tokens")
    # If the model emitted reasoning but we have no reliable reasoning-token count,
    # visible-content decode speed is UNAVAILABLE (do not assign all completion
    # tokens to the visible-content window). Total output throughput is separate.
    reasoning_unquantified = reasoning_chunks > 0 and not isinstance(reasoning_tokens, int)
    if reasoning_unquantified:
        visible = None
        decode = None
    else:
        visible = (
            completion_tokens - reasoning_tokens
            if isinstance(reasoning_tokens, int)
            else completion_tokens
        )
        decode = None
        if (
            first_content_t is not None
            and last_content_t
            and last_content_t > first_content_t
            and visible
            and visible > 1
        ):
            decode = (visible - 1) / (last_content_t - first_content_t)
    return {
        "completion_tokens": completion_tokens,
        "prompt_tokens": usage.get("prompt_tokens"),
        "reasoning_tokens": reasoning_tokens if isinstance(reasoning_tokens, int) else None,
        "visible_content_tokens": visible,
        "content_chunks": content_chunks,
        "reasoning_chunks": reasoning_chunks,
        "decode_tok_s": decode,
        "decode_unavailable_reason": "reasoning tokens present but uncounted"
        if reasoning_unquantified
        else None,
        "first_content_t": first_content_t,
        "last_content_t": last_content_t,
    }
