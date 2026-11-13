"""Typed schemas for the serving benchmark harness (`scripts/bench/`).

**Scope note (important):** this is a measurement harness for the *serving
endpoint's* throughput/latency/capacity trade-offs — context length vs
concurrency vs batching, TTFT, inter-token latency, memory headroom. It is
NOT the brief's sealed cybersecurity capability benchmark
(`benchmarks/sealed/`), which scores whether a model generation is better
at security tasks. Nothing here touches that benchmark's scenarios or
scoring; see `docs/ARCHITECTURE.md` §4.8 for the separation.

Every result is a `harness_test` (ran against a controlled/mock endpoint,
proving the harness's own accounting/error-handling) or a real measurement
(`evidence=HARDWARE` in `BenchmarkReport`) — never ambiguous about which,
per CLAUDE.md directive #5 ("measure, don't assume") and #6 ("fail loud").
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from libs.schemas.results import EvidenceKind, HostEnvironment


class LengthPair(BaseModel):
    """One (input_tokens, output_tokens) point to test within a context bucket."""

    model_config = ConfigDict(extra="forbid")

    input_tokens: int = Field(gt=0)
    output_tokens: int = Field(gt=0)


class BenchmarkConfig(BaseModel):
    """`configs/benchmark.yaml` — the sweep definition. No magic numbers in
    the harness code: every bound and every sweep axis lives here."""

    model_config = ConfigDict(extra="forbid")

    seed: int
    warmup_requests_per_point: int = Field(ge=0)
    requests_per_point: int = Field(gt=0)
    max_requests_total: int = Field(gt=0)
    max_runtime_s: float = Field(gt=0)
    request_timeout_s: float = Field(gt=0)
    context_buckets: list[int] = Field(min_length=1)
    length_pairs: list[LengthPair] = Field(min_length=1)
    concurrency_levels: list[int] = Field(min_length=1)
    prefix_cache_probe_repeats: int = Field(ge=0)
    # Adapter ids to cycle through for the LoRA adapter-switching exercise.
    # Left empty until model_registry has certified adapters to point at.
    lora_adapters_to_exercise: list[str] = Field(default_factory=list)
    memory_sample_interval_s: float = Field(gt=0, default=5.0)
    # Optional latency SLA used only to compute a recommended operating
    # configuration from real measurements; if unset, the recommender still
    # runs but ranks on throughput alone.
    sla_p99_e2e_latency_s: float | None = Field(default=None, gt=0)


class BenchmarkWorkloadSpec(BaseModel):
    """One sweep point: a fully-specified, reproducible workload."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["sweep", "prefix_cache_probe", "adapter_switch"] = "sweep"
    context_bucket: int = Field(gt=0)
    input_tokens: int = Field(gt=0)
    output_tokens: int = Field(gt=0)
    concurrency: int = Field(gt=0)
    seed: int
    lora_adapter: str | None = None


class MemorySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taken_at: datetime
    system_mem_available_gib: float | None = Field(default=None, ge=0)
    system_mem_total_gib: float | None = Field(default=None, ge=0)
    gpu_mem_free_gib: float | None = Field(default=None, ge=0)
    gpu_mem_total_gib: float | None = Field(default=None, ge=0)
    source: Literal["proc_meminfo", "nvidia_smi", "unavailable"]


class RequestOutcome(BaseModel):
    """One request's measured result (or failure)."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    error: str | None = None
    timed_out: bool = False
    ttft_s: float | None = Field(default=None, ge=0)
    e2e_latency_s: float | None = Field(default=None, ge=0)
    # Gaps between successive SSE content chunks. vLLM may batch more than
    # one token per chunk, so this is INTER-CHUNK latency, not strictly
    # inter-TOKEN latency unless the server streams one token per chunk —
    # see docs/BENCHMARK_HARNESS.md.
    inter_chunk_latencies_s: list[float] = Field(default_factory=list)
    requested_input_tokens: int
    requested_output_tokens: int
    actual_prompt_tokens: int | None = None
    actual_completion_tokens: int | None = None
    # Heuristic only (no definitive per-request hit/miss flag from the
    # generic OpenAI-compatible endpoint): a repeat of the same prompt whose
    # TTFT is markedly lower than the first (cold) issue.
    prefix_cache_hit_hint: bool | None = None


class PercentileStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p50: float
    p90: float
    p99: float
    mean: float
    min: float
    max: float
    n: int = Field(gt=0)


class BenchmarkPointResult(BaseModel):
    """Aggregated outcome for one `BenchmarkWorkloadSpec`."""

    model_config = ConfigDict(extra="forbid")

    spec: BenchmarkWorkloadSpec
    n_requests: int = Field(ge=0)
    n_errors: int = Field(ge=0)
    n_timeouts: int = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    timeout_rate: float = Field(ge=0, le=1)
    # Only meaningful/filled at concurrency==1: this model's own tok/s on a
    # single in-flight request, not an aggregate.
    single_request_output_tok_s: PercentileStats | None = None
    # sum(completion_tokens across all requests at this point) / wall_time —
    # the batching-sensitive aggregate number. Compared ACROSS concurrency
    # levels in the report, never multiplied together with another point.
    aggregate_output_tok_s: float | None = Field(default=None, ge=0)
    ttft_s: PercentileStats | None = None
    inter_chunk_latency_s: PercentileStats | None = None
    e2e_latency_s: PercentileStats | None = None
    memory_before: MemorySnapshot | None = None
    memory_after: MemorySnapshot | None = None
    started_at: datetime
    finished_at: datetime


class RecommendedOperatingConfiguration(BaseModel):
    """Only ever produced from `evidence=HARDWARE` points; see
    `scripts/bench/run_benchmark.py` — never computed as a guess."""

    model_config = ConfigDict(extra="forbid")

    context_bucket: int
    recommended_concurrency: int
    rationale: str
    aggregate_output_tok_s: float
    p99_e2e_latency_s: float


class BenchmarkReport(BaseModel):
    """The full, exportable benchmark result — machine-readable (this JSON)
    plus a rendered Markdown report built from the same data
    (`scripts/bench/run_benchmark.py --out-report`)."""

    model_config = ConfigDict(extra="forbid")

    # harness_test=True means this ran against a controlled/mock endpoint to
    # test the harness's own accounting and failure handling — it is a
    # harness test, NOT a GPU performance result, regardless of what the
    # numbers inside it look like.
    harness_test: bool
    host: HostEnvironment
    evidence: EvidenceKind

    model: str
    model_revision: str
    served_model_name: str
    image_reference: str | None = None
    serving_config_snapshot: dict = Field(default_factory=dict)
    benchmark_config_snapshot: dict = Field(default_factory=dict)
    hardware_descriptor: dict = Field(default_factory=dict)

    points: list[BenchmarkPointResult] = Field(default_factory=list)
    adapter_switch_skipped_reason: str | None = None

    truncated: bool = False
    truncation_reason: str | None = None

    started_at: datetime
    finished_at: datetime

    # None/absent unless this is a real hardware run with enough passing
    # points to rank — never a guess (task requirement: "otherwise leave
    # that recommendation pending").
    recommended_operating_configuration: list[RecommendedOperatingConfiguration] | None = None
    recommendation_pending_reason: str | None = None
