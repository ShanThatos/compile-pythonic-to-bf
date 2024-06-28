from typing import Any, Callable, Generator, List, Optional

from c2bf.bf.code.main import BFCode

type BFCodeFunc = Callable[[], BFCode]
type BFCodeGeneratorFunc = Callable[[], Generator[BFCode, Any, None]]

INSTRUCTIONS: List["Instruction"] = []
MULTI_INSTRUCTIONS: List["MultiInstruction"] = []

class Instruction:
    def __init__(self, name: str, bf_code_func: BFCodeFunc):
        self.name = name
        self.bf_code_func = bf_code_func
        self.code: Optional[BFCode] = None

    def get_code(self):
        if self.code is None:
            self.code = self.bf_code_func()
        return self.code
    
    @property
    def id(self):
        return INSTRUCTIONS.index(self)

class MultiInstruction:
    def __init__(self, name: str, bf_code_func: BFCodeGeneratorFunc):
        self.name = name
        self.bf_code_func = bf_code_func

def bfasm_ins(name: Optional[str] = None):
    def wrapper(func: BFCodeFunc):
        INSTRUCTIONS.append(Instruction(name or func.__name__, func))
        return func
    return wrapper

def bfasm_multi_ins(name: Optional[str] = None):
    def wrapper(func: BFCodeGeneratorFunc):
        MULTI_INSTRUCTIONS.append(MultiInstruction(name or func.__name__, func))
        return func
    return wrapper

def clean_instructions():
    for ins in MULTI_INSTRUCTIONS:
        if isinstance(ins, MultiInstruction):
            def ins_name(i: int):
                return ins.name if i == 0 else f"{ins.name}_{i}"
            code_generator = ins.bf_code_func()
            i = 0
            while True:
                INSTRUCTIONS.append(Instruction(ins_name(i), lambda: BFCode()))
                INSTRUCTIONS.append(Instruction(ins_name(i + 1), lambda: BFCode()))
                code = next(code_generator, None)
                INSTRUCTIONS.pop()
                if code is None:
                    INSTRUCTIONS.pop()
                    break
                INSTRUCTIONS[-1].code = code
                i += 1

def get_instruction(name: str):
    for ins in INSTRUCTIONS:
        if isinstance(ins, Instruction) and ins.name == name:
            return ins
    raise ValueError(f"Instruction {name} not found.")
