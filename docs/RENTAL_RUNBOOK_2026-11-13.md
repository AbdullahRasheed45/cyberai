# Current rental preparation and execution record

13 November 2026. This supersedes the execution status and commands in the
12 November readiness/handoff snapshots. The briefs remain architecture
references; v1.3 is a proposal. No GPU result has been produced.

## Current verdict

Offline validation: full suite 225 passed, 2 optional Torch-dependent skips.
After the final process-error handling changes, focused lifecycle/export checks
passed 30 tests. Lint, format and compilation passed. No tests were disabled.
Executed local reference evidence:
`artifacts/live_web_reference_complete_20261113.jsonl`, SHA256
`c5aca044b60dea2c6d025cde2e06a6668dd5ac371e4e1a2fbefabce74ea9f0c4`.
Exported five-example pilot SHA256:
`332d22fb25bdfe31942fdcedf6c737eb14999ab04c12066fffb09c79175568f2`.
Runtime fields make regenerated evidence bytes differ; retain each actual hash.
Raw artifacts remain local/ignored; commands reproduce the workflow. The narrow
target expansion is tracked in DECISIONS_TO_REVISIT.md R-005 / issue #14.

NOT READY to book the representative trial until actual machine access,
separate-lab rehearsal, export destination and runtime image pins are verified.
Offline code blockers addressed here do not establish those external facts.

Implemented: real loopback HTTP owned-account target; resettable SQLite audit;
response-versus-audit offensive verification; pre-satisfied and patched controls;
controller-only patch; blocked-cross-account plus valid-owner and health retest;
separate-process bounded JSON-lines interface; iterative Qwen client via SSH;
12-action limit, request/response timeouts and fail-loud verdicts; trajectory
export; actual API usage and monotonic timing. The target holds no model or
engine credentials. This is one narrow authorization scenario, not web mastery.

The target's controller and database share a lab process/filesystem trust
boundary. Response and audit are separate observation paths, not two physically
independent trust roots. There is no arbitrary code execution tool. A future
general-purpose target requires stronger process/network isolation.

## Before billing: development checks

