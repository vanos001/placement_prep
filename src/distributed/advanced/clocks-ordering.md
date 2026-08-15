# Clocks & Ordering — Advanced Topics

> **Reference papers**: Lamport (1978); Mattern (1988); Schwarz & Mattern (1994); Kulkarni et al. (2014) — dotted version vectors; Lloyd et al. (2011) — Hybrid Logical Clocks; Corbett et al. (2012) — Spanner/TrueTime

## Vector Clocks: Deeper Dive

[Vector clocks](../fundamentals/vector-clocks.md) track causality by assigning each process a component in a logical clock vector. Event `e` on process `p` increments `VC[e][p]` and merges (`component-wise max`) with received message timestamps.

### Vector Clock Properties

- **Happened-before**: `a → b` iff `VC[a] < VC[b]` (strictly less in every component, at least one strictly less)
- **Concurrent**: `a ∥ b` iff neither `VC[a] ≤ VC[b]` nor `VC[b] ≤ VC[a]`
- **Size**: `O(n)` per event, where `n` is the number of processes
- **Comparison cost**: `O(n)` per comparison

### Scalability Problem

With thousands of processes, each vector clock entry is kilobytes in size, and comparison is expensive. Several compressed variants address this:

| Variant | Space per Event | Comparison Cost | Use Case |
|---------|----------------|-----------------|----------|
| Full VC | O(n) | O(n) | Small groups |
| Version vectors (per-key) | O(n) per key | O(n) | Dynamo, Riak |
| Dotted VV | O(k) where k = concurrent writers | O(k) | Riak 2.0 |
| Interval tree clocks | O(log n) amortized | O(log n) | Theoretical |
| Matrix clocks | O(n²) | O(n²) | Detecting common knowledge |
| Hybrid logical clocks | O(1) | O(1) | Spanner, CockroachDB |

## Dotted Version Vectors

**Dotted version vectors** (DVV) solve a fundamental problem with standard version vectors in dynamo-style systems: when a client writes concurrently with a server-side update, a plain version vector can't distinguish "this client saw version X and intentionally branched" from "this client didn't know about version X."

### The Problem

``n```
1. Server has key "k" at vclock [A:2, B:1]
2. Client reads "k" → gets vclock [A:2, B:1]
3. Meanwhile, Server receives write from B → vclock [A:2, B:2]
4. Client writes back (intending sibling) with vclock [A:2, B:1]
   → With plain VV: this looks like a stale overwrite!
   → With DVV: the dot counter distinguishes client-caused siblings
```

### Solution: Add a Dot Counter

A dotted version vector is a pair `(vc, dot)` where:
- `vc` is a standard version vector
- `dot` is a pair `(node_id, counter)` identifying the specific event that caused this version

```
DVV = (vclock: [A:2, B:2], dot: (C, 1))
       ↑ the server's context    ↑ the client's unique contribution
```

**Ordering rule**: `(vc1, d1) < (vc2, d2)` iff `vc1 < vc2` OR (`vc1 == vc2` AND `d1.counter < d2.counter`). This ensures that concurrent sibling creation is properly detected and never mistaken for a stale overwrite.

Riak 2.0 adopted DVVs as their internal conflict detection mechanism, replacing the older plain version vector approach.

> **Interview Angle**: "Explain the problem with version vectors that DVVs solve." With plain VVs, a concurrent write looks identical to a stale write when the client's knowledge is behind. DVVs add a per-event dot that makes it explicit: "I saw up to this context, and here's my new contribution." This is crucial for avoiding false conflict detection in read-modify-write cycles.

## Interval Tree Clocks (ITC)

**Interval Tree Clocks** (Preguiça, Baquero, Shapiro, 2008) achieve `O(log n)` space per event by encoding the causal history as a balanced binary tree (an interval) rather than a flat vector.

### Encoding

Each event gets an **interval** in the rational number space `[0, 1)`:
- A process's events occupy a sub-interval
- Forking a process splits the interval
- Joining (syncing) takes the union

