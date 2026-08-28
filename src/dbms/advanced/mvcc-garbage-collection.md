# MVCC Garbage Collection: Reclaiming What Concurrency Left Behind

Multi-version concurrency control buys readers and writers freedom from each
other by never overwriting anything in place - every UPDATE leaves the old
version behind for whoever might still be reading it. That promise has a bill:
the engine is now two engines, a version store and a garbage collector, and
the second one only gets noticed when it stops working. Every MVCC system
converges on the same failure - one forgotten transaction freezes reclamation
for the whole database - and every engine has grown its own vocabulary,
knobs, and disaster stories for it. This page is a cross-engine tour of that
machinery; the version-visibility rules themselves are in
[MVCC Internals](./mvcc-internals.md) and the snapshot semantics they serve in
[Snapshot Isolation](./snapshot-isolation.md).

## The shape of garbage

What "garbage" means depends on where versions live:

```text
PostgreSQL / SQL Server style: old versions stay in the table
  heap page:  [tuple v1 dead] [tuple v2 live] [tuple v3 dead] ...
  GC unit: a dead tuple, reclaimed in place (page compaction)

InnoDB / Oracle style: old versions live in undo
  current row in the table --version chain--> undo log record --> older
  GC unit: an undo record, dropped by walking the chain from the tail

Hekaton / SQL Server In-Memory style: versions chained in memory
  row: [begin-ts][end-ts] -> next version
  GC unit: a row whose end-ts is below the oldest active timestamp
```

The storage choice drives everything else - what the collector can safely
skip, what I/O it must pay, and what "too slow at GC" looks like:

| Engine | Versions live in | GC unit | Horizon = oldest version needed by | Throttle / knob | Overload symptom |
|--------|------------------|---------|-------------------------------------|-----------------|------------------|
| PostgreSQL | heap itself | dead tuple | global xmin (all snapshots, slots, standbys) | autovacuum cost limit/delay | table+index bloat, wraparound shutdown |
| MySQL InnoDB | undo log (rollback segs) | undo record | oldest active ReadView | `innodb_max_purge_lag` | history list growth, slowing reads |
| Oracle | undo tablespaces | undo extent | oldest active SCN (query flashbacks) | undo retention tuning | ORA-01555 snapshot too old |
| SQL Server rowstore | tempdb version store | version record | oldest active snapshot sequence | tempdb sizing | tempdb full |
| SQL Server In-Memory | in-memory row chains | timestamped row | oldest active txn timestamp | GC worker quantums | memory pressure, OOM |

## The xmin horizon: one transaction pins everything

A version is garbage only when no snapshot needs it. Formally: a dead version
created by xid A and killed by xid B is removable once B is known committed
and every still-active snapshot was taken after B committed. The largest
transaction ID any reader may need - the **xmin horizon** (Oracle: oldest
active SCN; SQL Server: oldest snapshot sequence) - is therefore a global
minimum over:

- every in-flight transaction, including the idle-in-transaction session that
  started a report and went to lunch;
- prepared (two-phase-commit) transactions;
- replication slots and standby feedback (PostgreSQL holds back the primary's
  horizon for a standby that advertises `hot_standby_feedback = on`);
- any snapshot exported by `pg_export_snapshot` or held by a cursor.

One pinned transaction degrades reclamation to zero for the whole database,
because the horizon is a minimum, not an average. The worked simulation below
shows what that does to a table over 24 epochs.

## PostgreSQL: VACUUM, freezing, and wraparound

VACUUM sweeps a table, decides each tuple dead or alive, removes dead ones,
and compacts pages so the freespace map can reuse them. Between full passes,
HOT (heap-only tuple) updates prune dead versions opportunistically when a
page is touched - but only versions their own transaction chain already hides,
which is why HOT both reduces garbage and cleans it up early.

The trigger arithmetic is the first tuning surface: autovacuum fires when
`n_dead_tup > autovacuum_vacuum_threshold + autovacuum_vacuum_scale_factor * reltuples`
(50 + 20% by default). A 10M-row table therefore tolerates 2M dead tuples
before doing anything - fine for inserts, terrible for an update-in-place
workload that rewrites the same 50K rows, where per-table overrides should
drop the scale factor to near zero.

