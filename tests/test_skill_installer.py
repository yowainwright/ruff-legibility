from __future__ import annotations

import unittest
from pathlib import Path


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
        relative_paths = ("SKILL.md", "agents/openai.yaml")

        for relative_path in relative_paths:
            shared_path = shared_skill_root / relative_path
            packaged_path = packaged_skill_root / relative_path
            shared_text = shared_path.read_text()
            packaged_text = packaged_path.read_text()
            self.assertEqual(packaged_text, shared_text)


if __name__ == "__main__":
    unittest.main()
