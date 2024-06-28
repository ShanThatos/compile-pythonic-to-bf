# type: ignore

# Credits to https://www.nayuki.io/page/optimizing-brainfuck-compiler
# I have built a slightly modified version of bfc.py that 
# optimizes even more common operations


# 
# Optimizing brainfuck compiler
# 
# This script translates brainfuck source code into C/Java/Python source code.
# Usage: python bfc.py BrainfuckFile OutputFile.c/java/py
# 
# Copyright (c) 2023 Project Nayuki
# All rights reserved. Contact Nayuki for licensing.
# https://www.nayuki.io/page/optimizing-brainfuck-compiler
# 

import pathlib, re, sys
from typing import Callable, Dict, Iterator, List, Optional, Sequence, Set, Tuple


# ---- Intermediate representation (IR) ----

class Command:  # Common superclass
	def __eq__(self, other):
		if not isinstance(other, self.__class__):
			return False
		return self.__dict__ == other.__dict__

	def __repr__(self):
		nm = self.__class__.__name__
		return nm + "(" + ", ".join(f"{k}={v}" for k,v in self.__dict__.items()) + ")"

class Assign(Command):
	def __init__(self, offset: int, value: int):
		self.offset = offset
		self.value = value

class Add(Command):
	def __init__(self, offset: int, value: int):
		self.offset = offset
		self.value = value

class MultAssign(Command):
	def __init__(self, srcOff: int, destOff: int, value: int):
		self.srcOff = srcOff
		self.destOff = destOff
		self.value = value

class MultAdd(Command):
	def __init__(self, srcOff: int, destOff: int, value: int):
		self.srcOff = srcOff
		self.destOff = destOff
		self.value = value

class Right(Command):
	def __init__(self, offset: int):
		self.offset = offset

class Input(Command):
	def __init__(self, offset: int):
		self.offset = offset

class Output(Command):
	def __init__(self, offset: int):
		self.offset = offset

class Dbg(Command):
	def __init__(self, offset: int):
		self.offset = offset

class If(Command):
	def __init__(self, commands: List[Command]):
		self.commands = commands

class Loop(Command):
	def __init__(self, commands: List[Command]):
		self.commands = commands

class Glider(Command):
	def __init__(self, offset: int, target: int):
		self.offset = offset
		self.target = target

class DecMove(Command):
	def __init__(self, offset: int, max_moves: int):
		self.offset = offset
		self.max_moves = max_moves

class MemMove(Command):
	def __init__(self, srcOff: int, destOff: int, mem_size: int):
		self.srcOff = srcOff
		self.destOff = destOff
		self.mem_size = mem_size

# ---- Main ----

def main(args: Sequence[str]) -> Optional[str]:
	# Handle command-line arguments
	if len(args) != 2:
		return "Usage: python bfc.py BrainfuckFile OutputFile.c/java/py"
	
	inpath: pathlib.Path = pathlib.Path(args[0])
	if not inpath.is_file():
		return f"{inpath}: Not a file"
	
	outpath: pathlib.Path = pathlib.Path(args[1])
	outfunc: Callable[[List[Command],str,bool,int], str]
	if   outpath.suffix == ".c"   :  outfunc = commands_to_c
	else:  return f"{outpath}: Unknown output type"
	
	# Read input
	with inpath.open("rt") as fin:
		incode = fin.read()
	
	# Parse and optimize Brainfuck code
	commands = parse(incode)
	commands = optimize_gliders(commands)
	# commands = optimize_decmoves(commands)
	commands = optimize(commands)
	commands = optimize(commands)
	commands = optimize(commands)
	commands = optimize_memmoves(commands)
	
	# Write output
	outcode = outfunc(commands, outpath.stem)
	with outpath.open("wt") as fout:
		fout.write(outcode)
	return None


# ---- Parser ----

# Parses the given raw code string, returning a list of Command objects.
def parse(codestr: str) -> List[Command]:
	codestr = re.sub(r"[^+\-<>.,\[\]@]", "", codestr)  # Keep only the 8 Brainfuck characters
	return _parse(iter(codestr), True)


