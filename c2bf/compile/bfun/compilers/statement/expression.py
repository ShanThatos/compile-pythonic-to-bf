from typing import List, Tuple, Optional
from c2bf.compile.bfasm.registers import REGISTERS
from c2bf.compile.bfun.compilers.utils import alwaystab, get_scope, new_label, parse_asm, resolve_ref, tabs, copy_whitespace
from c2bf.parser.ast import ASTNode

def is_er(reg: str):
    return (len(reg) == 2 and reg[0] == "e" and reg[1:].isdigit()) or reg == "et"

ALL_REGS = [r for r, _ in REGISTERS]
ERS = [r for r, _ in REGISTERS if r[0] == "e" and r[1:].isdigit()]

next_pick_index = 0
def pick_reg(regs: List[List[str]]):
    global next_pick_index
    next_pick_index += 1
    key = lambda r: sum(1 for rs in regs[1:] if r in rs)
    er_vals = sorted((key(er), er) for er in ERS)
    good_ers = [er for val, er in er_vals if val == er_vals[0][0]]
    return good_ers[next_pick_index % len(good_ers)]

next_cycle_reg = 0
def cycle_reg():
    global next_cycle_reg
    ret = ERS[next_cycle_reg]
    next_cycle_reg = (next_cycle_reg + 1) % len(ERS)
    return ret

@tabs()
def compile_expression_statement(ast: ASTNode):
    return optimize_expression(compile_expression(ast[0], False)[0])


type ExprCompileResult = Tuple[List[ASTNode], List[str], bool]

@alwaystab
def compile_expression(ast: ASTNode) -> ExprCompileResult:
    if ast[0].name == "e_assign":
        return compile_assign(ast[0], False)
    code, regs, const = compile_lor(ast[0], False)
    if code:
        expr_comment = parse_asm(f"# expr: {ast.to_string().replace("\n", "").strip()}")
        expr_comment[0].literals[0].whitespace = "\n"
        code = expr_comment + code
    return code, regs, const

ASSIGN_OP_MAP = {
    "=": "mov",
    "+=": "add",
    "-=": "sub",
    "*=": "mul",
}
@alwaystab
def compile_assign(ast: ASTNode) -> ExprCompileResult:
    unit = ast.get("e_unit")
    refs = unit.get_all("e_ref")
    op_ins = ASSIGN_OP_MAP.get(ast.get("e_assign_op")[0].literal.value, None)

    if not op_ins:
        raise Exception(f"Unsupported assignment operator {op_ins}")

    code, regs, const = compile_expression(ast.get("expression"))

    if len(refs) == 0:
        if unit[0].name == "REF":
            var_label = resolve_ref(ast, unit[0].literal.value)
            code += parse_asm(f"{op_ins} {var_label} {regs[0]}")
            return code, [var_label] + regs, True
        raise Exception(f"Invalid assignment {ast.to_string()}")
    
    last_ref = refs[-1][0]
    if last_ref.name not in ("e_index", "e_dot"):
        raise Exception(f"Invalid assignment {ast.to_string()}\n\nExpected index or dot operator")
    
    unit.children.pop()
    unit.index_children()

    compiled_unit = compile_unit(unit)
    if last_ref.name == "e_index":
        compiled_unit = compile_index(compiled_unit, last_ref, get_value=False)
    elif last_ref.name == "e_dot":
        compiled_unit = compile_dot(compiled_unit, last_ref, get_value=False)
    else:
        raise NotImplementedError()

    unit_code, unit_regs, _ = compiled_unit

    if regs[0] in unit_regs:
        sub_reg = next((r for r in ERS if r not in unit_regs), None)
        const = False
        if sub_reg is None:
            code += parse_asm(f"push {regs[0]}")
            regs.insert(0, next(r for r in ERS if r != unit_regs[0]))
            unit_code += parse_asm(f"pop {regs[0]}")
        else:
            code += parse_asm(f"mov {sub_reg} {regs[0]}")
            regs.insert(0, sub_reg)

    code += unit_code
    if op_ins == "mov":
        code += parse_asm(f"set {unit_regs[0]} {regs[0]}")
    else:
        code += parse_asm(f"get et {unit_regs[0]}; {op_ins} et {regs[0]}; set {unit_regs[0]} et")
        if const:
            regs.insert(0, next(r for r in ERS if r != unit_regs[0]))
            const = False
        code += parse_asm(f"mov {regs[0]} et")
    
    return code, [*regs, *unit_regs], const

