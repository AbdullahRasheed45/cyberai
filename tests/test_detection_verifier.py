"""Runnable evidence + regression tests for every defect Astra's probing found
(Rounds 6–7). No GPU / model / network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from detection_verifier import assurance
from detection_verifier.checker import SCHEMA_FIELDS, EvaluationInputError, check_rule
from detection_verifier.sigma_subset import RuleSyntaxError, parse_rule

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "fixtures" / "detection"
RULES = FX / "rules"


def _jsonl(n):
    return [
        json.loads(line)
        for line in (FX / n).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _rule(n):
    return yaml.safe_load((RULES / n).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def corpora():
    return (
        _jsonl("behaviour_present.jsonl"),
        _jsonl("behaviour_absent.jsonl"),
        _jsonl("out_of_scope.jsonl"),
    )


def _check(rule, corpora, **kw):
    pres, absent, oos = corpora
    return check_rule(rule, pres, absent, out_of_scope=oos, **kw)


# --- baseline verdicts -------------------------------------------------------


@pytest.mark.parametrize(
    "rule_file,expected",
    [
        ("good.yml", "VERIFIED"),
        ("trivial.yml", "FAILED"),
        ("overfit.yml", "FAILED"),
        ("incidental_only.yml", "FAILED"),
        ("broken.yml", "FAILED"),
        ("unknown_field.yml", "FAILED"),
        ("lint_bypass.yml", "FAILED"),
    ],
)
def test_rule_verdicts(corpora, rule_file, expected):
    v = _check(_rule(rule_file), corpora)
    assert v.outcome == expected, (rule_file, v.metrics.reasons)


def test_good_rule_metrics(corpora):
    v = _check(_rule("good.yml"), corpora)
    assert v.metrics.coverage == 1.0 and v.metrics.fp == 0
    assert v.metrics.has_behavioral_field


def test_good_rule_surfaces_benign_behaviour(corpora):
    """Defect #9: a benign-but-behaviour-present event (admin encoded command) is
    still coverage — the detector surfaces behaviour, intent is downstream."""
    pres, absent, oos = corpora
    benign_behaviour = [
        e for e in pres if "svc_automation" in e.get("CommandLine", "") + e.get("User", "")
    ]
    assert benign_behaviour, "fixture missing the benign-behaviour example"
    v = check_rule(_rule("good.yml"), benign_behaviour, absent, out_of_scope=oos)
    assert v.metrics.coverage == 1.0


def test_out_of_scope_not_counted_as_fp(corpora):
    """Defect #9: short-payload invocations are out-of-scope, never negatives."""
    v = _check(_rule("good.yml"), corpora)
    assert v.metrics.n_out_of_scope == 2
    # whatever the rule does on them, it does not affect fp_burden
    assert v.metrics.fp == 0 and v.metrics.fp_burden == 0.0


# --- defect #1 (reload) is in the smoke scripts; checker-level input guards ---


def test_empty_benign_raises(corpora):
    pres, _, oos = corpora
    with pytest.raises(EvaluationInputError):
        check_rule(_rule("good.yml"), pres, [], out_of_scope=oos)


def test_certify_empty_is_false():
    ok, reasons = assurance.certify([])
    assert ok is False and reasons


# --- defect #4: missing required telemetry -> invalid input, not VERIFIED -----


def test_missing_required_field_is_rejected(corpora):
    pres, absent, _ = corpora
    bad_absent = absent + [{}]  # empty benign observation
    with pytest.raises(EvaluationInputError):
        check_rule(_rule("good.yml"), pres, bad_absent)


def test_null_required_field_is_rejected(corpora):
    pres, absent, _ = corpora
    bad = absent + [{"Image": "x\\powershell.exe", "CommandLine": None}]
    with pytest.raises(EvaluationInputError):
        check_rule(_rule("good.yml"), pres, bad)


def test_reproduce_astra_probe4():
    """Astra's exact probe: a rule + an empty benign event must NOT be VERIFIED."""
    rule = {
        "logsource": {"category": "process_creation"},
        "detection": {"s": {"Image": "x"}, "condition": "s"},
    }
    with pytest.raises(EvaluationInputError):
        check_rule(rule, [{"Image": "x", "CommandLine": "x"}], [{}])


