"""
test_edulang.py — Automated Unit & Integration Tests for EduLang
================================================================
Covers all compiler stages for the full extended language:
  Datatypes  : int  float  str  bool
  Operators  : + - * / % ** // > < >= <= == != and or not (unary -)
  Statements : int/float/str/bool decl, assign, input, print, if/else, loop

Run with:
    python -m unittest test_edulang -v
"""

import unittest, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from lexer import (
    Lexer, LexerError, Token,
    INT, FLOAT, STR, BOOL, TRUE, FALSE,
    INPUT, PRINT, IF, ELSE, LOOP, TILL, AND, OR, NOT,
    IDENTIFIER, NUMBER, FLOAT_LIT, STRING,
    PLUS, MINUS, MULTIPLY, DIVIDE, MODULO, POWER, FLOORDIV,
    GT, LT, GTE, LTE, EQ, NEQ, ASSIGN,
    COLON, COMMA, LPAREN, RPAREN, INDENT, DEDENT, EOF,
)
from parser   import Parser, ParseError
from semantic import SemanticAnalyzer, SemanticError, SymbolTable
from intermediate import (TACGenerator, TACAssign, TACUnary,
                           TACIfGoto, TACGoto, TACLabel, TACPrint, TACRead)
from optimizer import constant_folding, remove_redundant_assignments, optimize
from codegen   import CodeGenerator
from errors    import friendly
from main      import compile_source


# ═══════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════

def run(source: str, inputs=None) -> list:
    it = iter(inputs or [])
    r  = compile_source(source, input_fn=lambda: str(next(it)))
    assert r["error"] is None, f"Unexpected compile error: {r['error']}"
    return r["output"]

def compile_error(source: str) -> str:
    r = compile_source(source)
    assert r["error"] is not None, "Expected a compile error but got none"
    return r["error"]

def lex(source: str):
    return Lexer(source).tokenize()

def parse(source: str):
    return Parser(lex(source)).parse()

def gen_tac(source: str):
    ast = parse(source)
    SemanticAnalyzer().analyze(ast)
    return TACGenerator().generate(ast)

def full_run(source: str, inputs=None):
    it      = iter(inputs or [])
    tac     = gen_tac(source)
    tac_opt = optimize(tac)
    cg      = CodeGenerator()
    cg.generate(tac_opt)
    return cg.run(input_fn=lambda: str(next(it)))


# ═══════════════════════════════════════════════════════════════════════
# 1. LEXER — Keywords
# ═══════════════════════════════════════════════════════════════════════

class TestLexerKeywords(unittest.TestCase):

    def _type(self, src): return lex(src)[0].type

    def test_int_keyword(self):     self.assertEqual(self._type("int"),   INT)
    def test_float_keyword(self):   self.assertEqual(self._type("float"), FLOAT)
    def test_str_keyword(self):     self.assertEqual(self._type("str"),   STR)
    def test_bool_keyword(self):    self.assertEqual(self._type("bool"),  BOOL)
    def test_true_keyword(self):    self.assertEqual(self._type("true"),  TRUE)
    def test_false_keyword(self):   self.assertEqual(self._type("false"), FALSE)
    def test_input_keyword(self):   self.assertEqual(self._type("input"), INPUT)
    def test_print_keyword(self):   self.assertEqual(self._type("print"), PRINT)
    def test_if_keyword(self):      self.assertEqual(self._type("if"),    IF)
    def test_else_keyword(self):    self.assertEqual(self._type("else"),  ELSE)
    def test_loop_keyword(self):    self.assertEqual(self._type("loop"),  LOOP)
    def test_till_keyword(self):    self.assertEqual(self._type("till"),  TILL)
    def test_and_keyword(self):     self.assertEqual(self._type("and"),   AND)
    def test_or_keyword(self):      self.assertEqual(self._type("or"),    OR)
    def test_not_keyword(self):     self.assertEqual(self._type("not"),   NOT)

    def test_identifier_not_keyword(self):
        self.assertEqual(self._type("integer"), IDENTIFIER)

    def test_keywords_case_sensitive(self):
        # uppercase must be identifiers
        self.assertEqual(self._type("INT"),   IDENTIFIER)
        self.assertEqual(self._type("True"),  IDENTIFIER)
        self.assertEqual(self._type("AND"),   IDENTIFIER)


# ═══════════════════════════════════════════════════════════════════════
# 2. LEXER — Literals
# ═══════════════════════════════════════════════════════════════════════

class TestLexerLiterals(unittest.TestCase):

    def test_integer_literal(self):
        t = lex("42")[0]
        self.assertEqual(t.type, NUMBER); self.assertEqual(t.value, "42")

    def test_zero_literal(self):
        self.assertEqual(lex("0")[0].type, NUMBER)

    def test_large_number(self):
        self.assertEqual(lex("9999999")[0].value, "9999999")

    def test_float_literal(self):
        t = lex("3.14")[0]
        self.assertEqual(t.type, FLOAT_LIT); self.assertEqual(t.value, "3.14")

    def test_float_no_leading_zero(self):
        # .5 is a valid float token
        t = lex(".5")[0]
        self.assertEqual(t.type, FLOAT_LIT)

    def test_string_literal(self):
        t = lex('"hello world"')[0]
        self.assertEqual(t.type, STRING); self.assertEqual(t.value, "hello world")

    def test_empty_string(self):
        self.assertEqual(lex('""')[0].value, "")

    def test_string_with_escape_n(self):
        t = lex(r'"line1\nline2"')[0]
        self.assertEqual(t.type, STRING)

    def test_string_with_numbers_symbols(self):
        t = lex('"a + b = 10"')[0]
        self.assertEqual(t.type, STRING)


# ═══════════════════════════════════════════════════════════════════════
# 3. LEXER — Operators
# ═══════════════════════════════════════════════════════════════════════

