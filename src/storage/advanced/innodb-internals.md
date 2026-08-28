# InnoDB Internals

InnoDB keeps one logical copy of your data — a forest of B+tree pages — but
it surrounds that forest with four write-path structures that absorb every
awkward physical reality of disks: a buffer pool that must not lose hot
pages to table scans, a change buffer that defers secondary-index work, a
doublewrite area that survives torn pages, and a redo log that makes the
whole thing replayable. This page walks the write path the way the engine
does, subsystem by subsystem, and ends with a runnable model of the two
structures engineers argue about most: midpoint LRU and doublewrite.

## One UPDATE, end to end

```text
 client: UPDATE t SET v=42 WHERE id=7
   |
   v                      buffer pool (RAM)
 [row id=7 located] --> +--------------------------+
   |                    | clustered-index page copy|<--- undo log record
   |                    | secondary-index pages?   |     (old row image)
   |                    +--------------------------+
   |                            | dirty            ^
   v                            v                  | purge (later)
 redo log buffer: (space,page,action) records     |
   |  group commit, fsync                         |
   v                                              |
 ib_logfile / #innodb_redo  <--- LSN advances     |
   |                                             |
   v                                             |
 page cleaner flushes dirty pages                |
   |  (through doublewrite area first)           |
   v                                             |
 doublewrite file --> data tablespace .ibd ------+ (page images at rest)
```

The ordering constraints inside that diagram are the entire durability
story: the redo record for a change reaches stable storage before the dirty
page it describes is written, and a dirty page is written nowhere until a
complete copy of it is safely sitting in the doublewrite area. General WAL
theory behind this is covered in [wal-internals.md](../../dbms/advanced/wal-internals.md)
and the ARIES recovery lineage in [aries.md](../../dbms/transactions/aries.md).

## Buffer pool: three lists, not one

The buffer pool is a set of frames (default page size 16 KB) managed by
three linked structures: the **free list** (empty frames), the **LRU list**
(all resident pages in recency order), and the **flush list** (dirty pages
in oldest-modification order — the page cleaner flushes from its head to
control checkpoint age). Large pools are sharded into
`innodb_buffer_pool_instances` to reduce latch contention on those lists.

The LRU list is not a plain LRU. A naive LRU destroys a hot OLTP working
set the moment any large sequential scan (a reporting query, a backup read,
`SELECT ... INTO OUTFILE`) streams tens of thousands of one-touch pages
through it. InnoDB therefore splits the list at a **midpoint**:

```text
    young sublist (hot)            midpoint           old sublist (new + churn)
 +---------------------------+      |      +-----------------------------+
 | h0 h1 h2 ... hN  (63%)    | <----+      | new pages enter here (37%)  |
 +---------------------------+                    | ... old tail = victim LRU   |
        ^ promoted here only                       +-----------------------------+
        after innodb_old_blocks_time (1000 ms)      ^ evictions come from here
```

- New (read-in) pages are inserted at the **head of the old sublist**, not
  the list head — `innodb_old_blocks_pct` defaults to 37.
- A page moves to the young head only if it is accessed again after
  residing in the old sublist for at least `innodb_old_blocks_time`
  (default 1000 ms). One-touch scan pages never qualify; they recirculate
  through the old sublist and fall off the tail.
- Eviction always takes the old-sublist tail. Young pages are only demoted
  when the young sublist overflows its share.

The runnable model below shows the payoff: after one 40-page scan, naive
LRU has lost its entire hot set (0/10 hits on the next hot loop) while the
midpoint pool keeps 10/10. The classic cache-policy background is in
[buffer-pool.md](../../dbms/caching/buffer-pool.md); the trade against
LSM-tree designs (which give up in-place updates entirely to make writes
sequential) is in [lsm-tree-deep.md](./lsm-tree-deep.md).

## Change buffer: deferring the second B+tree

