# Peephole Optimization

Peephole optimization is a back-end compiler technique that examines a small window (the "peephole") of generated machine instructions and rewrites them with a shorter or faster equivalent sequence. It is the last optimization pass before code emission, catching patterns that earlier passes (instruction selection, register allocation) missed. This page covers the technique, the common patterns (algebraic simplification, strength reduction, instruction fusion), and the production implementations in LLVM and GCC.

## The Basic Idea

A peephole optimizer maintains a sliding window of 2-3 instructions over the generated code. For each window, it matches against a table of patterns and rewrites:

```text
Pattern:
  add %eax, 0
→ Replace with: nothing (the add is a no-op)

Pattern:
  mov %eax, %ebx
  mov %ebx, %ecx
→ Replace with: mov %eax, %ecx (eliminate the intermediate)

Pattern:
  imul %eax, 1
→ Replace with: nothing (multiply by 1 is identity)
```

The peephole optimizer iterates until no more patterns match (a fixed point), then moves to the next window.

## Algebraic Simplifications

The most common peephole patterns are algebraic identities:

- `x + 0 = x` — eliminate the add.
- `x * 1 = x` — eliminate the multiply.
- `x * 0 = 0` — eliminate the multiply and use a `mov 0`.
- `x - x = 0` — replace with `xor %eax, %eax`.
- `x | x = x` — eliminate the or.
- `x & 0xFF...FF = x` — eliminate the and.

These are obvious in source code but may emerge from earlier passes (e.g., constant propagation generates `add %eax, 0` from `x + constant_propagated_to_zero`).

## Strength Reduction

Peephole replaces expensive operations with cheaper ones when the operands are known constants or fit a pattern:

- `x * 2` → `x << 1` (shift is faster than multiply on most CPUs).
- `x * 4` → `x << 2`.
- `x / 2^k` → `x >> k` (arithmetic shift for signed, logical for unsigned).
- `x % 2^k` → `x & ((1 << k) - 1)`.
- `x * 2^k + c` → `lea (x, x, k), c` (x86 LEA computes shifts and adds in one instruction).

The compiler's earlier passes (instruction selection) usually do this, but peephole catches cases the selector missed (e.g., when the constant is revealed by constant propagation after instruction selection).

## Instruction Fusion

Modern CPUs can execute two dependent instructions as one (macro-op fusion). Peephole can arrange instructions to enable this:

```text
Pattern:
  cmp %eax, %ebx
  je label
→ Replace with: cmp+je as a single fused op (the CPU executes them together)
```

On x86, the CPU fuses:
- `cmp + jcc` (test/compare + conditional jump) — single decode.
- `test + jcc` — same.
- `add/sub + adc/sbb` — single ALU op.

