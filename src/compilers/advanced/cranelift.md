# Cranelift

Cranelift is a fast code generator written in Rust, developed by the Bytecode Alliance since 2018 as the JIT back-end for Wasmtime, the WebAssembly runtime. It is designed to compile one function at a time, with a compilation budget of microseconds-to-milliseconds per function, rather than LLVM's typical milliseconds-to-seconds per function. This page covers the IR design (CLIF), the egraph-based optimization layer, the register allocator, and why Cranelift exists alongside LLVM rather than replacing it.

## Why Cranelift Exists

LLVM was designed for ahead-of-time compilation, where compilation time is amortized across the program's lifetime. In a JIT, compilation time is on the critical path: every millisecond spent compiling is a millisecond of startup latency. LLVM's compile times are 10-100 ms per function for typical code; Cranelift's are 0.1-1 ms.

The reason for the difference is structural:

- LLVM's IR is rich (~200 instructions, full type system, optimization pipeline of ~50 passes) — each pass touches every instruction in the function.
- Cranelift's IR is minimal (~80 instructions, smaller type system, optimization pipeline of ~5 passes) — focused on the bare essentials.
- LLVM's back-end (SelectionDAG, GlobalISel) is sophisticated but heavy; Cranelift's back-end (`isle`, a pattern-matching DSL) is small and targeted.

Cranelift targets x86_64, ARM64, RISC-V (64-bit), s390x (64-bit), and aarch32. It does not target obscure ISAs and is not designed to compete with LLVM on optimization quality — only on speed.

## The CLIF IR

Cranelift IR (CLIF) is a function-level SSA representation. A simple function:

```text
function %add(i32, i32) -> i32 {
    ss0 = arg i32
    ss1 = arg i32
    ss2 = iadd ss0, ss1
    return ss2
}
```

Key properties:

- **Function-level**: each function is one CLIF unit. No cross-function inlining is done by Cranelift — callers must do their own inlining first.
- **SSA**: every value has exactly one definition.
- **Stack slots**: instead of an infinite virtual register file, CLIF uses explicit "stack slots" (`ss0`, `ss1`, ...) for values that don't fit in registers. This makes register allocation simpler.
- **Blocks and branches**: like LLVM, but the block parameters are explicit values rather than phi nodes. CLIF uses "block parameters" instead of phi nodes, which the literature calls "argument-based SSA".

```text
block1(v0: i32):
    ...
    brif v0, block2(v0), block3(v0)

block2(v1: i32):    ← v1 receives the value from block1's v0
    ...

block3(v2: i32):    ← v2 receives the value from block1's v0
    ...
```

This is more compact than phi nodes and matches the way modern SSA research has gone (MLIR also uses block arguments).

## The Optimization Pipeline

Cranelift has a small set of passes:

1. **EGraph-based DCE and constant folding** (since 0.85). An egraph (e-graph) is a data structure that represents equivalent expressions as a DAG, allowing fast rewriting. Cranelift's egraph pass replaces the older hand-written `egraph-iso` and `egraph` passes.
2. **Instruction Simplification**: fold `iadd x, 0` to `x`, `band x, -1` to `x`, etc.
3. **Constant Hoisting**: move loop-invariant constants out of loops.
4. **Register Allocation**: the only pass that touches every instruction.

The pass pipeline is intentionally small. Each pass is fast (linear in the function size, with constant factors), and the egraph approach is much faster than LLVM's pattern-matching passes because it processes the whole function at once rather than walking the IR repeatedly.

## ISLE: The Pattern-Matching Back-End

Cranelift's back-end is written in `ISLE` (Instruction Selection Language for Cranelift), a domain-specific language for writing pattern-matching rules that lower CLIF instructions to machine instructions. A rule like:

```lisp
(rule (machine_instr (iadd ?a ?b) (x86_add ?a ?b))
      (when (and (is_i32 ?a) (is_i32 ?b))))
```

Says: "when lowering an `iadd` of two i32 values, emit an `x86_add` machine instruction". The ISLE compiler generates Rust code from these rules, and the generated code is highly optimized for fast pattern matching.

ISLE was originally developed for Cranelift but has been adopted by other JIT projects. The original paper "[ISLE: A Declarative Pattern-Matching IR for Compilers](https://github.com/bytecodealliance/wasmtime/blob/main/cranelift/isle)" describes the design.

## Register Allocation

Cranelift uses a custom register allocator that's faster but produces slightly worse code than LLVM's:

- **Linear scan with extensions**: O(n) in function size, fast but not optimal.
- LLVM's greedy allocator is O(n log n) and produces better code at the cost of slower compilation.

For Cranelift's target use case (Wasm JIT, where the input code is usually small functions), the linear scan's quality is "good enough" and the speed is the deciding factor.

## Comparison to LLVM

| Aspect | Cranelift | LLVM |
|--------|-----------|------|
| Compilation speed | 0.1-1 ms per function | 10-100 ms per function |
| Optimization quality | Modest (-10% perf vs -O3) | High (-O3) |
| IR richness | ~80 instructions | ~200 instructions |
| Target ISAs | x86_64, ARM64, RISC-V64, s390x | All major ISAs (~25) |
| Code size | ~10 MB binary | ~100+ MB binary |
| Embeddability | Pure Rust, no LLVM deps | Requires LLVM toolchain |
| Use case | JIT (Wasm, fast) | AOT, JIT (high quality) |

Production Wasm runtimes pick Cranelift for fast startup, LLVM for steady-state throughput. Wasmtime supports both, with Cranelift as the default and LLVM as an opt-in via `--codegen=llvm`.

## Production Users

- **Wasmtime**: the primary user, defaults to Cranelift.
- **WAMR (WebAssembly Micro Runtime)**: optional back-end for fast compilation.
- **Firefox SpiderMonkey**: experimental integration for some JIT tiers (with Cranelift as an alternative to its own back-end).
- **Fizzy, Wasm3**: smaller Wasm interpreters that use Cranelift for fast compilation when needed.
- **Rust's `wasmtime` crate**: directly uses Cranelift under the hood for embedded Wasm execution.

The Bytecode Alliance is the umbrella organization that develops Cranelift, Wasmtime, and other WebAssembly tooling.

## When to Use Cranelift vs. LLVM

**Use Cranelift when**:
- You need sub-millisecond function compilation (JIT).
- You can tolerate ~10% slower runtime vs. LLVM -O3.
- You don't have a target ISA that Cranelift supports (it has fewer back-ends).
- You're already in Rust and want a pure-Rust back-end.

**Use LLVM when**:
- You need -O2 or -O3 quality.
- Your target ISA is unusual (e.g., MIPS, SPARC, ancient x86).
- You need cross-language LTO.
- You can tolerate 10-100 ms per function compilation.

For Wasm runtime scenarios specifically, the conventional pattern is:
- Tier 1: Interpreter (no compilation, ~10 ns/instruction).
- Tier 2: Cranelift (fast compilation, ~1 ns/instruction).
- Tier 3: LLVM (slow compilation, ~0.5 ns/instruction, with PGO).

SpiderMonkey and V8 use a similar tiered approach but with their own JITs instead of Cranelift/LLVM.

## Common Pitfalls

1. **Assuming Cranelift is a drop-in LLVM replacement.** It is not. Cranelift does not do -O3-style optimization, does not support all LLVM targets, and does not have LLVM's mature ecosystem. Production users should benchmark both and pick per use case.

2. **Expecting Cranelift's compilation speed without measuring.** A common mistake is to assume the 0.1-1 ms/function number is universal. Very large functions (thousands of instructions) can take 5-10 ms even in Cranelift.

3. **Forgetting that CLIF has no cross-function inlining.** Callers (e.g., Wasmtime) must do their own inlining of Wasm function calls before passing the IR to Cranelift. Cranelift's compile-time budget is per-function, so the front-end is responsible for keeping functions small.

4. **Mixing CLIF and LLVM IR.** They are different IRs and cannot be interconverted automatically. Tools that emit CLIF for Cranelift and LLVM IR for LLVM have two separate code paths.

5. **Ignoring the ISLE rewrite rules' importance.** Cranelift's quality on each ISA is determined by the ISLE rules for that ISA. A new ISA support is mostly about writing the ISLE rules; the framework is largely constant.

## References

- [Cranelift documentation](https://github.com/bytecodealliance/wasmtime/blob/main/cranelift/docs)
- [Cranelift: A Fast Code Generator for WebAssembly (whitepaper)](https://github.com/bytecodealliance/cranelift)
- [ISLE: Pattern-matching DSL paper](https://docs.rs/cranelift-isle/latest/cranelift_isle/)
- [Wasmtime: WebAssembly runtime](https://wasmtime.dev/)
- [Bytecode Alliance](https://bytecodealliance.org/)
- [Cranelift's e-graph optimization](https://github.com/bytecodealliance/wasmtime/blob/main/cranelift/src/egraph.rs)