def _parse(chargen: Iterator[str], maincall: bool) -> List[Command]:
	result: List[Command] = []
	for c in chargen:
		item: Command
		if   c == "+": item = Add(0, +1)
		elif c == "-": item = Add(0, -1)
		elif c == "<": item = Right(-1)
		elif c == ">": item = Right(+1)
		elif c == ",": item = Input (0)
		elif c == ".": item = Output(0)
		elif c == "@": item = Dbg(0)
		elif c == "[": item = Loop(_parse(chargen, False))
		elif c == "]":
			if maincall:
				raise ValueError("Extra loop closing")
			else:
				return result
		else:
			raise AssertionError("Illegal code character")
		result.append(item)
	
	if maincall:
		return result
	else:
		raise ValueError("Unclosed loop")


# ---- Optimizers ----

# Optimizes the given list of Commands, returning a new list of Commands.
def optimize(commands: List[Command]) -> List[Command]:
	result: List[Command] = []
	offset: int = 0  # How much the memory pointer has moved without being updated
	off: int
	prev: Optional[Command]
	for cmd in commands:
		if isinstance(cmd, Assign):
			# Try to fuse into previous command
			off = cmd.offset + offset
			prev = result[-1] if len(result) >= 1 else None
			if isinstance(prev, (Add,Assign)) and prev.offset == off \
					or isinstance(prev, (MultAdd,MultAssign)) and prev.destOff == off:
				del result[-1]
			result.append(Assign(off, cmd.value))
		elif isinstance(cmd, MultAssign):
			result.append(MultAssign(cmd.srcOff + offset, cmd.destOff + offset, cmd.value))
		elif isinstance(cmd, Add):
			# Try to fuse into previous command
			off = cmd.offset + offset
			prev = result[-1] if len(result) >= 1 else None
			if isinstance(prev, Add) and prev.offset == off:
				prev.value = (prev.value + cmd.value) & 0xFF
			elif isinstance(prev, Assign) and prev.offset == off:
				prev.value = (prev.value + cmd.value) & 0xFF
			else:
				result.append(Add(off, cmd.value))
		elif isinstance(cmd, MultAdd):
			# Try to fuse into previous command
			off = cmd.destOff + offset
			prev = result[-1] if len(result) >= 1 else None
			if isinstance(prev, Assign) and prev.offset == off and prev.value == 0:
				result[-1] = MultAssign(cmd.srcOff + offset, off, cmd.value)
			else:
				result.append(MultAdd(cmd.srcOff + offset, off, cmd.value))
		elif isinstance(cmd, Right):
			offset += cmd.offset
		elif isinstance(cmd, Input):
			result.append(Input(cmd.offset + offset))
		elif isinstance(cmd, Output):
			result.append(Output(cmd.offset + offset))
		elif isinstance(cmd, Dbg):
			result.append(Dbg(cmd.offset + offset))
		else:
			# Commit the pointer movement before starting a loop/if
			if offset != 0:
				result.append(Right(offset))
				offset = 0
			
			if isinstance(cmd, Loop):
				temp0: Optional[List[Command]] = optimize_simple_loop(cmd.commands)
				if temp0 is not None:
					result.extend(temp0)
				else:
					temp1: Optional[If] = optimize_complex_loop(cmd.commands)
					if temp1 is not None:
						result.append(temp1)
					else:
						# result.append(Loop(optimize(cmd.commands)))
						temp2: Optional[If] = optimize_if_loop(cmd.commands)
						if temp2 is not None:
							result.append(temp2)
						else:
							result.append(Loop(optimize(cmd.commands)))
			elif isinstance(cmd, If):
				result.append(If(optimize(cmd.commands)))
			elif isinstance(cmd, Glider | DecMove):
				result.append(cmd)
			else:
				raise AssertionError("Unknown command")
	
	# Commit the pointer movement before exiting this block
	if offset != 0:
		result.append(Right(offset))
	return result


# Tries to optimize the given list of looped commands into a list that would be executed without looping. Returns None if not possible.
def optimize_simple_loop(commands: List[Command]) -> Optional[List[Command]]:
	deltas: Dict[int,int] = {}  # delta[i] = v means that in each loop iteration, mem[p + i] is added by the amount v
	offset: int = 0
	for cmd in commands:
		# This implementation can only optimize loops that consist of only Add and Right
		if isinstance(cmd, Add):
			off = cmd.offset + offset
			deltas[off] = deltas.get(off, 0) + cmd.value
		elif isinstance(cmd, Right):
			offset += cmd.offset
		else:
			return None
	# Can't optimize if a loop iteration has a net pointer movement, or if the cell being tested isn't decremented by 1
	if offset != 0 or deltas.get(0, 0) != -1:
		return None
	
	# Convert the loop into a list of multiply-add commands that source from the cell being tested
	del deltas[0]
	result: List[Command] = []
	for off in sorted(deltas.keys()):
		result.append(MultAdd(0, off, deltas[off]))
	result.append(Assign(0, 0))
	return result