Cost throttling is the second surface. Vacuum prices I/O - page hit, page
miss, page dirty - accumulates credits, and sleeps `vacuum_cost_delay` (2ms)
whenever the accumulated cost exceeds `vacuum_cost_limit` (200; PostgreSQL 16
lowered the miss default from 10 to 2, roughly a 3-5x faster default vacuum on
cold caches). The intent is politeness; the failure mode is a vacuum that can
never catch up, which is why `vacuum_failsafe_age` (1.6B by default) exists:
when a table approaches wraparound danger, the failsafe disables cost-based
delays and index bypass entirely.

Freezing is the part with a hard deadline. Transaction IDs are 32 bits; a
tuple's `xmin` must be made "frozen" (permanently past) before its creating
xid could be reused, or old rows would suddenly appear to be from the future.
Autovacuum anti-wraparound passes are forced once a table's age passes
`autovacuum_freeze_max_age` (200M). If the whole database ages past the
limits, PostgreSQL escalates: warnings at ~40M xids before wraparound, then
`database is not accepting commands to avoid wraparound data loss` and
refusal to assign new XIDs at ~3M before - an emergency that historically
required days of single-user VACUUM to clear. Monitor `age(datfrozenxid)` per
database, not just bloat.

## MySQL InnoDB: purge threads and the history list

InnoDB never needs a VACUUM command because GC is continuous: the current row
is updated in place, old versions go to undo logs, and dedicated **purge
threads** (coordinator plus `innodb_purge_threads` workers, 4 by default) walk
undo records whose killing transaction is below the oldest active ReadView.
The queue's length is visible as the history list length in
`SHOW ENGINE INNODB STATUS` - the single most useful InnoDB GC metric.

The failure mode is the long-running ReadView: undo cannot be purged past it,
every subsequent SELECT on those rows walks longer version chains, and read
latency climbs with the undo backlog. InnoDB's self-defense is
`innodb_max_purge_lag`: when history exceeds the threshold, reads and writes
are deliberately throttled (up to `innodb_max_purge_lag_delay` per row) to
give purge a chance - trading application latency for reclaim progress. Large
undo backlogs can also be relieved by `innodb_undo_log_truncate` with
separate undo tablespaces.

## Oracle: undo retention and the oldest SCN

Oracle's undo tablespace is a ring of segments; retention says how long old
undo should survive. With auto-extend datafiles, the instance tunes retention
upward to satisfy the longest running query (`undo_retention` is a *low
threshold*); with fixed-size files, it reuses undo as needed and old queries
risk `ORA-01555: snapshot too old` - Oracle's version of the horizon problem,
surfaced as an error instead of silent bloat. V$UNDOSTAT tracks the
max-query-length and unexpired-undo statistics that make retention sizing a
measured decision rather than folklore.

## SQL Server: a tempdb version store and quantized in-memory GC

Row-versioning isolation (read-committed-snapshot, snapshot) writes old row
versions into a version store in tempdb; a background cleanup thread drops
versions once no active transaction needs their snapshot sequence number.
The operational story is tempdb capacity: an abandoned long transaction turns
into tempdb growth, and tempdb is shared by everything - sort spills, index
builds, and the version store fight for the same disk.

In-Memory OLTP (Hekaton lineage) is the interesting outlier: rows are memory
residents chained by (begin-ts, end-ts) timestamps, and GC is *eager at
commit* for transaction-local garbage plus background workers that sweep rows
visible to nobody. The design detail worth knowing is quantization: GC work
is done in small time slices donated by worker threads rather than by one big
collector, so cleanup never becomes a long pause - the price is that very
large update transactions release memory late, behind the same
oldest-active-timestamp horizon as everyone else. The durability side of
these tables (checkpoint files, tail-of-log) is in Microsoft's memory-OLTP
documentation.

## Tuning without cargo cult

| Question to ask | PostgreSQL answer | InnoDB answer |
|-----------------|-------------------|---------------|
| is GC keeping up? | `pg_stat_user_tables.n_dead_tup` trend vs trigger | history list length in `SHOW ENGINE INNODB STATUS` |
| what is pinned? | `pg_stat_activity` (xact_start), `pg_locks`, slot `xmin` | `information_schema.innodb_trx`, `SHOW ENGINE` oldest ReadView |
| is vacuum throttled? | `pg_stat_progress_vacuum` + log lines (`log_autovacuum_min_duration`) | purge system history / undo tablespace usage |
| what did it reclaim? | `n_dead_tup` drop, `pg_stat_user_indexes` unused | `trx_rseg_history_len` drop, undo truncation events |