From repository root, using the project environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe scripts/run_live_web_reference.py --out artifacts/live_reference.jsonl
.\.venv\Scripts\python.exe scripts/rental/make_pilot.py --domain web --trajectories artifacts/live_reference.jsonl --out artifacts/web_pilot.jsonl
.\.venv\Scripts\python.exe scripts/rental/check_preparation.py
```

Reference output paths must be new. Five records cover success, failed,
pre-satisfied, patched control and long-context success. The long context
contains 128 actually served benign owner requests exposed as application
activity, rather than repeated copies of an identical trace. This tests a noisy
context profile for one scenario; it does not establish multi-step attack-chain
diversity. Actual tokenizer lengths and consumed/truncated tokens are measured
by the GPU trainer. `--context-stress` explicitly opts into the older repetition
stress fixture; it is excluded by default.

Pilot selection accepts only development provenance and verified/remediated
records. Public challenge and future restricted acceptance scenarios are not
inputs. Reference scripts emit zero model tokens because no model executes.

## Separate lab setup, before billing

Use the owned isolated lab host, not the DGX engine. Copy/install only `lab/`
from the reviewed commit into its Python module path. Standard-library Python
is sufficient. Do not copy model caches, engine SSH private keys or acceptance
data. Configure a dedicated SSH account whose module path contains that package.
Configure engine SSH alias `cyberai-lab`, verify its host key independently, and
restrict connectivity to that lab host. Never disable SSH host-key checking.

Local lab assurance (from the checkout on that host):

```bash
python3 -m lab.web_workflow.worker --case success
```

The worker prints readiness. Send each JSON line, observing each response:

```json
{"kind":"discover"}
{"kind":"read_owner"}
{"kind":"read_other"}
{"kind":"finish"}
```

Expected final verdict: VERIFIED/REMEDIATED and task_success true. Repeat from
the engine with `ssh -T cyberai-lab python3 -m lab.web_workflow.worker`.
Actual SSH/two-machine rehearsal remains unexecuted here. The HTTP target binds
only lab loopback; the agent receives no direct network-address input. Worker
exit stops its server and removes its temporary database. SSH and provider
cleanup must still be verified on the actual machines.

## Engine configuration and image collection

DGX Spark/GB10 ARM64 is the serving/training host. Docker is unavailable on
this Windows development host; exact GPU-image dependency versions cannot be
honestly resolved here. Preserve the FILL template until actual image probes
produce the reviewed candidate freeze. Registry digests/model revisions are
already pinned; runtime compatibility is pending.

```bash
uv sync --frozen
uv pip install huggingface-hub
export LAB_SSH_HOST=cyberai-lab
export MODEL_PATH=/data/models/qwen3-fp8
export EVIDENCE_EXPORT_DIR=/mnt/durable/cyberai-trial
export RENTAL_STOP_UTC=REPLACE_WITH_ACTUAL_PROVIDER_DEADLINE
uname -m
nvidia-smi
# Pull both exact image digests from scripts/rental/FREEZE.yaml.
timeout 1800 uv run python scripts/rental/collect_image_pins.py
export FREEZE=artifacts/image_pin_collection/FREEZE.image-versions.yaml
# Review probe logs, CUDA/bf16 and lineage before proceeding.
uv run python scripts/rental/materialise_checkpoint.py
uv run python scripts/rental/check_preparation.py
```

Create the model/export directories on the intended storage first. The export
directory must be an existing durable mount outside the run directory. Verify
that it is actually off-instance, and read back a copied test bundle from an
independent machine. The copy helper verifies bytes, not physical durability.
`RENTAL_STOP_UTC` records the operator deadline; it does not stop provider billing.
Set a provider-side deadline/alarm and preserve a three-hour export reserve.

Transfer the verified development pilot to `data/web_pilot.jsonl` on the engine,
preserving its hash. Do not regenerate it from acceptance data.

## Bounded GPU lifecycle

```bash
export RUN_ID=trial_s2048_b1
export TRAIN_MODE=pilot PILOT_DATA=data/web_pilot.jsonl WORKLOAD_DOMAIN=web
export TRAIN_MAX_SEQ_LENGTH=2048 TRAIN_MAX_STEPS=30 TRAIN_BATCH_SIZE=1
export TRAIN_GRAD_ACCUM=1 TRAIN_MEASURE_WARMUP_STEPS=5
set -o pipefail
timeout 6h uv run python -m rental.orchestrate 2>&1 | tee artifacts/trial_s2048_b1.log
```

The web lifecycle now calls `46_live_web_workflow.py`; legacy `45` remains a
symbolic regression utility. Model failures are saved and return nonzero.
Exporter includes `workload_result.json`, live trajectories and the selected
FREEZE, then copies the hashed bundle to EVIDENCE_EXPORT_DIR with read-back
verification. Adapter files support inference/fresh-optimizer restart, not
faithful optimizer-state resumption. Never overwrite previous run IDs/bundles.

For a base-model behavior comparison, run the same live workflow while the base
endpoint is running, with SERVED_MODEL=qwen3 and a separate ARTIFACT_DIR, before
training. Save both records; development differences do not prove held-out gain.

## Prioritized 24-hour schedule

| Hours | Work and stop condition |
|---|---|
| 0–2 | GB10/ARM64, driver, storage, image probes, SSH lab and export checks. Stop early if required compatibility fails. |
| 2–5 | Base serving: loading/startup, single-request latency and aggregate throughput separately; base web workflow. |
| 5–11 | Train 2048/b1, 4096/b1, 8192/b1; 4096/b2 only with measured headroom. Fresh output per cell. |
| 11–15 | Save/fresh-process reload; deploy actual adapter; inspect real adapter effect and memory. |
| 15–19 | Same iterative live web task and controls, retaining all failures and model token usage. |
| 19–21 | One diagnosed rerun or sustained measurement. |
| 21–24 | Copy evidence/adapters, independent readback, stop containers, end rental, confirm billing stopped. |

Use 5 warm-up and 25 measured optimizer steps initially. Preserve observed token
lengths, truncation, non-padding/supervised tokens, synchronized seconds/step,
load overhead and host/CUDA memory. No hardware recommendation uses requested
max tokens as processed tokens. Include every run's dataset/config hash.

On interruption, inspect `docker ps` and stop the trial's serving/training
containers explicitly. Shell timeout does not terminate detached containers or
the provider instance. Never delete model caches/evidence to improvise cleanup.

## Purchase and learning gates

Required: actual GB10 serving; real MoE train/save/fresh reload; deployable
adapter; bounded live workflow; memory/storage headroom; complete copied evidence;
measured total cycle time acceptable to the owner's workload. Owner still needs
to choose acceptable round duration, dataset/context mix and throughput budget.
The default integration pin is non-thinking Instruct-2507: native reasoning and
the controlled model comparison remain unresolved requirements, not silently
waived. No fine-tuning gain, recurring improvement or six-domain capability is
established by this trial alone.

Remaining external facts: provider/access, physical lab availability and network
isolation, durable storage identity, deadline, actual image probes. Fresh sealed
acceptance data is required before learning/promotion claims; it is excluded
from this platform-purchase trial. Loop-B parking policy versus January target
remains an explicit owner policy question.
