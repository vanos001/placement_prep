# Design a Key-Value Store

> **Difficulty:** ⭐⭐⭐ | **Asked at:** Amazon (DynamoDB), Google, Meta | **Time:** 45 minutes

## 🎯 Problem Statement

Design a distributed key-value store like DynamoDB, Redis Cluster, or etcd that:
- Supports put(key, value) and get(key) operations
- Handles high throughput with low latency
- Scales horizontally across many nodes
- Provides configurable consistency

---

## Step 1: Requirements

### Functional Requirements
1. put(key, value) — Store a key-value pair
2. get(key) → value — Retrieve value by key
3. delete(key) — Remove a key-value pair
4. TTL support — Auto-expire keys

### Non-Functional Requirements
| Requirement | Target |
|------------|--------|
| Latency | < 10ms for reads, < 50ms for writes |
| Throughput | 1M+ operations/sec |
| Availability | 99.99% |
| Durability | Data never lost |
| Scalability | Petabytes of data, thousands of nodes |

---

## Step 2: High-Level Design

### Single Node Design

```
┌─────────────────────────────────────────┐
│              KV Store Node              │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │     In-Memory Hash Map          │    │
│  │  (primary data structure)       │    │
│  └──────────────┬──────────────────┘    │
│                 │                       │
│  ┌──────────────▼──────────────────┐    │
│  │     Write-Ahead Log (WAL)       │    │
│  │  (durability on disk)           │    │
│  └──────────────┬──────────────────┘    │
│                 │                       │
│  ┌──────────────▼──────────────────┐    │
│  │     SSTable / LSM Tree          │    │
│  │  (persistent storage)           │    │
│  └─────────────────────────────────┘    │
│                                         │
└─────────────────────────────────────────┘

Write Path:
1. Write to WAL (append-only, fast)
2. Update in-memory hash map
3. Return success
4. Periodically flush to SSTable

Read Path:
1. Check in-memory hash map → Hit? Return
2. Check SSTables (newest to oldest) → Found? Return
3. Return not found
```

---

## Step 3: Deep Dive

### Data Partitioning — Consistent Hashing

```
Problem: How to distribute keys across N nodes?

Solution: Consistent Hashing

Hash Ring:
          Node A (0°)
           ╱    ╲
         ╱        ╲
  Node D ◄────────► Node B
  (270°)   ╲    ╱   (90°)
           ╲  ╱
         Node C (180°)

Key Placement:
  hash(key) → position on ring → first node clockwise

Adding Node E (between A and B):
  Only keys between A and E need to move (not all keys)

Virtual Nodes:
  Each physical node → multiple virtual nodes on ring
  Node A → A1, A2, A3, A4 (spread around ring)
  Better load distribution, handles uneven node capacities
```

```python
import hashlib
import bisect

class ConsistentHash:
    def __init__(self, nodes, virtual_nodes=150):
        self.ring = {}
        self.sorted_keys = []
        self.virtual_nodes = virtual_nodes

        for node in nodes:
            self.add_node(node)

    def add_node(self, node):
        for i in range(self.virtual_nodes):
            key = self._hash(f"{node}:{i}")
            self.ring[key] = node
            bisect.insort(self.sorted_keys, key)

    def get_node(self, key):
        if not self.ring:
            return None
        hash_val = self._hash(key)
        idx = bisect.bisect_right(self.sorted_keys, hash_val)
        if idx == len(self.sorted_keys):
            idx = 0
        return self.ring[self.sorted_keys[idx]]

    def _hash(self, key):
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
```

### Replication

