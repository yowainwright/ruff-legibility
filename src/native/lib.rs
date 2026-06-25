use pyo3::prelude::*;
use ruff_python_ast::{
    BoolOp, CmpOp, ExceptHandler, Expr, ModModule, Parameters, Stmt, StmtFunctionDef, UnaryOp,
};
use ruff_python_parser::parse_module;
use ruff_source_file::SourceFileBuilder;
use ruff_text_size::Ranged;
use serde::{Deserialize, Serialize};

type JsonResult = PyResult<String>;
type ModuleResult = Result<ModModule, String>;
type Names = Vec<String>;
type OptionalBool = Option<bool>;
type OptionalNames = Option<Names>;
type UnitResult = PyResult<()>;
type PyModuleRef<'py> = Bound<'py, PyModule>;
type ExprRefs<'a> = Vec<&'a Expr>;
type DiagnosticKey = (usize, usize, &'static str);

const ARRAY_CHAIN_METHODS: &[&str] = &[
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
];

const BOOLEAN_PREFIXES: &[&str] = &[
    "is", "are", "was", "were", "has", "have", "had", "can", "could", "should", "will",
    "would", "did", "does",
];

const NEGATIVE_PREFIXES: &[&str] = &["not_", "no_", "without_"];

#[derive(Deserialize)]
struct Settings {
    select: Vec<String>,
    ignore: Vec<String>,
    max_expression_operators: usize,
    max_if_operators: usize,
    max_ternary_operators: usize,
    max_control_flow_depth: usize,
    max_array_chain_depth: usize,
}

#[derive(Serialize)]
struct Diagnostic {
    filename: String,
    line: usize,
    column: usize,
    end_line: usize,
    end_column: usize,
    code: &'static str,
    message: String,
}

#[pyfunction]
fn check_source_json(source: &str, path: &str, settings_json: &str) -> JsonResult {
    let settings = match serde_json::from_str(settings_json) {
        Ok(settings) => settings,
        Err(error) => return Err(value_error(error.to_string())),
    };
    let parsed = match parse_source(source, path) {
        Ok(parsed) => parsed,
        Err(json) => return Ok(json),
    };
    let mut visitor = Visitor::new(path, source, settings);
    visitor.visit_module(&parsed);
    visitor.sort();
    json_result(&visitor.diagnostics)
}

#[pymodule]
fn _native(m: &PyModuleRef) -> UnitResult {
    let function = match wrap_pyfunction!(check_source_json, m) {
        Ok(function) => function,
        Err(error) => return Err(error),
    };
    m.add_function(function)
}

fn parse_source(source: &str, path: &str) -> ModuleResult {
    match parse_module(source) {
        Ok(parsed) => Ok(parsed.into_syntax()),
        Err(error) => {
            let message = format!("SyntaxError: {error}");
            let diagnostic = diagnostic_at_start(path, "LEG999", message);
            match serde_json::to_string(&[diagnostic]) {
                Ok(json) => Err(json),
                Err(error) => Err(error.to_string()),
            }
        }
    }
}

fn diagnostic_at_start(path: &str, code: &'static str, message: String) -> Diagnostic {
    Diagnostic {
        filename: path.to_owned(),
        line: 1,
        column: 1,
        end_line: 1,
        end_column: 1,
        code,
        message,
    }
}

fn json_result(diagnostics: &[Diagnostic]) -> JsonResult {
    match serde_json::to_string(diagnostics) {
        Ok(json) => Ok(json),
        Err(error) => Err(value_error(error.to_string())),
    }
}

fn value_error(message: String) -> PyErr {
    pyo3::exceptions::PyValueError::new_err(message)
}

struct Visitor {
    path: String,
    source_file: ruff_source_file::SourceFile,
    settings: Settings,
    diagnostics: Vec<Diagnostic>,
    control_depth: usize,
    loop_depth: usize,
}

impl Visitor {
    fn new(path: &str, source: &str, settings: Settings) -> Self {
        let source_file = SourceFileBuilder::new(path.to_owned(), source.to_owned()).finish();
        Self {
            path: path.to_owned(),
            source_file,
            settings,
            diagnostics: Vec::new(),
            control_depth: 0,
            loop_depth: 0,
        }
    }

    fn visit_module(&mut self, module: &ModModule) {
        self.visit_body(&module.body);
    }

    fn visit_body(&mut self, body: &[Stmt]) {
        for stmt in body {
            self.visit_stmt(stmt);
        }
    }

    fn visit_stmt(&mut self, stmt: &Stmt) {
        match stmt {
            Stmt::FunctionDef(function) => self.visit_function(function),
            Stmt::ClassDef(class_def) => self.visit_body(&class_def.body),
            Stmt::Return(return_stmt) => self.visit_return(return_stmt.value.as_deref()),
            Stmt::Assign(assign) => self.visit_assign(&assign.targets, &assign.value),
            Stmt::AnnAssign(assign) => self.visit_ann_assign(&assign.target, assign.value.as_deref()),
            Stmt::For(for_stmt) => self.visit_loop(stmt, &for_stmt.body, &for_stmt.orelse),
            Stmt::While(while_stmt) => {
                self.visit_while(stmt, &while_stmt.test, &while_stmt.body, &while_stmt.orelse);
            }
            Stmt::If(if_stmt) => self.visit_if(if_stmt),
            Stmt::With(with_stmt) => self.visit_control(stmt, &with_stmt.body, &[]),
            Stmt::Try(try_stmt) => self.visit_try(stmt, try_stmt),
            Stmt::Match(match_stmt) => self.visit_match(stmt, match_stmt),
            Stmt::Expr(expr_stmt) => self.visit_expr_checked(&expr_stmt.value),
            Stmt::Raise(raise_stmt) => self.visit_optional_expr(raise_stmt.exc.as_deref()),
            Stmt::Assert(assert_stmt) => self.visit_expr(&assert_stmt.test),
            _ => {}
        }
    }

    fn visit_function(&mut self, function: &StmtFunctionDef) {
        self.check_name(function.name.as_str(), function);
        self.check_trivial_wrapper(function);
        self.check_guard_clause(function);
        self.visit_parameters(&function.parameters);
        self.visit_body(&function.body);
    }

    fn visit_parameters(&mut self, parameters: &Parameters) {
        for parameter in parameters.iter() {
            self.check_name(parameter.name().as_str(), parameter.name());
        }
    }

    fn visit_assign(&mut self, targets: &[Expr], value: &Expr) {
        self.check_expression(value);
        for target in targets {
            self.check_condition_target(target);
            self.visit_expr(target);
        }
        self.visit_expr(value);
    }

    fn visit_ann_assign(&mut self, target: &Expr, value: Option<&Expr>) {
        if let Some(value) = value {
            self.check_expression(value);
            self.visit_expr(value);
        }
        self.check_condition_target(target);
        self.visit_expr(target);
    }

    fn visit_return(&mut self, value: Option<&Expr>) {
        if let Some(value) = value {
            self.check_expression(value);
            self.visit_expr(value);
        }
    }

    fn visit_while(&mut self, node: &Stmt, test: &Expr, body: &[Stmt], orelse: &[Stmt]) {
        self.check_condition(test);
        self.visit_loop(node, body, orelse);
    }

    fn visit_if(&mut self, node: &ruff_python_ast::StmtIf) {
        self.check_condition(&node.test);
        self.check_early_return(node);
        self.enter_control(node);
        self.visit_body(&node.body);
        for clause in &node.elif_else_clauses {
            if let Some(test) = &clause.test {
                self.check_condition(test);
            }
            self.visit_body(&clause.body);
        }
        self.leave_control();
    }

    fn visit_loop(&mut self, node: &Stmt, body: &[Stmt], orelse: &[Stmt]) {
        if self.loop_depth > 0 {
            self.add_nested_loop(node);
        }
        self.loop_depth += 1;
        self.visit_control(node, body, orelse);
        self.loop_depth -= 1;
    }

    fn visit_control(&mut self, node: &impl Ranged, body: &[Stmt], orelse: &[Stmt]) {
        self.enter_control(node);
        self.visit_body(body);
        self.visit_body(orelse);
        self.leave_control();
    }

    fn visit_try(&mut self, node: &Stmt, try_stmt: &ruff_python_ast::StmtTry) {
        self.enter_control(node);
        self.visit_body(&try_stmt.body);
        for handler in &try_stmt.handlers {
            let ExceptHandler::ExceptHandler(handler) = handler;
            self.visit_body(&handler.body);
        }
        self.visit_body(&try_stmt.orelse);
        self.visit_body(&try_stmt.finalbody);
        self.leave_control();
    }

    fn visit_match(&mut self, node: &Stmt, match_stmt: &ruff_python_ast::StmtMatch) {
        self.enter_control(node);
        for case in &match_stmt.cases {
            self.visit_body(&case.body);
        }
        self.leave_control();
    }

    fn visit_expr_checked(&mut self, expr: &Expr) {
        self.check_expression(expr);
        self.visit_expr(expr);
    }

    fn visit_expr(&mut self, expr: &Expr) {
        self.visit_expr_with_chain_context(expr, false);
    }

    fn visit_expr_with_chain_context(&mut self, expr: &Expr, has_parent_chain: bool) {
        match expr {
            Expr::If(if_expr) => self.visit_conditional_expr(if_expr),
            Expr::Named(named) => self.visit_named_expr(named),
            Expr::Compare(compare) => self.visit_compare(compare),
            Expr::BoolOp(bool_op) => self.visit_bool_op(bool_op),
            Expr::Call(call) => self.visit_call(call, has_parent_chain),
            Expr::BinOp(bin_op) => {
                self.visit_expr(&bin_op.left);
                self.visit_expr(&bin_op.right);
            }
            Expr::UnaryOp(unary_op) => self.visit_expr(&unary_op.operand),
            Expr::Attribute(attribute) => self.visit_expr(&attribute.value),
            Expr::Subscript(subscript) => {
                self.visit_expr(&subscript.value);
                self.visit_expr(&subscript.slice);
            }
            Expr::Starred(starred) => self.visit_expr(&starred.value),
            Expr::List(list) => self.visit_many_exprs(&list.elts),
            Expr::Tuple(tuple) => self.visit_many_exprs(&tuple.elts),
            Expr::Set(set) => self.visit_many_exprs(&set.elts),
            Expr::Dict(dict) => self.visit_dict(dict),
            Expr::ListComp(comp) => self.visit_comprehension(&comp.elt, &comp.generators),
            Expr::SetComp(comp) => self.visit_comprehension(&comp.elt, &comp.generators),
            Expr::Generator(comp) => self.visit_comprehension(&comp.elt, &comp.generators),
            Expr::DictComp(comp) => self.visit_dict_comprehension(comp),
            Expr::Await(await_expr) => self.visit_expr(&await_expr.value),
            Expr::Yield(yield_expr) => self.visit_optional_expr(yield_expr.value.as_deref()),
            Expr::YieldFrom(yield_expr) => self.visit_expr(&yield_expr.value),
            Expr::Slice(slice) => self.visit_slice(slice),
            _ => {}
        }
    }

    fn visit_conditional_expr(&mut self, node: &ruff_python_ast::ExprIf) {
        self.check_redundant_boolean_conditional(node);
        self.check_complex_conditional_expr(node);
        self.visit_expr(&node.test);
        self.visit_expr(&node.body);
        self.visit_expr(&node.orelse);
    }

    fn visit_named_expr(&mut self, node: &ruff_python_ast::ExprNamed) {
        self.check_condition_target(&node.target);
        self.check_expression(&node.value);
        self.visit_expr(&node.target);
        self.visit_expr(&node.value);
    }

    fn visit_compare(&mut self, node: &ruff_python_ast::ExprCompare) {
        self.check_redundant_boolean_compare(node);
        self.check_membership_search(node);
        self.visit_expr(&node.left);
        self.visit_many_exprs(&node.comparators);
    }

    fn visit_bool_op(&mut self, node: &ruff_python_ast::ExprBoolOp) {
        self.check_redundant_boolean_operand(node);
        self.visit_many_exprs(&node.values);
    }

    fn visit_call(&mut self, node: &ruff_python_ast::ExprCall, has_parent_chain: bool) {
        if has_parent_chain == false {
            self.check_call_chain(node);
        }
        self.visit_call_func(&node.func);
        self.visit_many_exprs(&node.arguments.args);
        for keyword in &node.arguments.keywords {
            self.visit_expr(&keyword.value);
        }
    }

    fn visit_call_func(&mut self, func: &Expr) {
        if let Expr::Attribute(attribute) = func {
            self.visit_expr_with_chain_context(&attribute.value, true);
            return;
        }
        self.visit_expr(func);
    }

    fn visit_dict(&mut self, dict: &ruff_python_ast::ExprDict) {
        for item in &dict.items {
            if let Some(key) = &item.key {
                self.visit_expr(key);
            }
            self.visit_expr(&item.value);
        }
    }

    fn visit_comprehension(&mut self, element: &Expr, generators: &[ruff_python_ast::Comprehension]) {
        self.visit_expr(element);
        for generator in generators {
            self.visit_expr(&generator.target);
            self.visit_expr(&generator.iter);
            self.visit_many_exprs(&generator.ifs);
        }
    }

    fn visit_dict_comprehension(&mut self, comp: &ruff_python_ast::ExprDictComp) {
        if let Some(key) = &comp.key {
            self.visit_expr(key);
        }
        self.visit_comprehension(&comp.value, &comp.generators);
    }

    fn visit_slice(&mut self, slice: &ruff_python_ast::ExprSlice) {
        self.visit_optional_expr(slice.lower.as_deref());
        self.visit_optional_expr(slice.upper.as_deref());
        self.visit_optional_expr(slice.step.as_deref());
    }

    fn visit_optional_expr(&mut self, expr: Option<&Expr>) {
        if let Some(expr) = expr {
            self.visit_expr(expr);
        }
    }

    fn visit_many_exprs(&mut self, expressions: &[Expr]) {
        for expression in expressions {
            self.visit_expr(expression);
        }
    }

    fn check_expression(&mut self, expression: &Expr) {
        if self.settings.enabled("LEG001") == false {
            return;
        }
        if is_simple_expr(expression) {
            return;
        }
        let count = count_readability_operators(expression);
        if count <= self.settings.max_expression_operators {
            return;
        }
        let message = expression_message(count, self.settings.max_expression_operators);
        self.add(expression, "LEG001", &message);
    }

    fn check_condition(&mut self, expression: &Expr) {
        if self.settings.enabled("LEG002") == false {
            return;
        }
        let count = count_condition_operators(expression);
        if count <= self.settings.max_if_operators {
            return;
        }
        let message = condition_message(count, self.settings.max_if_operators);
        self.add(expression, "LEG002", &message);
    }

    fn check_complex_conditional_expr(&mut self, node: &ruff_python_ast::ExprIf) {
        if self.settings.enabled("LEG004") == false {
            return;
        }
        if has_nested_conditional_expr(node) {
            self.add(node, "LEG004", "Nested conditional expression detected. Extract named branches or use an if statement.");
        }
        let wrapped = Expr::If(node.clone());
        let count = count_readability_operators(&wrapped);
        if count <= self.settings.max_ternary_operators {
            return;
        }
        let message = conditional_expr_message(count, self.settings.max_ternary_operators);
        self.add(node, "LEG004", &message);
    }

    fn check_redundant_boolean_compare(&mut self, node: &ruff_python_ast::ExprCompare) {
        if self.settings.enabled("LEG006") == false {
            return;
        }
        if has_redundant_boolean_compare(node) == false {
            return;
        }
        self.add(node, "LEG006", "Avoid redundant boolean comparisons. Use the boolean value directly.");
    }

    fn check_redundant_boolean_operand(&mut self, node: &ruff_python_ast::ExprBoolOp) {
        if self.settings.enabled("LEG006") == false {
            return;
        }
        if has_redundant_boolean_operand(node) == false {
            return;
        }
        self.add(node, "LEG006", "Avoid redundant boolean operands like `and True` or `or False`.");
    }

    fn check_redundant_boolean_conditional(&mut self, node: &ruff_python_ast::ExprIf) {
        if self.settings.enabled("LEG006") == false {
            return;
        }
        if has_redundant_boolean_conditional(node) == false {
            return;
        }
        self.add(node, "LEG006", "Avoid redundant boolean ternaries. Use the condition directly or invert it.");
    }

    fn check_membership_search(&mut self, node: &ruff_python_ast::ExprCompare) {
        if self.loop_depth == 0 {
            return;
        }
        if self.settings.enabled("LEG005") == false {
            return;
        }
        if has_membership_search(node) == false {
            return;
        }
        self.add(node, "LEG005", "Membership test inside a loop can become O(n^2). Use a set or dict for repeated lookups.");
    }

    fn check_condition_target(&mut self, target: &Expr) {
        if let Expr::Name(name) = target {
            self.check_name(name.id.as_str(), target);
        }
    }

    fn check_name(&mut self, name: &str, node: &impl Ranged) {
        if self.settings.enabled("LEG007") == false {
            return;
        }
        if is_negative_condition_name(name) == false {
            return;
        }
        let message = format!("Prefer a positive condition name instead of `{name}`.");
        self.add(node, "LEG007", &message);
    }

    fn check_trivial_wrapper(&mut self, function: &StmtFunctionDef) {
        if self.settings.enabled("LEG008") == false {
            return;
        }
        if is_trivial_wrapper(function) == false {
            return;
        }
        let name = function.name.as_str();
        let message = format!("`{name}` only forwards its parameters to another call. Inline it or add meaningful behavior.");
        self.add(function, "LEG008", &message);
    }

    fn check_early_return(&mut self, node: &ruff_python_ast::StmtIf) {
        if self.settings.enabled("LEG009") == false {
            return;
        }
        if statement_list_exits(&node.body) == false {
            return;
        }
        let index = else_clause_index(node);
        if index == usize::MAX {
            return;
        }
        let else_clause = &node.elif_else_clauses[index];
        if let Some(first_stmt) = else_clause.body.first() {
            self.add(first_stmt, "LEG009", "Avoid an else branch after a branch that already exits. Return early instead.");
        }
    }

    fn check_guard_clause(&mut self, function: &StmtFunctionDef) {
        if self.settings.enabled("LEG010") == false {
            return;
        }
        if is_guard_clause_candidate(function) == false {
            return;
        }
        self.add(&function.body[0], "LEG010", "Prefer a guard clause instead of wrapping the main path in one large if block.");
    }

    fn check_call_chain(&mut self, node: &ruff_python_ast::ExprCall) {
        if self.settings.enabled("LEG011") == false {
            return;
        }
        let methods = chained_methods(&Expr::Call(node.clone()));
        let count = methods.len();
        if count <= self.settings.max_array_chain_depth {
            return;
        }
        let message = chain_message(count, self.settings.max_array_chain_depth, methods);
        self.add(node, "LEG011", &message);
    }

    fn add_nested_loop(&mut self, node: &Stmt) {
        if self.settings.enabled("LEG005") == false {
            return;
        }
        self.add(node, "LEG005", "Nested loop detected. Consider restructuring around a set, dict, or precomputed lookup.");
    }

    fn enter_control(&mut self, node: &impl Ranged) {
        self.control_depth += 1;
        if self.settings.enabled("LEG003") == false {
            return;
        }
        if self.control_depth <= self.settings.max_control_flow_depth {
            return;
        }
        let message = control_depth_message(self.control_depth, self.settings.max_control_flow_depth);
        self.add(node, "LEG003", &message);
    }

    fn leave_control(&mut self) {
        self.control_depth -= 1;
    }

    fn add(&mut self, node: &impl Ranged, code: &'static str, message: &str) {
        if self.settings.enabled(code) == false {
            return;
        }
        let range = node.range();
        let source_code = self.source_file.to_source_code();
        let start = source_code.line_column(range.start());
        let end = source_code.line_column(range.end());
        self.diagnostics.push(Diagnostic {
            filename: self.path.clone(),
            line: start.line.get(),
            column: start.column.get(),
            end_line: end.line.get(),
            end_column: end.column.get(),
            code,
            message: message.to_owned(),
        });
    }

    fn sort(&mut self) {
        self.diagnostics
            .sort_by(|left, right| diagnostic_key(left).cmp(&diagnostic_key(right)));
    }
}

impl Settings {
    fn enabled(&self, code: &str) -> bool {
        let is_selected = selector_matches(code, &self.select);
        if is_selected == false {
            return false;
        }
        let is_ignored = selector_matches(code, &self.ignore);
        is_ignored == false
    }
}

fn selector_matches(code: &str, selectors: &[String]) -> bool {
    selectors.iter().any(|selector| code.starts_with(selector))
}

fn is_simple_expr(expression: &Expr) -> bool {
    if matches!(expression, Expr::Name(_)) {
        return true;
    }
    expression.is_literal_expr()
}

fn count_condition_operators(expression: &Expr) -> usize {
    let own_count = condition_operator_count(expression);
    let child_count = count_child_condition_operators(expression);
    own_count + child_count
}

fn count_child_condition_operators(expression: &Expr) -> usize {
    let mut children = Vec::new();
    collect_expression_children(expression, &mut children);
    children.iter().map(|child| count_condition_operators(child)).sum()
}

fn condition_operator_count(expression: &Expr) -> usize {
    match expression {
        Expr::BoolOp(bool_op) => bool_op.values.len().saturating_sub(1),
        Expr::If(_) => 1,
        Expr::UnaryOp(unary_op) => unary_not_count(unary_op.op),
        _ => 0,
    }
}

fn count_readability_operators(expression: &Expr) -> usize {
    let own_count = readability_operator_count(expression);
    let child_count = count_child_readability_operators(expression);
    own_count + child_count
}

fn count_child_readability_operators(expression: &Expr) -> usize {
    let mut children = Vec::new();
    collect_expression_children(expression, &mut children);
    children.iter().map(|child| count_readability_operators(child)).sum()
}

fn readability_operator_count(expression: &Expr) -> usize {
    match expression {
        Expr::BoolOp(bool_op) => bool_op.values.len().saturating_sub(1),
        Expr::BinOp(_) => 1,
        Expr::If(_) => 1,
        Expr::Compare(compare) => compare.ops.len(),
        Expr::UnaryOp(unary_op) => unary_readability_count(unary_op.op),
        _ => 0,
    }
}

fn unary_not_count(operator: UnaryOp) -> usize {
    if operator == UnaryOp::Not {
        return 1;
    }
    0
}

fn unary_readability_count(operator: UnaryOp) -> usize {
    if operator == UnaryOp::Not {
        return 1;
    }
    if operator == UnaryOp::Invert {
        return 1;
    }
    0
}

fn collect_expression_children<'a>(expression: &'a Expr, children: &mut ExprRefs<'a>) {
    match expression {
        Expr::BoolOp(node) => children.extend(node.values.iter()),
        Expr::Named(node) => collect_two(children, &node.target, &node.value),
        Expr::BinOp(node) => collect_two(children, &node.left, &node.right),
        Expr::UnaryOp(node) => children.push(&node.operand),
        Expr::If(node) => collect_three(children, &node.test, &node.body, &node.orelse),
        Expr::Compare(node) => collect_compare_children(children, node),
        Expr::Call(node) => collect_call_children(children, node),
        Expr::Attribute(node) => children.push(&node.value),
        Expr::Subscript(node) => collect_two(children, &node.value, &node.slice),
        Expr::Starred(node) => children.push(&node.value),
        Expr::List(node) => children.extend(node.elts.iter()),
        Expr::Tuple(node) => children.extend(node.elts.iter()),
        Expr::Set(node) => children.extend(node.elts.iter()),
        Expr::Dict(node) => collect_dict_children(children, node),
        _ => {}
    }
}

