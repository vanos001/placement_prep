# Clang/LLVM

## Introduction

Clang is a compiler front-end for the C, C++, and Objective-C languages, built on
top of the LLVM compiler infrastructure. Together, Clang/LLVM form a modern, modular
compiler toolchain that has become a major alternative to GCC. Clang is known for
its fast compilation, excellent diagnostics, and modular architecture.

LLVM is not just a compiler — it's a collection of reusable compiler and toolchain
components. The name originally stood for "Low Level Virtual Machine" but is now
just "LLVM". Projects like Rust, Swift, Julia, and many GPU shader compilers are
built on LLVM.

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        Front Ends                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │  Clang   │  │  rustc   │  │  swiftc  │  │ Other front  │ │
│  │ (C/C++/  │  │ (Rust)   │  │ (Swift)  │  │ ends         │ │
│  │  ObjC)   │  │          │  │          │  │              │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │
└───────┼──────────────┼─────────────┼───────────────┼─────────┘
        │              │             │               │
        └──────────────┴──────┬──────┴───────────────┘
                              │
                    ┌─────────▼─────────┐
                    │    LLVM IR        │
                    │  (Intermediate    │
                    │   Representation) │
                    └─────────┬─────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│                      LLVM Middle End                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Analysis │  │Optimization│ │Transform │  │ Pass Manager │ │
│  │ Passes   │  │ Passes   │  │ Passes   │  │              │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
└─────────────────────────────┬─────────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│                       LLVM Back End                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │  x86_64  │  │  AArch64 │  │  RISC-V  │  │  ARM, MIPS,  │ │
│  │  Target  │  │  Target  │  │  Target  │  │  WebAssembly │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
└─────────────────────────────┬─────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Machine Code    │
                    │  (Object files)   │
                    └───────────────────┘
```

## LLVM IR (Intermediate Representation)

LLVM IR is a typed, SSA-based (Static Single Assignment) intermediate representation.
It's the lingua franca of the LLVM ecosystem — all front-ends produce IR, and all
back-ends consume it.

### LLVM IR Basics

```llvm
; hello.ll — Simple LLVM IR
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@.str = private constant [14 x i8] c"Hello, World!\00"

declare i32 @printf(i8*, ...)

define i32 @main() {
entry:
  %ptr = getelementptr [14 x i8], [14 x i8]* @.str, i64 0, i64 0
  %call = call i32 (i8*, ...) @printf(i8* %ptr)
  ret i32 0
}
```

### SSA Form

```
; Every value is assigned exactly once
; New values for each "version"

define i32 @example(i32 %a, i32 %b) {
entry:
  %sum = add i32 %a, %b          ; %sum is defined once
  %product = mul i32 %sum, %a    ; uses %sum
  %result = add i32 %product, %b ; new definition
  ret i32 %result
}

; PHI nodes for control flow merging
define i32 @phi_example(i32 %x) {
entry:
  %cmp = icmp sgt i32 %x, 0
  br i1 %cmp, label %then, label %else

then:
  %double = mul i32 %x, 2
  br label %merge

else:
  %triple = mul i32 %x, 3
  br label %merge

merge:
  %result = phi i32 [%double, %then], [%triple, %else]
  ret i32 %result
}
```

### Working with LLVM IR

```bash
# Generate LLVM IR from C
clang -S -emit-llvm -O2 -o hello.ll hello.c

# Compile LLVM IR to assembly
llc -o hello.s hello.ll

# Compile LLVM IR to object
llc -filetype=obj -o hello.o hello.ll

# Interpret LLVM IR (for testing)
lli hello.ll

# Optimize LLVM IR
opt -O2 -o hello_opt.ll hello.ll

# View optimization passes
opt -O2 -S -print-pipeline-passes hello.ll

