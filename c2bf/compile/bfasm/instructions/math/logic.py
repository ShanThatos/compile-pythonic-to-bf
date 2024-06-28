from c2bf.bf.code.main import BFCode
from c2bf.compile.bfasm.instructions.capture import bfasm_multi_ins
from c2bf.compile.bfasm.instructions.utils import b256, get_register_mr, marked_unit_bf, marked_unit_fb, route_get_unit, route_mark_unit, route_next_ins
from c2bf.compile.bfasm.registers import get_register_index
from c2bf.compile.mem.units import unit
from c2bf.compile.mem.workspaces.compute import COMPUTE, cextra, cnext, compute, query
from c2bf.compile.mem.workspaces.unit import UNIT, nextunit

@bfasm_multi_ins()
def norm():
    yield route_mark_unit(compute.data1, "norm_1")
    code = marked_unit_fb(norm_code := BFCode(), True)
    norm_code += UNIT.or_(unit.empty[0], unit.data)
    norm_code += UNIT.move(unit.empty[0], unit.data[-1])
    yield code

@bfasm_multi_ins("not")
def not_():
    yield route_mark_unit(compute.data1, "not_1")
    code = marked_unit_fb(not_code := BFCode(), True)
    not_code += UNIT.or_(unit.empty[0], unit.data)
    not_code += UNIT.set(unit.data[-1], [1])
    not_code += UNIT.if_(unit.empty[0], UNIT.clear(unit.data[-1]))
    yield code

@bfasm_multi_ins()
def zcmp():
    yield route_mark_unit(compute.data1, "zcmp_1")
    
    def set_cr_reg(val: int):
        cr_mr = get_register_mr("cr")
        return marked_unit_bf(COMPUTE.clear(cr_mr[unit.data.slice]) + COMPUTE.set(cr_mr[unit.data[-1].slice], [val]))
    
    code = marked_unit_fb(cmp_code := BFCode(), True)
    cmp_code += UNIT.clear(unit.empty) + UNIT.or_keep(unit.empty[0], unit.empty[1], unit.data)
    cmp_code += UNIT.set(unit.empty[1], [1])
    cmp_code += UNIT.if_(unit.empty[0], UNIT.clear(unit.empty[1]) + (nzero_code := BFCode()))

    nzero_code += UNIT.copy(unit.data[0], nextunit.empty[0], nextunit.empty[1])
    nzero_code += UNIT.foreach(nextunit.empty[0], UNIT.inc(unit.empty[0]) * 2 + UNIT.inc(unit.empty[1]))
    nzero_code += UNIT.loop(unit.empty[0], UNIT.dec(unit.empty[0]) * 2 + UNIT.dec(unit.empty[1]) + UNIT.inc(nextunit.empty[0]))
    nzero_code += UNIT.set(unit.empty[0], [1])
    nzero_code += UNIT.if_(unit.empty[1], UNIT.clear(unit.empty[0]) + set_cr_reg(0)) # negative
    nzero_code += UNIT.if_(unit.empty[0], set_cr_reg(2)) # positive
    nzero_code += UNIT.clear(nextunit.empty[0])

    cmp_code += UNIT.if_(unit.empty[1], set_cr_reg(1)) # zero

    yield code

@bfasm_multi_ins()
def cmp():
    yield route_get_unit(compute.data2, "cmp_1", compute.data1)
    code = COMPUTE.move(query.data, cextra.data)
    code += route_get_unit(compute.data1, "cmp_2")
    yield code
    cr_vals = b256(get_register_index("cr"), compute.data1.size)
    code = COMPUTE.set(compute.data1, cr_vals)
    code += COMPUTE.set(cnext.data1, cr_vals)
    code += route_next_ins("sub_2", "zcmp")
    yield code

@bfasm_multi_ins()
def streq():
    yield route_get_unit(compute.data2, "streq_1", compute.data1)
    code = COMPUTE.move(query.data2, cextra.data2)
    code += route_get_unit(compute.data1, "streq_2")
    yield code

    code = COMPUTE.move(query.data2, cextra.data1)
    code += COMPUTE.dec_num(cextra.data1, cextra.empty[0], cextra.empty[1])
    code += COMPUTE.dec_num(cextra.data2, cextra.empty[0], cextra.empty[1])
    cr_mr = get_register_mr("cr")
    code += COMPUTE.clear(cr_mr[unit.data.slice]) + COMPUTE.inc(cr_mr[unit.data[-1].slice])

    code += route_next_ins("streq_3")
    yield code

    code = COMPUTE.copy(cextra.data1, query.id, cextra.empty[0])
    code += route_get_unit(query.id, "streq_4")
    yield code
    code = COMPUTE.move(query.data[-1], cextra.empty[1])
    code += COMPUTE.copy(cextra.data2, query.id, cextra.empty[0])
    code += route_get_unit(query.id, "streq_5")
    yield code

    code = COMPUTE.clear(cextra.flag)
    code += COMPUTE.loop(cextra.empty[1], COMPUTE.inc(cextra.flag) + COMPUTE.move(cextra.empty[1], cextra.empty[0]))
    code += COMPUTE.loop(query.data[-1], COMPUTE.inc(cextra.flag) + COMPUTE.foreach(query.data[-1], COMPUTE.dec(cextra.empty[0])))
    
    code += COMPUTE.copy(cextra.flag, compute.empty[0], compute.empty[1])
    code += COMPUTE.dec(compute.empty[0]) * 2
    code += COMPUTE.not_(compute.empty[0], compute.empty[1])
    code += COMPUTE.set(compute.empty[1], [1])
    code += COMPUTE.if_(compute.empty[0], COMPUTE.clear(compute.empty[1]) + (check_char_code := BFCode()))
    code += COMPUTE.if_(compute.empty[1], end_loop_code := BFCode())

    check_char_code += COMPUTE.set(cextra.empty[1], [1])
    check_char_code += COMPUTE.if_(cextra.empty[0], COMPUTE.clear(cextra.empty[1]) + (noteq_code := BFCode()))
    check_char_code += COMPUTE.if_(cextra.empty[1], eq_code := BFCode())
    
    noteq_code += COMPUTE.clear(cr_mr[unit.data[-1].slice])
    
    eq_code += COMPUTE.inc_num(cextra.data1, cextra.empty[0], cextra.empty[1])
    eq_code += COMPUTE.inc_num(cextra.data2, cextra.empty[0], cextra.empty[1])
    eq_code += route_next_ins("streq_3")

    end_loop_code += COMPUTE.if_(cextra.flag, COMPUTE.clear(cr_mr[unit.data[-1].slice]))

    yield code