# Distributed Query Execution: Exchanges, Joins, and Aggregation at Scale

A single-node optimizer only decides *what* to compute: scan order, join
algorithms, memory grants. A distributed engine must additionally decide *where*
every piece of work runs and *what crosses the network* — and the network is
100–1000× slower per byte than local memory, so data movement dominates. The
design object that carries this decision is the **exchange operator**: the only
point in a physical plan where data is repartitioned between workers. Nearly
every distributed-query interview question — slow sharded joins, skew, global
aggregation, wrong LIMIT results — reduces to "what exchanges did the planner
choose, and why were they wrong for this data?"

Placement fundamentals (how tables get split) are in
[Database Sharding](./database-sharding.md) and
[Partitioning Schemes](../../distributed/partitioning/README.md); this page
assumes data is already spread and asks how a query executes across it. The
stage-DAG view for one system is in [Spanner SQL Execution](./spanner-sql.md);
TiDB's storage-side pushdown is in [TiDB Internals](./tidb-internals.md).

## Plan fragments and the exchange operator

A logical plan is location-agnostic. The distributed physical planner cuts it
into **fragments** (Spark and Spanner: *stages*, TiDB: *MPP tasks*): a fragment
is a maximal subtree connected without an exchange, and exchanges are its only
exits and entrances.

Graefe's Volcano exchange (1990) made this an ordinary operator rather than
special-cased machinery. An exchange does three jobs that used to be scattered
through the engine: **partitioning** (how an operator's work divides among
workers), **distribution** (which worker gets which rows), and
**demand/synchronization** (when the receiving side may start and consume).
The encapsulation is the point: the rest of the plan is *unchanged* whether the
subtree below an exchange executes serially, threaded, or on another machine —
which is why one optimizer produces both single-node and distributed plans, and
why an engine can parallelize without rewriting operators.

Two execution shapes exist for running the fragment DAG:

- **MPP, push-based.** Each fragment is instantiated as many tasks, one per
  partition; upstream tasks push row blocks down through exchanges. TiDB's MPP
  mode literally names the pair — `ExchangeSender` serializes a fragment's
  output (Hash, Broadcast, or PassThrough) and `ExchangeReceiver` ingests it
  upstream; Spanner stages ship column batches over RPC; Greenplum's ORCA
  optimizer costs equivalent "Motion" operators.
- **Volcano-over-network, pull-based.** The coordinator calls `next()` across
  the network boundary: PostgreSQL foreign-data-wrapper federation, and
  MongoDB's `mongos`, which runs per-shard pipeline fragments and merges
  results at the router.

The shape matters in interviews: a pull-based coordinator is on the critical
path of every batch (bottleneck *and* blast radius), while push-MPP moves data
worker-to-worker and the coordinator only tracks metadata.

Every distributed plan also ends in a **gather**: a singleton exchange funnelling
the final fragment to one coordinator. It is unavoidable, and it is the natural
place to watch result-set-size runaway.

```text
SELECT region, sum(amount) FROM orders JOIN customers USING (cid)
GROUP BY region ORDER BY 2 DESC LIMIT 10

F1 (per worker):  Scan(customers)
F2 (per worker):  Scan(orders) ──┐
        both sides hash-repartitioned on cid        <- shuffle exchange
F3 (per worker):  HashJoin → partial (region; sum,count)
        partial groups → coordinator               <- gather exchange
F4 (coordinator): merge partials → top-10 → client
```

### Local versus global optimization

Each fragment is optimized like a normal plan — predicate pushdown, join
algorithm, vectorization (see [Execution Engines](./execution-engines.md)). But
decisions that *cross* fragments are global: join distribution (broadcast vs
shuffle), partition counts, fragment placement. These carry a cost the local
model cannot see — network bytes — so engines either enumerate them in a
cost-based optimizer (ORCA's contribution: costed Motion alternatives) or leave
them to heuristics and hints. A locally optimal join order can be globally
wrong: reordering joins to save a scan is a micro-optimization if it forces a
500 GB shuffle that broadcast would have avoided.

The exchange cost model, one line each: **shuffle** both sides of a join ≈
|A| + |B| bytes; **broadcast** the build side ≈ N × |build| bytes (N = nodes);
**gather** ≈ result-set bytes. Hence the universal rule: *never move what you
can filter or aggregate in place* — predicate and partial-aggregate pushdown
shrink every exchange downstream. TiDB's coprocessor (filters and partial
aggregation inside storage regions) and Spanner's distributed scans are both
instances (see [TiDB Internals](./tidb-internals.md)).