# Analyze LLVM IR
opt -passes=dot-cfg -disable-output hello.ll  # Generate CFG dot files
opt -passes=dot-dom -disable-output hello.ll   # Dominator tree
```

## LLVM Passes

Passes are the fundamental unit of transformation in LLVM. Each pass analyzes
or transforms the IR.

### Pass Types

| Type | Purpose | Examples |
|------|---------|---------|
| Analysis Pass | Compute information | AliasAnalysis, LoopInfo |
| Transform Pass | Modify IR | InstCombine, LICM, SLP |
| Utility Pass | Infrastructure | Verifier, PrintModule |

### Key Optimization Passes

```
┌─────────────────────────────────────────────────────────┐
│                LLVM Pass Pipeline                         │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Module Passes                                      │ │
│  │  - GlobalOpt (global variable optimization)         │ │
│  │  - DeadArgumentElimination                          │ │
│  │  - Inline (function inlining)                       │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Function Passes                                    │ │
│  │  - SimplifyCFG (simplify control flow)              │ │
│  │  - InstCombine (combine instructions)               │ │
│  │  - SROA (scalar replacement of aggregates)          │ │
│  │  - GVN (global value numbering)                     │ │
│  │  - LICM (loop-invariant code motion)                │ │
│  │  - LoopVectorize (auto-vectorization)               │ │
│  │  - SLPVectorize (superword-level parallelism)       │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Loop Passes                                        │ │
│  │  - LoopRotate (normalize loops)                     │ │
│  │  - LoopUnroll (unroll loops)                        │ │
│  │  - LoopStrengthReduce (address mode optimization)   │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### New Pass Manager

```bash
# Use the new pass manager syntax
opt -passes='default<O2>' -S input.ll -o output.ll

# Custom pass pipeline
opt -passes='function(instcombine,simplifycfg),module(inline)' -S input.ll -o output.ll

# List available passes
opt --print-pipeline-passes -disable-output < /dev/null 2>&1 | head -50
```

## Clang Compilation

### Basic Compilation

```bash
# Simple compilation
clang -o myprogram myprogram.c

# With warnings (Clang's excellent diagnostics)
clang -Wall -Wextra -o myprogram myprogram.c

# With optimization
clang -O2 -o myprogram myprogram.c

# Generate LLVM IR
clang -S -emit-llvm -o myprogram.ll myprogram.c

# Generate bitcode
clang -c -emit-llvm -o myprogram.bc myprogram.c

# Link bitcode files
llvm-link a.bc b.bc -o merged.bc
```

### Clang Diagnostics

Clang is known for its superior diagnostic output:

```
$ clang -Wall -Wextra myprogram.c
myprogram.c:10:5: warning: variable 'x' is uninitialized when used here [-Wuninitialized]
    printf("%d\n", x);
                   ^
myprogram.c:9:9: note: initialize the variable 'x' to silence this warning
    int x;
        ^
         = 0

myprogram.c:15:5: warning: implicit conversion turns floating-point number into integer:
      'float' to 'int' [-Wfloat-conversion]
    int y = 3.14f;
        ~   ^~~~~

myprogram.c:20:5: error: use of undeclared identifier 'foo'
    foo();
    ^
```

Features of Clang diagnostics:
- **Column-precise error locations** with underline
- **Fix-it hints** (suggested corrections)
- **Note chains** (show related code locations)
- **Macro expansion traces**
- **Template instantiation traces** (C++)

### Clang-Specific Features

```bash
# Thread safety analysis
clang -Wthread-safety -o myprogram myprogram.c

# Static analyzer
clang --analyze -Xanalyzer -analyzer-output=text myprogram.c

# Clang-tidy (linting + modernization)
clang-tidy myprogram.c -- -Wall -Wextra

# Clang-format (code formatting)
clang-format -i myprogram.c

# AddressSanitizer
clang -fsanitize=address -g -o myprogram myprogram.c

# MemorySanitizer (better than GCC's)
clang -fsanitize=memory -g -o myprogram myprogram.c

# UndefinedBehaviorSanitizer
clang -fsanitize=undefined -g -o myprogram myprogram.c

# ThreadSanitizer
clang -fsanitize=thread -g -o myprogram myprogram.c

# Coverage
clang -fprofile-instr-generate -fcoverage-mapping -o myprogram myprogram.c
./myprogram
llvm-profdata merge -sparse default.profraw -o default.profdata
llvm-cov show ./myprogram -instr-profile=default.profdata
```

## GCC vs Clang Comparison

