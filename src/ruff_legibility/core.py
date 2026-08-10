from __future__ import annotations

import ast
import tokenize
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
    try:
        source = _read_source(path)
    except (SyntaxError, UnicodeError) as error:
        return _source_read_diagnostics(path, error, settings)

    return check_source(source, path=path, settings=settings)


def _read_source(path: Path) -> str:
    with tokenize.open(path) as source_file:
        return source_file.read()


def _source_read_diagnostics(
    path: Path,
    error: SyntaxError | UnicodeError,
    settings: Settings,
) -> list[Diagnostic]:
    if settings.ignored_for_path("LEG999", path):
        return []

    error_name = type(error).__name__
    message = f"{error_name}: {error}"
    diagnostic = Diagnostic(path=path, line=1, column=1, code="LEG999", message=message)
    return [diagnostic]


def check_source(source: str, *, path: Path, settings: Settings) -> list[Diagnostic]:
    native_result = check_source_native(source, path=path, settings=settings)
    if native_result is not None:
        native_diagnostics, fallback_settings = native_result
        if _has_syntax_error(native_diagnostics):
            return _filter_diagnostics(native_diagnostics, source=source, settings=settings)
        python_diagnostics = _check_source_python(source, path=path, settings=fallback_settings)
        return _filter_diagnostics(native_diagnostics + python_diagnostics, source=source, settings=settings)

    python_diagnostics = _check_source_python(source, path=path, settings=settings)
    return _filter_diagnostics(python_diagnostics, source=source, settings=settings)


def _check_source_python(source: str, *, path: Path, settings: Settings) -> list[Diagnostic]:
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
    return visitor.diagnostics


def _has_syntax_error(diagnostics: list[Diagnostic]) -> bool:
    return any(diagnostic.code == "LEG999" for diagnostic in diagnostics)


def discover_python_files(paths: Iterable[Path], settings: Settings) -> list[Path]:
    path_list = list(paths)
    _validate_paths_exist(path_list)
    files = [path for path in path_list if _is_included_python_file(path, settings)]
    directory_files = [
        candidate
        for path in path_list
        if path.is_dir()
        for candidate in _discover_directory_python_files(path, settings)
    ]

    return sorted(set(files + directory_files))


def _validate_paths_exist(paths: list[Path]) -> None:
    for path in paths:
        if not path.exists():
            raise ValueError(f"path does not exist: {path}")


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
