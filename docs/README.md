# docs/ — what each file is

The single governing document is **`MASTER_BRIEF_v2.2.md`**. Everything else here is either an
operational runbook for the GB10 trial or a focused reference. Superseded briefs and dated
snapshots live in `history/` (kept for provenance; v2.2 supersedes their conflicting task contracts).

## Current remediation evidence

- `REVIEW_FIX_LEDGER_2026-11-16.md`: all 29 findings and six follow-up defects,
  separating tested code from future specifications and open decisions.
- `HANDOFF_2026-11-16.md`: actual offline results and unexecuted machine checks.
- `CLAUDE_HANDOFF_PROMPT_2026-11-16.md`: owner-voice prompt for the next session.
- `MASTER_BRIEF_v2.1.md` and `history/MASTER_BRIEF_v2.0.md`: preserved prior versions.

## Start here

| File | What it is |
|---|---|
| **`MASTER_BRIEF_v2.2.md`** | **The whole project in one file.** Part A: system design, the twelve rules, data contracts, the cheat-proof verifier specification. Part B: every in-scope stage as an ordered list of numbered tasks, each naming the files, behaviour, tests and the command that proves it done. A coding agent builds the project by working through it. Read this first. |
| `diagram-master-comprehensive.drawio` | The system in one picture (open in draw.io). |

## The GB10 trial (Stage 1A — built, tested offline, not yet run)

| File | What it is |
|---|---|
| `OWNER_GUIDE_GB10_TRIAL.md` | The trial in plain English: purpose, what happens, the pre-booking checklist, the day-of steps, and how to read each result file. Read this before the trial. |
| `RENTAL_START_HERE.md` | The exact commands for the trial, step by step, with the lifecycle knobs and what to watch. |
| `ENVERGE_SETUP.md` | Provider specifics: the sandboxed Docker-in-Docker container, why `--gpus all` fails there, and the measured-flags setup. |
| `MEASUREMENTS_AND_TRACKING.md` | The live tracker and the command wrapper; the GB10 unified-memory note; what every measurement means. |
| `RENTAL_RUNBOOK_2026-11-13.md` | The current rental preparation and execution record (validation counts, evidence hashes, remaining external gates). |

## Hardware and serving reference

| File | What it is |
|---|---|
| `PENDING_HARDWARE_CHECKS.md` | Every claim that still needs real-GPU evidence, each mapped to the command that produces it. Ticked off during and after the trial. |
| `GB10_SERVING.md` | How to operate `scripts/gb10_serve.sh` and the GB10 serving helpers. |
| `BENCHMARK_HARNESS.md` | How to run the serving-capacity benchmark (`scripts/bench/run_benchmark.py`). |
| `EXECUTION_ENVIRONMENTS.md` | Which of the three machines (Windows dev, GB10 engine, lab laptop) may run what — the machine-isolation safety boundary. |

## Elsewhere in the repo

`DECISIONS_TO_REVISIT.md` (repo root) — every constraint-driven "for now" choice with its trigger and GitHub issue. `CLAUDE.md` / `AGENTS.md` (repo root) — the operating contract and owner context. `containers/vllm-gb10/PROVENANCE.md` — the evidence behind the pinned image and flag choices. `historical_evidence/` — the model-lineage evidence the freeze file cites.

## `history/` — superseded, kept for provenance

These were the path to v2.0; v2.0 folds in everything in them that still holds.

| File | What it was |
|---|---|
| `MASTER_PROJECT_BRIEF_v1.1.md` | The first consolidated design (three critique rounds). The origin of most decisions. |
| `MASTER_PROJECT_BRIEF_v1.2_FOR_CRITIQUE.md` | v1.1 condensed, with the verified GB10 setup. |
| `MASTER_PROJECT_BRIEF_v1.3.md` | Added the six-domain curriculum and offensive foregrounding. |
| `MASTER_PROJECT_BRIEF_v1.5.md` | Added the one-Spark recipe (Part II) and the stage-by-stage plan (Part III). v2.0's direct parent. |
| `BRIEF_v1.2_CORRECTIONS_AND_SETUP.md` | The known-good GB10 container/setup appendix (historical setup reference). |
| `ARCHITECTURE.md` | The original service-by-service code structure (the 16-network-service design C-2 proposes replacing, pending R-011/D-8 approval, with one application; useful as the detailed component reference). |
| `SONNET_COMPLETE_BUILD_PLAN.md` | The original all-stages build plan with definitions of done (historical build plan). |
| `STAGE_0_AND_1_EXACT.md` | The original line-by-line Stage 0/1 runbook (now the trial runbooks above). |
| `PRODUCT_ALIGNMENT_AND_SIX_DOMAIN_CURRICULUM.md`, `CURRENT_PRODUCT_SPEC.md` | The owner's product-direction notes v2.0 consolidates. |
| `CODEX_PROJECT_HANDOFF_2026-11-12.md`, `PRE_RENTAL_READINESS.md`, `ROUND18_INTEGRATION.md` | Dated handoff and readiness snapshots. |
