# Data-Centric Query Compilation

A query plan is a program, and something has to run it. The classical answer - a tree of operator objects calling `next()` on each other once per tuple - spends more CPU on running the operators than on the data. Data-centric query compilation is the fix: cut the plan into pipelines at pipeline breakers, and compile each pipeline into one tightly nested loop over columns, where the tuples of the plan live in registers instead of on the heap. This is the MonetDB/X100 -> HyPer -> Umbra line of work, and it is also what Apache Spark's whole-stage codegen does on the JVM. This page covers why interpretation is expensive, the produced code shape, how compile time and plan reuse are managed, and the adaptive compromise Umbra ships.

## Why plans get interpreted at all

A SQL engine must handle queries it has never seen, so the plan cannot be a compiled binary shipped with the product. Three ways to bridge the gap between "plan as data" and "plan as code":

1. **Interpret** - an operator tree walks over tuples at runtime (Volcano iterator model). Flexible, zero preparation, per-tuple overhead.
2. **Compile per query** - treat the plan as an IR, emit machine code for it, execute the code (HyPer, Umbra). Fast execution, pays codegen cost per plan.
3. **Precompile templates** - generic compiled loops with a small interpretation layer for the varying parts (expression trees evaluated by a VM). The middle ground many engines actually ship.

The plan still needs a data representation (for optimization, caching, and prepared statements); compilation is an *extra* stage after optimization, not a replacement for it. The optimizer picks the plan - see [Cascades Optimizer](./cascades-optimizer.md) - and the compiler turns the winning physical plan into code.

## MonetDB/X100: measuring the interpretation tax

The motivation is a profile. The MonetDB/X100 paper (CIDR 2005) profiled a full-scan aggregation query in a row-at-a-time system and showed that the CPU spent the overwhelming majority of its cycles on per-tuple interpretation machinery - operator calls, tuple copies, branchy dispatch - rather than on the data. Their fix, vectorized execution, attacks the per-tuple part: process a batch (a "vector") per `next()` call so the fixed cost is amortized. That model and its trade-offs are covered in [Vectorized Execution](./vectorized-execution.md); X100's deeper insight is that *cache-resident columnar data plus a tight loop* is the shape the hardware wants. The compilation line of work takes that shape literally: instead of interpreting a loop over a batch, emit the loop itself.

## Data-centric execution: operators become loop fragments

Neumann (PVLDB 2011) formulated data-centric execution: **an operator does not pull tuples from its child; it produces a materialized intermediate result that the parent consumes inside its own loop**. This "for-loop pushing" inverts Volcano. The query is first split at pipeline breakers - operators that must see all input before producing output (hash join build side, sort, aggregation finalize). Each pipeline is translated into machine code as a set of nested loops over the columns of its inputs.

```text
Physical plan                Pipeline split (breaker = hash-join build side)
   HashJoin
   /      \                  P0 (build):  Scan(orders)             -> hash table
Scan(orders) \               P1 (probe):  Scan(lineitem) -> Filter(v>10)
   Filter(v>10)                           -> probe ht -> Project -> output

Emitted code shape - one flat function per pipeline, no per-tuple calls:

  P0:  for r in orders:          P1:  for r in lineitem:
         ht[r.key] = r.price            v = r.value
                                        if v > 10 and r.key in ht:
                                            emit(v * ht[r.key])
```

Inside a pipeline the "tuple" is not an object - it is a set of scalar variables holding the currently streamed values. The compiler's register allocator turns those variables into registers, which is why the model is called register-local tuples. Consequences:

- **Zero virtual dispatch** on the hot path: no `next()` calls, no vtable indirection, and the CPU's branch predictor and inliner see straight-line loop bodies.
- **Specialization on constants**: a literal like `v > 10` compiles to an immediate compare; a parameterized predicate can be specialized per value (see "peeling" below).
- **Materialization only at breakers** (and at the pipeline output): late materialization of whole rows becomes a deliberate choice instead of an accident of the tuple representation.

