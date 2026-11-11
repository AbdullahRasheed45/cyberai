#!/usr/bin/env python3
"""CLI front door for `libs.common.gb10_serving.render_serve_command`.

This is the thin, I/O-only wrapper: it reads `configs/serving.yaml`
(override with `--config`), applies CLI overrides, and prints the result in
whichever shape the caller needs. All the actual logic (including the
multi-LoRA/FP8 refusal) lives in `libs/common/gb10_serving.py` and is unit
tested there — this script has none of its own to re-test.

Usage:
    uv run python scripts/gb10/render_serve_args.py --variant primary --format argv
    uv run python scripts/gb10/render_serve_args.py --variant dense_fallback --lora --format env
    uv run python scripts/gb10/render_serve_args.py --format json  # full ServeCommand
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libs.common import (  # noqa: E402
    ConfigError,
    UnverifiedLoraCombinationError,
    load_yaml_config,
    render_serve_command,
)
from libs.schemas import ServingConfig  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default=str(REPO_ROOT / "configs" / "serving.yaml"), help="path to serving.yaml"
    )
    parser.add_argument("--variant", choices=["primary", "dense_fallback"], default="primary")
    parser.add_argument(
        "--lora",
        action="store_true",
        help="request --enable-lora (refused for primary unless verified)",
    )
    parser.add_argument(
        "--format",
        choices=["argv", "env", "shell", "json", "meta"],
        default="argv",
        help=(
            "argv: one token per line. env: KEY=VALUE per line. shell: a single quoted "
            "command line. json: full ServeCommand. meta: HOST/PORT/SERVED_MODEL_NAME/MODEL/"
            "REVISION as KEY=VALUE lines, for shell callers that need one field without "
            "parsing JSON."
        ),
    )
    args = parser.parse_args()

    try:
        cfg = load_yaml_config(args.config, ServingConfig)
        cmd = render_serve_command(cfg, variant=args.variant, lora_enabled=args.lora)
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2
    except UnverifiedLoraCombinationError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 3

    if args.format == "argv":
        print("\n".join(cmd.argv))
    elif args.format == "env":
        for k, v in cmd.env.items():
            print(f"{k}={v}")
    elif args.format == "shell":
        import shlex

        env_prefix = " ".join(f"{k}={shlex.quote(v)}" for k, v in cmd.env.items())
        argv_str = " ".join(shlex.quote(a) for a in cmd.argv)
        print(f"{env_prefix} {argv_str}".strip())
    elif args.format == "meta":
        host = cmd.argv[cmd.argv.index("--host") + 1]
        port = cmd.argv[cmd.argv.index("--port") + 1]
        print(f"HOST={host}")
        print(f"PORT={port}")
        print(f"SERVED_MODEL_NAME={cmd.served_model_name}")
        print(f"MODEL={cmd.model}")
        print(f"REVISION={cmd.revision}")
    else:  # json
        print(cmd.model_dump_json(indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
