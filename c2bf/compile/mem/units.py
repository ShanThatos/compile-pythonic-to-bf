from typing import List, Optional, Type, Union

from c2bf.config import N


class memrange:
    def __init__(self, *args, unit: Optional[Type["unit"]] = None):
        self.indices: List[int] = list(*args)
        self.unit = unit
        self.normalize()

    def __getitem__(self, key: Union[int, slice]):
        if isinstance(key, int):
            key = key % self.size
            key = slice(key, key + 1)
        cl = memrange(self.indices[key])
        cl.unit = self.unit
        return cl
    
    def __iter__(self):
        for i in range(self.size):
            yield self[i]

    def __add__(self, other: "memrange"):
        assert(self.unit == other.unit)
        return memrange(self.indices + other.indices, unit=self.unit)

    def normalize(self):
        self.indices = sorted(set(self.indices))

    @property
    def size(self):
        return len(self.indices)

    @property
    def index(self):
        return self.indices[0]

    @property
    def slice(self):
        assert(len(self.indices) > 0)
        for i in range(len(self.indices) - 1):
            assert(self.indices[i] + 1 == self.indices[i + 1])
        return slice(self.indices[0], self.indices[-1] + 1)


def memunit[T: Type["unit"]](unit_class: T) -> T:
    for attr in dir(unit_class):
        if isinstance(cl := getattr(unit_class, attr), memrange):
            setattr(unit_class, attr, memrange(cl.indices, unit=unit_class))
    return unit_class


USIZE = 3 + 3 * N

s = lambda x: memrange([x])
r = lambda x, n: memrange(range(x, x + n))

@memunit
class unit:
    marker   = s(0)
    ipmarker = s(1)
    flag     = s(2)

    empty    = r(3, N)

    data     = r(3 + N, 2 * N)
    data1    = data[:N]
    data2    = data[N:]

    fdata    = flag + data

    all      = r(0, USIZE)


