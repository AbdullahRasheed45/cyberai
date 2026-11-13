"""Collect actual pinned-image GPU probe results; never infer versions from CPU.

Run from the repository root on the setup/Spark machine. Images must already
be pulled by their frozen digest. Writes evidence and a separate candidate
freeze; does not assert model lineage or overwrite the operator's freeze.
"""

import json
import subprocess
from pathlib import Path

import yaml

from rental.probe import extract_probe, probe_argv


def main():
    freeze_path = Path("scripts/rental/FREEZE.yaml")
    cfg = yaml.safe_load(freeze_path.read_text(encoding="utf-8"))
    out = Path("artifacts/image_pin_collection")
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    required = {
        "vllm_image": ["torch", "vllm"],
        "unsloth_image": ["torch", "transformers", "unsloth", "trl", "peft", "bitsandbytes"],
    }
    for key, components in required.items():
        result = subprocess.run(probe_argv(cfg[key]), capture_output=True, text=True, timeout=900)
        (out / (key + ".log")).write_text(result.stdout + "\n" + result.stderr)
        parsed = extract_probe(result.stdout)
        if result.returncode or not parsed:
            raise RuntimeError(f"{key}: failed probe; see {out}")
        results[key] = parsed
        (out / "probes.json").write_text(json.dumps(results, indent=2))
        if not parsed.get("cuda") or not parsed.get("bf16"):
            raise RuntimeError(f"{key}: CUDA/bf16 unavailable")
        for component in components:
            version = parsed.get("versions", {}).get(component)
            if not version or version == "?" or version.startswith("IMPORT_FAIL"):
                raise RuntimeError(f"{key}: missing usable {component} version")
    training = results["unsloth_image"]["versions"]
    cfg["dependencies"] = [
        f"{name}=={training[name]}"
        for name in ["transformers", "unsloth", "peft", "trl", "bitsandbytes"]
    ]
    candidate = out / "FREEZE.image-versions.yaml"
    candidate.write_text(yaml.safe_dump(cfg, sort_keys=False))
    print(
        f"Wrote {candidate}; model-lineage attestation is unchanged. "
        "Review and use this freeze only after lineage verification."
    )


if __name__ == "__main__":
    main()