## The three exchange modes

| Mode | What moves | Network cost | Used for |
|---|---|---|---|
| Shuffle / hash repartition | both inputs rehashed on the key | \|A\| + \|B\| | large-large joins, GROUP BY on any key |
| Broadcast | build side replicated to every node | N × \|build\| | small-large joins |
| Gather | all results to one coordinator | result size | final stage, `LIMIT` |

### Shuffle: hash repartitioning on the join key

Both sides are hashed on the join key into P partitions; because both sides use
the same hash function, all rows with matching keys land in the same partition
and the join becomes local per partition. Two engineering details matter:

- **P is chosen ≫ N** (Spark defaults to 200 shuffle partitions; TiDB MPP
  splits fragments into many tasks). Fewer partitions than tasks makes the
  plan rigid — you cannot split a straggler partition later without another
  exchange. This is the same virtual-shard logic as
  [sharding](./database-sharding.md), applied per query.
- The routing is **deterministic and side-symmetric**: no metadata lookup, no
  coordination, retry-safe (a replayed task produces the same destinations).

### Broadcast: when replicating the small side wins

Broadcast skips the probe side's exchange entirely: every worker builds a hash
table of the full build side, then joins its local slice of the probe side.
Arithmetic beats shuffle when N × |build| < |build| + |probe| — whenever the
build side is small relative to the probe side *and* the probe side is already
distributed. Spark's `autoBroadcastJoinThreshold` default is 10 MB; Trino's
`join_distribution_type` session property exposes
`AUTOMATIC`/`BROADCAST`/`PARTITIONED` explicitly, and its docs note broadcast
wins when the build side is much smaller than the probe side, but requires the
build table to fit on every worker.

**Broadcast is a statistics bet, and the failure mode is multiplicative.** The
planner estimates the build side from optimizer statistics (see
[Cardinality Estimation](./cardinality-estimation.md)). If stale stats or an
unanalyzed staging table say 8 MB when reality is 40 GB, every one of N nodes
attempts a 40 GB hash table simultaneously — one bad estimate becomes N
simultaneous OOMs, seconds into the query. A wrong shuffle decision costs one
extra pass; a wrong broadcast decision costs the whole cluster. Defenses, in
order of preference: **hard caps** that refuse to broadcast above a size
regardless of estimates (Trino caps the replicated table size explicitly);
**runtime re-decision** — measure the actual exchange output and switch the
remaining plan (Spark AQE converts sort-merge to broadcast and back at stage
boundaries, see [Adaptive Query Execution](./adaptive-query-execution.md)); and
**hints as escape hatches** when you know the data better than the optimizer
(Spark's `/*+ BROADCAST(t) */`, `/*+ MERGE(t) */`, `/*+ SHUFFLE_HASH(t) */`).

Broadcast also has a quiet superpower: it is **probe-skew-immune**. The probe
side is never repartitioned, so no join key — however hot — creates a shuffle
hotspot, and the fully-replicated build side needs no balancing. One reason
skewed joins are often best fixed by broadcasting the small side rather than by
clever partitioning.

## Distributed joins

Join strategies in a distributed engine are exchange placements. For
`A ⋈ B`:

1. **Co-located join** — both tables are already partitioned on the join key
   *by construction* (the shard key is the join key), so the fragment joins
   local data with **zero exchanges**. This is schema design acting as
   query optimization: co-partitioning eliminates the shuffle permanently,
   not per query. Systems expose it through placement primitives —
   CockroachDB co-locates ranges and can pin rows to regions
   (`REGIONAL BY ROW` tables keep each row near its home region's
   leaseholders); TiDB's [placement rules](https://docs.pingcap.com/tidb/stable/placement-rules-in-sql)
   pin regions by label so a join lands on one store; Spanner's
   `INTERLEAVE` physically nests child rows inside their parents (see
   [Spanner SQL Execution](./spanner-sql.md)). The cost of co-partitioning is
   rigidity: choose the partitioning for your *most frequent expensive join*,
   and every other join pays an exchange (the tradeoffs are the shard-key
   discussion in [Database Sharding](./database-sharding.md)).
2. **Shuffle (repartitioned) join** — both sides exchanged on the join key.
   The default for large-large joins on arbitrary keys; cost = both tables
   over the network once.
3. **Broadcast join** — covered above; best for small-large.
4. **Lookup-style distributed join** (Spanner "Cross Apply", CockroachDB
   "lookup join") — the probe side stays put and issues per-row (or per-batch)
   point lookups to the other side's owner. Cost is one RPC per probe row, so
   it is superb when the inner side is indexed and the outer side is
   selective, and catastrophic when it is not: 1M outer rows mean 1M RPCs, and
   at ~100 µs each the RPC overhead alone is on the order of a minute — which
   is why Spanner's cost model counts RPCs explicitly (see
   [Spanner SQL Execution](./spanner-sql.md)).