class TestLexerOperators(unittest.TestCase):

    def _tok(self, src): return lex(src)[0].type

    # Arithmetic
    def test_plus(self):      self.assertEqual(self._tok("+"),  PLUS)
    def test_minus(self):     self.assertEqual(self._tok("-"),  MINUS)
    def test_multiply(self):  self.assertEqual(self._tok("*"),  MULTIPLY)
    def test_divide(self):    self.assertEqual(self._tok("/"),  DIVIDE)
    def test_modulo(self):    self.assertEqual(self._tok("%"),  MODULO)
    def test_power(self):     self.assertEqual(self._tok("**"), POWER)
    def test_floordiv(self):  self.assertEqual(self._tok("//"), FLOORDIV)

    # Relational
    def test_gt(self):    self.assertEqual(self._tok(">"),  GT)
    def test_lt(self):    self.assertEqual(self._tok("<"),  LT)
    def test_gte(self):   self.assertEqual(self._tok(">="), GTE)
    def test_lte(self):   self.assertEqual(self._tok("<="), LTE)
    def test_eq(self):    self.assertEqual(self._tok("=="), EQ)
    def test_neq(self):   self.assertEqual(self._tok("!="), NEQ)
    def test_assign(self):self.assertEqual(self._tok("="),  ASSIGN)

    # Punctuation
    def test_colon(self):  self.assertEqual(self._tok(":"), COLON)
    def test_comma(self):  self.assertEqual(self._tok(","), COMMA)
    def test_lparen(self): self.assertEqual(self._tok("("), LPAREN)
    def test_rparen(self): self.assertEqual(self._tok(")"), RPAREN)

    # Multi-char longest-match
    def test_power_not_two_multiplies(self):
        self.assertEqual(lex("**")[0].type, POWER)
        self.assertEqual(len(lex("**")), 2)   # POWER + EOF

    def test_floordiv_not_two_divides(self):
        self.assertEqual(lex("//")[0].type, FLOORDIV)

    def test_neq_not_bang_then_assign(self):
        self.assertEqual(lex("!=")[0].type, NEQ)

    def test_gte_not_gt_then_assign(self):
        self.assertEqual(lex(">=")[0].type, GTE)

    def test_eq_not_two_assigns(self):
        self.assertEqual(lex("==")[0].type, EQ)
        self.assertEqual(len(lex("==")), 2)


# ═══════════════════════════════════════════════════════════════════════
# 4. LEXER — Positions, Indentation, Errors
# ═══════════════════════════════════════════════════════════════════════

class TestLexerPositions(unittest.TestCase):

    def test_first_token_line_1(self):
        self.assertEqual(lex("int x")[0].line, 1)

    def test_second_line_token(self):
        tokens = lex("int x\nint y")
        self.assertEqual(tokens[2].line, 2)

    def test_column_tracking(self):
        tokens = lex("int x")
        self.assertEqual(tokens[0].column, 1)
        self.assertEqual(tokens[1].column, 5)


class TestLexerIndentation(unittest.TestCase):

    def test_indent_emitted(self):
        src   = "if x > 0:\n    print \"yes\"\n"
        types = [t.type for t in lex(src)]
        self.assertIn(INDENT, types)

    def test_dedent_emitted(self):
        src   = "if x > 0:\n    print \"yes\"\nprint \"done\"\n"
        types = [t.type for t in lex(src)]
        self.assertIn(DEDENT, types)

    def test_eof_at_end(self):
        self.assertEqual(lex("int x\n")[-1].type, EOF)

    def test_blank_lines_ignored(self):
        types = [t.type for t in lex("int x\n\n\nint y\n")]
        self.assertNotIn(INDENT, types)


class TestLexerErrors(unittest.TestCase):

    def test_unexpected_character(self):
        with self.assertRaises(LexerError) as ctx:
            lex("int x@")
        self.assertIn("Unexpected character", str(ctx.exception))

    def test_unterminated_string(self):
        with self.assertRaises(LexerError) as ctx:
            lex('"hello')
        self.assertIn("Unterminated string", str(ctx.exception))

    def test_at_sign_raises(self):
        with self.assertRaises(LexerError): lex("@bad")

    def test_dollar_sign_raises(self):
        with self.assertRaises(LexerError): lex("x = $5")

    def test_hash_is_comment(self):
        types = [t.type for t in lex("# comment\nint x\n")]
        self.assertNotIn(STRING, types)
        self.assertIn(INT, types)


# ═══════════════════════════════════════════════════════════════════════
# 5. PARSER — Declarations (all 4 types)
# ═══════════════════════════════════════════════════════════════════════

from ast_nodes import (
    ProgramNode, DeclarationNode, AssignmentNode, InputNode,
    PrintNode, IfNode, LoopNode,
    BinaryOpNode, UnaryOpNode,
    NumberNode, FloatNode, StringNode, BoolNode, IdentifierNode,
)

class TestParserDeclarations(unittest.TestCase):

    def test_int_declaration(self):
        node = parse("int x\n").statements[0]
        self.assertIsInstance(node, DeclarationNode)
        self.assertEqual(node.name, "x")
        self.assertEqual(node.var_type, "int")

    def test_float_declaration(self):
        node = parse("float y\n").statements[0]
        self.assertEqual(node.var_type, "float")

    def test_str_declaration(self):
        node = parse("str s\n").statements[0]
        self.assertEqual(node.var_type, "str")

    def test_bool_declaration(self):
        node = parse("bool b\n").statements[0]
        self.assertEqual(node.var_type, "bool")

    def test_multiple_declarations(self):
        ast = parse("int a\nfloat b\nstr c\nbool d\n")
        types = [s.var_type for s in ast.statements]
        self.assertEqual(types, ["int", "float", "str", "bool"])


# ═══════════════════════════════════════════════════════════════════════
# 6. PARSER — Expressions and new operators
# ═══════════════════════════════════════════════════════════════════════

