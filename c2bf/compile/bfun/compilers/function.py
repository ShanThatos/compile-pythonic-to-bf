import c2bf.compile.bfun.compilers.statement.all as all

from c2bf.compile.bfasm.registers import REGISTERS
from c2bf.compile.bfun.compilers.statement.expression import compile_expression
from c2bf.compile.bfun.compilers.utils import extend_label, get_scope, new_label, parse_asm, resolve_ref, tabs
from c2bf.parser.ast import ASTNode

REGISTER_VARS = {r for r, _ in REGISTERS}
RETURN_ATTR = "return_lbl"

def collect_function(ast: ASTNode):
    assert(ast.name == "function")
    func_name = ast.get("REF").literal.value
    if func_name in REGISTER_VARS:
        raise Exception(f"Invalid function name {func_name}")

    parent_scope_vars = getattr(get_scope(ast.parent), "vars")
    if func_name in parent_scope_vars:
        raise Exception(f"Function {func_name} already defined (possible as a variable?)")

    parent_scope_vars[func_name] = new_label(ast, f"func_{func_name}")
    ast.get("REF").literal.value = parent_scope_vars[func_name]

    func_scope_vars = getattr(get_scope(ast), "vars")
    params = ast.get("function_params").get_all("REF")

    if ast.get_all("variadic") and len(params) != 1:
        raise Exception("Variadic function must have exactly 1 parameter")
    for param in params:
        param_name = param.literal.value
        if param_name in REGISTER_VARS:
            raise Exception(f"Invalid parameter name {param_name}")
        if param_name in func_scope_vars:
            raise Exception(f"Parameter {param_name} already defined")
        func_scope_vars[param_name] = new_label(ast, f"param_{param_name}")

@tabs()
def compile_function(ast: ASTNode):
    assert(ast.name == "function")

    scope_vars = getattr(get_scope(ast), "vars", {})
    func_lbl = ast.get("REF").literal.value
    start_lbl = extend_label(ast, func_lbl, "start")
    end_lbl = extend_label(ast, func_lbl, "end")
    return_lbl = extend_label(ast, func_lbl, "return")
    setattr(ast, RETURN_ATTR, return_lbl)
    
    code = parse_asm(f"\n# function {func_lbl}\n; mov {func_lbl} {start_lbl}; jp {end_lbl}")

    for var_lbl in scope_vars.values():
        code += parse_asm(f"{var_lbl}: 0", tab=True)

    code += parse_asm(f"{start_lbl}:")
    for var_lbl in scope_vars.values():
        code += parse_asm(f"push {var_lbl}", tab=True)
    
    params = []
    if ast.get_all("variadic"):
        param_lbl = resolve_ref(ast, ast.get("function_params").literals[0].value)
        code += parse_asm(f"mov {param_lbl} _call_args", tab=True)
        params.append(param_lbl)
    else:
        param_refs = ast.get("function_params").get_all("REF")
        for i, param in enumerate(param_refs):
            if i > 0:
                code += parse_asm(f"inc _call_args", tab=True)
            param_lbl = resolve_ref(ast, param.literal.value)
            code += parse_asm(f"get {param_lbl} _call_args", tab=True)
            params.append(param_lbl)
        if param_refs:
            code += parse_asm(f"sub _call_args {len(param_refs) - 1}", tab=True)
    
    for var_lbl in scope_vars.values():
        if var_lbl not in params:
            code += parse_asm(f"mov {var_lbl} 0", tab=True)

    code += all.compile_statement(ast.get("statement"), tab=True)

    code += parse_asm(f"{return_lbl}:", tab=True)
    for var_lbl in reversed(scope_vars.values()):
        code += parse_asm(f"pop {var_lbl}", tab=True)
    code += parse_asm(f"ret rv", tab=True)
    code += parse_asm(f"{end_lbl}:")
    return code

@tabs()
def compile_return_statement(ast: ASTNode):
    parent = ast
    while parent and not hasattr(parent, RETURN_ATTR):
        parent = parent.parent
    if not parent:
        raise Exception("Invalid return statement")
    code = parse_asm(f"# return\n")
    expr_code, regs, _ = compile_expression(ast.get("expression"), tab=True)
    code += expr_code
    code += parse_asm(f"mov rv {regs[0]}")
    code += parse_asm(f"jp {getattr(parent, RETURN_ATTR)}")
    return code
