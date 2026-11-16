import subprocess
import sys

import pytest

from rental.exclusive import trial_lock


def test_lock_refuses_concurrent_process_then_releases(tmp_path):
    path = tmp_path / "trial.lock"
    code = "from rental.exclusive import trial_lock; import sys\nwith trial_lock(sys.argv[1]): pass"
    with trial_lock(path):
        result = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True)
        assert result.returncode != 0
        assert b"another trial operation" in result.stderr
    with trial_lock(path):
        pass
    assert path.exists()  # do not unlink a lock inode while a waiter may have it open


def test_lock_releases_after_failure(tmp_path):
    path = tmp_path / "trial.lock"
    with pytest.raises(ValueError), trial_lock(path):
        raise ValueError("trial failed")
    with trial_lock(path):
        pass


def test_cleanup_does_not_stop_a_refused_existing_server():
    from rental import orchestrate
    from tests.test_orchestration import _ex, _Mock, _rc

    mock = _Mock()

    def refuse(name, argv):
        raise RuntimeError("existing server")

    mock.start = refuse
    with pytest.raises(RuntimeError, match="existing server"):
        orchestrate.run(_rc(), _ex(mock))
    assert mock.stopped == []


def test_training_failure_cleans_named_training_container():
    from rental import orchestrate
    from tests.test_orchestration import _ex, _Mock, _rc

    mock = _Mock("train_fail")
    with pytest.raises(RuntimeError):
        orchestrate.run(_rc(), _ex(mock))
    assert "cyberai_train_testrun" in mock.stopped
