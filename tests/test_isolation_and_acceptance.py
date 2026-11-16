"""Regression tests for the isolation worker (Astra #1/#2) and the untrusted
acceptance entry point (#3). Pure Python; no torch/GPU."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
import yaml

from detection_verifier.acceptance import evaluate_untrusted_candidate
from detection_verifier.checker import EvaluationInputError
from detection_verifier.isolation import (
    MAX_RESULT_BYTES,
    CandidateError,
    CandidateTimeout,
    ResultTooLarge,
    run_isolated,
)

FX = Path(__file__).resolve().parents[1] / "fixtures" / "detection"


def _j(n):
    return [
        json.loads(line)
        for line in (FX / n).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _r(n):
    return yaml.safe_load((FX / "rules" / n).read_text(encoding="utf-8"))


PRES, ABSENT, OOS = (
    _j("behaviour_present.jsonl"),
    _j("behaviour_absent.jsonl"),
    _j("out_of_scope.jsonl"),
)


# module-level callables (picklable) for the worker
def _raise():
    raise ValueError("boom")


def _exit_no_result():
    os._exit(0)


# --- Astra #1: larger valid results must not look like a timeout --------------


def test_small_result():
    assert run_isolated(bytes, (16,), timeout_s=5.0) == bytes(16)


def test_large_valid_result_returns():
    out = run_isolated(bytes, (1_000_000,), timeout_s=5.0)  # was a false CandidateTimeout
    assert out == bytes(1_000_000)


def test_result_too_large_is_distinct():
    with pytest.raises(ResultTooLarge):
        run_isolated(bytes, (MAX_RESULT_BYTES + 1,), timeout_s=5.0)


def test_worker_exception_propagates_by_type():
    with pytest.raises(ValueError):
        run_isolated(_raise, (), timeout_s=5.0)


def test_worker_exit_without_result():
    with pytest.raises(CandidateError):
        run_isolated(_exit_no_result, (), timeout_s=5.0)


def test_timeout_killed_quickly():
    t0 = time.monotonic()
    with pytest.raises(CandidateTimeout):
        run_isolated(time.sleep, (5,), timeout_s=0.3)
    assert time.monotonic() - t0 < 2.0


@pytest.mark.parametrize("bad", [0, -1, float("inf"), float("nan")])
def test_bad_timeout_rejected(bad):
    with pytest.raises(ValueError):
        run_isolated(abs, (-1,), timeout_s=bad)


# --- Astra #3: the untrusted acceptance entry point --------------------------


def test_entry_valid_rule():
    v = evaluate_untrusted_candidate(_r("good.yml"), PRES, ABSENT, out_of_scope=OOS, timeout_s=5.0)
    assert v.outcome == "VERIFIED"


def test_entry_invalid_rule_syntax_is_failed_not_error():
    v = evaluate_untrusted_candidate(_r("broken.yml"), PRES, ABSENT, timeout_s=5.0)
    assert v.outcome == "FAILED"  # syntax failure is a normal verdict


def test_entry_invalid_telemetry_raises_input_error():
    with pytest.raises(EvaluationInputError):
        evaluate_untrusted_candidate(_r("good.yml"), PRES, ABSENT + [{}], timeout_s=5.0)


def _slow_check(*args, **kwargs):
    time.sleep(5)


def _broken_check(*args, **kwargs):
    raise RuntimeError("injected worker failure")


def test_entry_execution_timeout(monkeypatch):
    import detection_verifier.acceptance as acceptance

    monkeypatch.setattr(acceptance, "check_rule", _slow_check)
    with pytest.raises(CandidateTimeout):
        acceptance.evaluate_untrusted_candidate(_r("good.yml"), PRES, ABSENT, timeout_s=0.3)


def test_entry_worker_failure(monkeypatch):
    import detection_verifier.acceptance as acceptance

    monkeypatch.setattr(acceptance, "check_rule", _broken_check)
    with pytest.raises((CandidateError, RuntimeError)):
        acceptance.evaluate_untrusted_candidate(_r("good.yml"), PRES, ABSENT, timeout_s=5.0)


# --- Astra #4: empty adapter state dicts rejected ----------------------------


def test_compare_rejects_empty_state_dicts():
    pytest.importorskip("torch")
    from detection_verifier.adapter_utils import compare_state_dicts

    ok, detail = compare_state_dicts({}, {}, atol=1e-3, rtol=1e-3)
    assert ok is False and "empty" in detail
