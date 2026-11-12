"""Pure-logic tests for the benchmark harness's planning, budgeting,
percentile, and recommendation functions — none of these need a server."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from libs.common import (
    build_sweep_plan,
    enforce_budget,
    percentile_stats,
    recommend_configuration,
    summarize_point,
    synthetic_prompt,
)
from libs.schemas import BenchmarkConfig, BenchmarkWorkloadSpec, LengthPair, RequestOutcome


def _cfg(**overrides) -> BenchmarkConfig:
    base = dict(
        seed=1,
        warmup_requests_per_point=1,
        requests_per_point=5,
        max_requests_total=1000,
        max_runtime_s=600,
        request_timeout_s=30,
        context_buckets=[8192, 32768],
        length_pairs=[LengthPair(input_tokens=512, output_tokens=128)],
        concurrency_levels=[1, 8],
        prefix_cache_probe_repeats=1,
        lora_adapters_to_exercise=[],
    )
    base.update(overrides)
    return BenchmarkConfig(**base)


# --- synthetic_prompt -------------------------------------------------------


def test_synthetic_prompt_deterministic_for_same_seed():
    a = synthetic_prompt(seed=42, approx_tokens=100)
    b = synthetic_prompt(seed=42, approx_tokens=100)
    assert a == b


def test_synthetic_prompt_differs_for_different_seed():
    a = synthetic_prompt(seed=1, approx_tokens=100)
    b = synthetic_prompt(seed=2, approx_tokens=100)
    assert a != b


def test_synthetic_prompt_rejects_nonpositive_length():
    with pytest.raises(ValueError):
        synthetic_prompt(seed=1, approx_tokens=0)


# --- build_sweep_plan --------------------------------------------------------


def test_sweep_plan_skips_bucket_exceeding_max_model_len():
    cfg = _cfg(context_buckets=[8192, 65536])
    specs, skipped = build_sweep_plan(cfg, max_model_len=32768)
    assert all(s.context_bucket != 65536 for s in specs)
    assert any("65536" in s for s in skipped)


def test_sweep_plan_skips_length_pair_that_does_not_fit_bucket():
    cfg = _cfg(
        context_buckets=[1024],
        length_pairs=[LengthPair(input_tokens=900, output_tokens=900)],  # 1800 > 1024
    )
    specs, skipped = build_sweep_plan(cfg, max_model_len=32768)
    assert specs == []
    assert any("skipped" in s for s in skipped)


def test_sweep_plan_produces_one_spec_per_bucket_pair_concurrency_combo():
    cfg = _cfg(
        context_buckets=[8192], length_pairs=[LengthPair(input_tokens=100, output_tokens=50)]
    )
    specs, skipped = build_sweep_plan(cfg, max_model_len=32768)
    assert len(specs) == len(cfg.concurrency_levels)
    assert {s.concurrency for s in specs} == set(cfg.concurrency_levels)
    assert skipped == []


def test_sweep_plan_seeds_are_unique_and_reproducible():
    cfg = _cfg()
    specs1, _ = build_sweep_plan(cfg, max_model_len=32768)
    specs2, _ = build_sweep_plan(cfg, max_model_len=32768)
    assert [s.seed for s in specs1] == [s.seed for s in specs2]
    assert len(set(s.seed for s in specs1)) == len(specs1)


# --- enforce_budget -----------------------------------------------------------


def test_enforce_budget_no_op_when_within_budget():
    specs = [
        BenchmarkWorkloadSpec(
            context_bucket=8192, input_tokens=1, output_tokens=1, concurrency=1, seed=i
        )
        for i in range(3)
    ]
    kept, truncated, reason = enforce_budget(
        specs, requests_per_point=5, warmup_per_point=1, max_requests_total=1000
    )
    assert kept == specs
    assert truncated is False
    assert reason is None


def test_enforce_budget_truncates_and_explains_when_over_budget():
    specs = [
        BenchmarkWorkloadSpec(
            context_bucket=b, input_tokens=1, output_tokens=1, concurrency=c, seed=i
        )
        for i, (b, c) in enumerate([(8192, 1), (8192, 16), (32768, 1), (32768, 16)])
    ]
    # Each point costs 6 requests (5 + 1 warmup); budget for only 2 points.
    kept, truncated, reason = enforce_budget(
        specs, requests_per_point=5, warmup_per_point=1, max_requests_total=12
    )
    assert truncated is True
    assert reason is not None
    assert len(kept) <= 2
    # The cheapest (lowest concurrency/context) points are kept preferentially.
    assert all(s.concurrency == 1 for s in kept) or len(kept) < 2


def test_enforce_budget_never_exceeds_max_requests_total():
    specs = [
        BenchmarkWorkloadSpec(
            context_bucket=8192, input_tokens=1, output_tokens=1, concurrency=c, seed=i
        )
        for i, c in enumerate([1, 2, 4, 8, 16, 32])
    ]
    kept, _, _ = enforce_budget(
        specs, requests_per_point=10, warmup_per_point=2, max_requests_total=25
    )
    assert len(kept) * 12 <= 25


# --- percentile_stats ---------------------------------------------------------


def test_percentile_stats_empty_is_none():
    assert percentile_stats([]) is None


def test_percentile_stats_single_value():
    stats = percentile_stats([5.0])
    assert stats.p50 == stats.p90 == stats.p99 == stats.mean == stats.min == stats.max == 5.0
    assert stats.n == 1


def test_percentile_stats_monotonic_ordering():
    stats = percentile_stats([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    assert stats.min <= stats.p50 <= stats.p90 <= stats.p99 <= stats.max
    assert stats.n == 10


# --- summarize_point -----------------------------------------------------------


def _spec(**overrides) -> BenchmarkWorkloadSpec:
    base = dict(context_bucket=8192, input_tokens=100, output_tokens=50, concurrency=1, seed=1)
    base.update(overrides)
    return BenchmarkWorkloadSpec(**base)


def test_summarize_point_all_ok_reports_zero_errors():
    spec = _spec()
    outcomes = [
        RequestOutcome(
            ok=True,
            ttft_s=0.1,
            e2e_latency_s=1.0,
            inter_chunk_latencies_s=[0.01, 0.02],
            requested_input_tokens=100,
            requested_output_tokens=50,
            actual_completion_tokens=50,
        )
        for _ in range(5)
    ]
    t0 = datetime.now(UTC)
    result = summarize_point(spec, outcomes, started_at=t0, finished_at=t0 + timedelta(seconds=5))
    assert result.n_requests == 5
    assert result.n_errors == 0
    assert result.error_rate == 0.0
    assert result.ttft_s is not None
    assert result.aggregate_output_tok_s is not None


def test_summarize_point_counts_errors_and_timeouts_separately():
    spec = _spec()
    outcomes = [
        RequestOutcome(
            ok=True,
            ttft_s=0.1,
            e2e_latency_s=1.0,
            requested_input_tokens=1,
            requested_output_tokens=1,
        ),
        RequestOutcome(
            ok=False, error="connection reset", requested_input_tokens=1, requested_output_tokens=1
        ),
        RequestOutcome(
            ok=False,
            timed_out=True,
            error="timeout",
            requested_input_tokens=1,
            requested_output_tokens=1,
        ),
    ]
    t0 = datetime.now(UTC)
    result = summarize_point(spec, outcomes, started_at=t0, finished_at=t0 + timedelta(seconds=1))
    assert result.n_requests == 3
    assert result.n_errors == 2
    assert result.n_timeouts == 1
    assert result.error_rate == pytest.approx(2 / 3)
    assert result.timeout_rate == pytest.approx(1 / 3)


def test_summarize_point_single_request_tok_s_only_at_concurrency_one():
    outcomes = [
        RequestOutcome(
            ok=True,
            e2e_latency_s=2.0,
            requested_input_tokens=1,
            requested_output_tokens=100,
            actual_completion_tokens=100,
        )
    ]
    t0 = datetime.now(UTC)
    at_c1 = summarize_point(
        _spec(concurrency=1), outcomes, started_at=t0, finished_at=t0 + timedelta(seconds=2)
    )
    at_c8 = summarize_point(
        _spec(concurrency=8), outcomes, started_at=t0, finished_at=t0 + timedelta(seconds=2)
    )
    assert at_c1.single_request_output_tok_s is not None
    assert at_c8.single_request_output_tok_s is None


# --- recommend_configuration ---------------------------------------------------


def test_recommend_configuration_picks_highest_throughput_with_no_errors():
    t0 = datetime.now(UTC)
    low = summarize_point(
        _spec(concurrency=1, context_bucket=8192),
        [
            RequestOutcome(
                ok=True,
                e2e_latency_s=1.0,
                requested_input_tokens=1,
                requested_output_tokens=10,
                actual_completion_tokens=10,
            )
        ],
        started_at=t0,
        finished_at=t0 + timedelta(seconds=1),
    )
    high = summarize_point(
        _spec(concurrency=8, context_bucket=8192),
        [
            RequestOutcome(
                ok=True,
                e2e_latency_s=1.0,
                requested_input_tokens=1,
                requested_output_tokens=100,
                actual_completion_tokens=100,
            )
            for _ in range(8)
        ],
        started_at=t0,
        finished_at=t0 + timedelta(seconds=1),
    )
    recs = recommend_configuration([low, high], sla_p99_e2e_latency_s=None)
    assert len(recs) == 1
    assert recs[0].recommended_concurrency == 8
    assert recs[0].context_bucket == 8192


def test_recommend_configuration_excludes_points_with_errors():
    t0 = datetime.now(UTC)
    bad = summarize_point(
        _spec(concurrency=8, context_bucket=8192),
        [
            RequestOutcome(
                ok=False, error="boom", requested_input_tokens=1, requested_output_tokens=1
            )
        ],
        started_at=t0,
        finished_at=t0 + timedelta(seconds=1),
    )
    recs = recommend_configuration([bad], sla_p99_e2e_latency_s=None)
    assert recs == []


def test_recommend_configuration_respects_sla():
    t0 = datetime.now(UTC)
    fast_low_throughput = summarize_point(
        _spec(concurrency=1, context_bucket=8192),
        [
            RequestOutcome(
                ok=True,
                e2e_latency_s=0.5,
                requested_input_tokens=1,
                requested_output_tokens=10,
                actual_completion_tokens=10,
            )
        ],
        started_at=t0,
        finished_at=t0 + timedelta(seconds=1),
    )
    slow_high_throughput = summarize_point(
        _spec(concurrency=8, context_bucket=8192),
        [
            RequestOutcome(
                ok=True,
                e2e_latency_s=10.0,
                requested_input_tokens=1,
                requested_output_tokens=1000,
                actual_completion_tokens=1000,
            )
            for _ in range(8)
        ],
        started_at=t0,
        finished_at=t0 + timedelta(seconds=1),
    )
    recs = recommend_configuration(
        [fast_low_throughput, slow_high_throughput], sla_p99_e2e_latency_s=1.0
    )
    assert len(recs) == 1
    assert recs[0].recommended_concurrency == 1  # the only one within the SLA
