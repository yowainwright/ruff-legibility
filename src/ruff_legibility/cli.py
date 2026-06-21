from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .config import apply_overrides, load_settings, parse_selectors
from .core import Diagnostic, check_path, discover_python_files
from .rules import RULES


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(list(argv) if argv is not None else sys.argv[1:])

    if args.command == "rules":
        _print_rules()
        return 0

    try:
        settings = load_settings(Path(args.config) if args.config else None)
        settings = apply_overrides(
            settings,
            select=parse_selectors(args.select),
            ignore=parse_selectors(args.ignore),
            max_expression_operators=args.max_expression_operators,
            max_if_operators=args.max_if_operators,
            max_ternary_operators=args.max_ternary_operators,
            max_control_flow_depth=args.max_control_flow_depth,
        )
    except ValueError as error:
        print(f"ruff-legibility: {error}", file=sys.stderr)
        return 2

    paths = [Path(path) for path in args.paths]
    files = discover_python_files(paths, settings)
    diagnostics = _check_files(files, settings)
    _print_diagnostics(diagnostics, output_format=args.output_format)

    if args.exit_zero:
        return 0
    return 1 if diagnostics else 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    top_level_flags = {"-h", "--help", "--version"}
    if not argv or (argv[0] not in {"check", "rules"} and argv[0] not in top_level_flags):
        argv = ["check", *argv]

    parser = argparse.ArgumentParser(prog="ruff-legibility")
    parser.add_argument("--version", action="version", version=f"ruff-legibility {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="check Python files")
    check.add_argument("paths", nargs="*", default=["."], help="files or directories to check")
    check.add_argument("--config", help="path to ruff-legibility.toml or pyproject.toml")
    check.add_argument("--select", help="comma-separated rule selectors to enable")
    check.add_argument("--ignore", help="comma-separated rule selectors to ignore")
    check.add_argument(
        "--output-format",
        "--format",
        choices=("text", "json", "github"),
        default="text",
        help="diagnostic output format",
    )
    check.add_argument("--exit-zero", action="store_true", help="always exit successfully")
    check.add_argument("--max-expression-operators", type=int)
    check.add_argument("--max-if-operators", type=int)
    check.add_argument("--max-ternary-operators", type=int)
    check.add_argument("--max-control-flow-depth", type=int)

    subparsers.add_parser("rules", help="list available rules")
    return parser.parse_args(argv)


def _check_files(files: list[Path], settings) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for file in files:
        diagnostics.extend(check_path(file, settings))
    return sorted(diagnostics)


def _print_diagnostics(diagnostics: list[Diagnostic], *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps([diagnostic.to_json() for diagnostic in diagnostics], indent=2))
        return

    for diagnostic in diagnostics:
        if output_format == "github":
            print(
                f"::warning file={diagnostic.path.as_posix()},"
                f"line={diagnostic.line},col={diagnostic.column}::"
                f"{diagnostic.code} {diagnostic.message}"
            )
        else:
            print(
                f"{diagnostic.path.as_posix()}:{diagnostic.line}:{diagnostic.column}: "
                f"{diagnostic.code} {diagnostic.message}"
            )


def _print_rules() -> None:
    for code, rule in RULES.items():
        print(f"{code} {rule.name}: {rule.summary}")
