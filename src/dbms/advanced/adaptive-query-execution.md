# Adaptive Query Execution: Re-Optimizing the Plan While It Runs

The optimizer commits to a physical plan before the first row is read. When its
estimates are right, that commitment is a feature - zero planning overhead at
run time. When they are wrong, the plan still runs to completion: a join
estimated at 10K rows that turns out to hold 900M executes with a memory-
bounded hash table that spills continuously, or a broadcast that ships a 40 GB
build side to every node. Adaptive query execution (AQP) closes this gap: it
treats the running plan as provisional, measures actual intermediate data as
it flows, and rewrites the remaining plan at the points where a rewrite is
still legal.

## The classic failure: one plan, one guess, 200 partitions

A join keyed on a low-cardinality column is the textbook case. Suppose a fact
table is joined on `status`, whose 8 values are not remotely uniform - the
optimizer has no frequency histogram for the column, so it assumes uniform
spread across 200 shuffle partitions:

```text
planned view of the shuffle (what the optimizer believed)
  p000..p199 : each ~ 500K rows   -> 200 uniform tasks, 8 slots, ~63s

actual shuffle contents (what arrives at runtime)
  p014 : 86,000,000 rows (86% of the table - "completed")
  p031 :   6,000,000 rows  p058 :   4,000,000  p117 :   2,500,000
  p140 :     900,000 rows  p166 :     350,000  p183 :     250,000
  p007,p102:     250,000   remaining 192 partitions: 0 rows
```

One task now owns 86% of the data. The other 192 tasks finish in the first
seconds; 7 of 8 slots sit idle through the entire tail while one task grinds
through 86M rows. No amount of extra slots helps, because the parallelism was
fixed at plan time - splitting a partition after tasks have launched requires
knowing it was oversized before it was too late. The worked simulation at the
end of this page reproduces this scenario.

Cardinality estimation itself - the machinery that produces these wrong numbers
and why - is covered in [Cardinality Estimation](./cardinality-estimation.md);
the optimizer framework that consumes them is in
[Cascades Query Optimizer](./cascades-optimizer.md). The question here is
different: once a guess is committed into a plan, how and when can the engine
correct it?

## Runtime feedback: what the engine can measure while it runs

Every plan has natural observation points. The most important is the
**exchange operator** - the shuffle, redistribute, or materialization barrier
between stages. All data in a distributed plan already flows through exchanges,
so recording row counts, byte sizes, and per-partition distribution there costs
almost nothing beyond the accounting itself. This is the pattern Microsoft's
SCOPE/Cosmos engine generalized: statistics gathered at exchanges are relayed
to the controller, which re-plans later stages of the same job from observed
instead of estimated sizes. Ranking the signals by cost:

| Feedback signal | Where collected | Cost | What it can correct |
|-----------------|-----------------|------|---------------------|
| rows/bytes per partition | exchange (shuffle map output) | ~free | partition coalescing, splitting, broadcast decision |
| actual rows out of a filter | operator close-out | ~free | downstream estimates after first barrier |
| hash table size / spill count | join operator | cheap (counter) | memory grants, algorithm choice for later stages |
| sampled input distribution | during a blocking operator's work | moderate | join strategy and order re-planning |
| per-tuple routing latency | eddy scheduler | cheap | operator ordering in a pipeline (see below) |

