from __future__ import annotations

import os
import shutil
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

SKILL_NAME = "ruff-legibility"


def default_skill_root(target: str) -> Path:
    home = Path.home()

    if target == "agents":
        agents_home = home / ".agents"
        agents_root = agents_home / "skills"
        return agents_root

    if target == "codex":
        default_codex_home = home / ".codex"
        codex_home = Path(os.environ.get("CODEX_HOME", default_codex_home))
        codex_root = codex_home / "skills"
        return codex_root

    raise ValueError(f"unsupported skill target: {target}")


def install_skill(target_root: Path, *, force: bool = False) -> Path:
    expanded_root = target_root.expanduser()
    destination = expanded_root / SKILL_NAME
    destination_exists = destination.exists() or destination.is_symlink()

    if destination_exists:
        if not force:
            message = f"{destination} already exists; use --force to replace it"
            raise FileExistsError(message)
        _remove_existing(destination)

    source = _skill_source()
    expanded_root.mkdir(parents=True, exist_ok=True)
    _copy_resource_tree(source, destination)
    return destination


def _skill_source() -> Traversable:
    package_files = resources.files("ruff_legibility")
    skills_root = package_files / "skills"
    source = skills_root / SKILL_NAME

    if source.is_dir():
        return source

    raise FileNotFoundError(f"packaged {SKILL_NAME} skill was not found")


def _remove_existing(path: Path) -> None:
    is_directory = path.is_dir() and not path.is_symlink()
    if is_directory:
        shutil.rmtree(path)
        return

    path.unlink()


def _copy_resource_tree(source: Traversable, destination: Path) -> None:
    if source.is_dir():
        destination.mkdir()
        for child in source.iterdir():
            child_destination = destination / child.name
            _copy_resource_tree(child, child_destination)
        return

    with source.open("rb") as source_file, destination.open("wb") as target_file:
        shutil.copyfileobj(source_file, target_file)
