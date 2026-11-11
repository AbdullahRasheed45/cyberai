#!/usr/bin/env python3
"""Three-tier health check against a running vLLM OpenAI-compatible server,
plus a real inference smoke test. Produces a `libs.schemas.EvidenceRecord`.

Tiers (the vLLM `/health` endpoint is a LIVENESS check only — it returns 200
once the process is up, before the model has finished loading; it is not a
readiness check on its own):
    1. liveness   GET  /health         — process is up
    2. readiness  GET  /v1/models      — the expected served_model_name is loaded
    3. inference  POST /v1/chat/completions — an actual completion comes back

Usage:
    uv run python scripts/gb10/health_check.py \
        --served-model-name qwen3 --host 127.0.0.1 --port 8000

Marks the produced EvidenceRecord as HostEnvironment.GB10_CLOUD /
EvidenceKind.HARDWARE only if `--host-env` says so explicitly — never
infers "this is real hardware" from the mere fact that a server answered
(it could just as well be a local mock listening on the same port).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libs.schemas import EvidenceKind, EvidenceRecord, HostEnvironment  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--served-model-name", default="qwen3")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--host-env",
        choices=[e.value for e in HostEnvironment],
        default=HostEnvironment.WINDOWS_DEV.value,
        help="which host actually ran this check — only HARDWARE counts as confirming a BLOCKER",
    )
    parser.add_argument(
        "--evidence",
        choices=[e.value for e in EvidenceKind],
        default=EvidenceKind.LOCAL.value,
    )
    parser.add_argument("--out", default=None, help="write the EvidenceRecord JSON here too")
    args = parser.parse_args()

    base = f"http://{args.host}:{args.port}"
    checks: dict[str, object] = {}
    passed = True

    with httpx.Client(timeout=args.timeout) as client:
        # 1. liveness
        try:
            r = client.get(f"{base}/health")
            checks["liveness"] = {"status_code": r.status_code}
            if r.status_code != 200:
                passed = False
        except httpx.HTTPError as exc:
            checks["liveness"] = {"error": str(exc)}
            passed = False
            print(f"LIVENESS FAILED: cannot reach {base}/health: {exc}", file=sys.stderr)

        # 2. readiness: the expected model is actually loaded
        try:
            r = client.get(f"{base}/v1/models")
            model_ids = [m.get("id") for m in r.json().get("data", [])]
            ready = args.served_model_name in model_ids
            checks["readiness"] = {
                "status_code": r.status_code,
                "models": model_ids,
                "ready": ready,
            }
            if not ready:
                passed = False
                print(
                    f"READINESS FAILED: '{args.served_model_name}' not in {model_ids}",
                    file=sys.stderr,
                )
        except httpx.HTTPError as exc:
            checks["readiness"] = {"error": str(exc)}
            passed = False
            print(f"READINESS FAILED: {exc}", file=sys.stderr)

        # 3. inference smoke test
        if passed:
            t0 = time.monotonic()
            try:
                r = client.post(
                    f"{base}/v1/chat/completions",
                    json={
                        "model": args.served_model_name,
                        "messages": [{"role": "user", "content": "Say OK and nothing else."}],
                        "max_tokens": 8,
                    },
                )
                dt = time.monotonic() - t0
                body = r.json()
                text = body.get("choices", [{}])[0].get("message", {}).get("content", "")
                checks["inference"] = {
                    "status_code": r.status_code,
                    "latency_s": round(dt, 2),
                    "response_text": text,
                }
                if r.status_code != 200 or not text.strip():
                    passed = False
                    print(
                        f"INFERENCE SMOKE TEST FAILED: status={r.status_code} body={body}",
                        file=sys.stderr,
                    )
            except httpx.HTTPError as exc:
                checks["inference"] = {"error": str(exc)}
                passed = False
                print(f"INFERENCE SMOKE TEST FAILED: {exc}", file=sys.stderr)
        else:
            checks["inference"] = {"skipped": "liveness/readiness failed"}

    record = EvidenceRecord(
        label="vllm_health_and_smoke_test",
        host=HostEnvironment(args.host_env),
        evidence=EvidenceKind(args.evidence),
        command=(
            f"health_check.py --host {args.host} --port {args.port} "
            f"--served-model-name {args.served_model_name}"
        ),
        passed=passed,
        result=checks,
        measured_at=datetime.now(UTC),
    )

    out_json = record.model_dump_json(indent=2)
    print(out_json)
    if args.out:
        Path(args.out).write_text(out_json, encoding="utf-8")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