```
Replication Factor = 3 (store each key on 3 nodes)

N1 (primary) ──replicate──→ N2 (secondary) ──replicate──→ N3 (secondary)

Strategy: Choose N-1 successor nodes on the hash ring

Consistency Levels:
┌─────────────┬────────────────────────────────────────────┐
│ Level       │ Behavior                                   │
├─────────────┼────────────────────────────────────────────┤
│ ONE         │ Return after 1 replica confirms            │
│ QUORUM      │ Return after (N/2 + 1) replicas confirm   │
│ ALL         │ Return after all N replicas confirm        │
│ LOCAL_QUORUM│ Quorum within local data center            │
└─────────────┴────────────────────────────────────────────┘

Trade-off:
  ONE    → Fast, but possible data loss
  QUORUM → Balance of speed and safety (recommended)
  ALL    → Slowest, strongest consistency
```

### Conflict Resolution

```
Problem: Network partition → two nodes accept different writes for same key

Solution 1: Last Write Wins (LWW)
├── Use timestamp to determine winner
├── Simple, but may lose writes
└── Used by: Cassandra (default)

Solution 2: Vector Clocks
├── Track causal ordering of events
├── Detect conflicts, let application resolve
└── Used by: Amazon Dynamo (2007 paper), Riak. (AWS DynamoDB the product uses LWW + conditional writes, not vector clocks.)

Vector Clock Example:
  Node A writes: VC = {A:1}
  Node B writes: VC = {B:1}  (concurrent!)
  Node C sees both: VC = {A:1, B:1} → CONFLICT detected
  Application resolves: merge values or pick one
```

### Storage Engine — LSM Tree

```
Write Path (LSM Tree):
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Write   │────→│ MemTable │────→│ WAL      │
│ Request  │     │ (sorted) │     │ (disk)   │
└──────────┘     └────┬─────┘     └──────────┘
                      │ (when full)
               ┌──────▼─────┐
               │  SSTable   │  (sorted, immutable)
               │  Level 0   │
               └──────┬─────┘
                      │ (compaction)
               ┌──────▼─────┐
               │  SSTable   │
               │  Level 1   │
               └──────┬─────┘
                      │
               ┌──────▼─────┐
               │  SSTable   │
               │  Level 2   │
               └────────────┘

Read Path:
1. Check MemTable
2. Check Bloom Filter (skip SSTable if key definitely not there)
3. Check SSTables Level 0 → 1 → 2

Compaction:
├── Size-Tiered: Merge SSTables of similar size
└── Leveled: Merge into levels with size limits
```

### Handling Failures

```
Detection: Gossip Protocol
├── Each node periodically pings random peers
├── If no response after N pings → mark as suspect
├── If no response after 2N pings → mark as failed
└── Failure info propagated to all nodes

Temporary Failures: Hinted Handoff
├── If target node is down, write to a nearby node
├── Nearby node stores "hint" (temporary copy)
├── When target recovers → replay hints
└── Ensures writes aren't lost during brief outages

Permanent Failures: Anti-Entropy with Merkle Trees
├── Each node maintains Merkle tree of its data
├── Compare trees with replica nodes
├── Only sync differing branches
└── Efficient synchronization of large datasets
```

---

## Step 4: Trade-offs

### CAP Theorem Choices

```
CP System (Consistency + Partition Tolerance):
├── Reject writes during partition if quorum can't be reached
├── Examples: HBase, MongoDB (with write concern majority)
└── Use: Financial data, inventory

AP System (Availability + Partition Tolerance):
├── Accept writes during partition, resolve conflicts later
├── Examples: Cassandra, DynamoDB, CouchDB
└── Use: Social media, shopping cart, analytics
```

### Consistency vs Latency
| Level | Write Latency | Read Latency | Consistency |
|-------|--------------|--------------|-------------|
| ONE | Lowest | Possible stale | Eventual |
| QUORUM | Medium | Fresh | Strong (probabilistic) |
| ALL | Highest | Always fresh | Strong |

## 🔗 Cross-References

- [Distributed File System](./dfs.md) — Similar distributed storage concepts
- [Architecture Concepts](../../cheatsheets/architecture.md) — CAP theorem, consistency models
- [DBMS Questions](../dbms-questions.md) — SQL vs NoSQL trade-offs
- [OS Questions](../os-questions.md) — File systems, I/O
