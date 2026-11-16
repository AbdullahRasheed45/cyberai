"""Reward-boundary regressions: Boolean syntax must not fake attribution."""

from detection_verifier.checker import WEB_REQUEST_SCHEMA, check_rule


def evaluate(condition, selections, *, distinct_behavior=False):
    base = {"Method": "GET", "UriPath": "/same", "QueryString": "", "Body": ""}
    positive = dict(base, RequestId="attack-id")
    negative = dict(base, RequestId="benign-id")
    if distinct_behavior:
        positive["UriPath"] = "/attack"
    rule = {
        "title": "counterfactual regression",
        "logsource": {"category": "web_request"},
        "detection": dict(selections, condition=condition),
    }
    return check_rule(rule, [positive], [negative], schema=WEB_REQUEST_SCHEMA)


def test_negated_identifier_cannot_supply_all_discrimination():
    result = evaluate(
        "pad and not identity",
        {"pad": {"Method": "GET"}, "identity": {"RequestId": "benign-id"}},
    )
    assert result.outcome == "FAILED"
    assert result.metrics.behavior_attributable is False


def test_impossible_identifier_branch_preserves_behavioral_verdict():
    result = evaluate(
        "good or (a and b)",
        {
            "good": {"UriPath": "/attack"},
            "a": {"RequestId": "a"},
            "b": {"RequestId": "b"},
        },
        distinct_behavior=True,
    )
    assert result.outcome == "VERIFIED"


def test_two_incidental_fields_are_varied_together():
    result = evaluate(
        "pad and not (a or b)",
        {
            "pad": {"Method": "GET"},
            "a": {"RequestId": "benign-id"},
            "b": {"Host": "benign-host"},
        },
    )
    assert result.outcome == "FAILED"


def test_counterfactual_budget_exhaustion_cannot_verify(monkeypatch):
    import detection_verifier.sigma_subset as subset

    monkeypatch.setattr(subset, "MAX_COUNTERFACTUAL_ASSIGNMENTS", 1)
    result = evaluate(
        "good and identity",
        {"good": {"UriPath": "/attack"}, "identity": {"RequestId": "attack-id"}},
        distinct_behavior=True,
    )
    assert result.outcome == "FAILED"
    assert not result.metrics.execution_valid
    assert any("assignment budget" in reason for reason in result.metrics.reasons)
