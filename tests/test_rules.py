from __future__ import annotations

import unittest
from pathlib import Path

from ruff_legibility.config import Settings
from ruff_legibility.core import check_source


def codes(source: str, *, settings: Settings | None = None) -> list[str]:
    diagnostics = check_source(source, path=Path("example.py"), settings=settings or Settings())
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


if __name__ == "__main__":
    unittest.main()
