import os
import subprocess
import sys

from rental.live_web import LabSession


def test_oversized_line_ends_session_without_parsing():
    session = LabSession([sys.executable, "-m", "lab.web_workflow.worker"])
    try:
        session.process.stdin.write("x" * 8193 + "\n")
        session.process.stdin.flush()
        result = session.receive()
        assert result["failure_category"] == "INPUT_TOO_LARGE"
        assert result["task_success"] is False
        session.process.wait(timeout=3)
    finally:
        session.close()


def test_partial_line_has_a_deadline_and_returns_terminal_evidence():
    session = LabSession([sys.executable, "-m", "lab.web_workflow.worker", "--idle-timeout", "0.1"])
    try:
        session.process.stdin.write('{"kind":')
        session.process.stdin.flush()
        result = session.receive()
        assert result["failure_category"] == "TIMEOUT"
        assert result["task_success"] is False
    finally:
        session.close()


def test_forced_command_refuses_unexpected_original_command():
    result = subprocess.run(
        [sys.executable, "-m", "lab.web_workflow.worker", "--from-ssh"],
        input="",
        capture_output=True,
        text=True,
        timeout=5,
        env=dict(os.environ, SSH_ORIGINAL_COMMAND="sh -c whoami"),
    )
    assert result.returncode == 2
    assert "SSH command refused" in result.stdout


def test_duplicate_keys_are_rejected_and_counted():
    session = LabSession([sys.executable, "-m", "lab.web_workflow.worker"])
    try:
        session.process.stdin.write('{"kind":"discover","kind":"finish"}\n')
        session.process.stdin.flush()
        assert session.receive() == {"error": "duplicate JSON key"}
        final = session.action("finish")
        assert final["actions_attempted"] == 2
        assert final["task_success"] is False
    finally:
        session.close()
