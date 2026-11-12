"""Adapter state-dict comparison that survives DIFFERENT adapter names (defect #1).

Training may save weights under adapter name 'default'; reload may attach as
'smoke'. In-memory LoRA param names embed the active adapter name, e.g.:
    base_model.model....q_proj.lora_A.default.weight
    base_model.model....q_proj.lora_A.smoke.weight
A canonical key strips the adapter-name segment so the two line up. The key logic
is pure string manipulation (no torch), so it is unit-tested on CPU without the
30B model. Value comparison (torch) is separated out and used by the smoke script.

Production note: prefer peft.utils.get_peft_model_state_dict for a version-correct
canonical extraction; this canonicaliser is the tested fallback and the mapping
contract the comparison relies on.
"""

from __future__ import annotations

import re

# matches lora_A / lora_B / lora_embedding_A / lora_magnitude_vector then
# '.<adapter_name>.(weight|bias)' at the end, and drops the name segment.
_LORA = re.compile(
    r"(lora_(?:A|B|embedding_A|embedding_B|magnitude_vector))\.[^.]+\.(weight|bias)$"
)


def canonical_key(name: str) -> str:
    return _LORA.sub(r"\1.\2", name)


def canonicalise_keys(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        ck = canonical_key(k)
        if ck in out:
            raise ValueError(f"canonical key collision: {k!r} and another map to {ck!r}")
        out[ck] = v
    return out


def compare_state_dicts(saved: dict, reloaded: dict, *, atol: float, rtol: float):
    """Return (ok, detail). Requires matching canonical key SETS and SHAPES
    before comparing values; checks finiteness. torch imported lazily so this
    module stays importable (and its key logic testable) without torch."""
    import torch

    if not saved or not reloaded:
        return False, "empty adapter state dict (nothing to compare)"
    s = canonicalise_keys(saved)
    r = canonicalise_keys(reloaded)
    if set(s) != set(r):
        only_s = sorted(set(s) - set(r))[:3]
        only_r = sorted(set(r) - set(s))[:3]
        return False, f"key-set mismatch: only_saved={only_s} only_reloaded={only_r}"
    for k in s:
        if tuple(s[k].shape) != tuple(r[k].shape):
            return False, f"shape mismatch at {k}: {tuple(s[k].shape)} vs {tuple(r[k].shape)}"
        if not torch.isfinite(r[k]).all():
            return False, f"non-finite reloaded tensor at {k}"
        if not torch.allclose(s[k].float(), r[k].float(), atol=atol, rtol=rtol):
            return False, f"value mismatch at {k}"
    return True, f"{len(s)} adapter tensors match (atol={atol}, rtol={rtol})"
