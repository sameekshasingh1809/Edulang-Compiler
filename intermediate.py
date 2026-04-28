"""
intermediate.py — Three Address Code (TAC) Generator for EduLang
=================================================================
Extended to support:
  - float, str, bool literals
  - Operators:  %  **  //  !=  and  or  not
  - String concatenation via +
"""

from ast_nodes import (
    ProgramNode, DeclarationNode, AssignmentNode, InputNode,
    PrintNode, IfNode, LoopNode,
    BinaryOpNode, UnaryOpNode,
    NumberNode, FloatNode, StringNode, BoolNode, IdentifierNode,
)


# ── TAC Instruction Classes ──────────────────────────────────

class TACAssign:
    """result = arg1 [op arg2]"""
    def __init__(self, result: str, arg1, op: str = None, arg2=None):
        self.result = result
        self.arg1   = arg1
        self.op     = op
        self.arg2   = arg2
    def __str__(self):
        if self.op and self.arg2 is not None:
            return f"{self.result} = {self.arg1} {self.op} {self.arg2}"
        return f"{self.result} = {self.arg1!r}" if isinstance(self.arg1, str) and self.result != self.arg1 else f"{self.result} = {self.arg1}"


class TACUnary:
    """result = op arg"""
    def __init__(self, result: str, op: str, arg):
        self.result = result
        self.op     = op
        self.arg    = arg
    def __str__(self):
        return f"{self.result} = {self.op} {self.arg}"


class TACIfGoto:
    """IF left op right GOTO label"""
    def __init__(self, left, op: str, right, label: str):
        self.left  = left
        self.op    = op
        self.right = right
        self.label = label
    def __str__(self):
        return f"IF {self.left} {self.op} {self.right} GOTO {self.label}"


class TACGoto:
    def __init__(self, label: str):
        self.label = label
    def __str__(self):
        return f"GOTO {self.label}"


class TACLabel:
    def __init__(self, name: str):
        self.name = name
    def __str__(self):
        return f"{self.name}:"


class TACPrint:
    """
    Holds ALL items from one 'print' statement as a list.
    Each element is either:
      - a plain str  (string literal to print as-is)
      - ("var", name)  (variable whose runtime value to print)
    The whole list is printed on ONE output line, items separated by a space.
    """
    def __init__(self, items: list):
        self.items = items   # list of str | ("var", name)

    # Legacy single-item constructor support kept for backward compat
    @property
    def item(self):
        return self.items[0] if len(self.items) == 1 else self.items

    def __str__(self):
        parts = []
        for it in self.items:
            if isinstance(it, str):
                parts.append(f'"{it}"')
            elif isinstance(it, tuple) and it[0] == "var":
                parts.append(it[1])
            else:
                parts.append(str(it))
        return "PRINT " + ", ".join(parts)


class TACRead:
    def __init__(self, var: str):
        self.var = var
    def __str__(self):
        return f"READ {self.var}"


# ── Generator ────────────────────────────────────────────────