fn collect_two<'a>(children: &mut ExprRefs<'a>, first: &'a Expr, second: &'a Expr) {
    children.push(first);
    children.push(second);
}

fn collect_three<'a>(children: &mut ExprRefs<'a>, first: &'a Expr, second: &'a Expr, third: &'a Expr) {
    children.push(first);
    children.push(second);
    children.push(third);
}

fn collect_compare_children<'a>(children: &mut ExprRefs<'a>, node: &'a ruff_python_ast::ExprCompare) {
    children.push(&node.left);
    children.extend(node.comparators.iter());
}

fn collect_call_children<'a>(children: &mut ExprRefs<'a>, node: &'a ruff_python_ast::ExprCall) {
    children.push(&node.func);
    children.extend(node.arguments.args.iter());
}

fn collect_dict_children<'a>(children: &mut ExprRefs<'a>, node: &'a ruff_python_ast::ExprDict) {
    for item in &node.items {
        if let Some(key) = &item.key {
            children.push(key);
        }
        children.push(&item.value);
    }
}

fn has_redundant_boolean_compare(node: &ruff_python_ast::ExprCompare) -> bool {
    for pair in node.ops.iter().zip(node.comparators.iter()) {
        let (operator, comparator) = pair;
        let is_equality = matches!(operator, CmpOp::Eq | CmpOp::NotEq);
        if is_equality == false {
            continue;
        }
        if is_boolean(comparator) {
            return true;
        }
    }
    false
}