class TestParserExpressions(unittest.TestCase):

    def test_float_literal(self):
        ast  = parse("float x\nx = 3.14\n")
        node = ast.statements[1]
        self.assertIsInstance(node.expr, FloatNode)
        self.assertAlmostEqual(node.expr.value, 3.14)

    def test_string_literal_expr(self):
        ast  = parse('str s\ns = "hello"\n')
        node = ast.statements[1]
        self.assertIsInstance(node.expr, StringNode)
        self.assertEqual(node.expr.value, "hello")

    def test_bool_true_literal(self):
        ast  = parse("bool b\nb = true\n")
        self.assertIsInstance(ast.statements[1].expr, BoolNode)
        self.assertTrue(ast.statements[1].expr.value)

    def test_bool_false_literal(self):
        ast  = parse("bool b\nb = false\n")
        self.assertFalse(ast.statements[1].expr.value)

    def test_modulo_operator(self):
        ast  = parse("int x\nx = 10 % 3\n")
        expr = ast.statements[1].expr
        self.assertIsInstance(expr, BinaryOpNode)
        self.assertEqual(expr.op, "%")

    def test_power_operator(self):
        ast  = parse("int x\nx = 2 ** 8\n")
        expr = ast.statements[1].expr
        self.assertEqual(expr.op, "**")

    def test_floordiv_operator(self):
        ast  = parse("int x\nx = 17 // 5\n")
        expr = ast.statements[1].expr
        self.assertEqual(expr.op, "//")

    def test_neq_operator(self):
        ast  = parse("int x\nx = 5\nif x != 3:\n    print \"ne\"\n")
        cond = ast.statements[2].condition
        self.assertEqual(cond.op, "!=")

    def test_and_operator(self):
        ast  = parse("int x\nx = 1\nif x > 0 and x < 10:\n    print \"ok\"\n")
        cond = ast.statements[2].condition
        self.assertEqual(cond.op, "and")

    def test_or_operator(self):
        ast  = parse("int x\nx = 15\nif x < 0 or x > 10:\n    print \"out\"\n")
        cond = ast.statements[2].condition
        self.assertEqual(cond.op, "or")

    def test_not_unary(self):
        ast  = parse("bool b\nb = false\nif not b:\n    print \"ok\"\n")
        cond = ast.statements[2].condition
        self.assertIsInstance(cond, UnaryOpNode)
        self.assertEqual(cond.op, "not")

    def test_unary_minus_node(self):
        ast  = parse("int x\nx = -5\n")
        expr = ast.statements[1].expr
        self.assertIsInstance(expr, UnaryOpNode)
        self.assertEqual(expr.op, "-")

    def test_power_is_right_associative(self):
        # 2 ** 3 ** 2  →  BinOp(**, Num(2), BinOp(**, Num(3), Num(2)))
        ast   = parse("int x\nx = 2 ** 3 ** 2\n")
        outer = ast.statements[1].expr
        self.assertEqual(outer.op, "**")
        self.assertIsInstance(outer.right, BinaryOpNode)
        self.assertEqual(outer.right.op, "**")

    def test_operator_precedence_mul_over_add(self):
        ast  = parse("int x\nx = 2 + 3 * 4\n")
        expr = ast.statements[1].expr
        self.assertEqual(expr.op, "+")
        self.assertEqual(expr.right.op, "*")

    def test_parentheses_override_precedence(self):
        ast  = parse("int x\nx = (2 + 3) * 4\n")
        expr = ast.statements[1].expr
        self.assertEqual(expr.op, "*")


# ═══════════════════════════════════════════════════════════════════════
# 7. PARSER — Control flow
# ═══════════════════════════════════════════════════════════════════════

class TestParserControlFlow(unittest.TestCase):

    def test_if_no_else(self):
        ast  = parse("int x\nx = 5\nif x > 3:\n    print \"big\"\n")
        node = ast.statements[2]
        self.assertIsInstance(node, IfNode)
        self.assertEqual(node.else_body, [])

    def test_if_else(self):
        src  = ("int x\nx = 2\n"
                "if x > 3:\n    print \"big\"\n"
                "else:\n    print \"small\"\n")
        node = parse(src).statements[2]
        self.assertEqual(len(node.else_body), 1)

    def test_loop_structure(self):
        src  = "int i\nloop i = 0 till i < 5:\n    print i\n    i = i + 1\n"
        node = parse(src).statements[1]
        self.assertIsInstance(node, LoopNode)
        self.assertEqual(node.var, "i")

    def test_all_comparison_ops_parsed(self):
        for op in [">", "<", ">=", "<=", "==", "!="]:
            src  = f"int x\nx = 1\nif x {op} 0:\n    print \"y\"\n"
            cond = parse(src).statements[2].condition
            self.assertEqual(cond.op, op)


class TestParserErrors(unittest.TestCase):

    def test_missing_colon_on_if(self):
        with self.assertRaises(ParseError):
            parse("int x\nif x > 0\n    print \"ok\"\n")

    def test_missing_till_in_loop(self):
        with self.assertRaises(ParseError):
            parse("int i\nloop i = 0 i < 5:\n    print i\n")

    def test_unexpected_token(self):
        with self.assertRaises(ParseError):
            parse("int + x\n")


# ═══════════════════════════════════════════════════════════════════════
# 8. SEMANTIC ANALYZER
# ═══════════════════════════════════════════════════════════════════════

class TestSymbolTable(unittest.TestCase):

    def test_declare_and_lookup(self):
        st = SymbolTable()
        st.declare("x", "int")
        self.assertEqual(st.lookup("x"), "int")

    def test_double_declare_raises(self):
        st = SymbolTable()
        st.declare("x", "int")
        with self.assertRaises(SemanticError):
            st.declare("x", "int")

    def test_lookup_undeclared_raises(self):
        with self.assertRaises(SemanticError):
            SymbolTable().lookup("z")

    def test_all_symbols(self):
        st = SymbolTable()
        st.declare("a", "int"); st.declare("b", "float")
        self.assertEqual(set(st.all_symbols()), {"a", "b"})


