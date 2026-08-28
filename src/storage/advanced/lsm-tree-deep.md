# LSM-Tree Compaction Deep Dive

The Log-Structured Merge Tree (LSM-tree), introduced by O'Neil et al. in 1996, is the storage engine behind nearly every modern write-heavy database: RocksDB (used in MySQL/MyRocks, CockroachDB, TiKV, Fess FoundationDB, MongoDB WiredTiger), Cassandra/ScyllaDB, HBase, LevelDB, and SQLite's LSM mode. The basic structure is simple — a MemTable in RAM, immutable SSTables on disk organized into levels — but the **compaction** strategy is what actually determines performance. This page is about the four major compaction styles, the write-amplification formula, and the subtle interactions with Bloom filters that bite at scale.

For the basic structure (memtable, L0, SSTable format) see [the LSM internals page](../../dbms/internals/lsm-trees.md). For compaction alternatives at a glance, see [LSM compaction overview](../lsm-compaction.md).

## Why Compaction Exists

LSMs trade write throughput for storage overhead: every write hits the WAL once and is rewritten into successively larger SSTables through compaction. Without compaction:

- The number of SSTables on disk grows linearly with writes.
- A point read would have to consult every SSTable (linear scan, O(N)).
- Tombstones (deletions) never get reclaimed.
- Bloom filters multiply: 1000 SSTables × 10-byte-per-key filter = 1 KB per key wasted.

Compaction rewrites a set of SSTables into fewer, larger, non-overlapping SSTables, removing duplicates and dead data. The cost is **write amplification** (WA): the same bytes are rewritten many times. Different compaction strategies make different trade-offs on WA, RA (read amplification), and SA (space amplification).

## Leveled Compaction (RocksDB Default, LevelDB)

In leveled compaction, each level `L_i` (for i ≥ 1) is a **single sorted run** of SSTables whose key ranges do not overlap within the level. The size ratio `T` between adjacent levels is the **size-tier ratio**, typically 10:

```
L0: 4 SSTables, each 64 MB (flushed from memtable)         <- overlap
L1: 10 SSTables of 64 MB = 640 MB total, non-overlapping
L2: 100 SSTables of 64 MB = 6.4 GB total, non-overlapping
L3: 1000 SSTables of 64 MB = 64 GB total, non-overlapping
L4: 10000 SSTables of 64 MB = 640 GB total, non-overlapping
```

Compaction picks **one** SST from `L_i`, finds the SSTs in `L_{i+1}` whose key ranges overlap (typically 1–2 SSTs for size ratio T=10), and merges them into new SSTs that get written back into `L_{i+1}`. Because the inputs already overlap, the merge is `O(|input|)` and the level stays non-overlapping.

```
Before:                              After:
  L1: [a-f] [g-m] [n-z]                L1: [a-f]      [n-z]
  L2: [a-c] [d-i] [j-m] [n-r] [s-z]   L2: [a-c] [d-i] [j-m] [n-r] [s-z]
              ^^^^ merge with overlapping L1 SST [g-m]
        Compaction: merge L1[g-m] + L2[d-i] + L2[j-m]
        → produces L2[d-i] + L2[j-m] (now with g-m updates applied)
```

**Properties:**
- RA: low. A point lookup checks at most one SST per level (plus all of L0). With T=10 and Lmax=4, that's ~5 SSTable reads per lookup, ~1 of which is real (Bloom filters reject the rest).
- SA: low. Within a level, no two SSTs share keys, so each key lives in exactly one SST per level. The deepest level holds ~90% of data; total duplicate ratio is bounded by 1 + 1/T ≈ 1.1 (10% space waste).
- WA: high. A key written at L1 gets rewritten at every level until it lands at Lmax. With size ratio T and total levels L = log_T(N/SST_size), each key is rewritten L times. So WA ≈ L·T·(1-1/T) per byte written — roughly **T = 10** in the worst case in practice, or **T · (L-1) ≈ 30-40** in pure level-Lmax throughput. The asymptotic formula is `WA = O(T)` per level × `O(log_T N)` levels.

