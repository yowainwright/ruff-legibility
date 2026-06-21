from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .rules import DEFAULT_SELECT, RULES

DEFAULT_EXCLUDE = (
    ".bzr",
    ".direnv",
    ".eggs",
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pants.d",
    ".pytype",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pypackages__",
    "_build",
    "build",
    "dist",
    "node_modules",
    "site-packages",
    "venv",
)


@dataclass(frozen=True)
class Settings:
    select: tuple[str, ...] = DEFAULT_SELECT
    ignore: tuple[str, ...] = ()
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    per_file_ignores: dict[str, tuple[str, ...]] = field(default_factory=dict)
    max_expression_operators: int = 4
    max_if_operators: int = 0
    max_ternary_operators: int = 2
    max_control_flow_depth: int = 3

    def enabled(self, code: str) -> bool:
        return selector_matches(code, self.select) and not selector_matches(code, self.ignore)

    def ignored_for_path(self, code: str, path: Path) -> bool:
        path_text = path.as_posix()
        for pattern, selectors in self.per_file_ignores.items():
            if fnmatch.fnmatch(path_text, pattern) and selector_matches(code, selectors):
                return True
        return False


def selector_matches(code: str, selectors: tuple[str, ...] | list[str] | set[str]) -> bool:
    return any(code.startswith(selector) for selector in selectors)


def parse_selectors(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None

    selectors = tuple(part.strip().upper() for part in value.split(",") if part.strip())
    return selectors


def validate_selectors(selectors: tuple[str, ...]) -> None:
    unknown_rules = [selector for selector in selectors if selector != "LEG" and selector not in RULES]
    if unknown_rules:
        joined = ", ".join(sorted(set(unknown_rules)))
        raise ValueError(f"Unknown rule selector(s): {joined}")


def find_config(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for candidate in _candidate_config_paths(current):
        if not candidate.is_file():
            continue
        if candidate.name == "pyproject.toml" and not _pyproject_has_config(candidate):
            continue
        return candidate

    return None


def load_settings(config_path: Path | None = None, cwd: Path | None = None) -> Settings:
    settings = Settings()
    path = config_path or find_config(cwd)
    if path is None:
        return settings

    data = tomllib.loads(path.read_text())
    table = _config_table(data, path)
    return apply_config(settings, table)


def apply_overrides(
    settings: Settings,
    *,
    select: tuple[str, ...] | None = None,
    ignore: tuple[str, ...] | None = None,
    max_expression_operators: int | None = None,
    max_if_operators: int | None = None,
    max_ternary_operators: int | None = None,
    max_control_flow_depth: int | None = None,
) -> Settings:
    updates: dict[str, Any] = {}
    if select is not None:
        validate_selectors(select)
        updates["select"] = select
    if ignore is not None:
        validate_selectors(ignore)
        updates["ignore"] = ignore
    if max_expression_operators is not None:
        updates["max_expression_operators"] = max_expression_operators
    if max_if_operators is not None:
        updates["max_if_operators"] = max_if_operators
    if max_ternary_operators is not None:
        updates["max_ternary_operators"] = max_ternary_operators
    if max_control_flow_depth is not None:
        updates["max_control_flow_depth"] = max_control_flow_depth
    return replace(settings, **updates)


def apply_config(settings: Settings, table: dict[str, Any]) -> Settings:
    updates: dict[str, Any] = {}

    selectors = _string_list(table.get("select"), "select")
    if selectors is not None:
        updates["select"] = tuple(selector.upper() for selector in selectors)

    extend_selectors = _string_list(table.get("extend-select", table.get("extend_select")), "extend-select")
    if extend_selectors is not None:
        existing_selectors = updates.get("select", settings.select)
        updates["select"] = (*existing_selectors, *(selector.upper() for selector in extend_selectors))

    ignored = _string_list(table.get("ignore"), "ignore")
    if ignored is not None:
        updates["ignore"] = tuple(selector.upper() for selector in ignored)

    extend_ignored = _string_list(table.get("extend-ignore", table.get("extend_ignore")), "extend-ignore")
    if extend_ignored is not None:
        existing_ignored = updates.get("ignore", settings.ignore)
        updates["ignore"] = (*existing_ignored, *(selector.upper() for selector in extend_ignored))

    excluded = _string_list(table.get("exclude"), "exclude")
    if excluded is not None:
        updates["exclude"] = tuple(excluded)

    per_file_ignores = table.get("per-file-ignores", table.get("per_file_ignores"))
    if per_file_ignores is not None:
        if not isinstance(per_file_ignores, dict):
            raise ValueError("per-file-ignores must be a table")
        updates["per_file_ignores"] = {
            str(pattern): tuple(code.upper() for code in _required_string_list(codes, str(pattern)))
            for pattern, codes in per_file_ignores.items()
        }

    int_options = {
        "max-expression-operators": "max_expression_operators",
        "max-if-operators": "max_if_operators",
        "max-ternary-operators": "max_ternary_operators",
        "max-control-flow-depth": "max_control_flow_depth",
    }
    for option_name, field_name in int_options.items():
        if option_name not in table:
            continue
        value = table[option_name]
        if not isinstance(value, int):
            raise ValueError(f"{option_name} must be an integer")
        updates[field_name] = value

    validate_selectors(updates.get("select", settings.select))
    validate_selectors(updates.get("ignore", settings.ignore))

    return replace(settings, **updates)


def _pyproject_has_config(path: Path) -> bool:
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError:
        return False

    tool = data.get("tool")
    return isinstance(tool, dict) and isinstance(tool.get("ruff-legibility"), dict)


def _candidate_config_paths(current: Path) -> tuple[Path, ...]:
    directories = (current, *current.parents)
    names = ("ruff-legibility.toml", ".ruff-legibility.toml", "pyproject.toml")
    return tuple(directory / name for directory in directories for name in names)


def _config_table(data: dict[str, Any], path: Path) -> dict[str, Any]:
    if path.name == "pyproject.toml":
        tool = data.get("tool", {})
        if not isinstance(tool, dict):
            return {}
        table = tool.get("ruff-legibility", {})
        if not isinstance(table, dict):
            raise ValueError("[tool.ruff-legibility] must be a table")
        return table

    return data


def _string_list(value: Any, name: str) -> list[str] | None:
    if value is None:
        return None
    return _required_string_list(value, name)


def _required_string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a list of strings")
    return value
