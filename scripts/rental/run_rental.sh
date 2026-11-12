#!/usr/bin/env bash
# Thin wrapper: the phased lifecycle lives in rental.orchestrate (testable Python).
set -euo pipefail
: "${MODEL_PATH:?set MODEL_PATH to the verified serving snapshot}"
exec python -m rental.orchestrate
