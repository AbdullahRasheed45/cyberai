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


def _wait_ready(ex: Executor, url: str):
    for _ in range(ex.readiness_tries):
        if ex.is_ready(url):
            return
        ex.sleep(2)
    raise LifecycleError("server did not become ready within bound")


def _assert_identity(ex: Executor, url: str, expected: str):
    ids = ex.served_ids(url)
    if expected not in ids:
        raise LifecycleError(f"expected served id {expected!r} not present; got {ids}")


def _stop_and_verify_release(ex: Executor, name: str, baseline: float | None) -> dict:
    ex.stop(name)
    if not ex.exited(name):
        raise LifecycleError(f"container {name} did not exit after stop")
    used = ex.mem_gb()
    if used is None:
        return {"container": name, "exited": True, "release": "unverified_no_telemetry"}
    base = baseline if baseline is not None else 0.0
    if used <= base + ex.release_margin_gb:
        return {
            "container": name,
            "exited": True,
            "release": "confirmed",
            "mem_used_gb": used,
            "baseline_gb": baseline,
        }
    raise LifecycleError(f"GPU memory not released after {name}: used={used} baseline={baseline}")


def run(rc: ResolvedConfig, ex: Executor) -> dict:
    base, lora = "cyberai_serve_base", "cyberai_serve_lora"
    evidence = {
        "resolved_config": plan.resolved_dict(rc),
        "phases": [],
        "commands": {},
        "releases": [],
        "phase_events": [],
    }

    def record(phase):
        evidence["phases"].append(phase)
        evidence["phase_events"].append({"phase": phase, "monotonic_s": time.monotonic()})

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
        baseline = ex.mem_gb()
        evidence["baseline_gb"] = baseline

        # Phase 0: real hardware/container/checkpoint preflight BEFORE any server (#1)
        record("preflight")
        pf_argv, pf_env = plan.preflight_cmd(rc)
        evidence["commands"]["preflight"] = pf_argv
        ex.run(pf_argv, pf_env)  # non-zero/raise aborts before start_base

        record("start_base")
        base_argv = plan.base_serve_argv(rc)
        evidence["commands"]["base_serve"] = base_argv
        ex.start(base, base_argv)
        record("wait_base")
        _wait_ready(ex, rc.health_url)
        record("verify_base_identity")
        _assert_identity(ex, rc.health_url, rc.base_served_id)

        record("measure")
        m_argv, m_env = plan.measure_cmd(rc)
        evidence["commands"]["measure"] = (m_argv, m_env)
        ex.run(m_argv, m_env)
        record("stop_base")
        evidence["releases"].append(_stop_and_verify_release(ex, base, baseline))

        record("train")
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
        lora_argv = plan.lora_serve_argv(rc)
        evidence["commands"]["lora_serve"] = lora_argv
        ex.start(lora, lora_argv)
        record("wait_lora")
        _wait_ready(ex, rc.health_url)
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


def _real_executor() -> Executor:  # pragma: no cover - real side effects
    import subprocess
    import urllib.request

    def start(name, argv):
        subprocess.check_call(argv)

    def stop(name):
        subprocess.call(["docker", "rm", "-f", name])

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
        try:
            return (
                float(
                    subprocess.check_output(
                        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"]
                    ).split()[0]
                )
                / 1024
            )
        except Exception:
            return None

    def adapter_cfg(path):
        return json.loads(Path(path).read_text(encoding="utf-8")) if os.path.isfile(path) else None

    def train_meta(path):
        return json.loads(Path(path).read_text(encoding="utf-8")) if os.path.isfile(path) else None

    def write_ev(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text(text, encoding="utf-8")

    import time as _t

    return Executor(
        start, stop, exited, run_, ready, ids, mem, adapter_cfg, train_meta, write_ev, _t.sleep
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
