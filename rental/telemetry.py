"""Memory telemetry that stays honest on GB10 unified memory.

On DGX Spark, `nvidia-smi --query-gpu=memory.used` reports `[N/A]`: CPU and GPU
share one LPDDR5x pool. The fallback is host `/proc/meminfo` (MemTotal -
MemAvailable), always labelled with its source so a host-memory reading is never
presented as a discrete-GPU reading. Standard library only.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

NVIDIA_SMI = "nvidia-smi memory.used"
HOST_MEMINFO = "host /proc/meminfo (unified memory)"


def host_used_memory_gb(meminfo_text: str) -> float | None:
    """MemTotal - MemAvailable in GiB. Reclaimable page cache counts as
    available, so a warm cache is not mistaken for a leak."""
    values = {}
    for line in meminfo_text.splitlines():
        key, _, rest = line.partition(":")
        if key in ("MemTotal", "MemAvailable") and rest.split():
            values[key] = int(rest.split()[0])
    if "MemTotal" not in values or "MemAvailable" not in values:
        return None
    return (values["MemTotal"] - values["MemAvailable"]) / (1024 * 1024)


def used_memory_gb() -> tuple[float | None, str]:
    """(GiB used, source label). nvidia-smi first; host meminfo when it is N/A."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        return float(out.split()[0]) / 1024, NVIDIA_SMI
    except Exception:
        pass
    try:
        value = host_used_memory_gb(Path("/proc/meminfo").read_text())
    except OSError:
        value = None
    return value, (HOST_MEMINFO if value is not None else "none")
