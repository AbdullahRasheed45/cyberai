#!/usr/bin/env bash
# Training-matrix cell without the serving phases: train -> persist -> fresh-process
# reload. Mirrors rental.plan.train_argv (same image login shell, PYTHONPATH import of
# this checkout, unbuffered logs, shared HF cache, HF_TOKEN passed by name only).
# UNEXECUTED on GB10 as shipped — awaits the authorised hardware session.
set -euo pipefail
: "${UNSLOTH_IMAGE:?set UNSLOTH_IMAGE to the pinned unsloth_image digest from the reviewed FREEZE}"
: "${SMOKE_REVISION:?set SMOKE_REVISION to the pinned trainable_base_commit}"
: "${SMOKE_OUT:?set SMOKE_OUT to a fresh runs/<RUN_ID> directory}"
mkdir -p "$SMOKE_OUT" runs/hf_cache
chmod 777 "$SMOKE_OUT" runs/hf_cache  # the image may run as a different uid
run(){ docker run --rm --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
        -e SMOKE_MODEL -e SMOKE_REVISION -e SMOKE_OUT -e SMOKE_ADAPTER_NAME -e RUN_ID \
        -e TRAIN_MODE -e PILOT_DATA -e TRAINING_CONFIG -e HF_TOKEN \
        -e TRAIN_MAX_SEQ_LENGTH -e TRAIN_MAX_STEPS -e TRAIN_BATCH_SIZE \
        -e TRAIN_GRAD_ACCUM -e TRAIN_MEASURE_WARMUP_STEPS -e PYTHONUNBUFFERED=1 \
        -v "$PWD:/work" -v "$PWD/runs/hf_cache:/hf-cache" -e HF_HOME=/hf-cache \
        -w /work "$UNSLOTH_IMAGE" bash -lc "export PYTHONPATH=/work\${PYTHONPATH:+:\$PYTHONPATH} && $1"; }
run "python scripts/smoke_train.py"
run "python scripts/smoke_reload.py"
echo "train/persist/reload/local-generate smoke complete (NETWORK SERVING is a separate check)."
