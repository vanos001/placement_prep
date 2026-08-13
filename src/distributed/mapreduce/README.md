# MapReduce and Distributed Processing

## Overview

Distributed processing frameworks allow computation to be **parallelized across thousands of machines**. This is essential for processing datasets too large for a single machine. The key insight: move computation to data, not data to computation.

## Why Distributed Processing?

```mermaid
graph TD
    subgraph "Single Machine"
        S1[1 Machine] --> D1["1TB data"]
        D1 --> T1["10 hours processing"]
    end
    
    subgraph "Distributed (100 Machines)"
        S2["100 Machines"] --> D2["1TB data (10GB each)"]
        D2 --> T2["6 minutes processing"]
    end
```

| Benefit | Description |
|---------|-------------|
| **Speed** | Parallel processing across many machines |
| **Scale** | Process petabytes of data |
| **Fault tolerance** | Recompute failed tasks on other machines |
| **Cost** | Use commodity hardware |

## Evolution of Processing Frameworks

```mermaid
graph LR
    MR["MapReduce\n(2004)"] --> SP["Spark\n(2014)"]
    MR --> FL["Flink\n(2016)"]
    MR --> KS["Kafka Streams\n(2016)"]
    
    subgraph "Batch"
        MR
        SP
    end
    
    subgraph "Stream"
        FL
        KS
    end
```

| Framework | Type | Key Innovation |
|-----------|------|----------------|
| **MapReduce** | Batch | Simple map/shuffle/reduce paradigm |
| **Spark** | Batch/Stream | In-memory processing, RDDs |
| **Flink** | Stream/Batch | True streaming, event time |
| **Kafka Streams** | Stream | Library (no cluster needed) |

## Processing Models

### Batch Processing

Process large datasets with bounded input:

```mermaid
graph LR
    Input["Large Dataset"] --> Process["Batch Job"]
    Process --> Output["Results"]
    
    Note["Minutes to hours"]
```

### Stream Processing

Process unbounded data streams in real-time:

```mermaid
graph LR
    Input["Event Stream"] --> Process["Stream Job"]
    Process --> Output["Real-time Results"]
    
    Note["Milliseconds to seconds"]
```

## Key Concepts

### Data Locality

```mermaid
graph TD
    subgraph "Move Data to Compute (Bad)"
        D1[Data on Node 1] -->|Transfer| C1[Compute on Node 2]
        Note1["Network bottleneck"]
    end
    
    subgraph "Move Compute to Data (Good)"
        D2[Data on Node 1] --> C2[Compute on Node 1]
        Note2["No network transfer"]
    end
```

### Fault Tolerance

```mermaid
graph TD
    T1[Task 1] -->|Success| R1[Result 1]
    T2[Task 2] -->|Failure| X[Crash!]
    T2b["Task 2 (retry)"] -->|Success| R2[Result 2]
    T3[Task 3] -->|Success| R3[Result 3]
```

### Data Partitioning

```mermaid
graph TD
    D[Dataset] --> P1[Partition 1 → Node 1]
    D --> P2[Partition 2 → Node 2]
    D --> P3[Partition 3 → Node 3]
    
    P1 --> R1[Result 1]
    P2 --> R2[Result 2]
    P3 --> R3[Result 3]
    
    R1 --> M[Merge]
    R2 --> M
    R3 --> M
```

## Comparison

| Aspect | MapReduce | Spark | Flink |
|--------|-----------|-------|-------|
| **Model** | Batch | Micro-batch | True streaming |
| **Latency** | High (minutes) | Low (seconds) | Very low (ms) |
| **State** | Stateless | RDDs/DStreams | Stateful |
| **Fault tolerance** | Recompute | Lineage | Checkpoints |
| **Ease of use** | Complex | Moderate | Moderate |

## Interview Questions

1. **What is data locality and why is it important?**
   - Moving computation to where data resides, rather than transferring data over the network. This avoids network bottlenecks and dramatically improves performance.

2. **How do distributed processing frameworks handle failures?**
   - Recompute failed tasks on other machines. MapReduce re-runs map/reduce tasks. Spark uses RDD lineage to reconstruct lost data. Flink uses checkpoints.

3. **When would you use batch vs. stream processing?**
   - Batch: when you can wait for results (daily reports, training ML models). Stream: when you need real-time results (fraud detection, live dashboards).

## Summary

Distributed processing enables computation at scale by parallelizing work across many machines. MapReduce introduced the paradigm, Spark optimized it with in-memory processing, and Flink/Kafka Streams handle real-time streaming. The choice depends on latency requirements and data characteristics.

## Cross-References

- [MapReduce Framework](mapreduce.md) — The foundational paradigm
- [Apache Spark](spark.md) — In-memory processing
- [Stream Processing](streaming.md) — Real-time processing
- [Partitioning](../partitioning/README.md) — How data is distributed
- [Message Queues](../messaging/queues.md) — Input for stream processing
- [Kafka](../messaging/kafka.md) — Common data source
