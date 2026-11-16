#!/usr/bin/env bash
# Host-level preflight for GB10 serving. Run this directly on the GB10 host
# (NOT inside the vLLM container) before `gb10_serve.sh start`.
#
# Each check fails loud with a specific message (CLAUDE.md directive #6) —
# this script never silently continues past a failed check. It writes a
# plain-text log to stdout; wrap it with `tee` to keep a copy for the
# evidence bundle (gb10_serve.sh diagnose does this automatically).
set -euo pipefail

FAIL=0
note() { echo "[preflight] $*"; }
fail() {
    echo "[preflight] FAIL: $*" >&2
    FAIL=1
}

note "=== architecture ==="
ARCH="$(uname -m)"
note "uname -m: $ARCH"
if [[ "$ARCH" != "aarch64" ]]; then
    fail "expected aarch64 (GB10/ARM64), got '$ARCH'. This is not a GB10 host — do not proceed."
fi

note "=== GPU visibility (nvidia-smi) ==="
if ! command -v nvidia-smi >/dev/null 2>&1; then
    fail "nvidia-smi not found. No NVIDIA driver visible to this host/container."
else
    if ! SMI_OUT="$(nvidia-smi --query-gpu=name,compute_cap,memory.total,memory.free --format=csv,noheader 2>&1)"; then
        fail "nvidia-smi ran but failed: $SMI_OUT"
    else
        note "nvidia-smi: $SMI_OUT"
        if ! echo "$SMI_OUT" | grep -qiE 'GB10|Spark|12\.1'; then
            note "WARNING: GPU name/compute_cap does not obviously say GB10/12.1 — double-check this is the right host."
        fi
    fi
fi

note "=== CUDA driver / docker GPU passthrough ==="
if command -v docker >/dev/null 2>&1; then
    if docker info 2>/dev/null | grep -qi nvidia; then
        note "docker info reports an nvidia runtime."
    else
        note "WARNING: docker info does not obviously list an nvidia runtime — '--gpus all' may still work on recent Docker, but verify."
    fi
else
    fail "docker not found on this host."
fi

note "=== system memory (GB10's 128GB is a UNIFIED CPU+GPU pool) ==="
if [[ -r /proc/meminfo ]]; then
    MEM_TOTAL_KB="$(awk '/MemTotal/ {print $2}' /proc/meminfo)"
    MEM_AVAIL_KB="$(awk '/MemAvailable/ {print $2}' /proc/meminfo)"
    note "MemTotal: $((MEM_TOTAL_KB / 1024 / 1024)) GiB, MemAvailable: $((MEM_AVAIL_KB / 1024 / 1024)) GiB"
    if [[ "$MEM_AVAIL_KB" -lt $((20 * 1024 * 1024)) ]]; then
        fail "less than 20 GiB available — insufficient for a 30B-A3B FP8 load plus KV cache. Free memory first."
    fi
else
    note "WARNING: /proc/meminfo not readable; cannot check available memory."
fi

note "=== model cache dir ==="
CACHE_DIR="${HF_HOME:-$HOME/.cache/huggingface}"
note "HF cache dir: $CACHE_DIR"
mkdir -p "$CACHE_DIR" 2>/dev/null || fail "cannot create/access model cache dir: $CACHE_DIR"
AVAIL_GB="$(df -Pk "$CACHE_DIR" | awk 'NR==2 {print int($4/1024/1024)}')"
note "free space at cache dir: ${AVAIL_GB:-unknown} GiB"
if [[ -n "${AVAIL_GB:-}" ]] && [[ "$AVAIL_GB" -lt 40 ]]; then
    fail "less than 40 GiB free at $CACHE_DIR — not enough room for the FP8 model weights."
fi

note "=== HF_TOKEN (optional for these public models, but checked) ==="
if [[ -z "${HF_TOKEN:-}" ]]; then
    note "WARNING: HF_TOKEN is unset. Both configured models are public (no gating found as of 2026-11-11 — see containers/vllm-gb10/PROVENANCE.md), so this is not fatal, but downloads may be rate-limited without it."
else
    note "HF_TOKEN is set (value not logged)."
fi

note "=== image reference ==="
IMAGE_FILE="$(dirname "$0")/../../containers/vllm-gb10/IMAGE.txt"
if [[ -r "$IMAGE_FILE" ]]; then
    IMAGE="$(grep -v '^#' "$IMAGE_FILE" | head -1 | xargs)"
    note "pinned image: $IMAGE"
else
    fail "cannot read $IMAGE_FILE"
fi

if [[ "$FAIL" -ne 0 ]]; then
    echo "[preflight] one or more checks FAILED — do not start the server. See messages above." >&2
    exit 1
fi
note "all host-level checks passed. Run 'scripts/gb10_serve.sh preflight-container' next."
