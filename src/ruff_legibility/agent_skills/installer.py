from __future__ import annotations

import os
import shutil
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from uuid import uuid4

from .constants import AUTO_SKILL_TARGET, DEFAULT_SKILL_TARGET, SKILL_NAME, SKILL_TARGETS
from .schema import SkillTarget


def default_skill_root(target: str) -> Path:
    if target == AUTO_SKILL_TARGET:
        detected_target = detect_skill_target()
        return default_skill_root(detected_target)

    target_config = SKILL_TARGETS.get(target)
    if target_config is None:
        raise ValueError(f"unsupported skill target: {target}")

    target_home = _target_home(target_config)
    return _skill_root(target_home, target_config)


def detect_skill_target() -> str:
    configured_target = _configured_target()
    if configured_target:
        return configured_target

    existing_target = _existing_target()
    if existing_target:
        return existing_target

    return DEFAULT_SKILL_TARGET


def install_skill(target_root: Path, *, force: bool = False) -> Path:
    expanded_root = target_root.expanduser()
    destination = expanded_root / SKILL_NAME
    destination_exists = destination.exists() or destination.is_symlink()
    should_refuse_existing = destination_exists and not force

    if should_refuse_existing:
        message = f"{destination} already exists; use --force to replace it"
        raise FileExistsError(message)

    source = _skill_source()
    expanded_root.mkdir(parents=True, exist_ok=True)
    _install_from_resource(source, destination, replace_existing=destination_exists)
    return destination


def _target_home(target: SkillTarget) -> Path:
    if target.env_var:
        configured_home = os.environ.get(target.env_var)
        if configured_home:
            return Path(configured_home)

    return Path.home() / target.home_dir


def _skill_root(target_home: Path, target: SkillTarget) -> Path:
    skill_root = target_home
    for path_part in target.skills_path:
        skill_root = skill_root / path_part
    return skill_root


def _configured_target() -> str | None:
    for name, target in SKILL_TARGETS.items():
        has_env_var = target.env_var and os.environ.get(target.env_var)
        if has_env_var:
            return name
    return None


def _existing_target() -> str | None:
    skill_root_target = _existing_skill_root_target()
    if skill_root_target:
        return skill_root_target

    return _existing_home_target()


def _existing_skill_root_target() -> str | None:
    for name, target in SKILL_TARGETS.items():
        target_home = _target_home(target)
        skill_root = _skill_root(target_home, target)
        if skill_root.exists():
            return name
    return None


def _existing_home_target() -> str | None:
    for name, target in SKILL_TARGETS.items():
        target_home = _target_home(target)
        if target_home.exists():
            return name
    return None


def _skill_source() -> Traversable:
    package_files = resources.files("ruff_legibility")
    skills_root = package_files / "skills"
    source = skills_root / SKILL_NAME

    if source.is_dir():
        return source

    raise FileNotFoundError(f"packaged {SKILL_NAME} skill was not found")


def _install_from_resource(source: Traversable, destination: Path, *, replace_existing: bool) -> None:
    replacement = _temporary_path(destination, "tmp")
    try:
        _copy_resource_tree(source, replacement)
        if replace_existing:
            _replace_existing(replacement, destination)
            return
        os.replace(replacement, destination)
    finally:
        if replacement.exists() or replacement.is_symlink():
            _remove_existing(replacement)


def _replace_existing(replacement: Path, destination: Path) -> None:
    backup = _temporary_path(destination, "old")
    os.replace(destination, backup)
    try:
        os.replace(replacement, destination)
    except BaseException:
        os.replace(backup, destination)
        raise
    _remove_existing(backup)


def _temporary_path(destination: Path, label: str) -> Path:
    temporary_name = f".{destination.name}.{label}.{uuid4().hex}"
    return destination.with_name(temporary_name)


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
