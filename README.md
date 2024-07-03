# Compiling Pythonic to Brainf**k

BF for the masses! 

[Blog post](https://shanthatos.dev/_/blogs/c2bf-p1)

## Usage Options
```
python launch.py

Output:
No file path provided
Usage: launch.py <filepath> [options]
Options:
  -h, --help:                    Display this help message
  -v, --verbose:                 Verbose output
  -c, --compile-to-c:            Compile to C
  -e, --execute:                 Execute [gcc] (forces -c)
  -o, --output:                  Output path (default: c2bf-build)
  -hs, --heap-size:              Heap size (default: 500)
```

## Examples
```
python .\launch.py -v -e .\examples\helloworld\code.bfun -o .\examples\helloworld\

Output:
parsing code
compiling bfun to bfasm
encoding bfasm to bf
compiling bf to c
compiling c to binary [gcc]
running
-------
Hello World!
-------
parse time:          0.280s
compile time:        0.481s
encode time:         0.798s
bf code size:        115312
bf to c time:        0.716s
c to bin time:       0.577s
run time:            0.214s
```