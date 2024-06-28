from typing import List, Literal, Tuple, Union
from c2bf.compile.bfasm.instructions.capture import get_instruction
from c2bf.compile.bfasm.instructions.utils import b256
from c2bf.compile.bfasm.registers import REGISTERS
from c2bf.compile.mem.units import USIZE, unit
from c2bf.parser.ast import ASTNode


type CodeType = List[Union[
    Tuple[Literal["label"], str, List[int]],
    Tuple[Literal["instruction"], str, List[str]]
]]

def encode_bfasm_to_bytes(bfasm: ASTNode):
    labels = set[str]()
    consts = set[int]()

    reg_code: CodeType = []
    for (reg, val) in REGISTERS:
        reg_code.append(("label", reg, [val]))
        labels.add(reg)

    code: CodeType = []
    for line in bfasm.children:
        if line.name == "label":
            label = line.get("REF").literal.value
            nums = [int(num.literal.value) for num in line.get_all("NUMBER")]
            if label in labels:
                raise Exception(f"Label {label} already defined")
            labels.add(label)
            code.append(("label", label, nums))
        elif line.name == "instruction":
            ins = line[0]
            ins_name = ins[0].literal.value
            args = []
            for arg in ins[1:]:
                if arg.name == "NUMBER":
                    const = int(arg.literal.value)
                    consts.add(const)
                    args.append(f"$const_{const}")
                elif arg.name == "REF":
                    args.append(arg.literal.value)
            code.append(("instruction", ins_name, args))

    consts = sorted(consts)
    for const in reversed(consts):
        code.insert(0, ("label", f"$const_{const}", [const]))

    code.insert(0, ("label", "$start", [4294967295]))

    code = reg_code + code

    label_map = {}
    mem_index = 0
    for ins in code:
        if ins[0] == "label":
            label_map[ins[1]] = b256(mem_index, unit.data1.size)
            if len(ins[2]) == 0:
                ins[2].append(mem_index)
            mem_index += len(ins[2])
        elif ins[0] == "instruction":
            mem_index += 1
    
    unit_data_slice = unit.data.slice
    unit_data1_slice = unit.data1.slice
    unit_data2_slice = unit.data2.slice
    code_bytes: List[int] = []
    for ins in code:
        if ins[0] == "label":
            for num in ins[2]:
                unit_bytes = [0] * USIZE
                unit_bytes[unit_data_slice] = b256(num, unit.data.size)
                code_bytes.extend(unit_bytes)
        elif ins[0] == "instruction":
            unit_bytes = [0] * USIZE
            unit_bytes[unit.flag.index] = get_instruction(ins[1]).id
            args = ins[2]
            if len(args) > 0:
                unit_bytes[unit_data1_slice] = label_map[args[0]]
            if len(args) > 1:
                unit_bytes[unit_data2_slice] = label_map[args[1]]
            code_bytes.extend(unit_bytes)

    unit_bytes = [0] * USIZE
    unit_bytes[unit.flag.index] = get_instruction("end").id
    code_bytes.extend(unit_bytes)
    
    unit_bytes = [0] * USIZE
    unit_bytes[unit.marker.index] = 255
    code_bytes.extend(unit_bytes)

    return code_bytes