import sys
import time
from pathlib import Path

from rental.live_web import LabSession, run_loop


def test_model_wait_does_not_spend_partial_line_deadline():
    session = LabSession([sys.executable, "-m", "lab.web_workflow.worker"])
    try:
        # Previous default killed a healthy session before a valid 120s model reply.
        assert session.ready_info["idle_timeout_s"] > 120
        assert session.ready_info["partial_timeout_s"] == 10
        time.sleep(10.2)
        assert session.action("discover")["identity"] == "owner"
    finally:
        session.close()


def test_partial_timeout_is_independent_of_model_wait():
    session = LabSession(
        [
            sys.executable,
            "-m",
            "lab.web_workflow.worker",
            "--idle-timeout",
            "30",
            "--partial-timeout",
            "0.1",
        ]
    )
    try:
        session.process.stdin.write('{"kind":')
        session.process.stdin.flush()
        started = time.monotonic()
        assert session.receive()["failure_category"] == "TIMEOUT"
        assert time.monotonic() - started < 2
    finally:
        session.close()


def test_failed_model_action_is_counted():
    session = LabSession([sys.executable, "-m", "lab.web_workflow.worker"])
    try:
        result = run_loop(
            session,
            lambda _: {
                "content": "not JSON",
                "prompt_tokens": 11,
                "completion_tokens": 3,
            },
        )
        assert result["task_success"] is False
        assert result["model_calls"] == 1
        assert result["action_attempts"] == 1
        assert result["action_count"] == 0
        assert result["model_usage"]["completion_tokens"] == 3
    finally:
        session.close()


def test_training_config_override_reaches_container(tmp_path, monkeypatch):
    import yaml

    from rental.plan import resolve, train_argv
    from tests.test_orchestration import _good_freeze

    data = yaml.safe_load(Path("configs/training.yaml").read_text())
    data["lora_rank"] = 32
    freeze = _good_freeze()
    (tmp_path / "custom.yaml").write_text(yaml.safe_dump(data))
    monkeypatch.chdir(tmp_path)
    rc = resolve(freeze, env={"MODEL_PATH": "/m", "TRAINING_CONFIG": "custom.yaml"})
    assert rc.hparams.lora_rank == 32
    assert "TRAINING_CONFIG=/work/custom.yaml" in train_argv(rc)


def test_real_and_scripted_handshake_refuses_wrong_host_or_protocol(monkeypatch):
    import pytest

    from rental.live_web import validate_remote_worker

    monkeypatch.setattr("rental.live_web.socket.gethostname", lambda: "spark")
    valid = {"host": "lab", "scenario": "owned-http-authz-v1", "protocol": 1}
    validate_remote_worker(valid, "lab")
    for bad in (
        {**valid, "host": "spark"},
        {**valid, "protocol": 2},
        {**valid, "scenario": "other"},
    ):
        with pytest.raises(ValueError):
            validate_remote_worker(bad, "lab")
    with pytest.raises(ValueError):
        validate_remote_worker(valid, None)


def test_web_baseline_runs_before_training_and_preserves_separate_evidence():
    from rental import orchestrate, plan
    from tests.test_orchestration import _ex, _Mock, _rc

    rc = _rc()
    _, env = plan.baseline_workload_cmd(rc)
    assert env["SERVED_MODEL"] == rc.base_served_id
    assert env["ARTIFACT_DIR"] == rc.artifact_dir + "/baseline"
    result = orchestrate.run(rc, _ex(_Mock()))
    assert result["phases"].index("baseline_workload") < result["phases"].index("train")
