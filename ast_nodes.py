"""
ast_nodes.py — Abstract Syntax Tree Node Definitions for EduLang
=================================================================
Covers all datatypes (int, float, str, bool) and all operators.
"""


class ProgramNode:
    def __init__(self, statements: list):
        self.statements = statements
    def __repr__(self):
        return f"Program({self.statements})"


# ── Declarations ─────────────────────────────────────────────

class DeclarationNode:
    """int / float / str / bool  <name>"""
    def __init__(self, name: str, var_type: str, line: int = 0):
        self.name     = name
        self.var_type = var_type   # "int" | "float" | "str" | "bool"
        self.line     = line
    def __repr__(self):
        return f"Declare({self.var_type} {self.name})"


# ── Statements ───────────────────────────────────────────────

class AssignmentNode:
    def __init__(self, name: str, expr, line: int = 0):
        self.name = name
        self.expr = expr
        self.line = line
    def __repr__(self):
        return f"Assign({self.name} = {self.expr})"


class InputNode:
    def __init__(self, name: str, line: int = 0):
        self.name = name
        self.line = line
    def __repr__(self):
        return f"Input({self.name})"


class PrintNode:
    def __init__(self, items: list, line: int = 0):
        self.items = items
        self.line  = line
    def __repr__(self):
        return f"Print({self.items})"


class IfNode:
    def __init__(self, condition, body: list, else_body: list = None, line: int = 0):
        self.condition = condition
        self.body      = body
        self.else_body = else_body or []
        self.line      = line
    def __repr__(self):
        return f"If({self.condition}, body={self.body}, else={self.else_body})"


class LoopNode:
    def __init__(self, var: str, init_expr, condition, body: list, line: int = 0):
        self.var       = var
        self.init_expr = init_expr
        self.condition = condition
        self.body      = body
        self.line      = line
    def __repr__(self):
        return f"Loop({self.var}={self.init_expr} till {self.condition})"


# ── Expressions ──────────────────────────────────────────────

class BinaryOpNode:
    """<left> <op> <right>   — arithmetic, relational, or logical"""
    def __init__(self, op: str, left, right, line: int = 0):
        self.op    = op
        self.left  = left
        self.right = right
        self.line  = line
    def __repr__(self):
        return f"BinOp({self.left} {self.op} {self.right})"


class UnaryOpNode:
    """<op> <operand>   — unary minus  or  not"""
    def __init__(self, op: str, operand, line: int = 0):
        self.op      = op
        self.operand = operand
        self.line    = line
    def __repr__(self):
        return f"UnaryOp({self.op} {self.operand})"


class NumberNode:
    """Integer literal."""
    def __init__(self, value: int, line: int = 0):
        self.value = value
        self.line  = line
    def __repr__(self):
        return f"Num({self.value})"


class FloatNode:
    """Float literal."""
    def __init__(self, value: float, line: int = 0):
        self.value = value
        self.line  = line
    def __repr__(self):
        return f"Float({self.value})"


class StringNode:
    """String literal used as an expression (rhs of str assignment)."""
    def __init__(self, value: str, line: int = 0):
        self.value = value
        self.line  = line
    def __repr__(self):
        return f"Str({self.value!r})"


class BoolNode:
    """Boolean literal: true / false."""
    def __init__(self, value: bool, line: int = 0):
        self.value = value
        self.line  = line
    def __repr__(self):
        return f"Bool({self.value})"


class IdentifierNode:
    """Variable reference."""
    def __init__(self, name: str, line: int = 0):
        self.name = name
        self.line = line
    def __repr__(self):
        return f"Id({self.name})"
