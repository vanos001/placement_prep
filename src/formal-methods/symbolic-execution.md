# Symbolic Execution and Concolic Testing

A fuzzer mutates inputs and hopes. Symbolic execution does the arithmetic: it runs a
program with inputs as *variables*, records the branch conditions it would need to reach
each point as a formula (the path constraint), and asks an SMT solver for a concrete
input that satisfies the formula. "Take the else branch at line 40" stops being a
probability and becomes an equation to solve. Concolic (concrete + symbolic) testing is
the practical variant: execute for real, maintain the path constraint alongside, flip one
constraint, solve, re-execute.

## Concrete state vs symbolic state

A symbolic executor interprets the program twice, in parallel:

```text
 concrete store: x = 44    symbolic store: x = x0
 y = x % 4                 -> y = x0 mod 4
 if y == 0 ----- fork ----- {x0 mod 4 == 0}   |   {x0 mod 4 != 0}
 z = x // 4                -> z = x0 div 4
 if z > 10 ----- fork ----- {.. and x0 div 4 > 10}  |  {.. and x0 div 4 <= 10}
   each feasible path condition goes to the solver; SAT -> new test input
```

Every branch is a fork: the engine explores both sides, conjoining the branch predicate
(or its negation) to the path condition. A path is *feasible* if its constraint set is
satisfiable; the solver's model is a test input that drives the real program down that
path. Infeasible paths are pruned without ever being executed.

## What the solver costs you

Path constraints are handed to an SMT solver (bitvectors, arrays, uninterpreted
functions; rarely quantifiers). Practical economics:

- Solving is NP-hard in general (SAT with structure); typical per-query times are
  microseconds to seconds, and a single path can generate thousands of queries.
- Engines therefore cache aggressively: KLEE keeps a solver cache plus a
  counterexample cache, and reuses simplified equivalence classes for reads/writes.
