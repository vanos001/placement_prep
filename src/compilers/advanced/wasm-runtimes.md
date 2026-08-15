# WebAssembly Runtimes

WebAssembly (Wasm) is a **portable, sandboxed binary instruction format** designed as a compilation target for the web and beyond. It provides near-native execution speed with a compact binary format and a secure sandbox. This chapter covers Wasm internals, the WASI system interface, Wasm GC, the component model, and how language runtimes use Wasm.

## WebAssembly Internals

### Binary Format

Wasm binaries use a **compact binary encoding** with LEB128 varint encoding. A `.wasm` file is a sequence of sections:

```
Wasm Binary Structure:
┌────────────────────────────────────────────────────┐
│ Magic: \x00\x61\x73\x6D ("\0asm")                │
│ Version: 1 (LEB128)                               │
├────────────────────────────────────────────────────┤
│ Type Section    — function signatures              │
│ Import Section  — imported funcs/memories/tables   │
│ Function Section — type indices for local funcs    │
│ Table Section   — indirect function tables         │
│ Memory Section  — linear memory declarations       │
│ Global Section  — mutable/immutable globals        │
│ Export Section  — exported items                   │
│ Start Section   — start function                   │
│ Element Section — table initialization             │
│ Code Section    — function bodies (bytecode)        │
│ Data Section    — memory initialization            │
│ DataCount Section — data segment count (for GC)    │
└────────────────────────────────────────────────────┘
```

The binary format is designed for **fast validation and streaming compilation** — a browser can start compiling a Wasm module while still downloading it.

### Execution Model

Wasm is a **stack machine** with a structured control flow (blocks, loops, if/else with explicit end markers). The key design choice: Wasm has **no garbage collection** in the base spec — memory is a flat `ArrayBuffer` (linear memory). This keeps the language simple and the runtime minimal.

```wasm
;; Factorial in Wasm text format (WAT)
(module
  (func $fact (param $n i32) (result i32)
    (if (i32.le_s (local.get $n) (i32.const 1))
      (then (i32.const 1))
      (else
        (i32.mul
          (local.get $n)
          (call $fact (i32.sub (local.get $n) (i32.const 1)))))))
  (export "fact" (func $fact)))
```

### Stack vs Register

Wasm's binary encoding is a **stack machine**, but virtually all runtimes (V8, SpiderMonkey, Wasmtime) convert it to a **register-based IR** internally for optimization. The conversion is straightforward because Wasm's validation guarantees a well-typed stack.

### Security Sandbox

Wasm's security model:
- **Memory isolation**: Each instance has its own linear memory. No pointer to the host's memory.
- **No raw pointer access**: All memory accesses are bounds-checked against the declared memory size.
- **Capability-based**: Only exported functions are callable; imports are explicitly declared.
- **Control flow integrity**: No computed jumps — all control flow is via structured constructs.

> **Interview Angle**: "How does Wasm achieve 'near-native' performance?" Several factors: (1) compact binary format enables fast parsing/validation. (2) The instruction set is close to hardware (no dynamic typing, explicit types). (3) Runtimes compile Wasm to native code via JIT or AOT. (4) Linear memory enables efficient bounds-check elision. (5) No GC in the base spec means predictable pauses. Benchmarks show 10–20% slower than native C for compute-bound workloads.

## WASI (WebAssembly System Interface)

WASI provides a **standardized system interface** for Wasm modules, enabling Wasm to run outside the browser as a portable application format.

### Design Principles

1. **Capability-based security**: File descriptors are explicit capabilities. A module can only access files it was granted.
2. **POSIX-like API**: `fd_read`, `fd_write`, `path_open`, `proc_exit`, `clock_gettime`.
3. **Module composition**: WASI imports are a standard set; any WASI-compliant runtime can run any WASI module.

```rust
// Rust + WASI example
use std::fs::File;
use std::io::{self, Read};

fn main() -> io::Result<()> {
    let mut f = File::open("/data/input.txt")?;  // WASI: path_open capability
    let mut contents = String::new();
    f.read_to_string(&mut contents)?;             // WASI: fd_read
    println!("{}", contents);                      // WASI: fd_write
    Ok(())
}

// Compile:  cargo build --target wasm32-wasi
// Run:      wasmtime target/wasm32-wasi/debug/app.wasm
```

### WASI Preview 2

The original WASI (preview 1) used POSIX-style file descriptors. **WASI preview 2** (built on the Component Model) uses a **component-level API** with typed, composable interfaces. It's a major redesign that trades POSIX familiarity for composability.

## Wasm GC

Wasm GC (proposed, shipping in V8/Firefox) adds **garbage-collected object types** natively to Wasm:

- `struct` types (heap-allocated, GC-managed)
- `array` types (GC-managed arrays)
- `i31ref` (small integer optimization — 31-bit integers stored directly in references)
- `externref` / `anyref` (references to host objects)

```wasm
;; Wasm GC: define a struct type
(type $Cons (struct
  (field $car i32)
  (field $cdr (ref null $Cons))))  ;; recursive type!

(func $make-list (param $n i32) (result (ref null $Cons))
  (if (i32.le_s (local.get $n) (i32.const 0))
    (then (ref.null $Cons))
    (else
      (struct.new $Cons
        (local.get $n)
        (call $make-list (i32.sub (local.get $n) (i32.const 1)))))))
```

