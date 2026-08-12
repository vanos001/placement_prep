# GCC — The GNU Compiler Collection

## Introduction

GCC (GNU Compiler Collection) is the standard compiler for Linux and many other
Unix-like systems. It supports C, C++, Fortran, Ada, Go, D, and Objective-C. GCC
is more than a compiler — it's a complete toolchain including a preprocessor,
compiler, assembler, and linker, all orchestrated by a single driver program.

GCC has been the backbone of Linux development since the early 1990s. Understanding
its optimization capabilities, warning system, and advanced features is essential
for writing high-performance, reliable C and C++ code.

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│                     GCC Driver (gcc/g++)                   │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │   cpp    │→ │   cc1    │→ │   as     │→ │   ld     │ │
│  │(preproc) │  │(compile) │  │(assemble)│  │ (link)   │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│                                                           │
│  Source     →  Preprocessed  →  Assembly  →  Object  →   │
│  (.c/.cpp)    (.i)            (.s)         (.o)      Executable│
└───────────────────────────────────────────────────────────┘
```

### Compilation Pipeline

```bash
# Show all compilation steps
gcc -v -o myprogram myprogram.c

# Step by step:
# 1. Preprocessing
gcc -E myprogram.c -o myprogram.i

# 2. Compilation to assembly
gcc -S myprogram.i -o myprogram.s

# 3. Assembly to object
gcc -c myprogram.s -o myprogram.o

# 4. Linking
gcc myprogram.o -o myprogram
```

## Optimization Levels

### Overview

| Level | Description | Debug | Speed | Size |
|-------|-------------|-------|-------|------|
| `-O0` | No optimization (default) | ✅ Best | ❌ Slowest | ❌ Largest |
| `-O1` | Basic optimizations | ✅ Good | ✅ Better | ✅ Better |
| `-O2` | Recommended optimizations | ⚠️ Fair | ✅✅ Good | ✅✅ Good |
| `-O3` | Aggressive optimizations | ⚠️ Poor | ✅✅✅ Best | ❌ Larger |
| `-Os` | Optimize for size | ⚠️ Fair | ✅ Good | ✅✅✅ Smallest |
| `-Og` | Optimize for debugging | ✅ Very good | ✅ Better | ✅ Good |
| `-Ofast` | O3 + fast-math | ❌ Poor | ✅✅✅ Best | ❌ Largest |

### -O1 — Basic Optimizations

```bash
gcc -O1 -o myprogram myprogram.c
```

Includes:
- Dead code elimination
- Constant folding and propagation
- Common subexpression elimination
- Basic register allocation
- Basic block reordering

### -O2 — Recommended Level

```bash
gcc -O2 -o myprogram myprogram.c
```

Adds (beyond -O1):
- Loop optimizations (unrolling, peeling)
- Instruction scheduling
- Alias analysis
- Tail call optimization
- Inter-procedural analysis (limited)
- Vectorization (basic)

### -O3 — Aggressive Optimizations

```bash
gcc -O3 -o myprogram myprogram.c
```

Adds (beyond -O2):
- Loop vectorization (auto-vectorization)
- Loop interchange
- Loop unrolling (aggressive)
- Function cloning
- IPA (Inter-Procedural Analysis)
- Loop distribution
- Tree-loop vectorization

### -Os — Optimize for Size

```bash
gcc -Os -o myprogram myprogram.c
```

Like -O2 but disables optimizations that increase code size:
- No aggressive loop unrolling
- Smaller alignment
- Prefers size-efficient instructions

### -Ofast — Maximum Performance

```bash
gcc -Ofast -o myprogram myprogram.c
```

Includes -O3 plus:
- `-ffast-math`: Relaxes IEEE 754 compliance for faster floating-point
- `-fallow-store-data-races`: May introduce data races for speed

⚠️ **Warning**: `-ffast-math` can change numerical results. Not suitable for
scientific computing without careful testing.

### -Og — Optimize for Debugging

```bash
gcc -Og -o myprogram myprogram.c
```

Optimizations that don't interfere with debugging:
- Constant folding
- Dead code elimination
- But preserves variable values and function structure

## Warnings

### Essential Warning Flags

```bash
# Basic warnings
gcc -Wall -Wextra -o myprogram myprogram.c

