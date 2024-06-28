from pathlib import Path
from typing import Optional
import c2bf.compile.bfun.compilers.statement.all as statement
import c2bf.compile.bfun.compilers.function as function

from c2bf.compile.bfun.compilers.classes import transform_classes
from c2bf.compile.bfun.compilers.statement.forloops import transform_forloops
from c2bf.compile.bfasm.registers import REGISTERS
from c2bf.compile.bfun.compilers.string import transform_strings
from c2bf.compile.bfun.compilers.utils import get_scope, new_label, parse_asm
from c2bf.parser.ast import ASTNode

REGISTER_VARS = {r:r for r, _ in REGISTERS}

def collect_transform_vars(root_ast: ASTNode):
    def collect(ast: ASTNode):
        if ast == get_scope(ast):
            if not hasattr(ast, "vars"):
                setattr(ast, "vars", {})

        if ast.name == "function":
            function.collect_function(ast)
            return

        if ast.name != "e_assign":
            return
        unit = ast.get("e_unit")
        if unit[0].name != "REF":
            raise Exception("Invalid assignment")
        var_name = unit[0].literal.value
        if var_name in REGISTER_VARS:
            return
        scope_vars = getattr(get_scope(ast), "vars")
        if var_name not in scope_vars:
            scope_vars[var_name] = new_label(ast, f"var_{var_name}")

    ASTNode.transform(root_ast, collect)

def compile_program(ast: ASTNode, heap_size = 500, output_path: Optional[str | Path] = None):
    assert(ast == ast.root)
    assert(ast.name == "program")

    root_labels = set(x[0].literal.value for x in ast if x.name == "label")
    root_labels.update(REGISTER_VARS)
    root_labels.update({"__heap__", "__heap_data__", "__heap_end__"})
    setattr(ast, "labels", root_labels)

    
    if output_path:
        Path(output_path).joinpath("passes").mkdir(parents=True, exist_ok=True)
        with open(Path(output_path).joinpath("passes/code-0.bfun"), "w") as f:
            f.write(ast.to_string().strip())

    transform_strings(ast)
    if output_path:
        with open(Path(output_path).joinpath("passes/code-1-strings.bfun"), "w") as f:
            f.write(ast.to_string().strip())
    
    transform_classes(ast)
    if output_path:
        with open(Path(output_path).joinpath("passes/code-2-classes.bfun"), "w") as f:
            f.write(ast.to_string().strip())
    
    transform_forloops(ast)
    if output_path:
        with open(Path(output_path).joinpath("passes/code-3-floops.bfun"), "w") as f:
            f.write(ast.to_string().strip())

    collect_transform_vars(ast)

    asm_code = []
    for label in getattr(ast, "vars").values():
        asm_code.append(f"{label}: 0")
    
    for _, (chars, str_lbl, str_db_lbl, _) in getattr(ast, "strings").items():
        chars = [len(chars), *chars, 0]
        asm_code.append(f"{str_lbl}: ")
        asm_code.append(f"{str_db_lbl}: {', '.join(str(c) for c in chars)}")
        asm_code.append(f"add {str_lbl} 2")
    
    if asm_code:
        ast.children = parse_asm(";".join(asm_code)) + ast.children
        ast.index_children()

    i = 0
    while i < len(ast.children):
        child = ast.children[i]
        sub_compiler = lambda _: None
        if child.name == "function":
            sub_compiler = function.compile_function
        elif child.name == "statement":
            sub_compiler = statement.compile_statement
        
        if (result := sub_compiler(child)) is not None:
            if isinstance(result, ASTNode):
                ast.children[i] = result
                i += 1
            elif isinstance(result, list):
                ast.children[i:i+1] = result
                i += len(result)
            ast.index_children()
        else:
            i += 1

    heap_code = f"end; __heap__:; __heap_data__: 0, {heap_size}"
    heap_code += ", 0" * heap_size + "; __heap_end__:"
    ast.children.extend(parse_asm(heap_code))
    ast.index_children()

    return ast
