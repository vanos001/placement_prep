# Polyhedral Compilation: When Loops Become Integer Sets

Most loop optimizations you meet in practice (unrolling, interchange, tiling) are pattern-matched one loop at a time, and their legality is argued ad hoc. The **polyhedral model** replaces that per-loop folklore with a single uniform representation: every statement in a loop nest gets an **iteration domain** (a set of integer points described by affine constraints), every memory access gets an **affine access function** mapping iterations to addresses, and the whole execution order is captured by a **schedule** - a map from iteration vectors to time vectors. Once loops live in this world, transformations stop being special cases: fusion, interchange, skewing, and tiling are just different schedules over the same domains, and "is this transform legal?" becomes a question of integer feasibility that a library like isl can answer mechanically. This page builds that machinery from the inside: the data structures, the dependence tests, the scheduling algorithms, and the two production pipelines (Polly in LLVM, Graphite in GCC). For how the non-polyhedral machinery of a modern compiler handles the same problems - scalar evolution, rotation, peeling, pipelining - see [Loop Optimizations Internals](../loop-optimizations-deep.md); that page's SCEV-vs-polyhedral comparison table is the 30-second version of this page's cost argument.

## The Three Ingredients: Domains, Accesses, Schedules

Consider a matrix-multiply statement `C[i][j] += A[i][k] * B[k][j]` inside `for (i...) for (j...) for (k...)`. The polyhedral representation is three small algebraic objects:

| Object | Written as | Meaning |
|---|---|---|
| Iteration domain | `S[i,j,k] : 0 <= i,j,k < N` | The integer points for which statement `S` executes |
| Read relations | `C_S(i,j,k) = { (i,j) }`, `A_S = { (i,k) }`, `B_S = { (k,j) }` | Affine map from an iteration to the elements it reads |
| Write relation | `W_S(i,j,k) = { (i,j) }` | Affine map from an iteration to the element it writes |
| Schedule | `theta(i,j,k) = (i, j, k)` | A map whose lexicographic order is the execution order |

Three properties make this representation tractable. First, domains are **convex polyhedra intersected with an integer lattice**, so a domain with a billion points is still a handful of inequalities. Second, accesses are functions, not arbitrary graphs - asking "which iteration writes address `x`?" is inverting an affine map, which is linear algebra, not pointer analysis. Third, everything composes: the union of two statements' domains is a domain, the composition of a schedule with a transform is a schedule. isl (the Integer Set Library that Polly and Graphite both use) implements exactly these objects - `isl_set`, `isl_map`, and their `union` variants for multi-statement domains - as unions of pairwise-disjoint basic polyhedra, with operations like `intersect`, `apply` (relation composition), `lexmin`/`lexmax` (smallest/largest feasible solutions), `coalesce`, and transitive closure (`powers`) built on top. An isl set for the matmul domain reads `{ S[i,j,k] : 0 <= i < N and 0 <= j < N and 0 <= k < N }`, and the same textual syntax is what its tools accept as input.

## What "Affine" Means - and What Breaks It

**Affine** means exactly `f(x) = A*x + b` for a constant integer matrix `A` and vector `b`: loop bounds like `0 <= i < N`, index expressions like `a[i][2*j + 1]`, and conditions like `i < j` are all affine. The generalization to **Presburger arithmetic** (integer linear formulas with `and/or/not/exists`) is where the practical tools draw the boundary: domains and schedules stay in the affine (or at most quasi-affine, allowing divisibility like `i % 4 == 0`) fragment, because every operation above it costs an order of magnitude more analysis. The detector that decides "is this region a SCoP (Static Control Part)?" therefore spends most of its time refusing code:

| Construct | Affine? | Example | What the detector does |
|---|---|---|---|
| Linear loop bounds | Yes | `for (i = 0; i < n; i++)` | Accepts |
| Loop-varying stride reads | Yes | `a[2*i + 3]` | Accepts |
| Affine guards | Yes | `if (i < j) ...` | Accepts (splits the domain) |
| Divisibility bounds | Quasi-affine | `if (i % 4 == 0)` | Accepts in isl, often rejected by Polly |
| Indirect indexing | No | `a[b[i]]` | Rejects the SCoP (or splits around it) |
| Data-dependent trip count | No | `while (a[i] != 0)` | Rejects |
| Nonlinear recurrence | No | `x = i * i` feeding an index | Rejects |
| Pointer chasing / calls | No | `p = p->next` | Rejects |

