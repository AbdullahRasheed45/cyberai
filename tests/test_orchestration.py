"""Round-12: the production execution boundary — exact Docker argv/env from one
resolved config, the real lifecycle through a mock executor, and the actual
module entry point (Astra #1-#6)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from rental import orchestrate as orch
from rental import plan
from rental.clients import parse_stream_events
from rental.plan import FreezeInvalid, ResolvedConfig

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rc():
    return ResolvedConfig(
        vllm_image="vllm@sha256:" + "a" * 64,
        unsloth_image="uns@sha256:" + "b" * 64,
        host_repo="/repo",
        host_model_path="/data/model",
        host_adapter_path="/repo/out_smoke/adapter",
        train_repo="unsloth/Qwen3-30B-A3B",
        train_commit="c" * 40,
        serving_repo="Qwen/Qwen3-30B-A3B-Instruct-2507-FP8",
        serving_commit="d" * 40,
        serving_quant="FP8",
        serving_provenance="official",
        dependencies=(),
        run_id="testrun",
        max_model_len=32768,
    )


# --- #2: EXACT Docker argv arrays --------------------------------------------


def test_base_serve_argv_exact():
    a = plan.base_serve_argv(_rc())
    assert a[:9] == [
        "docker",
        "run",
        "-d",
        "--name",
        "cyberai_serve_base",
        "--gpus",
        "all",
        "--ipc=host",
        "-p",
    ]
    assert "-v" in a and "/data/model:/model:ro" in a  # read-only model mount
    assert a[a.index("--served-model-name") + 1] == "qwen3"
    assert "--enable-prefix-caching" in a and "--enable-chunked-prefill" in a
    assert a[a.index("--max-model-len") + 1] == "32768"
    assert "vllm@sha256:" + "a" * 64 in a  # pinned image by digest


def test_lora_serve_argv_has_adapter_mount_and_lora_flags():
    a = plan.lora_serve_argv(_rc())
    assert "/repo/out_smoke/adapter:/adapter:ro" in a
    assert "--enable-lora" in a
    assert a[a.index("--lora-modules") + 1] == "smoke=/adapter"


def test_train_argv_imports_project_from_mounted_checkout():
    a = plan.train_argv(_rc())
    assert "-v" in a and "/repo:/work" in a and a[a.index("-w") + 1] == "/work"
    # project imported via PYTHONPATH from the mount — no pip/build backend/network
    assert not any("pip install" in tok for tok in a)
    assert "export PYTHONPATH=/work" in a[-1]
    assert "smoke_train.py" in a[-1] and "smoke_reload.py" in a[-1]
    assert "PYTHONUNBUFFERED=1" in a  # live training console for the tracker
    assert a[a.index("HF_TOKEN") - 1] == "-e"  # passed by NAME; value never in argv
    assert not any(tok.startswith("HF_TOKEN=") for tok in a)
    assert "uns@sha256:" + "b" * 64 in a
    assert a[a.index("-e") + 1] == "SMOKE_MODEL=unsloth/Qwen3-30B-A3B"
    assert "SMOKE_REVISION=" + "c" * 40 in a


def test_serve_argv_takes_engine_flags_from_serving_yaml():
    rc = _rc()
    cfg = rc.serving
    for a in (plan.base_serve_argv(rc), plan.lora_serve_argv(rc)):
        assert a[a.index("--gpu-memory-utilization") + 1] == str(cfg.gpu_memory_utilization)
        assert a[a.index("--max-num-seqs") + 1] == str(cfg.max_num_seqs)
        assert a[a.index("--port") + 1] == str(rc.port)  # container port == mapped port
        assert f"127.0.0.1:{rc.port}:{rc.port}" in a  # host exposure stays loopback-only
        if cfg.attention_backend.lower() != "auto":
            assert f"VLLM_ATTENTION_BACKEND={cfg.attention_backend}" in a
            # env flags precede the image; vllm args follow it
            assert a.index(f"VLLM_ATTENTION_BACKEND={cfg.attention_backend}") < a.index(
                rc.vllm_image
            )


def test_lora_serve_rank_matches_training_config():
    rc = _rc()
    a = plan.lora_serve_argv(rc)
    assert a[a.index("--max-lora-rank") + 1] == str(rc.hparams.lora_rank)
    assert a[a.index("--max-loras") + 1] == "1"


def test_attention_backend_auto_sets_no_env():
    from libs.common.gb10_serving import engine_env

    cfg = _rc().serving.model_copy(update={"attention_backend": "auto"})
    assert engine_env(cfg) == {}


def test_resolve_rejects_training_targets_differing_from_freeze():
    f = _good_freeze()
    f["adapter_targets"] = ["q_proj", "v_proj"]
    with pytest.raises(FreezeInvalid, match="target_modules"):
        plan.resolve(f, env={"MODEL_PATH": "/m", "RUN_ID": "r1"})


def test_resolve_takes_max_model_len_from_serving_yaml_unless_overridden():
    rc = plan.resolve(_good_freeze(), env={"MODEL_PATH": "/m", "RUN_ID": "r1"})
    assert rc.max_model_len == rc.serving.max_model_len
    rc = plan.resolve(
        _good_freeze(), env={"MODEL_PATH": "/m", "RUN_ID": "r1", "MAX_MODEL_LEN": "8192"}
    )
    assert rc.max_model_len == 8192
    with pytest.raises(FreezeInvalid):
        plan.resolve(_good_freeze(), env={"MODEL_PATH": "/m", "MAX_MODEL_LEN": "big"})


def test_resolved_dict_is_json_serialisable_with_configs():
    d = plan.resolved_dict(_rc())
    json.dumps(d)
    assert d["serving"]["max_num_seqs"] and d["hparams"]["lora_rank"]


def test_host_envs_derived_from_one_config():
    rc = _rc()
    _, mev = plan.measure_cmd(rc)
    _, wev = plan.workload_cmd(rc)
    assert mev == {"VLLM_URL": rc.url, "SERVED_MODEL": "qwen3", "ARTIFACT_DIR": rc.artifact_dir}
    assert wev == {
        "VLLM_URL": rc.url,
        "SERVED_MODEL": "smoke",
        "ARTIFACT_DIR": rc.artifact_dir,
        "WORKLOAD_DOMAIN": "web",
        "LAB_SSH_HOST": os.environ.get("LAB_SSH_HOST", ""),
    }


# --- #3: resolve rejects a bad freeze ----------------------------------------


def _good_freeze():
    import yaml

    f = yaml.safe_load(Path("scripts/rental/FREEZE.yaml").read_text(encoding="utf-8"))
    sha = "a" * 40
    dig = "x@sha256:" + "b" * 64
    f.update(
        trainable_base_commit=sha,
        serving_base_commit=sha,
        serving_quant_provenance="official FP8",
        vllm_image=dig,
        unsloth_image=dig,
        trainable_serving_relation_attested=True,
        dependencies=[
            "transformers==5.0.0",
            "unsloth==2025.11.1",
            "peft==0.17.0",
            "trl==0.12.0",
            "bitsandbytes==0.45.0",
        ],
    )
    return f


def test_resolve_aborts_on_placeholder_freeze():
    with pytest.raises(FreezeInvalid):
        plan.resolve(
            __import__("yaml").safe_load(
                Path("scripts/rental/FREEZE.yaml").read_text(encoding="utf-8")
            ),
            env={"MODEL_PATH": "/m"},
        )


def test_resolve_rejects_adapter_path_override():
    with pytest.raises(FreezeInvalid):
        plan.resolve(_good_freeze(), env={"MODEL_PATH": "/m", "ADAPTER_PATH": "/somewhere/else"})


def test_resolve_keeps_serving_identity_and_single_adapter_path():
    rc = plan.resolve(_good_freeze(), env={"MODEL_PATH": "/data/model", "RUN_ID": "r1"})
    import os as _os

    assert rc.serving_repo and rc.serving_commit and rc.serving_provenance
    assert rc.host_adapter_path == _os.path.join(
        rc.host_repo, "runs", "r1", "adapter"
    )  # run-isolated
    assert rc.output_dir_rel == "runs/r1"
    assert plan.resolved_dict(rc)["serving_repo"] == rc.serving_repo


# --- #5/#6: full lifecycle through a MOCK EXECUTOR ---------------------------


class _Mock:
    def __init__(self, scenario="ok"):
        self.scenario = scenario
        self.started = []
        self.stopped = []
        self.ran = []
        self.evidence = {}
        self.lora_up = False
        self.train_called = False

    def start(self, name, argv):
        self.started.append((name, argv))
        if name == "cyberai_serve_lora":
            self.lora_up = True

    def stop(self, name):
        self.stopped.append(name)

    def exited(self, name):
        return True

    def run(self, argv, env):
        self.ran.append(argv)
        if self.scenario == "preflight_fail" and any("00_preflight" in str(t) for t in argv):
            raise RuntimeError("preflight failed")
        if self.scenario == "export_fail" and any("50_export" in str(t) for t in argv):
            raise RuntimeError("export failed")
        if any("smoke_train" in str(t) for t in argv):
            self.train_called = True
        if self.scenario == "train_fail" and any("smoke_train" in str(t) for t in argv):
            raise RuntimeError("train crashed")

    def is_ready(self, url):
        return self.scenario != "not_ready"

    def served_ids(self, url):
        if self.scenario == "bad_identity":
            return ["wrong"]
        return ["qwen3", "smoke"] if self.lora_up else ["qwen3"]

    def mem_gb(self):
        return 2.0

    def read_adapter_config(self, path):
        if self.scenario == "bad_lineage":
            return {"base_model_name_or_path": "someone/else"}
        return {"base_model_name_or_path": "unsloth/Qwen3-30B-A3B"}

    def read_train_meta(self, path):
        rid = "stale" if self.scenario == "stale_adapter" else "testrun"
        return {"run_id": rid}

    def write_evidence(self, path, text):
        self.evidence[path] = text

    def sleep(self, s):
        pass


def _ex(m):
    return orch.Executor(
        m.start,
        m.stop,
        m.exited,
        m.run,
        m.is_ready,
        m.served_ids,
        m.mem_gb,
        m.read_adapter_config,
        m.read_train_meta,
        m.write_evidence,
        m.sleep,
        readiness_tries=3,
    )


def test_lifecycle_happy_path_real_commands():
    m = _Mock("ok")
    ev = orch.run(_rc(), _ex(m))
    assert ev["phases"][0] == "preflight" and ev["status"] == "COMPLETED"
    assert any("00_preflight" in str(t) for t in m.ran[0])  # preflight ran FIRST
    assert ev["phases"].index("preflight") < ev["phases"].index("start_base")
    assert (
        ev["phases"].index("measure")
        < ev["phases"].index("train")
        < ev["phases"].index("start_lora")
    )
    assert ev["export_status"] == "ok"


def test_preflight_failure_prevents_server_start():
    m = _Mock("preflight_fail")
    with pytest.raises(RuntimeError):
        orch.run(_rc(), _ex(m))
    assert m.started == []  # no container started
    assert (
        "run_testrun/orchestration.json" in str(list(m.evidence)) or m.evidence
    )  # evidence preserved


def test_export_failure_fails_trial():
    m = _Mock("export_fail")
    with pytest.raises(orch.LifecycleError):
        orch.run(_rc(), _ex(m))  # success path export failure => trial fails


def test_lifecycle_readiness_failure_exports_and_cleans():
    m = _Mock("not_ready")
    with pytest.raises(orch.LifecycleError):
        orch.run(_rc(), _ex(m))
    assert "cyberai_serve_base" in m.stopped and "cyberai_serve_lora" in m.stopped
    assert any("orchestration.json" in k for k in m.evidence)  # evidence saved on failure


def test_lifecycle_training_failure_exports():
    m = _Mock("train_fail")
    with pytest.raises(RuntimeError):
        orch.run(_rc(), _ex(m))
    key = [k for k in m.evidence if "orchestration.json" in k][0]
    assert any("export_on_failure" in p for p in json.loads(m.evidence[key])["phases"])


def test_lifecycle_adapter_lineage_checked():
    m = _Mock("bad_lineage")
    with pytest.raises(orch.LifecycleError):
        orch.run(_rc(), _ex(m))


def test_stale_adapter_from_prior_run_rejected():
    """Old adapter present but its train_meta run_id != this run -> rejected, and
    the new bundle does not present it as current (Astra #1)."""
    m = _Mock("stale_adapter")
    with pytest.raises(orch.LifecycleError) as ei:
        orch.run(_rc(), _ex(m))
    assert "stale adapter" in str(ei.value)
    # a receipt recording the FINAL (failed) status exists
    assert any("receipt.json" in k for k in m.evidence)


def test_receipt_records_final_status_on_success():
    m = _Mock("ok")
    orch.run(_rc(), _ex(m))
    rk = [k for k in m.evidence if "receipt.json" in k][0]
    import json as _j

    assert _j.loads(m.evidence[rk])["status"] == "COMPLETED"


def test_release_unavailable_telemetry_not_confirmed():
    m = _Mock("ok")
    m.mem_gb = lambda: None
    ev = orch.run(_rc(), _ex(m))
    assert any(r["release"] == "unverified_no_telemetry" for r in ev["releases"])


# --- #4: reasoning tokens via nested details -> decode unavailable -----------


def test_reasoning_nested_details_makes_decode_unavailable():
    ev = [
        (0.0, 'data: {"choices":[{"delta":{"reasoning":"x"}}]}'),
        (0.5, 'data: {"choices":[{"delta":{"content":"a"}}]}'),
        (1.5, 'data: {"choices":[{"delta":{"content":"b"}}]}'),
        (
            1.6,
            'data: {"usage":{"completion_tokens":102,'
            '"completion_tokens_details":{"reasoning_tokens":100}}}',
        ),
        (1.6, "data: [DONE]"),
    ]
    r = parse_stream_events(ev)
    assert r["reasoning_tokens"] == 100 and r["visible_content_tokens"] == 2
    assert abs(r["decode_tok_s"] - 1.0) < 1e-6  # 1 token / 1.0s window, not 101


def test_reasoning_present_but_uncounted_decode_unavailable():
    ev = [
        (0.0, 'data: {"choices":[{"delta":{"reasoning":"x"}}]}'),
        (0.5, 'data: {"choices":[{"delta":{"content":"a"}}]}'),
        (1.5, 'data: {"choices":[{"delta":{"content":"b"}}]}'),
        (1.6, 'data: {"usage":{"completion_tokens":102}}'),
        (1.6, "data: [DONE]"),
    ]
    r = parse_stream_events(ev)
    assert r["decode_tok_s"] is None and r["visible_content_tokens"] is None
    assert "uncounted" in r["decode_unavailable_reason"]


# --- #1: the actual documented module entry point ----------------------------


def test_module_entry_point_structured_abort_clean_env():
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["MODEL_PATH"] = "/tmp/model"
    r = subprocess.run(
        [sys.executable, "-m", "rental.orchestrate"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert "NameError" not in r.stderr and "Traceback" not in r.stderr, r.stderr
    assert json.loads(r.stdout)["orchestrate"] == "ABORTED"


# --- GB10 hardening: readiness, live logs, unified memory, phases -------------


def _ex_full(m, **kw):
    ex = _ex(m)
    for key, value in kw.items():
        setattr(ex, key, value)
    return ex


def test_container_exit_during_wait_fails_fast_with_log_pointer():
    m = _Mock("not_ready")
    checks = []
    m.exited = lambda name: checks.append(name) or True
    with pytest.raises(orch.LifecycleError, match="exited before becoming ready"):
        orch.run(_rc(), _ex_full(m, readiness_tries=1000))
    assert checks == ["cyberai_serve_base"]  # failed on the first poll, not after 1000


def test_serving_consoles_followed_into_run_artifacts():
    m = _Mock("ok")
    followed = []
    orch.run(_rc(), _ex_full(m, follow_logs=lambda n, p: followed.append((n, p))))
    assert followed == [
        ("cyberai_serve_base", "artifacts/run_testrun/cyberai_serve_base.console.log"),
        ("cyberai_serve_lora", "artifacts/run_testrun/cyberai_serve_lora.console.log"),
    ]


def test_live_phase_file_tracks_progress():
    m = _Mock("ok")
    orch.run(_rc(), _ex(m))
    phase = json.loads(m.evidence["artifacts/run_testrun/phase.json"])
    assert phase["phase"] == "export" and phase["phases"][0] == "preflight"
    assert phase["run_id"] == "testrun" and phase["elapsed_s"] >= 0


def test_train_dirs_prepared_and_cache_drops_recorded():
    m = _Mock("ok")
    prepared = []
    ev = orch.run(
        _rc(),
        _ex_full(
            m, prepare_dirs=lambda paths: prepared.extend(paths), drop_caches=lambda: "dropped"
        ),
    )
    assert prepared == plan.train_dirs(_rc())
    assert ev["cache_drops"] == {
        "before_serve": "dropped",
        "before_train": "dropped",
        "before_lora_serve": "dropped",
    }


def test_release_waits_for_unified_memory_to_settle():
    m = _Mock("ok")
    readings = iter([2.0] + [50.0, 2.5] * 2)  # baseline, then slow release per container
    ev = orch.run(
        _rc(),
        _ex_full(m, mem_gb=lambda: next(readings), release_wait_s=10, mem_source=lambda: "host"),
    )
    assert [r["release"] for r in ev["releases"]] == ["confirmed", "confirmed"]
    assert all(r["settle_wait_s"] == 5 and r["telemetry"] == "host" for r in ev["releases"])


def test_release_still_fails_loudly_if_memory_never_returns():
    m = _Mock("ok")
    readings = iter([2.0] + [50.0] * 20)
    with pytest.raises(orch.LifecycleError, match="memory not released"):
        orch.run(_rc(), _ex_full(m, mem_gb=lambda: next(readings), release_wait_s=10))


def test_host_meminfo_fallback_for_unified_memory():
    from rental.telemetry import host_used_memory_gb

    text = "MemTotal:       125829120 kB\nMemFree: 1 kB\nMemAvailable:    94371840 kB\n"
    assert host_used_memory_gb(text) == pytest.approx(30.0)
    assert host_used_memory_gb("MemTotal: 5 kB\n") is None
