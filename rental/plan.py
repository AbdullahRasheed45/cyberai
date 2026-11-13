"""Resolve ONE config from the validated freeze and emit the EXACT Docker argv
arrays + subprocess environments for every phase (Astra #2/#3/#R12). Pure.

Single source of truth for: training output dir, adapter-metadata path, deployment
mount, host script/evidence paths, client URL, served IDs, AND serving identity/
provenance. Unsupported path overrides are rejected rather than silently honoured.
"""

from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from .freeze import validate_freeze, validate_lineage


@dataclass(frozen=True)
class TrainingBenchmarkConfig:
    max_seq_length: int = 2048
    max_steps: int = 10
    batch_size: int = 1
    grad_accum: int = 1
    measure_warmup_steps: int = 2

    @classmethod
    def from_env(cls, env):
        values = {}
        for name, default in cls().__dict__.items():
            key = "TRAIN_" + name.upper()
            raw = env.get(key, str(default))
            try:
                value = int(raw)
            except (ValueError, TypeError):
                raise FreezeInvalid(f"{key} must be an integer, got {raw!r}") from None
            if value < (0 if name == "measure_warmup_steps" else 1):
                raise FreezeInvalid(f"{key} outside valid range: {value}")
            values[name] = value
        cfg = cls(**values)
        if cfg.measure_warmup_steps >= cfg.max_steps:
            raise FreezeInvalid("measurement warm-up must leave at least one measured step")
        return cfg

    def docker_env(self):
        return {"TRAIN_" + name.upper(): str(value) for name, value in self.__dict__.items()}


@dataclass(frozen=True)
class ResolvedConfig:
    vllm_image: str
    unsloth_image: str
    host_repo: str
    host_model_path: str
    host_adapter_path: str
    train_repo: str
    train_commit: str
    serving_repo: str
    serving_commit: str
    serving_quant: str
    serving_provenance: str
    dependencies: tuple
    run_id: str
    workload_domain: str = "web"
    train_mode: str = "pingpong"
    pilot_rel: str = ""
    base_served_id: str = "qwen3"
    adapter_served_id: str = "smoke"
    max_model_len: int = 32768
    port: int = 8000
    training: TrainingBenchmarkConfig = field(default_factory=TrainingBenchmarkConfig)

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}/v1/chat/completions"

    @property
    def health_url(self) -> str:
        return f"http://localhost:{self.port}"

    @property
    def artifact_dir(self) -> str:
        return f"artifacts/run_{self.run_id}"

    @property
    def output_dir_rel(self) -> str:
        return f"runs/{self.run_id}"

    @property
    def host_output_dir(self) -> str:
        return os.path.join(self.host_repo, "runs", self.run_id)

    @property
    def adapter_config_path(self) -> str:
        return os.path.join(self.host_adapter_path, "adapter_config.json")


class FreezeInvalid(Exception):
    pass


def resolve(freeze: dict, env: dict | None = None) -> ResolvedConfig:
    env = env or os.environ
    errs = validate_freeze(freeze)
    errs += validate_lineage(
        freeze.get("tokenizer_identity", ""),
        freeze.get("trainable_base_repo", ""),
        freeze.get("trainable_base_commit", ""),
    )
    if errs:
        raise FreezeInvalid("; ".join(errs))
    cwd = os.path.abspath(os.getcwd())
    repo = os.path.abspath(env.get("HOST_REPO", cwd))
    if repo != cwd:
        raise FreezeInvalid(
            f"HOST_REPO {repo!r} must equal cwd {cwd!r} "
            "(host scripts + evidence are relative to cwd)"
        )
    if "MODEL_PATH" not in env:
        raise KeyError("MODEL_PATH")
    model = os.path.abspath(env["MODEL_PATH"])
    if "ADAPTER_PATH" in env:
        raise FreezeInvalid(
            "ADAPTER_PATH override unsupported; the adapter path is derived from RUN_ID"
        )
    run_id = env.get("RUN_ID") or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", run_id):
        raise FreezeInvalid("RUN_ID must be a bounded filename-safe identifier")
    train_mode = env.get("TRAIN_MODE", "pingpong")
    pilot_rel = env.get("PILOT_DATA", "")
    if train_mode == "pilot":
        if not pilot_rel:
            raise FreezeInvalid("TRAIN_MODE=pilot requires PILOT_DATA (path under the repo)")
        if not (Path(repo) / pilot_rel).resolve().is_relative_to(Path(repo).resolve()):
            raise FreezeInvalid("PILOT_DATA must remain under the repo")
        if os.path.isabs(pilot_rel) or not os.path.isfile(os.path.join(repo, pilot_rel)):
            raise FreezeInvalid(f"pilot file {pilot_rel!r} must exist as a repo-relative path")
    elif train_mode != "pingpong":
        raise FreezeInvalid(f"TRAIN_MODE must be 'pilot' or 'pingpong', got {train_mode!r}")
    domain = env.get("WORKLOAD_DOMAIN", "web")
    if domain not in ("web", "detection"):
        raise FreezeInvalid("WORKLOAD_DOMAIN must be web or detection")
    derived_adapter = os.path.join(
        repo, "runs", run_id, "adapter"
    )  # run-isolated (overrides the check below)
    return ResolvedConfig(
        vllm_image=freeze["vllm_image"],
        unsloth_image=freeze["unsloth_image"],
        host_repo=repo,
        host_model_path=model,
        host_adapter_path=derived_adapter,
        train_repo=freeze["trainable_base_repo"],
        train_commit=freeze["trainable_base_commit"],
        serving_repo=freeze["serving_base_repo"],
        serving_commit=freeze["serving_base_commit"],
        serving_quant=freeze["serving_quantisation"],
        serving_provenance=freeze["serving_quant_provenance"],
        dependencies=tuple(freeze.get("dependencies", [])),
        run_id=run_id,
        workload_domain=domain,
        train_mode=train_mode,
        pilot_rel=pilot_rel,
        max_model_len=int(env.get("MAX_MODEL_LEN", "32768")),
        training=TrainingBenchmarkConfig.from_env(env),
    )


