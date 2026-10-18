# Compilers of Intent: Query Planners, Optimization Passes, and Dataflow DAGs

## Overview

A C compiler turning `-O2` loose on SSA IR, a Postgres planner choosing between a hash join and a nested loop, a Flink job graph scheduling operators across task slots, and Bazel scheduling 40,000 actions on a build cluster are all answers to the same question: *given a declarative statement of WHAT is wanted, choose a HOW that runs efficiently as a plan over a DAG.* In each case the input is intent, the output is an executable DAG of steps, and in between sits an optimizer: a set of correctness-preserving rewrites plus (sometimes) a cost model that picks among alternatives. The differences are in how good the cost model can be — and that is where each system's characteristic failure lives.

This page explains the four sides independently, names the shared principle, and works one query planned two ways with numbers — including the classic "statistics said 1 row, there were 1,000,000" plan flip.

## The Concepts, Independently

**Compiler optimization passes.** A compiler lowers source to an intermediate representation — today, usually SSA form, where every variable is assigned once, which makes data flow explicit ([../../compilers/advanced/ssa-form.md](../../compilers/advanced/ssa-form.md)). Over this IR it runs passes: *analyses* prove facts (this expression is loop-invariant; this branch is dead; this pointer cannot alias that one) and *transforms* exploit them (constant folding, dead-code elimination, loop-invariant code motion, vectorization — see [../../compilers/scalar-optimizations-deep.md](../../compilers/scalar-optimizations-deep.md) and [../../compilers/loop-optimizations-deep.md](../../compilers/loop-optimizations-deep.md)). Two properties define the game: every transform must preserve observable semantics, and the program text is *static* — the optimizer can reason about the code forever, but it cannot know the data ("which branch is taken more often") without profiling, which is why profile-guided optimization exists as a patch ([../../compilers/advanced/profile-guided-optimization.md](../../compilers/advanced/profile-guided-optimization.md)).

**The SQL query planner.** SQL is the most successful declarative language in production: you state the result, not the algorithm. The planner parses to a logical plan (relational algebra), applies heuristic rewrites (predicate pushdown, projection pruning, subquery flattening), then performs *cost-based search* over join orders and access paths: a cost model combines per-operator costs with cardinality estimates derived from statistics (row counts, distinct counts, histograms, most-common values) — see [../../dbms/query-planner.md](../../dbms/query-planner.md), [../../dbms/query-processing/cost-estimation.md](../../dbms/query-processing/cost-estimation.md), and [../../dbms/advanced/volcano-optimizer.md](../../dbms/advanced/volcano-optimizer.md). The optimizer is a *program optimizer with a cost model the compiler world mostly lacks*, and it optimizes a program whose "input data" is the entire database, described by statistics that go stale.

**Stream-processing DAGs (Flink/Beam).** A streaming job is a logical graph of operators (source → map → keyBy/window → aggregate → sink) that the runtime compiles into an execution graph with parallelism per operator, operator chaining (fusing adjacent operators into one thread — a peephole optimization), and placement decisions ([../../data-engineering/flink.md](../../data-engineering/flink.md)). The query never ends, so the "plan" must also schedule *state*: which operator holds which keyed state, how windows buffer, how watermarks order event time ([../../data-engineering/stream-processing.md](../../data-engineering/stream-processing.md), [../../data-engineering/apache-beam.md](../../data-engineering/apache-beam.md)). Rewrites look familiar: push filters before shuffles, fuse operators, choose what to pre-aggregate.

**Build-system scheduling.** make/Bazel read a declared dependency graph (targets and rules) and schedule the dirty subgraph topologically, maximizing parallelism ([./dependency-resolution.md](./dependency-resolution.md)). There is essentially *no* cost model and no plan search — the "optimizer" answers only what must run and in what order — but the skeleton is identical: declarative dependencies → DAG → execution engine that caches (memoizes) results keyed by inputs ([../../software-engineering/build-systems.md](../../software-engineering/build-systems.md)).

## The Shared Principle

**Declarative intent is compiled into an executable DAG, and an optimizer chooses the plan: correctness-preserving rewrites shrink the search space, a cost model (when present) ranks the survivors.** The rewrite that best shows the family resemblance is *filter early*: predicate pushdown in a planner (apply `WHERE` before the join), constant folding and dead-branch elimination in a compiler (compute and discard before the loop), filter-before-shuffle in Flink/Beam SQL (filter at the source, not after the network hop), and "don't rebuild what didn't change" in a build system. All four are the same algebraic move — *reduce the volume flowing through expensive downstream operators* — and all four are justified by the same algebra, not by measurement.

The second shared mechanism is the compile-time/run-time split: all four pay an upfront cost (optimization, planning, DAG construction) to make repeated execution cheaper, and all four cache the compiled artifact (plan cache, job graph, build cache) — importing the same invalidation question, answered by statistics drift in the planner, source changes in the compiler, and input-hash changes in build systems.