```
Process A: [0, 1)          Event 1: [0, 0.5)
    ↓ fork                 Event 2: [0.5, 1)
Process B: [0, 0.5)       Event 3: [0, 0.25)
Process A: [0.5, 1)

Event 3 < Event 1 < Event 2  (by interval ordering)
```

The interval is represented as a balanced binary tree where each node is either a `Leaf(id, count)` or a `Fork(left, right)`. Operations are `O(log n)` amortized because the tree depth grows logarithmically with the number of concurrent processes.

In practice, ITCs have not seen widespread production adoption due to implementation complexity, but they remain important theoretically as a proof that sub-linear causal tracking is possible.

## Matrix Clocks

**Matrix clocks** extend vector clocks to track **what every process knows about what every other process knows**. A matrix clock on process `i` is an `n × n` matrix `MC[i]` where:

- `MC[i][j][k]` = process `i`'s knowledge of process `j`'s knowledge of process `k`'s logical clock
- The diagonal `MC[i][j][j]` equals process `j`'s vector clock as known by process `i`

### Use Cases

1. **Garbage collection**: if `MC[i][j][k]` is sufficiently advanced, process `i` knows that process `j` knows about event `k`, so event `k`'s data can be safely garbage collected
2. **Distributed termination detection**: all processes have "caught up" when the entire matrix stabilizes
3. **Checkpointing**: determining a consistent global snapshot

Space is `O(n²)` per process, limiting scalability to small groups. Used in research systems and some specialized coordination services.

## Hybrid Logical Clocks (HLC)

**Hybrid Logical Clocks** (Lloyd et al., 2011) combine the best of physical and logical clocks into a single `O(1)`-size timestamp. Used in **CockroachDB** and **Google Spanner** (as part of TrueTime).

### HLC Structure

```
HLC = (l, pt, c)
  l  = logical time (monotonically non-decreasing, tracks max of physical times seen)
  pt = physical time (wall clock at the moment of last update)
  c  = counter (disambiguates events within the same l value)
```

### HLC Algorithm

```
Send/Local event:
  l' = max(l_now, pt_now)  # logical time is max of current logical and physical
  if l' == l_now and pt_now == pt:
      c' = c + 1            # same logical tick → increment counter
  else:
      c' = 0                # new logical tick → reset counter
  pt' = max(pt_now, pt)    # update physical time
  return (l', pt', c')

Receive event (received timestamp (l_j, pt_j, c_j)):
  l' = max(l_now, pt_now, l_j)
  if l' == l_now and pt_now == pt:
      c' = c + 1
  elif l' == l_j and pt_j == pt_now:
      c' = max(c, c_j) + 1
  else:
      c' = 0
  pt' = max(pt_now, pt_j)
  return (l', pt', c')
```

### HLC Properties

1. **Monotonicity**: `HLC` never decreases on any single process
2. **Causality**: if `a → b` (happened-before), then `HLC(a) < HLC(b)`
3. **Physical closeness**: `|l - pt| ≤ ε` (the logical clock never drifts far from physical time)
4. **O(1) size**: single `(l, pt, c)` triple, no vector needed

> **Interview Angle**: "Why does CockroachDB use HLCs instead of TrueTime?" TrueTime requires GPS/atomic clocks in every datacenter and tight clock synchronization infrastructure, which is a significant hardware investment. HLCs achieve similar ordering guarantees using only software and standard NTP-synchronized clocks. The tradeoff: HLCs can't bound clock uncertainty the way TrueTime can, so CockroachDB uses HLCs with an additional uncertainty wait for serializability in some cases.

## TrueTime & Spanner

**TrueTime** (Corbett et al., 2012) is Google Spanner's clock API that provides **externally consistent** timestamps by combining GPS and atomic clocks with a bounded uncertainty interval.

### TrueTime API