A write to a clustered-index page almost always implies writes to every
secondary index whose key covers the row — and those leaf pages may not be
resident. Reading a random secondary-index leaf page into the pool for
every write is exactly the random-I/O bill InnoDB tries to avoid, so for a
non-unique secondary index whose leaf page is **absent** from the pool,
InnoDB instead records the pending change in the **change buffer**
(a B+tree in the system tablespace). The merge happens later: when the
leaf page is read into the pool, or during periodic background merge.
An index can only be change-buffered if uniqueness can be checked without
reading the page, which is why `UNIQUE` secondary indexes are exempt.

The costs are asymmetric and worth naming: the benefit is one less random
read+write per row per secondary index on write-heavy workloads; the cost
is that reads of change-buffered ranges become slower (they pay the merged
debt), and recovery replays the change buffer too. Workloads with
read-after-write index access patterns (e.g. counters read back by dashboards)
sometimes measure a net loss and disable it
(`innodb_change_buffering=none`).

## Doublewrite buffer: the torn-page defense

A page is 16 KB; the atomicity unit below it is the disk sector (512 B or,
on 4Kn drives, 4 KB). A crash mid-write can therefore land **half a page** —
a torn page — and no amount of redo replay helps, because redo recovery
assumes it is applying records to a valid page image. InnoDB's answer is to
never write a dirty page straight to its tablespace:

1. Copy the page into an in-memory doublewrite buffer (two ~1 MB blocks).
2. `fsync` those blocks sequentially into the doublewrite area
   (system tablespace before MySQL 8.0.20; dedicated `#innodb_redo`-style
   `.dblwr` files after).
3. Only then write the pages to their real tablespace locations.

After a crash, recovery checksums every restored page (checksum lives in
the FIL trailer): a torn or blank page is simply replaced by its complete
doublewrite copy, which by construction finished fsyncing before the
datafile write began. The cost is every page written twice — the price of
turning "16 KB must be atomic" into "1 MB was already durable". The demo
below models exactly this sequence. For the redo-log interplay (why redo
replay can tolerate a stale but *valid* page, but not a torn one), see
[wal.md](../wal.md) and Percona's torn-page comparison with PostgreSQL.

## Redo log: LSNs, mini-transactions, group commit

Redo is physical: records describe byte-level changes to specific
`(space, page)` targets, generated by **mini-transactions** (mtr) — the
internal units of atomicity below the transaction level (one mtr per index
page operation, atomic because each log block carries its own checksum).
Everything is ordered by the 64-bit **log sequence number (LSN)**, which
doubles as the currency of durability: a dirty page at LSN 9000 may not be
written to disk before redo through LSN 9000 is fsynced (WAL rule), and the
difference between the oldest un-checkpointed change and the current LSN —
the **checkpoint age** — must stay under the redo capacity. When age grows,
the page cleaner flushes dirty pages from the flush list head aggressively;
when it approaches capacity, user threads are forced to stall and flush
themselves. That is **fuzzy checkpointing**: no stop-the-world checkpoint,
just a continuously advanced boundary, with `innodb_adaptive_flushing`
smoothing the rate based on how fast redo is generated.

Commit-path mechanics that interviews probe:

| Knob | Value | Meaning |
|------|-------|---------|
| `innodb_flush_log_at_trx_commit` | 1 | fsync redo on every commit (default; ACID) |
| | 2 | write to OS cache per commit, fsync ~1/s (loses ~1s of commits on OS crash) |
| | 0 | flush once per second from a background thread (loses ~1s on server crash too) |
| binlog group commit | stages | commits queue: flush → sync → commit stages shared across threads |
| redo log blocks | 512 B | each block: header, payload, checksum; survives partial blocks |

**Group commit** matters because one fsync per transaction cannot scale:
concurrent commits are batched so a single fsync makes all of their redo
durable. The binary log implements its own multi-stage group commit so the
redo fsync and binlog fsync of the MySQL-level two-phase commit stay
pipelined rather than serialized per transaction.

