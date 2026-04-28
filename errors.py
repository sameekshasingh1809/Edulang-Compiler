"""
errors.py — Human-Friendly Error Messages for EduLang
======================================================
Every message is written in plain, beginner-friendly English.
No compiler jargon. No raw internal error text shown to the user.
"""

import re

# ── Helpers ──────────────────────────────────────────────────

def _get_line(source: str, line_no: int) -> str:
    lines = source.splitlines()
    return lines[line_no - 1] if 1 <= line_no <= len(lines) else ""

def _pointer(col: int, line: str) -> str:
    """Return a '^' pointer aligned under column col of line."""
    prefix = len(line[:max(col - 1, 0)].expandtabs(4))
    return " " * prefix + "^"

def _indent(text: str, spaces: int = 6) -> str:
    """Indent every line of a multi-line string by `spaces` spaces."""
    pad = " " * spaces
    return "\n".join(pad + ln for ln in text.splitlines())

def _box(headline, location, src_line, col_no, what, fix):
    """Assemble the final error box."""
    W = 54
    out = []
    out.append("━" * W)
    out.append(f"  ❌  {headline}")
    out.append("━" * W)
    if location:
        out.append(f"\n  📍  {location}")
    if src_line:
        out.append(f"\n      {src_line}")
        if col_no:
            out.append(f"      {_pointer(col_no, src_line)}")
    if what:
        out.append(f"\n  ℹ   What went wrong:\n{_indent(what)}")
    if fix:
        out.append(f"\n  🔧  How to fix it:\n{_indent(fix)}")
    out.append("\n" + "━" * W)
    return "\n".join(out)


# ── Public API ────────────────────────────────────────────────

def friendly(raw_error: str, source: str) -> str:
    """Turn a raw EduLang exception into a plain-English error box."""
    if not raw_error:
        return ""
    msg = raw_error.strip()

    line_no, col_no = 0, 0
    m = re.search(r'line\s+(\d+)', msg, re.I)
    if m:
        line_no = int(m.group(1))
    m = re.search(r'col(?:umn)?\s+(\d+)', msg, re.I)
    if m:
        col_no = int(m.group(1))

    src_line = _get_line(source, line_no) if line_no else ""
    loc = (f"Line {line_no}" + (f", column {col_no}" if col_no else "")) if line_no else ""

    if "LexerError"    in msg: return _lex_error(msg, loc, src_line, col_no, line_no)
    if "ParseError"    in msg: return _parse_error(msg, loc, src_line, col_no)
    if "SemanticError" in msg: return _semantic_error(msg, loc, src_line, line_no)

    return _box(
        headline = "Something went wrong while compiling",
        location = loc, src_line = src_line, col_no = col_no,
        what = ("An unexpected error occurred inside the compiler.\n"
                "This is likely a bug in EduLang itself, not in your code."),
        fix  = ("Try simplifying your program to find which line causes the problem.\n"
                "If the problem keeps happening, report it to your instructor."),
    )


# ── Lexer errors ──────────────────────────────────────────────

def _lex_error(msg, loc, src_line, col_no, line_no):
    if "Unexpected character" in msg:
        ch_m = re.search(r"Unexpected character '(.+?)'", msg)
        ch   = ch_m.group(1) if ch_m else "?"
        return _box(
            headline = f"Unknown symbol  '{ch}'  found in your code",
            location = loc, src_line = src_line, col_no = col_no,
            what = (f"The symbol  '{ch}'  does not mean anything in EduLang.\n"
                    "EduLang only understands:\n"
                    "  • Letters and digits (for names and numbers)\n"
                    "  • Operators:  +  -  *  /  %  **  //\n"
                    "  • Comparisons:  ==  !=  <  >  <=  >=\n"
                    "  • Punctuation:  =  :  ,  (  )\n"
                    '  • Double quotes for strings:  "hello"'),
            fix  = (f"Remove or replace  '{ch}'  on line {line_no}.\n"
                    "Watch out for accidental symbols like  @  $  &  ;  etc."),
        )
    if "Unterminated string" in msg:
        return _box(
            headline = "You opened a string but never closed it",
            location = loc, src_line = src_line, col_no = col_no,
            what = ('A string must start AND end with double-quote  "  on the SAME line.\n'
                    "Your string is missing the closing  \"."),
            fix  = ('Add a closing  "  at the end of your text.\n'
                    "\n"
                    '  WRONG:   greeting = "Hello, World!\n'
                    '  RIGHT:   greeting = "Hello, World!"'),
        )
    if "Indentation" in msg:
        return _box(
            headline = "Indentation (spacing) is wrong on this line",
            location = loc, src_line = src_line, col_no = col_no,
            what = ("The spaces at the start of this line do not match\n"
                    "any surrounding block.\n"
                    "EduLang uses indentation to group lines together."),
            fix  = ("Use exactly 4 spaces per level. Do NOT mix tabs and spaces.\n"
                    "\n"
                    "  if x > 0:\n"
                    "      print x      ← 4 spaces before 'print'"),
        )
    return _box(
        headline = "Unreadable text found in your code",
        location = loc, src_line = src_line, col_no = col_no,
        what = "The compiler could not understand something on this line.",
        fix  = "Check the character at the indicated position for typos\nor symbols that do not belong in EduLang.",
    )


