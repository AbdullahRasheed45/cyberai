# Start here: 24-hour DGX Spark hardware trial

13 November 2026. Primary purpose: measure GB10 latency, tokens/sec,
context/concurrency limits, memory pressure and real training/save/reload speed
before purchasing hardware. A separate cyber lab is optional for this trial.
No command below provisions paid compute or authorises a purchase.

## 1. Which repository to clone

Use the existing repository and feature branch; `main` is intentionally minimal.
On the rented Linux ARM64 Spark, after connecting with the provider's SSH command:

```bash
git clone --branch stage-1/live-web-rental-readiness --single-branch https://github.com/AbdullahRasheed45/cyberai.git
cd cyberai
git status --short --branch
git rev-parse HEAD
```

Private repository access requires your existing GitHub credentials or an approved
deploy key. Do not place a token in a clone URL or terminal logs. Record the HEAD
SHA with your run evidence. Do not merge PRs to prepare the trial.

## 2. Confirm the rental host

```bash
uname -m
nvidia-smi
docker version
docker info
df -h
free -h
```

Require actual GB10/DGX Spark and `aarch64`, a working GPU-enabled Docker runtime,
and sufficient disk for serving FP8 weights, training weights, both images, shared
cache, adapters and evidence. Do not substitute another GPU as Spark evidence.
Check the provider's actual storage allowance before downloading. Setup/download
time may already be billable; arrange caches in advance if the provider permits.

Use the documented NGC/SM121 container path. Do not install host Torch to fix a
container failure. The Windows laptop's Docker installation is unrelated to
whether Docker/GPU passthrough works on this Linux rental.

## 3. Install the lightweight project environment

Use the provider's installed `uv`, or install it using its official instructions:
https://docs.astral.sh/uv/getting-started/installation/

```bash
uv sync --frozen
uv pip install huggingface-hub
mkdir -p artifacts data runs/hf_cache
uv run pytest -q
uv run ruff check .
```

These are CPU checks; they do not confirm CUDA/model compatibility.

## 4. Select the hardware-only workload and storage

```bash
export WORKLOAD_DOMAIN=detection
export TRAIN_MODE=pilot
export PILOT_DATA=data/platform_pilot.jsonl
uv run python scripts/rental/make_pilot.py --domain detection --out "$PILOT_DATA"
export MODEL_PATH=/data/models/qwen3-fp8
export EVIDENCE_EXPORT_DIR=/mnt/durable/cyberai-trial
export RENTAL_STOP_UTC='REPLACE_WITH_ACTUAL_FUTURE_ISO_UTC_DEADLINE'
```

Replace paths with actual locations and the deadline with e.g. a valid
`YYYY-MM-DDTHH:MM:SSZ` timestamp. Create/verify those directories. The export
destination must be durable storage outside the rental instance or an explicitly
mounted durable volume; a folder name alone cannot establish durability.

`detection` executes the existing model-to-rule integration smoke without SSH or
a target lab. The small detection pilot validates training plumbing and provides
a baseline timing result, not representative long-context cyber training or a
learning-gain claim. For representative data, transfer your prepared, verified
development trajectory JSONL and set PILOT_DATA to its repo-relative path.
Run a second profile with that data; report actual length/truncation statistics.
Never substitute repeated short rows as diverse trajectories.

## 5. Pull the exact image digests and resolve runtime versions

```bash
uv run python -c 'import subprocess,yaml; c=yaml.safe_load(open("scripts/rental/FREEZE.yaml")); [subprocess.run(["docker","pull",c[k]],check=True) for k in ("vllm_image","unsloth_image")]'
timeout 1800 uv run python scripts/rental/collect_image_pins.py
export FREEZE=artifacts/image_pin_collection/FREEZE.image-versions.yaml
```

Read both image logs and `probes.json`. Confirm CUDA, bf16 and required imports.
Review the generated freeze; never replace unresolved FILL values with guessed
versions. Image/driver incompatibility is a stop condition with saved evidence.
The template remains unchanged. All GPU compatibility is unexecuted as of this guide.

## 6. Download Qwen on the Spark

```bash
uv run python scripts/rental/materialise_checkpoint.py
```

This obtains the pinned serving snapshot into MODEL_PATH and writes a hash
manifest. Training obtains its pinned trainable base inside the Unsloth container.
Both training and fresh reload share `runs/hf_cache`, mounted at `/hf-cache` with
HF_HOME set. This avoids repeated downloads across matrix cells. The cache is
on the rental filesystem; it is not automatically durable beyond termination.