The first four rejections are the honest ones - the dependence pattern of `a[b[i]]` is a graph, not a function, and no schedule over integer points can describe it. The rest of the compiler does not give up when the polyhedral pass does: a rejected region simply continues through the normal scalar pipeline, which is why Polly can be enabled aggressively without risking correctness (the risk is lost opportunity, not wrong code).

## Dependences as Polyhedra, Feasibility as ILP

A **dependence** is a witness that one iteration must observe another's memory effect. Given a write relation `W` and a read relation `R`, the set of all (source, sink) iteration pairs that touch the same element is the polyhedron

```text
Dep = { [s -> t] : s in Dom_W, t in Dom_R, W(s) = R(t) }
```

- a system of linear equalities and inequalities over integer iteration vectors. Everything the scheduler needs is a question about this set:

- **Does the dependence exist at all?** Is `Dep` non-empty? (Integer feasibility.)
- **What is its distance?** Compute `t - s`, i.e. `lexmin`/`lexmax` over the linear form `(t - s)` on `Dep`.
- **Is a candidate schedule legal?** For every dependence, is `theta(s)` lexicographically before `theta(t)`? This is again feasibility: substitute the schedule into `Dep` and test emptiness of the "violation" polyhedron.

Each question is an integer linear program. The rational relaxation is polynomial (LP), but integer feasibility is NP-hard in general, and full Presburger decision procedures carry a super-exponential worst case. Real implementations thread this needle in three ways: they keep the problem **small** (a SCoP has a few dozen dependences, not billions), they use **parametric integer programming** (Feautrier's PIP algorithm) rather than naive branch-and-bound, and they accept **incompleteness** - when a solver cannot decide, the pass bails out to the scalar pipeline. The demo at the bottom of this page brute-forces the ILP on a 36-point domain so you can watch the mechanism without a solver.

## The Pluto Algorithm

Pluto (Bondhugula, Hartono, Ramanujam, Sadayappan, PLDI 2008) turned this machinery from a research curiosity into the first practical *automatic* parallelizer + locality optimizer, and its structure is still the mental model for the field:

1. **SCoP extraction** - find maximal regions of affine control (using the tools of the era: candl for dependences, CLooG for code generation).
2. **Exact dependence polyhedra** - compute `Dep` for every read/write pair, exactly, not approximately.
3. **Find affine transforms by optimization** - search for hyperplanes `c . x + c0 = 0` that (a) put every dependence source strictly before its sink (**validity** constraints, one per dependence), and (b) maximize "coincidence" - iterations sharing a hyperplane touch the same data (**profitability** objective). Pluto encodes this as a single ILP per hyperplane level and solves it with an LP/ILP solver, which is what made it *practical*: the optimum comes out of the solver, not from a fixed catalog of transformations.
4. **Fusion/fission as a modeling parameter** - a per-statement-group parameter `M` lets one solve decide to fuse loops (share a hyperplane) or split them (better locality), instead of enumerating fusion orders combinatorially.
5. **Skew + tile permutable bands, then codegen** - the discovered hyperplanes expose bands of dimensions that can be legally permuted; Pluto skews and tiles them and asks CLooG to emit the loops.

The key legacy idea is step 3: transformation *finding* becomes constrained optimization over the schedule space. isl's modern scheduler and Polly's `isl_scheduler` descend directly from this formulation (with Feautrier's algorithm as the fallback for hard dependence graphs and an ILP-based cost model for profitability).

## Schedule Trees and Transforms as Tree Edits

Early polyhedral tools represented a schedule as one full-dimensional affine map per statement. isl since 2014 represents it as a **schedule tree**, which composes partial schedules hierarchically - and this representation is what makes tiling and parallelization *local* edits rather than global rewrites:

```text
            domain { S[i,j] : 0 <= i,j < N }                 (root)
                        |
          band [ floor(i/32), floor(j/32) ]   <- tile band, permutable+coincident
                        |
                   filter: tile (p, q)                     (one tile)
                        |
                  band [ i%32 ... , j%32 ... ]             (point band)
```

A **band node** carries a partial schedule and flags: *permutable* means its dimensions may be freely reordered/tiled (the scheduler only marks this when dependences permit), *coincident* means all iterations at the same level touch the same data (safe to run in parallel). **Sequence and filter nodes** encode statement-level separation when dependences forbid fusion. Tiling is inserting a point band under a tile band; parallelization is emitting OpenMP at coincident dimensions; fusion is pulling bands under one sequence node. Because the tree keeps legality annotations, the code generator (isl AST) can walk it and emit nested loops - with `pragma omp` or CUDA kernels (PPCG, a Pluto successor, uses the same trees to target GPUs) - without re-proving anything.

## The Production Pipelines: Polly and Graphite

**Polly** is LLVM's polyhedral optimizer, built as an optional project on top of isl (its architecture page at [polly.llvm.org/docs/Architecture.html](https://polly.llvm.org/docs/Architecture.html) documents the flow below). Crucially, Polly does not replace LLVM's analyses - it *feeds* on them:

```text
LLVM IR (canonical form: mem2reg, loop-simplify, LCSSA)
        |
        v
ScopDetection ---not a SCoP---> region keeps running normal LLVM passes
   (uses SCEV + delinearization, AliasAnalysis, DominatorTree)
        |
        v
ScopBuilder: domains / access relations / initial schedule (isl objects)
        |
        v
isl scheduler: dependence-aware ILP scheduling -> schedule tree
        |
        v
isl AST generation (tiling, OpenMP marks, vectorization hints)
        |
        v
CodeGeneration: isl AST back to LLVM IR -> normal vectorizer/RA/etc.
```

Two design points are worth internalizing. First, **delinearization**: LLVM lowers `a[i][j]` to flat pointer arithmetic, and SCEV's recurrence algebra is what recovers the two-dimensional access - the hand-off point with [Loop Optimizations Internals](../loop-optimizations-deep.md). When SCEV gives up (casts, unions, irregular strides), Polly gives up on the SCoP. Second, **position**: Polly is off by default (`-polly` under `opt`, or enabled at build time), runs before or after the classical pipeline, and its output is deliberately plain loops so the ordinary vectorizer finishes the job - see [Auto-Vectorization Internals](./auto-vectorization-deep.md) for that stage.

**Graphite** is GCC's counterpart: it also builds on isl, and its only user-visible entry point is `-floop-nest-optimize` (plus loop-interchange under related flags). It is more conservative than Polly - smaller SCoP window, fewer modeled statements - and it carries a build-time requirement the GCC installation docs state plainly: an "isl Library version 0.15 or later ... Necessary to build GCC with the Graphite loop optimizations" ([gcc.gnu.org/install/prerequisites.html](https://gcc.gnu.org/install/prerequisites.html)). Historically Graphite used CLooG for code generation and migrated to isl's AST generator, the same consolidation that swept the whole toolchain (Pluto, PPCG, Polly) onto isl.

| Aspect | Polly (LLVM) | Graphite (GCC) |
|---|---|---|
| Front-end analysis | SCEV + delinearization + AliasAnalysis | GCC data-dependence + region analysis |
| isl role | Domains, scheduling, AST generation | Scheduling, AST generation (via isl) |
| Default status | Off; `-polly` under `opt`, optional project | Off; `-floop-nest-optimize` at `-O3`+ |
| Strength | Full SCoP model, OpenMP + JIT hooks | Low maintenance cost, safe fallbacks |
| Failure mode | Bail-out to scalar pipeline | Bail-out to scalar pipeline |

## The Cost Side of the Ledger

The polyhedral model's trade is expressiveness for analysis expense, and every production decision in this space traces back to it. On the **win** side: dependence tests that are *complete* for affine code (no false dependences), transformations found rather than enumerated, and parallelism (wavefronts, tiles) that loop-by-loop passes structurally cannot see. On the **cost** side: SCoP detection rejects a large fraction of real code (the table above), each scheduling query is NP-hard-flavored, schedule construction can blow up on imperfectly-nested or many-statement regions, and code size grows with tiling bookkeeping. The practical consequence is a strict diet: polyhedral passes earn their keep on dense, regular, numeric kernels - exactly the 30 kernels of [PolyBench/C](https://github.com/MatthiasJReisinger/PolyBenchC-4.2.1) (LU, Cholesky, stencils, dynamic programming), the standard suite Polly, Graphite, and Pluto papers benchmark on - and mostly stand down elsewhere, leaving the cheap per-loop machinery (SCEV, the vectorizer) to do the volume work. A rule of thumb for interviews: *SCEV answers "what is this value at iteration k" in polynomial time per value; polyhedral scheduling answers "what is the best legal order for a whole nest" at NP-hard-flavored cost - and the former is a prerequisite for the latter, since without delinearization there is no model to schedule.*

## The Demo: Skewing a Stencil Into Parallel Waves

The classic example of the whole pipeline in miniature. The recurrence `A[i][j] = A[i-1][j] + A[i][j-1]` carries two dependences, `(1,0)` and `(0,1)`. Part 1 of the demo runs the dependence test as brute-force integer feasibility over the 36-point domain (an ILP solver replaces the nested loops in production). Part 2 shows that the naive parallelization (run each row's outer iterations in parallel) is illegal, and that skewing the schedule by `(i, j) -> (i, i+j)` - then interchanging - produces **wavefronts**: `max(i+j)` groups of iterations, zero same-wave dependences, 11 waves instead of 36 sequential steps.

```python
# Wavefront parallelization of a 2-D recurrence, the polyhedral way:
#   [1] dependence test  = brute-force integer feasibility over the domain
#   [2] schedules        = affine maps; skew (i,j) -> (i, i+j) then
#                          interchange yields parallel waves (i+j, i)
# Loop nest under study (N x N integer domain, pure ASCII math):
#     for i in 0..N-1:  for j in 0..N-1:
#         A[i][j] = A[i-1][j] + A[i][j-1]        # reads older cells only

N = 6
dom = [(i, j) for i in range(N) for j in range(N)]
D = set(dom)

def lex_before(a, b):                # lexicographic order on iteration vectors
    return a < b

def feasible(d):
    """True iff source p and sink p+d both lie in D with source lex-before."""
    pairs = 0
    for p in dom:
        q = (p[0] + d[0], p[1] + d[1])
        if q in D and lex_before(p, q):
            pairs += 1
    return pairs

reads = [((-1, 0), "A[i-1][j]"), ((0, -1), "A[i][j-1]"), ((-1, -1), "A[i-1][j-1] (hypothetical)")]
print("[1] dependence test: integer feasibility over the %d-point domain" % len(dom))
dists = []
for off, name in reads:
    d = (-off[0], -off[1])           # distance vector = -read offset
    n = feasible(d)
    dists.append(d)
    print("    read %-28s -> distance d=%-8s feasible: %-3s (%d sink/source pairs)"
          % (name, str(d), "yes" if n else "no", n))
zero = feasible((0, 0))
print("    same-iteration probe d=(0, 0)   feasible: %-3s (write and read never collide)"
      % ("yes" if zero else "no"))

def waves(f):
    b = {}
    for p in dom:
        b.setdefault(f(p), []).append(p)
    return [len(b[k]) for k in sorted(b)]

def legal(f):
    """Count true dependences landing in the SAME wave (illegal to parallelize)."""
    bad = 0
    for d in dists:
        for p in dom:
            q = (p[0] + d[0], p[1] + d[1])
            if q in D and f(q) == f(p):
                bad += 1
    return bad

orig = lambda p: p[0]                    # time = i   (row-sequential)
wavf = lambda p: p[0] + p[1]             # skew + interchange: wave = i+j

print("[2] schedules as affine maps (time vectors compared lexicographically)")
print("    original order (i, j)         : 36 sequential steps, width 1 (total order)")
print("    naive outer-parallel (time=i) : same-wave violations = %d -> illegal to parallelize"
      % legal(orig))
print("    skew (i,j) -> (i, i+j)        : (2,1) -> (2, 3)   legality kept, still sequential")
print("    skew + interchange, wave=i+j  : wave widths %s" % waves(wavf))
print("    same-wave violations, wave=i+j: %d -> every wave fully parallel" % legal(wavf))
w = waves(wavf)
makespan, work = len(w), len(dom)
print("    makespan %d waves vs %d sequential steps; max parallel width %d"
      % (makespan, work, max(w)))
print("    work-limited speedup bound: %d/%d = %.2fx" % (work, makespan, work / makespan))
```

Output (verbatim from the run above):

```text
[1] dependence test: integer feasibility over the 36-point domain
    read A[i-1][j]                    -> distance d=(1, 0)   feasible: yes (30 sink/source pairs)
    read A[i][j-1]                    -> distance d=(0, 1)   feasible: yes (30 sink/source pairs)
    read A[i-1][j-1] (hypothetical)   -> distance d=(1, 1)   feasible: yes (25 sink/source pairs)
    same-iteration probe d=(0, 0)   feasible: no  (write and read never collide)
[2] schedules as affine maps (time vectors compared lexicographically)
    original order (i, j)         : 36 sequential steps, width 1 (total order)
    naive outer-parallel (time=i) : same-wave violations = 30 -> illegal to parallelize
    skew (i,j) -> (i, i+j)        : (2,1) -> (2, 3)   legality kept, still sequential
    skew + interchange, wave=i+j  : wave widths [1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]
    same-wave violations, wave=i+j: 0 -> every wave fully parallel
    makespan 11 waves vs 36 sequential steps; max parallel width 6
    work-limited speedup bound: 36/11 = 3.27x
```

The picture behind those wave widths - each diagonal is one parallel wave:

```text
i (row, drawn upward)
 5 | 10  9  8  7  6  5
 4 |  9  8  7  6  5  4
 3 |  8  7  6  5  4  3
 2 |  7  6  5  4  3  2
 1 |  6  5  4  3  2  1
 0 |  5  4  3  2  1  0
   +---------------------  j (col)  ->  cell value = wave index i + j
```

Note what the solver did *not* need: it never enumerated schedules. The skew `(i, i+j)` and wave function `i+j` are affine maps; checking them against the two dependence polyhedra is the same feasibility test as in Part 1. That is the entire polyhedral value proposition in 36 integer points.

## Interview Angles

- **Why is dependence testing an ILP and not just algebra?** Because domains are constrained integer sets - asking whether two affine access functions can collide inside loop bounds is integer feasibility, which has no closed-form answer in general.
- **Where does Polly get its 2-D arrays from flat LLVM pointers?** SCEV delinearization; without it the access relations are not affine and the SCoP is rejected.
- **Why did skewing matter in the demo?** The unskewed order buries dependences inside waves; skewing aligns dependences with a single wave axis so the perpendicular dimensions become freely parallelizable (permutable bands).
- **When is polyhedral optimization a bad deal?** Irregular access (`a[b[i]]`), data-dependent control flow, sparse code - detection fails, and the analysis cost is paid for nothing. Sparse numeric and pointer-chasing code stays with scalar passes.
- **What do Pluto and isl's scheduler have in common?** Transformation *search as constrained optimization*: validity constraints per dependence, profitability objective, solver in the loop.

## References

1. Polly - Polyhedral optimization in LLVM, official documentation (The LLVM Project). <https://polly.llvm.org/docs/>
2. T. Grosser, A. Groesslinger, C. Lengauer. "Polly - performing polyhedral optimizations on a low-level intermediate representation." *Parallel Processing Letters* 22(4), 2012. DOI: [10.1142/S0129626412500107](https://doi.org/10.1142/S0129626412500107)
3. U. Bondhugula, A. Hartono, J. Ramanujam, P. Sadayappan. "A practical automatic polyhedral parallelizer and locality optimizer." *PLDI 2008*. DOI: [10.1145/1375581.1375595](https://doi.org/10.1145/1375581.1375595)
4. isl - Integer Set Library for the polyhedral model (S. Verdoolaege), official Inria repository. <https://gitlab.inria.fr/isl/isl>
5. PolyBench/C 4.2.1 benchmark suite (L.-N. Pouchet, T. Yuki; Ohio State), maintained mirror. <https://github.com/MatthiasJReisinger/PolyBenchC-4.2.1>
