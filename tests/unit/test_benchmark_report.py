from __future__ import annotations

from datetime import UTC, datetime, timedelta

from libs.common import render_markdown, summarize_point
from libs.schemas import (
    BenchmarkReport,
    BenchmarkWorkloadSpec,
    EvidenceKind,
    HostEnvironment,
    RequestOutcome,
)


def _sweep_point():
    spec = BenchmarkWorkloadSpec(
        context_bucket=8192, input_tokens=512, output_tokens=128, concurrency=4, seed=1
    )
    outcomes = [
        RequestOutcome(
            ok=True,
            ttft_s=0.2,
            e2e_latency_s=1.5,
            requested_input_tokens=512,
            requested_output_tokens=128,
            actual_completion_tokens=128,
        )
        for _ in range(4)
    ]
    t0 = datetime.now(UTC)
    return summarize_point(spec, outcomes, started_at=t0, finished_at=t0 + timedelta(seconds=2))


def _report(**overrides) -> BenchmarkReport:
    base = dict(
        harness_test=True,
        host=HostEnvironment.CI,
        evidence=EvidenceKind.MOCKED,
        model="Qwen/Qwen3-30B-A3B-Instruct-2507-FP8",
        model_revision="abc123",
        served_model_name="qwen3",
        points=[_sweep_point()],
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC) + timedelta(seconds=10),
        recommended_operating_configuration=None,
        recommendation_pending_reason="no authorised hardware endpoint was available",
    )
    base.update(overrides)
    return BenchmarkReport(**base)


def test_harness_test_run_is_clearly_labelled_not_a_gpu_result():
    report = _report(harness_test=True)
    md = render_markdown(report)
    assert "HARNESS TEST" in md
    assert "not a GPU performance result" in md


def test_measurement_run_is_not_mislabelled_as_harness_test():
    report = _report(
        harness_test=False, evidence=EvidenceKind.HARDWARE, host=HostEnvironment.GB10_CLOUD
    )
    md = render_markdown(report)
    assert "MEASUREMENT RUN" in md
    assert "not a GPU performance result" not in md


def test_pending_recommendation_shown_when_absent():
    report = _report(recommended_operating_configuration=None)
    md = render_markdown(report)
    assert "PENDING" in md
    assert "no authorised hardware endpoint" in md


def test_recommendation_table_shown_when_present():
    from libs.schemas import RecommendedOperatingConfiguration

    rec = RecommendedOperatingConfiguration(
        context_bucket=8192,
        recommended_concurrency=4,
        rationale="highest throughput, zero errors",
        aggregate_output_tok_s=256.0,
        p99_e2e_latency_s=1.8,
    )
    report = _report(recommended_operating_configuration=[rec])
    md = render_markdown(report)
    assert "256.0" in md
    assert "recommended concurrency" in md


def test_sweep_table_includes_the_point_row():
    report = _report()
    md = render_markdown(report)
    assert "8192" in md
    assert "512/128" in md


def test_batching_not_multiplicative_caveat_present():
    md = render_markdown(_report())
    assert "never multiplied together" in md


def test_truncation_reason_surfaced():
    md = render_markdown(_report(truncated=True, truncation_reason="hit max_requests_total"))
    assert "TRUNCATED" in md
    assert "hit max_requests_total" in md


def test_adapter_switch_skip_reason_shown():
    md = render_markdown(_report(adapter_switch_skipped_reason="no adapters configured"))
    assert "no adapters configured" in md
