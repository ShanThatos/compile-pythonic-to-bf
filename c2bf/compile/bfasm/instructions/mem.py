from c2bf.bf.code.common import bf_set
from c2bf.bf.code.main import BFCode
from c2bf.compile.bfasm.instructions.capture import bfasm_ins, bfasm_multi_ins
from c2bf.compile.bfasm.instructions.utils import *
from c2bf.compile.mem.units import USIZE, memrange, unit
from c2bf.compile.mem.workspaces.compute import COMPUTE, query
from c2bf.compile.mem.workspaces.unit import UNIT, nextunit, prevunit


@bfasm_ins()
def mark_unit():
    code = COMPUTE.set(memrange([USIZE], unit=COMPUTE.units[-1]), [254])
    for i, qidx in enumerate(range(query.id.size - 1, -1, -1)):
        code += COMPUTE.foreach(query.id[qidx], marked_unit_fb("[-]" + ">" * (256**i * USIZE) + bf_set(254)))

    code += COMPUTE.dec(query.marker) + COMPUTE.copy(query.marker, query.id[0], query.id[1])
    code += COMPUTE.not_(query.id[0], query.id[1])
    code += COMPUTE.if_(query.id[0], route_next_ins("get_unit_1"))

    code += COMPUTE.dec(query.marker) + COMPUTE.not_(query.marker, query.id[0])
    code += COMPUTE.if_(query.marker, route_next_ins("set_unit_1"))

    return code

@bfasm_ins("get_unit")
def get_unit_0():
    return COMPUTE.set(query.marker, [1]) + route_next_ins("mark_unit")
@bfasm_ins()
def get_unit_1():
    code = COMPUTE.clear(query.fdata) + marked_unit_fb(copy_code := BFCode(), True)
    for umc, qmc in zip(unit.fdata, query.fdata):
        copy_code += UNIT.clear(unit.empty[0])
        copy_code += UNIT.foreach(umc, UNIT.inc(unit.empty[0]) + marked_unit_bf(COMPUTE.inc(qmc)))
        copy_code += UNIT.move(unit.empty[0], umc)
    return code

@bfasm_ins("set_unit")
def set_unit_0():
    return COMPUTE.set(query.marker, [2]) + route_next_ins("mark_unit")
@bfasm_ins()
def set_unit_1():
    code = marked_unit_fb(UNIT.clear(unit.fdata))
    code += COMPUTE.clear(query.marker)
    for umc, qmc in zip(unit.fdata, query.fdata):
        code += COMPUTE.foreach(qmc, marked_unit_fb(UNIT.inc(umc)))
    code += marked_unit_fb(BFCode(), True)
    return code


# Split because ret depends on mov
@bfasm_ins("mov")
def mov_0():
    return route_get_unit(compute.data2, "mov_1", compute.data1)
@bfasm_ins()
def mov_1():
    return route_set_unit(compute.data1)


@bfasm_multi_ins()
def getf():
    yield route_get_unit(compute.data2, "getf_1", compute.data1)
    code = COMPUTE.clear(query.data)
    code += COMPUTE.move(query.flag, query.data[-1])
    code += route_set_unit(compute.data1)
    yield code

@bfasm_multi_ins()
def setf():
    yield route_get_unit(compute.data2, "setf_1", compute.data1)
    code = COMPUTE.move(query.data[-1], compute.data2[0])
    code += route_get_unit(compute.data1, "setf_2", compute.data1, compute.data2)
    yield code
    code = COMPUTE.move(compute.data2[0], query.flag)
    code += route_set_unit(compute.data1)
    yield code


@bfasm_multi_ins()
def get():
    yield route_get_unit(compute.data2, "get_1", cnext_data1=compute.data1)
    code = COMPUTE.move(query.data2, compute.data2)
    code += route_next_ins("mov")
    yield code

@bfasm_multi_ins("set")
def set_():
    yield route_get_unit(compute.data1, "set_1", cnext_data2=compute.data2)
    code = COMPUTE.move(query.data2, compute.data1)
    code += route_next_ins("mov")
    yield code


@bfasm_ins("push")
def push_0():
    return route_mark_unit(compute.data1, "push_1")
# split since call depends on push_1
@bfasm_ins()
def push_1():
    def gfb(c: BFCode):
        return glide_fb(c, 254, 255)
    code = marked_unit_fb(copy_code := BFCode(), True)
    copy_code += gfb(UNIT.clear(unit.fdata))
    for mc in unit.fdata:
        copy_code += UNIT.foreach(mc, UNIT.inc(unit.empty[0]) + gfb(UNIT.inc(mc)))
        copy_code += UNIT.move(unit.empty[0], mc)
    copy_code += gfb(UNIT.move(unit.marker, nextunit.marker))
    return code


@bfasm_ins("pop")
def pop_0():
    return route_mark_unit(compute.data1, "pop_1")
# split because ret depends on pop_1
@bfasm_ins()
def pop_1():
    code = marked_unit_fb(UNIT.clear(unit.fdata) + glide_fb(copy_code := BFCode(), 254, 255), True)
    copy_code += UNIT.move(unit.marker, prevunit.marker) + UNIT.to(prevunit.marker)
    for mc in unit.fdata:
        copy_code += UNIT.foreach(mc, UNIT.inc(unit.empty[0]) + glide_bf(UNIT.inc(mc), 254, 255))
        copy_code += UNIT.move(unit.empty[0], mc)
    return code
