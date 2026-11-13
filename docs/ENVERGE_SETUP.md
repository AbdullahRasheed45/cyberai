# Enverge: two execution paths and download budget

For measured execution and saved console/telemetry logs on either path, use the
command wrapper in `MEASUREMENTS_AND_TRACKING.md`.

13 November 2026. Read `RENTAL_START_HERE.md` for the shared workload, export and
shutdown steps. This provider-specific supplement takes precedence on access.

## Provider facts and limits

Enverge's operational docs describe Linux rentals as containers reached over an
SSH relay, despite bare-metal language on the Spark marketing page. Custom GPU
Docker execution is not established by that marketing. Storage is ephemeral;
copy results before deleting the instance. Only deletion stops metered billing.
Actual portal pricing applies; the landing page currently advertises $0.85/hour
for one Spark, so 24 hours would be $20.40 before tax at that rate.

Sources checked 13 November:
- https://enverge.ai/docs/instances
- https://enverge.ai/docs/billing
- https://enverge.ai/terms
- https://spark.enverge.ai/

## First commands after connecting

Clone the reviewed feature branch as in RENTAL_START_HERE.md. Then, using the
provider's existing GPU-enabled Python interpreter:

```bash
python3 scripts/rental/provider_probe.py --out artifacts/enverge_initial_probe.json
```

This standard-library entrypoint needs no project installation. It inventories
architecture, driver, Docker daemon and existing package/CUDA/FastModel execution.
It downloads no weights and installs nothing. It has bounded subprocess timeouts.
Review its JSON; status INVENTORY_ONLY_REVIEW_REQUIRED is not an acceptance pass.
No Docker daemon or missing existing libraries is recorded, not silently repaired.

## A: custom GPU Docker works

Use the existing pinned-image route in RENTAL_START_HERE.md. `docker info` alone
does not prove GPU access or usable volume mounts. Pull the exact images and run
collect_image_pins.py: its actual GPU probes must succeed. Confirm the host path
mounted at /work contains this checkout. With a host-mounted daemon, paths may
refer to the provider host rather than your SSH container; do not assume identical
paths. Verify the repository mount before training.

Once image probes, snapshot/configuration and export checks pass, run the bounded
`python -m rental.orchestrate` lifecycle. Use WORKLOAD_DOMAIN=detection for the
lab-free hardware trial. Run the longer matrix only after the first path succeeds.

## B: no Docker daemon, use only an already compatible provider GPU environment

This path does not launch nested containers. It uses Enverge's installed GPU
stack only if the inventory establishes aarch64, GB10 capability 12.1, CUDA bf16
arithmetic and the required imports. `existing_environment_blockers` must be empty.
Also review package versions, provider image identity and provenance against the
known-good SM121/FastModel recipe in BRIEF_v1.2_CORRECTIONS_AND_SETUP.md.
An empty blocker list checks interfaces/basic CUDA, not optimized MoE kernels.

If the required environment is absent or incompatible, neither runnable Docker
nor a verified existing stack is available. Save the report and end the trial
early. Do not install arbitrary Torch/vLLM/Unsloth versions on ARM64 or describe
this as a supported fallback. This failure cannot be fixed offline without
access to the actual provider environment.

For an admitted existing environment, preserve its Python interpreter and packages.
Do not `uv sync` and accidentally switch to a venv without its CUDA libraries.
Set the repo import path and an explicit cache:

```bash
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
export HF_HOME="$PWD/runs/hf_cache"
mkdir -p artifacts data runs/hf_cache
export MODEL_PATH=/path/to/actual/model-storage/qwen3-fp8
python3 scripts/rental/materialise_checkpoint.py
```

The snapshot tool needs the already-probed yaml/huggingface_hub libraries. The
source FREEZE template supplies pinned model identities for downloading; its FILL
dependency values remain unresolved and must not be labelled an accepted freeze.
Retain the provider inventory as the actual native-runtime version evidence.

Start serving in a separate SSH terminal using the existing environment:

