"""Pure logic for the serving benchmark harness: sweep planning, budget
enforcement, synthetic workload text, percentile/aggregate summarisation,
and the operating-configuration recommender.

No I/O here (no network, no subprocess, no filesystem) — `scripts/bench/
run_benchmark.py` is the thin, unit-untested I/O layer that calls this.
Keeping the planning/accounting/recommendation logic pure is what makes
"bound request count and runtime" and "don't recommend without real
measurements" checkable facts rather than claims about a script.
"""

from __future__ import annotations

import random
from datetime import datetime

from libs.schemas import (
    BenchmarkConfig,
    BenchmarkPointResult,
    BenchmarkWorkloadSpec,
    PercentileStats,
    RecommendedOperatingConfiguration,
    RequestOutcome,
)

_WORDLIST = [
    "system",
    "network",
    "process",
    "memory",
    "packet",
    "service",
    "config",
    "token",
    "signal",
    "buffer",
    "thread",
    "socket",
    "kernel",
    "module",
    "cluster",
    "vector",
    "matrix",
    "sample",
    "record",
    "report",
    "metric",
    "latency",
    "request",
    "response",
    "cache",
    "index",
    "stream",
    "queue",
    "worker",
    "handler",
]

# Rough words-per-token used only to SIZE the synthetic prompt when no
# tokenizer is available; the harness relies on the server's own reported
# `usage.prompt_tokens` as the authoritative count, never this estimate.
_APPROX_TOKENS_PER_WORD = 0.75


def synthetic_prompt(seed: int, approx_tokens: int) -> str:
    """A deterministic, non-sensitive prompt of roughly `approx_tokens` tokens.

    Same `seed` + `approx_tokens` always produces the same text. This is a
    sizing heuristic, not an exact token count — see module docstring and
    docs/BENCHMARK_HARNESS.md for why, and compare the request's reported
    `usage.prompt_tokens` against `approx_tokens` to see the real gap.
    """
    if approx_tokens <= 0:
        raise ValueError("approx_tokens must be positive")
    n_words = max(1, round(approx_tokens * _APPROX_TOKENS_PER_WORD))
    rng = random.Random(seed)
    words = [rng.choice(_WORDLIST) for _ in range(n_words)]
    return " ".join(words) + "."


def build_sweep_plan(
    cfg: BenchmarkConfig, max_model_len: int
) -> tuple[list[BenchmarkWorkloadSpec], list[str]]:
    """All sweep points implied by `cfg`, filtered against `max_model_len`.

    Returns (specs, skipped_notes) — a bucket/length-pair combination that
    doesn't fit is SKIPPED and explained, never silently clipped to fit.
    """
    specs: list[BenchmarkWorkloadSpec] = []
    skipped: list[str] = []
    seed_counter = 0

    for bucket in cfg.context_buckets:
        if bucket > max_model_len:
            skipped.append(f"bucket={bucket} exceeds max_model_len={max_model_len}; skipped")
            continue
        for pair in cfg.length_pairs:
            total = pair.input_tokens + pair.output_tokens
            pair_label = f"in={pair.input_tokens},out={pair.output_tokens}"
            if total > bucket:
                skipped.append(f"bucket={bucket}: pair({pair_label}) > bucket; skipped")
                continue
            if total > max_model_len:
                skipped.append(
                    f"bucket={bucket}: pair({pair_label}) needs {total} > max_model_len; skipped"
                )
                continue
            for concurrency in cfg.concurrency_levels:
                specs.append(
                    BenchmarkWorkloadSpec(
                        kind="sweep",
                        context_bucket=bucket,
                        input_tokens=pair.input_tokens,
                        output_tokens=pair.output_tokens,
                        concurrency=concurrency,
                        seed=cfg.seed + seed_counter,
                    )
                )
                seed_counter += 1

    return specs, skipped


def estimate_requests_for_plan(
    specs: list[BenchmarkWorkloadSpec], requests_per_point: int, warmup_per_point: int
) -> int:
    return len(specs) * (requests_per_point + warmup_per_point)


