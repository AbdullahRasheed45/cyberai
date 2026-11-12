from __future__ import annotations

import json

import pytest

from lab.web_workflow.reference import run_reference_case
from lab.web_workflow.store import TrajectoryStore
from lab.web_workflow.tools import BoundedWebTools, ToolRejected
from rental.offensive_web import parse_action_plan
from rental.plan import ResolvedConfig, workload_cmd
from rental.web_pilot import build_web_offensive_pilot_examples


@pytest.mark.parametrize(
    ("case", "offensive", "defensive", "training_eligible"),
    [
        ("success", "VERIFIED", "REMEDIATED", True),
        ("failed", "NOT_VERIFIED", "NOT_ATTEMPTED", False),
        ("pre_satisfied", "UNVERIFIABLE_PRE_SATISFIED", "NOT_ATTEMPTED", False),
        ("patched_control", "NOT_VERIFIED", "ALREADY_PATCHED", False),
    ],
)
def test_scripted_reference_cases_have_distinct_deterministic_verdicts(
    case, offensive, defensive, training_eligible
):
    record = run_reference_case(case)

    assert record.offensive_verdict == offensive
    assert record.defensive_verdict == defensive
    assert record.training_eligible is training_eligible
    assert record.provenance["scenario_id"] == "owned-web-authz-boundary-v1"
    assert record.provenance["verifier_versions"] == ["offense-v1", "offense-shadow-v1"]
    assert record.telemetry


def test_tool_boundary_rejects_external_targets_and_unknown_actions():
    tools = BoundedWebTools.for_case("success")

    with pytest.raises(ToolRejected):
        tools.invoke({"kind": "verify_authorization_boundary", "target": "https://example.com"})
    with pytest.raises(ToolRejected):
        tools.invoke({"kind": "shell", "target": "owned-web-authz-boundary-v1"})


def test_trajectory_store_writes_provenance_tagged_jsonl(tmp_path):
    store = TrajectoryStore(tmp_path / "trajectories.jsonl")
    expected = run_reference_case("success")
    store.append(expected)

    row = json.loads((tmp_path / "trajectories.jsonl").read_text(encoding="utf-8"))
    assert row["trajectory_id"] == expected.trajectory_id
    assert row["provenance"]["source"] == "scripted_reference"
    assert row["training_eligible"] is True


def test_qwen_action_plan_is_strictly_bounded_to_the_owned_lab():
    plan = parse_action_plan(
        '{"actions":[{"kind":"discover","target":"owned-web-authz-boundary-v1"},'
        '{"kind":"verify_authorization_boundary","target":"owned-web-authz-boundary-v1","subject":"other"}]}'
    )
    assert len(plan) == 2
    with pytest.raises(ValueError):
        parse_action_plan('{"actions":[{"kind":"shell","target":"owned-web-authz-boundary-v1"}]}')


def test_web_rental_workload_uses_offensive_workflow_runner():
    config = ResolvedConfig(
        vllm_image="vllm@sha256:" + "a" * 64,
        unsloth_image="unsloth@sha256:" + "b" * 64,
        host_repo="/repo",
        host_model_path="/model",
        host_adapter_path="/adapter",
        train_repo="base",
        train_commit="c" * 40,
        serving_repo="serve",
        serving_commit="d" * 40,
        serving_quant="FP8",
        serving_provenance="official",
        dependencies=(),
        run_id="test",
    )
    command, env = workload_cmd(config)
    assert command[-1] == "scripts/rental/45_web_offensive_workflow.py"
    assert env["WORKLOAD_DOMAIN"] == "web"


def test_long_training_trace_is_development_only_and_not_acceptance_data():
    row = build_web_offensive_pilot_examples()[0]
    assert row["metadata"]["acceptance_data_read"] is False
    assert row["metadata"]["long_context_repetition"] == 24
    assert len(row["messages"][0]["content"]) > 10_000