fn has_redundant_boolean_operand(node: &ruff_python_ast::ExprBoolOp) -> bool {
    match node.op {
        BoolOp::And => node.values.iter().any(|value| is_boolean_value(value, true)),
        BoolOp::Or => node.values.iter().any(|value| is_boolean_value(value, false)),
    }
}

fn has_redundant_boolean_conditional(node: &ruff_python_ast::ExprIf) -> bool {
    let Some(body) = boolean_value(&node.body) else {
        return false;
    };
    let Some(orelse) = boolean_value(&node.orelse) else {
        return false;
    };
    body != orelse
}

fn has_nested_conditional_expr(node: &ruff_python_ast::ExprIf) -> bool {
    if contains_conditional_expr(&node.test) {
        return true;
    }
    if contains_conditional_expr(&node.body) {
        return true;
    }
    contains_conditional_expr(&node.orelse)
}

fn contains_conditional_expr(expression: &Expr) -> bool {
    if matches!(expression, Expr::If(_)) {
        return true;
    }
    let mut children = Vec::new();
    collect_expression_children(expression, &mut children);
    children.iter().any(|child| contains_conditional_expr(child))
}

fn has_membership_search(node: &ruff_python_ast::ExprCompare) -> bool {
    node.ops.iter().any(|operator| matches!(operator, CmpOp::In | CmpOp::NotIn))
}