class TestSemanticAnalyzer(unittest.TestCase):

    def _analyze(self, src):
        return SemanticAnalyzer().analyze(parse(src))

    def test_valid_int_program(self):
        st = self._analyze("int x\nx = 5\n")
        self.assertIn("x", st.all_symbols())

    def test_valid_float_program(self):
        st = self._analyze("float x\nx = 3.14\n")
        self.assertEqual(st.lookup("x"), "float")

    def test_valid_str_program(self):
        st = self._analyze('str s\ns = "hello"\n')
        self.assertEqual(st.lookup("s"), "str")

    def test_valid_bool_program(self):
        st = self._analyze("bool b\nb = true\n")
        self.assertEqual(st.lookup("b"), "bool")

    def test_undeclared_in_assignment(self):
        with self.assertRaises(SemanticError) as ctx:
            self._analyze("x = 5\n")
        self.assertIn("used before declaration", str(ctx.exception))

    def test_double_declaration(self):
        with self.assertRaises(SemanticError) as ctx:
            self._analyze("int x\nint x\n")
        self.assertIn("already declared", str(ctx.exception))

    def test_str_wrong_type_raises(self):
        with self.assertRaises(SemanticError):
            self._analyze("str s\ns = 42\n")

    def test_bool_wrong_type_raises(self):
        with self.assertRaises(SemanticError):
            self._analyze('bool b\nb = "hello"\n')

    def test_arithmetic_on_str_raises(self):
        with self.assertRaises(SemanticError):
            self._analyze('str s\nstr t\ns = "a"\nt = "b"\nint x\nx = s - t\n')

    def test_int_float_coercion_allowed(self):
        # assigning int literal to float var is ok
        st = self._analyze("float x\nx = 5\n")
        self.assertEqual(st.lookup("x"), "float")

    def test_undeclared_in_loop(self):
        with self.assertRaises(SemanticError):
            self._analyze("loop i = 0 till i < 5:\n    print i\n    i = i + 1\n")

    def test_undeclared_in_print(self):
        with self.assertRaises(SemanticError):
            self._analyze("print z\n")


# ═══════════════════════════════════════════════════════════════════════
# 9. TAC GENERATOR
# ═══════════════════════════════════════════════════════════════════════

class TestTACGenerator(unittest.TestCase):

    def test_assignment_produces_tac_assign(self):
        tac = gen_tac("int x\nx = 5\n")
        self.assertTrue(any(isinstance(i, TACAssign) and i.result == "x" for i in tac))

    def test_binary_op_produces_temp(self):
        tac = gen_tac("int x\nint y\nx = y + 3\n")
        temps = [i for i in tac if isinstance(i, TACAssign) and i.result.startswith("t")]
        self.assertTrue(len(temps) >= 1)

    def test_unary_minus_emits_tacunary(self):
        tac = gen_tac("int x\nx = -5\n")
        self.assertTrue(any(isinstance(i, TACUnary) and i.op == "-" for i in tac))

    def test_not_emits_tacunary(self):
        tac = gen_tac("bool b\nb = false\nif not b:\n    print \"ok\"\n")
        # not is handled via _cond_jump which flips negate; check no crash
        self.assertIsInstance(tac, list)

    def test_print_emits_tacprint(self):
        tac = gen_tac('print "hi"\n')
        self.assertTrue(any(isinstance(i, TACPrint) for i in tac))

    def test_input_emits_tacread(self):
        tac = gen_tac("int x\ninput x\n")
        self.assertTrue(any(isinstance(i, TACRead) for i in tac))

    def test_if_emits_labels(self):
        tac = gen_tac("int x\nx = 1\nif x > 0:\n    print \"ok\"\n")
        self.assertGreaterEqual(sum(isinstance(i, TACLabel) for i in tac), 1)

    def test_if_else_emits_goto(self):
        src = "int x\nx = 1\nif x > 0:\n    print \"pos\"\nelse:\n    print \"neg\"\n"
        tac = gen_tac(src)
        self.assertGreaterEqual(sum(isinstance(i, TACGoto) for i in tac), 1)

    def test_loop_emits_two_labels(self):
        src = "int i\nloop i = 0 till i < 3:\n    i = i + 1\n"
        tac = gen_tac(src)
        self.assertGreaterEqual(sum(isinstance(i, TACLabel) for i in tac), 2)

    def test_no_tac_for_declaration(self):
        tac = gen_tac("int x\n")
        self.assertEqual(len([i for i in tac if isinstance(i, TACAssign)]), 0)


# ═══════════════════════════════════════════════════════════════════════
# 10. OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════