### Joins on non-partition keys: dynamic remapping

A shuffle join can be read as *per-query re-sharding*: the exchange
re-implements a hash-partitioned layout on the join key for exactly the
lifetime of the query, then throws it away. "Ownership" of a key is decided by
the hash function at run time — the planner does not consult where rows are
stored, it remaps them. This is why the strategy generalizes to any key and any
placement, and why it costs: a co-located layout pays once (at write time),
dynamic repartitioning pays per query. The standing rule for schemas follows
directly: **partition by the key your most expensive join uses; let exchanges
handle the rest.** Engines that can change partitioning online
([Online Resharding](./online-resharding.md)) let you re-align placement with
the query workload later, converting recurring shuffle joins into co-located
ones.

### Skew: the within-key problem

Hash exchange assumes keys are roughly uniform. They often are not: one
customer owns 40% of the orders, one status value owns 86% of rows. Then one
partition holds 40% of the data, one worker runs it alone, and N−1 workers
idle through the tail. No amount of adding nodes helps: skew is a
**within-key** problem and parallelism is a **between-key** resource — a
single key's rows cannot be split across workers without changing the
algorithm. The standard fixes, in increasing invasiveness:

- **Broadcast the small side** — eliminates the exchange, hence the skew, when
  sizing allows.
- **Salting** — rewrite the hot key on the large side as `key_0 … key_{s-1}`
  (append a salt suffix) and fan the matching small-side row out to all s
  salts; the hot key becomes s partitions of work. Available as a rewrite or
  as an engine feature (Hive's skew-join optimization, Spark's `/*+ SKEW('rel',
  'key') */` hint names skewed keys so the engine does the fan-out).
- **Dynamic splitting** — at the exchange, detect that one partition exceeds a
  threshold and a skew factor over the median (Spark AQE: 256 MB and 5×),
  split it into sub-partitions, and give each a replicated copy of the
  matching build-side partition. The production-grade version of salting, done
  at run time; the worked simulation in
  [Adaptive Query Execution](./adaptive-query-execution.md) shows a 4×
  makespan win from exactly this mechanism.

## Distributed aggregation: partial → final

A global `GROUP BY` over sharded data is executed in **two phases** — the
combiner pattern from MapReduce, now universal:

1. **Partial (combiner) phase**, computed where the data lives, *before* any
   exchange: each fragment emits per-group *partial states*, not raw rows.
2. **Exchange** on the grouping key — partial states, which are far smaller
   than raw rows (one state per group per fragment, vs one row per record).
3. **Final phase**: merge the partial states per group.

TiDB pushes the partial phase into storage coprocessors; PostgreSQL parallel
queries run PartialAggregate → Gather → FinalAggregate; MongoDB's sharded
aggregation runs per-shard stages and routes the partial results to `mongos`
to be merged. The pattern is the distributed-query application of Gray's
data-cube classification: most aggregates are *distributive* or *algebraic* —
computable by merging partial aggregates — which is exactly what the table
below formalizes. It is also what federated engines do when the wrapper
supports it: postgres_fdw has been able to push aggregate functions to the
remote server "when possible" since PostgreSQL 10, offloading the aggregation
instead of shipping every row.

