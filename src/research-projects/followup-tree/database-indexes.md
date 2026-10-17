# Follow-up Tree: Database Indexes

## Overview

"What is a database index?" is answered in every tutorial — and then the interviewer asks why B+trees and not binary search trees, why column order matters, and when you would throw the B+tree away for an LSM. That ladder is this page. It deliberately overlaps in *topic* with [Database Indexing Strategy](../../dbms/indexing-strategy.md), which covers the practical "which index do I create" decisions; here we cover the escalation chain and the reasoning that survives unfamiliar variants. The sibling comparison [DB Indexes and Data Structures](../connection-atlas/db-indexes-data-structures.md) maps the same material onto classic data-structure theory.

## The Opening Question

**"What is a database index, and why do we need one?"**

The expected core answer: an auxiliary on-disk structure that replaces a full table scan with a targeted lookup — it trades extra storage and slower writes for much faster reads on the indexed columns. Concretely: without an index, finding rows matching `WHERE email = ?` reads every page of the table; with a B+tree index on `email`, the engine descends the tree to the matching key range and reads only those rows.

Why this answer is correct: it states the *trade*, not just the benefit. Every subsequent follow-up is a re-balancing of that trade — write amplification, storage cost, index-only scans, LSM engines — and a candidate who opened with "indexes make reads faster" has no framework to receive them. Say the trade at rung one.

## Follow-up 1: Describe the B+tree's Layout — Why Is It Shaped Like That?

**What it tests:** whether "B+tree" is a word or a mechanism; whether you connect the shape to the disk cost model.

**How to reason:** every question about database structures secretly starts with "what does an I/O cost?" A page read is ~10M CPU cycles on SSD, far worse on spinning disk; a memory comparison is ~1 ns. The tree's shape is what you get when you optimize for *fewest page reads*, not fewest comparisons.

**Answer.** A B+tree is a short, wide, multi-level tree whose nodes are *pages* (8–16 KB typically): internal nodes hold sorted separator keys with child pointers; all values live in the leaves, which are chained left-to-right so range scans are a linear walk after a single descent. Fanout — the number of children per internal node — is large (hundreds, up to ~1000) because each child pointer costs only a key and a page number, and the node fits in one page. The consequence is depth ~4 for a billion rows (fanout ~500: 500⁴ ≈ 6×10¹⁰ ≥ 10⁹), so a point lookup costs ~4 page reads, and the top levels are nearly always cached, so the real cost approaches 1 leaf read. Compare the naive alternative — a binary search tree at log₂(10⁹) ≈ 30 levels, potentially 30 page reads with pointer chasing — and the "why is it shaped like that" answer writes itself: *maximize the work done per page fetched*. The repo's [B+ Tree](../../dbms/indexing/b-plus-tree.md) and [B-trees (DSA)](../../dsa/chapters/ch77-btrees.md) cover insertion, splitting, and order maintenance in depth; at this rung the interviewer wants the depth-vs-fanout argument and the leaf chaining for ranges.

## Follow-up 2: Why Not a Binary Search Tree? Why Not a Hash Index?

**What it tests:** whether you can defend the default against both neighbors — the "inferior-looking" tree and the "faster-looking" hash.

**How to reason:** evaluate each alternative against the *workload family* a general-purpose database must serve: point lookups, ranges, prefix scans, ordered pagination — on a storage hierarchy.

**Answer.** The BST dies on the cost model: depth grows as log₂(N), its nodes are scattered in memory, and nothing about it maps to pages — the [Why Not Binary Search for DB Indexes?](../why-not-handbook/binary-search-vs-hashing.md) comparison and [BST](../../dsa/chapters/ch14-bst.md) cover the theory. The hash index is subtler and more interesting, because for pure equality lookups it *wins*: O(1)-ish instead of O(log N). It loses on everything else: no range scans (hashes destroy order), no prefix matching, no ordering for `ORDER BY`, and poor behavior under skewed keys — a hash index cannot help `WHERE email LIKE 'a%'` or `ORDER BY created_at`. That is why a general-purpose engine defaults to the structure that serves the *broadest query family* (B+tree) and offers hash indexes as a specialized option ([Hash Index](../../dbms/indexing/hash-index.md) — PostgreSQL's hash indexes, Redis's in-memory hash tables). The senior framing: B+tree vs hash is not fast-vs-slow, it is *ordered access vs point access*; choose by query shape. If the interviewer pushes "memory is cheap now, why still a tree?", the answer is that even in memory, cache lines play the role pages played — a B+tree is also cache-friendly, and structures like adaptive radix trees ([Bw-tree and Latch-Free Indexes](../../dbms/internals/bwtree-and-latch-free.md), [Adaptive Radix Tree](../../dbms/advanced/adaptive-radix-tree.md)) are the in-memory descendants of the same argument.

