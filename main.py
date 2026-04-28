"""
main.py — EduLang Compiler Pipeline
=====================================
Wires all compiler stages together.
"""

from lexer        import Lexer
from parser       import Parser
from semantic     import SemanticAnalyzer
from intermediate import TACGenerator
from optimizer    import optimize
from codegen      import CodeGenerator


def _section(title: str) -> str:
    return f"\n{'─'*20} {title} {'─'*20}\n"


def format_tokens(tokens) -> str:
    lines = [f"{'TYPE':<14} {'VALUE':<22} {'LINE':>4}  {'COL':>4}", "─" * 50]
    for t in tokens:
        lines.append(f"{t.type:<14} {t.value!r:<22} {t.line:>4}  {t.column:>4}")
    return "\n".join(lines)


def format_ast(node, indent: int = 0) -> str:
    from ast_nodes import (
        ProgramNode, DeclarationNode, AssignmentNode, InputNode,
        PrintNode, IfNode, LoopNode,
        BinaryOpNode, UnaryOpNode,
        NumberNode, FloatNode, StringNode, BoolNode, IdentifierNode,
    )
    pad  = "  " * indent
    if isinstance(node, ProgramNode):
        return pad + "Program\n" + "\n".join(format_ast(s, indent+1) for s in node.statements)
    if isinstance(node, DeclarationNode):
        return f"{pad}Declare({node.var_type} {node.name})"
    if isinstance(node, AssignmentNode):
        return f"{pad}Assign {node.name} =\n{format_ast(node.expr, indent+1)}"
    if isinstance(node, InputNode):
        return f"{pad}Input({node.name})"
    if isinstance(node, PrintNode):
        items = ", ".join(repr(i) if isinstance(i, str) else str(i) for i in node.items)
        return f"{pad}Print({items})"
    if isinstance(node, IfNode):
        body = "\n".join(format_ast(s, indent+2) for s in node.body)
        r = f"{pad}If\n{format_ast(node.condition,indent+1)}\n{'  '*(indent+1)}Body:\n{body}"
        if node.else_body:
            eb = "\n".join(format_ast(s, indent+2) for s in node.else_body)
            r += f"\n{'  '*(indent+1)}Else:\n{eb}"
        return r
    if isinstance(node, LoopNode):
        body = "\n".join(format_ast(s, indent+2) for s in node.body)
        return (f"{pad}Loop {node.var}\n"
                f"{'  '*(indent+1)}Init:\n{format_ast(node.init_expr,indent+2)}\n"
                f"{'  '*(indent+1)}Cond:\n{format_ast(node.condition,indent+2)}\n"
                f"{'  '*(indent+1)}Body:\n{body}")
    if isinstance(node, BinaryOpNode):
        return (f"{pad}BinOp({node.op})\n"
                f"{format_ast(node.left,indent+1)}\n"
                f"{format_ast(node.right,indent+1)}")
    if isinstance(node, UnaryOpNode):
        return f"{pad}UnaryOp({node.op})\n{format_ast(node.operand,indent+1)}"
    if isinstance(node, NumberNode):   return f"{pad}Num({node.value})"
    if isinstance(node, FloatNode):    return f"{pad}Float({node.value})"
    if isinstance(node, StringNode):   return f"{pad}Str({node.value!r})"
    if isinstance(node, BoolNode):     return f"{pad}Bool({node.value})"
    if isinstance(node, IdentifierNode): return f"{pad}Id({node.name})"
    return f"{pad}{type(node).__name__}"


def compile_source(source: str, input_fn=None):
    result = {
        "tokens": [], "ast": None, "ast_text": "",
        "symbol_table": None, "tac": [], "tac_opt": [],
        "target": [], "output": [], "error": None,
    }
    try:
        result["tokens"]       = Lexer(source).tokenize()
        ast                    = Parser(result["tokens"]).parse()
        result["ast"]          = ast
        result["ast_text"]     = format_ast(ast)
        result["symbol_table"] = SemanticAnalyzer().analyze(ast)
        result["tac"]          = TACGenerator().generate(ast)
        result["tac_opt"]      = optimize(result["tac"])
        cg                     = CodeGenerator()
        result["target"]       = cg.generate(result["tac_opt"])
        result["output"]       = cg.run(input_fn=input_fn)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def main():
    import sys
    if len(sys.argv) < 2:
        source = """\
int i
int sum
i = 0
sum = 0
loop i = 0 till i < 5:
    sum = sum + i
    i = i + 1
print "Result =", sum
"""
    else:
        with open(sys.argv[1]) as f:
            source = f.read()

    print("EduLang Compiler"); print("=" * 58)
    result = compile_source(source)
    if result["error"]:
        print(f"\n❌  {result['error']}"); return

    print(_section("TOKENS"))
    print(format_tokens(result["tokens"]))
    print(_section("AST"))
    print(result["ast_text"])
    print(_section("SYMBOL TABLE"))
    for n, t in result["symbol_table"].all_symbols().items():
        print(f"  {n}: {t}")
    print(_section("THREE ADDRESS CODE"))
    for i, ins in enumerate(result["tac"], 1):
        print(f"  {i:>3}.  {ins}")
    print(_section("OPTIMISED TAC"))
    for i, ins in enumerate(result["tac_opt"], 1):
        print(f"  {i:>3}.  {ins}")
    print(_section("TARGET (STACK) CODE"))
    for i, ins in enumerate(result["target"], 1):
        print(f"  {i:>3}.  {ins}")
    print(_section("OUTPUT"))
    for line in result["output"]:
        print(f"  {line}")


if __name__ == "__main__":
    main()
