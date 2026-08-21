# MVCC (Multi-Version Concurrency Control) Internals

Multi-Version Concurrency Control (MVCC) is the mechanism used by virtually every modern database to provide concurrent access without readers blocking writers or writers blocking readers. Instead of locking a row when a transaction reads it, MVCC maintains **multiple versions** of every row, and each transaction sees only the versions consistent with its snapshot. PostgreSQL, InnoDB, Oracle, SQL Server (under ALLOW_SNAPSHOT_ISOLATION), Spanner, and CockroachDB all use MVCC under the hood — but with very different on-disk representations.

This page covers the version-chain structures, snapshot/visibility logic, garbage collection, and the subtle interaction between secondary indexes and version chains that causes real-world performance bugs.

## The Core Idea

A single-version database has only one current value for each row. To prevent dirty reads, every reader must take a shared lock on the row, and every writer takes an exclusive lock. Readers and writers block each other. This is **2PL (Two-Phase Locking)**.

An MVCC database instead keeps a **version chain** for each row:

```
Row X: V1 (committed at t=10) ← older
       V2 (committed at t=20)
       V3 (committed at t=30, latest)

A transaction that started at t=15 reads V2 (the latest version committed before its snapshot time).
A transaction that started at t=5 reads V1.
A transaction that started at t=25 reads V3 (well, V3 is committed at 30, but t=25 sees V2 because V2 is committed at 20 ≤ 25).
```

Readers walk the chain to find the right version. Writers append a new version (or update an in-place marker) — they don't overwrite, so a concurrent reader can still see the older version. The bet is that "version chain walk" is cheaper than "lock wait", and for read-heavy OLTP workloads it almost always is.

## Version Chain Structures

There are three main on-disk representations of the version chain. Each database picks one based on its history and storage model.

### 1. Heap-Tuple + xmin/xmax (PostgreSQL)

In PostgreSQL, every row (called a "tuple") lives in a heap page. Each tuple has a header containing:

```
HeapTupleHeader {
    HeapTupleFields t_heap {
        TransactionId t_xmin;    // XID that inserted this tuple
        TransactionId t_xmax;    // XID that deleted/updated this tuple (InvalidXid if alive)
        CommandId    t_field3;   // CID for in-transaction command ordering
    }
    ItemPointerData t_ctid;     // points to the next version, or self if latest
    uint16  t_infomask;          // visibility flags: COMMITTED, INVALID, etc.
    ...
    [actual row data]
}
```

On `UPDATE`, PostgreSQL does **not** modify the tuple in place. Instead it:

1. Marks the old tuple's `t_xmax` = current transaction XID, sets a "updated" bit, and points `t_ctid` to the new tuple.
2. Inserts a brand-new tuple at the end of the page (or next page) with `t_xmin` = current XID, `t_xmax` = InvalidXid, `t_ctid` = self.

The chain looks like:

```
tuple v1: xmin=100, xmax=200, ctid→v2    (inserted by txn 100, marked for update by txn 200)
tuple v2: xmin=200, xmax=InvalidXid, ctid→v2  (inserted by txn 200, currently latest)
```

A reader looking for the "current" version of row X reads the latest tuple and checks whether `xmax = InvalidXid` (i.e., not deleted) and `xmin` was committed before the reader's snapshot. If `xmax` is set, the reader walks `ctid` forward to find a version with `xmin ≤ snapshot` and (`xmax > snapshot` or `xmax = InvalidXid`).

A `DELETE` just sets `t_xmax` and a "deleted" bit. No new tuple is created.

### 2. Undo Log (InnoDB / Oracle)

InnoDB stores only the **latest** version of each row in the clustered index (the table itself). When a row is updated, the old version is moved to an **undo log segment** that lives in the system tablespace (or in a separate undo tablespace). The undo log entry contains:

```
UndoLogEntry {
    TrxID       // the transaction that did the original modification
    Type        // INSERT / UPDATE / DELETE
    OldTrxID    // prior version's TrxID
    OldValues   // before-image of the columns changed
    RollPtr     // points to the prior undo entry, forming a singly-linked list
}
```

The current row in the clustered index contains a `roll_pointer` field (7-byte) that links to the most recent undo entry. A reader needing an older version follows `roll_pointer` back through undo entries, applying each "before-image" until reaching a version with `TrxID < snapshot_low_limit` (i.e., committed before the snapshot).

