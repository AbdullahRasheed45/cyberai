"""Structural verification of a LOCAL serving checkpoint against the declared
serving identity (Astra #2). This is the minimum enforced locally: reject missing
weights, a non-MoE / wrong-size architecture, and a missing FP8 quantisation when
FP8 is declared. It does NOT rely on _name_or_path.

Full provenance (materialise from the declared repo+immutable commit and match
every file hash) is a RENTAL-SETUP step that needs the hub; this function's job is
to make an obviously-wrong local checkpoint (e.g. Qwen3-0.6B where 30B-A3B is
declared) fail immediately, offline.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path

# expected shape of Qwen3-30B-A3B (MoE); generous lower bounds, not exact match
_MIN_EXPERTS = 64
_MIN_LAYERS = 40


def verify_local_checkpoint(model_dir: str, serving_quant: str) -> list[str]:
    errs: list[str] = []
    conf = os.path.join(model_dir, "config.json")
    if not os.path.isfile(conf):
        return [f"missing config.json in {model_dir!r}"]
    try:
        c = json.loads(Path(conf).read_text(encoding="utf-8"))
    except Exception as e:
        return [f"unreadable config.json: {e}"]

    if not (
        glob.glob(os.path.join(model_dir, "*.safetensors"))
        or glob.glob(os.path.join(model_dir, "*.bin"))
    ):
        errs.append("no weight files (*.safetensors/*.bin) in checkpoint")

    model_type = str(c.get("model_type", "")).lower()
    n_experts = c.get("num_experts") or c.get("num_local_experts") or c.get("n_routed_experts")
    if "moe" not in model_type and not n_experts:
        errs.append(
            f"not a MoE checkpoint (model_type={model_type!r}, no expert count); 30B-A3B is MoE"
        )
    elif n_experts and n_experts < _MIN_EXPERTS:
        errs.append(f"expert count {n_experts} < {_MIN_EXPERTS}; wrong model size")

    layers = c.get("num_hidden_layers")
    if layers and layers < _MIN_LAYERS:
        errs.append(f"num_hidden_layers {layers} < {_MIN_LAYERS}; wrong model size")

    if "fp8" in (serving_quant or "").lower():
        qc = c.get("quantization_config") or {}
        if "fp8" not in json.dumps(qc).lower():
            errs.append("serving_quant=FP8 declared but checkpoint has no FP8 quantization_config")
    return errs
