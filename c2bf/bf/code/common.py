from typing import Iterable

from c2bf.bf.code.main import BFCode



def bf_f(n=1):
    return BFCode(">" if n > 0 else "<") * abs(n)

def bf_b(n=1):
    return BFCode("<" if n > 0 else ">") * abs(n)

def bf_fb(n=1, code: str | BFCode = ""):
    return bf_f(n) + code + bf_b(n)

def bf_bf(n=1, code: str | BFCode = ""):
    return bf_b(n) + code + bf_f(n)

def bf_set(v: int, clear: bool = True):
    return clear * BFCode("[-]") + (BFCode("-") * (256 - v) if v > 128 else BFCode("+") * v)

def bf_glide_f(target: int, step: int):
    assert(target >= 250) # trying to only use high target values
    p = BFCode("+") * (256-target)
    m = BFCode("-") * (256-target)
    return p + "[" + m + BFCode(">") * step + p + "]" + m

def bf_glide_b(target: int, step: int):
    assert(target >= 250) # trying to only use high target values
    p = BFCode("+") * (256-target)
    m = BFCode("-") * (256-target)
    return p + "[" + m + BFCode("<") * step + p + "]" + m

def bf_sum(code: Iterable[BFCode]):
    return sum(code, BFCode())