@alwaystab
def compile_lor(ast: ASTNode) -> ExprCompileResult:
    def compile_lor_sub(a, b):
        lbl = new_label(ast, "lor_")
        return parse_asm(f"jpif {lbl} {a}; mov {a} {b}; {lbl}:")
    return compile_op_delim(ast, compile_land, {"or": compile_lor_sub})

@alwaystab
def compile_land(ast: ASTNode) -> ExprCompileResult:
    def compile_land_sub(a, b):
        lbl = new_label(ast, "land_")
        return parse_asm(f"jpz {lbl} {a}; mov {a} {b}; {lbl}:")
    return compile_op_delim(ast, compile_rel, {"and": compile_land_sub})

@alwaystab
def compile_rel(ast: ASTNode) -> ExprCompileResult:
    sub_units = ast.get_all("e_add")
    if len(sub_units) == 1:
        code, regs, const = compile_add(sub_units[0])
    else:
        a_code, a_regs, _ = compile_add(ast[0])
        b_code, b_regs, _ = compile_add(ast[2])

        if a_regs[0] in b_regs:
            a_sub_reg = next((r for r in ("cr", *ERS) if r not in b_regs), None)
            if a_sub_reg is None:
                a_code += parse_asm(f"push {a_regs[0]}")
                b_code += parse_asm(f"pop et")
                a_regs.insert(0, "et")
            else:
                a_code += parse_asm(f"mov {a_sub_reg} {a_regs[0]}")
                a_regs.insert(0, a_sub_reg)

        code = a_code + b_code
        OP_MAP = {
            "==": lambda a,b: parse_asm(f"cmp {a} {b}; dec cr; not cr"),
            "!=": lambda a,b: parse_asm(f"cmp {a} {b}; dec cr; norm cr"),
            "<": lambda a,b: parse_asm(f"cmp {a} {b}; not cr"),
            "<=": lambda a,b: parse_asm(f"cmp {b} {a}; norm cr"),
            ">": lambda a,b: parse_asm(f"cmp {b} {a}; not cr"),
            ">=": lambda a,b: parse_asm(f"cmp {a} {b}; norm cr"),
        }
        code += OP_MAP[ast[1].literal.value](a_regs[0], b_regs[0])
        regs = ["cr", *a_regs, *b_regs]
        const = True
    
    return code, regs, const

@alwaystab
def compile_add(ast: ASTNode) -> ExprCompileResult:
    return compile_op_delim(ast, compile_mul, {"+": "add", "-": "sub"})

@alwaystab
def compile_mul(ast: ASTNode) -> ExprCompileResult:
    OP_MAP = {
        "*": "mul",
        "/": lambda a,b: parse_asm(f"mov r0 {a}; mov r1 {b}; call __divmod__; mov {a} rv"),
        "%": lambda a,b: parse_asm(f"mov r0 {a}; mov r1 {b}; call __divmod__; mov {a} r0")
    }

    code, regs, const = compile_op_delim(ast, compile_neg, OP_MAP)
    if ast.get_all("/") or ast.get_all("%"):
        regs = [regs[0], *ALL_REGS, *regs]
    return code, regs, const

def compile_op_delim(ast: ASTNode, sub_compile, op_map) -> ExprCompileResult:
    result = sub_compile(ast[0])
    if len(ast.children) == 1:
        return result

    ops = []
    results = [result]
    for i in range(1, len(ast.children), 2):
        ops.append(ast[i].name)
        results.append(sub_compile(ast[i + 1]))
    
    all_regs = [r[1] for r in results]
    breg = pick_reg(all_regs)
    code, regs, _ = result
    if breg != regs[0]:
        code += parse_asm(f"mov {breg} {regs[0]}")
    for (op, (ncode, nregs, _)) in zip(ops, results[1:]):
        if breg in nregs:
            ncode = parse_asm(f"push {breg}") + ncode
            if breg == nregs[0]:
                ncode += parse_asm(f"mov et {nregs[0]}")
                nregs.insert(0, "et")
            ncode += parse_asm(f"pop {breg}")
        code += ncode

        if op not in op_map:
            raise Exception(f"Unsupported operator {op}")
        
        op_entry = op_map[op]
        if isinstance(op_entry, str):
            code += parse_asm(f"{op_entry} {breg} {nregs[0]}")
        else:
            code += op_entry(breg, nregs[0])
    
    flat_regs = list({r for regs in all_regs for r in regs})
    return code, [breg] + flat_regs, False