## Where the Analogy HOLDS and BREAKS

| Property | HOLDS across compilers, planners, stream DAGs, build schedulers | BREAKS |
|---|---|---|
| Logical/physical separation | IR vs machine code; algebra vs plan; job graph vs execution graph; target graph vs action graph | Only the planner has a *cost model* over physical alternatives; make has none (order + parallelism only), compilers rank some alternatives but rarely search exponentially |
| Correctness-preserving rewrites | Predicate pushdown ≈ constant folding ≈ filter-before-shuffle ≈ skip-unchanged | Compiler rewrites are verified against semantics; planner rewrites must also respect SQL's three-valued logic and NULL corner cases, where several "obvious" rewrites are unsound |
| Plan choice depends on data | PGO approximates it for compilers | The planner's "program semantics" is *fine* — but its *performance* depends on data distributions that mutate at runtime; a compiler never faces input that changes the meaning of its cost model mid-flight |
| Enumeration of alternatives | Join-order search is dynamic programming over an exponential space, like instruction scheduling | Cascades-style memo search (planner) has no common analog in build systems, which never choose between plans |
| Cached plans get invalidated | Plan cache, PGO profiles, incremental build state | Streams add a novel constraint: state (window buffers) is part of the "plan," and rescaling changes key ownership, forcing state migration a compiler never imagines |

The deepest break: **compilers optimize a static program; planners estimate a dynamic one.** The compiler's model of the program is exact (the text is given); the planner's model of the data is a *guess from statistics that were sampled at some past moment*. Every structural claim about the optimizer transfers; the reliability of the cost model does not. The second break is time itself: stream systems add event-time/window semantics, so "the query" has no fixed output — a plan is also a *state-management policy*, a dimension with no compiler analog.

## A Concrete Worked Example

**One query, two plans.** Schema: `orders` (10M rows), `users` (1M rows). Query:

```sql
SELECT u.name, o.total
FROM orders o JOIN users u ON o.user_id = u.id
WHERE u.country = 'DE' AND o.amount > 100;
```

Statistics (accurate): `users.country = 'DE'` selects 10,000 rows (1%); `orders.amount > 100` selects 5,000,000 rows (50%); each user has ~10 orders on average.

- *Plan A — join first, filter after:* hash join builds on `users` (1M rows, ~20 MB), probes with 10M orders, emitting ~10M joined rows; then filter `country` and `amount`. Work: probe 10M rows, materialize ~10M intermediates, then discard ~99% of them. Network shuffle (if distributed): ~10M rows through the join stage.
- *Plan B — push down, then join:* filter `users` first → 10K rows; filter `orders` first → 5M rows; hash join builds on the 10K-row side. The 10 orders-per-user average means the 10K German users own ~100K orders, so the join emits ~100K rows. Work: 5M + 10K row touches; shuffle ~5M rows; build side 200× smaller.

Same result, ~2× less shuffle, ~100× less join-build memory, ~100× smaller intermediate set. Predicate pushdown did not "optimize the code" — it shrank the data the expensive operator had to see. That is the constant-folding move wearing a database's clothes.

**The classic disaster: stale statistics flip the plan.** Now suppose the histogram on `users.country` was last sampled before the German market launch: the planner estimates `country = 'DE'` matches **1 row**. With that estimate, the planner reasons: "filter users to 1 row, then for that one user, probe `orders` by index" — a nested-loop plan whose estimated cost is tiny. Reality: 10,000 German users × 10 orders each; the nested loop executes 100K index probes and re-binds parameters per row while the hash join would have built once. The plan is not wrong *structurally* — it is wrong *for a data distribution the planner did not know about*. Estimated 1 row, actual 100K: a 5-order-of-magnitude cardinality error, which is why production runbooks prescribe `ANALYZE` after bulk loads, plan guards, and adaptive execution that re-plans mid-query when estimates and reality diverge ([../../dbms/advanced/cardinality-estimation.md](../../dbms/advanced/cardinality-estimation.md), [../../dbms/internals/adaptive-query-execution.md](../../dbms/internals/adaptive-query-execution.md)).

**The same two moments in the other systems.** The compiler's version of "stale statistics" is a mispredicted branch or a profile captured on different inputs — annoying, not catastrophic, because semantics never depended on the guess. The stream version is worse than either: choose parallelism 8 for a keyed window aggregate and a hot key puts 90% of state on one subtask — the cost model was right about volume and wrong about skew, and the "query" runs forever, so the mistake compounds every second. The build system, with no cost model, fails differently: it cannot choose a better plan at all, only refuse stale ones — which is why build optimization is about *invalidation precision* (see [./incremental-computation.md](./incremental-computation.md)).

## When This Connection Is Useful

