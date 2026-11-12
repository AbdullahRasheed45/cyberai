"""DetectionChecker — deterministic verdict for a generated detection rule.

Round-7 fixes:
  #4 telemetry contract: records missing a REQUIRED field (absent or null) are
     rejected as invalid input — an absent observation never becomes silent
     evidence that a rule avoided a false positive. Completeness is reported.
  #5 no silent truncation: an oversized field value makes the record invalid
     input (rejected), never a semantics-changing truncation.
  #6 the whole candidate runs under an overall evaluation deadline.
  #9 labels are separated: behaviour_present / behaviour_absent / out_of_scope.
     "Benign" is not a detector label; maliciousness is a separate task. The
     objective's restricted scope (payload length >= N) is named consistently;
     shorter-payload invocations are OUT OF SCOPE, not negatives.

Outcomes: VERIFIED | FAILED. Invalid harness input -> EvaluationInputError.
No LLM anywhere (Prime Directive #3).
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from math import isfinite, isinf, isnan
from typing import Any

from .sigma_subset import (
    MAX_EVENT_FIELD_LEN,
    MAX_EVENTS,
    OVERALL_DEADLINE_S,
    Rule,
    RuleExecutionError,
    RuleSyntaxError,
    evaluate_over,
    parse_rule,
    shannon_entropy,
)


@dataclass(frozen=True)
class TelemetrySchema:
    """Telemetry contract per objective domain (process_creation, web, ...).
    behavioral = fields carrying the detected behaviour; incidental = context
    (identifiers a rule must not key on alone); required = present+non-null;
    payload = fields where a base64 blob literal is a suspected overfit."""

    behavioral: frozenset
    incidental: frozenset
    required: frozenset
    payload: frozenset = frozenset()
    category: str = "process_creation"
    captured_empty_allowed: frozenset = frozenset()

    @property
    def all(self) -> frozenset:
        return self.behavioral | self.incidental


PROCESS_CREATION_SCHEMA = TelemetrySchema(
    behavioral=frozenset(
        {"Image", "OriginalFileName", "CommandLine", "ParentImage", "TargetFilename"}
    ),
    incidental=frozenset(
        {"User", "ComputerName", "SourceIp", "UtcTime", "LogonId", "ProcessGuid", "Hashes"}
    ),
    required=frozenset({"Image", "CommandLine"}),
    payload=frozenset({"CommandLine"}),
    category="process_creation",
)
# Web request telemetry (access log / WAF event) — the web beachhead.
WEB_REQUEST_SCHEMA = TelemetrySchema(
    behavioral=frozenset({"Method", "UriPath", "QueryString", "Body", "UserAgent", "Referer"}),
    incidental=frozenset({"SourceIp", "Host", "Status", "RequestId", "UtcTime"}),
    required=frozenset({"Method", "UriPath", "QueryString", "Body"}),
    captured_empty_allowed=frozenset({"QueryString", "Body"}),
    payload=frozenset(),
    category="web_request",
)

# Backward-compatible module constants (process_creation defaults).
BEHAVIORAL_FIELDS = set(PROCESS_CREATION_SCHEMA.behavioral)
INCIDENTAL_FIELDS = set(PROCESS_CREATION_SCHEMA.incidental)
SCHEMA_FIELDS = set(PROCESS_CREATION_SCHEMA.all)
REQUIRED_FIELDS = set(PROCESS_CREATION_SCHEMA.required)

DEFAULT_CMIN = 0.80
DEFAULT_FPMAX = 0.0
_PAYLOAD_CHARSET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
_PAYLOAD_MIN_LEN = 16
_PAYLOAD_MIN_ENTROPY = 3.0


class EvaluationInputError(ValueError):
    """Harness input is invalid (NOT a candidate verdict)."""


@dataclass
class DetectionMetrics:
    syntax_valid: bool = False
    execution_valid: bool = False
    has_behavioral_field: bool = False
    coverage: float = 0.0
    fp_burden: float = 0.0
    tp: int = 0
    fn: int = 0
    fp: int = 0
    tn: int = 0
    n_behaviour_present: int = 0
    n_behaviour_absent: int = 0
    n_out_of_scope: int = 0
    out_of_scope_fires: int = 0  # informational only; NOT counted as FP
    completeness: float = 1.0  # fraction of records with all schema fields
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Verdict:
    outcome: str
    metrics: DetectionMetrics
    verifier_name: str = "detection.process_creation"  # overridden per telemetry category
    verifier_version: str = "0.3.0"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_corpus(events: Any, name: str, schema: TelemetrySchema) -> float:
    """Validate a corpus against the telemetry contract. Returns completeness
    (fraction of records carrying every schema field). Raises on invalid input."""
    if not isinstance(events, list) or not events:
        raise EvaluationInputError(f"{name} corpus must be a non-empty list")
    if len(events) > MAX_EVENTS:
        raise EvaluationInputError(f"{name} corpus exceeds MAX_EVENTS={MAX_EVENTS}")
    field_coverage_sum = 0.0
    for i, ev in enumerate(events):
        if not isinstance(ev, dict):
            raise EvaluationInputError(f"{name}[{i}] is not a mapping")
        for k, v in ev.items():
            if not isinstance(k, str):
                raise EvaluationInputError(f"{name}[{i}] has non-string key {k!r}")
            if v is None:
                continue  # explicit null for an optional field is allowed
            # defect #4: schema fields are TEXT; bool/int/float are contract
            # violations, not silently stringified (bool is an int subclass).
            if k in schema.all and not isinstance(v, str):
                raise EvaluationInputError(
                    f"{name}[{i}].{k} must be a string, got {type(v).__name__} {v!r}"
                )
            if isinstance(v, str) and len(v) > MAX_EVENT_FIELD_LEN:
                raise EvaluationInputError(  # defect #5: reject, never truncate
                    f"{name}[{i}].{k} exceeds MAX_EVENT_FIELD_LEN={MAX_EVENT_FIELD_LEN} "
                    f"(oversized record rejected, not truncated)"
                )
        # defect #4: required fields present, non-null, non-empty strings
        for rf in schema.required:
            if rf not in ev:
                raise EvaluationInputError(
                    f"{name}[{i}] missing required field {rf!r} (unevaluable)"
                )
            if ev[rf] is None:
                raise EvaluationInputError(f"{name}[{i}].{rf} is null (required; unevaluable)")
            if not isinstance(ev[rf], str) or (
                ev[rf] == "" and rf not in schema.captured_empty_allowed
            ):
                raise EvaluationInputError(
                    f"{name}[{i}].{rf} must be a non-empty string (unevaluable)"
                )
        # mean fractional field-coverage across the schema (informational, #4)
        present = sum(1 for f in schema.all if ev.get(f) is not None)
        field_coverage_sum += present / len(schema.all)
    return field_coverage_sum / len(events)


def _validate_thresholds(cmin, fpmax, deadline_s) -> None:
    for nm, x in (("cmin", cmin), ("fpmax", fpmax)):
        if not isinstance(x, (int, float)) or not isfinite(x) or not (0.0 <= float(x) <= 1.0):
            raise EvaluationInputError(f"threshold {nm}={x!r} must be a finite number in [0,1]")
    if (
        not isinstance(deadline_s, (int, float))
        or isnan(deadline_s)
        or isinf(deadline_s)
        or deadline_s <= 0
    ):
        raise EvaluationInputError(f"deadline_s={deadline_s!r} must be a positive finite number")


def _payload_warnings(rule: Rule, payload_fields: frozenset) -> list[str]:
    warns: list[str] = []
    for name in rule.referenced_selections():
        for c in rule.selections[name].conds:
            if c.field_name not in payload_fields or c.modifier not in ("eq", "contains"):
                continue
            for v in c.values:
                if (
                    len(v) >= _PAYLOAD_MIN_LEN
                    and set(v) <= _PAYLOAD_CHARSET
                    and shannon_entropy(v) >= _PAYLOAD_MIN_ENTROPY
                ):
                    warns.append(
                        f"suspected payload literal on {c.field_name} "
                        f"(len={len(v)}, entropy={shannon_entropy(v):.1f}): {v[:12]}…"
                    )
    return warns


def check_rule(
    rule_doc: dict[str, Any],
    behaviour_present: list[dict[str, Any]],
    behaviour_absent: list[dict[str, Any]],
    *,
    out_of_scope: list[dict[str, Any]] | None = None,
    schema: TelemetrySchema = PROCESS_CREATION_SCHEMA,
    cmin: float = DEFAULT_CMIN,
    fpmax: float = DEFAULT_FPMAX,
    deadline_s: float = OVERALL_DEADLINE_S,
) -> Verdict:
    _validate_thresholds(cmin, fpmax, deadline_s)
    vname = f"detection.{schema.category}"
    allowed_fields = set(schema.all)
    c_pos = _validate_corpus(behaviour_present, "behaviour_present", schema)
    c_neg = _validate_corpus(behaviour_absent, "behaviour_absent", schema)
    oos = out_of_scope or []
    c_oos = _validate_corpus(oos, "out_of_scope", schema) if oos else 1.0

    m = DetectionMetrics(
        n_behaviour_present=len(behaviour_present),
        n_behaviour_absent=len(behaviour_absent),
        n_out_of_scope=len(oos),
    )
    total = len(behaviour_present) + len(behaviour_absent) + len(oos)
    m.completeness = round(
        (c_pos * len(behaviour_present) + c_neg * len(behaviour_absent) + c_oos * len(oos)) / total,
        3,
    )

    try:
        rule = parse_rule(rule_doc, allowed_fields, schema.category)
        m.syntax_valid = True
    except RuleSyntaxError as e:
        m.reasons.append(f"syntax: {e}")
        return Verdict("FAILED", m, verifier_name=vname)

    try:
        # ONE absolute deadline shared across all three corpora (defect #3)
        deadline_abs = time.monotonic() + deadline_s
        pos_hits = evaluate_over(rule, behaviour_present, deadline_abs)
        neg_hits = evaluate_over(rule, behaviour_absent, deadline_abs)
        oos_hits = evaluate_over(rule, oos, deadline_abs) if oos else []
        m.execution_valid = True
    except RuleExecutionError as e:
        m.reasons.append(f"execution: {e}")
        return Verdict("FAILED", m, verifier_name=vname)

    ref_behavioral = rule.referenced_fields() & set(schema.behavioral)
    m.has_behavioral_field = bool(ref_behavioral)
    if not m.has_behavioral_field:
        m.reasons.append(
            "incidental-only: referenced selections use no behavioural field "
            f"({sorted(schema.behavioral)})"
        )
    m.warnings.extend(_payload_warnings(rule, schema.payload))

    m.tp = sum(pos_hits)
    m.fn = len(pos_hits) - m.tp
    m.fp = sum(neg_hits)
    m.tn = len(neg_hits) - m.fp
    m.out_of_scope_fires = sum(oos_hits)  # reported, NOT a FP (defect #9)
    m.coverage = m.tp / len(pos_hits)
    m.fp_burden = m.fp / len(neg_hits)

    passed = (
        m.syntax_valid
        and m.execution_valid
        and m.has_behavioral_field
        and m.coverage >= cmin
        and m.fp_burden <= fpmax
    )
    if not passed:
        if m.coverage < cmin:
            m.reasons.append(
                f"coverage {m.coverage:.2f} ({m.tp}/{m.n_behaviour_present}) < Cmin {cmin:.2f}"
            )
        if m.fp_burden > fpmax:
            m.reasons.append(
                f"fp_burden {m.fp_burden:.2f} ({m.fp}/{m.n_behaviour_absent}) > FPmax {fpmax:.2f}"
            )
    return Verdict("VERIFIED" if passed else "FAILED", m, verifier_name=vname)
