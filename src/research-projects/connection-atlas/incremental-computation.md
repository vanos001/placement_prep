# Recompute Only What Changed: Builds, Spreadsheets, Compilers, Views, React

## Overview

A 40,000-target Bazel build, an Excel spreadsheet, an incremental compiler, a database materialized view, and a React application are five answers to one engineering question: *the world changed a little — why would you recompute everything?* Each stores the results of past computation, records which inputs each result depended on, and on a change walks only the invalidated region of the dependency graph. The shared recipe has exactly three ingredients — a dependency graph, dirty propagation from changed inputs, and memoized results keyed on those inputs — and every bug in every one of these systems is a bug in one of the three ingredients: a missing edge, a dirty mark that never propagated, or a memo that outlived its justification.

This page explains the five sides independently, names the shared principle, works the arithmetic of changing one header file in a 10,000-file build with and without dependency tracking, prices a materialized-view refresh, and identifies where each system's invalidation is deliberately over-approximated — and what that costs.

## The Concepts, Independently

**Build systems (make/Bazel).** A build declares a graph: targets depend on sources and on other targets' outputs. make checks whether prerequisites are newer than the target (file timestamps) and rebuilds the stale subgraph topologically; Bazel and friends replace timestamps with content-hash cache keys, so "stale" means "some input's hash differs from the recorded one" ([../../linux/compilers/make.md](../../linux/compilers/make.md), [../../software-engineering/build-systems.md](../../software-engineering/build-systems.md), [../../supply-chain/bazel-build-graphs.md](../../supply-chain/bazel-build-graphs.md)). The scheduling question (what order, how parallel) is [./dependency-resolution.md](./dependency-resolution.md)'s territory; here the question is *membership*: which nodes are dirty?

**Spreadsheet recalculation.** The original incremental engine: each cell's formula declares its dependencies syntactically (the cell references it contains), so the dependency graph is *exact* by construction. Edit one cell; the engine marks its transitive dependents dirty and recomputes them in topological order, skipping everything untouched. Spreadsheet users get interactive latency on million-cell models precisely because invalidation is per-cell and automatic.

**Incremental compilers.** rustc runs as a query system: every compiler operation is a query memoized on disk, tagged with the hashes of the queries it depended on. After an edit, a query is "green" (reused) if its own input hash and all its dependencies are green — recomputation follows the changed region through the compiler's own DAG, which is what turns a 30 s crate rebuild into a 200 ms keystroke-to-diagnostic loop ([../../languages/rust/rustc-internals.md](../../languages/rust/rustc-internals.md)). The soundness requirement is brutal and instructive: a missed dependency edge means the compiler emits stale-but-plausible output — "clean lies" — so query systems make edges explicit *by construction* rather than by convention. The same discipline reappears in JITs from the other side: when an optimization's assumption breaks (a class is subclassed after all), the VM deoptimizes compiled code — invalidation of memoized machine code ([../../compilers/jit-compilation.md](../../compilers/jit-compilation.md)).

**Materialized views.** A materialized view is a memoized query result stored in the database. Refresh is the invalidation decision: full refresh re-runs the query (correct, O(query)); incremental view maintenance (IVM) applies only the deltas the base tables received, propagating inserts/updates/deletes through the view's algebra into the stored result ([../../dbms/advanced/incremental-view-maintenance.md](../../dbms/advanced/incremental-view-maintenance.md)). IVM is incremental computation with a twist: the "dependency graph" is the query plan, and deltas are *transformed*, not just recomputed.

**React re-renders.** A component is a function from props/state to UI; setState marks the component dirty; React re-renders the dirty subtree and diffs the resulting element trees against the previous ones, touching only the changed DOM nodes ([../../frontend/react-internals.md](../../frontend/react-internals.md)). The memoization boundaries (`memo`, `useMemo`, `useCallback`) are programmer-placed dependency declarations: they say "skip re-running this function unless these inputs change." React's model is deliberately coarser than a spreadsheet's — it invalidates the whole subtree under a state change and relies on diffing to keep the *write* cost small.

## The Shared Principle

**Recompute only what a change invalidates: dependency graph + dirty propagation + memoized results.** Formally, every system maintains a mapping from nodes (targets, cells, queries, components, view rows) to cached values, plus a graph of "node depends on nodes." A change marks changed nodes dirty; dirt propagates along edges (forward, from inputs to dependents); a recompute pass evaluates dirty nodes in topological order, and each node's evaluation either reuses its memo (if nothing it depends on actually changed) or recomputes and re-records. All five systems implement this loop; they differ in three dials:

- **Dependency precision.** Spreadsheet cells: exact (syntactic). rustc queries: exact (tracked). Bazel: exact per action, coarse per glob. make with header deps: exact once generated; without: catastrophically wrong. React subtree: over-approximated (parent state invalidates children that did not read it). Matviews: exact in theory, hand-maintained in many engines.
- **Key of the memo.** File timestamp (make), content hash (Bazel, rustc), cell address (spreadsheets), plan + base-table deltas (IVM), identity + props (React).
- **Who declares the edges.** Compiler queries: the language runtime tracks them. Build files: the human writes them (and forgets them — see the worked example). React: a hybrid (automatic subtree invalidation, manual memo escape hatches). Spreadsheets: the formula language tracks them, invisibly, correctly.

The dials explain the historical feel of each tool: make feels fragile because edges are human-declared and keys are timestamps; Bazel feels safe but slow to bootstrap because keys are hashes of everything; spreadsheets feel magical because the language derives exact edges for free.

## Where the Analogy HOLDS and BREAKS

| Property | HOLDS (all five) | BREAKS |
|---|---|---|
| DAG of dependencies | All require acyclicity for the recompute order to exist | Systems handle cycles differently: spreadsheets refuse them (or iterate to fixpoint); build systems reject or break ties; React "cycles" (render → state → render) are legal but hand-throttled |
| Dirty propagation is monotone | One changed input dirties all transitive dependents, always | Over-approximation is the norm, not the exception: make dirties on *timestamp*, not content; React dirties whole subtrees; the art is bounding the over-approximation's cost |
| Memo reuse is keyed on inputs | Content-hash keys make reuse verifiable; timestamp keys make it probable | "Clean lies" are the failure mode of every weak key: a build that is up-to-date by timestamp but wrong by content; a memo whose real dependency was undeclared |
| Invalidation is automatic | The engine, not the user, walks the graph | Except the edges themselves: in build systems the human wrote the graph, and a forgotten header dependency produces the classic "works on my machine" — automation of propagation cannot rescue a wrong graph |
| Cost model | Recompute cost ≈ size of the changed region's forward cone | React pays diffing even for memoized regions; IVM pays delta-join costs that can exceed full refresh for churn-heavy views; incremental compilers pay hashing/serialization overhead per run |

The deepest break: **incrementality is a soundness bet on the dependency graph.** Full recomputation is the only zero-assumption strategy; every incremental scheme asserts "these are ALL the dependencies," and the assertion is only as good as its enforcement. Spreadsheets and query engines enforce it by construction (the language is the graph); build systems and UI frameworks enforce it by convention and tooling — which is why the industry keeps reinventing content-hash keys (Bazel, rustc, Turborepo) as the enforcement mechanism of choice.

## A Concrete Worked Example

**Changing one header in a 10,000-file C++ build.** Assume 1 s per translation unit (TU), so a clean build is 10,000 s ≈ 2.8 h serial (~6 min on 32 cores). The change: edit `core/config.h`, which 200 TUs include (directly or transitively).

- *Proper dependency tracking (compiler-generated `-MMD` header deps, content-hash keys):* exactly the 200 dependent TUs recompile — 200 s serial, ~7 s on 32 cores; the other 9,800 results are memoized. This is the correct forward cone: 2% of the build.
- *No dependency tracking (naive make):* make compares timestamps of the `.o` files against the `.c` sources only; the header never appears as a prerequisite. Result: **0 files rebuild** — the linker happily produces a binary mixing old and new definitions of the config constants. The build says "up to date" and lies: the clean-lie failure, caused by a missing edge in the human-declared graph. This exact bug is why every real C build system generates header dependencies mechanically (`-MMD`/depfiles) instead of trusting programmers to list them.
- *Over-approximation instead (touch-based tooling, or `make clean`):* 10,000 TUs recompile — the full 2.8 h. Over-approximating "everything might depend on the header" is *sound* (no stale outputs) but converts a 2% change into a 100% rebuild.
- *Content-hash keys close the loop:* record for each TU the hash of its inputs (sources + headers + flags); a teammate with a warm remote cache replays the 9,800 unchanged TUs from cache and compiles only the 200 — and the "same content, different timestamp" pathology (git checkout, NFS clock skew) disappears because the key is the bytes, not the clock (the same principle as [./git-cas.md](./git-cas.md)).

**Materialized-view refresh cost model.** View V joins `orders` (10M rows) with `users` (1M rows) and aggregates revenue by region. Full refresh: scan 10M + 1M rows, join, aggregate — every refresh pays the whole query. Incremental maintenance: the day's changes touch 100K orders (1%); the engine propagates those 100K deltas through the join/aggregate plan into the stored result — roughly 100× less read work, at the price of maintaining per-view state and applying deltas in the right order. The break-even is churn-rate-driven: below a few percent daily churn, incremental wins by orders of magnitude; above it (or with delta-joins that fan out — one inserted row joining against 10M existing rows), a full refresh can be cheaper. The same churn-versus-recompute trade governs spreadsheet recalc strategies and React memo granularity, which is why the decision framework transfers.

