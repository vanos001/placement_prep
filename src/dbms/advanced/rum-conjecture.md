# The RUM Conjecture: Reads, Updates, and Memory in Access Methods

Every storage engine must decide how to organize records so they can be found again: that organization is the **access method** (B+trees, LSM-trees, hash indexes, zone maps, tries). Access methods keep *base data* (the records themselves) plus *auxiliary data* (index pages, filters, routing structures) whose only job is making future accesses cheaper. In 2016, Manos Athanassoulis, Michael Kester, and Lukas Maas compressed fifty years of access-method engineering into one page-sized claim — the **RUM conjecture** — published in *"Designing Access Methods: The RUM Conjecture"* at EDBT 2016 (a companion tutorial, *"Design Tradeoffs of Data Methods"*, appeared at SIGMOD 2016 the same year). This page states the conjecture formally, defines its three overheads, places B-trees and LSM-trees on the RUM triangle, tours the write-optimized middle ground (buffer trees, Bε-trees, fractal trees), reads the conjecture as a guaranteed-I/O planning tool, and runs a small amplification model over a synthetic mixed workload.

For the mechanics of the two dominant structures, read the sibling pages separately: [B-Trees](../indexing/btrees.md) covers B+tree internals (splits, fill factor, bulk load) and [LSM Compaction](../../storage/lsm-compaction.md) covers leveled/tiered merge policy. Here we care only about what each structure *costs*, not how it works inside.

## The three overheads, defined as amplification ratios

The conjecture is about **overheads**: the extra data movement and storage an access method adds beyond touching the base data. All three are ratios relative to the "perfect" structure that reads, writes, and stores exactly the base data and nothing else:

| Overhead | Amplification name | Ratio (per the EDBT paper) | Ratio of 1.0 means | Where engineers see it |
|---|---|---|---|---|
| RO (read) | read amplification | total data read (auxiliary + base) / data actually retrieved | every byte read is answer bytes | `io_stall`, cache misses per lookup, SSTable probes per `GET` |
| UO (update) | write amplification | physical bytes written / logical bytes updated | one byte to disk per byte changed | SSD wear, WAL volume, compaction bandwidth bills |
| MO (memory) | space amplification | space for auxiliary + base data / base data alone | no index or metadata at all | index-to-table size ratio, cache-resident metadata, RAM per GB stored |

The theoretical minimum of each overhead is 1.0. The paper's driving observation is that the three minima are mutually exclusive: each is achieved by a structure that is pathological on the others.

## The conjecture and its corollaries

The paper builds up to the conjecture through three thought experiments, each minimizing exactly one overhead with the simplest possible structure:

| Minimize | Structure achieving it | Forced consequence |
|---|---|---|
| RO = 1.0 | direct-address array (block `blkID = value`) | UO = 2.0 (old + new block on move); MO grows with the key domain |
| UO = 1.0 | append-only log | RO and MO grow without bound (everything is a scan) |
| MO = 1.0 | dense unsorted array (no auxiliary data) | RO = N (full scan); updates are in-place but reads pay everything |

Then the central claim, quoted from the paper: *"An access method that can set an upper bound for two out of the read, update, and memory overheads, also sets a lower bound for the third overhead."* Two corollaries matter in practice. First, optimizing one overhead to its minimum forces the other two to pathological values (the table above). Second — the useful engineering direction — picking the two upper bounds you can afford *determines* the floor on the third, whether you looked or not. The conjecture is stated about overheads (ratios), not latencies: a structure can still lose on both sides of a trade if its implementation is careless.

```text
                          Read-optimized corner
                          (hash, B-tree, trie,
                           skiplist, Bw-tree)
                                 /\
                                /  \
                               /    \
                    adaptive  /      \
              (cracking,     /        \   differential structures
               adaptive      /          \  (LSM, PBT, MaSM, PDT,
               merging)     /            \  B-epsilon, fractal)
                           /              \
                          /                \
                         /                  \
                        /                    \
                       /______________________\
              Space-optimized corner      Write-optimized corner
              (zone maps, sparse index,   (append-only log:
               bloom filters, bitmaps,     UO = 1, RO and MO
               compression)                unbounded)

        Every structure is a point; tunable structures sweep an area.
        Adapted from Figure 1 of the EDBT 2016 paper (ASCII redraw).
```