## HyPer: compiling the plan to machine code with LLVM

HyPer (Kemper & Neumann, ICDE 2011) is the system that made per-query compilation practical: a main-memory hybrid OLTP&OLAP engine where analytical queries are compiled to native machine code, while transactional consistency is handled separately with virtual-memory snapshots. The compilation technique is the PVLDB 2011 paper above: plans go to LLVM IR ([language reference](https://llvm.org/docs/LangRef.html)), LLVM's optimizer runs over the IR, and the result is cached as machine code.

Why LLVM rather than emitting C and invoking gcc?

| Requirement | What LLVM gives the engine |
|---|---|
| Compile time | IR generation is in-process; a query compiles in milliseconds, no external toolchain spawn |
| Portability | One IR, many targets (x86, ARM); the engine carries no per-architecture code emitters |
| Optimization | Reuses mature passes (inlining, vectorization, register allocation) instead of reimplementing them |
| Control | The engine decides which IR to emit, so the loop shape survives to machine code |

The pipeline breaker is the only place where data slows down: the hash table build materializes one side, and the probe loop streams the other side through registers. Long analytical queries dominate the cost, so the one-time compile (milliseconds) is paid back after roughly the first microsecond-scale slice of execution.

## Spark Tungsten: whole-stage codegen on the JVM

Spark SQL shows the same idea forced through a different runtime. Early Spark SQL already generated Java bytecode for *expressions* via Catalyst (described in the SIGMOD 2015 paper) - but operators were still Volcano-style iterators, and the JVM's inability to inline across operator boundaries kept per-tuple call overhead high. Tungsten's **whole-stage code generation** fuses the operators of a pipeline into a single Java function: the planner inserts a `WholeStageCodegen` node, and each operator in that subtree contributes its loop fragment to one generated source string, compiled by the JVM's own compiler (see Spark's [performance tuning docs](https://spark.apache.org/docs/latest/sql-performance-tuning.html) for the operator-fusion description).

Differences from HyPer worth knowing for interviews:

- Spark emits **Java source and lets the JVM JIT it**; HyPer emits LLVM IR and controls the backend. Spark inherits JVM JIT warmup and deoptimization behavior (see [Deoptimization and OSR](../../compilers/advanced/deoptimization-osr.md)).
- Spark still materializes `UnsafeRow` at pipeline boundaries; HyPer materializes only at breakers and for output.
- The generated code is cached per plan version; a plan change (new optimizer output) invalidates the cached generated classes.

## The demo: pull interpreter vs fused loop

The Python below builds the same tiny column-store plan twice: once as a Volcano pull-model interpreter (generator-based `next()` protocol, tuple tuples materialized per step) and once through a code generator that emits a fused loop and compiles it with CPython's own compiler - the same structural step LLVM performs for HyPer, at interpreter scale. Counted ops are deterministic; no wall clock is involved.

```python
# Volcano pull interpreter vs data-centric fused loop over a tiny column store.
# Query: SELECT lineitem.value * orders.price FROM lineitem JOIN orders
#        ON lineitem.key = orders.key WHERE lineitem.value > 10
# Deterministic op-count model: d = control dispatches (next() calls vs flat
# loop iterations), t = intermediate tuple objects materialized.

lk = [(i % 8) + 100 * (i // 8) for i in range(4000)]   # lineitem.key
lv = [15, 3, 22, 8, 40, 7, 12, 31] * 500               # lineitem.value
ok = [(i % 6) + 100 * (i // 6) for i in range(120)]    # orders.key
op = [100, 200, 300, 400, 500, 600] * 20               # orders.price

# ---- Volcano interpreter: pull model, one next() call per tuple ----------
def scan(c1, c2):
    i = 0
    while True:
        st["d"] += 1
        if i >= len(c1):
            return None
        st["t"] += 1                       # row tuple materialized
        r = (c1[i], c2[i]); i += 1
        yield r

def filt(child, pred):
    while True:
        st["d"] += 1
        for r in child:                    # pulls one tuple per call
            if pred(r):
                yield r
                break
        else:
            return

def join(build, probe):
    ht = {}
    for k, v in build:                     # pipeline breaker, built once
        st["t"] += 1; ht[k] = v
    while True:
        st["d"] += 1
        for r in probe:
            st["t"] += 1
            if r[0] in ht:
                yield r, ht[r[0]]; break
        else:
            return

def run_interpreted():
    p = join(scan(ok, op), filt(scan(lk, lv), lambda r: r[1] > 10))
    return sum(r[1] * pv for (r, pv) in p)  # project folded into the driver

# ---- Data-centric: codegen emits one fused function per pipeline ---------
SRC = '''
def run_compiled(lk, lv, ok, op, st):
    ht = {}
    for j in range(len(ok)):               # pipeline 0: build (breaker)
        st["d"] += 1; st["t"] += 1; ht[ok[j]] = op[j]
    out = 0
    for i in range(len(lk)):               # pipeline 1: scan+filter+probe+
        st["d"] += 1                       # project fused into one flat
        k, v = lk[i], lv[i]                # loop over column arrays; values
        if v > 10 and k in ht:             # stay in locals (registers)
            out += v * ht[k]
    return out
'''

def run_compiled():
    ns = {}
    exec(compile(SRC, "<fused>", "exec"), ns)   # compile once per plan
    return ns["run_compiled"](lk, lv, ok, op, st)

for tag, fn in (("interpreted", run_interpreted), ("compiled", run_compiled)):
    st = {"d": 0, "t": 0}
    r = fn()
    print("%-12s result=%d dispatches=%6d tuples=%5d" % (tag, r, st["d"], st["t"]))
print()
print("--- emitted source (codegen output) ---")
print(SRC.strip())
```

Real output (both sides compute the identical aggregate, 562000, verified independently):

```text
interpreted  result=562000 dispatches=  6684 tuples= 6740
compiled     result=562000 dispatches=  4120 tuples=  120

--- emitted source (codegen output) ---
def run_compiled(lk, lv, ok, op, st):
    ht = {}
    for j in range(len(ok)):               # pipeline 0: build (breaker)
        st["d"] += 1; st["t"] += 1; ht[ok[j]] = op[j]
    out = 0
    for i in range(len(lk)):               # pipeline 1: scan+filter+probe+
        st["d"] += 1                       # project fused into one flat
        k, v = lk[i], lv[i]                # loop over column arrays; values
        if v > 10 and k in ht:             # stay in locals (registers)
            out += v * ht[k]
    return out
```

Read the numbers honestly. Dispatch count drops ~39%, but tuple materialization drops ~98% (6740 -> 120): every interpreter step built a heap tuple where the fused loop keeps `k, v` in locals. In CPython, dispatch itself is just a bytecode op, so the dispatch gap looks small; in machine code, each eliminated `next()` call is an indirect call plus a lost inlining opportunity, which is why compiled HyPer pipelines reach near-peak CPU throughput while a Volcano interpreter typically achieves well under 1% of peak (the comparison table in [Execution Engines](./execution-engines.md) summarizes the three models).

## Compile time, warmup, and prepared plans

Compilation shifts cost from *every tuple* to *the first execution of a plan*. Managing that shift is most of the engineering:

| Strategy | First-run cost | Steady state | Failure mode |
|---|---|---|---|
| Interpret always | none | slowest per tuple | overhead scales with data |
| Compile per query (HyPer) | ms of codegen | near-peak | short queries pay compile for little gain |
| Prepared / reusable plans | compile once at PREPARE | fast, amortized over re-executions | code cache invalidation on DDL or plan change |
| Adaptive specialized + general (Umbra) | compile two variants | fast, self-correcting | double codegen memory |

- **Prepared statements become genuinely prepared**: parse, optimize, and compile once; later executions pass parameter values as runtime arguments to cached machine code. HyPer additionally *peels* literals - if a parameter was bound to a constant at compile time, the code is specialized for it, and recompilation happens only when the value distribution makes it worthwhile.
- **JIT warmup** is the same phenomenon as in language runtimes: the first executions of a plan pay codegen (and in Spark's case, JVM profiling/compilation tiers), later ones run at full speed. Long analytics amortize instantly; OLTP point queries may never amortize, which is why engines keep an interpreter or expression-VM fallback for trivial plans.
- **Code cache coherence**: compiled code embeds schema assumptions (column offsets, types). DDL that changes those offsets must invalidate the code, exactly like a CPU cache invalidated by a self-modifying store.
- **Umbra** (Neumann & Freudenreich, CIDR 2020), HyPer's successor, keeps the compiled data-centric model, adds a buffer manager so data exceeds RAM, and runs morsel-driven parallelism over compiled pipelines. Its adaptive execution (Kohn et al., ICDE 2018) compiles both a *specialized* plan for the predicted selectivity and a *general* plan, starts with the specialized code, and switches to the general one if runtime statistics contradict the prediction - removing the classic compiled-engine fear that a wrong cardinality estimate bakes a bad loop into machine code (see [Learned Query Optimization](./learned-query-optimization.md) for the estimation side).

## Interview angles

- **Explain the produced code shape.** Draw the pipeline split at the hash-join build, then write the two nested loops - values in locals, no operator calls, materialization only at the breaker. This one sketch separates candidates who know the model from those who only know the buzzword.
- **Why does vectorized execution still exist if compilation is faster?** Compilation gives per-tuple peak speed but pays per-plan codegen; vectorization gets most of the win with zero codegen and simpler fallbacks, and hybrid engines (DuckDB-style vectorized outer loop, compiled inner loops) combine both.
- **What goes wrong when the optimizer's estimate is wrong?** With compiled plans the mistake is baked into specialized machine code; the mitigation is Umbra's dual compilation with runtime switching, or plan invalidation and recompilation - connecting this page to cardinality estimation.

## Related pages

- [Execution Engines](./execution-engines.md) - the survey-level view of interpreter, vectorized, and compiled models
- [Vectorized Execution](./vectorized-execution.md) - the batch interpretation alternative X100 introduced
- [Cascades Optimizer](./cascades-optimizer.md) - where the physical plan that gets compiled comes from
- [Learned Query Optimization](./learned-query-optimization.md) - the estimation problem adaptive compiled execution defends against

## References

- Zukowski, Heman, Boncz. "MonetDB/X100: Hyper-Pipelining Query Execution." CIDR 2005. https://www.cidrdb.org/cidr2005/papers/P19.pdf
- Neumann. "Efficiently Compiling Efficient Query Plans for Modern Hardware." PVLDB 4(9), 2011. https://doi.org/10.14778/2002938.2002940 (ACM blocks direct fetch; verified via Crossref)
- Kemper, Neumann. "HyPer: A Hybrid OLTP&OLAP Main Memory Database System Based on Virtual Memory Snapshots." ICDE 2011. https://doi.org/10.1109/ICDE.2011.5767867 (verified via Crossref; note the often-cited 10.1109/ICDE.2011.5747480 is a different/non-resolving DOI)
- Armbrust et al. "Spark SQL: Relational Data Processing in Spark." SIGMOD 2015. https://doi.org/10.1145/2723372.2742797 (verified via Crossref; ACM blocks direct fetch) - plus Apache Spark docs on whole-stage codegen: https://spark.apache.org/docs/latest/sql-performance-tuning.html
- Neumann, Freudenreich. "Umbra: A Disk-Based System with Efficient Memory Access." CIDR 2020. https://www.cidrdb.org/cidr2020/papers/p29-neumann-cidr20.pdf
