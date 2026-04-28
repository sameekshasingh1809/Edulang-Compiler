"""
lexer.py — Lexical Analyzer for EduLang
========================================
Tokenizes EduLang source code.

Datatypes:   int  float  str  bool
Bool literals: true  false
Operators:   +  -  *  /  %  **  //  >  <  >=  <=  ==  !=  and  or  not
"""

# ─────────────────────────────────────────────
# TOKEN TYPE CONSTANTS
# ─────────────────────────────────────────────

# Type declaration keywords
INT    = "INT"
FLOAT  = "FLOAT"
STR    = "STR"
BOOL   = "BOOL"

# Literal value keywords
TRUE   = "TRUE"
FALSE  = "FALSE"

# Control-flow keywords
INPUT  = "INPUT"
PRINT  = "PRINT"
IF     = "IF"
ELSE   = "ELSE"
LOOP   = "LOOP"
TILL   = "TILL"

# Logical keywords
AND    = "AND"
OR     = "OR"
NOT    = "NOT"

# Literal token types
IDENTIFIER = "IDENTIFIER"
NUMBER     = "NUMBER"      # integer  e.g. 42
FLOAT_LIT  = "FLOAT_LIT"  # float    e.g. 3.14
STRING     = "STRING"      # string   e.g. "hello"

# Arithmetic operators
PLUS     = "PLUS"      # +
MINUS    = "MINUS"     # -
MULTIPLY = "MULTIPLY"  # *
DIVIDE   = "DIVIDE"    # /
MODULO   = "MODULO"    # %
POWER    = "POWER"     # **
FLOORDIV = "FLOORDIV"  # //

# Relational operators
GT  = "GT"   # >
LT  = "LT"   # <
GTE = "GTE"  # >=
LTE = "LTE"  # <=
EQ  = "EQ"   # ==
NEQ = "NEQ"  # !=

# Assignment
ASSIGN = "ASSIGN"  # =

# Punctuation
COLON  = "COLON"
COMMA  = "COMMA"
LPAREN = "LPAREN"
RPAREN = "RPAREN"

# Indentation
INDENT = "INDENT"
DEDENT = "DEDENT"

# End of file
EOF = "EOF"

# ─────────────────────────────────────────────
# KEYWORD MAP
# ─────────────────────────────────────────────

KEYWORDS = {
    "int":   INT,
    "float": FLOAT,
    "str":   STR,
    "bool":  BOOL,
    "true":  TRUE,
    "false": FALSE,
    "input": INPUT,
    "print": PRINT,
    "if":    IF,
    "else":  ELSE,
    "loop":  LOOP,
    "till":  TILL,
    "and":   AND,
    "or":    OR,
    "not":   NOT,
}


# ─────────────────────────────────────────────
# TOKEN CLASS
# ─────────────────────────────────────────────

class Token:
    """A single token with type, raw value, line, and column."""

    def __init__(self, type: str, value: str, line: int = 0, column: int = 0):
        self.type   = type
        self.value  = value
        self.line   = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line}, col={self.column})"


# ─────────────────────────────────────────────
# LEXER ERROR
# ─────────────────────────────────────────────

class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"LexerError at line {line}, col {column}: {message}")
        self.line   = line
        self.column = column


# ─────────────────────────────────────────────
# LEXER
# ─────────────────────────────────────────────