Three cross-engine rules survive contact with production. First, find the
pinned transaction before tuning the vacuum - `idle in transaction` is almost
always the answer, and no knob compensates for it (set `idle_in_transaction_session_timeout`
in PostgreSQL, and equivalent kill switches elsewhere). Second, throttle vacuums
*below* your IO headroom, not your fear level: a throttled vacuum that never
finishes is worse than a brief IO storm. Third, monitor the horizon age, not
just bloat - bloat recovers after release, wraparound risk only accumulates.

## Worked simulation: pinned horizon, then the catch-up sweep

A pure-stdlib, deterministic model of the classic incident: one long-running
reader pins the horizon from epoch 6 to epoch 30 while 300 single-row updates
per epoch continue on a 10,000-tuple heap. Removability follows the real rule
(a dead version is removable only when its *killing* xid precedes the oldest
needed snapshot), and vacuum I/O is priced with the PostgreSQL cost model.

```python
"""MVCC garbage-collection cost model with a long-running reader.

Deterministic simulation of a 10,000-tuple PostgreSQL-style heap under an
UPDATE workload with one long-running reader pinning the xmin horizon from
epoch 6 to epoch 30. Autovacuum triggers at dead > 0.2*n_live + 50 and can
only remove tuples created before the horizon. Vacuum I/O is priced with the
PostgreSQL cost model (miss=10, dirty=20, hit=1, limit=200, sleep=2ms).
No RNG: tuple rotation is arithmetic.
"""
N_TUPLES = 10_000
TUPLES_PER_PAGE = 50                     # -> 200 heap pages
UPDATES_PER_EPOCH = 300
VACUUM_SCALE, VACUUM_THRESHOLD = 0.2, 50
COST_MISS, COST_DIRTY, COST_LIMIT, COST_DELAY_MS = 10, 20, 200, 2.0
PAGE_SCAN_MS = 0.005

xid = 100                                # fake, wraparound-safe base
last_frozen = 100                        # age(datfrozenxid) baseline
last_modified = list(range(100, 100 + N_TUPLES))   # xid that wrote each tuple
dead = []                                # dead tuple creating-xids
events = []
rows = []
pinned_xmin = None                       # long-running reader's snapshot xmin

def run_vacuum(epoch, horizon):
    """Sweep removable dead tuples; price I/O with the PostgreSQL cost model.

    A dead version is removable only when the transaction that killed it
    (its updater) has a commit xid below the oldest snapshot still needed -
    snapshots that predate the kill may still be reading that version.
    """
    removable = [d for d in dead if d[1] < horizon]
    dead[:] = [d for d in dead if d[1] >= horizon]
    pages = sorted({d[0] // TUPLES_PER_PAGE for d in removable}) or [0]
    cost = len(pages) * (COST_MISS + COST_DIRTY)
    sleeps = cost // COST_LIMIT
    dur = sleeps * COST_DELAY_MS + len(pages) * PAGE_SCAN_MS
    return removable, pages, dur

for epoch in range(0, 49):
    base = (epoch * UPDATES_PER_EPOCH) % N_TUPLES
    for _ in range(UPDATES_PER_EPOCH):   # 300 single-row UPDATE txns
        xid += 1
        t = (base + xid) % N_TUPLES
        dead.append((last_modified[t], xid))   # (creating xid, killing xid)
        last_modified[t] = xid

    if epoch == 6:                       # long reader opens, pins the horizon
        xid += 1
        pinned_xmin = xid
        events.append(f"epoch {epoch:2d}: long reader opens, pins horizon at xid {xid}")
    if epoch == 30:
        pinned_xmin = None
        events.append("epoch 30: long reader commits, horizon released")

    horizon = pinned_xmin or xid

    if len(dead) > VACUUM_SCALE * N_TUPLES + VACUUM_THRESHOLD:
        removable, pages, dur = run_vacuum(epoch, horizon)
        if removable:
            events.append(f"epoch {epoch:2d}: vacuum removes {len(removable):5d} dead "
                          f"(horizon {horizon}), {len(pages):3d} pages, "
                          f"{dur:6.1f} ms throttled / {len(pages) * PAGE_SCAN_MS:5.2f} ms unthrottled")
            if epoch > 6:
                last_frozen = xid        # whole-table freeze pass ran here
        elif epoch % 8 == 0:
            events.append(f"epoch {epoch:2d}: vacuum runs, 0 removable (horizon {horizon} too old)")
    rows.append((epoch, len(dead), horizon))

print("MVCC GC simulation: 10,000 tuples, 300 updates/epoch, 200 heap pages")
print(f"autovacuum trigger: dead > {int(VACUUM_SCALE * N_TUPLES + VACUUM_THRESHOLD)}")
print()
print(" epoch | dead | horizon")
for e, d, h in rows:
    if e % 3 == 0 or e in (6, 30, 31, 32):
        print(f"   {e:2d}  | {d:5d} |  {h:5d}")
print()
for msg in events:
    print(msg)
print()
peak = max(d for _, d, _ in rows)
print(f"peak bloat while reader pinned: {peak} dead tuples "
      f"({peak / N_TUPLES * 100:.0f}% of table = {peak / TUPLES_PER_PAGE:.0f} extra pages)")
print(f"xid age at end: {xid - last_frozen:,} -> epochs to 2^31 wraparound "
      f"at this rate: ~{(2**31 - (xid - last_frozen)) / (UPDATES_PER_EPOCH * 2):,.0f}")
```