# -Wall enables (among others):
#   -Wformat         — printf/scanf format issues
#   -Wreturn-type    — missing return value
#   -Wunused         — unused variables/parameters
#   -Wimplicit       — implicit declarations
#   -Wparentheses    — ambiguous precedence
#   -Wswitch         — missing switch cases
#   -Wuninitialized  — uninitialized variables

# -Wextra adds:
#   -Wsign-compare   — signed/unsigned comparison
#   -Wunused-parameter
#   -Wmissing-field-initializers
#   -Wtype-limits    — always true/false comparisons
```

### Strict and Pedantic

```bash
# Strict standards compliance
gcc -Wall -Wextra -Wpedantic -o myprogram myprogram.c

# -Wpedantic warns about:
#   Non-standard extensions
#   GNU extensions when using -std=c11

# Treat warnings as errors (essential for CI)
gcc -Wall -Wextra -Werror -o myprogram myprogram.c

# Treat specific warning as error
gcc -Werror=return-type -o myprogram myprogram.c

# Treat specific warning as non-error
gcc -Wall -Wno-unused-variable -o myprogram myprogram.c
```

### Advanced Warning Flags

```bash
# Comprehensive warnings
gcc -Wall -Wextra -Wpedantic -Wshadow -Wconversion \
    -Wnull-dereference -Wdouble-promotion \
    -Wformat=2 -Wformat-truncation -Wformat-overflow \
    -Wstrict-overflow=2 -Wstrict-aliasing=2 \
    -Wmissing-include-dirs -Wswitch-enum \
    -Wlogical-op -Wduplicated-cond -Wduplicated-branches \
    -Wrestrict -Warray-bounds=2 \
    -o myprogram myprogram.c

# Specific warning explanations:
# -Wshadow:         Variable shadows another variable
# -Wconversion:     Implicit type conversion that may lose data
# -Wformat=2:       Extended format checking
# -Wlogical-op:     Suspicious logical operations (&& vs ||)
# -Wduplicated-cond: Duplicated conditions in if-else chains
# -Warray-bounds=2: Array bounds checking (aggressive)
```

### Static Analysis Flags

```bash
# Fanalyzer — GCC's built-in static analyzer
gcc -fanalyzer -o myprogram myprogram.c

# Detects:
# - NULL pointer dereferences
# - Double frees
# - Use-after-free
# - Buffer overflows
# - Resource leaks
# - Uninitialized values
```

## Link-Time Optimization (LTO)

LTO performs optimization across translation units at link time, enabling
whole-program analysis.

### How LTO Works

```
Without LTO:
  file1.c → file1.o (optimized individually)
  file2.c → file2.o (optimized individually)
  file1.o + file2.o → binary (link only)

With LTO:
  file1.c → file1.o (GIMPLE IR, not fully optimized)
  file2.c → file2.o (GIMPLE IR, not fully optimized)
  file1.o + file2.o → binary (optimize together, then link)
```

### Using LTO

```bash
# Compile with LTO
gcc -flto -O2 -c file1.c -o file1.o
gcc -flto -O2 -c file2.c -o file2.o
gcc -flto -O2 -o myprogram file1.o file2.o

# Or all at once
gcc -flto -O2 -o myprogram file1.c file2.c

# Thin LTO (faster, parallel, nearly as effective)
gcc -flto=thin -O2 -o myprogram file1.c file2.c

# Fat LTO (keeps both IR and object code)
gcc -flto -ffat-lto-objects -O2 -c file1.c

