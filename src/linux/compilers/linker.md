# Linkers — Connecting the Pieces

## Introduction

A linker takes one or more object files produced by the compiler and combines them
into a single executable, shared library, or relocatable object. The linker resolves
symbol references between translation units, allocates final addresses, and produces
the output binary in a format the operating system can load and execute.

Understanding linkers is essential for debugging link errors, optimizing binary size,
building shared libraries, and working with embedded systems. The linker is the last
step in the compilation pipeline, and its behavior directly affects how your program
loads and runs.

## The Linking Process

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ file1.o  │  │ file2.o  │  │ libfoo.a │
│ (object) │  │ (object) │  │ (archive)│
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │
     └──────────────┼──────────────┘
                    │
             ┌──────▼──────┐
             │   Linker     │
             │   (ld/lld)   │
             │              │
             │ 1. Symbol    │
             │    resolution│
             │ 2. Section   │
             │    merging   │
             │ 3. Relocation│
             │ 4. Output    │
             └──────┬──────┘
                    │
             ┌──────▼──────┐
             │  Executable  │
             │  (ELF binary)│
             └──────────────┘
```

### Linking Steps

1. **Symbol Resolution**: Match each symbol reference with a definition
2. **Section Merging**: Combine similar sections from all input files
3. **Relocation**: Patch code/data references with final addresses
4. **Output Generation**: Write the final ELF binary

## The GNU Linker (ld)

### Basic Usage

```bash
# Link object files
ld -o myprogram file1.o file2.o -lc

# Link with GCC driver (handles libc, crt, etc.)
gcc -o myprogram file1.o file2.o

# Link with libraries
gcc -o myprogram file1.o -L/path/to/libs -lfoo -lbar

# Link with specific dynamic linker
gcc -Wl,--dynamic-linker=/lib64/ld-linux-x86-64.so.2 -o myprogram file1.o
```

### Common Linker Options

```bash
# Specify output format
ld -m elf_x86_64 -o myprogram file1.o

# Set entry point
ld -e _start -o myprogram file1.o

# Add library search path
ld -L/usr/local/lib -o myprogram file1.o -lc

# Link shared library
ld -shared -o libfoo.so file1.o file2.o

# Create relocatable object
ld -r -o combined.o file1.o file2.o

# Define symbols at link time
ld --defsym=myvar=0x1234 -o myprogram file1.o

# Generate map file
ld -Map=output.map -o myprogram file1.o

# Set maximum page size
ld -z max-page-size=4096 -o myprogram file1.o

# Enable/disable warnings
ld --warn-common -o myprogram file1.o
ld --no-warn-mismatch -o myprogram file1.o
```

### Linker Warnings

```bash
# Warn about common symbols (global variables without extern)
gcc -Wl,--warn-common -o myprogram file1.o file2.o

# Warn about unresolved symbols
gcc -Wl,--no-undefined -o myprogram file1.o

# Warn about shared library dependencies
gcc -Wl,--no-as-needed -o myprogram file1.o -lfoo

# Error on undefined symbols
gcc -Wl,--fatal-warnings -o myprogram file1.o
```

## Symbol Resolution

### Symbol Types

```
┌──────────────────────────────────────────────────────┐
│                    Symbol Types                        │
│                                                       │
│  ┌────────────────┐  ┌────────────────┐              │
│  │ Defined        │  │ Undefined      │              │
│  │ (provides def) │  │ (needs def)    │              │
│  └────────────────┘  └────────────────┘              │
│                                                       │
│  ┌────────────────┐  ┌────────────────┐              │
│  │ Strong         │  │ Weak           │              │
│  │ (function def) │  │ (default impl) │              │
│  └────────────────┘  └────────────────┘              │
│                                                       │
│  ┌────────────────┐  ┌────────────────┐              │
│  │ Common         │  │ Tentative      │              │
│  │ (uninit global)│  │ (uninit global)│              │
│  └────────────────┘  └────────────────┘              │
└──────────────────────────────────────────────────────┘
```

### Strong vs Weak Symbols

```c
// file1.c — Strong definition
int myvar = 42;
void myfunc(void) { /* ... */ }

