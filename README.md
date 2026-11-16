# cyberai

Autonomous, self-improving cybersecurity AI — Stage 0/1 foundation.

**Read `CLAUDE.md` first.** It is the operating contract for this repo
(prime directives, stage order, git/PR discipline) and takes precedence over
anything below. This README is a quick-start for humans; `CLAUDE.md` and
`docs/` are authoritative.

## What this is, right now

Stage 0 scaffolding + Stage 1 foundation: typed config/result schemas,
validation, tooling, and governance docs. It does **not** yet include a
running verifier, a learning engine, or a served model — see
`docs/ARCHITECTURE.md` for what gets built in which stage.

## Build order (do not reorder)

```
infrastructure  →  assured web verifier  →  verified-volume measurement  →  eligible SFT experiment
   (this repo)       (Stage 2, brief §6)      (Stage 1.5 gate, §7.8)          (Stage 2 proof, §17)
```

Each stage is gated on the previous one's Definition-of-Done
(`docs/SONNET_COMPLETE_BUILD_PLAN.md`). In particular: **no training, no
scoring, before the verifier it depends on exists and passes its own
assurance suite** (CLAUDE.md PRIME DIRECTIVE #1).

## Setup

Prerequisites: `git`, Python 3.11+, [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync          # installs runtime + dev (ruff) dependency groups
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
services/        per-service api/domain/infra skeletons (docs/ARCHITECTURE.md)
verifiers/       the assured verifier (Stage 2 — build order above)
benchmarks/      sealed hold-out benchmark + forgetting canaries
lab/             isolated-lab code (targets, state machine) — never imports Spark code
containers/      pinned container image tags (vLLM, Unsloth NGC)
scripts/         GB10-session scripts (serving smoke test, train smoke test, benchmarks)
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

## Current status

Stage 0 → Stage 1 foundation (no GB10/lab hardware touched by this work —
see the PR's "Hardware evidence" section and
`DECISIONS_TO_REVISIT.md` for what that implies and what to do once a GB10
session / lab laptop is available).
