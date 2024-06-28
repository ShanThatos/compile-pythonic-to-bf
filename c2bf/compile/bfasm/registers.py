from typing import List, Tuple

from c2bf.config import N

REGISTERS: List[Tuple[str, int]] = [
    # Instruction Pointer
    ("ip", 0),
    # Expression Registers
    ("e0", 0),
    ("e1", 0),
    ("e2", 0),
    ("et", 0),
    # Compare Register
    ("cr", 0),
    # Function Calling
    ("_call_func", 0),
    ("_call_args", 0),
    # Return Value
    ("rv", 0),
    # Misc
    ("r0", 0),
    ("r1", 0),
    ("r2", 0),
    ("r3", 0),
    # this pointer
    ("this", 0),
    # N-constants
    ("_n_bit_size", N*8),
]

def get_register_index(name: str):
    for i, (n, _) in enumerate(REGISTERS):
        if n == name:
            return i
    raise Exception(f"Register {name} not found")

