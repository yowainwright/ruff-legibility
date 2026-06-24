from __future__ import annotations

import ast
import fnmatch
import re
import shlex
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


@dataclass
class AliasCandidate:
    name: str
    target: str
    node: ast.AST
    references: int = 0


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
    "LEG008": Rule(
        "LEG008",
        "no-trivial-wrapper-functions",
        "Avoid functions that only forward their parameters to another call.",
    ),
    "LEG009": Rule(
        "LEG009",
        "prefer-early-return",
        "Avoid else branches after a branch that already exits.",
    ),
    "LEG010": Rule(
        "LEG010",
        "prefer-guard-clauses",
        "Prefer guard clauses over wrapping the main path in one large if block.",
    ),
    "LEG011": Rule(
        "LEG011",
        "max-array-chain-depth",
        "Limit consecutive collection-style method chains.",
    ),
    "LEG012": Rule(
        "LEG012",
        "no-computed-values",
        "Prefer named values before returning computed expressions or building dict values.",
    ),
    "LEG013": Rule(
        "LEG013",
        "no-hidden-side-effects",
        "Avoid mutations hidden inside expressions.",
    ),
    "LEG014": Rule(
        "LEG014",
        "no-standalone-array-mutations",
        "Avoid standalone list mutation calls when an expression is clearer.",
    ),
    "LEG015": Rule(
        "LEG015",
        "prefer-concat-object-assign",
        "Prefer explicit collection composition over starred literal unpacking.",
    ),
    "LEG016": Rule(
        "LEG016",
        "require-executable-shebang",
        "Require configured executable Python source files to start with a shebang.",
    ),
    "LEG017": Rule(
        "LEG017",
        "no-direct-python-bin-smoke",
        "Prefer smoke-testing installed Python package entry points.",
    ),
    "LEG018": Rule(
        "LEG018",
        "no-repeated-collection-search",
        "Avoid repeated scans over the same collection in one scope.",
    ),
    "LEG019": Rule(
        "LEG019",
        "no-single-use-renaming-alias",
        "Avoid aliases that only rename another value for one use.",
    ),
    "LEG020": Rule(
        "LEG020",
        "no-unnecessary-lambda",
        "Avoid lambdas that only forward their parameters to another callable.",
    ),
    "LEG021": Rule(
        "LEG021",
        "prefer-flat-comprehension",
        "Prefer a flat comprehension over map followed by flattening.",
    ),
    "LEG022": Rule(
        "LEG022",
        "no-identity-array-callback",
        "Avoid map/filter callbacks that keep every item unchanged.",
    ),
    "LEG023": Rule(
        "LEG023",
        "no-redundant-none-fallback",
        "Avoid fallback expressions that only return None unchanged.",
    ),
    "LEG024": Rule(
        "LEG024",
        "prefer-object-lookup",
        "Prefer set or dict lookups over long equality-or chains.",
    ),
    "LEG025": Rule(
        "LEG025",
        "require-filename-matches-dirname",
        "Require files in named subdirectories to match the directory name.",
    ),
    "LEG026": Rule(
        "LEG026",
        "no-mixed-filename-casing",
        "Avoid filenames that mix casing conventions.",
    ),
}

DEFAULT_SELECT = ("LEG",)
DEFAULT_ALLOWED_FILENAME_QUALIFIERS = (
    "constants",
    "helpers",
    "models",
    "schema",
    "schemas",
    "services",
    "test",
    "tests",
    "types",
    "utils",
)
DEFAULT_ALLOWED_STANDALONE_FILENAMES = (
    "__init__",
    "__main__",
    "conftest",
    "constants",
    "index",
    "types",
    "utils",
)
DEFAULT_DIRECT_BIN_ENTRY_PATTERNS = (
    "bin/*.py",
    "scripts/*.py",
    "src/**/__main__.py",
    "src/**/cli.py",
)
DEFAULT_EXECUTABLE_ENTRY_PATTERNS = ("bin/*.py", "scripts/*.py")
DEFAULT_EXECUTABLE_RUNTIMES = ("python", "python3")

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
ARRAY_CHAIN_METHODS = frozenset(
    {
        "exclude",
        "filter",
        "flat_map",
        "group_by",
        "limit",
        "map",
        "order_by",
        "select",
        "sort",
        "sorted",
        "where",
    }
)
ARRAY_MUTATING_METHOD_NAMES = ("append", "clear", "extend", "insert", "pop", "remove", "reverse", "sort")
OTHER_MUTATING_METHOD_NAMES = ("add", "discard", "setdefault", "update")
SEARCH_METHOD_NAMES = ("count", "index")
SUBPROCESS_METHOD_NAMES = ("call", "check_call", "check_output", "run", "Popen")

