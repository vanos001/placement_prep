# Consistency Tradeoffs in Distributed Systems

## The Fundamental Challenge

In distributed systems, you can't have everything. The **CAP theorem** proves that when a network partition occurs, you must choose between consistency and availability.

## CAP Theorem

### The Three Properties

```
         Consistency
            /\
           /  \
          /    \
         /  ??  \
        /________\
Availability    Partition
              Tolerance
```

| Property | Definition | Example |
|----------|-----------|---------|
| **Consistency** | Every read gets the most recent write | Read from any node → same result |
| **Availability** | Every request gets a (non-error) response | Node responds even if data is stale |
| **Partition Tolerance** | System works despite network failures | Nodes can't communicate → system still works |

### CAP in Practice

In a distributed system, network partitions **will** happen. So you must choose:

```
CP (Consistency + Partition Tolerance):
- Sacrifice availability during partitions
- Example: MongoDB (with majority reads), HBase, ZooKeeper

AP (Availability + Partition Tolerance):
- Sacrifice consistency during partitions
- Example: Cassandra, DynamoDB, CouchDB

CA (Consistency + Availability):
- Only possible in single-node systems
- Example: Traditional RDBMS on one server
```

### CAP Theorem Visualization

```
Normal operation (no partition):
Consistency ✓  Availability ✓  Partition Tolerance ✓
(All three work when network is healthy)

Network partition occurs:
Choose CP: Response = "Error, try again later" (unavailable but consistent)
Choose AP: Response = "Here's stale data" (available but inconsistent)
```

## Consistency Models

### Strong Consistency
Every read returns the most recent write.

```
Client A: Write(x=5) → Primary DB → Replicate to Replica
Client B: Read(x) → Must wait for replication → Returns 5

Guarantee: If you wrote it, everyone sees it immediately
Cost: Higher latency (must wait for replication)
```

**When to use**:
- Financial transactions
- Inventory management
- Any "single source of truth" scenario

### Eventual Consistency
Given enough time, all replicas converge to the same value.

```
Client A: Write(x=5) → Primary DB
Client B: Read(x) → Replica → May return 4 (old value)
... some time passes ...
Client C: Read(x) → Replica → Returns 5 (converged)

Guarantee: If you stop writing, eventually all reads return the last write
Cost: May read stale data temporarily
```

**When to use**:
- Social media feeds
- Product reviews
- DNS records
- CDN content

### Causal Consistency
Operations that are causally related are seen in the same order by all nodes.

```
Client A: Post("Hello") → Post("World")
Client B: Sees "Hello" before "World" (causal order preserved)
Client C: May see "World" before "Hello" IF no causal relationship

Guarantee: Cause-and-effect relationships preserved
Cost: More bookkeeping than eventual, less than strong
```

### Read-Your-Writes Consistency
A user always sees their own writes.

```
Client A: Write(x=5) → Read(x) → Always returns 5
Client B: Read(x) → May return 4 (not guaranteed to see A's write yet)

Guarantee: You see your own changes
Cost: Routing complexity (must read from same node/replica)
```

### Consistency Spectrum

```
Strong ←──────────────────────────────────→ Eventual
  │           │           │           │
Strong    Causal    Read-Your    Eventual
Consistency  Consistency  Writes    Consistency

Higher latency ←──────────────────→ Lower latency
Higher availability ←─────────────→ Lower availability
```

## Conflict Resolution

When multiple nodes accept writes concurrently, conflicts arise.

### Last-Writer-Wins (LWW)
```
Node 1: Write(x=5) at T=1
Node 2: Write(x=7) at T=2
Resolution: x=7 (latest timestamp wins)
```

- Simple to implement
- May lose concurrent updates
- Timestamps must be synchronized (problematic)

### Vector Clocks
```
Node 1: Write(x=5) → vector: {N1:1, N2:0}
Node 2: Write(x=7) → vector: {N1:0, N2:1}
Both concurrent: {N1:1, N2:0} and {N1:0, N2:1}
→ Conflict! Application must resolve.
```

