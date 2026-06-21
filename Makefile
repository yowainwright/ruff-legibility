.PHONY: build check clean format lint test

check: lint test build

lint:
	uv run ruff check .
	uv run ruff-legibility check src tests

format:
	uv run ruff format .

test:
	uv run pytest

build:
	uv build

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +
