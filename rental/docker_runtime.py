"""Docker runtime flags for every container this project launches — one source.

Providers differ in how a container reaches the GPU and what an unprivileged
sandbox allows. Enverge, for example, puts the SSH session inside an
unprivileged container with Docker-in-Docker, where the NVIDIA runtime runs in
no-cgroups mode and plain `--gpus all` fails. Rather than hardcoding one
provider's flags, every `docker run` here takes its GPU / IPC / ulimit /
network flags from these environment variables, which
`scripts/rental/docker_runtime_setup.py` measures on the real machine and
writes into a sourceable file:

    DOCKER_GPU_MODE   gpus (default) -> --gpus all
                      runtime        -> --runtime nvidia -e NVIDIA_VISIBLE_DEVICES=all
                      cdi            -> --device nvidia.com/gpu=all
    DOCKER_IPC_HOST   1 (default) -> --ipc=host ; 0 -> --shm-size $DOCKER_SHM_SIZE (16g)
    DOCKER_ULIMITS    1 (default) -> NVIDIA-recommended memlock/stack ulimits ; 0 -> none
    DOCKER_NETWORK    publish (default) -> -p 127.0.0.1:PORT:PORT
                      host              -> --network host, server binds 127.0.0.1

Standard library only (also runs on a provider's bare python3).
CLI: `python3 -m rental.docker_runtime gpu|resources|all|network PORT|bind-host`
prints shell-quoted flags for the bash scripts.
"""

from __future__ import annotations

import os
import shlex
import sys

GPU_MODES = {
    "gpus": ["--gpus", "all"],
    "runtime": [
        "--runtime",
        "nvidia",
        "-e",
        "NVIDIA_VISIBLE_DEVICES=all",
        "-e",
        "NVIDIA_DRIVER_CAPABILITIES=compute,utility",
    ],
    "cdi": ["--device", "nvidia.com/gpu=all"],
}
NETWORK_MODES = ("publish", "host")
ULIMIT_ARGS = ["--ulimit", "memlock=-1", "--ulimit", "stack=67108864"]

# Asks a container which GPU it sees. NVIDIA images print a banner on start, so the
# answer is tagged and parsed (parse_gpu_name) rather than taking all of stdout. If
# the runtime does not inject nvidia-smi, PyTorch (present in the pinned images) is
# asked instead, so a working GPU is never reported missing for want of a tool.
GPU_NAME_MARKER = "CYBERAI_GPU_NAME:"
GPU_NAME_SHELL = (
    "N=$(nvidia-smi --query-gpu=name,driver_version,compute_cap --format=csv,noheader "
    "2>/dev/null | head -1); "
    'if [ -z "$N" ]; then N=$(python3 -c "import torch; '
    "print(torch.cuda.get_device_name(0) + ', via torch' if torch.cuda.is_available() "
    "else 'NO_CUDA')\" 2>/dev/null); fi; "
    f'echo "{GPU_NAME_MARKER}${{N:-NONE}}"'
)


def gpu_name_argv(image: str, gpu_flags: list[str]) -> list[str]:
    """`docker run` argv that prints one tagged GPU-name line from inside `image`."""
    return ["docker", "run", "--rm", *gpu_flags, image, "sh", "-c", GPU_NAME_SHELL]


def parse_gpu_name(output: str) -> str | None:
    """The tagged GPU name, or None when the container saw no CUDA device."""
    for line in (output or "").splitlines():
        index = line.find(GPU_NAME_MARKER)
        if index != -1:
            name = line[index + len(GPU_NAME_MARKER) :].strip()
            return None if name in ("", "NONE", "NO_CUDA") else name
    return None


class DockerRuntimeError(ValueError):
    pass


def _env(env):
    return os.environ if env is None else env


def gpu_mode(env=None) -> str:
    mode = _env(env).get("DOCKER_GPU_MODE", "gpus").strip() or "gpus"
    if mode not in GPU_MODES:
        raise DockerRuntimeError(
            f"DOCKER_GPU_MODE must be one of {sorted(GPU_MODES)}, got {mode!r}"
        )
    return mode