def _common(name, rc):
    return [
        "docker",
        "run",
        "-d",
        "--name",
        name,
        "--gpus",
        "all",
        "--ipc=host",
        "-p",
        f"127.0.0.1:{rc.port}:{rc.port}",
    ]


def base_serve_argv(rc):
    return _common("cyberai_serve_base", rc) + [
        "-v",
        f"{rc.host_model_path}:/model:ro",
        rc.vllm_image,
        "vllm",
        "serve",
        "/model",
        "--served-model-name",
        rc.base_served_id,
        "--gpu-memory-utilization",
        "0.85",
        "--max-model-len",
        str(rc.max_model_len),
        "--enable-prefix-caching",
        "--enable-chunked-prefill",
    ]


def lora_serve_argv(rc):
    return _common("cyberai_serve_lora", rc) + [
        "-v",
        f"{rc.host_model_path}:/model:ro",
        "-v",
        f"{rc.host_adapter_path}:/adapter:ro",
        rc.vllm_image,
        "vllm",
        "serve",
        "/model",
        "--served-model-name",
        rc.base_served_id,
        "--enable-lora",
        "--lora-modules",
        f"{rc.adapter_served_id}=/adapter",
        "--max-model-len",
        str(rc.max_model_len),
        "--enable-prefix-caching",
        "--enable-chunked-prefill",
    ]


def train_argv(rc):
    # The heavy GB10 training stack (Unsloth/TRL/PEFT/bitsandbytes) comes from the
    # pinned image; `pip install -e .` only adds THIS project so detection_verifier/
    # rental import inside the container. Output lands at the single adapter path.
    inner = (
        "pip install -e . --no-deps -q && "
        "python scripts/smoke_train.py && python scripts/smoke_reload.py"
    )
    return [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--ipc=host",
        "-v",
        f"{rc.host_repo}:/work",
        "-w",
        "/work",
        "-e",
        f"SMOKE_MODEL={rc.train_repo}",
        "-e",
        f"SMOKE_REVISION={rc.train_commit}",
        "-e",
        f"SMOKE_OUT={rc.output_dir_rel}",
        "-e",
        f"RUN_ID={rc.run_id}",
        "-e",
        f"TRAIN_MODE={rc.train_mode}",
        "-e",
        f"PILOT_DATA={rc.pilot_rel}",
        *[
            token
            for key, value in rc.training.docker_env().items()
            for token in ("-e", f"{key}={value}")
        ],
        rc.unsloth_image,
        "bash",
        "-lc",
        inner,
    ]


def _base_env(rc):
    return {"ARTIFACT_DIR": rc.artifact_dir}


def host_env(rc, served_id):
    return {**_base_env(rc), "VLLM_URL": rc.url, "SERVED_MODEL": served_id}


def preflight_cmd(rc):
    return (
        [sys.executable, "scripts/rental/00_preflight.py"],
        {
            **_base_env(rc),
            "MODEL_PATH": rc.host_model_path,
            "FREEZE": os.environ.get("FREEZE", "scripts/rental/FREEZE.yaml"),
        },
    )


def measure_cmd(rc):
    return [sys.executable, "scripts/rental/20_measure_inference.py"], host_env(
        rc, rc.base_served_id
    )


def workload_cmd(rc):
    if rc.workload_domain == "web":
        return [sys.executable, "scripts/rental/46_live_web_workflow.py"], {
            **host_env(rc, rc.adapter_served_id),
            "WORKLOAD_DOMAIN": rc.workload_domain,
            "LAB_SSH_HOST": os.environ.get("LAB_SSH_HOST", ""),
        }
    return [sys.executable, "scripts/rental/40_workload.py"], {
        **host_env(rc, rc.adapter_served_id),
        "WORKLOAD_DOMAIN": rc.workload_domain,
    }


def export_cmd(rc):
    return [sys.executable, "scripts/rental/50_export.py"], {
        **_base_env(rc),
        "SMOKE_OUT": rc.output_dir_rel,
        "FREEZE": os.environ.get("FREEZE", "scripts/rental/FREEZE.yaml"),
        "EVIDENCE_EXPORT_DIR": os.environ.get("EVIDENCE_EXPORT_DIR", ""),
    }


def resolved_dict(rc):
    d = {k: (list(v) if isinstance(v, tuple) else v) for k, v in rc.__dict__.items()}
    d["training"] = rc.training.__dict__
    d.update(url=rc.url, artifact_dir=rc.artifact_dir)
    return d