# LTO with link-time warnings
gcc -flto -O2 -Wl,-plugin-opt=-stats -o myprogram file1.c file2.c
```

### LTO Benefits

- **Cross-module inlining**: Inline functions across translation units
- **Dead code elimination**: Remove unused functions globally
- **Constant propagation**: Propagate constants across files
- **Devirtualization**: Devirtualize C++ virtual calls when target is known
- **Whole-program optimization**: See entire program at once

### LTO with Static Libraries

```bash
# Use gcc-ar and gcc-ranlib for LTO archives
gcc-ar rcs libmylib.a file1.o file2.o
gcc-ranlib libmylib.a
```

## Profile-Guided Optimization (PGO)

PGO uses runtime profiling data to guide optimization decisions. It typically
yields 10-30% performance improvement.

### PGO Workflow

```
┌──────────────┐    Instrumented    ┌──────────────┐
│  Source Code │───────────────────►│  Binary      │
│              │    Compile with    │  (instrum.)  │
└──────────────┘    -fprofile-generate│             │
                                      └──────┬───────┘
                                             │ Run with
                                             │ representative
                                             │ workload
                                             ▼
                                      ┌──────────────┐
                                      │ Profile Data │
                                      │ (.gcda files)│
                                      └──────┬───────┘
                                             │
┌──────────────┐    Re-compile with  ┌───────▼──────┐
│  Optimized   │◄───────────────────│  Source Code │
│  Binary      │    -fprofile-use   │              │
└──────────────┘                    └──────────────┘
```

### PGO Step by Step

```bash
# Step 1: Build instrumented binary
gcc -O2 -fprofile-generate -o myprogram_instr myprogram.c

# Step 2: Run with representative workload
./myprogram_instr < typical_input.txt
./myprogram_instr --benchmark

# This creates .gcda files with profile data

# Step 3: Rebuild with profile data
gcc -O2 -fprofile-use -o myprogram_opt myprogram.c

# Verify profile data is used
gcc -O2 -fprofile-use -fprofile-report -o myprogram_opt myprogram.c
```

### AutoFDO (Automatic Feedback-Directed Optimization)

```bash
# Build with debug info
gcc -O2 -g -o myprogram myprogram.c

# Record profile with perf
perf record -b -o perf.data ./myprogram

# Convert to AutoFDO profile
# Using create_llvm_prof (from AutoFDO project)
create_llvm_prof --binary=./myprogram --profile=perf.data --out=profile.afdo

# Rebuild with AutoFDO profile
gcc -O2 -fauto-profile=profile.afdo -o myprogram_opt myprogram.c
```

## Sanitizers

GCC supports several runtime sanitizers that detect bugs at execution time.

### AddressSanitizer (ASan)

```bash
# Compile with ASan
gcc -fsanitize=address -fno-omit-frame-pointer -g -o myprogram myprogram.c

# Run
./myprogram

# Detects:
# - Heap buffer overflow/underflow
# - Stack buffer overflow
# - Use-after-free
# - Use-after-return
# - Memory leaks (with leak sanitizer)
# - Double-free

# ASan options
ASAN_OPTIONS=detect_leaks=1:halt_on_error=0 ./myprogram
```

### ASan Example Output

```
=================================================================
==1234==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x60200000eff4
WRITE of size 4 at 0x60200000eff4 thread T0
    #0 0x4005b6 in myfunction myprogram.c:10
    #1 0x400678 in main myprogram.c:20

0x60200000eff4 is located 0 bytes to the right of 4-byte region [0x60200000eff0,0x60200000eff4)
allocated by thread T0 here:
    #0 0x7f1234567890 in __interceptor_malloc
    #1 0x400523 in myfunction myprogram.c:8

SUMMARY: AddressSanitizer: heap-buffer-overflow myprogram.c:10 in myfunction
```

### UndefinedBehaviorSanitizer (UBSan)

```bash
gcc -fsanitize=undefined -g -o myprogram myprogram.c

# Detects:
# - Signed integer overflow
# - Shift out of bounds
# - Misaligned pointer dereference
# - NULL pointer dereference
# - Boolean misalignment
# - Invalid enum values
# - VLA bounds
# - Float-cast overflow

