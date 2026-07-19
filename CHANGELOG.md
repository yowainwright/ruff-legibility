# Changelog

All notable user-facing changes to `ruff-legibility` should be recorded here.

## Unreleased

- Add `LEG034 no-unmatched-comments` with configurable comment matchers,
  ownership identifiers, one unowned comment per function, adjacent stack
  detection, per-token standalone and inline diagnostics, Python comment-block
  handling, and metadata exclusions.
- Document comment ownership in the packaged agent skill.
- Add agent, human, pre-commit, CI, and gradual-adoption recipes.
- Check every configured comment ownership identifier when candidates overlap.
- Fix native `LEG005` parity for membership conditions and nested comprehensions.

## 0.3.1

- Build Python 3.11+ `abi3` manylinux release wheels so installs do not fall
  back to source builds on supported CPython versions.

## 0.3.0

- Add repository guidance for Claude and Codex agents.
- Add a reusable `ruff-legibility` skill for Claude and Codex agent loops.
- Ship the shared skill in the package with an explicit install command.
- Add static skill target configuration with explicit auto-detection support.
- Refresh GitHub support metadata for the 0.3.x release line.

## 0.2.0

- Add the native Rust parser backend.
- Expand the rule set through `LEG033`.
- Add PyPI release workflow support.

## 0.1.0

- Initial public release.
