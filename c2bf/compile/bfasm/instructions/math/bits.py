from c2bf.compile.bfasm.instructions.capture import bfasm_multi_ins
from c2bf.compile.bfasm.instructions.utils import marked_unit_fb, route_get_unit, route_mark_unit
from c2bf.compile.mem.units import unit
from c2bf.compile.mem.workspaces.compute import COMPUTE, cextra, compute, query
from c2bf.compile.mem.workspaces.unit import UNIT, nextunit


@bfasm_multi_ins()
def lshift():
    yield route_get_unit(compute.data2, "lshift_1", compute.data1)
    code = COMPUTE.move(query.data[-1], cextra.data[-1])
    code += route_mark_unit(compute.data1, "lshift_2")
    yield code
    code = marked_unit_fb(UNIT.clear(nextunit.empty[0]))
    code += COMPUTE.foreach(cextra.data[-1], marked_unit_fb(UNIT.inc(nextunit.empty[0])))
    code += marked_unit_fb(UNIT.foreach(nextunit.empty[0], UNIT.lshift(unit.data, unit.empty[0], unit.empty[1])), True)
    yield code

@bfasm_multi_ins()
def rshift():
    yield route_get_unit(compute.data2, "rshift_1", compute.data1)
    code = COMPUTE.move(query.data[-1], cextra.data[-1])
    code += route_mark_unit(compute.data1, "rshift_2")
    yield code
    code = marked_unit_fb(UNIT.clear(nextunit.empty[0]))
    code += COMPUTE.foreach(cextra.data[-1], marked_unit_fb(UNIT.inc(nextunit.empty[0])))
    code += marked_unit_fb(UNIT.foreach(nextunit.empty[0], UNIT.rshift(unit.data, unit.empty[0], unit.empty[1])), True)
    yield code
