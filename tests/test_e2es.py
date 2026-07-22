from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = ROOT / "scripts" / "test_e2es.sh"
DOCKER_STUB = """#!/bin/sh
set -eu

while [ "$#" -gt 0 ]; do
  if [ "$1" = "--file" ]; then
    shift
    printf '%s\\n' "$1" >> "$DOCKER_LOG"
    exit 0
  fi
  shift
done

exit 2
"""


class E2EScriptTests(unittest.TestCase):
    def test_builds_base_and_every_recipe(self) -> None:
        result, calls = self._run_script()

        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(calls), 4)
        self.assertEqual(Path(calls[0]).name, "Dockerfile.base")
        self.assertEqual(
            [Path(call).name for call in calls[1:]],
            ["Dockerfile.agent", "Dockerfile.human", "Dockerfile.ci"],
        )

    def test_builds_only_selected_recipe(self) -> None:
        result, calls = self._run_script("human")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(Path(calls[1]).name, "Dockerfile.human")

    def test_preserves_checkout_path_with_spaces(self) -> None:
        result, calls = self._run_script("agent")

        self.assertEqual(result.returncode, 0)
        self.assertIn("checkout with spaces", calls[0])
        self.assertIn("checkout with spaces", calls[1])

    def test_rejects_unknown_recipe_before_building(self) -> None:
        result, calls = self._run_script("unknown")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])
        self.assertIn("unknown E2E mode: unknown", result.stderr)

    def _run_script(self, *args: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            checkout_root = temporary_root / "checkout with spaces"
            script_path = self._copy_script(checkout_root)
            log_path = temporary_root / "docker.log"
            docker_path = temporary_root / "docker"
            docker_path.write_text(DOCKER_STUB, encoding="utf-8")
            docker_path.chmod(0o755)
            environment = dict(os.environ)
            environment["DOCKER_BIN"] = str(docker_path)
            environment["DOCKER_LOG"] = str(log_path)
            command = [str(script_path)] + list(args)
            result = subprocess.run(
                command,
                cwd=checkout_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            calls = log_path.read_text(encoding="utf-8").splitlines() if log_path.exists() else []
        return result, calls

    @staticmethod
    def _copy_script(checkout_root: Path) -> Path:
        script_directory = checkout_root / "scripts"
        script_directory.mkdir(parents=True)
        script_path = script_directory / SOURCE_SCRIPT.name
        shutil.copy2(SOURCE_SCRIPT, script_path)
        return script_path


if __name__ == "__main__":
    unittest.main()
