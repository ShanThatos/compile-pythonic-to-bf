from c2bf.bf.code.main import BFCode
from c2bf.compile.bfasm.instructions.capture import bfasm_ins, bfasm_multi_ins
from c2bf.compile.bfasm.instructions.utils import *
from c2bf.compile.mem.workspaces.compute import cextra, compute
from c2bf.compile.mem.workspaces.unit import UNIT, unit


@bfasm_ins("inc")
def inc_0():
    return route_mark_unit(compute.data1, "inc_1")
@bfasm_ins()
def inc_1():
    return marked_unit_fb(UNIT.inc_num(unit.data, unit.empty[0], unit.empty[1]), True)

@bfasm_multi_ins()
def dec():
    yield route_mark_unit(compute.data1, "dec_1")
    yield marked_unit_fb(UNIT.dec_num(unit.data, unit.empty[0], unit.empty[1]), True)

@bfasm_multi_ins()
def neg():
    yield route_mark_unit(compute.data1, "neg_1")
    code = marked_unit_fb(neg_code := BFCode())
    for mc in unit.data:
        neg_code += UNIT.set(unit.empty[0], [255])
        neg_code += UNIT.foreach(mc, UNIT.dec(unit.empty[0]))
        neg_code += UNIT.move(unit.empty[0], mc)
    code += route_next_ins("inc_1")
    yield code


@bfasm_multi_ins()
def add():
    yield route_get_unit(compute.data2, "add_1", compute.data1)
    code = COMPUTE.move(query.data, cextra.data)
    code += route_get_unit(compute.data1, "add_2", compute.data1)
    yield code
    code = BFCode()
    for i in range(query.data.size - 1, -1, -1):
        code += COMPUTE.foreach(cextra.data[i], COMPUTE.inc_num(query.data[:i+1], query.id[0], query.id[1]))
    code += route_set_unit(compute.data1)
    yield code


@bfasm_multi_ins()
def sub():
    yield route_get_unit(compute.data2, "sub_1", compute.data1)
    code = COMPUTE.move(query.data, cextra.data)
    code += route_get_unit(compute.data1, "sub_2", compute.data1)
    yield code
# sub is split because cmp depends on sub_2
@bfasm_ins()
def sub_2():
    code = BFCode()
    for i in range(query.data.size - 1, -1, -1):
        code += COMPUTE.foreach(cextra.data[i], COMPUTE.dec_num(query.data[:i+1], query.id[0], query.id[1]))
    code += route_set_unit(compute.data1)
    return code