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
from .skill_installer import SKILL_NAME, default_skill_root, install_skill


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = sys.argv[1:]
    if argv is not None:
        raw_argv = list(argv)

    args = _parse_args(raw_argv)

    if args.command == "rules":
        _print_rules()
        return 0

    if args.command == "install-skill":
        return _install_skill_command(args)

    try:
        settings = load_settings(Path(args.config) if args.config else None)
        settings = apply_overrides(
            settings,
            select=parse_selectors(args.select),
            ignore=parse_selectors(args.ignore),
            max_expression_operators=args.max_expression_operators,
            max_if_operators=args.max_if_operators,
            max_ternary_operators=args.max_ternary_operators,
            max_computed_value_operators=args.max_computed_value_operators,
            max_control_flow_depth=args.max_control_flow_depth,
            max_array_chain_depth=args.max_array_chain_depth,
            min_object_lookup_chain_length=args.min_object_lookup_chain_length,
            min_dirname_match_depth=args.min_dirname_match_depth,
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
    commands = {"check", "install-skill", "rules"}
    has_command = bool(argv) and argv[0] in commands
    has_top_level_flag = bool(argv) and argv[0] in top_level_flags
    has_known_prefix = has_command or has_top_level_flag
    should_default_to_check = not argv or not has_known_prefix

    if should_default_to_check:
        argv = ["check"] + argv

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
    check.add_argument("--max-computed-value-operators", type=int)
    check.add_argument("--max-control-flow-depth", type=int)
    check.add_argument("--max-array-chain-depth", type=int)
    check.add_argument("--min-object-lookup-chain-length", type=int)
    check.add_argument("--min-dirname-match-depth", type=int)

    subparsers.add_parser("rules", help="list available rules")

    install_skill_parser = subparsers.add_parser("install-skill", help="install the packaged agent skill")
    install_skill_parser.add_argument(
        "--target",
        choices=("agents", "codex"),
        default="agents",
        help="agent skill root to install into",
    )
    install_skill_parser.add_argument("--path", help="override the skill root directory")
    install_skill_parser.add_argument("--force", action="store_true", help="replace an existing installed skill")
    return parser.parse_args(argv)


def _install_skill_command(args: argparse.Namespace) -> int:
    target_root = _resolve_skill_root(args)

    try:
        installed_path = install_skill(target_root, force=args.force)
    except (FileExistsError, OSError, ValueError) as error:
        print(f"ruff-legibility: {error}", file=sys.stderr)
        return 2

    print(f"Installed {SKILL_NAME} skill to {installed_path}")
    return 0


def _resolve_skill_root(args: argparse.Namespace) -> Path:
    if not args.path:
        return default_skill_root(args.target)

    target_root = Path(args.path)
    return target_root.expanduser()


def _check_files(files: list[Path], settings) -> list[Diagnostic]:
    diagnostics = [diagnostic for file in files for diagnostic in check_path(file, settings)]
    return sorted(diagnostics)


def _print_diagnostics(diagnostics: list[Diagnostic], *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps([diagnostic.to_json() for diagnostic in diagnostics], indent=2))
        return

    for diagnostic in diagnostics:
        if output_format == "github":
            file_name = _escape_github_command_property(diagnostic.path.as_posix())
            message = _escape_github_command_data(f"{diagnostic.code} {diagnostic.message}")
            print(
                f"::warning file={file_name},"
                f"line={diagnostic.line},col={diagnostic.column}::"
                f"{message}"
            )
        else:
            print(
                f"{diagnostic.path.as_posix()}:{diagnostic.line}:{diagnostic.column}: "
                f"{diagnostic.code} {diagnostic.message}"
            )


def _escape_github_command_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_github_command_property(value: str) -> str:
    return _escape_github_command_data(value).replace(":", "%3A").replace(",", "%2C")


def _print_rules() -> None:
    for code, rule in RULES.items():
        print(f"{code} {rule.name}: {rule.summary}")
