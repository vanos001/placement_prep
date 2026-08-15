# Advanced Replication Strategies

> **Reference papers**: Ladin et al. (1992) — CRAQ; Malkhi et al. (2012) — Merkle tree sync; DeCandia et al. (2007) — Dynamo

## Primary-Backup: Production Details

See [primary-backup basics](../replication/primary-backup.md). Production systems add several optimizations:

### Synchronous vs Asynchronous Replication

```
Synchronous (strong consistency):
  Client → Primary → Backup (wait) → ACK to client
  Latency: 1 RTT to backup + 1 RTT to client
  Used by: PostgreSQL synchronous replicas, MySQL semi-sync

Asynchronous (eventual consistency):
  Client → Primary → ACK to client → Primary → Backup (later)
  Latency: 1 RTT to client only
  Used by: most production defaults, MongoDB secondaries
```

### Log-Shipping vs Statement-Based

- **Log shipping (WAL replication)**: the primary sends its write-ahead log entries to backups, which replay them. This handles non-deterministic operations correctly (e.g., `NOW()`, random values) because the actual values are in the log.
- **Statement-based replication**: the primary sends SQL statements to backups. Requires all operations to be deterministic, which is often violated in practice.
- **Row-based replication**: the primary sends the actual row changes (before/after images). Used by MySQL's binlog in row mode.

## Chain Replication Deep Dive

See [chain replication basics](../replication/chain.md).

### Chain Replication with Apportioned Queries (CRAQ)

**CRAQ** (Ladin et al., 1992) extends chain replication to allow **any replica** to serve reads (not just the tail), while still maintaining strong consistency via a versioning scheme.

#### Protocol

1. Each object version is tagged with a **version number**
2. All replicas store all versions, but only the **latest** is "current"
3. When the tail commits a write, it increments the version and sends a **version update** backward through the chain
4. Any replica can serve reads at the latest committed version it knows about
5. A replica that hasn't received the version update yet serves the **previous** version (which is still valid)

```
  Client read → Replica 2 (knows v=5) → returns value at v=5

  Meanwhile, a write committed at tail (v=6):
    Tail → Replica 3: "object X is now v=6"
    Replica 3 → Replica 2: "object X is now v=6"
    Replica 2 → Replica 1: "object X is now v=6"

  Reads served during the version propagation are still consistent
  because they return a valid (if slightly stale) committed version
```

#### CRAQ vs Chain Replication

| Aspect | Chain Replication | CRAQ |
|--------|------------------|------|
| Read location | Tail only | Any replica |
| Read throughput | Limited by tail | Scales with replicas |
| Write throughput | Same | Same (bottleneck at head) |
| Consistency | Strong (linearizable) | Strong (linearizable) |
| Extra overhead | None | Version updates backward |

## Witness Replicas

**Witness replicas** participate in consensus (voting) but do **not** store the actual data. They exist solely to pad the quorum size, allowing systems to maintain fault tolerance with fewer full replicas.

### Use Cases

- **CockroachDB**: uses witness replicas for ranges that need fault tolerance but are infrequently accessed
- **Cost optimization**: a witness stores only the Raft log metadata (a few KB) instead of the full data (potentially GBs)

```
  Without witness: 3 full replicas for f=1 tolerance
    → 3× storage cost

  With witness: 2 full replicas + 1 witness for f=1 tolerance
    → 2× storage cost + minimal witness overhead
    → Witness can still vote in Raft, maintaining quorum safety
```

### Witness Tradeoffs

- **Pro**: reduced storage cost while maintaining fault tolerance
- **Con**: if both full replicas fail, the witness can't serve data (only voting)
- **Con**: witness promotion to full replica requires a full data transfer

## Quorum Replication: Advanced Patterns

See [quorum basics](../replication/quorum.md).

### Anti-Entropy via Merkle Trees

**Anti-entropy** is the process of reconciling divergent replicas. Merkle trees (hash trees) enable efficient difference detection:

```
           Root Hash
          /          \
     Hash(L)      Hash(R)
     /    \        /    \
   H(a)  H(b)   H(c)  H(d)
    |     |       |     |
  [k:a] [k:b]  [k:c] [k:d]

  Compare root hashes:
  - If equal → replicas are identical
  - If different → recurse into children to find the divergent subtrees
  - Each level comparison narrows the search by half
```

The tree has `O(log n)` levels for `n` keys. Comparing each level costs `O(fan-out)` where `fan-out` is the branching factor (typically 16-256). Total comparison cost is `O(fan-out × log n)` vs. `O(n)` for comparing all keys.

**Cassandra** uses Merkle tree anti-entropy in its repair process. During repair, two replicas exchange Merkle tree digests level by level, descending into subtrees only when hashes differ. The differing keys are then synchronized.

### Hinted Handoff

When a replica is down, the coordinator stores **hints** — lightweight records of writes that the downed replica missed. When the replica recovers, hints are delivered to it.

```
1. Client writes to key owned by Node D (which is down)
2. Coordinator routes write to Nodes A, B, C (other replicas)
3. Coordinator also stores a hint: "Node D missed write(key, value, ts)"
4. Node D comes back online
5. Coordinator sends all hints for Node D
6. Node D applies missed writes
```

**Used by**: Cassandra, Dynamo, Riak. Hinted handoff significantly reduces recovery time after node failures by avoiding a full anti-entropy scan.

### Read Repair

On a read, if replicas return different versions, the coordinator triggers **read repair**: it writes the most recent version back to the lagging replicas.

```
Client reads key "k" from replicas A, B, C:
  A returns (value="X", ts=10)
  B returns (value="Y", ts=10)   ← concurrent with X
  C returns (value="X", ts=10)

Coordinator detects B has different value at same timestamp (conflict)
  → Triggers read repair: sends X to B (or resolves conflict)
  → Returns resolved value to client
```

Read repair is **eventual consistency's convergence mechanism** for read path. Combined with **anti-entropy** (background Merkle tree sync for the write path), it guarantees convergence.

### Sloppy Quorum

During failures, Dynamo-style systems use **sloppy quorums** — a node that is temporarily unavailable is replaced by a "preferred list" alternative (usually the next node in the consistent hash ring).

```
  Normal: key "K" maps to nodes [A, B, C]
  Node B is down → sloppy quorum uses [A, D, C] instead
    D is the next node after B in the ring
  When B recovers, hints are handed off from D to B
```

**Tradeoff**: sloppy quorums improve **availability** (you can always find `W` or `R` live nodes) at the cost of **temporary consistency weakening** (the same key might be stored on different node sets during different failure windows).

## Replication Strategy Comparison

| Strategy | Write Path | Read Path | Consistency | Availability | Best For |
|----------|-----------|-----------|-------------|-------------|----------|
| Synchronous primary-backup | Primary → all, wait | From primary | Linearizable | Moderate | OLTP databases |
| Chain | Head → ... → Tail | From tail | Linearizable | Moderate | Storage systems |
| CRAQ | Head → ... → Tail, version back-propagation | From any | Linearizable | High reads | Read-heavy workloads |
| Quorum (R+W>N) | W replicas acknowledge | R replicas respond | Tunable | High | Dynamo-style stores |
| Multi-leader | Any leader, conflict resolution | From local leader | Eventual | Highest | Geo-distributed writes |

> **Interview Angle**: "Design a replication strategy for a global key-value store with 3 datacenters (US, EU, Asia), each with 5 nodes. Must tolerate full DC failure. Writes should be fast from any DC." Use multi-leader replication with quorum reads (R=2 from local DC) and asynchronous cross-DC replication. Each DC runs a local quorum of 3/5. Writes go to the local DC and are asynchronously propagated to other DCs. For keys that need strong consistency, use a cross-DC consensus group (Raft with 1 node per DC, total 3, quorum=2). Cross-reference: [multi-primary replication](../replication/multi-primary.md) and [quorum systems](quorum-systems.md).