from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from libs.common.config import ConfigError, load_yaml_config

# Six logging groups as explicit categories (brief §13)
LOG_GROUPS = ("training", "routing", "eval", "data_lineage", "verifier_health", "config_env")


def get_logger(service: str):
    return structlog.get_logger(service=service)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def now() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "LOG_GROUPS",
    "get_logger",
    "new_id",
    "now",
    "load_yaml_config",
    "ConfigError",
]
