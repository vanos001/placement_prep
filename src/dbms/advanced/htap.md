# HTAP: Hybrid Transactional/Analytical Processing Architectures

HTAP (the label Gartner applied to platforms serving transactional and analytical workloads together) is usually presented as a product category. For interview purposes it is better understood as one engineering question with three sub-decisions. Transactions want narrow, fresh, point-fast access: B-tree or LSM row storage, short lock hold times, tight tail latency. Analytics want wide, compressed, scan-fast access: a columnar layout, vectorized or MPP execution, large sequential reads. Serving both from one platform forces every system to answer three things:

1. **Where does the second representation live?** In the same storage engine, the same process, a replica node, or a separate system entirely?
2. **How do writes propagate to it?** Through shared in-engine structures, the commit log (consensus or redo), or an external CDC pipeline?
3. **What do analytical readers see?** The same snapshot as OLTP, a lagged-but-consistent snapshot, or whatever the last applied/merged batch produced?

The four architectures below are just the combinations of those answers. The [TiDB internals page](./tidb-internals.md) covers one family member (TiFlash) in depth; this page is the survey and the tradeoff map. Columnar layout mechanics themselves are assumed from [column stores](../storage/column-stores.md).

## The Spectrum

```text
      coupled <----------------------------------------------> decoupled
  +----------------+  +------------------+  +----------------+  +------------------+
  | unified engine |  | in-process dual  |  | consensus      |  | CDC pipeline     |
  | (one store,    |  | copy (row store  |  | replica        |  | into a separate  |
  |  two paths)    |  |  + columnar copy)|  | (TiFlash)      |  | columnar store   |
  +----------------+  +------------------+  +----------------+  +------------------+
   SingleStore         Oracle In-Memory,     TiDB + TiFlash     OLTP -> Flink CDC
   universal storage   SQL Server + CCI                         -> StarRocks

   freshness:  always current   high (apply lag)   ~learner lag    L + refresh R
   isolation:  weakest          weak (shared RAM)  strong (nodes)  strongest
```

| Architecture | Propagation | Analytical freshness | Workload isolation | Documented examples |
|---|---|---|---|---|
| Unified engine | internal structures | current (same store) | weakest, shared engine | SingleStore universal storage, SQL Server CCI |
| In-process dual copy | redo apply | seconds, snapshot-consistent | weak-medium, shared memory/CPU | Oracle In-Memory, SQL Server nonclustered CCI |
| Consensus learner replica | Raft log apply | learner apply lag | strong, separate nodes | TiDB + TiFlash |
| External CDC pipeline | log -> Kafka -> load | L + refresh R | strongest, separate cluster | Flink CDC into StarRocks |

## 1. Replication-Based: Row Primary, Columnar Learner

TiDB is the canonical open example. Each TiFlash node joins every region's Raft group as a **learner**: it receives log entries but never votes, so its lag can never delay an OLTP commit. Analytical reads are served as consistent snapshots, but only as fresh as the learner's applied log index, and the planner routes each query to TiKV or TiFlash by cost. The DeltaTree storage, delta-merge compaction, and MPP execution layer are covered on [TiDB internals](./tidb-internals.md); the design point to remember here is that *replication is the propagation mechanism*, which buys snapshot consistency across both representations without an external pipeline.

The learner (not follower) choice is the interview-grade detail: a follower that lags can break quorum under load; a learner cannot. The cost is duplicated storage and an apply pipeline that must keep up with the OLTP write rate.

## 2. Unified Engines: One Store, Two Access Paths

These systems keep one logical table and maintain both access paths inside the engine, so no propagation protocol exists to fail.

- **SingleStore universal storage** is a columnstore-first design that the vendor documents as the evolution of its columnstore to support transactional workloads. Recent writes land in an in-memory rowstore-backed segment; background flush converts them into columnstore blobs plus column group index blobs. Column group indexes restore fast point lookups and full-row locking over the columnar data, and the docs argue this is easier to manage than moving data between separate rowstore and columnstore tables. This is HTAP by *unifying the write path* rather than replicating it.
- **SQL Server** documents two patterns. A nonclustered columnstore index over a rowstore table is what Microsoft calls "real-time operational analytics": OLTP keeps using the underlying clustered B-tree while analytics scan the columnar index. A clustered columnstore index instead stores new and updated rows in a deltastore (a clustered B-tree holding rows until the ~102,400-row compression threshold), and a background tuple mover compresses them. The memory-optimized Hekaton engine (SIGMOD 2013) is a separate OLTP engine that can be combined with columnstore; it is not itself a columnar hybrid.
- **Oracle Database In-Memory** keeps rows in row format on disk and maintains a compressed columnar copy of chosen tables inside the In-Memory column store in the SGA. One instance, two representations, populated and evicted per the 19c guide's population and automatic-management controls.