For a 1 TB database with T=10, ~30 keys are rewritten per insert. With NVMe at 1 GB/s sequential write bandwidth, the disk does ~30 GB of internal writes per 1 GB of user writes — the so-called "WA = 30x" problem documented in RocksDB tuning guide.

## Size-Tiered Compaction (Cassandra Default)

In size-tiered (also called tiered or universal), each level can hold **multiple sorted runs** whose key ranges overlap. When `T` SSTables of similar size accumulate at a level, they are all merged into one larger SST at the next level:

```
L0: 64MB × 4 SSTs (flushed from memtable, may overlap)
        ── merge 4 → one 256MB SST
L1: 256MB × 4 SSTs (each, individually, contains the full key range)
        ── merge 4 → one 1GB SST
L2: 1GB × 4 SSTs
        ── merge 4 → one 4GB SST
```

**Properties:**
- RA: high. Point reads must check every SST in every level (since they may overlap). With 4 levels × 4 SSTs = 16 SSTs scanned (Bloom-checked) per lookup. Bloom false positives translate directly into real reads.
- SA: high. Up to 2× peak space during a major compaction (the new SST is written before the old ones are deleted); tombstones are not reclaimed until a major compaction.
- WA: low. The asymptotic WA is `O(log_T N)` — only one merge per level, regardless of how many keys the level contains. For T=4 and 4 levels, WA ≈ 4 (vs 30 for leveled). This is why Cassandra's default has been size-tiered for write-heavy workloads.

WA formula (precise): a key written at the top is merged exactly once per level, into a SST of size growing by factor T. Total rewrite = `1 + T + T² + ... + T^L = (T^(L+1)-1)/(T-1)`. Per unit of original data: `WA = (T^(L+1)-1) / ((T-1)·T^L) → T/(T-1)` for large L. So **WA → ~T/(T-1)**, which is **2 for T=2, ~1.33 for T=4, ~1.11 for T=10** — asymptotically O(1).

## Time-Window Compaction (TWCS)

Cassandra's TWCS is designed for **time-series data**: each row has a timestamp, queries are range-scans over recent time, and old data is dropped after TTL. TWCS partitions the keyspace into **time windows** (e.g., 1-hour or 1-day windows). Within a time window, compaction is size-tiered. Across windows, no compaction happens — once a window's data is "frozen", it never gets merged with another window.

```
Hour 1:  T1.bin   (size-tiered inside this window)
Hour 2:  T2.bin
Hour 3:  T3.bin
...
After TTL expires for hour 1: T1.bin deleted as a whole (no merge needed).
```

