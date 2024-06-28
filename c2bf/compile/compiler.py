import shutil
import subprocess
import time
from pathlib import Path
from c2bf.bf import bfc
from c2bf.compile.bfasm.encode import encode_bfasm_to_bytes
from c2bf.compile.bfasm.main import encode_to_bf_with_processor
from c2bf.compile.bfun.combine import parse_resolve_imports
from c2bf.compile.bfun.compilers.program import compile_program
from c2bf.parser.main import ParseError


def ttime(func, *args, **kwargs):
    start = time.time()
    result = func(*args, **kwargs)
    return result, time.time() - start

class BFCompiler:
    def __init__(
            self, 
            filepath: str, 
            heap_size = 500,
            verbose = False, 
            output_path: str = "c2bf-build", 
            compile_to_c = False, 
            execute = False
        ):
        self.filepath = filepath
        self.heap_size = heap_size
        self.verbose = verbose
        self.output_path = Path(output_path)
        self.compile_to_c = compile_to_c
        self.execute = execute
        self.details = []

    def print(self, *args):
        if self.verbose:
            print(*args)

    def run(self):
        self.output_path.mkdir(parents=True, exist_ok=True)

        ast = self.__parse_resolve_imports()
        ast = self.__compile_bfun_to_bfasm(ast)
        bf_code = self.__encode_bfasm_to_bf(ast)

        if self.compile_to_c or self.execute:
            self.__compile_to_c()
        if self.execute:
            self.__compile_to_binary_execute()

        if self.verbose:
            self.__print_details()

        return bf_code
    
    def __parse_resolve_imports(self):
        self.print("parsing code")
        try:
            ast, parse_time = ttime(parse_resolve_imports, self.filepath, import_common=True)
        except ParseError as pe:
            print(pe)
            raise Exception("Failed to parse code")
        self.details.append(("parse time", f"{parse_time:.3f}s"))
        return ast
    
    def __compile_bfun_to_bfasm(self, ast):
        self.print("compiling bfun to bfasm")
        ast, compile_time = ttime(compile_program, ast, heap_size=self.heap_size, output_path=self.output_path)
        self.details.append(("compile time", f"{compile_time:.3f}s"))
        self.__opath_write("code.bfasm", ast.to_string().strip())
        return ast
    
    def __encode_bfasm_to_bf(self, ast):
        self.print("encoding bfasm to bf")
        mem, encode_bytes_time = ttime(encode_bfasm_to_bytes, ast)
        code, encode_bf_time = ttime(encode_to_bf_with_processor, mem)
        bf_code, bf_write_time = ttime(code.to_bf)
        self.details.append(("encode time", f"{encode_bytes_time + encode_bf_time + bf_write_time:.3f}s"))
        self.details.append(("bf code size", len(bf_code)))
        self.__opath_write("code.bf", bf_code)
        return bf_code

    def __compile_to_c(self):
        self.print("compiling bf to c")
        _, compile_time = ttime(bfc.main, (self.__opath("code.bf"), self.__opath("code.c")))
        self.details.append(("bf to c time", f"{compile_time:.3f}s"))

    def __compile_to_binary_execute(self):
        self.print("compiling c to binary [gcc]")
        _, compile_time = ttime(subprocess.run, ["gcc", self.__opath("code.c"), "-o", self.__opath("code")])
        self.details.append(("c to bin time", f"{compile_time:.3f}s"))

        self.print("running")
        self.print("-------")
        _, run_time = ttime(subprocess.run, [self.__opath("code")])
        print()
        self.details.append(("run time", f"{run_time:.3f}s"))

    def __print_details(self):
        print("-------")
        for name, value in self.details:
            print(f"{name+':':20s} {value}")

    def __opath(self, path):
        return str(self.output_path.joinpath(path))
    def __opath_write(self, path, content):
        with open(self.__opath(path), "w") as f:
            f.write(content)

__all__ = ["BFCompiler"]