The unified-engine tradeoff is isolation: both workloads share the same memory, CPU, and compaction budget, so a big scan or a background flush can move OLTP tail latency.

## 3. Log-Based CDC Into a Columnar Store

The most decoupled option ships the OLTP log outward: binlog or WAL -> CDC capture (Debezium, Flink CDC) -> Kafka -> streaming load into a columnar warehouse. StarRocks documents exactly this path: its **Primary Key table** applies CDC upserts with a Delete+Insert strategy backed by a primary key index and DelVector, so only the latest version is read at query time (the vendor claims 3-10x better query performance than a merge-on-read Unique Key table). The Flink CDC pipeline connector is the documented bridge from MySQL/Postgres binlogs into those tables.

Two properties distinguish this from TiFlash even though both consume "the log":

- There is no shared snapshot timestamp, so analytical queries see the store as of the last applied batch. Total staleness is CDC apply lag **L** plus the load/refresh cadence **R** (modeled below).
- Every pipeline hazard becomes your problem: schema drift, out-of-order events, exactly-once application (see [outbox/CDC patterns](../../backend/patterns/cdc-outbox.md)), and backfill after downtime.

The payoff is total isolation and the freedom to transform on the way (joins, partial updates, denormalized serving tables).

## 4. The Lakehouse End of the Spectrum

Push the same idea further - CDC or batch ELT into open table formats - and freshness degrades to minutes or hours while scan economics and storage cost improve. [Lakehouses](../../data-engineering/lakehouses.md) sit at the extreme right of the spectrum above; they are the right answer when freshness is genuinely not required, and the wrong answer when a dashboard promises "real time".

## Freshness vs Isolation: A Staleness Model

What does the refresh interval R actually buy and cost? This is a **model, not a benchmark**: CDC apply lag L, periodic refresh R, and a freshness SLO (query must see data at most X seconds old for 95% of queries). A query issued at time t reads the newest completed refresh cycle, so its staleness is uniform on [L, L+R), giving the closed form below; a seeded simulation cross-checks it.

```python
# MODEL, not a benchmark. Staleness of a CDC-fed columnar store.
#
# Pipeline: OLTP commit -> CDC capture/apply lag L -> columnar store that
# refreshes (makes applied data visible to queries) every R seconds.
#
# A query issued at time t reads the newest completed refresh cycle:
#   snapshot taken at k*R (k = floor(t/R)) carries rows committed by
#   k*R - L (apply lag L means later rows have not landed yet).
#   staleness(t) = t - (k*R - L) = (t - kR) + L,  uniform on [L, L+R).
#
# Closed form for "fraction of queries seeing data older than X seconds":
#   stale_frac(R) = max(0, 1 - (X - L)/R)   for X > L;  1.0 for X <= L.
#
# Fixed per-refresh cost (metadata bumps, small-batch write amplification,
# query-side re-merge of tiny deltas) amortizes as 3600/R refreshes/hour.

import random

L = 2.0          # CDC capture + apply lag (seconds), model constant
X = 10.0         # freshness SLO: query must see data at most 10 s old
TARGET = 0.05    # ...for at least 95% of queries (stale_frac <= 0.05)
N = 200_000      # simulated query instants
HORIZON = 10_000.0  # seconds of simulated wall clock

random.seed(7)

def analytic_stale_frac(R):
    if X <= L:
        return 1.0
    return max(0.0, 1.0 - (X - L) / R)

def simulated_stale_frac(R):
    stale = 0
    for _ in range(N):
        t = random.random() * HORIZON
        staleness = (t - (t // R) * R) + L
        if staleness > X:
            stale += 1
    return stale / N

print(f"Model: CDC apply lag L={L:g}s, SLO staleness X={X:g}s, "
      f"fresh-at-least {(1-TARGET)*100:g}% of queries")
print("  R(s)  analytic%  simulated%  refreshes/h")
for R in (1, 2, 4, 6, 8, 12, 16, 30, 60):
    a = analytic_stale_frac(R) * 100
    s = simulated_stale_frac(R) * 100
    print(f"{R:>5}  {a:>9.2f}  {s:>10.2f}  {3600/R:>10.0f}")

# Operating point: largest refresh interval still meeting the SLO.
# stale_frac grows monotonically with R, and fewer refreshes/hour means
# the fixed per-refresh cost is amortized best at the SLO boundary.
best = None
for R in [x / 100 for x in range(100, 6001)]:
    if analytic_stale_frac(R) <= TARGET:
        best = R
print(f"Picked operating point: R = {best:g}s (largest interval meeting SLO)")
print(f"  analytic stale frac = {analytic_stale_frac(best)*100:.2f}% "
      f"(<={TARGET*100:g}%), refreshes/h = {3600/best:.0f}")
print("  Note: fixed per-refresh cost amortizes as R grows, so run at the")
print("  largest SLO-compliant R, minus margin for refresh-duration jitter")
print("  and compaction stalls (a 1s stall doubles effective staleness here).")
```

