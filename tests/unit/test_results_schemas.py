from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from libs.schemas import (
    EvidenceKind,
    EvidenceRecord,
    HostEnvironment,
    ServingThroughputResult,
    TrainSmokeMetrics,
)


def test_evidence_record_roundtrip():
    result = ServingThroughputResult(single_stream_tok_s=61.4, batch_tok_s=301.0, batch_size=32)
    rec = EvidenceRecord(
        label="vllm_serve_smoke",
        host=HostEnvironment.GB10_CLOUD,
        evidence=EvidenceKind.HARDWARE,
        command="uv run python scripts/measure_throughput.py",
        passed=True,
        result=result.model_dump(),
        measured_at=datetime.now(UTC),
    )
    restored = EvidenceRecord.model_validate_json(rec.model_dump_json())
    assert restored.host == HostEnvironment.GB10_CLOUD
    assert restored.evidence == EvidenceKind.HARDWARE
    assert restored.result["batch_size"] == 32


def test_local_evidence_cannot_be_mistaken_for_hardware():
    """Distinct enum values — a LOCAL run is never serialised as HARDWARE."""
    rec = EvidenceRecord(
        label="config_schema_check",
        host=HostEnvironment.WINDOWS_DEV,
        evidence=EvidenceKind.LOCAL,
        command="uv run pytest -q",
        passed=True,
        measured_at=datetime.now(UTC),
    )
    assert rec.evidence != EvidenceKind.HARDWARE


def test_negative_throughput_rejected():
    with pytest.raises(ValidationError):
        ServingThroughputResult(single_stream_tok_s=-1.0)


def test_train_smoke_metrics_cpu_only_is_representable_but_explicit():
    """A CPU-only torch wheel (brief BLOCKER #2 failure mode) must still be
    representable — fail loud means recording the failure, not refusing to
    construct it."""
    metrics = TrainSmokeMetrics(torch_cuda_available=False, torch_cuda_version=None)
    assert metrics.torch_cuda_available is False
