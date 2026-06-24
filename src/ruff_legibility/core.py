from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .native import check_source_native
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
    native_diagnostics = check_source_native(source, path=path, settings=settings)
    if native_diagnostics is not None:
        return _filter_diagnostics(native_diagnostics, source=source, settings=settings)

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

    _annotate_parents(tree)
    visitor = LegibilityVisitor(path=path, settings=settings, source=source)
    visitor.visit(tree)
    return _filter_diagnostics(visitor.diagnostics, source=source, settings=settings)


def discover_python_files(paths: Iterable[Path], settings: Settings) -> list[Path]:
    path_list = list(paths)
    files = [path for path in path_list if _is_included_python_file(path, settings)]
    directory_files = [
        candidate
        for path in path_list
        if path.is_dir()
        for candidate in _discover_directory_python_files(path, settings)
    ]

    return sorted(set(files + directory_files))


def _discover_directory_python_files(path: Path, settings: Settings) -> list[Path]:
    return [candidate for candidate in path.rglob("*.py") if not _is_excluded(candidate, settings)]


def _is_included_python_file(path: Path, settings: Settings) -> bool:
    if not path.is_file():
        return False
    if path.suffix != ".py":
        return False
    return not _is_excluded(path, settings)


def _is_excluded(path: Path, settings: Settings) -> bool:
    parts = set(path.parts)
    return any(excluded in parts or path.match(excluded) for excluded in settings.exclude)


def _filter_diagnostics(
    diagnostics: Iterable[Diagnostic],
    *,
    source: str,
    settings: Settings,
) -> list[Diagnostic]:
    lines = source.splitlines()
    filtered = [
        diagnostic
        for diagnostic in diagnostics
        if not settings.ignored_for_path(diagnostic.code, diagnostic.path)
        and not is_noqa_suppressed(lines, diagnostic.line, diagnostic.code)
    ]
    return sorted(filtered)


def _annotate_parents(tree: ast.AST) -> None:
    pairs = [(parent, child) for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)]
    for parent, child in pairs:
        child._legibility_parent = parent
