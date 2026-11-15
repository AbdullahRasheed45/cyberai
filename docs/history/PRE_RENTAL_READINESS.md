# Pre-rental readiness — 12 November 2026

> Historical snapshot. Current status, repaired live workflow/export wiring and
> exact commands: [13 November runbook](RENTAL_RUNBOOK_2026-11-13.md).
> v1.2 is now present. Later commands use the real HTTP lab, not the symbolic runner.

**NOT READY for the full offensive/defensive product purchase trial.** The source-archive blocker is resolved: Round 18 is now integrated and repaired on `stage-1/round18-rental-integration`, preserving the earlier serving fixes. See `ROUND18_INTEGRATION.md` for source hashes, defect dispositions and evidence limits. This is a concrete preparation update, not a new architecture.

## Remaining blockers before booking

1. A separate owned target lab has not been demonstrated available, isolated, resettable and accessible. The available web workflow evaluates detection rules on fixtures; it does not implement the offensive environment outcome → defensive action → independent retest path. Either prepare that lab/workflow or explicitly narrow the trial to platform/adapter integration; this report does not make that scope decision for the owner.
2. There are no representative independently verified offensive/defensive trajectories. The web pilot export contains three public-fixture detection examples sharing a target rule. They are plumbing data, not a representative training corpus or learning-gain evidence. Supply verified trajectory/data profiles before using the matrix to forecast production cadence.
3. Exact dependency versions inside the two candidate GPU images are still `FILL` in FREEZE.yaml. The runtime collector and fail-closed gate exist. Inspect/cache image assets and collect versions before billing where infrastructure allows; accelerator compatibility and performance must be checked during the authorised GB10 session. Never insert CPU-host versions to pass the gate.
4. Owner must identify the actual rental access, storage capacity and durable export destination, acceptable training-round duration, dataset size/context mix and provider teardown/billing deadline. Local archive verification is implemented; an off-instance copy/receipt is not configured or demonstrated.

Fresh restricted acceptance data/runner remain absent. Those are excluded from purchase and learning-gain claims, rather than calling the public challenge an acceptance set. The SQLite ledger does not by itself enforce all possible direct-scoring access. All six original Round-18 defects have specific repairs or exclusions in ROUND18_INTEGRATION.md.

## Before billing starts

Prepare the separate target lab; define workload/purchase criteria; import real verified train/dev trajectories; retain public challenge fixtures as regression only; select a durable export destination and verify a small copy/restore receipt; freeze this code commit and review model/image identities; arrange caches and storage. Do not run Docker/GPU commands on a target lab holding untrusted targets or model credentials.

On the development machine, from repo root:

```bash
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
mkdir -p data
uv run python scripts/rental/make_pilot.py --domain web --out data/web_pilot.jsonl
# This must ABORT while dependency pins remain unresolved; it is not a dry-run pass:
uv run python -m rental.orchestrate
```

The JSONL export refuses to overwrite an existing file. The emitted examples remain labelled public fixture plumbing. The native-reasoning Qwen3 family and model comparison remain product requirements; the pinned Instruct-2507 integration candidate does not silently settle that choice.

## Setup/GB10-only commands after explicit authorisation

Run on the actual Linux ARM64 GB10 engine, never as evidence on an unrelated GPU. Install project plus snapshot helper on the engine host. Do not install host Torch as a substitute for the frozen CUDA containers.

```bash
uv sync --frozen
uv pip install huggingface-hub
mkdir -p artifacts
set -o pipefail
# Record hardware/driver first; confirm GB10 and aarch64:
uname -m
nvidia-smi
# Pull both exact image digests from scripts/rental/FREEZE.yaml; retain logs.
# After pulls, collect actual per-image versions/CUDA/bf16:
timeout 1800 uv run python scripts/rental/collect_image_pins.py
```

Review `artifacts/image_pin_collection/FREEZE.image-versions.yaml`, its per-image logs and model-lineage evidence before using it. Copy that reviewed candidate to a run-specific freeze and preserve it; do not overwrite the source template to conceal a failed image. Materialise the serving snapshot using the chosen freeze:

```bash
export FREEZE=artifacts/image_pin_collection/FREEZE.image-versions.yaml
export MODEL_PATH=/path/on/engine/model-cache/qwen3-fp8
uv run python scripts/rental/materialise_checkpoint.py
```

`materialise_checkpoint.py` requires MODEL_PATH and creates/checks the exact snapshot manifest; allow sufficient model storage/download time. `/path/on/engine/...` must be replaced with an actual prepared persistent/cache location. No accessible engine path is known today.

Once runtime pins, snapshots and review are complete, run a bounded pilot lifecycle with explicit training mode:

```bash
export RUN_ID=trial_seq2048_b1
export TRAIN_MODE=pilot PILOT_DATA=data/web_pilot.jsonl WORKLOAD_DOMAIN=web
export TRAIN_MAX_SEQ_LENGTH=2048 TRAIN_MAX_STEPS=30 TRAIN_BATCH_SIZE=1
export TRAIN_GRAD_ACCUM=1 TRAIN_MEASURE_WARMUP_STEPS=5
# MODEL_PATH/FREEZE remain set. Do not set ADAPTER_PATH; it is derived from RUN_ID.
timeout 6h uv run python -m rental.orchestrate 2>&1 | tee artifacts/trial_seq2048_b1.log
```

