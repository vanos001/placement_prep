# Anti-Entropy Protocols

Anti-entropy is a class of protocols for detecting and repairing divergence between replicas in eventually-consistent distributed systems. The name comes from the entropy metaphor: replicas drift apart (entropy increases) due to concurrent writes, network partitions, and failure recoveries. Anti-entropy protocols reduce this drift by periodically comparing replicas and reconciling differences. This page covers the canonical algorithms (Merkle tree sync, read-repair, hinted handoff, vector-clock-based reconciliation), and how Dynamo, Cassandra, and Riak use them in production.

## Why Anti-Entropy Exists

In a strongly consistent system (e.g., Spanner), every write goes through a leader and is replicated synchronously. Replicas never diverge because they all see the same writes in the same order.

In an eventually consistent system (e.g., Dynamo), writes can go to any replica. During a network partition, different replicas may accept different writes:

```text
Time T0:
  Replica A: { key1: v1, key2: v2 }
  Replica B: { key1: v1, key2: v2 }

Time T1: Network partition between A and B
  Replica A: { key1: v1a, key2: v2 }   ← writes v1a to key1
  Replica B: { key1: v1, key2: v2b }   ← writes v2b to key2

Time T2: Partition heals. A and B must reconcile.
```

After healing, A and B have conflicting versions. The reconciliation (which version wins) is application-specific — but the system must first detect that the versions differ. Anti-entropy protocols do this detection.

## The Three Canonical Mechanisms

### 1. Read Repair

When a client reads a key, the coordinator contacts multiple replicas. If the replicas return different versions, the coordinator:

1. Reconciles the versions (using vector clocks or application logic).
2. Returns the reconciled version to the client.
3. Writes the reconciled version back to the replicas that returned stale versions.

Read repair is **lazy**: it only fixes divergence that a client happens to observe. Replicas that are not read continue to drift. Dynamo uses read repair as its primary anti-entropy mechanism for frequently-read keys.

### 2. Hinted Handoff

When a write should go to replica R, but R is unreachable, the write goes to a different node R' as a "hint". R' stores the write locally (typically in a separate "hint" area), and periodically tries to deliver it to R when R comes back online.

```text
Coordinator: send write(key=K, value=V) to replicas A, B, C
A acks OK
B unreachable → coordinator sends to D with hint: "deliver to B when B returns"
C acks OK

D stores: hint[B] = (K, V)
D periodically tries to deliver (K, V) to B.
```

Hinted handoff is **best-effort**: if D crashes before delivering the hint, the hint is lost. Cassandra, Dynamo, and Voldemort all use hinted handoff.

### 3. Merkle Tree Anti-Entropy (Background Reconciliation)

Periodically, replicas exchange Merkle trees (hash trees) of their key ranges and compare:

1. Each replica computes a Merkle tree over its keys, with leaf nodes being hashes of (key, value) pairs.
2. Two replicas exchange the roots of their Merkle trees.
3. If the roots differ, they recursively compare child nodes until they reach the leaves that differ.
4. The differing leaves identify the keys that need to be reconciled.

Merkle tree sync is O(log N) bytes for the comparison and O(diff) bytes for the actual repair, where N is the number of keys and diff is the number that differ. This is much more efficient than a full state comparison (which is O(N) bytes).

Cassandra's `nodetool repair` command runs Merkle tree sync to reconcile divergent replicas. Riak's Active Anti-Entropy runs it in the background continuously.

## Vector Clock Reconciliation

Once divergence is detected, the system must reconcile. The standard mechanism is **vector clocks** (or dotted version vectors, which fix a specific issue with vector clocks).

A vector clock tracks, per replica, the number of writes that replica has seen. When replica A writes a value, it increments its own entry in the vector clock:

```text
Replica A's state: { key1: (v1, [A:1]) }   ← A wrote v1, vector clock [A:1]
Replica B's state: { key1: (v2, [B:1]) }   ← B wrote v2, vector clock [B:1]
```

When the two replicas see each other's writes, the reconciliation algorithm:

1. If `v1.clock < v2.clock` (v1 causally precedes v2): v2 wins.
2. If `v2.clock < v1.clock` (v2 causally precedes v1): v1 wins.
3. If neither is causally before the other: conflict — return both to the application.

The application's conflict-resolution logic typically picks one:
- **Last-Writer-Wins (LWW)**: use wall-clock timestamps; the latest write wins. Loses data if timestamps are concurrent.
- **Application-specific merge**: e.g., for a counter, sum the two values; for a set, union them.

The merged value gets a new vector clock that includes both predecessors.

## Production Implementations

### Dynamo (Amazon, 2007)

Dynamo's anti-entropy combines read repair (lazy, for hot keys) and Merkle tree sync (background, every N seconds). The Merkle trees are computed per "virtual node" (a hash range), so the comparison is fast.

Dynamo's read path requires `R` replicas to respond (default 3 of 3). If they disagree, read repair is triggered. If they agree (the common case), no repair happens.

