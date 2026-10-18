# Virtual DOM vs Signals: Diff Everything Against Track Exactly What Changed

## Overview

When application state changes, how does the UI learn which pixels to update? The two dominant answers compute "what changed" at different times and different granularities. The **virtual DOM** re-runs a render function that produces a lightweight tree description, diffs it against the previous tree, and patches the real DOM where they differ ([React](https://react.dev/) is the canonical implementation). **Signals** make state itself a live dependency graph: reading a signal inside a binding records the dependency, and writing it propagates to exactly the dependents — typically the handful of DOM nodes bound to that value ([Vue](https://vuejs.org/guide/extras/reactivity-in-depth.html) refines this model; Solid builds rendering directly on it). The fork is **where change detection happens**: post-hoc, by comparing two snapshots; or incrementally, by tracking reads and writes as they occur.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **the VDOM pays a cost proportional to the re-rendered subtree plus the diff, regardless of how little changed — and buys a dead-simple mental model (UI = f(state)) plus the largest ecosystem in front-end; signals pay a cost proportional to what actually changed, and buy that with tracking machinery whose consistency and edge semantics are subtler.** Neither is free, and the most instructive position is a third one: compiler-driven frameworks ([Svelte](../../frontend/svelte.md)-style) move change detection to build time, proving the axis is not "diff vs track" but *where and when the work of noticing change is paid*. The edge cases — the memoization treadmill, signal tearing, and the list that both models still need keys for — are where rote answers fall apart.

## Step 1: The Problem and Its Constraints

The abstract shape: a UI holds state *s*; events mutate *s*; the DOM must reflect *s* within a frame budget (16.7 ms at 60 fps). Constraints that decide the answer:

- **Update frequency and granularity.** A dashboard updating a price 30× per second in one cell is a fine-grained problem; a form re-rendering on submit is not. The more localized and frequent the updates, the more VDOM's per-update floor hurts.
- **State shape.** Fine-grained, independent values (counters, flags, positions) map naturally to signals. Coarse, interdependent application state (one store, derived views) maps naturally to render-from-state — the VDOM's whole-subtree recomputation is *harmless* when almost everything changed.
- **Team and ecosystem gravity.** Hiring pool, component libraries, SSR frameworks, devtools, and accumulated organizational React knowledge are constraints as real as frame budgets. Ecosystem maturity is a correctness story too: known failure modes have known fixes.
- **Snapshot consistency needs.** Does the UI need to render one coherent moment of state per event (transactional consistency), or can independent bindings update piecemeal? VDOM's render-once-per-update gives snapshot consistency by construction; signal graphs must schedule for it deliberately.
- **Memory and device profile.** Two trees plus churn allocations (VDOM) versus a persistent dependency graph (signals) stress the GC differently — see the [V8](../../languages/javascript/v8.md) dimension in the edge cases.

## Step 2: The Mechanisms

### Virtual DOM: re-render, diff, patch

- **The update loop is render → diff → patch.** State changes mark components dirty; the framework re-executes their render functions, producing new lightweight trees; a diff against the previous trees finds minimal edits; the real DOM receives the patch. The real DOM is never diffed — it is too expensive to read and compare — so the VDOM is a cheap proxy that makes "recompute the whole view" affordable.
- **The cost model is proportional to the rendered subtree, not to the change.** Re-rendering a component re-executes its *entire* function body and diffs the whole result, even when one boolean flipped. The floor is set by component granularity, so performance work becomes granularity work: `memo`, `useMemo`, `useCallback`, splitting components — all manual moves to shrink the re-rendered unit.
- **The diff is heuristic, not minimal.** O(n) by design, resting on two assumptions: elements of the same type keep their subtree (skip it), and list children are matched by `key`. Correct keys make list reconciliation O(n log n)-ish in practice; absent keys force worst-case re-creation. The heuristics are the contract — break them (same position, different component type) and subtrees are destroyed and rebuilt, which is also why conditional branches need stable shapes.
- **Scheduling is the hidden half.** Modern implementations ([React internals](../../frontend/react-internals.md)) batch updates, interrupt rendering to stay responsive, and prioritize transitions. The scheduler converts the "re-render everything marked dirty" model into one that respects frame budgets — but the work to be done is still bounded by what got marked.
- **GC pressure is structural.** Every update allocates fresh tree objects; short-lived allocation churn is the steady-state diet. Generational GCs absorb it well — young-object death is the cheap case — but on low-memory devices the churn is measurable.

### Signals: read-tracking, write-propagation, direct update

- **Dependency tracking happens at read time.** A signal is a reactive cell; when a computed or effect reads it, the read is recorded as a dependency. Writing the signal notifies dependents directly. There is no re-render of a tree, no diff: the update path is write → (scheduled) dependents → their DOM writes.
- **The cost model is proportional to actual change.** One cell updated, three nodes bound to it, three DOM writes — independent of application size. This is the fine-grained promise: updates do not scale with how big the app is, only with how much changed.
- **Granularity is automatic — until it isn't.** No memo ceremony: the dependency graph *is* the memoization, maintained by the runtime. But granularity depends on where reads happen: a coarse effect that reads fifty signals re-runs on any of them; over-fine effects (one per derived value, each touching the DOM) can add scheduler overhead. Tuning signal granularity is the analog of tuning component granularity.
- **Consistency must be scheduled, not assumed.** An effect reading two signals can observe a mixed state (one updated, one not) unless the scheduler batches writes and defers effects to a flush point — the analog of VDOM's "one render per update". Frameworks differ in guarantee; naive compositions tear (edge case below).
- **Ecosystem gravity is the real price.** Mature SSR/hydration, form libraries, tables, devtools, and a deep hiring pool exist on the VDOM side; the signal frameworks are younger and smaller. The technical model is not chosen in a vacuum — it is chosen inside a labor market.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Virtual DOM | Signals |
|----------|-------------|---------|
| Update cost | O(re-rendered subtree + diff) | O(actual dependents updated) |
| Cost scales with | Component granularity (manual tuning) | Dependency granularity (mostly automatic) |
| Consistency | Snapshot per update, by construction | Scheduler-dependent; tearing possible if naive |
| Memory profile | Two trees + allocation churn | Persistent graph, stable allocations |
| Perf model for teams | Simple rule; tuning via memo discipline | Good defaults; subtle when graphs grow |
| Debugging | Render traces; devtools mature | Effect loops; dependency graph inspection |
| Lists | Keyed reconciliation required | Keyed reconciliation required (structural change is structural) |
| SSR/hydration | Deeply mature | Maturing; resumability variants |
| Ecosystem | Largest | Smaller, newer |
| Failure mode | Whole-subtree re-render storms | Stale/over-fine effects, torn reads |

The **granularity symmetry** deserves the arrow drawn: both models ultimately tune the same variable — the size of the unit that re-executes when state changes. VDOM tunes it manually (memo boundaries, component splits), signals tune it structurally (where reads happen). This is why the "signals are automatically fast" claim needs qualification: a coarse effect is the signal world's un-memoized component, and both worlds' performance failures are granularity failures. The difference is that signals make the *good* granularity the default, while VDOM makes the *coarse* granularity the default and sells the fix as a discipline.

## Step 4: When Each Wins

**The VDOM wins** when: the team optimizes for ecosystem, hiring, and mature tooling; application state is coarse and interdependent (whole-view re-renders are nearly free because most of the view did change); snapshot consistency per event is wanted by default; and performance is manageable under a memoization discipline the team can enforce. Large product teams on React are not choosing ignorance of fine-grained updates — they are pricing ecosystem maturity above a performance floor that memo discipline usually reaches.

**Signals win** when: updates are frequent and fine-grained (prices, positions, drag states, live editors, big dashboards); the app cannot afford a memoization treadmill (the discipline does not hold across 40 engineers); bundle and parse budgets are tight (signal runtimes are small); and per-update cost should scale with change, not with app size. The decisive test: if a profiler shows re-renders dominating frame time and the fix is an ever-growing wall of memo wrappers, the workload has outgrown the VDOM's cost model.

**The honest middle ground** — where the frontier actually is:
- **Compiler-driven reactivity (Svelte-style).** A compiler analyzes each component, statically determines which state can affect which DOM nodes, and emits minimal, dependency-free update code — no runtime diff, no runtime dependency graph. It proves change detection can be *paid at build time* when components are analyzable, falling back to coarser updates where they are not (edge case below). The axis is therefore three-valued: runtime diff, runtime tracking, compile-time derivation.
- **Signals inside a VDOM framework.** Fine-grained primitives for hot paths (`useSyncExternalStore`-style bridges) while keeping the VDOM's composition and ecosystem for structure — the pragmatic destination of most large React apps.

## Step 5: Edge Cases and Counterexamples

- **The memoization treadmill: re-implementing signals by hand.** A React dashboard's hot path grows `React.memo` on eleven components, `useMemo` on nine derivations, and a `useCallback` for every handler — each a manual declaration of "this depends on that, skip otherwise". The team has rebuilt a dependency graph in userland, with the staleness bugs that follow when one wrapper cites the wrong prop. The signal model automates exactly this bookkeeping. The edge case is not "signals beat VDOM"; it is that *VDOM's cost model collapses into hand-written signals* when update granularity is fine and the team is large — the point where the default stops being good enough.
- **Torn reads in a naive signal graph.** An effect reads `total` and `currency`; a write to `total` flushes immediately, runs the effect with the new total and the old currency; then `currency` updates and runs it again — the user glimpses "1200 USD"→"1200 EUR"→"1300 EUR". VDOM never tears because it renders one coherent snapshot per update. Signal frameworks fix this with batched writes and deferred flushes — but the guarantee is scheduler policy, not model necessity, and composable libraries that trigger effects synchronously can reintroduce tearing. The general lesson: fine-grained reactivity buys granular updates by giving up snapshot consistency *by default*; it must be re-purchased deliberately.
- **The 10,000-row list that signals do not save.** Insert one row at the top of a large list. Signals make each cell cheap to update, but the structural change — shifting keys, reordering DOM nodes — is reconciliation work no tracking eliminates; keyed list diffing reappears in every signal framework. Virtualization (rendering a window) fixes the real problem in both worlds. "Signals eliminate diffing" is a leaf-level truth and a list-level falsehood.
- **The GC dimension inverts the benchmark.** Micro-benchmarks often favor VDOM churn (fast young-gen allocation, fast death) over a persistent signal graph (tenured, long-lived). On memory-constrained devices the long-lived graph plus retained closures can push old-gen pressure and compaction costs the benchmark never measured. The real question is not "which is faster" but "which allocation profile fits this device's GC" — a [V8](../../languages/javascript/v8.md) detail that flips naive conclusions.
- **What the compiler cannot see.** A Svelte-style compiler emits minimal updates when the state→DOM mapping is statically analyzable. Highly dynamic constructs — components assembled from runtime configuration, generic slot indirection, anything where "which state feeds which node" is decided at runtime — degrade to conservative, coarser update code or runtime fallbacks. The compiler middle ground is strongest for app-like UIs with legible structure, and weakest exactly where frameworks' abstraction height is highest. "Compile-time change detection" is a real third point on the axis, not a free lunch.

## Step 6: Decision Framework

1. **Are updates frequent and fine-grained** (per-cell, per-pixel, per-keystroke in large views)? Yes → signals-shaped model (or compiler-driven), because VDOM's per-update floor scales with the wrong thing.
2. **Is coarse, interdependent state the dominant shape?** Yes → VDOM re-renders are nearly optimal; the diff overhead is noise against the change size.
3. **Is ecosystem maturity a correctness requirement** (hiring, libraries, SSR, devtools)? Weight it honestly — it is the VDOM's largest and least refutable advantage.
4. **Can the org enforce a memoization discipline across teams and years?** No, and updates are fine-grained → signals; the treadmill fails quietly at scale.
5. **Is snapshot consistency per event required** (financial UIs, editors)? Either model provides it — VDOM by default, signals by scheduler — but it must be an explicit requirement in the signal case.
6. **Default in doubt:** VDOM-family for app-scale teams optimizing for ecosystem; signals for fine-grained hot paths and budget-sensitive apps; compiler-driven frameworks where the component structure is legible and the bundle is the constraint — and bridge the two (signals inside VDOM) rather than rewriting, when a hot path, not an architecture, is the problem.

## Interview Questions

1. **Explain the VDOM's cost model and why performance work is granularity work.** Each update re-executes and diffs a whole component subtree regardless of how little changed, so per-update cost is bounded by component granularity, not change size. Optimization therefore means shrinking the re-rendered unit — memo boundaries, component splits — which is manual dependency bookkeeping.
2. **How do signals achieve updates proportional to change, and what do they pay?** Reads are tracked as dependencies; writes notify dependents directly, so only bound nodes update. The payments: a persistent dependency graph, scheduler machinery for batched/deferred effects, and consistency that must be enforced (batching, flush points) rather than inherited from a snapshot-render model.
3. **What is the compiler-driven middle ground, and where does it fall short?** Svelte-style compilers statically derive the state→DOM mapping and emit minimal update code — no runtime diff or graph, change detection paid at build time. It falls short where the mapping is runtime-decided (dynamic composition, generic indirection), degrading to conservative updates; it is strongest for structurally legible apps.
4. **A team's React app is a wall of memo/useMemo wrappers with occasional stale-render bugs. Diagnose.** They have hand-implemented a dependency graph — memo wrappers are manual dependency declarations — and the bugs are staleness from wrong manual edges. This is the memoization treadmill: fine-grained update needs expressed in a coarse-grained model. Fix: correct the edges short-term; adopt fine-grained primitives (signals-style bridges) for the hot path long-term.
5. **Why do both models still need keys on lists?** Structural changes (insert, reorder) are reconciliation of *identity*, not of value: the runtime must know which node corresponds to which item to move or patch rather than recreate. Signals make leaf updates cheap; they do not make list identity tracking unnecessary. Keyed reconciliation is about element identity, orthogonal to the change-detection mechanism.

## Key Takeaways

- The fork is **where change detection is computed**: after the fact by diffing snapshots (VDOM), at read/write time by tracking dependencies (signals), or at build time by static analysis (compiler-driven). Cost models follow directly.
- VDOM's per-update cost scales with the re-rendered subtree; signals' scales with actual change. Fine-grained, high-frequency updates are where the difference is decisive — and where VDOM's fix (memo discipline) collapses into hand-written dependency tracking.
- Snapshot consistency is VDOM's quiet gift; signals must schedule for it deliberately, or users see torn intermediate states.
- Lists need keys in both worlds — structural reconciliation is about identity, orthogonal to change detection.
- Ecosystem maturity is a first-class constraint, not a footnote: the VDOM's advantage is as much labor market and tooling as runtime model, and the production answer is often signals inside a VDOM app rather than a rewrite.

## Cross-References

- [React Internals](../../frontend/react-internals.md) — the scheduler, fibers, and reconciliation mechanics behind the VDOM half.
- [Svelte](../../frontend/svelte.md) — the compiler-driven middle ground in depth.
- [State Management](../../frontend/state-management.md) — where the state that feeds either model lives and flows.
- [JavaScript Deep Dive](../../frontend/javascript-deep-dive.md) — the language-level behavior (closures, GC, events) both runtimes sit on.
- [V8](../../languages/javascript/v8.md) — the GC and allocation behavior behind the memory-profile edge case.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
- [React](https://react.dev/) — the canonical VDOM implementation and its escape hatches for fine-grained updates.
- [Vue: Reactivity in Depth](https://vuejs.org/guide/extras/reactivity-in-depth.html) — a production-grade signal system and its scheduling guarantees.
- SolidJS documentation (solidjs.com) — the build-directly-on-signals rendering model, cited by title (site blocks automated fetch).
