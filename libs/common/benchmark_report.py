"""Render a `libs.schemas.BenchmarkReport` as a readable Markdown report.

Pure formatting of already-typed data — no I/O, no measurement logic (that
is `libs/common/benchmark_domain.py`). Kept separate and unit-tested on its
own so a reporting bug can't masquerade as a measurement bug.
"""

from __future__ import annotations

from libs.schemas import BenchmarkPointResult, BenchmarkReport


def _fmt(x: float | None, nd: int = 2) -> str:
    return "-" if x is None else f"{x:.{nd}f}"


def _point_row(p: BenchmarkPointResult) -> str:
    s = p.spec
    single = _fmt(p.single_request_output_tok_s.p50 if p.single_request_output_tok_s else None)
    agg = _fmt(p.aggregate_output_tok_s)
    ttft = _fmt(p.ttft_s.p50 if p.ttft_s else None)
    ttft99 = _fmt(p.ttft_s.p99 if p.ttft_s else None)
    e2e = _fmt(p.e2e_latency_s.p50 if p.e2e_latency_s else None)
    e2e99 = _fmt(p.e2e_latency_s.p99 if p.e2e_latency_s else None)
    return (
        f"| {s.context_bucket} | {s.input_tokens}/{s.output_tokens} | {s.concurrency} "
        f"| {p.n_requests} | {p.error_rate:.0%} | {p.timeout_rate:.0%} "
        f"| {single} | {agg} | {ttft}/{ttft99} | {e2e}/{e2e99} |"
    )


def render_markdown(report: BenchmarkReport) -> str:
    lines: list[str] = []
    kind = "HARNESS TEST (mocked/controlled endpoint)" if report.harness_test else "MEASUREMENT RUN"
    lines.append(f"# Serving benchmark report — {kind}")
    lines.append("")
    if report.harness_test:
        lines.append(
            "> **This is a harness test, not a GPU performance result.** It proves the "
            "benchmark harness's own accounting and failure handling against a "
            "controlled/mock endpoint — none of the numbers below say anything about "
            "real vLLM/GB10 performance."
        )
        lines.append("")
    lines.append(
        "This is a serving-capacity/latency harness, not the sealed cybersecurity "
        "capability benchmark (`benchmarks/sealed/`)."
    )
    lines.append("")

    lines.append("## Provenance")
    lines.append(f"- host: `{report.host.value}` · evidence: `{report.evidence.value}`")
    lines.append(f"- model: `{report.model}` @ `{report.model_revision}`")
    lines.append(f"- served as: `{report.served_model_name}`")
    if report.image_reference:
        lines.append(f"- image: `{report.image_reference}`")
    lines.append(
        f"- run window: {report.started_at.isoformat()} -> {report.finished_at.isoformat()}"
    )
    if report.truncated:
        lines.append(f"- **TRUNCATED**: {report.truncation_reason}")
    lines.append("")

    lines.append("## Sweep results")
    lines.append(
        "> Concurrency levels are compared side by side, never multiplied together — "
        "batching and long-context workloads spend the same KV-cache budget in "
        "opposite ways (brief §5.2), so a higher number at one concurrency does not "
        "imply a proportional gain at another."
    )
    lines.append("")
    lines.append(
        "| ctx | in/out tok | conc | n | err% | timeout% | single tok/s (p50) "
        "| agg tok/s | TTFT s (p50/p99) | e2e s (p50/p99) |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for p in report.points:
        if p.spec.kind == "sweep":
            lines.append(_point_row(p))
    lines.append("")

    probe_points = [p for p in report.points if p.spec.kind == "prefix_cache_probe"]
    lines.append("## Prefix-cache hit/miss comparison (heuristic)")
    if probe_points:
        lines.append(
            "> No definitive per-request hit/miss flag is exposed by the generic "
            "OpenAI-compatible endpoint; this compares TTFT on a cold (first) issue "
            "of a prompt against repeats of the identical prompt as a heuristic."
        )
        for p in probe_points:
            ttft = p.ttft_s
            p50 = _fmt(ttft.p50 if ttft else None)
            tmin = _fmt(ttft.min if ttft else None)
            tmax = _fmt(ttft.max if ttft else None)
            lines.append(
                f"- bucket={p.spec.context_bucket}, in={p.spec.input_tokens}: "
                f"TTFT p50={p50}s over {p.n_requests} repeats (min={tmin}s, max={tmax}s)"
            )
    else:
        lines.append("- not run.")
    lines.append("")

    adapter_points = [p for p in report.points if p.spec.kind == "adapter_switch"]
    lines.append("## Multi-LoRA adapter switching")
    if report.adapter_switch_skipped_reason:
        lines.append(f"- skipped: {report.adapter_switch_skipped_reason}")
    elif adapter_points:
        lines.append("| adapter | n | err% | e2e s (p50/p99) |")
        lines.append("|---|---|---|---|")
        for p in adapter_points:
            e2e = p.e2e_latency_s
            lines.append(
                f"| {p.spec.lora_adapter} | {p.n_requests} | {p.error_rate:.0%} "
                f"| {_fmt(e2e.p50 if e2e else None)}/{_fmt(e2e.p99 if e2e else None)} |"
            )
    else:
        lines.append("- not run (no adapters configured to exercise).")
    lines.append("")

    lines.append("## Recommended operating configuration")
    if report.recommended_operating_configuration:
        lines.append(
            "| context bucket | recommended concurrency | agg tok/s | p99 e2e s | rationale |"
        )
        lines.append("|---|---|---|---|---|")
        for rec in report.recommended_operating_configuration:
            agg = f"{rec.aggregate_output_tok_s:.1f}"
            p99 = f"{rec.p99_e2e_latency_s:.2f}"
            lines.append(
                f"| {rec.context_bucket} | {rec.recommended_concurrency} "
                f"| {agg} | {p99} | {rec.rationale} |"
            )
    else:
        lines.append(f"- **PENDING**: {report.recommendation_pending_reason}")
    lines.append("")

    return "\n".join(lines)
