"""Typed, validated configuration schemas.

Every YAML file under `configs/` has exactly one matching model here.
`extra="forbid"` is deliberate: a typo'd or stale key in a config file must
fail loudly at load time (CLAUDE.md directive #6: fail loud), never be
silently ignored. See `libs/common/config.py` for the loader that parses a
YAML file against one of these models.

No service may re-define these shapes locally — import from here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ServingConfig(BaseModel):
    """`configs/serving.yaml` — the shared vLLM endpoint.

    `model` is the primary candidate (Qwen3-30B-A3B FP8); `dense_fallback_model`
    is Qwen3-14B dense, used while the MoE serving/training path is being
    debugged (brief §4.2). Multi-LoRA personas are listed in `lora_adapters`
    and must each be a generation that has passed the promotion gate before
    being added here — this file is not where untested adapters get tried.

    GB10/sm_121 is not an officially merged vLLM target as of 2026-11-11
    (upstream PR vllm-project/vllm#31740 was closed, unmerged — see
    `containers/vllm-gb10/PROVENANCE.md`). `attention_backend` and
    `require_lora_fp8_verified` exist specifically to make that uncertainty
    an explicit, checked setting rather than a silent assumption.
    """

    model_config = ConfigDict(extra="forbid")

    model: str
    # The exact HF commit this config was validated against (CLAUDE.md
    # directive #6 extends to model identity: no floating "latest" in a
    # serving config). Re-pin deliberately, never drop to None.
    model_revision: str
    served_model_name: str = "qwen3"
    dense_fallback_model: str
    dense_fallback_revision: str
    dtype: str = "auto"
    gpu_memory_utilization: float = Field(gt=0, le=1)
    max_model_len: int = Field(gt=0)
    enable_prefix_caching: bool = True
    enable_chunked_prefill: bool = True

    # --- network exposure: bind to a trusted interface, never a blind 0.0.0.0 ---
    host: str = "127.0.0.1"
    port: int = Field(gt=0, le=65535, default=8000)

    # --- concurrency / memory knobs (brief §5.2: batching vs long-context
    # spend the same KV budget; tune on measured hardware, don't trust a
    # default) ---
    max_num_seqs: int = Field(gt=0, default=4)
    kv_cache_dtype: str = "auto"  # vLLM: auto | fp8 | fp8_e5m2 | fp8_e4m3

    # --- GB10/sm_121: upstream CUTLASS scaled_mm has no sm_121 kernel
    # (vllm-project/vllm#31740); known-working fallback is the Triton
    # attention backend (set via the VLLM_ATTENTION_BACKEND env var — no
    # confirmed stable `--attention-backend` CLI flag as of this writing).
    # Re-verify against `vllm serve --help` on the actual installed image
    # before trusting this; see scripts/gb10/preflight.sh.
    attention_backend: str = "TRITON_ATTN"

    enable_lora: bool = True
    # Adapter ids already certified by the promotion gate (model_registry);
    # empty until a generation exists. Never list an unpromoted adapter here.
    lora_adapters: list[str] = Field(default_factory=list)
    # Multi-LoRA on a quantized MoE model (our FP8 primary) is NOT verified:
    # vLLM issue #29424 ("MoE LoRA for quantized models") was closed as "not
    # planned", and a real LoRA-on-quantized-MoE attempt (AWQ, same code
    # path family as FP8) produced garbage output. Serving scripts must
    # refuse --enable-lora against the FP8 primary model unless this is
    # explicitly set true after a real, hardware-verified correctness check
    # — see containers/vllm-gb10/PROVENANCE.md. The dense bf16 fallback has
    # no such restriction; ordinary multi-LoRA is well-supported there.
    require_lora_fp8_verified: bool = False


class TrainingConfig(BaseModel):
    """`configs/training.yaml` — LoRA hyperparameters for the Unsloth + TRL path.

    The trainer runs inside the Unsloth image and reads this file through the
    container-safe mirror `rental.training_config` (no pydantic there); a test
    keeps the two field sets identical. Model identity lives in the freeze,
    per-run matrix knobs in TRAIN_* env vars — never here.
    """

    model_config = ConfigDict(extra="forbid")

    lora_rank: Literal[1, 8, 16, 32, 64, 128, 256, 320, 512]
    lora_alpha: int = Field(gt=0)
    lora_dropout: float = Field(ge=0, lt=1)
    target_modules: list[str] = Field(min_length=1)
    gradient_checkpointing: Literal["unsloth"] | bool
    packing: bool
    learning_rate: float = Field(gt=0)
    lr_scheduler_type: str
    warmup_steps: int = Field(ge=0)
    max_grad_norm: float = Field(gt=0)
    weight_decay: float = Field(ge=0)
    seed: int


class CurriculumDomain(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["implemented_offline_reference", "planned"]
    levels: list[str] = Field(min_length=5, max_length=5)
    resource_profile: str


class CurriculumScheduling(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: str
    note: str


class CurriculumConfig(BaseModel):
    """`configs/six_domain_curriculum.yaml` — product inventory, not lab claims.

    All six domains must be present (PRODUCT_ALIGNMENT doc); each has exactly
    five easy-to-hard levels. `status: planned` never implies an environment
    exists.
    """

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    domains: dict[
        Literal["web", "linux", "windows", "active_directory", "cloud", "mobile"],
        CurriculumDomain,
    ]
    scheduling: CurriculumScheduling

    @model_validator(mode="after")
    def _all_six_domains(self) -> CurriculumConfig:
        expected = {"web", "linux", "windows", "active_directory", "cloud", "mobile"}
        missing = expected - set(self.domains)
        if missing:
            raise ValueError(f"curriculum is missing domains: {sorted(missing)}")
        return self


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
