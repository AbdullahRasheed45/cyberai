"""Phased rental lifecycle — one testable execution boundary (Astra #1-#6).

Everything runs through an injected Executor that receives the EXACT Docker argv
arrays and subprocess envs produced by rental.plan, so tests assert the real
commands, not abstract tokens. Lifecycle distinguishes unavailable telemetry from
confirmed release, uses a measured baseline, validates the actual saved adapter's
base, and saves evidence (phase log, command arrays, resolved config) with
export-on-failure.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import plan
from .freeze import validate_lineage
from .plan import FreezeInvalid, ResolvedConfig


class LifecycleError(Exception):
    pass


@dataclass
class Executor:
    start: Callable[[str, list], None]  # (name, argv) -> run detached
    stop: Callable[[str], None]  # (name)
    exited: Callable[[str], bool]  # (name) -> container not running
    run: Callable[[list, dict], None]  # (argv, env) -> run to completion
    is_ready: Callable[[str], bool]  # (health_url)
    served_ids: Callable[[str], list]  # (health_url) -> [model_id,...]
    mem_gb: Callable[[], float | None]
    read_adapter_config: Callable[[str], dict | None]
    read_train_meta: Callable[[str], dict | None]
    write_evidence: Callable[[str, str], None]
    sleep: Callable[[float], None] = lambda s: None
    release_margin_gb: float = 1.0
    readiness_tries: int = 120
    ready_poll_s: float = 2.0
    # Seconds to let memory settle after a container exits before judging release.
    release_wait_s: float = 0.0
    # Stream a detached container's console to a file (live + preserved after rm -f).
    follow_logs: Callable[[str, str], None] = lambda name, path: None
    # Create host dirs a container writes, writable regardless of the image's uid.
    prepare_dirs: Callable[[list], None] = lambda paths: None
    # Best-effort page-cache drop before large unified-memory allocations.
    drop_caches: Callable[[], str] = lambda: "not_attempted"
    # Which telemetry source produced mem_gb (GB10 nvidia-smi memory is N/A).
    mem_source: Callable[[], str] = lambda: "executor"


def _wait_ready(ex: Executor, url: str, name: str):
    for _ in range(ex.readiness_tries):
        if ex.is_ready(url):
            return
        if ex.exited(name):
            raise LifecycleError(
                f"container {name} exited before becoming ready; see its console log"
            )
        ex.sleep(ex.ready_poll_s)
    raise LifecycleError(
        f"server did not become ready within {ex.readiness_tries * ex.ready_poll_s:.0f}s"
    )


def _assert_identity(ex: Executor, url: str, expected: str):
    ids = ex.served_ids(url)
    if expected not in ids:
        raise LifecycleError(f"expected served id {expected!r} not present; got {ids}")


def _stop_and_verify_release(ex: Executor, name: str, baseline: float | None) -> dict:
    ex.stop(name)
    if not ex.exited(name):
        raise LifecycleError(f"container {name} did not exit after stop")
    base = baseline if baseline is not None else 0.0
    waited = 0.0
    while True:
        used = ex.mem_gb()
        if used is None:
            return {"container": name, "exited": True, "release": "unverified_no_telemetry"}
        if used <= base + ex.release_margin_gb:
            return {
                "container": name,
                "exited": True,
                "release": "confirmed",
                "mem_used_gb": used,
                "baseline_gb": baseline,
                "telemetry": ex.mem_source(),
                "settle_wait_s": waited,
            }
        if waited >= ex.release_wait_s:
            break
        ex.sleep(5)
        waited += 5
    raise LifecycleError(
        f"memory not released after {name}: used={used} baseline={baseline} "
        f"margin={ex.release_margin_gb} source={ex.mem_source()} waited={waited}s"
    )


def run(rc: ResolvedConfig, ex: Executor) -> dict:
    base, lora = "cyberai_serve_base", "cyberai_serve_lora"
    evidence = {
        "resolved_config": plan.resolved_dict(rc),
        "phases": [],
        "commands": {},
        "releases": [],
        "phase_events": [],
    }

    started = time.monotonic()

    def record(phase):
        evidence["phases"].append(phase)
        evidence["phase_events"].append({"phase": phase, "monotonic_s": time.monotonic()})
        # Live progress for the tracker/dashboard; orchestration.json is final evidence.
        with contextlib.suppress(Exception):
            ex.write_evidence(
                f"{rc.artifact_dir}/phase.json",
                json.dumps(
                    {
                        "run_id": rc.run_id,
                        "phase": phase,
                        "phases": evidence["phases"],
                        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "elapsed_s": round(time.monotonic() - started, 1),
                    },
                    indent=2,
                ),
            )

    def log_path(name):
        return f"{rc.artifact_dir}/{name}.console.log"

    orch_path = f"{rc.artifact_dir}/orchestration.json"

    def export_now() -> bool:
        argv, env = plan.export_cmd(rc)
        evidence["commands"]["export"] = argv
        ex.write_evidence(
            orch_path, json.dumps(evidence, indent=2)
        )  # written BEFORE export so it is archived
        try:
            ex.run(argv, env)
            evidence["export_status"] = "ok"
            return True
        except Exception as e:
            evidence["export_status"] = f"FAILED: {e}"
            ex.write_evidence(
                orch_path, json.dumps(evidence, indent=2)
            )  # persist the export failure
            return False

    try:
        # Phase 0: real hardware/container/checkpoint preflight BEFORE any server (#1)
        record("preflight")
        pf_argv, pf_env = plan.preflight_cmd(rc)
        evidence["commands"]["preflight"] = pf_argv
        ex.run(pf_argv, pf_env)  # non-zero/raise aborts before start_base

        # Preflight hashes the whole snapshot, filling page cache on unified memory;
        # drop it (best effort, recorded) before measuring the baseline and serving.
        evidence["cache_drops"] = {"before_serve": ex.drop_caches()}
        baseline = ex.mem_gb()
        evidence["baseline_gb"] = baseline
        evidence["memory_telemetry"] = ex.mem_source()

        record("start_base")
        base_argv = plan.base_serve_argv(rc)
        evidence["commands"]["base_serve"] = base_argv
        ex.start(base, base_argv)
        ex.follow_logs(base, log_path(base))
        record("wait_base")
        _wait_ready(ex, rc.health_url, base)
        record("verify_base_identity")
        _assert_identity(ex, rc.health_url, rc.base_served_id)

        record("measure")
        m_argv, m_env = plan.measure_cmd(rc)
        evidence["commands"]["measure"] = (m_argv, m_env)
        ex.run(m_argv, m_env)
        record("stop_base")
        evidence["releases"].append(_stop_and_verify_release(ex, base, baseline))

        record("train")
        evidence["cache_drops"]["before_train"] = ex.drop_caches()
        ex.prepare_dirs(plan.train_dirs(rc))
        t_argv = plan.train_argv(rc)
        evidence["commands"]["train"] = t_argv
        ex.run(t_argv, {})
        # validate the ACTUAL saved adapter's base (Astra #6), not tokenizer identity
        record("verify_adapter_metadata")
        acfg = ex.read_adapter_config(rc.adapter_config_path)
        meta = ex.read_train_meta(f"{rc.host_output_dir}/train_meta.json")
        if not acfg or not meta:
            raise LifecycleError("no adapter_config.json / train_meta.json after training")
        if meta.get("run_id") != rc.run_id:
            raise LifecycleError(
                f"train_meta run_id {meta.get('run_id')!r} != this run "
                f"{rc.run_id!r} (stale adapter)"
            )
        lerr = validate_lineage(
            acfg.get("base_model_name_or_path", ""), rc.train_repo, rc.train_commit
        )
        if lerr:
            raise LifecycleError("adapter lineage mismatch: " + "; ".join(lerr))

        record("start_lora")
        evidence["cache_drops"]["before_lora_serve"] = ex.drop_caches()
        lora_argv = plan.lora_serve_argv(rc)
        evidence["commands"]["lora_serve"] = lora_argv
        ex.start(lora, lora_argv)
        ex.follow_logs(lora, log_path(lora))
        record("wait_lora")
        _wait_ready(ex, rc.health_url, lora)
        record("verify_adapter_identity")
        _assert_identity(ex, rc.health_url, rc.adapter_served_id)

        record("workload")
        w_argv, w_env = plan.workload_cmd(rc)
        evidence["commands"]["workload"] = (w_argv, w_env)
        ex.run(w_argv, w_env)
        record("stop_lora")
        evidence["releases"].append(_stop_and_verify_release(ex, lora, baseline))

        record("export")
        exported = export_now()
        evidence["status"] = "COMPLETED" if exported else "EXPORT_FAILED"
        _receipt(ex, rc, evidence)  # receipt reflects the FINAL status (outside the bundle)
        if not exported:
            raise LifecycleError(f"required export failed: {evidence.get('export_status')}")
        return evidence
    except Exception as exc:
        record("cleanup")
        for n in (base, lora):
            with contextlib.suppress(Exception):
                ex.stop(n)
        record("export_on_failure")
        export_now()  # preserve partial evidence
        evidence.setdefault("status", f"FAILED: {type(exc).__name__}: {exc}")
        _receipt(ex, rc, evidence)  # receipt records the failure outcome too
        raise


def _receipt(ex: Executor, rc: ResolvedConfig, evidence: dict):
    """A small run receipt OUTSIDE the archive, recording the final outcome so the
    saved evidence is accurate without a circular hashing requirement."""
    ex.write_evidence(
        f"{rc.artifact_dir}/receipt.json",
        json.dumps(
            {
                "run_id": rc.run_id,
                "status": evidence.get("status"),
                "export_status": evidence.get("export_status"),
                "phases": evidence.get("phases"),
                "releases": evidence.get("releases"),
            },
            indent=2,
        ),
    )


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "")
    try:
        value = float(raw) if raw else default
    except ValueError:
        raise SystemExit(f"{name} must be a number, got {raw!r}") from None
    if value <= 0:
        raise SystemExit(f"{name} must be positive")
    return value


def _real_executor() -> Executor:  # pragma: no cover - real side effects
    import subprocess
    import urllib.request

    followers: dict = {}
    source = {"last": "unavailable"}

    def start(name, argv):
        subprocess.check_call(argv)

    def follow_logs(name, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        handle = open(path, "ab")  # noqa: SIM115 - lifetime spans the container
        followers[name] = (
            subprocess.Popen(
                ["docker", "logs", "-f", "--timestamps", name],
                stdout=handle,
                stderr=subprocess.STDOUT,
            ),
            handle,
        )

    def stop(name):
        subprocess.call(["docker", "rm", "-f", name])
        follower = followers.pop(name, None)
        if follower:
            process, handle = follower
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            handle.close()

    def exited(name):
        out = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name=^{name}$"], capture_output=True, text=True
        )
        return out.stdout.strip() == ""

    def run_(argv, env):
        subprocess.check_call(argv, env={**os.environ, **(env or {})})

    def ready(url):
        try:
            return urllib.request.urlopen(url + "/health", timeout=3).status == 200
        except Exception:
            return False

    def ids(url):
        try:
            with urllib.request.urlopen(url + "/v1/models", timeout=5) as r:
                return [m["id"] for m in json.load(r)["data"]]
        except Exception:
            return []

    def mem():
        from .telemetry import used_memory_gb

        value, source["last"] = used_memory_gb()
        return value

    def prepare_dirs(paths):
        for path in paths:
            os.makedirs(path, exist_ok=True)
            with contextlib.suppress(OSError):
                os.chmod(path, 0o777)  # container may run as a different uid

    def drop_caches():
        subprocess.call(["sync"])
        try:
            Path("/proc/sys/vm/drop_caches").write_text("3\n")
            return "dropped"
        except OSError:
            pass
        try:
            code = subprocess.call(
                ["sudo", "-n", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            return "dropped_via_sudo" if code == 0 else "not_permitted"
        except (OSError, subprocess.TimeoutExpired):
            return "not_permitted"

    def adapter_cfg(path):
        return json.loads(Path(path).read_text(encoding="utf-8")) if os.path.isfile(path) else None

    def train_meta(path):
        return json.loads(Path(path).read_text(encoding="utf-8")) if os.path.isfile(path) else None

    def write_ev(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text(text, encoding="utf-8")

    import time as _t

    poll_s = 5.0
    # First FP8 MoE load + kernel compile/CUDA-graph capture can take many minutes.
    ready_timeout_s = _env_float("SERVE_READY_TIMEOUT_S", 1800)
    return Executor(
        start,
        stop,
        exited,
        run_,
        ready,
        ids,
        mem,
        adapter_cfg,
        train_meta,
        write_ev,
        _t.sleep,
        release_margin_gb=_env_float("RELEASE_MARGIN_GB", 2.0),
        readiness_tries=max(1, int(ready_timeout_s / poll_s)),
        ready_poll_s=poll_s,
        release_wait_s=_env_float("RELEASE_WAIT_S", 60),
        follow_logs=follow_logs,
        prepare_dirs=prepare_dirs,
        drop_caches=drop_caches,
        mem_source=lambda: source["last"],
    )


def main():
    import sys
    import time as _t

    import yaml

    os.environ.setdefault("RUN_ID", _t.strftime("%Y%m%dT%H%M%SZ", _t.gmtime()))
    freeze_path = os.environ.get("FREEZE", "scripts/rental/FREEZE.yaml")
    freeze = yaml.safe_load(Path(freeze_path).read_text(encoding="utf-8"))
    try:
        rc = plan.resolve(freeze)
    except FreezeInvalid as e:
        print(json.dumps({"orchestrate": "ABORTED", "reason": str(e)}, indent=2))
        sys.exit(1)
    except KeyError as e:
        print(
            json.dumps(
                {"orchestrate": "ABORTED", "reason": f"missing operational env: {e}"}, indent=2
            )
        )
        sys.exit(1)
    run(rc, _real_executor())


if __name__ == "__main__":
    main()
