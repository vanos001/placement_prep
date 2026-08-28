# Auto-Vectorization Internals

Auto-vectorization is the compiler's answer to a question every performance
engine eventually asks: why didn't my loop use the SIMD unit? The hardware
offers 8 or 16 lanes per register; the source says "add these numbers"; and
between the two sits a surprisingly deep pile of machinery: dependence
analysis, runtime versioning, an intermediate "plan" representation, cost
models, and a second vectorizer that works on straight-line code. This page
covers those mechanics. The catalog-level view of where vectorization fits
among other optimizations lives in
[Compiler Optimizations](compiler-optimizations.md); instruction tables and
intrinsics live in [SIMD](../../arch/parallelism/simd.md).

## The Two Vectorizers and the Pipeline That Feeds Them

LLVM ships two vectorizers, both enabled by default at `-O2` and above
(controlled by `-fvectorize` / `-fslp-vectorize`): the **Loop Vectorizer**
(`-loop-vectorize`) and the **SLP Vectorizer** (`-slp-vectorize`). They solve
different problems and run back-to-back:

```text
                   scalar IR
                       |
        +--------------+----------------+
        |                               |
  Loop Vectorizer                  SLP Vectorizer
  (loop bodies, trip counts,       (straight-line trees,
   reductions, interleaving)        adjacent isomorphic stmts)
        |                               |
        +--------------+----------------+
                       |
              cost-model-gated rewrite
                       |
                 vector IR -> ISel
```

The loop vectorizer handles one loop at a time and can manufacture entirely
new control flow (versioning, epilogues, peeling). SLP works on basic blocks:
it finds groups of scalar operations that happen to sit next to each other and
fuses them into single vector operations. GCC has the analogous
`-ftree-vectorize` (on at `-O2` since GCC 12) built on the same
legality/profitability split, but a different internal representation.

## Legality: Can This Loop Be Vectorized at All?

Every vectorizer first asks a **safety** question, independent of speed. For a
`for (i = 0; i < n; ++i)` loop over arrays, the checks include:

1. **Countability**: the trip count must be computable before or during entry,
   with a single (or predicable) exit.
2. **Memory dependence**: no write may feed a read that it overtakes. This is
   the heart of legality. If iteration `i` writes `A[i+1]` and reads `A[i]`,
   the dependence distance is -1 and any VF > 1 reorders memory. If the
   distance is `d`, a load/store chain vectorizes only when `d >= VF`; the
   interleaved-group machinery covers a few fixed patterns beyond that:

```text
   distance d = 3, VF = 4:  ILLEGAL (lane 3 of iter i writes A[i+4-3]=A[i+1]
                                    before lane 1 reads it)
   distance d = 5, VF = 4:  legal   (all loads of iter i come from a
                                     previous scalar region)
   iter i:    L: A[i] ......... S: A[i+5]
   iter i+1:  L: A[i+1] ....... S: A[i+6]
   lanes never cross the dependence edge when d >= VF
```

3. **No side effects**: calls that might write memory, `volatile` accesses,
   and unwinding operations block transformation unless proven inert.
4. **No wrap-around**: induction variables must be `nsw` (no signed wrap) or
   provably in-range, or the vectorized pointer arithmetic could overflow.

Pointer aliasing is the classic gray zone: if `a` and `b` might overlap, the
dependence distance is unknown at compile time. The fix is not refusal but
**runtime versioning** (next section).

## Runtime Checks and the Versioned CFG

When aliasing, stride, alignment, or trip-count divisibility cannot be proven
statically, LLVM emits a check at loop entry and two copies of the loop. The
documented behavior ("Runtime Checks of Pointers" in the LLVM vectorizer
docs) is: vectorize only if the arrays are disjoint, or separated by at least
the vector width. The resulting control flow looks like:

```text
         entry
           |
      +----+----+   runtime checks:
      |         |   disjoint(a, b) OR |a - b| >= VF*esz ?
   vector    scalar  strides == expected?
   version   version trip_count >= VF?
      |         |
      +----+----+
           |
          exit
```

This is why `restrict`/`__restrict` matters: it lets the frontend emit
`noalias` metadata, which deletes the check and the scalar fallback. It is
also why adding a third array argument can silently de-vectorize a loop: the
check set grows, and the cost model starts rejecting the vector path.

Strides get their own checks: an array-of-structs loop that "looks" scalar may
access with stride 24 bytes; LLVM builds **interleaved memory groups** and
verifies each group's stride at runtime. Alignment used to require peeling
(prologue iterations until the pointer is aligned to the vector width);
modern targets with unaligned-friendly loads mostly dropped that, and SVE /
AVX-512 make even the epilogue cheap via masking.