fn is_boolean(expression: &Expr) -> bool {
    matches!(expression, Expr::BooleanLiteral(_))
}

fn boolean_value(expression: &Expr) -> OptionalBool {
    match expression {
        Expr::BooleanLiteral(boolean) => Some(boolean.value),
        _ => None,
    }
}

fn is_boolean_value(expression: &Expr, expected: bool) -> bool {
    boolean_value(expression) == Some(expected)
}

fn is_negative_condition_name(name: &str) -> bool {
    for prefix in BOOLEAN_PREFIXES {
        let named_prefix = format!("{prefix}_");
        let Some(rest) = name.strip_prefix(&named_prefix) else {
            continue;
        };
        return NEGATIVE_PREFIXES.iter().any(|negative| rest.starts_with(negative));
    }
    false
}

fn is_trivial_wrapper(function: &StmtFunctionDef) -> bool {
    if function.decorator_list.is_empty() == false {
        return false;
    }
    let Some(parameter_names) = simple_parameter_names(function) else {
        return false;
    };
    let [Stmt::Return(return_stmt)] = function.body.as_slice() else {
        return false;
    };
    let Some(Expr::Call(call)) = return_stmt.value.as_deref() else {
        return false;
    };
    if call.arguments.keywords.is_empty() == false {
        return false;
    }
    let callee_is_valid = call_names_other_function(call, function.name.as_str());
    if callee_is_valid == false {
        return false;
    }
    arguments_match_names(&call.arguments.args, &parameter_names)
}