// file2.c — Weak definition (can be overridden)
__attribute__((weak)) int myvar = 0;
__attribute__((weak)) void myfunc(void) { /* default impl */ }

// file3.c — Reference
extern int myvar;
extern void myfunc(void);
```

Linker rules:
1. **Multiple strong definitions** → error (multiple definition)
2. **One strong + multiple weak** → strong wins
3. **Only weak definitions** → one weak wins (largest size, or first encountered)

### Common Symbols

```c
// In a header file (without extern)
int global_var;  // Tentative definition → common symbol

// Better practice
extern int global_var;  // In header
int global_var = 0;     // In exactly one .c file
```

```bash
# Show common symbols
nm --defined-only file1.o | grep ' C '

# Warn about common symbols
gcc -fno-common -o myprogram file1.c file2.c
# (default since GCC 10)
```

## ELF Object File Format

```
┌──────────────────────────────────────────────┐
│              ELF Object File                  │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │ ELF Header                              │ │
│  │ - Magic: 7f 45 4c 46 (.ELF)            │ │
│  │ - Class: ELF64                          │ │
│  │ - Type: REL (relocatable) / EXEC        │ │
│  │ - Machine: EM_X86_64                    │ │
│  │ - Entry point address                   │ │
│  └─────────────────────────────────────────┘ │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │ Section Header Table                    │ │
│  │ - .text    (code)                       │ │
│  │ - .data    (initialized data)           │ │
│  │ - .bss     (uninitialized data)         │ │
│  │ - .rodata  (read-only data)             │ │
│  │ - .symtab  (symbol table)               │ │
│  │ - .strtab  (string table)               │ │
│  │ - .rel.text (relocation entries)        │ │
│  │ - .debug_* (debug information)          │ │
│  └─────────────────────────────────────────┘ │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │ Program Header Table (executables only) │ │
│  │ - LOAD segments                         │ │
│  │ - DYNAMIC segment                       │ │
│  │ - INTERP (dynamic linker path)          │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

### Examining ELF Files

```bash
# Read ELF header
readelf -h myprogram

# Show section headers
readelf -S myprogram

# Show program headers (segments)
readelf -l myprogram

# Show symbol table
readelf -s myprogram

# Show dynamic section
readelf -d myprogram

# Show relocation entries
readelf -r myprogram.o

# Using objdump
objdump -d myprogram          # Disassemble
objdump -t myprogram          # Symbol table
objdump -h myprogram          # Section headers
objdump -s myprogram          # Full section contents
objdump -R myprogram          # Dynamic relocations
```

## Shared Libraries and PIC

### Position-Independent Code (PIC)

Shared libraries must be position-independent because they can be loaded at
any address. PIC uses relative addressing and indirection through the GOT.

```bash
# Compile with PIC (required for shared libraries)
gcc -fPIC -c file1.c -o file1.o
gcc -fPIC -c file2.c -o file2.o

# Create shared library
gcc -shared -o libfoo.so file1.o file2.o

# Or with soname
gcc -shared -Wl,-soname,libfoo.so.1 -o libfoo.so.1.0.0 file1.o file2.o
```

### PLT and GOT

```
┌───────────────────────────────────────────────────────┐
│                    PLT/GOT Mechanism                    │
│                                                        │
│  Program calls printf()                                │
│       │                                                │
│       ▼                                                │
│  ┌──────────────────┐                                 │
│  │ PLT Entry for    │                                 │
│  │ printf           │                                 │
│  │  jmp *GOT[3]     │──────┐                           │
│  │  push index      │      │                           │
│  │  jmp PLT[0]      │      │                           │
│  └──────────────────┘      │                           │
│                             │                           │
│       ┌─────────────────────┘                           │
│       │                                                 │
│       ▼                                                 │
│  ┌──────────────────┐     First call:                  │
│  │ GOT Entry for    │     1. Points back to PLT        │
│  │ printf           │     2. PLT[0] calls ld.so        │
│  │ (initially →PLT) │     3. ld.so resolves printf     │
│  └──────────────────┘     4. Updates GOT entry          │
│       │                                                 │
│       │  Subsequent calls:                              │
│       └──► Direct jump to printf in libc               │
│                                                        │
└───────────────────────────────────────────────────────┘
```