## When This Connection Is Useful

- **Engineering decisions.** When a tool feels slow, ask which of the three ingredients is weak: wrong edges (undeclared deps), weak keys (timestamps), or no memoization (full refresh). Each has a known fix: generate edges from the language or compiler (depfiles, query systems), strengthen keys to content hashes, add a memo layer with explicit invalidation. "Add a build cache" without fixing keys just caches lies faster.
- **Interview: "design Google Docs / a spreadsheet / a live dashboard."** The senior move is to identify the invalidation unit (cell, keystroke, query result, component) and the dependency source (formula, edit log, upstream table, props), then present dirty propagation with memoized results. The spreadsheet case study is precisely this design ([../../interview/system-design/case-studies/collaborative-spreadsheet.md](../../interview/system-design/case-studies/collaborative-spreadsheet.md)).
- **Cross-domain debugging.** "The build says up-to-date but the binary is wrong" (missing edge), "the view is stale after the ETL ran" (propagation skipped), "the component re-renders on every keystroke" (memo boundary missing) — three symptoms, one diagnosis framework, one set of fixes.

## Interview Questions

1. Explain the three ingredients of incremental computation (graph, dirty propagation, memoized results) using a spreadsheet example, then identify which ingredient fails in "the build says up-to-date but the binary is wrong."
2. Compare timestamp-based (make) and content-hash-based (Bazel) staleness keys: give one false rebuild and one false reuse that each key produces, and why content hashing cannot produce false reuse.
3. In the 10,000-TU build example, why does adding the header as a prerequisite (depfiles) fix the clean-lie bug while `touch`-based workarounds do not? What does each do to the rebuild count?
4. Give a workload and a view definition for which incremental view maintenance is *slower* than full refresh. What property of the delta-join algebra causes the flip?
5. React re-renders a whole subtree on a state change while spreadsheets invalidate exact cells. What does React buy with the coarser invalidation, and what mechanism keeps its write cost bounded anyway?

## Key Takeaways

- One recipe spans build systems, spreadsheets, incremental compilers, materialized views, and React: dependency graph + dirty propagation + memoized results; every bug is a missing edge, a lost dirty mark, or an over-lived memo.
- Dependency precision is the quality dial: enforced-by-construction (spreadsheets, query engines) beats human-declared (build files) beats over-approximated (subtree re-renders, timestamps).
- Memo keys decide soundness: content hashes cannot produce false reuse; timestamps routinely do. "Clean lies" — up-to-date but wrong — are the characteristic failure of weak keys and missing edges.
- Incremental maintenance is a churn-rate bet: at low churn, deltas beat full recomputation by orders of magnitude; at high churn or fan-out-heavy joins, refresh wins — the break-even is computable, not ideological.
- Full recomputation is the only zero-assumption baseline; every incremental design is a soundness wager on its dependency graph, and the wager's enforcement mechanism (query systems, content hashes, generated depfiles) is the actual engineering.

## Cross-References

- [./dependency-resolution.md](./dependency-resolution.md) — Dependency Resolution — the build DAG, topological scheduling, and cycle handling.
- [../why-not-handbook/caching-distributed.md](../why-not-handbook/caching-distributed.md) — Caching vs Distributed Coordination — the decision-level view of when memoization is worth it.
- [../../software-engineering/build-systems.md](../../software-engineering/build-systems.md) — Build Systems — make, Bazel, and build graph engineering.
- [../../linux/compilers/make.md](../../linux/compilers/make.md) — make — timestamps, rules, and the classic header-dependency trap.
- [../../supply-chain/bazel-build-graphs.md](../../supply-chain/bazel-build-graphs.md) — Bazel Build Graphs — action graph, hashing, and remote cache keys.
- [../../dbms/advanced/incremental-view-maintenance.md](../../dbms/advanced/incremental-view-maintenance.md) — Incremental View Maintenance — delta propagation through relational algebra.
- [../../frontend/react-internals.md](../../frontend/react-internals.md) — React Internals — the render/diff loop and memoization boundaries.
- [../../interview/system-design/case-studies/collaborative-spreadsheet.md](../../interview/system-design/case-studies/collaborative-spreadsheet.md) — Collaborative Spreadsheet — the design-interview application of this connection.
- Mokhov, A., Mitchell, N., & Peyton Jones, S., "Build Systems à la Carte," ICFP 2018 — builds as applicative/monadic tasks over dependency graphs, cited by name.
- Hammer, M. et al., "Adapton: Composable, Demand-Driven Incremental Computation," PLDI 2014 — the demand-driven incremental programming model, cited by name.
