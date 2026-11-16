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


def test_rejected_actions_count_toward_the_budget():
    """Astra finding 18, confirmed: the budget check used len(observations),
    incremented only on a SUCCESSFULLY processed action, so malformed/rejected
    lines were free retries that never consumed it — an attacker could send
    unlimited garbage and still have the full 16-action budget left afterward.
    Send 16 malformed lines directly (bypassing LabSession.action()'s
    client-side allowlist, to reach the worker's own counter), each correctly
    still rejected on its own shape error, then prove the budget itself is
    exhausted: a well-formed, otherwise-valid "discover" sent as the 17th
    attempt is now ALSO refused — purely for exhausting the budget, with no
    shape problem of its own. Under the old code this discover would have
    succeeded (16 "free" malformed attempts would never have been counted)."""
    session = LabSession([sys.executable, "-m", "lab.web_workflow.worker"])
    try:
        for _ in range(16):
            session.process.stdin.write('{"bogus": true}\n')
            session.process.stdin.flush()
            reply = session.receive()
            assert reply["error"] == "only a kind field is allowed"
        session.process.stdin.write('{"kind": "discover"}\n')
        session.process.stdin.flush()
        seventeenth = session.receive()
        assert seventeenth == {"error": "action budget exhausted"}
        # "finish" must still be accepted even though the budget is long spent.
        session.process.stdin.write('{"kind": "finish"}\n')
        session.process.stdin.flush()
        final = session.receive()
        assert final["task_success"] is False  # never attempted read_other
    finally:
        session.close()


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
