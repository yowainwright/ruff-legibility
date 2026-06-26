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
max-computed-value-operators = 1
max-control-flow-depth = 3
max-array-chain-depth = 2
min-object-lookup-chain-length = 3
min-dirname-match-depth = 3

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

Each rule has an inline dos / don'ts diff example in [Examples](#examples).

<!-- rule codes and descriptions from src/ruff_legibility/rules.py -->

| Code | Rule | Default |
| --- | --- | --- |
| [`LEG001`](#leg001-max-expression-operators) | Limit readability operators inside a single expression. | on |
| [`LEG002`](#leg002-hoist-if-operators) | Prefer a named boolean before operator-heavy `if` / `while` conditions. | on |
| [`LEG003`](#leg003-max-control-flow-depth) | Limit nested control-flow depth. | on |
| [`LEG004`](#leg004-no-complex-ternary) | Avoid complex ternary expressions. | on |
| [`LEG005`](#leg005-no-quadratic-patterns) | Flag likely quadratic patterns such as nested loops and repeated membership checks in loops. | on |
| [`LEG006`](#leg006-no-redundant-boolean-logic) | Avoid redundant boolean comparisons and boolean ternaries like `flag == True` or `True if flag else False`. | on |
| [`LEG007`](#leg007-prefer-positive-condition-names) | Prefer positive condition names over names like `is_not_ready`. | on |
| [`LEG008`](#leg008-no-trivial-wrapper-functions) | Avoid trivial wrapper functions that only forward parameters to another call. | on |
| [`LEG009`](#leg009-prefer-early-return) | Avoid `else` branches after a branch that already exits. | on |
| [`LEG010`](#leg010-prefer-guard-clauses) | Prefer guard clauses over wrapping the main path in one large `if` block. | on |
| [`LEG011`](#leg011-max-array-chain-depth) | Limit consecutive collection-style method chains. | on |
| [`LEG012`](#leg012-no-computed-values) | Prefer named values before returning computed expressions or building dict values. | on |
| [`LEG013`](#leg013-no-hidden-side-effects) | Avoid mutations and assignment expressions hidden inside expressions. | on |
| [`LEG014`](#leg014-no-standalone-array-mutations) | Avoid standalone list mutation calls when an expression is clearer. | on |
| [`LEG015`](#leg015-prefer-concat-object-assign) | Prefer explicit collection composition over starred literal unpacking. | on |
| [`LEG016`](#leg016-require-executable-shebang) | Require configured executable Python source files to start with a shebang. | on |
| [`LEG017`](#leg017-no-direct-python-bin-smoke) | Prefer smoke-testing installed Python package entry points. | on |
| [`LEG018`](#leg018-no-repeated-collection-search) | Avoid repeated scans over the same collection in one scope. | on |
| [`LEG019`](#leg019-no-single-use-renaming-alias) | Avoid aliases that only rename another value for one use. | on |
| [`LEG020`](#leg020-no-unnecessary-lambda) | Avoid lambdas that only forward their parameters to another callable. | on |
| [`LEG021`](#leg021-prefer-flat-comprehension) | Prefer a flat comprehension over map followed by flattening. | on |
| [`LEG022`](#leg022-no-identity-array-callback) | Avoid map/filter callbacks that keep every item unchanged. | on |
| [`LEG023`](#leg023-no-redundant-none-fallback) | Avoid fallback expressions that only return `None` unchanged. | on |
| [`LEG024`](#leg024-prefer-object-lookup) | Prefer set or dict lookups over long equality-or chains. | on |
| [`LEG025`](#leg025-require-filename-matches-dirname) | Require files in named subdirectories to match the directory name. | on |
| [`LEG026`](#leg026-no-mixed-filename-casing) | Avoid filenames that mix casing conventions. | on |
| [`LEG027`](#leg027-no-identity-comprehension) | Avoid comprehensions that keep every item unchanged. | on |
| [`LEG028`](#leg028-prefer-comprehension-over-map-filter) | Prefer comprehensions over map/filter calls with lambdas. | on |
| [`LEG029`](#leg029-no-loop-append-comprehension) | Prefer comprehensions over simple list-building append loops. | on |
| [`LEG030`](#leg030-no-repeated-comprehension-filter) | Avoid filtering the same collection with comprehensions multiple times in one scope. | on |
| [`LEG031`](#leg031-no-deep-subscript-chain) | Avoid deep subscript chains without named intermediate values. | on |
| [`LEG032`](#leg032-prefer-named-exception-context) | Prefer named context when wrapping or logging broad exceptions. | on |
| [`LEG033`](#leg033-no-boolean-parameter-name-drift) | Avoid positive boolean names assigned from inverted expressions. | on |

## Examples

Removed lines are don'ts. Added lines are dos.

<!-- do/don't diff examples for every LEG rule documented in this README -->

---

### `LEG001 max-expression-operators`

#### do / don't

```diff
- return user.is_active and user.score > 10 and (user.role == "admin" or user.role == "owner")
+ is_admin = user.role == "admin"
+ is_owner = user.role == "owner"
+ has_privileged_role = is_admin or is_owner
+ return user.is_active and user.score > 10 and has_privileged_role
```

---

### `LEG002 hoist-if-operators`

#### do / don't

```diff
- if user and user.is_active and not user.is_locked:
-     send_invite(user)
+ can_invite_user = user and user.is_active and not user.is_locked
+ if can_invite_user:
+     send_invite(user)
```

---

### `LEG003 max-control-flow-depth`

#### do / don't

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

#### do / don't

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

#### do / don't

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

#### do / don't

```diff
- return True if flag == True else False
+ return flag
```

---

### `LEG007 prefer-positive-condition-names`

#### do / don't

```diff
- is_not_ready = status != "ready"
- if is_not_ready:
+ is_ready = status == "ready"
+ if not is_ready:
      return
```

---

### `LEG008 no-trivial-wrapper-functions`

#### do / don't

```diff
- def normalize(value):
-     return clean(value)
- result = normalize(value)
+ result = clean(value)
```

---

### `LEG009 prefer-early-return`

#### do / don't

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

#### do / don't

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

#### do / don't

```diff
- users = query.filter(active=True).order_by("name").limit(10)
+ active_users = query.filter(active=True)
+ sorted_users = active_users.order_by("name")
+ users = sorted_users.limit(10)
```

---

### `LEG012 no-computed-values`

#### do / don't

```diff
- return total + tax - discount
+ subtotal = total + tax
+ return subtotal - discount
```

---

### `LEG013 no-hidden-side-effects`

#### do / don't

```diff
- return cache.setdefault(key, build_value())
+ if key not in cache:
+     cache[key] = build_value()
+ return cache[key]
```

---

### `LEG014 no-standalone-array-mutations`

#### do / don't

```diff
- items.append(item)
- return items
+ return items + [item]
```

---

### `LEG015 prefer-concat-object-assign`

#### do / don't

```diff
- payload = {**base_payload, "id": user_id}
+ payload = base_payload | {"id": user_id}
```

---

### `LEG016 require-executable-shebang`

#### do / don't

```diff
- # scripts/report.py
- print("ok")
+ #!/usr/bin/env python3
+ print("ok")
```

---

### `LEG017 no-direct-python-bin-smoke`

#### do / don't

```diff
- subprocess.run(["python", "src/example/cli.py", "--help"], check=True)
+ subprocess.run(["example", "--help"], check=True)
```

---

### `LEG018 no-repeated-collection-search`

#### do / don't

```diff
- if user_id in ids and owner_id in ids:
-     return True
+ id_lookup = set(ids)
+ required_ids = {user_id, owner_id}
+ return required_ids.issubset(id_lookup)
```

---

### `LEG019 no-single-use-renaming-alias`

#### do / don't

```diff
- current_user = request.user
- return current_user.email
+ return request.user.email
```

---

### `LEG020 no-unnecessary-lambda`

#### do / don't

```diff
- users = sorted(users, key=lambda user: normalize(user))
+ users = sorted(users, key=normalize)
```

---

### `LEG021 prefer-flat-comprehension`

#### do / don't

```diff
- values = list(chain.from_iterable(map(expand, items)))
+ values = [value for item in items for value in expand(item)]
```

---

### `LEG022 no-identity-array-callback`

#### do / don't

```diff
- names = list(map(lambda name: name, names))
+ names = list(names)
```

---

### `LEG023 no-redundant-none-fallback`

#### do / don't

```diff
- return value if value is not None else None
+ return value
```

---

### `LEG024 prefer-object-lookup`

#### do / don't

```diff
- if status == "new" or status == "open" or status == "pending":
-     queue_item(item)
+ if status in {"new", "open", "pending"}:
+     queue_item(item)
```

---

### `LEG025 require-filename-matches-dirname`

#### do / don't

```diff
- src/billing/customer/profile.py
+ src/billing/customer/customer.py
```

---

### `LEG026 no-mixed-filename-casing`

#### do / don't

```diff
- user_Profile.py
+ user_profile.py
```

---

### `LEG027 no-identity-comprehension`

#### do / don't

```diff
- copied = [item for item in items]
+ copied = list(items)
```

---

### `LEG028 prefer-comprehension-over-map-filter`

#### do / don't

```diff
- names = list(map(lambda user: user.name, users))
+ names = [user.name for user in users]
```

---

### `LEG029 no-loop-append-comprehension`

#### do / don't

```diff
- names = []
- for user in users:
-     names.append(user.name)
+ names = [user.name for user in users]
```

---

### `LEG030 no-repeated-comprehension-filter`

#### do / don't

```diff
- active_users = [user for user in users if user.active]
- admin_users = [user for user in users if user.is_admin]
+ filtered_users = [user for user in users if user.active or user.is_admin]
+ active_users = [user for user in filtered_users if user.active]
+ admin_users = [user for user in filtered_users if user.is_admin]
```

---

### `LEG031 no-deep-subscript-chain`

#### do / don't

```diff
- return payload["user"]["profile"]["email"]
+ user = payload["user"]
+ profile = user["profile"]
+ return profile["email"]
```

---

### `LEG032 prefer-named-exception-context`

#### do / don't

```diff
- except Exception as error:
-     raise RuntimeError(error)
+ except Exception as error:
+     message = "Failed to load user profile"
+     raise RuntimeError(message) from error
```

---

### `LEG033 no-boolean-parameter-name-drift`

#### do / don't

```diff
- is_ready = status != "ready"
+ is_ready = status == "ready"
```

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
