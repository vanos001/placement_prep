# Multi-Primary Replication

## Overview

Multi-primary (also called multi-leader or active-active) replication allows **multiple nodes to accept writes simultaneously**. Unlike primary-backup where only one node handles writes, multi-primary replication distributes write load across multiple primaries, each replicating to the others. This pattern is used for geo-distributed databases, offline-first applications, and high-availability systems.

## How It Works

```mermaid
graph TD
    subgraph "Region A"
        C1[Client A] --> P1[Primary A]
    end
    subgraph "Region B"
        C2[Client B] --> P2[Primary B]
    end
    subgraph "Region C"
        C3[Client C] --> P3[Primary C]
    end
    
    P1 <-->|Replicate| P2
    P2 <-->|Replicate| P3
    P3 <-->|Replicate| P1
```

Each primary accepts writes from its local clients and asynchronously replicates to other primaries.

## Use Cases

| Use Case | Why Multi-Primary |
|----------|------------------|
| **Multi-datacenter** | Each datacenter has its own primary for low latency |
| **Offline-first** | Each device has a local database that syncs when online |
| **High availability** | Writes continue even if one primary fails |
| **Collaborative editing** | Multiple users edit simultaneously |

## The Conflict Problem

The core challenge: **what happens when two primaries modify the same data simultaneously?**

```mermaid
sequenceDiagram
    participant P1 as Primary A
    participant P2 as Primary B
    
    Note over P1,P2: Both modify the same key
    P1->>P1: SET x=1 (at time 1)
    P2->>P2: SET x=2 (at time 1)
    
    P1->>P2: Replicate: x=1
    P2->>P1: Replicate: x=2
    
    Note over P1: x=2 (overwrite from B)
    Note over P2: x=1 (overwrite from A)
    
    Note over P1,P2: Conflict! Different values
```

## Conflict Resolution Strategies

### 1. Last-Write-Wins (LWW)

Each write gets a timestamp. The write with the latest timestamp wins.

```mermaid
graph TD
    W1["Write x=1 (timestamp: 100)"] --> C{Conflict}
    W2["Write x=2 (timestamp: 101)"] --> C
    C -->|LWW| R["Result: x=2"]
```

**Pros**: Simple, deterministic, no coordination needed
**Cons**: Writes can be lost; clock skew causes issues; doesn't handle concurrent writes well

### 2. Merge Functions

Define a function that merges conflicting values:

```python
# Example: Set union merge
def merge(current, incoming):
    return current.union(incoming)

# Example: Counter merge (sum)
def merge(current, incoming):
    return current + incoming
```

### 3. CRDTs (Conflict-free Replicated Data Types)

Data structures that can be merged automatically without conflicts:

```mermaid
graph TD
    subgraph "G-Counter (Grow-only Counter)"
        A["Node A: {A:3, B:0}"] --> M["Merge: max each"]
        B["Node B: {A:0, B:5}"] --> M
        M --> R["Result: {A:3, B:5} = 8"]
    end
    
    subgraph "OR-Set (Observed-Remove Set)"
        S1["Node A: {(x, tag1)}"] --> M2["Merge: union"]
        S2["Node B: {(x, tag2), (y, tag3)}"] --> M2
        M2 --> R2["Result: {(x, tag1), (x, tag2), (y, tag3)}"]
    end
```

Common CRDTs:
| Type | Description | Example Use |
|------|-------------|-------------|
| **G-Counter** | Grow-only counter | Page views, likes |
| **PN-Counter** | Positive-Negative counter | Inventory |
| **G-Set** | Grow-only set | Tags, bookmarks |
| **OR-Set** | Add/remove set | Shopping cart |
| **LWW-Register** | Last-writer-wins register | User profile |
| **LWW-Element-Set** | LWW set | Configuration |

### 4. Application-Level Resolution

The application decides how to handle conflicts:

```python
def resolve_conflict(current, incoming):
    # Custom logic
    if current.version > incoming.version:
        return current
    elif incoming.priority == "urgent":
        return incoming
    else:
        return merge(current, incoming)
```

### 5. Version Vectors

Track causality using version vectors:

```mermaid
graph TD
    subgraph "Version Vectors"
        V1["Node A writes: x=1\nVector: {A:1, B:0}"] --> C{Compare}
        V2["Node B writes: x=2\nVector: {A:0, B:1}"] --> C
        C -->|Concurrent| Conflict["Conflict! Both are valid"]
    end
    
    subgraph "Causal Ordering"
        V3["Node A writes: x=1\nVector: {A:1, B:0}"] --> D{Compare}
        V4["Node B writes after seeing A's write: x=2\nVector: {A:1, B:1}"] --> D
        D -->|B > A| Winner["x=2 wins (B causally after A)"]
    end
```

## Comparison of Strategies

| Strategy | Complexity | Data Loss | Deterministic | Use Case |
|----------|-----------|-----------|---------------|----------|
| **LWW** | Low | Possible | Yes | Simple systems |
| **CRDTs** | Medium | No | Yes | Counters, sets |
| **Version Vectors** | Medium | No | No (needs resolution) | General purpose |
| **Application** | High | Depends | Depends | Complex business logic |

## Multi-Primary Topologies

```mermaid
graph TD
    subgraph "All-to-All"
        A1[P1] <--> A2[P2]
        A2 <--> A3[P3]
        A3 <--> A1
    end
    
    subgraph "Circular"
        C1[P1] --> C2[P2]
        C2 --> C3[P3]
        C3 --> C1
    end
    
    subgraph "Star/Tree"
        S1[Hub P1] --> S2[P2]
        S1 --> S3[P3]
    end
```

| Topology | Pros | Cons |
|----------|------|------|
| **All-to-All** | Low latency | Complex, duplicate messages |
| **Circular** | Simple | Single point of failure |
| **Star** | Centralized control | Hub failure affects all |

## Real-World Examples

| System | Multi-Primary? | Notes |
|--------|---------------|-------|
| **Cassandra** | Yes | All nodes are equal; tunable consistency |
| **DynamoDB** | Yes | Multi-region with last-writer-wins |
| **CouchDB** | Yes | Offline-first with version vectors |
| **MySQL Galera** | Yes | Synchronous multi-primary |
| **PostgreSQL BDR** | Yes | Bi-directional replication |
| **Google Spanner** | No | Single-primary with TrueTime |

## Interview Questions

1. **What is multi-primary replication and when would you use it?**
   - Multiple nodes accept writes simultaneously. Use for geo-distributed systems (low latency per region), offline-first apps, or high availability (writes survive single node failure).

2. **How do you handle write conflicts in multi-primary replication?**
   - Last-write-wins (simple but loses data), CRDTs (automatic merge), version vectors (detect conflicts, resolve manually or with custom logic), or application-level resolution.

3. **What are CRDTs?**
   - Conflict-free Replicated Data Types are data structures designed to merge automatically without coordination. Examples: G-Counter (grow-only counter), OR-Set (add/remove set), LWW-Register (last-writer-wins).

4. **What's the difference between LWW and version vectors?**
   - LWW uses timestamps to pick the latest write (simple but can lose concurrent writes). Version vectors track causality and can detect whether writes are concurrent or causally related.

5. **What is the CAP trade-off in multi-primary replication?**
   - Multi-primary is typically AP (available, partition-tolerant) — it sacrifices consistency for availability. During partitions, each partition can continue accepting writes, but conflicts must be resolved later.

## Common Mistakes

- Ignoring **conflict resolution** until it's too late
- Using LWW when concurrent writes matter (data loss)
- Not accounting for **clock skew** with timestamp-based resolution
- Assuming all conflicts are resolvable — sometimes human intervention is needed
- Forgetting about **replication lag** and its impact on reads

## Summary

Multi-primary replication enables high availability and geo-distributed writes by allowing multiple nodes to accept writes. The key challenge is conflict resolution when the same data is modified concurrently. Strategies range from simple (LWW) to sophisticated (CRDTs, version vectors). The choice depends on consistency requirements, data model, and application needs.

## Cross-References

- [Replication Overview](README.md) — Replication strategies comparison
- [Primary-Backup Replication](primary-backup.md) — Simpler alternative
- [Chain Replication](chain.md) — Strong consistency alternative
- [Quorum-Based Replication](quorum.md) — Tunable consistency
- [Consensus Algorithms](../consensus/README.md) — For coordination when needed
- [Message Queues](../messaging/queues.md) — For async replication
