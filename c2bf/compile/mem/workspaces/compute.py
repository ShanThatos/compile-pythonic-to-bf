from c2bf.compile.mem.units import memunit, unit
from c2bf.compile.mem.workspace import workspace

@memunit
class cnext(unit):
    pass

@memunit
class compute(unit):
    running         = unit.marker

@memunit
class cextra(unit):
    pass

@memunit
class query(unit):
    id              = unit.empty


COMPUTE = workspace([cnext, compute, cextra, query], compute.running)

