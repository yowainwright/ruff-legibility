from __future__ import annotations

from typing import NamedTuple


class SkillTarget(NamedTuple):
    env_var: str | None
    home_dir: str
    skills_path: tuple[str, ...]
