"""The ONE documented entry point for evaluating UNTRUSTED (model-generated)
detection rules: it runs the full check inside the isolation worker so a
pathological candidate is bounded and isolated (Astra #3).

Trusted unit tests keep calling check_rule directly; untrusted candidates MUST
go through evaluate_untrusted_candidate. check_rule is module-level and picklable,
so it runs cleanly under run_isolated with the fork start method.
"""

from __future__ import annotations

from typing import Any

from .checker import EvaluationInputError, Verdict, check_rule  # noqa: F401 (re-exported)
from .isolation import CandidateError, CandidateTimeout, ResultTooLarge, run_isolated  # noqa: F401

DEFAULT_CANDIDATE_TIMEOUT_S = 10.0


def evaluate_untrusted_candidate(
    rule_doc: dict[str, Any],
    behaviour_present: list[dict],
    behaviour_absent: list[dict],
    *,
    out_of_scope: list[dict] | None = None,
    timeout_s: float = DEFAULT_CANDIDATE_TIMEOUT_S,
    **check_kwargs,
) -> Verdict:
    """Evaluate a model-generated rule under an OS-enforced wall-clock timeout.

    Returns a Verdict (VERIFIED/FAILED) for a well-formed evaluation — including
    a rule that FAILS on syntax/coverage (that is a normal verdict, not an error).
    Raises:
      * EvaluationInputError  — the telemetry/thresholds are invalid (operator fault)
      * CandidateTimeout      — the candidate exceeded its budget (killed)
      * ResultTooLarge        — the candidate returned an oversized result
      * CandidateError        — the candidate crashed without a usable result
    """
    kwargs = {"out_of_scope": out_of_scope, **check_kwargs}
    return run_isolated(
        check_rule, (rule_doc, behaviour_present, behaviour_absent), kwargs, timeout_s=timeout_s
    )
