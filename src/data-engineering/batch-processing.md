# Batch Processing

## MapReduce

Programming model for processing large datasets in parallel:

```
Input → Split → Map → Shuffle → Reduce → Output
```

```python
# Word count (classic example)
def mapper(document):
    for word in document.split():
        emit(word, 1)

def reducer(word, counts):
    emit(word, sum(counts))

# MapReduce handles: splitting, shuffling, fault tolerance
```

**Phases:**
1. **Map**: Process input chunks, emit (key, value) pairs
2. **Shuffle**: Group by key, send to reducers
3. **Reduce**: Aggregate values per key

## Apache Spark

In-memory distributed computing framework:

### RDDs (Resilient Distributed Datasets)

```python
rdd = sc.textFile("data.txt")
counts = (rdd
    .flatMap(lambda line: line.split())
    .map(lambda word: (word, 1))
    .reduceByKey(lambda a, b: a + b))
```

### DataFrames (modern Spark)

```python
from pyspark.sql.functions import avg, count, desc

df = spark.read.csv("data.csv", header=True)
result = (df
    .filter(df.age > 25)
    .groupBy("city")
    .agg(avg("salary").alias("avg_salary"),
         count("*").alias("row_count"))
    .orderBy(desc("row_count"))
)
```

### Spark Architecture

```
Driver → Cluster Manager → Executors
         ├── Executor 1 (tasks)
         ├── Executor 2 (tasks)
         └── Executor 3 (tasks)
```

- **Driver**: Runs your application, creates SparkContext
- **Cluster Manager**: Allocates resources (YARN, Mesos, K8s)
- **Executors**: Run tasks, store data in memory

## Apache Airflow

Workflow orchestration platform:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG('etl_pipeline',
         start_date=datetime(2024, 1, 1),
         schedule='@daily',
         default_args=default_args) as dag:
    
    extract = PythonOperator(
        task_id='extract',
        python_callable=extract_data)
    
    transform = PythonOperator(
        task_id='transform',
        python_callable=transform_data)
    
    load = PythonOperator(
        task_id='load',
        python_callable=load_data)
    
    extract >> transform >> load