- A *divergence* (KLEE's term) is a query that times out on constraints the engine
  believed it had already solved -- usually caused by incidental slack in earlier
  models. Divergences and expensive array reasoning dominate real-world slowdowns.
- When a query comes back UNSAT, the *unsat core* (the minimal subset of constraints
  responsible) is valuable: replay can drop guards that provably do not matter, and
  test-generation can minimize the input.

## Path explosion and its mitigations

Loops are the killer. A k-iteration loop whose body has one data-dependent branch has
2^k paths; a program with 30 such loops has more paths than atoms. Function calls with
loops multiply the same effect (every call site re-explores the callee). Standard
countermeasures:

| Mitigation | Mechanism | Cost |
|---|---|---|
| Bounded search | Unroll loops k times, cap depth | Misses deeper paths |
| Search heuristics | DFS for depth, coverage-optimized or random-path search for breadth | No completeness |
| Function summarization (compositional) | Solve a callee once per "behavior", reuse the summary at every caller | Wrong if summary invalid (recursion, globals) |
| State merging | Join divergent states into one with a phi-guard instead of exploring both | Bigger formulas per state |
| Memoization / caching | Reuse solver results across states | Memory pressure |

Concolic testing (DART, Godefroid et al., PLDI 2005) arose precisely to bound this:
random testing produces inputs, and symbolic reasoning runs *backwards from one failed
run* to construct the next input -- one path at a time, chosen by the fuzzer's luck,
never enumerating the tree. CUTE (Sen and Agha, 2006) added structure-aware treatment
of pointers and heap; note it is often misattributed -- the Cadar/Engler lineage is the
separate EXE/"execution generated tests" work (CAV 2005) that became KLEE.

## KLEE (OSDI '08): the reference architecture

KLEE (Cadar, Dunbar, Engler) compiles C to LLVM bitcode and interprets it on a virtual
little operating system:

- State = (path constraint set, copy-on-write memory objects, symbolic store). Forking
  is cheap because memory is shared until written.
- Symbolic/actual duality: whenever an operation is under-specified symbolically
  (syscalls, floating point corner cases, some libc internals), KLEE falls back to
  *concrete execution*, calling into a real environment (uClibc, a POSIX model). The
  oracle problem is dodged by keeping concrete state alongside symbolic state.
- Search: interleaved heuristics (random path selection to dodge solver thrash,
  coverage-weighted selection to steer toward untested code).
- Output: for each error (assertion failure, memory error, divergence), the satisfying
  input is emitted as a `.ktest` file -- a plain regression test replayable without KLEE.

The OSDI'08 numbers: run against GNU coreutils, KLEE "exhaustively" covered ~90% of
lines across 89 utilities, including parsers that had shipped for 15 years, and found 56
real bugs. The follow-up lesson everyone should internalize: the bugs were mostly in
*input handling* -- exactly where path constraints concentrate -- and many remained
unfixed upstream years after being reported with reproducing inputs.

## Binary-level engines: angr and S2E

- **angr** (UCSB, IEEE S&P'16 SoK on binary analysis): loads stripped binaries, recovers
  a CFG, and does VEX-IR symbolic execution with *simprocedures* -- pre-written summaries
  for library calls whose source you lack. Its hook model plus CLI makes it the default
  for CTF-style and analysis work; see docs.angr.io.
- **S2E** (OSDI'11): symbolic execution *inside QEMU*, so the "environment" (kernel,
  drivers, whole guest OS) is real and the analysis is in-vivo. Its selective
  symbolization (mark exactly which bytes/registers are symbolic) plus plugin
  architecture made it the workhorse for OS-level and firmware analysis.

## Limits you will be asked about

- Environment modeling: syscalls, files, and networks must be modeled or concretized;
  modeling wrong gives false confidence. Whole-OS tools (S2E) trade this for scale.
- Concurrency and real time: interleavings explode the path tree in a second dimension.
- Pointer arithmetic and arrays push queries into expensive array theory; floats need
  floating-point solvers that are much slower than bitvector ones.
- The oracle problem: symbolic execution finds *crashes and assertion failures* for
  free; finding "wrong but not crashing" requires a spec, which someone must write.

## Where fuzzing fits (see the fuzzing chapter for the tooling)

Coverage-guided fuzzing (AFL-style) is symbolic execution's practical rival: it has no
solver, scales to millions of executions per second, and its coverage feedback greedily
finds shallow paths. Symbolic execution is slow per path but *targeted*: it computes an
input for a specific hard predicate (a magic-byte check, a checksum, a format string).
The hybrid is now standard practice: SAGE (Microsoft) white-box-fuzzed file parsers and
reportedly found a large share of a Windows service pack's file-format bugs; Driller
(NDSS'16) runs AFL, and when coverage stalls, invokes angr's concolic engine to solve
the predicate blocking progress, then hands the solved input back to the fuzzer. Fuzzing
provides throughput and state; symbolic execution provides the key for locked doors.

## A runnable mini engine

Pure Python (no z3 needed): path enumeration with constraint collection, and "solving"
by bounded-domain replay -- the same shape as real engines, with the SMT call replaced
by scanning. The ERROR path needs x == 44; the solver must find it from the constraints,
not from luck.

```python
"""Mini symbolic executor: path enumeration with constraint collection;
'solving' = bounded-domain replay (a real engine calls an SMT solver like z3).
Then: path explosion measured on an unrolled k-iteration loop."""
DOMAIN = range(-50, 51)

# def check(x):
#     y = x % 4
#     if y == 0:  z = x // 4
#         if z > 10 and x == 44: BUG   # reachable only for x == 44
#     else: return -1
#     return z
PROG = [
    ("assign", "y", ("bin", "%", ("var", "x"), ("num", 4))),
    ("if", ("cmp", "==", ("var", "y"), ("num", 0)),
        [("assign", "z", ("bin", "//", ("var", "x"), ("num", 4))),
         ("if", ("cmp", ">", ("var", "z"), ("num", 10)),
             [("if", ("cmp", "==", ("var", "x"), ("num", 44)), [("bug",)], [])],
             [])],
        [("return", "-1")]),
    ("return", ("var", "z")),
]

def ev(e, st):
    if e[0] == "num": return e[1]
    if e[0] == "var": return st[e[1]]
    a, b = ev(e[2], st), ev(e[3], st)
    return a + b if e[1] == "+" else a % b if e[1] == "%" else a // b

def evc(c, st):
    l, r = ev(c[2], st), ev(c[3], st)
    return {"==": l == r, "!=": l != r, ">": l > r, "<=": l <= r}[c[1]]

def neg(c):
    op = {"==": "!=", "!=": "==", ">": "<=", "<=": ">"}[c[1]]
    return ("cmp", op, c[2], c[3])

def sym_exec(stmts, pc):
    """Enumerate paths. pc = ordered constraints that must hold; 'BUG' marks
    reaching the error site (then-branch constraints are the guard itself,
    else-branch constraints are its negation)."""
    if not stmts:
        yield pc; return
    s, rest = stmts[0], stmts[1:]
    if s[0] in ("assign", "return"):
        yield from sym_exec(rest, pc)
    elif s[0] == "bug":
        yield pc + ["BUG"]
    elif s[0] == "if":
        yield from sym_exec(s[2] + rest, pc + [s[1]])
        yield from sym_exec(s[3] + rest, pc + [neg(s[1])])

def follows(x, pc):
    """Concrete replay: does input x satisfy every constraint and end at BUG?"""
    st, stack, i, k = {"x": x}, PROG, 0, 0
    while i < len(stack):
        s = stack[i]
        if s[0] == "assign":
            st[s[1]] = ev(s[2], st); i += 1
        elif s[0] == "return":
            return k == len(pc)
        elif s[0] == "bug":
            return k == len(pc) - 1 and pc[-1] == "BUG"
        elif s[0] == "if":
            c = pc[k]
            if not evc(c, st):            # this path's constraint violated
                return False
            k += 1
            br = evc(s[1], st)            # branch on the program's own guard
            stack = (s[2] if br else s[3]) + stack[i + 1:]; i = 0
    return False

def show(c):
    def s(e): return str(e[1]) if e[0] == "num" else e[1]
    return "%s %s %s" % (s(c[2]), c[1], s(c[3]))

paths = list(sym_exec(PROG, []))
print("enumerated %d paths" % len(paths))
for pc in paths:
    hit = pc and pc[-1] == "BUG"
    conds = pc[:-1] if hit else pc
    w = next((x for x in DOMAIN if follows(x, pc)), None)
    print("  pc: %-40s sat=%-5s witness=%-4s %s"
          % (" and ".join(show(c) for c in conds), w is not None, w,
             "<== ERROR path" if hit else ""))

# Path explosion: unroll "for i in range(k): if x & (1<<i): acc = x" k times.
def unrolled(k):
    stmts = [("return", ("var", "x"))]
    for i in range(k):
        stmts = [("if", ("cmp", ">", ("bin", "&", ("var", "x"), ("num", 1 << i)),
                         ("num", 0)), [("assign", "acc", ("var", "x"))], [])] + stmts
    return stmts

print("\npath explosion from a k-iteration loop (fully unrolled):")
import time
for k in (4, 8, 12, 16, 20):
    t0 = time.perf_counter()
    n = sum(1 for _ in sym_exec(unrolled(k), []))
    print("  k=%2d -> %7d paths (%.3fs)" % (k, n, time.perf_counter() - t0))
```

Real output (Python 3.12):

```text
enumerated 4 paths
  pc: y == 0 and z > 10 and x == 44            sat=True  witness=44   <== ERROR path
  pc: y == 0 and z > 10 and x != 44            sat=True  witness=48
  pc: y == 0 and z <= 10                       sat=True  witness=-48
  pc: y != 0                                   sat=True  witness=-50

path explosion from a k-iteration loop (fully unrolled):
  k= 4 ->      16 paths (0.000s)
  k= 8 ->     256 paths (0.001s)
  k=12 ->    4096 paths (0.008s)
  k=16 ->  65536 paths (0.144s)
  k=20 -> 1048576 paths (2.434s)
```

Two things to take from the output. First, the solver produced x = 44 for the ERROR path
-- the constraint `x == 44` sits behind two other guards, and blind fuzzing would find it
here but not once the guards become a checksum. Second, path count is exactly 2^k: the
explosion is in *paths*, not program size -- which is why every practical engine caps,
merges, or summarizes rather than enumerating.

## References

- [King, Symbolic Execution and Program Testing, CACM 1976 (the original formulation)](https://doi.org/10.1145/360303.360308)
- [Godefroid, Klarlund, Sen, DART: Directed Automated Random Testing, PLDI 2005](https://doi.org/10.1145/1065010.1065036)
- [Cadar, Dunbar, Engler, KLEE: Unassisted and Automatic Generation of High-Coverage Tests, OSDI 2008](https://www.usenix.org/legacy/event/osdi08/tech/full_papers/cadar/cadar.pdf)
- [angr documentation (loading binaries, simprocedures, exploration)](https://docs.angr.io/)
- [Shoshitaishvili et al., Driller: Augmenting Fuzzing Through Selective Symbolic Execution, NDSS 2016](https://doi.org/10.14722/ndss.2016.23368)
