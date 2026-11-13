#!/usr/bin/env python3
"""Find the Docker flags that actually work on THIS rental machine, and save them.

Why: on Enverge the SSH session is an unprivileged container sandbox running
Docker-in-Docker. The NVIDIA runtime there is in no-cgroups mode, so the usual
`--gpus all` fails and GPU containers need `--runtime nvidia -e
NVIDIA_VISIBLE_DEVICES=all` or `--device nvidia.com/gpu=all` instead. A
sandbox may also refuse `--ipc=host` or raised ulimits, publish ports
differently, or (with a host-mounted daemon) see different file paths.

What it does (no root needed, installs nothing, downloads nothing — the image
must already be pulled):
  1. Docker reachable? Records daemon version, runtimes, security options.
  2. GPU: tries each mode (gpus, runtime, cdi) running `nvidia-smi` in the image;
     picks the first that shows a GPU (GB10 expected).
  3. Shared memory: --ipc=host, else --shm-size.  4. ulimits: memlock/stack.
  5. Mounts: the container must READ a marker from this checkout and WRITE a file
     back that the sandbox sees (catches daemons that see different paths).
  6. Networking: a loopback-published port, else host networking.
Writes artifacts/docker_runtime/docker_runtime.json (evidence) and docker_env.sh:

    source artifacts/docker_runtime/docker_env.sh

Exit 0 = usable (GPU + mounts + a network mode work); 1 = blocker found (read the JSON).
Standard library only. Run from the repository root.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rental.docker_runtime import GPU_MODES, ULIMIT_ARGS  # noqa: E402

PROBE_PORT = 18999


def run(argv, timeout=300):
    """Run a command; never raise. Records exit code, tail of output and duration."""
    started = time.monotonic()
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout + r.stderr).strip()
        result = {"ok": r.returncode == 0, "code": r.returncode, "output": out[-2000:]}
    except subprocess.TimeoutExpired:
        result = {"ok": False, "code": None, "output": f"timed out after {timeout}s"}
    except OSError as exc:
        result = {"ok": False, "code": None, "output": f"{type(exc).__name__}: {exc}"}
    result["seconds"] = round(time.monotonic() - started, 2)
    return result


def freeze_image(freeze_path):
    """vllm_image from the freeze without needing PyYAML (simple key: value line)."""
    for line in Path(freeze_path).read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("vllm_image:"):
            value = line.split(":", 1)[1].split("#", 1)[0].strip().strip('"').strip("'")
            return value
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--image", help="already-pulled GPU image (default: FREEZE vllm_image)")
    parser.add_argument("--freeze", default=os.environ.get("FREEZE", "scripts/rental/FREEZE.yaml"))
    parser.add_argument("--out-dir", default="artifacts/docker_runtime")
    parser.add_argument(
        "--rehearsal-no-gpu",
        action="store_true",
        help="skip the GPU test to rehearse mounts/network on a non-GPU machine; "
        "the result is REHEARSAL_ONLY and never READY",
    )
    args = parser.parse_args()

    repo = Path.cwd().resolve()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    image = args.image or freeze_image(args.freeze)
    report = {
        "started_utc": datetime.now(UTC).isoformat(),
        "image": image,
        "repo": str(repo),
        "checks": {},
        "blockers": [],
        "chosen": {},
    }

    def save():
        report["finished_utc"] = datetime.now(UTC).isoformat()
        (out / "docker_runtime.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    # 1. daemon
    info = run(["docker", "info", "--format", "{{json .}}"], timeout=30)
    if not info["ok"]:
        report["blockers"].append("docker daemon not reachable: " + info["output"][-300:])
        save()
        print(json.dumps(report, indent=2))
        return 1
    try:
        d = json.loads(info["output"])
        report["checks"]["daemon"] = {
            "server_version": d.get("ServerVersion"),
            "runtimes": sorted((d.get("Runtimes") or {}).keys()),
            "default_runtime": d.get("DefaultRuntime"),
            "security_options": d.get("SecurityOptions"),
            "architecture": d.get("Architecture"),
            "cgroup_driver": d.get("CgroupDriver"),
        }
    except ValueError:
        report["checks"]["daemon"] = {"raw": info["output"][-500:]}
    if not image or not run(["docker", "image", "inspect", image], timeout=30)["ok"]:
        report["blockers"].append(
            f"image {image!r} is not pulled locally; pull it first (RENTAL_START_HERE step 5)"
        )
        save()
        print(json.dumps(report, indent=2))
        return 1

    # 2. GPU access modes — try all, record all, choose the first that sees a GPU
    gpu_results = {}
    for mode, flags in ({} if args.rehearsal_no_gpu else GPU_MODES).items():
        r = run(
            [
                "docker",
                "run",
                "--rm",
                *flags,
                image,
                "nvidia-smi",
                "--query-gpu=name,driver_version,compute_cap",
                "--format=csv,noheader",
            ],
            timeout=180,
        )
        r["sees_gpu"] = r["ok"] and bool(r["output"].strip()) and "error" not in r["output"].lower()
        r["sees_gb10"] = r["sees_gpu"] and "GB10" in r["output"]
        gpu_results[mode] = r
    report["checks"]["gpu_modes"] = gpu_results
    working = [m for m, r in gpu_results.items() if r["sees_gpu"]]
    if args.rehearsal_no_gpu:
        working = ["gpus"]
        gpu_results["gpus"] = {"sees_gpu": False, "sees_gb10": True, "output": "skipped"}
        report["checks"]["gpu_modes"] = "SKIPPED (rehearsal)"
    if not working:
        report["blockers"].append("no Docker GPU mode exposed a GPU (see checks.gpu_modes)")
        save()
        print(json.dumps(report, indent=2))
        return 1
    preferred = [m for m in working if gpu_results[m]["sees_gb10"]] or working
    gpu_mode = preferred[0]
    report["chosen"]["DOCKER_GPU_MODE"] = gpu_mode
    if not gpu_results[gpu_mode]["sees_gb10"]:
        report["blockers"].append(
            "a GPU is visible but it is not reported as GB10 — this is not DGX Spark evidence"
        )
    gpu = GPU_MODES[gpu_mode]

    # 3. shared memory
    ipc = run(["docker", "run", "--rm", "--ipc=host", image, "true"], timeout=120)
    report["checks"]["ipc_host"] = ipc
    if ipc["ok"]:
        report["chosen"]["DOCKER_IPC_HOST"] = "1"
    else:
        shm = run(["docker", "run", "--rm", "--shm-size", "16g", image, "true"], timeout=120)
        report["checks"]["shm_size_16g"] = shm
        report["chosen"]["DOCKER_IPC_HOST"] = "0"
        report["chosen"]["DOCKER_SHM_SIZE"] = "16g"
        if not shm["ok"]:
            report["blockers"].append("neither --ipc=host nor --shm-size 16g is permitted")

    # 4. ulimits (an unprivileged sandbox may not raise its hard limits)
    ul = run(["docker", "run", "--rm", *ULIMIT_ARGS, image, "true"], timeout=120)
    report["checks"]["ulimits"] = ul
    report["chosen"]["DOCKER_ULIMITS"] = "1" if ul["ok"] else "0"

    # 5. bind mounts: read a marker from the checkout, write one back. The probe lives
    #    in runs/ (git-ignored) because that is exactly where training writes.
    probe_dir = repo / "runs" / f".mount_probe_{uuid.uuid4().hex[:8]}"
    probe_dir.mkdir(parents=True)
    os.chmod(probe_dir, 0o777)
    marker = uuid.uuid4().hex
    (probe_dir / "marker.txt").write_text(marker, encoding="utf-8")
    rel = probe_dir.resolve().relative_to(repo).as_posix()
    mount = run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{repo}:/work",
            "-w",
            "/work",
            image,
            "sh",
            "-c",
            f"cat {shlex.quote(rel)}/marker.txt && echo && id -u"
            f" && echo written > {shlex.quote(rel)}/back.txt",
        ],
        timeout=120,
    )
    back = probe_dir / "back.txt"
    mount["read_ok"] = mount["ok"] and marker in mount["output"]
    mount["write_ok"] = back.is_file() and back.read_text(encoding="utf-8").strip() == "written"
    mount["container_uid"] = mount["output"].split()[-1] if mount["ok"] else None
    report["checks"]["bind_mount"] = mount
    if not mount["read_ok"]:
        report["blockers"].append(
            "a container cannot see this checkout at the same path: the Docker daemon is not "
            "running in this sandbox's filesystem. Training/serving mounts would be empty."
        )
    elif not mount["write_ok"]:
        report["blockers"].append("container can read but not write the checkout (output dirs)")
    # A root-owned file written by the container may resist removal; harmless leftover.
    for leftover in (probe_dir / "back.txt", probe_dir / "marker.txt"):
        with contextlib.suppress(OSError):
            leftover.unlink(missing_ok=True)
    with contextlib.suppress(OSError):
        probe_dir.rmdir()

    # 6. networking: loopback publish, else host network
    chosen_net = None
    for net, flags, host in (
        ("publish", ["-p", f"127.0.0.1:{PROBE_PORT}:{PROBE_PORT}"], "0.0.0.0"),
        ("host", ["--network", "host"], "127.0.0.1"),
    ):
        name = f"cyberai_netprobe_{uuid.uuid4().hex[:6]}"
        started = run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                *flags,
                image,
                "python3",
                "-m",
                "http.server",
                str(PROBE_PORT),
                "--bind",
                host,
            ],
            timeout=120,
        )
        reachable = False
        if started["ok"]:
            for _ in range(30):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{PROBE_PORT}/", timeout=2) as r:
                        reachable = r.status == 200
                except OSError:
                    time.sleep(1)
                if reachable:
                    break
        run(["docker", "rm", "-f", name], timeout=60)
        report["checks"][f"network_{net}"] = {**started, "reachable_on_loopback": reachable}
        if reachable:
            chosen_net = net
            break
    if chosen_net:
        report["chosen"]["DOCKER_NETWORK"] = chosen_net
    else:
        report["blockers"].append("a container server is not reachable on 127.0.0.1 either way")

    report["status"] = "READY" if not report["blockers"] else "BLOCKED"
    report["gpu_flags"] = gpu
    if args.rehearsal_no_gpu:
        # A rehearsal never measured the GPU: never emit a GPU mode or a READY status.
        report["status"] = "REHEARSAL_ONLY" if not report["blockers"] else "BLOCKED"
        report["chosen"].pop("DOCKER_GPU_MODE", None)
        report["gpu_flags"] = None

    # write the sourceable env file + evidence
    lines = [
        "# Generated by scripts/rental/docker_runtime_setup.py — measured on this machine.",
        f"# {report['started_utc']}  image={image}  status={report['status']}",
    ]
    lines += [f"export {k}={shlex.quote(v)}" for k, v in report["chosen"].items()]
    (out / "docker_env.sh").write_text("\n".join(lines) + "\n", encoding="utf-8")
    save()
    print(json.dumps({k: report[k] for k in ("status", "chosen", "blockers")}, indent=2))
    print(f"\nNext: source {out / 'docker_env.sh'}")
    return 0 if report["status"] in ("READY", "REHEARSAL_ONLY") else 1


if __name__ == "__main__":
    raise SystemExit(main())
