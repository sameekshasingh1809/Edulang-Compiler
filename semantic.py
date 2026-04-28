"""
semantic.py — Semantic Analyzer for EduLang
============================================
Enforces:
  1. No variable used before declaration.
  2. No variable declared twice.
  3. Basic type compatibility for assignments and operations.

Supported types: "int"  "float"  "str"  "bool"
"""

from ast_nodes import (
    ProgramNode, DeclarationNode, AssignmentNode, InputNode,
    PrintNode, IfNode, LoopNode,
    BinaryOpNode, UnaryOpNode,
    NumberNode, FloatNode, StringNode, BoolNode, IdentifierNode,
)


# ── Error ─────────────────────────────────────────────────────

class SemanticError(Exception):
    def __init__(self, message: str, line: int = 0):
        loc = f" (line {line})" if line else ""
        super().__init__(f"SemanticError{loc}: {message}")
        self.line = line


# ── Symbol Table ──────────────────────────────────────────────

class SymbolTable:
    def __init__(self):
        self._table: dict = {}   # name → type str

    def declare(self, name: str, var_type: str, line: int = 0):
        if name in self._table:
            raise SemanticError(f"Variable '{name}' is already declared", line)
        self._table[name] = var_type

    def lookup(self, name: str, line: int = 0) -> str:
        if name not in self._table:
            raise SemanticError(f"Variable '{name}' used before declaration", line)
        return self._table[name]

    def is_declared(self, name: str) -> bool:
        return name in self._table

    def all_symbols(self) -> dict:
        return dict(self._table)

    def __repr__(self):
        return f"SymbolTable({self._table})"


# ── Type helpers ──────────────────────────────────────────────

# Numeric types that can freely mix (int op float → float)
_NUMERIC = {"int", "float"}

def _numeric_result(t1: str, t2: str) -> str:
    """Return result type for a numeric binary op."""
    if t1 == "float" or t2 == "float":
        return "float"
    return "int"

ARITH_OPS   = {"+", "-", "*", "/", "%", "**", "//"}
COMPARE_OPS = {">", "<", ">=", "<=", "==", "!="}
LOGICAL_OPS = {"and", "or", "not"}


def _infer_expr_type(node, sym: SymbolTable) -> str:
    """Infer the EduLang type of an expression node."""
    if isinstance(node, NumberNode):   return "int"
    if isinstance(node, FloatNode):    return "float"
    if isinstance(node, StringNode):   return "str"
    if isinstance(node, BoolNode):     return "bool"
    if isinstance(node, IdentifierNode):
        return sym.lookup(node.name, node.line)

    if isinstance(node, UnaryOpNode):
        t = _infer_expr_type(node.operand, sym)
        if node.op == "not":   return "bool"
        if node.op == "-":
            if t not in _NUMERIC:
                raise SemanticError(
                    f"Unary minus requires int or float, got '{t}'", node.line)
            return t

    if isinstance(node, BinaryOpNode):
        lt = _infer_expr_type(node.left,  sym)
        rt = _infer_expr_type(node.right, sym)

        if node.op in ARITH_OPS:
            # String concatenation with +
            if node.op == "+" and lt == "str" and rt == "str":
                return "str"
            if lt not in _NUMERIC or rt not in _NUMERIC:
                raise SemanticError(
                    f"Operator '{node.op}' requires numeric operands, "
                    f"got '{lt}' and '{rt}'", node.line)
            return _numeric_result(lt, rt)

        if node.op in COMPARE_OPS:
            # Allow comparing same-type or numeric mix
            if lt == rt:
                return "bool"
            if lt in _NUMERIC and rt in _NUMERIC:
                return "bool"
            raise SemanticError(
                f"Cannot compare '{lt}' and '{rt}' with '{node.op}'", node.line)

        if node.op in LOGICAL_OPS:
            return "bool"

    return "int"   # fallback


# ── Analyzer ──────────────────────────────────────────────────

class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()

    def analyze(self, node) -> SymbolTable:
        self._visit(node)
        return self.symbol_table

    def _visit(self, node):
        method = f"_visit_{type(node).__name__}"
        return getattr(self, method, self._generic)(node)

    def _generic(self, node):
        raise SemanticError(f"No visitor for {type(node).__name__}")

    # ── Statements ────────────────────────────────

    def _visit_ProgramNode(self, node):
        for s in node.statements: self._visit(s)

    def _visit_DeclarationNode(self, node):
        self.symbol_table.declare(node.name, node.var_type, node.line)

    def _visit_AssignmentNode(self, node):
        declared_type = self.symbol_table.lookup(node.name, node.line)
        rhs_type      = _infer_expr_type(node.expr, self.symbol_table)
        # Allow int ↔ float coercion silently
        if declared_type in _NUMERIC and rhs_type in _NUMERIC:
            return
        if declared_type != rhs_type:
            raise SemanticError(
                f"Cannot assign '{rhs_type}' to variable '{node.name}' of type '{declared_type}'",
                node.line)

    def _visit_InputNode(self, node):
        self.symbol_table.lookup(node.name, node.line)

    def _visit_PrintNode(self, node):
        for item in node.items:
            if isinstance(item, str): continue
            self._visit(item)

    def _visit_IfNode(self, node):
        self._visit(node.condition)
        for s in node.body:      self._visit(s)
        for s in node.else_body: self._visit(s)

    def _visit_LoopNode(self, node):
        self.symbol_table.lookup(node.var, node.line)
        self._visit(node.init_expr)
        self._visit(node.condition)
        for s in node.body: self._visit(s)

    # ── Expressions ───────────────────────────────

    def _visit_BinaryOpNode(self, node):
        self._visit(node.left); self._visit(node.right)
        # Type-check (will raise SemanticError if incompatible)
        _infer_expr_type(node, self.symbol_table)

    def _visit_UnaryOpNode(self, node):
        self._visit(node.operand)
        _infer_expr_type(node, self.symbol_table)

    def _visit_NumberNode(self, _):     pass
    def _visit_FloatNode(self, _):      pass
    def _visit_StringNode(self, _):     pass
    def _visit_BoolNode(self, _):       pass

    def _visit_IdentifierNode(self, node):
        self.symbol_table.lookup(node.name, node.line)
