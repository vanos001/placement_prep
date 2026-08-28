# Time-Series Database Internals

The [temporal/streaming chapter](temporal-streaming.md) covers the time-series data-model landscape and the Gorilla compression math. This page goes one layer down: what a TSDB engine does between accepting a write and serving a query - ingestion path, series indexes, cardinality limits, retention/downsampling enforcement, compaction, tombstones, and the distributed layer. Anchors: InfluxDB (TSM engine + TSI), Prometheus TSDB, VictoriaMetrics, Monarch (Google).

## What the Engine Optimizes For

- Writes are append-mostly and ~monotonic per series: no per-point B-tree updates, deltas compress, immutable files win.
- Queries scan time ranges across *many* series: data laid out per-series in time order, so a time predicate prunes files.
- Recency dominates reads: hot window in memory, cold data becomes read-only blocks.
- Deletes/corrections are rare: tombstone + lazy purge at compaction, never in-place updates.

## The Ingestion Path: WAL, Memtable, Immutable Files

### InfluxDB: the TSM engine

InfluxDB's v1 storage engine centers on **TSM (Time-Structured Merge tree)** files, an LSM-family design tuned for time-ordered blocks. The documented write path:

```text
          InfluxDB v1 ingestion path (one shard = one time range + RP)
  point(tagset, field, ts)
     |
     v
  +---------+     +---------------+  snapshot trigger: cache size, timer,
  |   WAL   | --> |  Cache (RAM)  |  cold duration
  | snappy, |     | read cache +  | -------------------+
  | fsync'd |     | write buffer  |                    v
  +---------+     +---------------+  +--------------------------+
                                      | TSM file (immutable)     |
                                      |  [t+values blocks][index]|
                                      +--------------------------+
                                        Compactor -> level 1,2,3, full
```

1. **WAL first.** Each point is snappy-compressed, appended to the write-ahead log, and fsynced before the write is acknowledged; a crash replays the WAL to rebuild the cache.
2. **Cache.** The in-memory cache holds recent points keyed by series and field; reads merge it with on-disk TSM blocks.
3. **Snapshot.** Crossing the cache threshold (or a timer) sorts, batches, and compresses points into immutable TSM files: compressed blocks per (series key, field), plus an index mapping series keys and timestamps to block offsets.
4. **Compactor.** Merges TSM files through levels 1-3, then a "full" compaction that also re-optimizes the index.

### Prometheus TSDB: head block and WAL

Prometheus splits differently but analogously: the **head block** holds recent samples in in-memory chunks backed by a **WAL** for crash recovery, and every ~2 hours the head is cut into an immutable on-disk **block** (chunks + index + metadata). One refinement from the head-chunks design doc: full head chunks are spilled to **memory-mapped files** early, so a crash replays only the WAL tail instead of reconstructing hours of chunk data.

| Aspect | InfluxDB (TSM) | Prometheus TSDB |
|---|---|---|
| In-memory stage | Cache (TSM-shaped memtable) | Head block (chunks + m-map spill) |
| Durability | WAL, fsync per write | WAL + checkpoint; m-map chunks |
| Immutable unit | TSM file inside a shard | 2h block directory |
| Compaction | Levels 1-3 + full, per shard | Vertical/horizontal block merges |

(For the general LSM/WAL mechanics both inherit, see [WAL Internals](wal-internals.md) and [LSM Compaction](../internals/compaction.md).)

## Series Indexes: Tag Sets, Inverted Indexes, TSI

A series key is the measurement plus its full tag set; the classic TSDB index is an **inverted index** mapping each tag term to the set of series IDs carrying it:

```text
  http_requests_total,host=web-17,service=checkout,method=POST  -> series id S
```

A query intersects the posting sets of its matchers, then fetches only surviving series' samples in the requested range:

```text
  matchers: {service="checkout", method="POST", status="500"}
    service=checkout  -> postings [1, 4, 9, 11, 17]
    method=POST       -> postings [4, 9, 11, 23]
    status=500        -> postings [4, 11, 23]
    INTERSECT         -> [4, 11]   then time-range fetch for series 4 and 11
```

