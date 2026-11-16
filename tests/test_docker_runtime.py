"""Docker runtime flags: one source for every container, measured per provider.

Enverge runs the SSH session in an unprivileged sandbox with Docker-in-Docker where
the NVIDIA runtime is in no-cgroups mode, so `--gpus all` fails and the lifecycle
must switch flags via DOCKER_* env without code changes.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from rental import docker_runtime as dr
from rental import plan
from rental.probe import probe_argv
from tests.test_orchestration import _good_freeze, _rc

ENVERGE = {
    "DOCKER_GPU_MODE": "runtime",
    "DOCKER_IPC_HOST": "0",
    "DOCKER_SHM_SIZE": "16g",
    "DOCKER_ULIMITS": "0",
    "DOCKER_NETWORK": "host",
}


def test_defaults_are_the_standard_docker_flags():
    assert dr.gpu_args({}) == ["--gpus", "all"]
    assert dr.ipc_args({}) == ["--ipc=host"]
    assert dr.ulimit_args({}) == ["--ulimit", "memlock=-1", "--ulimit", "stack=67108864"]
    assert dr.network_args(8000, {}) == ["-p", "127.0.0.1:8000:8000"]
    assert dr.server_bind_host({}) == "0.0.0.0"


def test_enverge_modes():
    assert dr.gpu_args({"DOCKER_GPU_MODE": "runtime"}) == [
        "--runtime",
        "nvidia",
        "-e",
        "NVIDIA_VISIBLE_DEVICES=all",
        "-e",
        "NVIDIA_DRIVER_CAPABILITIES=compute,utility",
    ]
    assert dr.gpu_args({"DOCKER_GPU_MODE": "cdi"}) == ["--device", "nvidia.com/gpu=all"]
    assert dr.ipc_args(ENVERGE) == ["--shm-size", "16g"]
    assert dr.ulimit_args(ENVERGE) == []
    assert dr.network_args(8000, ENVERGE) == ["--network", "host"]
    assert dr.server_bind_host(ENVERGE) == "127.0.0.1"  # host networking: loopback only


@pytest.mark.parametrize(
    "bad", [{"DOCKER_GPU_MODE": "magic"}, {"DOCKER_NETWORK": "bridge"}, {"DOCKER_ULIMITS": "maybe"}]
)
def test_invalid_settings_fail_loudly(bad):
    with pytest.raises(dr.DockerRuntimeError):
        dr.describe(bad)


def test_every_container_uses_the_measured_flags(monkeypatch):
    for key, value in ENVERGE.items():
        monkeypatch.setenv(key, value)
    rc = _rc()
    base, lora, train = plan.base_serve_argv(rc), plan.lora_serve_argv(rc), plan.train_argv(rc)
    for argv in (base, lora, train, probe_argv("img")):
        assert "--gpus" not in argv
        assert argv[argv.index("--runtime") + 1] == "nvidia"
        assert "NVIDIA_VISIBLE_DEVICES=all" in argv
    for argv in (base, lora):
        assert "--network" in argv and "-p" not in argv
        assert argv[argv.index("--host") + 1] == "127.0.0.1"
        assert "--shm-size" in argv and "--ipc=host" not in argv
    assert "--ulimit" not in train and "--shm-size" in train


def test_resolve_rejects_bad_docker_settings():
    with pytest.raises(plan.FreezeInvalid, match="docker runtime"):
        plan.resolve(_good_freeze(), env={"MODEL_PATH": "/m", "DOCKER_GPU_MODE": "nope"})


def test_cli_prints_shell_flags_for_bash_scripts():
    env = {"DOCKER_GPU_MODE": "cdi", "PATH": ""}
    out = subprocess.run(
        [sys.executable, "-m", "rental.docker_runtime", "gpu"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert out.returncode == 0 and out.stdout.strip() == "--device nvidia.com/gpu=all"
    bad = subprocess.run(
        [sys.executable, "-m", "rental.docker_runtime", "gpu"],
        capture_output=True,
        text=True,
        env={"DOCKER_GPU_MODE": "x"},
    )
    assert bad.returncode == 2


# --- in-container GPU name: tagged, banner-proof, torch fallback ----------------


def test_gpu_name_parsed_from_tagged_line_despite_banner():
    banner = "== vLLM ==\nNVIDIA Release 26.10\nCopyright (c) NVIDIA CORPORATION\n"
    assert dr.parse_gpu_name(banner + "CYBERAI_GPU_NAME:NVIDIA GB10, 580.95, 12.1\n") == (
        "NVIDIA GB10, 580.95, 12.1"
    )
    assert dr.parse_gpu_name(banner + "CYBERAI_GPU_NAME:NO_CUDA\n") is None
    assert dr.parse_gpu_name(banner + "CYBERAI_GPU_NAME:NONE\n") is None
    assert dr.parse_gpu_name(banner) is None  # no tagged line = no answer


def test_gpu_name_argv_runs_shell_inside_the_image():
    argv = dr.gpu_name_argv("img@sha256:x", ["--runtime", "nvidia"])
    assert argv[:5] == ["docker", "run", "--rm", "--runtime", "nvidia"]
    assert argv[-4:] == ["img@sha256:x", "sh", "-c", dr.GPU_NAME_SHELL]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell; runs in Linux CI")
def test_gpu_name_shell_prefers_nvidia_smi_then_reports_none(tmp_path):
    fake = tmp_path / "nvidia-smi"
    fake.write_text("#!/bin/sh\necho 'NVIDIA GB10, 580.95, 12.1'\n")
    fake.chmod(0o755)
    env = {"PATH": f"{tmp_path}:/usr/bin:/bin"}
    out = subprocess.run(["sh", "-c", dr.GPU_NAME_SHELL], capture_output=True, text=True, env=env)
    assert dr.parse_gpu_name(out.stdout) == "NVIDIA GB10, 580.95, 12.1"
    fake.unlink()  # no nvidia-smi and (in CI) no torch: an explicit "no GPU" answer
    out = subprocess.run(["sh", "-c", dr.GPU_NAME_SHELL], capture_output=True, text=True, env=env)
    assert "CYBERAI_GPU_NAME:" in out.stdout and dr.parse_gpu_name(out.stdout) is None


# --- interruption: SIGTERM becomes a normal failure with cleanup ---------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals; runs in Linux CI")
def test_sigterm_becomes_terminated_exception():
    script = (
        "import os, signal, time\n"
        "from rental.orchestrate import Terminated, install_termination_handler\n"
        "install_termination_handler()\n"
        "try:\n"
        "    os.kill(os.getpid(), signal.SIGTERM)\n"
        "    time.sleep(5)\n"
        "except Terminated as exc:\n"
        "    print('CAUGHT', exc)\n"
    )
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=20)
    assert "CAUGHT received signal SIGTERM" in out.stdout


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups; runs in Linux CI")
def test_tracker_timeout_gives_the_command_a_grace_period(tmp_path):
    import json

    done = tmp_path / "cleaned_up"
    child = (
        "import signal, sys, time, pathlib\n"
        "def stop(*a):\n"
        "    time.sleep(1)  # simulated cleanup/export\n"
        f"    pathlib.Path({str(done)!r}).write_text('ok')\n"
        "    sys.exit(3)\n"
        "signal.signal(signal.SIGTERM, stop)\n"
        "time.sleep(60)\n"
    )
    out = tmp_path / "t.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/rental/track_command.py",
            "--out",
            str(out),
            "--timeout",
            "1",
            "--grace",
            "20",
            "--",
            sys.executable,
            "-c",
            child,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    record = json.loads(out.read_text())
    assert done.read_text() == "ok"  # cleanup finished inside the grace period
    assert record["state"] == "TIMED_OUT" and record["exit_code"] == 3
    assert not record.get("killed_after_grace")


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups; runs in Linux CI")
def test_tracker_kills_after_grace_if_command_ignores_sigterm(tmp_path):
    import json

    child = "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)\n"
    out = tmp_path / "t.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/rental/track_command.py",
            "--out",
            str(out),
            "--timeout",
            "1",
            "--grace",
            "2",
            "--",
            sys.executable,
            "-c",
            child,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    record = json.loads(out.read_text())
    assert record["killed_after_grace"] is True and record["state"] == "TIMED_OUT"


# --- forgetting to `source docker_env.sh` in a new terminal is caught -----------


def _measured(tmp_path):
    path = tmp_path / "docker_env.sh"
    path.write_text(
        "# Generated\nexport DOCKER_GPU_MODE=runtime\nexport DOCKER_NETWORK=host\n",
        encoding="utf-8",
    )
    return path


def test_unsourced_measured_settings_are_detected(tmp_path):
    path = _measured(tmp_path)
    assert dr.read_measured(path) == {"DOCKER_GPU_MODE": "runtime", "DOCKER_NETWORK": "host"}
    assert dr.unsourced_settings({}, path) == ["DOCKER_GPU_MODE=runtime", "DOCKER_NETWORK=host"]
    sourced = {"DOCKER_GPU_MODE": "runtime", "DOCKER_NETWORK": "host"}
    assert dr.unsourced_settings(sourced, path) == []
    assert dr.unsourced_settings({}, tmp_path / "absent.sh") == []  # standard host: nothing to do


def test_lifecycle_refuses_to_start_without_sourced_settings(tmp_path, monkeypatch):
    path = _measured(tmp_path)
    monkeypatch.setattr(dr, "MEASURED_ENV_FILE", str(path))  # absolute: join() keeps it
    with pytest.raises(plan.FreezeInvalid, match="source"):
        plan.resolve(_good_freeze(), env={"MODEL_PATH": "/m", "RUN_ID": "r1"})
    env = {
        "MODEL_PATH": "/m",
        "RUN_ID": "r1",
        "DOCKER_GPU_MODE": "runtime",
        "DOCKER_NETWORK": "host",
    }
    assert plan.resolve(_good_freeze(), env=env).run_id == "r1"


def test_cli_check_fails_until_sourced(tmp_path):
    (tmp_path / "artifacts" / "docker_runtime").mkdir(parents=True)
    _measured(tmp_path / "artifacts" / "docker_runtime")
    import os

    repo = os.getcwd()
    base = {"PATH": "", "PYTHONPATH": repo}
    run = lambda env: subprocess.run(  # noqa: E731
        [sys.executable, "-m", "rental.docker_runtime", "check"],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    missing = run(base)
    assert missing.returncode == 3 and "source artifacts/docker_runtime/docker_env.sh" in (
        missing.stderr
    )
    ok = run({**base, "DOCKER_GPU_MODE": "runtime", "DOCKER_NETWORK": "host"})
    assert ok.returncode == 0


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals; runs in Linux CI")
def test_second_sigterm_does_not_interrupt_cleanup():
    """`uv run` forwards SIGTERM on top of the process-group signal: two deliveries."""
    script = (
        "import os, signal, time\n"
        "from rental.orchestrate import Terminated, install_termination_handler\n"
        "install_termination_handler()\n"
        "try:\n"
        "    os.kill(os.getpid(), signal.SIGTERM)\n"
        "    time.sleep(5)\n"
        "except Terminated:\n"
        "    os.kill(os.getpid(), signal.SIGTERM)  # second delivery during cleanup\n"
        "    time.sleep(0.2)\n"
        "    print('CLEANUP_FINISHED')\n"
    )
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=20)
    assert "CLEANUP_FINISHED" in out.stdout


def test_lineage_comparison_ignores_repo_id_case():
    from rental.freeze import validate_lineage

    assert (
        validate_lineage(
            "unsloth/qwen3-30b-a3b-instruct-2507", "unsloth/Qwen3-30B-A3B-Instruct-2507", "a" * 40
        )
        == []
    )
    assert validate_lineage("someone/else", "unsloth/Qwen3-30B-A3B-Instruct-2507", "a" * 40)