@alwaystab
def compile_neg(ast: ASTNode) -> ExprCompileResult:
    result = compile_unit(ast.get("e_unit"))
    num_negs = len(ast.get_all("-"))
    if num_negs % 2 == 0:
        return result
    
    code, regs, const = result
    if const:
        er = cycle_reg()
        code += parse_asm(f"mov {er} {regs[0]}")
        regs.insert(0, er)
    code += parse_asm(f"neg {regs[0]}")
    return code, regs, False

@alwaystab
def compile_unit(ast: ASTNode) -> ExprCompileResult:
    result = compile_base_unit(ast[0])
    for ref in ast.get_all("e_ref"):
        result = compile_ref(result, ref[0])
    return result

def compile_base_unit(unit: ASTNode) -> ExprCompileResult:
    if unit.name == "NUMBER":
        return [], [unit.literal.value], True
    if unit.name == "REF":
        if is_er(unit.literal.value):
            raise Exception("Cannot explicitly use expression registers in expressions")
        return [], [resolve_ref(unit, unit.literal.value)], True
    if unit.name == "e_par":
        return compile_expression(unit.get("expression"))
    if unit.name == "e_not":
        return compile_not(unit)

    raise NotImplementedError(f"Unsupported unit type {unit.name} {unit.to_string()}")

@alwaystab
def compile_not(ast: ASTNode) -> ExprCompileResult:
    code, regs, const = compile_unit(ast.get("e_unit"))
    er = cycle_reg()
    if const:
        code += parse_asm(f"mov {er} {regs[0]}")
        regs.insert(0, er)
    
    num_nots = len(ast.get_all("!"))
    ins = ("norm", "not")[num_nots % 2]
    code += parse_asm(f"{ins} {regs[0]}")
    return code, regs, False

def compile_ref(compiled_unit: ExprCompileResult, ref: ASTNode) -> ExprCompileResult:
    if ref.name == "e_index":
        return compile_index(compiled_unit, ref)
    elif ref.name == "e_call":
        return compile_call(compiled_unit, ref)
    elif ref.name == "e_dot":
        return compile_dot(compiled_unit, ref)
    raise NotImplementedError()

def compile_index(compiled_unit: ExprCompileResult, ref: ASTNode, get_value=True) -> ExprCompileResult:
    # DUNDER INDEXING IMPLEMENTATION
    code, regs, const = compiled_unit
    expr_code, expr_regs, expr_const = compile_expression(ref.get("expression"))

    if regs[0] in expr_regs or (const and expr_const):
        sub_reg = next((r for r in ERS if r not in expr_regs), None)
        if sub_reg is None:
            code += parse_asm(f"push {regs[0]}")
            regs.insert(0, next(r for r in ERS if r != expr_regs[0]))
            expr_code += parse_asm(f"pop {regs[0]}")
        else:
            code += parse_asm(f"mov {sub_reg} {regs[0]}")
            regs.insert(0, sub_reg)
        const = False
    
    code += expr_code

    dunder_index_lbl = new_label(ref, "dunder_index_")
    index_end_lbl = new_label(ref, "index_end_")
    code += parse_asm(f"getf cr {regs[0]}; dec cr; jpz {dunder_index_lbl} cr")
    code += parse_asm(f"mov rv {regs[0]}; add rv {expr_regs[0]}; jp {index_end_lbl}")
    code += parse_asm(f"{dunder_index_lbl}:; mov r0 {regs[0]}; mov r1 {expr_regs[0]}; call __findindex__; {index_end_lbl}:")

    er = cycle_reg()
    if get_value:
        code += parse_asm(f"get {er} rv")
    else:
        code += parse_asm(f"mov {er} rv")
    
    return code, [er, *ALL_REGS, *regs, *expr_regs], False

    # DEFAULT INDEXING IMPLEMENTATION
    # code, regs, const = compiled_unit
    # expr_code, expr_regs, expr_const = compile_expression(ref.get("expression"))

    # if regs[0] in expr_regs or (const and expr_const):
    #     sub_reg = next((r for r in ERS if r not in expr_regs), None)
    #     if sub_reg is None:
    #         code += parse_asm(f"push {regs[0]}")
    #         regs.insert(0, next(r for r in ERS if r != expr_regs[0]))
    #         expr_code += parse_asm(f"pop {regs[0]}")
    #     else:
    #         code += parse_asm(f"mov {sub_reg} {regs[0]}")
    #         regs.insert(0, sub_reg)
    #     const = False

    # ret_reg = expr_regs[0] if const else regs[0]
    # other_reg = regs[0] if const else expr_regs[0]
    # code += expr_code
    # code += parse_asm(f"add {ret_reg} {other_reg}")
    # if get_value:
    #     code += parse_asm(f"get {ret_reg} {ret_reg}")
    
    # return code, [ret_reg, other_reg] + regs + expr_regs, False

