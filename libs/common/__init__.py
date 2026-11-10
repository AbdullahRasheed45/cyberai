from __future__ import annotations
import uuid
from datetime import datetime, timezone
import structlog

# Six logging groups as explicit categories (brief §13)
LOG_GROUPS = ("training", "routing", "eval", "data_lineage", "verifier_health", "config_env")

def get_logger(service: str):
    return structlog.get_logger(service=service)

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def now() -> datetime:
    return datetime.now(timezone.utc)
