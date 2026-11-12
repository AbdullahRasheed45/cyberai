"""Pure logic: `ServingConfig` -> the exact `vllm serve` invocation.

No I/O here (no subprocess, no filesystem, no network) — this is the
"domain" half of GB10 serving; `scripts/gb10/render_serve_args.py` is the
thin CLI that calls it, and `scripts/gb10_serve.sh` is the infra that
actually runs docker. Keeping this pure makes the one rule that matters
(never serve LoRA on the unverified FP8 MoE path) a unit-testable fact
instead of something only checkable by reading a shell script.

See `containers/vllm-gb10/PROVENANCE.md` for why these specific flags/env
vars were chosen, and what is still unverified on real hardware.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from libs.schemas import ServingConfig

ModelVariant = Literal["primary", "dense_fallback"]


class UnverifiedLoraCombinationError(ValueError):
    """Raised when asked to serve LoRA adapters against the unverified FP8 MoE path.

    See PROVENANCE.md: vLLM issue #29424 (MoE LoRA for quantized models) was
    closed "not planned", and a same-family quantized-MoE + LoRA attempt
    produced garbage output. This is a refusal, not a warning — flipping
    `ServingConfig.require_lora_fp8_verified` requires a real hardware
    correctness check first.
    """


class ServeCommand(BaseModel):
    """What to actually run: argv for `vllm serve` plus the env it needs."""

    model_config = ConfigDict(extra="forbid")

    argv: list[str]
    env: dict[str, str]
    variant: ModelVariant
    model: str
    revision: str
    served_model_name: str
    lora_enabled: bool


def _bool_flag(name: str, value: bool) -> str:
    return f"--{name}" if value else f"--no-{name}"


def render_serve_command(
    cfg: ServingConfig,
    *,
    variant: ModelVariant = "primary",
    lora_enabled: bool = False,
    served_model_name: str | None = None,
) -> ServeCommand:
    """Build the `vllm serve` argv + env for one model variant of `cfg`.

    Raises `UnverifiedLoraCombinationError` if `lora_enabled` is requested
    for the FP8 MoE `primary` variant while
    `cfg.require_lora_fp8_verified` is false — never silently drops the
    adapters and never silently serves them against doubt (CLAUDE.md
    directive #6: fail loud).
    """
    if lora_enabled and variant == "primary" and not cfg.require_lora_fp8_verified:
        raise UnverifiedLoraCombinationError(
            "refusing to serve LoRA adapters against the FP8 MoE primary model: "
            "this combination is not verified (see containers/vllm-gb10/PROVENANCE.md). "
            "Set ServingConfig.require_lora_fp8_verified=true only after a real, "
            "hardware-run correctness check — not just 'it did not crash'."
        )

    if variant == "primary":
        model, revision = cfg.model, cfg.model_revision
        default_served_name = cfg.served_model_name
    else:
        model, revision = cfg.dense_fallback_model, cfg.dense_fallback_revision
        default_served_name = f"{cfg.served_model_name}-dense"

    name = served_model_name or default_served_name

    argv = [
        "vllm",
        "serve",
        model,
        "--revision",
        revision,
        "--served-model-name",
        name,
        "--host",
        cfg.host,
        "--port",
        str(cfg.port),
        "--dtype",
        cfg.dtype,
        "--gpu-memory-utilization",
        str(cfg.gpu_memory_utilization),
        "--max-model-len",
        str(cfg.max_model_len),
        "--max-num-seqs",
        str(cfg.max_num_seqs),
        "--kv-cache-dtype",
        cfg.kv_cache_dtype,
        _bool_flag("enable-prefix-caching", cfg.enable_prefix_caching),
        _bool_flag("enable-chunked-prefill", cfg.enable_chunked_prefill),
    ]

    if lora_enabled:
        argv.append("--enable-lora")
        for adapter_id in cfg.lora_adapters:
            # Adapter *paths* are resolved by model_registry (Stage 2+); for
            # now this records intent (which certified ids should be live)
            # without inventing a path format that infra hasn't built yet.
            argv.extend(["--lora-modules", adapter_id])

    env = {"VLLM_ATTENTION_BACKEND": cfg.attention_backend}

    return ServeCommand(
        argv=argv,
        env=env,
        variant=variant,
        model=model,
        revision=revision,
        served_model_name=name,
        lora_enabled=lora_enabled,
    )