# Attempts to convert the body of a while-loop into an if-statement. This is possible if roughly all these conditions are met:
# - There are no commands other than Add/Assign/MultAdd/MultAssign (in particular, no net movement, I/O, or embedded loops)
# - The value at offset 0 is decremented by 1
# - All MultAdd and MultAssign commands read from {an offset other than 0 whose value is cleared before the end in the loop}
def optimize_complex_loop(commands: List[Command]) -> Optional[If]:
	result: List[Command] = []
	origindelta: int = 0
	clears: Set[int] = {0}
	for cmd in commands:
		if isinstance(cmd, Add):
			if cmd.offset == 0:
				origindelta += cmd.value
			else:
				clears.discard(cmd.offset)
				result.append(MultAdd(0, cmd.offset, cmd.value))
		elif isinstance(cmd, (MultAdd,MultAssign)):
			if cmd.destOff == 0:
				return None
			clears.discard(cmd.destOff)
			result.append(cmd)
		elif isinstance(cmd, Assign):
			if cmd.offset == 0:
				return None
			else:
				if cmd.value == 0:
					clears.add(cmd.offset)
				else:
					clears.discard(cmd.offset)
				result.append(cmd)
		else:
			return None
	
	if origindelta != -1:
		return None
	for cmd in result:
		if isinstance(cmd, (MultAdd,MultAssign)) and cmd.srcOff not in clears:
			return None
	
	result.append(Assign(0, 0))
	return If(result)


def optimize_if_loop(commands: List[Command]) -> Optional[If]:
	if not isinstance(commands[0], Assign) or commands[0].offset != 0 or commands[0].value != 0:
		return None

	result: List[Command] = [commands[0]]
	for i in range(1, len(commands)):
		cmd = commands[i]
		if isinstance(cmd, Add):
			if cmd.offset == 0:
				return None
		elif isinstance(cmd, (MultAdd,MultAssign)):
			if cmd.destOff == 0 or cmd.srcOff == 0:
				return None
		elif isinstance(cmd, Assign):
			if cmd.offset == 0:
				return None
		else:
			return None
		result.append(cmd)
	
	return If(result)



def extract_multiple(cmds: List[Command], index: int, cmd: Command) -> int:
	count = 0
	while index + count < len(cmds) and cmds[index + count] == cmd:
		count += 1
	return count


def try_extract_glider(cmds: List[Command], index: int) -> Tuple[Optional[Glider], int]:
	P, M = Add(0, 1), Add(0, -1)
	RR, RL = Right(1), Right(-1)

	p1_count = extract_multiple(cmds, index, P)
	if p1_count == 0 or index + p1_count >= len(cmds): 
		return None, index
	loop = cmds[index + p1_count]
	if not isinstance(loop, Loop): 
		return None, index
	inner_cmds = loop.commands
	m1_count = extract_multiple(inner_cmds, 0, M)
	if m1_count != p1_count: 
		return None, index
	
	rr_count = extract_multiple(inner_cmds, m1_count, RR)
	rl_count = extract_multiple(inner_cmds, m1_count, RL)
	r_count = rr_count + rl_count
	offset = rr_count - rl_count
	
	p2_count = extract_multiple(inner_cmds, m1_count + r_count, P)
	if p2_count != p1_count:
		return None, index
	if m1_count + r_count + p2_count != len(inner_cmds):
		return None, index

	m2_count = min(extract_multiple(cmds, index + p1_count + 1, M), p1_count)
	if m2_count != p1_count:
		return None, index
	
	gl = Glider(offset, 256 - p1_count)
	return gl, index + p1_count + 1 + m2_count

def optimize_gliders(commands: List[Command]) -> List[Command]:
	result: List[Command] = []
	i = 0
	while i < len(commands):
		gl, new_i = try_extract_glider(commands, i)
		if gl is not None:
			result.append(gl)
			i = new_i
		elif hasattr(commands[i], "commands"):
			result.append(type(commands[i])(optimize_gliders(commands[i].commands))) 
			i += 1
		else:
			result.append(commands[i])
			i += 1
	return result

