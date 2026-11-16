#!/usr/bin/env python3
"""Read-only provider inventory; no model downloads or framework installation.

Run with Enverge's GPU-enabled python, not an unrelated project virtualenv.
Docker visibility alone does not establish that nested GPU containers work.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

GPU_PROBE = """
import json, importlib
d = {'versions': {}, 'errors': []}
try:
    import unsloth
    from unsloth import FastModel
    d['fastmodel'] = True
except Exception as e:
    d['errors'].append('FastModel: ' + str(e))
names = ['torch','vllm','transformers','unsloth','peft','trl','bitsandbytes',
         'yaml','huggingface_hub']
for name in names:
    try:
        module = importlib.import_module(name)
        d['versions'][name] = getattr(module, '__version__', 'unknown')
    except Exception as e:
        d['errors'].append(name + ': ' + str(e))
try:
    import torch
    d['cuda'] = torch.cuda.is_available()
    d['torch_cuda'] = torch.version.cuda
    if d['cuda']:
        d['device'] = torch.cuda.get_device_name(0)
        d['capability'] = list(torch.cuda.get_device_capability(0))
        d['bf16'] = torch.cuda.is_bf16_supported()
        d['cuda_arithmetic'] = torch.ones(4,device='cuda',dtype=torch.bfloat16).sum().item() == 4
        torch.cuda.synchronize()
except Exception as e:
    d['errors'].append('CUDA execution: ' + str(e))
print('__PROVIDER_PROBE__' + json.dumps(d))
"""


def execute(argv, timeout=30):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return {
            "argv": argv,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"argv": argv, "error": str(exc)}


def existing_environment_blockers(machine, gpu):
    errors = list(gpu.get("errors", []))
    if machine != "aarch64":
        errors.append("expected aarch64")
    for key in ("cuda", "bf16", "cuda_arithmetic", "fastmodel"):
        if gpu.get(key) is not True:
            errors.append(f"{key} not established")
    if "GB10" not in gpu.get("device", "").upper() or gpu.get("capability") != [12, 1]:
        errors.append("actual GB10 / compute capability 12.1 not established")
    if "+cpu" in gpu.get("versions", {}).get("torch", ""):
        errors.append("CPU-only torch")
    return errors


def main():
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("artifacts/provider_environment.json"))
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("output already exists; preserve prior probe and choose --out")
    report = {
        "measured_at": datetime.now(UTC).isoformat(),
        "machine": platform.machine(),
        "python": sys.executable,
        "gpu": {},
        "commands": {},
    }
    for name, argv in {
        "driver": ["nvidia-smi"],
        "disk": ["df", "-h", "."],
        "docker": ["docker", "info"],
    }.items():
        report["commands"][name] = (
            execute(argv) if shutil.which(argv[0]) else {"error": "not found"}
        )
    probe = execute([sys.executable, "-c", GPU_PROBE], timeout=120)
    report["existing_stack_probe"] = probe
    for line in probe.get("stdout", "").splitlines():
        if line.startswith("__PROVIDER_PROBE__"):
            report["gpu"] = json.loads(line.removeprefix("__PROVIDER_PROBE__"))
    report["existing_environment_blockers"] = existing_environment_blockers(
        report["machine"], report["gpu"]
    )
    report["docker_daemon_visible"] = report["commands"]["docker"].get("returncode") == 0
    report["status"] = "INVENTORY_ONLY_REVIEW_REQUIRED"
    report["gpu_container_execution_verified"] = False
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
