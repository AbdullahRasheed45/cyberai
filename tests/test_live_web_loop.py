import sys

import pytest

from rental.live_web import LabSession, run_loop


@pytest.mark.parametrize(
    "case,success",
    [("success", True), ("failed", False), ("pre_satisfied", False), ("patched_control", False)],
)
def test_iterative_worker_reference(case, success):
    session = LabSession([sys.executable, "-m", "lab.web_workflow.worker", "--case", case])
    sequence = iter(
        ["discover", "read_owner"] + ([] if case == "failed" else ["read_other"]) + ["finish"]
    )

    def complete(messages):
        assert messages
        return {
            "content": '{"kind":"' + next(sequence) + '"}',
            "prompt_tokens": 10,
            "completion_tokens": 3,
        }

    try:
        record = run_loop(session, complete)
    finally:
        session.close()
    assert record["task_success"] is success
    assert record["model_usage"]["completion_tokens"] == record["action_count"] * 3
    assert record["runtime_s"] > 0


def test_rejects_arbitrary_model_action():
    session = LabSession([sys.executable, "-m", "lab.web_workflow.worker"])
    try:
        record = run_loop(
            session,
            lambda messages: {
                "content": '{"kind":"shell"}',
                "prompt_tokens": 1,
                "completion_tokens": 1,
            },
        )
    finally:
        session.close()
    assert record["task_success"] is False
    assert record["failure_category"] == "ValueError"


def test_long_context_contains_real_http_background_events():
    session = LabSession(
        [sys.executable, "-m", "lab.web_workflow.worker", "--background-requests", "128"]
    )
    try:
        result = session.action("read_activity")
        assert len(result["body"]["owner_activity"]) == 128
        assert len(str(result)) > 10_000
        assert session.action("read_other")["body"]["account"] == "other"
        assert session.action("finish")["task_success"] is True
    finally:
        session.close()