Properties:
- WA: very low — each row is compacted a bounded number of times within its own window, never across windows.
- RA: excellent for time-range queries (only the relevant window's SSTs are scanned).
- SA: minimal (windows are self-contained).
- The perfect fit for IoT metrics, event logs, and metrics. Cassandra 3.8+ ships TWCS; many time-series workloads (KairosDB, Prometheus-tier) use it.

Limitations: poorly chosen window size causes "twcs storms" — a 24-hour window with 1-day TTL means the entire day's data compacts at once, spiking disk and CPU. Best practice: small windows (1 hour) and TTL-aligned to window boundaries.

## Unified Compaction (RocksDB)

RocksDB introduced a "**Universal**" (size-tiered) and a "**FIFO**" (drop oldest) compaction, and a more recent "**kDelete**" style. But the most general approach is **unified compaction**, which generalizes both leveled and size-tiered with two parameters:

- `F` — the fan-out: how many SSTs from level `L` participate in one compaction.
- `T` — size ratio: how much larger the output SST is than each input SST.

Setting `F = 1` gives **leveled** (one SST from level L, multiple from L+1). Setting `F = T` gives **size-tiered** (T SSTs from level L, all merged). Intermediate values give a hybrid.

RocksDB's default `kCompactionStyleLevel` is leveled. The Universal style is `kCompactionStyleUniversal` (size-tiered-like). There's no exposed "unified" style yet, but the academic literature (Dong et al. 2017, "Rocksdb: Evolution of unkey-evolution") shows that the sweet spot for mixed workloads is `F ≈ T/2`, giving roughly half the WA of leveled with manageable RA.

## Compaction Scheduling

Compaction is a background job that competes with foreground I/O. Schedulers decide **when** to run and **which** SSTs to compact:

1. **Size trigger**: when level `L_i` exceeds its target size, compact some SSTs into `L_{i+1}`. Simple but bursty.
2. **File-count trigger**: when L0 has more than `level0_file_num_compaction_trigger` (default 4) SSTs, force a flush-compaction. Critical because L0 SSTs overlap.
3. **Tombstone ratio trigger**: when an SST has >10% tombstones, prioritize compacting it (reclaims space).
4. **Read-latency trigger**: when read latency spikes (often from too many L0 files), trigger compaction to clear the bottleneck.

RocksDB runs compaction in a thread pool (`Env::SetBackgroundThreads`, default 1 for flush + 1 for compaction, scaled by `max_background_compactions`). Setting `max_background_compactions` high (e.g., 16 on a 32-core server) lets multiple compactions run in parallel, useful when disk bandwidth is the bottleneck.

**Subcompaction**: For a single huge compaction, RocksDB can split the key range into N pieces and compact each in parallel (`subcompactions=N`, ~1 GB per subcompaction). This is critical for large databases where a single-threaded compaction cannot keep up with ingest.

## Write Amplification Formula — Derivation

For **leveled** with size ratio T:

Each SST at level i has size `S · T^i` where S is the memtable flush size. A new key starts at L0 (size S) and is merged at every level. At level i → i+1, the merge input is `S · T^i` (one SST from level i) + `S · T^i · (T-1)` (the overlapping SSTs in level i+1) = `S · T^i · T`. The new key's bytes are rewritten once into the merged SST.

So the per-byte WA = number of levels = `log_T(N/S)` where N is total DB size. But the disk write per byte at each level = (input/output ratio) = `(T·S·T^i) / (S·T^(i+1))` = 1. Summed across `log_T N` levels: WA = `log_T N` rewrites per byte × `T·(log_T N - 1)` total bytes of merged output per byte at Lmax — actually `WA_leveled = T · (L-1)` where L is the number of levels.

For T=10, L=4: **WA_leveled ≈ 30×.** Empirically RocksDB sees 20-40× in production.

For **size-tiered**: each key participates in one merge per level, and the merged output has the key once. So per-key WA = number of levels = `log_T N`. **WA_size-tiered ≈ log_T N.** For T=4, N=1TB: WA ≈ 5-6×. Empirically 4-8× in production.

The ratio `WA_leveled / WA_size-tiered = T`, the size ratio. This is the fundamental tension: large T → low RA (smaller levels) but high WA in leveled.

## Bloom Filter Degradation During Compaction

Every SST has a Bloom filter that lets the read path skip the SST if the key is "definitely not here." As compaction merges SSTs, the new SST contains more keys, so its Bloom filter has a higher false-positive rate (FPR) at the same memory budget.

For a Bloom filter of `b` bits per key, FPR = `(1 - e^(-k·n/m))^k ≈ (0.6185)^(m/n)`. If we keep `b = 10` bits/key, FPR ≈ 1%. After merging T=4 SSTs of 1M keys each into one SST of 4M keys, the same 10-bit-per-key filter gives the same 1% FPR — but now the SST has 4× as many keys. For a point lookup of a non-existent key:

```
Before (4 SSTs × 1M keys, separate Bloom filters):
  4 filter lookups, each with 1% FPR → 4% chance of any one
  triggering a real SST read.

After (1 SST × 4M keys, one Bloom filter with same FPR):
  1 filter lookup with 1% FPR → 1% chance of real SST read.
```

So merging reduces total FPR sum. **Bloom filters don't degrade** from compaction if the bits-per-key ratio is preserved. They *do* degrade if the merged SST has memory pressure and uses a smaller filter (typical in size-tiered with many large SSTs).

The real Bloom degradation in size-tiered:

```
Size-tiered with 4 levels × 4 SSTs each (16 SSTs):
  Each SST has its own Bloom, 10 bits/key, 1% FPR.
  A point lookup of non-existent key:
    - 16 Bloom checks, 1% each → 16% probability of at least
      one false positive → real read on a non-existent key.
  That's a ~16× higher effective FPR than leveled.
```

This is why size-tiered gets killed on point lookup workloads even with Bloom filters — the lookup cost grows linearly with SST count. Leveled's bounded L0 + 1 SST per level keeps effective FPR constant.

## Production Tuning Cheatsheet

Workload → recommended strategy:

```
Read-heavy point lookups (e.g., user DB):
  → Leveled, T=10, max_levels=4-6, write_buffer_size=64MB.
     Bloom: 10 bits/key, block-cache 4-8 GB.

Write-heavy (e.g., event log, metrics):
  → Size-tiered or TWCS. T=4. Larger memtable (256 MB+).
     Compaction: max_background_compactions=8+.

Time-series with TTL:
  → TWCS, window=1h, TTL=window×N for integer N.

Mixed / unknown:
  → Leveled with subcompactions=2-4, write_buffer_size=128MB,
     level_compaction_dynamic_level_bytes=true (RocksDB 5.x+).
```

## References

- P. O'Neil, E. Cheng, D. Gawlick, E. O'Neil, "[The Log-Structured Merge-Tree (LSM-Tree)](https://www.cs.umb.edu/~poneil/lsmtree.pdf)", *Acta Informatica* 33(4), 1996 — the foundational LSM paper.
- Facebook/Meta, "[RocksDB Tuning Guide](https://github.com/facebook/rocksdb/wiki/RocksDB-Tuning-Guide)" — official tuning reference.
- Facebook/Meta, "[RocksDB Compaction Overview](https://github.com/facebook/rocksdb/wiki/Compaction)" — official compaction documentation.
- Apache Cassandra, "[Compaction Strategies](https://cassandra.apache.org/doc/latest/operating/compaction.html)" — STCS, LCS, TWCS docs.
- Dzenan Silajdzic, "[Compaction in Cassandra and ScyllaDB](https://www.scylladb.com/2018/01/16/compaction-in-cassandra-and-scylladb/)" — ScyllaDB blog with practical tuning notes.
- Dong, S., Callaghan, M., et al., "[Rocksdb: Evolution of development experience of unkey evolution](https://www.slideshare.net/DongXu/rocksdb-evolution-of-development-experience-of-unkey-evolution)", *SIGMOD 2017* — production RocksDB evolution.
- Lanyu Lu, et al., "[UniKV: Toward the Performance of LSM-tree in Key-value Stores](https://www.usenix.org/system/files/conference/atc17/atc17-lu.pdf)", *USENIX ATC 2017* — hybrid compaction analysis.
- Wu, X., et al., "[The LSM-tree Storage Engine](https://www.eecs.harvard.edu/~cmnz/publications/hptnt-sigmod-2020.pdf)", *ACM SIGMOD* tutorial — modern survey.
- N. Dayan et al., "[The Log-Structured Merge-Bush & the B epsilon-Tree](https://cs.uwaterloo.ca/~jnwKim/papers/sigmod2020.pdf)", *SIGMOD 2020* — modern LSM variants and complexity proofs.
- Apache ScyllaDB, "[Twcs in Scylla](https://docs.scylladb.com/stable/cql/compaction.html)" — TWCS implementation details.
