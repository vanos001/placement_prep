# Advanced Concurrency Control

Beyond basic 2PL and MVCC (covered in [../transactions/mvcc.md](../transactions/mvcc.md) and [../transactions/isolation-levels.md](../transactions/isolation-levels.md)), this chapter covers serializable snapshot isolation (SSI), deterministic databases, distributed concurrency protocols, and real-world transaction systems like Spanner and CockroachDB.

## MVCC Internals Deep Dive

### Multi-Version Storage

In an MVCC system, each row version carries metadata: a creation timestamp (xmin) and a deletion timestamp (xmax). A transaction with timestamp T can see a version if `xmin ≤ T < xmax` and the creating transaction committed.

```
Row versions in PostgreSQL (heap tuple header):
┌──────────┬──────────┬──────────┬─────────┬──────────────┐
│  xmin    │  xmax    │  cid     │  ctid   │  data...     │
│ (create) │ (delete) │ (command)│ (next   │              │
│          │          │          │  tuple) │              │
└──────────┴──────────┴──────────┴─────────┴──────────────┘

Visibility check for TXN with snapshot (xmin, xmax, xid_array):
  if tuple.xmin == xid_array:      # created by in-progress TXN → invisible
    invisible
  if tuple.xmin < snapshot_xmin:   # created before our snapshot
    if committed(tuple.xmin): visible
  if tuple.xmax == 0:              # not deleted → visible
    visible
```

### Garbage Collection of Old Versions

MVCC accumulates old tuple versions that are no longer visible to any active transaction. GC (vacuum in PostgreSQL, compaction in others) reclaims this space. The challenge: **identifying which versions are safe to remove** requires knowing the oldest active snapshot.

- **PostgreSQL**: `autovacuum` daemon tracks `xmin_horizon` (oldest transaction still running). Only versions older than this horizon are reclaimable. Long-running transactions block vacuum, causing table bloat.
- **CockroachDB**: GC is triggered by the **GC TTL** (default 25 hours). The range lease holder identifies the oldest timestamp at which all replicas have applied the GC watermark.

## Timestamp Ordering (T/O)

### Basic T/O

In timestamp ordering, each transaction receives a timestamp at start. Operations are validated at commit time: for each write on key k by TXN T, check that no later transaction wrote k before T's read. Equivalent to checking the **precedence (conflict) graph** has no cycles.

### Multi-Version T/O (MVTO)

Combine MVCC with timestamp ordering: reads go to the latest version with `timestamp ≤ reader's timestamp`. Writes create a new version tagged with the writer's timestamp. No locks needed — purely optimistic.

## Optimistic Concurrency Control (OCC) / PCC

### OCC Phases (Kung & Robinson, 1981)

1. **Read phase**: Transaction reads and writes to private workspace. Each read records the version/timestamp read from.
2. **Validation phase**: At commit, check that all read values haven't changed. If any have, abort and retry.
3. **Write phase**: If validation passes, apply writes atomically.

### Predicate Concurrency Control (PCC)

PCC (Srinivasan & Carey, 1992) extends OCC to handle **predicate reads** (range scans). Instead of recording individual row reads, PCC records the **predicate** (e.g., `salary > 100000`). At validation, re-evaluate the predicate to check for **phantom** rows that would have matched.

## Serializable Snapshot Isolation (SSI)

### The Problem with Snapshot Isolation

Snapshot Isolation (SI) prevents read-write conflicts but allows **write skew** — a subtle anomaly:

```
TXN A:                             TXN B:
  READ doctors WHERE on_call=true     READ doctors WHERE on_call=true
  -- sees 3 doctors                  -- sees 3 doctors
                                    UPDATE doctors SET on_call=false
                                    WHERE id=2
                                    COMMIT
  UPDATE doctors SET on_call=false  
  WHERE id=1                        
  COMMIT

Result: 1 doctor on call (both A and B assumed the other would remain)
This is a write skew anomaly — not serializable!
```

### How SSI Prevents Anomalies

SSI (Porter & Moon, 2014; implemented in **PostgreSQL 9.1+**) augments SI with **danger structure tracking** to detect serialization conflicts:

