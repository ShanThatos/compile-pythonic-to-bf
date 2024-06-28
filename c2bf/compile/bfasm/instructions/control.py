from c2bf.bf.code.common import bf_f
from c2bf.compile.bfasm.instructions.utils import *
from c2bf.compile.mem.workspaces.compute import COMPUTE, compute, query
from c2bf.compile.mem.workspaces.unit import UNIT, unit

from .capture import *


@bfasm_ins()
def noop():
    return BFCode()

@bfasm_ins()
def obj_noop():
    return BFCode()

@bfasm_ins()
def end():
    return COMPUTE.clear(compute.running)

@bfasm_ins()
def dbg():
    return BFCode("@")

@bfasm_multi_ins()
def start_ins():
    ip_mr = get_register_mr("ip")
    code = COMPUTE.tb(ip_mr[unit.marker.slice], UNIT.inc_num(unit.data2, unit.empty[0], unit.empty[1]))

    code += COMPUTE.clear(query.id)
    code += COMPUTE.tb(compute.ipmarker, marked_unit_fb(UNIT.bt(unit.ipmarker, get_ip_code := BFCode())))
    get_ip_code += UNIT.clear(unit.ipmarker) + bf_f(USIZE) + UNIT.set(unit.ipmarker, [254])
    for cmc, umc in zip(compute.fdata, unit.fdata):
        get_ip_code += UNIT.copy(umc, unit.empty[0], unit.empty[1])
        get_ip_code += UNIT.foreach(unit.empty[0], UNIT.tb(unit.ipmarker, marked_unit_bf(COMPUTE.bt(compute.ipmarker, COMPUTE.inc(cmc)))))
    yield code

@bfasm_multi_ins()
def jp():
    yield route_get_unit(compute.data1, "jp_1")
    code = COMPUTE.copy(query.data2, get_register_mr("ip")[unit.data2.slice], query.data1[-1])
    code += route_mark_unit(query.data2, "jp_2")
    yield code
    code = COMPUTE.tb(compute.ipmarker, marked_unit_fb(UNIT.bt(unit.ipmarker, UNIT.clear(unit.ipmarker))))
    code += marked_unit_fb(UNIT.set(unit.ipmarker, [254]), True)
    yield code

@bfasm_multi_ins()
def jpif():
    yield route_get_unit(compute.data2, "jpif_1", compute.data1)
    code = COMPUTE.or_(query.flag, query.data)
    code += COMPUTE.if_(query.flag, route_next_ins("jp"))
    yield code

@bfasm_multi_ins()
def jpz():
    yield route_get_unit(compute.data2, "jpz_1", compute.data1)
    code = COMPUTE.or_(query.flag, query.data)
    code += COMPUTE.not_(query.flag, query.data[0])
    code += COMPUTE.if_(query.flag, route_next_ins("jp"))
    yield code

@bfasm_ins()
def call():
    ip_mr = get_register_mr("ip")
    code = COMPUTE.set(ip_mr[unit.marker.slice], [254])
    code += route_next_ins("push_1", "jp", compute.data1)
    return code

@bfasm_multi_ins()
def ret():
    ip_mr = get_register_mr("ip")
    code = COMPUTE.set(ip_mr[unit.marker.slice], [254])
    code += route_next_ins("pop_1", "ret_1", cnext_data2=compute.data1)
    yield code
    code = COMPUTE.tb(compute.ipmarker, marked_unit_fb(UNIT.bt(unit.ipmarker, UNIT.clear(unit.ipmarker))))
    code += COMPUTE.move(compute.data2, cnext.data2)
    code += COMPUTE.copy(get_register_mr("ip")[unit.data2.slice], query.id, query.data1[0])
    code += route_mark_unit(query.id, "ret_2")
    yield code
    code = marked_unit_fb(UNIT.set(unit.ipmarker, [254]), True)
    code += COMPUTE.set(compute.data1, b256(get_register_index("rv"), compute.data1.size))
    code += route_next_ins("mov")
    yield code
    