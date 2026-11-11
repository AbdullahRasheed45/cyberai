"""Typed, validated configuration schemas.

Every YAML file under `configs/` has exactly one matching model here.
`extra="forbid"` is deliberate: a typo'd or stale key in a config file must
fail loudly at load time (CLAUDE.md directive #6: fail loud), never be
silently ignored. See `libs/common/config.py` for the loader that parses a
YAML file against one of these models.

No service may re-define these shapes locally — import from here.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ServingConfig(BaseModel):
    """`configs/serving.yaml` — the shared vLLM endpoint.

    `model` is the primary candidate (Qwen3-30B-A3B FP8); `dense_fallback_model`
    is Qwen3-14B dense, used while the MoE serving/training path is being
    debugged (brief §4.2). Multi-LoRA personas are listed in `lora_adapters`
    and must each be a generation that has passed the promotion gate before
    being added here — this file is not where untested adapters get tried.
    """

    model_config = ConfigDict(extra="forbid")

    model: str
    served_model_name: str = "qwen3"
    dense_fallback_model: str
    dtype: str = "auto"
    gpu_memory_utilization: float = Field(gt=0, le=1)
    max_model_len: int = Field(gt=0)
    enable_prefix_caching: bool = True
    enable_chunked_prefill: bool = True
    enable_lora: bool = True
    # Adapter ids already certified by the promotion gate (model_registry);
    # empty until a generation exists. Never list an unpromoted adapter here.
    lora_adapters: list[str] = Field(default_factory=list)


class TrainingConfig(BaseModel):
    """`configs/training.yaml` — the Unsloth + TRL fine-tune path."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    max_seq_length: int = Field(gt=0)
    load_in_4bit: bool = True
    full_finetuning: bool = False
    lora_rank: int = Field(gt=0)
    lora_alpha: int = Field(gt=0)
    gradient_checkpointing: bool = True
    packing: bool = True
    learning_rate: float = Field(gt=0)
    warmup_steps: int = Field(ge=0)
    max_grad_norm: float = Field(gt=0)


class RevisionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lower_bar_if: str
    give_up_if: str
    give_up_action: str


class LoopBGateConfig(BaseModel):
    """`configs/loopB_gate.yaml` — the pre-registered Loop B threshold.

    PRE-REGISTERED (brief §7.8): do not edit the thresholds after a
    measurement run except via the two-way revision rule, and log any such
    revision in `DECISIONS_TO_REVISIT.md`.
    """

    model_config = ConfigDict(extra="forbid")

    floor_verified_unique_per_day: int = Field(gt=0)
    max_template_share: float = Field(gt=0, le=1)
    aspirational_per_day: int = Field(gt=0)
    revision_rule: RevisionRule


class LabConfig(BaseModel):
    """`configs/lab.yaml` — isolated lab policy (non-secret).

    Host-specific values (the WireGuard lab IP, the lab gateway URL) are
    environment-specific and stay in `.env` / `.env.example`, never here —
    see `docs/EXECUTION_ENVIRONMENTS.md`. This file holds the policy that is
    the same regardless of which laptop/subnet is in use.
    """

    model_config = ConfigDict(extra="forbid")

    default_state: str = "TARGET_SERVING"  # LabState: TARGET_SERVING | DETONATION
    require_tunnel_down_on_detonation: bool = True
    lab_subnet: str
    web_targets: list[str] = Field(default_factory=list)