fn simple_parameter_names(function: &StmtFunctionDef) -> OptionalNames {
    let parameters = &function.parameters;
    if parameters.vararg.is_some() {
        return None;
    }
    if parameters.kwarg.is_some() {
        return None;
    }
    if parameters.kwonlyargs.is_empty() == false {
        return None;
    }
    let positionals = parameters.posonlyargs.iter().chain(parameters.args.iter());
    if positionals.clone().any(|parameter| parameter.default.is_some()) {
        return None;
    }
    let names = positionals.map(|parameter| parameter.name().as_str().to_owned());
    Some(names.collect())
}

fn call_names_other_function(call: &ruff_python_ast::ExprCall, current_name: &str) -> bool {
    match call.func.as_ref() {
        Expr::Name(name) => name.id.as_str() != current_name,
        Expr::Attribute(attribute) => attribute.attr.as_str() != current_name,
        _ => false,
    }
}

fn arguments_match_names(arguments: &[Expr], names: &[String]) -> bool {
    if arguments.len() != names.len() {
        return false;
    }
    for pair in arguments.iter().zip(names) {
        let (argument, name) = pair;
        if argument_matches_name(argument, name) == false {
            return false;
        }
    }
    true
}

fn argument_matches_name(argument: &Expr, name: &str) -> bool {
    let Expr::Name(expr_name) = argument else {
        return false;
    };
    expr_name.id.as_str() == name
}

