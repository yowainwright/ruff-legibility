from __future__ import annotations

import unittest
from pathlib import Path

from ruff_legibility.config import Settings
from ruff_legibility.core import check_source


def codes(
    source: str,
    *,
    path: Path = Path("example.py"),
    settings: Settings | None = None,
) -> list[str]:
    diagnostics = check_source(source, path=path, settings=settings or Settings())
    return [diagnostic.code for diagnostic in diagnostics]


class RuleTests(unittest.TestCase):
    def test_hoist_if_operators_reports_boolean_condition(self) -> None:
        source = """
def can_invite(user):
    if user and user.is_active and not user.is_locked:
        return True
    return False
"""
        self.assertIn("LEG002", codes(source))

    def test_max_control_flow_depth_reports_nested_branch(self) -> None:
        source = """
def f(a, b, c, d):
    if a:
        for item in b:
            if c:
                while d:
                    return item
"""
        self.assertIn("LEG003", codes(source, settings=Settings(max_control_flow_depth=3)))

    def test_complex_ternary_reports(self) -> None:
        source = """
def f(a, b, c, d):
    return a + b if c and d else a - b
"""
        self.assertIn("LEG004", codes(source, settings=Settings(max_ternary_operators=1)))

    def test_quadratic_nested_loop_reports(self) -> None:
        source = """
def f(items, others):
    for item in items:
        for other in others:
            print(item, other)
"""
        self.assertIn("LEG005", codes(source))

    def test_redundant_boolean_compare_reports(self) -> None:
        source = """
def f(flag):
    return flag == True
"""
        self.assertIn("LEG006", codes(source))

    def test_redundant_boolean_ternary_reports(self) -> None:
        source = """
def f(flag):
    return True if flag else False
"""
        self.assertIn("LEG006", codes(source))

    def test_negative_condition_name_reports(self) -> None:
        source = """
def f(is_not_ready):
    return is_not_ready
"""
        self.assertIn("LEG007", codes(source))

    def test_trivial_wrapper_function_reports(self) -> None:
        source = """
def normalize(value):
    return clean(value)
"""
        self.assertIn("LEG008", codes(source))

    def test_prefer_early_return_reports_else_after_terminal_branch(self) -> None:
        source = """
def f(flag):
    if flag:
        return 1
    else:
        return 2
"""
        self.assertIn("LEG009", codes(source))

    def test_prefer_guard_clause_reports_wrapped_main_path(self) -> None:
        source = """
def f(is_ready):
    if is_ready:
        prepare()
        finish()
"""
        self.assertIn("LEG010", codes(source))

    def test_noqa_suppresses_specific_rule(self) -> None:
        source = """
def f(flag):
    return flag == True  # noqa: LEG006
"""
        self.assertNotIn("LEG006", codes(source))

    def test_direct_python_bin_smoke_uses_configured_runtime(self) -> None:
        source = """
import subprocess

def test_entry():
    subprocess.run(["python3.11", "scripts/entry.py"])
"""
        settings = Settings(select=("LEG017",), executable_runtimes=("python3.11",))

        self.assertIn("LEG017", codes(source, settings=settings))

    def test_direct_python_bin_smoke_supports_subprocess_imports(self) -> None:
        source = """
from subprocess import run as subprocess_run
import subprocess as sp

def test_entry():
    subprocess_run(["python", "scripts/entry.py"])
    sp.call(["python", "scripts/entry.py"])
"""
        settings = Settings(select=("LEG017",))

        self.assertEqual(codes(source, settings=settings).count("LEG017"), 2)

    def test_direct_python_bin_smoke_ignores_unqualified_user_functions(self) -> None:
        source = """
def run(command):
    return command

def test_entry():
    run(["python", "scripts/entry.py"])
"""
        settings = Settings(select=("LEG017",))

        self.assertNotIn("LEG017", codes(source, settings=settings))

    def test_mixed_filename_casing_allows_screaming_kebab_case(self) -> None:
        settings = Settings(select=("LEG026",))

        self.assertNotIn("LEG026", codes("value = 1\n", path=Path("FEATURE-FLAG.py"), settings=settings))
        self.assertIn("LEG026", codes("value = 1\n", path=Path("Feature-flag.py"), settings=settings))


if __name__ == "__main__":
    unittest.main()