- **Reading `EXPLAIN ANALYZE` like a compiler person.** Estimated rows vs actual rows is the IR-vs-reality gap; plan flips after `ANALYZE` are recompiles triggered by profile drift. Engineers who see plans as "compiled intent with a cost model" debug them faster and know the levers: statistics, access paths, rewritten SQL, plan hints.
- **Interview: "why is my query slow?"** The senior-shaped answer names the mechanism, not the symptom: cardinality misestimate → wrong join order/access path → plan chosen from a stale cost model. Then the fix menu: refresh statistics, restructure the query to be estimate-robust, index to change the access-path set, or force a plan — each mapping to the compiler-world concept (better profile, simpler IR, different lowering, pragma).
- **Engineering decisions.** Trust declarative interfaces (SQL, build graphs, stream topologies) *because* an optimizer can improve them without rewriting callers — but budget for the cost model's blind spots: skew, staleness, and time semantics. In stream systems, design topology for state placement first; the planner's freedom is smaller than batch SQL's, and rescaling is a first-class plan event.

## Interview Questions

1. Rewrite one SQL query three ways (subquery form, join form, CTE form) and explain why the planner may compile all three to the same plan — and give a case where it provably cannot.
2. Predicate pushdown, constant folding, and filter-before-shuffle: state the shared algebraic justification in one sentence, and explain why all three shrink *downstream* work rather than upstream work.
3. Statistics say 1 row; there are 1,000,000. Walk through exactly which plan property flips, why the plan was locally rational given the estimate, and three defenses ordered by invasiveness.
4. Why can a build system be correct with no cost model while a database planner cannot? What question does the planner answer that `make` never asks?
5. A Flink job has a keyed window aggregate with a hot key. Explain the failure in plan/cost terms (not "it's slow") and give two plan-level mitigations, including their state-management cost.

## Key Takeaways

- Declarative intent → optimizer → executable DAG is one shape shared by compilers, SQL planners, stream-processing runtimes, and build systems; they differ mainly in how much search and what cost model they can afford.
- Filter-early rewrites (predicate pushdown ≈ constant folding ≈ filter-before-shuffle) are the same algebraic move: shrink the volume seen by expensive downstream operators.
- The planner is a compiler whose input distribution mutates under it: cardinality misestimates are the characteristic failure, and stale statistics flip plans that were locally rational.
- Stream systems add time: plans include state placement and windowing, so "optimization" includes state management, and hot keys are skew failures the cost model must anticipate.
- Build systems sit at the minimal end of the spectrum — no cost model, just invalidation and topological scheduling — which isolates exactly what the others gain from their optimizers.

## Cross-References

- [./dependency-resolution.md](./dependency-resolution.md) — Dependency Resolution — the build-system DAG, topological scheduling, and invalidation on the reversed graph.
- [./incremental-computation.md](./incremental-computation.md) — Incremental Computation — cached plans and memoized results as one mechanism.
- [../../dbms/query-planner.md](../../dbms/query-planner.md) — The Query Planner — parsing, planning, and plan selection in one page.
- [../../dbms/query-processing/cost-estimation.md](../../dbms/query-processing/cost-estimation.md) — Cost Estimation — the cost model and its inputs.
- [../../dbms/advanced/volcano-optimizer.md](../../dbms/advanced/volcano-optimizer.md) — The Volcano Optimizer — equivalence classes and dynamic-programming search.
- [../../dbms/advanced/cardinality-estimation.md](../../dbms/advanced/cardinality-estimation.md) — Cardinality Estimation — statistics, histograms, and misestimate anatomy.
- [../../dbms/internals/adaptive-query-execution.md](../../dbms/internals/adaptive-query-execution.md) — Adaptive Query Execution — re-planning when estimates meet reality.
- [../../compilers/README.md](../../compilers/README.md) — Compilers Track — front/middle/back-end organization.
- [../../compilers/advanced/ssa-form.md](../../compilers/advanced/ssa-form.md) — SSA Form — the IR that makes data flow explicit.
- [../../compilers/scalar-optimizations-deep.md](../../compilers/scalar-optimizations-deep.md) — Scalar Optimizations — constant folding, DCE, and friends.
- [../../compilers/advanced/profile-guided-optimization.md](../../compilers/advanced/profile-guided-optimization.md) — Profile-Guided Optimization — the compiler's patch for missing data statistics.
- [../../data-engineering/flink.md](../../data-engineering/flink.md) — Apache Flink — job graph, chaining, and stateful stream execution.
- [../../data-engineering/stream-processing.md](../../data-engineering/stream-processing.md) — Stream Processing — event time, windows, and watermarks.
- Selinger, P. et al., "Access Path Selection in a Relational Database Management System," SIGMOD 1979 — the founding cost-based optimization paper (System R).
- Graefe, G., "Query Evaluation Techniques for Large Databases," ACM Computing Surveys, 1993 — the standard survey of planner architecture.
- Akidau, T. et al., "The Dataflow Model," VLDB 2015 — unbounded-data semantics behind Beam/Flink windowing.
