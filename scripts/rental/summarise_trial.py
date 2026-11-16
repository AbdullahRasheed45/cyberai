#!/usr/bin/env python3
"""Build the Stage-1 baseline / hardware-fitness report from the trial's result files.

Reads only what the lifecycle actually wrote (artifacts/run_*/ and runs/*/) and
writes one Markdown report: the document the DGX purchase gate
(DECISIONS_TO_REVISIT.md P-001) is decided from. It never judges pass/fail and
never invents a threshold or a number: a missing measurement is printed as
"not measured", and the owner's acceptance criteria are a section the owner fills.

Optional extrapolation (pure arithmetic on measured rates, labelled as such):
  --round-tokens N    training tokens in one planned round -> hours per round
  --hourly-rate R     rental price per hour (any currency) -> cost per round/run

    python3 scripts/rental/summarise_trial.py --out docs/stage1_baseline.md \
        --round-tokens 20000000 --hourly-rate 0.85

Standard library only. Run from the repository root (on the Spark or on a laptop
holding the copied artifacts/ and runs/ folders).
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

NA = "not measured"


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def fmt(value, digits=2, unit=""):
    if value is None:
        return NA
    if isinstance(value, float):
        value = round(value, digits)
    return f"{value}{unit}"


def workload_outcome(record):
    if "task_success" in record:
        return (
            "VERIFIED WORKFLOW"
            if record["task_success"] is True
            else ("FAILED: " + str(record.get("failure_category") or "WORKFLOW_NOT_VERIFIED"))
        )
    return record.get("outcome", NA)


def workflow_rows(artifacts):
    rows = []
    for run in sorted(artifacts.glob("run_*")):
        for label, directory in (("base", run / "baseline"), ("adapter", run)):
            record = load(directory / "workload_result.json")
            if not record or "task_success" not in record:
                continue
            usage = record.get("model_usage") or {}
            rows.append(
                [
                    run.name,
                    label,
                    workload_outcome(record),
                    usage.get("prompt_tokens", NA),
                    usage.get("completion_tokens", NA),
                    record.get("model_calls", NA),
                    record.get("action_attempts", NA),
                    record.get("action_count", NA),
                    fmt(record.get("complete_runtime_s"), 3),
                ]
            )
    return rows


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return out


def lifecycle_rows(artifacts: Path):
    rows, serving, grid = [], [], []
    for run_dir in sorted(artifacts.glob("run_*")):
        run = run_dir.name[len("run_") :]
        receipt = load(run_dir / "receipt.json") or {}
        orch = load(run_dir / "orchestration.json") or {}
        workload = load(run_dir / "workload_result.json") or {}
        releases = [r.get("release") for r in receipt.get("releases") or []]
        rows.append(
            [
                run,
                receipt.get("status", NA),
                (receipt.get("phases") or [NA])[-1],
                ", ".join(releases) or NA,
                orch.get("memory_telemetry", NA),
                (orch.get("docker_runtime") or {}).get("gpu_mode", NA),
                workload_outcome(workload),
            ]
        )
        inf = load(run_dir / "inference_measurements.json")
        if not inf:
            continue
        single = inf.get("single_stream") or {}
        serving.append(
            [
                run,
                fmt(single.get("ttft_s_mean"), 3, " s"),
                fmt(single.get("decode_tok_s_mean"), 1),
                fmt(single.get("e2e_tok_s_mean"), 1),
                fmt(inf.get("sampled_peak_mem_GB"), 1, " GB"),
                inf.get("sampled_peak_mem_source", NA),
                "yes" if inf.get("passed") else "no (see failures)",
            ]
        )
        for cell, result in (inf.get("matrix") or {}).items():
            grid.append(
                [
                    run,
                    cell,
                    f"{result.get('n_ok', NA)}/{result.get('n', NA)}",
                    fmt(result.get("aggregate_output_tok_s"), 1),
                    fmt(result.get("batch_wall_s"), 1, " s"),
                ]
            )
        for ctx, error in (inf.get("context_errors") or {}).items():
            grid.append([run, f"ctx {ctx}", "error", error[:80], ""])
    return rows, serving, grid


def training_rows(runs: Path, round_tokens, hourly_rate):
    rows, extrap = [], []
    for meta_path in sorted(runs.glob("*/train_meta.json")):
        meta = load(meta_path) or {}
        run = meta_path.parent.name
        cfg = meta.get("training_config") or {}
        reload_result = load(meta_path.parent / "reload_result.json") or {}
        hist = meta.get("processed_sequence_length_histogram") or {}
        longest = max((int(k) for k in hist), default=None)
        rate = meta.get("steady_state_tok_s")
        rows.append(
            [
                run,
                meta.get("precision", "bf16 (pre-precision file)"),
                cfg.get("max_seq_length", NA),
                cfg.get("batch_size", NA),
                meta.get("completed_steps", NA),
                fmt(rate, 1),
                fmt(meta.get("steady_state_seconds_per_step"), 2, " s"),
                fmt(meta.get("train_peak_mem_GB"), 1, " GB"),
                fmt(meta.get("load_runtime_s"), 0, " s"),
                fmt(longest),
                f"{reload_result.get('smoke_reload', NA)} / {reload_result.get('logit_match', NA)}",
            ]
        )
        if round_tokens and rate:
            hours = round_tokens / rate / 3600
            cost = fmt(hours * hourly_rate, 2) if hourly_rate else "rate not given"
            extrap.append([run, meta.get("precision", NA), fmt(rate, 1), fmt(hours, 1), cost])
    return rows, extrap


def build(artifacts: Path, runs: Path, round_tokens=None, hourly_rate=None) -> str:
    life, serving, grid = lifecycle_rows(artifacts)
    train, extrap = training_rows(runs, round_tokens, hourly_rate)
    probes = load(artifacts / "image_pin_collection" / "probes.json") or {}
    docker = load(artifacts / "docker_runtime" / "docker_runtime.json") or {}
    lines = [
        "# Stage 1 baseline — GB10 hardware-fitness report",
        "",
        f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} by "
        "`scripts/rental/summarise_trial.py` from the trial's own result files. "
        f"Missing measurements are shown as “{NA}”. This report contains no verdict: "
        "the purchase decision (DECISIONS_TO_REVISIT.md P-001) is the owner's.",
        "",
        "## Owner acceptance criteria (write these BEFORE reading the numbers)",
        "",
        "- Acceptable hours per training round on my data: ______",
        "- Minimum acceptable serving throughput (batched tok/s) and context: ______",
        "- Required: adapter serves on the FP8 MoE model (yes/no): ______",
        "- Decision: BUY / DO NOT BUY / RE-TEST — reason: ______",
        "",
        "## Machine and software",
        "",
    ]
    devices = {k: v.get("device") for k, v in probes.items()}
    lines += [
        f"- GPU seen inside images: {devices or NA}",
        f"- Docker settings measured: {docker.get('chosen') or NA} "
        f"(status {docker.get('status', NA)})",
        f"- Library versions (training image): "
        f"{(probes.get('unsloth_image') or {}).get('versions') or NA}",
        f"- Library versions (serving image): "
        f"{(probes.get('vllm_image') or {}).get('versions') or NA}",
        "",
        "## Lifecycle runs",
        "",
    ]
    headers = ["Run", "Status", "Last phase", "Memory released", "Memory source", "GPU mode"]
    lines += table([*headers, "Workload outcome"], life) if life else [NA]
    lines += ["", "## Web workflow (development only; no learning-gain claim)", ""]
    workflow = workflow_rows(artifacts)
    lines += (
        table(
            [
                "Run",
                "Model",
                "Outcome",
                "Prompt tokens",
                "Completion tokens",
                "Model calls",
                "Action attempts",
                "Completed actions",
                "Complete runtime s",
            ],
            workflow,
        )
        if workflow
        else [NA]
    )
    lines += ["", "## Serving speed (base model, FP8)", ""]
    lines += (
        table(
            ["Run", "Time to first token", "Decode tok/s", "End-to-end tok/s", "Peak memory"]
            + ["Peak source", "All requests OK"],
            serving,
        )
        if serving
        else [NA]
    )
    lines += ["", "### Context × concurrency grid", ""]
    lines += (
        table(["Run", "Cell", "OK/total", "Aggregate output tok/s", "Batch wall time"], grid)
        if grid
        else [NA]
    )
    lines += ["", "## Training speed (LoRA)", ""]
    lines += (
        table(
            ["Run", "Precision", "Max seq", "Batch", "Steps", "Steady tok/s", "s/step"]
            + ["Peak CUDA mem", "Model load", "Longest seq seen", "Reload / logit match"],
            train,
        )
        if train
        else [NA]
    )
    lines += [
        "",
        "Compare precisions only between runs that differ in nothing else. “Longest seq "
        "seen” shows whether the data actually exercised the configured length.",
        "",
        "## Extrapolation (arithmetic on the measured rates above — not a measurement)",
        "",
    ]
    if extrap:
        lines.append(
            f"Assumes one round = {round_tokens:,} training tokens at the measured steady "
            "rate; excludes model load, evaluation and export time."
        )
        lines.append("")
        lines += table(["Run", "Precision", "Steady tok/s", "Hours per round", "Cost"], extrap)
    else:
        lines.append("Not computed: pass `--round-tokens` (and `--hourly-rate`) with real rates.")
    lines += [
        "",
        "## Not established by this trial",
        "",
        "Model quality or learning gain; six-domain capability; behaviour on the owned "
        "unit's OS image (re-run on purchase, R-003). Pilot-data timings do not forecast "
        "production cadence unless the data profile was representative.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--runs", type=Path, default=Path("runs"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--round-tokens", type=int)
    parser.add_argument("--hourly-rate", type=float)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"{args.out} exists; choose a new path (reports are never overwritten)")
    report = build(args.artifacts, args.runs, args.round_tokens, args.hourly_rate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
