from __future__ import annotations

from .scenario import SCENARIO_ID, ResettableWebScenario


class ToolRejected(ValueError):
    """Raised when an agent plan attempts to leave the bounded lab interface."""


class BoundedWebTools:
    """Strict action allow-list; no network, subprocess, or arbitrary arguments."""

    _ALLOWED = {
        "discover",
        "verify_authorization_boundary",
        "apply_authorization_patch",
        "health_check",
    }

    def __init__(self, scenario: ResettableWebScenario):
        self.scenario = scenario

    @classmethod
    def for_case(cls, case: str) -> BoundedWebTools:
        return cls(ResettableWebScenario.reset(case))

    def invoke(self, action: dict) -> dict:
        if not isinstance(action, dict) or set(action) - {"kind", "target", "subject"}:
            raise ToolRejected("action must contain only kind, target, and optional subject")
        if action.get("target") != SCENARIO_ID:
            raise ToolRejected("action target is outside the owned scenario")
        kind = action.get("kind")
        if kind not in self._ALLOWED:
            raise ToolRejected("action kind is not authorized")
        if kind == "discover":
            return self.scenario.discover()
        if kind == "verify_authorization_boundary":
            return self.scenario.verify_authorization_boundary(action.get("subject", "other"))
        if kind == "apply_authorization_patch":
            return self.scenario.apply_authorization_patch()
        return self.scenario.health_check()
