#!/usr/bin/env python3
"""Reproducible serving-capacity benchmark harness.

Measures the SERVING ENDPOINT's throughput/latency/capacity trade-offs
(context length x concurrency x batching) against synthetic, non-sensitive,
seeded workloads. This is NOT the sealed cybersecurity capability benchmark
(`benchmarks/sealed/`) — see `docs/BENCHMARK_HARNESS.md`.

All planning/accounting/recommendation logic is pure and lives in
`libs/common/benchmark_domain.py` (unit tested there); this script is the
I/O layer: issuing HTTP requests, sampling memory, writing the report.

Usage (against a real or mock endpoint — the harness doesn't care which;
`--evidence`/`--host-env`/`--harness-test` say which it actually was):
    uv run python scripts/bench/run_benchmark.py \
        --host 127.0.0.1 --port 8000 --served-model-name qwen3 \
        --evidence hardware --host-env gb10_cloud \
        --out-json evidence/bench/run.json --out-report evidence/bench/run.md

    # Harness self-test against a controlled/mock endpoint:
    uv run python scripts/bench/run_benchmark.py \
        --host 127.0.0.1 --port <mock-port> --served-model-name qwen3 \
        --evidence mocked --host-env ci --harness-test \
        --benchmark-config configs/benchmark.harness-test.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libs.common import (  # noqa: E402
    build_sweep_plan,
    enforce_budget,
    load_yaml_config,
    recommend_configuration,
    render_markdown,
    summarize_point,
    synthetic_prompt,
)
from libs.schemas import (  # noqa: E402
    BenchmarkConfig,
    BenchmarkReport,
    BenchmarkWorkloadSpec,
    EvidenceKind,
    HostEnvironment,
    MemorySnapshot,
    RequestOutcome,
    ServingConfig,
)

# --- memory telemetry (best-effort; never crashes the run if unavailable) ---


def sample_memory() -> MemorySnapshot:
    now = datetime.now(UTC)
    sys_avail = sys_total = gpu_free = gpu_total = None
    source: str = "unavailable"

    try:
        meminfo: dict[str, int] = {}
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    meminfo[parts[0].strip()] = int(parts[1].strip().split()[0])
        if "MemTotal" in meminfo:
            sys_total = meminfo["MemTotal"] / 1024 / 1024
        if "MemAvailable" in meminfo:
            sys_avail = meminfo["MemAvailable"] / 1024 / 1024
        source = "proc_meminfo"
    except OSError:
        pass

    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            free_mib, total_mib = (float(x) for x in out.stdout.strip().splitlines()[0].split(","))
            gpu_free, gpu_total = free_mib / 1024, total_mib / 1024
            source = "nvidia_smi"
    except (OSError, subprocess.SubprocessError, ValueError):
        pass

    return MemorySnapshot(
        taken_at=now,
        system_mem_available_gib=sys_avail,
        system_mem_total_gib=sys_total,
        gpu_mem_free_gib=gpu_free,
        gpu_mem_total_gib=gpu_total,
        source=source,  # type: ignore[arg-type]
    )


class _MemorySampler:
    """Periodic background memory sampling, independent of per-point
    before/after snapshots. Runs in a thread since both /proc reads and
    nvidia-smi are blocking."""

    def __init__(self, interval_s: float):
        self.interval_s = interval_s
        self.samples: list[MemorySnapshot] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.samples.append(sample_memory())
            self._stop.wait(self.interval_s)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)


# --- a single streaming request ---------------------------------------------


async def issue_request(
    client: httpx.AsyncClient,
    url: str,
    model: str,
    prompt: str,
    requested_input_tokens: int,
    requested_output_tokens: int,
    timeout_s: float,
) -> RequestOutcome:
    t_start = time.monotonic()
    ttft: float | None = None
    prev_chunk_t: float | None = None
    inter_chunk: list[float] = []
    text_parts: list[str] = []
    actual_prompt_tokens: int | None = None
    actual_completion_tokens: int | None = None

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": requested_output_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
        # vLLM OpenAI-server extension: generate the full requested length
        # instead of stopping at EOS, so output-length is actually controlled.
        "ignore_eos": True,
    }
    try:
        async with client.stream("POST", url, json=body, timeout=timeout_s) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line[len("data:") :].strip()
                if payload == "[DONE]":
                    break
                chunk = json.loads(payload)
                now = time.monotonic()
                choices = chunk.get("choices") or []
                content = choices[0].get("delta", {}).get("content") if choices else None
                if content:
                    if ttft is None:
                        ttft = now - t_start
                    elif prev_chunk_t is not None:
                        inter_chunk.append(now - prev_chunk_t)
                    prev_chunk_t = now
                    text_parts.append(content)
                usage = chunk.get("usage")
                if usage:
                    actual_prompt_tokens = usage.get("prompt_tokens")
                    actual_completion_tokens = usage.get("completion_tokens")
        e2e = time.monotonic() - t_start
        return RequestOutcome(
            ok=True,
            ttft_s=ttft,
            e2e_latency_s=e2e,
            inter_chunk_latencies_s=inter_chunk,
            requested_input_tokens=requested_input_tokens,
            requested_output_tokens=requested_output_tokens,
            actual_prompt_tokens=actual_prompt_tokens,
            actual_completion_tokens=actual_completion_tokens or len(text_parts) or None,
        )
    except httpx.TimeoutException as exc:
        return RequestOutcome(
            ok=False,
            timed_out=True,
            error=str(exc),
            requested_input_tokens=requested_input_tokens,
            requested_output_tokens=requested_output_tokens,
        )
    except httpx.HTTPError as exc:
        return RequestOutcome(
            ok=False,
            error=str(exc),
            requested_input_tokens=requested_input_tokens,
            requested_output_tokens=requested_output_tokens,
        )


async def run_point(
    client: httpx.AsyncClient,
    url: str,
    model: str,
    spec: BenchmarkWorkloadSpec,
    n_requests: int,
    timeout_s: float,
) -> list[RequestOutcome]:
    prompt = synthetic_prompt(seed=spec.seed, approx_tokens=spec.input_tokens)
    sem = asyncio.Semaphore(spec.concurrency)

    async def _one() -> RequestOutcome:
        async with sem:
            return await issue_request(
                client,
                url,
                model,
                prompt,
                spec.input_tokens,
                spec.output_tokens,
                timeout_s=timeout_s,
            )

    return list(await asyncio.gather(*[_one() for _ in range(n_requests)]))


# --- CLI / orchestration -----------------------------------------------------


class _Budget:
    """Runtime (not just planning-time) bound enforcement."""

    def __init__(self, max_requests_total: int, max_runtime_s: float):
        self.max_requests_total = max_requests_total
        self.max_runtime_s = max_runtime_s
        self.requests_issued = 0
        self.start = time.monotonic()

    def exhausted(self) -> str | None:
        if self.requests_issued >= self.max_requests_total:
            return f"hit max_requests_total={self.max_requests_total} mid-run"
        if (time.monotonic() - self.start) >= self.max_runtime_s:
            return f"hit max_runtime_s={self.max_runtime_s} mid-run"
        return None


async def main_async(args: argparse.Namespace) -> BenchmarkReport:
    serving_cfg = load_yaml_config(args.serving_config, ServingConfig)
    bench_cfg = load_yaml_config(args.benchmark_config, BenchmarkConfig)

    host = args.host or serving_cfg.host
    port = args.port or serving_cfg.port
    served_model_name = args.served_model_name or serving_cfg.served_model_name
    url = f"http://{host}:{port}/v1/chat/completions"

    specs, skipped_notes = build_sweep_plan(bench_cfg, max_model_len=serving_cfg.max_model_len)
    specs, plan_truncated, plan_truncation_reason = enforce_budget(
        specs,
        requests_per_point=bench_cfg.requests_per_point,
        warmup_per_point=bench_cfg.warmup_requests_per_point,
        max_requests_total=bench_cfg.max_requests_total,
    )
    for note in skipped_notes:
        print(f"[bench] SKIPPED: {note}", file=sys.stderr)

    budget = _Budget(bench_cfg.max_requests_total, bench_cfg.max_runtime_s)
    started_at = datetime.now(UTC)
    points = []
    runtime_truncated = False
    runtime_truncation_reason: str | None = None

    sampler = _MemorySampler(bench_cfg.memory_sample_interval_s)
    sampler.start()

    async with httpx.AsyncClient() as client:
        for spec in specs:
            reason = budget.exhausted()
            if reason:
                runtime_truncated, runtime_truncation_reason = True, reason
                print(f"[bench] STOPPING sweep early: {reason}", file=sys.stderr)
                break

            # warm-up (discarded, not counted in stats, but still logged)
            if bench_cfg.warmup_requests_per_point:
                warm = await run_point(
                    client,
                    url,
                    served_model_name,
                    spec,
                    bench_cfg.warmup_requests_per_point,
                    bench_cfg.request_timeout_s,
                )
                budget.requests_issued += len(warm)
                warm_failures = sum(1 for o in warm if not o.ok)
                if warm_failures:
                    print(
                        f"[bench] WARNING: {warm_failures}/{len(warm)} warm-up requests "
                        f"failed for {spec.context_bucket=} {spec.concurrency=}",
                        file=sys.stderr,
                    )

            mem_before = sample_memory()
            t0 = datetime.now(UTC)
            outcomes = await run_point(
                client,
                url,
                served_model_name,
                spec,
                bench_cfg.requests_per_point,
                bench_cfg.request_timeout_s,
            )
            budget.requests_issued += len(outcomes)
            t1 = datetime.now(UTC)
            mem_after = sample_memory()

            points.append(
                summarize_point(
                    spec,
                    outcomes,
                    started_at=t0,
                    finished_at=t1,
                    memory_before=mem_before,
                    memory_after=mem_after,
                )
            )

        # Prefix-cache probe: sequential repeats of ONE prompt at concurrency=1.
        probe_specs = [
            BenchmarkWorkloadSpec(
                kind="prefix_cache_probe",
                context_bucket=bc,
                input_tokens=pair.input_tokens,
                output_tokens=pair.output_tokens,
                concurrency=1,
                seed=bench_cfg.seed,
            )
            for bc in bench_cfg.context_buckets[:1]
            for pair in bench_cfg.length_pairs[:1]
            if not budget.exhausted()
        ]
        for spec in probe_specs:
            prompt = synthetic_prompt(seed=spec.seed, approx_tokens=spec.input_tokens)
            outcomes = []
            t0 = datetime.now(UTC)
            for _ in range(bench_cfg.prefix_cache_probe_repeats + 1):
                if budget.exhausted():
                    break
                outcome = await issue_request(
                    client,
                    url,
                    served_model_name,
                    prompt,
                    spec.input_tokens,
                    spec.output_tokens,
                    timeout_s=bench_cfg.request_timeout_s,
                )
                outcomes.append(outcome)
                budget.requests_issued += 1
            t1 = datetime.now(UTC)
            if outcomes:
                points.append(summarize_point(spec, outcomes, started_at=t0, finished_at=t1))

    sampler.stop()
    finished_at = datetime.now(UTC)

    truncated = plan_truncated or runtime_truncated
    truncation_reason = (
        " ; ".join(r for r in [plan_truncation_reason, runtime_truncation_reason] if r) or None
    )

    adapter_skip_reason = None
    if not bench_cfg.lora_adapters_to_exercise:
        adapter_skip_reason = "no adapters listed in benchmark.yaml:lora_adapters_to_exercise"
    elif not serving_cfg.enable_lora:
        adapter_skip_reason = "serving.yaml:enable_lora is false"

    recommended = None
    recommendation_pending_reason = None
    if args.evidence == EvidenceKind.HARDWARE.value and not args.harness_test:
        recommended = recommend_configuration(
            points, sla_p99_e2e_latency_s=bench_cfg.sla_p99_e2e_latency_s
        )
        if not recommended:
            recommendation_pending_reason = (
                "no sweep point had zero errors/timeouts to recommend from"
            )
    else:
        recommendation_pending_reason = (
            "no authorised hardware endpoint was available for this run "
            f"(evidence={args.evidence}, harness_test={args.harness_test})"
        )

    hardware_descriptor: dict = {"memory_samples_taken": len(sampler.samples)}
    try:
        uname = subprocess.run(["uname", "-a"], capture_output=True, text=True, timeout=5)
        hardware_descriptor["uname"] = uname.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        smi = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=10)
        hardware_descriptor["nvidia_smi_L"] = smi.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    image_reference = None
    image_file = REPO_ROOT / "containers" / "vllm-gb10" / "IMAGE.txt"
    if image_file.is_file():
        for line in image_file.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.strip().startswith("#"):
                image_reference = line.strip()
                break

    return BenchmarkReport(
        harness_test=args.harness_test,
        host=HostEnvironment(args.host_env),
        evidence=EvidenceKind(args.evidence),
        model=serving_cfg.model,
        model_revision=serving_cfg.model_revision,
        served_model_name=served_model_name,
        image_reference=image_reference,
        serving_config_snapshot=serving_cfg.model_dump(),
        benchmark_config_snapshot=bench_cfg.model_dump(),
        hardware_descriptor=hardware_descriptor,
        points=points,
        adapter_switch_skipped_reason=adapter_skip_reason,
        truncated=truncated,
        truncation_reason=truncation_reason,
        started_at=started_at,
        finished_at=finished_at,
        recommended_operating_configuration=recommended,
        recommendation_pending_reason=recommendation_pending_reason,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serving-config", default=str(REPO_ROOT / "configs" / "serving.yaml"))
    parser.add_argument("--benchmark-config", default=str(REPO_ROOT / "configs" / "benchmark.yaml"))
    parser.add_argument(
        "--host", default=None, help="override serving.yaml host (e.g. to hit a mock)"
    )
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--served-model-name", default=None)
    parser.add_argument(
        "--harness-test",
        action="store_true",
        help="mark this run as testing the HARNESS ITSELF, not a GPU performance result",
    )
    parser.add_argument("--host-env", choices=[e.value for e in HostEnvironment], required=True)
    parser.add_argument("--evidence", choices=[e.value for e in EvidenceKind], required=True)
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--out-report", default=None)
    args = parser.parse_args()

    if args.evidence == EvidenceKind.HARDWARE.value and args.harness_test:
        print(
            "REFUSED: --harness-test cannot be combined with --evidence hardware", file=sys.stderr
        )
        return 2

    report = asyncio.run(main_async(args))

    out_json = report.model_dump_json(indent=2)
    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(out_json, encoding="utf-8")
    else:
        print(out_json)

    md = render_markdown(report)
    if args.out_report:
        Path(args.out_report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_report).write_text(md, encoding="utf-8")
    else:
        print(md, file=sys.stderr)

    any_errors = any(p.error_rate > 0 for p in report.points)
    return 1 if any_errors and args.evidence == EvidenceKind.HARDWARE.value else 0


if __name__ == "__main__":
    raise SystemExit(main())
