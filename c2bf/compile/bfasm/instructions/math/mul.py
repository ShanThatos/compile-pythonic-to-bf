from c2bf.bf.code.main import BFCode
from c2bf.compile.bfasm.instructions.capture import bfasm_multi_ins
from c2bf.compile.bfasm.instructions.utils import route_get_unit, route_set_unit
from c2bf.compile.mem.workspaces.compute import COMPUTE, cextra, compute, query


@bfasm_multi_ins()
def mul():
    yield route_get_unit(compute.data2, "mul_1", compute.data1)
    
    code = COMPUTE.move(query.data, cextra.data)
    code += route_get_unit(compute.data1, "mul_2", compute.data1)
    yield code
    
    code = COMPUTE.move(compute.data1, compute.empty)
    code += COMPUTE.move(query.data, compute.data)

    code += COMPUTE.while_(cextra.marker, loop_expr_code := BFCode(), loop_code := BFCode())
    loop_expr_code += COMPUTE.or_keep(cextra.marker, cextra.flag, cextra.data)
    
    loop_code += COMPUTE.clear(cextra.empty)
    loop_code += COMPUTE.foreach(cextra.data[-1], COMPUTE.inc(cextra.empty[0]) * 128 + COMPUTE.inc(cextra.empty[1]))
    loop_code += COMPUTE.move(cextra.empty[1], cextra.data[-1])
    loop_code += COMPUTE.set(cextra.empty[1], [1])
    loop_code += COMPUTE.if_(cextra.empty[0], COMPUTE.clear(cextra.empty[1]) + (accum_code := BFCode()))
    loop_code += COMPUTE.if_(cextra.empty[1], double_half_code := BFCode())

    accum_code += COMPUTE.dec(cextra.data[-1])
    for i in range(query.data.size - 1, -1, -1):
        accum_code += COMPUTE.foreach(compute.data[i], COMPUTE.inc(cextra.empty[0]) + COMPUTE.inc_num(query.data[:i+1], query.id[0], query.id[1]))
        accum_code += COMPUTE.move(cextra.empty[0], compute.data[i])

    double_half_code += COMPUTE.lshift(compute.data, cextra.empty[0], cextra.empty[1])
    double_half_code += COMPUTE.rshift(cextra.data, cextra.empty[0], cextra.empty[1])

    code += COMPUTE.clear(compute.data)
    code += route_set_unit(compute.empty)
    yield code