# ── Parse errors ──────────────────────────────────────────────

def _parse_error(msg, loc, src_line, col_no):
    stripped = src_line.strip() if src_line else ""

    # Missing colon
    if "COLON" in msg and "Expected" in msg:
        if stripped.startswith("if") or stripped.startswith("loop"):
            return _box(
                headline = "Missing  :  at the end of this line",
                location = loc, src_line = src_line, col_no = col_no,
                what = ("Every  if  and  loop  line must end with a colon  :\n"
                        "so EduLang knows a block of code is coming next."),
                fix  = ("Add  :  at the very end of the line.\n"
                        "\n"
                        "  WRONG:   if x > 5\n"
                        "  RIGHT:   if x > 5:"),
            )

    # Empty block body
    if "INDENT" in msg and "EOF" in msg:
        return _box(
            headline = "The body of your if / loop is empty",
            location = loc, src_line = src_line, col_no = col_no,
            what = ("You wrote  :  at the end of a line to start a block,\n"
                    "but there are no indented statements after it."),
            fix  = ("Add at least one statement indented by 4 spaces after the  :\n"
                    "\n"
                    "  if x > 0:\n"
                    "      print x      ← this is the body"),
        )

    # Missing indentation
    if "INDENT" in msg:
        return _box(
            headline = "Expected an indented block after the  :",
            location = loc, src_line = src_line, col_no = col_no,
            what = ("After  :  the next line must be indented by 4 spaces.\n"
                    "EduLang uses indentation to know where the block starts."),
            fix  = ("Add 4 spaces at the start of the line after  :\n"
                    "\n"
                    "  WRONG:\n"
                    "  if x > 0:\n"
                    "  print x\n"
                    "\n"
                    "  RIGHT:\n"
                    "  if x > 0:\n"
                    "      print x"),
        )

    # Missing 'till'
    if "TILL" in msg:
        return _box(
            headline = "Missing  till  in your loop",
            location = loc, src_line = src_line, col_no = col_no,
            what = ("A loop needs the word  till  to say:\n"
                    "\"keep looping TILL this condition becomes false\".\n"
                    "The word  till  is missing from your loop line."),
            fix  = ("Use this format:\n"
                    "\n"
                    "  loop <variable> = <start> till <condition>:\n"
                    "      <body>\n"
                    "\n"
                    "  Example:\n"
                    "  loop i = 0 till i < 10:\n"
                    "      print i\n"
                    "      i = i + 1"),
        )

    # == vs = confusion
    got_m = re.search(r"got '?([A-Z_]+)'?\s+\('?(.*?)'?\)", msg)
    got_v = (got_m.group(2).strip().strip("'\"") if got_m else "")
    got_t = (got_m.group(1) if got_m else "")

    if got_v == "==":
        return _box(
            headline = "Used  ==  where a single  =  was expected",
            location = loc, src_line = src_line, col_no = col_no,
            what = ("  ==  means \"check if equal\" (comparison).\n"
                    "   =  means \"store a value\" (assignment).\n"
                    "You used  ==  where you just wanted to store a value."),
            fix  = ("Change  ==  to  =  for assignment:\n"
                    "\n"
                    "  WRONG:   x == 5\n"
                    "  RIGHT:   x = 5"),
        )

    display_got = f"'{got_v}'" if got_v else f"an unexpected {got_t.lower()}" if got_t else "something unexpected"
    return _box(
        headline = f"Syntax error — found  {display_got}  where it was not expected",
        location = loc, src_line = src_line, col_no = col_no,
        what = (f"The compiler was reading your code and found {display_got}\n"
                "at a point where it did not make sense."),
        fix  = _parse_hint(stripped),
    )


def _parse_hint(line):
    s = line.strip()
    if s.startswith("loop"):
        return ("Check your loop format:\n"
                "\n"
                "  loop <variable> = <start> till <condition>:\n"
                "      <body>\n"
                "\n"
                "  Example:\n"
                "  loop i = 0 till i < 10:\n"
                "      i = i + 1")
    if s.startswith("if"):
        return ("Check your if format:\n"
                "\n"
                "  if <condition>:\n"
                "      <body>\n"
                "\n"
                "Make sure the line ends with  :  and uses\n"
                "comparison operators like  ==  !=  <  >  <=  >=")
    if s.startswith("print"):
        return ("Check your print format:\n"
                "  print <expression>\n"
                "  print \"text\", <variable>\n"
                '  print "some text"')
    return ("Common mistakes to check:\n"
            "  • Missing  :  at the end of an  if  or  loop  line\n"
            "  • Using  =  instead of  ==  in a condition\n"
            "  • Missing  (  )  around an expression\n"
            "  • Using  ^  instead of  **  for power")


# ── Semantic errors ───────────────────────────────────────────

