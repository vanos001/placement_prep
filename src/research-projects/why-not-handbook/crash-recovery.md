# Crash Recovery: WAL vs In-Place Updates vs Append-Only/Copy-on-Write

## Overview

Every durable storage engine must answer one question before it can accept a single write: *if the process dies, or the machine loses power mid-write, how does the disk end up containing exactly the committed prefix of the log and nothing else?* The three classical answers — write-ahead logging (WAL) that protects in-place page updates, pure in-place updating with no log, and append-only/copy-on-write structures that never overwrite live data — are not three points on a performance dial. They are three different contracts about *when data is safe* and *who pays for that safety*.

This page runs the [handbook framework](./index.md) over that choice. The short version: in-place updating without a log is the fastest and the most fragile; WAL is the industry default because it converts an unbounded durability problem into a bounded, sequential one; append-only designs sidestep some of WAL's hardest problems (torn pages, undo of partial overwrites) and pay for it with compaction, write amplification, and space amplification. Along the way: ARIES by name, fsync discipline, torn pages, checksummed pages, and group commit.

## Step 1: The Problem and Its Constraints

The workload: writes arrive continuously, pages on disk are a fixed size (4–16 KiB typical), and the device can fail in the middle of any operation. The constraints that shape the choice:

- **Atomicity of the unit of change.** A transaction may touch many rows on many pages. Either all of it survives a crash or none of it does — the caller never sees half a transaction.
- **Durability without zero-latency hardware.** fsync latency is milliseconds on spinning disks, hundreds of microseconds on NVMe, and lies under some battery-backed write caches. No design may require "wait for the data page itself to be durably on disk before acknowledging" if a cheaper proxy exists.
- **Crash at any instruction boundary.** Not just "between transactions" — *during* a page write, during a log write, during a checkpoint.
- **Bounded recovery time.** A database that comes back after an outage in seconds and one that replays a week of un-checkpointed log are different products.

## Step 2: The Mechanisms

### Option 1: In-place updates with no log — the strawman that is not quite a strawman

Mutate the page in the buffer pool, write the dirty page back over its old disk image. No journal, no redo, no undo. The failure mode is total: kill the machine between a page-4 write and a page-9 write and the database contains a *mixture* of two transactions. Some systems genuinely live here — benchmark configurations with durability disabled, or analytics stores rebuilt nightly from source data. The honest statement: *this design is correct exactly when the data is disposable or re-derivable*, and it is the performance ceiling every other design pays down from.

### Option 2: Write-ahead logging (WAL) for in-place engines

The rule (Härder, 1977 — "Steady recovery upon system restarts is guaranteed if the log record describing a database change reaches stable storage *before* the data page it describes"): log first, mutate the page second, flush log before flushing data. The full machinery has named parts, and the named parts matter in interviews:

