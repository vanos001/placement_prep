# ZooKeeper Atomic Broadcast (ZAB)

## Overview

ZAB (ZooKeeper Atomic Broadcast) is the consensus protocol used by Apache ZooKeeper. It provides total ordering of messages and ensures that all updates to ZooKeeper's state are replicated consistently across all servers. ZAB is similar to Raft and Multi-Paxos but was designed specifically for ZooKeeper's use case: a hierarchical key-value store used for coordination.

## ZAB's Guarantees

1. **Total ordering**: Messages are delivered in the same order to all nodes
2. **Causal ordering**: If message A causally precedes message B, A is delivered before B
3. **Reliability**: If a message is delivered, it will be delivered to all correct nodes

## ZAB vs. Raft

| Aspect | ZAB | Raft |
|--------|-----|------|
| Designed for | ZooKeeper | General consensus |
| Leader name | Leader | Leader |
| Log entries | Transactions (zxid) | Log entries |
| Epoch | Epoch (high 32 bits of zxid) | Term |
| Message ordering | Atomic broadcast | Log replication |

## ZAB Protocol Phases

ZAB operates in four phases:

```mermaid
stateDiagram-v2
    [*] --> Election: Start or leader failure
    Election --> Discovery: Leader elected
    Discovery --> Synchronization: History synced
    Synchronization --> Broadcast: Ready for requests
    Broadcast --> Election: Leader failure
```

### Phase 1: Election (Leader Election)

When the system starts or the leader fails, nodes elect a new leader. ZooKeeper uses a fast leader election algorithm based on **zxid** (transaction ID):

```mermaid
sequenceDiagram
    participant S1 as Server 1 (zxid: 10.5)
    participant S2 as Server 2 (zxid: 10.3)
    participant S3 as Server 3 (zxid: 9.1)
    
    Note over S1: Propose self as leader
    S1->>S2: LEADER_ELECTION(epoch=10, zxid=10.5)
    S1->>S3: LEADER_ELECTION(epoch=10, zxid=10.5)
    
    S2-->>S1: ACK (I have lower zxid)
    S3-->>S1: ACK (I have lower zxid)
    
    Note over S1: Majority votes → become Leader
```

**Voting rule**: A server with a higher zxid (more up-to-date) is preferred. If zxids are equal, the server with the higher server ID wins.

### Phase 2: Discovery

The new leader collects information from followers about their last processed transactions:

```mermaid
sequenceDiagram
    participant L as Leader
    participant F1 as Follower 1
    participant F2 as Follower 2
    
    L->>F1: FOLLOWERINFO(epoch=10)
    L->>F2: FOLLOWERINFO(epoch=10)
    
    F1-->>L: LEADERINFO(lastZxid=10.5)
    F2-->>L: LEADERINFO(lastZxid=10.3)
    
    Note over L: Learns followers' states
```

The leader determines the **highest zxid** among all followers and establishes a new **epoch**.

### Phase 3: Synchronization

The leader ensures all followers have a consistent history:

```mermaid
sequenceDiagram
    participant L as Leader (history up to zxid 10.5)
    participant F1 as Follower 1 (up to 10.5)
    participant F2 as Follower 2 (up to 10.3)
    
    Note over L: F2 is behind
    L->>F2: DIFF (send entries 10.4 and 10.5)
    L->>F1: NEWLEADER(epoch=10)
    
    F2-->>L: ACK
    F1-->>L: ACK
    
    Note over L: Majority synced → proceed to broadcast
```

### Phase 4: Broadcast (Normal Operation)

Once synchronized, the system processes client requests using atomic broadcast:

```mermaid
sequenceDiagram
    participant C as Client
    participant L as Leader
    participant F1 as Follower 1
    participant F2 as Follower 2
    
    C->>L: write(x=5)
    
    Note over L: Phase 1: PROPOSE
    L->>F1: PROPOSE(zxid=11.1, x=5)
    L->>F2: PROPOSE(zxid=11.1, x=5)
    
    Note over F1,F2: Phase 2: ACK
    F1-->>L: ACK(zxid=11.1)
    F2-->>L: ACK(zxid=11.1)
    
    Note over L: Majority ACKed → COMMIT
    L->>F1: COMMIT(zxid=11.1)
    L->>F2: COMMIT(zxid=11.1)
    L-->>C: OK
    
    F1->>F1: Apply to state machine
    F2->>F2: Apply to state machine
```

## Zxid Structure

The zxid is a 64-bit number:

```
|<--- 32 bits --->|<--- 32 bits --->|
|     Epoch       |    Counter      |
```

