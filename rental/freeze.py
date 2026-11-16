"""Freeze-file validation: a frozen config has no placeholders, pinned commits/
digests, and pinned dependencies (Astra #5). Model lineage is coherent (#3)."""

from __future__ import annotations

import re

_PLACEHOLDER = re.compile(r"FILL|changeme|<[^>]+>|TODO", re.I)
_SHA = re.compile(r"[0-9a-f]{40}")
_DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")

_REQUIRED = [
    "reference_candidate",
    "trainable_base_repo",
    "trainable_base_commit",
    "tokenizer_identity",
    "serving_base_repo",
    "serving_base_commit",
    "serving_quantisation",
    "serving_quant_provenance",
    "vllm_image",
    "unsloth_image",
    "adapter_targets",
    "trainable_serving_relation_attested",
]


def validate_freeze(cfg: dict) -> list[str]:
    errs: list[str] = []
    if not isinstance(cfg, dict):
        return ["freeze config is not a mapping"]
    for k in _REQUIRED:
        if k not in cfg or cfg[k] in (None, "", []):
            errs.append(f"missing/empty: {k}")
        elif isinstance(cfg[k], str) and _PLACEHOLDER.search(cfg[k]):
            errs.append(f"placeholder in {k}: {cfg[k]!r}")
    for k in ("trainable_base_commit", "serving_base_commit"):
        v = cfg.get(k, "")
        if isinstance(v, str) and v and not _SHA.fullmatch(v):
            errs.append(f"{k} is not a 40-hex commit")
    for k in ("vllm_image", "unsloth_image"):
        v = cfg.get(k, "")
        if isinstance(v, str) and v and not _DIGEST.search(v):
            errs.append(f"{k} is not pinned by @sha256 digest")
    deps = cfg.get("dependencies") or []
    required_deps = {"transformers", "unsloth", "peft", "trl", "bitsandbytes"}
    seen = set()
    _VER = re.compile(r"[0-9][0-9A-Za-z.+!-]*$")
    for d in deps:
        if (
            not isinstance(d, str)
            or "==" not in d
            or any(op in d for op in (">=", "<=", "~=", ">", "<"))
        ):
            errs.append(f"unpinned dependency: {d!r}")
            continue
        name, _, ver = d.partition("==")
        seen.add(name.strip().lower())
        if _PLACEHOLDER.search(ver) or not _VER.fullmatch(ver.strip()):
            errs.append(f"dependency {name.strip()!r} has no concrete pinned version: {ver!r}")
    missing_deps = required_deps - seen
    if missing_deps:
        errs.append(f"missing required dependencies: {sorted(missing_deps)}")
    if cfg.get("trainable_serving_relation_attested") is not True:
        errs.append("trainable<->serving relation not explicitly attested (must be true)")
    return errs


def validate_lineage(adapter_base: str, trainable_repo: str, trainable_commit: str) -> list[str]:
    """The adapter must have been trained against the declared trainable base."""
    errs = []
    if adapter_base != trainable_repo:
        errs.append(f"adapter base {adapter_base!r} != trainable_base_repo {trainable_repo!r}")
    if not _SHA.fullmatch(trainable_commit or ""):
        errs.append("trainable_base_commit is not a resolved commit")
    return errs