# --- defect #5: no silent truncation -----------------------------------------


def test_oversized_field_rejected_not_truncated(corpora):
    from detection_verifier.sigma_subset import MAX_EVENT_FIELD_LEN

    pres, absent, _ = corpora
    huge = {
        "Image": "x\\powershell.exe",
        "CommandLine": "x" * (MAX_EVENT_FIELD_LEN - 4) + "MARK" + "TAIL",
    }
    with pytest.raises(EvaluationInputError):
        check_rule(_rule("good.yml"), pres, absent + [huge])


def test_truncation_cannot_flip_endswith():
    """Astra's probe: endswith MARK must not match a field truly ending TAIL."""
    from detection_verifier.sigma_subset import MAX_EVENT_FIELD_LEN

    rule = {
        "logsource": {"category": "process_creation"},
        "detection": {"s": {"CommandLine|endswith": "MARK"}, "condition": "s"},
    }
    evt = {
        "Image": "p\\powershell.exe",
        "CommandLine": "x" * (MAX_EVENT_FIELD_LEN - 4) + "MARK" + "TAIL",
    }
    with pytest.raises(EvaluationInputError):  # oversized -> rejected, never truncated
        check_rule(rule, [evt], [{"Image": "a", "CommandLine": "b"}])


# --- defect #6: whole-candidate deadline + referenced-only + depth ------------


def test_overall_deadline_terminates(corpora, monkeypatch):
    import time

    import detection_verifier.sigma_subset as ss

    orig = ss.Rule.evaluate
    monkeypatch.setattr(ss.Rule, "evaluate", lambda self, ev: (time.sleep(0.02), orig(self, ev))[1])
    pres, absent, oos = corpora
    v = check_rule(_rule("good.yml"), pres, absent, out_of_scope=oos, deadline_s=0.05)
    assert v.outcome == "FAILED"
    assert any("deadline exceeded" in r for r in v.metrics.reasons)


def test_deadline_catches_single_overdue_event(corpora, monkeypatch):
    """Astra's probe: one event exceeding the deadline must be caught by the
    AFTER-check, not returned successfully."""
    import time

    import detection_verifier.sigma_subset as ss

    orig = ss.Rule.evaluate
    monkeypatch.setattr(ss.Rule, "evaluate", lambda self, ev: (time.sleep(0.03), orig(self, ev))[1])
    pres, absent, oos = corpora
    v = check_rule(_rule("good.yml"), pres[:1], absent[:1], deadline_s=0.001)
    assert v.outcome == "FAILED"
    assert any("deadline exceeded" in r for r in v.metrics.reasons)


@pytest.mark.parametrize("bad", [0, -1, float("inf"), float("nan"), "x"])
def test_bad_deadline_rejected(corpora, bad):
    pres, absent, _ = corpora
    with pytest.raises(EvaluationInputError):
        check_rule(_rule("good.yml"), pres, absent, deadline_s=bad)


# --- defect #4: required-field TYPES enforced --------------------------------


def test_required_field_types_enforced(corpora):
    """Astra's probe: {Image:1, CommandLine:False} must NOT be VERIFIED."""
    pres, absent, _ = corpora
    rule = {
        "logsource": {"category": "process_creation"},
        "detection": {"s": {"Image|endswith": "x"}, "condition": "s"},
    }
    with pytest.raises(EvaluationInputError):
        check_rule(rule, [{"Image": 1, "CommandLine": False}], [{"Image": 2, "CommandLine": True}])


def test_empty_required_field_rejected(corpora):
    pres, absent, _ = corpora
    with pytest.raises(EvaluationInputError):
        check_rule(
            _rule("good.yml"), pres, absent + [{"Image": "p\\powershell.exe", "CommandLine": ""}]
        )


# --- defect #1: adapter-key canonicalisation (torch-free) --------------------