The cheap signals are the ones production systems act on; the moderate one
(Kabra and DeWitt's sampling) is the exception, described next.

## Where a running plan can legally change

A plan is not a monolith; it is pipelined subtrees separated by materialization
(blocking) boundaries. Inside a pipeline, tuples flow incrementally and no
operator can stop and renegotiate without stalling everything upstream. At a
boundary, though, the full intermediate result exists on disk or in memory,
its size is exactly known, and the consuming subtree can be discarded and
re-planned from scratch. These boundaries are the **re-optimization points**
of a plan: sort outputs, hash-build completions, aggregation materializations,
stage barriers in a shuffle-execution DAG.

Three families of mechanisms use them, with different aggressiveness:

```text
plan-based re-optimization (one or few checkpoints)

  scan -> filter -> [SORT] ==> X <== re-plan boundary
                             |  (actual rows known here)
                             +-> join -> agg -> out
      upstream salvaged      ^ downstream may be swapped for a fresh plan

continuous adaptation (eddies - no fixed plan at all)

  tuples -> [ eddy ] -> out      every tuple routed by a scheduler that
                                 keeps rate/latency stats per operator
```

- **Checkpoint re-optimization.** At each boundary the engine compares observed
  vs estimated cardinalities - cheaply, by sampling the half-built intermediate
  result while the blocking operator is still materializing it. If deviation
  exceeds a threshold, the optimizer is re-invoked for the remainder of the
  query, reusing ("salvaging") completed work. Kabra & DeWitt formalized this;
  Cole and Graefe (1994) earlier proposed pre-computed *alternate* operators -
  a join compiled as hash that can switch to merge mid-run without losing
  state, so the switch need not wait for a full barrier.
- **Proactive re-optimization.** Babu, Bizarro and DeWitt (2005) observed that
  instrumenting everything is wasteful; their scheme statically analyzes the
  plan to find the points where a re-plan would plausibly trigger and
  instruments only those, checking *before* the expensive stage starts.
- **Continuous adaptation (eddies).** Avnur and Hellerstein (2000) removed the
  plan as a first-class object: an "eddy" routes each tuple to one of several
  stateful operators (symmetric hash joins), adapting the routing per-tuple
  from throughput statistics. Finest granularity, but state must live in every
  operator and behavior is hard to explain after the fact.

Deshpande, Ives and Raman's survey (2007) sorts this landscape into plan-based,
CQ-based, and routing-based AQP; deployed systems have overwhelmingly chosen
checkpoint-based plan mutation, which stays explainable while catching the
worst mistakes.

## Spark AQE: checkpoint adaptation at scale

Apache Spark's AQE (default-on since Spark 3.2) is the most widely deployed
implementation and maps one-to-one onto the checkpoint model: after every
shuffle (exchange) the engine sees exact map-output statistics and is free to
re-plan everything downstream of that shuffle. Three mutations are enabled:

1. **Shuffle-partition coalescing.** After the map stage, adjacent small
   partitions are merged up to `spark.sql.adaptive.advisoryPartitionSizeInBytes`
   (64 MB default), restoring task granularity that a wrong
   `spark.sql.shuffle.partitions` choice would otherwise ruin.
2. **Skew join splitting.** A partition exceeding
   `spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes` (256 MB) and
   more than `spark.sql.adaptive.skewJoin.skewedPartitionFactor` (5) times the
   median is split into sub-partitions, each paired with a replicated copy of
   the matching build-side partition.
3. **Join strategy switching.** A sort-merge join planned because the build
   side was estimated too large becomes a broadcast hash join once the actual
   shuffle output fits under `spark.sql.adaptive.autoBroadcastJoinThreshold`;
   the same statistics can select shuffled-hash where sort order is useless.

The controller only ever mutates plan fragments downstream of a materialized
exchange, so no running task is interrupted - adaptation is strictly between
stages. That is the design's whole trick: it sidesteps hot-swapping live
operators (Cole & Graefe's alternates, eddies) by choosing re-optimization
points that are already natural barriers. Spark's AQE mechanics and their
tuning context are also summarized in
[Spark Internals](../../data-engineering/spark-internals.md).

## SQL Server: adaptive operators inside a classic engine

SQL Server 2017 introduced a family Microsoft documents as Adaptive Query
Processing, under a different constraint than Spark: the engine runs
Volcano-style iterators (see [Advanced Execution Engines](./execution-engines.md)),
so adaptation must happen inside operator logic rather than between stages.
Its three features:

- **Batch-mode adaptive joins.** A single plan contains a hybrid join operator
  that starts as a hash join; after consuming a threshold number of build-side
  rows it compares the actual count against a precomputed break-even point and
  commits to either hash or nested loops. One plan, both algorithms, decision
  deferred until the data speaks.
- **Memory grant feedback.** If a query's memory grant is persistently
  oversized (discarded reservation) or undersized (spilling to tempdb), the
  engine adjusts the grant on the next execution of the same plan and persists
  the correction in the plan cache. Iterative, cross-execution adaptation
  rather than intra-query.
- **Interleaved execution.** Multi-statement table-valued functions - whose
  cardinality was historically a fixed guess - pause optimization: the first
  statement runs, its actual row count feeds back, and only then is the
  enclosing plan finalized.

The iterator constraint shows: SQL Server adapts at operator granularity and
across executions, Spark at stage boundaries within one execution. Both are
checkpoint models; neither tries to reschedule live pipelines.

## The price of adaptivity

Adaptive execution is not free, and its failure modes are distinct from
static planning's:

| Cost / failure mode | Mechanism | Mitigation in practice |
|---------------------|-----------|------------------------|
| instrumentation overhead | extra counters, exchange stats, occasional sampling | Spark: negligible (~statistics piggyback on exchange); sampling-based: only at blocking operators |
| re-optimization latency | re-invoking the optimizer mid-query adds seconds on big plans | only re-plan at boundaries; cache and reuse re-planned fragments |
| thrash between plans | oscillating estimates trigger repeated re-plans | hysteresis thresholds (re-plan only on >N% deviation) |
| lost locality after split | skew-split partitions re-read the build side | replicate only the needed build partition |
| nondeterministic plans | same query, different plan depending on data/arrival | log the chosen post-reopt plan next to the query history |
| wasted speculative work | proactive instrumentation that never fires | static analysis of likely trigger points (Babu et al.) |

Two corollaries matter in practice. Adaptivity substitutes for - but does not
eliminate - statistics maintenance: SQL Server pairs runtime feedback with an
automatic statistics tuner (the LEO project lineage) so the *next* compile is
also better. And the more often a plan mutates, the harder regressions are to
attribute; engines therefore expose the final adapted plan in explain output
(Spark's `EXPLAIN` shows the post-adaptation DAG), and reading that as ground
truth is the first debugging habit to learn. Vectorized operators, which these
features assume, are covered in [Vectorized Execution](./vectorized-execution.md).

## Worked simulation: splitting the fat partition

Simulation of the opening scenario, pure stdlib and deterministic (md5-based
hash placement, no RNG):

```python
"""Skew-partition splitting simulation (Spark AQE-style).

A shuffled hash join keyed by a low-cardinality status column: the optimizer
sees uniform stats and plans 200 shuffle partitions, but one status owns 86%
of the rows. Without AQE every planned partition is one task; with AQE the
engine reads actual map-output sizes, splits the skewed partition, coalesces
tiny ones. Simulated on 8 worker slots at 1M rows/sec/task. No RNG.
"""
import hashlib

ROWS_PER_SEC_PER_SLOT = 1_000_000
SLOTS = 8
PLAN_PARTITIONS = 200
ADVISORY_ROWS = 12_000_000          # ~ target task size after splitting
SKEW_FACTOR = 5                     # task must be 5x median AND > 64M rows to split
SKEW_MIN_ROWS = 64_000_000

# status -> row count in the fact table (zipf-ish, the classic case)
STATUS_ROWS = {
    "completed":  86_000_000,
    "failed":      6_000_000,
    "pending":     4_000_000,
    "returned":    2_500_000,
    "cancelled":     900_000,
    "shipped":       350_000,
    "held":           150_000,
    "queued":         100_000,
}

def md5_mod(s: str, m: int) -> int:
    """Deterministic hash placement of a key into a partition."""
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % m

# --- partition rows exactly as a hash shuffle would -------------------------
partition_rows = [0] * PLAN_PARTITIONS
for status, n in STATUS_ROWS.items():
    partition_rows[md5_mod(status, PLAN_PARTITIONS)] += n

# --- schedule helper: greedy assignment of tasks (sorted big-first) ----------
def makespan(task_rows, slots):
    slots_free = [0.0] * slots
    for rows in task_rows:                      # Spark submits larger tasks first
        i = min(range(slots), key=lambda k: slots_free[k])
        slots_free[i] += rows / ROWS_PER_SEC_PER_SLOT
    return max(slots_free)

# --- plan without AQE: every planned partition = one task --------------------
no_aqe_tasks = [r for r in partition_rows if r > 0]
t_noaqe = makespan(sorted(no_aqe_tasks, reverse=True), SLOTS)

# --- plan with AQE: split skewed, coalesce tiny, then schedule ---------------
alive = [r for r in partition_rows if r > 0]
median = sorted(alive)[len(alive) // 2]
aqe_tasks = []
split_parts = 0
for r in alive:
    if r > SKEW_FACTOR * median and r > SKEW_MIN_ROWS:
        k = -(-r // ADVISORY_ROWS)              # ceil division
        base, rem = divmod(r, k)
        aqe_tasks.extend([base + 1] * rem + [base] * (k - rem))
        split_parts += 1
    elif r < ADVISORY_ROWS // 4:                # too small: candidate for coalesce
        aqe_tasks.append(r)
    else:
        aqe_tasks.append(r)
# coalesce the tiny ones greedily up to the advisory target
aqe_tasks.sort(reverse=True)
coalesced, buf = [], 0
for r in aqe_tasks:
    if buf and buf + r > ADVISORY_ROWS:
        coalesced.append(buf); buf = r
    else:
        buf += r
if buf:
    coalesced.append(buf)
t_aqe = makespan(sorted(coalesced, reverse=True), SLOTS)

print(f"fact rows {sum(STATUS_ROWS.values()):,} | status NDV {len(STATUS_ROWS)} "
      f"| planned partitions {PLAN_PARTITIONS} | slots {SLOTS}")
print(f"actual non-empty partitions: {len(alive)} "
      f"(largest {max(alive)/1e6:.1f}M rows = {max(alive)/sum(partition_rows)*100:.0f}% of data)")
print()
print(f"AQE off : {len(no_aqe_tasks)} tasks, makespan {t_noaqe:6.1f} s "
      f"(one task holds all {max(alive):,} skew rows)")
print(f"AQE on  : {len(coalesced)} tasks after splitting {split_parts} skewed "
      f"partition(s) and coalescing, makespan {t_aqe:6.1f} s")
print(f"speedup : {t_noaqe/t_aqe:.2f}x")
print()
print("AQE task sizes (M rows, scheduled big-first on 8 slots):")
print("  " + " ".join(f"{r/1e6:5.1f}" for r in sorted(coalesced, reverse=True)))
```

```text
fact rows 100,000,000 | status NDV 8 | planned partitions 200 | slots 8
actual non-empty partitions: 8 (largest 86.0M rows = 86% of data)

AQE off : 8 tasks, makespan   86.0 s (one task holds all 86,000,000 skew rows)
AQE on  : 10 tasks after splitting 1 skewed partition(s) and coalescing, makespan   20.8 s
speedup : 4.14x

AQE task sizes (M rows, scheduled big-first on 8 slots):
   10.8  10.8  10.8  10.8  10.8  10.8  10.8  10.8  10.0   4.0
```

Read the numbers the way an interviewer would want: the 86-second tail is not
a throughput problem but a *granularity* problem - the last runnable unit of
work is 86M rows and nothing else can hide it. Splitting converts that one
unit into 8 parallel ones; coalescing the small partitions keeps the rest from
becoming scheduling overhead. The 4.14x speedup comes entirely from deferring
two decisions until real sizes were known.

## References

- Apache Spark: [Adaptive Query Execution section, SQL Performance Tuning guide](https://spark.apache.org/docs/latest/sql-performance-tuning.html)
- Microsoft Learn: [Intelligent query processing in SQL Server (adaptive joins, memory grant feedback, interleaved execution)](https://learn.microsoft.com/en-us/sql/relational-databases/performance/intelligent-query-processing?view=sql-server-ver16)
- N. Kabra, D. DeWitt, [Efficient Mid-Query Re-Optimization of Sub-Optimal Query Execution Plans](https://doi.org/10.1145/276305.276315), SIGMOD 1998
- R. Avnur, J. Hellerstein, [Eddies: Continuously Adaptive Query Processing](https://doi.org/10.1145/335191.335420), SIGMOD 2000
- A. Deshpande, Z. Ives, V. Raman, [Adaptive Query Processing](https://doi.org/10.1561/1900000001), Foundations and Trends in Databases 1(1), 2007
