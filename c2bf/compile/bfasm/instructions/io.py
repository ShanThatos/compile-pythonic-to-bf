from c2bf.bf.code.common import bf_b, bf_f, bf_glide_b, bf_set
from c2bf.bf.code.main import BFCode
from c2bf.compile.bfasm.instructions.capture import bfasm_multi_ins
from c2bf.compile.bfasm.instructions.utils import glide_fb, marked_unit_fb, route_get_unit, route_mark_unit, route_next_ins
from c2bf.compile.mem.units import USIZE, unit
from c2bf.compile.mem.workspaces.compute import COMPUTE, cextra, compute, query
from c2bf.compile.mem.workspaces.unit import UNIT


@bfasm_multi_ins()
def out():
    yield route_mark_unit(compute.data1, "out_1")
    yield marked_unit_fb(UNIT.tb(unit.data[-1], "."), True)

@bfasm_multi_ins("in")
def in_():
    yield route_mark_unit(compute.data1, "in_1")
    yield marked_unit_fb(UNIT.tb(unit.data[-1], ","), True)

@bfasm_multi_ins()
def outnum():
    code = bf_f(USIZE) + glide_fb(">[-]<" + bf_b(USIZE), 255, 255)
    code += route_get_unit(compute.data1, "outnum_1", compute.data1)
    yield code

    code = COMPUTE.copy(query.data[0], query.flag, query.empty[0])
    code += COMPUTE.foreach(query.flag, COMPUTE.inc(query.empty[0]) * 2 + COMPUTE.inc(query.empty[1]))
    code += COMPUTE.loop(query.empty[0], COMPUTE.dec(query.empty[0]) * 2 + COMPUTE.dec(query.empty[1]) + COMPUTE.inc(query.flag))
    code += COMPUTE.if_(query.empty[1], neg_code := BFCode())
    code += COMPUTE.clear(query.flag)

    neg_code += COMPUTE.tb(query.empty[0], bf_set(45) + ".")
    for mc in query.data:
        neg_code += COMPUTE.set(query.empty[0], [255])
        neg_code += COMPUTE.foreach(mc, COMPUTE.dec(query.empty[0]))
        neg_code += COMPUTE.move(query.empty[0], mc)
    neg_code += COMPUTE.inc_num(query.data, query.empty[0], query.empty[1])

    code += COMPUTE.clear(cextra.data)
    code += route_next_ins("outnum_2")
    yield code

    code = BFCode()
    div10 = COMPUTE.bt(compute.data[1], COMPUTE.inc(cextra.empty[0]) + COMPUTE.clear(cextra.empty[1])) + "<"
    inc_rem = COMPUTE.bt(compute.data[1], COMPUTE.inc(cextra.empty[1]))
    for _ in range(9):
        div10 = "[-" + inc_rem + div10 + "]"
    div10 = COMPUTE.tb(compute.data[1], "[-" + inc_rem + div10 + ">]>[-<]<")
    div10 = COMPUTE.clear(cextra.empty) + COMPUTE.clear(compute.data[0]) + COMPUTE.clear(compute.data[2]) + COMPUTE.set(compute.data[3], [1]) + div10
    div10 += COMPUTE.clear(compute.data[3])

    for amc, bmc in zip(cextra.data, query.data):
        code += COMPUTE.move(bmc, compute.data[1]) + div10
        code += COMPUTE.foreach(cextra.empty[0], COMPUTE.inc(amc))
        code += COMPUTE.move(cextra.empty[1], bmc)

    # 19 19 19 19
    # 1 1 1 1    9 9 9 9

    for i in range(query.data.size - 2, -1, -1):
        amc, bmc = cextra.data[i], query.data[i]
        code += COMPUTE.move(bmc, query.empty[0])
        code += COMPUTE.foreach(query.empty[0], split := BFCode())
        split += COMPUTE.set(query.empty[1], [25])
        split += COMPUTE.foreach(query.empty[1], COMPUTE.inc_num(cextra.data[:i+2], cextra.empty[0], cextra.empty[1]))
        split += COMPUTE.set(query.empty[1], [6])
        split += COMPUTE.foreach(query.empty[1], COMPUTE.inc_num(query.data[:i+2], cextra.empty[0], cextra.empty[1]))

    code += COMPUTE.set(query.flag, [1])
    code += COMPUTE.copy(query.data[-1], query.empty[0], query.empty[1])
    code += COMPUTE.set(query.empty[1], [10])
    code += COMPUTE.foreach(query.empty[1], (check_zero := BFCode()) + COMPUTE.dec(query.empty[0]))
    check_zero += COMPUTE.copy(query.empty[0], cextra.empty[0], cextra.empty[1])
    check_zero += COMPUTE.not_(cextra.empty[0], cextra.empty[1])
    check_zero += COMPUTE.if_(cextra.empty[0], COMPUTE.clear(query.flag))

    # query.flag says if last byte is >= 10
    code += COMPUTE.or_keep(query.empty[0], query.empty[1], query.data[:-1])
    code += COMPUTE.or_(query.empty[1], query.flag, query.empty[0])

    # if query.empty[1], number >= 10, need to keep dividing
    code += COMPUTE.set(query.empty[0], [1])
    code += COMPUTE.if_(query.empty[1], keep_dividing := BFCode())
    code += COMPUTE.if_(query.empty[0], finished_dividing := BFCode())

    keep_dividing += COMPUTE.clear(query.empty[0])
    keep_dividing += COMPUTE.move(compute.empty, compute.data1) 
    keep_dividing += route_next_ins("outnum_2")

    finished_dividing += bf_f(USIZE) + glide_fb("[>]>[-]<" + "+" * 48 + bf_glide_b(255, 1) + bf_b(USIZE), 255, 255)
    finished_dividing += COMPUTE.foreach(query.data[-1], move_code := BFCode())
    move_code += bf_f(USIZE) + glide_fb("[>]<+" + bf_glide_b(255, 1) + bf_b(USIZE), 255, 255)

    # check if quotient != 0
    finished_dividing += COMPUTE.or_keep(cextra.empty[0], cextra.empty[1], cextra.data)
    finished_dividing += COMPUTE.set(cextra.empty[1], [1])
    finished_dividing += COMPUTE.if_(cextra.empty[0], next_digit := BFCode())
    finished_dividing += COMPUTE.if_(cextra.empty[1], output_digits := BFCode())

    # quotient != 0, divide by 10 again
    next_digit += COMPUTE.clear(cextra.empty[1])
    next_digit += COMPUTE.move(cextra.data, query.data)
    next_digit += route_next_ins("outnum_2")

    # quotient == 0, output digits
    output_digits += bf_f(USIZE) + glide_fb("[>]<+[-.[-]<+]-" + bf_b(USIZE), 255, 255)

    yield code

@bfasm_multi_ins()
def outstr():
    yield route_get_unit(compute.data1, "outstr_1")
    yield route_mark_unit(query.data2, "outstr_2")
    
    code = marked_unit_fb(output_code := BFCode())
    output_code += UNIT.clear(unit.marker)
    output_code += UNIT.tb(unit.data[-1], f"[.{">" * USIZE}]")

    yield code