from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.agent.build import (
    check_agent_artifacts,
    create_agent_artifacts,
    parse_build_targets,
    write_agent_artifacts,
)


class AgentBuildTests(unittest.TestCase):
    def test_parses_build_targets(self) -> None:
        all_targets = ("package", "agents", "codex", "claude")

        self.assertEqual(parse_build_targets([], {}), ("package",))
        self.assertEqual(parse_build_targets(["--target", "agents,codex"], {}), ("agents", "codex"))
        self.assertEqual(parse_build_targets(["--target=all"], {}), all_targets)
        self.assertEqual(parse_build_targets(["--target=auto"], {"CODEX_HOME": "/tmp/codex"}), ("codex",))
        self.assertEqual(parse_build_targets(["--target=auto"], {"CLAUDECODE": "1"}), ("claude",))
        self.assertEqual(parse_build_targets(["codex"], {}), ("package",))

        with self.assertRaisesRegex(ValueError, "unknown agent build target"):
            parse_build_targets(["--target=unknown"], {})

    def test_creates_package_and_rule_artifacts(self) -> None:
        package_artifacts = create_agent_artifacts("package")
        codex_artifacts = create_agent_artifacts("codex")
        claude_artifacts = create_agent_artifacts("claude")
        package_paths = {artifact.relative_path.as_posix() for artifact in package_artifacts}

        self.assertEqual(
            package_paths,
            {
                "src/ruff_legibility/skills/ruff-legibility/SKILL.md",
                "src/ruff_legibility/skills/ruff-legibility/agents/openai.yaml",
            },
        )
        self.assertEqual(codex_artifacts[0].relative_path.as_posix(), ".codex/rules/ruff-legibility.md")
        self.assertEqual(claude_artifacts[0].relative_path.as_posix(), ".claude/rules/ruff-legibility.md")
        self.assertIn("shared agent skill workflow", codex_artifacts[0].content)

    def test_writes_selected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = write_agent_artifacts(root=root, targets=("agents",))
            skill_path = root / ".agents" / "skills" / "ruff-legibility" / "SKILL.md"
            openai_path = skill_path.parent / "agents" / "openai.yaml"

            self.assertEqual(len(artifacts), 2)
            self.assertTrue(skill_path.is_file())
            self.assertTrue(openai_path.is_file())
            self.assertIn("# Ruff Legibility", skill_path.read_text())

    def test_check_reports_stale_artifacts_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_agent_artifacts(root=root, targets=("package",))
            package_root = root / "src" / "ruff_legibility" / "skills"
            skill_path = package_root / "ruff-legibility" / "SKILL.md"
            skill_path.write_text("stale\n")

            stale_paths = check_agent_artifacts(root=root, targets=("package",))

            self.assertEqual(stale_paths, (skill_path.relative_to(root),))
            self.assertEqual(skill_path.read_text(), "stale\n")

    def test_repository_artifacts_match_generator(self) -> None:
        root = Path(__file__).resolve().parents[1]

        self.assertEqual(check_agent_artifacts(root=root, targets=("package", "agents")), ())


if __name__ == "__main__":
    unittest.main()
