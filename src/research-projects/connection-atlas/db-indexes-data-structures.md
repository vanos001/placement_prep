# Database Indexes and Data Structures: Shaped by the Medium

## Overview

Ask a DSA course why we use B+ trees and you will hear "O(log n) with good constants." That answer is true and empty. The real answer is physical: a B+ tree is a binary search tree *redesigned so that each node transfer matches the transfer unit of a block device*, its branching factor is dictated by bytes-per-page, and its height is dictated by dollars-per-IO. Every index structure in a database — B+ tree, LSM tree, hash index, skip list, columnar layout — is the same handful of abstract operations (lookup, range scan, insert) re-instantiated for a specific medium's latency profile, transfer granularity, and mutation cost.

This page states each structure on its own terms, names the shared principle, and is precise about where the DSA intuition survives the translation to storage and where it quietly dies.

## The Concepts, Independently

**B+ tree.** A multiway search tree optimized for *block* access: all values in leaves, interior nodes pure routers, leaves chained for range scans. The design goal is minimizing disk reads: with a branching factor of ~hundreds, the tree is 3–4 levels tall even at billions of rows, so a lookup costs 2–4 I/Os, of which the root and upper levels are almost always cached. Nodes are sized to the filesystem page (commonly 8–16 KiB) so one logical read = one physical read. Updates are in-place with a write-ahead log, which makes writes *random-ish* I/O plus logging.

**LSM tree (log-structured merge).** Invert the trade: buffer writes in an in-memory memtable, flush it as an immutable sorted run (SSTable), and periodically merge runs (compaction) in the background. Writes become sequential appends — the fastest thing a disk does — at the cost of *read amplification* (a lookup may check the memtable plus every level, mitigated by Bloom filters) and *write amplification* (compaction rewrites the same data multiple times). Full mechanics live in [../../dbms/internals/lsm-trees.md](../../dbms/internals/lsm-trees.md); here we only need the trade shape.