### The in-memory index cliff, and TSI

InfluxDB v1 originally kept this index as hash maps **in memory, per shard**, so memory scaled with *series per shard* - which is why the cardinality cliff below manifests first as OOM, not slow queries. **TSI (Time Series Index)**, introduced in InfluxDB v1.3, moves the index on-disk as its own merge-tree structure compacted like data: memory stays roughly flat as series grow; the cost moves to disk and query latency. Prometheus resolves matchers through per-block **postings lists** (sorted series IDs) with set operations; VictoriaMetrics merges its inverted index into the data parts themselves, avoiding a separate index-to-data lookup round trip.

## Value Compression: Cross-Link, Not Re-Derivation

Gorilla's delta-of-delta timestamp encoding and XOR float encoding - the worked bit layouts and the ~1.4 bytes/sample result - are derived in [Temporal Databases, Streaming & Time-Series](temporal-streaming.md). The internals-level point is the structural precondition: per-series contiguity plus time ordering make deltas tiny, which is why both engines compress *inside immutable per-series blocks* rather than compressing a row store. Practical storage budgets use ~1.5-2 bytes/sample for steady metrics, which the model below uses.

## Cardinality: The Product Rule That Kills TSDBs

Series cardinality is **the product of distinct tag-value counts across tag keys** - not the sum. One added tag key multiplies series count by its distinct-value count:

```text
  cardinality = |host| x |service| x |handler| x |method| x |code| x ...
```

This is the number-one TSDB outage cause in practice: one seemingly innocent tag (an HTTP path, a pod name, a customer ID) turns a 50k-series system into a 50M-series system, and RAM indexes, WAL replay, snapshot storms, and query planning degrade together. The operational playbook (which tags to forbid, cardinality alerting) lives in [Metrics Cardinality](../../sre/metrics-cardinality.md); the calculation itself:

```python
"""Tag-cardinality explosion calculator + retention/rollup storage model.
Part 1: cardinality = product of distinct tag-value counts (the product rule).
Part 2: storage footprint of a retention + downsampling policy chain."""
def series_count(card):
    n = 1
    for v in card.values():
        n *= v
    return n

def storage_model(active, bps=1.5):
    """Tiers: raw 15s kept 15d; 1m rollup (3 aggregates) 90d; 5m rollup (3) 400d."""
    tiers = [("raw 15s", 86400 // 15, 1, 15),   # samples/day, aggregates, days
             ("1m rollup", 86400 // 60, 3, 90),
             ("5m rollup", 86400 // 300, 3, 400)]
    total, rows = 0.0, []
    for name, spd, aggs, days in tiers:
        per_day = active * spd * aggs * bps
        tier_tb = (per_day * days) / 2**30 / 1024
        total += tier_tb
        rows.append((name, spd * aggs, days, per_day / 2**20, tier_tb))
    return rows, total

base = {"host": 2000, "service": 80, "handler": 40, "method": 5, "code": 40}
scenarios = [("naive: all five tag keys", base),
             ("drop code (bucket to 5xx only)", {**base, "code": 4}),
             ("drop code + handler -> 8 route classes",
              {"host": 2000, "service": 80, "route_class": 8, "method": 5})]
print("PART 1: series cardinality for http_requests_total")
for label, card in scenarios:
    print(f"  {label:42s} -> {series_count(card):>12,d} series")
full = series_count(base)
print(f"  one extra tag key with 10 values on the naive set: x10 -> {full*10:,d} series")
active = series_count(scenarios[2][1])

print(f"\nPART 2: storage model at {active:,d} active series, 1.5 B/sample")
print(f"  {'tier':<10} {'samp/d/series':>13} {'keep':>6} {'MiB/day':>10} {'TB total':>9}")
rows, total = storage_model(active)
for name, spd, days, mib, tb in rows:
    print(f"  {name:<10} {spd:>13,d} {days:>5}d {mib:>10.1f} {tb:>9.2f}")
print(f"  {'TOTAL':<10} {'':>13} {'':>6} {'':>10} {total:>9.2f}")
_, total10 = storage_model(active * 10)
print(f"  with one 10-value tag added (10x cardinality): TOTAL {total10:.2f} TB")
```