## VPlan: Modeling the Vector Loop Before Building It

Early vectorizers transformed code greedily and prayed; that scaled badly
once features interact (epilogue vectorization x predication x early exits x
interleaving). LLVM's answer is **VPlan** (Vectorization Plan), documented in
the LLVM VectorizationPlan spec: an explicit model of the vector loop's
control-flow graph and its per-block "recipes" that exists *before* any IR is
rewritten. Recipes describe what each vector instruction should become:

```text
VPlan (model)                      generated IR
---------------------------        ---------------------------
VPWidenLoadRecipe  (A[i])   --->   <4 x float> load
VPWidenLoadRecipe  (B[i])   --->   <4 x float> load
VPWidenRecipe      (add)    --->   fadd <4 x float>
VPWidenStoreRecipe (C[i])   --->   store <4 x float>
VPReplicateRecipe  (call)   --->   scalar call, one per lane
VPBranchOnMaskRecipe        --->   masked-block branch (AVX-512/SVE)
```

Legality, cost modeling, and transformation each consume the same VPlan, so a
feature like "vectorize the epilogue too, at half width" becomes a plan-level
composition instead of a special case. The docs describe early-exit handling
as a `BranchOnTwoConds` recipe that funnels both the latch and the early-exit
conditions through one exit path - a shape that would be brittle to hack
directly into IR.

## Interleaving vs Vectorization: VF and IF

Two independent knobs come out of the loop vectorizer:

- **VF (vectorization factor)**: lanes per register. VF=8 for f32 with AVX2.
- **IF (interleave count)**: how many vector chunks each iteration processes,
  i.e. vector-mode unrolling. Controlled with
  `-force-vector-interleave=N` / `#pragma clang loop interleave_count(N)`.

```text
VF=4, IF=2, one vector iteration handles 8 elements:

  v0 = A[i+0..3]   v1 = A[i+4..7]        two loads
  v2 = B[i+0..3]   v3 = B[i+4..7]        two loads
  v0+=v2           v1+=v3                two adds (ILP across v0/v1)
  C[i+0..3]=v0     C[i+4..7]=v1          two stores
```

IF exists because vector execution units are pipelined: one `fadd <8 x float>`
per iteration leaves the accumulator serially dependent, so the loop runs at
add-latency speed. With IF=2+ the two accumulators overlap. Too much
interleaving, however, spills registers - another cost-model decision.

## The Cost Model: Will It Actually Run Faster?

Legality says "can"; the cost model says "should". LLVM asks each target
(back end) to price every recipe through its target-transform-info (TTI)
tables: instruction latencies/throughputs, shuffle and blend costs, gather
penalties, register pressure. The vectorizer then compares candidate VFs
(2, 4, 8, ... interleaved with IFs) against the scalar baseline and picks the
cheapest plan - or none. Decisions that routinely surprise people:

| Cost-model driver | Effect seen in code |
|---|---|
| Gather cost >> load cost | strided access may stay scalar on some targets |
| Reduction latency | IF raised to hide fadd chain dependency |
| Register pressure | interleaving capped before spills appear |
| Predication cost | short loops may fold tail into masked vector ops |
| Branch cost | `if/else` bodies become `select` only when cheap |

The cost model can and does answer "scalar is faster" - notably for loops
whose body is a single cheap operation on data already in cache lines it must
touch anyway (memory-bound), or where shuffling inputs into shape costs more
than the arithmetic saved.

## SLP: Vectorizing Straight-Line Code

SLP (superword-level parallelism) targets the code the loop vectorizer never
sees: `a0 = x0+y0; a1 = x1+y1; ...` written out by hand, generated code, or
unrolled blocks. Larsen and Amarasinghe's PLDI 2000 paper framed it as pack
discovery: find adjacent statements whose expression trees are **isomorphic**
(same operator at every level, operands commuted only where legal), then
execute each pack as one vector op. The simulator below reproduces that
core algorithm - contiguity in program order, isomorphism via normalized
signatures, chaining on earlier packs:

```python
"""SLP-style pack discovery (simplified Larsen-Amarasinghe isomorphism test).

Each statement is dst = op(a, b) over scalar variables. Real SLP packs only
CONSECUTIVE isomorphic statements: same operator at every level of the two
expression trees, operands either commutative-swapped or drawn from an already
formed pack at consistent lane offsets. Depth-limited signature matching below
emulates the isomorphism check; contiguity in program order is enforced.
"""
PROGRAM = [
    ("a0", "add", "x0", "y0"),
    ("a1", "add", "x1", "y1"),
    ("a2", "add", "x2", "y2"),
    ("a3", "add", "x3", "y3"),
    ("b0", "mul", "a0", "g0"),
    ("b1", "mul", "a1", "g1"),  # chains on a-pack lanes 0,1; gathers g0,g1
    ("c0", "add", "p", "q"),
    ("c1", "sub", "p", "q"),    # different op at root -> never packs with c0
    ("d0", "add", "r", "s"),
    ("d1", "add", "s", "r"),    # commuted operands -> still isomorphic
    ("e0", "add", "a0", "a2"),
    ("e1", "add", "a1", "a3"),  # operands strided by 2 inside the a-pack
]

def iso_sig(dst, depth, stmts):
    """Signature with commutative normalization at every level."""
    op, x, y = stmts[dst]
    def side(o):
        if depth == 0 or o not in stmts:
            return "leaf"          # independent scalars -> gatherable
        return iso_sig(o, depth - 1, stmts)
    return (op,) + tuple(sorted([side(x), side(y)], key=repr))

def find_packs(stmt_list, depth=3):
    stmts = {dst: (op, x, y) for dst, op, x, y in stmt_list}
    order = [s[0] for s in stmt_list]
    sig = {v: iso_sig(v, depth, stmts) for v in order}
    packs, used = [], set()
    i = 0
    while i < len(order):
        v = order[i]
        pack = [v]
        # packs must be contiguous in program order (consecutive defs)
        while (i + len(pack) < len(order)
               and sig[order[i + len(pack)]] == sig[v]):
            pack.append(order[i + len(pack)])
        if len(pack) > 1:
            packs.append((pack, stmts[v][0]))
            used.update(pack)
        i += len(pack)
    return packs, used

packs, packed = find_packs(PROGRAM)
print(f"{len(PROGRAM)} scalar statements -> {len(packs)} SIMD packs")
for pack, op in packs:
    print(f"  pack VF={len(pack)}  op={op:3s}  lanes={','.join(pack)}")
skipped = [s[0] for s in PROGRAM if s[0] not in set(packed)]
print("left as scalars:", ",".join(skipped))
```

Running it (`python3 slp_pack.py`) prints:

```text
12 scalar statements -> 4 SIMD packs
  pack VF=4  op=add  lanes=a0,a1,a2,a3
  pack VF=2  op=mul  lanes=b0,b1
  pack VF=2  op=add  lanes=d0,d1
  pack VF=2  op=add  lanes=e0,e1
left as scalars: c0,c1
```

Note what the algorithm got right: `c0/c1` are rejected (different root
operator), `d0/d1` survive commutativity, `e0/e1` reuse the a-pack at lane
stride 2, and the `b` pack chains on `a`'s result - real SLP then bills the
cost of gathering `g0,g1` into a vector and may split the pack if that
buildvector is too expensive.

## Pragmas and Keywords: What Each One Promises

Pragmas are contracts, and they are not interchangeable:

| Directive / flag | Promise made | Still required for speed |
|---|---|---|
| `#pragma omp simd` | loop has no deps except stated `reduction(...)` clauses; enables reassociation within the loop | cost model must still like it |
| `#pragma clang loop vectorize_width(8) interleave_count(4)` | exact VF/IF demanded from LLVM's vectorizer | legality still checked first |
| `#pragma GCC ivdep` | GCC assumes no *lexical* loop-carried dependencies | aliasing between different pointers still checked |
| `restrict` / `__restrict` | pointers do not alias for the call's lifetime | removes runtime checks, not dependence logic |
| `-ffast-math` (or `-fassociative-math`) | FP may be reordered/associated | needed for float reductions without omp simd |

The classic trap: `sum += a[i]` looks vectorizable but floating-point
addition is not associative, so the compiler must keep the serial chain until
told otherwise. `#pragma omp simd reduction(+:sum)` grants that freedom
locally; `-ffast-math` grants it globally and changes numerics everywhere.

## ISA Width: A Short History from the Vectorizer's Seat

The vectorizer's job changed every time the ISA did:

| ISA | Year | Width | Vectorizer-visible change |
|---|---|---|---|
| SSE / SSE2 | 1999/2001 | 128-bit | first mass-market auto-vector target |
| AVX | 2011 | 256-bit | VEX encoding, 3 operands; non-destructive ops |
| AVX2 | 2013 | 256-bit | integer lanes catch up; gathers arrive (slow) |
| AVX-512 | 2017 | 512-bit | opmask registers, masked/compacting loads, embedded rounding |
| SVE / SVE2 | 2017/2019 Armv9 | scalable (128-2048) | VL-agnostic code, per-lane predication, first-faulting loads |
| RVV 1.0 | 2021+ | scalable (VLEN) | `vl` register, LMUL, no fixed VF at compile time |