def _semantic_error(msg, loc, src_line, line_no):
    var_m    = re.search(r"Variable '(.+?)'", msg)
    var      = var_m.group(1) if var_m else None
    assign_m = re.search(r"Cannot assign '(.+?)' to variable '(.+?)' of type '(.+?)'", msg)

    # Variable used before declaration
    if "used before declaration" in msg and var:
        return _box(
            headline = f"Variable  '{var}'  has not been declared yet",
            location = loc, src_line = src_line, col_no = 0,
            what = (f"You used  '{var}'  before telling EduLang what type it is.\n"
                    "In EduLang, every variable must be declared (introduced)\n"
                    "before you can use it."),
            fix  = (f"Add a declaration for  '{var}'  BEFORE line {line_no}.\n"
                    "Choose the type that fits what you want to store:\n"
                    "\n"
                    f"  int {var}      ← whole numbers  (1, 42, -5)\n"
                    f"  float {var}    ← decimal numbers  (3.14, 0.5)\n"
                    f"  str {var}      ← text  (\"hello\")\n"
                    f"  bool {var}     ← true or false"),
        )

    # Variable declared twice
    if "already declared" in msg and var:
        return _box(
            headline = f"Variable  '{var}'  is declared more than once",
            location = loc, src_line = src_line, col_no = 0,
            what = (f"You declared  '{var}'  twice.\n"
                    "Each variable can only be declared once in EduLang."),
            fix  = (f"Delete the second declaration of  '{var}'  on line {line_no}.\n"
                    "Keep only the first declaration."),
        )

    # Type mismatch — wrong value stored in variable
    if assign_m:
        rhs_type  = assign_m.group(1)
        var_name  = assign_m.group(2)
        decl_type = assign_m.group(3)
        type_desc = {
            "int":   "whole numbers  (e.g.  5, -3, 100)",
            "float": "decimal numbers  (e.g.  3.14, 0.5)",
            "str":   'text  (e.g.  "hello", "abc")',
            "bool":  "true  or  false  only",
        }
        val_desc = {
            "int": "a whole number", "float": "a decimal number",
            "str": "a text string",  "bool":  "a true/false value",
        }
        return _box(
            headline = f"Wrong type of value stored in  '{var_name}'",
            location = loc, src_line = src_line, col_no = 0,
            what = (f"'{var_name}'  was declared as  {decl_type},\n"
                    f"which only accepts {type_desc.get(decl_type, decl_type)}.\n"
                    f"But you are trying to put {val_desc.get(rhs_type, rhs_type)} into it."),
            fix  = (f"Option 1 — change the value to match  {decl_type}:\n"
                    f"  str variables need text:   {var_name} = \"some text\"\n"
                    f"  int variables need numbers: {var_name} = 42\n"
                    f"  bool variables need:        {var_name} = true\n"
                    f"\n"
                    f"Option 2 — change the declaration to match what you want:\n"
                    f"  Replace  {decl_type} {var_name}  with  {rhs_type} {var_name}"),
        )

    # Arithmetic on non-numeric types
    if "requires numeric" in msg or ("require" in msg and "numeric" in msg):
        return _box(
            headline = "Math operator used on a non-number",
            location = loc, src_line = src_line, col_no = 0,
            what = ("Operators like  +  -  *  /  only work on numbers (int or float).\n"
                    "You used one of them on a value that is not a number\n"
                    "(such as a string or a bool)."),
            fix  = ("Make sure both sides of the operator are numbers.\n"
                    "\n"
                    '  WRONG:  x = "hello" + 5\n'
                    "  WRONG:  x = true * 2\n"
                    "  RIGHT:  x = 3 + 5\n"
                    "\n"
                    "Note: you CAN join two strings with  +  if both are  str."),
        )

    # Incompatible comparison
    if "Cannot compare" in msg:
        cmp_m = re.search(r"Cannot compare '(.+?)' and '(.+?)'", msg)
        t1, t2 = (cmp_m.group(1), cmp_m.group(2)) if cmp_m else ("?", "?")
        return _box(
            headline = f"Cannot compare  {t1}  with  {t2}",
            location = loc, src_line = src_line, col_no = 0,
            what = (f"You are comparing a  {t1}  value with a  {t2}  value.\n"
                    "EduLang can only compare values of the same type\n"
                    "(e.g. int with int, or str with str)."),
            fix  = ("Make sure both sides of the comparison are the same type.\n"
                    "\n"
                    '  WRONG:  if x > "hello":      (int vs str)\n'
                    "  RIGHT:  if x > 5:             (int vs int)\n"
                    '  RIGHT:  if name == "Ada":     (str vs str)'),
        )

    # Generic fallback
    return _box(
        headline = "Variable or type error",
        location = loc, src_line = src_line, col_no = 0,
        what = ("There is a problem with how a variable or value is being used.\n"
                "This is usually a wrong type or a missing declaration."),
        fix  = ("Check:\n"
                "  • Every variable is declared before use  (int x / float x / etc.)\n"
                "  • You are not storing the wrong type  (e.g. a number into a str)\n"
                "  • Both sides of a comparison are the same type"),
    )