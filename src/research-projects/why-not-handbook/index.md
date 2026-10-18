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

The framework generalizes beyond the twenty-eight comparisons here. When you meet a fresh "X vs Y" question, running these six steps produces an answer that is specific to your constraints and honest about costs.

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
| [crash-recovery](./crash-recovery.md) | WAL vs in-place vs append-only/COW: where does atomicity live on disk? | Torn pages defeat redo deltas — full-page writes and doublewrite exist; append-only's compaction as slow-motion recovery |
| [push-vs-pull](./push-vs-pull.md) | Who owns the pacing — consumer or producer — and what failure does each import? | Retry storm after receiver recovery; slow consumer under push turns broker memory into the failure |
| [replication-modes](./replication-modes.md) | What exactly does a commit OK promise about the second copy? | MySQL semi-sync silently downgrades to async during the failure it exists for; PG sync stalls indefinitely |
| [scaling-up-vs-out](./scaling-up-vs-out.md) | Which part of the workload is serial, and what makes the serial remainder irrelevant? | The global counter hot row sharding cannot fix; Amdahl crossover when coordination grows with node count |
| [stateless-vs-stateful](./stateless-vs-stateful.md) | Every system has state — which placement's failure mode can you afford? | JWT logout that logs out nothing until expiry; per-node rate limiter undercounting by the fleet size |
| [static-vs-dynamic-typing](./static-vs-dynamic-typing.md) | When is type information checked, and which error class does each choice relocate? | TypeScript's erased boundary — the typed lie at unvalidated data edges; the orthogonal strong/weak axis (Python vs JS vs Java) |
| [monolith-vs-microservices](./monolith-vs-microservices.md) | What failure layer do you import when the network becomes a design layer? | The 27× retry cascade through three layers of 3× retries; five engineers operating a distributed monolith |
| [rest-vs-grpc](./rest-vs-grpc.md) | Where does the API contract live — social convention or compiled artifact — and who is the client? | gRPC-Web exists because browsers cannot read trailers; long-lived HTTP/2 channels unbalancing L4 load balancers |
| [orm-vs-raw-sql](./orm-vs-raw-sql.md) | Who owns the query text, and what does each ownership model hide? | ORM-generated predicates that defeat indexes (function-wrapped columns, implicit casts); identity-map staleness |
| [tcp-vs-udp](./tcp-vs-udp.md) | Where does reliability live — transport or application — and who owns congestion? | TCP's loss-based congestion control misdiagnosing wireless loss; UDP MTU fragmentation black holes |
| [sync-vs-async-io](./sync-vs-async-io.md) | What does the program do while waiting for the kernel, and who hides the wait? | The async file I/O myth on Linux (epoll reports regular files always-ready); one blocking call freezing an event loop |
| [snowflake-vs-uuid](./snowflake-vs-uuid.md) | Who generates the ID, what does the B-tree experience, and what do strangers learn? | UUIDv4 index fragmentation multiplied across every secondary index; sharded auto-increment steps that resharding breaks |
| [row-vs-column-stores](./row-vs-column-stores.md) | Which questions is the physical layout cheap at — few rows/all columns or all rows/few columns? | HTAP's async staleness seam; compaction starvation under chatty updates; "Cassandra is a column store" (data-model vs storage axis) |
| [password-hashing-choices](./password-hashing-choices.md) | How is verification made deliberately expensive, and what does each hardness buy? | bcrypt's silent 72-byte truncation (and the pre-hashing zero-byte bug it spawns); the login endpoint as a DoS amplifier |
| [graphql-vs-rest](./graphql-vs-rest.md) | Who shapes the response — and who pays for shape? | Introspection hands attackers the schema map; the request-scoped DataLoader that leaks; one GraphQL round trip slower than three cached REST calls |
| [batching-vs-streaming](./batching-vs-streaming.md) | When does processing start — after a window or on arrival? | The lambda architecture's dual-truth drift; the micro-batch interval that is three dials in one; the backfill a pure streaming system cannot perform |
| [etl-vs-elt](./etl-vs-elt.md) | Which engine owns transformation, and does raw data land? | The raw-zone PII masking race; silent schema drift landing loud downstream; streaming CDC that fits neither letter |
| [monorepo-vs-multirepo](./monorepo-vs-multirepo.md) | Is coordination tooling or process — where do contracts break? | The shared package that never reached 2.0 (polyrepo upgrade deadlock); monorepo CI collapse without affected-target computation; access control fragmenting the monorepo anyway |
| [canary-vs-blue-green](./canary-vs-blue-green.md) | How is the new version exposed over time, and who notices failure? | Dual-write doubling side effects in the overlap window; sticky sessions poisoning canary statistics; the migration that broke the rollback target |
| [virtual-dom-vs-signals](./virtual-dom-vs-signals.md) | Where is change detection computed — diff, track, or compile? | The memoization treadmill (hand-written dependency graphs); torn reads in naive signal graphs; the 10,000-row list that signals do not save |
| [normalize-vs-denormalize](./normalize-vs-denormalize.md) | Where does complexity live — the read path or the sync path? | JSON columns as transactionally-synced denormalization (and the planner-statistics trap); the index as the denormalization you already accepted; the join that outgrew a node |

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
| Crash recovery and WAL | WAL vs in-place vs append-only by failure mechanism | [WAL Internals](../../dbms/advanced/wal-internals.md) (engine mechanics), [Storage Durability](../assumptions-hunt/storage-durability.md) (device-level assumptions) |
| Push vs pull | Pacing ownership and where each mode relocates failure | [Backpressure: Atlas](../connection-atlas/backpressure.md) (the queue-full path), [Kafka](../../distributed/messaging/kafka.md) and [Pulsar](../../distributed/messaging/pulsar.md) (pull vs push brokers) |
| Replication modes | What the commit acknowledgment promises | [Primary-Backup](../../distributed/replication/primary-backup.md) (topology), [GitHub October 2018](../failure-casebook/github-october-2018.md) (async failover incident) |
| Scaling direction | Amdahl crossover; contention is not partitioning | [Amdahl's Law](../../arch/performance/amdahl.md) (the arithmetic), [Relational DBs Don't Scale](../misconceptions/relational-dbs-dont-scale.md) (the anti-slogan) |
| State placement | Failure-mode and revocation-latency relocation per state type | [Leases](../../distributed/advanced/leases.md) (ownership primitive), [Consensus & Leases: Atlas](../connection-atlas/consensus-leases.md) (safety under partitions) |
| Type systems | Checking time, erasure, and the orthogonal strong/weak axis | [Python Typing](../../languages/python/typing.md) and [TypeScript](../../languages/typescript/README.md) (the gradual middle path) |
| Architecture style | The network as a failure layer; Conway-aligned team topology | [Architecture Trade-offs](../../trade-offs/architecture-tradeoffs.md) (quick tables), [Microservices](../../distributed/microservices/README.md) (operational catalog) |
| API style (REST vs gRPC) | Contract location, reachability, caching, deadline propagation | [REST](../../networks/http/rest.md) and [gRPC](../../networks/http/grpc.md) (protocol mechanics), [API Contracts](../assumptions-hunt/api-contracts.md) (contract assumptions) |
| Query ownership (ORM vs SQL) | Who writes the text the planner sees | [Query Planner](../../dbms/query-planner.md) (plan mechanics), [Query Planner Dataflow](../connection-atlas/query-planner-dataflow.md) (text-to-execution web) |
| Transport choice (TCP vs UDP) | Where reliability lives; QUIC as the synthesis | [TCP vs UDP](../../networks/udp/tcp-vs-udp.md) (quick tables), [QUIC](../../networks/http/quic.md) (reliability rebuilt on UDP) |
| I/O model (sync vs async) | Who hides the wait: scheduler, readiness, or completion queues | [I/O Multiplexing](../../networks/sockets/io-multiplexing.md) (syscall mechanics), [io_uring](../../os/kernel/io-uring.md) (completion-based design) |
| Identifier design (auto-increment vs UUID vs Snowflake) | Generation authority, index locality, leakage | [B+Tree](../../dbms/indexing/b-plus-tree.md) (locality mechanics), [URL Shortener](../followup-tree/url-shortener.md) (ID design as a design interview) |
| Physical layout (row vs column) | Access-shape economics; HTAP as the hybrid answer | [Column Stores](../../dbms/storage/column-stores.md) (layout depth), [HTAP](../../dbms/advanced/htap.md) (the hybrid architecture) |
| Password hashing (SHA-2 vs bcrypt/scrypt/Argon2) | Cost-per-guess engineering and memory hardness | [Security & Crypto](../assumptions-hunt/security-crypto.md) (deployment assumptions), [Cryptography](../../security/cryptography.md) (the primitives) |
| API style (GraphQL vs REST) | Who shapes the response; caching, query cost, introspection | [GraphQL](../../backend/api/graphql.md) (the query language), [REST](../../networks/http/rest.md) (the resource model), [REST vs gRPC](./rest-vs-grpc.md) (the contract-location fork) |
| Pipeline pacing (batch vs streaming) | When processing starts: windows vs continuous | [Batch Processing](../../data-engineering/batch-processing.md) and [Stream Processing](../../data-engineering/stream-processing.md) (mechanics), [Exactly-Once Semantics](../../distributed/messaging-internals/exactly-once-semantics.md) (the stream tax) |
| Transform placement (ETL vs ELT) | Which engine transforms; whether raw lands | [Snowflake](../../dbms/advanced/snowflake.md) (the elasticity that flipped ELT), [Debezium](../../data-engineering/debezium.md) (streaming CDC) |
| Repository strategy (monorepo vs multirepo) | Coordination as tooling vs process | [Git Workflows](../../git/workflows.md) (branching inside either shape), [Git Workflow Assumptions](../assumptions-hunt/git-workflow-assumptions.md) (what history promises) |
| Deployment strategy (canary vs blue-green) | Exposure over time; detection vs rollback | [Canary Releases](../../sre/canary-releases.md) (the playbook), [Feature Flags](../../sre/feature-flags.md) (software-layer exposure) |
| UI update model (VDOM vs signals) | Where change detection is computed | [React Internals](../../frontend/react-internals.md) (diff/scheduler mechanics), [Svelte](../../frontend/svelte.md) (the compiler-driven middle) |
| Physical schema (normalize vs denormalize) | Copies and their sync strategies, uniformly | [Denormalization](../../dbms/normalization/denormalization.md) (read-optimization patterns), [Incremental View Maintenance](../../dbms/advanced/incremental-view-maintenance.md) (engine-maintained copies) |

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
