from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .config import Settings
from .rules import RULES

if TYPE_CHECKING:
    from .core import Diagnostic

SUPPORTED_NATIVE_RULES = frozenset(f"LEG{number:03d}" for number in range(1, 12))


def check_source_native(source: str, *, path: Path, settings: Settings) -> list[Diagnostic] | None:
    if os.environ.get("RUFF_LEGIBILITY_NATIVE") != "1":
        return None

    if not _settings_supported_by_native(settings):
        return None

    try:
        from . import _native
    except ImportError:
        return None

    payload = json.dumps(_settings_payload(settings))
    diagnostics = json.loads(_native.check_source_json(source, path.as_posix(), payload))
    return [_to_diagnostic(item) for item in diagnostics]


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


def _settings_supported_by_native(settings: Settings) -> bool:
    for code in RULES:
        if code in SUPPORTED_NATIVE_RULES:
            continue
        if settings.enabled(code):
            return False
    return True


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
