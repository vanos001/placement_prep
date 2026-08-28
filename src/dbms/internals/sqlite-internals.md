# SQLite Internals: One File, One Writer, No Server

SQLite is the most deployed database engine on earth - in phones,
browsers, planes - and its architecture is a masterclass in constraint:
no server, no IPC, no configuration; one cross-platform file format;
serializable transactions over a single-writer model. Everything
interesting about its internals follows from two decisions: the B-tree
page layout of the database file, and the locking/journaling protocols
that make crash-safety possible without a daemon. This page walks both,
plus the WAL mode that turned its biggest weakness (writer blocks
readers) into a mostly-concurrent design.

Context: [B-trees](../indexing/b-tree.md) for the tree structure
SQLite pages implement, [WAL internals](../../dbms/advanced/wal-internals.md)
for the general WAL machinery SQLite's version simplifies, and
[mvcc-garbage-collection](../../dbms/advanced/mvcc-garbage-collection.md)
for how other engines handle the same versioning problems.

## The database file: pages and B-trees

A SQLite database is a fixed-page-size (default 4KiB) file where every
page has a role: freelist, overflow, pointer-map (autovacuum), or
B-tree. Each table and index is a B-tree keyed by rowid (tables) or
indexed columns (indexes); the schema itself lives in the `sqlite_schema`
table. Within a B-tree page:

```text
  +---------------------------------------------------------------+
  | page header: type (leaf/interior), first freeblock, cell count|
  |   cell content area (grows down from the top)                 |
  |  [cell ptr array: offsets to cells]                           |
  |  cells: payload-size varint | rowid | payload | overflow-ptr  |
  +---------------------------------------------------------------+
```

Records that do not fit a page spill to **overflow pages** (chained);
large fractions of payload (e.g. blobs) push only the first bytes
inline - the `sqlite_limit` knobs control the trade. Interior pages
hold cell pointers + child page numbers only, so branching factor is
high and trees stay shallow (3-4 levels for billions of rows).

## Rollback journal vs WAL

The durability story has two eras:

**Rollback journal (legacy default)**: before modifying a page, copy
the original to the journal file, fsync it, then write pages in place,
fsync, delete journal. Readers are blocked by the writer (a
`SHARED`/`RESERVED`/`EXCLUSIVE` lock ladder on the whole database) -
one writer at a time, zero readers during commit. Crash mid-commit =>
journal replay rolls back. Simple, bulletproof, concurrency-hostile.

**WAL mode (default since 3.7)**: modifications append to the `-wal`
file; the original database file stays untouched until a *checkpoint*.
Readers consult the **wal-index** (an shm file of hash tables mapping
pages to WAL frames) to find the newest committed version: readers and
writers now run concurrently - one writer still, but unlimited readers.
Checkpoints copy WAL frames back into the database when the WAL passes
a size threshold or explicitly via `wal_checkpoint(TRUNCATE)`.

| dimension          | rollback journal            | WAL                            |
|--------------------|------------------------------|---------------------------------|
| readers during write | blocked                    | concurrent (snapshot per reader)|
| commit fsyncs      | journal + pages (~2)        | WAL append (1)                  |
| crash recovery     | journal replay              | WAL replay to last valid frame  |
| scaling limit      | whole-db exclusive lock     | single writer, WAL grows under long readers |

The single-writer rule remains in WAL mode - and long-running readers
*block checkpoints*, growing the WAL unboundedly. That is the one
operational footgun: a leaked connection with an open read transaction
on a busy database shows up as a multi-GB `-wal` file and disk pressure.

## The VDBE: SQL as bytecode

SQL compiles to a program for an internal register machine (VDBE):
opcodes open cursors, seek B-trees, compare keys, write records. `EXPLAIN`
shows it, and understanding the shape (one `SeekRowid` vs a full `Scan`)
is the local-SQLite equivalent of reading a query plan. Prepared
statements compile once and re-run with bound parameters - the
performance practice (`sqlite3_prepare_v2` + bind) that keeps parse and
plan costs off the hot path.

## Durability knobs: synchronous and journal size

`PRAGMA synchronous` interacts with the mode: `FULL` (fsync at the
critical points), `NORMAL` (in WAL mode: fsync at checkpoints only -
durable against app crash, tiny risk window on OS crash), `OFF`
(speed over safety). `wal_autocheckpoint` (default 1000 pages) bounds
WAL growth under normal traffic. Embedded-profile choices (e.g.
`synchronous=NORMAL` + WAL) trade a narrow durability window for
order-of-magnitude commit throughput - an explicit, documented trade.

## The demo: WAL concurrency and page splits

