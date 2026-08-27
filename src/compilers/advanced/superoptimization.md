# Superoptimization

A normal compiler asks: what is a *good* instruction sequence for this expression? A superoptimizer inverts the question: define optimal (fewest instructions, fewest cycles), then *search* for the sequence that achieves it - with no heuristics, no pattern library, and no guarantee the search terminates before the heat death of the universe. That inversion was Henry Massalin's 1987 move, and it produced machine code shorter than anything compilers or assembly programmers wrote. This page covers the original exhaustive algorithm, its stochastic successor STOKE, why superoptimization survives only in small hot kernels, and how the idea leaks back into everyday compilers through peephole and synthesis machinery.

## Massalin, 1987: generate and test

Massalin's paper - "Superoptimizer: A Look at the Smallest Program," ASPLOS 1987 (the second ASPLOS, pages 122-126) - enumerated instruction sequences shortest-first and *tested* each candidate against the specification. No theorem proving: candidates were run on sample inputs, and survivors were promoted to a probabilistic final check. Two tricks made exhaustive search tractable:

- **Pruning.** A candidate is discarded if any prefix stores a value to a location no later instruction reads (dead side effect), or if the sequence is equivalent to a shorter one already generated. The generator produced only "normal-form" programs.
- **Cascading.** Solutions for shorter windows seeded the search for longer ones; instructions that verified correctly at depth n were reused as fixed context at depth n+1, exploding less.

The payoffs were startling: Massalin's tool found sign-of-a-number in 4 instructions and other sequences 1-5 instructions shorter than the best known code, including ones machine-dependent enough that no human had written them (implicit flag side effects, overlapping operand encodings). The tool became GNU `superopt` (Torbjorn Granlund's 1995 packaging, still on the GNU ftp archive), whose output was used to hand-check arithmetic routines in GNU multiprecision code. The cost: hours of compute on 1987 hardware, for windows of 2-4 instructions.

## What optimal costs: the space grows as |ISA|^n

The brute-force search space for n-instruction sequences is |ops|^n. On a 4-op toy ISA that is 4^n; on a realistic ISA with ~1,000 encodings it is 1000^n. Log-scale, the wall looks like this:

```text
  log10(programs)
  24 |                            #
  21 |                         #
  18 |                      #
  15 |                   #
  12 |                #
   9 |             #
   6 |          #                 *
   3 |       #     *  *  *  *  *
   0 |       *  *
     +-------------------------------
            1  2  3  4  5  6  7  8
          instructions in sequence

     #  1000-op ISA  (10^(3n):  8 instr = 10^24 programs)
     *  4-op toy ISA  (4^n:      8 instr =      65,536)
```

Every superoptimizer since 1987 is a strategy for climbing fewer steps of that wall: prune candidates before testing (exhaustive), sample the wall (stochastic), or shrink the ISA you search (work on IR instead of x86).

## Exhaustive vs stochastic search

| Property | Exhaustive (Massalin, superopt) | Stochastic (STOKE) |
|----------|--------------------------------|--------------------|
| Search order | Shortest sequences first | Random walks (MCMC) from a seed |
| Claim when done | Found the *optimal* sequence | Found a *good* sequence, maybe optimal |
| Scaling | Death at ~4-5 instructions | Practical at ~10-50 instructions |
| Needs | Enumerable ISA, cheap test | Cost function + verifier |
| Correctness gate | Test inputs (+ probabilistic check) | Test penalty during search, solver check at the end |
| Cost model | Length only (later: latency tables) | Any differentiable-ish cost: length, cycles, register pressure |
| Failure mode | Space explosion | Local minima, wasted walks |

## STOKE: MCMC over machine code

STOKE (Schkufza, Sharma, Aiken - "Stochastic Superoptimization," ASPLOS 2013) reframed the task: treat a loop-free x86-64 instruction sequence as a state in an enormous graph, and run Markov-chain Monte Carlo over it. Each step applies one random transformation - swap an opcode, swap an operand, replace an instruction, insert, delete, reorder. Each candidate gets a cost:

```text
cost(C)  =  penalty(C)  +  w * perf(C)

  penalty(C) : huge fixed value if any test-case output, signal, or
               memory effect disagrees with the original program
  perf(C)    : weighted instruction latency/throughput estimate
```