## Undo logs and purge: the MVCC debt

InnoDB keeps old row versions not in the clustered index (PostgreSQL's
style) but in **undo logs**: insert undo (needed only to roll back the
inserting transaction; discarded at commit) and update undo (needed by
MVCC ReadViews; kept after commit until no possible reader needs it). A
long-running reader pins update undo, which is why an uncommitted-open
transaction over a write-heavy table makes history grow without bound.
The **purge** subsystem (coordinator + worker threads) walks committed
update-undo in commit order, physically deleting dead versions and freed
index entries; if it falls behind, `innodb_max_purge_lag` throttles writers
as backpressure. Undo tablespaces can be truncated at runtime
(`innodb_undo_log_truncate`). The version-chain mechanics (DB_TRX_ID,
roll pointers, ReadView construction) are detailed in
[mvcc-internals.md](../../dbms/advanced/mvcc-internals.md).

## Page anatomy: where the row actually lives

```text
 16 KB page
 +--------------------------------+ 0
 | FIL header (38 B)              |  checksum, page no, prev/next page ptrs,
 |                                |  page type, latest LSN applied
 +--------------------------------+
 | Index page header (56 B)       |  record counts, levels, last-insert pos
 +--------------------------------+
 | Infimum + Supremum records     |  virtual min/max keys for locking/scans
 +--------------------------------+
 | User records grow downward     |  key cols | trx_id(6B) | roll_ptr(7B) | cols
 |                                |  record header: delete-mark, heap no,
 |                                |  next-record offset, var-len lengths,
 |                                |  null bitmap (Compact format)
 +--------------------------------+
 |        free space              |
 +--------------------------------+
 | Page directory grows upward    |  binary-search slots into record list
 +--------------------------------+
 | FIL trailer (8 B)              |  checksum + old-style LSN (torn detection)
 +--------------------------------+ 16384
```

Two layout decisions explain most InnoDB behavior at scale. First, rows
live **inside** the clustered-index leaf pages in primary-key order — a
table with no explicit PK gets a hidden auto-increment-style row id, which
is why "give every table an explicit PK" is standing advice. Second,
secondary index leaf entries store the indexed key **plus the primary key
value** (the back-pointer), so a secondary lookup is a second B+tree
traversal — the trade-off analysis lives in
[b-tree.md](../../dbms/indexing/b-tree.md). Random PKs (e.g. UUIDs) split
clustered pages everywhere; monotonic PKs append (with the tail-insert
hotspot as the flip side).

## Flushing details that show up in production

- **Flush neighbor** (`innodb_flush_neighbors`): when flushing a dirty
  page, also flush adjacent dirty pages in the same extent — one seek on
  rotating disks, pure waste on SSDs. The default has been `0` (off) since
  MySQL 8.0, matching SSD-first hardware.
- **Page cleaner** threads own flushing and adaptive flushing; starvation
  shows up as checkpoint-age alarms long before the disk is "full".
- **Dirty-page percentage** (`innodb_max_dirty_pages_pct` and its low-water
  sibling) tunes how far the cleaner lets the pool fill; combined with
  adaptive flushing this is the main latency-smoothing knob for write-heavy
  fleets.
- **Log capacity planning**: redo capacity too small forces stuttering
  flushes at every checkpoint-age peak; too large stretches recovery replay.

## Interview drills

1. *Why can't redo replay alone fix a torn page?* Redo assumes a valid base
   image; the FIL-trailer checksum catches the tear and the doublewrite
   area supplies the pre-image.
2. *A reporting scan tanks your OLTP latency for 30 s. Which two
   parameters would you touch and why?* (Midpoint old-sublist share and
   time guard — plus moving the scan to a replica.)
3. *Your history list length grows unbounded. Name the pinning transaction
   and the two knobs that mitigate it.*
4. *Why does a UUID primary key hurt InnoDB specifically but not a
   heap-organized engine?*
