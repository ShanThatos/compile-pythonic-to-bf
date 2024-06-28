import re
from typing import List
from c2bf.compile.bfun.compilers.utils import extend_label, new_label, parse_code
from c2bf.parser.ast import ASTNode

def parse_string(value: str) -> List[int]:
    ret = []
    i = 0
    while i < len(value):
        if value[i] == "\\":
            i += 1
            if value[i] == "n":
                ret.append(10)
            elif value[i] == "t":
                ret.append(9)
            elif value[i] == "r":
                ret.append(13)
            elif value[i] == "0":
                ret.append(0)
            elif value[i] == "\\":
                ret.append(92)
            elif value[i] == "\"":
                ret.append(34)
            else:
                raise Exception(f"Invalid escape sequence \\{value[i]} in string {value}")
        else:
            ret.append(ord(value[i]))
        i += 1
    return ret

def simplify_key(base: str, key: str):
    key = "".join(c.replace(" ", "_") for c in key if re.match(r"[a-zA-Z0-9 ]", c))[:8]
    if key:
        return f"{base}_{key.lower()}"
    return base

def transform_strings(root_ast: ASTNode):
    strings = getattr(root_ast, "strings", {})
    string_instances_needed = set()
    def collect(ast: ASTNode):
        if ast.name not in ("STRING", "class_field", "class_function", "e_dot"):
            return
        
        if ast.name == "STRING":
            key = ast.literal.value[1:-1]
            chars = parse_string(key)
        elif ast.name in ("class_field", "class_function", "e_dot"):
            key = ast.get("REF").literal.value
            chars = [ord(c) for c in key]
        if key not in strings:
            str_lbl = new_label(ast, simplify_key("str", key))
            str_db_lbl = extend_label(ast, str_lbl, "db")
            str_instance_lbl = extend_label(ast, str_lbl, "instance")
            strings[key] = (chars, str_lbl, str_db_lbl, str_instance_lbl)
        
        if ast.name == "STRING":
            ast.name = "REF"
            ast.literal.value = strings[key][3]
            string_instances_needed.add(key)

    ASTNode.transform(root_ast, collect)

    setattr(root_ast, "strings", strings)

    added_str_instances = False
    def transform(ast: ASTNode):
        nonlocal added_str_instances
        if added_str_instances:
            return
        is_comment = ast.name == "statement" and ast[0].name == "COMMENT"
        if not is_comment or ast.literals[0].value.strip() != "# ~~~AFTERCOMMON~~~":
            return
        added_str_instances = True
        
        str_code = []
        for key in string_instances_needed:
            _, str_lbl, _, str_instance_lbl = strings[key]
            str_code.append(f"{str_instance_lbl}: 0")
            str_code.append(f"{str_instance_lbl} = str({str_lbl})")
        return parse_code("\n\n# STRINGS\n" + "\n".join(str_code) + "\n\n").children
    
    ASTNode.transform(root_ast, transform)

