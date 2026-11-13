"""Container-safe loader for `configs/training.yaml`.

`scripts/smoke_train.py` runs inside the pinned Unsloth image, where only the
standard library and PyYAML (a huggingface_hub dependency) can be assumed —
not pydantic. This mirrors `libs.schemas.TrainingConfig` field-for-field
(`tests/test_training_configuration.py` enforces parity) and is just as strict:
unknown or missing keys and out-of-range values fail loudly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

DEFAULT_PATH = "configs/training.yaml"

# vLLM only accepts these --max-lora-rank values.
VLLM_LORA_RANKS = (1, 8, 16, 32, 64, 128, 256, 320, 512)
# Frozen-base precision during training. FP8 training is deliberately not offered.
PRECISIONS = ("qlora_4bit", "bf16")


def effective_precision(hp: TrainingHyperparameters, env=None) -> str:
    """TRAIN_PRECISION (a per-run matrix knob) overrides the file's default."""
    env = os.environ if env is None else env
    value = (env.get("TRAIN_PRECISION") or hp.precision).strip()
    if value not in PRECISIONS:
        raise TrainingConfigError(f"precision must be one of {PRECISIONS}, got {value!r}")
    return value


class TrainingConfigError(ValueError):
    pass


@dataclass(frozen=True)
class TrainingHyperparameters:
    precision: str
    lora_rank: int
    lora_alpha: int
    lora_dropout: float
    target_modules: tuple
    gradient_checkpointing: object  # "unsloth" | True | False
    packing: bool
    learning_rate: float
    lr_scheduler_type: str
    warmup_steps: int
    max_grad_norm: float
    weight_decay: float
    seed: int

    def as_dict(self) -> dict:
        d = {f.name: getattr(self, f.name) for f in fields(self)}
        d["target_modules"] = list(self.target_modules)
        return d


def _check(raw: dict) -> TrainingHyperparameters:
    if not isinstance(raw, dict):
        raise TrainingConfigError("training config must be a mapping")
    names = {f.name for f in fields(TrainingHyperparameters)}
    unknown, missing = set(raw) - names, names - set(raw)
    if unknown or missing:
        raise TrainingConfigError(
            f"training config keys: unknown={sorted(unknown)} missing={sorted(missing)}"
        )
    if raw["precision"] not in PRECISIONS:
        raise TrainingConfigError(f"precision must be one of {PRECISIONS}")
    if raw["lora_rank"] not in VLLM_LORA_RANKS:
        raise TrainingConfigError(f"lora_rank must be one of {VLLM_LORA_RANKS} (vLLM limit)")
    if not isinstance(raw["lora_alpha"], int) or raw["lora_alpha"] <= 0:
        raise TrainingConfigError("lora_alpha must be a positive integer")
    if not (0.0 <= float(raw["lora_dropout"]) < 1.0):
        raise TrainingConfigError("lora_dropout must be in [0, 1)")
    targets = raw["target_modules"]
    if not isinstance(targets, list) or not targets or not all(isinstance(t, str) for t in targets):
        raise TrainingConfigError("target_modules must be a non-empty list of names")
    if raw["gradient_checkpointing"] not in ("unsloth", True, False):
        raise TrainingConfigError("gradient_checkpointing must be unsloth, true or false")
    if not isinstance(raw["packing"], bool):
        raise TrainingConfigError("packing must be a boolean")
    if not float(raw["learning_rate"]) > 0:
        raise TrainingConfigError("learning_rate must be positive")
    if not isinstance(raw["warmup_steps"], int) or raw["warmup_steps"] < 0:
        raise TrainingConfigError("warmup_steps must be a non-negative integer")
    if not float(raw["max_grad_norm"]) > 0:
        raise TrainingConfigError("max_grad_norm must be positive")
    if float(raw["weight_decay"]) < 0:
        raise TrainingConfigError("weight_decay must be non-negative")
    if not isinstance(raw["seed"], int):
        raise TrainingConfigError("seed must be an integer")
    return TrainingHyperparameters(
        precision=raw["precision"],
        lora_rank=int(raw["lora_rank"]),
        lora_alpha=int(raw["lora_alpha"]),
        lora_dropout=float(raw["lora_dropout"]),
        target_modules=tuple(targets),
        gradient_checkpointing=raw["gradient_checkpointing"],
        packing=raw["packing"],
        learning_rate=float(raw["learning_rate"]),
        lr_scheduler_type=str(raw["lr_scheduler_type"]),
        warmup_steps=int(raw["warmup_steps"]),
        max_grad_norm=float(raw["max_grad_norm"]),
        weight_decay=float(raw["weight_decay"]),
        seed=int(raw["seed"]),
    )


def load(path: str | os.PathLike | None = None) -> TrainingHyperparameters:
    import yaml

    p = Path(path or os.environ.get("TRAINING_CONFIG", DEFAULT_PATH))
    if not p.is_file():
        raise TrainingConfigError(f"training config not found: {p}")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TrainingConfigError(f"invalid YAML in {p}: {exc}") from exc
    return _check(raw)
