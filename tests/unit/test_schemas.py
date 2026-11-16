from datetime import UTC, datetime

from libs.schemas import Outcome, Provenance, Trajectory, TrajectoryStep, Verdict


def test_trajectory_requires_provenance():
    p = Provenance(scenario_id="s1", generating_adapter="gen_0", timestamp=datetime.now(UTC))
    t = Trajectory(
        id="t1",
        agent_config_id="a1",
        adapter_id="gen_0",
        domain="web",
        difficulty_tier=1,
        task_class="exploitation",
        steps=[TrajectoryStep(action="final", content="done")],
        raw_output="done",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        provenance=p,
    )
    assert t.provenance.generating_adapter == "gen_0"


def test_verdict_roundtrip():
    v = Verdict(
        trajectory_id="t1",
        task_class="exploitation",
        outcome=Outcome.VERIFIED,
        detail={"uid": 0},
        verifier_name="web.exploitation",
        verifier_version="1.0",
        checked_at=datetime.now(UTC),
    )
    assert Verdict.model_validate_json(v.model_dump_json()).outcome == Outcome.VERIFIED
