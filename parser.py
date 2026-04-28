"""
parser.py — Recursive Descent Parser for EduLang
==================================================
Grammar (extended):

  declaration    → (INT|FLOAT|STR|BOOL) IDENTIFIER
  assignment     → IDENTIFIER ASSIGN expression
  print_item     → STRING | expression
  expression     → or_expr
  or_expr        → and_expr (OR and_expr)*
  and_expr       → not_expr (AND not_expr)*
  not_expr       → NOT not_expr | comparison
  comparison     → additive ((GT|LT|GTE|LTE|EQ|NEQ) additive)?
  additive       → multiplicative ((PLUS|MINUS) multiplicative)*
  multiplicative → power ((MULTIPLY|DIVIDE|MODULO|FLOORDIV) power)*
  power          → unary (POWER unary)*          (right-associative)
  unary          → MINUS unary | factor
  factor         → NUMBER | FLOAT_LIT | STRING | TRUE | FALSE
                 | IDENTIFIER | LPAREN expression RPAREN
"""

from ast_nodes import (
    ProgramNode, DeclarationNode, AssignmentNode, InputNode,
    PrintNode, IfNode, LoopNode,
    BinaryOpNode, UnaryOpNode,
    NumberNode, FloatNode, StringNode, BoolNode, IdentifierNode,
)
from lexer import (
    INT, FLOAT, STR, BOOL, TRUE, FALSE,
    INPUT, PRINT, IF, ELSE, LOOP, TILL,
    AND, OR, NOT,
    IDENTIFIER, NUMBER, FLOAT_LIT, STRING,
    PLUS, MINUS, MULTIPLY, DIVIDE, MODULO, POWER, FLOORDIV,
    GT, LT, GTE, LTE, EQ, NEQ, ASSIGN,
    COLON, COMMA, LPAREN, RPAREN,
    INDENT, DEDENT, EOF,
)

TYPE_KEYWORDS = (INT, FLOAT, STR, BOOL)


class ParseError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        loc = f" (line {line}, col {col})" if line else ""
        super().__init__(f"ParseError{loc}: {message}")
        self.line = line
        self.col  = col


