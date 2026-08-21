# Register Allocation

Register allocation is the compiler phase that decides which program values live in CPU registers (fast, scarce) and which live in memory (slow, abundant). It is the most studied problem in compiler back-ends, with algorithms dating from 1970 (Belady's MIN), refined in the 1980s (Chaitin's graph-coloring), and modernized in the 2000s (linear-scan and SSA-form algorithms). This page covers the liveness analysis foundation, the graph-coloring approach, the linear-scan alternative, and the production approach (LLVM's `GreedyRegisterAllocator`).

## The Problem

A CPU has a fixed number of registers (e.g., x86-64 has 16 GPRs; ARM64 has 31). A program may have many more values in flight at any time. The compiler must decide which values get the fast registers and which spill to memory.

The decision is constrained by:
- **Liveness**: a value is "live" from its definition to its last use. Two simultaneously-live values must use different registers (otherwise they'd overwrite each other).
- **Spill cost**: a value spilled to memory costs ~100 ns per access; a value in a register costs ~0.3 ns. Spilling hot values is expensive.
- **Calling conventions**: certain registers are reserved for arguments, return values, the stack pointer, etc.

A "good" register allocation minimizes the total spill cost while respecting the liveness constraints.

## Liveness Analysis

Liveness analysis computes, for each program point, which values are "live" (will be used in the future). The data-flow equations:

```text
live_in[BB]  = use[BB] ∪ (live_out[BB] - def[BB])
live_out[BB] = ∪ live_in[successors]

where:
  use[BB]  = values read before being defined in BB
  def[BB]  = values defined in BB
  live_in  = values live at BB entry
  live_out = values live at BB exit
```

Solved by backward iteration over the control-flow graph until fixed point. For a function with N basic blocks, the analysis converges in O(N) iterations in practice.

## Graph Coloring (Chaitin-Briggs)

The classic algorithm (Chaitin, 1981; Briggs, 1992):

1. Build the **interference graph**: nodes are values (live ranges), edges between values that are simultaneously live.
2. Find a **k-coloring** of the graph (where k = number of available registers). Two adjacent nodes (interfering values) must have different colors (registers).
3. If the graph isn't k-colorable, **spill** some values to memory and retry.

The k-coloring problem is NP-hard in general, but the heuristic approach (simplify, select, spill) is fast in practice:

```text
Algorithm:
1. Pick a node with degree < k. Push it on a stack.
2. Remove it from the graph.
3. Repeat until no node has degree < k.
4. If the graph is empty, we can color: pop nodes from the stack,
   assign colors avoiding conflicts with already-colored neighbors.
5. If the graph has nodes with degree ≥ k, pick one to spill (heuristic: 
   highest spill cost / degree ratio). Mark it as "spilled", remove from graph.
6. Repeat step 1.
```

The "spill" decision is a heuristic: spill the value whose memory cost is lowest relative to its interference count. Chaitin's original used `(uses + defs) / degree`; modern allocators use more sophisticated heuristics.

After the spill decision, the spilled values' uses are rewritten as memory loads/stores (the "spill code"), and the algorithm retries the whole graph coloring.

## Linear Scan (Traub et al., 1998)

Linear scan is a faster algorithm that doesn't build an interference graph. It works on the live ranges' sorted-by-start-point list:

```text
1. Sort live ranges by their start points.
2. Walk through the live ranges in order.
3. Maintain a list of "active" live ranges (those currently in registers).
4. When a new live range starts:
   - If a register is free, assign it.
   - If all registers are in use, spill one of the active live ranges
     (heuristic: spill the one with the furthest end point).
5. When a live range ends, free its register.
```

Linear scan is O(N log N) (for the sort) and works on the fly without building a graph. It's the basis for just-in-time compilers (JVM HotSpot's client compiler, V8, .NET RyuJIT, WebAssembly engines) where compile time matters.

The quality of linear scan is ~10% worse than graph coloring for typical programs, but it runs in ~10% of the time.

## SSA-Based Allocation

Modern allocators exploit the Static Single Assignment (SSA) form, where each value has exactly one definition. In SSA, live ranges can be "split" at every definition, making them shorter and the interference graph smaller.

Two key algorithms:

- **PBQP (Partitioned Boolean Quadratic Problem)**: used in LLVM 3.x. Models register allocation as a constrained optimization problem.
- **Regalloc (Ahn & Paek, 2014)**: uses SSA to find a "perfect" allocation in polynomial time, then falls back to graph coloring for spills.

LLVM's modern `GreedyRegisterAllocator` (since 3.5) is a hybrid: SSA-based live range splitting + graph coloring + linear-scan-style spill decisions. It produces code within 5% of the theoretical optimum for SPEC CPU2006 benchmarks.

## Spill Code Insertion

When a value is spilled, the allocator:
1. Assigns the value to a stack slot (one 8-byte slot per spilled value on x86-64).
2. Rewrites every use of the value: load it into a temporary register before use, store it back after definition.
3. Re-runs the allocation to handle the new temporary registers.

The result: spilled values' uses cost ~100 ns (memory load) instead of 0.3 ns (register). For a hot loop variable that's used 100 times, this is 10 µs of extra time per iteration — a 10× slowdown for that loop.

## Register Pressure

Register pressure is the maximum number of simultaneously-live values at any point. High pressure forces spills. Common causes:
- Long basic blocks with many intermediate values.
- Functions with many parameters (each parameter is a live value at entry).
- Loops with many induction variables.

Optimizations that reduce register pressure:
- **Loop strength reduction**: replace expensive computations (multiplies) with cheaper ones (adds), reducing the number of intermediate values.
- **Loop invariant code motion**: hoist invariant computations out of loops, reducing live ranges inside.
- **Common subexpression elimination**: reuse computed values, reducing the number of unique live values.

## Calling Conventions

Calling conventions dictate which registers are caller-saved (the callee may overwrite them) and which are callee-saved (the callee must preserve them). The allocator:
- For caller-saved registers: free at every call site (the value must be spilled or saved across the call).
- For callee-saved registers: save at function entry (prologue), restore at exit (epilogue).

A common strategy: assign hot live ranges to caller-saved registers (cheap to use, but expensive across calls), and cold-but-long-lived ranges to callee-saved registers (expensive at prologue/epilogue but free across calls).

## x86-64 Calling Conventions

| Convention | Argument registers | Callee-saved | Notes |
|-------------|---------------------|--------------|-------|
| System V (Linux, macOS) | rdi, rsi, rdx, rcx, r8, r9 (integers); xmm0-7 (floats) | rbx, rbp, r12-r15 | Used by GCC/Clang |
| Microsoft x64 | rcx, rdx, r8, r9 (integers); xmm0-3 (floats) | rbx, rbp, rdi, rsi, r12-r15 | Used by MSVC |
| Vector calling convention (System V) | xmm0-7, ymm0-7, zmm0-7 | Same as above | For SIMD-heavy functions |

The number of caller-saved registers affects the spill cost across calls. The number of callee-saved registers affects the prologue/epilogue cost.

## Production Register Allocators

- **LLVM**: `Greedy` (default), `Basic` (simple, for tests), `PBQP` (rare).
- **GCC**: `ira` (interference-based register allocator), `lra` (reload after spills).
- **HotSpot (JVM)**: linear scan, optimized for fast JIT.
- **V8**: linear scan.
- **Cranelift**: linear scan (with extensions for SSA).

For ahead-of-time compilation, graph-coloring-based allocators dominate. For JITs, linear-scan dominates.

## Common Pitfalls

1. **Assuming more registers always helps.** Going from 16 to 32 GPRs helps, but only for functions with high register pressure. Most functions fit in 8 registers; the extra 24 are wasted.

2. **Forgetting that spill code itself uses registers.** A spilled value's load requires a temporary register, which itself must be allocated. The recursive allocator handles this; naive implementations can deadloop.

3. **Treating all spills equally.** A value used 1000 times in a loop has 1000× the spill cost of a value used once. The allocator must weight spill decisions by use count.

4. **Ignoring calling conventions.** A register allocator that doesn't account for call sites will spill at every call, making the function very slow.

5. **Forgetting that register allocation depends on instruction selection.** Some instructions (e.g., x86's `idiv`) use specific registers. The allocator must reserve these.

## References

- Chaitin, "[Register Allocation and Spilling via Graph Coloring](https://chaitin.net/pdf/regalloc-1982.pdf)" (SIGPLAN 1982)
- Briggs, "[Register Allocation via Graph Coloring](https://www.cs.utexas.edu/users/mckinley/380D/papers/briggs-thesis.pdf)" (PhD thesis, Rice 1992)
- Traub, Holloway, Smith, "[Quality and Speed in Linear-scan Register Allocation](https://courses.cs.washington.edu/courses/cse501/06wi/reading/traub-oopsla98.pdf)" (OOPSLA 1998)
- Poletto & Sarkar, "[Linear Scan Register Allocation](https://www.cs.princeton.edu/courses/archive/fall06/cos598A/papers/LinearScan.pdf)" (TOPLAS 2002)
- [LLVM Register Allocator documentation](https://llvm.org/docs/CodeGenerator.html#register-allocator)
- [GCC IRA (interference-based register allocator) documentation](https://gcc.gnu.org/wiki/VarModifications)
- George & Appel, "[Iterated Register Coalescing](https://www.cs.princeton.edu/~appel/papers/irc.pdf)" (TOPLAS 1996) — the Briggs-Chaitin improvement
