from typing import List, Optional

from c2bf.bf.code.common import bf_glide_b, bf_glide_f
from c2bf.bf.code.main import BFCode
from c2bf.compile.bfasm.instructions.capture import get_instruction
from c2bf.compile.bfasm.registers import get_register_index
from c2bf.compile.mem.units import USIZE, memrange, unit
from c2bf.compile.mem.workspaces.compute import COMPUTE, cnext, compute, query
from c2bf.compile.mem.workspaces.unit import UNIT


def b256(n: int, size: int) -> List[int]:
    n %= 256**size
    ret = []
    while len(ret) < size:
        ret.append(n % 256)
        n //= 256
    return list(reversed(ret))

def glide_fb(code: BFCode, src_marker: int, dest_marker: int):
    gf = bf_glide_f(dest_marker, USIZE)
    gb = bf_glide_b(src_marker, USIZE)
    return gf + code + gb
def glide_bf(code: BFCode, src_marker: int, dest_marker: int):
    gf = bf_glide_f(dest_marker, USIZE)
    gb = bf_glide_b(src_marker, USIZE)
    return gb + code + gf

def marked_unit_fb(code: BFCode, clear_marker = False):
    return glide_fb(code + UNIT.clear(unit.marker) * clear_marker, 255, 254)
def marked_unit_bf(code: BFCode):
    return glide_bf(code, 255, 254)


def get_register_mr(name: str):
    reg_idx = get_register_index(name)
    reg_start = COMPUTE.size + reg_idx * USIZE
    return memrange(range(reg_start, reg_start + USIZE), unit=COMPUTE.units[0])


def route_next_ins(c_ins: str, cnext_ins: Optional[str] = None, cnext_data1: Optional[memrange] = None, cnext_data2: Optional[memrange] = None):
    code = COMPUTE.set(compute.flag, [get_instruction(c_ins).id])
    if cnext_ins:
        code += COMPUTE.set(cnext.flag, [get_instruction(cnext_ins).id])
    if cnext_data1:
        code += COMPUTE.move(cnext_data1, cnext.data1)
    if cnext_data2:
        code += COMPUTE.move(cnext_data2, cnext.data2)
    return code

def route_get_unit(id_mr: memrange, cnext_ins: Optional[str] = None, cnext_data1: Optional[memrange] = None, cnext_data2: Optional[memrange] = None):
    code = COMPUTE.move(id_mr, query.id)
    if id_mr == cnext_data1 or id_mr == cnext_data2:
        code = COMPUTE.copy(id_mr, query.id, query.flag)
    if id_mr == query.id:
        code = BFCode()
    return code + route_next_ins("get_unit", cnext_ins, cnext_data1, cnext_data2)

def route_set_unit(id_mr: memrange, cnext_ins: Optional[str] = None, cnext_data1: Optional[memrange] = None, cnext_data2: Optional[memrange] = None):
    code = COMPUTE.move(id_mr, query.id)
    if id_mr == cnext_data1 or id_mr == cnext_data2:
        code = COMPUTE.copy(id_mr, query.id, query.flag)
    if id_mr == query.id:
        code = BFCode()
    return code + route_next_ins("set_unit", cnext_ins, cnext_data1, cnext_data2)

def route_mark_unit(id_mr: memrange, cnext_ins: Optional[str] = None):
    code = COMPUTE.move(id_mr, query.id)
    if id_mr == query.id:
        code = BFCode()
    return code + route_next_ins("mark_unit", cnext_ins)