Running it prints (real output):

```text
Model: CDC apply lag L=2s, SLO staleness X=10s, fresh-at-least 95% of queries
  R(s)  analytic%  simulated%  refreshes/h
    1       0.00        0.00        3600
    2       0.00        0.00        1800
    4       0.00        0.00         900
    6       0.00        0.00         600
    8       0.00        0.00         450
   12      33.33       33.15         300
   16      50.00       49.95         225
   30      73.33       73.27         120
   60      86.67       86.62          60
Picked operating point: R = 8.42s (largest interval meeting SLO)
  analytic stale frac = 4.99% (<=5%), refreshes/h = 428
  Note: fixed per-refresh cost amortizes as R grows, so run at the
  largest SLO-compliant R, minus margin for refresh-duration jitter
  and compaction stalls (a 1s stall doubles effective staleness here).
```

Read the table as a phase transition: below R = 8s the SLO is met with headroom; the moment R crosses (X - L)/0.95 ~ 8.4s, a third of queries at R = 12s see data past the SLO. The general interview answer: **freshness in a decoupled HTAP system is a bulkhead you size, not a property you inherit** - and the same SLO sizing decides whether you need a learner replica (sub-second) at all.

## Interference: Compaction, Delta Merges, and Resource Groups

Isolation is not only about nodes; background work in the analytical representation is the usual violator.

- **Compaction/delta-merge I/O.** Every columnar ingest path accumulates small files or delta records that background processes merge. TiFlash exposes `storage.io_rate_limit` (added in v5.2.0) to cap total background disk I/O because delta merges otherwise compete with OLTP on shared disks. SQL Server's tuple mover and SingleStore's background flush are the same story in-process.
- **Small-batch write amplification.** A CDC pipeline that commits every transaction as its own load round creates pathological segment counts; batching (part of R above) is a deliberate trade of freshness for compaction health.
- **Resource groups are the practical isolation tool.** StarRocks resource groups classify queries (by user, role, or workload type) and enforce CPU hard limits, memory limits, big-query kill limits, and queues - so a rogue scan dies instead of starving a dashboard. TiDB Resource Control performs the equivalent role inside TiDB with per-group Request Unit (RU) quotas. Expect a follow-up question: "how do you stop analytics from hurting OLTP?" - the strong answer names the isolation mechanism of your architecture, not "more hardware".

## Adaptive Storage: Heat-Based Row-to-Column Migration

If hot rows want row format and cold rows want columnar, the engine could migrate data by temperature. Reality is mostly manual or write-path-driven:

- SingleStore's universal storage bakes migration into the write path (in-memory segment -> columnstore blobs on flush), which is heat migration in miniature: recent = row-backed, aged = columnar.
- Oracle documents In-Memory population and automatic-management controls that decide *what is columnar in RAM* by access patterns, though the disk format stays row-based.
- SQL Server requires an explicit index DDL decision; no mainstream engine fully automates row-to-column migration by measured temperature across disk formats. Treat "we automatically tier rows to columnstore by heat" in an interview answer as a claim to challenge.

## Choosing: Workload-to-Architecture Decision Table

