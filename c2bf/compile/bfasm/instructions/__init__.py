from .capture import *
from .control import *
from .mem import *
from .io import *
from .math.add import *
from .math.bits import *
from .math.logic import *
from .math.mul import *

clean_instructions()

# for ins in INSTRUCTIONS:
#     print(ins.id, ins.name, len(ins.get_code().to_bf()))