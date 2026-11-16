# cyberai

Autonomous, self-improving cybersecurity AI — Stage 0/1 foundation.

**Read `CLAUDE.md` first.** It is the operating contract for this repo
(prime directives, stage order, git/PR discipline) and takes precedence over
anything below. This README is a quick-start for humans; `CLAUDE.md` and
`docs/` are authoritative.

## What this is, right now

Stage 1, prepared for the GB10 hardware trial that gates the DGX Spark purchase:
typed configs and evidence schemas; a narrow, assurance-tested detection verifier
(`detection_verifier/`); a small owned-lab web workflow (`lab/web_workflow/`); and
the phased rental lifecycle (`rental/`) that serves Qwen3-30B-A3B (FP8), measures
it, trains a 4-bit QLoRA adapter, reloads and deploys it, and exports hashed
evidence, with a live tracker. Nothing has run on a GPU yet. There is no learning
engine, model registry or sealed benchmark yet — see `docs/MASTER_BRIEF_v2.2.md` §4 (design) and §8–§12 (the build, stage by stage).

**The design, status and the whole build plan:** `docs/MASTER_BRIEF_v2.2.md` — the single governing document. `docs/README.md` indexes every other doc.

**Running the trial:** start with `docs/OWNER_GUIDE_GB10_TRIAL.md` (plain English),
then `docs/RENTAL_START_HERE.md` (exact commands).

## Build order (do not reorder)

```
infrastructure  →  assured web verifier  →  verified-volume measurement  →  eligible SFT experiment
   (this repo)       (Stage 2A, §7)          (pilot/volume decision, §11)      (Stage 2B, §11)
```

Each stage is gated on the previous one's Definition-of-Done
(`docs/MASTER_BRIEF_v2.2.md` §8–§12). In particular: **no training, no
scoring, before the verifier it depends on exists and passes its own
assurance suite** (CLAUDE.md PRIME DIRECTIVE #1).

## Setup

Prerequisites: `git`, Python 3.11+, [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync          # installs runtime + dev (pytest, ruff) dependency groups
make test        # uv run pytest -q
make lint        # ruff check + ruff format --check
make format      # ruff format + ruff check --fix
make check       # lint + test — what CI runs
```

All of the above run on a plain machine — no GPU, no Linux, no Docker
required. `make serve-smoke`, `make train-smoke`, and `make bench` require
the ARM64 GB10 host and are **not** part of `make check`. See
`docs/EXECUTION_ENVIRONMENTS.md` for exactly what needs which hardware.

> `make` itself isn't installed on a stock Windows/Git-Bash setup. If it's
> missing, run the `uv run ...` command from the matching Makefile target
> directly — every target is a single `uv run`/`bash` line.

## Repository layout

```
libs/schemas/    typed DTOs + config/result models — the cross-service lingua franca
libs/common/     logging, ids, timestamps, the YAML config loader
libs/clients/    typed inter-service HTTP clients (filled as services exist)
configs/         non-secret policy YAML, each validated against a libs/schemas model
engine/          Spark-side engine: agents, verifier, dataset, train, gate, registry (v2.0 §4.2; built in Stage 2)
verifiers/       the assured verifier (Stage 2 — build order above)
benchmarks/      sealed hold-out benchmark + forgetting canaries
lab/             isolated-lab code (web workflow target/worker) — never imports Spark code
rental/          GB10 trial lifecycle: plan, orchestrate, docker runtime, telemetry, live tracker
detection_verifier/  bounded Sigma-subset detection verifier + assurance suite
fixtures/        verifier/workflow fixtures (detection, web train/dev/challenge)
containers/      pinned container image tags + PROVENANCE.md (vLLM, Unsloth NGC)
scripts/gb10/    GB10 serving: arg rendering, preflight, health checks (docs/GB10_SERVING.md)
scripts/bench/   serving-capacity benchmark harness (docs/BENCHMARK_HARNESS.md)
scripts/rental/  trial steps: preflight, measure, workload, export, image pins, docker setup
scripts/         train/reload smoke (smoke_train.py, smoke_reload.py), run_smoke.sh
tests/           unit / integration / assurance
docs/            the design docs and stage runbooks — read in the order CLAUDE.md gives
```

Config and result shapes are typed and validated, not ad hoc:
- `libs/schemas/config.py` — one pydantic model per `configs/*.yaml` file,
  loaded via `libs/common.load_yaml_config(path, Model)`. An unknown or
  out-of-range key fails loudly at load time (`ConfigError`), never silently.
- `libs/schemas/results.py` — `EvidenceRecord` and friends, so any
  benchmark/smoke-test number is traceable to a host
  (`HostEnvironment.WINDOWS_DEV` / `GB10_CLOUD` / `GB10_OWNED` / `LAB_LAPTOP`
  / `CI`) and an evidence kind (`LOCAL` / `MOCKED` / `HARDWARE`) — never a
  bare number in prose.

## Secrets

`.env` is git-ignored and never committed; `.env.example` holds placeholders
only. CI fails if a `.env` file is ever tracked. Non-secret policy goes in
`configs/*.yaml` (committed, validated); host-specific or sensitive values
(`HF_TOKEN`, DSNs, the WireGuard lab IP) go in `.env`. See
`docs/EXECUTION_ENVIRONMENTS.md`.

## Contributing / git workflow

See `GIT_WORKFLOW.md`. In short: feature branch → PR → **the human merges**,
never a direct push to `main`; no AI/Claude attribution anywhere; log any
constraint-driven "for now" decision in `DECISIONS_TO_REVISIT.md` plus a
`gh issue`.

## GB10 serving

`scripts/gb10_serve.sh` + `scripts/gb10/` render, preflight, start/stop, and
health-check a GB10 vLLM deployment; `containers/vllm-gb10/PROVENANCE.md`
records the current (2026-11-11) compatibility research behind the image
and flag choices, and is explicit about what's still unverified (notably:
GB10/sm_121 has no merged upstream vLLM support, and multi-LoRA on the FP8
MoE model is refused by default pending a real hardware correctness check).
See `docs/GB10_SERVING.md` to run it and `docs/PENDING_HARDWARE_CHECKS.md`
for exactly what a real session still needs to confirm.

## Benchmark harness

`scripts/bench/run_benchmark.py` measures the serving endpoint's
throughput/latency/capacity trade-offs (context length × concurrency ×
batching) against synthetic, seeded, non-sensitive workloads — **not** the
sealed cybersecurity capability benchmark (`benchmarks/sealed/`). Every
report is explicitly marked `harness_test` (ran against a controlled/mock
endpoint — proves the harness's own accounting/bounding/error-handling,
not GPU performance) or a real measurement; a recommended operating
configuration is only ever computed from real hardware results, and is
`pending` otherwise. See `docs/BENCHMARK_HARNESS.md`.

## Current status

Stage 0 → Stage 1. Offline preparation for the GB10 trial is complete and tested
(CPU only); the authorised trial on a rented Enverge GB10 is next. Owner decisions in
force: Qwen3-30B-A3B MoE only; 4-bit QLoRA training by default with bf16 as a measured
comparison. Everything that still needs real hardware is listed in
`docs/PENDING_HARDWARE_CHECKS.md`; temporary choices and their triggers are in
`DECISIONS_TO_REVISIT.md`.
