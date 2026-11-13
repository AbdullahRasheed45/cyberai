from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Outcome(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNVERIFIABLE = "UNVERIFIABLE"


class Provenance(BaseModel):
    scenario_id: str
    verifier_version: str | None = None
    generating_adapter: str
    timestamp: datetime
    lab_target_id: str | None = None


class TrajectoryStep(BaseModel):
    action: str  # e.g. "tool_call" | "reason" | "final"
    content: str
    tool_name: str | None = None
    tool_result: str | None = None


class Trajectory(BaseModel):
    id: str
    agent_config_id: str
    adapter_id: str  # gen_N
    domain: str  # "web" in Phase 1
    difficulty_tier: int
    task_class: str  # "exploitation" | "detection" | "remediation" | ...
    steps: list[TrajectoryStep]
    raw_output: str
    started_at: datetime
    finished_at: datetime
    provenance: Provenance  # MANDATORY — no trajectory without provenance


class Verdict(BaseModel):
    trajectory_id: str
    task_class: str
    outcome: Outcome
    detail: dict[str, Any] = Field(default_factory=dict)  # e.g. {"uid":0} or {"tp":95,"fp":2}
    verifier_name: str
    verifier_version: str
    checked_at: datetime
    dual_checker_agreement: bool | None = None


class DatasetVersion(BaseModel):
    id: str
    hash: str
    composition: dict[str, int]  # {"verified_new":.., "seed_replay":.., "<source>":..}
    diversity_stats: dict[str, float]  # per-template share
    created_at: datetime
    provenance: list[Provenance]


class TrainingRun(BaseModel):
    id: str
    base_model: str
    adapter_in: str | None
    adapter_out: str
    config: dict[str, Any]
    dataset_version_id: str
    metrics: dict[str, Any]  # loss curves, grad-norm, LR, expert-load
    started_at: datetime
    finished_at: datetime


class EvalResult(BaseModel):
    candidate_adapter: str
    benchmark_version: str
    overall_score: float
    per_category: dict[str, float]
    fp_rate: float
    canary_scores: dict[str, float]
    confidence_interval: tuple[float, float]
    per_task: list[dict[str, Any]]


class AuthzRequest(BaseModel):
    target: str
    scope_token: str | None = None
    ownership_proof: dict[str, Any] | None = None
    tier: str  # "read_only" | "sandbox" | "production"
    action_hash: str | None = None


class AuthzDecision(BaseModel):
    allow: bool
    reason: str


# Re-exported so every service imports schemas from one place (see
# docs/ARCHITECTURE.md §2): `from libs.schemas import ServingConfig` etc.,
# never a locally redefined shape.
from libs.schemas.benchmark import (  # noqa: E402
    BenchmarkConfig,
    BenchmarkPointResult,
    BenchmarkReport,
    BenchmarkWorkloadSpec,
    LengthPair,
    MemorySnapshot,
    PercentileStats,
    RecommendedOperatingConfiguration,
    RequestOutcome,
)
from libs.schemas.config import (  # noqa: E402
    CurriculumConfig,
    LabConfig,
    LoopBGateConfig,
    RevisionRule,
    ServingConfig,
    TrainingConfig,
)
from libs.schemas.results import (  # noqa: E402
    EvidenceKind,
    EvidenceRecord,
    HostEnvironment,
    ServingThroughputResult,
    TrainSmokeMetrics,
)

__all__ = [
    "Outcome",
    "Provenance",
    "TrajectoryStep",
    "Trajectory",
    "Verdict",
    "DatasetVersion",
    "TrainingRun",
    "EvalResult",
    "AuthzRequest",
    "AuthzDecision",
    "ServingConfig",
    "TrainingConfig",
    "CurriculumConfig",
    "LoopBGateConfig",
    "LabConfig",
    "RevisionRule",
    "HostEnvironment",
    "EvidenceKind",
    "EvidenceRecord",
    "ServingThroughputResult",
    "TrainSmokeMetrics",
    "BenchmarkConfig",
    "BenchmarkWorkloadSpec",
    "LengthPair",
    "MemorySnapshot",
    "RequestOutcome",
    "PercentileStats",
    "BenchmarkPointResult",
    "RecommendedOperatingConfiguration",
    "BenchmarkReport",
]