class TACGenerator:
    def __init__(self):
        self._instructions = []
        self._temp_count   = 0
        self._label_count  = 0

    def _tmp(self):
        self._temp_count += 1
        return f"t{self._temp_count}"

    def _lbl(self):
        self._label_count += 1
        return f"L{self._label_count}"

    def _emit(self, instr):
        self._instructions.append(instr)

    def generate(self, node) -> list:
        self._visit(node)
        return self._instructions

    def _visit(self, node):
        return getattr(self, f"_visit_{type(node).__name__}")(node)

    # ── Statements ────────────────────────────────

    def _visit_ProgramNode(self, node):
        for s in node.statements: self._visit(s)

    def _visit_DeclarationNode(self, node):
        pass   # no TAC for declarations

    def _visit_AssignmentNode(self, node):
        rhs = self._expr(node.expr)
        self._emit(TACAssign(node.name, rhs))

    def _visit_InputNode(self, node):
        self._emit(TACRead(node.name))

    def _visit_PrintNode(self, node):
        tac_items = []
        for item in node.items:
            if isinstance(item, str):
                tac_items.append(item)          # plain string literal
            else:
                val = self._expr(item)
                tac_items.append(("var", val))  # variable / expression result
        self._emit(TACPrint(tac_items))         # ONE instruction per print statement

    def _visit_IfNode(self, node):
        if node.else_body:
            else_lbl = self._lbl()
            end_lbl  = self._lbl()
            self._cond_jump(node.condition, else_lbl, negate=True)
            for s in node.body:      self._visit(s)
            self._emit(TACGoto(end_lbl))
            self._emit(TACLabel(else_lbl))
            for s in node.else_body: self._visit(s)
            self._emit(TACLabel(end_lbl))
        else:
            end_lbl = self._lbl()
            self._cond_jump(node.condition, end_lbl, negate=True)
            for s in node.body: self._visit(s)
            self._emit(TACLabel(end_lbl))

    def _visit_LoopNode(self, node):
        start = self._lbl()
        end   = self._lbl()
        init  = self._expr(node.init_expr)
        self._emit(TACAssign(node.var, init))
        self._emit(TACLabel(start))
        self._cond_jump(node.condition, end, negate=True)
        for s in node.body: self._visit(s)
        self._emit(TACGoto(start))
        self._emit(TACLabel(end))

    # ── Expression lowering ───────────────────────

    def _expr(self, node) -> str:
        """Lower an expression node; return the name/temp holding the result."""

        if isinstance(node, NumberNode):
            return str(node.value)

        if isinstance(node, FloatNode):
            return str(node.value)

        if isinstance(node, StringNode):
            # Wrap in a sentinel so codegen knows it's a literal string
            tmp = self._tmp()
            self._emit(TACAssign(tmp, ("strlit", node.value)))
            return tmp

        if isinstance(node, BoolNode):
            # Use a sentinel tuple so codegen knows to push a Python bool
            tmp = self._tmp()
            self._emit(TACAssign(tmp, ("boollit", node.value)))
            return tmp

        if isinstance(node, IdentifierNode):
            return node.name

        if isinstance(node, UnaryOpNode):
            arg = self._expr(node.operand)
            tmp = self._tmp()
            self._emit(TACUnary(tmp, node.op, arg))
            return tmp

        if isinstance(node, BinaryOpNode):
            l = self._expr(node.left)
            r = self._expr(node.right)
            tmp = self._tmp()
            self._emit(TACAssign(tmp, l, node.op, r))
            return tmp

        raise ValueError(f"Unknown expr node: {type(node).__name__}")

    # ── Conditional jump helper ───────────────────

    NEGATE = {">": "<=", "<": ">=", ">=": "<", "<=": ">",
              "==": "!=", "!=": "==",
              "and": "_not_and", "or": "_not_or"}

    def _cond_jump(self, condition, label: str, negate: bool = False):
        """Emit a conditional jump for a boolean / relational condition."""

        # Logical  AND / OR  — short-circuit not implemented; evaluate fully
        if isinstance(condition, BinaryOpNode) and condition.op in ("and", "or"):
            val = self._expr(condition)
            op  = "==" if negate else "!="
            self._emit(TACIfGoto(val, op, "0", label))
            return

        # Unary NOT
        if isinstance(condition, UnaryOpNode) and condition.op == "not":
            # negate of NOT  =  the inner condition straight
            self._cond_jump(condition.operand, label, negate=not negate)
            return

        # Relational binary
        if isinstance(condition, BinaryOpNode) and condition.op in (
                ">", "<", ">=", "<=", "==", "!="):
            l  = self._expr(condition.left)
            r  = self._expr(condition.right)
            op = condition.op
            if negate:
                op = {">=": "<", "<=": ">", ">": "<=", "<": ">=",
                      "==": "!=", "!=": "=="}[op]
            self._emit(TACIfGoto(l, op, r, label))
            return

        # Scalar (treat non-zero as truthy)
        val = self._expr(condition)
        op  = "==" if negate else "!="
        self._emit(TACIfGoto(val, op, "0", label))