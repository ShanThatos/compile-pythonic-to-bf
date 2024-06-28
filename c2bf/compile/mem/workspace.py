from typing import List, Type

from c2bf.bf.code.common import bf_b, bf_f, bf_set, bf_sum
from c2bf.bf.code.main import BFCode
from c2bf.compile.mem.units import USIZE, memrange, unit

type CodeParam = BFCode | str

class workspace:
    def __init__(self, units: List[Type[unit]], reference: memrange):
        self.units = units
        self.reference = reference

    def get_index(self, mr: memrange):
        for i, unit in enumerate(self.units):
            if mr.unit == unit:
                return i * USIZE + mr.index
        raise ValueError("memrange not found in workspace")

    def get_distance(self, mr: memrange):
        return self.get_index(mr) - self.get_index(self.reference)

    @property
    def size(self):
        return len(self.units) * USIZE


    # movement
    def to(self, mr: memrange):
        return bf_f(self.get_distance(mr))
    def back(self, mr: memrange):
        return bf_b(self.get_distance(mr))

    def tb(self, mr: memrange, code: CodeParam):
        return self.to(mr) + code + self.back(mr)
    def bt(self, mr: memrange, code: CodeParam):
        return self.back(mr) + code + self.to(mr)


    # memory
    def clear(self, mr: memrange):
        return bf_sum(self.tb(mc, "[-]") for mc in mr)
    def set(self, mr: memrange, vals: List[int]):
        assert(mr.size == len(vals))
        return bf_sum(self.tb(mc, bf_set(v, True)) for mc, v in zip(mr, vals))
    
    def move(self, src: memrange, dest: memrange):
        assert(src.size == dest.size)
        return self.clear(dest) + bf_sum(self.foreach(s, self.inc(d)) for s, d in zip(src, dest))
    def copy(self, src: memrange, dest: memrange, temp: memrange):
        assert(src.size == dest.size)
        assert(temp.size == 1)
        code = self.clear(temp) + self.clear(dest)
        for s, d in zip(src, dest):
            code += self.foreach(s, self.inc(d) + self.inc(temp))
            code += self.foreach(temp, self.inc(s))
        return code


    # math
    def inc(self, mr: memrange):
        return bf_sum(self.tb(mc, "+") for mc in mr)
    def dec(self, mr: memrange):
        return bf_sum(self.tb(mc, "-") for mc in mr)

    def inc_num(self, mr: memrange, t1: memrange, t2: memrange, clear_temps = True):
        if mr.size == 1: 
            return self.inc(mr)
        code = BFCode()
        if clear_temps:
            code += self.clear(t1) + self.clear(t2)
        code += self.inc(mr[-1]) + self.copy(mr[-1], t1, t2) + self.not_(t1, t2)
        code += self.if_(t1, self.inc_num(mr[:-1], t1, t2, False))
        return code
    def dec_num(self, mr: memrange, t1: memrange, t2: memrange, clear_temps = True):
        if mr.size == 1:
            return self.dec(mr)
        code = BFCode()
        if clear_temps:
            code += self.clear(t1) + self.clear(t2)
        code += self.copy(mr[-1], t1, t2) + self.dec(mr[-1]) + self.not_(t1, t2)
        code += self.if_(t1, self.dec_num(mr[:-1], t1, t2, False))
        return code

    def lshift(self, mr: memrange, t1: memrange, t2: memrange):
        assert(t1.size == t2.size == 1)
        code = self.clear(t1) + self.clear(t2)
        for i, mc in enumerate(mr):
            if i == 0:
                code += self.foreach(mc, self.inc(t1) * 2) + self.move(t1, mc)
            else:
                code += self.foreach(mc, self.inc(t1) * 2 + self.inc(t2))
                code += self.loop(t1, self.dec(t1) * 2 + self.inc(mc) * 2 + self.dec(t2))
                code += self.if_(t2, self.inc(mr[i - 1]))
        return code
    def rshift(self, mr: memrange, t1: memrange, t2: memrange):
        assert(t1.size == t2.size == 1)
        code = self.clear(t1) + self.clear(t2)
        for i in range(mr.size - 1, -1, -1):
            mc = mr[i]
            code += self.foreach(mc, self.inc(t1) + self.inc(t2) * 128)
            code += self.if_(t2, self.dec(t1) + self.inc(mr[i + 1]) * 128 * (i != mr.size - 1))
            code += self.loop(t1, self.dec(t1) * 2 + self.inc(mc))
        return code


    # logic
    def not_(self, mr: memrange, temp: memrange):
        assert(mr.size == 1)
        assert(temp.size == 1)
        return self.set(temp, [1]) + self.if_(mr, self.dec(temp)) + self.move(temp, mr)

    def eq(self, mr1: memrange, mr2: memrange):
        assert(mr1.size == mr2.size == 1)
        return self.foreach(mr2, self.dec(mr1)) + self.not_(mr1, mr2)

    def and_(self, result: memrange, *mrs: memrange):
        assert(result.size == 1)
        code = self.clear(result)
        short_circuit = self.set(result, [1])
        for mr in mrs:
            for mc in mr:
                short_circuit = self.if_(mc, short_circuit)
        code += short_circuit
        return code

    def or_(self, result: memrange, *mrs: memrange):
        assert(result.size == 1)
        code = self.clear(result)
        for mr in mrs:
            for mc in mr:
                code += self.if_(mc, self.set(result, [1]))
        return code
    def or_keep(self, result: memrange, temp: memrange, *mrs: memrange):
        assert(result.size == 1)
        assert(temp.size == 1)
        code = self.clear(result) + self.clear(temp)
        for mr in mrs:
            for mc in mr:
                code += self.loop(mc, self.move(mc, temp) + self.set(result, [1])) + self.move(temp, mc)
        return code


    # control
    def if_(self, mr: memrange, code: CodeParam):
        assert(mr.size == 1)
        return self.tb(mr, "[[-]" + self.bt(mr, code) + "]")

    def loop(self, mr: memrange, code: CodeParam):
        assert(mr.size == 1)
        return self.tb(mr, "[" + self.bt(mr, code) + "]")
    def foreach(self, mr: memrange, code: CodeParam):
        assert(mr.size == 1)
        return self.tb(mr, "[-" + self.bt(mr, code) + "]")
    def while_(self, mr: memrange, expr: CodeParam, code: CodeParam):
        assert(mr.size == 1)
        return self.set(mr, [255]) + self.loop(mr, self.inc(mr) + self.if_(mr, code) + expr)

