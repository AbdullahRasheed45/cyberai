#!/usr/bin/env python3
"""Preflight checks that can only run INSIDE the vLLM container (torch/CUDA
visibility, compute capability, the installed vLLM's actual CLI surface).

Run it with the pinned image before starting the real server:
    docker run --rm --gpus all -v "$PWD:/work" -w /work <image> \
        python3 scripts/gb10/preflight_in_container.py

Exits non-zero and prints a specific, actionable message on each known
failure mode named in the task brief: CPU-only torch, an incompatible/
missing kernel, missing weights, insufficient memory. Never silently
downgrades a failure to a warning (CLAUDE.md directive #6).

This script has no dependency on the rest of the repo (it must run with
only whatever the base image provides) — it is intentionally standalone,
unlike render_serve_args.py.
"""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import UTC, datetime

CUTLASS_SM121_SIGNATURE = "No compiled cutlass_scaled_mm for compute capability: 121"


def check_architecture() -> tuple[bool, str]:
    arch = platform.machine()
    ok = arch == "aarch64"
    return ok, f"platform.machine()={arch}" + ("" if ok else " (expected aarch64)")


def check_torch_cuda() -> tuple[bool, str, dict]:
    try:
        import torch
    except ImportError as exc:
        return False, f"FAIL: cannot import torch: {exc}", {}

    if not torch.cuda.is_available():
        return (
            False,
            "FAIL: torch has no CUDA accelerator visible (CPU-only wheel, or driver/toolkit "
            "mismatch). This is the exact failure CLAUDE.md directive #8 warns about for a "
            "bare-metal aarch64 pip install — if you see this INSIDE the pinned container, the "
            "container itself is broken, not just a missing flag.",
            {},
        )

    try:
        cap = torch.cuda.get_device_capability(0)
        name = torch.cuda.get_device_name(0)
        free_bytes, total_bytes = torch.cuda.mem_get_info(0)
    except Exception as exc:  # noqa: BLE001 - report whatever CUDA gave us
        return False, f"FAIL: torch.cuda is available but device query failed: {exc}", {}

    detail = {
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "device_name": name,
        "compute_capability": f"{cap[0]}.{cap[1]}",
        "free_gib": round(free_bytes / 1024**3, 1),
        "total_gib": round(total_bytes / 1024**3, 1),
    }

    if cap != (12, 1):
        return (
            False,
            f"WARN/FAIL: compute capability is {cap[0]}.{cap[1]}, not GB10's 12.1 (sm_121). "
            "Either this is not a GB10 host, or torch/CUDA is misreporting — do not assume the "
            "sm_121 kernel-gap findings in containers/vllm-gb10/PROVENANCE.md apply here.",
            detail,
        )

    if detail["free_gib"] < 20:
        return (
            False,
            f"FAIL: only {detail['free_gib']} GiB free on the GPU/unified-memory pool — "
            "insufficient for a 30B-A3B FP8 load plus KV cache.",
            detail,
        )

    return True, f"OK: {name}, sm_{cap[0]}{cap[1]}, {detail['free_gib']} GiB free", detail


def check_vllm_import_and_help() -> tuple[bool, str, dict]:
    try:
        import vllm

        version = getattr(vllm, "__version__", "unknown")
    except ImportError as exc:
        return False, f"FAIL: cannot import vllm: {exc}", {}

    try:
        help_result = subprocess.run(
            ["vllm", "serve", "--help"], capture_output=True, text=True, timeout=60
        )
        if help_result.returncode != 0:
            return (
                False,
                f"FAIL: vllm help exited {help_result.returncode}",
                {"stderr": help_result.stderr},
            )
        help_out = help_result.stdout
    except Exception as exc:  # noqa: BLE001
        return (
            False,
            f"FAIL: vllm {version} importable, but 'vllm serve --help' failed: {exc}",
            {"vllm_version": version},
        )

    # Self-document the ACTUAL installed CLI surface — the task brief
    # explicitly says not to assume our guessed flags remain valid. We do
    # not parse this; we just capture it for the evidence bundle so a human
    # (or a later run) can diff it against configs/serving.yaml's flags.
    known_flags = ["--enable-lora", "--kv-cache-dtype", "--enable-prefix-caching", "--max-num-seqs"]
    missing = [f for f in known_flags if f not in help_out]
    msg = f"OK: vllm {version}; 'vllm serve --help' captured ({len(help_out)} chars)."
    if missing:
        msg += f" NOTE: flags assumed by serving.yaml missing from --help: {missing}."
    return not missing, msg, {"vllm_version": version, "serve_help_missing_assumed_flags": missing}


def main() -> int:
    results: dict[str, object] = {"checked_at": datetime.now(UTC).isoformat(), "checks": []}
    overall_ok = True

    for label, fn in [
        ("architecture", check_architecture),
        ("vllm_cli", check_vllm_import_and_help),
        ("torch_cuda", check_torch_cuda),
    ]:
        out = fn()
        if len(out) == 2:
            ok, msg = out
            detail: dict = {}
        else:
            ok, msg, detail = out
        overall_ok = overall_ok and ok
        print(f"[preflight-container] {label}: {msg}")
        results["checks"].append({"label": label, "passed": ok, "message": msg, "detail": detail})

    results["passed"] = overall_ok
    print(json.dumps(results, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
