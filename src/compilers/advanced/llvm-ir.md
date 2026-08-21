# LLVM IR

LLVM IR (Intermediate Representation) is the core data structure of the LLVM compiler framework, designed by Chris Lattner in 2002 as part of his M.S. thesis at the University of Illinois. It is a typed, register-based, RISC-like intermediate representation that every LLVM front-end (clang, rustc, swiftc, flang, etc.) emits and every LLVM back-end consumes. This page covers the IR's structure, the SSA form requirement, the type system, and the optimization passes that operate on the IR.

## The IR in One Slide

A simple C function:

```c
int add(int a, int b) {
    return a + b;
}
```

Compiles to (after `clang -O2 -emit-llvm -S`):

```llvm
define i32 @add(i32 noundef %a, i32 noundef %b) {
entry:
    %add = add nsw i32 %a, %b
    ret i32 %add
}
```

The IR is a textual form of an in-memory data structure. Key properties:
- **SSA (Static Single Assignment)**: every value is assigned exactly once.
- **Infinite virtual registers**: `%0`, `%1`, ..., `%add`, etc. — no fixed register file.
- **Explicit types**: `i32` for 32-bit integer, `ptr` (or `ptr<T>` in opaque-pointer mode) for pointers.
- **Basic blocks**: each function has named blocks (`entry`, `if.then`, `if.else`) connected by branches.
- **Instruction set**: ~200 instructions, most of them very simple (`add`, `mul`, `load`, `store`, `br`, `call`, `ret`, ...).

## SSA Form and Phi Nodes

The IR is in **Static Single Assignment** form: every register is defined exactly once. For code with control flow, this requires **phi nodes** to merge values from different predecessors:

```c
int max(int a, int b) {
    int result;
    if (a > b) result = a;
    else        result = b;
    return result;
}
```

In LLVM IR:

```llvm
define i32 @max(i32 %a, i32 %b) {
entry:
    %cmp = icmp sgt i32 %a, %b
    br i1 %cmp, label %if.then, label %if.else

if.then:
    br label %if.end

if.else:
    br label %if.end

if.end:
    %result = phi i32 [ %a, %if.then ], [ %b, %if.else ]
    ret i32 %result
}
```

The `phi` instruction picks a value based on which basic block was the predecessor. SSA and phi nodes are what make LLVM's dataflow analysis tractable: every use of a value can be traced to exactly one definition.

## The Type System

LLVM IR types are first-class:

- **Integer**: `i1` (bool), `i8` (byte), `i16`, `i32`, `i64`, `i128`. Arbitrary bit widths (`i23`) are legal but rarely used.
- **Float**: `half` (fp16), `float` (fp32), `double` (fp64), `fp128` (ieee quadruple), `x86_fp80` (8087 80-bit).
- **Vector**: `<4 x float>` (SIMD), `<16 x i8>` (SSE). Variable-length vectors (`<vscale x 4 x i32>`) for SVE/RVV.
- **Pointer**: `ptr` (opaque pointer mode, LLVM 15+) or `T*` (typed pointer mode, deprecated).
- **Array**: `[4 x i32]`.
- **Struct**: `{ i32, ptr, [8 x i8] }` (anonymous) or `%T = type { i32, ptr }` (named).
- **Function**: `i32 (i32, ptr)` — a function taking i32 and ptr, returning i32.

Types are used for code generation: the back-end knows the type of every value, so it can emit the correct instruction (`add` for `i32`, `fadd` for `float`, `vadd` for vectors).

## Memory Model

LLVM IR has a typed memory model. Pointers are addresses into a byte-addressable memory. The `load`/`store` instructions move data between registers and memory:

```llvm
%ptr = alloca i32          ; allocate a 4-byte stack slot
store i32 42, ptr %ptr     ; store 42 into the slot
%loaded = load i32, ptr %ptr  ; load the value back
```

The `alloca` instruction allocates on the stack frame; the slot is freed when the function returns. Heap allocation is by `call` to a function like `malloc` or `operator new` — the IR has no first-class heap primitive.

## The Optimization Pipeline

A typical LLVM optimization pipeline:

```text
Clang front-end → Clang AST → LLVM IR (unoptimized)
   ↓
-InstCombine -SimplifyCFG -GVN -MemCpyOpt -ADCE -SCCP -LoopUnroll -LICM -...
   ↓
LLVM IR (optimized)
   ↓
SelectionDAG / GlobalISel
   ↓
MachineInstr
   ↓
Register allocator (greedy / basic)
   ↓
Machine code (assembly or object file)
```