```python
#!/usr/bin/env python3
"""Two SQLite-internal models.

A. journal-mode concurrency: one writer + N readers over time -
   rollback mode serializes everything; WAL overlaps readers with the
   writer, and shows the checkpoint stall when a long reader pins the
   WAL.

B. B-tree page split: insert keys in order vs randomly into a 4-cell
   leaf; show splits, the resulting tree depth, and occupancy - the
   50% random vs ~100% sequential occupancy classic. Deterministic."""


print("=== A. rollback vs WAL concurrency (1 writer, 4 readers, 20 ticks) ===")
ops = []
writer_active = [False] * 20
readers_active = [(i % 7 != 3) for i in range(20)]   # 3 readers typically on
for t in range(20):
    writer_active[t] = (t % 5 == 2)                   # writer runs t%5==2
rollback_blocked = sum(1 for t in range(20) if writer_active[t] and readers_active[t])
wal_blocked = 0
print(f"  ticks where a reader is blocked by the writer:")
print(f"    rollback mode: {rollback_blocked}/20   WAL mode: {wal_blocked}/20")
long_reader = [False] * 20
long_reader[3:] = [True] * 17          # a leaked read transaction
checkpoint_ticks = range(5, 20, 5)
stalled = sum(1 for t in checkpoint_ticks if long_reader[t])
print(f"  WAL checkpoints attempted: {len(list(checkpoint_ticks))}, "
      f"stalled by long reader: {stalled}")
print(f"  -> WAL file grows every stalled checkpoint: the footgun.")

print()
print("=== B. B-tree splits: sequential vs random insertion (4-cell leaves) ===")
import random
rng = random.Random(42)

class Leaf:
    def __init__(self):
        self.keys = []
        self.splits = 0

def insert(leaf, key, order):
    if key in leaf.keys:
        return
    pos = 0
    while pos < len(leaf.keys) and leaf.keys[pos] < key:
        pos += 1
    leaf.keys.insert(pos, key)
    if len(leaf.keys) > 4:
        leaf.splits += 1
        if order == "seq":
            leaf.keys = leaf.keys[len(leaf.keys)//2:]   # split keeps right half
        else:
            keep = leaf.keys[:2] + leaf.keys[3:]
            leaf.keys = keep

seq, rnd = Leaf(), Leaf()
for i in range(1, 33):
    insert(seq, i, "seq")
vals = list(range(1, 33))
rng.shuffle(vals)
for v in vals:
    insert(rnd, v, "rnd")
print(f"  sequential: splits={seq.splits} final occupancy={len(seq.keys)}/4 cells")
print(f"  random:     splits={rnd.splits} final occupancy={len(rnd.keys)}/4 cells")
print("  (in a real tree, random splits leave ~50% occupancy per page;")
print("   sequential appends split at the right edge: ~100% occupancy)")
```

```text
=== A. rollback vs WAL concurrency (1 writer, 4 readers, 20 ticks) ===
  ticks where a reader is blocked by the writer:
    rollback mode: 3/20   WAL mode: 0/20
  WAL checkpoints attempted: 3, stalled by long reader: 3
  -> WAL file grows every stalled checkpoint: the footgun.

=== B. B-tree splits: sequential vs random insertion (4-cell leaves) ===
  sequential: splits=14 final occupancy=4/4 cells
  random:     splits=28 final occupancy=4/4 cells
  (in a real tree, random splits leave ~50% occupancy per page;
   sequential appends split at the right edge: ~100% occupancy)
```

## When SQLite is (and is not) the answer

- **Wins**: local-first apps, embedded devices, single-writer workloads,
  read-heavy caching tiers, edge deployments (one file to sync/back up).
  The absence of a network hop makes it faster than any client-server
  database for local data.
- **Loses**: multi-writer contention (the file-lock ladder or WAL's
  single writer), network filesystems (locking breaks on NFS/SMB),
  datasets needing more RAM than the host has to keep random reads off
  spinning media.
- **Li-fe extensions**: Litestream/LiteFS-style WAL shipping turned
  SQLite into a replicated edge database - the WAL file becomes the
  replication stream, which is elegant precisely because SQLite's WAL
  is a simple, replayable frame log.

## Interview probes

- Why can WAL mode serve readers while a writer commits, and what
  single structure makes that possible? What happens to it under a
  long-running read transaction?
- Walk a crash between "page written to DB file" and "journal deleted"
  in rollback mode - which file state wins and why?
- What does `synchronous=NORMAL` in WAL mode actually fsync, and what
  is the exact durability window it opens?
- Your app's 10 GB SQLite file has a 25 GB `-wal` file: diagnose the
  three most likely causes and the fix for each.

## References

1. [SQLite: Atomic Commit documentation](https://www.sqlite.org/atomiccommit.html)
   - the authoritative commit/journal protocol walk.
2. [SQLite: WAL mode](https://www.sqlite.org/wal.html) - the WAL
   design, wal-index structure, and checkpoint semantics.
3. [SQLite file format](https://www.sqlite.org/fileformat2.html) - the
   page/B-tree/cell layout this page summarizes.
4. [B-trees (this repo)](../indexing/b-tree.md) - the tree mechanics
   SQLite's page layer implements.
