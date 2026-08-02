# Distributed Storage

## Overview

Distributed storage systems spread data across multiple machines to achieve scalability, fault tolerance, and performance beyond what a single machine can provide. Understanding distributed storage — replication, consistency, consensus, and partitioning — is essential for systems design interviews. This page covers the theoretical foundations and practical systems.

## Core Challenges

```mermaid
graph TD
    DS[Distributed Storage] --> C1[Data Partitioning]
    DS --> C2[Replication]
    DS --> C3[Consistency]
    DS --> C4[Failure Handling]
    DS --> C5[Consensus]

    C1 --> T1[How to split data across nodes?]
    C2 --> T2[How to keep copies in sync?]
    C3 --> T3[What does "up-to-date" mean?]
    C4 --> T4[What happens when nodes fail?]
    C5 --> T5[How do nodes agree on a value?]
```

## Data Partitioning

### Hash-Based Partitioning

```mermaid
graph TD
    KEY[Key: "user:1234"] --> HASH[hash("user:1234") % N]
    HASH --> N1[Node 0]
    HASH --> N2[Node 1]
    HASH --> N3[Node 2]
```

Simple but problematic when N changes — most keys remap.

### Consistent Hashing

```mermaid
graph TD
    subgraph Ring[Consistent Hash Ring]
        K1[Key A] --> N1[Node 1]
        K2[Key B] --> N2[Node 2]
        K3[Key C] --> N3[Node 3]
        K4[Key D] --> N1
    end

    NEW[New Node 4] -->|Only nearby keys remap| MINIMAL[Minimal disruption]
```

- Keys and nodes are hashed onto a ring (0 to 2^32 - 1).
- Each key is assigned to the next node clockwise.
- When a node is added/removed, only keys in that node's range move.
- **Virtual nodes**: Each physical node gets multiple positions on the ring for better balance.

### Range-Based Partitioning

```mermaid
graph TD
    subgraph Partitions[Range Partitions]
        P1[Partition 1: a-f → Node 1]
        P2[Partition 2: g-m → Node 2]
        P3[Partition 3: n-s → Node 3]
        P4[Partition 4: t-z → Node 4]
    end
```

Keys are sorted and divided into ranges. Good for range queries but prone to hotspots.

## Replication Strategies

### Leader-Based Replication

```mermaid
graph TD
    W[Write Request] --> L[Leader]
    L -->|Replicate| F1[Follower 1]
    L -->|Replicate| F2[Follower 2]
    L -->|Replicate| F3[Follower 3]

    R[Read Request] --> F1
    R --> F2
    R --> F3
```

- All writes go to the leader.
- Leader replicates to followers (sync or async).
- Reads can go to followers (eventual consistency) or leader (strong consistency).

### Multi-Leader Replication

```mermaid
graph TD
    subgraph DC1[Datacenter 1]
        L1[Leader 1]
    end
    subgraph DC2[Datacenter 2]
        L2[Leader 2]
    end

    L1 <-->|Async sync| L2
    W1[Write] --> L1
    W2[Write] --> L2
```

Each datacenter has a leader. Writes can happen at any leader. Conflicts must be resolved (last-write-wins, application-level merge).

### Leaderless Replication (Dynamo-style)

```mermaid
graph TD
    C[Client] -->|Write to N nodes| N1[Node 1]
    C -->|Write| N2[Node 2]
    C -->|Write| N3[Node 3]

    C -->|Read from N nodes| N1
    C -->|Read| N2
    C -->|Read| N3

    N1 -.->|Anti-entropy| N2
    N2 -.->|Anti-entropy| N3
```

- **Quorum writes**: Write to W out of N nodes.
- **Quorum reads**: Read from R out of N nodes.
- **Quorum condition**: W + R > N ensures at least one node in the read set has the latest write.
- Typical: N=3, W=2, R=2.

## Consistency Models

```mermaid
graph TD
    CM[Consistency Models] --> S[Strong]
    CM --> E[Eventual]
    CM --> C[Causal]

    S --> S1[Linearizability: all operations appear atomic]
    E --> E1[All replicas converge eventually]
    C --> C1[Respects causality order]
```

### Linearizability (Strongest)

```mermaid
sequenceDiagram
    participant C1 as Client 1
    participant Node
    participant C2 as Client 2

    C1->>Node: Write x = 1
    Node-->>C1: Ack
    C2->>Node: Read x
    Node-->>C2: Returns 1 (guaranteed)
```