### Lazy Binding

By default, shared library functions are resolved lazily (on first call):

```bash
# Show PLT entries
objdump -d -j .plt myprogram

# Show GOT entries
objdump -s -j .got myprogram
objdump -s -j .got.plt myprogram

# Disable lazy binding (resolve all at load time)
gcc -Wl,-z,now -o myprogram file1.o -lfoo

# Or with environment variable
LD_BIND_NOW=1 ./myprogram

# Preload a library (override functions)
LD_PRELOAD=/path/to/mylib.so ./myprogram
```

### Library Versioning

```bash
# Create versioned shared library
gcc -shared -Wl,-soname,libfoo.so.1 -o libfoo.so.1.0.0 file1.o
ln -sf libfoo.so.1.0.0 libfoo.so.1
ln -sf libfoo.so.1 libfoo.so

# Symbol versioning
# libfoo.map:
LIBFOO_1.0 {
    global:
        foo_init;
        foo_process;
    local:
        *;
};
LIBFOO_2.0 {
    global:
        foo_new_api;
} LIBFOO_1.0;

gcc -shared -Wl,--version-script=libfoo.map -o libfoo.so file1.o
```

## Linker Scripts

Linker scripts control how the linker organizes sections in the output binary.
They're essential for embedded systems and kernel development.

### Basic Linker Script

```ld
/* linker.ld — Simple linker script */
ENTRY(_start)

SECTIONS
{
    . = 0x400000;           /* Load address */

    .text : {
        *(.text.startup)    /* Startup code first */
        *(.text)            /* Then all other code */
    }

    .rodata : {
        *(.rodata)
    }

    . = ALIGN(0x1000);      /* Page-align data */

    .data : {
        *(.data)
    }

    .bss : {
        *(COMMON)
        *(.bss)
    }

    /DISCARD/ : {
        *(.comment)
        *(.note.*)
    }
}
```

### Advanced Linker Script Features

```ld
/* Embedded system linker script */
MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 512K
    RAM (rwx)   : ORIGIN = 0x20000000, LENGTH = 128K
}

SECTIONS
{
    .text : {
        _text_start = .;
        *(.isr_vector)      /* Interrupt vector table */
        *(.text*)
        *(.rodata*)
        _text_end = .;
    } > FLASH

    .data : {
        _data_start = .;
        *(.data*)
        _data_end = .;
    } > RAM AT > FLASH      /* Load from FLASH, run from RAM */

    .bss : {
        _bss_start = .;
        *(.bss*)
        *(COMMON)
        _bss_end = .;
    } > RAM

    /* Symbols for startup code */
    _sidata = LOADADDR(.data);
}
```

### Using Linker Scripts

```bash
# Use a linker script
gcc -T linker.ld -o myprogram file1.o

# Or with ld directly
ld -T linker.ld -o myprogram file1.o

# Define symbols at link time
gcc -Wl,--defsym=STACK_SIZE=0x1000 -T linker.ld -o myprogram file1.o
```

## LLD — The LLVM Linker

LLD is significantly faster than GNU ld, often 2-10x:

```bash
# Use LLD
clang -fuse-ld=lld -o myprogram file1.o file2.o

# Direct invocation
ld.lld -o myprogram file1.o file2.o

# Benchmark comparison
time ld -o /dev/null file1.o file2.o ...     # GNU ld
time ld.lld -o /dev/null file1.o file2.o ... # LLD
```

### LLD Features

- **Speed**: 2-10x faster than GNU ld
- **Link-time optimization**: Native LTO support
- **Better diagnostics**: Clear error messages
- **Reproducible builds**: Deterministic output
- **Compatible**: Drop-in replacement for GNU ld
- **Cross-linking**: Excellent cross-platform support

## Link-Time Errors and Debugging

