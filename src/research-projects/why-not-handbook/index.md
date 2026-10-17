# Why-Not Handbook

## Overview

Most engineering material explains why an approach works. This handbook answers the opposite, harder question: **why not the alternative?** Each page takes a pair — or a small set — of options that interviewers, code reviewers, and designers routinely contrast (BFS vs DFS, hashing vs binary search, mutex vs semaphore, B-tree vs LSM, caching vs recomputation) and explains the *mechanism* behind each option deeply enough that the trade-offs fall out as consequences rather than memorized slogans.

The collection deliberately overlaps with the [Trade-offs](../../trade-offs/README.md) section, which stores quick-reference comparison tables. There, a one-line table row says "hash: O(1) average, no ordering". Here, the same comparison is re-derived from first principles: how the hash bucket is probed, what the cache does to that probe, what happens under adversarial keys, and the specific workloads where the binary search that "loses" on paper is the correct engineering answer. If you want a fast answer, read [trade-offs](../../trade-offs/README.md); if you want to defend that answer under three rounds of "why?", read here.

## The Six-Step Meta-Framework

Every page in this handbook applies the same six steps, in the same order. The order is the point: each step narrows the space so the final recommendation is a consequence of evidence, not taste.

1. **Define the problem and its constraints.** A comparison without a workload is a slogan. Before comparing, the pages pin down: what the input looks like (size, distribution, mutation rate), what guarantees the caller needs (exact vs approximate, ordering, freshness, worst-case bounds), and what resources are fixed (memory budget, latency budget, hardware). Binary search vs hashing is undecidable until someone says whether range queries are needed and whether keys are adversarial.
2. **Explain the mechanism of each option.** Not "hash tables are O(1)" but *why*: hash the key, index into a bucket array, resolve collisions by chaining or probing, resize when load factor exceeds a threshold. Mechanism-level explanations expose the constants, the memory behavior, and the failure modes that asymptotic notation hides. Two operations with the same big-O can differ by 50× in practice, and the mechanism tells you which one.
3. **State complexity, guarantees, and failure modes.** For each option: worst-case, average-case, and amortized complexity where they differ; the formal guarantees it gives (ordering, stability, linearizability, bounded latency); and the characteristic ways it breaks (rehash storms, deadlocks, frontier blowups, write skew). Guarantees are contracts — the pages state exactly which contract each option signs.
4. **Name the conditions where each option wins.** Not a generic ranking, but explicit trigger conditions: "DFS wins when the graph is deep and memory is bounded", "LSM wins when write throughput dominates and reads tolerate milliseconds of staleness". Every option in every page is the right choice somewhere — the handbook has no strawmen.
5. **Find the edge cases and counterexamples.** This is where most material stops and this handbook starts. Each page includes at least one non-obvious case where the "obvious" choice fails: BFS frontier blowup on lattice graphs, hash-flooding attacks, lost wakeups in condition variables, write skew under snapshot isolation, cache stampedes after an invalidation. These cases are what interviewers use to separate rote answers from real understanding.
6. **Write the decision framework.** Each page ends with a table or ordered checklist mapping workload properties to a choice. The framework is falsifiable: if your workload matches the left column, the right column is the recommendation — and the page has already told you what you are giving up.

The framework generalizes beyond the seven topics here. When you meet a fresh "X vs Y" question, running these six steps produces an answer that is specific to your constraints and honest about costs.

## File Inventory

| Page | Core question | Flagship edge case covered |
|------|---------------|----------------------------|
| [bfs-vs-dfs](./bfs-vs-dfs.md) | Same O(V+E) complexity — why does traversal order change what you can guarantee? | BFS frontier blowup on grid/lattice graphs; recursion depth overflow in DFS |
| [binary-search-vs-hashing](./binary-search-vs-hashing.md) | O(log n) guaranteed vs O(1) average — which contract do you need? | Hash-flooding adversarial keys; cache-friendly sorted arrays beating hash tables at small n |
| [arrays-vs-linked-lists](./arrays-vs-linked-lists.md) | When is O(1) insertion real, and when is cache locality worth more? | "O(1) insertion" that requires an O(n) search first; reallocation invalidating iterators |
| [sorting-algorithms](./sorting-algorithms.md) | Five n-log-n-class algorithms — why do libraries ship hybrids? | Naive quicksort's O(n²) collapse on sorted input; radix sort's hidden per-pass costs |
| [concurrency-primitives](./concurrency-primitives.md) | Mutex vs semaphore vs condvar; processes vs threads; polling vs event-driven I/O | Lost wakeup; crash blast radius; busy-polling trading CPU for tail latency |
| [database-choices](./database-choices.md) | Normalization vs denormalization; B-tree vs hash vs LSM vs GiST/GIN; optimistic vs pessimistic | Write skew under snapshot isolation; LSM read amplification without bloom filters |
| [caching-distributed](./caching-distributed.md) | Caching vs recomputation; consistency vs availability vs latency | Cache stampede after invalidation; per-operation CAP choices inside one system |

## Coverage Ledger

The same concepts appear across several research projects **from deliberately different angles** — the coverage plan requires linking, not re-explaining. The ledger below records which angle each project takes so you know where to go next. (Paths are relative to pages in this directory.)

