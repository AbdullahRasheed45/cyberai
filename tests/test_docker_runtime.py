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
