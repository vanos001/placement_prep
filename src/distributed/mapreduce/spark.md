# Apache Spark

## Overview

Apache Spark is a unified analytics engine for large-scale data processing. It was developed at UC Berkeley's AMPLab in 2009 and open-sourced in 2010. Spark's key innovation is **in-memory processing** — keeping intermediate results in memory rather than writing to disk, making it up to 100x faster than Hadoop MapReduce for iterative algorithms.

## Why Spark?

```mermaid
graph LR
    subgraph "MapReduce"
        MR1[Map] -->|Disk| MR2[Reduce]
        MR2 -->|Disk| MR3[Map]
        MR3 -->|Disk| MR4[Reduce]
    end
    
    subgraph "Spark"
        S1[Stage 1] -->|Memory| S2[Stage 2]
        S2 -->|Memory| S3[Stage 3]
        S3 -->|Memory| S4[Stage 4]
    end
```

| Feature | MapReduce | Spark |
|---------|-----------|-------|
| **Speed** | Slow (disk I/O) | Fast (in-memory) |
| **Ease of use** | Low-level Java | High-level APIs (Scala, Python, SQL) |
| **Iterative** | Poor (each iteration writes to disk) | Excellent (RDDs stay in memory) |
| **Streaming** | Not native | Structured Streaming |
| **SQL** | Hive (slow) | Spark SQL (fast) |

## Core Abstraction: RDDs

**Resilient Distributed Datasets (RDDs)** are Spark's fundamental data structure:

```mermaid
graph TD
    subgraph "RDD Properties"
        R[Resilient] --> R1["Can recompute lost partitions"]
        D[Distributed] --> D1["Data across multiple nodes"]
        D[Dataset] --> D2["Collection of partitioned data"]
        I[Immutable] --> I1["Once created, cannot be changed"]
        L[Lazy] --> L1["Transformations not executed until action"]
    end
```

### RDD Operations

```mermaid
graph LR
    subgraph "Transformations (Lazy)"
        T1[map]
        T2[filter]
        T3[flatMap]
        T4[groupByKey]
        T5[reduceByKey]
        T6[join]
    end
    
    subgraph "Actions (Trigger Execution)"
        A1[collect]
        A2[count]
        A3[reduce]
        A4[saveAsTextFile]
    end
```

### Example: Word Count with RDDs

```python
from pyspark import SparkContext

sc = SparkContext("local", "WordCount")

# Create RDD from text file
text = sc.textFile("input.txt")

# Transformations (lazy - not executed yet)
words = text.flatMap(lambda line: line.split(" "))
pairs = words.map(lambda word: (word, 1))
counts = pairs.reduceByKey(lambda a, b: a + b)

# Action (triggers execution)
results = counts.collect()
for word, count in results:
    print(f"{word}: {count}")
```

```mermaid
graph LR
    text["textFile"] --> flatMap["flatMap:\nsplit lines"]
    flatMap --> map["map:\n(word, 1)"]
    map --> reduce["reduceByKey:\nsum counts"]
    reduce --> collect["collect:\nreturn results"]
```

## DAG (Directed Acyclic Graph)

Spark builds a DAG of stages from RDD transformations:

```mermaid
graph TD
    subgraph "DAG Execution Plan"
        R1["textFile (RDD)"] --> R2["flatMap (RDD)"]
        R2 --> R3["map (RDD)"]
        R3 --> R4["reduceByKey (Shuffle)"]
        R4 --> R5["collect (Result)"]
    end
    
    subgraph "Stages"
        S1["Stage 1:\ntextFile → flatMap → map"]
        S2["Stage 2:\nreduceByKey"]
    end
    
    R1 --> S1
    R2 --> S1
    R3 --> S1
    R4 --> S2
    R5 --> S2
```

### Stage Boundaries

A new stage starts at each **shuffle** operation (data transfer between partitions):

| Operation | Type | Stage Boundary? |
|-----------|------|----------------|
| `map` | Narrow | No |
| `filter` | Narrow | No |
| `flatMap` | Narrow | No |
| `groupByKey` | Wide | **Yes** |
| `reduceByKey` | Wide | **Yes** |
| `join` | Wide | **Yes** |

## Memory Management

```mermaid
graph TD
    subgraph "Spark Memory Layout"
        VM["Executor Memory"] --> R["Reserved Memory (~300MB)"]
        VM --> U["User Memory"]
        VM --> SM["Spark Memory"]
        
        SM --> S["Storage (cached RDDs)"]
        SM --> E["Execution (shuffles, joins)"]
        
        S <-->|"Unified Memory"| E
    end
```

### Storage Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| `MEMORY_ONLY` | Store as deserialized Java objects | Default, fastest |
| `MEMORY_AND_DISK` | Spill to disk if memory full | Large datasets |
| `MEMORY_ONLY_SER` | Store as serialized bytes | Memory-efficient |
| `DISK_ONLY` | Store only on disk | Very large datasets |
| `OFF_HEAP` | Store outside JVM | GC-sensitive apps |

## Spark SQL and DataFrames

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Example").getOrCreate()