The walk accepts uphill moves with a Metropolis-style probability, so it escapes dead ends that greedy local search cannot. Two design choices make STOKE work. First, the search starts from *existing compiled code*, so it only has to beat GCC/LLVM, not find code from scratch. Second, correctness is layered: cheap test cases prune during search, and a solver-backed validator (symbolic execution + SMT over the ISA semantics) proves equivalence of loop-free candidates before STOKE accepts them - test inputs alone are never trusted for the final result. On published benchmarks STOKE produced memcpy faster than glibc's hand-tuned version and shortened compiler output on libm-style kernels; the [Stanford PL group repo](https://github.com/StanfordPL/stoke) documents the enumerator and the stochastic search. For the solver machinery that makes the validator sound, see [SAT/SMT solvers](../../formal-methods/sat-smt-solvers.md); for what it means to verify a compiler end-to-end, see [verified compilation](./verified-compilation.md).

## Runnable: brute-force abs-diff over a 4-op ISA

The model below is Massalin's loop in miniature: two 8-bit registers, a 4-op ISA, exhaustive enumeration shortest-first with full test coverage, counting every candidate evaluated. Part B swaps one opcode (`cmovneg` out, `xor` in) to show how ISA expressiveness changes the length of the optimal program:

```python
"""Brute-force superoptimization of abs(x - y) over a tiny 4-op ISA.

Machine model: two 8-bit registers (a, b), two's-complement arithmetic.
Inputs are 7-bit unsigned (0..127) - with full 8-bit inputs |x - y| can
reach 255, whose wrapped encoding is unrecoverable from the sign bit.
Start state: a = x, b = y. Goal: a == |x - y| for every input pair.

ISA A (4 operations, each a pure rewrite of the (a, b) state):
  sub      a = (a - b) mod 256
  neg      a = (-a) mod 256
  cmovneg  a = (-a) mod 256, only if a is negative (sign bit set)
  rsub     b = (b - a) mod 256

ISA B: cmovneg replaced by xor - does the branchless trick survive?

Exhaustive generate-and-test over all sequences of length 1, then 2,
counting every candidate program evaluated (Massalin's loop, in miniature).
"""
INPUTS = [(x, y) for x in range(128) for y in range(128)]  # 7-bit inputs


def sub(a, b):
    return (a - b) & 255, b


def neg(a, b):
    return (-a) & 255, b


def cmovneg(a, b):
    return ((256 - a) & 255, b) if a & 128 else (a, b)


def rsub(a, b):
    return a, (b - a) & 255


def xor(a, b):
    return a ^ b, b


ISA_A = {"sub": sub, "neg": neg, "cmovneg": cmovneg, "rsub": rsub}
ISA_B = {"sub": sub, "neg": neg, "rsub": rsub, "xor": xor}


def superopt(ops, max_depth):
    """Exhaustive search, shortest first. Returns (program, evaluated)."""
    goal = [abs(x - y) for x, y in INPUTS]

    def run(seq):
        out = []
        for x, y in INPUTS:
            a, b = x, y
            for op in seq:
                a, b = ops[op](a, b)
            out.append(a)
        return out

    evaluated = 0
    names = list(ops)
    for depth in range(1, max_depth + 1):
        print(f"  depth {depth}: {len(names) ** depth} candidate programs")
        # lexicographic enumeration in canonical op order
        sequences = [[]]
        for _ in range(depth):
            sequences = [seq + [n] for seq in sequences for n in names]
        for seq in sequences:
            evaluated += 1
            if run(seq) == goal:
                return seq, evaluated
        print(f"    no correct program of length {depth}")
    return None, evaluated


for label, isa in (("ISA A (has cmovneg)", ISA_A), ("ISA B (xor instead)", ISA_B)):
    print(f"{label}:")
    program, count = superopt(isa, max_depth=3)
    if program:
        print(f"  OPTIMAL: {'; '.join(program)}   ({count} programs evaluated)")
    else:
        print(f"  no program up to length 3  ({count} programs evaluated)")
```

Output (real run, CPython 3.12):

```text
ISA A (has cmovneg):
  depth 1: 4 candidate programs
    no correct program of length 1
  depth 2: 16 candidate programs
  OPTIMAL: sub; cmovneg   (7 programs evaluated)
ISA B (xor instead):
  depth 1: 4 candidate programs
    no correct program of length 1
  depth 2: 16 candidate programs
    no correct program of length 2
  depth 3: 64 candidate programs
    no correct program of length 3
  no program up to length 3  (84 programs evaluated)
```