Each pass operates on the IR in a structured way:
- **InstCombine**: simplifies constant expressions (`add 1, 2` → `add 3`).
- **SimplifyCFG**: merges basic blocks, removes unreachable code.
- **GVN** (Global Value Numbering): eliminates redundant computations.
- **MemCpyOpt**: converts `memcpy` chains into direct stores.
- **ADCE** (Aggressive Dead Code Elimination): removes instructions with no side effects and unused results.
- **SCCP** (Sparse Conditional Constant Propagation): propagates constants through the CFG.
- **LoopUnroll**: unrolls loops to expose ILP.
- **LICM** (Loop Invariant Code Motion): hoists invariant computations out of loops.

The pass pipeline is configurable via the `-passes=` flag of `opt`, the LLVM IR optimizer. Production compilers (rustc, clang) use curated pass lists tuned for their target workloads.

## The Verifier

LLVM IR has a strict verifier (`llvm-as -verify` or `opt -verify`). It checks:

- SSA: every value defined exactly once.
- Dominance: every use of a value is dominated by its definition.
- Type safety: every instruction uses values of the correct type.
- Memory safety: every `load`/`store` accesses memory of the right size.
- Block structure: every block ends with a terminator (`br`, `ret`, `unreachable`, `switch`, etc.).

A pass that produces invalid IR is rejected before it can corrupt the pipeline. This is one of LLVM's main advantages over hand-rolled IR.

## The Back End

The back end converts LLVM IR to machine code via two main approaches:

1. **SelectionDAG** (the traditional approach): IR → SelectionDAG → MachineInstr → MCInst → assembly/object.
2. **GlobalISel** (the modern approach, since LLVM 5.0): IR → Generic MachineInstr → specific MachineInstr.

GlobalISel is the future: it provides a uniform interface across all back-ends and reduces the per-target work to write a back-end from ~50,000 lines (SelectionDAG) to ~5,000 lines (GlobalISel).

## Production Front-Ends

LLVM IR is emitted by:
- **Clang** (C, C++, Objective-C) — the canonical front-end.
- **rustc** — Rust uses LLVM IR as its back-end IR.
- **swiftc** — Swift uses LLVM IR via SIL (Swift Intermediate Language).
- **flang** — Fortran, using MLIR for high-level analysis and LLVM IR for codegen.
- **GHC (Haskell)** — GHC's LLVM back-end.
- **Cranelift** — alternative to LLVM, focusing on fast compilation for JITs (Wasmtime).
- **MLIR compilers** — eventually lower to LLVM IR via the `llvm` dialect.

## Use in Production JITs

LLVM's `orc` (On-Request-Compilation) JIT API is the basis for:

- **Julia**: compiles Julia code to LLVM IR at runtime.
- **HHVM (HipHop Virtual Machine)**: PHP/HHVM JITs via LLVM.
- **Azul Zing**: commercial JVM with LLVM-based JIT.
- **Kotlin/Native**: AOT compiler via LLVM.

The JIT API provides incremental compilation (compile a function at a time), lazy compilation (only compile functions that are called), and remote compilation (compile on a different process for sandboxing).

## Common Pitfalls

1. **Forgetting that LLVM IR is target-specific.** Two machines with the same OS but different ISAs (x86-64 vs ARM64) need different LLVM IR. The IR's type `i32` is the same, but `inttoptr` semantics differ; calling conventions differ; available instructions differ.

2. **Assuming IR is portable across LLVM versions.** LLVM IR evolves: the typed-pointer-to-opaque-pointer migration in LLVM 15 required updating all IR consumers. Production code that pins to a specific LLVM version is safer.

3. **Confusing `i32` with the C `int`.** On most platforms `sizeof(int) == 4`, so they coincide. But `i32` in LLVM IR is always 32 bits, while C's `int` is implementation-defined. Use `i32` and don't make assumptions about C types from the IR.

4. **Using `undef` and `poison` incorrectly.** `undef` is an arbitrary value; the compiler can choose any value. `poison` is a value that propagates if used. Code that assumes `undef` is zero will be miscompiled.

5. **Writing passes that don't preserve the verifier.** A pass that produces invalid IR is rejected by the PassManager. Always run `opt -verify-each=true` during development.

## References

- Chris Lattner, "[LLVM: An Infrastructure for Multi-Stage Optimization](https://llvm.org/pubs/2003-Chris-Lattner-MSThesis.pdf)" (UIUC M.S. thesis, 2002)
- [LLVM Language Reference Manual](https://llvm.org/docs/LangRef.html)
- [LLVM IR Tutorial](https://llvm.org/docs/tutorial/)
- [LLVM's Pass Infrastructure](https://llvm.org/docs/WritingAnLLVMPass.html)
- [The New Pass Manager (LLVM 13+)](https://llvm.org/docs/NewPassManager.html)
- [Chris Lattner's blog: LLVM IR design](http://nondot.org/sabre/)
- [Cranelift: A faster JIT alternative](https://github.com/bytecodealliance/cranelift)