```
[Clustered index, current row X]
    TrxID=200, roll_ptr → [Undo entry 2]
                          Undo entry 2: TrxID=200, old=V2, ptr→[Undo 1]
                          Undo entry 1:  TrxID=100, old=V1, ptr=null

A txn with snapshot low_limit=150 walks:
  - Current row X (TrxID 200 > 150) → not visible
  - Undo entry 2 (TrxID 200 > 150) → apply old=V2 → now we have V2's state
  - Undo entry 1 (TrxID 100 ≤ 150) → visible!  Apply old=V1 to see prior state.
```

This is more space-efficient than PostgreSQL's heap (only changed columns are kept in undo, not the full tuple) but reconstructing an old version requires applying diffs in sequence, which is O(chain-length) per read.

### 3. Delta Records in Append-Only Storage (Datomic, Eventuate)

Some systems (Datomic, Crux, some blockchains) keep every version explicitly as an immutable fact. The "version chain" is just the time-ordered sequence of write events, and a reader computes "current state at time t" by folding events up to t. Simpler to reason about but read cost is high without materialization. Not used in mainstream OLTP.

## The Visibility Check

Given a tuple (or undo entry) and a transaction snapshot, the database must answer: **"Is this version visible to me?"** This is a per-tuple decision made on every read.

### PostgreSQL: SnapshotData

When a transaction begins (at REPEATABLE READ or SERIALIZABLE), it builds a `SnapshotData` struct:

```c
typedef struct SnapshotData {
    TransactionId xmin;          // minimum active XID at snapshot time
    TransactionId xmax;          // first XID after snapshot time
    TransactionId *xip;          // array of XIDs in-progress at snapshot time
    uint32      xcnt;            // count of xip
    ...
} SnapshotData;
```

Visibility of tuple `t`:

```
1. If t.xmin is "committed before snapshot" AND t.xmin < xmax AND t.xmin not in xip:
     → xmin is "visible" (the tuple's existence is committed and visible).

2. If t.xmax is InvalidXid OR t.xmax not committed before snapshot:
     → tuple has not been deleted/updated visibly.
     → tuple is VISIBLE.

3. Else, tuple is not visible (or its "next" version via ctid must be consulted).
```

There are also sub-transaction CIDs (command IDs) for in-transaction visibility — a transaction must see its own writes from previous commands but not future ones. The full decision tree is in `HeapTupleSatisfiesMVCC` in `src/backend/utils/time/heapam_visibility.c`.

At READ COMMITTED isolation, PostgreSQL takes a *new* snapshot at the start of every statement (not every transaction). This is why two statements in the same READ COMMITTED transaction see different data.

### InnoDB: ReadView

InnoDB maintains a global `trx_sys` with a list of active transactions. When a transaction starts at REPEATABLE READ, it creates a `ReadView`:

```c
struct ReadView {
    trx_id_t  m_low_limit_id;   // highest TrxID assigned at ReadView creation
    trx_id_t  m_up_limit_id;    // lowest TrxID active at ReadView creation
    trx_ids_t m_ids;            // sorted vector of active TrxIDs
    trx_id_t  m_creator_trx_id; // TrxID of the ReadView owner
};
```

Visibility of a row version with `TrxID = t`:

```
- If t < m_up_limit_id: visible (the writer committed before ReadView).
- If t == m_creator_trx_id: visible (my own write).
- If t ≥ m_low_limit_id: NOT visible (writer started after ReadView).
- Else (binary search m_ids):
    - t not in m_ids: visible (writer committed before ReadView).
    - t in m_ids: NOT visible (writer was still active).
```

The roll_pointer chain is walked until a visible version is found.

## Garbage Collection: VACUUM and Purge

Old versions must eventually be removed, or the database grows without bound. Each database has a garbage-collection process.

### PostgreSQL VACUUM

PostgreSQL's VACUUM is invoked by the autovacuum daemon or manually. It:

1. Scans the heap, identifies "dead tuples" (tuples with `t_xmax` set, committed, and not visible to any active transaction).
2. Removes them from the page (compacts the page) — this is "regular" VACUUM.
3. Optionally, returns freed pages to the OS — "VACUUM FULL" (which requires an exclusive lock and rewrites the table).
4. Updates the visibility map (a per-page bitmap that says "all tuples on this page are visible to all snapshots" — a major optimization for index-only scans).
5. Updates the free space map.

Key tuning:

```
autovacuum_vacuum_scale_factor = 0.2   # vacuum when 20% of table changed
autovacuum_vacuum_threshold = 50       # ...and at least 50 rows
autovacuum_naptime = 1min              # check interval
autovacuum_vacuum_cost_limit = 200     # IO credits per cycle
autovacuum_vacuum_cost_delay = 2ms     # throttle to avoid I/O storm
```

