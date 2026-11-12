"""AssuranceSuite — who checks the checker (brief §6.6), Round-6 corrected.

Fixes:
  #1 certify() requires a named set of MANDATORY checks to be present and all
     passed; it rejects missing / duplicate / failed / errored checks instead of
     all()-ing over whatever happened to be supplied. certify([]) is False.
  #6 the former "corpus_integrity" is renamed to what it actually is:
     reference_rule_consistency — it checks agreement between a reference rule
     and the fixtures. It does NOT independently establish labels; fixture
     provenance is asserted separately in objective.yaml.

Honest residual assumption (#9): the checker and the fixtures share one
observation channel (the loader). Independence here is limited to the
reference-rule consistency probe; a corrupted loader would fool both.
"""

from __future__ import annotations

from dataclasses import dataclass

from .checker import EvaluationInputError, check_rule

MANDATORY_CHECKS = frozenset(
    {"seed:good", "seed:trivial", "reference_rule_consistency", "determinism"}
)


@dataclass
class AssuranceResult:
    name: str
    passed: bool
    detail: str
    errored: bool = False


def run_seed_suite(cases, pos, ben):
    """cases: (short_name, rule_doc, expected_outcome) -> names 'seed:<short_name>'."""
    out = []
    for short, rule_doc, expected in cases:
        try:
            v = check_rule(rule_doc, pos, ben)
            out.append(
                AssuranceResult(
                    f"seed:{short}",
                    v.outcome == expected,
                    f"expected={expected} got={v.outcome} reasons={v.metrics.reasons}",
                )
            )
        except EvaluationInputError as e:
            out.append(AssuranceResult(f"seed:{short}", False, f"input error: {e}", errored=True))
    return out


def run_reference_rule_consistency(reference_rule, pos, ben):
    """A fixture set CONSISTENT with the reference rule yields coverage=1.0 /
    fp=0. Divergence flags a reference/fixture mismatch — it does NOT by itself
    prove the labels are correct (that is the objective's provenance job)."""
    try:
        v = check_rule(reference_rule, pos, ben)
    except EvaluationInputError as e:
        return AssuranceResult(
            "reference_rule_consistency", False, f"input error: {e}", errored=True
        )
    consistent = v.metrics.coverage == 1.0 and v.metrics.fp == 0
    return AssuranceResult(
        "reference_rule_consistency",
        consistent,
        f"coverage={v.metrics.coverage:.2f} fp={v.metrics.fp} "
        f"(consistent requires coverage=1.0, fp=0; this is agreement, not label truth)",
    )


def run_determinism(rule_doc, pos, ben):
    try:
        a = check_rule(rule_doc, pos, ben).outcome
        b = check_rule(rule_doc, pos, ben).outcome
    except EvaluationInputError as e:
        return AssuranceResult("determinism", False, f"input error: {e}", errored=True)
    return AssuranceResult("determinism", a == b, f"{a} == {b}")


def certify(results, required=MANDATORY_CHECKS) -> tuple[bool, list[str]]:
    """Return (ok, reasons). Reject missing/duplicate/failed/errored checks."""
    reasons: list[str] = []
    names = [r.name for r in results]
    seen = set()
    dups = {n for n in names if n in seen or seen.add(n)}
    if dups:
        reasons.append(f"duplicate checks: {sorted(dups)}")
    present = set(names)
    missing = set(required) - present
    if missing:
        reasons.append(f"missing mandatory checks: {sorted(missing)}")
    for r in results:
        if r.errored:
            reasons.append(f"check errored: {r.name} ({r.detail})")
        elif not r.passed:
            reasons.append(f"check failed: {r.name} ({r.detail})")
    return (len(reasons) == 0, reasons)