- **ARIES** (Mohan et al., 1992 — "ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging") is the reference design: *analysis* (find the dirty page table and the set of in-flight transactions from the last checkpoint), *redo* (repeat history — reapply every logged change forward, even to uncommitted transactions), *undo* (roll back in-flight transactions backward using compensation log records, which are themselves logged). "Repeating history" is the property that makes ARIES restartable after a crash during recovery.
- **Undo records** exist because in-place updates destroy the old value; you cannot roll back what you no longer have. Redo records exist because a dirty page flushed before its transaction committed may have carried uncommitted data to disk.
- **Checkpoints** bound redo length: flush dirty pages and record the dirty-page table so recovery starts from a known cut (see [checkpointing](../../dbms/transactions/checkpointing.md) and [WAL internals](../../dbms/advanced/wal-internals.md)).
- **fsync discipline** is the contract's teeth: a commit is acknowledged only after the commit record's fsync returns. PostgreSQL defaults to `fsync=on` with `synchronous_commit=on` precisely so an acknowledged commit survives OS crash, not just process crash ([PostgreSQL reliability docs](https://www.postgresql.org/docs/current/wal-intro.html)).

WAL converts an unbounded problem ("which pages are inconsistent?") into a bounded one ("replay the log since the last checkpoint"), and it keeps the log access pattern — sequential appends — which is the pattern disks and SSDs are best at.

### Option 3: Append-only / copy-on-write

Never overwrite live data. New versions are written to fresh locations; the structure that maps keys to locations is itself updated atomically.

- **LSM-trees** write immutable SSTables and let background compaction merge them — the log *is* the data, so there is nothing to "redo" (see [LSM trees](../../dbms/internals/lsm-trees.md)).
- **Copy-on-write B-trees** (LMDB, ZFS's file tree, sharded B-trees): a modifying path clones pages up to the root, and one pointer swap (or one root-page CAS) publishes the new tree atomically. Old pages become garbage for collection.
- **Bw-trees** map logical page IDs to physical locations through an indirection table and mutate pages by appending *delta records* rather than in-place edits — a design midway between WAL-protected mutation and pure immutability (see [bwtree-and-latch-free](../../dbms/internals/bwtree-and-latch-free.md)).
- **SQLite's rollback journal** is the mirror-image trick: copy the *original* pages aside, overwrite in place, and on crash restore the copies — same atomicity goal, opposite direction of saving (see [SQLite internals](../../dbms/internals/sqlite-internals.md)).

The unifying mechanism: **atomic pointer/segment publication**. A single small write (a root pointer, a manifest, a file rename) is made atomic by the filesystem/device, and everything else is immutable history. The Log-Structured File System (Rosenblum & Ousterhout, 1992) stated the idea for filesystems; LMDB's design note is explicit that COW plus a single root pointer eliminates the need for a separate WAL.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | In-place, no log | WAL + in-place | Append-only / COW |
|----------|------------------|----------------|-------------------|
| Commit cost | Data-page fsync (or nothing, if unsafe) | Log fsync (small, sequential) | New-version write + atomic publish (often without per-commit fsync of data) |
| Recovery work | None possible — state is broken | Bounded: replay log since checkpoint | Near-zero replay: open manifest/root, discard partial tail |
| Write amplification | Lowest (one page write) | Moderate: data page + log records + checkpoint rewrites | Highest: compaction rewrites data repeatedly; COW rewrites the whole path to the root per mutation |
| Read path | Fastest possible (pages in place) | Fast, but buffer-pool latches contend with recovery | Extra indirection (key → location map); fragmentation until compaction |
| Space behavior | Exact | Log adds headroom; checkpoint truncates | Garbage versions live until compaction/GC — space amplification |
| Signature failure | Torn multi-page update — silent corruption | Torn pages during data writes; slow recovery after long gap between checkpoints | Compaction falling behind; long GC pauses on old versions |

**Durability vs fsync discipline** deserves its own statement, because "WAL = durable" hides the knob: PostgreSQL's `synchronous_commit=off` keeps atomicity (no torn transactions) while allowing the last few milliseconds of acknowledged commits to vanish on OS crash; MySQL's `innodb_flush_log_at_trx_commit=2` has the same shape. Atomicity and durability are separately purchasable — a distinction interviewers reward (see [ACID, escalated](../followup-tree/acid-transactions.md)).

## Step 4: When Each Wins

**In-place without a log** is the right choice when data is a cache of something re-derivable (materialized views, search index replicas, CI scratch databases). The failure mode you accept is "restore from source", and you save every journal byte.

**WAL for in-place engines** wins when reads must stay fast on a mutable working set: update-in-place keeps hot pages at their addresses, so read amplification is minimal and the buffer pool does its job. This is why PostgreSQL and MySQL InnoDB are WAL machines: the OLTP workload is read-mostly with random point reads, exactly what in-place B-trees serve best. WAL also gives *physical* replication almost for free (ship the log; see [primary-backup replication](../../distributed/replication/primary-backup.md)).

**Append-only/COW** wins when writes stream faster than in-place mutation can take latching and journaling for, when reads tolerate extra indirection, or when snapshot semantics are valuable: LMDB reads are lock-free snapshots of a consistent tree; event-sourced systems (see [event sourcing and WAL](../connection-atlas/event-sourcing-wal.md)) treat the immutable log as the primary record. Time-travel reads and cheap replicas come from the same immutability.

## Step 5: Edge Cases and Counterexamples

- **Torn pages — the reason doublewrite/`full_page_writes` exist.** A 16 KiB page write is many 512-byte or 4 KiB device sectors; power loss can persist *half a page*. Redo alone cannot fix this: the page image on disk is garbage, and reapplying a delta log record to garbage yields garbage. PostgreSQL's answer is `full_page_writes=on`: after each checkpoint, the *first* modification of a page writes its full image to WAL, so recovery can restore a valid page image before reapplying deltas. InnoDB's answer is the doublewrite buffer: page images go to a staging area first. Both are pure taxes paid by *in-place* engines; append-only engines do not have torn live pages to protect.
- **Checksummed pages change the recovery calculus.** Without checksums, a torn page is a silent corrupt database; with checksums (PostgreSQL `initdb --data-checksums`, InnoDB's `crc32` page checksums), the corruption is at least *detected* and recovery can fail loudly or fall back to a replica. The catch: a checksum converts silent corruption into an outage at read time — one bad page can take a whole query or even startup down. Detection is not recovery; you still need a replica or backup to restore from (a data-loss incident of exactly this shape is dissected in [GitLab 2017](../failure-casebook/gitlab-2017-data-loss.md), where the postmortem's "restore path was untested" lesson generalizes to page-level recovery).
- **Group commit amortizes the log fsync.** Naively, each commit pays one fsync — 100 transactions/s ceiling on a 10 ms disk. Group commit batches concurrent commits into one log flush, trading a bounded extra delay for a multiplicative throughput gain; both PostgreSQL (`commit_delay`) and MySQL's binlog group commit implement it. The counterexample: under *low* concurrency there is nothing to batch with, and the fsync tax is paid in full — which is why latency-sensitive low-QPS writers see worse commit latency than high-concurrency benchmarks suggest.
- **Append-only does not remove recovery — it moves it into compaction.** An LSM that never compacts turns reads into merge-sorts over hundreds of runs and tombstone checks over an unbounded graveyard; a COW tree that never frees old versions is a space leak. "No WAL needed" is true; "no background recovery machinery needed" is false — compaction *is* the ongoing recovery from a garbage-accumulation crash-in-slow-motion. Compaction storms can also starve foreground latency at exactly the wrong moment (see [compaction](../../dbms/internals/compaction.md)).
- **The fsync lie.** Some drives and virtualized disks acknowledge fsync without flushing. WAL is only as strong as the fsync beneath it; systems that truly care test device behavior. This is why "we have WAL" and "we are durable" are two different sentences.

## Step 6: Decision Framework

1. **Is the data re-derivable from a source of truth?** Yes → in-place/no-log (or even in-memory) is legitimate; invest in rebuild tooling instead of journals.
2. **Is the workload read-mostly OLTP with random point access?** → WAL + in-place B-tree; budget for `full_page_writes`, checksums, and checkpoint tuning.
3. **Write-heavy ingest, or need immutable history/snapshots?** → append-only (LSM or COW); budget for compaction resources, tombstone/GC policy, and read-amplification tuning (bloom filters).
4. **What exactly must an acknowledged commit survive?** Process crash → WAL + OS cache suffices; OS crash/power loss → fsync per commit (or accept `synchronous_commit=off` losses explicitly); storage lie → test the device, use battery-backed caches knowingly.
5. **What is the recovery-time objective?** Seconds → append-only or aggressive checkpointing; minutes of log replay tolerable → checkpoint interval is a tunable, not a fixed law.

## Interview Questions

1. **Why does WAL require the log record to reach disk *before* the data page?** Because the log is the only record of the change. If the data page reaches disk first and the machine dies before the log record does, the page carries a change that cannot be redone *or* undone — ARIES's redo/undo machinery has nothing to work from. Steal-no-read, force-nothing, the WAL rule is the invariant that makes recovery complete.
2. **A candidate says "LSM-trees don't need recovery because they're append-only." Where is the error?** The memtable and the not-yet-compacted tail are still volatile; recovery must locate segment boundaries and drop a partial last segment (or replay a small write log). The deeper error: compaction is itself crash-prone background work, and its atomic publication (manifest switch) is the append-only world's equivalent of a commit record.
3. **What is a torn page, and why can't redo alone fix it?** A page partially persisted because one logical write spans multiple device sectors and power failed mid-way. Redo applies *deltas* to a page image assumed valid; if the image itself is garbage, the result is garbage. Full-page images in WAL (PostgreSQL) or a doublewrite buffer (InnoDB) provide a known-good base image.
4. **Why does group commit exist, and what does it cost?** One fsync per transaction is a per-commit serialization point costing milliseconds; batching concurrent commits into one flush amortizes it. The cost is added commit latency for the waiters (bounded by the flush window) and slightly longer crash-loss windows when `synchronous_commit=off`-style relaxation is combined with it.
5. **You replace PostgreSQL with an LSM store and commit latency improves 10×, but p99 reads degrade. Explain both observations with one mechanism.** Append-only commits write an immutable record instead of latching and journaling a B-tree page — cheap, sequential, no torn-page protection needed. But reads now consult memtable plus multiple SSTable levels (and bloom filters for negative lookups), and compaction lag increases the number of runs until it catches up — read amplification is the bill for write-optimized ingestion.

## Key Takeaways

- The three designs differ in *where atomicity lives*: nowhere (unsafe in-place), in the log (WAL), or in an atomic publication step (append-only/COW). Everything else — cost, failure modes, recovery time — follows from that placement.
- WAL for in-place engines buys minimal read amplification and physical replication, and pays with log fsyncs, torn-page protection (doublewrite/full-page writes), and bounded-but-nonzero recovery replay.
- Append-only sidesteps undo, torn live pages, and separate redo logs, and pays with write amplification, space amplification, and compaction as a foreground-critical background job.
- Atomicity and durability are separately configurable (`synchronous_commit`, `innodb_flush_log_at_trx_commit`); interviews and postmortems both hinge on knowing which one you traded.
- fsync is the trust anchor of every design here, and it can lie; checksums detect corruption but never fix it — restore paths are part of the design.

## Cross-References

- [ARIES](../../dbms/transactions/aries.md) — the reference write-ahead recovery method, step by step.
- [Log-Based Recovery](../../dbms/transactions/log-recovery.md) and [Recovery](../../dbms/transactions/recovery.md) — undo/redo taxonomy.
- [Checkpointing](../../dbms/transactions/checkpointing.md) — how recovery length is bounded.
- [WAL Internals](../../dbms/advanced/wal-internals.md) — engine-level WAL mechanics in depth.
- [LSM Trees](../../dbms/internals/lsm-trees.md) and [Compaction](../../dbms/internals/compaction.md) — the append-only cost model.
- [Bw-tree and Latch-Free Indexes](../../dbms/internals/bwtree-and-latch-free.md) — delta-updating indirection-tree design.
- [SQLite Internals](../../dbms/internals/sqlite-internals.md) — rollback journal vs WAL mode in a small, readable engine.
- [Buffer Pool](../../dbms/caching/buffer-pool.md) — where dirty pages live between mutation and flush.
- [ACID Transactions: Follow-up Tree](../followup-tree/acid-transactions.md) — escalating interview chain on atomicity, durability, and isolation.
- [Event Sourcing and WAL: Connection Atlas](../connection-atlas/event-sourcing-wal.md) — the immutable log as a system-design pattern, not just an engine detail.
- [Storage Durability: Assumptions Hunt](../assumptions-hunt/storage-durability.md) — the device-level assumptions fsync discipline rests on.
- [GitLab 2017: Failure Casebook](../failure-casebook/gitlab-2017-data-loss.md) — named incident where restore paths, not journals, failed.
- [Database Choices](./database-choices.md) — sibling page: engine and index structure choices upstream of this one.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
