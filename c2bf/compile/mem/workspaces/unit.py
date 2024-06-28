from c2bf.compile.mem.units import memunit, unit
from c2bf.compile.mem.workspace import workspace


@memunit
class prevunit(unit):
    pass

@memunit
class nextunit(unit):
    pass

UNIT = workspace([prevunit, unit, nextunit], unit.marker)