"""Config loading: YAML on disk -> validated pydantic model, or a loud failure.

CLAUDE.md directive #6 ("fail loud") applies directly to config: a missing
file, invalid YAML, or a value that fails its model's validation must raise
here, never fall back to a silent default.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class ConfigError(RuntimeError):
    """A config file is missing, unparsable, or fails its schema."""


def load_yaml_config(path: str | Path, model: type[T]) -> T:
    """Parse `path` as YAML and validate it against `model`.

    Raises `ConfigError` (never returns a partial/defaulted object) if the
    file is missing, is not valid YAML, or does not match `model` exactly
    (models use `extra="forbid"` so a stale/typo'd key is also a failure).
    """
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"config file not found: {p}")

    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {p}: {exc}") from exc

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError(f"{p} must parse to a mapping, got {type(raw).__name__}")

    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"{p} failed validation against {model.__name__}:\n{exc}") from exc
