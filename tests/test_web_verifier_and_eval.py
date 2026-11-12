"""Web beachhead (SQLi) verifier + held-out evaluation regression tests.

These assert SUBSTANTIVE properties, not a test count:
  - the generalizing rule VERIFIES across public regression train/dev/challenge;
  - an overfit rule PASSES train but FAILS on challenge (the disjoint design works);
  - crude/incidental rules FAIL;
  - McNemar + paired bootstrap recover a real improvement and reject noise.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from detection_verifier.checker import WEB_REQUEST_SCHEMA
from detection_verifier.evaluation import (
    AcceptanceController,
    load_split,
    mcnemar,
    paired_pass_rate_diff,
    score_rule_on_split,
)

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "fixtures" / "web"
WRULES = WEB / "rules"
SPLITS = ("train", "dev", "challenge")


def _rule(n):
    return yaml.safe_load((WRULES / n).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def splits():
    return {s: load_split(str(WEB), s) for s in SPLITS}


# --- the generalizing rule works on every public regression split -----------


@pytest.mark.parametrize("split", SPLITS)
def test_good_rule_verifies_on_all_splits(splits, split):
    r = score_rule_on_split(_rule("good.yml"), splits[split], WEB_REQUEST_SCHEMA)
    assert r.outcome == "VERIFIED", (split, r.as_dict())
    assert r.metrics.coverage == 1.0
    assert r.metrics.fp == 0
    assert r.verifier_name == "detection.web_request"  # provenance tracks telemetry domain


# --- the overfit rule is the whole point of a held-out split -----------------


def test_overfit_rule_passes_train_but_fails_challenge(splits):
    rule = _rule("overfit.yml")
    train_verdict = score_rule_on_split(rule, splits["train"], WEB_REQUEST_SCHEMA)
    assert train_verdict.outcome == "VERIFIED"
    train = train_verdict.metrics
    held = score_rule_on_split(rule, splits["challenge"], WEB_REQUEST_SCHEMA)
    # it keys on a train-only payload family, so it cannot carry to challenge
    assert train.coverage == 1.0
    assert held.metrics.coverage == 0.0
    assert held.outcome != "VERIFIED"
    assert held.metrics.coverage < train.coverage  # demonstrable generalization gap


@pytest.mark.parametrize("rule_file", ["trivial.yml", "incidental_only.yml"])
def test_crude_rules_fail(splits, rule_file):
    r = score_rule_on_split(_rule(rule_file), splits["challenge"], WEB_REQUEST_SCHEMA)
    assert r.outcome != "VERIFIED", (rule_file, r.as_dict())


# --- paired-difference analysis ----------------------------------------------


def test_mcnemar_detects_one_sided_improvement():
    # candidate fixes 8 tasks the base failed, breaks none
    base = [False] * 8 + [True] * 12
    cand = [True] * 20
    m = mcnemar(base, cand)
    assert m["c"] == 8 and m["b"] == 0
    assert m["p_value"] < 0.01


def test_mcnemar_null_when_symmetric():
    base = [True, False] * 10
    cand = [False, True] * 10
    m = mcnemar(base, cand)
    assert m["p_value"] > 0.2  # 10 vs 10 discordant -> no evidence of direction


def test_paired_bootstrap_ci_excludes_zero_on_real_gain():
    base = [False] * 10 + [True] * 10
    cand = [True] * 20
    d = paired_pass_rate_diff(base, cand, iters=1000, seed=1)
    assert d["diff"] == 0.5
    assert d["improved"] and d["ci95"][0] > 0


def test_paired_bootstrap_ci_includes_zero_on_noise():
    base = [True, False] * 10
    cand = [False, True] * 10
    d = paired_pass_rate_diff(base, cand, iters=1000, seed=1)
    assert d["ci95"][0] <= 0 <= d["ci95"][1]
    assert not d["improved"]


def test_cluster_bootstrap_widens_ci_vs_iid():
    # one family of 10 correlated tasks + one of 10; a per-task CI is falsely tight
    base = [False] * 20
    cand = [True] * 10 + [False] * 10  # whole first family improved, second not
    fams = ["A"] * 10 + ["B"] * 10
    iid = paired_pass_rate_diff(base, cand, iters=2000, seed=3)
    clustered = paired_pass_rate_diff(base, cand, families=fams, iters=2000, seed=3)
    iid_w = iid["ci95"][1] - iid["ci95"][0]
    cl_w = clustered["ci95"][1] - clustered["ci95"][0]
    assert cl_w > iid_w  # clustering refuses to treat 20 correlated tasks as 20 independent


# --- restricted-acceptance access policy -------------------------------------


def test_acceptance_controller_enforces_budget(tmp_path):
    ac = AcceptanceController(
        ledger_path=tmp_path / "acceptance.sqlite", set_id="fixture-v1", max_uses=2
    )
    ac.score(lambda: 1, model_id="base-v1", experiment_id="exp1")
    ac.score(lambda: 1, model_id="candidate-v1", experiment_id="exp1")
    with pytest.raises(RuntimeError):
        ac.score(lambda: 1, model_id="candidate-v2", experiment_id="exp2")


# --- web SFT pilot builder ---------------------------------------------------


def test_web_pilot_builds_and_gates_on_development():
    from rental.web_pilot import build_web_pilot_examples

    ex = build_web_pilot_examples(str(WEB))
    assert len(ex) >= 3
    for e in ex:
        roles = [m["role"] for m in e["messages"]]
        assert roles == ["user", "assistant"]
        assert "<rule>" in e["messages"][1]["content"]
        # challenge payloads must NOT leak into the shown (train-only) prompt
        assert "DROP TABLE" not in e["messages"][0]["content"]


def test_web_pilot_refuses_nongeneralizing_target(tmp_path, monkeypatch):
    # point the builder at a fixtures dir whose good.yml is the OVERFIT rule
    import shutil

    dst = tmp_path / "web"
    shutil.copytree(WEB, dst)
    (dst / "rules" / "good.yml").write_text((WRULES / "overfit.yml").read_text(encoding="utf-8"))
    from rental.web_pilot import build_web_pilot_examples

    with pytest.raises(ValueError, match="does not verify on dev"):
        build_web_pilot_examples(str(dst))
