from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Settings
    from .core import Diagnostic


@dataclass(frozen=True)
class Rule:
    code: str
    name: str
    summary: str


RULES = {
    "LEG001": Rule(
        "LEG001",
        "max-expression-operators",
        "Limit readability operators inside a single expression.",
    ),
    "LEG002": Rule(
        "LEG002",
        "hoist-if-operators",
        "Prefer named booleans before operator-heavy conditions.",
    ),
    "LEG003": Rule(
        "LEG003",
        "max-control-flow-depth",
        "Limit nested control-flow depth.",
    ),
    "LEG004": Rule(
        "LEG004",
        "no-complex-ternary",
        "Avoid complex ternary expressions.",
    ),
    "LEG005": Rule(
        "LEG005",
        "no-quadratic-patterns",
        "Flag likely quadratic loops and repeated searches.",
    ),
    "LEG006": Rule(
        "LEG006",
        "no-redundant-boolean-logic",
        "Avoid redundant boolean comparisons.",
    ),
    "LEG007": Rule(
        "LEG007",
        "prefer-positive-condition-names",
        "Prefer positive condition names.",
    ),
}

DEFAULT_SELECT = ("LEG",)

CONTROL_FLOW_NODES = (
    ast.AsyncFor,
    ast.AsyncWith,
    ast.For,
    ast.If,
    ast.Match,
    ast.Try,
    ast.While,
    ast.With,
)

BOOLEAN_NAME_PATTERN = re.compile(r"^(?:is|are|was|were|has|have|had|can|could|should|will|would|did|does)_")
NEGATIVE_CONDITION_PATTERN = re.compile(
    r"^(?:is|are|was|were|has|have|had|can|could|should|will|would|did|does)_"
    r"(?:not|no|without)_"
)


