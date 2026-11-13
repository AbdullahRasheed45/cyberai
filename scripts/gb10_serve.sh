#!/usr/bin/env bash
# Repeatable start/stop/status/diagnostic commands for GB10 vLLM serving.
# Run this ON the GB10 host (rented cloud instance or, later, the owned
# DGX Spark) — see docs/EXECUTION_ENVIRONMENTS.md. It does nothing useful
# on a non-GB10/non-GPU machine except `render` and `preflight-host` (which
# will correctly report "not GB10" rather than pretending to work).
#
# This script supersedes the single-shot scripts/serve_smoke.sh heredoc in
# docs/STAGE_0_AND_1_EXACT.md Part B2 with the configurable version this
# task asked for; it does not edit that doc (CLAUDE.md: follow the runbook
# exactly as written). Use whichever you prefer on the actual session — if
# you run the runbook's literal heredocs instead, this script is simply
# unused, not contradicted.
#
# Subcommands:
#   preflight-host        host-level checks (scripts/gb10/preflight.sh)
#   preflight-container    in-container torch/CUDA/vllm checks (pulls IMAGE)
#   render [primary|dense_fallback] [--lora]   print the vllm serve command, don't run it
#   start  [primary|dense_fallback]   start the server (detached)
#   stop                   stop and remove the container
#   status                 is it running? what does docker think?
#   logs                   follow container logs
#   smoke-test             health_check.py against the running server
#   diagnose                dump a timestamped evidence bundle (preflight + logs + vllm --help)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTAINER_NAME="cyberai-vllm-gb10"
IMAGE_FILE="$REPO_ROOT/containers/vllm-gb10/IMAGE.txt"
FALLBACK_IMAGE_FILE="$REPO_ROOT/containers/vllm-gb10/FALLBACK_IMAGE.txt"
HF_CACHE_DIR="${HF_HOME:-$HOME/.cache/huggingface}"
EVIDENCE_DIR="$REPO_ROOT/evidence/gb10"

pinned_image() {
    local file="${1:-$IMAGE_FILE}"
    grep -v '^#' "$file" | grep -v '^\s*$' | head -1 | xargs
}

render_args() {
    # variant and --lora are forwarded as-is to render_serve_args.py
    uv run --project "$REPO_ROOT" python "$REPO_ROOT/scripts/gb10/render_serve_args.py" "$@"
}

cmd_render() {
    local variant="${1:-primary}"
    shift || true
    render_args --variant "$variant" --format shell "$@"
}

cmd_preflight_host() {
    bash "$SCRIPT_DIR/gb10/preflight.sh"
}

cmd_preflight_container() {
    local image
    image="$(pinned_image)"
    echo "[gb10_serve] running in-container preflight with image: $image"
    docker run --rm --gpus all -v "$REPO_ROOT:/work" -w /work "$image" \
        python3 scripts/gb10/preflight_in_container.py
}