**Which aggregates split safely** — an aggregate decomposes if its partial
states can be merged associatively:

| Aggregate | Decomposable? | Partial state | Notes |
|---|---|---|---|
| `SUM`, `COUNT`, `MIN`, `MAX` | yes | the obvious scalar | merge = re-apply the same op |
| `AVG` | yes, if decomposed | `(sum, count)` | naive "average of averages" is the classic correctness bug |
| `VAR`/`STDDEV` | yes | `(sum, sum_sq, count)` | textbook parallel formula |
| `COUNT(DISTINCT x)` | **no** | exact value sets per group | needs a two/three-phase plan or a sketch |
| `MEDIAN` / percentiles | **no** | all values, or a sketch | exact median needs materialization |

`AVG` deserves a beat: `(avg₁+avg₂)/2` is wrong whenever groups differ in
size; the partial phase must carry `(sum, count)` and the final phase computes
`sum/count`. Interviewers use this as a two-minute correctness check, and it
generalizes: whenever you invent a partial state for a new aggregate, write
down the merge function and test associativity.

**Distinct aggregation needs an extra shuffle.** `COUNT(DISTINCT user) GROUP
BY region` cannot be finished by merging `(region → set)` states at scale, so
engines insert a second exchange keyed on the *concatenation* `(region, user)`:
phase 1 deduplicates `(region, user)` pairs per fragment; phase 2 (exchange on
`(region, user)`) collapses duplicates across fragments; phase 3 counts per
region. That is why `DISTINCT` inside an aggregate roughly doubles the
shuffles. The alternative is a **mergeable sketch**: HyperLogLog registers
merge exactly like `(sum, count)` states — approximate cardinality with
tiny, bounded memory (see [Sketch Algorithms](./sketch-algorithms.md));
quantile sketches (t-digest) do the same for median. Exact distinct at NDV of
billions means spilling value sets that rival the base table — the
exact/approximate choice is a latency/SLA decision, not an implementation
detail.

When the grouping key *is* the partition key, the whole dance disappears —
groups are co-located and one phase suffices. High-NDV groupings are the
opposite extreme: billions of partial states can exceed the final phase's
memory, so engines spill, and the group-count estimate (again
[Cardinality Estimation](./cardinality-estimation.md)) decides whether partial
aggregation is profitable. `GROUP BY` inherits join skew too: one hot group
key starves the final phase exactly as a hot join key starves a partition —
salting works identically.

## ORDER BY and LIMIT: the top-K merge

`ORDER BY … LIMIT k` has a beautiful distributed answer. Push `(ORDER BY,
LIMIT k)` into every shard: each returns its local top-k (a bounded heap, not
a sort), the coordinator merges the N·k winners and emits the global top-k.
It is correct by an exchange argument: any element in the global top-k is
necessarily in its own shard's top-k. Cost: O(N·k) rows transferred instead of
a full distributed sort. TiDB documents exactly this TopN/Limit pushdown into
its storage layer; Spark and Trino plan the same shape as a per-partition
`TakeOrderedAndProject` followed by a merge.

Two adjacent traps worth stating in interviews:

- **Bare `LIMIT k` without `ORDER BY`** is still pushable (any k rows per
  shard), but the result is nondeterministic — and *appears* stable, which is
  worse. Paginate without a total order and the "same" query may skip or
  repeat rows across runs and shards.
- **Deep `OFFSET`** must be pushed as `LIMIT offset + k` per shard: page
  5,001 (`OFFSET 100000 LIMIT 20`) makes every shard scan and discard 100,020
  rows. Keyset pagination (`WHERE created_at < last_seen ORDER BY created_at
  DESC LIMIT 20`) turns offset into a filter each shard can seek on.
- `ORDER BY` *without* `LIMIT` cannot avoid a full merge sort across shards —
  sort is a pipeline breaker (see
  [Spanner SQL Execution](./spanner-sql.md)); the coordinator either merges
  N sorted streams (k-way merge, streaming-friendly) or materializes
  everything. Sort result sets are where distributed plans go to OOM.

## Fault tolerance during execution