Real output of the script above:

```text
PART 1: series cardinality for http_requests_total
  naive: all five tag keys                   -> 1,280,000,000 series
  drop code (bucket to 5xx only)             ->  128,000,000 series
  drop code + handler -> 8 route classes     ->    6,400,000 series
  one extra tag key with 10 values on the naive set: x10 -> 12,800,000,000 series

PART 2: storage model at 6,400,000 active series, 1.5 B/sample
  tier       samp/d/series   keep    MiB/day  TB total
  raw 15s            5,760    15d    52734.4      0.75
  1m rollup          4,320    90d    39550.8      3.39
  5m rollup            864   400d     7910.2      3.02
  TOTAL                                           7.17
  with one 10-value tag added (10x cardinality): TOTAL 71.67 TB
```

Two lessons hide in those numbers. First, cardinality mitigation is multiplicative: bucketing `handler` from 40 route paths to 8 route classes and collapsing `code` from 40 values to 4 cut 1.28B series to 6.4M - a 200x reduction from two decisions. Second, rollup tiers dominate total storage (raw 15s retention holds only 0.75 TB of 7.17 TB) because aggregates are samples too - a 1m rollup storing avg/min/max costs 3 samples per bucket, nearly the raw ingestion rate, retained 6x longer. Storing count+sum (2 values) and deriving the average halves rollup cost while keeping most dashboards correct.

## Retention and Downsampling: Drop vs. Rollup

Different policies with different enforcement mechanics:

| Policy | What it does | InfluxDB | Prometheus | VictoriaMetrics |
|---|---|---|---|---|
| Retention (drop) | Deletes data past an age | Retention policy; shards dropped whole per shard-group duration | Blocks deleted once `maxTime < now - retention` | Per-metric retention filters at part level |
| Downsampling (rollup) | Writes new, coarser aggregated series | Continuous queries (v1) / tasks (v2+) | Recording rules; tiered downsampling via Thanos/Cortex compactor | Enterprise downsampling; community rollup via recording rules |

Enforcement details: InfluxDB retention is **shard-granular** - a shard group covers one time window (e.g. a day), so data drops a shard group at a time; 15.5 days is not expressible with 1-day shard groups. Prometheus deletion is **block-granular plus tombstones** - blocks outside retention are unlinked, while deleting individual series inside retained blocks goes through tombstones. Rollups are *written as new series*, not views over raw data: that is why they survive raw-data expiry, and why their own cardinality must be managed identically.

## Compaction and Tombstones: Rewriting History

**TSM compaction** (InfluxDB) runs per shard through levels 1, 2, 3, and full: re-reading smaller TSM files, writing larger blocks (better compression, fewer index lookups), rebuilding indexes. Deletes never touch TSM files directly; they append **tombstone files** recording deleted series/fields/time ranges, which reads consult to skip data; only a full compaction physically purges tombstoned points.

**Prometheus compaction** merges adjacent 2h blocks into larger ones (2h x 3 => 6h, and so on) and rewrites chunks; series deletion writes **tombstones** alongside the block index, and queries subtract tombstoned intervals at read time until a later compaction materializes the deletion. Same lazy-delete contract as LSM systems: reads pay a tombstone tax, compaction eventually collects it (see [LSM Compaction](../internals/compaction.md)).

## The Distributed Layer: Meta Nodes, Shards, Cells

**InfluxDB Enterprise** shards by shard group (time + retention policy) across data nodes. Meta nodes run a Raft-consistent metastore (cluster membership, retention policies, shard-group ownership, continuous queries); data nodes own shards, replicate them per retention-policy replication factor, and receive fanned-out queries per shard group. Open-source InfluxDB is the same engine with one data node.

