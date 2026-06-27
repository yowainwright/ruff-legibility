from __future__ import annotations

from .schema import SkillTarget

AUTO_SKILL_TARGET = "auto"
DEFAULT_SKILL_TARGET = "agents"
SKILL_NAME = "ruff-legibility"

AGENTS_TARGET = SkillTarget(env_var=None, home_dir=".agents", skills_path=("skills",))
CODEX_TARGET = SkillTarget(env_var="CODEX_HOME", home_dir=".codex", skills_path=("skills",))
SKILL_TARGETS = {
    "agents": AGENTS_TARGET,
    "codex": CODEX_TARGET,
}
SKILL_TARGET_CHOICES = (AUTO_SKILL_TARGET,) + tuple(SKILL_TARGETS)