# Create DataFrame
df = spark.read.json("users.json")

# SQL-like operations
result = df.filter(df.age > 25) \
           .groupBy("city") \
           .count() \
           .orderBy("count", ascending=False)

# Register as temp view and use SQL
df.createOrReplaceTempView("users")
result = spark.sql("SELECT city, COUNT(*) FROM users WHERE age > 25 GROUP BY city")
```

### Catalyst Optimizer

```mermaid
graph LR
    SQL["SQL/DataFrame"] --> Parse["Parse"]
    Parse --> Analyze["Analyze"]
    Analyze --> Optimize["Optimize\n(Catalyst)"]
    Optimize --> Codegen["Code Generation"]
    Codegen --> Execute["Execute"]
```

Catalyst optimizes queries by:
- Predicate pushdown
- Column pruning
- Join reordering
- Constant folding

## Structured Streaming

```python
# Read stream
stream = spark.readStream \
    .format("kafka") \
    .option("subscribe", "events") \
    .load()

# Process
counts = stream \
    .groupBy(window("timestamp", "5 minutes"), "event_type") \
    .count()

# Write stream
query = counts.writeStream \
    .outputMode("complete") \
    .format("console") \
    .start()
```

```mermaid
graph LR
    Source["Kafka Source"] --> Process["Micro-batch\nProcessing"]
    Process --> Sink["Console Sink"]
    
    Note["Triggered every few seconds"]
```

## Spark Architecture

```mermaid
graph TD
    subgraph "Spark Cluster"
        D[Driver] --> CM[Cluster Manager]
        CM --> E1[Executor 1]
        CM --> E2[Executor 2]
        CM --> E3[Executor 3]
        
        E1 --> T1[Task 1]
        E1 --> T2[Task 2]
        E2 --> T3[Task 3]
        E2 --> T4[Task 4]
        E3 --> T5[Task 5]
    end
    
    subgraph "Storage"
        HDFS[HDFS/S3]
    end
    
    HDFS --> E1
    HDFS --> E2
    HDFS --> E3
```

| Component | Role |
|-----------|------|
| **Driver** | Runs main program, creates SparkContext, schedules tasks |
| **Cluster Manager** | Allocates resources (YARN, Mesos, K8s, Standalone) |
| **Executor** | Runs tasks on worker nodes, stores data in memory |
| **Task** | Unit of work, one task per partition |

## Spark vs. MapReduce vs. Flink

| Aspect | MapReduce | Spark | Flink |
|--------|-----------|-------|-------|
| **Processing** | Batch | Micro-batch | True streaming |
| **Latency** | Minutes | Seconds | Milliseconds |
| **State** | Stateless | DStreams/RDDs | Stateful |
| **Fault tolerance** | Recompute | Lineage | Checkpoints |
| **Use case** | ETL | Analytics | Real-time |

## Interview Questions

1. **What are RDDs and why are they important?**
   - Resilient Distributed Datasets: immutable, partitioned collections that can be operated on in parallel. They're resilient because lost partitions can be recomputed from lineage. They enable in-memory processing.

2. **What is the difference between transformations and actions?**
   - Transformations (map, filter, join) are lazy — they build a DAG but don't execute. Actions (collect, count, save) trigger execution of the DAG.

3. **How does Spark achieve fault tolerance?**
   - RDD lineage — each RDD remembers how it was created from other RDDs. If a partition is lost, Spark recomputes it from the source using the lineage.

4. **What is the Catalyst optimizer?**
   - Spark SQL's query optimizer that applies rule-based and cost-based optimizations: predicate pushdown, column pruning, join reordering, and code generation.

5. **How does Spark differ from MapReduce?**
   - Spark keeps intermediate results in memory (MapReduce writes to disk). Spark has higher-level APIs. Spark supports iterative algorithms efficiently. Spark can be 10-100x faster.

6. **What are narrow and wide transformations?**
   - Narrow: each input partition maps to one output partition (map, filter). Wide: each input partition can map to multiple output partitions (groupByKey, join) — requires shuffle.

## Common Mistakes

- Not caching frequently used RDDs — causes recomputation
- Using `collect()` on large datasets — pulls all data to driver, causes OOM
- Too many small partitions or too few large partitions — affects parallelism
- Not understanding shuffle operations — they're expensive and create stage boundaries
- Confusing DataFrames with RDDs — DataFrames have Catalyst optimization

## Summary

Spark revolutionized big data processing with in-memory computing and high-level APIs. RDDs provide fault-tolerant distributed collections, the DAG scheduler optimizes execution, and Catalyst optimizes SQL queries. Spark unifies batch, streaming, SQL, and ML processing in a single framework.

## Cross-References

- [MapReduce Framework](mapreduce.md) — Spark's predecessor
- [Stream Processing](streaming.md) — Spark Streaming vs. Flink
- [Kafka](../messaging/kafka.md) — Common data source for Spark
- [Partitioning](../partitioning/README.md) — How RDDs are partitioned
- [MapReduce Overview](README.md) — Distributed processing context
