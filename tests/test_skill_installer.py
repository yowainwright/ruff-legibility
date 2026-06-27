from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ruff_legibility.agent_skills.constants import SKILL_TARGET_CHOICES, SKILL_TARGETS
from ruff_legibility.agent_skills.installer import default_skill_root, install_skill


class SkillInstallerTests(unittest.TestCase):
    def test_packaged_skill_matches_shared_skill(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        agents_root = repo_root / ".agents"
        shared_skills_root = agents_root / "skills"
        shared_skill_root = shared_skills_root / "ruff-legibility"
        source_root = repo_root / "src"
        package_root = source_root / "ruff_legibility"
        packaged_skills_root = package_root / "skills"
        packaged_skill_root = packaged_skills_root / "ruff-legibility"
        shared_paths = _relative_files(shared_skill_root)
        packaged_paths = _relative_files(packaged_skill_root)

        self.assertEqual(packaged_paths, shared_paths)

        for relative_path in shared_paths:
            shared_path = shared_skill_root / relative_path
            packaged_path = packaged_skill_root / relative_path
            shared_text = shared_path.read_text()
            packaged_text = packaged_path.read_text()
            self.assertEqual(packaged_text, shared_text)

    def test_codex_default_ignores_empty_codex_home(self) -> None:
        home = Path("/tmp/example-home")
        codex_env = {"CODEX_HOME": ""}
        home_patch = "ruff_legibility.agent_skills.installer.Path.home"

        with patch.dict(os.environ, codex_env), patch(home_patch, return_value=home):
            skill_root = default_skill_root("codex")

        self.assertEqual(skill_root, home / ".codex" / "skills")

    def test_codex_default_uses_configured_codex_home(self) -> None:
        configured_home = Path("/tmp/codex-home")
        codex_env = {"CODEX_HOME": str(configured_home)}

        with patch.dict(os.environ, codex_env):
            skill_root = default_skill_root("codex")

        self.assertEqual(skill_root, configured_home / "skills")

    def test_auto_target_uses_configured_codex_home(self) -> None:
        configured_home = Path("/tmp/codex-home")
        codex_env = {"CODEX_HOME": str(configured_home)}

        with patch.dict(os.environ, codex_env):
            skill_root = default_skill_root("auto")

        self.assertEqual(skill_root, configured_home / "skills")

    def test_auto_target_detects_existing_agents_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            agents_root = home / ".agents"
            skills_root = agents_root / "skills"
            codex_env = {"CODEX_HOME": ""}
            home_patch = "ruff_legibility.agent_skills.installer.Path.home"
            skills_root.mkdir(parents=True)

            with patch.dict(os.environ, codex_env), patch(home_patch, return_value=home):
                skill_root = default_skill_root("auto")

            self.assertEqual(skill_root, skills_root)

    def test_auto_target_falls_back_to_agents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            codex_env = {"CODEX_HOME": ""}
            home_patch = "ruff_legibility.agent_skills.installer.Path.home"

            with patch.dict(os.environ, codex_env), patch(home_patch, return_value=home):
                skill_root = default_skill_root("auto")

            self.assertEqual(skill_root, home / ".agents" / "skills")

    def test_cli_targets_come_from_skill_target_constant(self) -> None:
        self.assertEqual(sorted(SKILL_TARGETS), ["agents", "codex"])
        self.assertEqual(SKILL_TARGET_CHOICES, ("auto", "agents", "codex"))

    def test_force_replace_keeps_existing_skill_when_copy_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target_root = Path(directory) / "skills"
            installed = install_skill(target_root)
            marker = installed / "marker.txt"
            copy_patch = "ruff_legibility.agent_skills.installer._copy_resource_tree"
            marker.write_text("keep\n")

            with patch(copy_patch, side_effect=OSError("boom")), self.assertRaises(OSError):
                install_skill(target_root, force=True)

            self.assertEqual(marker.read_text(), "keep\n")


def _relative_files(root: Path) -> list[str]:
    file_paths = [path for path in root.rglob("*") if path.is_file()]
    relative_files = [path.relative_to(root).as_posix() for path in file_paths]
    return sorted(relative_files)


if __name__ == "__main__":
    unittest.main()