ARRAY_MUTATING_METHODS = frozenset(ARRAY_MUTATING_METHOD_NAMES)
MUTATING_METHODS = ARRAY_MUTATING_METHODS | frozenset(OTHER_MUTATING_METHOD_NAMES)
SEARCH_METHODS = frozenset(SEARCH_METHOD_NAMES)
SUBPROCESS_METHODS = frozenset(SUBPROCESS_METHOD_NAMES)


AliasScope = dict[str, AliasCandidate]


class LegibilityVisitor(ast.NodeVisitor):
    def __init__(self, *, path: Path, settings: Settings, source: str = "") -> None:
        self.path = path
        self.settings = settings
        self.source = source
        self.diagnostics: list[Diagnostic] = []
        self.control_depth = 0
        self.loop_depth = 0
        self.alias_scopes: list[AliasScope] = []

    def visit_Module(self, node: ast.Module) -> None:
        self._check_module_path_rules(node)
        self._enter_alias_scope()
        self._visit_many(node.body)
        self._leave_alias_scope()

    def visit_If(self, node: ast.If) -> None:
        self._check_condition(node.test)
        self._check_early_return(node)
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
        if self.settings.enabled("LEG006") and _has_redundant_boolean_ternary(node):
            self._add(
                node,
                "LEG006",
                "Avoid redundant boolean ternaries. Use the condition directly or invert it.",
            )

        should_check_none_fallback = self.settings.enabled("LEG023")
        has_redundant_none_ternary = _has_redundant_none_ternary(node)
        if should_check_none_fallback and has_redundant_none_ternary:
            self._add(
                node,
                "LEG023",
                "Avoid a fallback expression that only returns None unchanged.",
            )

        if self.settings.enabled("LEG004"):
            if _has_nested_ternary(node):
                self._add(
                    node,
                    "LEG004",
                    "Nested ternary detected. Extract named branches or use an if statement.",
                )

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
        self._track_alias_assignment(node)
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
            self._check_computed_return(node.value)
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        self._check_expression(node.value)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self._check_name(node.arg, node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_name(node.name, node)
        self._check_trivial_wrapper_function(node)
        self._check_guard_clause(node)
        self._enter_alias_scope()
        self.generic_visit(node)
        self._leave_alias_scope()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_name(node.name, node)
        self._check_guard_clause(node)
        self._enter_alias_scope()
        self.generic_visit(node)
        self._leave_alias_scope()

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._check_unnecessary_lambda(node)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self._track_alias_reference(node)

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
        self._check_repeated_membership_search(node)
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        if self.settings.enabled("LEG006") and _has_redundant_boolean_operand(node):
            self._add(
                node,
                "LEG006",
                "Avoid redundant boolean operands like `and True` or `or False`.",
            )
        self._check_redundant_none_boolop(node)
        self._check_object_lookup(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._check_call_chain_depth(node)
        self._check_direct_python_bin_smoke(node)
        self._check_hidden_side_effect(node)
        self._check_identity_callback(node)
        self._check_prefer_flat_comprehension(node)
        self._check_repeated_collection_search(node)
        self._check_standalone_array_mutation(node)
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        self._check_dict_unpacking(node)
        self._check_computed_dict_values(node)
        self.generic_visit(node)

    def visit_List(self, node: ast.List) -> None:
        self._check_starred_collection(node)
        self.generic_visit(node)

    def visit_Set(self, node: ast.Set) -> None:
        self._check_starred_collection(node)
        self.generic_visit(node)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        self._check_starred_collection(node)
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

    def _check_trivial_wrapper_function(self, node: ast.FunctionDef) -> None:
        if not self.settings.enabled("LEG008") or not _is_trivial_wrapper_function(node):
            return

        self._add(
            node,
            "LEG008",
            f"`{node.name}` only forwards its parameters to another call. Inline it or add meaningful behavior.",
        )

    def _check_early_return(self, node: ast.If) -> None:
        if not self.settings.enabled("LEG009"):
            return

        has_else_branch = bool(node.orelse)
        body_exits = _statement_list_always_exits(node.body)
        if not has_else_branch:
            return
        if not body_exits:
            return

        self._add(
            node.orelse[0],
            "LEG009",
            "Avoid an else branch after a branch that already exits. Return early instead.",
        )

    def _check_guard_clause(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if not self.settings.enabled("LEG010") or not _is_guard_clause_candidate(node):
            return

        only_statement = node.body[0]
        self._add(
            only_statement,
            "LEG010",
            "Prefer a guard clause instead of wrapping the main path in one large if block.",
        )

    def _check_module_path_rules(self, node: ast.Module) -> None:
        self._check_executable_shebang(node)
        self._check_filename_matches_dirname(node)
        self._check_mixed_filename_casing(node)

    def _check_executable_shebang(self, node: ast.Module) -> None:
        if not self.settings.enabled("LEG016"):
            return

        path_text = _relative_path(self.path)
        is_executable_entry = _matches_any_path_pattern(path_text, self.settings.executable_entry_patterns)
        if not is_executable_entry:
            return

        has_shebang = _has_allowed_shebang(self.source, self.settings.executable_runtimes)
        if has_shebang:
            return

        message = f"{path_text} is configured as executable but has no shebang."
        self._add(node, "LEG016", message)

    def _check_filename_matches_dirname(self, node: ast.Module) -> None:
        if not self.settings.enabled("LEG025"):
            return

        problem = _filename_dirname_problem(self.path, self.settings)
        if problem is None:
            return

        self._add(node, "LEG025", problem)

    def _check_mixed_filename_casing(self, node: ast.Module) -> None:
        if not self.settings.enabled("LEG026"):
            return

        name = _mixed_filename_casing_name(self.path)
        if name is None:
            return

        message = f'Filename "{name}" mixes casing conventions.'
        self._add(node, "LEG026", message)

    def _check_call_chain_depth(self, node: ast.Call) -> None:
        if not self.settings.enabled("LEG011"):
            return

        has_parent_chain = _has_parent_chain_call(node)
        if has_parent_chain:
            return

        methods = _chained_methods(node)
        count = len(methods)
        if count <= self.settings.max_array_chain_depth:
            return

        chain = ".".join(methods)
        message = f"Method chain has {count} steps (max {self.settings.max_array_chain_depth}): {chain}."
        self._add(node, "LEG011", message)

    def _check_computed_return(self, node: ast.expr) -> None:
        if not self.settings.enabled("LEG012"):
            return

        should_skip = _is_computed_return_skipped(node)
        if should_skip:
            return

        count = count_readability_operators(node)
        if count <= self.settings.max_computed_value_operators:
            return

        message = _computed_message("Return value", count, self.settings.max_computed_value_operators)
        self._add(node, "LEG012", message)

    def _check_computed_dict_values(self, node: ast.Dict) -> None:
        if not self.settings.enabled("LEG012"):
            return

        for value in node.values:
            self._check_computed_dict_value(value)

    def _check_computed_dict_value(self, node: ast.expr | None) -> None:
        if node is None:
            return

        should_skip = _is_computed_return_skipped(node)
        if should_skip:
            return

        count = count_readability_operators(node)
        if count <= self.settings.max_computed_value_operators:
            return

        message = _computed_message("Dict value", count, self.settings.max_computed_value_operators)
        self._add(node, "LEG012", message)

    def _check_hidden_side_effect(self, node: ast.Call) -> None:
        if not self.settings.enabled("LEG013"):
            return

        is_mutating = _is_mutating_call(node)
        if not is_mutating:
            return

        is_visible_statement = _is_standalone_expression(node)
        is_fresh_target = _is_fresh_mutation_target(node)
        if is_visible_statement:
            return
        if is_fresh_target:
            return

        message = "Avoid side effects inside expressions. Move this mutation into its own statement."
        self._add(node, "LEG013", message)

    def _check_standalone_array_mutation(self, node: ast.Call) -> None:
        if not self.settings.enabled("LEG014"):
            return

        is_array_mutation = _is_array_mutating_call(node)
        if not is_array_mutation:
            return

        is_standalone = _is_standalone_expression(node)
        is_fresh_target = _is_fresh_mutation_target(node)
        if not is_standalone:
            return
        if is_fresh_target:
            return

        method = _call_method_name(node)
        if method is None:
            method = "unknown"
        message = f"Avoid standalone .{method}() list mutation. Prefer a returned expression."
        self._add(node, "LEG014", message)

    def _check_dict_unpacking(self, node: ast.Dict) -> None:
        if not self.settings.enabled("LEG015"):
            return

        has_unpack = None in node.keys
        if not has_unpack:
            return

        message = "Prefer explicit dict composition over unpacking in a literal."
        self._add(node, "LEG015", message)

    def _check_starred_collection(self, node: ast.List | ast.Set | ast.Tuple) -> None:
        if not self.settings.enabled("LEG015"):
            return

        for element in node.elts:
            is_starred = isinstance(element, ast.Starred)
            if not is_starred:
                continue

            message = "Prefer explicit collection composition over starred literal unpacking."
            self._add(element, "LEG015", message)

    def _check_direct_python_bin_smoke(self, node: ast.Call) -> None:
        if not self.settings.enabled("LEG017"):
            return

        entry = _direct_python_entry(
            node,
            self.settings.direct_bin_entry_patterns,
            self.settings.executable_runtimes,
        )
        if entry is None:
            return

        message = f"Smoke tests should execute the installed package bin, not python {entry}."
        self._add(node, "LEG017", message)

    def _check_repeated_collection_search(self, node: ast.Call) -> None:
        if not self.settings.enabled("LEG018"):
            return

        is_search = _is_search_call(node)
        if not is_search:
            return

        key = _search_call_key(node)
        if key is None:
            return

        self._track_repeated_search(node, key)

    def _check_repeated_membership_search(self, node: ast.Compare) -> None:
        if not self.settings.enabled("LEG018"):
            return

        for key in _membership_search_keys(node):
            self._track_repeated_search(node, key)

    def _check_unnecessary_lambda(self, node: ast.Lambda) -> None:
        if not self.settings.enabled("LEG020"):
            return

        is_forwarding = _is_forwarding_lambda(node)
        if not is_forwarding:
            return

        self._add(node, "LEG020", "Pass the callable directly instead of wrapping it in a lambda.")

    def _check_identity_callback(self, node: ast.Call) -> None:
        if not self.settings.enabled("LEG022"):
            return

        message = _identity_callback_message(node)
        if message is None:
            return

        self._add(node, "LEG022", message)

    def _check_prefer_flat_comprehension(self, node: ast.Call) -> None:
        if not self.settings.enabled("LEG021"):
            return

        is_map_flattening = _is_map_followed_by_flatten(node)
        if not is_map_flattening:
            return

        message = "Prefer a flat comprehension over map followed by chain.from_iterable."
        self._add(node, "LEG021", message)

    def _check_redundant_none_boolop(self, node: ast.BoolOp) -> None:
        if not self.settings.enabled("LEG023"):
            return

        has_redundant_fallback = _has_redundant_none_boolop(node)
        if not has_redundant_fallback:
            return

        message = "Avoid `or None`; the expression already falls back to None."
        self._add(node, "LEG023", message)

    def _check_object_lookup(self, node: ast.BoolOp) -> None:
        if not self.settings.enabled("LEG024"):
            return

        is_or_chain = isinstance(node.op, ast.Or)
        if not is_or_chain:
            return

        if _has_parent_or(node):
            return

        key = _lookup_chain_key(node, self.settings.min_object_lookup_chain_length)
        if key is None:
            return

        message = f"Replace repeated `{key}` equality checks with a set or dict lookup."
        self._add(node, "LEG024", message)

    def _enter_alias_scope(self) -> None:
        self.alias_scopes = self.alias_scopes + [{}]

    def _leave_alias_scope(self) -> None:
        scope = self.alias_scopes[-1]
        self.alias_scopes = self.alias_scopes[:-1]
        if not self.settings.enabled("LEG019"):
            return

        for candidate in scope.values():
            if candidate.references == 1:
                message = _alias_message(candidate)
                self._add(candidate.node, "LEG019", message)

    def _track_alias_assignment(self, node: ast.Assign) -> None:
        if not self.settings.enabled("LEG019"):
            return
        if not self.alias_scopes:
            return

        candidate = _alias_candidate(node)
        if candidate is None:
            return

        self.alias_scopes[-1][candidate.name] = candidate

    def _track_alias_reference(self, node: ast.Name) -> None:
        if not self.alias_scopes:
            return
        if not isinstance(node.ctx, ast.Load):
            return

        candidate = _find_alias_candidate(self.alias_scopes, node.id)
        if candidate is not None:
            candidate.references += 1

    def _track_repeated_search(self, node: ast.AST, key: str) -> None:
        if not self.alias_scopes:
            return

        scope = self.alias_scopes[-1]
        seen_key = f"search:{key}"
        if seen_key not in scope:
            scope[seen_key] = AliasCandidate(seen_key, key, node, references=-1)
            return

        message = f"`{key}` is searched multiple times in this scope. Build a named lookup."
        self._add(node, "LEG018", message)

    def _add(self, node: ast.AST, code: str, message: str) -> None:
        if not self.settings.enabled(code):
            return

        from .core import Diagnostic

        diagnostic = Diagnostic(
            path=self.path,
            line=getattr(node, "lineno", 1),
            column=getattr(node, "col_offset", 0) + 1,
            end_line=getattr(node, "end_lineno", None),
            end_column=(getattr(node, "end_col_offset", 0) or 0) + 1,
            code=code,
            message=message,
        )
        self.diagnostics = self.diagnostics + [diagnostic]


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


def _parent(node: ast.AST) -> ast.AST | None:
    parent = getattr(node, "_legibility_parent", None)
    if isinstance(parent, ast.AST):
        return parent
    return None


def _call_method_name(node: ast.Call) -> str | None:
    if not isinstance(node.func, ast.Attribute):
        return None
    return node.func.attr


def _call_object(node: ast.Call) -> ast.expr | None:
    if not isinstance(node.func, ast.Attribute):
        return None
    return node.func.value


def _stable_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _stable_name(node.value)
        if owner is None:
            return None
        return f"{owner}.{node.attr}"
    return None


def _has_parent_chain_call(node: ast.Call) -> bool:
    parent = _parent(node)
    if not isinstance(parent, ast.Attribute):
        return False
    grandparent = _parent(parent)
    return isinstance(grandparent, ast.Call)


def _chained_methods(node: ast.AST) -> list[str]:
    if not isinstance(node, ast.Call):
        return []

    method = _call_method_name(node)
    if method not in ARRAY_CHAIN_METHODS:
        return []

    previous_methods = _chained_methods(_call_object(node))
    return previous_methods + [method]


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


def _has_redundant_boolean_ternary(node: ast.IfExp) -> bool:
    has_boolean_body = isinstance(node.body, ast.Constant) and isinstance(node.body.value, bool)
    has_boolean_else = isinstance(node.orelse, ast.Constant) and isinstance(node.orelse.value, bool)
    has_inverted_branches = has_boolean_body and has_boolean_else and node.body.value != node.orelse.value
    return has_inverted_branches


def _has_nested_ternary(node: ast.IfExp) -> bool:
    child_expressions = (node.test, node.body, node.orelse)
    return any(_contains_ternary(child) for child in child_expressions)


def _contains_ternary(node: ast.AST) -> bool:
    return any(isinstance(child, ast.IfExp) for child in ast.walk(node) if child is not node)


def _has_redundant_none_ternary(node: ast.IfExp) -> bool:
    value = _none_passthrough_value(node)
    return value is not None


def _none_passthrough_value(node: ast.IfExp) -> str | None:
    if isinstance(node.orelse, ast.Constant) and node.orelse.value is None:
        return _none_guarded_name(node.test, node.body, positive=True)
    if isinstance(node.body, ast.Constant) and node.body.value is None:
        return _none_guarded_name(node.test, node.orelse, positive=False)
    return None


def _none_guarded_name(test: ast.expr, value: ast.expr, *, positive: bool) -> str | None:
    if not isinstance(value, ast.Name):
        return None

    expected = _is_not_none_compare(test) if positive else _is_none_compare(test)
    if expected != value.id:
        return None
    return value.id


def _is_none_compare(node: ast.expr) -> str | None:
    return _single_none_compare_name(node, ast.Is)


def _is_not_none_compare(node: ast.expr) -> str | None:
    return _single_none_compare_name(node, ast.IsNot)


def _single_none_compare_name(node: ast.expr, operator_type: type[ast.cmpop]) -> str | None:
    if not isinstance(node, ast.Compare):
        return None
    if len(node.ops) != 1 or len(node.comparators) != 1:
        return None
    if not isinstance(node.ops[0], operator_type):
        return None
    if not isinstance(node.left, ast.Name):
        return None
    comparator = node.comparators[0]
    if not isinstance(comparator, ast.Constant) or comparator.value is not None:
        return None
    return node.left.id


def _has_membership_search(node: ast.Compare) -> bool:
    return any(isinstance(operator, (ast.In, ast.NotIn)) for operator in node.ops)


def _computed_message(label: str, count: int, max_count: int) -> str:
    return f"{label} has {count} computed operators (max {max_count}). Extract it into a named value."


def _is_computed_return_skipped(node: ast.expr) -> bool:
    return isinstance(node, (ast.Constant, ast.Name, ast.Call, ast.Dict, ast.Lambda))


def _is_mutating_call(node: ast.Call) -> bool:
    method = _call_method_name(node)
    return method in MUTATING_METHODS


def _is_array_mutating_call(node: ast.Call) -> bool:
    method = _call_method_name(node)
    return method in ARRAY_MUTATING_METHODS


def _is_standalone_expression(node: ast.AST) -> bool:
    return isinstance(_parent(node), ast.Expr)


def _is_fresh_mutation_target(node: ast.Call) -> bool:
    target = _call_object(node)
    return isinstance(target, (ast.List, ast.Dict, ast.Set, ast.Call))


def _direct_python_entry(
    node: ast.Call,
    patterns: tuple[str, ...],
    runtimes: tuple[str, ...],
) -> str | None:
    if not _is_subprocess_call(node):
        return None

    parts = _command_parts(node)
    if not parts:
        return None

    command = parts[0]
    if not _is_python_runtime(command, runtimes):
        return None

    return _first_direct_entry(parts[1:], patterns)


def _is_subprocess_call(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Name):
        return _is_subprocess_method(node.func.id)
    if not isinstance(node.func, ast.Attribute):
        return False
    owner = _stable_name(node.func.value)
    if owner != "subprocess":
        return False
    return _is_subprocess_method(node.func.attr)


def _is_subprocess_method(name: str) -> bool:
    return name in SUBPROCESS_METHODS


def _command_parts(node: ast.Call) -> list[str]:
    if not node.args:
        return []

    first_arg = node.args[0]
    sequence_parts = _literal_string_sequence(first_arg)
    if sequence_parts:
        return sequence_parts

    command_text = _literal_string(first_arg)
    if command_text is None:
        return []
    return shlex.split(command_text)


def _literal_string_sequence(node: ast.AST) -> list[str]:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return []

    values = [_literal_string(element) for element in node.elts]
    if not all(value is not None for value in values):
        return []
    return [value for value in values if value is not None]


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_python_runtime(command: str, runtimes: tuple[str, ...]) -> bool:
    command_name = command.rsplit("/", maxsplit=1)[-1]
    return command_name in runtimes


def _first_direct_entry(parts: list[str], patterns: tuple[str, ...]) -> str | None:
    for part in parts:
        is_flag = part.startswith("-")
        if is_flag:
            continue

        normalized = part.removeprefix("./")
        if _matches_any_path_pattern(normalized, patterns):
            return normalized
    return None


def _is_search_call(node: ast.Call) -> bool:
    method = _call_method_name(node)
    return method in SEARCH_METHODS


def _search_call_key(node: ast.Call) -> str | None:
    target = _stable_name(_call_object(node))
    method = _call_method_name(node)
    if target is None:
        return None
    if method is None:
        return None
    return f"{target}.{method}"


def _membership_search_keys(node: ast.Compare) -> list[str]:
    comparisons = zip(node.ops, node.comparators, strict=False)
    keys = [
        _membership_search_key(comparator)
        for operator, comparator in comparisons
        if isinstance(operator, (ast.In, ast.NotIn))
    ]
    return [key for key in keys if key is not None]


def _membership_search_key(node: ast.AST) -> str | None:
    collection = _stable_name(node)
    if collection is None:
        return None
    return f"{collection}.membership"


def _alias_candidate(node: ast.Assign) -> AliasCandidate | None:
    if len(node.targets) != 1:
        return None

    target = node.targets[0]
    if not isinstance(target, ast.Name):
        return None

    source = _stable_name(node.value)
    if source is None:
        return None
    if source == target.id:
        return None

    return AliasCandidate(target.id, source, node)


def _find_alias_candidate(scopes: list[AliasScope], name: str) -> AliasCandidate | None:
    for scope in reversed(scopes):
        candidate = scope.get(name)
        if candidate is not None:
            return candidate
    return None


def _alias_message(candidate: AliasCandidate) -> str:
    return f"`{candidate.name}` only renames `{candidate.target}` for one use. Use the original value."


def _is_forwarding_lambda(node: ast.Lambda) -> bool:
    parameter_names = _simple_lambda_parameter_names(node)
    if parameter_names is None:
        return False
    if not isinstance(node.body, ast.Call):
        return False
    if node.body.keywords:
        return False
    if len(node.body.args) != len(parameter_names):
        return False
    return _arguments_match_names(node.body.args, parameter_names)


def _simple_lambda_parameter_names(node: ast.Lambda) -> tuple[str, ...] | None:
    arguments = node.args
    has_variadic = arguments.vararg is not None or arguments.kwarg is not None
    has_keyword_only = bool(arguments.kwonlyargs)
    has_defaults = bool(arguments.defaults or arguments.kw_defaults)
    if has_variadic:
        return None
    if has_keyword_only:
        return None
    if has_defaults:
        return None
    return tuple(argument.arg for argument in arguments.args)


def _arguments_match_names(arguments: list[ast.expr], names: tuple[str, ...]) -> bool:
    pairs = zip(arguments, names, strict=True)
    return all(isinstance(argument, ast.Name) and argument.id == name for argument, name in pairs)


def _identity_callback_message(node: ast.Call) -> str | None:
    function_name = _callable_name(node.func)
    if function_name == "map":
        return _identity_map_message(node)
    if function_name == "filter":
        return _identity_filter_message(node)
    return None


def _identity_map_message(node: ast.Call) -> str | None:
    callback = _first_lambda_arg(node)
    if callback is None:
        return None
    parameter_names = _simple_lambda_parameter_names(callback)
    if not parameter_names:
        return None
    if isinstance(callback.body, ast.Name) and callback.body.id == parameter_names[0]:
        return "Avoid map callbacks that return the item unchanged."
    return None


def _identity_filter_message(node: ast.Call) -> str | None:
    callback = _first_lambda_arg(node)
    if callback is None:
        return None
    if isinstance(callback.body, ast.Constant) and callback.body.value is True:
        return "Avoid filter callbacks that always keep every item."
    return None


def _first_lambda_arg(node: ast.Call) -> ast.Lambda | None:
    if not node.args:
        return None
    callback = node.args[0]
    if isinstance(callback, ast.Lambda):
        return callback
    return None


def _callable_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_map_followed_by_flatten(node: ast.Call) -> bool:
    function_name = _stable_name(node.func)
    if function_name not in {"chain.from_iterable", "itertools.chain.from_iterable"}:
        return False
    if not node.args:
        return False
    first_arg = node.args[0]
    if not isinstance(first_arg, ast.Call):
        return False
    return _callable_name(first_arg.func) == "map"


def _has_redundant_none_boolop(node: ast.BoolOp) -> bool:
    if not isinstance(node.op, ast.Or):
        return False
    if len(node.values) != 2:
        return False
    fallback = node.values[1]
    is_constant = isinstance(fallback, ast.Constant)
    if not is_constant:
        return False
    return fallback.value is None


def _has_parent_or(node: ast.BoolOp) -> bool:
    parent = _parent(node)
    is_parent_boolop = isinstance(parent, ast.BoolOp)
    if not is_parent_boolop:
        return False
    return isinstance(parent.op, ast.Or)


def _lookup_chain_key(node: ast.BoolOp, minimum: int) -> str | None:
    parts = _lookup_parts(node)
    if len(parts) < minimum:
        return None

    first_part = parts[0]
    checks_same_key = all(part == first_part for part in parts)
    if not checks_same_key:
        return None
    return first_part


def _lookup_parts(node: ast.AST) -> list[str]:
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return [part for value in node.values for part in _lookup_parts(value)]

    part = _lookup_compare_key(node)
    if part is None:
        return []
    return [part]


def _lookup_compare_key(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Compare):
        return None
    if len(node.ops) != 1 or len(node.comparators) != 1:
        return None
    if not isinstance(node.ops[0], (ast.Eq, ast.Is)):
        return None
    return _literal_lookup_key(node.left, node.comparators[0])


def _literal_lookup_key(left: ast.expr, right: ast.expr) -> str | None:
    left_name = _stable_name(left)
    right_name = _stable_name(right)
    if left_name is not None and _is_literal_lookup_value(right):
        return left_name
    if right_name is not None and _is_literal_lookup_value(left):
        return right_name
    return None


def _is_literal_lookup_value(node: ast.AST) -> bool:
    if not isinstance(node, ast.Constant):
        return False
    return isinstance(node.value, str | int | bool | type(None))


def _relative_path(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        return path.as_posix()
    return relative.as_posix()


def _matches_any_path_pattern(path_text: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path_text, pattern) for pattern in patterns)


def _has_allowed_shebang(source: str, runtimes: tuple[str, ...]) -> bool:
    first_line = source.splitlines()[0] if source.splitlines() else ""
    if not first_line.startswith("#!"):
        return False
    return any(_shebang_uses_runtime(first_line, runtime) for runtime in runtimes)


def _shebang_uses_runtime(line: str, runtime: str) -> bool:
    command = line[2:].strip()
    if command == runtime:
        return True
    if command.endswith(f"/{runtime}"):
        return True
    env_command = f"/usr/bin/env {runtime}"
    if command == env_command:
        return True
    return command.startswith(f"{env_command} ")


def _filename_dirname_problem(path: Path, settings: Settings) -> str | None:
    parts = Path(_relative_path(path)).parts
    parent_depth = len(parts) - 1
    if parent_depth < settings.min_dirname_match_depth:
        return None

    parent_dir = parts[-2]
    file_name = _filename_without_last_suffix(path)
    base_name, qualifiers = _filename_parts(file_name)
    if base_name in settings.allowed_standalone_filenames:
        return None
    if base_name != parent_dir:
        return f'Filename "{file_name}" does not match parent directory "{parent_dir}".'
    return _unknown_qualifier_problem(qualifiers, file_name, settings)


def _filename_without_last_suffix(path: Path) -> str:
    name = path.name[1:] if path.name.startswith(".") else path.name
    if not path.suffix:
        return name
    return name[: -len(path.suffix)]


def _filename_parts(file_name: str) -> tuple[str, list[str]]:
    parts = file_name.split(".")
    base_name = parts[0]
    qualifiers = parts[1:]
    return base_name, qualifiers


def _unknown_qualifier_problem(qualifiers: list[str], file_name: str, settings: Settings) -> str | None:
    for qualifier in qualifiers:
        if qualifier not in settings.allowed_filename_qualifiers:
            allowed = ", ".join(settings.allowed_filename_qualifiers)
            return f'Qualifier "{qualifier}" in "{file_name}" is not in the allowed list: {allowed}.'
    return None


def _mixed_filename_casing_name(path: Path) -> str | None:
    name = path.name[1:] if path.name.startswith(".") else path.name
    base_name = name.split(".", maxsplit=1)[0]
    has_hyphen = base_name.find("-") >= 0
    has_underscore = base_name.find("_") >= 0
    has_upper = any(character.isupper() for character in base_name)
    has_lower = any(character.islower() for character in base_name)
    mixes_hyphen_upper = has_hyphen and has_upper
    mixes_underscore_case = has_underscore and has_upper and has_lower
    mixes_separators = has_hyphen and has_underscore
    if mixes_hyphen_upper or mixes_underscore_case or mixes_separators:
        return base_name
    return None


def _is_trivial_wrapper_function(node: ast.FunctionDef) -> bool:
    if node.decorator_list:
        return False

    parameter_names = _simple_parameter_names(node)
    if parameter_names is None:
        return False

    if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
        return False

    returned = node.body[0].value
    if not isinstance(returned, ast.Call) or returned.keywords:
        return False

    callee = _call_name(returned)
    if callee is None or callee == node.name:
        return False

    if len(returned.args) != len(parameter_names):
        return False

    return all(
        isinstance(argument, ast.Name) and argument.id == name
        for argument, name in zip(returned.args, parameter_names, strict=True)
    )


def _simple_parameter_names(node: ast.FunctionDef) -> tuple[str, ...] | None:
    arguments = node.args
    has_variadic_parameters = arguments.vararg or arguments.kwarg
    has_keyword_only_parameters = bool(arguments.kwonlyargs)
    has_default_values = bool(arguments.defaults or arguments.kw_defaults)
    if has_variadic_parameters or has_keyword_only_parameters or has_default_values:
        return None

    positional_arguments = arguments.posonlyargs + arguments.args
    return tuple(argument.arg for argument in positional_arguments)


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _statement_list_always_exits(statements: list[ast.stmt]) -> bool:
    if not statements:
        return False
    return _statement_always_exits(statements[-1])


def _statement_always_exits(statement: ast.stmt) -> bool:
    if isinstance(statement, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
        return True
    if isinstance(statement, ast.If) and statement.orelse:
        return _statement_list_always_exits(statement.body) and _statement_list_always_exits(statement.orelse)
    return False


def _is_guard_clause_candidate(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if len(node.body) != 1:
        return False

    only_statement = node.body[0]
    if not isinstance(only_statement, ast.If) or only_statement.orelse:
        return False

    if len(only_statement.body) < 2:
        return False

    return not _statement_list_always_exits(only_statement.body)