All operations appear to happen atomically at some point in time. Requires consensus (Paxos/Raft).

### Eventual Consistency

```mermaid
sequenceDiagram
    participant C1 as Client 1
    participant Node A
    participant Node B
    participant C2 as Client 2

    C1->>Node A: Write x = 1
    Node A-->>C1: Ack
    C2->>Node B: Read x
    Node B-->>C2: Returns 0 (stale!)
    Note over Node A,Node B: Async replication
    Node A->>Node B: Replicate x = 1
    C2->>Node B: Read x
    Node B-->>C2: Returns 1 (converged)
```

All replicas eventually converge. No guarantee when. Used by DynamoDB, Cassandra.

### Causal Consistency

Operations that are causally related are seen in the same order by all nodes. Concurrent operations may be seen in different orders.

## Consensus Algorithms

### Paxos

```mermaid
sequenceDiagram
    participant P as Proposer
    participant A1 as Acceptor 1
    participant A2 as Acceptor 2
    participant A3 as Acceptor 3

    P->>A1: Prepare(n)
    P->>A2: Prepare(n)
    P->>A3: Prepare(n)
    A1-->>P: Promise(n, prev_value)
    A2-->>P: Promise(n, null)
    A3-->>P: Promise(n, prev_value)

    P->>A1: Accept(n, value)
    P->>A2: Accept(n, value)
    P->>A3: Accept(n, value)
    A1-->>P: Accepted
    A2-->>P: Accepted
    A3-->>P: Accepted

    Note over P: Majority accepted → value chosen
```

### Raft (Simplified Paxos)

```mermaid
graph TD
    subgraph Raft[Raft Consensus]
        LE[Leader Election] --> LR[Log Replication]
        LR --> SS[Safety]
    end

    LE -->|Timeout triggers| VOTE[RequestVote RPC]
    LR -->|Heartbeat + AppendEntries| REPLICATE[Replicate log entries]
    SS -->|Commit requires majority| COMMIT[Entry committed]
```

Raft decomposes consensus into:
1. **Leader Election**: One leader, others are followers. Leader sends heartbeats.
2. **Log Replication**: Leader appends entries to its log and replicates to followers.
3. **Safety**: A committed entry is guaranteed to be present in all future leaders' logs.

```mermaid
sequenceDiagram
    participant C as Client
    participant L as Leader (S1)
    participant F1 as Follower (S2)
    participant F2 as Follower (S3)

    C->>L: SET x = 5
    L->>L: Append to local log
    L->>F1: AppendEntries(SET x = 5)
    L->>F2: AppendEntries(SET x = 5)
    F1-->>L: Success
    F2-->>L: Success
    Note over L: Majority (2/3) acked → commit
    L->>L: Apply to state machine
    L-->>C: OK
    L->>F1: Commit index updated
    L->>F2: Commit index updated
```

## Distributed Storage Systems

### Amazon DynamoDB

```mermaid
graph TD
    CLIENT[Client] -->|API| DDB[DynamoDB]
    DDB --> PK[Partition Key Hash]
    PK --> P1[Partition 1]
    PK --> P2[Partition 2]
    PK --> P3[Partition N]

    P1 --> R1[Replica Set: 3 nodes]
    P2 --> R2[Replica Set: 3 nodes]
```

- Key-value and document store.
- Consistent hashing for partitioning.
- Leaderless replication (sloppy quorum + hinted handoff).
- Eventually consistent by default, strongly consistent reads available.

### Google Spanner

```mermaid
graph TD
    CLIENT[Client] --> SPANNER[Spanner]
    SPANNER --> SPLIT[Split into Tablets]
    SPLIT --> PAXOS[Paxos Group per Tablet]
    PAXOS --> REPLICA1[Replica 1 - DC East]
    PAXOS --> REPLICA2[Replica 2 - DC West]
    PAXOS --> REPLICA3[Replica 3 - DC Central]

    SPANNER --> TT[TrueTime API]
    TT --> GPS[GPS + Atomic Clocks]
```

- Globally distributed, strongly consistent SQL database.
- Uses Paxos for replication within each tablet.
- **TrueTime API**: Provides bounded clock uncertainty (±7ms), enabling globally consistent transactions.

### CockroachDB