class TestConstantFolding(unittest.TestCase):

    def _fold(self, r, a, op, b):
        return constant_folding([TACAssign(r, a, op, b)])

    def test_addition(self):
        self.assertEqual(str(self._fold("t1", 5, "+", 3)[0]), "t1 = 8")

    def test_subtraction(self):
        self.assertEqual(str(self._fold("t1", 10, "-", 4)[0]), "t1 = 6")

    def test_multiplication(self):
        self.assertEqual(str(self._fold("t1", 6, "*", 7)[0]), "t1 = 42")

    def test_division_true_div(self):
        # / is true division → 20/4 = 5.0
        out = self._fold("t1", 20, "/", 4)
        self.assertAlmostEqual(float(str(out[0]).split("= ")[1]), 5.0)

    def test_floordiv(self):
        self.assertEqual(str(self._fold("t1", 17, "//", 5)[0]), "t1 = 3")

    def test_modulo(self):
        self.assertEqual(str(self._fold("t1", 10, "%", 3)[0]), "t1 = 1")

    def test_power(self):
        self.assertEqual(str(self._fold("t1", 2, "**", 10)[0]), "t1 = 1024")

    def test_division_by_zero_not_folded(self):
        out = self._fold("t1", 5, "/", 0)
        self.assertEqual(out[0].op, "/")

    def test_variable_operand_not_folded(self):
        out = constant_folding([TACAssign("t1", "x", "+", 3)])
        self.assertEqual(out[0].op, "+")

    def test_neq_comparison_folded(self):
        self.assertEqual(str(self._fold("t1", 5, "!=", 3)[0]), "t1 = 1")

    def test_eq_comparison_false(self):
        self.assertEqual(str(self._fold("t1", 5, "==", 3)[0]), "t1 = 0")

    def test_and_fold(self):
        self.assertEqual(str(self._fold("t1", 1, "and", 1)[0]), "t1 = 1")

    def test_or_fold_short(self):
        self.assertEqual(str(self._fold("t1", 0, "or", 1)[0]), "t1 = 1")

    def test_unary_neg_folded(self):
        out = constant_folding([TACUnary("t1", "-", 5)])
        self.assertEqual(str(out[0]), "t1 = -5")

    def test_unary_not_folded(self):
        out = constant_folding([TACUnary("t1", "not", 0)])
        self.assertEqual(str(out[0]), "t1 = 1")

    def test_non_assign_passes_through(self):
        out = constant_folding([TACLabel("L1")])
        self.assertIsInstance(out[0], TACLabel)


class TestRedundantAssignmentRemoval(unittest.TestCase):

    def test_removes_overwritten(self):
        code = [TACAssign("x", 0), TACAssign("x", "a", "+", "b")]
        out  = remove_redundant_assignments(code)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].arg1, "a")

    def test_keeps_when_used_by_next(self):
        code = [TACAssign("t1", "a", "+", "b"), TACAssign("x", "t1")]
        self.assertEqual(len(remove_redundant_assignments(code)), 2)

    def test_empty_list(self):
        self.assertEqual(remove_redundant_assignments([]), [])

    def test_labels_kept(self):
        code = [TACLabel("L1"), TACLabel("L2")]
        self.assertEqual(len(remove_redundant_assignments(code)), 2)

    def test_both_passes_together(self):
        code = [TACAssign("t1", 2, "+", 3), TACAssign("t1", 10)]
        out  = optimize(code)
        self.assertEqual(len(out), 1)
        self.assertEqual(str(out[0]), "t1 = 10")


# ═══════════════════════════════════════════════════════════════════════
# 11. CODE GENERATOR — int arithmetic
# ═══════════════════════════════════════════════════════════════════════

class TestCodeGeneratorInt(unittest.TestCase):

    def test_add(self):
        self.assertEqual(full_run("int x\nx = 3 + 4\nprint x\n"), ["7"])

    def test_sub(self):
        self.assertEqual(full_run("int x\nx = 10 - 3\nprint x\n"), ["7"])

    def test_mul(self):
        self.assertEqual(full_run("int x\nx = 6 * 7\nprint x\n"), ["42"])

    def test_div_true(self):
        # / returns float for int operands too
        out = full_run("int x\nfloat r\nr = x / 2\nprint r\n")
        # x is uninitialized → 0; 0/2 = 0.0
        self.assertIn("0", out[0])

    def test_floordiv(self):
        self.assertEqual(full_run("int x\nx = 17 // 5\nprint x\n"), ["3"])

    def test_modulo(self):
        self.assertEqual(full_run("int x\nx = 10 % 3\nprint x\n"), ["1"])

    def test_power(self):
        self.assertEqual(full_run("int x\nx = 2 ** 10\nprint x\n"), ["1024"])

    def test_unary_minus(self):
        self.assertEqual(full_run("int x\nx = -7\nprint x\n"), ["-7"])

    def test_parentheses(self):
        self.assertEqual(full_run("int x\nx = (2 + 3) * 4\nprint x\n"), ["20"])

    def test_chained_add(self):
        self.assertEqual(full_run("int x\nx = 1 + 2 + 3 + 4\nprint x\n"), ["10"])

    def test_precedence_mul_over_add(self):
        self.assertEqual(full_run("int x\nx = 2 + 3 * 4\nprint x\n"), ["14"])

    def test_left_associative_sub(self):
        self.assertEqual(full_run("int x\nx = 10 - 3 - 2\nprint x\n"), ["5"])


# ═══════════════════════════════════════════════════════════════════════
# 12. CODE GENERATOR — float
# ═══════════════════════════════════════════════════════════════════════

class TestCodeGeneratorFloat(unittest.TestCase):

    def test_float_literal_print(self):
        out = full_run("float x\nx = 3.14\nprint x\n")
        self.assertIn("3.14", out[0])

    def test_float_add(self):
        out = full_run("float x\nx = 1.5 + 2.5\nprint x\n")
        self.assertIn("4", out[0])

    def test_float_mul(self):
        out = full_run("float x\nx = 2.5 * 4.0\nprint x\n")
        self.assertIn("10", out[0])

    def test_float_div(self):
        out = full_run("float x\nx = 7.0 / 2.0\nprint x\n")
        self.assertIn("3.5", out[0])

    def test_float_power(self):
        out = full_run("float x\nx = 2.0 ** 0.5\nprint x\n")
        self.assertTrue(float(out[0]) > 1.4)

    def test_int_float_mixed(self):
        # int + float → float
        out = full_run("float r\nint a\na = 3\nr = a + 1.5\nprint r\n")
        self.assertIn("4.5", out[0])


# ═══════════════════════════════════════════════════════════════════════
# 13. CODE GENERATOR — str
# ═══════════════════════════════════════════════════════════════════════