5. *Why is the change buffer useless for a UNIQUE secondary index?*

## Runnable model: midpoint LRU + doublewrite recovery

```python
"""InnoDB buffer-pool midpoint LRU vs naive LRU + doublewrite torn-page recovery.

Part A replays one deterministic trace against two 30-frame pools:
  - naive LRU: single recency list, evict the tail
  - InnoDB midpoint LRU: new pages enter the OLD sublist (37% of frames);
    a page may move to the young head only after it has RESIDED in the old
    sublist for >= innodb_old_blocks_time (1000 ms) -- one-touch scan pages
    never qualify. Eviction always takes the old-sublist tail, so young
    pages are immune to scan churn.
Part B models a torn page: a 4-sector page lands only half-written in the
datafile during a crash. Recovery checksums every datafile page; any page
that is torn or blank is restored from the doublewrite area, whose own
fsync completed before datafile writes began.
"""
from collections import OrderedDict

# ---- Part A: midpoint LRU ---------------------------------------------------
HOT = ["h%d" % i for i in range(10)]        # 10 hot pages, re-touched each loop
SCAN = ["s%d" % i for i in range(40)]       # 40 pages touched once (table scan)
POOL, OLD_PCT, OLD_TIME_MS = 30, 37, 1000

class NaiveLRU:
    def __init__(self, cap): self.cap, self.m, self.hits = cap, OrderedDict(), 0
    def access(self, p, t):
        if p in self.m: self.hits += 1; self.m.move_to_end(p)
        else:
            if len(self.m) >= self.cap: self.m.popitem(last=False)
            self.m[p] = t

class MidpointLRU:
    def __init__(self, cap, pct, min_ms):
        self.old_cap, self.min_ms, self.hits = cap * pct // 100, min_ms, 0
        self.young_cap = cap - self.old_cap
        self.young, self.old, self.entered = OrderedDict(), OrderedDict(), {}

    def access(self, p, t):
        if p in self.young:
            self.hits += 1; self.young.move_to_end(p); return
        if p in self.old:                                   # hit inside old list
            self.hits += 1
            if t - self.entered[p] >= self.min_ms:          # survived the guard
                del self.old[p]; del self.entered[p]
                self.young[p] = t                           # promote: young head
                if len(self.young) > self.young_cap:        # push young tail down
                    tp, tt = self.young.popitem(last=False)
                    self.old[tp] = tt; self.entered[tp] = tt
            return
        if len(self.old) >= self.old_cap:                   # evict old tail only
            tp, _ = self.old.popitem(last=False); del self.entered[tp]
        self.old[p] = t; self.entered[p] = t                # new page -> old head

def run_trace(pool):
    """2 hot loops -> 40-page scan -> 3 hot loops, 200 ms per access.
    Returns (total hits, hits in the first hot loop after the scan)."""
    t, phase_hits, post_scan = 0.0, [0] * 6, 0
    for phase, pages in enumerate([HOT, HOT, SCAN, HOT, HOT, HOT]):
        for p in pages:
            before = pool.hits
            pool.access(p, t); t += 200
            if phase >= 3: post_scan += pool.hits - before
            phase_hits[phase] += pool.hits - before
    return pool.hits, phase_hits[3]

total = 5 * len(HOT) + len(SCAN)
n, n_post = run_trace(NaiveLRU(POOL))
m, m_post = run_trace(MidpointLRU(POOL, OLD_PCT, OLD_TIME_MS))
print("PART A  pool=30 frames  hot set=10  one-shot scan=40  accesses=%d" % total)
print("  trace: 2 hot loops, 40-page scan, 3 hot loops (200 ms per access)")
print("  naive LRU     total hits: %d/%d  first hot loop after scan: %d/10" % (n, total, n_post))
print("  midpoint LRU  total hits: %d/%d  first hot loop after scan: %d/10" % (m, total, m_post))
print("  the 1000 ms old-sublist guard promotes hot pages to young BEFORE")
print("  the scan; eviction only touches the old tail, so midpoint keeps them")

# ---- Part B: doublewrite torn-page recovery ---------------------------------
def cksum(page):
    return sum(ord(c) for sec in page for c in sec) % 65536

dblwr, data, crc = {}, {}, {}                 # dblwr: committed copies
for i in range(16):
    pg = ["%s%d" % ("ABCD"[j], i) for j in range(4)]
    dblwr["pg%d" % i] = pg; crc["pg%d" % i] = cksum(pg)

status = "CRASH during datafile write: pg7 torn after 2 of 4 sectors"
for i in range(16):                            # datafile write, torn at pg7
    n = "pg%d" % i
    if i < 7:
        for j in range(4): data[(n, j)] = dblwr[n][j]
    elif i == 7:
        data[(n, 0)], data[(n, 1)] = dblwr[n][0], dblwr[n][1]
        break                                  # ...power lost here

print("PART B  %s" % status)
fixed = []
for i in range(16):
    n = "pg%d" % i
    on_disk = [data.get((n, j), "") for j in range(4)]
    if all(on_disk) and cksum(on_disk) == crc[n]:
        continue                               # clean page: redo skips it
    why = "torn" if any(on_disk) else "blank"
    for j in range(4): data[(n, j)] = dblwr[n][j]
    fixed.append((n, why))
print("  recovery scan: %d of 16 pages bad: %s" %
      (len(fixed), ", ".join("%s=%s" % f for f in fixed)))
print("  restored all %d from the doublewrite area (fsynced pre-crash)" % len(fixed))
ok = all(cksum([data[("pg%d" % i, j)] for j in range(4)]) == crc["pg%d" % i]
         for i in range(16))
print("  post-recovery checksums: %s" % ("all 16 valid" if ok else "STILL BAD"))
```