cmd_start() {
    local variant="${1:-primary}"
    local extra_lora_flag=()
    if [[ "${2:-}" == "--lora" ]]; then
        extra_lora_flag=(--lora)
    fi

    if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
        echo "[gb10_serve] $CONTAINER_NAME is already running. Run 'stop' first." >&2
        exit 1
    fi

    local image
    image="$(pinned_image)"
    mkdir -p "$HF_CACHE_DIR"

    # Pull argv + env from the pure renderer (libs/common/gb10_serving.py) —
    # the one place the multi-LoRA/FP8 refusal is enforced. A non-zero exit
    # here (e.g. REFUSED) must stop this script, not fall through to a
    # docker run with half-applied flags.
    local rendered_argv rendered_env
    rendered_argv="$(render_args --variant "$variant" "${extra_lora_flag[@]}" --format argv)"
    rendered_env="$(render_args --variant "$variant" "${extra_lora_flag[@]}" --format env)"
    mapfile -t argv <<< "$rendered_argv"
    mapfile -t env_lines <<< "$rendered_env"

    local docker_env_flags=()
    for line in "${env_lines[@]}"; do
        docker_env_flags+=(-e "$line")
    done

    local host port
    host="$(render_args --variant "$variant" "${extra_lora_flag[@]}" --format meta | awk -F= '/^HOST=/{print $2}')"
    port="$(render_args --variant "$variant" "${extra_lora_flag[@]}" --format meta | awk -F= '/^PORT=/{print $2}')"

    for i in "${!argv[@]}"; do
        if [[ "${argv[$i]}" == "--host" ]]; then argv[$((i+1))]="0.0.0.0"; fi
    done
    echo "[gb10_serve] starting $CONTAINER_NAME ($variant) on $host:$port with image $image"
    docker run -d --name "$CONTAINER_NAME" \
        --gpus all --ipc=host --restart no \
        -p "${host}:${port}:${port}" \
        -v "$HF_CACHE_DIR:/root/.cache/huggingface" \
        -e HF_TOKEN="${HF_TOKEN:-}" \
        "${docker_env_flags[@]}" \
        "$image" \
        "${argv[@]}"

    echo "[gb10_serve] started. 'status' to check, 'logs' to follow, 'smoke-test' once it's up (first load can take 10-15 min)."
}

cmd_stop() {
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    echo "[gb10_serve] stopped and removed $CONTAINER_NAME (if it existed)."
}

cmd_status() {
    if docker ps --format '{{.Names}}\t{{.Status}}' | grep -P "^$CONTAINER_NAME\t"; then
        :
    else
        echo "[gb10_serve] $CONTAINER_NAME is not running."
        docker ps -a --filter "name=$CONTAINER_NAME" --format '{{.Names}}\t{{.Status}}' || true
    fi
}

cmd_logs() {
    docker logs -f "$CONTAINER_NAME"
}

cmd_smoke_test() {
    local host_env="${1:-gb10_cloud}"
    local evidence="${2:-hardware}"
    local variant="${3:-primary}" meta host port model
    meta="$(render_args --variant "$variant" --format meta)"
    host="$(printf '%s\n' "$meta" | awk -F= '/^HOST=/{print $2}')"
    port="$(printf '%s\n' "$meta" | awk -F= '/^PORT=/{print $2}')"
    model="$(printf '%s\n' "$meta" | awk -F= '/^SERVED_MODEL_NAME=/{print $2}')"
    uv run --project "$REPO_ROOT" python "$SCRIPT_DIR/gb10/health_check.py" \
        --host "$host" --port "$port" --served-model-name "$model" \
        --host-env "$host_env" --evidence "$evidence"
}

cmd_diagnose() {
    mkdir -p "$EVIDENCE_DIR"
    local stamp
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    local out="$EVIDENCE_DIR/diagnose-$stamp.log"
    {
        echo "=== gb10_serve diagnose: $stamp ==="
        echo "--- preflight-host ---"
        cmd_preflight_host || true
        echo "--- docker ps -a ---"
        docker ps -a --filter "name=$CONTAINER_NAME" || true
        echo "--- docker logs (last 200 lines) ---"
        docker logs --tail 200 "$CONTAINER_NAME" 2>&1 || true
        echo "--- vllm serve --help (from pinned image) ---"
        docker run --rm "$(pinned_image)" vllm serve --help 2>&1 || true
    } | tee "$out"
    echo "[gb10_serve] evidence bundle written to $out"
}

usage() {
    sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'
}

main() {
    local sub="${1:-}"
    shift || true
    case "$sub" in
        preflight-host) cmd_preflight_host "$@" ;;
        preflight-container) cmd_preflight_container "$@" ;;
        render) cmd_render "$@" ;;
        start) cmd_start "$@" ;;
        stop) cmd_stop "$@" ;;
        status) cmd_status "$@" ;;
        logs) cmd_logs "$@" ;;
        smoke-test) cmd_smoke_test "$@" ;;
        diagnose) cmd_diagnose "$@" ;;
        *) usage; exit 1 ;;
    esac
}

main "$@"
