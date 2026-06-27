# ruff-legibility Agent Instructions

## Project

`ruff-legibility` is a Python CLI and library with a Rust parser backend built
through `maturin`. It emits Ruff-style `LEG###` diagnostics for readability and
reviewability rules.

## Git

Do not run `git add`, `git commit`, or `git push`. Leave staging and commits to
the user.

## Development

- Use `uv` for Python commands.
- Keep rule implementations low false-positive and narrowly scoped.
- Add positive and negative tests for rule changes.
- Update README rule tables/examples when rule codes, messages, or behavior
  changes.
- Update `CHANGELOG.md` for user-facing changes.
- Keep generated build artifacts out of changes.

## Validation

Run the narrowest useful check first, then broaden when behavior changed:

```sh
uv run ruff check .
uv run ruff-legibility check src tests
uv run pytest
uv build
```

For a full local check, run:

```sh
make check
```

## Shared Agent Skill

Use `.agents/skills/ruff-legibility/SKILL.md` as the shared Claude/Codex skill
when another agent should run the ruff-legibility feedback loop or maintain this
project. Do not duplicate the workflow in tool-specific rules.

Installed packages can copy the same skill into a local agent skill root with:

```sh
ruff-legibility install-skill
```
