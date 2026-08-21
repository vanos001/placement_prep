# Write-Ahead Log (WAL) Internals

The Write-Ahead Log (WAL) is the single mechanism that makes a database durable without flushing every modified page to disk on every commit. The deal is simple and absolute: **a log record describing a change must reach stable storage before the data page that change touches.** Once the log record is on disk, the change cannot be lost — even if the database crashes one microsecond later, recovery can replay the log and rebuild the page. Every serious storage engine (PostgreSQL, InnoDB, Oracle, SQL Server, RocksDB, SQLite WAL mode, LevelDB, FoundationDB) is built around this rule.

This page goes deep: log record formats, the redo/undo distinction, the ARIES recovery algorithm, sharp vs fuzzy checkpoints, group commit, and why shadow paging lost the war.

## The WAL Rule, Formally

Let `LSN(p)` be the Log Sequence Number of the most recent log record that modifies page `p`. The WAL invariant is:

> A page `p` may be written to disk only if `LSN(WAL) ≥ LSN(p)` at the moment of the write — i.e., the page's modifications have already been persisted to the log.

Equivalently: the buffer-pool page may be dirtier than its on-disk counterpart, but the on-disk log must always be ahead of the on-disk page.

A consequence: when the database flushes a 64-page "checkpoint" batch to data files, it must first `fsync()` the WAL up to the highest LSN among those pages, then flush the pages. Otherwise a crash mid-flush could leave on-disk pages newer than the log, and a subsequent redo would skip the modifications — silently corrupting the database.

## Log Record Format

A log record is a self-describing byte sequence. The classical ARIES record layout:

```
┌─────────────────────────────────────────────────────────────────┐
│ Header:                                                          │
│   LSN ............ 8 bytes, monotonic, byte-offset into log      │
│   prevLSN ........ 8 bytes, prior LSN for same txn (undo chain)  │
│   TxnID .......... 8 bytes, transaction identifier              │
│   Type ........... 2 bytes: UPDATE/COMMIT/ABORT/CLR/CHECKPOINT   │
│   PageID ......... 8 bytes, which buffer-pool page               │
│   Length ......... 4 bytes, total record length                   │
├─────────────────────────────────────────────────────────────────┤
│ Body (UPDATE):                                                   │
│   Offset in page ........ 2 bytes                                │
│   Before-image (undo) ... variable (often binary diff)          │
│   After-image  (redo) ... variable (often binary diff)            │
├─────────────────────────────────────────────────────────────────┤
│ Footer:                                                          │
│   Checksum ...... 4 bytes CRC32 / 8 bytes xxHash                 │
└─────────────────────────────────────────────────────────────────┘
```

Key fields:

- **LSN** — the global ordering. In PostgreSQL this is `(timeline, xlogid, xrecoff)`. In InnoDB it's a 64-bit counter into the redo log. In RocksDB it's a per-column-family sequence number.
- **prevLSN** — links all records of one transaction into a singly-linked list, used during undo.
- **Before-image** — what the bytes were *before* this update. Used to undo the change during rollback or recovery.
- **After-image** — what they are *after*. Used to redo the change during crash recovery.
- **CLR (Compensation Log Record)** — written during undo. A CLR contains only a redo image (the inverse of the original update) and points back to the LSN of the original. It is idempotent and never undone, so undo is recoverable from crashes.

Commit and Abort records typically contain no page image — they just mark the transaction's outcome. A `CHECKPOINT` record contains the list of active transactions and their last LSNs (a "dirty page table").

## Redo and Undo Recovery

After a crash, the recovery system performs three passes over the WAL:

```
   Analysis pass ──▶ Redo pass ──▶ Undo pass
       │                │             │
       │                │             └─ roll back non-committed
       │                └── replay all updates from minRecLSN
       └── rebuild dirty page table + active txn table
```

### Analysis

Scan forward from the last checkpoint record. Reconstruct:
- **Dirty Page Table (DPT)** — pages that were dirty at crash time, with their `recLSN` (first LSN that dirtied them).
- **Active Transaction Table (ATT)** — transactions that had not yet committed at crash time, with their `lastLSN`.