def enforce_budget(
    specs: list[BenchmarkWorkloadSpec],
    *,
    requests_per_point: int,
    warmup_per_point: int,
    max_requests_total: int,
) -> tuple[list[BenchmarkWorkloadSpec], bool, str | None]:
    """Drop the most expensive points first (highest concurrency, then
    largest context bucket) until the plan fits `max_requests_total`.

    Deterministic and logged — never a silent, unexplained truncation.
    """
    per_point_cost = requests_per_point + warmup_per_point
    total = len(specs) * per_point_cost
    if total <= max_requests_total:
        return specs, False, None

    # Most expensive (by concurrency, then context_bucket, then output_tokens) first.
    ordered = sorted(
        specs,
        key=lambda s: (s.concurrency, s.context_bucket, s.output_tokens),
        reverse=True,
    )
    kept: list[BenchmarkWorkloadSpec] = []
    dropped = 0
    budget = max_requests_total
    # Walk from cheapest to most expensive, keeping what fits, so the kept
    # set is biased toward the smaller/cheaper points rather than dropping
    # everything arbitrarily.
    for spec in sorted(ordered, key=lambda s: (s.concurrency, s.context_bucket, s.output_tokens)):
        if budget - per_point_cost >= 0:
            kept.append(spec)
            budget -= per_point_cost
        else:
            dropped += 1

    reason = (
        f"plan required {total} requests (> max_requests_total={max_requests_total}); "
        f"dropped {dropped} of {len(specs)} sweep points (highest concurrency/context first)"
    )
    return kept, True, reason


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolation percentile over already-sorted values."""
    if not sorted_values:
        raise ValueError("no values to compute a percentile over")
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * pct
    f, c = int(k), min(int(k) + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def percentile_stats(values: list[float]) -> PercentileStats | None:
    if not values:
        return None
    s = sorted(values)
    return PercentileStats(
        p50=_percentile(s, 0.50),
        p90=_percentile(s, 0.90),
        p99=_percentile(s, 0.99),
        mean=sum(s) / len(s),
        min=s[0],
        max=s[-1],
        n=len(s),
    )


def summarize_point(
    spec: BenchmarkWorkloadSpec,
    outcomes: list[RequestOutcome],
    *,
    started_at: datetime,
    finished_at: datetime,
    memory_before=None,
    memory_after=None,
) -> BenchmarkPointResult:
    n = len(outcomes)
    errors = [o for o in outcomes if not o.ok]
    timeouts = [o for o in outcomes if o.timed_out]
    ok_outcomes = [o for o in outcomes if o.ok]

    ttft_values = [o.ttft_s for o in ok_outcomes if o.ttft_s is not None]
    e2e_values = [o.e2e_latency_s for o in ok_outcomes if o.e2e_latency_s is not None]
    itl_values = [v for o in ok_outcomes for v in o.inter_chunk_latencies_s]

    single_request_stats = None
    if spec.concurrency == 1 and ok_outcomes:
        per_request_tok_s = [
            (o.actual_completion_tokens or o.requested_output_tokens) / o.e2e_latency_s
            for o in ok_outcomes
            if o.e2e_latency_s and o.e2e_latency_s > 0
        ]
        single_request_stats = percentile_stats(per_request_tok_s)

    aggregate_tok_s = None
    wall_s = (finished_at - started_at).total_seconds()
    if wall_s > 0 and ok_outcomes:
        total_completion_tokens = sum(
            (o.actual_completion_tokens or o.requested_output_tokens) for o in ok_outcomes
        )
        aggregate_tok_s = total_completion_tokens / wall_s

    return BenchmarkPointResult(
        spec=spec,
        n_requests=n,
        n_errors=len(errors),
        n_timeouts=len(timeouts),
        error_rate=(len(errors) / n) if n else 0.0,
        timeout_rate=(len(timeouts) / n) if n else 0.0,
        single_request_output_tok_s=single_request_stats,
        aggregate_output_tok_s=aggregate_tok_s,
        ttft_s=percentile_stats(ttft_values),
        inter_chunk_latency_s=percentile_stats(itl_values),
        e2e_latency_s=percentile_stats(e2e_values),
        memory_before=memory_before,
        memory_after=memory_after,
        started_at=started_at,
        finished_at=finished_at,
    )


def recommend_configuration(
    points: list[BenchmarkPointResult],
    *,
    sla_p99_e2e_latency_s: float | None,
) -> list[RecommendedOperatingConfiguration]:
    """For each context bucket, the concurrency level with the highest
    aggregate throughput among points with zero errors/timeouts (and, if
    `sla_p99_e2e_latency_s` is set, within that SLA). Never invents a
    recommendation for a bucket with no qualifying point.
    """
    by_bucket: dict[int, list[BenchmarkPointResult]] = {}
    for p in points:
        by_bucket.setdefault(p.spec.context_bucket, []).append(p)

    recs: list[RecommendedOperatingConfiguration] = []
    for bucket, bucket_points in sorted(by_bucket.items()):
        candidates = [
            p
            for p in bucket_points
            if p.error_rate == 0
            and p.timeout_rate == 0
            and p.aggregate_output_tok_s is not None
            and (
                sla_p99_e2e_latency_s is None
                or (p.e2e_latency_s is not None and p.e2e_latency_s.p99 <= sla_p99_e2e_latency_s)
            )
        ]
        if not candidates:
            continue
        best = max(candidates, key=lambda p: p.aggregate_output_tok_s)
        rationale = f"highest throughput, zero errors/timeouts, of {len(candidates)} candidates"
        if sla_p99_e2e_latency_s is not None:
            rationale += f", within the {sla_p99_e2e_latency_s}s p99 SLA"
        recs.append(
            RecommendedOperatingConfiguration(
                context_bucket=bucket,
                recommended_concurrency=best.spec.concurrency,
                rationale=rationale,
                aggregate_output_tok_s=best.aggregate_output_tok_s,
                p99_e2e_latency_s=best.e2e_latency_s.p99 if best.e2e_latency_s else float("nan"),
            )
        )
    return recs