def test_adapter_canonical_key_handles_different_names():
    from detection_verifier.adapter_utils import canonical_key

    a = "base_model.model.layers.0.self_attn.q_proj.lora_A.default.weight"
    b = "base_model.model.layers.0.self_attn.q_proj.lora_A.smoke.weight"
    assert (
        canonical_key(a)
        == canonical_key(b)
        == "base_model.model.layers.0.self_attn.q_proj.lora_A.weight"
    )


def test_adapter_canonical_key_lora_b_and_bias():
    from detection_verifier.adapter_utils import canonical_key

    assert canonical_key("x.lora_B.default.weight") == "x.lora_B.weight"
    assert canonical_key("x.lora_A.anything.bias") == "x.lora_A.bias"
    assert canonical_key("x.base_layer.weight") == "x.base_layer.weight"  # untouched


# --- defect #3: OS-enforced isolation boundary -------------------------------


def test_isolation_kills_overrunning_candidate():
    import time

    from detection_verifier.isolation import CandidateTimeout, run_isolated

    t0 = time.monotonic()
    with pytest.raises(CandidateTimeout):
        run_isolated(time.sleep, (5,), timeout_s=0.3)
    assert time.monotonic() - t0 < 2.0  # actually killed, did not wait 5s


def test_isolation_returns_fast_result():
    from detection_verifier.isolation import run_isolated

    assert run_isolated(abs, (-7,), timeout_s=2.0) == 7


def test_unused_selection_not_evaluated(corpora):
    """Referenced-only evaluation: a rule with a pathological UNUSED selection is
    unaffected because that selection is never evaluated."""
    rule = {
        "logsource": {"category": "process_creation"},
        "detection": {
            "used": {
                "Image|endswith": "\\powershell.exe",
                "CommandLine|re": "(?i)-enc\\s+[A-Za-z0-9+/=]{16,}",
            },
            "unused": {"CommandLine|re": "(a+)+$"},  # never evaluated
            "condition": "used",
        },
    }
    v = _check(rule, corpora)
    assert v.metrics.execution_valid


def test_condition_depth_bounded():
    from detection_verifier.sigma_subset import MAX_PARSE_DEPTH

    cond = "(" * (MAX_PARSE_DEPTH + 2) + "a" + ")" * (MAX_PARSE_DEPTH + 2)
    doc = {
        "logsource": {"category": "process_creation"},
        "detection": {"a": {"Image|endswith": "\\p.exe"}, "condition": cond},
    }
    with pytest.raises(RuleSyntaxError):
        parse_rule(doc, SCHEMA_FIELDS)


# --- defect #2/#3 regressions kept -------------------------------------------


def test_boolean_precedence(corpora):
    v = _check(_rule("precedence.yml"), corpora)
    assert v.metrics.tp > 0


@pytest.mark.parametrize("cond", ["a!!!", "all of", "a and and b", "and a", "a or", "( a", "a )"])
def test_bad_conditions_rejected(cond):
    doc = {
        "logsource": {"category": "process_creation"},
        "detection": {"a": {"Image|endswith": "\\powershell.exe"}, "condition": cond},
    }
    with pytest.raises(RuleSyntaxError):
        parse_rule(doc, SCHEMA_FIELDS)


@pytest.mark.parametrize(
    "doc",
    [
        {"logsource": "nope", "detection": {"a": {"Image": "p"}, "condition": "a"}},
        {"logsource": {"category": "process_creation"}, "detection": "nope"},
        {"logsource": {"category": "process_creation"}, "detection": {"a": {}, "condition": "a"}},
    ],
)
def test_malformed_structure_rejected(doc):
    with pytest.raises(RuleSyntaxError):
        parse_rule(doc, SCHEMA_FIELDS)


def test_oversized_regex_rejected_before_execution():
    from detection_verifier.sigma_subset import MAX_REGEX_LEN

    doc = {
        "logsource": {"category": "process_creation"},
        "detection": {"s": {"CommandLine|re": "a" * (MAX_REGEX_LEN + 1)}, "condition": "s"},
    }
    with pytest.raises(RuleSyntaxError):
        parse_rule(doc, SCHEMA_FIELDS)


