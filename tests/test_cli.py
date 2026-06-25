from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ruff_legibility.cli import _print_diagnostics, main
from ruff_legibility.core import Diagnostic


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
            self.assertIn("LEG006", [item["code"] for item in output])

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
        self.assertIn("ruff-legibility 0.2.0", stdout.getvalue())

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
            output = json.loads(stdout.getvalue())
            self.assertIn("LEG006", [item["code"] for item in output])

    def test_cli_passes_new_integer_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example" / "example.py"
            path.parent.mkdir()
            path.write_text("value = 1\n")
            captured = {}

            def capture_overrides(settings, **kwargs):
                captured.update(kwargs)
                return settings

            with patch("ruff_legibility.cli.apply_overrides", side_effect=capture_overrides):
                exit_code = main(
                    [
                        "check",
                        str(path),
                        "--max-computed-value-operators",
                        "3",
                        "--max-array-chain-depth",
                        "4",
                        "--min-object-lookup-chain-length",
                        "5",
                        "--min-dirname-match-depth",
                        "6",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(captured["max_computed_value_operators"], 3)
            self.assertEqual(captured["max_array_chain_depth"], 4)
            self.assertEqual(captured["min_object_lookup_chain_length"], 5)
            self.assertEqual(captured["min_dirname_match_depth"], 6)

    def test_github_output_escapes_workflow_command_values(self) -> None:
        diagnostics = [
            Diagnostic(
                path=Path("dir:name,with\nnewline.py"),
                line=1,
                column=2,
                code="LEG999",
                message="first line\n::error::injected%message",
            )
        ]
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            _print_diagnostics(diagnostics, output_format="github")

        output = stdout.getvalue()
        self.assertEqual(output.count("\n"), 1)
        self.assertIn("file=dir%3Aname%2Cwith%0Anewline.py", output)
        self.assertIn("LEG999 first line%0A::error::injected%25message", output)


if __name__ == "__main__":
    unittest.main()
