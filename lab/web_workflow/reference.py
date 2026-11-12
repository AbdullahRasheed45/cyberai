from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from .scenario import SCENARIO_ID
from .tools import BoundedWebTools
from .verifier import verify_defensive_retest, verify_offense


@dataclass(frozen=True)
class WorkflowRecord:
    trajectory_id: str
    case: str
    actions: list[dict]
    telemetry: list[dict]
    offensive_verdict: str
    defensive_verdict: str
    training_eligible: bool
    provenance: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _plan(case: str) -> list[dict]:
    target = SCENARIO_ID
    plans = {
        "success": [
            {"kind": "discover", "target": target},
            {"kind": "verify_authorization_boundary", "target": target, "subject": "other"},
        ],
        "failed": [
            {"kind": "discover", "target": target},
            {"kind": "verify_authorization_boundary", "target": target, "subject": "owner"},
        ],
        "pre_satisfied": [
            {"kind": "verify_authorization_boundary", "target": target, "subject": "other"}
        ],
        "patched_control": [
            {"kind": "verify_authorization_boundary", "target": target, "subject": "other"}
        ],
    }
    return plans[case]


def run_reference_case(case: str, plan: list[dict] | None = None) -> WorkflowRecord:
    tools = BoundedWebTools.for_case(case)
    before = tools.scenario.snapshot()
    executed = []
    for action in plan if plan is not None else _plan(case):
        executed.append({"kind": action["kind"], "result": tools.invoke(action)})
    after = tools.scenario.snapshot()
    offensive = verify_offense(before, executed, after)
    defensive = verify_defensive_retest(tools.scenario, offensive)
    provenance = {
        "source": "scripted_reference",
        "scenario_id": SCENARIO_ID,
        "scenario_version": "v1",
        "verifier_versions": ["offense-v1", "offense-shadow-v1"],
        "split": "development_reference_not_acceptance",
    }
    canonical = json.dumps({"case": case, "actions": executed, "before": before}, sort_keys=True)
    return WorkflowRecord(
        trajectory_id=hashlib.sha256(canonical.encode()).hexdigest(),
        case=case,
        actions=executed,
        telemetry=list(tools.scenario.telemetry),
        offensive_verdict=offensive,
        defensive_verdict=defensive,
        training_eligible=offensive == "VERIFIED" and defensive == "REMEDIATED",
        provenance=provenance,
    )
