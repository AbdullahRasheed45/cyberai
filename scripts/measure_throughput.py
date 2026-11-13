#!/usr/bin/env python3
"""Reproducible serving-throughput measurement against a running vLLM
endpoint. Supersedes the inline heredoc version in
docs/STAGE_0_AND_1_EXACT.md B3 with a configurable, typed one — the
runbook's own numbers (stage1_serving_numbers.json) are a valid simpler
alternative if you prefer to follow it literally; this script produces the
same shape of number as a `libs.schemas.EvidenceRecord` instead of a bare
dict, and reads its target from CLI flags / env rather than a hardcoded URL.

Usage:
    uv run python scripts/measure_throughput.py \
        --host 127.0.0.1 --port 8000 --served-model-name qwen3 \
        --host-env gb10_cloud --evidence hardware

NEVER run this against a model you have not confirmed is the one you think
it is — pair it with scripts/gb10/health_check.py's readiness check first.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libs.schemas import EvidenceKind, EvidenceRecord, HostEnvironment  # noqa: E402


def _one_completion(
    client: httpx.Client, url: str, model: str, prompt: str, max_tokens: int
) -> dict:
    t0 = time.monotonic()
    r = client.post(
        url,
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        },
        timeout=client.timeout,
    )
    dt = time.monotonic() - t0
    r.raise_for_status()
    out = r.json()
    n_tokens = out.get("usage", {}).get("completion_tokens")
    if type(n_tokens) is not int or n_tokens < 0:
        raise ValueError("missing or invalid completion_tokens; cannot measure throughput")
    return {"completion_tokens": n_tokens, "wall_s": dt}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--served-model-name", default="qwen3")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument(
        "--host-env",
        choices=[e.value for e in HostEnvironment],
        required=True,
        help="no default on purpose — never let a throughput number go unlabelled",
    )
    parser.add_argument("--evidence", choices=[e.value for e in EvidenceKind], required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument("--warmup-requests", type=int, default=1)
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/v1/chat/completions"
    model = args.served_model_name

    if args.batch_size <= 0 or args.max_tokens <= 0 or args.warmup_requests < 0:
        parser.error("batch-size/max-tokens must be positive; warmup-requests nonnegative")
    prompt = args.prompt_file.read_text(encoding="utf-8") if args.prompt_file else "Explain DNS."
    failures = []

    def attempt(client):
        try:
            return _one_completion(client, url, model, prompt, args.max_tokens)
        except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
            failures.append(str(exc))
            return None

    started = time.monotonic()
    with httpx.Client(timeout=args.timeout, trust_env=False) as client:
        warm_start = time.monotonic()
        warmup = [attempt(client) for _ in range(args.warmup_requests)]
        warmup_wall = time.monotonic() - warm_start
        single = attempt(client)
        batch_start = time.monotonic()
        with cf.ThreadPoolExecutor(max_workers=args.batch_size) as ex:
            batch = list(ex.map(lambda _: attempt(client), range(args.batch_size)))
        batch_wall = time.monotonic() - batch_start
    actual_tokens = sum(item["completion_tokens"] for item in batch if item is not None)
    result = {
        "single_request": single,
        "single_stream_tok_s": single["completion_tokens"] / single["wall_s"] if single else None,
        "batch_tok_s": actual_tokens / batch_wall,
        "batch_completion_tokens": actual_tokens,
        "batch_wall_s": batch_wall,
        "batch_requests": batch,
        "warmup_requests": warmup,
        "warmup_wall_s": warmup_wall,
        "total_runtime_s": time.monotonic() - started,
        "failures": failures,
        "memory": {
            "status": "not_collected",
            "reason": "external server; capture device metrics separately",
        },
        "loading": {"status": "not_measured", "reason": "server must already be running"},
        "timing_scope": "non-streaming end-to-end; TTFT/decode not measured",
        "settings": vars(args)
        | {"prompt_file": str(args.prompt_file) if args.prompt_file else None},
    }
    record = EvidenceRecord(
        label="vllm_throughput",
        host=HostEnvironment(args.host_env),
        evidence=EvidenceKind(args.evidence),
        command=" ".join(sys.argv),
        passed=not failures,
        result=result,
        measured_at=datetime.now(UTC),
    )

    out_json = record.model_dump_json(indent=2)
    print(out_json)
    if args.out:
        Path(args.out).write_text(out_json, encoding="utf-8")
    return 0 if record.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