def try_extract_decmove(cmds: List[Command], index: int) -> Tuple[Optional[DecMove], int]:
	M = Add(0, -1)
	R = Right(1)
	loop = cmds[index]
	exp_move_count = None

	for j in range(255):
		if not isinstance(loop, Loop):
			return None, index
		inner_cmds = loop.commands
		if len(inner_cmds) < 3:
			return None, index
		if inner_cmds[0] != M:
			return None, index
		move_count = extract_multiple(inner_cmds, 2, R)
		if exp_move_count is None:
			exp_move_count = move_count
		if move_count != exp_move_count:
			return None, index
		if len(inner_cmds) - 2 != move_count:
			return None, index
		loop = inner_cmds[1]
		if isinstance(loop, Loop) and len(loop.commands) == 1 and loop.commands[0] == M and j > 20:
			return DecMove(exp_move_count, j + 1), index + 1

	return None, index

def optimize_decmoves(commands: List[Command]) -> List[Command]:
	result: List[Command] = []
	i = 0
	while i < len(commands):
		dm, new_i = try_extract_decmove(commands, i)
		if dm is not None:
			result.append(dm)
			i = new_i
		elif hasattr(commands[i], "commands"):
			result.append(type(commands[i])(optimize_decmoves(commands[i].commands)))
			i += 1
		else:
			result.append(commands[i])
			i += 1
	return result

def try_extract_memmoves(cmds: List[Command], index: int) -> Tuple[Optional[DecMove], int]:
	o_index = index
	first_assign = cmds[index]
	if not isinstance(first_assign, MultAssign):
		return None, index
	
	src_offset = first_assign.srcOff
	dest_offset = first_assign.destOff

	def is_move(i: int, offset: int):
		nonlocal src_offset, dest_offset
		if i + 1 >= len(cmds): return False
		if not isinstance(cmds[i], MultAssign): return False
		if cmds[i].value != 1: return False
		if cmds[i].srcOff != src_offset + offset: return False
		if cmds[i].destOff != dest_offset + offset: return False
		if not isinstance(cmds[i + 1], Assign): return False
		if cmds[i + 1].offset != src_offset + offset: return False
		if cmds[i + 1].value != 0: return False
		return True
	
	if not is_move(index, 0): 
		return None, index
	if not (is_move(index + 2, 1) or is_move(index + 2, -1)):
		return None, index
	
	move_dir = 1 if is_move(index + 2, 1) else -1
	move_size = 2
	index += 4

	if not (dest_offset - src_offset < 0 and move_dir == 1 or dest_offset - src_offset > 0 and move_dir == -1):
		return None, o_index

	while True:
		if not is_move(index, move_size * move_dir):
			break
		move_size += 1
		index += 2
	
	if move_dir == -1:
		src_offset -= move_size - 1
		dest_offset -= move_size - 1
	
	if move_size > 10:
		return MemMove(src_offset, dest_offset, move_size), index
	return None, o_index

def optimize_memmoves(commands: List[Command]) -> List[Command]:
	result: List[Command] = []
	i = 0
	while i < len(commands):
		dm, new_i = try_extract_memmoves(commands, i)
		if dm is not None:
			result.append(dm)
			i = new_i
		elif hasattr(commands[i], "commands"):
			result.append(type(commands[i])(optimize_memmoves(commands[i].commands)))
			i += 1
		else:
			result.append(commands[i])
			i += 1
	return result

# ---- Output formatters ----