1. **rw-conflict tracking**: If TXN A reads a row and TXN B later writes that row (B commits first), this is an **rw-dependency** (A depends on B). SSI records this as A → B.
2. **Dangerous structures**: If TXN A also has a **ww-dependency** or **wr-dependency** back to B (A writes something B read), this forms a cycle: A → B → A, which is a serialization failure. SSI aborts one of them.
3. **Summary rw-conflicts**: For scans, SSI tracks **key-range locks** (actually predicate locks via `SIReadLock` in PostgreSQL) to detect phantoms. These are **shared, non-blocking** — they only create rw-conflict edges.

```
TXN A reads R → records SIReadLock on R
TXN B writes R, commits → rw-conflict: A → B
TXN A writes S → check if B read S (via SIReadLock on S)
  If yes: cycle A→B→A detected → abort TXN A
```

### Performance Characteristics

- **Overhead**: SSI adds ~5-15% overhead over plain SI due to rw-conflict tracking and predicate lock management. Much cheaper than full 2PL for read-heavy workloads.
- **Abort rate**: For typical OLTP workloads with low contention, abort rates are < 1%. For hot-row workloads, aborts increase but remain manageable.
- **PostgreSQL**: `SET TRANSACTION ISOLATION LEVEL SERIALIZABLE` enables SSI. It is the **recommended** isolation level for correctness-critical workloads.

> **Interview Angle**: "How does PostgreSQL implement serializable snapshot isolation?" — Explain the write skew anomaly in plain SI, then describe rw-conflict tracking, predicate/SIRead locks, dangerous structure detection, and the abort mechanism.

## Predicate Locking & Phantom Prevention

### Lock-Based Approaches

| Approach | Granularity | Phantom Prevention | Overhead |
----------|-------------|-------------------|----------|
| **Key-range locks** (SQL Server) | Range + individual keys | Yes | Moderate |
| **Next-key locking** (InnoDB) | Gap before + key itself | Yes | Moderate |
| **Predicate locks** (SSI) | Exact predicate | Yes | Low (non-blocking) |
| **Index-based** (PostgreSQL page locks) | Page-level | Partial (page-level granularity) | Low |

**Next-key locking** (MySQL InnoDB): Locks the gap *before* a key and the key itself. This prevents phantoms by blocking inserts into the gap. For `WHERE age > 30`, InnoDB locks the gap from 30 to the next existing key.

## Lock-Free Transactions

Lock-free transactional data structures use **atomic operations** (CAS, FAA) instead of locks. The Bw-tree (covered in [index-advanced.md](index-advanced.md)) is the canonical example: delta records are installed via CAS on the mapping table. Transactions read a consistent snapshot by following delta chains.

**Challenges**: Implementing multi-key serializable transactions lock-free is extremely difficult. Most systems use locks for correctness but optimize for low contention (e.g., single-record latches with optimistic paths).

## Deadlock Prevention: Wound-Wait vs. Wait-Die

For systems using locking, deadlocks must be handled. Two classic *prevention* (not detection) strategies:

| Strategy | Rule | Older TXN | Younger TXN |
----------|------|-----------|-------------|
| **Wound-Wait** | If older TXN wants lock held by younger, younger is *wounded* (aborted). If younger wants lock held by older, younger *waits*. | Preempts younger | Waits for older |
| **Wait-Die** | If older TXN wants lock held by younger, older *waits*. If younger wants lock held by older, younger *dies* (aborts). | Waits for younger | Aborts itself |

**Wound-wait** is generally preferred because it aborts *fewer* transactions: only younger ones that hold contested resources. **Wait-die** is simpler to implement because only the requesting TXN checks timestamps. Both guarantee no deadlock because the wait-for graph is always a DAG (edges point from younger to older).

## Deterministic Databases

### The Calvin Approach

Calvin (Thomson et al., SOSP 2012) is a **deterministic** database system that eliminates concurrency control entirely by ensuring all replicas execute transactions in the **same order**.

```
Traditional DB:                    Calvin:
  TXN arrives                       TXN arrives
  Acquire locks                     Assign sequence number
  Execute (nondeterministic)        Log to sequencer
  Commit/abort                     All replicas replay in sequence order
                                    (no locks, no aborts for conflicts)
```

