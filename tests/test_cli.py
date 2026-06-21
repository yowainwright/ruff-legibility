from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from ruff_legibility.cli import main


class CliTests(unittest.TestCase):
    def test_cli_reports_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.py"
            path.write_text("def f(flag):\n    return flag == True\n")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["check", str(path), "--format", "json"])

            output = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertEqual(output[0]["code"], "LEG006")

    def test_cli_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.py"
            path.write_text("def f(flag):\n    return flag == True\n")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["check", str(path), "--exit-zero"])

            self.assertEqual(exit_code, 0)

    def test_cli_rules(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["rules"])

        self.assertEqual(exit_code, 0)
        self.assertIn("LEG001 max-expression-operators", stdout.getvalue())

    def test_cli_version_is_top_level_flag(self) -> None:
        stdout = io.StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
            main(["--version"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("ruff-legibility 0.1.0", stdout.getvalue())

    def test_default_check_accepts_check_options(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.py"
            path.write_text("def f(flag):\n    return flag == True\n")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([str(path), "--output-format", "json", "--exit-zero"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(json.loads(stdout.getvalue())[0]["code"], "LEG006")


if __name__ == "__main__":
    unittest.main()