Current candidates are Qwen3-30B-A3B-Instruct-2507 MoE: official FP8 serving and
the lineage-matched Unsloth trainable base. Instruct-2507 is non-thinking. Native
reasoning and the planned model comparison remain requirements; do not claim
they were validated by this candidate alone.

```bash
uv run python scripts/rental/check_preparation.py
```

For WORKLOAD_DOMAIN=detection this does not require LAB_SSH_HOST. A successful
configuration report still requires actual GPU execution, not just file checks.

## 7. Execute the first bounded lifecycle

```bash
export RUN_ID=hardware_s2048_b1
export TRAIN_MAX_SEQ_LENGTH=2048 TRAIN_MAX_STEPS=30 TRAIN_BATCH_SIZE=1
export TRAIN_GRAD_ACCUM=1 TRAIN_MEASURE_WARMUP_STEPS=5
set -o pipefail
timeout 6h uv run python -m rental.orchestrate 2>&1 | tee artifacts/hardware_s2048_b1.log
```

This executes preflight, base serving/measurement, resource release, training,
save, fresh-process reload, adapter serving, detection integration smoke and
hashed evidence export. A failed model smoke is retained as a failure; it is
distinct from measured hardware speed. Preserve logs from failed phases.

Do not restart with the same RUN_ID. A timeout can leave containers running;
inspect `docker ps` before continuing. Never overlap serving and training merely
to save time on a shared-memory device.

## 8. Training matrix after the first path works

To avoid repeating serving for every cell, load the reviewed identities:

```bash
export UNSLOTH_IMAGE="$(uv run python -c 'import os,yaml; print(yaml.safe_load(open(os.environ["FREEZE"]))["unsloth_image"])')"
export SMOKE_MODEL="$(uv run python -c 'import os,yaml; print(yaml.safe_load(open(os.environ["FREEZE"]))["trainable_base_repo"])')"
export SMOKE_REVISION="$(uv run python -c 'import os,yaml; print(yaml.safe_load(open(os.environ["FREEZE"]))["trainable_base_commit"])')"
export RUN_ID=training_s4096_b1
export SMOKE_OUT=runs/training_s4096_b1
export TRAIN_MAX_SEQ_LENGTH=4096 TRAIN_BATCH_SIZE=1
bash scripts/run_smoke.sh
```

Keep TRAIN_MODE, PILOT_DATA, steps/accumulation/warm-up set from above. Then use a
new RUN_ID/SMOKE_OUT for 8192/b1. Try 4096/b2 only with measured memory headroom.
Use actual long development trajectories for those cells; configured max length
does not create long input. Copy these additional run directories before teardown.

## 9. Measurements and 24-hour priorities

| Hours | Priority |
|---|---|
| 0–2 | Host, images, storage and download/probe setup; stop early on incompatibility |
| 2–5 | Base latency, actual tokens/sec, context/concurrency and sampled memory |
| 5–11 | Training matrix, actual tokens, synchronized step times, save/fresh reload |
| 11–15 | Real adapter deployment and repeatable output checks |
| 15–19 | Representative data/model behavior comparison; optional lab only if already rehearsed |
| 19–21 | One diagnosed rerun; preserve results of failures |
| 21–24 | Export, independent readback, cleanup and provider termination |

Run inference measurements on the Spark itself so internet latency is excluded.
Separate single-request latency from aggregate throughput. Context/concurrency
curves reveal bandwidth-sensitive workload behavior; tokens/sec is not a direct
measurement of DRAM bandwidth. Direct bandwidth testing/profiling is a separate
measurement and is not implemented by the current token-rate harness.

Include loading/compilation overhead and actual processed training tokens;
record unavailable memory telemetry honestly. Decide acceptable training-round
duration against your intended data/context mix, not a guessed speed target.

## 10. Export and stop billing

Check export_result.json and receipt.json in the per-run artifact directory.
The bundle copy verifies destination bytes; also verify access from outside the
rental. Copy extra matrix outputs, console logs and selected freeze/probe logs.
Save the trained adapter and dataset hash. Keep SSH keys/secrets out of bundles.

Inspect `docker ps`; stop only this trial's containers. Terminate the instance
through the provider and confirm billing stopped. `timeout` and RENTAL_STOP_UTC
do not terminate the provider instance. Preserve the final three hours for this.

For the optional isolated Windows-laptop lab, follow
`RENTAL_RUNBOOK_2026-11-13.md`; set WORKLOAD_DOMAIN=web and LAB_SSH_HOST only after
the VM/SSH workflow is rehearsed. Lab readiness does not block the hardware-only scope.