**Architecture**:
1. **Sequencer layer**: Assigns a global sequence number to each transaction. Transactions are batched into **epochs**.
2. **Replication**: All replicas receive the same epoch-ordered transaction batch.
3. **Deterministic execution**: Each replica executes transactions in sequence order. Since execution is deterministic (same input, same order → same output), all replicas produce identical results without coordination.
4. **No concurrency control needed**: No locks, no MVCC, no deadlock detection. Conflicts are impossible because execution is serialized.

**Handling read-write dependencies**: Calvin uses **read pre-processing** to determine which keys each transaction reads. If a transaction in epoch E reads a key written by a transaction in the same epoch, Calvin defers the reader to the next epoch. This ensures deterministic read results.

### Pros and Cons of Determinism

| Aspect | Advantage | Disadvantage |
--------|-----------|-------------|
| **Replication** | Trivial — same order = same result | Sequencer is a bottleneck |
| **Latency** | No lock wait, no abort-retry loops | Read pre-processing adds latency |
| **Throughput** | High under contention | Sequencer limits horizontal scaling |
| **Programming model** | Simpler (no retry logic) | Deterministic-only operations (no `NOW()`, random) |

## Distributed Concurrency

### Distributed Serializability

Achieving serializability across multiple nodes requires coordinating locks, timestamps, or determinism across machines. The main approaches:

| Approach | Mechanism | Latency | Throughput | Used In |
----------|-----------|---------|------------|----------|
| **2PL + distributed deadlock** | Lock managers per partition, global deadlock detection | High (lock waits) | Low under contention | Traditional distributed DBs |
| **Distributed MVCC + SSI** | Per-node MVCC, distributed rw-conflict tracking | Medium | Medium | CockroachDB |
| **Deterministic (Calvin)** | Global sequencer, deterministic replay | Medium (epoch latency) | High | FaunaDB (inspired) |
| **TrueTime-based** | Clock-assisted timestamps, no WW conflicts | Low-Medium | High | Spanner |

### Distributed MVCC

In distributed MVCC, each node maintains its own versioned storage. A global timestamp oracle assigns timestamps. The key challenge is **cross-partition transaction atomicity**: a transaction touching partitions A and B must appear atomic across both.

### Distributed Deadlock Detection

With distributed locking, deadlocks can span nodes. Detection uses a **global wait-for graph (WFG)**:

1. Each node maintains a **local WFG** for its partitions.
2. Periodically, nodes exchange WFG fragments to build a **global WFG**.
3. A cycle in the global WFG indicates a distributed deadlock.
4. The **youngest** transaction in the cycle is aborted (to match wound-wait semantics).

**Challenges**: Global WFG construction has overhead proportional to the number of lock waits. In practice, distributed systems prefer **prevention** (wound-wait with timestamps) over detection.

### Distributed Commit: Beyond 2PC

See [../transactions/two-phase-commit.md](../transactions/two-phase-commit.md) for 2PC basics. Advanced systems optimize:

- **Presumed abort**: If coordinator crashes, assume abort. No logging needed at participants until they vote yes.
- **Presumed commit**: If coordinator crashes after sending commit, participants can commit independently. Reduces coordinator log writes.
- **One-phase commit (1PC)**: If only one participant, skip the prepare phase. CockroachDB detects single-partition TXNs and uses 1PC.

### Transaction Timestamp Allocation

In distributed systems, timestamps must be **globally unique** and **monotonically increasing**. Approaches:

| Method | Mechanism | Skew | Bottleneck |
--------|-----------|------|------------|
| **Centralized TS oracle** | Single node hands out timestamps | Minimal (~1us) | Yes (single point) |
| **TrueTime** (Spanner) | GPS + atomic clock, uncertainty interval | ±few ms | No (per-node) |
| **Hybrid Logical Clock (HLC)** | Lamport clock + physical clock | Bounded | No |
| **HLC + batching** (CockroachDB) | Per-node HLC, batched commit | ~few ms | No |

## Spanner Transactions

### TrueTime

