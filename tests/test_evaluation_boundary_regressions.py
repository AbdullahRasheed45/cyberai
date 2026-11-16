import math

import pytest

from detection_verifier.evaluation import (
    AcceptanceController,
    compare_task_results,
    mcnemar,
    paired_pass_rate_diff,
)


@pytest.mark.parametrize("base,candidate", [([], []), ([True], []), ([1], [True])])
def test_invalid_paired_vectors_are_rejected(base, candidate):
    with pytest.raises(ValueError):
        paired_pass_rate_diff(base, candidate)
    with pytest.raises(ValueError):
        mcnemar(base, candidate)


@pytest.mark.parametrize("families,iters", [(["a"], 100), ([], 100), (None, 0), (None, True)])
def test_invalid_bootstrap_settings_are_rejected(families, iters):
    with pytest.raises(ValueError):
        paired_pass_rate_diff([False, True], [True, True], families=families, iters=iters)


def test_single_correlated_family_cannot_establish_improvement():
    result = paired_pass_rate_diff([False] * 20, [True] * 20, families=["a"] * 20)
    assert result["diff"] == 1
    assert result["ci95"] is None
    assert result["improved"] is False
    assert result["inference_supported"] is False


def test_large_exact_mcnemar_does_not_overflow():
    result = mcnemar([False] * 1100, [True] * 1100)
    assert math.isfinite(result["p_value"])
    assert result["p_value"] < 0.001
    assert result["inference_scope"] == "independent_pairs_only"


def test_comparison_pairs_task_ids_instead_of_mapping_order():
    result = compare_task_results({"b": True, "a": False}, {"a": True, "b": True})
    assert result["task_ids"] == ["a", "b"]
    assert result["diff"] == 0.5
    with pytest.raises(ValueError, match="task"):
        compare_task_results({"a": False}, {"b": True})


def test_acceptance_budget_survives_controller_recreation(tmp_path):
    path = tmp_path / "ledger.sqlite"
    first = AcceptanceController(ledger_path=path, set_id="manifest-sha", max_uses=1)
    assert first.score(lambda: 12, model_id="base-sha", experiment_id="exp-1") == 12
    second = AcceptanceController(ledger_path=path, set_id="manifest-sha", max_uses=1)
    with pytest.raises(RuntimeError, match="exhausted"):
        second.score(lambda: 13, model_id="candidate-sha", experiment_id="exp-1")
    assert second.uses == 1


def test_acceptance_cannot_raise_existing_budget(tmp_path):
    path = tmp_path / "ledger.sqlite"
    AcceptanceController(ledger_path=path, set_id="manifest-sha", max_uses=1)
    with pytest.raises(ValueError, match="budget"):
        AcceptanceController(ledger_path=path, set_id="manifest-sha", max_uses=2)


def test_acceptance_cannot_raise_budget_by_mutating_controller(tmp_path):
    controller = AcceptanceController(
        ledger_path=tmp_path / "ledger.sqlite", set_id="sha", max_uses=1
    )
    controller.max_uses = 100
    with pytest.raises(ValueError, match="budget"):
        controller.score(lambda: None, model_id="base", experiment_id="exp")


def test_acceptance_failed_run_consumes_budget_and_requires_identity(tmp_path):
    controller = AcceptanceController(
        ledger_path=tmp_path / "ledger.sqlite", set_id="sha", max_uses=1
    )
    with pytest.raises(ValueError, match="model_id"):
        controller.score(lambda: None, model_id="", experiment_id="exp")
    assert controller.uses == 0
    with pytest.raises(ZeroDivisionError):
        controller.score(lambda: 1 / 0, model_id="base", experiment_id="exp")
    assert controller.uses == 1