Distributed queries can run for hours on fleets of transient machines, so the
execution model must survive worker death mid-query. The enabling assumption
is that **query inputs are immutable for the query's duration**: table files
under a snapshot, MVCC-consistent reads. Given that, any task can be
re-executed and will produce the same output — which unlocks the design every
mainstream engine chose:

- **Task-level retry.** On node death, re-run the failed task on another
  worker, reading the same inputs. MapReduce re-executes map and reduce tasks;
  Spark recomputes lost partitions from the lineage graph rather than
  replicating intermediates; Presto retries tasks for batch queries.
- **At-least-once at exchange granularity.** Between retries, exchanges do
  *not* do per-row acknowledgments — an ack per tuple would cost a network
  round trip per row and make the exchange slower than the computation.
  Instead a task's output is delivered in full or (after a retry) possibly
  twice; downstream operators are written so replay is idempotent (hash-table
  inserts, partition overwrites). You get exactly-once *semantics* from
  at-least-once *delivery* plus idempotent consumption.
- **Query-level retry** is the blunt instrument: re-run the whole query. It is
  what you fall back to when state is not recoverable per task — coordinator
  crash, a failure inside a sink that already wrote partial output — or when
  the query is short enough that re-running is cheaper than the bookkeeping.

| Retry granularity | Re-executes | Cost | Needed when |
|---|---|---|---|
| tuple ack | one tuple | impossible (1 RTT/row) | never in OLAP engines |
| task | one fragment's partition | seconds–minutes | worker death (default) |
| stage/exchange | one exchange's output | minutes | corrupt/spoiled intermediate |
| query | everything | hours | non-recoverable state, coordinator loss |

The genuinely hard case is the **non-idempotent sink**: a pipeline that writes
to an external table mid-DAG and then fails must not double-write on retry.
Engines commit sinks transactionally at the end (Spark's commit protocol
stages output files and atomically marks success), push sinks to the final
fragment, or record committed partitions for deduplication. Streaming engines
face this continuously and solve it with checkpointed exactly-once sinks —
out of scope here, but the same idempotency core.

## Interview problems

### Problem 1: "A two-table join that took 40 s now takes 2 hours in our sharded MPP database, right after a big backfill. Walk me through what you inspect."

**Solution.** Diagnose the plan before the data. Ordered checklist:

1. **`EXPLAIN` (analyze) — what did each exchange become?** Compare against
   the old plan. The likely headline: the join was **co-located or broadcast**
   and is now a **full shuffle**. A backfill rewrites table data and
   statistics go stale; if the build side's estimated size crossed the
   broadcast threshold in the wrong direction, a 10 MB-class broadcast became
   a two-sided shuffle of the same tables.
2. **Statistics freshness.** A backfill that inserts 500M rows without
   re-`ANALYZE` makes every cardinality estimate fiction: wrong broadcast
   decisions, wrong join order, no skew expectation. Refresh stats first — it
   is the cheapest possible fix and the most common one.
3. **Skew at the exchange.** If the plan shows one shuffle partition taking
   the whole time (task-level metrics: max vs median partition size), the
   backfill concentrated a key. Fix: AQE-style splitting/salting or broadcast
   the small side.
4. **Co-location.** Did the backfill (or a concurrent reshard) move rows off
   the co-partitioned layout? If shard placement no longer matches the join
   key — the classic post-[resharding](./online-resharding.md) regression —
   every query that used to be zero-exchange is now re-sharding both tables
   on every run.
5. **Join order and fragment count.** With stale stats the optimizer may have
   swapped build/probe sides (hash table now built on the 800M-row table) or
   re-ordered joins into a plan that shuffles an intermediate result instead
   of a base table.

The answer that scores: inspect the *exchange types* first — a regression
after a data change is almost always a plan regression (broadcast → shuffle,
co-located → shuffled, or unseen skew), and all three are visible in the plan,
not the data.

### Problem 2: "Design a global GROUP BY over 1 TB spread across 32 nodes."

**Solution.** Fix the shape: partial → exchange → final, with explicit
parameters.

