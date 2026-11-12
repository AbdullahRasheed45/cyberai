"""In-image accelerator probe (Astra #2, R15 defect #1): a REAL compilable source
run via argv (no shell interpolation), emitting a marker-delimited JSON line that
survives entrypoint banners. Parsed and version-compared per image.
"""

from __future__ import annotations

import json

MARKER = "__PROBE_JSON__"

# Real multiline source (actual newlines). compile(PROBE_SRC) must succeed, and
# executing it must print a MARKER line even when optional imports fail.
PROBE_SRC = """\
import json, importlib
d = {"versions": {}, "cuda": False, "bf16": False, "device": None}
for _m in ["torch", "vllm", "transformers", "unsloth", "trl", "peft", "bitsandbytes"]:
    try:
        _mod = importlib.import_module(_m)
        d["versions"][_m] = getattr(_mod, "__version__", "?")
    except Exception as _e:
        d["versions"][_m] = "IMPORT_FAIL:" + type(_e).__name__
try:
    import torch
    d["cuda"] = bool(torch.cuda.is_available())
    d["bf16"] = bool(d["cuda"] and torch.cuda.is_bf16_supported())
    d["device"] = torch.cuda.get_device_name(0) if d["cuda"] else None
except Exception:
    pass
print("__PROBE_JSON__" + json.dumps(d))
"""


def probe_argv(image: str) -> list[str]:
    """Exact Docker argv for the probe — passed as ONE arg, no shell interpolation."""
    return ["docker", "run", "--rm", "--gpus", "all", image, "python", "-c", PROBE_SRC]


def extract_probe(stdout: str) -> dict | None:
    for line in (stdout or "").splitlines():
        i = line.find(MARKER)
        if i != -1:
            try:
                return json.loads(line[i + len(MARKER) :])
            except Exception:
                return None
    return None


def compare_versions(found: dict, pins: dict, components: list[str]) -> list[str]:
    errs = []
    for comp in components:
        v = found.get(comp)
        if v is None:
            errs.append(f"{comp} not reported by probe")
        elif isinstance(v, str) and v.startswith("IMPORT_FAIL"):
            errs.append(f"{comp} failed to import in image ({v})")
        elif comp in pins and v != pins[comp]:
            errs.append(f"{comp} {v} != pinned {pins[comp]}")
    return errs