# Options
UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 ./myprogram
```

### ThreadSanitizer (TSan)

```bash
gcc -fsanitize=thread -g -o myprogram myprogram.c

# Detects:
# - Data races
# - Deadlocks (with some configurations)
# - Thread leaks
```

### MemorySanitizer (MSan)

```bash
# Note: MSan is better supported in Clang than GCC
# For GCC, use ASan + UBSan instead

# If available:
gcc -fsanitize=memory -fPIE -pie -g -o myprogram myprogram.c
```

### Sanitizer Comparison

| Sanitizer | Detects | Overhead | GCC | Clang |
|-----------|---------|----------|-----|-------|
| ASan | Memory errors | ~2x | ✅ | ✅ |
| UBSan | Undefined behavior | ~1.5x | ✅ | ✅ |
| TSan | Data races | ~5-15x | ✅ | ✅ |
| MSan | Uninitialized reads | ~3x | ⚠️ | ✅ |
| LSan | Memory leaks | ~1.1x | ✅ (via ASan) | ✅ |

## Inline Assembly

GCC supports inline assembly for embedding architecture-specific instructions.

### Basic Syntax

```c
// x86-64 inline assembly
static inline uint64_t rdtsc(void) {
    uint32_t lo, hi;
    __asm__ __volatile__ (
        "rdtsc"
        : "=a"(lo), "=d"(hi)   // outputs
        :                       // inputs
        :                       // clobbers
    );
    return ((uint64_t)hi << 32) | lo;
}

// Extended inline assembly
static inline void cpuid(uint32_t op, uint32_t *eax, uint32_t *ebx,
                         uint32_t *ecx, uint32_t *edx) {
    __asm__ __volatile__ (
        "cpuid"
        : "=a"(*eax), "=b"(*ebx), "=c"(*ecx), "=d"(*edx)
        : "a"(op)
    );
}
```

### Memory Barriers

```c
// Full memory barrier
__asm__ __volatile__ ("mfence" ::: "memory");

// Compiler barrier (prevents reordering)
__asm__ __volatile__ ("" ::: "memory");

// Read barrier
__asm__ __volatile__ ("lfence" ::: "memory");

// Write barrier
__asm__ __volatile__ ("sfence" ::: "memory");
```

### Atomic Operations

```c
// Atomic compare-and-swap
static inline int cas(int *ptr, int old, int new_val) {
    int result;
    __asm__ __volatile__ (
        "lock cmpxchgl %2, %1"
        : "=a"(result), "+m"(*ptr)
        : "r"(new_val), "0"(old)
        : "memory"
    );
    return result;
}
```

## GCC Extensions

### __attribute__ Extensions

```c
// Function attributes
__attribute__((noreturn)) void die(const char *msg);
__attribute__((format(printf, 1, 2))) void myprintf(const char *fmt, ...);
__attribute__((noinline)) void slow_function(void);
__attribute__((always_inline)) inline void fast_function(void);
__attribute__((hot)) void critical_path(void);
__attribute__((cold)) void error_handler(void);

// Variable attributes
__attribute__((aligned(64))) char cache_line_buf[64];
__attribute__((packed)) struct network_header {
    uint8_t version;
    uint16_t length;
    uint32_t src_addr;
};

// Type attributes
typedef int __attribute__((vector_size(16))) v4si;  // 4x int SIMD vector
typedef float __attribute__((vector_size(32))) v8sf; // 8x float SIMD vector

// Section placement
__attribute__((section(".mydata"))) int special_var = 42;
__attribute__((constructor)) void init_func(void) { /* runs before main */ }
__attribute__((destructor)) void fini_func(void) { /* runs after main */ }
```

### Built-in Functions

```c
// Expectation (branch prediction)
if (__builtin_expect(!!(ptr == NULL), 0)) {
    // unlikely path
}

// Unreachable
__builtin_unreachable();

