import c2bf.compile.bfun.compilers.statement.all as all

from c2bf.compile.bfun.compilers.statement.expression import compile_expression
from c2bf.compile.bfun.compilers.utils import new_label, parse_asm, tabs
from c2bf.parser.ast import ASTNode

CONTINUE_ATTR = "continue_lbl"
BREAK_ATTR = "break_lbl"

@tabs()
def compile_if_statement(ast: ASTNode):
    if ast.get_all("else"):
        return compile_if_else_statement(ast)

    code = parse_asm("# if statement")
    expr_code, expr_regs, _ = compile_expression(ast.get("expression"))
    code += expr_code
    end_lbl = new_label(ast, "if_end")
    code += parse_asm(f"jpz {end_lbl} {expr_regs[0]}")
    code += all.compile_statement(ast.get("statement"), tab=True)
    code += parse_asm(f"{end_lbl}:")
    return code

def compile_if_else_statement(ast: ASTNode):
    code = parse_asm("# if-else statement")
    expr_code, expr_regs, _ = compile_expression(ast.get("expression"))
    code += expr_code
    else_lbl = new_label(ast, "else")
    end_lbl = new_label(ast, "if_end")
    code += parse_asm(f"jpz {else_lbl} {expr_regs[0]}")
    code += all.compile_statement(ast.get("statement"), tab=True)
    code += parse_asm(f"jp {end_lbl}")
    code += parse_asm(f"{else_lbl}:")
    code += all.compile_statement(ast.get("statement", 1), tab=True)
    code += parse_asm(f"{end_lbl}:")
    return code


@tabs()
def compile_loop_statement(ast: ASTNode):
    if ast[0].name == "while_statement":
        return compile_while_statement(ast[0])
    raise Exception("Unexpected loop statement")

def compile_while_statement(ast: ASTNode):
    start_lbl = new_label(ast, "while_start")
    end_lbl = new_label(ast, "while_end")
    setattr(ast.parent, CONTINUE_ATTR, start_lbl)
    setattr(ast.parent, BREAK_ATTR, end_lbl)

    code = parse_asm("# while loop")
    code += parse_asm(f"{start_lbl}:")
    expr_code, expr_regs, _ = compile_expression(ast.get("expression"))
    code += expr_code
    code += parse_asm(f"jpz {end_lbl} {expr_regs[0]}")
    code += all.compile_statement(ast.get("statement"), tab=True)
    code += parse_asm(f"jp {start_lbl}")
    code += parse_asm(f"{end_lbl}:")
    return code

@tabs()
def compile_continue_statement(ast: ASTNode):
    parent = ast
    while parent and not hasattr(parent, CONTINUE_ATTR):
        parent = parent.parent
    if not parent:
        raise Exception("Invalid continue statement")
    return parse_asm(f"# continue\n; jp {getattr(parent, CONTINUE_ATTR)}")

@tabs()
def compile_break_statement(ast: ASTNode):
    parent = ast
    while parent and not hasattr(parent, BREAK_ATTR):
        parent = parent.parent
    if not parent:
        raise Exception("Invalid break statement")
    return parse_asm(f"# break\n; jp {getattr(parent, BREAK_ATTR)}")
