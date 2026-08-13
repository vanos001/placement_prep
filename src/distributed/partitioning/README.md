# Partitioning (Sharding)

## Overview

Partitioning (also called sharding) is the practice of **splitting a large dataset across multiple nodes**. Each node is responsible for a subset of the data, allowing the system to scale beyond what a single machine can handle. Partitioning is essential for horizontal scalability — adding more nodes to increase capacity.

## Why Partition?

```mermaid
graph TD
    subgraph "No Partitioning"
        S1[Single Server] --> D1["All Data (10TB)"]
        S1 --> P1["All Queries"]
        P1 -.->|Bottleneck| B1["Limited by one machine"]
    end
    
    subgraph "With Partitioning"
        S2[Server 1] --> D2["Data A (2.5TB)"]
        S3[Server 2] --> D3["Data B (2.5TB)"]
        S4[Server 3] --> D4["Data C (2.5TB)"]
        S5[Server 4] --> D5["Data D (2.5TB)"]
    end
```

| Benefit | Description |
|---------|-------------|
| **Scalability** | Data and queries distributed across nodes |
| **Performance** | Parallel processing of queries |
| **Storage** | More data than fits on one machine |
| **Availability** | Failure affects only one partition |

## Partitioning + Replication

In practice, partitioning and replication are combined:

```mermaid
graph TD
    subgraph "Partition 1"
        P1L[Leader] --> P1F1[Follower 1]
        P1L --> P1F2[Follower 2]
    end
    subgraph "Partition 2"
        P2L[Leader] --> P2F1[Follower 1]
        P2L --> P2F2[Follower 2]
    end
    subgraph "Partition 3"
        P3L[Leader] --> P3F1[Follower 1]
        P3L --> P3F2[Follower 2]
    end
```

Each partition is replicated independently. A node may be leader for one partition and follower for another.

## Partitioning Strategies

```mermaid
graph TD
    P[Partitioning] --> H[Hash Partitioning]
    P --> R[Range Partitioning]
    P --> C[Consistent Hashing]
    P --> D[Directory-Based]
    
    H --> H1[Uniform distribution]
    H --> H2[No range queries]
    
    R --> R1[Range queries supported]
    R --> R2[Hotspot risk]
    
    C --> C1[Minimal redistribution]
    C --> C2[Load balancing]
```

## Comparison

| Strategy | Distribution | Range Queries | Hotspot Risk | Redistribution |
|----------|-------------|---------------|-------------|----------------|
| **Hash** | Uniform | No | Low | Full reshuffling |
| **Range** | Ordered | Yes | High | Minimal |
| **Consistent Hashing** | Ring-based | No | Low | Minimal |

## Key Challenges

### Hotspots

When one partition receives disproportionately more traffic:

```mermaid
graph TD
    subgraph "Hotspot Problem"
        C1[Client 1] --> P1[Partition A - Hot!]
        C2[Client 2] --> P1
        C3[Client 3] --> P1
        C4[Client 4] --> P2[Partition B - Idle]
    end
```

**Solutions**:
- Split the hotspot partition
- Add a key prefix/suffix to distribute load
- Use consistent hashing with virtual nodes

### Cross-Partition Queries

Queries that span multiple partitions are expensive:

```mermaid
sequenceDiagram
    participant C as Client
    participant P1 as Partition 1
    participant P2 as Partition 2
    participant P3 as Partition 3
    
    C->>P1: Query (partial)
    C->>P2: Query (partial)
    C->>P3: Query (partial)
    
    P1-->>C: Results 1
    P2-->>C: Results 2
    P3-->>C: Results 3
    
    C->>C: Merge results
```

### Rebalancing

When adding or removing nodes, data must be redistributed:

```mermaid
graph TD
    subgraph "Before: 3 Partitions"
        B1[P1: Keys 0-33]
        B2[P2: Keys 34-66]
        B3[P3: Keys 67-100]
    end
    
    subgraph "After: 4 Partitions"
        A1[P1: Keys 0-25]
        A2[P2: Keys 26-50]
        A3[P3: Keys 51-75]
        A4[P4: Keys 76-100]
    end
```

## Secondary Indexes with Partitioning

Secondary indexes complicate partitioning because they can point to data on different partitions.

### Local Index (Per-Partition)

```mermaid
graph TD
    subgraph "Partition 1"
        D1["doc1: color=red"] --> I1["color_index: red→{doc1}"]
    end
    subgraph "Partition 2"
        D2["doc2: color=red"] --> I2["color_index: red→{doc2}"]
    end
    
    Q["Query: color=red"] --> P1
    Q --> P2
    P1 --> M["Merge results"]
    P2 --> M
```

### Global Index (Partitioned Separately)

```mermaid
graph TD
    subgraph "Data Partitions"
        D1["Partition 1: doc1"]
        D2["Partition 2: doc2"]
    end
    subgraph "Index Partitions"
        I1["Index P1: color=blue→doc3"]
        I2["Index P2: color=red→{doc1, doc2}"]
    end
```

## Interview Questions

1. **What is partitioning and why is it needed?**
   - Splitting data across multiple nodes for scalability. A single machine has finite storage and processing capacity; partitioning allows horizontal scaling.

2. **Compare hash partitioning and range partitioning.**
   - Hash: uniform distribution, no range queries, low hotspot risk. Range: supports range queries, ordered data, but prone to hotspots.

3. **What is the hotspot problem and how do you solve it?**
   - One partition receives disproportionate traffic. Solve by: splitting the hotspot, adding key salting, using consistent hashing with virtual nodes, or caching.

4. **How does partitioning interact with replication?**
   - Each partition is independently replicated. A node can be leader for one partition and follower for another. This combines scalability (partitioning) with availability (replication).

5. **What are the challenges of secondary indexes with partitioning?**
   - Local indexes: each partition has its own index; queries must scatter-gather across all partitions. Global indexes: index is partitioned separately; writes must update multiple partitions, but reads can target one.

## Common Mistakes

- Choosing the **wrong partition key** — leads to hotspots or unbalanced partitions
- Forgetting about **cross-partition queries** — they're expensive and complex
- Not planning for **rebalancing** — adding nodes requires data redistribution
- Ignoring **secondary index** implications — they complicate partitioning
- Assuming partitions are independent — transactions across partitions are hard

## Summary

Partitioning is essential for scaling beyond a single machine. The choice of partitioning strategy depends on query patterns: hash for uniform distribution, range for ordered queries, consistent hashing for dynamic clusters. Combining partitioning with replication provides both scalability and availability. Key challenges include hotspots, cross-partition queries, and rebalancing.

## Cross-References

- [Hash Partitioning](hash.md) — Simple hash-based distribution
- [Range Partitioning](range.md) — Ordered partitioning
- [Consistent Hashing](consistent-hashing.md) — Dynamic partitioning
- [Replication Strategies](../replication/README.md) — Combining with partitioning
- [MapReduce](../mapreduce/README.md) — Processing partitioned data
- [Kafka](../messaging/kafka.md) — Partitioned message queues

## Cross References

- [Hash Partitioning](hash.md)
- [Range Partitioning](range.md)
- [Consistent Hashing](consistent-hashing.md)
- [DBMS Sharding](../../dbms/distributed/sharding.md)
