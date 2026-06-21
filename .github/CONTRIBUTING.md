# Contributing to ruff-legibility

Thanks for taking the time to contribute.

## Development Setup

1. Fork and clone the repository.
2. Install `uv`.
3. Install dependencies:

```sh
uv sync --all-groups
```

## Development Workflow

Run the full local check before opening a pull request:

```sh
make check
```

The individual commands are:

```sh
uv run ruff check .
uv run ruff-legibility check src tests
uv run pytest
uv build
```

Format Python code with:

```sh
uv run ruff format .
```

## Rules

New rules should:

- Use a stable `LEG###` code.
- Include unit tests for positive and negative examples.
- Respect `select`, `ignore`, per-file ignores, and `# noqa`.
- Prefer low-false-positive checks over clever inference.
- Emit messages that explain what to do next.

## Pull Requests

Before opening a pull request:

- Run `make check`.
- Update `README.md` when behavior or CLI usage changes.
- Update `CHANGELOG.md` for user-facing changes.
- Keep rule changes narrowly scoped.

## Issues

Please include:

- `ruff-legibility --version`
- `uv --version`
- Python version
- Minimal Python input that reproduces the issue
- Expected and actual diagnostics
