# Spark Internals

Apache Spark is an open-source cluster computing framework, originally developed at UC Berkeley AMPLab in 2009 by Matei Zaharia (later Databricks). Spark extends the MapReduce model with in-memory computation, lazy evaluation, and a richer DAG (Directed Acyclic Graph) execution model. This page covers the RDD abstraction, the Catalyst optimizer, the Tungsten execution engine, and the shuffle mechanics — complementing the existing [Spark page](../distributed/mapreduce/spark.md).

## The RDD Abstraction

A Resilient Distributed Dataset (RDD) is Spark's core abstraction: an immutable, partitioned collection of records that can be processed in parallel.

```python
# Create an RDD from a file
lines = sc.textFile("hdfs:///data/logs.txt")

# Transformations (lazy)
words = lines.flatMap(lambda line: line.split())
pairs = words.map(lambda word: (word, 1))
counts = pairs.reduceByKey(lambda a, b: a + b)

# Action (triggers execution)
counts.saveAsTextFile("hdfs:///data/word_counts.txt")
```

Key properties:
- **Immutable**: transformations create new RDDs; the original is unchanged.
- **Lazy**: transformations don't compute; they build a DAG of operations. Actions trigger execution.
- **Partitioned**: each RDD is divided into partitions that can be processed independently.
- **Resilient**: if a partition is lost (e.g., node failure), it can be recomputed from the DAG.

## The Catalyst Optimizer

Since Spark 2.0, the RDD abstraction is wrapped by a Dataset/DataFrame API that uses a query optimizer (Catalyst) and a code generator (Tungsten). The optimizer:

```text
User code (Python/Scala/Java/SQL)
   │
   ▼
Logical plan (unresolved)
   │
   ▼
Analysis (resolve names, types)
   │
   ▼
Logical plan (resolved)
   │
   ▼
Optimization (rule-based: predicate pushdown, constant folding, etc.)
   │
   ▼
Physical plan (multiple candidates)
   │
   ▼
Cost-based selection (pick the cheapest plan)
   │
   ▼
Code generation (Tungsten)
   │
   ▼
Execution
```

The optimizer applies ~50 rules, including:
- **Predicate pushdown**: push filters as early as possible (reduces intermediate data).
- **Constant folding**: evaluate constant expressions at compile time.
- **Projection pruning**: only read columns that are actually used.
- **Join reordering**: pick the order of joins to minimize intermediate data.

For SQL queries, Catalyst is competitive with commercial optimizers.

## Tungsten: The Execution Engine

Tungsten (since Spark 1.4) is Spark's native execution engine, replacing the JVM-based RDD execution with:

1. **Binary in-memory format**: rows are stored in compact binary form (like a struct), not as JVM objects. Reduces memory overhead and GC pressure.
2. **Code generation**: queries are compiled to JVM bytecode at runtime. The generated code is "whole-stage codegen" — the entire query is one Java method, avoiding virtual calls.
3. **Cache-aware data layout**: data is laid out in cache-friendly tiles, with prefetching for sequential access.

```python
# Enable whole-stage code generation (default in Spark 3+)
spark.conf.set("spark.sql.codegen.wholeStage", "true")
```

Tungsten's whole-stage codegen is the main reason Spark 3 is ~2× faster than Spark 2 on TPC-DS.

## The DAG Scheduler

Spark's DAG scheduler breaks a job into stages:

```text
Job: count.saveAsTextFile()
   │
   ▼
Stage 0: read textFile, flatMap, map
   │
   ▼ (shuffle boundary)
Stage 1: reduceByKey (reads shuffle, aggregates)
   │
   ▼ (shuffle boundary)
Stage 2: saveAsTextFile (writes to HDFS)
```

Stages are separated by "shuffle boundaries" — points where data must be repartitioned across nodes. Within a stage, all operations are pipelined (no data movement).

The DAG scheduler's job:
1. Identify the shuffle dependencies (where stages split).
2. Schedule stages in topological order (stages with no dependencies first).
3. For each stage, schedule tasks (one per partition) on available executors.

## The Shuffle

The shuffle is the most expensive operation in Spark. When an operation requires repartitioning (e.g., `groupByKey`, `reduceByKey`, `join`), Spark writes the data to disk on the source side and reads it back on the destination side:

```text
Source side (Map task):
  For each output partition p:
    Open a shuffle file for p on local disk.
    Write records to the file in sorted order.
    Track the file's location in the MapStatus.

Destination side (Reduce task):
  For each input partition p:
    Fetch the shuffle file from the source's MapStatus.
    Read records from the file.
    Process them (e.g., reduce by key).
```