def _flag(env, name, default="1") -> bool:
    raw = _env(env).get(name, default).strip().lower()
    if raw not in ("0", "1", "true", "false", "yes", "no"):
        raise DockerRuntimeError(f"{name} must be 1/0, got {raw!r}")
    return raw in ("1", "true", "yes")


def gpu_args(env=None) -> list[str]:
    return list(GPU_MODES[gpu_mode(env)])


def ipc_args(env=None) -> list[str]:
    if _flag(env, "DOCKER_IPC_HOST"):
        return ["--ipc=host"]
    return ["--shm-size", _env(env).get("DOCKER_SHM_SIZE", "16g")]


def ulimit_args(env=None) -> list[str]:
    return list(ULIMIT_ARGS) if _flag(env, "DOCKER_ULIMITS") else []


def network_mode(env=None) -> str:
    mode = _env(env).get("DOCKER_NETWORK", "publish").strip() or "publish"
    if mode not in NETWORK_MODES:
        raise DockerRuntimeError(f"DOCKER_NETWORK must be one of {NETWORK_MODES}, got {mode!r}")
    return mode


def network_args(port: int, env=None) -> list[str]:
    """Publish only on loopback, or share the (sandbox) network namespace."""
    if network_mode(env) == "host":
        return ["--network", "host"]
    return ["-p", f"127.0.0.1:{port}:{port}"]


def server_bind_host(env=None) -> str:
    """Address the server inside the container listens on. With a published port
    it must be 0.0.0.0 (exposure is limited by the loopback publish); with host
    networking it binds loopback directly so nothing else is exposed."""
    return "127.0.0.1" if network_mode(env) == "host" else "0.0.0.0"


MEASURED_ENV_FILE = "artifacts/docker_runtime/docker_env.sh"


def read_measured(path=MEASURED_ENV_FILE) -> dict[str, str]:
    """KEY -> value from the `export KEY=value` lines docker_runtime_setup.py wrote."""
    values = {}
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            key, _, raw = line[len("export ") :].partition("=")
            parts = shlex.split(raw) or [""]
            values[key.strip()] = parts[0]
    return values


def unsourced_settings(env=None, path=MEASURED_ENV_FILE) -> list[str]:
    """Measured settings this shell does not have — i.e. the operator opened a new
    terminal and forgot `source artifacts/docker_runtime/docker_env.sh`. Without it the
    defaults (`--gpus all`) are used, which fail on sandboxed providers."""
    env = _env(env)
    return [f"{key}={value}" for key, value in read_measured(path).items() if env.get(key) != value]


def describe(env=None) -> dict:
    return {
        "gpu_mode": gpu_mode(env),
        "gpu_args": gpu_args(env),
        "ipc_args": ipc_args(env),
        "ulimit_args": ulimit_args(env),
        "network_mode": network_mode(env),
    }


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    what = argv[0] if argv else "all"
    if what == "check":
        missing = unsourced_settings()
        if missing:
            print(
                f"measured Docker settings not active in this shell ({', '.join(missing)}); "
                f"run: source {MEASURED_ENV_FILE}",
                file=sys.stderr,
            )
            return 3
        return 0
    try:
        if what == "gpu":
            flags = gpu_args()
        elif what == "resources":
            flags = ipc_args() + ulimit_args()
        elif what == "all":
            flags = gpu_args() + ipc_args() + ulimit_args()
        elif what == "network" and len(argv) == 2 and argv[1].isdigit():
            flags = network_args(int(argv[1]))
        elif what == "bind-host":
            flags = [server_bind_host()]
        else:
            print(
                "usage: python3 -m rental.docker_runtime "
                "check|gpu|resources|all|network PORT|bind-host",
                file=sys.stderr,
            )
            return 2
    except DockerRuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(" ".join(shlex.quote(flag) for flag in flags))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
