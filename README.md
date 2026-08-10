# ruff-legibility

[![PyPI version](https://img.shields.io/pypi/v/ruff-legibility.svg)](https://pypi.org/project/ruff-legibility/)
[![CI](https://github.com/yowainwright/ruff-legibility/actions/workflows/ci.yml/badge.svg)](https://github.com/yowainwright/ruff-legibility/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/yowainwright/ruff-legibility/badge)](https://scorecard.dev/viewer/?uri=github.com/yowainwright/ruff-legibility)

`ruff-legibility` is a Ruff-adjacent Python linter for readability and reviewability rules inspired by `eslint-plugin-legibility`.

## Rules

Each rule has an inline dos / don'ts diff example in [Examples](#examples).

<!-- rule codes and descriptions from src/ruff_legibility/rules.py -->

| Code | Rule | Default |
| --- | --- | --- |
| [`LEG001`](#leg001-example-diff) | Limit readability operators inside a single expression. | on |
| [`LEG002`](#leg002-example-diff) | Prefer a named boolean before operator-heavy `if` / `while` conditions. | on |
| [`LEG003`](#leg003-example-diff) | Limit nested control-flow depth. | on |
| [`LEG004`](#leg004-example-diff) | Avoid complex ternary expressions. | on |
| [`LEG005`](#leg005-example-diff) | Flag likely quadratic patterns such as nested loops and repeated membership checks in loops. | on |
| [`LEG006`](#leg006-example-diff) | Avoid redundant boolean comparisons and boolean ternaries like `flag == True` or `True if flag else False`. | on |
| [`LEG007`](#leg007-example-diff) | Prefer positive condition names over names like `is_not_ready`. | on |
| [`LEG008`](#leg008-example-diff) | Avoid trivial wrapper functions that only forward parameters to another call. | on |
| [`LEG009`](#leg009-example-diff) | Avoid `else` branches after a branch that already exits. | on |
| [`LEG010`](#leg010-example-diff) | Prefer guard clauses over wrapping the main path in one large `if` block. | on |
| [`LEG011`](#leg011-example-diff) | Limit consecutive collection-style method chains. | on |
| [`LEG012`](#leg012-example-diff) | Prefer named values before returning computed expressions or building dict values. | on |
| [`LEG013`](#leg013-example-diff) | Avoid mutations and assignment expressions hidden inside expressions. | on |
| [`LEG014`](#leg014-example-diff) | Avoid standalone list mutation calls when an expression is clearer. | on |
| [`LEG015`](#leg015-example-diff) | Prefer explicit collection composition over starred literal unpacking. | on |
| [`LEG016`](#leg016-example-diff) | Require configured executable Python source files to start with a shebang. | on |
| [`LEG017`](#leg017-example-diff) | Prefer smoke-testing installed Python package entry points. | on |
| [`LEG018`](#leg018-example-diff) | Avoid repeated scans over the same collection in one scope. | on |
| [`LEG019`](#leg019-example-diff) | Avoid aliases that only rename another value for one use. | on |
| [`LEG020`](#leg020-example-diff) | Avoid lambdas that only forward their parameters to another callable. | on |
| [`LEG021`](#leg021-example-diff) | Prefer a flat comprehension over map followed by flattening. | on |
| [`LEG022`](#leg022-example-diff) | Avoid map/filter callbacks that keep every item unchanged. | on |
| [`LEG023`](#leg023-example-diff) | Avoid fallback expressions that only return `None` unchanged. | on |
| [`LEG024`](#leg024-example-diff) | Prefer set or dict lookups over long equality-or chains. | on |
| [`LEG025`](#leg025-example-diff) | Require files in named subdirectories to match the directory name. | on |
| [`LEG026`](#leg026-example-diff) | Avoid filenames that mix casing conventions. | on |
| [`LEG027`](#leg027-example-diff) | Avoid comprehensions that keep every item unchanged. | on |
| [`LEG028`](#leg028-example-diff) | Prefer comprehensions over map/filter calls with lambdas. | on |
| [`LEG029`](#leg029-example-diff) | Prefer comprehensions over simple list-building append loops. | on |
| [`LEG030`](#leg030-example-diff) | Avoid filtering the same collection with comprehensions multiple times in one scope. | on |
| [`LEG031`](#leg031-example-diff) | Avoid deep subscript chains without named intermediate values. | on |
| [`LEG032`](#leg032-example-diff) | Prefer named context when wrapping or logging broad exceptions. | on |
| [`LEG033`](#leg033-example-diff) | Avoid positive boolean names assigned from inverted expressions. | on |
| [`LEG034`](#leg034-example-diffs) | Reject unmatched comments and unowned comment stacking within functions. | on |

## Examples

Removed lines are don'ts. Added lines are dos.

<!-- do/don't diff examples for every LEG rule documented in this README -->

---

### `LEG001 max-expression-operators`

#### LEG001 example diff

```diff
- return user.is_active and user.score > 10 and (user.role == "admin" or user.role == "owner")
+ is_admin = user.role == "admin"
+ is_owner = user.role == "owner"
+ has_privileged_role = is_admin or is_owner
+ return user.is_active and user.score > 10 and has_privileged_role
```

---

### `LEG002 hoist-if-operators`

#### LEG002 example diff

```diff
- if user and user.is_active and not user.is_locked:
-     send_invite(user)
+ can_invite_user = user and user.is_active and not user.is_locked
+ if can_invite_user:
+     send_invite(user)
```

---

### `LEG003 max-control-flow-depth`

#### LEG003 example diff

```diff
- if user:
-     for invite in invites:
-         if invite.pending:
-             while invite.retries < 3:
-                 send_invite(invite)
+ if not user:
+     return
+ pending_invites = [invite for invite in invites if invite.pending]
+ for invite in pending_invites:
+     retry_invite(invite)
```

---

### `LEG004 no-complex-ternary`

#### LEG004 example diff

```diff
- label = "owner" if user.is_owner else "admin" if user.is_admin else "member"
+ if user.is_owner:
+     label = "owner"
+ elif user.is_admin:
+     label = "admin"
+ else:
+     label = "member"
```

---

### `LEG005 no-quadratic-patterns`

#### LEG005 example diff

```diff
- for user in users:
-     for owner in owners:
-         if user.id == owner.user_id:
-             assign_owner(user, owner)
+ owners_by_user_id = {owner.user_id: owner for owner in owners}
+ for user in users:
+     owner = owners_by_user_id.get(user.id)
+     if owner is not None:
+         assign_owner(user, owner)
```

---

### `LEG006 no-redundant-boolean-logic`

#### LEG006 example diff

```diff
- return True if flag == True else False
+ return flag
```

---

### `LEG007 prefer-positive-condition-names`

#### LEG007 example diff

```diff
- is_not_ready = status != "ready"
- if is_not_ready:
+ is_ready = status == "ready"
+ if not is_ready:
      return
```

---

### `LEG008 no-trivial-wrapper-functions`

#### LEG008 example diff

```diff
- def normalize(value):
-     return clean(value)
- result = normalize(value)
+ result = clean(value)
```

---

### `LEG009 prefer-early-return`

#### LEG009 example diff

```diff
- if not user:
-     return None
- else:
-     return user.email
+ if not user:
+     return None
+ return user.email
```

---

### `LEG010 prefer-guard-clauses`

#### LEG010 example diff

```diff
- if user:
-     prepare(user)
-     send_invite(user)
+ if not user:
+     return
+ prepare(user)
+ send_invite(user)
```

---

### `LEG011 max-array-chain-depth`

#### LEG011 example diff

```diff
- users = query.filter(active=True).order_by("name").limit(10)
+ active_users = query.filter(active=True)
+ sorted_users = active_users.order_by("name")
+ users = sorted_users.limit(10)
```

---

### `LEG012 no-computed-values`

#### LEG012 example diff

```diff
- return total + tax - discount
+ subtotal = total + tax
+ return subtotal - discount
```

---

### `LEG013 no-hidden-side-effects`

#### LEG013 example diff

```diff
- return cache.setdefault(key, build_value())
+ if key not in cache:
+     cache[key] = build_value()
+ return cache[key]
```

---

### `LEG014 no-standalone-array-mutations`

#### LEG014 example diff

```diff
- items.append(item)
- return items
+ return items + [item]
```

---

### `LEG015 prefer-concat-object-assign`

#### LEG015 example diff

```diff
- payload = {**base_payload, "id": user_id}
+ payload = base_payload | {"id": user_id}
```

---

### `LEG016 require-executable-shebang`

#### LEG016 example diff

```diff
- # scripts/report.py
- print("ok")
+ #!/usr/bin/env python3
+ print("ok")
```

---

### `LEG017 no-direct-python-bin-smoke`

#### LEG017 example diff

```diff
- subprocess.run(["python", "src/example/cli.py", "--help"], check=True)
+ subprocess.run(["example", "--help"], check=True)
```

---

### `LEG018 no-repeated-collection-search`

#### LEG018 example diff

```diff
- if user_id in ids and owner_id in ids:
-     return True
+ id_lookup = set(ids)
+ required_ids = {user_id, owner_id}
+ return required_ids.issubset(id_lookup)
```

---

### `LEG019 no-single-use-renaming-alias`

#### LEG019 example diff

```diff
- current_user = request.user
- return current_user.email
+ return request.user.email
```

---

### `LEG020 no-unnecessary-lambda`

#### LEG020 example diff

```diff
- users = sorted(users, key=lambda user: normalize(user))
+ users = sorted(users, key=normalize)
```

---

### `LEG021 prefer-flat-comprehension`

#### LEG021 example diff

```diff
- values = list(chain.from_iterable(map(expand, items)))
+ values = [value for item in items for value in expand(item)]
```

---

### `LEG022 no-identity-array-callback`

#### LEG022 example diff

```diff
- names = list(map(lambda name: name, names))
+ names = list(names)
```

---

### `LEG023 no-redundant-none-fallback`

#### LEG023 example diff

```diff
- return value if value is not None else None
+ return value
```

---

### `LEG024 prefer-object-lookup`

#### LEG024 example diff

```diff
- if status == "new" or status == "open" or status == "pending":
-     queue_item(item)
+ if status in {"new", "open", "pending"}:
+     queue_item(item)
```

---

### `LEG025 require-filename-matches-dirname`

#### LEG025 example diff

```diff
- src/billing/customer/profile.py
+ src/billing/customer/customer.py
```

---

### `LEG026 no-mixed-filename-casing`

#### LEG026 example diff

```diff
- user_Profile.py
+ user_profile.py
```

---

### `LEG027 no-identity-comprehension`

#### LEG027 example diff

```diff
- copied = [item for item in items]
+ copied = list(items)
```

---

### `LEG028 prefer-comprehension-over-map-filter`

#### LEG028 example diff

```diff
- names = list(map(lambda user: user.name, users))
+ names = [user.name for user in users]
```

---

### `LEG029 no-loop-append-comprehension`

#### LEG029 example diff

```diff
- names = []
- for user in users:
-     names.append(user.name)
+ names = [user.name for user in users]
```

---

### `LEG030 no-repeated-comprehension-filter`

#### LEG030 example diff

```diff
- active_users = [user for user in users if user.active]
- admin_users = [user for user in users if user.is_admin]
+ filtered_users = [user for user in users if user.active or user.is_admin]
+ active_users = [user for user in filtered_users if user.active]
+ admin_users = [user for user in filtered_users if user.is_admin]
```

---

### `LEG031 no-deep-subscript-chain`

#### LEG031 example diff

```diff
- return payload["user"]["profile"]["email"]
+ user = payload["user"]
+ profile = user["profile"]
+ return profile["email"]
```

---

### `LEG032 prefer-named-exception-context`

#### LEG032 example diff

```diff
- except Exception as error:
-     raise RuntimeError(error)
+ except Exception as error:
+     message = "Failed to load user profile"
+     raise RuntimeError(message) from error
```

---

### `LEG033 no-boolean-parameter-name-drift`

#### LEG033 example diff

```diff
- is_ready = status != "ready"
+ is_ready = status == "ready"
```

---

### `LEG034 no-unmatched-comments`

`LEG034` checks standalone and trailing inline `#` comments.

#### LEG034 example diffs

Fails with two diagnostics:

```python
# Explain the assignment.
value = 1  # Keep this value stable.
```

Fix:

```diff
- # Convert cents to dollars.
- total_dollars = cents / 100  # Store the converted total.
+ total_dollars = cents / 100
```

#### LEG034 setup

By default, `LEG034` allows common tool directives: `noqa`, `type:`,
`ruff: noqa`, `fmt:`, `isort:`, and `pragma: no cover`. These directives do
not count toward the one-comment-per-function limit. Setting
`comment-matchers` replaces those defaults, so include them when adding
project-specific patterns:

```toml
[tool.ruff-legibility]
comment-matchers = [
  '\b(ENG|OPS)-\d+\b',
  '^\s*(noqa\b|type:\s*|ruff:\s*noqa\b)',
  '^\s*(fmt|isort):\s*(on|off|skip)\b',
  '^\s*pragma:\s*no cover\b',
]
comment-prefix-identifiers = ["HUMAN", "LEGAL", "SECURITY"]
comment-suffix-identifiers = ["@owned"]
```

| Setting | Allows the comment | Exempt from one-comment-per-function limit |
| --- | --- | --- |
| `comment-matchers` | Regex matches | only default tool directives |
| `comment-prefix-identifiers` | Block starts with identifier | yes |
| `comment-suffix-identifiers` | Block ends with identifier | yes |

Matching is case-insensitive and ignores the leading `#`.
Adjacent standalone comments form one block and produce at most one diagnostic
spanning the block. A `# noqa: LEG034` on the first line suppresses that block.

#### Regex-matched comments

Passes with the setup above:

```python
# ENG-481: Provider retries must remain ordered.
for retry in retries:
    send(retry)

timeout = 30  # OPS-92: Keep worker and provider timeouts aligned.
```

Only one regex-matched physical comment is allowed per function. This reports
the second comment:

```python
def load_value():
    value = load()  # ENG-481: Load the configured value once.
    # ENG-482: Preserve the configured fallback.
    return value or fallback()
```

Fix by keeping one useful comment:

```diff
 def load_value():
-    value = load()  # ENG-481: Load the configured value once.
-    # ENG-482: Preserve the configured fallback.
+    # ENG-481: Load once and use the configured fallback when empty.
+    value = load()
     return value or fallback()
```

The same limit applies immediately above and below a function. The second line
in each block reports:

```python
# ENG-481: First leading comment.
# ENG-482: Second leading comment.
def first():
    return 1


def second():
    return 2
# ENG-483: First trailing comment.
# ENG-484: Second trailing comment.
```

An indented comment after the final statement still belongs to the function.
This reports the second comment:

```python
def load_value():
    # ENG-481: Load the configured value.
    value = load()
    return value
    # ENG-482: Preserve the provider contract.
```

Nested functions have separate counts:

```python
def outer():
    # ENG-481: Preserve the outer contract.
    value = load()

    def inner():
        # ENG-482: Preserve the inner contract.
        return value

    return inner()
```

A comment immediately below a nested function belongs to that nested function.
This reports the second comment:

```python
def outer():
    def inner():
        # ENG-481: Preserve the inner contract.
        return 1
    # ENG-482: Keep this adjacent to the inner function.
    return inner()
```

#### Human-owned comment blocks

Prefix- and suffix-owned blocks pass and do not count toward the function
limit:

```python
def load_value():
    # HUMAN: The provider requires ordered retries.
    # Reordering these calls breaks failover.
    retry()

    # The operator selects this timeout.
    # The worker must use the same value. @owned
    return timeout
```

Identifiers require a boundary:

```diff
- # HUMANIZED: This is not owned.
+ # HUMAN: This block is owned.

- value = 1  # Preserve this not@owned
+ value = 1  # Preserve this. @owned
```

#### Ignored Python metadata

These pass without comment configuration:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module documentation."""


def load():
    """Load the value."""
```

Encoding cookies must occupy a comment-only line:

```diff
- value = 1  # coding: utf-8
+ # coding: utf-8
+ value = 1
```

## Recipes

<!-- recipe commands exercised by tests/e2es/Dockerfile.*, scripts/test_e2es.sh, src/ruff_legibility/cli.py, and pyproject.toml -->

Use the same committed [comment ownership configuration](#leg034-setup) in every
context. Change only the scope and when a diagnostic blocks work.

| Context | Why | How |
| --- | --- | --- |
| Agent | Agents can produce redundant comments at scale. | Block every edited Python file. |
| Human | A hard failure on every save interrupts editing. | Warn while editing; block before commit. |
| CI | Local checks can be skipped or narrowly scoped. | Block the whole repository. |

Run the tested Docker examples with `make test-e2e`.

### Agent: block edited files

Why: an agent should remove narration it introduced, not disguise it with an
ownership marker. Existing human-owned comments remain untouched.

How: install the shared skill once, give the agent the policy, and make its
edited-file check blocking.

```sh
ruff-legibility install-skill --target auto
```

```text
Use $ruff-legibility on every Python file you edit. Remove unmatched comments
you add. Do not add ownership markers, matchers, or noqa suppressions.
```

```sh
ruff check src/package/changed.py
ruff-legibility check src/package/changed.py
```

[Tested agent example](tests/e2es/Dockerfile.agent)

### Human: warn while editing, block before commit

Why: advisory output keeps the policy visible without breaking the edit loop.
The blocking check keeps unmatched comments out of commits.

How: use `--exit-zero` while editing, then remove it for the changed-file gate.

```sh
ruff-legibility check src/package --select LEG034 --exit-zero
ruff-legibility check src/package/changed.py
```

`pre-commit` can install the pinned package and pass staged Python filenames to
the blocking command:

```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-legibility
        name: ruff-legibility
        entry: ruff-legibility check
        language: python
        additional_dependencies:
          - ruff-legibility==0.4.0
        types: [python]
```

[Tested human example](tests/e2es/Dockerfile.human)

### CI: block the repository

Why: CI is the backstop for skipped hooks, partial local checks, and files
changed outside the normal edit loop.

How: install from the lockfile, run both linters across the repository, and use
GitHub annotations for review visibility.

```yaml
- run: uv sync --locked --all-groups
- run: uv run --locked ruff check .
- run: uv run --locked ruff-legibility check . --output-format github
```

[Tested CI example](tests/e2es/Dockerfile.ci)

### Existing codebase: warn, fix, then block

Why: a new gate should not stop unrelated work because of an existing comment
baseline.

How: inventory `LEG034` without blocking, tune the ownership configuration,
fix the baseline, then remove `--exit-zero`.

```sh
ruff-legibility check . --select LEG034 --exit-zero
ruff-legibility check . --select LEG034
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

Run it beside Ruff:

```sh
ruff check .
ruff-legibility check .
```

```sh
ruff-legibility check src tests --output-format json
ruff-legibility check . --select LEG001,LEG002 --ignore LEG007
ruff-legibility check . --exit-zero
```

## Agent Skill

<!-- agent skill installer config from src/ruff_legibility/agent_skills; generated files from scripts/agent/templates/ruff-legibility -->

The package includes a reusable Claude/Codex skill, but it is never installed
automatically. Install it explicitly when you want local agents to use the
`ruff-legibility` loop:

```sh
ruff-legibility install-skill
ruff-legibility install-skill --target auto
ruff-legibility install-skill --target codex
ruff-legibility install-skill --path ~/.agents/skills --force
```

Default installs copy the skill to `~/.agents/skills/ruff-legibility`. Codex
target installs copy it to `$CODEX_HOME/skills/ruff-legibility`, or
`~/.codex/skills/ruff-legibility` when `CODEX_HOME` is not set.
Auto target detection uses the packaged static target registry, prefers a
configured target such as `CODEX_HOME`, then falls back to an existing known
skill root, then `~/.agents/skills`.
Use `--path` for any other agent skill root instead of adding vendor-specific
folders to this repository.

After installing the skill, use it in an agent prompt:

```text
Use $ruff-legibility to check Python readability and iterate on LEG diagnostics.
```

Generate tracked package and shared-skill files:

```sh
make build-agent
```

Generate ignored local rule pointers:

```sh
uv run python -m scripts.agent.build --target codex
uv run python -m scripts.agent.build --target claude
```

Check generated files without writing:

```sh
make check-agent
```

## Configuration

Keep `# noqa: LEG001` valid when Ruff checks unknown `noqa` codes:

```toml
[tool.ruff.lint]
external = ["LEG"]
```

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
max-computed-value-operators = 1
max-control-flow-depth = 3
max-array-chain-depth = 2
min-object-lookup-chain-length = 3
min-dirname-match-depth = 3
comment-matchers = [
  '^\s*(noqa\b|type:\s*|ruff:\s*noqa\b)',
  '^\s*(fmt|isort):\s*(on|off|skip)\b',
  '^\s*pragma:\s*no cover\b',
]
comment-prefix-identifiers = []
comment-suffix-identifiers = []

[tool.ruff-legibility.per-file-ignores]
"tests/*" = ["LEG003"]
```

Standalone config files omit the `tool.ruff-legibility` wrapper:

```toml
select = ["LEG"]
ignore = ["LEG007"]
```

This repository includes a `ruff-legibility.toml` for its own source. The default package thresholds stay stricter than the project-local development config.

## Development

Common commands:

```sh
uv sync --all-groups
uv run ruff check .
uv run ruff-legibility check src tests scripts
uv run pytest
uv build
```

Repository scripts:

```sh
./scripts/setup.sh
./scripts/test_setup.sh
uv run python -m scripts.agent.build --target package,agents
```

Local release artifact checks should use:

```sh
uv build --no-sources
```

Tagged releases are published by GitHub Actions. The workflow builds an sdist
and Python 3.11+ `abi3` wheels for Linux x86-64, macOS x86-64 and arm64, and
Windows x86-64. Each wheel installs without building from source.

Publishing is configured for PyPI Trusted Publishing:

```sh
uv publish
```