fn statement_list_exits(statements: &[Stmt]) -> bool {
    let Some(statement) = statements.last() else {
        return false;
    };
    statement_exits(statement)
}

fn statement_exits(statement: &Stmt) -> bool {
    match statement {
        Stmt::Return(_) => true,
        Stmt::Raise(_) => true,
        Stmt::Break(_) => true,
        Stmt::Continue(_) => true,
        Stmt::If(if_stmt) => if_statement_exits(if_stmt),
        _ => false,
    }
}

fn if_statement_exits(if_stmt: &ruff_python_ast::StmtIf) -> bool {
    let index = else_clause_index(if_stmt);
    if index == usize::MAX {
        return false;
    }
    if statement_list_exits(&if_stmt.body) == false {
        return false;
    }
    let clause = &if_stmt.elif_else_clauses[index];
    statement_list_exits(&clause.body)
}

fn else_clause_index(node: &ruff_python_ast::StmtIf) -> usize {
    for pair in node.elif_else_clauses.iter().enumerate() {
        let (index, clause) = pair;
        if clause.test.is_none() {
            return index;
        }
    }
    usize::MAX
}

fn is_guard_clause_candidate(function: &StmtFunctionDef) -> bool {
    let [Stmt::If(if_stmt)] = function.body.as_slice() else {
        return false;
    };
    if if_stmt.elif_else_clauses.is_empty() == false {
        return false;
    }
    if if_stmt.body.len() < 2 {
        return false;
    }
    statement_list_exits(&if_stmt.body) == false
}

