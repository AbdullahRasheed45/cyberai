.PHONY: install test lint serve-smoke train-smoke bench
install:
	uv venv && uv pip install -e .
test:
	uv run pytest -q
lint:
	uv run python -m py_compile libs/schemas/__init__.py libs/common/__init__.py
serve-smoke:
	bash scripts/serve_smoke.sh
train-smoke:
	bash scripts/train_smoke.sh
bench:
	uv run python scripts/measure_throughput.py
