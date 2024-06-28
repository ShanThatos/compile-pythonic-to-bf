from typing import List

from c2bf.compile.mem.units import USIZE
from c2bf.bf.code.common import bf_f, bf_fb, bf_set
from c2bf.bf.code.main import BFCode
from c2bf.compile.bfasm.instructions.capture import INSTRUCTIONS, get_instruction
from c2bf.compile.mem.workspaces.compute import COMPUTE, cnext, compute


def encode_to_bf_with_processor(mem: List[int]) -> BFCode:
    code = encode_bytes_to_bf(mem)
    code += processor()
    return code

def encode_bytes_to_bf(mem: List[int]) -> BFCode:
    code = []
    for n in mem:
        if n:
            code.append(bf_set(n, True).to_bf())
        code.append(">")
    code.append("<" * len(mem))
    return bf_fb(COMPUTE.size, "".join(code))

def processor() -> BFCode:
    code = bf_f(COMPUTE.get_index(compute.running))
    code += bf_set(255, True)
    code += bf_fb(COMPUTE.get_distance(COMPUTE.units[-1].ipmarker) + USIZE, bf_set(254, True))
    code += COMPUTE.set(compute.ipmarker, [255])
    
    code += COMPUTE.loop(compute.running, program_loop := BFCode())
    
    program_loop += COMPUTE.set(compute.flag, [get_instruction("start_ins").id])
    program_loop += COMPUTE.loop(compute.flag, instruction_loop := BFCode())
    
    for ins in INSTRUCTIONS[1:]:
        instruction_loop += COMPUTE.copy(compute.flag, compute.empty[0], compute.empty[1])
        instruction_loop += COMPUTE.dec(compute.empty[0]) * ins.id
        instruction_loop += COMPUTE.not_(compute.empty[0], compute.empty[1])
        instruction_loop += COMPUTE.if_(compute.empty[0], run_ins := BFCode())
        run_ins += COMPUTE.clear(compute.flag) + ins.get_code()
    
    instruction_loop += (check_cnext := BFCode())
    
    check_cnext += COMPUTE.copy(compute.flag, compute.empty[0], compute.empty[1])
    check_cnext += COMPUTE.not_(compute.empty[0], compute.empty[1])
    check_cnext += COMPUTE.if_(compute.empty[0], COMPUTE.move(cnext.fdata, compute.fdata))

    return code