Two lessons hide in 91 evaluated programs. Exhaustive search *proves minimality*: `sub; cmovneg` is optimal not because it looks short but because all 4 length-1 programs failed first - that certificate is something no heuristic compiler pass provides. And the optimal length is a property of the *ISA*, not the function: remove the conditional move and the same abs-diff needs a longer (or input-split) program entirely - which is why superoptimizers tuned to one ISA's weird ops keep finding "impossible" code.

## Where it pays: small hot kernels

Superoptimized code shows up wherever a few instructions execute billions of times and the function rarely changes:

- **Crypto and arithmetic inner loops.** Field arithmetic, masking, and mixing functions are short, branch-free, and security-relevant; STOKE-style searches over them have produced sequences faster than compiler output, and hand-superoptimized constants appear in production bignum and crypto libraries (GNU `superopt` fed its results into GNU multiprecision routines).
- **libc string and memory functions.** STOKE's headline result was a `memcpy` variant faster than glibc's assembly - straight-line, alias-light, exhaustively testable: the ideal superoptimization target.
- **JIT intrinsic kernels.** Runtime engines keep hand-tuned stencils for hot ops (string hashing, typed-array loops, `Math.min`/`abs` idiom lowering); the same generate-and-test discipline validates them offline, even though the JIT emits them online - see the [JIT optimization](./jit-optimization.md) page for where those intrinsics get plugged in.
- **Compiler backend hygiene.** Souper-style tools run continuously over IR being compiled, harvesting expressions where the search can beat the built-in rules (next section).

## Why whole programs resist

The wall from the diagram is only the first obstacle:

- **Loops break the model.** Exhaustive search over straight-line code has a fixed semantics per input; a loop's iterations are unbounded, so "run it and compare" needs inductive invariants, not test cases. STOKE confines itself to loop-free kernels and treats loops as a frontier.
- **Memory effects explode equivalence.** Two stores to the same unknown address commute in neither order nor value; aliasing makes the equivalence check explode in pointer arguments and drags in the full analysis machinery covered in [alias analysis](./alias-analysis.md).
- **Flags and partial side effects.** x86 condition codes are written as side effects of almost every ALU op. A validator must model them or accept bogus candidates; an ISA with implicit effects multiplies the semantic surface the search must respect.
- **Verification is the cost floor.** Even after the search finds a candidate, the solver-checked equivalence proof can dominate runtime. Search cost falls with hardware; proof cost falls only with better theories.
- **The cost model lies.** Fewest instructions is not fewest cycles: front-end limits, micro-fusion, and cache effects invert length-based rankings - the same reason the [peephole benchmarks](./peephole-optimization.md) are measured, not counted.

## Family tree: peephole, synthesis, and back

Superoptimization sits between two neighbors. Below it, [peephole optimization](./peephole-optimization.md) applies local, hand-written rewrite rules; a superoptimizer *derives* such rules by search and, once found, they can be frozen into a peephole table forever - GNU superopt output shipped as exactly that. Above it, program synthesis searches program space against a specification; superoptimization is synthesis with the spec being "same observable behavior, lower cost" and the language being machine code - which makes the SMT-based correctness check from synthesis mandatory, not optional. Souper is the bridge made production-real: it harvests expressions from real LLVM IR compilations, uses its SMT-backed search to find shorter instruction sequences, and emits them as candidate peephole rules for the LLVM midend. The everyday-compiler takeaway: most production benefit from superoptimization research arrives not as a whole-program optimal codegen, but as searched, verified local rewrites folded into the optimizers you already run.

## References

- Massalin, "Superoptimizer: A Look at the Smallest Program," ASPLOS 1987: <https://dl.acm.org/doi/10.1145/36206.36194>
- Schkufza, Sharma, Aiken, "Stochastic Superoptimization" (STOKE), ASPLOS 2013: <https://dl.acm.org/doi/10.1145/2451116.2451150> (preprint: <https://arxiv.org/abs/1211.0557>)
- STOKE - Stanford PL group: <https://github.com/StanfordPL/stoke>
- Souper - a superoptimizer for LLVM IR: <https://github.com/google/souper> (paper: <https://arxiv.org/abs/1711.04422>)
- GNU superopt archive: <https://ftp.gnu.org/gnu/superopt/> (maintained mirror: <https://github.com/embecosm/gnu-superopt>)
