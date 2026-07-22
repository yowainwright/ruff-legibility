.PHONY: build build-agent check check-agent clean format lint
.PHONY: test test-e2e test-python test-scripts

check: check-agent lint test build

check-agent:
	uv run python -m scripts.agent.build --target package,agents --check

lint:
	uv run ruff check .
	uv run ruff-legibility check src tests scripts

format:
	uv run ruff format .

test: test-python test-scripts

test-python:
	uv run pytest

test-scripts:
	./scripts/test_setup.sh

test-e2e:
	./scripts/test_e2es.sh

build: build-agent
	uv build

build-agent:
	uv run python -m scripts.agent.build --target package,agents

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +
