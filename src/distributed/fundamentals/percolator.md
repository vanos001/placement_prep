# Percolator: Incremental Processing with Distributed Transactions on Bigtable

## Why Google Rebuilt Its Index Pipeline

Google's original web-index pipeline was pure MapReduce: crawl, then *regenerate the entire index* from the whole repository in one giant batch job. Full rewrites are simple to reason about, but they have two structural costs. First, a change to a single page — a news article, a price update — waits for the *next* full rebuild before the index sees it; freshness is bounded by batch cadence. Second, the pipeline must store intermediate artifacts for every page, whether or not anything changed, which wastes enormous storage and machine-hours.

Percolator (OSDI 2010, Peng & Dabek) replaced that pipeline for the Google web index: it processes the same crawl corpus *incrementally*, updating just the documents that changed. Doing that safely requires three things MapReduce never provided:

1. **Random-access reads and writes** against petabytes of data at massive throughput;
2. **Multi-row atomic transactions**, because "this page's content changed" must atomically update the page record, its out-links, and its reverse-index entries — index corruption here means wrong search results;
3. **An observer/notification mechanism**, so that "when this document's status changes, re-evaluate its PageRank" could be expressed as a small reaction rather than a full pipeline stage.

Percolator's workload shaping is the key to its design: the system is built for **throughput, not latency**. An index build does not care whether one document takes 100 ms or 10 s; it cares that millions of documents per second flow through. That tolerance for latency is exactly what lets Percolator simplify the hardest part of distributed transactions — *what to do when a coordinator dies holding locks* — with a lazy, throughput-friendly answer (below).

## The Storage Layer: Three Columns on Bigtable

Percolator stores all state in Bigtable. Every logical "column" of application data becomes a *family* of three physical Bigtable columns:

```text
Logical cell (row key, column) as stored in Bigtable:

Row: url:http://example.com/a
┌──────────────┬───────────────────────────────┐
│ Column       │ Versions (Bigtable keeps many)│
├──────────────┼───────────────────────────────┤
│ balance:data │ @7  :  {"balance": 90}        │  <- written by txn, tagged start_ts
│              │ @5  :  {"balance": 100}       │
│ balance:lock │ @7  :  {primary: "url:.../b"} │  <- uncommitted txn's lock
│ balance:write│ @6  :  data@5                 │  <- commit marker: "committed
│              │ @4  :  data@3                 │      version @6 reads data@5"
└──────────────┴───────────────────────────────┘
```

- **`data`** holds the value, timestamped with the *start* timestamp of the transaction that wrote it.
- **`lock`** marks an in-flight, uncommitted write. The lock on the **primary** cell is the transaction's commit point and fate oracle.
- **`write`** is the commit marker: a record at `commit_ts` that says "the committed value for this cell is the `data` entry at `start_ts`." A read at snapshot `ts` scans the `write` column for the newest commit marker at or below `ts`, then fetches the corresponding `data` version. Uncommitted data (a `data` entry whose `lock` still exists) is invisible to snapshot reads — this is how snapshot isolation falls out of the representation.

Because Bigtable rows are singly-ordered by key and each row mutation is atomic, Percolator gets *per-cell* atomicity for free; everything else is protocol on top.

## Timestamps from a Single Oracle

Every transaction gets two timestamps: `start_ts` (begin) and `commit_ts` (commit), handed out by a **timestamp oracle** — a single process that dispenses monotonically increasing values. The oracle is deliberately trivial: it keeps the next number in memory and, to amortize RPC cost, **hands out timestamps in batches of roughly ten** to each client. A busy oracle serves millions of transactions per second precisely because it does almost nothing; and since reads never need the oracle (snapshot reads use `start_ts` the client already has), the oracle is not on the read path at all.

## The Two-Phase Commit Protocol

Percolator transactions are snapshot isolation with a two-phase commit executed *by the client library*, cell by cell:

```python
# Percolator commit protocol (Peng & Dabek, OSDI 2010), essential form.
# kv is a versioned store:  data[cell][start_ts] = value
#                           lock[cell][start_ts] = {...}
#                           write[cell][commit_ts] = start_ts

def prewrite(kv, txn, start_ts, writes, primary_cell):
    """Phase 1: lock every cell; writes buffered under start_ts."""
    for cell, value in writes.items():
        row = kv.row(cell)
        if row.has_write_after(start_ts) or row.locked():
            return False                      # write-write conflict: abort
        kv.put_data(cell, start_ts, value)
        kv.put_lock(cell, start_ts,
                    {"primary": primary_cell,
                     "is_primary": cell == primary_cell})
    return True

def commit(kv, start_ts, writes, primary_cell):
    """Phase 2: mark primary committed, then secondaries."""
    if kv.commit(primary_cell, start_ts):     # THE commit point
        for cell in writes:
            if cell != primary_cell:
                kv.commit_secondary(cell, start_ts)
        return True
    return False

def get(kv, cell, snapshot_ts):
    """Snapshot read: find newest commit <= snapshot_ts, check locks."""
    marker = kv.latest_write_at_or_before(cell, snapshot_ts)
    if marker is None:
        return None
    if kv.lock_exists_between(cell, marker.start_ts, snapshot_ts):
        return handle_stale_lock(kv, cell, snapshot_ts)   # see below
    return kv.get_data(cell, marker.start_ts)
```

The subtle parts are the ordering rules that make the protocol crash-safe:

- **The primary lock is chosen among the cells the transaction writes** (the first-written one). Commit writes the primary's `write` marker *first*. That single record is the atomic commit point: a transaction is committed if and only if its primary's write record exists.
- Secondaries are marked afterwards; if the coordinator dies midway, some secondaries stay locked forever *until something cleans them up* — and the protocol guarantees that "something" can always determine the transaction's fate by looking at the primary.

### Lazy Cleanup: Why Latency Tolerance Buys Simplicity

When a reader hits a stale lock, it must decide: committed, or abandoned? The rule:

```python
def handle_stale_lock(kv, cell, snapshot_ts):
    """Another transaction's lock blocks our read. Resolve its fate."""
    lock = kv.get_lock(cell)
    locked_ts = lock["start_ts"]              # the blocker's start_ts
    primary = lock["primary"]
    if not kv.lock_exists(primary):           # primary already decided
        kv.commit_secondary(cell, locked_ts)  #   -> roll secondary FORWARD
    elif kv.write_exists(primary):            # primary committed:
        kv.commit_secondary(cell, locked_ts)  #   same rollforward
    else:
        # primary still locked: coordinator's fate unknown.
        # Elect a cleanup performer (via a distributed lock service on the
        # primary cell), then roll the whole transaction BACK.
        with distributed_lock(primary):
            kv.rollback(primary)
            kv.rollback_secondary(cell, locked_ts)
    return get(kv, cell, snapshot_ts)
```

If the primary is committed (or clearly rolled back), the stale secondary lock is resolved immediately — *by the bystander transaction itself*, not by a dedicated cleanup service. If the primary is still locked, the transaction's coordinator might be alive and mid-commit, so the reader backs off and retries rather than guessing. In a latency-sensitive system this "wait on a possibly-dead coordinator" rule would be unacceptable; in an index pipeline it is a non-event. Cleanup work is spread across whichever transactions happen to collide with the stale locks — an elegant, if famous, consequence of designing for throughput.

## The Observer Model: Incremental Pipelines

Transactions can mark cells with a **notify**. Percolator workers continuously scan for notified cells and run registered **observers** — small pieces of code that execute like MapReduce tasks (workers coordinate through a Chubby-based lock service to spread cells across machines). Observers fire *at least once* per notification and may run *concurrently* for the same cell under different transactions, so observers must be idempotent and tolerate races ("weak iterations" in the paper's terms).

This inverts the MapReduce pipeline: instead of "crawl batch → rank batch → index batch," each stage is a reaction to the previous stage's *cell-level* changes, and only changed documents ever flow. The end-to-end effect the paper reports: Percolator's raw write throughput was roughly half of the MapReduce pipeline it replaced, but documents appeared in the index *days sooner* — the median time for a changed page to become searchable dropped from the batch cadence (many hours to days) to minutes-to-hours, a 50%+ improvement in average time-to-index.

## Where Percolator Sits in the Lineage

| System | Consistency | Cross-row atomicity | Notes |
|---|---|---|---|
| Bigtable | eventual (async replication) | single row | storage substrate for Percolator |
| Percolator | snapshot isolation | yes, via client 2PC + primary/secondary locks | throughput-first; lazy cleanup |
| Megastore | serializable per entity group | per entity group | sync Paxos replication, interactive workloads |
| Spanner | external consistency | yes, via 2PC over Paxos groups + TrueTime | latency paid for global ordering |

Percolator's protocol outlived the original system. **TiKV/TiDB** implement a percolator-style transaction model (primary/secondary locks, TSO timestamps from a Placement Driver, async-secondary cleanup) as their default transaction engine. **Apache Omid** provides snapshot-isolation transactions on HBase using the same primary-lock trick (Percolator's design directly influenced it), and Google Cloud Bigtable still ships only single-row transactions — the gap Percolator originally filled — which is why HBase ecosystem transaction layers remain popular.

## Interview Angles

- **Why is a single timestamp oracle not a bottleneck?** It holds one integer in memory and batches ~10 timestamps per RPC; reads never touch it. Contrast with Spanner, which uses TrueTime *precisely because* a single oracle does not span datacenters.
- **What exactly makes the protocol crash-tolerant with no cleanup service?** The primary lock/commit record encodes the transaction's fate; any later transaction that collides with a stale lock can resolve it (rollforward if primary decided, rollback after taking a cleanup lease if undecided).
- **What isolation level does Percolator provide and what anomalies remain?** Snapshot isolation: write-write conflicts abort via first-committer-wins; read-only snapshots are consistent; write-skew is possible (see the isolation-levels chapter for a concrete write-skew trace).
- **Why would you NOT build an OLTP payments system on Percolator?** Latency is unbounded (lock waits, backoff, lazy cleanup), conflicts collapse throughput, and snapshot isolation is weaker than what financial ledgers usually require — hence the Spanner/F1 line of design.
- **Implement `get()` correctly:** expect you to check the `write` column for the newest marker at/below the snapshot, then consult the `lock` column for staleness *between* the data version and the snapshot — the classic whiteboard exercise from this paper.

## References

- [Peng & Dabek, "Large-scale Incremental Processing Using Distributed Transactions and Notifications", OSDI 2010](https://www.usenix.org/legacy/event/osdi10/tech/full_papers/Peng.pdf)
- [Percolator paper page — Google Research](https://research.google/pubs/large-scale-incremental-processing-using-distributed-transactions-and-notifications)
- [Chang et al., "Bigtable: A Distributed Storage System for Structured Data", OSDI 2006](https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf)
- [Apache Omid — transactional layer for HBase (Percolator-influenced)](https://omid.apache.org/)