```bash
vllm serve "$MODEL_PATH" --served-model-name qwen3 --host 127.0.0.1 --port 8000 --gpu-memory-utilization 0.85 --max-model-len 32768 --enable-prefix-caching --enable-chunked-prefill
```

Capture the terminal's startup/error log. After /health and /v1/models confirm
readiness and qwen3 identity, measure locally from another SSH terminal:

```bash
export VLLM_URL=http://127.0.0.1:8000/v1/chat/completions
export SERVED_MODEL=qwen3 ARTIFACT_DIR=artifacts/enverge_native_base
python3 scripts/rental/20_measure_inference.py
```

Stop the serving process and verify memory release before training. Prepare data
using make_pilot.py as in the main guide, set TRAIN_MODE=pilot and PILOT_DATA to
that repo-relative file. Read the training repo/commit from the checked-in freeze;
do not substitute the FP8 snapshot as the trainable BF16 base:

```bash
export SMOKE_MODEL=unsloth/Qwen3-30B-A3B-Instruct-2507
export SMOKE_REVISION=41d47883cd854ab6d119fb7cba6e9ed3511886e2
export RUN_ID=enverge_native_s2048_b1 SMOKE_OUT=runs/enverge_native_s2048_b1
export TRAIN_MAX_SEQ_LENGTH=2048 TRAIN_MAX_STEPS=30 TRAIN_BATCH_SIZE=1
export TRAIN_GRAD_ACCUM=1 TRAIN_MEASURE_WARMUP_STEPS=5
python3 scripts/smoke_train.py
python3 scripts/smoke_reload.py
```

Run reload only after training succeeds. These are fresh processes using FastModel
and frozen-router checks; no bare-metal framework installation is prescribed.
For adapter serving, start the same server command with `--enable-lora
--lora-modules smoke=runs/enverge_native_s2048_b1/adapter`, then verify smoke in
/v1/models and run 40_workload.py with SERVED_MODEL=smoke, WORKLOAD_DOMAIN=detection
and a fresh ARTIFACT_DIR. A model smoke failure is retained as a failure.

This existing-environment path is manual and is not wired to the Docker
orchestrator or its completeness manifest. Export the full artifacts/run output,
provider inventory, dataset hash, source commit and environment identity manually,
verify copied bytes and retain a list of files. Do not generate synthetic
preflight/orchestration records to make the Docker exporter pass.

## Download timing

Pinned Hub snapshot metadata checked 13 November:
- FP8 serving snapshot: 31,195,094,809 bytes (31.2 decimal GB).
- BF16 training snapshot: 61,084,174,447 bytes (61.1 decimal GB).
- Combined: 92,279,269,256 bytes (92.3 decimal GB).

These sizes are downloaded bytes of the declared snapshots, not runtime memory.
Sources: pinned Hugging Face API revisions recorded in scripts/rental/FREEZE.yaml.

| Effective sustained download rate | FP8 | BF16 | Both |
|---|---|---|---|
| 100 Mbps (12.5 MB/s) | 42 min | 81 min | 123 min |
| 500 Mbps (62.5 MB/s) | 8 min | 16 min | 25 min |
| 1 Gbps (125 MB/s) | 4 min | 8 min | 12 min |

These are transfer-only estimates, not provider measurements. Authentication,
Hub throttling, contention, file hashing, retries and Docker-image downloads add
time. The provider's advertised link speed is not guaranteed Hub throughput.
Record actual elapsed downloads. Serving weights download before serving; training
weights may otherwise first download when training starts. A warm existing cache
can reduce this time, but must be checked against the exact model revision.

## What running scripts means

There is no honest unconditional one-click script for an uninspected provider.
Sequence: connect -> inventory -> choose compatible execution path -> download
and verify weights -> serve/measure -> stop serving -> train/save/reload -> deploy
adapter -> export/readback -> delete provider instance. Path A automates most of
the lifecycle after reviewed setup; path B supplies explicit existing-environment
commands and preserves failures without pretending Docker worked.