class Lexer:
    """Tokenizes EduLang source into a flat list of Token objects."""

    def __init__(self, source: str):
        self.lines        = source.splitlines()
        self.source       = source
        self.pos          = 0
        self.line         = 1
        self.column       = 1
        self.indent_stack = [0]
        self.tokens       = []

    # ── Public API ─────────────────────────────

    def tokenize(self) -> list:
        for idx, raw in enumerate(self.lines):
            lineno = idx + 1
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            self.handle_indentation(raw, lineno)
            col_start = len(raw) - len(raw.lstrip(" "))
            self.pos    = self._line_start_pos(idx) + col_start
            self.line   = lineno
            self.column = col_start + 1
            while self.pos < len(self.source) and self.source[self.pos] != "\n":
                tok = self.get_next_token()
                if tok is not None:
                    self.tokens.append(tok)

        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(DEDENT, "", self.line, 1))
        self.tokens.append(Token(EOF, "", self.line, self.column))
        return self.tokens

    def get_next_token(self):
        if self.pos >= len(self.source):
            return Token(EOF, "", self.line, self.column)

        ch  = self.source[self.pos]
        nxt = self._peek()

        # skip whitespace / comments / newlines
        if ch in (" ", "\t"):     self._advance(); return None
        if ch == "#":
            while self.pos < len(self.source) and self.source[self.pos] != "\n":
                self._advance()
            return None
        if ch == "\n":            self._advance(); return None

        # string literal
        if ch == '"':             return self._read_string()

        # number literal (integer or float)
        if ch.isdigit() or (ch == "." and nxt.isdigit()):
            return self._read_number()

        # identifier / keyword
        if ch.isalpha() or ch == "_":
            return self._read_identifier_or_keyword()

        # ── multi-char operators — longest match first ──────
        if ch == "*" and nxt == "*":   return self._make_token(POWER,    "**", 2)
        if ch == "/" and nxt == "/":   return self._make_token(FLOORDIV, "//", 2)
        if ch == ">" and nxt == "=":   return self._make_token(GTE,      ">=", 2)
        if ch == "<" and nxt == "=":   return self._make_token(LTE,      "<=", 2)
        if ch == "=" and nxt == "=":   return self._make_token(EQ,       "==", 2)
        if ch == "!" and nxt == "=":   return self._make_token(NEQ,      "!=", 2)

        # ── single-char ─────────────────────────────────────
        SINGLE = {
            "+": PLUS, "-": MINUS, "*": MULTIPLY, "/": DIVIDE, "%": MODULO,
            ">": GT, "<": LT, "=": ASSIGN,
            ":": COLON, ",": COMMA, "(": LPAREN, ")": RPAREN,
        }
        if ch in SINGLE:
            return self._make_token(SINGLE[ch], ch, 1)

        raise LexerError(f"Unexpected character {ch!r}", self.line, self.column)

    def handle_indentation(self, raw_line: str, line_number: int):
        level = len(raw_line) - len(raw_line.lstrip(" "))
        top   = self.indent_stack[-1]
        if level > top:
            self.indent_stack.append(level)
            self.tokens.append(Token(INDENT, "", line_number, 1))
        elif level < top:
            while self.indent_stack[-1] > level:
                self.indent_stack.pop()
                self.tokens.append(Token(DEDENT, "", line_number, 1))
            if self.indent_stack[-1] != level:
                raise LexerError(
                    f"Indentation level {level} does not match any outer level",
                    line_number, 1)

    # ── Helpers ─────────────────────────────────

    def _advance(self) -> str:
        ch = self.source[self.pos]; self.pos += 1
        if ch == "\n": self.line += 1; self.column = 1
        else:          self.column += 1
        return ch

    def _peek(self) -> str:
        n = self.pos + 1
        return self.source[n] if n < len(self.source) else ""

    def _make_token(self, ttype, value, length):
        tok = Token(ttype, value, self.line, self.column)
        for _ in range(length): self._advance()
        return tok

    def _read_string(self):
        sl, sc = self.line, self.column
        self._advance()   # consume opening "
        chars = []
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == '"':
                self._advance()
                return Token(STRING, "".join(chars), sl, sc)
            if ch == "\n":
                break
            if ch == "\\" and self.pos + 1 < len(self.source):
                ESC = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}
                nxt = self.source[self.pos + 1]
                if nxt in ESC:
                    self._advance(); self._advance()
                    chars.append(ESC[nxt]); continue
            chars.append(ch); self._advance()
        raise LexerError("Unterminated string literal", sl, sc)

    def _read_number(self):
        sc     = self.column
        digits = []
        # integer part
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            digits.append(self.source[self.pos]); self._advance()
        # optional decimal
        is_float = False
        if (self.pos < len(self.source) and self.source[self.pos] == "."
                and self.pos + 1 < len(self.source)
                and self.source[self.pos + 1].isdigit()):
            is_float = True
            digits.append("."); self._advance()
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                digits.append(self.source[self.pos]); self._advance()
        raw = "".join(digits)
        return Token(FLOAT_LIT if is_float else NUMBER, raw, self.line, sc)

    def _read_identifier_or_keyword(self):
        sc    = self.column
        chars = []
        while (self.pos < len(self.source) and
               (self.source[self.pos].isalnum() or self.source[self.pos] == "_")):
            chars.append(self.source[self.pos]); self._advance()
        word = "".join(chars)
        return Token(KEYWORDS.get(word, IDENTIFIER), word, self.line, sc)

    def _line_start_pos(self, line_index: int) -> int:
        pos = 0
        for i in range(line_index):
            pos += len(self.lines[i]) + 1
        return pos


# ─────────────────────────────────────────────
# PRETTY PRINTER
# ─────────────────────────────────────────────

def print_tokens(tokens):
    print(f"{'TYPE':<14} {'VALUE':<22} {'LINE':>4}  {'COL':>4}")
    print("-" * 50)
    for t in tokens:
        print(f"{t.type:<14} {t.value!r:<22} {t.line:>4}  {t.column:>4}")