## Follow-up 3: Clustered vs Secondary — What Actually Happens on a Lookup?

**What it tests:** whether you know that "the index found the row" hides a second lookup — and that the storage layout choice (clustered vs heap) changes everything downstream.

**How to reason:** ask where the *row data* physically lives relative to the index. Then trace a secondary-index lookup end to end.

**Answer.** In a *clustered* layout (MySQL InnoDB), the table **is** the primary-key B+tree — leaves hold the full rows. A secondary index is a separate B+tree whose leaves hold the indexed columns **plus the primary key**; a secondary lookup descends the secondary tree, fetches the PK, then descends the clustered tree — two B+tree traversals unless the first was *covering* (Follow-up 5). In a *heap* layout (PostgreSQL), rows live unsorted in the heap and every index's leaves hold row identifiers (TIDs); a lookup is index descent + heap fetch, and the heap fetch is the random-I/O cost indexes are criticized for. Two consequences worth volunteering: (1) **primary key choice is a storage decision** — a random UUID as InnoDB PK scatters inserts across the whole tree, causing page splits at ~50% fill, bloated trees, and buffer-pool churn, while a monotonically increasing key appends to the rightmost leaf; (2) **secondary index width feeds back into write cost** — every index on the row must be touched on update of its columns (PostgreSQL mitigates with HOT updates when indexed columns are unchanged; InnoDB mitigates with change buffering). The full comparison table lives in [Clustered vs Non-Clustered](../../dbms/indexing/clustered-vs-nonclustered.md); at this rung the interview signal is the *two-lookup trace* and the *UUID page-split* story.

## Follow-up 4: Composite Indexes — Why Does Column Order Matter?

**What it tests:** whether you understand the index as an *ordered list of concatenated keys* — the mechanism — rather than a bag of columns.

**How to reason:** mentally sort the table by `(a, b, c)` lexicographically and ask which WHERE clauses still describe contiguous ranges.

