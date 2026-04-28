"""
optimizer.py — TAC Optimizer for EduLang
=========================================
Pass 1: Constant folding  (all arithmetic + comparison ops on literals)
Pass 2: Redundant assignment elimination
"""

from intermediate import TACAssign, TACUnary, TACIfGoto, TACGoto, TACLabel, TACPrint, TACRead


_OPS = {
    "+":   lambda a, b: a + b,
    "-":   lambda a, b: a - b,
    "*":   lambda a, b: a * b,
    "/":   lambda a, b: a / b  if b != 0 else None,
    "//":  lambda a, b: a // b if b != 0 else None,
    "%":   lambda a, b: a % b  if b != 0 else None,
    "**":  lambda a, b: a ** b,
    ">":   lambda a, b: int(a > b),
    "<":   lambda a, b: int(a < b),
    ">=":  lambda a, b: int(a >= b),
    "<=":  lambda a, b: int(a <= b),
    "==":  lambda a, b: int(a == b),
    "!=":  lambda a, b: int(a != b),
    "and": lambda a, b: int(bool(a) and bool(b)),
    "or":  lambda a, b: int(bool(a) or  bool(b)),
}

_UNARY_OPS = {
    "-":   lambda a: -a,
    "not": lambda a: int(not bool(a)),
}


def _is_numeric_literal(v) -> bool:
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, tuple):  # strlit sentinel
        return False
    try:
        float(str(v))
        return True
    except (ValueError, TypeError):
        return False


def _as_num(v):
    s = str(v)
    try:
        return int(s)
    except ValueError:
        return float(s)


# ── Pass 1 — Constant Folding ─────────────────────────────────

def constant_folding(instructions: list) -> list:
    result = []
    for instr in instructions:
        # Binary fold
        if (isinstance(instr, TACAssign)
                and instr.op is not None
                and instr.op in _OPS
                and _is_numeric_literal(instr.arg1)
                and _is_numeric_literal(instr.arg2)):
            folded = _OPS[instr.op](_as_num(instr.arg1), _as_num(instr.arg2))
            if folded is not None:
                result.append(TACAssign(instr.result, folded))
                continue

        # Unary fold
        if (isinstance(instr, TACUnary)
                and instr.op in _UNARY_OPS
                and _is_numeric_literal(instr.arg)):
            folded = _UNARY_OPS[instr.op](_as_num(instr.arg))
            result.append(TACAssign(instr.result, folded))
            continue

        result.append(instr)
    return result


# ── Pass 2 — Redundant Assignment Removal ─────────────────────

def remove_redundant_assignments(instructions: list) -> list:
    if not instructions:
        return instructions
    result = []
    i = 0
    while i < len(instructions):
        curr = instructions[i]
        if (i + 1 < len(instructions)
                and isinstance(curr, TACAssign)
                and isinstance(instructions[i + 1], TACAssign)
                and curr.result == instructions[i + 1].result):
            nxt = instructions[i + 1]
            used = {str(nxt.arg1), str(nxt.arg2)}
            if curr.result not in used:
                i += 1; continue
        result.append(curr)
        i += 1
    return result


# ── Entry point ───────────────────────────────────────────────

def optimize(instructions: list) -> list:
    code = constant_folding(instructions)
    code = remove_redundant_assignments(code)
    return code