| Feature | GCC | Clang/LLVM |
|---------|-----|------------|
| License | GPLv3 | Apache 2.0 with LLVM Exception |
| Languages | C, C++, Fortran, Go, Ada, D | C, C++, ObjC, Swift, OpenCL |
| Compilation speed | Good | Faster |
| Diagnostic quality | Good | Excellent |
| C++ standards support | Good | Leading |
| Optimization quality | Excellent (often better for Fortran) | Excellent (often better for C++) |
| Cross-compilation | Supported | Better (native cross support) |
| IDE integration | Good | Excellent (libclang) |
| Error recovery | Good | Excellent |
| Modularity | Monolithic | Highly modular |
| Static analysis | -fanalyzer | Clang Static Analyzer, clang-tidy |
| Sanitizers | ASan, UBSan, TSan | ASan, UBSan, TSan, MSan (best) |
| LTO | -flto | -flto (ThinLTO is superior) |
| Target architectures | Many | Many (extensible) |
| Linker | ld (GNU) | lld (faster) |

## clang-tidy — Linting and Modernization

clang-tidy is a clang-based C++ "linter" and static analysis tool with automatic
fix capabilities.

### Usage

```bash
# Basic usage
clang-tidy myprogram.cpp -- -std=c++17

# With compile_commands.json (from CMake)
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON .
clang-tidy myprogram.cpp

# List available checks
clang-tidy --list-checks

# Enable specific checks
clang-tidy -checks='-*,modernize-*,readability-*' myprogram.cpp

# Fix automatically
clang-tidy --fix myprogram.cpp -- -std=c++17

# Fix only specific checks
clang-tidy --fix --fix-checks='modernize-use-auto' myprogram.cpp -- -std=c++17
```

### Common Check Categories

| Category | Description |
|----------|-------------|
| `bugprone-*` | Likely bugs (e.g., dangling references) |
| `cert-*` | CERT coding standard |
| `cppcoreguidelines-*` | C++ Core Guidelines |
| `google-*` | Google coding standards |
| `misc-*` | Miscellaneous checks |
| `modernize-*` | Use C++11/14/17 features |
| `performance-*` | Performance anti-patterns |
| `readability-*` | Readability improvements |

### Popular Checks

```yaml
# .clang-tidy
Checks: >
  -*,
  bugprone-*,
  modernize-*,
  performance-*,
  readability-identifier-naming,
  readability-implicit-bool-conversion,
  readability-redundant-member-init

CheckOptions:
  - key: readability-identifier-naming.ClassCase
    value: CamelCase
  - key: readability-identifier-naming.FunctionCase
    value: camelBack
  - key: readability-identifier-naming.VariableCase
    value: camelBack
```

### Example: modernize-use-auto

```cpp
// Before
std::vector<int>::iterator it = vec.begin();
std::map<std::string, int>::iterator mit = mymap.find("key");

// After (auto-applied by clang-tidy)
auto it = vec.begin();
auto mit = mymap.find("key");
```

## clang-format — Code Formatting

```bash
# Format a file
clang-format -i myprogram.cpp

# Format with specific style
clang-format -style=llvm -i myprogram.cpp
clang-format -style=google -i myprogram.cpp
clang-format -style=mozilla -i myprogram.cpp

# Generate .clang-format from existing style
clang-format -style=llvm -dump-config > .clang-format

# Dry-run (show changes without applying)
clang-format --dry-run myprogram.cpp

# Diff output
clang-format --dry-run -Werror myprogram.cpp
```

### .clang-format Example

```yaml
# .clang-format
BasedOnStyle: LLVM
IndentWidth: 4
TabWidth: 4
UseTab: Never
ColumnLimit: 100
AccessModifierOffset: -4
AllowShortFunctionsOnASingleLine: Inline
AllowShortIfStatementsOnASingleLine: Never
AllowShortLoopsOnASingleLine: false
BreakBeforeBraces: Allman
SortIncludes: CaseSensitive
IncludeBlocks: Regroup
```

## Clang Static Analyzer

The Clang Static Analyzer performs deep path-sensitive analysis to find bugs:

```bash
# Run the static analyzer
clang --analyze myprogram.c

# With HTML output
mkdir -p report
clang --analyze -Xanalyzer -analyzer-output=html -o report/ myprogram.c

# Check specific checkers
clang --analyze -Xanalyzer -analyzer-checker=core,unix myprogram.c

# List available checkers
clang --analyze -Xanalyzer -analyzer-checker-help

# Common checker groups:
#   core         — Core language checks
#   unix         — Unix API checks
#   security     — Security-related checks
#   deadcode     — Dead code detection
#   cplusplus    — C++ specific checks
```

