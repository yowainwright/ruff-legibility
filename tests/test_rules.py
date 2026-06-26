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

    def test_quadratic_membership_condition_in_loop_reports(self) -> None:
        source = """
def f(items, ids):
    for item in items:
        if item.id in ids:
            yield item
"""
        self.assertIn("LEG005", codes(source))

    def test_quadratic_nested_comprehension_reports(self) -> None:
        source = """
def f(items):
    return [[child for child in item.children] for item in items]
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

    def test_hidden_assignment_expression_reports_outside_condition(self) -> None:
        source = """
def f():
    return (value := load())
"""
        self.assertIn("LEG013", codes(source))

    def test_hidden_assignment_expression_allows_condition(self) -> None:
        source = """
def f():
    if value := load():
        return value
    return None
"""
        self.assertNotIn("LEG013", codes(source))

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

    def test_identity_comprehension_reports(self) -> None:
        source = """
def f(items):
    copied = [item for item in items]
    unique = {item for item in items}
    return copied, unique
"""
        self.assertEqual(codes(source, settings=Settings(select=("LEG027",))).count("LEG027"), 2)

    def test_prefer_comprehension_over_map_filter_reports(self) -> None:
        source = """
def f(items):
    names = list(map(lambda item: item.name, items))
    active = tuple(filter(lambda item: item.active, items))
    return names, active
"""
        self.assertEqual(codes(source, settings=Settings(select=("LEG028",))).count("LEG028"), 2)

    def test_loop_append_comprehension_reports(self) -> None:
        source = """
def f(items):
    names = []
    for item in items:
        names.append(item.name)
    return names
"""
        self.assertIn("LEG029", codes(source, settings=Settings(select=("LEG029",))))

    def test_repeated_comprehension_filter_reports(self) -> None:
        source = """
def f(users):
    active = [user for user in users if user.active]
    admins = [user for user in users if user.is_admin]
    return active, admins
"""
        self.assertIn("LEG030", codes(source, settings=Settings(select=("LEG030",))))

    def test_deep_subscript_chain_reports(self) -> None:
        source = """
def f(payload):
    return payload["user"]["profile"]["email"]
"""
        self.assertIn("LEG031", codes(source, settings=Settings(select=("LEG031",))))

    def test_named_exception_context_reports_direct_wrapping(self) -> None:
        source = """
def f():
    try:
        load()
    except Exception as error:
        raise RuntimeError(error)
"""
        self.assertIn("LEG032", codes(source, settings=Settings(select=("LEG032",))))

    def test_boolean_parameter_name_drift_reports(self) -> None:
        source = """
def f(status):
    is_ready = status != "ready"
    return is_ready
"""
        self.assertIn("LEG033", codes(source, settings=Settings(select=("LEG033",))))


if __name__ == "__main__":
    unittest.main()
