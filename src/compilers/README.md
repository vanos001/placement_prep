# Compiler Overview

A **compiler** is a program that translates source code written in a high-level programming language into a lower-level representation—machine code, bytecode, or another high-level language. Compilers are fundamental infrastructure: every program you run on a CPU was translated by one.

## Why Compilers Matter

- **Performance**: Compilers exploit hardware features (pipelines, SIMD, caches) that humans cannot manage manually at scale.
- **Portability**: Write once in C, compile for x86, ARM, RISC-V, and WebAssembly.
- **Correctness**: Static analysis at compile time catches bugs before runtime.
- **Abstraction**: Programmers use high-level constructs; compilers lower them to machine instructions.

## The Compilation Pipeline

```mermaid
flowchart LR
    A[Source Code] --> B[Lexical Analysis<br/>Tokens]
    B --> C[Syntax Analysis<br/>AST]
    C --> D[Semantic Analysis<br/>Typed AST]
    D --> E[IR Generation<br/>Three-Address Code]
    E --> F[Optimization<br/>SSA Transforms]
    F --> G[Code Generation<br/>Assembly]
    G --> H[Assembly / Linking<br/>Executable]
```

| Phase | Input | Output | Key Data Structure |
|---|---|---|---|
| Lexical Analysis | Source text | Token stream | Finite automaton / DFA |
| Parsing | Token stream | Parse tree / AST | Context-free grammar |
| Semantic Analysis | AST | Decorated (typed) AST | Symbol table |
| IR Generation | Typed AST | Three-address code / SSA | Control flow graph |
| Optimization | IR | Optimized IR | Data-flow analysis frameworks |
| Code Generation | IR | Assembly / machine code | Register allocator, instruction selector |
| Linking | Object files | Executable / library | Symbol resolution tables |

## Interpreted vs. Compiled vs. JIT

| Criterion | Interpreted | Compiled (AOT) | JIT |
|---|---|---|---|
| **Translation timing** | At runtime, line by line | Before execution | During execution, after profiling |
| **Startup cost** | Low | Low (pre-compiled) | Higher (warm-up phase) |
| **Peak performance** | Slowest | High | Can exceed AOT via profile data |
| **Examples** | Python (CPython), Ruby | C (GCC), Rust (rustc) | Java HotSpot, V8, PyPy |
| **Portability** | High (source ships) | Requires per-target build | Bytecode is portable; native code at runtime |

In practice, most modern runtimes use a **hybrid** approach: Python compiles to `.pyc` bytecode, Java compiles to JVM bytecode then JIT-compiles hot paths to native code.

## Bytecode and Virtual Machines

Bytecode is an intermediate instruction set designed for a **virtual machine** (VM) rather than physical hardware. This provides:

- **Platform independence**: JVM bytecode runs on any OS with a JVM.
- **Security**: VMs can sandbox untrusted code (e.g., Java security manager).
- **Optimization surface**: The VM can profile and recompile bytecode at runtime.

Common examples: JVM bytecode, CPython `.pyc`, .NET CIL, WebAssembly (Wasm).

## Cross-Compilation

**Cross-compilation** is building an executable for a target architecture different from the host running the compiler. This is essential in embedded systems (e.g., compiling ARM firmware from an x86 workstation).

```bash
# Example: Cross-compile C for ARM from x86
arm-linux-gnueabihf-gcc -o hello_arm hello.c -static

# Verify with file(1)
file hello_arm  # ELF 32-bit LSB executable, ARM, EABI5
```

Challenges include differing **calling conventions**, **endianness**, **word size**, and **available system libraries**. Toolchains like `crosstool-NG` and build systems like CMake simplify this.

## Major Compiler Infrastructure

| Compiler | Language(s) | Backend | Notes |
|---|---|---|---|
| **GCC** | C, C++, Fortran, Go, D | Target-specific | GNU toolchain; [`gcc.gnu.org`](https://gcc.gnu.org/) |
| **Clang/LLVM** | C, C++, Rust (via rustc), Swift | LLVM IR | Modular, library-based; [`llvm.org`](https://llvm.org/) |
| **rustc** | Rust | LLVM IR | Borrows LLVM for codegen |
| **Go toolchain** | Go | Go internal | Self-hosting; fast compilation |
| **GraalVM** | Java, polyglot | Truffle/Graal | AOT compilation for JVM languages |

## References

- Aho, Lam, Sethi, Ullman — *Compilers: Principles, Techniques, and Tools* ("Dragon Book"), 2nd Ed.
- LLVM Language Reference Manual: <https://llvm.org/docs/LangRef.html>
- GCC Internals Manual: <https://gcc.gnu.org/onlinedocs/gccint/>

## Interview Questions

1. **What are the phases of a compiler?** Name each phase and what it produces.
2. **How does a JIT compiler differ from an AOT compiler?** Discuss warm-up time, peak performance, and profiling.
3. **Why does LLVM use an intermediate representation?** Portability, shared optimization passes, retargetability.
4. **What is cross-compilation? When would you need it?** Embedded systems, mobile, heterogeneous targets.
5. **Can a language be both compiled and interpreted?** Give an example.** Java: compiled to bytecode, interpreted/JIT-compiled by the JVM. Python: compiled to `.pyc`, interpreted by CPython.
