from __future__ import annotations

import importlib
import importlib.util
import json
import unittest

from ruff_legibility import native
from ruff_legibility.config import Settings

NATIVE_MODULE = "ruff_legibility._native"
NATIVE_AVAILABLE = importlib.util.find_spec(NATIVE_MODULE) is not None


def native_diagnostics(source: str) -> list[dict[str, object]]:
    native_module = importlib.import_module(NATIVE_MODULE)
    selected_rules = ("LEG005",)
    settings = Settings(select=selected_rules)
    payload = json.dumps(native._settings_payload(settings))
    raw_diagnostics = native_module.check_source_json(source, "example.py", payload)
    return json.loads(raw_diagnostics)


def native_codes(source: str) -> list[str]:
    diagnostics = native_diagnostics(source)
    codes = [str(diagnostic["code"]) for diagnostic in diagnostics]
    return codes


@unittest.skipUnless(NATIVE_AVAILABLE, "native extension is not installed")
class NativeParityTests(unittest.TestCase):
    def test_syntax_error_preserves_location(self) -> None:
        source = "value = 1\n\n\ndef broken(:\n    pass\n"

        diagnostics = native_diagnostics(source)
        diagnostic = diagnostics[0]

        self.assertEqual(diagnostic["code"], "LEG999")
        self.assertEqual(diagnostic["line"], 4)

    def test_membership_condition_inside_loop_reports(self) -> None:
        source = """
def f(items, ids):
    for item in items:
        if item.id in ids:
            yield item
"""
        self.assertIn("LEG005", native_codes(source))

    def test_nested_comprehension_reports(self) -> None:
        source = """
def f(items):
    return [[child for child in item.children] for item in items]
"""
        self.assertIn("LEG005", native_codes(source))

    def test_nested_comprehension_inside_f_string_reports(self) -> None:
        source = '''
def f(items):
    return [f"{[child for child in item.children]}" for item in items]
'''
        self.assertIn("LEG005", native_codes(source))

    def test_nested_comprehension_inside_lambda_reports(self) -> None:
        source = """
def f(items):
    return [(lambda: [child for child in item.children]) for item in items]
"""
        self.assertIn("LEG005", native_codes(source))

    def test_membership_outside_loop_is_allowed(self) -> None:
        source = """
def f(item, ids):
    return item.id in ids
"""
        self.assertNotIn("LEG005", native_codes(source))

    def test_single_comprehension_outside_loop_is_allowed(self) -> None:
        source = """
def f(items):
    return [item.name for item in items]
"""
        self.assertNotIn("LEG005", native_codes(source))


if __name__ == "__main__":
    unittest.main()
