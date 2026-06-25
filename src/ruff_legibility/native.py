from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .config import Settings

if TYPE_CHECKING:
    from .core import Diagnostic

SUPPORTED_NATIVE_RULES = (
    "LEG001",
    "LEG002",
    "LEG003",
    "LEG004",
    "LEG005",
    "LEG006",
    "LEG007",
    "LEG008",
    "LEG009",
    "LEG010",
    "LEG011",
)


def check_source_native(source: str, *, path: Path, settings: Settings) -> tuple[list[Diagnostic], Settings] | None:
    if os.environ.get("RUFF_LEGIBILITY_NATIVE") != "1":
        return None

    native_settings = _native_settings(settings)
    if native_settings is None:
        return None

    try:
        from . import _native
    except ImportError:
        return None

    payload = json.dumps(_settings_payload(native_settings))
    diagnostics = json.loads(_native.check_source_json(source, path.as_posix(), payload))
    return [_to_diagnostic(item) for item in diagnostics], _python_fallback_settings(settings)


def _settings_payload(settings: Settings) -> dict[str, Any]:
    return {
        "select": settings.select,
        "ignore": settings.ignore,
        "max_expression_operators": settings.max_expression_operators,
        "max_if_operators": settings.max_if_operators,
        "max_ternary_operators": settings.max_ternary_operators,
        "max_control_flow_depth": settings.max_control_flow_depth,
        "max_array_chain_depth": settings.max_array_chain_depth,
    }


def _native_settings(settings: Settings) -> Settings | None:
    selected = _enabled_native_rules(settings)
    if not selected:
        return None

    return replace(settings, select=selected, ignore=())


def _python_fallback_settings(settings: Settings) -> Settings:
    native_ignored = _enabled_native_rules(settings)
    fallback_ignore = settings.ignore + native_ignored
    return replace(settings, ignore=fallback_ignore)


def _enabled_native_rules(settings: Settings) -> tuple[str, ...]:
    enabled_rules = filter(settings.enabled, SUPPORTED_NATIVE_RULES)
    return tuple(enabled_rules)


def _to_diagnostic(item: dict[str, Any]) -> Diagnostic:
    from .core import Diagnostic

    return Diagnostic(
        path=Path(str(item["filename"])),
        line=int(item["line"]),
        column=int(item["column"]),
        end_line=int(item["end_line"]),
        end_column=int(item["end_column"]),
        code=str(item["code"]),
        message=str(item["message"]),
    )