fn chained_methods(expression: &Expr) -> Names {
    let Expr::Call(call) = expression else {
        return Vec::new();
    };
    let Expr::Attribute(attribute) = call.func.as_ref() else {
        return Vec::new();
    };
    let method = attribute.attr.as_str();
    if ARRAY_CHAIN_METHODS.contains(&method) == false {
        return Vec::new();
    }
    let mut methods = chained_methods(&attribute.value);
    methods.push(method.to_owned());
    methods
}

fn expression_message(count: usize, maximum: usize) -> String {
    format!("Expression has {count} readability operators (max {maximum}). Extract named sub-expressions.")
}

fn condition_message(count: usize, maximum: usize) -> String {
    format!("If condition has {count} boolean operators (max {maximum}). Hoist it into a named boolean.")
}

fn conditional_expr_message(count: usize, maximum: usize) -> String {
    format!("Ternary expression has {count} readability operators (max {maximum}). Extract it into named branches.")
}

fn control_depth_message(depth: usize, maximum: usize) -> String {
    format!("Control-flow depth is {depth} (max {maximum}). Prefer guard clauses or extraction.")
}

fn chain_message(count: usize, maximum: usize, methods: Names) -> String {
    let chain = methods.join(".");
    format!("Method chain has {count} steps (max {maximum}): {chain}.")
}

fn diagnostic_key(diagnostic: &Diagnostic) -> DiagnosticKey {
    (diagnostic.line, diagnostic.column, diagnostic.code)
}