### Why Wasm GC Matters

Without Wasm GC, languages like Java, Kotlin, and Dart compiled to Wasm must **bundle their own GC** in the Wasm module (e.g., GraalVM's Truffle, Kotlin/Wasm). With native Wasm GC, these languages can use the **host's GC** (the browser's or runtime's), reducing binary size and improving interop.

| Approach | Binary Size | GC Pauses | Interop | Complexity |
|----------|------------|-----------|---------|------------|
| Bundle own GC | Large (1-10 MB) | Depends on impl | Poor | High |
| Wasm GC (native) | Small | Depends on host | Good | Low |

## Component Model

The Wasm **Component Model** provides a **standard way to compose Wasm modules** with typed interfaces, independent of language or source.

### Core Idea

A **component** is a Wasm module with:
- **Typed imports and exports** using the **Interface Definition Language (WIT)**.
- **Canonical ABI**: a standardized calling convention for passing complex types (strings, records, variants) across language boundaries.
- **Composition**: components can import other components' exports.

```wit
;; example.wit — Interface Definition
interface counter {
  /// Create a new counter with the given initial value.
  create: func(initial: u32) -> handle;
  /// Increment the counter and return the new value.
  increment: func(counter: handle) -> u32;
}
```

### Component vs. Module

| Aspect | Core Module | Component |
|--------|------------|-----------|
| **Interface** | Raw i32/i64/f32/f64 | Strings, records, variants, enums |
| **Composition** | Manual (imports/exports) | Typed, verified composition |
| **ABI** | Stack-based, flat | Canonical ABI (lifted/lowered) |
| **Language interop** | Manual marshaling | Automatic via WIT |

The Component Model is the foundation of **server-side Wasm** — deploying microservices as Wasm components that can call each other regardless of whether they were written in Rust, Go, Python, or Java.

## Language Runtimes on Wasm

### Wasmtime (Bytecode Alliance)

**Wasmtime** is a standalone Wasm runtime written in Rust. Key features:
- **Cranelift** code generator (Rust-based, JIT and AOT).
- **WASI** support (preview 1 and 2).
- **Component Model** support.
- Used in: Fastly edge computing, Fermyon Spin, AWS Lambda WebAssembly.

### Other Runtimes

| Runtime | Language | JIT/AOT | WASI | GC | Use Case |
|---------|----------|---------|------|-----|----------|
| **Wasmtime** | Rust | JIT + AOT (Cranelift) | Yes | Wasm GC | Edge, serverless |
| **Wasmer** | Rust | JIT + AOT | Yes | Wasm GC | General purpose |
| **Wamr** | C | JIT + AOT (Fast JIT) | Yes | Limited | Embedded, IoT |
| **JSC (WebKit)** | C++ | JIT (OMG/WTF) | Yes | Yes | Safari, Bun |
| **V8** | C++ | JIT (Liftoff + TurboFan) | Yes | Yes | Chrome, Deno, Node.js |
| **Wasm3** | C | Interpreter only | Yes | No | Minimal footprint |
| **GraalWasm** | Java | JIT (Truffle) | No | Via JVM | Polyglot on JVM |

### Wasm for Language Runtimes

Several language runtimes compile to Wasm as a **portable deployment target**:

- **Python (CPython → Wasm)**: Compiled via Emscripten or wasm32-wasi. Pyodide runs Python in the browser. Performance is ~2–5× slower than native due to GC and system call overhead.
- **Ruby (ruby.wasm)**: Artichoke and WASI-based Ruby runtimes enable Ruby in the browser.
- **Java (TeaVM)**: Compiles Java bytecode to Wasm without requiring a JVM.
- **Go**: Supports `GOOS=wasip1 GOARCH=wasm` natively since Go 1.21.
- **Kotlin/Wasm**: JetBrains' Kotlin compiler targets Wasm directly (not via JVM), using Wasm GC for Kotlin's object model.
- **.NET (NativeAOT Wasm)**: .NET 8+ supports Wasm AOT compilation, enabling Blazor WebAssembly and server-side Wasm .NET.

### Performance Characteristics

```
Wasm Performance vs. Native (approximate):

Compute-bound (pure arithmetic):
  Native C:       1.0× (baseline)
  Wasm (AOT):     1.1–1.3×
  Wasm (JIT):     1.2–1.5×

System-call heavy (I/O):
  Native C:       1.0×
  Wasm + WASI:    1.5–3.0×  (context switch overhead)

Language runtime on Wasm:
  Python (native):    1.0×
  Python (Pyodide):   2–5× slower
  Go (native):        1.0×
  Go (WASI):          1.1–1.5×
```

> **Interview Angle**: "Why would you choose Wasm over containers (Docker) for deployment?" Wasm starts in <5ms (vs. seconds for containers), has a 10–100× smaller footprint, provides strong sandboxing by default, and enables polyglot microservices. Tradeoff: Wasm is single-threaded (threads are a proposal, not universally available), lacks native networking (goes through WASI), and has limited library ecosystem compared to Linux containers.

## References

- WebAssembly Specification: <https://webassembly.github.io/spec/>
- WASI documentation: <https://wasi.dev/>
- Bytecode Alliance: <https://bytecodealliance.org/>
- Component Model explainer: <https://github.com/WebAssembly/component-model>
- A. Haas et al., *Bringing the Web up to Speed with WebAssembly* (PLDI 2017)