```

**Key concepts**: DAGs (Directed Acyclic Graphs), operators, sensors, XComs (cross-communication), pools, connections.

## Beyond the Nightly Window: Batch Window Design

The classic batch system is a nightly window: inputs land, a pipeline runs between midnight and the morning deadline, reports refresh. A batch window has two numbers that must not overlap: **freshness** (how stale outputs may be) and **runtime** (how long the pipeline needs). The window collapses when either grows. Three things break a nightly window:

1. **Data volume grows faster than the window.** A full recomputation costs ∝ N (the whole dataset); the daily delta is Δ. Incremental processing costs ∝ Δ plus the cost of touching derived state. The crossover is blunt arithmetic: at 10TB history and 50GB/day of new data, a full nightly recompute burns 200× the work of an incremental pass — but only *additive* transformations (counts, sums, unions) can be incremental at all.
2. **The transformation is non-additive.** Deduplicating across all history, computing percentiles, or applying retractions/corrections means yesterday's output depends on facts that changed today. Then you need either full recomputation (correct, expensive) or incremental machinery keyed on what changed (cheap, complex — the same trade as [Materialized View Maintenance](../dbms/advanced/incremental-view-maintenance.md)).
3. **Inputs arrive continuously.** Once sources stream all day, "nightly input" is fiction; the batch becomes a *micro-batch over a log* or moves to streaming ([Stream Processing](./stream-processing.md)).

The design lever left is **partitioning the computation by time**: process each day's slice separately, so a run's cost scales with Δ, and a failed run only reprocesses its own slice.

## Input Partitioning and Late-Arriving Data

Date-partitioned layout is the batch engine's unit of work and unit of recovery: `events/dt=2024-06-01/`. Partitioning inputs gives you pruning (a one-day backfill reads one day), parallelism (one file set per worker), and atomicity (write a whole partition, then swap it in). But events arrive with *processing time*, not *event time*: a mobile app offline for two days flushes its events after the partition for those days has already been processed. You need a policy, picked explicitly:

- **Reload affected partitions**: late events trigger a re-run for their event-date partition, overwriting it idempotently (next section). Correct and simple; costs a bounded recompute.
- **Grace window**: don't close partition N until N+2; everything later goes to a dead-letter store for manual or periodic repair.
- **Ignore and reconcile**: accept that very-late data lands in a "corrections" pass (finance systems often do corrections as explicit ledger entries instead of mutating history).

## Join Strategies in Batch Engines

Two ways to bring two large inputs together, with opposite cost profiles:

- **Shuffle (sort-merge) join**: both sides are repartitioned by the join key, so matching rows co-locate, then merged per key. The shuffle is the cost: "The shuffle is Spark's mechanism for re-distributing data so that it's grouped differently across partitions. This typically involves copying data across executors and machines, making the shuffle a complex and costly operation" (Spark docs; the mechanics live in [Spark Internals](./spark-internals.md)). Network cost ∝ size of *both* inputs; skew on a hot key makes one reducer the straggler (fix: salting the key).
- **Broadcast join**: if one side is small (rule of thumb: fits in executor memory — hundreds of MB to a few GB), replicate it to every worker and hash-join locally. Zero shuffle for the big side; the cost is the broadcast itself ∝ workers × small-side size. Dimension tables (products, users, geo) joined to event tables are the canonical broadcast case; choosing broadcast vs shuffle is often the single biggest lever on a join's runtime.

## The Small-Files Problem and Compaction

Streaming ingestion and over-partitioning produce millions of small files, which hurts three times: metadata pressure (the catalog/NameNode holds every file; object-store *listing* is O(files)), task scheduling overhead (Spark schedules roughly one task per file), and read amplification (opening a file costs a seek regardless of size). The fix is **compaction**: a periodic job that bin-packs small files into target-sized files (128MB–1GB, aligned to storage block sizes). Modern table formats build it in — Iceberg exposes a `rewrite_data_files` maintenance procedure exactly for this. Design rule: ingestion optimizes for latency (small appends), compaction re-optimizes for read cost, and the two are decoupled through the table format's snapshot mechanism.

## Backfill Patterns: Idempotent Overwrite by Partition

A backfill reprocesses history — a code fix, a new column, a repaired source. The safety rule is **idempotent overwrite**: re-running any partition produces the same result as running it once, so partial failures can simply be retried. The mechanics are per-partition atomic replacement. Delta Lake's `replaceWhere` is designed "to atomically overwrite rows that match a predicate. Use for replacements with a fixed matching condition"; Iceberg's write API makes "overwrite behavior explicit, either dynamic or by a user-supplied filter." The anti-pattern is append-only backfill — re-running doubles every row, and the only cure is dedup at read time forever.

Two table shapes make backfills cheap or expensive:

- **Snapshot tables**: one full copy of state per day (`customers_snapshot/dt=…`). Backfilling day N is self-contained (rebuild that day from inputs); queries are trivial ("state as of date X"); storage ∝ N × table size.
- **Incremental tables**: one row per change (`events`, `changes`). Storage ∝ total changes; "as of date X" queries require replaying/merging up to X (the same snapshot-then-apply-merges trick backups use), and correcting a past day means merging a new *correction* row, not rewriting state.

## Cost Levers

- **Spot/preemptible workers**: batch tasks are stateless and retried by the framework (MapReduce's original fault-tolerance story), so the cluster can run on deeply discounted interruptible capacity — the job slows when nodes vanish but never corrupts. Long-running coordinators (the Spark driver) stay on on-demand nodes.
- **Shuffle storage**: the shuffle is disk- and network-heavy; putting shuffle spill on local NVMe (vs network-attached storage) and sizing executors so shuffle blocks don't spill repeatedly changes runtimes more than CPU count does.
- **Right-size the parallelism**: too few partitions underutilizes the cluster; too many turns scheduling overhead and small-file writes into the bottleneck.

## Dependency DAGs and the Scheduling Handoff

A real pipeline is a DAG of dependencies: raw landing → cleaned tables → dimension/fact builds → aggregates → reports. Within a run, the orchestrator resolves *what* runs when; the batch engine resolves *how* each node executes. [Apache Airflow](./airflow.md) is the batch-era scheduler for these DAGs — cron-like triggers, retries, sensors for upstream readiness. Note the boundary: data-DAG scheduling handles *runs and retries of jobs*, but a business process that must react, wait days, and survive worker crashes across its lifetime needs a durable-execution engine — see [Workflow Orchestration and Durable Execution](../interview/system-design/hld/workflow-orchestration.md) — the two increasingly interoperate (orchestration engines kicking off batch runs as activities).

## References

- [Spark Documentation](https://spark.apache.org/docs/latest/)
- [Airflow Documentation](https://airflow.apache.org/docs/)
- [MapReduce Paper — Dean & Ghemawat](https://research.google.com/archive/mapreduce.html); Dean & Ghemawat, "MapReduce: Simplified Data Processing on Large Clusters," *Communications of the ACM* 51(1), 2008, DOI [10.1145/1327452.1327492](https://doi.org/10.1145/1327452.1327492). *(DOI verified via Crossref this session; Google page fetched.)*
- [Spark RDD Programming Guide](https://spark.apache.org/docs/latest/rdd-programming-guide.html) — "Shuffle operations" section quoted above. *(Fetched.)*
- [Apache Iceberg: Spark Writes](https://iceberg.apache.org/docs/latest/spark-writes/) — explicit dynamic/filter overwrite semantics. *(Fetched.)*
- [Apache Iceberg: Spark Procedures](https://iceberg.apache.org/docs/latest/spark-procedures/) — `rewrite_data_files` compaction maintenance. *(Fetched.)*
- [Delta Lake: Table Batch Reads and Writes](https://docs.delta.io/latest/delta-batch.html) — `replaceWhere` atomic predicate overwrite. *(Fetched.)*

## Cross-References

- [Apache Airflow](./airflow.md) — the scheduler that drives batch DAGs
- [Spark Internals](./spark-internals.md) — shuffle mechanics, stages, and Catalyst in depth
- [Stream Processing](./stream-processing.md) — the counterpart model when windows shrink to zero
- [Workflow Orchestration and Durable Execution](../interview/system-design/hld/workflow-orchestration.md) — durable-execution engines for business processes beyond batch DAGs
- [Data Lakehouses](./lakehouses.md) — the table formats (Delta/Iceberg/Hudi) that implement snapshot semantics and compaction
- [Messaging & Streaming](../distributed/messaging/messaging-streaming.md) — the log infrastructure incremental micro-batches consume
