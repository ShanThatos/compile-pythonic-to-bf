import sys
from pathlib import Path
from c2bf import BFCompiler

ARGS = [
    (["-h", "--help"], "Display this help message", False),
    (["-v", "--verbose"], "Verbose output", False),
    (["-c", "--compile-to-c"], "Compile to C", False),
    (["-e", "--execute"], "Execute [gcc] (forces -c)", False),
    (["-o", "--output"], "Output path (default: c2bf-build)", True),
    (["-hs", "--heap-size"], "Heap size (default: 500)", True),
]
ARG_MAP = {arg[0][0]: arg for arg in ARGS} | {arg[0][1]: arg for arg in ARGS}

def main():
    args = sys.argv[1:]

    unnamed_args = []
    named_args = {}
    i = 0
    while i < len(args):
        if args[i] in ARG_MAP:
            has_val = ARG_MAP[args[i]][2]
            if has_val:
                if i + 1 >= len(args):
                    print(f"Missing value for {args[i]}")
                    return
                named_args[args[i]] = args[i + 1]
                i += 1
            else:
                named_args[args[i]] = True
        else:
            unnamed_args.append(args[i])
        i += 1

    if "-h" in named_args or "--help" in named_args:
        help()
        return
    
    if not unnamed_args:
        print("No file path provided")
        help()
        return

    filepath = unnamed_args[0]
    if not filepath.endswith(".bfun"):
        print("Invalid file path (must end with .bfun)")
        return
    filepath = Path.cwd().joinpath(filepath)
    if not filepath.exists():
        print(f"File '{filepath}' does not exist")
        return


    options = {
        "verbose": "-v" in named_args or "--verbose" in named_args,
        "compile_to_c": "-c" in named_args or "--compile-to-c" in named_args,
        "execute": "-e" in named_args or "--execute" in named_args,
        "output_path": str(Path.cwd().joinpath(named_args.get("-o", named_args.get("--output", "c2bf-build"))).resolve()),
        "heap_size": int(named_args.get("-hs", named_args.get("--heap-size", 500))),
    }

    BFCompiler(str(filepath.resolve()), **options).run()

def help():
    print("Usage: launch.py <filepath> [options]")
    print("Options:")
    for arg in ARGS:
        print(f"  {f"{arg[0][0]}, {arg[0][1]}:":30s} {arg[1]}")

if __name__ == "__main__":
    main()