**Answer.** An index on `(a, b, c)` is sorted first by `a`, then `b` within equal `a`, then `c`. It therefore serves: equality-or-prefix on `a` alone; on `(a, b)`; on `(a, b, c)` — the **leftmost prefix rule** — plus range scans, `ORDER BY`, and grouping that respect that sort order. It does *not* serve `WHERE b = ?` (b is scattered within each `a` group — not contiguous) any more than a phone book sorted by last name serves lookups by first name. The ordering heuristic falls out: **equality predicates first (any order among themselves), then the single range/sort column last** — a range on the second column ends the usable prefix, because everything after a range is an unsorted scatter within that range. Worked example: `WHERE user_id = ? AND status = ? ORDER BY created_at` wants `(user_id, status, created_at)`; putting `created_at` in the middle breaks both the status filter and the sort. Multi-column subtleties (PostgreSQL's documentation of this is the canonical reference: [indexes-multicolumn](https://www.postgresql.org/docs/current/indexes-multicolumn.html)) and skip-scan-style behavior in some engines are covered in [Composite Index](../../dbms/indexing/composite-index.md); at this rung, demonstrating the lexicographic sort mental model is what separates knowing the rule from being able to apply it to an unseen schema.

## Follow-up 5: What Is a Covering Index and What Does It Cost?

**What it tests:** whether you can optimize *past* the index — and whether you know that every read optimization is paid for on the write path (a preview of Follow-up 6).

**How to reason:** a lookup's cost is index descent + row fetch; ask what structure makes the second cost disappear, then what that structure adds to every write.

**Answer.** A covering index includes all columns a query touches, so the engine answers from the index alone — an *index-only scan* (InnoDB secondary leaves carry the PK, so PK-included queries are covered automatically; PostgreSQL/SQL Server offer explicit `INCLUDE` columns stored in leaves but not part of the key). The read win is large: no heap/table fetch, and leaf pages are dense with just the needed columns. The costs: the index is wider (more pages, lower cache hit rate for everything), every write to any included column must update this index too, and — the senior detail — coverage is fragile: `SELECT *` or one extra column silently loses the covering property, and visibility rules can defeat it (PostgreSQL MVCC requires a heap check to confirm row visibility unless a visibility map bit is set). [Covering Index](../../dbms/indexing/covering-index.md) and [Index-Only Scans (strategy)](../../dbms/indexing-strategy.md) cover the mechanics; the escalation point is the sentence: *every read optimization on a B+tree is a write-amplification purchase* — which is exactly the doorway to the next rung.

## Follow-up 6: What Do Indexes Cost on Write? (Write Amplification)

**What it tests:** whether "add an index" is a one-sided decision in your head or a trade you can price.

**How to reason:** trace one INSERT through the engine: what structures must change, in what order, and what must be durable before the write is acknowledged.

**Answer.** Each secondary index adds one B+tree maintenance per row change: descent (page reads), possible page splits (allocations, sibling updates), and a WAL record ([WAL](../../dbms/internals/wal.md)) to make it durable — with n indexes, an INSERT touches n+1 trees. Update amplification is nastier: updating an indexed column can move the key *between* leaves (delete + insert), and random keys (UUIDs, hashed IDs) split pages everywhere instead of appending at the right edge. The aggregate effect is why teams audit unused indexes ([Index Maintenance Cost](../../dbms/indexing-strategy.md), [Index Tuning](../../dbms/indexing/tuning.md)): an index with no read traffic is a pure write tax plus a replication/buffer-pool tax. The design-space exit: if the workload is write-heavy and read-after-write, an entirely different structure — turn random writes into sequential ones — is the next rung.

## Follow-up 7: When Does an LSM Beat a B+tree?

**What it tests:** whether the B+tree is a default or a choice — the top rung for storage-engine questions.

**How to reason:** price both structures in the two currencies that matter — *read amplification* (pages read per lookup) and *write amplification* (bytes written per byte of logical change) — and ask which workload spends which currency.

**Answer.** An LSM (O'Neil, Cheng, Gawlick, O'Neil, "The Log-Structured Merge-Tree (LSM-Tree)," 1996) buffers writes in an in-memory memtable, flushes it as an immutable sorted run (SSTable), and merges runs in background compaction: **sequential I/O for writes**, at the price of lookups that may consult multiple levels (mitigated by Bloom filters — [Membership Filters](../../dbms/advanced/membership-filters.md)) and of a compaction "compaction debt" problem where background work falls behind sustained ingest ([LSM Trees](../../dbms/internals/lsm-trees.md), [Compaction](../../dbms/internals/compaction.md)). Roughly: LSM write amp is a tunable constant per level (leveled compaction ≈ number of levels × fan-in), while read amp grows with level count; B+tree is the mirror image — low read amp (~1 leaf read), in-place updates costing random I/O plus WAL. Choose LSM for write-heavy ingest with tolerable read latency (Cassandra, RocksDB, many TSDBs — [Cassandra Architecture](../../dbms/nosql/cassandra-architecture.md)); choose B+tree for read-heavy, latency-sensitive point and range queries (OLTP defaults in MySQL/Postgres). Hybrids exist ([LSM/B-tree Hybrid Engines](../../dbms/internals/lsm-btree-hybrid-engines.md)); naming that the space is a *continuum of read-amp/write-amp trades*, not two tribes, is the rung-5 answer.

## How to Approach Unfamiliar Variations

1. **Re-derive from the cost model.** Any index question — new hardware (NVMe, PMEM), new data type (vectors, geospatial), new access pattern — reduces to: how many *transfers* from the slow medium, and what order must the data keep? B+trees, LSMs, R-trees, and IVF indexes are all answers to that one question; see [Vector Indexes](../../dbms/internals/vector-indexes-deep.md) for the vector case.
2. **Follow the write path when someone proposes a read optimization.** Covering index, denormalization, materialized view, cache — each buys reads with writes or staleness. Saying "what does this cost on write, and who pays it" is the senior reflex.
3. **Ask what the query family is before judging an index choice.** "Hash index is bad" is false for equality-only key-value workloads and true for range-heavy analytics. The index is never right or wrong; the *match to the predicate and ordering shapes* is.
4. **When the interviewer invents a twist ("now the data is immutable"), invert the trade.** Immutability removes update amplification and page splits — which is why append-only/event-sourced systems lean LSM-ish, and why time-series engines get away with coarse indexes plus columnar scans.

## Interview Questions

**Q: Your table has 12 indexes and writes have become the bottleneck. How do you prune safely?**
A: Measure which indexes actually serve queries (pg_stat_user_indexes / sys schema: scans vs writes), drop those with near-zero reads after verifying no constraint or FK depends on them, and watch for plans that silently degraded (a dropped index may force a different plan). General rule: an index must earn its write tax; duplicated-prefix indexes like (a) under (a, b) are the first candidates.

**Q: Why can a query be fast in staging but slow in production with identical data volume?**
A: Plans depend on statistics, correlation, and *clustering* of data: production rows may be scattered across heap pages (different insert history), the buffer pool may be cold for the working set, and skewed value distributions can make the planner misestimate selectivity. Same row count, different physical layout — which is why "identical volume" is not "identical cost."

**Q: Would you index a boolean column?**
A: Almost never alone: selectivity is ~50%, so the planner prefers a scan. It earns its place as a *trailing* column in a composite index for specific equality combos (e.g., `(tenant_id, is_deleted, updated_at)` for "live rows per tenant"), or as a partial index (`WHERE is_deleted = false`) which indexes only the slice you query — smaller, cheaper to maintain.

**Q: InnoDB secondary indexes store the primary key in their leaves. What breaks if the PK is a wide composite?**
A: Every secondary index grows by the PK width — wider leaves, deeper trees, lower cache density, more write amplification — and every secondary lookup pays the PK lookback. This is a concrete reason PKs should be narrow and monotonically increasing; a random UUID PK taxes every index in the table, not just the PK.

## Key Takeaways

- An index is a trade — reads bought with storage and writes — and every rung of the ladder re-prices that trade; open your answer with the trade and the follow-ups land on prepared ground.
- B+tree shape follows the disk cost model: maximize fanout per page, minimize depth, chain leaves for ranges. Hash indexes beat it on pure equality and lose on everything ordered.
- Clustered vs heap layout decides whether a secondary lookup is one traversal or two, and makes primary-key design a storage decision (monotonic keys append; UUIDs split pages).
- Composite index order is lexicographic sorting: equality columns first, the range/sort column last; the leftmost-prefix rule is a corollary of the mental sort, not a memorized law.
- LSM vs B+tree is a read-amp/write-amp trade with workload-driven winners; write-heavy ingest favors LSM, latency-sensitive reads favor B+tree, and the argument generalizes to any storage-engine question.

## Cross-References

- [Database Indexing Strategy](../../dbms/indexing-strategy.md) — the practical companion: which indexes to create, index-only scans, maintenance cost.
- [B+ Tree](../../dbms/indexing/b-plus-tree.md) and [Clustered vs Non-Clustered](../../dbms/indexing/clustered-vs-nonclustered.md) — the two mechanisms behind rungs 1 and 3.
- [Composite Index](../../dbms/indexing/composite-index.md) and [Covering Index](../../dbms/indexing/covering-index.md) — rungs 4 and 5 in depth.
- [Hash Index](../../dbms/indexing/hash-index.md) — when the O(1) structure wins and what it gives up.
- [LSM Trees](../../dbms/internals/lsm-trees.md) and [Compaction](../../dbms/internals/compaction.md) — rung 7's write-optimized alternative.
- [WAL](../../dbms/internals/wal.md) — why index maintenance is crash-safe and what it adds to every write.
- [B-trees (DSA)](../../dsa/chapters/ch77-btrees.md) — the algorithmic view: splits, order maintenance, disk-block mapping.
- [Binary Search vs Hashing](../why-not-handbook/binary-search-vs-hashing.md) — sibling structured comparison of the ordered vs point-access families.
- [DB Indexes and Data Structures](../connection-atlas/db-indexes-data-structures.md) — sibling atlas page connecting this chain to classic data-structure theory.
- [Indexes Always Faster](../misconceptions/indexes-always-faster.md) — the write-path misconception behind bad indexing advice.
- [Buffer Management](../../dbms/storage/buffer-management.md) — why top-level tree pages are "always cached" and what a cold cache costs.