- **Epoch**: Incremented each time a new leader is elected
- **Counter**: Incremented for each transaction within an epoch

This ensures monotonically increasing transaction IDs across leader changes.

## ZAB Atomic Broadcast Properties

| Property | Description |
|----------|-------------|
| **Integrity** | A message is delivered at most once |
| **Total order** | All messages are delivered in the same order |
| **Agreement** | If a message is delivered by one node, it's delivered by all correct nodes |
| **Validity** | If a correct sender broadcasts a message, it will eventually be delivered |

## ZAB Failure Handling

### Leader Failure

```mermaid
sequenceDiagram
    participant L as Leader (crashes)
    participant F1 as Follower 1
    participant F2 as Follower 2
    
    L--xF1: Heartbeat lost
    L--xF2: Heartbeat lost
    
    Note over F1: Election timeout
    F1->>F2: Propose self as leader
    F2-->>F1: Vote
    
    Note over F1: New leader elected
    F1->>F2: Synchronize state
    Note over F1,F2: Resume broadcast
```

### Follower Failure and Recovery

```mermaid
sequenceDiagram
    participant L as Leader
    participant F as Follower (recovers)
    
    Note over F: Reconnects
    F->>L: FOLLOWERINFO(lastZxid=10.3)
    
    L->>F: DIFF (send missing transactions)
    
    F-->>L: ACK
    L->>F: NEWLEADER(epoch=11)
    
    Note over F: Catch up complete, join broadcast
```

## ZAB in ZooKeeper

ZooKeeper uses ZAB to replicate its **data tree** (hierarchical key-value store):

```mermaid
graph TD
    subgraph "ZooKeeper Data Tree"
        Root["/"] --> Z1["/services"]
        Root --> Z2["/config"]
        Z1 --> Z3["/services/api"]
        Z1 --> Z4["/services/db"]
    end
    
    subgraph "ZAB Replication"
        Write["Client Write"] --> Leader
        Leader --> F1["Follower 1"]
        Leader --> F2["Follower 2"]
    end
```

## ZAB vs. Paxos

| Aspect | ZAB | Paxos |
|--------|-----|-------|
| Message ordering | Total order guaranteed | No inherent ordering |
| Leader role | Required | Optional |
| Epoch handling | Part of zxid | Separate from values |
| Use case | State machine replication | Single value consensus |

## Interview Questions

1. **What is ZAB and how does it differ from Paxos?**
   - ZAB is ZooKeeper's atomic broadcast protocol. Unlike Paxos (which decides single values), ZAB provides total ordering of a message stream. It uses epochs (like Raft terms) and guarantees causal ordering.

2. **What is a zxid in ZooKeeper?**
   - A 64-bit transaction ID with a 32-bit epoch (leader term) and 32-bit counter. It monotonically increases, ensuring total ordering of transactions across leader changes.

3. **What are the four phases of ZAB?**
   - Election: Choose a new leader. Discovery: Leader learns followers' states. Synchronization: Leader ensures all followers are consistent. Broadcast: Normal atomic broadcast operation.

4. **How does ZAB handle leader failure?**
   - Followers detect missing heartbeats, trigger a new election. The new leader discovers the most up-to-date state, synchronizes followers, and resumes broadcast.

5. **Why does ZAB need a separate synchronization phase?**
   - After election, followers may have divergent states. Synchronization ensures all nodes have a consistent history before accepting new requests.

## Common Mistakes

- Confusing ZAB's **epoch** with Raft's **term** — they're conceptually similar but implementation details differ
- Thinking ZAB is identical to Raft — while similar, ZAB has distinct phases and zxid structure
- Forgetting that ZooKeeper reads can be served by followers (only writes go through ZAB)
- Not understanding that zxid ordering is what provides ZooKeeper's sequential consistency

## Summary

ZAB is ZooKeeper's consensus protocol that provides atomic broadcast with total ordering. It operates in four phases: election, discovery, synchronization, and broadcast. The zxid (epoch + counter) ensures globally unique, monotonically increasing transaction IDs. ZAB is conceptually similar to Raft but was designed specifically for ZooKeeper's state machine replication needs.

## Cross-References

- [Consensus Overview](README.md) — Consensus problem definition
- [Raft](raft.md) — A very similar protocol
- [Paxos](paxos.md) — The classic consensus algorithm
- [Service Discovery](../microservices/discovery.md) — ZooKeeper is commonly used for this
- [Primary-Backup Replication](../replication/primary-backup.md) — ZAB implements this pattern