Google Spanner (Corbett et al., OSDI 2012) uses **TrueTime**: a clock API that returns an interval `[earliest, latest]` instead of a single timestamp. TrueTime is synchronized using GPS receivers and atomic clocks in each datacenter, with typical uncertainty of **±1-7ms**.

```python
# TrueTime API
tt.now() → (earliest, latest)  # e.g., (1000.005, 1000.012)
tt.after(t)  # block until tt.now().earliest > t
tt.before(t) # block until tt.now().latest < t
```

### Spanner's External Consistency

Spanner guarantees **external consistency** (linearizability across transactions): if TXN A commits before TXN B starts, then A's commit timestamp < B's commit timestamp. This is achieved by:

1. **Commit wait**: After preparing all participants, the coordinator assigns `commit_ts = tt.now().latest` and then **waits** for `tt.after(commit_ts)` before responding to the client. This ensures no other transaction can get a lower timestamp that overlaps.
2. **Read operations**: Read at `timestamp = tt.now().latest`. Wait for `tt.after(timestamp)` to ensure all committed TXNs with earlier timestamps are visible.

### Spanner Transaction Types

| Type | Mechanism | Locking | Latency |
------|-----------|---------|---------|
| **Read-only** | Timestamp read from replicas, no locking | None | ~10ms (wait for TrueTime) |
| **Snapshot read** | Read at specific past timestamp | None | Near-instant (past timestamp) |
| **Read-write** | 2PC + Paxos + TrueTime commit wait | Pessimistic (2PL) | ~50-100ms |
| **Stand-alone** | Single-group read-write | Pessimistic | ~10-20ms |

## CockroachDB Transactions

CockroachDB provides **serializable isolation** (via SSI-like mechanism) on top of a distributed key-value store using **Raft** consensus per range.

### Architecture

```
SQL Layer (CockroachDB)
    ↓ (distributed SQL, 2PC for multi-range TXNs)
DistSQL Execution Engine
    ↓
KV Layer (RocksDB per node, Raft per range)
    ↓
Storage (RocksDB SSTables)
```

### Transaction Protocol

1. **Begin**: Client starts transaction, gets a timestamp from the **HLC clock** (hybrid logical clock).
2. **Read**: Read from any Raft replica at the transaction's timestamp. MVCC ensures consistent snapshot.
3. **Write**: Buffer writes in client memory (intents). On `FLUSH`, write **intent records** (uncommitted versions) to the KV store.
4. **Commit**: 
   - **Single-range TXN**: 1PC — write the commit timestamp directly (no coordinator needed).
   - **Multi-range TXN**: 2PC — coordinator writes commit intent, participants write intent resolutions.
   - **Contention resolution**: Uses **push** mechanism (like wound-wait): if TXN A's intent conflicts with TXN B's, and A has a higher priority (lower timestamp), B is pushed (aborted).

### SSI in CockroachDB

CockroachDB's serializable isolation uses a **distributed SSI** mechanism:
- **Read refresh**: If a transaction's reads might be stale (detected via version mismatch), the transaction is automatically restarted at a higher timestamp.
- **Write-write conflicts**: Resolved via **first-writer-wins**: the transaction that wrote first wins; the later writer is aborted.
- **Push mechanism**: Replaces traditional deadlock detection. Conflicting transactions receive a **push** signal and must abort or retry.

> **Interview Angle**: "Compare Spanner's and CockroachDB's approaches to distributed serializability." — Spanner uses TrueTime + 2PC + pessimistic locking. CockroachDB uses HLC + MVCC + distributed SSI + push-based contention resolution. Spanner has lower latency (hardware-assisted clocks) but requires GPS/atomic clocks. CockroachDB is deployable on commodity hardware.

## References

- Porter, G. & Moon, S. "Designing for Snapshot Isolation." Chapter in Architecture of a Database System, 2014.
- Thomson, A. et al. "Calvin: Fast Distributed Transactions for Partitioned Database Systems." SOSP, 2012.
- Corbett, J. et al. "Spanner: Google's Globally Distributed Database." OSDI, 2012.
- Kung, H.T. & Robinson, J.T. "Optimistic Concurrency Control." ACM TOCS, 1981.