### Redo

Replay every UPDATE record whose LSN ≥ the page's `recLSN`. ARIES redoes *all* updates — committed and uncommitted — because the redo pass establishes the page state as of the crash. The redo operation is idempotent: replaying an UPDATE record on a page whose `pageLSN` already ≥ record LSN is a no-op (this is the "repeating-history" principle).

After redo, the on-disk page state matches what it was in memory at the moment of crash. Now we roll back.

### Undo

For every transaction in ATT that did not commit, traverse its LSN chain backwards from `lastLSN`. For each UPDATE record, write a CLR (Compensation Log Record) and apply the inverse update to the page. CLRs point to the *next* record to undo via their `undoNextLSN` field, so even if the undo pass crashes, restarting undo is safe — we resume from `undoNextLSN`.

Worked example:

```
Log:
  LSN 10  T1 UPDATE P1 before=A after=B  prevLSN=null
  LSN 20  T1 UPDATE P2 before=C after=D  prevLSN=10
  LSN 30  T2 UPDATE P3 before=E after=F  prevLSN=null
  LSN 40  T1 COMMIT                    prevLSN=20

Crash. ATT after analysis: {T2}. DPT: {P1(recLSN=10), P2(recLSN=20), P3(recLSN=30)}.

Redo: apply LSN 10, 20, 30, 40 in order. PageLSNs now 10, 20, 30 respectively.

Undo: T2 not committed. Start at lastLSN=30.
  Undo LSN 30: write CLR LSN 50 "undo of 30" redo=E. Apply E to P3.
  undoNextLSN from CLR = prevLSN of 30 = null. Done.

Final state: P1=B (committed), P2=D (committed), P3=E (rolled back).
```

## Checkpointing: Sharp vs Fuzzy

A checkpoint is a moment at which recovery can begin. The simpler form is the **sharp checkpoint**: quiesce all transactions, flush every dirty page to disk, then write a checkpoint record. Recovery starts from that record. Sharp checkpoints are used by older systems (early SQL Server "CHECKPOINT" with `WITH CHECKPOINT` quiescing) but they introduce unacceptable stalls — the database must pause writes for the entire flush.

**Fuzzy checkpointing** (ARIES) avoids the quiesce:

```
At checkpoint time:
  1. Take an *atomic snapshot* of the Dirty Page Table and Active Txn Table.
  2. Write a CHECKPOINT record containing those snapshots, plus
     the current LSN and the oldest recLSN among dirty pages (minRecLSN).
  3. Continue serving transactions.
  4. In the background, flush dirty pages whose recLSN < nextCheckpointLSN.

Recovery starts at minRecLSN — the oldest LSN that any dirty page
could still need. Pages flushed before minRecLSN are skipped by redo
via the pageLSN optimization.
```

PostgreSQL uses a variant called the "non-exclusive backup checkpoint" for its routine checkpoints; the bgwriter/L2 flushes dirty buffers in the background, and `checkpointer` writes the checkpoint record only when the prior flush is complete. InnoDB's "fuzzy checkpoint" flushes a small fraction of the buffer pool each cycle ("coordinated fuzzy checkpointing") to avoid I/O spikes.

## Group Commit

A naive implementation calls `fsync()` on the WAL for every commit. `fsync` on NVMe is ~10-50 µs; on SATA SSD ~200 µs; on rotating rust ~10 ms. At 10 ms per fsync, a database tops out at 100 commits/sec regardless of CPU.

**Group commit** batches multiple transactions' commit records into one WAL write and one `fsync()`:

```
Thread A: write commit_rec(A) to WAL buffer, set "want fsync"
Thread B: write commit_rec(B) to WAL buffer, set "want fsync"
Thread C: arrives 5µs later, joins the group
Leader (the first to set "want"):  fsync(WAL buffer up to commit_rec(C))
All three wake up; COMMIT returns.
```

