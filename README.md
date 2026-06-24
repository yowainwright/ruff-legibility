# ruff-legibility

[![PyPI version](https://img.shields.io/pypi/v/ruff-legibility.svg)](https://pypi.org/project/ruff-legibility/)
[![CI](https://github.com/yowainwright/ruff-legibility/actions/workflows/ci.yml/badge.svg)](https://github.com/yowainwright/ruff-legibility/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/yowainwright/ruff-legibility/badge)](https://scorecard.dev/viewer/?uri=github.com/yowainwright/ruff-legibility)

`ruff-legibility` is a Ruff-adjacent Python linter for readability and reviewability rules inspired by `eslint-plugin-legibility`.

Ruff does not currently load third-party rule implementations from Python packages. This package therefore runs beside Ruff and emits Ruff-style diagnostics with `LEG###` codes.

```sh
ruff check .
ruff-legibility check .
```

To keep `# noqa: LEG001` comments valid when Ruff checks unused or unknown `noqa` codes, add `LEG` as an external prefix in Ruff:

```toml
[tool.ruff.lint]
external = ["LEG"]
```

## Install

```sh
pip install ruff-legibility
```

For local development:

```sh
uv sync --all-groups
make check
```

## Usage

```sh
ruff-legibility check .
ruff-legibility check src tests --output-format json
ruff-legibility check . --select LEG001,LEG002 --ignore LEG007
ruff-legibility check . --exit-zero
```

Default text output is intentionally close to Ruff:

```text
example.py:4:8: LEG002 If condition has 2 boolean operators (max 0). Hoist it into a named boolean.
```

## Configuration

Configuration can live in `pyproject.toml` under `[tool.ruff-legibility]`, or in `ruff-legibility.toml` / `.ruff-legibility.toml`.

```toml
[tool.ruff-legibility]
select = ["LEG"]
extend-select = []
ignore = ["LEG007"]
extend-ignore = []
exclude = [".venv", "build", "dist"]
max-expression-operators = 4
max-if-operators = 0
max-ternary-operators = 2
max-control-flow-depth = 3

[tool.ruff-legibility.per-file-ignores]
"tests/*" = ["LEG003"]
```

Standalone config files omit the `tool.ruff-legibility` wrapper:

```toml
select = ["LEG"]
ignore = ["LEG007"]
```

This repository includes a `ruff-legibility.toml` for its own source. The default package thresholds stay stricter than the project-local development config.

## Rules

| Code | Rule | Default |
| --- | --- | --- |
| `LEG001` | Limit readability operators inside a single expression. | on |
| `LEG002` | Prefer a named boolean before operator-heavy `if` / `while` conditions. | on |
| `LEG003` | Limit nested control-flow depth. | on |
| `LEG004` | Avoid complex ternary expressions. | on |
| `LEG005` | Flag likely quadratic patterns such as nested loops and repeated membership checks in loops. | on |
| `LEG006` | Avoid redundant boolean comparisons and boolean ternaries like `flag == True` or `True if flag else False`. | on |
| `LEG007` | Prefer positive condition names over names like `is_not_ready`. | on |
| `LEG008` | Avoid trivial wrapper functions that only forward parameters to another call. | on |
| `LEG009` | Avoid `else` branches after a branch that already exits. | on |
| `LEG010` | Prefer guard clauses over wrapping the main path in one large `if` block. | on |

## Pre-commit

```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-legibility
        name: ruff-legibility
        entry: ruff-legibility check
        language: system
        types: [python]
```

## Development

Common commands:

```sh
uv sync --all-groups
uv run ruff check .
uv run ruff-legibility check src tests
uv run pytest
uv build
```

Release builds should use:

```sh
uv build --no-sources
```

Publishing is configured for PyPI Trusted Publishing:

```sh
uv publish
```