// Population count
int bits = __builtin_popcount(x);

// Bit scan
int first_set = __builtin_ffs(x);

// Byte swap
uint32_t swapped = __builtin_bswap32(x);

// Prefetch
__builtin_prefetch(ptr + 64, 0, 3);  // read, high locality

// Stack protector
void *__builtin_frame_address(0);  // current frame
void *__builtin_return_address(0); // return address
```

### Statement Expressions

```c
// GCC extension: statement expressions ({ ... })
#define MAX(a, b) ({           \
    __typeof__(a) _a = (a);   \
    __typeof__(b) _b = (b);   \
    _a > _b ? _a : _b;        \
})
```

### __int128

```c
// 128-bit integer (GCC extension)
__int128 big = (__int128)1 << 64;
unsigned __int128 ubig = -1;
```

## Diagnostic Pragmas

```c
// Suppress specific warnings for a section of code
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-variable"
    int unused_but_ok = 42;
#pragma GCC diagnostic pop

// Treat specific warning as error locally
#pragma GCC diagnostic error "-Wreturn-type"
```

## GCC Version-Specific Features

```bash
# Check GCC version
gcc --version

# Enable C standard
gcc -std=c11 -o myprogram myprogram.c
gcc -std=c17 -o myprogram myprogram.c
gcc -std=c2x -o myprogram myprogram.c   # C2x draft

# Enable C++ standard
g++ -std=c++17 -o myprogram myprogram.cpp
g++ -std=c++20 -o myprogram myprogram.cpp
g++ -std=c++23 -o myprogram myprogram.cpp

# GNU extensions (enabled by default without -std)
gcc -std=gnu11 -o myprogram myprogram.c  # C11 + GNU extensions
```

## GCC Diagnostic Output

### Understanding GCC Warnings

```
myprogram.c: In function 'main':
myprogram.c:10:5: warning: implicit declaration of function 'foo' [-Wimplicit-function-declaration]
   10 |     foo();
      |     ^~~
myprogram.c:10:5: warning: this function declaration is not a prototype [-Wstrict-prototypes]
myprogram.c:15:12: warning: unused variable 'x' [-Wunused-variable]
   15 |     int x = 42;
      |            ^~
myprogram.c:20:5: warning: control reaches end of non-void function [-Wreturn-type]
   20 | }
      | ^
```

### Colored Output

```bash
# Force colored diagnostics
gcc -fdiagnostics-color=always -o myprogram myprogram.c

# Show source lines with errors
gcc -fdiagnostics-show-option -o myprogram myprogram.c

# JSON output for tooling
gcc -fdiagnostics-format=json -o myprogram myprogram.c
```

## Best Practices

1. **Always use `-Wall -Wextra`** — catch bugs early
2. **Use `-Werror` in CI** — prevent warning regressions
3. **Use `-O2` for production** — best balance of speed and safety
4. **Use `-Og` for debugging** — preserves variable values
5. **Use `-fsanitize=address` during development** — catch memory bugs
6. **Use LTO for release builds** — cross-module optimization
7. **Use PGO for performance-critical code** — 10-30% speedup typical
8. **Use `-march=native` for local builds** — optimize for your CPU
9. **Use `-march=x86-64-v2` for portable builds** — baseline for modern x86
10. **Use `-fstack-protector-strong`** — detect stack buffer overflows

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [GCC Documentation](https://gcc.gnu.org/onlinedocs/)
- [GCC Wiki](https://gcc.gnu.org/wiki/)
- [GCC Optimization Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)
- [GCC Warning Options](https://gcc.gnu.org/onlinedocs/gcc/Warning-Options.html)
- [GCC Instrumentation Options](https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html)

## Related Topics

- [Clang/LLVM](./clang-llvm.md) — Alternative compiler with different strengths
- [Linker](./linker.md) — Linking object files into executables
- [Make](./make.md) — Build automation
- [CMake](./cmake.md) — Cross-platform build system generator
