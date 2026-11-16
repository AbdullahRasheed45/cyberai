from dataclasses import replace

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