class LegibilityVisitor(ast.NodeVisitor):
    def __init__(self, *, path: Path, settings: Settings) -> None:
        self.path = path
        self.settings = settings
        self.diagnostics: list[Diagnostic] = []
        self.control_depth = 0
        self.loop_depth = 0

    def visit_If(self, node: ast.If) -> None:
        self._check_condition(node.test)
        self._visit_control_body(node, body=node.body, orelse=node.orelse)

    def visit_While(self, node: ast.While) -> None:
        self._check_condition(node.test)
        self._visit_loop(node)

    def visit_For(self, node: ast.For) -> None:
        self._visit_loop(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_loop(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_control_body(node, body=node.body)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_control_body(node, body=node.body)

    def visit_Try(self, node: ast.Try) -> None:
        self._enter_control(node)
        self._visit_many(node.body)
        for handler in node.handlers:
            self.visit(handler)
        self._visit_many(node.orelse)
        self._visit_many(node.finalbody)
        self._leave_control()

    def visit_Match(self, node: ast.Match) -> None:
        self._enter_control(node)
        for case in node.cases:
            self._visit_many(case.body)
        self._leave_control()

    def visit_IfExp(self, node: ast.IfExp) -> None:
        if self.settings.enabled("LEG004"):
            count = count_readability_operators(node)
            if count > self.settings.max_ternary_operators:
                self._add(
                    node,
                    "LEG004",
                    f"Ternary expression has {count} readability operators "
                    f"(max {self.settings.max_ternary_operators}). Extract it into named branches.",
                )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._check_expression(node.value)
        for target in node.targets:
            self._check_condition_name(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self._check_expression(node.value)
        self._check_condition_name(node.target)
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._check_condition_name(node.target)
        self._check_expression(node.value)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is not None:
            self._check_expression(node.value)
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        self._check_expression(node.value)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self._check_name(node.arg, node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_name(node.name, node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_name(node.name, node)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        if self.settings.enabled("LEG006") and _has_redundant_boolean_compare(node):
            self._add(
                node,
                "LEG006",
                "Avoid redundant boolean comparisons. Use the boolean value directly.",
            )

        if self.loop_depth > 0 and self.settings.enabled("LEG005") and _has_membership_search(node):
            self._add(
                node,
                "LEG005",
                "Membership test inside a loop can become O(n^2). Use a set or dict for repeated lookups.",
            )
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        if self.settings.enabled("LEG006") and _has_redundant_boolean_operand(node):
            self._add(
                node,
                "LEG006",
                "Avoid redundant boolean operands like `and True` or `or False`.",
            )
        self.generic_visit(node)

    def _visit_loop(self, node: ast.For | ast.AsyncFor | ast.While) -> None:
        if self.loop_depth > 0 and self.settings.enabled("LEG005"):
            self._add(
                node,
                "LEG005",
                "Nested loop detected. Consider restructuring around a set, dict, or precomputed lookup.",
            )

        self.loop_depth += 1
        self._visit_control_body(node, body=node.body, orelse=node.orelse)
        self.loop_depth -= 1

    def _visit_control_body(
        self,
        node: ast.AST,
        *,
        body: Iterable[ast.stmt],
        orelse: Iterable[ast.stmt] = (),
    ) -> None:
        self._enter_control(node)
        self._visit_many(body)
        self._visit_many(orelse)
        self._leave_control()

    def _enter_control(self, node: ast.AST) -> None:
        self.control_depth += 1
        if self.settings.enabled("LEG003") and self.control_depth > self.settings.max_control_flow_depth:
            self._add(
                node,
                "LEG003",
                f"Control-flow depth is {self.control_depth} "
                f"(max {self.settings.max_control_flow_depth}). Prefer guard clauses or extraction.",
            )

    def _leave_control(self) -> None:
        self.control_depth -= 1

    def _visit_many(self, nodes: Iterable[ast.AST]) -> None:
        for node in nodes:
            self.visit(node)

    def _check_condition(self, expression: ast.expr) -> None:
        if not self.settings.enabled("LEG002"):
            return

        count = count_condition_operators(expression)
        if count > self.settings.max_if_operators:
            self._add(
                expression,
                "LEG002",
                f"If condition has {count} boolean operators "
                f"(max {self.settings.max_if_operators}). Hoist it into a named boolean.",
            )

    def _check_expression(self, expression: ast.expr) -> None:
        if not self.settings.enabled("LEG001"):
            return

        if isinstance(expression, (ast.Constant, ast.Name)):
            return

        count = count_readability_operators(expression)
        if count > self.settings.max_expression_operators:
            self._add(
                expression,
                "LEG001",
                f"Expression has {count} readability operators "
                f"(max {self.settings.max_expression_operators}). Extract named sub-expressions.",
            )

    def _check_condition_name(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self._check_name(target.id, target)

    def _check_name(self, name: str, node: ast.AST) -> None:
        if not self.settings.enabled("LEG007"):
            return

        if BOOLEAN_NAME_PATTERN.match(name) and NEGATIVE_CONDITION_PATTERN.match(name):
            self._add(
                node,
                "LEG007",
                f"Prefer a positive condition name instead of `{name}`.",
            )

    def _add(self, node: ast.AST, code: str, message: str) -> None:
        if not self.settings.enabled(code):
            return

        from .core import Diagnostic

        self.diagnostics.append(
            Diagnostic(
                path=self.path,
                line=getattr(node, "lineno", 1),
                column=getattr(node, "col_offset", 0) + 1,
                end_line=getattr(node, "end_lineno", None),
                end_column=(getattr(node, "end_col_offset", 0) or 0) + 1,
                code=code,
                message=message,
            )
        )


def count_condition_operators(node: ast.AST) -> int:
    count = 0
    for child in _walk_expression(node):
        if isinstance(child, ast.BoolOp):
            count += max(len(child.values) - 1, 0)
        elif isinstance(child, ast.IfExp) or (isinstance(child, ast.UnaryOp) and isinstance(child.op, ast.Not)):
            count += 1
    return count


def count_readability_operators(node: ast.AST) -> int:
    count = 0
    for child in _walk_expression(node):
        if isinstance(child, ast.BoolOp):
            count += max(len(child.values) - 1, 0)
        elif isinstance(child, ast.BinOp):
            count += 1
        elif isinstance(child, ast.Compare):
            count += len(child.ops)
        elif isinstance(child, ast.IfExp) or (
            isinstance(child, ast.UnaryOp) and isinstance(child.op, (ast.Not, ast.Invert))
        ):
            count += 1
    return count


def _walk_expression(node: ast.AST) -> Iterable[ast.AST]:
    for child in ast.walk(node):
        if child is not node and isinstance(child, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        yield child


def _has_redundant_boolean_compare(node: ast.Compare) -> bool:
    comparisons = zip(node.ops, node.comparators, strict=False)
    return any(
        isinstance(operator, (ast.Eq, ast.NotEq))
        and isinstance(comparator, ast.Constant)
        and isinstance(comparator.value, bool)
        for operator, comparator in comparisons
    )


def _has_redundant_boolean_operand(node: ast.BoolOp) -> bool:
    constants = [value for value in node.values if isinstance(value, ast.Constant)]
    if isinstance(node.op, ast.And):
        return any(value.value is True for value in constants)
    if isinstance(node.op, ast.Or):
        return any(value.value is False for value in constants)
    return False


def _has_membership_search(node: ast.Compare) -> bool:
    return any(isinstance(operator, (ast.In, ast.NotIn)) for operator in node.ops)
