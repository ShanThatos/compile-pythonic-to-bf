import random
import re
import string

from typing import Callable, List, Optional

from c2bf.parser.ast import ASTNode
from c2bf.parser.main import ProceduralParser
from c2bf.compile.spec import SPEC


def parse_code(code: str, syntax = "program"):
    return ProceduralParser(SPEC, syntax).parse(code)

asm_parser = ProceduralParser(SPEC, "multi_asm")
def parse_asm(code: str, tab = False):
    asts = asm_parser.parse(code).children
    for child in asts:
        child.literals[0].whitespace = "\n" + tab * "\t"
    return asts

def keep_last_line(whitespace: str, tab = False):
    return "\n" + tab * "\t" + re.sub(r"[^\t]", "", whitespace.rpartition("\n")[2])

def normalize_asm_whitespace(ast: List[ASTNode], tab = False):
    for line in ast:
        if line.name not in ("COMMENT", "label", "instruction"):
            raise Exception(f"Unexpected node {line.name}")
        token = line.literals[0]
        token.whitespace = keep_last_line(token.whitespace, tab)

    while ast and all(line.literals[0].whitespace.startswith("\n\t\t") for line in ast):
        for line in ast:
            token = line.literals[0]
            token.whitespace = "\n" + token.whitespace[2:]
    return ast

def copy_whitespace(src: ASTNode, dest: ASTNode):
    dest.literals[0].whitespace = src.literals[0].whitespace
    return dest

def tabs(default: bool = False):
    def decorator[T](func: Callable[[ASTNode], T]):
        def wrapper(ast: ASTNode, tab = default) -> T:
            result = func(ast)
            if isinstance(result, tuple):
                normalize_asm_whitespace(result[0], tab)
            elif isinstance(result, list):
                normalize_asm_whitespace(result, tab)
            else:
                raise Exception("Unexpected result")
            return result
        return wrapper
    return decorator

def alwaystab[T](func: Callable[[ASTNode], T]):
    return tabs(True)(func)

def get_scope(ast: Optional[ASTNode]):
    while ast:
        if ast.name in ("program", "function"):
            return ast
        ast = ast.parent
    raise Exception("No scope found")
def resolve_ref(ast: ASTNode, ref: str):
    if ref in getattr(ast.root, "labels"):
        return ref
    try:
        scope = get_scope(ast)
        scope_vars = getattr(scope, "vars")
        while ref not in scope_vars:
            scope = get_scope(scope.parent)
            scope_vars = getattr(scope, "vars")
        return scope_vars[ref]
    except Exception: 
        pass
    raise Exception(f"Variable {ref} not found")


def rand_id():
    return "".join(random.choices(string.ascii_lowercase, k=5))
def new_label(ast: ASTNode, prefix: str):
    labels: set = getattr(ast.root, "labels")
    rand_label = lambda: f"{prefix}__{rand_id()}"
    while (label := rand_label()) in labels:
        pass
    labels.add(label)
    return label
def extend_label(ast: ASTNode, label: str, extension: str):
    labels: set = getattr(ast.root, "labels")
    prefix, rid = label.split("__", 1)
    erid = ""
    rand_label = lambda: f"{prefix}_{extension}__{rid}{erid}"
    while (label := rand_label()) in labels:
        erid = f"_{rand_id()}"
    labels.add(label)
    return label
