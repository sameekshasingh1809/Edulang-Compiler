"""
codegen.py — Stack-Based Target Code Generator for EduLang
===========================================================
Extended opcodes:
  MOD    — modulo
  POW    — power
  FDIV   — floor division
  NOT    — logical not
  AND    — logical and
  OR     — logical or
  NEG    — unary arithmetic negation
  PUSHF  — push float literal
  PUSHS  — push string literal (for str variables)
  CONCAT — pop two strings, push concatenation
"""

import operator as _op
from intermediate import (TACAssign, TACUnary, TACIfGoto,
                           TACGoto, TACLabel, TACPrint, TACRead)


class Instruction:
    def __init__(self, opcode: str, *args):
        self.opcode = opcode
        self.args   = args
    def __str__(self):
        if not self.args:
            return self.opcode
        # Special display for PRINTLINE — show as human-readable print list
        if self.opcode == "PRINTLINE":
            parts = []
            for desc in self.args[0]:
                if desc[0] == "literal":
                    parts.append(f'"{desc[1]}"')
                else:
                    parts.append("<value>")
            return f"{'PRINTLINE':<8} {', '.join(parts)}"
        return f"{self.opcode:<8} {' '.join(str(a) for a in self.args)}"


class CodeGenerator:
    def __init__(self):
        self._instrs: list = []

    def generate(self, tac: list) -> list:
        self._instrs = []
        for instr in tac:
            self._lower(instr)
        return self._instrs

    def _emit(self, opcode, *args):
        self._instrs.append(Instruction(opcode, *args))

    def _lower(self, instr):

        # ── Assignment ────────────────────────────────────────
        if isinstance(instr, TACAssign):
            # strlit sentinel: push the actual string value
            if isinstance(instr.arg1, tuple) and instr.arg1[0] == "strlit":
                self._emit("PUSHS", instr.arg1[1])
                self._emit("STORE", instr.result)
                return

            # boollit sentinel: push Python True/False so display shows true/false
            if isinstance(instr.arg1, tuple) and instr.arg1[0] == "boollit":
                self._emit("PUSHB", instr.arg1[1])
                self._emit("STORE", instr.result)
                return

            self._push_value(instr.arg1)

            if instr.op and instr.arg2 is not None:
                self._push_value(instr.arg2)
                OP_MAP = {
                    "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV",
                    "%": "MOD", "**": "POW", "//": "FDIV",
                    ">": "CMP", "<": "CMP", ">=": "CMP",
                    "<=": "CMP", "==": "CMP", "!=": "CMP",
                    "and": "AND", "or": "OR",
                }
                opcode = OP_MAP.get(instr.op, "ADD")
                if opcode == "CMP":
                    self._emit("CMP", instr.op)
                else:
                    self._emit(opcode)

                # Special-case: string concat
                if instr.op == "+":
                    # patch: replace ADD with CONCAT when needed at runtime
                    # We tag with CADD so the interpreter can choose
                    self._instrs.pop()   # remove ADD
                    self._emit("CADD")   # context-aware add

            self._emit("STORE", instr.result)
            return

        # ── Unary ─────────────────────────────────────────────
        if isinstance(instr, TACUnary):
            self._push_value(instr.arg)
            if instr.op == "-":
                self._emit("NEG")
            elif instr.op == "not":
                self._emit("NOT")
            self._emit("STORE", instr.result)
            return

        # ── Conditional jump ──────────────────────────────────
        if isinstance(instr, TACIfGoto):
            self._push_value(instr.left)
            self._push_value(instr.right)
            self._emit("CMP", instr.op)
            self._emit("JMPF", instr.label)
            return

        # ── Unconditional jump ────────────────────────────────
        if isinstance(instr, TACGoto):
            self._emit("JMP", instr.label); return

        # ── Label ─────────────────────────────────────────────
        if isinstance(instr, TACLabel):
            self._emit("LABEL", instr.name); return

        # ── Print ─────────────────────────────────────────────
        if isinstance(instr, TACPrint):
            # Collect each item's string value, then join and emit ONE output line
            parts = []
            for it in instr.items:
                if isinstance(it, str):
                    # plain string literal
                    parts.append(("literal", it))
                elif isinstance(it, tuple) and it[0] == "var":
                    # variable — emit a LOAD so runtime can pick it up
                    self._push_value(it[1])
                    parts.append(("stack", None))
                else:
                    self._push_value(it)
                    parts.append(("stack", None))
            self._emit("PRINTLINE", parts)
            return

        # ── Read ──────────────────────────────────────────────
        if isinstance(instr, TACRead):
            self._emit("READ", instr.var); return

    def _push_value(self, val):
        if isinstance(val, tuple) and val[0] == "strlit":
            self._emit("PUSHS", val[1]); return
        if isinstance(val, tuple) and val[0] == "boollit":
            self._emit("PUSHB", val[1]); return
        if isinstance(val, float):
            self._emit("PUSHF", val); return
        try:
            i = int(str(val))
            self._emit("PUSH", i)
        except (ValueError, TypeError):
            try:
                f = float(str(val))
                self._emit("PUSHF", f)
            except (ValueError, TypeError):
                self._emit("LOAD", val)

    # ── Execution ─────────────────────────────────────────────

    _CMP_OPS = {
        ">": _op.gt, "<": _op.lt, ">=": _op.ge,
        "<=": _op.le, "==": _op.eq, "!=": _op.ne,
    }

    def run(self, input_fn=None) -> list:
        if input_fn is None:
            input_fn = input

        label_map = {ins.args[0]: idx
                     for idx, ins in enumerate(self._instrs)
                     if ins.opcode == "LABEL"}

        stack  = []
        memory = {}
        output = []
        pc     = 0

        def _fmt(v):
            """Format a value for print output."""
            if isinstance(v, bool):
                return "true" if v else "false"
            if isinstance(v, float):
                s = f"{v:.10g}"
                if '.' not in s and 'e' not in s:
                    s += '.0'
                return s
            return str(v)

        while pc < len(self._instrs):
            ins = self._instrs[pc]
            op  = ins.opcode
            a   = ins.args
            pc += 1

            if   op == "PUSH":   stack.append(a[0])
            elif op == "PUSHF":  stack.append(float(a[0]))
            elif op == "PUSHS":  stack.append(str(a[0]))
            elif op == "PUSHB":  stack.append(bool(a[0]))   # Python True / False
            elif op == "LOAD":   stack.append(memory.get(a[0], 0))
            elif op == "STORE":  memory[a[0]] = stack.pop()

            elif op == "ADD":
                b, x = stack.pop(), stack.pop()
                stack.append(x + b)

            elif op == "CADD":   # context-aware add: numeric or string concat
                b, x = stack.pop(), stack.pop()
                if isinstance(x, str) or isinstance(b, str):
                    stack.append(str(x) + str(b))
                else:
                    stack.append(x + b)

            elif op == "SUB":
                b, x = stack.pop(), stack.pop(); stack.append(x - b)

            elif op == "MUL":
                b, x = stack.pop(), stack.pop(); stack.append(x * b)

            elif op == "DIV":
                b, x = stack.pop(), stack.pop()
                if b == 0:
                    stack.append(0)
                elif isinstance(x, float) or isinstance(b, float):
                    stack.append(x / b)
                else:
                    # int / int → integer result (floor toward zero)
                    stack.append(int(x / b))

            elif op == "FDIV":   # floor division //
                b, x = stack.pop(), stack.pop()
                stack.append(x // b if b != 0 else 0)

            elif op == "MOD":
                b, x = stack.pop(), stack.pop()
                stack.append(x % b if b != 0 else 0)

            elif op == "POW":
                b, x = stack.pop(), stack.pop()
                stack.append(x ** b)

            elif op == "NEG":
                stack.append(-stack.pop())

            elif op == "NOT":
                stack.append(int(not bool(stack.pop())))

            elif op == "AND":
                b, x = stack.pop(), stack.pop()
                stack.append(int(bool(x) and bool(b)))

            elif op == "OR":
                b, x = stack.pop(), stack.pop()
                stack.append(int(bool(x) or bool(b)))

            elif op == "CMP":
                b, x = stack.pop(), stack.pop()
                result = self._CMP_OPS[a[0]](x, b)
                stack.append(1 if result else 0)

            elif op == "JMPF":
                if stack.pop() != 0:
                    pc = label_map[a[0]] + 1

            elif op == "JMP":
                pc = label_map[a[0]] + 1

            elif op == "LABEL":
                pass

            elif op == "PRINTLINE":
                # a[0] is the parts list built during codegen
                # stack already has values for ("stack", None) slots pushed in order
                parts_desc = a[0]
                # collect from stack in reverse — we pushed left-to-right, pop right-to-left
                # but we need left-to-right order in output, so collect into a slot list
                slot_values = []
                for desc in reversed(parts_desc):
                    if desc[0] == "stack":
                        slot_values.append(_fmt(stack.pop()))
                    else:
                        slot_values.append(None)   # placeholder
                slot_values.reverse()

                result_parts = []
                stack_idx = 0
                for desc in parts_desc:
                    if desc[0] == "literal":
                        result_parts.append(str(desc[1]))
                    else:
                        result_parts.append(slot_values[stack_idx])
                    stack_idx += 1

                output.append(" ".join(result_parts))

            # Legacy single-item print opcodes (kept for any old codegen paths)
            elif op == "PRINT":
                output.append(_fmt(stack.pop()))

            elif op == "PRINTS":
                output.append(str(a[0]))

            elif op == "READ":
                try:
                    raw = input_fn(a[0])
                except TypeError:
                    raw = input_fn()
                # Try int, then float, then keep as string
                try:
                    memory[a[0]] = int(raw)
                except ValueError:
                    try:
                        memory[a[0]] = float(raw)
                    except ValueError:
                        memory[a[0]] = raw

        return output