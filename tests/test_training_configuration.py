import os
from dataclasses import replace
from pathlib import Path

import pytest

from rental.plan import FreezeInvalid, TrainingBenchmarkConfig, train_argv
from tests.test_orchestration import _rc


def test_representative_training_configuration_reaches_docker():
    cfg = TrainingBenchmarkConfig.from_env(
        {
            "TRAIN_MAX_SEQ_LENGTH": "8192",
            "TRAIN_MAX_STEPS": "30",
            "TRAIN_BATCH_SIZE": "2",
            "TRAIN_GRAD_ACCUM": "4",
            "TRAIN_MEASURE_WARMUP_STEPS": "5",
        }
    )
    argv = train_argv(replace(_rc(), training=cfg))
    assert "TRAIN_MAX_SEQ_LENGTH=8192" in argv
    assert "TRAIN_MAX_STEPS=30" in argv
    assert "TRAIN_BATCH_SIZE=2" in argv
    assert "TRAIN_GRAD_ACCUM=4" in argv
    assert "TRAIN_MEASURE_WARMUP_STEPS=5" in argv
    assert "HF_HOME=/hf-cache" in argv
    assert os.path.join("/repo", "runs", "hf_cache") + ":/hf-cache" in argv


@pytest.mark.parametrize(
    "env",
    [
        {"TRAIN_MAX_SEQ_LENGTH": "0"},
        {"TRAIN_MAX_STEPS": "bad"},
        {"TRAIN_BATCH_SIZE": "-1"},
        {"TRAIN_GRAD_ACCUM": "1.5"},
        {"TRAIN_MEASURE_WARMUP_STEPS": "10"},
    ],
)
def test_invalid_training_configuration_fails_before_docker(env):
    with pytest.raises(FreezeInvalid):
        TrainingBenchmarkConfig.from_env(env)


# --- configs/training.yaml is the trainer's real source of hyperparameters ----


def test_container_loader_and_ci_schema_agree_on_training_yaml():
    from libs.common import load_yaml_config
    from libs.schemas import TrainingConfig
    from rental import training_config

    hp = training_config.load("configs/training.yaml")
    ci = load_yaml_config("configs/training.yaml", TrainingConfig)
    assert set(hp.as_dict()) == set(TrainingConfig.model_fields)  # field parity
    assert hp.as_dict() == ci.model_dump()


def test_training_targets_match_the_freeze():
    import yaml

    from rental import training_config

    freeze = yaml.safe_load(Path("scripts/rental/FREEZE.yaml").read_text(encoding="utf-8"))
    assert list(training_config.load().target_modules) == freeze["adapter_targets"]


@pytest.mark.parametrize(
    "change",
    [
        {"lora_rank": 12},  # not a vLLM max-lora-rank value
        {"learning_rate": 0},
        {"gradient_checkpointing": "sometimes"},
        {"target_modules": []},
        {"unexpected_key": 1},
    ],
)
def test_training_loader_fails_loudly(tmp_path, change):
    import yaml

    from rental import training_config

    raw = yaml.safe_load(Path("configs/training.yaml").read_text(encoding="utf-8"))
    raw.update(change)
    bad = tmp_path / "training.yaml"
    bad.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(training_config.TrainingConfigError):
        training_config.load(bad)


def test_trainer_reads_hyperparameters_not_hardcoded_values():
    source = Path("scripts/smoke_train.py").read_text(encoding="utf-8")
    assert "training_config.load(" in source
    assert "learning_rate=HP.learning_rate" in source and "r=HP.lora_rank" in source
    assert "learning_rate=1e-5" not in source and "r=16," not in source


class _FakeTokenizer:
    def __init__(self, result):
        self.result = result

    def apply_chat_template(self, *a, **k):
        return self.result