def compile_call(compiled_unit: ExprCompileResult, ref: ASTNode) -> ExprCompileResult:
    code, regs, const = compiled_unit
    er = cycle_reg()
    
    args = ref.get_all("expression")
    if len(args) == 0:
        code += parse_asm(f"push _call_args; mov _call_args __heap_empty_block__; call {regs[0]}; mov {er} rv; pop _call_args")
        return code, [er, *ALL_REGS, *regs], False
    
    use_call_func = not const
    full_args_code = []
    all_args_regs = []
    for i, arg in enumerate(args):
        if i > 0:
            full_args_code += parse_asm(f"inc _call_args")
        arg_code, arg_regs, _ = compile_expression(arg)
        if regs[0] in arg_regs:
            use_call_func = True
        full_args_code += parse_asm(f"# arg {i}") + arg_code
        full_args_code += parse_asm(f"set _call_args {arg_regs[0]}")
        all_args_regs.extend(arg_regs)
    full_args_code += parse_asm(f"sub _call_args {len(args) - 1}")

    if use_call_func:
        code += parse_asm(f"push _call_func; mov _call_func {regs[0]}")

    code += parse_asm(f"push _call_args; mov r0 {len(args)}; call __malloc__; mov _call_args rv")
    code += full_args_code

    if use_call_func:
        code += parse_asm(f"call _call_func")
    else:
        code += parse_asm(f"call {regs[0]}")

    code += parse_asm(f"mov {er} rv; mov r0 _call_args; call __free__; pop _call_args")
    if use_call_func:
        code += parse_asm("pop _call_func")
    return code, [er, *ALL_REGS, *regs], False

def compile_dot(compiled_unit: ExprCompileResult, ref: ASTNode, get_value=True) -> ExprCompileResult:
    code, regs, _ = compiled_unit
    er = cycle_reg()
    scope_ast = get_scope(ref)
    if scope_ast.name == "function" and regs[0] == "this" and (class_structure := getattr(scope_ast, "class_structure", None)):
        if (attr_name := ref.get("REF").literal.value) in class_structure:
            attr_index = class_structure.index(attr_name)
            code = parse_asm(f"mov {er} this; add {er} {attr_index}")
            if get_value:
                code += parse_asm(f"get {er} {er}")
            return code, [er, *regs], False

    ref_str_lbl = getattr(ref.root, "strings")[ref.get("REF").literal.value][1]
    code += parse_asm(f"mov r0 {regs[0]}; mov r1 {ref_str_lbl}; call __findattr__")
    if get_value:
        code += parse_asm(f"get {er} rv")
    else:
        code += parse_asm(f"mov {er} rv")
    return code, [er, *ALL_REGS, *regs], False


def token_matches(token: str, test: Optional[str | List[str]]) -> bool:
    if isinstance(test, str):
        return token == test
    if isinstance(test, list):
        return token in test
    return True

def ins_matches(ast: ASTNode, *args: Optional[str | List[str]]):
    return all(token_matches(ast.literals[i].value, args[i]) for i in range(len(args)))

def optimize_instruction(code: ASTNode):
    if ins_matches(code, ["add", "sub"], None, "0"):
        return None
    if ins_matches(code, "mul", None, "1"):
        return None
    if ins_matches(code, "add", None, "1"):
        return copy_whitespace(code, parse_asm(f"inc {code.literals[1].value}")[0])
    if ins_matches(code, "sub", None, "1"):
        return copy_whitespace(code, parse_asm(f"dec {code.literals[1].value}")[0])
    return code

def optimize_expression(code: List[ASTNode]):
    return [result for ins in code if (result := optimize_instruction(ins))]