| Concept | This handbook's angle | Elsewhere |
|---------|----------------------|-----------|
| Hash tables | Vs binary search: ordering, guarantees, adversarial keys | [Follow-up Tree](../followup-tree/hash-tables.md) (escalation ladder), [Misconceptions](../misconceptions/hash-lookup-o1.md) (the false O(1) claim), [Assumptions Hunt](../assumptions-hunt/complexity-claims.md) (adversarial inputs) |
| DB index structures | B-tree vs hash vs LSM vs GiST/GIN by workload | [Connection Atlas](../connection-atlas/db-indexes-data-structures.md) (dependency web), [Indexing strategy](../../dbms/indexing-strategy.md) (practical SQL guide) |
| Mutexes and locking | Ownership semantics and signaling vs exclusion | [Follow-up Tree](../followup-tree/mutex-to-lock-free.md) (escalation to lock-free), [Misconceptions](../misconceptions/more-threads-faster.md) (threads-equal-speed myth) |
| Isolation and concurrency control | Optimistic vs pessimistic decision rule | [Assumptions Hunt](../assumptions-hunt/database-isolation.md) (implicit isolation assumptions) |
| Caching and backpressure | Caching vs recomputation; staleness vs availability | [Connection Atlas](../connection-atlas/backpressure.md) (queue-full path), [Cache patterns](../../sre/cache-patterns.md) (operational playbooks) |
| High-level comparison tables | Deep mechanisms here | [Trade-offs](../../trade-offs/README.md) (quick-reference tables) |

Duplication boundary (from the project plan): trade-offs pages hold the scannable tables; this handbook holds mechanisms, complexity derivations, guarantees, and edge cases. If you find yourself copying a table between the two, link instead.

## How to Use This in an Interview

A strong "why not X?" answer has three moves. First, name the mechanism of the rejected option ("a hash table probes one bucket after computing a hash"). Second, state the guarantee you actually need ("I need predecessor queries and ordered iteration"). Third, conclude conditionally, not absolutely ("so for this workload the hash table cannot substitute; for pure point lookups it would be faster"). Pages here give you all three moves pre-assembled, plus the edge case that turns a good answer into a memorable one.

## Interview Questions

1. **Why does the handbook insist on mechanisms before trade-offs?** Because every trade-off line item ("O(1) average", "stable", "no ordering") is a *consequence* of a mechanism. Deriving consequences from mechanisms lets you answer variants you never memorized — new workload, new failure mode, new hardware — while a memorized table breaks the moment the question changes.
2. **What does "conditions where each wins" prevent?** Strawman comparisons. If your explanation of an option cannot name a workload where it is the best choice, you do not understand the option — you have only memorized its weaknesses.
3. **Give an example of an edge case changing the default choice.** On paper, hashing beats binary search for lookups. Under adversarial keys and a known hash function, an attacker forces every key into one bucket and turns O(1) into O(n) — a denial of service. Hardened hash functions (keyed seeds, SipHash) restore the guarantee; alternatively, a sorted array plus binary search gives a hard O(log n) that no input can break. The workload detail — are keys attacker-controlled? — flips the decision.
4. **What belongs in a decision framework that does not belong in a trade-off table?** An ordering. A table lists dimensions; a framework says *which question to ask first* ("Do you need ordering? If yes, the hash family is out regardless of everything else"). Ordered checklists mirror how real designs narrow down.
5. **How do the coverage boundaries keep the book maintainable?** Same concept, different angles, explicit links. The Why-Not Handbook derives from mechanisms; trade-offs summarizes; Follow-up Tree escalates through interview question chains; Misconceptions attacks false claims. A reader landing on any page gets pointers to the others instead of duplicated prose.

## Key Takeaways

- Every comparison here runs the same six steps: constraints → mechanisms → complexity/guarantees/failure modes → winning conditions → edge cases → decision framework. The order matters; the last step is a consequence of the first five.
- Mechanisms expose what asymptotic notation hides: cache behavior, constants, amortization spikes, and the exact contract each data structure or system signs.
- No option is a strawman. Each page states the explicit conditions under which the "losing" option is the correct engineering choice.
- Edge cases — adversarial inputs, frontier blowups, write skew, stampedes — are where defaults fail and where interview depth is proven.
- This collection complements, and links to, the quick-reference tables in [Trade-offs](../../trade-offs/README.md) rather than duplicating them.

## Cross-References

- [Engineering Trade-offs](../../trade-offs/README.md) — the quick-reference comparison tables this handbook goes deeper than.
- [Database Trade-offs](../../trade-offs/database-tradeoffs.md) — high-level SQL/NoSQL, consistency, and indexing tables referenced by the database pages here.
- [DSA](../../dsa/README.md) — the main DSA track whose chapters (sorting, hashing, graphs) provide the tutorial-level background for the mechanism discussions here.
- [Follow-up Tree](../followup-tree/hash-tables.md) — question-escalation chains for concepts compared in these pages.
- [Assumptions Hunt](../assumptions-hunt/complexity-claims.md) — the hidden assumptions behind the complexity claims this handbook quotes.
- [Connection Atlas](../connection-atlas/db-indexes-data-structures.md) — dependency-web view of the same database concepts.
- [Misconceptions](../misconceptions/more-threads-faster.md) — the false beliefs this handbook's edge cases are designed to disarm.
