"""Development scoring, paired statistics and controlled acceptance-use ledger.

Roles (Astra, repeatedly requested):
  - TRAIN  split   -> source of SFT training data (and the pilot targets).
  - DEV    split   -> recipe/hyperparameter selection; may be scored freely.
  - HELDOUT split  -> RESTRICTED acceptance: generator-disjoint from train, scored
                      at a planned point only, under an access + refresh policy.
Bundled hand-authored splits are public regression data, not demonstrated
generator-disjoint acceptance evidence. Fresh restricted acceptance data is required.

Statistics: a candidate vs a base model are compared PAIRED on the SAME heldout
tasks â€” McNemar on discordant pairs + a (cluster) bootstrap CI for the pass-rate
DIFFERENCE. Not non-overlapping CIs of two models (which don't estimate the diff
and are over-conservative).
"""

from __future__ import annotations

import json
import math
import random
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .acceptance import evaluate_untrusted_candidate
from .checker import TelemetrySchema


def load_split(fixtures_dir: str, split: str) -> dict:
    d = Path(fixtures_dir) / split

    def jl(name):
        p = d / f"{name}.jsonl"
        return (
            [
                json.loads(line)
                for line in p.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if p.exists()
            else []
        )

    return {
        "behaviour_present": jl("behaviour_present"),
        "behaviour_absent": jl("behaviour_absent"),
        "out_of_scope": jl("out_of_scope"),
    }


def score_rule_on_split(rule_doc: dict, split: dict, schema: TelemetrySchema, **kw):
    return evaluate_untrusted_candidate(
        rule_doc,
        split["behaviour_present"],
        split["behaviour_absent"],
        out_of_scope=split["out_of_scope"],
        schema=schema,
        **kw,
    )


def mcnemar(base_pass: list[bool], cand_pass: list[bool]) -> dict:
    """Exact two-sided McNemar over paired pass/fail on the SAME tasks."""
    _validate_pairs(base_pass, cand_pass)
    b = sum(
        1 for x, y in zip(base_pass, cand_pass, strict=True) if x and not y
    )  # base win, cand lose
    c = sum(
        1 for x, y in zip(base_pass, cand_pass, strict=True) if y and not x
    )  # cand win, base lose
    n = b + c
    if n == 0:
        return {"b": 0, "c": 0, "p_value": 1.0, "inference_scope": "independent_pairs_only"}
    k = min(b, c)
    # Divide integers before float conversion; 2.0 * a large integer overflows.
    p = (2 * sum(math.comb(n, i) for i in range(k + 1))) / (1 << n)
    return {"b": b, "c": c, "p_value": min(1.0, p), "inference_scope": "independent_pairs_only"}


def paired_pass_rate_diff(
    base_pass: list[bool],
    cand_pass: list[bool],
    families: list | None = None,
    iters: int = 2000,
    seed: int = 0,
) -> dict:
    """Pass-rate DIFFERENCE (candidate - base) with a 95% bootstrap CI. If
    `families` are given, resamples at the family level (cluster bootstrap) so
    related tasks don't inflate confidence."""
    _validate_pairs(base_pass, cand_pass)
    if type(iters) is not int or iters < 2:
        raise ValueError("iters must be an integer >= 2")
    n = len(base_pass)
    if families is not None:
        if not isinstance(families, list) or len(families) != n:
            raise ValueError("families must align with every paired task")
        if any(not isinstance(f, str) or not f.strip() for f in families):
            raise ValueError("family IDs must be nonempty strings")
    diff = (sum(cand_pass) - sum(base_pass)) / n
    n_units = len(set(families)) if families is not None else n
    if n_units < 2:
        return {
            "diff": round(diff, 4),
            "ci95": None,
            "improved": False,
            "n_tasks": n,
            "clustered": families is not None,
            "n_independent_units": n_units,
            "inference_supported": False,
            "reason": "at least two independent units are required",
        }
    rng = random.Random(seed)
    idx_by_family = {}
    if families:
        for i, f in enumerate(families):
            idx_by_family.setdefault(f, []).append(i)
        fam_keys = list(idx_by_family)
    diffs = []
    for _ in range(iters):
        if families:
            picked = [i for _ in fam_keys for i in idx_by_family[rng.choice(fam_keys)]]
        else:
            picked = [rng.randrange(n) for _ in range(n)]
        bb = sum(base_pass[i] for i in picked)
        cc = sum(cand_pass[i] for i in picked)
        diffs.append((cc - bb) / len(picked))
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[int(0.975 * len(diffs)) - 1]
    return {
        "diff": round(diff, 4),
        "ci95": [round(lo, 4), round(hi, 4)],
        "improved": lo > 0,
        "n_tasks": n,
        "clustered": families is not None,
        "n_independent_units": n_units,
        "inference_supported": True,
        "inference_scope": "family_bootstrap"
        if families is not None
        else "independent_task_bootstrap",
    }


def _validate_pairs(base_pass, cand_pass) -> None:
    if not isinstance(base_pass, list) or not isinstance(cand_pass, list):
        raise ValueError("paired vectors must be lists")
    if not base_pass or len(base_pass) != len(cand_pass):
        raise ValueError("paired vectors must be nonempty and equal length")
    if any(type(v) is not bool for v in base_pass + cand_pass):
        raise ValueError("paired outcomes must be booleans")


def compare_task_results(
    base_by_task: dict, candidate_by_task: dict, families_by_task: dict | None = None, **kwargs
) -> dict:
    """Align keyed outcomes before computing a difference; no order-based joins.

    With family labels this reports only family-bootstrap inference. A separate
    unclustered McNemar p-value must not be used as family-level evidence.
    """
    if not isinstance(base_by_task, dict) or not isinstance(candidate_by_task, dict):
        raise ValueError("task outcomes must be mappings")
    if not base_by_task or set(base_by_task) != set(candidate_by_task):
        raise ValueError("base and candidate must contain the same nonempty task IDs")
    if any(not isinstance(k, str) or not k.strip() for k in base_by_task):
        raise ValueError("task IDs must be nonempty strings")
    if families_by_task is not None and (
        not isinstance(families_by_task, dict) or set(families_by_task) != set(base_by_task)
    ):
        raise ValueError("family labels must cover exactly the paired task IDs")
    task_ids = sorted(base_by_task)
    result = paired_pass_rate_diff(
        [base_by_task[k] for k in task_ids],
        [candidate_by_task[k] for k in task_ids],
        families=[families_by_task[k] for k in task_ids] if families_by_task is not None else None,
        **kwargs,
    )
    result["task_ids"] = task_ids
    return result


@dataclass
class AcceptanceController:
    """Persistent controlled-development access ledger, not a security sandbox.

    set_id must identify an immutable acceptance manifest. Reserve before scoring
    so failed/interrupted attempts consume budget too. A recreated controller
    cannot reset usage or raise the stored budget. Direct lower-level scorers are
    for regression/development only, never restricted acceptance evidence.
    """

    ledger_path: str | Path
    set_id: str
    max_uses: int = 3

    def __post_init__(self):
        if not isinstance(self.set_id, str) or not self.set_id.strip():
            raise ValueError("set_id must identify an immutable acceptance set")
        if type(self.max_uses) is not int or self.max_uses <= 0:
            raise ValueError("max_uses must be a positive integer")
        self.ledger_path = Path(self.ledger_path)
        if str(self.ledger_path) == ":memory:":
            raise ValueError("acceptance ledger must persist on disk")
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.ledger_path)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS acceptance_sets "
                "(set_id TEXT PRIMARY KEY, max_uses INTEGER NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS acceptance_uses "
                "(id INTEGER PRIMARY KEY, set_id TEXT NOT NULL, model_id TEXT NOT NULL, "
                "experiment_id TEXT NOT NULL, reserved_at TEXT NOT NULL)"
            )
            db.execute(
                "INSERT OR IGNORE INTO acceptance_sets VALUES (?, ?)", (self.set_id, self.max_uses)
            )
            stored = db.execute(
                "SELECT max_uses FROM acceptance_sets WHERE set_id=?", (self.set_id,)
            ).fetchone()[0]
            if stored != self.max_uses:
                raise ValueError("acceptance set budget differs from the immutable stored budget")

    @property
    def uses(self):
        with closing(sqlite3.connect(self.ledger_path)) as db, db:
            return db.execute(
                "SELECT COUNT(*) FROM acceptance_uses WHERE set_id=?", (self.set_id,)
            ).fetchone()[0]

    def score(self, fn, *args, model_id: str, experiment_id: str, **kwargs):
        for name, value in (("model_id", model_id), ("experiment_id", experiment_id)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty immutable identity")
        with closing(sqlite3.connect(self.ledger_path, timeout=10)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            stored = db.execute(
                "SELECT max_uses FROM acceptance_sets WHERE set_id=?", (self.set_id,)
            ).fetchone()
            if stored is None or stored[0] != self.max_uses:
                raise ValueError("acceptance set budget differs from the immutable stored budget")
            used = db.execute(
                "SELECT COUNT(*) FROM acceptance_uses WHERE set_id=?", (self.set_id,)
            ).fetchone()[0]
            if used >= self.max_uses:
                raise RuntimeError("acceptance set exhausted — rotate/refresh before re-use")
            db.execute(
                "INSERT INTO acceptance_uses "
                "(set_id, model_id, experiment_id, reserved_at) VALUES (?, ?, ?, ?)",
                (self.set_id, model_id, experiment_id, datetime.now(UTC).isoformat()),
            )
        return fn(*args, **kwargs)
