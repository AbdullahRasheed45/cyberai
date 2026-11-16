"""Typed result/evidence schemas.

CLAUDE.md directive #5 ("measure, don't assume") and #9 of the Stage 1
working rules ("never invent measurements; distinguish local, mocked, and
actual GB10/HP hardware results") both land here: any number quoted in a PR,
commit, or stage handoff should be constructible as one of these models, not
a bare figure in prose. Validation (`extra="forbid"`, bounded fields) makes
an impossible or mislabelled claim fail to construct rather than silently
pass review.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HostEnvironment(str, Enum):
    """Where a result was actually produced. See docs/EXECUTION_ENVIRONMENTS.md."""

    WINDOWS_DEV = "windows_dev"  # day-to-day Windows development machine
    GB10_CLOUD = "gb10_cloud"  # rented, ephemeral ARM64 GB10 instance
    GB10_OWNED = "gb10_owned"  # physical DGX Spark, once purchased
    LAB_LAPTOP = "lab_laptop"  # isolated HP laptop (lab/)
    CI = "ci"  # GitHub Actions runner


class EvidenceKind(str, Enum):
    """How much the result is allowed to claim."""

    LOCAL = "local"  # ran on this machine; no GPU/hardware claim implied
    MOCKED = "mocked"  # fake ports/doubles; no real backend touched
    HARDWARE = "hardware"  # a real GB10 or lab host produced this number


class ServingThroughputResult(BaseModel):
    """Payload shape for `scripts/measure_throughput.py` output."""

    model_config = ConfigDict(extra="forbid")

    single_stream_tok_s: float | None = Field(default=None, ge=0)
    batch_tok_s: float | None = Field(default=None, ge=0)
    batch_size: int | None = Field(default=None, gt=0)


class TrainSmokeMetrics(BaseModel):
    """Payload shape for the Unsloth LoRA smoke test (`scripts/train_smoke.py`)."""

    model_config = ConfigDict(extra="forbid")

    torch_cuda_available: bool
    torch_cuda_version: str | None = None
    training_loss_final: float | None = None
    adapter_saved: bool = False
    seconds_per_step: float | None = Field(default=None, ge=0)


class EvidenceRecord(BaseModel):
    """One claim: what was run, where, how trustworthy, and what it showed.

    `evidence=HARDWARE` is the only kind that may be cited as confirming a
    brief §19 BLOCKER; `LOCAL`/`MOCKED` results prove the code path works,
    not that the GB10/lab hardware does.
    """

    model_config = ConfigDict(extra="forbid")

    label: str  # e.g. "vllm_serve_smoke", "unsloth_lora_smoke"
    host: HostEnvironment
    evidence: EvidenceKind
    command: str  # the exact command/script invoked
    passed: bool
    result: dict[str, Any] = Field(default_factory=dict)  # a *Result/*Metrics model_dump()
    notes: str = ""
    measured_at: datetime