Without VACUUM, "bloat" grows — tables with 10% live data and 90% dead versions. Common PostgreSQL bug: a long-running transaction holds back the vacuum horizon; in extreme cases the database grows until disk fills and the long-running txn is killed (a "snapshot too old" or XID wraparound failure).

PostgreSQL 9.6+ added **replication-slot conflict resolution** that lets standbies cancel queries that would otherwise hold back vacuum on the primary.

### InnoDB Purge

InnoDB has a dedicated **purge coordinator thread** + worker threads that scan the undo log and remove undo entries (and the corresponding row data) for transactions that no longer have any active ReadView referencing them. The threshold is `innodb_max_purge_lag` (in microseconds of lag) — if purge falls behind, INSERTs/UPDATEs are throttled.

The purge process is implicit — no `VACUUM` command needed. But if purge falls behind (e.g., a long-running report query holds a ReadView), the undo log segment grows, and on the next SELECT, every read must walk a longer version chain → read latency spikes.

## The Index Pointer Problem

This is the most subtle MVCC issue, and it affects every database differently. The problem: secondary indexes point to rows. When a row is updated, where does the index point?

### PostgreSQL: Indexes Point to TID (Heap Tuple ID)

PostgreSQL secondary indexes contain `(key, TID)` pairs where TID is `(page, offset)` in the heap. On UPDATE, PostgreSQL always creates a new tuple at a new TID (unless HOT — see below).

To find the visible version of a row by index:

1. Look up `(key, TID)` in the index.
2. Fetch the tuple at TID.
3. Check visibility (xmin/xmax).
4. If not visible, follow `t_ctid` chain to the latest version, repeat.

If the row is updated often, the chain can be long, and the index still points to the *original* TID — readers must walk forward. This is the **HOT (Heap-Only-Tuple) update** optimization target.

**HOT update**: if the update (a) does not change any indexed column, and (b) the new tuple fits on the same page, PostgreSQL doesn't update indexes — it just chains the tuple. Reads use the original TID, follow the chain to the latest visible tuple. This avoids N index writes per UPDATE when N indexes exist on the table. Crucial for update-heavy tables. Documentation: <https://www.postgresql.org/docs/current/storage-hot-chain.html>.

If the update changes an indexed column, every index on that column must be updated — this is what makes secondary indexes on volatile columns expensive.

### InnoDB: Indexes Point to Primary Key

InnoDB secondary indexes contain `(key, primary_key_value)`. To find a row:

1. Look up `(key, PK)` in the secondary index.
2. Look up the PK in the clustered index (B-tree of the table itself).
3. The clustered index leaf contains the latest version + roll_pointer.
4. Walk the undo chain to find the visible version.

This is **double lookup** (secondary index → PK lookup → row), but the payoff is: secondary indexes never need to be updated when an UPDATE changes a non-indexed column. Only the clustered index is updated. So UPDATE-heavy tables in InnoDB scale better than PostgreSQL's, *until* the row is large enough that the clustered index is bigger than the equivalent heap — at which point PostgreSQL's HOT wins.

### The Generic Tradeoff

| Approach | Pros | Cons |
|---|---|---|
| Heap + indexes by TID (PostgreSQL) | Single-fetch row, simple | Index-only UPDATE impossible; N index writes if indexed column changes |
| Clustered + indexes by PK (InnoDB) | UPDATE of non-indexed column touches one B-tree | Every secondary lookup is two B-tree traversals; PK is variable width if string |
| Append-only + index rebuilds | No UPDATE cost at all | Massive space; expensive GC; rarely used in OLTP |

Production bug pattern: in PostgreSQL, a table with 5 secondary indexes updated on a non-indexed column appears to be cheap (HOT) — but the index still must point to the latest version somehow, so the chain grows. Eventually VACUUM removes dead versions, but until then, every read walks the chain. The fix: ensure `fillfactor` is < 100 (typically 80-90 for update-heavy tables) so HOT has space on the same page.

## MVCC vs 2PL

| Dimension | Single-Version 2PL | MVCC |
|---|---|---|
| Reader blocking writer? | Yes (S lock blocks X lock) | No |
| Writer blocking reader? | Yes (X lock blocks S lock) | No |
| Phantom reads | Preventable (range locks) | Preventable (snapshot) |
| Write skew | Preventable (range locks) | NOT at SI; needs SSI |
| Storage | 1 row per logical row | Multiple versions per row; needs GC |
| Long transactions | Fine (just hold locks longer) | Catastrophic — old versions cannot be GC'd |
| Deadlocks | Yes | No (no locks) |
| Under high contention | Limited by lock waits | Limited by abort rate (if OCC-flavored) |
| Implementation complexity | Moderate | High (visibility checks, GC, snapshots) |