## LLVM Tools

### llvm-config

```bash
# Get LLVM configuration
llvm-config --cxxflags
llvm-config --ldflags
llvm-config --libs core support
llvm-config --system-libs
llvm-config --prefix
llvm-config --version
```

### llvm-dis / llvm-as

```bash
# Disassemble bitcode to IR
llvm-dis myprogram.bc -o myprogram.ll

# Assemble IR to bitcode
llvm-as myprogram.ll -o myprogram.bc
```

### llvm-objdump

```bash
# Disassemble object file
llvm-objdump -d myprogram.o

# Disassemble with source
llvm-objdump -S myprogram.o

# Show sections
llvm-objdump -h myprogram.o

# Show symbols
llvm-objdump -t myprogram.o
```

### llvm-nm

```bash
# List symbols
llvm-nm myprogram.o

# Demangle C++ names
llvm-nm --demangle myprogram.o
```

### llvm-readelf

```bash
# Read ELF headers
llvm-readelf -h myprogram

# Show sections
llvm-readelf -S myprogram

# Show symbols
llvm-readelf -s myprogram

# Show dynamic dependencies
llvm-readelf -d myprogram
```

### llvm-profdata / llvm-cov

```bash
# Profile data for PGO
clang -fprofile-instr-generate -fcoverage-mapping -o myprogram myprogram.c
./myprogram
llvm-profdata merge -sparse default.profraw -o default.profdata
clang -fprofile-instr-use=default.profdata -O2 -o myprogram_opt myprogram.c

# Code coverage
clang -fprofile-instr-generate -fcoverage-mapping -o myprogram myprogram.c
./myprogram
llvm-profdata merge -sparse default.profraw -o default.profdata
llvm-cov report ./myprogram -instr-profile=default.profdata
llvm-cov show ./myprogram -instr-profile=default.profdata
```

## Building LLVM from Source

```bash
# Clone
git clone https://github.com/llvm/llvm-project.git
cd llvm-project

# Build
mkdir build && cd build
cmake -G Ninja ../llvm \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLVM_ENABLE_PROJECTS="clang;clang-tools-extra;lld" \
    -DLLVM_TARGETS_TO_BUILD="X86;AArch64" \
    -DLLVM_ENABLE_ASSERTIONS=ON
ninja -j$(nproc)

# Install
sudo ninja install
```

## LLD — The LLVM Linker

LLD is the LLVM linker, significantly faster than GNU ld:

```bash
# Use LLD with Clang
clang -fuse-ld=lld -o myprogram myprogram.o

# Direct invocation
lld -o myprogram myprogram.o

# LLD is 2-10x faster than GNU ld for large projects
```

## Best Practices

1. **Use Clang for development** — better diagnostics catch bugs earlier
2. **Use GCC for production (sometimes)** — some workloads benefit from GCC's optimizations
3. **Use clang-tidy for C++ modernization** — automated upgrades to modern C++
4. **Use clang-format in CI** — enforce consistent code style
5. **Use Clang's MSan** — GCC's MemorySanitizer is not well supported
6. **Use ThinLTO** — nearly as effective as full LTO, much faster
7. **Use `-Weverything` then selectively disable** — find warnings you didn't know existed
8. **Use `compile_commands.json`** — essential for clang-tidy and IDE integration

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Clang Documentation](https://clang.llvm.org/docs/)
- [LLVM Documentation](https://llvm.org/docs/)
- [LLVM Programmer's Manual](https://llvm.org/docs/ProgrammersManual.html)
- [Clang-Tidy Checks](https://clang.llvm.org/extra/clang-tidy/checks/)
- [Clang-Format Style Options](https://clang.llvm.org/docs/ClangFormatStyleOptions.html)
- [LLVM Tutorial](https://llvm.org/docs/tutorial/)

## Related Topics

- [GCC](./gcc.md) — The GNU Compiler Collection
- [Linker](./linker.md) — Linkers, symbol resolution, and shared libraries
- [Make](./make.md) — Build automation
- [CMake](./cmake.md) — Build system generator