| If your workload needs... | Then pick... | Why | Watch out for |
|---|---|---|---|
| Analytics over data < 1s old, on the same cluster | Learner replica (TiDB/TiFlash style) | snapshot-consistent, no external pipeline | double storage; apply lag under write bursts |
| OLTP plus moderate aggregates, one product, one team | Unified engine (SingleStore, SQL Server CCI) | no propagation to fail; single security/ops surface | shared CPU/RAM; OLTP tail latency under scans |
| OLTP stays on proven Postgres/MySQL; BI needs 1-5 min data | CDC pipeline into columnar (StarRocks PK tables) | total isolation; transform in flight | schema drift, exactly-once apply, backfills |
| Freshness in minutes-hours, huge scans, cheap storage | Lakehouse ELT | best scan economics, open formats | not HTAP; SLO math above will fail |
| Analytics must never touch OLTP nodes (compliance/noisy neighbor) | CDC or separate replica, never in-process | physical isolation only | higher TCO; two engines to operate |

## How HTAP Designs Fail

- Cost-based routing flips queries to the columnar replica just after a write burst, right when learner lag is worst - the fallback row path then melts under analytical load.
- CDC pipelines silently skew: one wide-table backfill delays every topic sharing the pipeline, and staleness jumps from seconds to hours.
- Deltastores/delta trees that never compact (thresholds mis-tuned for the actual batch sizes) degrade analytical latency gradually until the tuple mover or delta merge is the top consumer of I/O.
- Resource groups configured with soft limits only - classification exists, but nothing kills the query that breaches it.
- Dual-format cost surprise: a 300-column table's columnar copy plus secondary indexes can exceed the row storage it mirrors; per-table population decisions exist in every product for a reason.
- The interview trap: describing HTAP as "a columnar index on my OLTP database" without saying how writes propagate or what readers see. Walk the three questions from the top of this page instead.

## References

1. PingCAP, "TiFlash Overview" (TiDB docs) - https://docs.pingcap.com/tidb/stable/tiflash-overview (probed 200)
2. PingCAP, "TiDB Resource Control" (TiDB docs) - https://docs.pingcap.com/tidb/stable/tidb-resource-control (probed 200)
3. Huang, D. et al., "TiDB: A Raft-based HTAP Database", PVLDB 13(12), 2020 - https://www.vldb.org/pvldb/vol13/p3072-huang.pdf (probed 200)
4. SingleStore, "Universal Storage" (docs) - https://docs.singlestore.com/cloud/create-a-database/columnstore/universal-storage (probed 200)
5. SingleStore, "How the Columnstore Works" (docs, v9.1) - https://docs.singlestore.com/db/v9.1/create-a-database/columnstore/how-the-columnstore-works (probed 200)
6. StarRocks, "Primary Key table" (docs; Delete+Insert strategy, Flink CDC sync guidance) - https://docs.starrocks.io/docs/table_design/table_types/primary_key_table (probed 200)
7. Apache Flink CDC, "StarRocks pipeline connector" (stable docs) - https://nightlies.apache.org/flink/flink-cdc-docs-stable/docs/connectors/pipeline-connectors/starrocks (probed 200)
8. StarRocks, "Resource group" (docs) - https://docs.starrocks.io/docs/administration/management/resource_management/resource_group (probed 200)
9. Zhang, C., Li, G., Zhang, J., Zhang, X., Feng, J., "HTAP Databases: A Survey", arXiv:2404.15670, 2024 (authors/date verified via arXiv metadata; a version appears in the VLDB Journal, doi 10.1007/s00778-024-00858-9, probed 200) - https://arxiv.org/abs/2404.15670
10. Microsoft, "Columnstore indexes: Overview" (SQL Server docs; real-time operational analytics, deltastore mechanics) - https://learn.microsoft.com/en-us/sql/relational-databases/indexes/columnstore-indexes-overview (probed 200)
11. Oracle, "Database In-Memory Guide 19c" (E96137-12, Feb 2024) - https://docs.oracle.com/en/database/oracle/oracle-database/19/inmem/index.html (probed 200)
12. Diaconu, C. et al., "Hekaton: SQL server's memory-optimized OLTP engine", SIGMOD 2013, doi 10.1145/2463676.2463710 (dl.acm.org returns 403 to curl; bibliographic details verified via search, e.g. the Microsoft Research publication page)