Most modern OLTP databases are **MVCC + 2PL hybrid**: MVCC for readers (snapshot), 2PL for writers (row locks to enforce first-committer-wins). The row lock in PostgreSQL is a "tuple lock" (`LOCKTAG_TUPLE`) on the tuple's TID; in InnoDB it's a "next-key lock" combining the record lock and the gap before it. So readers don't block writers, but writers do block writers on the same row — the bet is that read-write contention dominates write-write contention in OLTP.

## Production Pitfalls

1. **Long-running transactions kill GC.** A 1-hour analytics query prevents VACUUM from reclaiming anything updated after its start. Set `statement_timeout` aggressively; route analytics to a replica with `hot_standby_feedback = off`.
2. **Subtransaction XID explosion.** PostgreSQL allocates a separate XID for every savepoint. Deeply nested transactions can churn XIDs. The XID is 32-bit; wraparound at 2^32 transactions forces emergency autovacuum and lockups. Monitor `pg_stat_activity` XID consumption.
3. **Index bloat from non-HOT updates.** Updates that change indexed columns must update every affected index, causing index bloat. Schedule periodic `REINDEX CONCURRENTLY`.
4. **Transaction ID wraparound.** If autovacuum cannot keep up with XID consumption, PostgreSQL reaches the 2^31 limit and stops accepting writes ("database is not accepting commands to avoid wraparound"). Emergency VACUUM is then required. Monitor `age(datfrozenxid)`.
5. **InnoDB undo log growth.** An aggressive long-running reader on a high-write table causes the undo segment to expand. Configure `innodb_undo_log_truncate=ON` and `innodb_max_undo_log_size`.
6. **Wrong isolation level.** READ COMMITTED gives statement-level snapshots; REPEATABLE READ gives transaction-level. Mixing them unintentionally causes "my transaction saw inconsistent data" bugs.
7. **Snapshot too old.** Oracle has a `ORA-01555 snapshot too old` error when an undo segment has been overwritten before a long-running reader needs it. Monitor undo tablespace size and `UNDO_RETENTION`.

## References

- PostgreSQL, "[MVCC: Overview of PostgreSQL internals](https://www.postgresql.org/docs/current/mvcc.html)" — official docs.
- PostgreSQL source, `src/backend/utils/time/heapam_visibility.c` — actual visibility logic, with extensive comments.
- H. Berenson et al., "[A Critique of ANSI SQL Isolation Levels](https://www.cs.umb.edu/~poneil/iso.pdf)", *SIGMOD 1995* — the foundational critique that defined snapshot isolation and write skew.
- A. Adya, B. Liskov, P. O'Neil, "[Generalized Isolation Level Definitions](https://www.cs.umb.edu/~poneil/iso.pdf)", *ICDE 2000* — formal definitions extending Berenson.
- J. Gray, R. Lorie, G. Putzolu, P. Traiger, "[Granularity of Locks and Degrees of Consistency in Shared Data Bases](https://drops.dagstuhl.de/opus/volltexte/2006/6284/)" (1975; published widely as *Dangerous Liaison* — the source of "degrees of consistency").
- P. Helland, "[Dangerous Liason: Locks and Deadlocks in Distributed Systems](https://arxiv.org/abs/cs/0512020)", 2005 — analysis of MVCC vs 2PL.
- InnoDB, "[InnoDB Architecture: Clustered and Secondary Indexes](https://dev.mysql.com/doc/refman/8.0/en/innodb-index-types.html)".
- InnoDB, "[InnoDB Multi-Versioning](https://dev.mysql.com/doc/refman/8.0/en/innodb-multi-versioning.html)" — official ReadView / undo log docs.
- M. Stonebraker, "[The Design of POSTGRES](https://dl.acm.org/doi/10.1145/16856.16859)", *SIGMOD 1986* — original PostgreSQL design with MVCC baked in.
- M. J. Cahill, J. Doherty, R. Kummeth, D. Lomet, "[Serializable Snapshot Isolation in PostgreSQL](https://drkp.net/papers/ssi-vldb12.pdf)", *VLDB 2012* — describes the SSI extension atop MVCC.
- Alvaro Herrera, "[HOT (Heap-Only-Tuple) updates](https://www.postgresql.org/docs/current/storage-hot-chain.html)" — PostgreSQL documentation of HOT chains.
- A. Thomson et al., "[Calvin: Fast Distributed Transactions](https://cs.yale.edu/homes/thom/publications/calvin-sigmod12.pdf)", *SIGMOD 2012* — interesting alternative to MVCC for distributed transactions.
