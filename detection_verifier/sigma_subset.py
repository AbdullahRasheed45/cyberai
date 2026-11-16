"""Bounded Sigma-subset executor — one documented rule format, schema, backend.

Rewritten (Round 6) to fix defects found by adversarial probing:
  * Boolean precedence: `and` binds tighter than `or` (Sigma spec). Conditions
    parse into a validated AST with explicit precedence levels.
  * Whole-input tokenisation: unconsumed/invalid characters are rejected with a
    position, not silently discarded (`a!!!` -> error). Truncated expressions
    (`all of`) raise a structured RuleSyntaxError, never an IndexError.
  * Structural YAML validation: non-mapping logsource / non-string keys etc.
    raise RuleSyntaxError, not a generic crash.
  * Bounded candidate execution: rule size / value / regex-length caps and a
    per-match regex TIMEOUT (via the `regex` module) + event-field truncation,
    so a model-supplied pathological pattern cannot stall the pipeline.

Supported subset (unchanged in meaning):
  logsource.category: process_creation
  detection:
    <selection>: { <Field>[|contains|startswith|endswith|re|eq]: value|[values] }
    condition: or_expr
  or_expr  := and_expr ('or' and_expr)*
  and_expr := not_expr ('and' not_expr)*
  not_expr := 'not' not_expr | primary
  primary  := '(' or_expr ')' | quant | NAME
  quant    := ('all'|'any'|'1'|<int>) 'of' ('them' | NAME['*'])
Case-insensitive eq/contains/startswith/endswith; `re` is a timed regex.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

import regex as _regex  # third-party: supports search(..., timeout=)

# ---- bounds (candidate execution safety, defect #8) -------------------------
MAX_SELECTIONS = 32
MAX_CONDS_PER_SELECTION = 32
MAX_VALUES_PER_COND = 64
MAX_VALUE_LEN = 1024
MAX_REGEX_LEN = 512
MAX_CONDITION_LEN = 1024
MAX_EVENT_FIELD_LEN = 65536  # fields longer than this -> record REJECTED (never truncated)
MAX_EVENTS = 100000  # corpus-size bound (total-work limit)
MAX_PARSE_DEPTH = 64  # condition nesting-depth bound
REGEX_TIMEOUT_S = 0.25  # per-match wall-clock cap (one layer)
OVERALL_DEADLINE_S = 5.0  # whole-candidate evaluation budget (second layer)

_MODIFIERS = {"eq", "contains", "startswith", "endswith", "re"}


class RuleSyntaxError(ValueError):
    """Rule is outside the supported subset or malformed (a candidate failure)."""


class RuleExecutionError(RuntimeError):
    """A valid-looking rule failed at evaluation time (e.g. regex timeout)."""


# ---- condition AST ----------------------------------------------------------
@dataclass
class Sel:
    name: str


@dataclass
class Not:
    x: Any


@dataclass
class BinOp:
    op: str  # 'and' | 'or'
    left: Any
    r: Any


@dataclass
class Quant:
    kind: str  # 'all' | 'any' | int-as-str
    targets: list[str]


def _tokenise(cond: str) -> list[tuple[str, int]]:
    """Scan the WHOLE string; reject any unexpected character (defect #3)."""
    toks: list[tuple[str, int]] = []
    i, n = 0, len(cond)
    while i < n:
        c = cond[i]
        if c.isspace():
            i += 1
            continue
        if c in "()":
            toks.append((c, i))
            i += 1
            continue
        if c.isalnum() or c in "_*":
            j = i
            while j < n and (cond[j].isalnum() or cond[j] in "_*"):
                j += 1
            toks.append((cond[i:j], i))
            i = j
            continue
        raise RuleSyntaxError(f"unexpected character {c!r} at position {i} in condition")
    return toks


_KEYWORDS = {"and", "or", "not", "of", "them", "all", "any"}


class _Parser:
    def __init__(self, toks, names):
        self.toks = toks
        self.names = names
        self.pos = 0
        self.depth = 0

    def _descend(self):
        self.depth += 1
        if self.depth > MAX_PARSE_DEPTH:
            raise RuleSyntaxError(f"condition nesting exceeds depth bound {MAX_PARSE_DEPTH}")

    def _peek(self):
        return self.toks[self.pos][0] if self.pos < len(self.toks) else None

    def _next(self):
        if self.pos >= len(self.toks):
            raise RuleSyntaxError("unexpected end of condition")
        t = self.toks[self.pos]
        self.pos += 1
        return t[0]

    def parse(self):
        node = self._or()
        if self.pos != len(self.toks):
            raise RuleSyntaxError(f"trailing tokens in condition near {self.toks[self.pos]!r}")
        return node

    def _or(self):
        node = self._and()
        while self._peek() == "or":
            self._next()
            node = BinOp("or", node, self._and())
        return node

    def _and(self):
        node = self._not()
        while self._peek() == "and":
            self._next()
            node = BinOp("and", node, self._not())
        return node

    def _not(self):
        if self._peek() == "not":
            self._next()
            self._descend()
            node = Not(self._not())
            self.depth -= 1
            return node
        return self._primary()

    def _primary(self):
        t = self._peek()
        if t == "(":
            self._next()
            self._descend()
            node = self._or()
            self.depth -= 1
            if self._peek() != ")":
                raise RuleSyntaxError("unbalanced parentheses in condition")
            self._next()
            return node
        if t in ("all", "any", "1") or (t is not None and t.isdigit()):
            return self._quant()
        if t is None:
            raise RuleSyntaxError("unexpected end of condition")
        if t in _KEYWORDS:
            raise RuleSyntaxError(f"misplaced keyword {t!r} in condition")
        name = self._next()
        if name not in self.names:
            raise RuleSyntaxError(f"condition references unknown selection {name!r}")
        return Sel(name)

    def _quant(self):
        kind = self._next()  # all | any | 1 | <int>
        if kind not in ("all", "any") and not kind.isdigit():
            raise RuleSyntaxError(f"bad quantifier {kind!r}")
        if self._peek() != "of":
            raise RuleSyntaxError("quantifier must be followed by 'of'")
        self._next()
        tgt = self._peek()
        if tgt is None:
            raise RuleSyntaxError("quantifier 'of' is missing a target")
        self._next()
        if tgt == "them":
            targets = sorted(self.names)
        elif tgt.endswith("*"):
            prefix = tgt[:-1]
            targets = sorted(n for n in self.names if n.startswith(prefix))
            if not targets:
                raise RuleSyntaxError(f"pattern {tgt!r} matches no selection")
        else:
            if tgt not in self.names:
                raise RuleSyntaxError(f"quantifier target {tgt!r} is not a selection")
            targets = [tgt]
        if kind.isdigit() and not (0 < int(kind) <= len(targets)):
            raise RuleSyntaxError(
                f"quantifier count {kind} out of range for {len(targets)} targets"
            )
        return Quant(kind, targets)


def _referenced_selections(node) -> set[str]:
    if isinstance(node, Sel):
        return {node.name}
    if isinstance(node, Not):
        return _referenced_selections(node.x)
    if isinstance(node, BinOp):
        return _referenced_selections(node.left) | _referenced_selections(node.r)
    if isinstance(node, Quant):
        return set(node.targets)
    return set()


def _safe_search(pattern: str, text: str) -> bool:
    # No silent truncation (defect #5): oversized records are rejected at corpus
    # validation, so text here is already within MAX_EVENT_FIELD_LEN.
    try:
        return _regex.search(pattern, text, timeout=REGEX_TIMEOUT_S) is not None
    except TimeoutError as e:
        raise RuleExecutionError(f"regex timed out (> {REGEX_TIMEOUT_S}s): {pattern!r}") from e
    except _regex.error as e:
        raise RuleExecutionError(f"bad regex {pattern!r}: {e}") from e


@dataclass
class FieldCond:
    field_name: str
    modifier: str
    values: list[str]

    def matches(self, event: dict[str, Any]) -> bool:
        raw = event.get(self.field_name)
        if raw is None:
            return False
        s = str(raw)  # no truncation; oversized records are rejected upstream
        sl = s.lower()
        for v in self.values:
            vs = str(v)
            if self.modifier == "eq" and sl == vs.lower():
                return True
            if self.modifier == "contains" and vs.lower() in sl:
                return True
            if self.modifier == "startswith" and sl.startswith(vs.lower()):
                return True
            if self.modifier == "endswith" and sl.endswith(vs.lower()):
                return True
            if self.modifier == "re" and _safe_search(vs, s):
                return True
        return False


@dataclass
class Selection:
    name: str
    conds: list[FieldCond]

    def matches(self, event):  # AND across fields
        return all(c.matches(event) for c in self.conds)


@dataclass
class Rule:
    title: str
    selections: dict[str, Selection]
    condition_ast: Any
    allowed_fields: set[str] = field(default_factory=set)

    def referenced_selections(self) -> set[str]:
        return _referenced_selections(self.condition_ast)

    def referenced_fields(self) -> set[str]:
        out: set[str] = set()
        for name in self.referenced_selections():
            for c in self.selections[name].conds:
                out.add(c.field_name)
        return out

    def evaluate(self, event) -> bool:
        # Evaluate ONLY referenced selections (defect #6): unused selections do
        # no work and cannot contribute cost or semantics.
        ref = self.referenced_selections()
        res = {n: self.selections[n].matches(event) for n in ref}
        return _eval_ast(self.condition_ast, res)


def _eval_ast(node, res: dict[str, bool]) -> bool:
    if isinstance(node, Sel):
        return res.get(node.name, False)
    if isinstance(node, Not):
        return not _eval_ast(node.x, res)
    if isinstance(node, BinOp):
        line = _eval_ast(node.left, res)
        if node.op == "and":
            return line and _eval_ast(node.r, res)
        return line or _eval_ast(node.r, res)
    if isinstance(node, Quant):
        vals = [res.get(t, False) for t in node.targets]
        if node.kind == "all":
            return all(vals)
        if node.kind == "any":
            return any(vals)
        return sum(bool(v) for v in vals) >= int(node.kind)
    raise RuleExecutionError("corrupt condition AST")


def parse_rule(doc: Any, allowed_fields: set[str], category: str = "process_creation") -> Rule:
    if not isinstance(doc, dict):
        raise RuleSyntaxError("rule is not a mapping")
    title = str(doc.get("title", "")).strip()
    logsource = doc.get("logsource")
    if not isinstance(logsource, dict):
        raise RuleSyntaxError("logsource must be a mapping")
    if logsource.get("category") != category:
        raise RuleSyntaxError(f"logsource.category must be {category!r}")
    detection = doc.get("detection")
    if not isinstance(detection, dict):
        raise RuleSyntaxError("detection must be a mapping")
    if "condition" not in detection:
        raise RuleSyntaxError("detection has no condition")
    condition = detection["condition"]
    if not isinstance(condition, str) or not condition.strip():
        raise RuleSyntaxError("condition must be a non-empty string")
    if len(condition) > MAX_CONDITION_LEN:
        raise RuleSyntaxError("condition exceeds length bound")

    selections: dict[str, Selection] = {}
    for name, body in detection.items():
        if name == "condition":
            continue
        if not isinstance(name, str):
            raise RuleSyntaxError(f"selection key {name!r} is not a string")
        if not isinstance(body, dict) or not body:
            raise RuleSyntaxError(f"selection {name!r} must be a non-empty mapping")
        if len(body) > MAX_CONDS_PER_SELECTION:
            raise RuleSyntaxError(f"selection {name!r} exceeds field-condition bound")
        conds: list[FieldCond] = []
        for key, val in body.items():
            if not isinstance(key, str):
                raise RuleSyntaxError(f"field key {key!r} is not a string")
            fld, _, mod = key.partition("|")
            mod = mod or "eq"
            if mod not in _MODIFIERS:
                raise RuleSyntaxError(f"unsupported modifier {mod!r} on {fld!r}")
            if fld not in allowed_fields:
                raise RuleSyntaxError(
                    f"field {fld!r} not in telemetry schema {sorted(allowed_fields)}"
                )
            values = val if isinstance(val, list) else [val]
            if not values:
                raise RuleSyntaxError(f"empty value list for {key!r}")
            if len(values) > MAX_VALUES_PER_COND:
                raise RuleSyntaxError(f"too many values for {key!r}")
            svals = []
            for v in values:
                if isinstance(v, (dict, list)):
                    raise RuleSyntaxError(f"value for {key!r} must be scalar")
                sv = str(v)
                if len(sv) > MAX_VALUE_LEN:
                    raise RuleSyntaxError(f"value for {key!r} exceeds length bound")
                if mod == "re" and len(sv) > MAX_REGEX_LEN:
                    raise RuleSyntaxError(f"regex for {key!r} exceeds length bound")
                if mod == "re":
                    try:
                        _regex.compile(sv)
                    except _regex.error as e:
                        raise RuleSyntaxError(f"invalid regex for {key!r}: {e}") from e
                svals.append(sv)
            conds.append(FieldCond(fld, mod, svals))
        selections[name] = Selection(name, conds)

    if not selections:
        raise RuleSyntaxError("no selections defined")
    if len(selections) > MAX_SELECTIONS:
        raise RuleSyntaxError("too many selections")

    toks = _tokenise(condition)
    if not toks:
        raise RuleSyntaxError("empty condition after tokenising")
    ast = _Parser(toks, set(selections)).parse()
    return Rule(title, selections, ast, set(allowed_fields))


def evaluate_over(rule: Rule, events: list, deadline_abs: float) -> list[bool]:
    """Evaluate a rule over a corpus under ONE absolute monotonic deadline shared
    across the whole candidate (caller computes it once). Checks the clock BEFORE
    and AFTER each event's work, so an event that pushes past the deadline is
    caught (a cooperative check cannot interrupt a single in-flight event — that
    is what the OS-enforced isolation worker in isolation.py is for).
    """
    out = []
    for i, ev in enumerate(events):
        if time.monotonic() > deadline_abs:
            raise RuleExecutionError(f"overall evaluation deadline exceeded before event {i}")
        out.append(rule.evaluate(ev))
        if time.monotonic() > deadline_abs:
            raise RuleExecutionError(f"overall evaluation deadline exceeded after event {i}")
    return out


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    from collections import Counter

    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())