### Cassandra

Cassandra uses:
- Read repair on every read (lazily, in the background).
- Hinted handoff when a write target is down (with a configurable TTL).
- Background Merkle tree sync via `nodetool repair` (manual) and "incremental repair" (continuous).

The Merkle tree is computed per range (a hash-partitioned chunk of the keyspace). A repair job computes the tree on each replica, exchanges, and reconciles differences.

### Riak

Riak's "Active Anti-Entropy" (AAE) continuously runs in the background:
- Each vnode maintains a hash of every key.
- AAE workers periodically compare hashes against the canonical N replicas.
- Differences are reconciled using vector clocks (with LWW fallback for conflicts).

Riak's AAE is the most thorough of the three — it operates continuously, not in response to client requests.

## Trade-offs

| Mechanism | Trigger | Repair latency | Network cost | Storage cost |
|-----------|---------|-----------------|---------------|---------------|
| Read repair | Client read | Immediate (at read time) | Low (only on read) | Low |
| Hinted handoff | Write failure | On recovery (seconds-minutes) | Low (per hint) | Medium (hint storage) |
| Merkle sync | Periodic (e.g., every hour) | Hours (until next sync) | O(log N) per range | High (tree maintenance) |
| Continuous AAE | Continuous | Seconds | Medium (per-vnode comparison) | Medium (hash storage) |

Production systems combine all four: read repair for hot keys, hinted handoff for transient failures, Merkle sync for periodic reconciliation, and AAE for continuous monitoring.

## Why Anti-Entropy Is Hard

1. **Conflict resolution is application-specific.** The system can detect divergence but cannot always resolve it. The application must implement merge logic, which is error-prone (especially for nested data structures).

2. **Merkle tree maintenance is expensive.** A tree over a billion keys takes ~30 GB of memory (a 64-byte hash per key, 2× overhead for the tree structure). Computing the tree incrementally (on each write) is the standard optimization.

3. **Repairs cause write amplification.** A Merkle tree diff identifies all divergent keys; repairing them all at once floods the network and disk. Production systems throttle repair rate.

4. **Background repair competes with foreground traffic.** A repair job that saturates the disk reads will starve client requests. Schedulers must prioritize client requests over repair.

## Modern Alternatives: CRDTs

A Conflict-Free Replicated Data Type (CRDT) is a data structure whose merge function is deterministic and associative: any two divergent states can be merged to the same result regardless of the order of operations. CRDTs eliminate the need for application-specific conflict resolution:

- **G-Counter**: each replica has its own counter; merge by taking the element-wise max.
- **PN-Counter**: a G-Counter + a "decrement" G-Counter; supports both inc and dec.
- **OR-Set (Observed-Remove Set)**: each add tags the element with a unique ID; remove takes the union of all IDs observed by the removing replica.

Riak and Redis support CRDTs natively. CockroachDB's CRDB-style counters are also CRDTs under the hood.

The trade-off: CRDTs are more complex to implement and may not match the application's semantics. A G-Counter that's used to track "current logged-in users" can over-count if users log in on multiple replicas concurrently.

## Common Pitfalls

1. **Treating read repair as sufficient.** Replicas that aren't read by clients never converge. Run periodic Merkle syncs to catch divergences that read repair misses.

2. **Letting hints pile up.** A replica that's down for days accumulates hints on every other replica. When it recovers, the hint delivery floods it. Configure hint TTLs (Cassandra default is 3 hours).

3. **Forgetting that LWW loses data.** Last-writer-wins uses wall-clock timestamps; concurrent writes that pick the same TS silently lose one. Use vector clocks + CRDTs where possible.

4. **Assuming Merkle trees always converge.** If the trees are based on stale data (e.g., a hash computed before a recent write), the comparison misses the divergence. Trees must be recomputed on each comparison.

5. **Not testing conflict resolution in production.** A bug in the merge function (e.g., off-by-one in a counter) propagates silently. Add tests for all merge scenarios.

## References

- DeCandia et al., "[Dynamo: Amazon's Highly Available Key-Value Store](https://www.cs.ucsb.edu/~suri/psdir/SOSP07-Dynamo.pdf)" (SOSP 2007)
- [Lamport: Time, Clocks, and the Ordering of Events](https://lamport.org/pubs/pubs.html#time-clocks) — vector clocks foundation
- [Cassandra Anti-Entropy Repair](https://cassandra.apache.org/doc/latest/operating/repair.html)
- [Riak Active Anti-Entropy](https://docs.riak.com/riak/kv/2.2.0/using/cluster-operations/active-anti-entropy.1.html)
- Shapiro et al., "[Conflict-free Replicated Data Types](https://hal.inria.fr/inria-00655378/document)" (SSS 2011)
- [LWN: Anti-entropy and reconciliation (2014)](https://lwn.net/Articles/612409/)
- [Merkle Trees for Syncing (Apache Cassandra)](https://cassandra.apache.org/doc/latest/cassandra/architecture/storage_internals.html)
