#!/usr/bin/env bash
# UNEXECUTED on GB10 as shipped — awaits integration validation on supported compute.
# Two SEPARATE processes; each reload step keeps ONE base resident.
set -euo pipefail
: "${UNSLOTH_IMAGE:?set UNSLOTH_IMAGE to the pinned NGC Unsloth image (see containers/unsloth-ngc/IMAGE.txt.example)}"
: "${SMOKE_REVISION:?set SMOKE_REVISION to the pinned model/tokenizer commit}"
run(){ docker run --rm --gpus all --ipc=host \
        -e SMOKE_MODEL -e SMOKE_REVISION -e SMOKE_OUT -e SMOKE_ADAPTER_NAME -e RUN_ID \
        -e TRAIN_MODE -e PILOT_DATA \
        -e TRAIN_MAX_SEQ_LENGTH -e TRAIN_MAX_STEPS -e TRAIN_BATCH_SIZE \
        -e TRAIN_GRAD_ACCUM -e TRAIN_MEASURE_WARMUP_STEPS \
        -v "$PWD:/work" -w /work "$UNSLOTH_IMAGE" bash -lc "$1"; }
run "python scripts/smoke_train.py"
run "python scripts/smoke_reload.py"
echo "train/persist/reload/local-generate smoke complete (NETWORK SERVING is a separate check)."