**Hash index.** A hash table over keys mapping to row locations: O(1) point lookups, no ordering, so no range scans, no prefix queries, no "ORDER BY for free." Perfect for equality-only workloads (Redis's entire key space; Postgres hash indexes exist but B+ trees dominate because range queries are the common case).

**Skip list (Redis sorted sets).** A probabilistic alternative to balanced trees: layered forward pointers, O(log n) expected search/insert/delete, range iteration in score order. Redis chose it for ZSETs (per the Redis docs and the `t_zset.c` source comments) because it is simple to implement correctly, offers easy rank operations, and — unlike balanced trees with rotations — has *local* pointer surgery that plays well with Redis's single-threaded event loop and incremental work budget. Note what it is *not*: it is not an on-disk structure. Redis is in-memory; the medium is DRAM, where pointer chasing is acceptable.

**Column stores and compression.** Row stores interleave a record's fields; column stores place each column's values contiguously. Two wins: queries touching few columns read few blocks, and a column of similar-typed values compresses superbly (run-length, dictionary, bit-packing, delta encoding). The medium-level insight: *layout is a data structure decision* — the physical adjacency of bytes is chosen to match the query's transfer pattern, exactly like B+ tree fan-out.

## The Shared Principle

**A storage data structure is an access-pattern transducer whose node size, fan-out, and mutation cost are chosen to match the physics of the storage medium: its transfer unit, its random-vs-sequential cost ratio, and its read-vs-write asymmetry.** Every "why does X exist" question about indexes is answered by asking what the medium charges for. Two corollaries:

- **Amplification is the exchange rate.** Read amplification (I/Os per logical read) and write amplification (physical bytes written per logical byte) are the currencies; structures are points on the read/write amplification frontier. B+ trees: low read amplification (2–4 I/Os), moderate write amplification (WAL + in-place RMW). LSM: low write cost (sequential), high read/write amplification via compaction. Columnar: minimal read amplification for column-projections, expensive row updates.
- **In-memory optimum ≠ on-disk optimum.** Binary search trees and hash tables are taught as if constants were medium-independent. On DRAM, pointer-chasing is fine (skip list wins on simplicity); on spindle, every pointer hop is a seek (fan-out must explode); on SSD, random reads are cheap-ish but writes are erase-block-shaped (LSM's sequential bias persists).

## Where the Analogy HOLDS and BREAKS

| DSA intuition | HOLDS on storage because… | BREAKS because… |
|---|---|---|
| "BSTs, hash tables, heaps are interchangeable by complexity class" | Abstract ops match: lookup/insert/range exist in all | Complexity classes ignore the constant that dominates: 3 I/Os × 100 µs = 300 µs vs 20 cache-miss hops × 100 ns = 2 µs — a 100× real-world gap hidden inside both being "O(log n)" |
| "Balanced via rotations (AVL/red-black)" | Ordering invariants transfer | Rotations rewrite nodes scattered across pages → many random I/Os; B+ trees instead *split* (amortized, local) and LSMs avoid reorganizing on the write path entirely |
| "Hash = O(1) beats tree = O(log n)" | True for pure point lookups on any medium | Databases are range-query machines; plus hash gives no ordering, no prefix scans, and resizes badly on disk |
| "Skip list ≈ balanced tree" | Same asymptotics, and in RAM it is a fair choice | On disk the layered pointers are cold-cache unfriendly; nobody ships an on-disk skiplist B-tree replacement — medium changes the winner |
| "Compression is orthogonal" | — | Compression *is* a data-structure decision in columnar engines: sortedness, dictionary cardinality, and RLE run length are layout properties, not add-ons |

The honest summary: the analogy between DSA structures and DB indexes **holds at the level of abstract operations and invariants**, and **breaks at the level of constants and mutation mechanics** — and constants are the entire game in storage.

## A Concrete Worked Example

**B+ tree height arithmetic.** Page size 16 KiB = 16,384 B. Interior entry: 8 B key + 6 B child pointer ≈ 14 B, plus overhead — call it ~20 B ⇒ fan-out ≈ 800. Leaf entry: ~20 B key+pointer pair ⇒ ~800 rows per leaf. A table with 1 billion rows needs ~1.25 M leaves; the interior level above holds ~1.25 M / 800 ≈ 1,560 nodes; above that, ~2 nodes; one root. Total height 3. A lookup = ≤ 3 leaf-level I/Os + root/interior reads — with the root and level-1 cached (they are: ~1,600 × 16 KiB ≈ 25 MiB), a point query is **one disk read** in the common case. This arithmetic, not "O(log n)," is why B+ trees won: the log is base-800, so the exponent is tiny.

**LSM write-path arithmetic.** Write amplification factor for a size-tiered/leveled LSM with per-level growth factor T=10 and L levels ≈ sum of rewrites: roughly 1 (memtable flush) + T-ish per level below; leveled compaction with T=10 gives W ≈ 1 + (L−1)·T in the worst case, and real systems measure ~10–30× (RocksDB's documented ballpark). Interpretation: writing 1 GB logically may move 10–30 GB physically — but all sequentially, so at 500 MB/s sequential that is 20–60 s of background I/O per GB ingested, *amortized*, while a B+ tree's random-write RMW on a spindle could be slower still. On SSD the calculus shifts (random reads are ~100 µs, not ~10 ms), which is exactly why LSMs displaced B+ trees in the SSD era for write-heavy workloads — the medium moved, so the frontier point moved.

**Redis skip list.** ZSET with 10⁶ members: expected depth ~log₂(10⁶) ≈ 20 levels, each `ZRANGE` hop is a DRAM pointer deref (~100 ns), so a range scan of 100 members is ~2 µs of traversal plus decode — fine *because the medium is DRAM*. The same structure on NVMe at 10 µs/read would be ~2 ms per scan: 1000× worse. Structure choice was a physics choice.

## When This Connection Is Useful

- **Problem-solving heuristics.** Given any storage problem, ask three questions: What is the transfer unit? What is the random/sequential cost ratio? What is the read/write asymmetry? Then derive the structure instead of memorizing it. This derives B+ trees (spindle: big fan-out, sequential leaf chains), LSMs (write-heavy, append-friendly), columnar (scan-heavy analytics), and log-structured filesystems with one principle.
- **Interview answers.** "Why not a hash index for everything?" — ranges, ordering, and prefix queries; plus hash resize cost on disk. "Why are LSMs 'better for writes'?" — sequential appends + amortized compaction vs in-place RMW + WAL; volunteer read amplification and Bloom filters to show the cost was not ignored. "Why does Redis use a skip list?" — in-memory medium, simplicity, rank support, incremental mutation in a single-threaded loop; citing the Redis docs' stated rationale lands as deep knowledge.
- **Engineering decisions.** Engine choice by workload shape: Postgres/MySQL (B+ tree) for read-mixed OLTP with range queries; RocksDB/Cassandra (LSM) for write-heavy ingest; ClickHouse/Parquet (columnar) for scan-heavy analytics; Redis for latency-critical hot sets. Sizing and tuning (page size, compaction threshold, Bloom filter bits) all fall out of the same amplification arithmetic.

## Interview Questions

1. Derive the height of a B+ tree for 1 billion rows with 16 KiB pages and 20-byte entries, then explain which two assumptions dominate the result and what happens to height on a 4 KiB-page filesystem.
2. State the read-amplification and write-amplification trade between B+ trees and LSM trees precisely, and explain why the SSD's 1000× better random-read latency shifted the industry toward LSMs.
3. Why does Redis use a skip list rather than a red-black tree or an on-disk structure, and which of those reasons survive if Redis were paged to disk?
4. A colleague proposes storing a 10 TB analytics table row-wise "since joins need rows." Use the medium/transfer-unit principle to argue columnar, naming two compression codecs that only work because of the layout.
5. Given a workload of 95% point lookups by ID and 5% inserts, which index structure do you pick and what does the amplification arithmetic say about the 5%?

## Key Takeaways

- Index structures are not "DSA on disk": they are re-derivations of DSA invariants under a physical cost model — transfer unit, random-vs-sequential ratio, read/write asymmetry.
- B+ trees win on block devices because fan-out shrinks height to 3–4 and puts the log in base-800; the win is arithmetic, not asymptotics.
- LSMs trade read amplification (Bloom-filtered multi-level lookups) and compaction write amplification (~10–30×) for sequential writes; the medium's properties set where that trade wins.
- Hash indexes, skip lists, and columnar layouts are each the optimal point of the same frontier for a different workload/medium pair; no structure dominates.
- Compression in column stores is a layout decision, not an afterthought — sortedness and cardinality are structural properties.

## Cross-References

- [../../dbms/indexing/b-plus-tree.md](../../dbms/indexing/b-plus-tree.md) — B+ Tree Index — node layout, splits, and page sizing in depth.
- [../../dbms/internals/lsm-trees.md](../../dbms/internals/lsm-trees.md) — LSM Trees — memtables, SSTables, compaction strategies, and amplification math.
- [../../dbms/indexing/hash-index.md](../../dbms/indexing/hash-index.md) — Hash Index — point-lookup structures and their limits.
- [../../dbms/storage/column-stores.md](../../dbms/storage/column-stores.md) — Column Stores — vectorized layouts and codec zoo.
- [../../dbms/indexing-strategy.md](../../dbms/indexing-strategy.md) — Database Indexing Strategy — workload-driven index selection at the SQL level.
- [../../redis/data-structures.md](../../redis/data-structures.md) — Redis Data Structures — ZSET/skip-list mechanics in their native habitat.
- [../../dsa/README.md](../../dsa/README.md) — Data Structures and Algorithms Track — the abstract invariants before the medium gets a vote.
- [./virtual-memory-caching.md](./virtual-memory-caching.md) — Virtual Memory and Caching — the cost ladder (DRAM vs SSD vs spindle) these structures sit on.
- [../followup-tree/database-indexes.md](../followup-tree/database-indexes.md) — Database Indexes Follow-up Tree — escalation chains for index reasoning.
- Redis docs, sorted sets: <https://redis.io/docs/latest/develop/data-types/sorted-sets/> and source comments in `src/t_zset.c` (<https://github.com/redis/redis/blob/unstable/src/t_zset.c>) — Redis's own stated rationale for skiplists.
