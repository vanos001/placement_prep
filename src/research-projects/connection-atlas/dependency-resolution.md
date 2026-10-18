# Dependency Resolution: Topological Sort Everywhere

## Overview

One algorithm from a second-semester graph unit — topological sort of a DAG — quietly runs the software supply chain. Make decides what to recompile with it, npm and pip decide which package versions to install with its cousin (version selection), Airflow decides the order your data pipelines run in, systemd and Kubernetes decide service startup order, and your CI system decides which stages can run in parallel. The connection is not loose metaphor: these systems literally construct a directed graph of "must-finish-before" edges and schedule a **linear extension** of that partial order.

This page builds both sides independently, names the shared principle, then is deliberately honest about where the mapping breaks — most importantly at cycles, which are fatal errors for build systems but routinely *tolerated* by package managers for reasons worth understanding.

## The Two Sides, Independently

**Topological sort.** Given a DAG (directed acyclic graph) with vertices V and edges E, a topological order is a linear sequence where every edge u → v appears with u before v. Two standard constructions: Kahn's algorithm (repeatedly remove vertices with in-degree 0, decrementing successors; O(|V| + |E|) with a queue) and DFS-based (emit vertices in reverse finish order). A topological order exists **if and only if** the graph is acyclic — so the same loop that builds the order *is* the cycle detector. Crucially, a DAG generally has many valid orders; a topological sort is one linear extension of a **partial order**, not a unique answer.

**Make.** A Makefile declares targets, prerequisites, and recipes. Make builds the dependency graph, then does a post-order traversal: a target is rebuilt if any prerequisite is newer (mtime comparison) or missing. Consequences that fall out of the mechanism, not from extra machinery: only the *affected* subgraph recompiles (incremental build); independent branches can be built in parallel (`make -j`) because the partial order constrains only dependency chains, not unrelated nodes; a cycle makes the traversal impossible, so Make reports `Circular dependency dropped` or errors out.

**Package managers (npm, pip).** Resolution is a two-layer problem. Layer one is *version selection*: each package declares constraints (semver ranges in npm, version specifiers in pip), and the resolver picks one version per package such that all constraints hold — a constraint-satisfaction problem over the package universe (npm's Arborist walks a tree with backtracking; pip's resolver backtracks through combinations; PubGrub, used by several ecosystems, encodes it as a sequence of derivations). Layer two is *ordering*: once versions are fixed, the install/lock/build order over "depends-on" edges is exactly a topological sort. A **diamond dependency** — root → A → C and root → B → C — is the classic shape: the question is whether one copy of C satisfies both parents, or whether two versions must coexist (npm nests a second copy under one parent; the lockfile records the chosen layout).

**Task schedulers and startup ordering.** Airflow parses `depends_on` links into a DAG and schedules in topological order (cycles are a validation error — the DAG import fails). systemd expresses ordering with `After=`/`Requires=` directives and refuses or ignores cycles depending on the relationship type. Kubernetes orders *init containers* sequentially (each must terminate before the next starts) but makes **no** ordering promise between regular containers in a pod — a frequent interview trap and a frequent real-world bug: app containers race each other to start, which is why readiness probes, not "started before," are the actual synchronization tool.

## The Shared Principle

**All of these systems schedule a linear extension of a partial order induced by dependencies, and all of their optimizations and error paths fall out of partial-order properties.** Three corollaries do the heavy lifting:

- **Parallelism = incomparability.** Two tasks may run concurrently exactly when neither is an ancestor of the other (they are incomparable in the order). `make -j`, CI fan-out, and Airflow parallelism are all just "execute incomparable nodes simultaneously."
- **Incremental rebuild = invalidation on the reversed DAG.** Changing a node invalidates its *dependents* (edges reversed), and only them. The rebuild set is the ancestor-closure of the changed node in the reversed graph; everything else is reusable. Correctness requires the order to be recomputed against a reliable "is it up to date" oracle.
- **Cycle = no valid schedule, so cycles surface as error reporting.** Since a topological order exists iff the graph is acyclic, any system that promises to run the order gets cycle detection for free, with the detection loop doubling as the error message generator.