- Tracks causal relationships
- Detects conflicts (doesn't resolve them)
- Used by DynamoDB, Riak

### CRDTs (Conflict-free Replicated Data Types)
Data structures that automatically resolve conflicts.

```
G-Counter (Grow-only Counter):
Node 1: {N1:5, N2:0}  → value = 5
Node 2: {N1:0, N2:3}  → value = 3
Merged: {N1:5, N2:3}  → value = 8

PN-Counter (Positive-Negative Counter):
Increment: G-Counter
Decrement: Separate G-Counter
Value: Increment - Decrement
```

**Types of CRDTs**:
| Type | Operations | Use Case |
|------|-----------|----------|
| G-Counter | Increment | Page views, likes |
| PN-Counter | Increment/Decrement | Shopping cart count |
| G-Set | Add | Tags, followers |
| OR-Set | Add/Remove | Shopping cart items |
| LWW-Register | Set | User profile |

### Merge Functions
```
Amazon DynamoDB: Last-writer-wins
Riak: Siblings (application resolves)
Redis: Single-leader (no conflict)
Cassandra: LWW with timestamp
```

## Real-World Consistency Choices

### Amazon DynamoDB
- **Default**: Eventually consistent reads
- **Option**: Strongly consistent reads (higher cost, higher latency)
- **Why**: Massive scale requires availability over consistency

### Cassandra
- **Model**: Tunable consistency
- **Options**: ONE, QUORUM, ALL
- **Formula**: W + R > N = strong consistency
  - W=2, R=2, N=3 → 2+2 > 3 → strong consistency

### PostgreSQL
- **Default**: Strong consistency (single node)
- **Replication**: Async by default, sync option available
- **Why**: ACID transactions are core feature

### MongoDB
- **Default**: Strong consistency (primary reads)
- **Secondary reads**: Eventually consistent
- **Write concern**: Configurable (w:1, w:majority)

## Tunable Consistency

Some systems let you choose consistency level per operation.

### Cassandra Consistency Levels
```
ONE:    Ack from 1 replica     (fastest, weakest)
QUORUM: Ack from majority      (balanced)
ALL:    Ack from all replicas  (slowest, strongest)

Example (replication factor = 3):
Write QUORUM (2) + Read QUORUM (2) = 4 > 3 → Strong consistency
Write ONE (1) + Read ONE (1) = 2 < 3 → Eventual consistency
```

## PACELC Theorem

Extension of CAP that accounts for normal operation.

```
If Partition:
  Choose A (availability) or C (consistency)
Else (normal operation):
  Choose L (latency) or C (consistency)
```

| System | Partition: A or C | Else: L or C |
|--------|------------------|--------------|
| Cassandra | A | L (low latency) |
| MongoDB | C | C (consistency) |
| DynamoDB | A | L |
| PostgreSQL | C | C |

## Interview Tips

1. **Always mention CAP** — It shows distributed systems understanding
2. **Choose based on requirements** — "Financial data needs strong consistency"
3. **Discuss trade-offs explicitly** — "We choose availability over consistency because..."
4. **Mention specific technologies** — "Cassandra with QUORUM reads for strong consistency"
5. **Consider tunable consistency** — "Different operations need different consistency levels"
6. **Talk about conflict resolution** — "We'll use vector clocks to detect conflicts"
7. **Don't forget about normal operation** — PACELC extends CAP
8. **Give concrete examples** — "User profile can be eventually consistent, but bank balance must be strongly consistent"

## Common Mistakes

- ❌ Assuming strong consistency is always needed
- ❌ Ignoring network partitions in distributed systems
- ❌ Using LWW without understanding data loss implications
- ❌ Not considering the latency cost of strong consistency
- ❌ Confusing consistency models

## Cross-References

- [Database Design](./database-design.md) — Replication and consistency
- [Availability](./availability.md) — CAP and availability trade-offs
- [Caching Strategy](./caching-strategy.md) — Cache consistency
- [Scalability](./scalability.md) — Sharding and consistency
- [Messaging Systems](./messaging-systems.md) — Eventual consistency in async systems
