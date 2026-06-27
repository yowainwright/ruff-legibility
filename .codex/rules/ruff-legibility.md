# ruff-legibility Codex Rules

Use this file with `AGENTS.md` for repo-specific Codex behavior. For the
complete shared workflow, read `.agents/skills/ruff-legibility/SKILL.md`.

## Work Loop

1. Read the relevant source, tests, and README symbolic comments before editing.
2. Make focused changes only.
3. Run the most relevant validation command.
4. Fix actionable `LEG###`, Ruff, test, or build failures.
5. Repeat until the touched behavior is clean or the remaining failure is
   unrelated and documented.

Keep this file as a Codex pointer. Do not duplicate the shared skill workflow
here.

## Rule Changes

- Add or update tests in `tests/`.
- Keep diagnostics actionable.
- Preserve `select`, `ignore`, per-file ignores, and `# noqa` behavior.
- Update the README rule table and examples when public rule behavior changes.
- Update `CHANGELOG.md` for user-facing changes.

## Commands

```sh
uv run ruff check .
uv run ruff-legibility check src tests
uv run pytest
uv build
```