## Where the Analogy HOLDS and BREAKS

| Aspect | HOLDS (mechanism is the same) | BREAKS (mechanism differs) |
|---|---|---|
| Core computation | All construct a DAG and execute/copy a linear extension | Version *selection* (which node versions exist at all) is constraint solving, not sorting |
| Cycles | Make, Airflow: cycle → hard error, because nothing can be ordered | npm tolerates cyclic dependencies: JS `require` is resolved at runtime, so install order can be an approximation ("install something somewhere"); pip historically forbade them via pip install order but the ecosystem lives with cycles — the *scheduler* strictness is not universal |
| Rebuild / reinstall trigger | Invalidate dependents on change (reversed-DAG closure) | Make's oracle is mtime (a proxy: touch a file without changing content and you rebuild everything downstream); content-addressed systems (Bazel, Nix) replace the proxy with hashes — see [git-cas.md](./git-cas.md) |
| Ordering semantics | Init containers, `After=`, recipe order: strict happens-before | Kubernetes regular containers: deliberately *unordered*; you must build ordering from readiness probes yourself |
| Diamond dependencies | The dependency shape and the partial order are identical | Resolution differs: one shared version (pip tries; lockfile pinning) vs nested duplicates (npm) vs error (strict resolvers with conflicting direct requirements, e.g., npm's `ERESOLVE`) |

The last row deserves emphasis because it is the most common misconception: "dependency resolution = topological sort" is true for the *ordering half only*. The hard engineering problems in npm/pip live in the *selection half*, which is a search problem (NP-hard in general for arbitrary constraint sets) that topology cannot solve.

## A Concrete Worked Example

**Diamond resolution, with numbers.** Root app requires `A@^2.0` and `B@^3.0`. `A@2.5` requires `C@^1.2`; `B@3.1` requires `C@^2.0`. No single C satisfies both constraints (`^1.2` allows `1.x`, `^2.0` allows `2.x`). npm installs `C@2.3` at the top level (satisfying B, installed later/larger heuristic aside) and nests a second physical copy `C@1.9` under `node_modules/A/node_modules/C`. Result: both parents are satisfied; the price is two copies of C in the bundle (~duplicated bytes, potential identity bugs if C has module-level state). A lockfile freezes this layout so every teammate and CI machine materializes the identical tree.

**Incremental rebuild, with numbers.** A C++ project has 400 translation units; one shared header `config.h` is included directly or transitively by 380 of them. You edit `config.h`. Full build: 400 compiles. Incremental with correct reversed-DAG invalidation: 380 compiles — no win, because the invalidation closure is nearly the whole graph. Now move the constants from `config.h` into a `.cpp` file and expose only a forward declaration: editing the implementation recompiles 1 unit (plus link). Same algorithm, same partial order — the *graph shape* was the performance problem, which is the actual lesson of the PIMPL idiom and of build-time interface/implementation splitting. Build time went from 380 compiles (~95% of the build) to 1 (~0.25%), an order of magnitude wall-clock difference on large projects.

**Cycle as error report.** Airflow: task `extract → transform → load → extract`. The validator rejects the DAG at parse time with the offending cycle named — exactly Kahn's algorithm reporting "no in-degree-0 vertex remains; these N vertices are cyclic." The error message quality is the algorithm; nothing else in the system had to be designed to produce it.

## When This Connection Is Useful

- **Problem-solving heuristic.** Any time the phrase "before X can happen, Y must finish" appears twice, draw the DAG and ask: who needs a topological order, who needs invalidation closure, and what is my up-to-date oracle? This decomposes build systems, CI, data pipelines, installers, and even onboarding checklists into the same three questions.
- **Engineering decisions.** (1) Choose your invalidation oracle deliberately — mtime is cheap and wrong under clock skew and checkouts; content hashes are correct and costier (this is the entire motivation for Bazel/Nix-style caching). (2) In orchestrators, do not "order" containers that the platform treats as unordered — use readiness probes and retry-on-failure, and say so explicitly in design docs. (3) Prefer making your dependency graph deeper-but-narrower at the hot interface (header hygiene, PIMPL, interface packages) because invalidation cost is a graph property, not a tool property.
- **Interview answers.** "Design a build system" decomposes into: parse → DAG → cycle check (Kahn) → parallel linear extension → invalidation closure → cache keyed by content hashes. "Detect a deadlock among N transactions/processes" is the same wait-for-graph cycle check — see [../../concurrency/deadlock-detection.md](../../concurrency/deadlock-detection.md) and the transactions page [transactions-concurrency-control.md](./transactions-concurrency-control.md). Naming the partial-order principle and the mtime-vs-hash oracle distinction is what separates a mid-level from a senior-shaped answer.

## Interview Questions

1. Why does a topological order exist exactly when the graph is acyclic? Prove both directions in at most five sentences, and explain why the proof structure gives you cycle detection for free in any scheduler built on the sort.
2. npm can install packages that depend on each other cyclically; Make errors on a circular dependency. Reconcile these two behaviors using the difference between install-time and runtime name resolution.
3. Your team's build recompiles 95% of targets after a one-line change. Walk through the mechanism that explains this and two concrete graph-level fixes, with expected recompile percentages.
4. Why does Kubernetes order init containers but not regular containers, and what should you use instead for "A must be healthy before B starts"?
5. Given a diamond dependency with incompatible version constraints, compare the nested-duplicate strategy (npm) with single-version selection (lockfile/pip) in terms of correctness, bundle size, and state-sharing bugs.

## Key Takeaways

- Build systems, package managers, task schedulers, and startup ordering all execute a linear extension of a dependency-induced partial order; parallelism is exactly incomparability.
- Incremental rebuilds are invalidation closures on the reversed DAG; the correctness hinge is the up-to-date oracle (mtime proxy vs content hash).
- Cycles are structurally unschedulable, so any order-based system inherits cycle detection as error reporting — except where runtime resolution (dynamic linking, JS `require`) lets the scheduler cheat.
- Resolution = selection + ordering. Topological sort answers only the ordering half; the selection half is constraint solving and is where real package-manager complexity lives.
- Graph shape is performance: invalidation cost, parallel fan-out, and rebuild latency are properties of the dependency graph you authored, not of the tool.

## Cross-References

- [../../dsa/advanced-algorithms.md](../../dsa/advanced-algorithms.md) — Advanced Algorithms — topological sort and DAG techniques in their algorithmic home.
- [../../software-engineering/build-systems.md](../../software-engineering/build-systems.md) — Build Systems — Make/Bazel mechanics, cache oracles, and hermetic builds in depth.
- [../../data-engineering/airflow.md](../../data-engineering/airflow.md) — Apache Airflow — DAG validation, scheduling, and backfills as a production case.
- [../../cloud/kubernetes/scheduling.md](../../cloud/kubernetes/scheduling.md) — Kubernetes Scheduling — pod placement vs the in-pod ordering rules discussed here.
- [../../concurrency/deadlock-detection.md](../../concurrency/deadlock-detection.md) — Deadlock Detection — wait-for-graph cycle detection, the same algorithm aimed at locks instead of tasks.
- [./git-cas.md](./git-cas.md) — Git as Content-Addressable Storage — content addressing as the correct rebuild oracle.
- [./transactions-concurrency-control.md](./transactions-concurrency-control.md) — Transactions and Concurrency Control — the second life of cycle detection on lock wait-for graphs.
- [../../os/scheduling/README.md](../../os/scheduling/README.md) — OS Scheduling — where the OS kernel does its own dependency- and priority-aware ordering of work.
