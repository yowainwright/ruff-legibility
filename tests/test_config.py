from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ruff_legibility.config import Settings, apply_config, apply_overrides, load_settings
from ruff_legibility.core import check_source


class ConfigTests(unittest.TestCase):
    def test_loads_pyproject_tool_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pyproject.toml"
            path.write_text(
                """
[tool.ruff-legibility]
select = ["LEG001"]
ignore = ["LEG007"]
max-expression-operators = 7

[tool.ruff-legibility.per-file-ignores]
"tests/*" = ["LEG003"]
""".strip()
            )

            settings = load_settings(path)

        self.assertEqual(settings.select, ("LEG001",))
        self.assertEqual(settings.ignore, ("LEG007",))
        self.assertEqual(settings.max_expression_operators, 7)
        self.assertEqual(settings.per_file_ignores, {"tests/*": ("LEG003",)})

    def test_extend_select_and_ignore_append_to_existing_values(self) -> None:
        settings = apply_config(
            Settings(select=("LEG001",), ignore=("LEG002",)),
            {
                "extend-select": ["LEG003"],
                "extend-ignore": ["LEG004"],
            },
        )

        self.assertEqual(settings.select, ("LEG001", "LEG003"))
        self.assertEqual(settings.ignore, ("LEG002", "LEG004"))

    def test_unknown_config_selector_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown rule selector"):
            apply_config(Settings(), {"select": ["NOPE"]})

    def test_unknown_cli_selector_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown rule selector"):
            apply_overrides(Settings(), select=("NOPE",))

    def test_per_file_ignores_suppress_matching_diagnostics(self) -> None:
        source = """
def f(flag):
    return flag == True
"""
        settings = Settings(per_file_ignores={"tests/*": ("LEG006",)})
        diagnostics = check_source(source, path=Path("tests/example.py"), settings=settings)

        self.assertEqual(diagnostics, [])


if __name__ == "__main__":
    unittest.main()
