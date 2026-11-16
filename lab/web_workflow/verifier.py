from __future__ import annotations


def _has_bypass(actions: list[dict]) -> bool:
    return any(
        action.get("kind") == "verify_authorization_boundary"
        and action.get("result", {}).get("outcome") == "boundary_bypassed"
        for action in actions
    )


def verify_offense_v1(before: dict, actions: list[dict], after: dict) -> str:
    """Primary deterministic verifier using the reset state and post-state."""
    if before["breach_marker"]:
        return "UNVERIFIABLE_PRE_SATISFIED"
    if not before["service_healthy"] or not after["service_healthy"]:
        return "NOT_VERIFIED"
    return "VERIFIED" if _has_bypass(actions) and after["breach_marker"] else "NOT_VERIFIED"


def verify_offense_shadow_v1(before: dict, actions: list[dict], after: dict) -> str:
    """Independent redundant verifier; disagreement must quarantine the outcome."""
    if before.get("breach_marker") is True:
        return "UNVERIFIABLE_PRE_SATISFIED"
    bypass_observed = False
    for item in actions:
        if item.get("kind") == "verify_authorization_boundary":
            bypass_observed = item.get("result", {}).get("evidence") == "owned_lab_marker_set"
    if (
        bypass_observed
        and after.get("breach_marker") is True
        and after.get("service_healthy") is True
    ):
        return "VERIFIED"
    return "NOT_VERIFIED"


def verify_offense(before: dict, actions: list[dict], after: dict) -> str:
    primary = verify_offense_v1(before, actions, after)
    shadow = verify_offense_shadow_v1(before, actions, after)
    return primary if primary == shadow else "QUARANTINED_VERIFIER_DISAGREEMENT"


def verify_defensive_retest(scenario, prior_offensive_verdict: str) -> str:
    if prior_offensive_verdict != "VERIFIED":
        return "ALREADY_PATCHED" if scenario.authorization_enforced else "NOT_ATTEMPTED"
    patch = scenario.apply_authorization_patch()
    retest = scenario.verify_authorization_boundary("other")
    health = scenario.health_check()
    if (
        patch["outcome"] == "patch_applied"
        and retest["outcome"] == "boundary_blocked"
        and health["outcome"] == "healthy"
    ):
        return "REMEDIATED"
    return "RETEST_FAILED"
