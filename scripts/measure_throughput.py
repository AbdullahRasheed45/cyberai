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

from libs.schemas import EvidenceKind, EvidenceRecord, HostEnvironment, ServingThroughputResult  # noqa: E402


def _one_completion(
    client: httpx.Client, url: str, model: str, prompt: str, max_tokens: int
) -> float:
    t0 = time.monotonic()
    r = client.post(
        url,
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    dt = time.monotonic() - t0
    r.raise_for_status()
    out = r.json()
    n_tokens = out.get("usage", {}).get("completion_tokens", max_tokens)
    return n_tokens / dt if dt > 0 else 0.0


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
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/v1/chat/completions"
    model = args.served_model_name

    with httpx.Client() as client:
        try:
            single = _one_completion(client, url, model, "Explain TCP in 100 words.", 128)
        except httpx.HTTPError as exc:
            print(f"single-stream measurement failed: {exc}", file=sys.stderr)
            return 1

        t0 = time.monotonic()
        try:
            with cf.ThreadPoolExecutor(max_workers=args.batch_size) as ex:
                list(
                    ex.map(
                        lambda _: _one_completion(
                            client, url, model, "Explain DNS.", args.max_tokens
                        ),
                        range(args.batch_size),
                    )
                )
        except httpx.HTTPError as exc:
            print(f"batch measurement failed: {exc}", file=sys.stderr)
            return 1
        batch_wall_s = time.monotonic() - t0
        batch_tok_s = (
            (args.batch_size * args.max_tokens) / batch_wall_s if batch_wall_s > 0 else 0.0
        )

    result = ServingThroughputResult(
        single_stream_tok_s=round(single, 1),
        batch_tok_s=round(batch_tok_s, 1),
        batch_size=args.batch_size,
    )
    record = EvidenceRecord(
        label="vllm_throughput",
        host=HostEnvironment(args.host_env),
        evidence=EvidenceKind(args.evidence),
        command=(
            f"measure_throughput.py --host {args.host} --port {args.port} "
            f"--batch-size {args.batch_size}"
        ),
        passed=True,
        result=result.model_dump(),
        measured_at=datetime.now(UTC),
    )

    out_json = record.model_dump_json(indent=2)
    print(out_json)
    if args.out:
        Path(args.out).write_text(out_json, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