```mermaid
graph TD
    CLIENT[Client] --> CRDB[CockroachDB SQL]
    CRDB --> RANGE[Ranges (64MB chunks)]
    RANGE --> RAFT[Raft consensus per range]
    RAFT --> N1[Node 1]
    RAFT --> N2[Node 2]
    RAFT --> N3[Node 3]
```

- Distributed SQL database inspired by Spanner.
- Uses Raft for replication.
- Serializable isolation by default.
- No dependency on TrueTime; uses hybrid logical clocks.

## Failure Handling

### Failure Detectors

```mermaid
graph TD
    HB[Heartbeat] --> TIMEOUT{Timeout?}
    TIMEOUT -->|No| ALIVE[Node alive]
    TIMEOUT -->|Yes| SUSPECT[Node suspected failed]
    SUSPECT --> MARK[Mark as failed after grace period]
    MARK --> REPLICA[Re-replicate data]
```

### Anti-Entropy and Merkle Trees

```mermaid
graph TD
    subgraph Merkle[Merkle Tree Comparison]
        ROOT[Root Hash] --> H1[Hash 0-3]
        ROOT --> H2[Hash 4-7]
        H1 --> H10[Hash 0-1]
        H1 --> H11[Hash 2-3]
        H10 --> B0[Block 0]
        H10 --> B1[Block 1]
    end

    N1[Node 1 Merkle] -->|Compare| N2[Node 2 Merkle]
    N1 -->|Root mismatch| DIFF[Find differing subtrees]
    DIFF --> SYNC[Sync only differing blocks]
```

Merkle trees enable efficient detection of which blocks differ between replicas without transferring all data.

## Interview Questions

1. **Q: Explain the CAP theorem and its practical implications.**
   A: In a distributed system, you can only guarantee two of: Consistency (all nodes see the same data), Availability (every request gets a response), Partition tolerance (system works despite network failures). Since network partitions are unavoidable, the real choice is between CP (consistent but may reject requests) and AP (available but may return stale data).

2. **Q: How does consistent hashing work and why is it better than simple modulo hashing?**
   A: Consistent hashing maps both keys and nodes to a ring. Each key goes to the next node clockwise. When a node is added/removed, only keys in that node's range move (1/N of all keys). Simple modulo hashing remaps most keys when N changes. Virtual nodes improve balance.

3. **Q: What is a quorum in distributed storage?**
   A: A quorum is the minimum number of nodes that must agree for an operation to succeed. For N replicas, if you write to W nodes and read from R nodes, and W + R > N, you're guaranteed to read at least one node with the latest write. Typical: N=3, W=2, R=2.

4. **Q: Explain Raft consensus in simple terms.**
   A: Raft elects one leader. All client requests go through the leader. The leader appends entries to its log and replicates them to followers. An entry is committed when a majority of nodes have it. If the leader fails, a new election happens. Committed entries are never lost.

5. **Q: How does Spanner achieve global consistency?**
   A: Spanner uses Paxos for replication and TrueTime (GPS + atomic clocks) to bound clock uncertainty across datacenters. Transactions use a commit-wait protocol: after committing, wait until TrueTime guarantees the commit timestamp is in the past everywhere. This enables externally consistent global transactions.

## Common Mistakes

- Confusing **replication** with **backup** — replication protects against node failure, not accidental deletion or corruption.
- Assuming **eventual consistency** is always acceptable — financial transactions, inventory, and leaderboards need strong consistency.
- Not considering **network partitions** — in distributed systems, partitions WILL happen. Design for it.
- Ignoring **tail latency** — with quorum reads/writes, latency = slowest node in quorum. P99 matters.
- Treating **consensus as free** — Paxos/Raft add latency and complexity. Only use when you actually need strong consistency.

## Summary

Distributed storage systems use partitioning (consistent hashing, range-based) to split data and replication (leader-based, leaderless) for fault tolerance. Consistency models range from linearizable (strongest, requires consensus) to eventual (weakest, highest availability). Consensus algorithms (Paxos, Raft) enable strong consistency. For interviews, understand the CAP theorem, quorum systems, consistent hashing, and the trade-offs between consistency and availability.

## Cross-References

- [Erasure Coding](./erasure-coding.md) — Space-efficient alternative to replication
- [Ceph](./ceph.md) — Production distributed storage system
- [Object Storage](./object-storage.md) — Built on distributed storage
- [Storage Overview](./overview.md) — Storage hierarchy