1. **Partial phase** (32 workers, local): filter and project first (rule: never
   exchange what you can drop), then pre-aggregate. Partial state = one row
   per (group × fragment). If NDV (number of distinct groups) is 10M with a
   24-byte state, each fragment's partial output is ≈ 10M × 24 B ≈ 240 MB —
   fine to hold/spill; total exchange traffic ≈ 32 × 240 MB ≈ 7.7 GB, a 130×
   reduction of the 1 TB. If NDV is 2B, partial aggregation barely compresses
   — exchange the *group key columns only* (narrow rows) and do effectively
   one phase.
2. **Exchange**: hash the group key into **P = 256–512 partitions, not 32**.
   More partitions than nodes gives you (a) elasticity — a slow worker's
   partitions can be reassigned; (b) skew granularity — a hot group pollutes
   1/256 of the work, not 1/32; (c) room to split stragglers (AQE) without a
   second exchange. 1 TB of input is not the exchange size — the partial
   states are; size P on *partial-state bytes* per partition (~64–256 MB).
3. **Skew plan**: if one group key is hot (measured or hinted), salt it across
   s sub-groups in the partial phase and merge the s results in the final
   phase; or accept the skew if the hot group is a small fraction.
4. **Failure plan**: task retry on identical snapshot reads; final phase
   idempotent (state merge); if the sink is external, commit at the end or
   record committed partitions.
5. **Result**: gather to the coordinator; if the consumer only wants top-N
   groups, replace the gather with a top-N exchange (per-partition top-N →
   merge).
6. **The DISTINCT follow-up** ("now make it COUNT(DISTINCT user)"): exact →
   second exchange on (group, user), three phases; approximate → HLL sketch
   carried through the original two phases. Say both and the trade
   (shuffle cost vs 0.8% error), and the follow-up is a point for you, not
   against.

### Problem 3 (rapid): "ORDER BY created_at DESC LIMIT 10 across 32 shards — why can't each shard just send its newest row?"

**Solution.** Because the 10 newest overall could be 10 rows from a single
shard; 32 candidates are insufficient by the exchange argument: any global
top-10 element is in its own shard's top-10, so every shard must send *its*
top-10 (320 rows), and the coordinator merges. Push `LIMIT 10` with the
`ORDER BY` per shard — a `LIMIT` alone neither requires nor forbids this, and
without a total order the result is nondeterministic. Cost: O(32·10) rows, vs
a full distributed sort.

## Key Takeaways

- The exchange is the only operator with network cost; plans are fragments
  glued by exchanges, and "optimization at scale" is mostly *exchange
  placement*.
- Shuffle = re-sharding per query (any key, pays per query); co-location =
  sharding chosen at write time (one key, pays once); broadcast = replicate
  the small side, a statistics bet with multiplicative failure.
- Aggregate twice: partial states where data lives, merge after the exchange.
  `SUM/COUNT/MIN/MAX` and properly decomposed `AVG` merge safely;
  `COUNT(DISTINCT)`/`MEDIAN` need an extra shuffle or a mergeable sketch.
- Top-K: push `(ORDER BY, LIMIT k)` to shards, merge N·k winners — correct
  because a global top-k element is always in its shard's top-k.
- Fault tolerance is task retry over immutable inputs + idempotent
  exchanges — at-least-once delivery, exactly-once semantics; per-row acks
  would cost more than the query.

## Cross-References

- [Database Sharding](./database-sharding.md) — placement: the thing that
  decides whether joins need exchanges at all.
- [Online Resharding](./online-resharding.md) — re-aligning placement with the
  join workload over time.
- [Adaptive Query Execution](./adaptive-query-execution.md) — fixing broadcast
  and skew decisions at run time, with a worked skew-splitting simulation.
- [TiDB Internals](./tidb-internals.md) — coprocessor pushdown (partial
  aggregation at storage) and TiFlash MPP exchange operators in production.
- [Spanner SQL Execution](./spanner-sql.md) — stage DAGs, pipeline breakers,
  and RPC-cost modeling of distributed join strategies.
- [Cardinality Estimation](./cardinality-estimation.md) — where broadcast and
  aggregation decisions go wrong.
- [Sketch Algorithms](./sketch-algorithms.md) — mergeable sketches for
  distinct counts and quantiles.
- [Execution Engines](./execution-engines.md) and
  [Vectorized Execution](./vectorized-execution.md) — what runs *inside* a
  fragment.