```text
MVCC GC simulation: 10,000 tuples, 300 updates/epoch, 200 heap pages
autovacuum trigger: dead > 2050

 epoch | dead | horizon
    0  |   300 |    400
    3  |  1200 |   1300
    6  |     0 |   2201
    9  |   900 |   2201
   12  |  1800 |   2201
   15  |  2700 |   2201
   18  |  3600 |   2201
   21  |  4500 |   2201
   24  |  5400 |   2201
   27  |  6300 |   2201
   30  |     1 |   9401
   31  |   301 |   9701
   32  |   601 |  10001
   33  |   901 |  10301
   36  |  1801 |  11201
   39  |   601 |  12101
   42  |  1501 |  13001
   45  |   301 |  13901
   48  |  1201 |  14801

epoch  6: long reader opens, pins horizon at xid 2201
epoch  6: vacuum removes  2100 dead (horizon 2201),  49 pages,   14.2 ms throttled /  0.24 ms unthrottled
epoch 16: vacuum runs, 0 removable (horizon 2201 too old)
epoch 24: vacuum runs, 0 removable (horizon 2201 too old)
epoch 30: long reader commits, horizon released
epoch 30: vacuum removes  7199 dead (horizon 9401), 154 pages,   46.8 ms throttled /  0.77 ms unthrottled
epoch 37: vacuum removes  2100 dead (horizon 11501),  53 pages,   14.3 ms throttled /  0.27 ms unthrottled
epoch 44: vacuum removes  2100 dead (horizon 13601),  60 pages,   18.3 ms throttled /  0.30 ms unthrottled

peak bloat while reader pinned: 6900 dead tuples (69% of table = 138 extra pages)
xid age at end: 1,200 -> epochs to 2^31 wraparound at this rate: ~3,579,137
```

Three things to read out of the numbers. The pinned phase is not an I/O
problem - vacuum runs and finds nothing removable, because removability is
governed by the horizon, not by effort. The 69% bloat is pure overhead of one
idle session: 6,900 dead tuples, 138 pages of dead weight that every seq
scan must skip. And the catch-up sweep at epoch 30 shows why throttling
matters in reverse: 154 pages cost 0.77ms of actual work but 46.8ms under the
cost model - politeness is a 60x tax, which is exactly the trade the
`vacuum_failsafe_age` mechanism reverses when survival demands speed.

## References

- PostgreSQL: [Routine Vacuuming chapter (incl. preventing transaction ID wraparound)](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- MySQL 8.x Reference Manual: [InnoDB Purge Configuration](https://dev.mysql.com/doc/refman/8.1/en/innodb-purge-configuration.html) (dev.mysql.com returns 403 to scripted probes; page verified via search)
- Oracle Database Administrator's Guide: [Managing Undo](https://docs.oracle.com/en/database/oracle/oracle-database/26/admin/managing-undo.html)
- Microsoft Learn: [Durability for Memory-Optimized Tables (In-Memory OLTP GC)](https://learn.microsoft.com/en-us/sql/relational-databases/in-memory-oltp/durability-for-memory-optimized-tables?view=sql-server-ver17)
- PostgreSQL: [Autovacuum runtime configuration](https://www.postgresql.org/docs/current/runtime-config-autovacuum.html)