class Parser:
    def __init__(self, tokens: list):
        self.tokens = tokens
        self.pos    = 0

    # ── Navigation ──────────────────────────────

    def _cur(self):        return self.tokens[self.pos]
    def _peek(self, n=1):
        i = self.pos + n
        return self.tokens[i] if i < len(self.tokens) else self.tokens[-1]

    def _advance(self):
        t = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1: self.pos += 1
        return t

    def _expect(self, ttype):
        t = self._cur()
        if t.type != ttype:
            raise ParseError(
                f"Expected {ttype!r} but got {t.type!r} ({t.value!r})",
                t.line, t.column)
        return self._advance()

    def _match(self, *types): return self._cur().type in types

    # ── Entry ────────────────────────────────────

    def parse(self) -> ProgramNode:
        stmts = self._stmt_list()
        self._expect(EOF)
        return ProgramNode(stmts)

    # ── Statement list / block ───────────────────

    def _stmt_list(self):
        stmts = []
        while not self._match(DEDENT, EOF):
            s = self._statement()
            if s is not None:
                stmts.append(s)
        return stmts

    def _block(self):
        self._expect(INDENT)
        stmts = self._stmt_list()
        self._expect(DEDENT)
        return stmts

    # ── Statement dispatch ───────────────────────

    def _statement(self):
        t = self._cur()
        if t.type in TYPE_KEYWORDS:   return self._declaration()
        if t.type == IDENTIFIER:      return self._assignment()
        if t.type == INPUT:           return self._input()
        if t.type == PRINT:           return self._print()
        if t.type == IF:              return self._if()
        if t.type == LOOP:            return self._loop()
        raise ParseError(
            f"Unexpected token {t.type!r} ({t.value!r})", t.line, t.column)

    # ── Declarations ─────────────────────────────

    def _declaration(self):
        type_tok = self._advance()    # INT / FLOAT / STR / BOOL
        name_tok = self._expect(IDENTIFIER)
        return DeclarationNode(name_tok.value, type_tok.value, line=type_tok.line)

    # ── Simple statements ─────────────────────────

    def _assignment(self):
        name = self._expect(IDENTIFIER)
        self._expect(ASSIGN)
        expr = self._expression()
        return AssignmentNode(name.value, expr, line=name.line)

    def _input(self):
        tok  = self._expect(INPUT)
        name = self._expect(IDENTIFIER)
        return InputNode(name.value, line=tok.line)

    def _print(self):
        tok   = self._expect(PRINT)
        items = [self._print_item()]
        while self._match(COMMA):
            self._advance()
            items.append(self._print_item())
        return PrintNode(items, line=tok.line)

    def _print_item(self):
        if self._match(STRING):
            return self._advance().value   # bare string, not a StringNode
        return self._expression()

    # ── Control flow ─────────────────────────────

    def _if(self):
        tok  = self._expect(IF)
        cond = self._expression()
        self._expect(COLON)
        body = self._block()
        else_body = []
        if self._match(ELSE):
            self._advance()
            self._expect(COLON)
            else_body = self._block()
        return IfNode(cond, body, else_body, line=tok.line)

    def _loop(self):
        tok  = self._expect(LOOP)
        var  = self._expect(IDENTIFIER)
        self._expect(ASSIGN)
        init = self._expression()
        self._expect(TILL)
        cond = self._expression()
        self._expect(COLON)
        body = self._block()
        return LoopNode(var.value, init, cond, body, line=tok.line)

    # ── Expression grammar (precedence ladder) ────
    #
    #  Lowest  →  or_expr
    #          →  and_expr
    #          →  not_expr
    #          →  comparison
    #          →  additive
    #          →  multiplicative
    #          →  power           (right-associative)
    #          →  unary
    #  Highest →  factor

    def _expression(self):
        return self._or_expr()

    def _or_expr(self):
        left = self._and_expr()
        while self._match(OR):
            op = self._advance()
            left = BinaryOpNode(op.value, left, self._and_expr(), line=op.line)
        return left

    def _and_expr(self):
        left = self._not_expr()
        while self._match(AND):
            op = self._advance()
            left = BinaryOpNode(op.value, left, self._not_expr(), line=op.line)
        return left

    def _not_expr(self):
        if self._match(NOT):
            op = self._advance()
            return UnaryOpNode("not", self._not_expr(), line=op.line)
        return self._comparison()

    def _comparison(self):
        left = self._additive()
        if self._match(GT, LT, GTE, LTE, EQ, NEQ):
            op  = self._advance()
            right = self._additive()
            left = BinaryOpNode(op.value, left, right, line=op.line)
        return left

    def _additive(self):
        left = self._multiplicative()
        while self._match(PLUS, MINUS):
            op   = self._advance()
            left = BinaryOpNode(op.value, left, self._multiplicative(), line=op.line)
        return left

    def _multiplicative(self):
        left = self._power()
        while self._match(MULTIPLY, DIVIDE, MODULO, FLOORDIV):
            op   = self._advance()
            left = BinaryOpNode(op.value, left, self._power(), line=op.line)
        return left

    def _power(self):
        """Right-associative: 2 ** 3 ** 2  →  2 ** (3 ** 2)"""
        base = self._unary()
        if self._match(POWER):
            op  = self._advance()
            exp = self._power()     # recursive for right-assoc
            return BinaryOpNode(op.value, base, exp, line=op.line)
        return base

    def _unary(self):
        if self._match(MINUS):
            op = self._advance()
            return UnaryOpNode("-", self._unary(), line=op.line)
        return self._factor()

    def _factor(self):
        t = self._cur()

        if t.type == NUMBER:
            self._advance()
            return NumberNode(int(t.value), line=t.line)

        if t.type == FLOAT_LIT:
            self._advance()
            return FloatNode(float(t.value), line=t.line)

        if t.type == STRING:
            self._advance()
            return StringNode(t.value, line=t.line)

        if t.type == TRUE:
            self._advance()
            return BoolNode(True, line=t.line)

        if t.type == FALSE:
            self._advance()
            return BoolNode(False, line=t.line)

        if t.type == IDENTIFIER:
            self._advance()
            return IdentifierNode(t.value, line=t.line)

        if t.type == LPAREN:
            self._advance()
            expr = self._expression()
            self._expect(RPAREN)
            return expr

        raise ParseError(
            f"Expected a value or expression, got {t.type!r} ({t.value!r})",
            t.line, t.column)