Two consequences deserve emphasis. First, **AVX-512's masks made tail
handling cheap**, which is why modern loops often have no scalar epilogue at
all: the last partial iteration runs masked (`-prefer-predicate-over-epilogue`
in LLVM). Second, **scalable vectors (SVE/RVV) removed VF from compile
time**: the compiler emits vector-length-agnostic loops and the cost model
reasons in "known multiples of vscale" instead of hardcoded lane counts.

The x86 story also shows the ecosystem risk: AVX-512's early implementations
downclocked on heavy 512-bit code, Intel's hybrid client chips shipped
without it (Alder Lake, 2021; Arrow Lake, 2024, dropped it again after
restorations), while server parts (Sapphire/Granite Rapids) and AMD's Zen 4
(double-pumped) and Zen 5 (full 512-bit datapath) embrace it. Intel's AVX10
spec (AVX10.2 revision, 2024) converges the extensions going forward with
512-bit as the ceiling. A vectorizer cost model that predates any of this
quietly makes the wrong call - which is why `-march=` choice is inseparable
from auto-vectorization.

## Gather, Scatter, and Memory Reality

A vector load assumes lanes live side by side. When they do not, the ISA
offers **gather** (AVX2/AVX-512, SVE, RVV) and **scatter** (AVX-512, SVE,
RVV): one instruction, one lane per element, implemented internally as
multiple micro-ops plus conflict handling. Rule of thumb backed by published
throughput tables (Agner Fog's instruction tables): a gather costs several
times a contiguous load, so compilers emit one only when the cost model
clears it - typically for irregular `idx[i]` access where the alternative is
scalar loads anyway. For constant strides, LLVM prefers interleaved groups
(deinterleave on load, interleave on store) over gathers. And when the loop
is memory-bandwidth-bound, all of this is moot: 16 lanes of adds still wait
on the same DRAM. Vectorization buys compute throughput, not bandwidth.

## Failure Catalog: Why Your Loop Didn't Vectorize

The vectorizer always explains itself if you ask:
`clang -Rpass-analysis=loop-vectorize` (GCC: `-fopt-info-vec-missed`).

| Diagnosis | Typical report line | Fix |
|---|---|---|
| loop-carried dependence | "unsafe dependent memory operations" | restructure, restrict, or accept scalar |
| side-effecting call | "call instruction cannot be vectorized" | inline + prove readnone, or vectorize the callee |
| FP reduction | "cannot be reordered; vectorization is illegal" | `#pragma omp simd reduction(+:s)` or fast-math |
| unknown stride | "unexpected memory access pattern" | pack the AOS, or provide a gather-friendly target |
| early exit + heavy body | predication judged too costly | split loop, or restructure exit |
| volatile / syscall inside | "cannot be vectorized" | hoist it out; no pragma will help |
| C++ iterator loops over containers | dependence not provable | use raw pointers / `std::span`, `restrict`-like discipline |
| inline asm | opaque to analysis | hand-vectorize that section yourself |

Diagnosis beats folklore every time: a `-Rpass-analysis` run distinguishes
"the compiler could not" (legality) from "the compiler would not" (cost
model) - two different engineering problems.

## Where to Go Next

- [Compiler Optimizations](compiler-optimizations.md) - the full
  transformation catalog and where vectorization sits among them.
- [SIMD](../../arch/parallelism/simd.md) - ISA-by-ISA instruction details,
  register tables, and intrinsics.
- [Profile-Guided Optimization](profile-guided-optimization.md) - hot-loop
  data that sharpens the cost model's guesses.
- [LLVM IR](llvm-ir.md) - the IR level contracts (`noalias`, `nsw`, fast-math
  flags) that vectorizers rely on.

## References

1. LLVM, "The LLVM Vectorizers" (Loop Vectorizer and SLP Vectorizer docs):
   <https://llvm.org/docs/Vectorizers.html>
2. LLVM, "Vectorization Plan" (VPlan design document):
   <https://llvm.org/docs/VectorizationPlan.html>
3. LLVM Language Reference, `llvm.loop` metadata:
   <https://llvm.org/docs/LangRef.html#llvm-loop-metadata>
4. G. Larsen, S. Amarasinghe, "Exploiting Superword Level Parallelism with
   Multimedia Instruction Sets," PLDI 2000, DOI 10.1145/349299.349320.
5. GCC manual, "Pragmas Accepted by GCC" (`#pragma GCC ivdep` semantics):
   <https://gcc.gnu.org/onlinedocs/gcc/Pragmas.html>
6. OpenMP Architecture Review Board, OpenMP Specification (simd construct):
   <https://www.openmp.org/spec-html/5.1/openmp.html>