```cpp
TT.now() → TTinterval [earliest, latest]
// earliest and latest are absolute UTC timestamps
// TTinterval bounds the true time: true_time ∈ [earliest, latest]
// Uncertainty: latest - earliest ≈ 1-7ms typical, up to ~10ms worst case
```

### How Spanner Achieves External Consistency

```
Transaction T1 starts at TT.now() = [100, 104]
Transaction T1 commits at TT.now() = [105, 108]
  → T1 gets commit timestamp = 108 (latest possible)
  → T1 waits until true time > 108 (uncertainty wait)

Transaction T2 starts at TT.now() = [109, 113]
  → T2's snapshot reads see all committed transactions with ts < 109
  → T1's commit ts = 108 < 109 → T2 sees T1's writes
  → External consistency guaranteed!
```

The key insight: by choosing the commit timestamp as the **latest** bound of `TT.now()` and then **waiting** until physical time advances past that value, Spanner ensures that any subsequent transaction's snapshot will be strictly after the commit timestamp.

### Clock Synchronization Infrastructure

- **GPS receivers** per datacenter (with backup antennas for redundancy)
- **Atomic clocks** (cesium or rubidium) as fallback when GPS is unavailable
- **TrueTime daemons** on each machine poll GPS/atomic clocks and maintain a time synchronization protocol
- **Guaranteed uncertainty**: `ε` is typically 1-7ms and is exposed to applications
- If both GPS and atomic clocks fail, machines shut down (Spanner refuses to serve inconsistent data)

## Consistency Models: Deep Comparison

### Linearizability

The strongest consistency model. Every operation appears to take effect **atomically** at some single point in real time between its invocation and response. Requires a total order on all operations consistent with real-time ordering.

### Sequential Consistency

All processes see the same order of operations, but that order doesn't need to be consistent with real time. Operations from different processes can be reordered as long as each process sees its own operations in program order.

### Causal Consistency

Operations that are causally related are seen by all processes in the same order. Concurrent (non-causally-related) operations may be seen in different orders. This is the strongest consistency achievable without coordination in an asynchronous network.

### Session Consistency

A weaker variant of causal consistency scoped to a single client session. Read-your-writes, monotonic reads, and writes-follow-reads are guaranteed within a session, but not across sessions.

### Eventual Consistency

If no new writes are made, all replicas will eventually converge to the same state. No ordering guarantees during concurrent writes.

### Consistency Model Comparison

| Model | Total Order | Real-Time Order | Causal Order | Convergence | Coordination Required |
|--------|-------------|-----------------|--------------|-------------|----------------------|
| Linearizability | Yes | Yes | Yes | Immediate | Yes (every op) |
| Sequential | Yes | No | Yes | Immediate | Yes (global ordering) |
| Causal | Partial | No | Yes | Yes (causal) | Yes (per dependency) |
| Session | No | No | Per-session | Per-session | No (client-side) |
| Eventual | No | No | No | Eventually | No |
| Monotonic reads | No | No | No | Yes (reads) | No |

### Convergence

**Convergence** is the property that replicas eventually reach the same state. Convergence mechanisms include:

1. **Last-writer-wins (LWW)**: use timestamps (logical or physical) to pick the winner
2. **CRDT merge**: mathematically defined merge functions guarantee convergence
3. **Read repair**: on reads, compare replicas and push the latest to lagging ones
4. **Anti-entropy**: periodic background synchronization (Merkle trees, digest comparison)
5. **Hinted handoff**: when a node recovers, other nodes send it missed writes

> **Interview Angle**: "Compare linearizability and serializability." Linearizability is a recency guarantee: every operation appears to take effect atomically at a point in real time. Serializability is a transaction isolation guarantee: transactions appear to execute in some serial order. They are orthogonal: you can have serializable but not linearizable (if transaction commit order doesn't match real time) and linearizable but not serializable (if individual operations are linearizable but transactions aren't isolated). Spanner provides both by using TrueTime to assign real-time-based commit timestamps.