def test_oversized_rule_rejected():
    big = {f"s{i}": {"Image|endswith": "\\x.exe"} for i in range(40)}
    big["condition"] = "s0"
    doc = {"logsource": {"category": "process_creation"}, "detection": big}
    with pytest.raises(RuleSyntaxError):
        parse_rule(doc, SCHEMA_FIELDS)


def test_regex_timeout_contained(corpora, monkeypatch):
    import detection_verifier.sigma_subset as ss

    monkeypatch.setattr(
        ss._regex, "search", lambda *a, **k: (_ for _ in ()).throw(TimeoutError("x"))
    )
    pres, absent, oos = corpora
    doc = {
        "logsource": {"category": "process_creation"},
        "detection": {
            "s": {"Image|endswith": "\\powershell.exe", "CommandLine|re": "something"},
            "condition": "s",
        },
    }
    v = check_rule(doc, pres, absent, out_of_scope=oos)
    assert v.outcome == "FAILED" and any("timed out" in r for r in v.metrics.reasons)


def test_payload_blob_warns_and_fails_on_coverage(corpora):
    v = _check(_rule("payload_blob.yml"), corpora)
    assert v.outcome == "FAILED"
    assert any("suspected payload literal" in w for w in v.metrics.warnings)


def test_low_entropy_long_literal_not_flagged(corpora):
    pres, absent, oos = corpora
    doc = {
        "logsource": {"category": "process_creation"},
        "detection": {
            "s": {
                "Image|endswith": "\\powershell.exe",
                "CommandLine|contains": "aaaaaaaaaaaaaaaaaaaa",
            },
            "condition": "s",
        },
    }
    v = check_rule(doc, pres, absent, out_of_scope=oos)
    assert not any("payload literal" in w for w in v.metrics.warnings)


def test_certify_rejects_missing_and_dupes(corpora):
    pres, absent, _ = corpora
    seed = assurance.run_seed_suite(
        [("good", _rule("good.yml"), "VERIFIED"), ("good", _rule("good.yml"), "VERIFIED")],
        pres,
        absent,
    )
    ok, reasons = assurance.certify(seed)
    assert ok is False
    assert any("duplicate" in r for r in reasons) and any("missing mandatory" in r for r in reasons)


# --- defect #4 lint + metamorphic (kept) -------------------------------------


def test_lint_bypass_is_caught(corpora):
    v = _check(_rule("lint_bypass.yml"), corpora)
    assert v.metrics.has_behavioral_field is False


def test_metamorphic_incidentals_preserve_verdict(corpora):
    pres, absent, oos = corpora
    mutated = []
    for i, ev in enumerate(pres):
        e = dict(ev)
        e["User"] = f"R\\u{i}"
        e["ComputerName"] = f"H{i}"
        e["UtcTime"] = f"2026-01-0{i % 9 + 1}"
        mutated.append(e)
    v = check_rule(_rule("good.yml"), mutated, absent, out_of_scope=oos)
    assert v.metrics.coverage == 1.0


# --- assurance ---------------------------------------------------------------


def test_assurance_certifies(corpora):
    pres, absent, _ = corpora
    results = assurance.run_seed_suite(
        [("good", _rule("good.yml"), "VERIFIED"), ("trivial", _rule("trivial.yml"), "FAILED")],
        pres,
        absent,
    ) + [
        assurance.run_reference_rule_consistency(_rule("good.yml"), pres, absent),
        assurance.run_determinism(_rule("good.yml"), pres, absent),
    ]
    ok, reasons = assurance.certify(results)
    assert ok, reasons


def test_reference_consistency_planted_mislabel(corpora):
    pres, absent, _ = corpora
    clean = assurance.run_reference_rule_consistency(_rule("good.yml"), pres, absent)
    assert clean.passed
    poisoned = pres + [absent[0]]
    alarmed = assurance.run_reference_rule_consistency(_rule("good.yml"), poisoned, absent)
    assert not alarmed.passed