**Monarch** (Google, PVLDB 2020) trades differently: a *planet-scale, in-memory* TSDB. From the paper, qualitatively: a **universe of cells**, each cell an independent Monarch cluster in one location; tables partition into **row ranges**, each assigned to two cells in different clusters (**multi-homing**), so a datacenter failure shifts traffic to the surviving replica; data lives in server memory with durability from **asynchronous recovery logs** on local disks, favoring write availability over synchronous durability (monitoring tolerates losing the tail).

| Property | InfluxDB Enterprise | Monarch |
|---|---|---|
| Metadata consistency | Raft meta nodes | Per-cell metadata + global cell directory |
| Data placement | Shard groups on data nodes | Row ranges multi-homed across two cells |
| Storage medium | Disk TSM files | In-memory, async recovery logs |
| Durability stance | WAL fsync per write | Loss-of-tail tolerated for availability |

## Query Execution: Time First, Then Series

Two pushdowns dominate TSDB query planning. **Time predicate pushdown**: `WHERE time > now() - 6h` selects only shard groups (InfluxDB) or blocks whose `mint`/`maxt` overlap the range (Prometheus), plus the head for the newest ~2h; everything else on disk is never opened. Wide ranges stay expensive even with few series; narrow ranges stay cheap even with millions. **Series predicate pushdown**: matchers resolve through the inverted-index/postings intersection above; the engine fetches chunks only for surviving series, clipped to the requested interval.

**Last-N queries** get special treatment because naive execution would scan every block: InfluxDB's `last()` is served from the cache plus the newest TSM data per shard rather than a full-range scan, and Prometheus instant queries evaluate over a short lookback window (default 5m) instead of a chart's full range. Applications needing "current value of 1M series" must use these paths - a generic `ORDER BY time DESC LIMIT 1` scan over 90 days is a classic self-inflicted outage.

## Interview Angles

- **"Why not just Postgres for metrics?"** - Per-series B-tree indexes explode with cardinality; TSDBs replace per-row indexing with an inverted series index plus time-ordered compressed blocks, and drop/rollup policies are enforced at shard/block granularity rather than per-row.
- **"What breaks first at 50M series?"** - With an in-memory per-shard index, RAM (then WAL replay time and snapshot latency); with TSI-style on-disk indexes, query latency and compaction throughput. Either way the product rule means the fix is tag design, not hardware.
- **"Drop vs. rollup?"** - Drop reclaims storage but loses history; rollup preserves long-horizon trends but costs write amplification and its own cardinality; mature setups layer both (short raw retention + count/sum rollups).

## References

1. InfluxData, "InfluxDB Storage Engine" (TSM engine: WAL, cache, TSM files, compactor): <https://docs.influxdata.com/influxdb/v1/concepts/storage_engine/>
2. InfluxData, "Time Series Index (TSI)": <https://docs.influxdata.com/influxdb/v1/concepts/time-series-index/>
3. Adams, C. et al., "Monarch: Google's Planet-Scale In-Memory Time Series Database," PVLDB 13(12):3181-3194, 2020. DOI: <https://doi.org/10.14778/3181-3194>; PDF: <https://vldb.org/pvldb/vol13/p3181-adams.pdf>
4. Prometheus, "Storage" (blocks, head, WAL, compaction, retention): <https://prometheus.io/docs/prometheus/latest/storage/>
5. Prometheus TSDB, "Head chunks format" design doc: <https://github.com/prometheus/prometheus/blob/main/tsdb/docs/format/head_chunks.md>
6. Pelkonen, T. et al., "Gorilla: A Fast, Scalable, In-Memory Time Series Database," PVLDB 8(12):1816-1827, 2015. DOI: <https://doi.org/10.14778/2824032.2824078>
7. VictoriaMetrics documentation (architecture, index design): <https://docs.victoriametrics.com/>