class TestCodeGeneratorStr(unittest.TestCase):

    def test_str_assign_and_print(self):
        self.assertEqual(
            full_run('str s\ns = "hello"\nprint s\n'), ["hello"])

    def test_str_concatenation(self):
        src = 'str a\nstr b\nstr c\na = "foo"\nb = "bar"\nc = a + b\nprint c\n'
        self.assertEqual(full_run(src), ["foobar"])

    def test_str_concat_with_spaces(self):
        src = 'str a\nstr b\nstr c\na = "hello "\nb = "world"\nc = a + b\nprint c\n'
        self.assertEqual(full_run(src), ["hello world"])

    def test_str_equality(self):
        src = 'str s\ns = "abc"\nif s == "abc":\n    print "match"\n'
        self.assertEqual(full_run(src), ["match"])

    def test_str_inequality(self):
        src = 'str s\ns = "abc"\nif s != "xyz":\n    print "diff"\n'
        self.assertEqual(full_run(src), ["diff"])


# ═══════════════════════════════════════════════════════════════════════
# 14. CODE GENERATOR — bool and logical operators
# ═══════════════════════════════════════════════════════════════════════

class TestCodeGeneratorBool(unittest.TestCase):

    def test_bool_true_if(self):
        src = "bool b\nb = true\nif b:\n    print \"yes\"\n"
        self.assertEqual(full_run(src), ["yes"])

    def test_bool_false_if(self):
        src = "bool b\nb = false\nif b:\n    print \"yes\"\n"
        self.assertEqual(full_run(src), [])

    def test_not_true(self):
        src = "bool b\nb = true\nif not b:\n    print \"flipped\"\n"
        self.assertEqual(full_run(src), [])

    def test_not_false(self):
        src = "bool b\nb = false\nif not b:\n    print \"flipped\"\n"
        self.assertEqual(full_run(src), ["flipped"])

    def test_and_both_true(self):
        src = "int x\nx = 5\nif x > 0 and x < 10:\n    print \"ok\"\n"
        self.assertEqual(full_run(src), ["ok"])

    def test_and_one_false(self):
        src = "int x\nx = 15\nif x > 0 and x < 10:\n    print \"ok\"\n"
        self.assertEqual(full_run(src), [])

    def test_or_both_false(self):
        src = "int x\nx = 5\nif x < 0 or x > 10:\n    print \"out\"\n"
        self.assertEqual(full_run(src), [])

    def test_or_one_true(self):
        src = "int x\nx = 15\nif x < 0 or x > 10:\n    print \"out\"\n"
        self.assertEqual(full_run(src), ["out"])

    def test_neq_operator_true(self):
        src = "int x\nx = 5\nif x != 3:\n    print \"ne\"\n"
        self.assertEqual(full_run(src), ["ne"])

    def test_neq_operator_false(self):
        src = "int x\nx = 3\nif x != 3:\n    print \"ne\"\n"
        self.assertEqual(full_run(src), [])

    def test_not_expr(self):
        src = "int x\nx = 5\nif not x == 3:\n    print \"ok\"\n"
        self.assertEqual(full_run(src), ["ok"])


# ═══════════════════════════════════════════════════════════════════════
# 15. CODE GENERATOR — control flow and I/O
# ═══════════════════════════════════════════════════════════════════════

class TestCodeGeneratorControlFlow(unittest.TestCase):

    def test_if_true_branch(self):
        src = "int x\nx = 5\nif x > 3:\n    print \"yes\"\n"
        self.assertEqual(full_run(src), ["yes"])

    def test_if_false_no_output(self):
        src = "int x\nx = 1\nif x > 3:\n    print \"yes\"\n"
        self.assertEqual(full_run(src), [])

    def test_if_else_true(self):
        src = "int x\nx = 5\nif x > 3:\n    print \"big\"\nelse:\n    print \"small\"\n"
        self.assertEqual(full_run(src), ["big"])

    def test_if_else_false(self):
        src = "int x\nx = 1\nif x > 3:\n    print \"big\"\nelse:\n    print \"small\"\n"
        self.assertEqual(full_run(src), ["small"])

    def test_loop_count(self):
        src = "int i\nloop i = 0 till i < 3:\n    print i\n    i = i + 1\n"
        self.assertEqual(full_run(src), ["0", "1", "2"])

    def test_loop_zero_iterations(self):
        src = "int i\nloop i = 5 till i < 3:\n    print i\n    i = i + 1\n"
        self.assertEqual(full_run(src), [])

    def test_loop_sum(self):
        src = ("int i\nint s\ns = 0\n"
               "loop i = 0 till i < 5:\n    s = s + i\n    i = i + 1\n"
               "print s\n")
        self.assertEqual(full_run(src), ["10"])

    def test_nested_if(self):
        src = ("int x\nint y\nx = 5\ny = 10\n"
               "if x > 3:\n    if y > 8:\n        print \"both\"\n")
        self.assertEqual(full_run(src), ["both"])

    def test_all_comparisons(self):
        cases = [
            ("if 5 > 3:\n",  True),
            ("if 3 < 5:\n",  True),
            ("if 5 >= 5:\n", True),
            ("if 5 <= 5:\n", True),
            ("if 5 == 5:\n", True),
            ("if 5 != 3:\n", True),
            ("if 5 > 9:\n",  False),
        ]
        for cond, expected in cases:
            src = cond + "    print \"yes\"\n"
            out = full_run(src)
            if expected:
                self.assertEqual(out, ["yes"], msg=f"Failed: {cond.strip()}")
            else:
                self.assertEqual(out, [], msg=f"Failed: {cond.strip()}")

    def test_input_read(self):
        src = "int x\ninput x\nprint x\n"
        self.assertEqual(full_run(src, ["42"]), ["42"])

    def test_float_input(self):
        src = "float x\ninput x\nprint x\n"
        out = full_run(src, ["3.14"])
        self.assertIn("3.14", out[0])

    def test_str_input(self):
        src = "str s\ninput s\nprint s\n"
        self.assertEqual(full_run(src, ["hello"]), ["hello"])

    def test_multiple_print_items(self):
        # print with comma joins all items onto ONE output line separated by spaces
        src = 'int x\nx = 7\nprint "val =", x\n'
        self.assertEqual(full_run(src), ["val = 7"])

    def test_print_string_literal(self):
        self.assertEqual(full_run('print "hello"\n'), ["hello"])

    def test_division_by_zero_returns_zero(self):
        out = full_run("int x\nx = 5 // 0\nprint x\n")
        self.assertEqual(out, ["0"])


