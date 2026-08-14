# Compiler Interview Questions

A curated collection of compiler-related interview questions organized by difficulty.

## Beginner

1. **What are the main phases of a compiler?**
   Lexical analysis, parsing, semantic analysis, IR generation, optimization, code generation, and linking. Each phase transforms the program representation toward machine code.

2. **What is the difference between a compiler and an interpreter?**
   A compiler translates the entire program to machine code before execution. An interpreter executes source code (or bytecode) directly, statement by statement. Most modern systems use a hybrid (e.g., Java compiles to bytecode, then JIT-compiles at runtime).

3. **What is a token?**
   A token is a pair (type, lexeme) representing the smallest meaningful unit of source code — e.g., `(INT_LITERAL, "42")`, `(PLUS, "+")`.

4. **What is an AST?**
   An Abstract Syntax Tree is a tree representation of the syntactic structure of source code, omitting punctuation and purely syntactic grouping. Each node represents a language construct (expression, statement, declaration).

5. **What is a symbol table?**
   A data structure that maps identifier names to their type, scope, memory location, and other attributes. Used during semantic analysis and code generation.

## Intermediate

6. **What is SSA and why do compilers use it?**
   Static Single Assignment form ensures each variable is assigned exactly once. This makes data-flow analyses straightforward (each use has exactly one reaching definition) and is required for most modern optimizations. LLVM IR and GCC GIMPLE both use SSA.

7. **Explain register allocation.**
   Mapping an unlimited set of virtual registers (from IR) to a finite set of physical CPU registers. The two main approaches are **graph coloring** (better code, slower) and **linear scan** (faster, used in JITs). Excess registers are "spilled" to the stack.

8. **What is the difference between static and dynamic linking?**
   Static linking embeds all library code into the executable at link time. Dynamic linking defers library resolution to runtime via shared objects (`.so` / `.dll`), enabling smaller executables and shared memory pages but requiring the dynamic loader at startup.

9. **What is a CFG and what is it used for?**
   A Control Flow Graph has basic blocks as nodes and jumps as edges. It models all possible execution paths and is the foundation for data-flow analysis and optimization passes.

10. **How does constant folding work?**
    The compiler evaluates constant expressions at compile time: `3 + 4` becomes `7`, `"hello" + "world"` becomes `"helloworld"`. This is typically done as an early optimization pass.

## Advanced

11. **How does LLVM's multi-stage design work?**
    LLVM separates the frontend (language-specific: Clang for C/C++, rustc for Rust), the optimizer (operates on LLVM IR), and the backend (target-specific code generation). Any frontend can target any backend through the shared IR. See: [llvm.org](https://llvm.org).

12. **What is deoptimization in a JIT compiler?**
    When the JIT makes a speculative optimization based on runtime profiles (e.g., "this variable is always an integer") and the assumption is violated at runtime, the compiled code must revert to the interpreter. This is called deoptimization or bailout. It requires preserving enough metadata to reconstruct the interpreter's state.

13. **Explain the PLT/GOT mechanism for dynamic linking.**
    The Procedure Linkage Table (PLT) contains stubs for calls to dynamic library functions. Each stub jumps to an address in the Global Offset Table (GOT). On first call, the GOT entry points back to the dynamic linker, which resolves the symbol, updates the GOT, and calls the real function. Subsequent calls go directly via the GOT — this is **lazy binding**.

14. **What is the difference between LALR(1) and LR(1) parsing?**
    Both are bottom-up shift-reduce parsers. LR(1) uses full lookahead sets (more powerful, larger tables). LALR(1) merges states with the same core, producing smaller tables at the cost of potentially introducing reduce-reduce conflicts that LR(1) would avoid. Bison generates LALR(1) parsers.

15. **How does profile-guided optimization (PGO) work in AOT compilers?**
    Compile with instrumentation (-fprofile-generate), run with representative workloads to collect branch frequencies and type information, then recompile using the profiles (-fprofile-use). This gives the AOT compiler some of the advantages of JIT (runtime data) without the runtime cost.

## Common Traps

- **"Compilers are only for compiled languages."** Python compiles to `.pyc` bytecode. JavaScript engines compile to machine code. Almost every language has a compilation step.
- **"Optimization always makes code faster."** Aggressive inlining can cause instruction cache pressure. Loop unrolling increases code size. Optimizations can regress performance on unrepresentative workloads.
- **"Interpreters don't have a compilation phase."** Most interpreters compile to bytecode first (CPython, Ruby MRI). The distinction is whether machine code is generated.
- **"Linking is trivial."** Modern linkers handle symbol versioning, LTO (link-time optimization), dead stripping, and address space layout randomization (ASLR).

## Quick Comparison Reference

| Concept | A | B | Key Difference |
|---|---|---|---|
 Interpreter vs Compiler | Executes source at runtime | Translates before execution | When translation happens |
 AOT vs JIT | Compile before execution | Compile during execution | Availability of runtime profiles |
 LL vs LR | Top-down, leftmost derivation | Bottom-up, rightmost derivation | Direction and power |
 Graph coloring vs Linear scan | Better allocation, NP-hard | Faster O(n log n), JIT-friendly | Quality vs speed trade-off |
 Static vs Dynamic linking | Libraries embedded in binary | Libraries resolved at runtime | Size vs flexibility |