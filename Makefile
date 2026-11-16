.PHONY: install test lint format check serve-smoke train-smoke bench
install:
	uv sync
test:
	uv run pytest -q
lint:
	uv run ruff check .
	uv run ruff format --check .
format:
	uv run ruff format .
	uv run ruff check --fix .
# Everything that can run on a plain dev machine, no GPU/Linux/Docker needed.
# This is what CI runs; see docs/EXECUTION_ENVIRONMENTS.md for what cannot.
check: lint test
serve-smoke:
	bash scripts/serve_smoke.sh
train-smoke:
	bash scripts/train_smoke.sh
bench:
	uv run python scripts/measure_throughput.py
