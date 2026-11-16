from __future__ import annotations

from dataclasses import dataclass, field

SCENARIO_ID = "owned-web-authz-boundary-v1"
CASES = frozenset({"success", "failed", "pre_satisfied", "patched_control"})


@dataclass
class ResettableWebScenario:
    """A symbolic owned-lab authorization-boundary scenario.

    It deliberately models state transitions rather than contacting a service.
    The only accepted target is this manifest's scenario ID.
    """

    case: str
    authorization_enforced: bool
    breach_marker: bool
    service_healthy: bool = True
    telemetry: list[dict] = field(default_factory=list)

    @classmethod
    def reset(cls, case: str) -> ResettableWebScenario:
        if case not in CASES:
            raise ValueError(f"unknown reference case: {case}")
        if case == "pre_satisfied":
            return cls(case=case, authorization_enforced=False, breach_marker=True)
        if case == "patched_control":
            return cls(case=case, authorization_enforced=True, breach_marker=False)
        return cls(case=case, authorization_enforced=False, breach_marker=False)

    def snapshot(self) -> dict:
        return {
            "scenario_id": SCENARIO_ID,
            "authorization_enforced": self.authorization_enforced,
            "breach_marker": self.breach_marker,
            "service_healthy": self.service_healthy,
        }

    def discover(self) -> dict:
        return {"outcome": "route_discovered", "route_label": "owned-profile"}

    def verify_authorization_boundary(self, subject: str) -> dict:
        if subject not in {"owner", "other"}:
            raise ValueError("subject must be owner or other")
        event = {
            "Method": "GET",
            "UriPath": "/owned-profile",
            "QueryString": f"account_id=lab-{subject}",
            "Body": "",
            "scenario_id": SCENARIO_ID,
            "subject": subject,
        }
        self.telemetry.append(event)
        if subject == "other" and not self.authorization_enforced:
            self.breach_marker = True
            return {"outcome": "boundary_bypassed", "evidence": "owned_lab_marker_set"}
        return {"outcome": "boundary_blocked", "evidence": "no_cross_account_access"}

    def apply_authorization_patch(self) -> dict:
        self.authorization_enforced = True
        return {"outcome": "patch_applied", "service_healthy": self.service_healthy}

    def health_check(self) -> dict:
        return {"outcome": "healthy" if self.service_healthy else "unhealthy"}