PostgreSQL's group commit activates when `commit_delay > 0` (microseconds to wait for followers) — historically inefficient, replaced by `group_commit` heuristics that piggyback on the existing backends' wakeups. InnoDB's `innodb_flush_log_at_trx_commit=1` plus `binlog_group_commit` is the canonical implementation; the binary-log group-commit (introduced in 5.7) reduced commit latency for read-write MySQL workloads by an order of magnitude.

Modern Linux io_uring + DSYNC writes has made sub-microsecond group commit possible on NVMe; this is the basis for ScyllaDB and RocksDB's `io_uring` WAL.

## ARIES Algorithm Summary

ARIES (Algorithm for Recovery and Isolation Exploiting Semantics), designed by C. Mohan at IBM Almaden and described in the 1992 paper, is the canonical industry-standard recovery algorithm. Its three innovations:

1. **Repeating history** — redo *all* updates, including those of transactions that will be undone. The redo pass reproduces the exact on-disk state at crash; undo only then reverses the uncommitted ones.
2. **CLRs are redo-only** — undo records are never themselves undone. This makes the algorithm idempotent under repeated crashes during recovery.
3. **Per-page LSN** — every page carries `pageLSN`, the LSN of the last log record applied to it. Redo skips records whose LSN ≤ pageLSN. This avoids redoing changes already present on disk (the dominant cost in naive redo).

ARIES supports partial rollback (savepoints), fine-grained locking (so a transaction can hold locks after a partial rollback), and topological commit ordering for nested transactions.

## ARIES in Practice

PostgreSQL does not literally implement ARIES — it uses a simpler scheme where the WAL contains only redo images (no before-images for undo). Rollback uses the in-memory transaction undo chain and a `XACT`-style record marker; full-crash undo is not needed because PostgreSQL's tuple-visibility mechanism means uncommitted tuples are simply ignored by readers, then vacuumed later. This is a "no-undo WAL" — closer to the original IBM System R design than to ARIES.

InnoDB is much closer to classical ARIES. The redo log records `(space_id, page_no, body)` and the undo log records `(undo_log_page, before_image)`. During recovery, InnoDB replays the redo log forward (analysis + redo) then rolls back uncommitted transactions via the undo log segment (the "insert undo" and "update undo" segments).

## Comparison: WAL vs Shadow Paging

An alternative to WAL is **shadow paging** (also called shadow paging / shadow file). The whole database is a tree of pages. To commit a transaction:

1. Copy the path from root to the modified leaves — a "shadow" tree.
2. Modify the shadow's pages.
3. Atomically swap the root pointer to the shadow.

No log needed — durability is provided by the atomic root pointer swap. This was used by System R and by early versions of LMDB.

Tradeoffs:

| Dimension | WAL + Buffer Pool | Shadow Paging |
|---|---|---|
| Write locality | Sequential log writes (good) | Random writes scattered across page tree (bad) |
| Read locality | Pages wherever they live (one fetch) | Same |
| Commit latency | `fsync(log)` once | `fsync` all new pages + root swap |
| Fragmentation | Page-level; can be compacted | Worsens with each commit |
| Crash recovery | Redo + undo log scan | Pick one root, lose the other |
| Concurrency | Locks on pages, cheap | Atomic root swap forces serialization |

Shadow paging loses on every axis except "no log to manage" once you scale beyond a few thousand pages. LMDB (Lightning Memory-Mapped Database, used as the OpenLDAP backend) is one of the few production survivors — and it works because of a write-pattern constraint: it's effectively single-writer. The PostgreSQL B-tree indirectly uses a form of shadow paging (page splits produce new pages via WAL-protected writes), but the overall system is WAL-based.

## Worked Example: PostgreSQL WAL Segment Anatomy

PostgreSQL WAL files (called "WAL segments" or "xlog" segments) are 16 MB by default (tunable at compile time to 1 GB):

