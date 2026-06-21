from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .noqa import is_noqa_suppressed
from .rules import LegibilityVisitor


@dataclass(frozen=True, order=True)
class Diagnostic:
    path: Path
    line: int
    column: int
    code: str
    message: str
    end_line: int | None = None
    end_column: int | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "filename": self.path.as_posix(),
            "location": {"row": self.line, "column": self.column},
            "end_location": {
                "row": self.end_line or self.line,
                "column": self.end_column or self.column,
            },
            "code": self.code,
            "message": self.message,
        }


def check_path(path: Path, settings: Settings) -> list[Diagnostic]:
    source = path.read_text(encoding="utf-8")
    return check_source(source, path=path, settings=settings)


def check_source(source: str, *, path: Path, settings: Settings) -> list[Diagnostic]:
    try:
        tree = ast.parse(source, filename=path.as_posix(), type_comments=True)
    except SyntaxError as error:
        line = error.lineno or 1
        column = (error.offset or 1) - 1
        return [
            Diagnostic(
                path=path,
                line=line,
                column=column + 1,
                code="LEG999",
                message=f"SyntaxError: {error.msg}",
            )
        ]

    visitor = LegibilityVisitor(path=path, settings=settings)
    visitor.visit(tree)
    lines = source.splitlines()
    diagnostics = [
        diagnostic
        for diagnostic in visitor.diagnostics
        if not settings.ignored_for_path(diagnostic.code, path)
        and not is_noqa_suppressed(lines, diagnostic.line, diagnostic.code)
    ]
    return sorted(diagnostics)


def discover_python_files(paths: Iterable[Path], settings: Settings) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            if path.suffix == ".py" and not _is_excluded(path, settings):
                files.append(path)
            continue

        if path.is_dir():
            files.extend(_discover_directory_python_files(path, settings))

    return sorted(set(files))


def _discover_directory_python_files(path: Path, settings: Settings) -> list[Path]:
    return [candidate for candidate in path.rglob("*.py") if not _is_excluded(candidate, settings)]


def _is_excluded(path: Path, settings: Settings) -> bool:
    parts = set(path.parts)
    return any(excluded in parts or path.match(excluded) for excluded in settings.exclude)