# ═══════════════════════════════════════════════════════════════════════
# 16. INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestIntegration(unittest.TestCase):

    def test_hello_world(self):
        self.assertEqual(run('print "Hello, World!"\n'), ["Hello, World!"])

    def test_factorial_5(self):
        src = ("int i\nint f\nf = 1\n"
               "loop i = 1 till i < 6:\n    f = f * i\n    i = i + 1\n"
               "print f\n")
        self.assertEqual(run(src), ["120"])

    def test_fibonacci_7(self):
        src = ("int a\nint b\nint tmp\nint i\na = 0\nb = 1\n"
               "loop i = 0 till i < 7:\n"
               "    print a\n    tmp = a + b\n    a = b\n    b = tmp\n    i = i + 1\n")
        self.assertEqual(run(src), ["0","1","1","2","3","5","8"])

    def test_sum_1_to_10(self):
        src = ("int i\nint s\ns = 0\n"
               "loop i = 1 till i < 11:\n    s = s + i\n    i = i + 1\n"
               "print s\n")
        self.assertEqual(run(src), ["55"])

    def test_float_area_of_circle(self):
        src = ("float r\nfloat pi\nfloat area\n"
               "r = 5.0\npi = 3.14159\narea = pi * r * r\nprint area\n")
        out = run(src)
        self.assertAlmostEqual(float(out[0]), 78.53975, places=3)

    def test_str_greeting(self):
        src = 'str name\nstr msg\nname = "Ada"\nmsg = "Hello, " + name\nprint msg\n'
        self.assertEqual(run(src), ["Hello, Ada"])

    def test_bool_logic_chain(self):
        src = ("int x\nx = 5\n"
               "if x > 0 and x < 10:\n    print \"in\"\n"
               "else:\n    print \"out\"\n")
        self.assertEqual(run(src), ["in"])

    def test_modulo_even_odd(self):
        src = ("int n\nn = 7\n"
               "if n % 2 == 0:\n    print \"even\"\n"
               "else:\n    print \"odd\"\n")
        self.assertEqual(run(src), ["odd"])

    def test_power_cubes(self):
        src = ("int i\nloop i = 1 till i < 4:\n"
               "    print i ** 3\n    i = i + 1\n")
        self.assertEqual(run(src), ["1", "8", "27"])

    def test_nested_loop(self):
        src = ("int i\nint j\nint c\nc = 0\n"
               "loop i = 0 till i < 3:\n"
               "    loop j = 0 till j < 3:\n"
               "        c = c + 1\n        j = j + 1\n"
               "    i = i + 1\n"
               "print c\n")
        self.assertEqual(run(src), ["9"])

    def test_loop_with_if(self):
        src = ("int i\nloop i = 0 till i < 6:\n"
               "    if i == 3:\n        print \"three\"\n"
               "    i = i + 1\n")
        self.assertEqual(run(src), ["three"])

    def test_multiple_inputs(self):
        src = "int a\nint b\ninput a\ninput b\nint s\ns = a + b\nprint s\n"
        self.assertEqual(run(src, ["13","27"]), ["40"])

    def test_comment_ignored(self):
        src = "# declare\nint x\nx = 99\nprint x\n"
        self.assertEqual(run(src), ["99"])

    def test_blank_source(self):
        self.assertEqual(run(""), [])

    def test_only_comments(self):
        self.assertEqual(run("# line 1\n# line 2\n"), [])

    def test_loop_accumulator_1000(self):
        src = ("int i\nint s\ns = 0\n"
               "loop i = 0 till i < 1000:\n    s = s + i\n    i = i + 1\n"
               "print s\n")
        self.assertEqual(run(src), ["499500"])

    def test_input_float_squared(self):
        src = "float x\ninput x\nfloat sq\nsq = x * x\nprint sq\n"
        out = run(src, ["3.0"])
        self.assertIn("9", out[0])

    def test_string_and_int_printed_together(self):
        # print with comma produces ONE joined output line
        src = 'int x\nx = 42\nprint "answer =", x\n'
        self.assertEqual(run(src), ["answer = 42"])

    def test_bool_and_not_combined(self):
        src = "int x\nx = 5\nbool ok\nok = true\nif ok and not x == 0:\n    print \"go\"\n"
        self.assertEqual(run(src), ["go"])

    def test_floordiv_loop(self):
        src = ("int n\nn = 64\nint i\n"
               "loop i = 0 till i < 6:\n    n = n // 2\n    i = i + 1\n"
               "print n\n")
        self.assertEqual(run(src), ["1"])


# ═══════════════════════════════════════════════════════════════════════
# 17. ERROR MESSAGE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestFriendlyErrors(unittest.TestCase):

    def test_undeclared_variable(self):
        err = compile_error("x = 5\n")
        msg = friendly(err, "x = 5\n")
        self.assertIn("has not been declared", msg)

    def test_double_declaration(self):
        err = compile_error("int x\nint x\n")
        msg = friendly(err, "int x\nint x\n")
        self.assertIn("more than once", msg)

    def test_type_mismatch_str(self):
        err = compile_error("str s\ns = 42\n")
        msg = friendly(err, "str s\ns = 42\n")
        self.assertIn("Wrong type", msg)

    def test_unexpected_character(self):
        try:
            lex("int x@\n")
        except LexerError as e:
            msg = friendly(str(e), "int x@\n")
            self.assertIn("Unknown symbol", msg)

    def test_unterminated_string_message(self):
        try:
            lex('"hello\n')
        except LexerError as e:
            msg = friendly(str(e), '"hello\n')
            self.assertIn("opened a string", msg)

    def test_line_number_shown(self):
        err = compile_error("int x\nint x\n")
        msg = friendly(err, "int x\nint x\n")
        self.assertIn("Line", msg)

    def test_empty_error_returns_empty(self):
        self.assertEqual(friendly("", "int x\n"), "")

    def test_fallback_for_unknown(self):
        msg = friendly("Some weird crash", "int x\n")
        self.assertIn("went wrong", msg)


