from typing import Callable, Dict, List
from c2bf.compile.bfun.compilers.function import compile_return_statement
from c2bf.compile.bfun.compilers.statement.control import compile_break_statement, compile_continue_statement, compile_if_statement, compile_loop_statement
from c2bf.compile.bfun.compilers.statement.expression import compile_expression_statement
from c2bf.compile.bfun.compilers.utils import alwaystab, parse_asm, resolve_ref
from c2bf.parser.ast import ASTNode


@alwaystab
def compile_statement_block(ast: ASTNode):
    return sum((compile_statement(stmt) for stmt in ast.get_all("statement")), [])

def compile_as_self(ast: ASTNode, *args, **kwargs):
    return [ast]

def compile_label_array(ast: ASTNode, *args, **kwargs):
    lbl = ast.get("REF").literal.value
    num = int(ast.get("NUMBER").literal.value)
    if num < 0:
        raise Exception("Invalid array size")
    return parse_asm(f"{lbl}: {', '.join('0' for _ in range(num))}")

def compile_instruction(ast: ASTNode, *args, **kwargs):
    for literal in ast.literals:
        if literal.name == "REF":
            literal.value = resolve_ref(ast, literal.value)
    return [ast]

STMT_COMPILERS: Dict[str, Callable[[ASTNode], List[ASTNode]]] = {
    "label": compile_as_self,
    "label_array": compile_label_array,
    "COMMENT": compile_as_self,
    "instruction": compile_instruction,
    "statement_block": compile_statement_block,
    "expression_statement": compile_expression_statement,
    "if_statement": compile_if_statement,
    "loop_statement": compile_loop_statement,
    "continue_statement": compile_continue_statement,
    "break_statement": compile_break_statement,
    "return_statement": compile_return_statement,
}

def compile_statement(ast: ASTNode, *args, **kwargs) -> List[ASTNode]:
    assert(ast.name == "statement")
    if stmt_compiler := STMT_COMPILERS.get(ast[0].name):
        return stmt_compiler(ast[0], *args, **kwargs)
    raise Exception(f"Unsupported statement type {ast[0].name}\n\t{ast[0].to_string()}")