def commands_to_c(commands: List[Command], name: str, maincall: bool = True, indentlevel: int = 1) -> str:
	def indent(line: str, level: int = indentlevel) -> str:
		return "\t" * level + line + "\n"
	def indent1(line: str) -> str:
		return indent(line, indentlevel + 1)
	
	result: str = ""
	if maincall:
		result += indent("#include <stdint.h>", 0)
		result += indent("#include <stdio.h>", 0)
		result += indent("#include <stdlib.h>", 0)
		result += indent("#include <string.h>", 0)
		result += indent("", 0)
		result += indent("static uint8_t read() {", 0)
		result += indent("int temp = getchar();", 1)
		result += indent("return (uint8_t)(temp != EOF ? temp : 0);", 1)
		result += indent("}", 0)
		result += indent("", 0)
		result += indent("static int BLOCK_SIZE = 9;", 0)
		result += indent("static void dbg(uint8_t mem[], uint8_t *p) {", 0)
		result += indent("printf(\"\\nDBG OUTPUT:\\n\");", 1)
		result += indent("int i, j;", 1)
		result += indent("for (i = 1000; i < 1300; i += BLOCK_SIZE) {", 1)
		result += indent("for (j = 0; j < BLOCK_SIZE; j++) {", 2)
		result += indent("if (p == &mem[i + j])", 3)
		result += indent("printf(\"*%3d \", mem[i + j]);", 4)
		result += indent("else", 3)
		result += indent("printf(\" %3d \", mem[i + j]);", 4)
		result += indent("}", 2)
		result += indent("printf(\"\\n\");", 2)
		result += indent("}", 1)
		result += indent("}", 0)
		result += indent("int main(void) {", 0)
		result += indent("uint8_t mem[1000000] = {0};")
		result += indent("uint8_t *p = &mem[1000];")
		result += indent("uint8_t dm;")
		result += indent("")
	
	for cmd in commands:
		if isinstance(cmd, Assign):
			result += indent(f"p[{cmd.offset}] = {cmd.value}u;")
		elif isinstance(cmd, Add):
			s: str = f"p[{cmd.offset}]"
			if cmd.value == 1:
				s += "++;"
			elif cmd.value == -1:
				s += "--;"
			else:
				s += f" {plusminus(cmd.value)}= {abs(cmd.value)}u;"
			result += indent(s)
		elif isinstance(cmd, MultAssign):
			if cmd.value == 1:
				result += indent(f"p[{cmd.destOff}] = p[{cmd.srcOff}];")
			else:
				result += indent(f"p[{cmd.destOff}] = p[{cmd.srcOff}] * {cmd.value};")
		elif isinstance(cmd, MultAdd):
			if abs(cmd.value) == 1:
				result += indent(f"p[{cmd.destOff}] {plusminus(cmd.value)}= p[{cmd.srcOff}];")
			else:
				result += indent(f"p[{cmd.destOff}] {plusminus(cmd.value)}= p[{cmd.srcOff}] * {abs(cmd.value)}u;")
		elif isinstance(cmd, Right):
			if cmd.offset == 1:
				result += indent("p++;")
			elif cmd.offset == -1:
				result += indent("p--;")
			else:
				result += indent(f"p {plusminus(cmd.offset)}= {abs(cmd.offset)};")
		elif isinstance(cmd, Input):
			result += indent(f"p[{cmd.offset}] = read();")
		elif isinstance(cmd, Output):
			result += indent(f"putchar(p[{cmd.offset}]);")
		elif isinstance(cmd, Dbg):
			result += indent(f"dbg(mem, &p[{cmd.offset}]);")
		elif isinstance(cmd, If):
			result += indent("if (*p) {")
			result += commands_to_c(cmd.commands, name, False, indentlevel + 1)
			result += indent("}")
		elif isinstance(cmd, Loop):
			result += indent("while (*p) {")
			result += commands_to_c(cmd.commands, name, False, indentlevel + 1)
			result += indent("}")
		elif isinstance(cmd, Glider):
			result += indent(f"while (*p != {cmd.target}) {{")
			result += commands_to_c([Right(cmd.offset)], name, False, indentlevel + 1)
			result += indent("}")
		elif isinstance(cmd, DecMove):
			if cmd.max_moves < 255:
				result += indent(f"dm = *p < {cmd.max_moves} ? *p : {cmd.max_moves};")
				result += indent("*p -= dm;")
				result += indent(f"p += {cmd.offset} * dm;")
			else:
				result += indent(f"dm = *p;")
				result += indent("*p = 0;")
				result += indent(f"p += {cmd.offset} * dm;")
		elif isinstance(cmd, MemMove):
			result += indent(f"memmove(p {plusminus(cmd.destOff)} {abs(cmd.destOff)}, p {plusminus(cmd.srcOff)} {abs(cmd.srcOff)}, {cmd.mem_size});")
			set_zero_range = sorted(set(range(cmd.srcOff, cmd.srcOff + cmd.mem_size)) - set(range(cmd.destOff, cmd.destOff + cmd.mem_size)))
			for x in set_zero_range:
				result += indent(f"p[{x}] = 0;")
		else:
			raise AssertionError("Unknown command")
	
	if maincall:
		result += indent("")
		result += indent("return EXIT_SUCCESS;")
		result += indent("}", 0)
	return result


def plusminus(val: int) -> str:
	if val >= 0:
		return "+"
	else:
		return "-"



# ---- Miscellaneous ----

if __name__ == "__main__":
	errmsg = main(sys.argv[1 : ])
	if errmsg is not None:
		sys.exit(errmsg)