def test_probe_ids_accepts_tensor_or_batch_encoding():
    import importlib.util

    spec = importlib.util.spec_from_file_location("smoke_train", "scripts/smoke_train.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ids = object()
    assert module.probe_input_ids(_FakeTokenizer(ids), []) is ids  # transformers v4
    assert module.probe_input_ids(_FakeTokenizer({"input_ids": ids}), []) is ids  # v5 dict


def test_reload_classifier_separates_kernel_noise_from_lost_adapter():
    torch = pytest.importorskip("torch")
    import importlib.util

    spec = importlib.util.spec_from_file_location("smoke_reload", "scripts/smoke_reload.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reference = torch.tensor([0.0, 10.0, 2.0])
    base = torch.tensor([0.0, 8.0, 9.0])  # different top token: adapter matters
    assert module.classify_reload(reference.clone(), reference, base, 1e-3, 1e-3)[0] == "exact"
    noisy = reference + torch.tensor([0.05, -0.05, 0.05])  # bf16 kernel-path noise
    assert module.classify_reload(noisy, reference, base, 1e-3, 1e-3)[0] == "kernel_tolerant"
    assert module.classify_reload(base.clone(), reference, base, 1e-3, 1e-3)[0] == "failed"


# --- precision: 4-bit QLoRA by default, bf16 only as a measured comparison ----


def test_default_precision_is_qlora_4bit_and_reaches_docker():
    from rental import training_config

    assert training_config.load().precision == "qlora_4bit"
    rc = _rc()
    assert "TRAIN_PRECISION=qlora_4bit" in train_argv(rc)


def test_train_precision_env_selects_bf16_comparison_and_rejects_fp8():
    from rental import plan
    from tests.test_orchestration import _good_freeze

    rc = plan.resolve(
        _good_freeze(), env={"MODEL_PATH": "/m", "RUN_ID": "r1", "TRAIN_PRECISION": "bf16"}
    )
    assert rc.train_precision == "bf16" and "TRAIN_PRECISION=bf16" in train_argv(rc)
    with pytest.raises(FreezeInvalid):
        plan.resolve(_good_freeze(), env={"MODEL_PATH": "/m", "TRAIN_PRECISION": "fp8"})


def _load_smoke_train():
    import importlib.util

    spec = importlib.util.spec_from_file_location("smoke_train", "scripts/smoke_train.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeTorch:
    bfloat16 = "bf16"


def test_base_load_kwargs_quantise_the_pinned_repo_without_substitution():
    module = _load_smoke_train()

    def from_pretrained(model_name, revision, use_exact_model_name=False, **kw):
        pass

    kw = module.base_load_kwargs(
        from_pretrained, "unsloth/X", "c" * 40, 2048, "qlora_4bit", _FakeTorch
    )
    assert kw["load_in_4bit"] is True and kw["model_name"] == "unsloth/X"
    assert kw["revision"] == "c" * 40 and kw["use_exact_model_name"] is True
    kw = module.base_load_kwargs(from_pretrained, "unsloth/X", "c" * 40, 2048, "bf16", _FakeTorch)
    assert kw["load_in_4bit"] is False and kw["load_in_8bit"] is False


def test_base_load_kwargs_omit_unsupported_exact_name_flag():
    module = _load_smoke_train()

    def old_from_pretrained(model_name, revision, **kw):
        pass

    kw = module.base_load_kwargs(old_from_pretrained, "m", "c" * 40, 2048, "qlora_4bit", _FakeTorch)
    assert "use_exact_model_name" not in kw  # the post-load name check still guards lineage
    assert "loaded_name).lower() != MODEL.lower()" in Path("scripts/smoke_train.py").read_text(
        encoding="utf-8"
    )


def test_reload_uses_training_precision():
    source = Path("scripts/smoke_reload.py").read_text(encoding="utf-8")
    assert 'meta.get("precision"' in source and "base_load_kwargs(" in source


# --- adapter target set: attention-only by default, expert projections as a comparison ---


def test_default_target_set_is_attention_and_reaches_docker():
    from rental import training_config

    hp = training_config.load()
    assert training_config.effective_targets(hp, {}) == (
        "attention",
        ["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    assert "TRAIN_TARGET_SET=attention" in train_argv(_rc())


def test_target_set_all_is_an_explicit_comparison_and_bad_values_fail():
    from rental import plan, training_config
    from tests.test_orchestration import _good_freeze

    hp = training_config.load()
    name, modules = training_config.effective_targets(hp, {"TRAIN_TARGET_SET": "all"})
    assert name == "all" and modules == list(hp.target_modules) and "gate_proj" in modules
    rc = plan.resolve(
        _good_freeze(), env={"MODEL_PATH": "/m", "RUN_ID": "r1", "TRAIN_TARGET_SET": "all"}
    )
    assert "TRAIN_TARGET_SET=all" in train_argv(rc)
    with pytest.raises(FreezeInvalid):
        plan.resolve(_good_freeze(), env={"MODEL_PATH": "/m", "TRAIN_TARGET_SET": "experts"})


def test_adapter_size_arithmetic_for_the_pinned_model():
    """Why attention is the default: sizes follow from the pinned config's dimensions."""
    hidden, layers, experts, moe, rank = 2048, 48, 128, 768, 16
    q, kv = 32 * 128, 4 * 128

    def lora(i, o):
        return rank * (i + o)

    attention = layers * (lora(hidden, q) + 2 * lora(hidden, kv) + lora(q, hidden))
    expert = layers * experts * (2 * lora(hidden, moe) + lora(moe, hidden))
    assert round(attention / 1e6, 1) == 13.4 and round(expert / 1e6, 1) == 830.5
    assert expert / (attention + expert) > 0.98


def test_trainer_uses_the_effective_targets_and_records_them():
    source = Path("scripts/smoke_train.py").read_text(encoding="utf-8")
    assert "target_modules=TARGETS" in source and '"target_set": TARGET_SET' in source
    assert '"trainable_parameters"' in source