The lifecycle serves/measures base, stops it, trains/saves, starts a fresh reload process, deploys the actual saved adapter, executes the web fixture smoke, and creates an archive with hashes. All real GPU phases remain UNEXECUTED. FP8-MoE LoRA may fail despite correct lineage; that is required evidence, not a configuration flag to wave through. A successful fixture smoke is not the separate offensive/defensive lab workflow.

A shell timeout does not guarantee detached Docker cleanup or stop provider billing. Independently schedule a provider deadline and retain export reserve. On timeout/interruption, explicitly inspect/stop serving containers and any active training container, preserve logs and export before terminating the rental. Verify provider billing stopped. Do not delete/reuse failed run output; choose a new RUN_ID.

## Prioritized workload and measurement

Training matrix: 2048 × batch1 first, then 4096 × batch1, then 8192 × batch1; try 4096 × batch2 only if measured headroom and remaining budget permit. Use fresh RUN_ID per trial and the same frozen data/config except the tested dimension. Do not repeat the whole serve/eval lifecycle unnecessarily for every training cell: the documented `scripts/run_smoke.sh` can run train/save/fresh-reload with explicit UNSLOTH_IMAGE, SMOKE_MODEL, SMOKE_REVISION and SMOKE_OUT from the reviewed freeze.

Use 5 measurement-warm-up + 25 measured optimizer steps initially. This is a provisional timing budget, not evidence of representative learning. Log actual consumed non-padding/supervised tokens (including repeated microbatches), sequence histogram, accumulation, completed steps, per-step synchronized durations, warm-up-excluded seconds/step and token rate, model-load time, allocated/reserved CUDA peaks and host memory/headroom. Never multiply requested max sequence length by steps and call it actual tokens. Padding/truncation and short fixture examples must be disclosed.

Inference harness separates TTFT/decode estimates and request latency from actual successful output tokens over batch wall time. It records failed requests and sampled device memory; unavailable memory remains unavailable. Record serving startup/load/compilation from container logs and outer monotonic durations separately; a warm server measurement does not measure loading overhead. The harness is not direct kernel-prefill instrumentation or a thermal profiler.

## Conditional 24-hour schedule

| Hours | Priority and stop condition |
|---|---|
| 0–2 | Confirm hardware/driver/storage, frozen assets and full entrypoints. Wrong host/incompatible stack: export and end session. |
| 2–5 | Baseline serve; measure startup separately, then bounded context/concurrency/warm-cache matrix and memory. Stop serving and verify release. |
| 5–11 | Representative training matrix, actual tokens/step durations, save and fresh reload. Stop on OOM and preserve evidence. |
| 11–15 | Deploy the real trained MoE adapter, verify identity/output correctness and adapter effect. |
| 15–19 | Prepared separate-lab complete workflow, or explicitly owner-approved platform-only scope. Do not substitute a detection fixture score for an offensive workflow. |
| 19–21 | One diagnosed rerun or sustained measurement; no broad tuning sweep. |
| 21–24 | Export all successes/failures/configs/adapter/data hashes; verify off-instance copy and restore/receipt; stop containers and terminate rental; confirm billing stopped. |

## Purchase criteria and evidence

Require actual GB10 serving, representative train/save/fresh-reload, real adapter deployment and correct output, measured memory/storage headroom, and verified off-instance evidence export. Full product trial also requires the prepared offensive/defensive lab workflow. Compare total measured cycle time including load/compilation/eval/export to the owner's accepted workload/cadence. Missing/failed required results prevent a positive recommendation. Do not infer six-domain mastery, recurring weight improvement or held-out gain from platform smokes.

Offline evidence: combined suite 201 passed, 2 skipped (Torch-dependent CPU checks unavailable); web export emits three examples; unresolved freeze aborts before Docker; lint/format and compilation checked. No GB10, training, adapter-deployment or separate-lab runtime check has been executed here. Bash lifecycle execution remains unverified on this Windows host.
# Authorised offensive web workflow (offline evidence)

The development slice in `lab/web_workflow/` is the smallest complete
offensive-first workflow. It is a symbolic, resettable owned-lab scenario only:
it cannot contact a host, execute a command, accept a URL, or accept arbitrary
payloads. It connects a bounded action interface, independent primary/shadow
offensive verifiers, telemetry, defensive patch plus independent retest, and
append-only provenance-tagged JSONL evidence.

Run its offline evidence suite before rental:

```powershell
.\.venv\Scripts\python.exe scripts\run_web_reference_workflow.py --case all --out artifacts\web_reference_evidence.jsonl
.\.venv\Scripts\python.exe -m pytest tests\test_offensive_web_workflow.py -q
```

Expected offline cases are `VERIFIED` then `REMEDIATED` (success),
`NOT_VERIFIED` (failed), `UNVERIFIABLE_PRE_SATISFIED`, and `ALREADY_PATCHED`.
Only the verified-and-remediated scripted reference record is eligible for the
development pilot; none is acceptance data. `configs/six_domain_curriculum.yaml`
retains the six-domain easy-to-hard inventory and resource-aware schedule; only
the web reference is implemented.

The GPU-only runner is deliberately separate. After adapter deployment, the
web `WORKLOAD_DOMAIN` invokes `scripts/rental/45_web_offensive_workflow.py`.
It asks Qwen for a strict JSON action plan, rejects any plan outside the owned
scenario, and records task success, API-reported prompt/completion tokens,
action count, monotonic runtime, and failure category in
`artifacts/run_<RUN_ID>/web_offensive_workflow_result.json`. It does not prove
GPU compatibility, model quality, or model-weight improvement until run on the
rented machine.