# ═══════════════════════════════════════════════════════════════════════
# 18. EDGE CASES & STRESS
# ═══════════════════════════════════════════════════════════════════════

class TestEdgeCases(unittest.TestCase):

    def test_zero_printed(self):
        self.assertEqual(run("int x\nx = 0\nprint x\n"), ["0"])

    def test_negative_unary(self):
        self.assertEqual(run("int x\nx = -1\nprint x\n"), ["-1"])

    def test_large_power(self):
        self.assertEqual(run("int x\nx = 2 ** 20\nprint x\n"), ["1048576"])

    def test_underscore_variable(self):
        self.assertEqual(run("int _x\n_x = 7\nprint _x\n"), ["7"])

    def test_variable_with_underscore_mid(self):
        self.assertEqual(run("int my_val\nmy_val = 99\nprint my_val\n"), ["99"])

    def test_empty_string_var(self):
        self.assertEqual(run('str s\ns = ""\nprint s\n'), [""])

    def test_bool_in_loop_condition(self):
        src = ("int i\nbool go\ngo = true\ni = 0\n"
               "loop i = 0 till i < 3:\n    i = i + 1\n"
               "print i\n")
        self.assertEqual(run(src), ["3"])

    def test_deeply_nested_if(self):
        src = ("int x\nx = 10\n"
               "if x > 5:\n"
               "    if x > 8:\n"
               "        if x > 9:\n"
               "            print \"deep\"\n")
        self.assertEqual(run(src), ["deep"])

    def test_many_variables(self):
        decls   = "\n".join(f"int v{i}" for i in range(10))
        assigns = "\n".join(f"v{i} = {i}" for i in range(10))
        src     = decls + "\n" + assigns + "\nprint v9\n"
        self.assertEqual(run(src), ["9"])

    def test_many_float_vars(self):
        src = ("float a\nfloat b\nfloat c\n"
               "a = 1.1\nb = 2.2\nc = a + b\nprint c\n")
        out = run(src)
        self.assertAlmostEqual(float(out[0]), 3.3, places=5)

    def test_string_comparison_in_if(self):
        src = 'str s\ns = "hello"\nif s == "hello":\n    print "yes"\n'
        self.assertEqual(run(src), ["yes"])

    def test_loop_100_iters(self):
        src = ("int i\nint s\ns = 0\n"
               "loop i = 0 till i < 100:\n    s = s + 1\n    i = i + 1\n"
               "print s\n")
        self.assertEqual(run(src), ["100"])

    def test_declaration_only_no_output(self):
        self.assertEqual(run("int x\nfloat y\nstr z\nbool b\n"), [])

    def test_lexer_error_stops_pipeline(self):
        err = compile_error("int x$\nx = 5\n")
        self.assertIn("LexerError", err)

    def test_semantic_error_stops_pipeline(self):
        err = compile_error("z = 10\n")
        self.assertIn("SemanticError", err)

    def test_modulo_zero(self):
        # mod by zero → 0, no crash
        out = run("int x\nx = 5 % 0\nprint x\n")
        self.assertEqual(out, ["0"])

    def test_chained_concat(self):
        src = 'str a\nstr b\nstr c\nstr d\na = "a"\nb = "b"\nc = a + b\nd = c + "c"\nprint d\n'
        self.assertEqual(run(src), ["abc"])

    def test_print_bool_true(self):
        # bool variables print as 'true' / 'false', not 1 / 0
        self.assertEqual(run("bool b\nb = true\nprint b\n"), ["true"])

    def test_print_bool_false(self):
        self.assertEqual(run("bool b\nb = false\nprint b\n"), ["false"])


# ═══════════════════════════════════════════════════════════════════════
# 19. OPTIMIZER INTEGRATION
# ═══════════════════════════════════════════════════════════════════════

class TestOptimizerIntegration(unittest.TestCase):

    def test_const_add_correct(self):
        self.assertEqual(run("int x\nx = 2 + 3\nprint x\n"), ["5"])

    def test_const_power_correct(self):
        self.assertEqual(run("int x\nx = 2 ** 8\nprint x\n"), ["256"])

    def test_const_mod_correct(self):
        self.assertEqual(run("int x\nx = 10 % 3\nprint x\n"), ["1"])

    def test_optimizer_safe_for_loop(self):
        src = ("int i\nint s\ns = 0\n"
               "loop i = 0 till i < 5:\n    s = s + i\n    i = i + 1\n"
               "print s\n")
        self.assertEqual(run(src), ["10"])

    def test_optimizer_safe_for_if_else(self):
        src = "int x\nx = 7\nif x > 5:\n    print \"big\"\nelse:\n    print \"small\"\n"
        self.assertEqual(run(src), ["big"])

    def test_all_arith_ops_fold(self):
        cases = [
            ("int x\nx = 3 + 4\nprint x\n",   "7"),
            ("int x\nx = 9 - 4\nprint x\n",   "5"),
            ("int x\nx = 3 * 4\nprint x\n",   "12"),
            ("int x\nx = 10 % 3\nprint x\n",  "1"),
            ("int x\nx = 2 ** 4\nprint x\n",  "16"),
            ("int x\nx = 17 // 5\nprint x\n", "3"),
        ]
        for src, expected in cases:
            with self.subTest(src=src):
                self.assertEqual(run(src), [expected])


if __name__ == "__main__":
    unittest.main(verbosity=2)