---
name: ruff-legibility
description: >
  Use when checking Python readability with ruff-legibility, fixing LEG
  diagnostics, maintaining this ruff-legibility repository, adding LEG rules, or
  guiding agents through a repeatable lint/test/build feedback loop.
---

# Ruff Legibility

## Purpose

Use `ruff-legibility` beside Ruff to find readability and reviewability issues
in Python code. Prefer small, behavior-preserving edits that make conditions,
computed values, collection processing, and control flow easier to review.

## Agent Compatibility

This is the single shared skill for Claude and Codex.

- Codex can invoke it as `$ruff-legibility` through the skill metadata.
- Claude should read this file directly when `.claude/rules/ruff-legibility.md`
  points here.
- Keep tool-specific rule files as small pointers. Do not fork this workflow
  into separate Claude and Codex copies.

## Package Install

The `ruff-legibility` package ships this skill, but does not install it
automatically. After installing the package, copy the skill explicitly:

```sh
ruff-legibility install-skill
```

For Codex-specific skill roots:

```sh
ruff-legibility install-skill --target codex
```

## Downstream Feedback Loop

1. Run Ruff first when it is available:

   ```sh
   ruff check .
   ```

2. Run ruff-legibility:

   ```sh
   ruff-legibility check .
   ```

3. Fix actionable `LEG###` diagnostics by preserving behavior and improving
   readability:

   - Hoist complex conditions into named booleans.
   - Prefer guard clauses and early returns over nested main paths.
   - Name intermediate computed values before returns and dict/list values.
   - Replace repeated scans with lookups.
   - Prefer comprehensions for simple collection transforms.

4. Re-run both commands until no actionable diagnostics remain.

If Ruff rejects `# noqa: LEG###`, add the external prefix:

```toml
[tool.ruff.lint]
external = ["LEG"]
```

## Repository Maintenance Loop

In this repository, use `uv` and the local package:

```sh
uv run ruff check .
uv run ruff-legibility check src tests
uv run pytest
uv build
```

For a full check:

```sh
make check
```

When changing rules:

1. Update the rule implementation in `src/ruff_legibility/rules.py`.
2. Add positive and negative tests in `tests/`.
3. Preserve `select`, `ignore`, per-file ignores, and `# noqa` behavior.
4. Update README rule tables and examples if public behavior changed.
5. Update `CHANGELOG.md` for user-facing changes.

## Review Guidance

- Do not install dependencies or fetch packages unless the user asked for it.
- Do not rewrite code just to satisfy a diagnostic when behavior would become
  less clear.
- Treat false positives as rule bugs and add regression tests before broadening
  detection.
- Keep generated build artifacts out of commits.
