"""Every configs/*.yaml file must parse against its typed schema.

This is the test that catches a typo'd or stale config key before it reaches
a GB10/lab session where it would be expensive to discover.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from libs.common import ConfigError, load_yaml_config
from libs.schemas import LabConfig, LoopBGateConfig, ServingConfig, TrainingConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = REPO_ROOT / "configs"


def test_serving_config_loads():
    cfg = load_yaml_config(CONFIGS_DIR / "serving.yaml", ServingConfig)
    assert cfg.model.startswith("Qwen/")
    assert cfg.dense_fallback_model.startswith("Qwen/")
    assert 0 < cfg.gpu_memory_utilization <= 1
    assert cfg.max_model_len > 0


def test_training_config_loads():
    cfg = load_yaml_config(CONFIGS_DIR / "training.yaml", TrainingConfig)
    assert cfg.lora_rank > 0
    assert cfg.learning_rate > 0


def test_loopb_gate_config_loads():
    cfg = load_yaml_config(CONFIGS_DIR / "loopB_gate.yaml", LoopBGateConfig)
    assert cfg.floor_verified_unique_per_day == 300
    assert cfg.aspirational_per_day == 800
    assert 0 < cfg.max_template_share <= 1


def test_lab_config_loads():
    cfg = load_yaml_config(CONFIGS_DIR / "lab.yaml", LabConfig)
    assert cfg.default_state == "TARGET_SERVING"
    assert cfg.require_tunnel_down_on_detonation is True
    assert "dvwa" in cfg.web_targets


def test_missing_file_fails_loudly():
    with pytest.raises(ConfigError):
        load_yaml_config(CONFIGS_DIR / "does_not_exist.yaml", ServingConfig)


def test_invalid_yaml_fails_loudly(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not: [valid, yaml:", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_yaml_config(bad, ServingConfig)


def test_unknown_key_fails_loudly(tmp_path):
    """A stale/typo'd config key must fail, not be silently dropped."""
    good = yaml.safe_load((CONFIGS_DIR / "serving.yaml").read_text(encoding="utf-8"))
    good["totally_unknown_field"] = "oops"
    bad = tmp_path / "serving_with_typo.yaml"
    bad.write_text(yaml.safe_dump(good), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_yaml_config(bad, ServingConfig)


def test_out_of_range_value_fails_loudly(tmp_path):
    good = yaml.safe_load((CONFIGS_DIR / "serving.yaml").read_text(encoding="utf-8"))
    good["gpu_memory_utilization"] = 1.5  # must be <= 1
    bad = tmp_path / "serving_oor.yaml"
    bad.write_text(yaml.safe_dump(good), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_yaml_config(bad, ServingConfig)


def test_curriculum_config_loads_all_six_domains():
    from libs.schemas import CurriculumConfig

    cfg = load_yaml_config(CONFIGS_DIR / "six_domain_curriculum.yaml", CurriculumConfig)
    assert set(cfg.domains) == {"web", "linux", "windows", "active_directory", "cloud", "mobile"}
    assert all(len(d.levels) == 5 for d in cfg.domains.values())


def test_curriculum_config_rejects_missing_domain(tmp_path):
    from libs.schemas import CurriculumConfig

    raw = yaml.safe_load((CONFIGS_DIR / "six_domain_curriculum.yaml").read_text(encoding="utf-8"))
    del raw["domains"]["mobile"]
    bad = tmp_path / "c.yaml"
    bad.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_yaml_config(bad, CurriculumConfig)


def test_every_config_file_has_a_schema():
    """No configs/*.yaml may exist without a validating test (EXECUTION_ENVIRONMENTS)."""
    covered = {
        "serving.yaml",
        "training.yaml",
        "loopB_gate.yaml",
        "lab.yaml",
        "six_domain_curriculum.yaml",
        "benchmark.yaml",
        "benchmark.harness-test.yaml",
    }
    assert {p.name for p in CONFIGS_DIR.glob("*.yaml")} <= covered


def test_benchmark_configs_load():
    from libs.schemas.benchmark import BenchmarkConfig

    for name in ("benchmark.yaml", "benchmark.harness-test.yaml"):
        load_yaml_config(CONFIGS_DIR / name, BenchmarkConfig)