### Common Link Errors

```
# Undefined reference
undefined reference to 'myfunction'
# Fix: Provide the definition, or link with -lfoo

# Multiple definition
multiple definition of 'myvar'
# Fix: Use extern in headers, define in one .c file; or use -fno-common (pre-GCC 10)

# Cannot find library
cannot find -lfoo
# Fix: Add -L/path/to/libs or install the library

# Incompatible object
file1.o: error adding symbols: file in wrong format
# Fix: Use matching compiler/architecture

# DSO missing from command line
/usr/bin/ld: file1.o: undefined reference to symbol 'dlopen@@GLIBC_2.17'
# Fix: Add -ldl
```

### Debugging Link Issues

```bash
# Verbose linking
gcc -v -o myprogram file1.o file2.o

# Show all link inputs
gcc -Wl,--verbose -o myprogram file1.o 2>&1 | less

# Map file
gcc -Wl,-Map=output.map -o myprogram file1.o

# Show symbol resolution
gcc -Wl,--print-map -o myprogram file1.o

# Show why a library is needed
gcc -Wl,--no-as-needed -Wl,--push-state -Wl,--as-needed -lfoo -Wl,--pop-state

# Trace library search
gcc -Wl,-t -o myprogram file1.o -lfoo 2>&1 | grep libfoo
```

### Symbol Visibility

```c
// Default visibility (exported)
__attribute__((visibility("default"))) void public_func(void);

// Hidden visibility (not exported from shared library)
__attribute__((visibility("hidden"))) void internal_func(void);

// Compile with -fvisibility=hidden to hide all by default
// Then explicitly export what you need
```

```bash
# Hide all symbols by default
gcc -fvisibility=hidden -shared -o libfoo.so file1.o

# Export specific symbols
# Use __attribute__((visibility("default"))) or a version script
```

## Dynamic Linker (ld-linux)

The dynamic linker (`ld-linux-x86-64.so.2` on x86-64) loads shared libraries
at runtime.

```bash
# Show shared library dependencies
ldd ./myprogram

# Trace dynamic linking
LD_DEBUG=all ./myprogram 2>&1 | head -100

# Show library search
LD_DEBUG=libs ./myprogram 2>&1

# Show symbol binding
LD_DEBUG=symbols ./myprogram 2>&1

# Show relocations
LD_DEBUG=reloc ./myprogram 2>&1

# Override library path
LD_LIBRARY_PATH=/custom/libs ./myprogram

# Preload a library
LD_PRELOAD=/path/to/intercept.so ./myprogram

# Search path (system-wide)
# /etc/ld.so.conf
# /etc/ld.so.conf.d/*.conf
# Then run: ldconfig
```

## Best Practices

1. **Use `-Wl,--no-undefined`** — catch missing symbols at link time
2. **Use `-Wl,--as-needed`** — only link libraries that are actually used
3. **Use `-fPIC` for shared libraries** — required for position-independent code
4. **Use `-Wl,-z,now`** — disable lazy binding for security (full RELRO)
5. **Use `-Wl,-z,relro`** — make GOT read-only after relocation
6. **Use symbol versioning** — maintain ABI compatibility
7. **Use visibility attributes** — reduce shared library size and improve load time
8. **Use LLD for faster builds** — especially for large projects
9. **Use linker scripts for embedded** — control memory layout precisely
10. **Use `ldd` and `readelf`** — inspect binaries for debugging

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [LD Manual](https://sourceware.org/binutils/docs/ld/)
- [LLD Documentation](https://lld.llvm.org/)
- [ELF Specification](https://refspecs.linuxfoundation.org/elf/elf.pdf)
- [System V ABI](https://www.sco.com/developers/devspecs/gabi41.pdf)
- [Linkers and Loaders (book)](https://www.iecc.com/linker/)

## Related Topics

- [GCC](./gcc.md) — Compiler that drives the linker
- [Clang/LLVM](./clang-llvm.md) — LLD linker and LLVM toolchain
- [Make](./make.md) — Build automation
- [CMake](./cmake.md) — Build system generator