```
$ ls -la $PGDATA/pg_wal/
-rw------- 1 postgres 16M 000000010000000000000003
-rw------- 1 postgres 16M 000000010000000000000004
-rw------- 1 postgres 16M 000000010000000000000005
```

Each segment is named `<timeline><log><seg>` in hex. The first 8 bytes of every record are the LSN. Each record is variable-length. A simple UPDATE produces something like:

```
XLOG record (rmgr=Heap, info=INSERT, len=74):
  xl_info: 0x00 (INSERT)
  xl_rmid: 10 (Heap)
  xl_xid:  1234
  Buffer: blk 0 of rel 16384/16385/16386
  Tuple: (id=42, name='alice', ...)   ← after-image
```

A checkpoint record (rmgr=XLOG, info=CHECKPOINT) contains the previous checkpoint's redo location, the oldest active XID, and the time of the checkpoint. Recovery scans forward from the last completed checkpoint's redo location.

## Pitfalls

1. **Setting `fsync = off`.** Devastating. A crash will leave torn pages on disk; the WAL cannot repair them because the WAL only knows the post-update bytes, not the torn half-way state. PostgreSQL defaults to `fsync=on`; never turn it off in production.
2. **Synchronous commit = off.** Faster, but commits return before the WAL is durable. Suitable only for workloads that can tolerate recent-transaction loss on crash (e.g., metrics counters).
3. **WAL segments filling the disk.** A standby that falls behind will cause the primary to retain WAL. Configure `wal_keep_size` and replication slots carefully.
4. **Forgetting to flush data pages after WAL.** A custom storage engine that buffers pages forever will violate the redo-no-need property and silently corrupt after crash. Always fsync data pages before discarding from buffer pool.
5. **`full_page_writes = off` to save WAL space.** Reduces WAL size but risks partial-page writes during crash. Only safe on filesystems that guarantee atomic 8 KiB writes (rare).
6. **Long transactions during checkpoint.** A 1-minute transaction prevents the checkpoint from advancing past its start LSN, growing the WAL indefinitely and slowing crash recovery.

## References

- C. Mohan, D. Haderle, B. Lindsay, H. Pirahesh, P. Schwarz, "[ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollback Using Write-Ahead Logging](https://web.stanford.edu/class/cs345d-01/rl/mohan-aries.pdf)", *ACM TODS* 17(1), 1992 — the canonical recovery paper.
- Jim Gray and Andreas Reuter, *Transaction Processing: Concepts and Techniques*, Morgan Kaufmann, 1993, Chapter 11 ("Isolation Concepts") and Chapter 12 ("Recovery Concepts") — the most-cited textbook on WAL.
- R. A. Lorie, "[Physical Integrity of Large Data Bases](https://dl.acm.org/doi/10.1145/582099.582036)", *TODS* 2(1), 1977 — shadow paging original.
- PostgreSQL Documentation, "[Reliability and the Write-Ahead Log](https://www.postgresql.org/docs/current/wal-intro.html)" — production WAL docs.
- PostgreSQL Documentation, "[Internals: WAL](https://www.postgresql.org/docs/current/wal-internals.html)" and "[How Plans Use Indices](https://www.postgresql.org/docs/current/wal-configuration.html)".
- InnoDB Documentation, "[InnoDB Architecture: The Redo Log](https://dev.mysql.com/doc/refman/8.0/en/innodb-redo-log.html)".
- L. M. Haas et al., "[Recovery in Shared-Nothing Database Systems](https://dl.acm.org/doi/10.1145/1287889.1287890)", *VLDB 1986* — distributed recovery.
- Percona, "[How InnoDB Redo Log Works](https://www.percona.com/blog/2018/07/04/how-innodb-redo-log-works-in-mysql-8-0/)" — implementation notes.
- Mohan, "[ARIES Nuts and Bolts](https://dl.acm.org/doi/10.5555/882471.882503)" series — IBM technical reports extending ARIES.
- Howard Chu, "[LMDB Internals](https://www.openldap.org/pub/hyc/lmdb-concurrency-llnl-slides.pdf)" — modern shadow paging.
