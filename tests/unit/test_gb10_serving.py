"""render_serve_command is the one place the multi-LoRA/FP8 refusal rule
(containers/vllm-gb10/PROVENANCE.md) is actually enforced — test it as a
fact about the code, not just a claim in a doc."""

from __future__ import annotations

from pathlib import Path

import pytest

from libs.common import UnverifiedLoraCombinationError, load_yaml_config, render_serve_command
from libs.schemas import ServingConfig

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def cfg() -> ServingConfig:
    return load_yaml_config(REPO_ROOT / "configs" / "serving.yaml", ServingConfig)


def test_primary_command_pins_model_and_revision(cfg):
    cmd = render_serve_command(cfg, variant="primary")
    assert cmd.model == cfg.model
    assert cmd.revision == cfg.model_revision
    assert "--revision" in cmd.argv
    assert cmd.argv[cmd.argv.index("--revision") + 1] == cfg.model_revision


def test_dense_fallback_uses_its_own_model_and_a_distinct_served_name(cfg):
    cmd = render_serve_command(cfg, variant="dense_fallback")
    assert cmd.model == cfg.dense_fallback_model
    assert cmd.revision == cfg.dense_fallback_revision
    assert cmd.served_model_name != cfg.served_model_name  # never silently aliases the primary


def test_binds_to_configured_host_not_a_bare_wildcard(cfg):
    cmd = render_serve_command(cfg, variant="primary")
    assert "--host" in cmd.argv
    bound_host = cmd.argv[cmd.argv.index("--host") + 1]
    assert bound_host == cfg.host
    assert bound_host != "0.0.0.0"  # configs/serving.yaml defaults to loopback


def test_attention_backend_applied_via_env_not_a_guessed_cli_flag(cfg):
    cmd = render_serve_command(cfg, variant="primary")
    assert cmd.env["VLLM_ATTENTION_BACKEND"] == cfg.attention_backend
    assert "--attention-backend" not in cmd.argv


def test_lora_on_fp8_primary_refused_by_default(cfg):
    assert cfg.require_lora_fp8_verified is False
    with pytest.raises(UnverifiedLoraCombinationError):
        render_serve_command(cfg, variant="primary", lora_enabled=True)


def test_lora_on_fp8_primary_allowed_once_explicitly_verified(cfg):
    verified_cfg = cfg.model_copy(update={"require_lora_fp8_verified": True})
    cmd = render_serve_command(verified_cfg, variant="primary", lora_enabled=True)
    assert "--enable-lora" in cmd.argv
    assert cmd.lora_enabled is True


def test_lora_on_dense_fallback_never_gated(cfg):
    """The refusal is specific to the unverified FP8 MoE path."""
    assert cfg.require_lora_fp8_verified is False
    cmd = render_serve_command(cfg, variant="dense_fallback", lora_enabled=True)
    assert "--enable-lora" in cmd.argv


def test_prefix_caching_and_chunked_prefill_flags_reflect_config(cfg):
    cmd = render_serve_command(cfg, variant="primary")
    assert _bool_flag_present(cmd.argv, "enable-prefix-caching", cfg.enable_prefix_caching)
    assert _bool_flag_present(cmd.argv, "enable-chunked-prefill", cfg.enable_chunked_prefill)


def _bool_flag_present(argv: list[str], name: str, expected: bool) -> bool:
    on, off = f"--{name}", f"--no-{name}"
    return (on in argv) is expected and (off in argv) is not expected