```text
PART A  pool=30 frames  hot set=10  one-shot scan=40  accesses=90
  trace: 2 hot loops, 40-page scan, 3 hot loops (200 ms per access)
  naive LRU     total hits: 30/90  first hot loop after scan: 0/10
  midpoint LRU  total hits: 40/90  first hot loop after scan: 10/10
  the 1000 ms old-sublist guard promotes hot pages to young BEFORE
  the scan; eviction only touches the old tail, so midpoint keeps them
PART B  CRASH during datafile write: pg7 torn after 2 of 4 sectors
  recovery scan: 9 of 16 pages bad: pg7=torn, pg8=blank, pg9=blank, pg10=blank, pg11=blank, pg12=blank, pg13=blank, pg14=blank, pg15=blank
  restored all 9 from the doublewrite area (fsynced pre-crash)
  post-recovery checksums: all 16 valid
```

## References

- MySQL 8.0 Reference Manual, "InnoDB Architecture" — buffer pool, redo,
  undo, doublewrite placement. <https://dev.mysql.com/doc/refman/8.0/en/innodb-architecture.html>
  (curl 403 bot-blocked; verified via search)
- MySQL 8.0 Reference Manual, "Buffer Pool" — old/young sublist parameters.
  <https://dev.mysql.com/doc/refman/8.0/en/innodb-buffer-pool.html> (bot-blocked;
  search-verified)
- MySQL 8.0 Reference Manual, "Doublewrite Buffer".
  <https://dev.mysql.com/doc/refman/8.0/en/innodb-doublewrite-buffer.html>
  (bot-blocked; search-verified)
- Percona blog, "InnoDB Double Write — what is it and how does it work".
  <https://www.percona.com/blog/innodb-double-write> (bot-blocked; search-verified)
- Percona blog, "A tale of two databases: how PostgreSQL and MySQL handle
  torn pages". <https://www.percona.com/blog/a-tale-of-two-databases-how-postgresql-and-mysql-handle-torn-pages>
- mysql-server source (row0*, buf0lru, dblwr) —
  <https://github.com/mysql/mysql-server>
