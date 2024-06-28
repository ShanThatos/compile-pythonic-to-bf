import re
from typing import Iterable, List, Optional, Union


def simplify(code):
    code = re.sub(r"[^<>+-.,\[\]@]", "", code)
    deletes = ["<>", "><", "+-", "-+"]
    replaces = {x:"" for x in deletes} | {"[[-]]":"[-]", "][-]": "]"}
    while any(k in code for k in replaces):
        for k,v in replaces.items():
            code = code.replace(k, v)
    return code

class BFOp:
    def __init__(self, op: str):
        self.op = op

OPS = [BFOp(op) for op in "+-><.,[]@"]
OPS_MAP = {op.op: op for op in OPS}

def parse(code: str) -> List[BFOp]:
    return [OPS_MAP[op] for op in code if op in OPS_MAP]

type BFCodeLike = Union[Iterable[BFOp], str]

class BFNode:
    def __init__(self, code: Optional[BFCodeLike] = None, repeat: int = 1, next: Optional["BFNode"] = None):
        if isinstance(code, str):
            code = parse(code)
        self.code = code
        self.repeat = repeat
        self.next = next
    
    def __iter__(self):
        if self.code is not None:
            for _ in range(self.repeat):
                yield from self.code


class BFCode:
    def __init__(self, code: Optional[BFCodeLike] = None):
        self.code = BFNode(code)


    def __append(self, code: BFCodeLike):
        current = self.code
        while current.next is not None:
            current = current.next
        current.next = BFNode(code)


    def __iter__(self):
        current = self.code
        while current is not None:
            yield from current
            current = current.next


    def __iadd__(self, other: BFCodeLike):
        self.__append(other)
        return self

    def __add__(self, other: BFCodeLike):
        ret = BFCode(self)
        ret += other
        return ret
    
    def __radd__(self, other: BFCodeLike):
        ret = BFCode(other)
        ret += self
        return ret
    

    def __imul__(self, amt: int):
        assert(amt >= 0)
        if amt == 0:
            self.code = BFNode()
        else:
            self.code = BFNode(self.code, repeat=amt)
        return self
    
    def __mul__(self, amt: int):
        ret = BFCode(self)
        ret *= amt
        return ret
    
    def __rmul__(self, amt: int):
        return self.__mul__(amt)

    def to_bf(self) -> str:
        return simplify("".join(op.op for op in self))
    
    def copy(self) -> "BFCode":
        return BFCode(self.to_bf())