Peephole can re-order adjacent instructions to enable fusion (e.g., move a `cmp` next to a `je` if there's a non-fusable instruction between them).

## Dead Code Elimination

After register allocation, some instructions become dead (e.g., a register was assigned but never read because the allocator spilled it). Peephole removes these:

```text
Pattern:
  mov %eax, %ebx   ← assigned
  ... (no use of %ebx)
  mov %eax, %ebx   ← re-assigned, first mov is dead
→ Replace with: mov %eax, %ebx (only the second one)
```

This is conservative — the optimizer must prove that the assigned value is never read between the two assignments.

## Constant Folding

Peephole folds constants when both operands are known:

```text
Pattern:
  mov $5, %eax
  add $3, %eax
→ Replace with: mov $8, %eax

Pattern:
  mov $0, %eax
  shr %eax
→ Replace with: mov $0, %eax (no need to shift)
```

Earlier constant propagation passes should have caught these, but peephole catches the cases where constant propagation runs after code generation (e.g., for macro-expanded constants).

## Branch Optimization

Peephole simplifies control flow:

- **Branch to branch**: `je label1; label1: jmp label2` → `je label2` (skip the intermediate jump).
- **Branch to next instruction**: `je label; label: ...` → remove the jump (it always falls through).
- **Conditional jump over unconditional**: `je label1; jmp label2; label1:` → `jne label2;` (invert the condition, eliminate the unconditional jump).

These are the most impactful peephole patterns; branches are expensive (~10 cycles when mispredicted) and the peephole can reduce branch counts by 20-30%.

## Common Subexpression Across Instructions

Peephole can recognize a common subexpression that was missed by earlier CSE:

```text
Pattern:
  mov (%rax), %eax      ← load
  add $1, %eax
  mov %eax, (%rax)
  mov (%rax), %ebx      ← load (same address)
  add $1, %ebx
  mov %ebx, (%rax)
→ Replace with: combine the two increment sequences into one
   mov (%rax), %eax
   add $2, %eax
   mov %eax, (%rax)
```

This is unusual; most CSE is done before code generation. But peephole can catch cases where the CSE was prevented by an alias analysis imprecision.

## Production Implementations

### LLVM

LLVM's peephole optimization is in `PEI::runOnMachineFunction` (Post-RA Instruction Selection) and the `MachinePeepholeOpt` pass. It handles:
- Algebraic simplifications.
- Strength reduction.
- Macro-op fusion.
- Dead code elimination.

User-visible flag: `llc -enable-peephole` (default: on).

### GCC

GCC's peephole is in `peephole2.c` (run after register allocation) and `peephole.c` (run after final reload). The patterns are machine-specific, defined in `gcc/config/<arch>/<arch>.md` files.

### Other Compilers

- **Cranelift**: has a `peepmatic` DSL for defining peephole patterns. Patterns are JIT-compiled for fast matching.
- **HotSpot (JVM)**: uses peephole after the `Matcher` (instruction selection) and `RegAlloc` (register allocation) passes.
- **V8 (JIT)**: simpler peephole, focused on JIT speed.

## DSLs for Peephole Patterns

Modern compilers use DSLs to define peephole patterns:

- **Cranelift's `peepmatic`**: separate DSL compiled to a Rust matcher.
- **Alive2**: a DSL for specifying LLVM peephole transformations, with automated correctness checking.
- **LLVM's TableGen**: used for instruction selection; can also define peephole patterns.

These DSLs let compiler writers add new patterns without writing C++ matching code, increasing productivity.

## Common Pitfalls

1. **Reordering instructions across aliasing boundaries.** A peephole that moves a load across a store must verify they don't alias. Many peephole passes don't have access to alias analysis, so they're conservative.

2. **Forgetting that peephole runs after register allocation.** The peephole sees real registers, not SSA values. Patterns must account for register pressure — replacing `imul %eax, 2` with `lea (%eax, %eax), %ebx` adds a register dependency that may hurt scheduling.

3. **Over-optimizing for one CPU.** A peephole pattern that helps Intel's uarch may hurt AMD's (e.g., the LEA fusion has different costs). Modern compilers tune per CPU model.

4. **Trusting that pattern matching is exhaustive.** Real-world peephole passes miss patterns. A new CPU instruction may not be in the pattern database, missing optimization opportunities.

5. **Forgetting that macro-op fusion is CPU-specific.** Some CPUs fuse `cmp+jcc` but not `test+jcc`. The peephole must respect the target's fusion rules.

6. **Reordering instructions that change exception behavior.** A load that may page-fault cannot be reordered past a store that may also page-fault (the exception order must be preserved).

## Benchmarks

Production peephole impact (LLVM 16 on x86-64, SPEC CPU2017):

- **Instruction count reduction**: 5-8% fewer instructions.
- **Cycle count reduction**: 3-5% faster (some instructions are slower than others).
- **Compile time**: peephole is <1% of compile time.

For JITs (V8, HotSpot), the peephole is much faster (sub-millisecond) and the impact is smaller (~2% speedup) because JITs run simpler passes.

## References

- Tanenbaum et al., "[A Fresh Look at Peephole Optimization](https://dl.acm.org/doi/10.1145/359114.359122)" (Software Practice & Experience 1982)
- Davidson & Fraser, "[The Design and Application of a Retargetable Peephole Optimizer](https://dl.acm.org/doi/10.1145/3570837)" (TOPLANS 1984)
- Massaroff & Drosch, "[The RTL Peephole Optimizer of GCC](https://gcc.gnu.org/wiki/peephole2)" (GCC internals doc)
- [LLVM MachinePeephole source](https://github.com/llvm/llvm-project/blob/main/llvm/lib/CodeGen/MachinePeephole.cpp)
- [Alive2: Verifying LLVM peephole optimizations](https://alive2.llvm.org/ce/)
- [Cranelift's peepmatic DSL](https://github.com/bytecodealliance/cranelift/tree/main/peepmatic)
- [GCC Machine Descriptions (.md) files for peephole](https://gcc.gnu.org/onlinedocs/gccint/Peephole-Definitions.html)
