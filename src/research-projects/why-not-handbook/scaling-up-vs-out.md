# Scaling Up vs Scaling Out: What Each Direction Actually Costs

## Overview

"Scale up or scale out?" is usually presented as buy-a-bigger-box versus buy-more-boxes. That framing hides the real question: **which part of your workload is parallel, and what will you pay to make the serial remainder irrelevant?** Vertical scaling (scale-up) keeps one machine — one memory domain, one storage engine, one transaction coordinator — and buys speed with hardware and license dollars. Horizontal scaling (scale-out) buys aggregate capacity with topology and pays in distributed-join latency, two-phase-commit stalls, hot partitions, and operational surface. The correct default for most teams is neither banner: **scale up until a measured wall, add read replicas as the cheap first out-step, and re-architect only when a specific bottleneck — named and measured — forces it.**

This page runs the [handbook framework](./index.md) over the choice, with Amdahl's law ([mechanism here](../../arch/performance/amdahl.md)) as the crossover engine and the anti-slogan treatment of "relational databases don't scale" left to [its own misconception page](../misconceptions/relational-dbs-dont-scale.md).

## Step 1: The Problem and Its Constraints

A service is outgrowing its database. The constraints that decide the direction:

- **What is growing?** Read volume (replicas solve cheaply), write volume (needs write-path parallelism: sharding or scale-up), working-set size (RAM: scale-up usually wins to absurd sizes), or data volume (partitioning or scale-up disk). "Traffic is growing" is not a spec.
- **What does the data model require?** Cross-row ACID transactions, foreign keys, unique constraints, and joins are free on one machine and *expensive to approximate* across shards. The model is a scaling constraint, not a detail.
- **What is the growth curve?** 10× planned or 100× hoped-for? Scale-up is a superb 10× strategy and a terrible 100× one; horizontal is a poor 2× strategy (all cost, little used) and the only 1000× one.
- **Team size.** Sharding adds permanent operational complexity — per-shard failover, resharding, cross-shard observability. A two-person team operating 64 shards pays a tax a 40-person platform org does not feel.

## Step 2: The Mechanisms

### Scale-up: one fast machine

The mechanisms by which "a bigger box" delivers:

- **RAM capacity.** A current two-socket server addresses multiple TB; a working set that fits in RAM converts disk-bound latency into cache-bound latency, the largest single performance step available. Buy-a-bigger-box is *the* fix for "my working set no longer fits".
- **More cores — with a NUMA tax.** Beyond one socket, memory is node-local: a core accessing another socket's DRAM pays roughly 1.5–2× the latency, and the buffer pool's pages land on whatever socket first touched them. Engines fight this with per-NUMA-node allocation and thread pinning; the mechanism (and why "more threads" alone does not scale) is in [more-threads-faster](../misconceptions/more-threads-faster.md) and [virtual memory's NUMA section](../followup-tree/virtual-memory.md). Scale-up has a real ceiling — it is soft (performance decay) rather than hard, which is what makes it easy to overstay.
- **License economics — the anti-ceiling.** Oracle EE and Microsoft SQL Server Enterprise license *per core*: a 64-core box costs multiples of the hardware per year at list prices, and RAC/Always-On options add more. Per-core licensing is a *workload* for avoiding vertical growth: it prices the serial-remainder fix at enterprise-software rates and is why scale-out is structurally cheaper for oracle-class estates even when engineering-wise inferior.

### Scale-out: many coordinated machines

The mechanisms by which "more boxes" delivers — and the price list attached to each:

- **Partitioning** ([hash and range strategies](../../distributed/partitioning/README.md)) splits data by key so each machine owns a slice; lookups on the partition key are one-shard and fast. The costs arrive immediately: **distributed joins** (a join across partitions ships rows over the network or runs as N partial joins + merge), **cross-partition transactions** (2PC: two extra round trips per commit plus a *blocking* failure mode if the coordinator dies between prepare and commit — see [two-phase commit](../../dbms/transactions/two-phase-commit.md) and [distributed transactions](../../distributed/advanced/distributed-transactions.md)), and **hot partitions** (hashing spreads load only if the key is high-cardinality; a tenant with 40% of the traffic owns one shard regardless — see [hot keys and sharded counters](../../distributed/advanced/hot-keys-and-sharded-counters.md)).
- **Resharding** is the permanent tax: adding a node means moving data while serving traffic (consistent hashing bounds movement but never to zero — see [consistent hashing](../../distributed/partitioning/consistent-hashing.md)); sharding proxies like Vitess ([architecture](../../dbms/advanced/vitess-sharding-proxy.md)) exist because this is a full-time problem.
- **Read replicas** ([modes and their guarantees](./replication-modes.md)) are the *cheap* horizontal step: no partitioning, no 2PC, one primary keeps the write path intact and each replica serves reads. Their limit is structural — replicas execute the same joins and cannot help the write path, the point where teams denormalize instead ([database-choices](./database-choices.md), Comparison A).

### Amdahl's crossover, stated as arithmetic

Amdahl: speedup ≤ 1 / (s + (1−s)/N) for serial fraction *s* across *N* nodes. Sharding parallelizes data access but serializes whatever must be global — cross-shard transactions, global unique constraints, the coordinator itself. Concretely: if 10% of a workload's end-to-end time is cross-shard coordination that *grows* with N (each transaction touches more shards as N rises), adding nodes past ~10 starts *reducing* throughput — the parallel gain per node (9/N) shrinks while the serial term inflates. The crossover reasoning: **project the serial fraction as a function of N before buying nodes.** Scale-up attacks *s* directly (faster single-threaded execution, one coordinator), and is unbeatable while s dominates; scale-out attacks (1−s) and wins only when s is genuinely small. Neither argument mentions hardware prices — the law is about structure.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Scale-up | Scale-out (sharded) |
|----------|----------|---------------------|
| Transaction semantics | Full ACID, single coordinator | Cross-shard = 2PC (blocking risk) or sagas/compensation |
| Joins / FK / unique constraints | Native | Cross-shard joins ship data; FK and uniqueness become application-enforced or per-shard only |
| Failure mode | One machine: total, but *simple* (restore on bigger/nicer hardware) | Partial: one shard down degrades one keyspace; complexity is in the coordinator and resharding, not the failure |
| Ceiling | RAM/sockets/NUMA decay + per-core licenses | Serial fraction growth (Amdahl), hot partitions, operational headcount |
| Scaling event | Downtime-ish migration to bigger box (or vertical online growth) | Resharding: data movement under load, the hardest routine operation in the estate |
| Cost curve | Steeply superlinear at the top (hardware + licenses) | Roughly linear in machines, superlinear in humans and tooling |

The guarantee asymmetry is the part interviews miss: **scale-up preserves every guarantee and raises price; scale-out preserves capacity and lowers guarantees.** Choosing scale-out is choosing which invariants you will now enforce in application code.

## Step 4: When Each Wins

**Scale-up wins** when: the working set fits (or can be made to fit) in one machine's RAM; the data model is transactional and relational; growth is 2–10×; the team is small; the workload is latency-sensitive per transaction (one coordinator, no cross-network commits). This is most B2B products, most startups, most line-of-business databases — hence the honest headline: a well-tuned single PostgreSQL or MySQL machine serves staggering numbers of applications, and "we'll need to shard" is usually a prediction about a product that has not found market fit.

**Read replicas (the middle step) win** when reads dominate: they are configuration, not architecture — hours to deploy, no schema change, no 2PC — with the explicit limit that they scale read *concurrency*, not per-query cost or write throughput ([replication modes](./replication-modes.md) for the consistency price of reading from them).

**Scale-out wins** when: write or data volume is genuinely beyond one machine (multi-TB working sets, write rates that saturate one node's fsync path); the access pattern is key-addressable (point reads/writes by a natural shard key, i.e., the workload matches [key-value access](../../dbms/nosql/key-value.md)); the product is multi-tenant where tenant = shard (isolation for free); global placement matters (data locality to users); or the serial fraction s has already been engineered near zero by design.

**The 10×-then-re-architect rule:** scale-up to buy the next 10× cheaply *while re-architecting the specific bottleneck* — not "scale up forever", and not "shard everything now". The re-architecture is targeted: make the shard key the access path, kill global constraints, move hot counters out of the transactional path.

## Step 5: Edge Cases and Counterexamples

- **The single-writer bottleneck sharding cannot fix — the global counter.** Shard the users table 64 ways and the `UPDATE counters SET n = n + 1` row is still one row on one shard, now serving the *entire* system's increments — sharding multiplied the load on it. The fixes are orthogonal to scale-up-vs-out: shard the counter into buckets and sum (loses exactness across buckets mid-flush), or move it out of the serial path (atomic INCR in Redis, queue-and-aggregate) — the full treatment is in [hot keys and sharded counters](../../distributed/advanced/hot-keys-and-sharded-counters.md). Lesson: **sharding parallelizes data, not contention**; a hot row is a serialization point no topology removes by adding nodes.
- **Engines and models that shard badly.** SQLite is single-writer by design ([internals](../../dbms/internals/sqlite-internals.md)) — "just shard it" means "replace the engine". Full-text indexes, graph traversals, and anything whose *query* pattern is "match across the whole corpus" resist key-based partitioning: the query, not the data, crosses shards. Serializable global ordering (a strict sequence for event sourcing) is a consensus problem, not a partitioning one. When the model resists the key-based split, scale-up buys more time than any premature partitioning scheme.
- **The license cliff that flips the economics.** A 4-socket Oracle estate can hit a point where one more core-year costs more than the engineering of a shard key — per-core licensing makes scale-out *cheaper than scale-up at the top end* even for workloads where scale-up is technically superior. The crossover is financial as well as architectural; both curves belong on the whiteboard.
- **NUMA: the soft ceiling that looks like a hard one.** A team sizes up to a 2-socket box, sees per-core throughput *fall* as they add sockets, and concludes "vertical scaling is dead". The mechanism is cross-socket memory latency, and the countermove is engine-level: NUMA-aware buffer-pool partitioning and pinned threads recover most of it (see [virtual memory, NUMA](../followup-tree/virtual-memory.md)). Measure with NUMA locality metrics before declaring the hardware ceiling.
- **The 2PC stall that sharding imported.** A checkout flow spanning orders, payments, and inventory shards now commits via 2PC; a network blip between prepare and commit holds locks across three shards — and one wedged coordinator stalls transactions system-wide. The mitigations (coordinator replication, saga compensation, keeping related keys co-located by design) are real engineering — which is exactly why "add nodes" is not free capacity: it imports a failure class the monolith-box never had ([distributed transactions](../../dbms/transactions/distributed.md)).
- **Premature scale-out as self-inflicted Amdahl.** A five-engineer team shards from day one "to be ready"; every feature now pays cross-shard joins, and the *serial fraction of engineering time* — every query shaped around the shard key — becomes the dominant cost. Scale-out's Amdahl term applies to people too: sharded systems serialize developer throughput on key discipline.

## Step 6: Decision Framework

1. **Name the bottleneck with a measurement** (write throughput? working set? read QPS? per-query latency?). Direction follows from the name, not the anxiety.
2. **Working set or read concurrency?** RAM-first scale-up, then read replicas — the cheap 80%; revisit only when replicas stop helping ([replication-modes](./replication-modes.md)).
3. **Write-bound and one machine saturated?** First: make the serial path cheaper (hot counters out of the transaction, batch, async). Then: partition *that specific dataset* along the natural access key.
4. **Can every query be answered from one partition by design?** Yes → sharding is viable. No (cross-corpus queries, global constraints, multi-key transactions) → either co-locate by design or stay vertical and pay the license/hardware curve consciously.
5. **Price both curves including humans:** per-core licenses + hardware at the top end vs resharding tooling, per-shard ops, and coordinator complexity. The crossover is where they meet — project it, don't feel it.
6. **Plan the 10× move, not the 1000× move:** scale up (or replicas) now; keep the shard key design sketched for the day the measured wall arrives. Re-architecting *at* the wall is survivable; living in a premature sharded estate for three years usually is not.

## Interview Questions

1. **"Just shard it" — what three costs does that sentence hide?** Cross-partition transactions (2PC round trips and blocking failure), distributed joins (data shipping or partial-merge), and resharding (moving data under load forever, plus hot-partition management). Sharding preserves capacity and *lowers guarantees*; naming which invariants move into application code is the senior answer.
2. **Why can read replicas be the wrong "first horizontal step" even though they are cheap?** They scale read *concurrency*, not per-query cost — a slow join runs identically on every replica — and they do nothing for write throughput. When the bottleneck is the query or the write path, replicas add consistency complexity (staleness) without touching the constraint ([database-choices](./database-choices.md) has the join case; [replication-modes](./replication-modes.md) the staleness case).
3. **A system is sharded 64 ways and one logical counter row is the bottleneck. Why doesn't sharding help, and what does?** Sharding parallelizes *data placement*, not *contention*: the counter is a single serialization point regardless of topology. Fix the contention shape — bucket the counter and sum, or move the increment to an atomic/async path — not the partition count ([hot keys and sharded counters](../../distributed/advanced/hot-keys-and-sharded-counters.md)).
4. **Use Amdahl to explain when adding shard nodes makes throughput worse.** If cross-shard coordination grows with N (transactions touching more shards, more coordinator work), the serial fraction s is a function of N, not a constant. Past the crossover, per-node parallel gain (1−s)/N shrinks while s inflates — total throughput falls. Project s(N) before adding nodes; measure the cross-shard transaction share first.
5. **A workload is outgrowing its box; the database is Oracle EE per-core licensed. Walk the economic part of the decision.** Scale-up cost curve: hardware × superlinear top-end pricing × per-core license fees × options (RAC). Scale-out cost: near-linear machines but resharding tooling, operational headcount, and lower transactional guarantees. The license term often flips the answer to scale-out *earlier than engineering would* — both curves, including human cost, go on the whiteboard before "re-architect" is announced.

## Key Takeaways

- The choice is about the **serial fraction**, not box count: scale-up attacks Amdahl's s (faster single path, one coordinator); scale-out attacks (1−s) and only pays off when coordination grows slower than data.
- Scale-up preserves every transactional guarantee and has a soft ceiling (NUMA decay, RAM top-end, per-core licenses); scale-out preserves capacity and has a hard tax (2PC, distributed joins, resharding, hot partitions, headcount).
- Read replicas are the correct cheap first horizontal step — and are commonly misapplied to write or per-query bottlenecks they cannot touch.
- Contention is not partitioning: hot rows, global counters, and single-writer engines survive every topology change; fix the contention shape or move it off the serial path.
- The durable rule is 10×-then-re-architect: buy the next 10× vertically while naming and engineering the one bottleneck that will force the horizontal redesign.

## Cross-References

- [Relational DBs Don't Scale: Misconceptions](../misconceptions/relational-dbs-dont-scale.md) — the false claim this page's default rule answers.
- [Database Choices](./database-choices.md) — sibling page: the schema/index/concurrency decisions that interact with scaling direction.
- [Replication Modes](./replication-modes.md) — sibling page: what read replicas promise and cost.
- [Amdahl's Law](../../arch/performance/amdahl.md) — the crossover arithmetic in full.
- [Database Sharding](../../dbms/advanced/database-sharding.md) and [Sharding](../../dbms/distributed/sharding.md) — engine-level sharding mechanics.
- [Partitioning Strategies](../../distributed/partitioning/README.md) and [Consistent Hashing](../../distributed/partitioning/consistent-hashing.md) — how keys map to nodes and what resharding moves.
- [Hot Keys and Sharded Counters](../../distributed/advanced/hot-keys-and-sharded-counters.md) — the contention-vs-topology edge case.
- [Two-Phase Commit](../../dbms/transactions/two-phase-commit.md) and [Distributed Transactions](../../distributed/advanced/distributed-transactions.md) — the blocking failure sharding imports.
- [Vitess Sharding Proxy](../../dbms/advanced/vitess-sharding-proxy.md) — the tooling layer that makes scale-out operable.
- [SQLite Internals](../../dbms/internals/sqlite-internals.md) — the single-writer engine that cannot "just shard".
- [More Threads, Faster: Misconceptions](../misconceptions/more-threads-faster.md) — why cores alone (vertical *or* horizontal) do not add throughput.
- [Virtual Memory: Follow-up Tree](../followup-tree/virtual-memory.md) — NUMA mechanics behind the soft scale-up ceiling.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
