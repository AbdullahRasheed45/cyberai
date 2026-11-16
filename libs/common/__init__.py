from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from libs.common.benchmark_domain import (
    build_sweep_plan,
    enforce_budget,
    estimate_requests_for_plan,
    percentile_stats,
    recommend_configuration,
    summarize_point,
    synthetic_prompt,
)
from libs.common.benchmark_report import render_markdown
from libs.common.config import ConfigError, load_yaml_config
from libs.common.gb10_serving import (
    ServeCommand,
    UnverifiedLoraCombinationError,
    render_serve_command,
)

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
    "render_serve_command",
    "ServeCommand",
    "UnverifiedLoraCombinationError",
    "synthetic_prompt",
    "build_sweep_plan",
    "estimate_requests_for_plan",
    "enforce_budget",
    "percentile_stats",
    "summarize_point",
    "recommend_configuration",
    "render_markdown",
]