## B-tree vs LSM: the two shipping corners

Production engines live at two corners. The paper's Table 1 compares representative structures with I/O complexities (N tuples, block size B tuples, LSM size ratio T, partition size P):

| Access method | Point query | Range query (m tuples) | Insert/Update/Delete | Index size |
|---|---|---|---|---|
| B+-tree | O(log_B(N)) | O(log_B(N) + m) | O(log_B(N)) | O(N/B) |
| Hash index | O(1) | O(N/B) | O(1) | O(N/B) |
| ZoneMaps (sparse) | O(N/P/B) | O(N/P/B) | O(N/P/B) | O(1) |
| Leveled LSM | O(log_T(N/B) . log_B(N)) | O(log_T(N/B) . log_B(N) + T.m.T^-1) | O(T/B . log_T(N/B)) | N.T |

Reading this as a RUM balance sheet: the B+-tree buys logarithmic point *and* range reads with O(N/B) auxiliary space, and pays by rewriting whole pages in place on every update. The hash index gets constant point reads and constant updates but cannot answer ranges — a corner case the RUM frame makes obvious (point-read optimal, range-read pathological). ZoneMaps are nearly free in space (MO near 1.0) but barely help point lookups. The leveled LSM pushes update cost down by writing full sorted runs and merging them in the background; its index is larger (T overlapping runs) and its point reads are nominally worse, though bloom filters — a deliberate MO investment — collapse them in practice (the [Monkey line of work](https://dl.acm.org/doi/10.1145/3035918.3064054) sizes those filters per level to shave exactly this term). The Bw-tree and ART take yet another cut of the same triangle by softening the B-tree's update path with delta records; see [Bw-Tree and ART](./bwtree-art.md).

## The write-optimized middle: buffering structures

Between the two corners sits a family that all use one recipe — **buffer updates in small fast storage, flush them in bulk to slow storage** — differing only in where the buffer sits and how big the flush batch is:

```text
        B+tree node                    buffered (B-epsilon-style) node
      +-----------+                  +-----------------------------+
      | pivots    |                  | pivots (1/eps of node)      |
      | p1 | p2   |                  | p1 | p2                     |
      +-----+-----+                  +----------+------------------+
            |                        | buffer:  +----------------+
            v                        | (k1,v1) (k2,v2) (k3,v3) ... |
       sorted leaf                   | S = eps * B records, sorted |
                                     +-----------------------------+
                                              |
                                              v
                                         sorted leaf

  Updates land in the root buffer; when it fills, the batch is
  partitioned and pushed one level down in ONE bulk write per child.
  The bigger the buffer (eps), the cheaper each update and the more
  data a point query must inspect per level.
```

| Structure | Buffering granularity | Update cost model | Read path | Shipped in |
|---|---|---|---|---|
| Buffer tree (Arge, WADS 1995) | O(B) records per internal node, batched/offline | amortized near-constant I/O per record for huge batches | queries are batched, not interactive | research; batch algorithms (sorting, sweeping) |
| Bε-tree (Brodal & Fagerberg, 2003) | per-node buffer, ε tunes pivots-vs-buffer split | O(log_B(N)) height but each flush amortized over the batch | B+-tree descent plus per-level buffer search | TokuDB / PerconaFT ("fractal tree index"), Fatode |
| Fractal tree (Kuszmaul et al., commercialized 2007+) | Bε-tree with engineering tuning of ε per level | same family; marketed for 10-100x insert speedups | same as Bε | TokuDB, TokuMX (pre-WiredTiger MongoDB) |
| LSM-tree (O'Neil et al., 1996) | memory table, then immutable runs merged by level | O(T) per record per level chain | bloom filter + one run per level | RocksDB, Cassandra, HBase, WiredTiger (option) |

The buffer tree is the theoretical ancestor: it achieves optimal amortized bulk-update I/O but assumes batched queries, so it never shipped as an OLTP index. The Bε-tree generalizes the B-tree by adding per-node buffers and a knob ε: ε = 1 degenerates to a plain B-tree, growing ε shifts node budget from pivots to buffers, flattening the effective height (log_{B^ε}(N)) and amortizing each flush over B^ε messages. The LSM-tree can be read as the limiting case where the "tree" is nearly flat and buffers are whole levels — maximum batching, maximum background merge traffic.

## The guaranteed-I/O reading (GUI)

The conjecture's second half is a planning tool. Restated: if you *choose* upper bounds for any two overheads, the third gets a provable lower bound — a **guaranteed I/O floor** you can plan against. Engineering notes often gloss this corollary as the *GUI* (guaranteed I/O) reading of the conjecture; the mathematics is the conjecture's own corollary, not a separate result. Three worked readings, using the propositions above:

- Budget UO ≤ 1.0 (pure append) and MO is whatever it is: RO has no finite bound — you must accept scan-shaped reads or relax the write budget.
- Budget RO ≤ 2.0 pages per point query *and* MO ≤ 1.5x base data: you have pinned both reads and space, so some floor on UO is forced — expect page rewrites plus logging, i.e., B+-tree-shaped write amplification.
- Budget UO ≤ 5.0 *and* MO ≤ 1.2x: the write-optimized middle, at best, since the guaranteed RO floor is now logarithmic-but-not-constant — leveled LSMs and Bε-trees live exactly at this edge, and the bloom sweep below shows the residual freedom.

The practical use is capacity and SLO planning: before promising "p99 read latency under 5 ms and 10k writes/s on this SSD", enumerate which two overheads the design pins and compute the floor the conjecture guarantees on the third. If that floor already violates the SLO, no tuning will save the design — the constraint is structural, not parametric.

## A worked RUM-overhead model

The model below computes all three overheads for a B+tree, a leveled LSM, and a buffered Bε-style tree over the same synthetic workload (1M records of 100 B on 4 KiB pages). Every formula is an explicit model assumption: B+tree UO is one dirty-leaf rewrite plus WAL per update; leveled-LSM UO is one flush plus T rewrites per merge level with bloom-filter bits counted into MO; the buffered tree amortizes each update into per-level bulk flushes; warm-cache reads subtract two RAM-resident tree levels; bloom false-positive rate is the standard (0.6185)^bits. It then sweeps the bloom filter budget (an internal R-vs-M trade) and scans the read fraction to find which structure wins each workload mix:

```python
"""RUM-overhead model: B+tree vs leveled LSM vs buffered (B-epsilon-style) tree.

Closed-form I/O amplification ratios for one synthetic mixed workload.
Every formula is a stated model assumption, not a measurement.
"""
import math

# ---- shared workload / device parameters --------------------------------
N    = 1_000_000        # live records
REC  = 100              # record bytes = the answer to a point query
PAGE = 4096             # device block (page) bytes
B    = PAGE // REC      # records per 4 KiB block -> 40
F    = 40               # B+tree internal fanout (pivot keys per node)
FILL = 0.70             # B+tree leaf fill after random inserts
T    = 10               # leveled-LSM size ratio per level
BPB  = 10               # bloom-filter bits per key (one filter per level)
CACHED = 2              # tree levels that fit in RAM (warm-cache model)

levels_lsm = math.ceil(math.log(N / B, T)) + 1          # L0 .. L5
height     = math.ceil(math.log(N / B / FILL, F))       # B+tree height

def bloom_fp(bpb):
    """Best-case false-positive rate of a bloom filter: (0.6185)^b."""
    return 0.6185 ** bpb

def rum_table():
    rows = []
    # B+tree: cold point read = one block per level; range read walks the
    # leaf chain; UO = dirty-leaf rewrite + WAL (2 x 4 KiB per 100 B
    # logical update); MO = 70% leaf fill + F/(F-1) internal-page share.
    rows.append(("B+tree (fanout=%d)" % F, height,
                 height + 1,
                 2 * PAGE / REC,
                 (1 / FILL) * (F / (F - 1))))
    # Leveled LSM: point read = 1 block at the level that holds the key,
    # upper levels probed only on bloom false positives; range read must
    # merge one sorted run per level; UO = 1 flush + T rewrites per merge
    # level; MO = T/(T-1) overlap bound + per-level bloom bits.
    cold = 1 + (levels_lsm - 1) * bloom_fp(BPB)
    rows.append(("LSM leveled (T=%d)" % T, cold,
                 levels_lsm + 1,
                 T * (levels_lsm - 1) + 1,
                 T / (T - 1) + levels_lsm * BPB / (8 * REC)))
    # Buffered (B-epsilon-style): same shape as the B+tree, but internal
    # nodes carry a batch buffer of S = 5*B records; updates are flushed
    # in bulk once per level (h batched writes + 1 leaf insert); a point
    # read may touch one extra buffer block; buffers add eps/F to space.
    rows.append(("Buffered (eps=5)", height + 1,
                 height + 2,
                 height + 1,
                 1 + 5 / F))
    out = []
    for (name, rc, rr, uo, mo) in rows:
        if "LSM" in name:                      # flat structure: no tree
            warm, warmr = rc, rr               # levels to cache
        else:
            warm = max(1.0, rc - CACHED)
            warmr = max(1.0, rr - CACHED)
        out.append((name, rc, warm, warmr, uo, mo))
    return out

print("Assumptions: N=%d records, %d B/record, %d B page (B=%d rec/page)"
      % (N, REC, PAGE, B))
print("LSM levels L=%d, B+tree height=%d (fanout %d, fill %.0f%%)"
      % (levels_lsm, height, F, FILL * 100))
print()
rows = rum_table()
print("%-22s %8s %8s %10s %7s %6s" %
      ("structure", "cold IO", "warm IO", "warm range", "UO", "MO"))
for (name, rc, rw, rr, uo, mo) in rows:
    print("%-22s %8.2f %8.2f %10.2f %7.1f %6.2f" %
          (name, rc, rw, rr, uo, mo))
print()
print("IO = block reads per point/range query; UO = bytes written per logical")
print("byte; MO = space amplification. warm = cold minus %d cached levels." % CACHED)
print()
print("LSM bloom sweep (R vs M trade inside one structure):")
print("%8s %8s %8s" % ("bits/key", "warm IO", "MO"))
for bpb in (0, 5, 10, 15):
    io = 1 + (levels_lsm - 1) * bloom_fp(bpb)
    mo = T / (T - 1) + levels_lsm * bpb / (8 * REC)
    print("%8d %8.2f %8.2f" % (bpb, io, mo))
print()
costs = {name: (rw * PAGE, uo * REC) for (name, rc, rw, rr, uo, mo) in rows}
print("Mixed cost (bytes/op) = rf * warm-read bytes + (1-rf) * UO bytes")
flip = []
prev = None
for i in range(101):
    rf = i / 100.0
    best = min(costs, key=lambda k: rf * costs[k][0] + (1 - rf) * costs[k][1])
    if prev and best != prev:
        flip.append((rf, prev.split(" ")[0], best.split(" ")[0]))
    prev = best
for rf in (0.0, 0.5, 0.9, 0.95, 0.99, 1.0):
    parts = " | ".join("%s=%.0f" % (k.split(" ")[0],
                                    rf * costs[k][0] + (1 - rf) * costs[k][1])
                       for k in costs)
    winner = min(costs, key=lambda k: rf * costs[k][0] + (1 - rf) * costs[k][1])
    print("rf=%.2f: %s -> winner: %s" % (rf, parts, winner.split(" ")[0]))
print("flip points:", ", ".join("rf=%.2f %s->%s" % (rf, a, b)
      for (rf, a, b) in flip))
```

Real output of a fresh run (`python3 rum_model.py`):

```text
Assumptions: N=1000000 records, 100 B/record, 4096 B page (B=40 rec/page)
LSM levels L=6, B+tree height=3 (fanout 40, fill 70%)

structure               cold IO  warm IO warm range      UO     MO
B+tree (fanout=40)         3.00     1.00       2.00    81.9   1.47
LSM leveled (T=10)         1.04     1.04       7.00    51.0   1.19
Buffered (eps=5)           4.00     2.00       3.00     4.0   1.12

IO = block reads per point/range query; UO = bytes written per logical
byte; MO = space amplification. warm = cold minus 2 cached levels.

LSM bloom sweep (R vs M trade inside one structure):
bits/key  warm IO       MO
       0     6.00     1.11
       5     1.45     1.15
      10     1.04     1.19
      15     1.00     1.22

Mixed cost (bytes/op) = rf * warm-read bytes + (1-rf) * UO bytes
rf=0.00: B+tree=8192 | LSM=5100 | Buffered=400 -> winner: Buffered
rf=0.50: B+tree=6144 | LSM=4682 | Buffered=4296 -> winner: Buffered
rf=0.90: B+tree=4506 | LSM=4347 | Buffered=7413 -> winner: LSM
rf=0.95: B+tree=4301 | LSM=4306 | Buffered=7802 -> winner: B+tree
rf=0.99: B+tree=4137 | LSM=4272 | Buffered=8114 -> winner: B+tree
rf=1.00: B+tree=4096 | LSM=4264 | Buffered=8192 -> winner: B+tree
flip points: rf=0.55 Buffered->LSM, rf=0.95 LSM->B+tree
```

## Reading the model

- **The bloom sweep is a live R-vs-M trade inside a single structure.** Zero filter bits make the LSM read path scan one block per level (6.00 warm I/Os); fifteen bits/key collapse it to ~1.0 at the price of ~0.11 extra space amplification. This is the Monkey insight expressed in RUM units: memory spent on filters is the cheapest way to buy reads — up to the point where filters are perfect and more bits buy nothing.
- **The crossover reproduces the folk rule of thumb.** In this model the leveled LSM wins mixed workloads from ~55% to ~95% reads; only genuinely read-dominated workloads (rf >= 0.95, the OLTP OLTP-tail regime) let the B+tree's warm single-block read and lower background noise win on bytes. TokuDB-style buffered trees win the ingestion-heavy regime because their UO (4.0) is an order of magnitude below leveled compaction (51.0) — and that is exactly the market TokuDB targeted.
- **Treat the absolute numbers as model output, not measurements.** The model ignores what actually decided the Bε-vs-LSM contest: CPU cost of searching per-node buffers, the root-buffer write hotspot, compaction stalls hurting read p99 (bytes/op does not see tail latency), SSTable block reuse, and compression changing MO entirely. The directions of the trade-offs, and the existence of the two flip points, are the durable part.

## Choosing an access method: a decision procedure

1. **Measure the workload, not the doctrine.** Estimate read fraction rf, point-vs-range mix, update-to-insert ratio, delete/tombstone pressure, and value size. The model above shows the winner can change between rf = 0.90 and rf = 0.95.
2. **Pin the two overheads you actually care about, and compute the floor on the third** (the GUI reading). If the floor breaks an SLO, change structure family — no parameter tuning escapes it.
3. **Map the corner to a family, then to an engine:** read-and-range-dominated with infrequent bursts of writes -> B+-tree family (PostgreSQL, InnoDB, SQL Server); sustained write-heavy with point reads -> LSM family, then tune compaction and filter budget ([LSM Compaction](../../storage/lsm-compaction.md)); ingestion-dominated with latency-tolerant reads -> buffered Bε-family or tiered LSM.
4. **Spend MO deliberately.** Filters, block caches, and index fill factor are the knobs that move a structure's point in RUM space. RocksDB exposes all three (bits-per-key, block cache, compaction style) per column family; PostgreSQL gives you fillfactor and index choice per table.
5. **Re-check on hardware change.** The paper's closing argument is that RUM balance is re-decided by every hardware shift: SSD endurance pushed UO first, cheap RAM pushed MO, NVMe's reduced asymmetry is re-creasing the triangle today.

| Workload signature | Structure family | What you concede | Examples |
|---|---|---|---|
| Read-mostly OLTP, range scans, rf >= 0.95 | B+-tree | write amplification, update bursts | PostgreSQL, MySQL/InnoDB, SQLite |
| Write-heavy point-access, streaming inserts | leveled LSM (T = 10-20) | read p99 under compaction, background I/O budget | RocksDB, MyRocks, Cassandra, ScyllaDB |
| Ingestion-heavy, latency-tolerant reads | Bε / fractal tree or tiered LSM | per-level buffer searches, less mature tooling | TokuDB/PerconaFT, HBase tiered-style merging |
| Wide scans over cold data, minimal footprint | sparse indexes + compression (no dense index) | point-query cost | zone maps (Snowflake, MonetDB), Parquet min/max |
| Pure key-value point lookups, no ranges | hash index / hash table | all range and ordered access | Redis, memcached, DynamoDB hash keys |

## How this shows up in interviews

- **"Why does RocksDB let you choose a different compaction style per column family?"** Because compaction style moves the LSM's point in RUM space: leveled pins MO low and UO high, tiered the reverse, and different column families have different read/write mixes.
- **"Your write throughput collapses every few minutes on a 10M-key store."** A leveled LSM's background merges are the UO side of the trade becoming visible; the RUM frame says the reads were never free — the cost was deferred and batched. Check compaction backlog and filter coverage before blaming the disk.
- **"Should the new service use Postgres or RocksDB?"** Estimate rf and range-need first. The conjecture says there is no universally right answer, only corners; at rf >= 0.95 with range queries the B+tree wins, at high update rates with point reads the LSM does.
- **"What did you give up to make reads fast?"** Any structure with RO near 1.0 must be paying somewhere — in space (dense indexes, big filters) or in writes (logs of auxiliary maintenance). Answering with the specific pair is the senior answer.

## Related pages

- [B-Trees](../indexing/btrees.md) — the read-optimized corner's internals: splits, fill factor, bulk loading, and its own LSM comparison.
- [Bw-Tree and ART](./bwtree-art.md) — delta-updating B-trees and tries: softening UO without leaving the read-optimized corner.
- [LSM Compaction](../../storage/lsm-compaction.md) — the U/M machinery of the write-optimized corner: leveled, tiered, and hybrid merges.
- [LSM Trees](../internals/lsm-trees.md) — the structural baseline: memtables, SSTables, and the merge lifecycle.

## References

1. M. Athanassoulis, M. S. Kester, L. M. Maas. *Designing Access Methods: The RUM Conjecture.* EDBT 2016, pp. 461-466. DOI: [10.5441/002/edbt.2016.42](https://doi.org/10.5441/002/edbt.2016.42) — open PDF: [openproceedings.org/2016/conf/edbt/paper-12.pdf](https://openproceedings.org/2016/conf/edbt/paper-12.pdf)
2. M. Athanassoulis, S. Idreos. *Design Tradeoffs of Data Access Methods.* SIGMOD 2016 tutorial. DOI: [10.1145/2882903.2912569](https://doi.org/10.1145/2882903.2912569)
3. P. O'Neil, E. Cheng, D. Gawlick, E. O'Neil. *The Log-Structured Merge-Tree (LSM-Tree).* Acta Informatica 33(4), 1996. DOI: [10.1007/s002360050048](https://doi.org/10.1007/s002360050048)
4. L. Arge. *The Buffer Tree: A New Technique for Optimal I/O-Algorithms.* WADS 1995, LNCS 955. DOI: [10.1007/3-540-60220-8_74](https://doi.org/10.1007/3-540-60220-8_74)
5. M. A. Bender, M. Farach-Colton, W. Jannen, R. Johnson, B. C. Kuszmaul, D. E. Porter, J. Yuan, Y. Zhan. *An Introduction to Bε-trees and Write-Optimization.* ;login: 40(4), USENIX, 2015: [usenix.org/publications/login/oct15/bender](https://www.usenix.org/publications/login/oct15/bender)
