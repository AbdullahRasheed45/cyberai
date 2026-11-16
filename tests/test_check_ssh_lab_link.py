"""The SSH two-machine link rehearsal (Astra finding 23): the reference
rehearsal script never read LAB_SSH_HOST and always ran the worker locally,
so it could not have told a working link from a completely unreachable lab
laptop. This script fixes that, and these tests prove the fix: a worker that
reports the SAME hostname as this process is refused, not silently accepted.
"""

from __future__ import annotations

import importlib.util
import socket
import sys
from pathlib import Path

import pytest

from rental.live_web import LabSession

spec = importlib.util.spec_from_file_location(
    "check_ssh_lab_link", Path("scripts/rental/check_ssh_lab_link.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_ssh_argv_matches_the_real_web_workload_transport():
    """Same shape as scripts/rental/46_live_web_workflow.py's SSH invocation,
    so a passing rehearsal is evidence about the transport the real workload
    will actually use — pinned here so the two cannot silently drift apart."""
    argv = mod.ssh_argv("cyberai-lab")
    assert argv == [
        "ssh",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "StrictHostKeyChecking=yes",
        "cyberai-lab",
        "python3",
        "-m",
        "lab.web_workflow.worker",
    ]


@pytest.mark.parametrize("bad", ["", "-x", "has space", "semi;colon", "a" * 65])
def test_validate_host_alias_rejects_anything_not_a_plain_alias(bad):
    with pytest.raises(ValueError):
        mod.validate_host_alias(bad)


def test_validate_host_alias_accepts_a_configured_alias():
    assert mod.validate_host_alias("cyberai-lab") == "cyberai-lab"


def test_verify_remote_rejects_a_worker_that_ran_locally():
    """The exact false-pass this script exists to catch: a worker reporting
    THIS machine's own hostname (or no hostname at all) did not go over SSH,
    whatever the SSH command line claimed to do."""
    with pytest.raises(mod.LinkNotExercisedError):
        mod.verify_remote("spark-dev-box", local_host="spark-dev-box")
    with pytest.raises(mod.LinkNotExercisedError):
        mod.verify_remote(None, local_host="spark-dev-box")
    with pytest.raises(mod.LinkNotExercisedError):
        mod.verify_remote("", local_host="spark-dev-box")


def test_verify_remote_accepts_a_genuinely_different_host():
    result = mod.verify_remote("cyberai-lab-laptop", local_host="spark-dev-box")
    assert result == "cyberai-lab-laptop"


def test_verify_remote_checks_the_configured_host_identity():
    with pytest.raises(mod.LinkNotExercisedError):
        mod.verify_remote("unexpected-host", "spark", expected_host="lab-laptop")
    assert mod.verify_remote("lab-laptop", "spark", expected_host="lab-laptop") == "lab-laptop"


def test_a_genuinely_local_worker_is_caught_end_to_end():
    """No real SSH involved: run the ACTUAL worker locally and confirm the
    whole chain — its reported host, through verify_remote — correctly
    identifies this as not having exercised any link, exactly the case a
    local-only rehearsal (the original bug) would have let pass silently."""
    session = LabSession([sys.executable, "-m", "lab.web_workflow.worker"])
    try:
        assert session.ready_info["host"] == socket.gethostname()
        with pytest.raises(mod.LinkNotExercisedError):
            mod.verify_remote(session.ready_info["host"], local_host=socket.gethostname())
    finally:
        session.close()


def test_scripted_actions_drives_the_fixed_reference_sequence():
    complete = mod.scripted_actions()
    kinds = [__import__("json").loads(complete([])["content"])["kind"] for _ in range(4)]
    assert kinds == ["discover", "read_owner", "read_other", "finish"]
    with pytest.raises(StopIteration):
        complete([])