- [Partitioning Schemes](../../distributed/partitioning/README.md) — hash vs
  range placement fundamentals.

## References

- G. Graefe, [Encapsulation of parallelism in the Volcano query processing system](https://doi.org/10.1145/93597.98720), SIGMOD 1990 — the exchange operator (partitioning, distribution, demand).
- D. DeWitt, J. Gray, [Parallel database systems](https://doi.org/10.1145/129888.129894), Communications of the ACM 35(6), 1992 — partitioned parallelism, the pipeline/slide model of parallel join and aggregation.
- D. DeWitt, S. Ghandeharizadeh, D. Schneider, A. Bricker, H.-I. Hsiao, R. Rasmussen, [The Gamma database machine project](https://doi.org/10.1109/69.50905), IEEE TKDE 2(1), 1990 — hash-parallel joins and the split-then-aggregate execution template.
- J. Gray, S. Chaudhuri, A. Bosworth et al., [Data Cube: A Relational Aggregation Operator Generalizing Group-By, Cross-Tab, and Sub-Totals](https://doi.org/10.1023/A:1009726021843), Data Mining and Knowledge Discovery 1(1), 1997 — the distributive/algebraic aggregate classification behind partial→final merging.
- M. A. Soliman et al., [ORCA: a modular query optimizer architecture for big data](https://doi.org/10.1145/2588555.2595637), SIGMOD 2014 — costed Motion (exchange) alternatives and MPP fragment optimization.
- Y. Sun, T. Meehan, R. Schlussel, W. Xie et al., [Presto: A Decade of SQL Analytics at Meta](https://doi.org/10.1145/3589769), Proceedings of the ACM on Management of Data 1(2), 2023 — stage/exchange execution at fleet scale, task retry for batch queries.
- Trino Documentation, [Concepts](https://trino.io/docs/current/overview/concepts.html) (stage/exchange model) and [Cost-based optimizations](https://trino.io/docs/current/optimizer/cost-based-optimizations.html) (`join_distribution_type`, replicated-table size cap).
- Apache Spark, [SQL Performance Tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html) (`autoBroadcastJoinThreshold` = 10 MB default, AQE partition handling) and [SQL hints](https://spark.apache.org/docs/latest/sql-ref-syntax-qry-select-hints.html) (`BROADCAST`, `SKEW`).
- TiDB Documentation, [Explain Statements in the MPP Mode](https://docs.pingcap.com/tidb/stable/explain-mpp) (`ExchangeSender` Hash/Broadcast/PassThrough) and [TopN and Limit Push-down](https://docs.pingcap.com/tidb/stable/topn-limit-push-down).
- CockroachDB Documentation, [Joins](https://www.cockroachlabs.com/docs/stable/joins) (merge/hash/lookup join algorithms), [Regional Tables](https://www.cockroachlabs.com/docs/stable/regional-tables) (row-to-region co-location), [Architecture Overview](https://www.cockroachlabs.com/docs/stable/architecture/overview.html).
- MongoDB Documentation, [Aggregation Pipeline on Sharded Collections](https://www.mongodb.com/docs/manual/core/aggregation-pipeline-sharded-collections/) — per-shard execution with merge at `mongos`.
- PostgreSQL 10 Release Notes, [postgres_fdw aggregate pushdown](https://www.postgresql.org/docs/10/release-10.html) — the partial/final split applied to federation.
- J. Dean, S. Ghemawat, [MapReduce: Simplified Data Processing on Large Clusters](https://static.googleusercontent.com/media/research.google.com/en/us/archive/mapreduce-osdi04.pdf), OSDI 2004 — combiner pattern; task re-execution as the fault-tolerance unit.
- M. Zaharia et al., [Resilient Distributed Datasets: A Fault-Tolerant Abstraction for In-Memory Cluster Computing](https://www.usenix.org/system/files/conference/nsdi12/nsdi12-final138.pdf), NSDI 2012 — lineage-based recovery instead of replicating intermediates.
- J. C. Corbett et al., [Spanner: Becoming a SQL System](https://research.google/pubs/pub47702/), SIGMOD 2017 — stage-based distributed execution and RPC-aware costing.