Shuffle costs:
- **Disk I/O**: source writes (often 1-5× the data size with sort + spill); destination reads (1× the data size).
- **Network**: data moves from source nodes to destination nodes (often 1× the data size).
- **Memory**: sort buffers (100 MB default per partition).

For a 1 TB shuffle, the cost is ~3 TB of disk I/O + 1 TB of network. On a 10 Gbps network with NVMe SSDs, this takes ~30 minutes.

## Shuffle Optimizations

Spark has several shuffle optimizations:

1. **Sort-based shuffle** (default since 2.0): each Map task sorts its output by key, so Reduce can merge efficiently.
2. **Tungsten sort shuffle**: uses Tungsten's binary format and direct memory for the sort buffer. ~2× faster than the JVM-based sort.
3. **Push-based shuffle** (Spark 3.3+ with cloud integration): writes shuffle data to cloud object storage (S3, GCS) instead of local disk. Survives executor failures.
4. **Bucketed shuffle** (when joining pre-bucketed tables): if both sides of a join are bucketed by the same key, no shuffle is needed.

## Adaptive Query Execution (AQE)

Since Spark 3.0, AQE adjusts the query plan at runtime based on statistics:

1. **Coalesce shuffle partitions**: if a shuffle has many small partitions, merge them.
2. **Switch join strategy**: if a sort-merge join's left side turns out to be small, switch to broadcast join.
3. **Skew join handling**: if one partition of a join is much larger than others, split it.

```python
# Enable AQE
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
```

AQE typically improves query performance by 10-50% on real workloads, by adapting to actual data distribution.

## Memory Management

Spark's memory is divided into:
- **Reserved Memory**: 300 MB (fixed).
- **User Memory**: 25% of (total - 300 MB). Used for user data structures, UDFs.
- **Spark Memory**: 75% of (total - 300 MB). Split into Storage (cache) and Execution (shuffles, joins).

```text
Total executor memory: 4 GB
  Reserved: 300 MB
  User: 925 MB (25% of 3.7 GB)
  Spark: 2.775 GB
    Storage (cache): 1.39 GB (50% of Spark)
    Execution (shuffles, joins): 1.39 GB (50% of Spark)
```

When Execution needs more memory, it can evict cached blocks. When Storage needs more, it can't borrow from Execution (Execution is hard-pinned).

## Common Pitfalls

1. **Forgetting to call `persist()` on reused RDDs/DataFrames.** Without caching, Spark recomputes the RDD on every action.

2. **Using `collect()` on large DataFrames.** `collect()` brings all data to the driver, which can OOM. Use `take(N)` or `toLocalIterator()`.

3. **Forgetting that shuffle is expensive.** A `groupByKey` followed by a map-reduce is much slower than a single `reduceByKey`. Minimize shuffles.

4. **Not partitioning data correctly.** A DataFrame with too few partitions underutilizes the cluster; too many partitions have high overhead. Target ~128 MB per partition.

5. **Forgetting that UDFs bypass the optimizer.** A Python UDF is treated as a black box by Catalyst — no predicate pushdown, no code generation. Use Spark SQL expressions where possible.

6. **Forgetting that `DataFrame.cache()` is lazy.** The cache is populated on the first action. If you `cache()` then immediately `unpersist()`, nothing is cached.

## References

- Zaharia et al., "[Resilient Distributed Datasets: A Fault-Tolerant Abstraction for In-Memory Cluster Computing](https://www.usenix.org/system/files/conference/nsdi12/nsdi12-final138.pdf)" (NSDI 2012)
- Armbrust et al., "[Spark SQL: Relational Data Processing in Spark](https://dl.acm.org/doi/10.1145/2723372.2742797)" (SIGMOD 2015)
- Xin & Rosen, "[Project Tungsten: Bringing Spark Closer to Bare Metal](https://databricks.com/session/project-tungsten-bringing-spark-closer-to-bare-metal)" (Spark Summit 2015)
- [Spark documentation](https://spark.apache.org/docs/latest/)
- [Adaptive Query Execution (Databricks blog)](https://www.databricks.com/blog/2020/05/29/fine-tuning-adaptive-query-execution-in-apache-spark.html)
- [Spark Performance Tuning (Databricks)](https://docs.databricks.com/optimizations/index.html)
- [LWN: Spark internals (2019)](https://lwn.net/Articles/796030/)
