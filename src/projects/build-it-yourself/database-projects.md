# Database Build-It-Yourself Projects

## 1. Build a B-Tree

Implement an on-disk B-tree with insert, search, and delete operations supporting variable-length keys. Handle node splitting (promote median key to parent) and merging/redistribution (borrow from sibling or merge with sibling on underflow). Persist nodes to disk via `pread`/`pwrite` with a fixed page size (e.g., 4 KB). Implement a buffer pool manager that caches recently accessed pages in memory and evicts with LRU or clock replacement.

**Key concepts**: B-tree invariants (all leaves at same depth, nodes half-full minimum), node splitting/merging, sequential vs random I/O, page-oriented storage, buffer pool management, disk I/O minimization. **Complexity**: Intermediate (3-4 weeks). **References**: SQLite B-tree implementation (`btree.c`), PostgreSQL `nbtree.c`, "Database Internals" by Alex Petrov (Ch. 3), CMU 15-445 lectures.

## 2. Build an LSM Tree

Implement a Log-Structured Merge tree with an in-memory sorted table (memtable, backed by a skip list or red-black tree), SSTable files on disk (sorted key-value pairs with a block index), and a compaction engine supporting size-tiered and leveled compaction. Add a Bloom filter per SSTable to speed up point lookups (avoid checking files that definitely don't contain the key).

**Key concepts**: Write-optimized structure, memtable flush to SSTable, compaction strategies (size-tiered vs leveled), Bloom filters (probabilistic membership), tombstones for deletes, merge iteration during reads. **Complexity**: Intermediate-Advanced (4-5 weeks). **References**: LevelDB source (`db/`), RocksDB architecture doc, Bitcask paper, "Designing Data-Intensive Applications" Ch. 3.

## 3. Build a Write-Ahead Log (WAL)

Implement a sequential write-ahead log that records mutations before they are applied to the main data structure. Support crash recovery by replaying the log on startup. Implement log rotation (segmented log files), log truncation after checkpoint, and both physical and logical logging formats. Add CRC checksums for integrity verification.

**Key concepts**: Write-ahead logging, atomicity and durability guarantees, log sequence numbers (LSN), checkpointing, group commit (batching multiple writes), fsync semantics, CRC integrity. **Complexity**: Beginner-Intermediate (2-3 weeks). **References**: SQLite WAL mode, PostgreSQL WAL (`xlog.c`), ARIES recovery algorithm paper, InnoDB redo log.

## 4. Build MVCC

Implement Multi-Version Concurrency Control with transaction timestamps. Each transaction gets a begin timestamp at start and a commit timestamp on completion. Reads see a snapshot of all versions with commit timestamp ≤ the reader's begin timestamp. Implement garbage collection of old versions no longer visible to any active transaction. Handle write-write conflicts with first-committer-wins or abort.

**Key concepts**: Snapshot isolation, transaction timestamps, version chains per key, garbage collection (vacuum), write skew anomaly, read/write conflicts, serializability vs snapshot isolation. **Complexity**: Advanced (4-6 weeks). **References**: PostgreSQL MVCC (`heapam.c`, `visibility.c`), CockroachDB MVCC, "Database Internals" Ch. 7, CMU 15-445 MVCC lecture.

## 5. Build a Query Optimizer

Build a SQL parser (or start with a simplified query language), construct a logical query plan as a tree of relational operators (scan, filter, project, join, sort, aggregate), and apply transformation rules (predicate pushdown, projection pushdown, join reordering). Implement a cost-based optimizer that estimates cardinality and I/O cost using histograms or sampling, and picks the cheapest physical plan (hash join vs merge join vs nested loop).

**Key concepts**: Relational algebra, logical vs physical plans, rule-based optimization, cost-based optimization, selectivity estimation, join ordering (dynamic programming), histogram statistics. **Complexity**: Advanced (5-8 weeks). **References**: SQLite query planner (`where.c`), CockroachDB optimizer, Cascades optimizer paper (Graefe), CMU 15-445 query optimization lectures.

## 6. Build a Vector Database

Implement an approximate nearest neighbor (ANN) search engine using the HNSW (Hierarchical Navigable Small World) index. Support cosine similarity and Euclidean distance. Implement vector insertion, bulk loading, and k-NN search with configurable recall/latency trade-off via the `ef_construction` and `ef_search` parameters. Add basic metadata filtering and persistence of the graph structure.

**Key concepts**: HNSW graph construction (multi-layer skip-list-like structure), ANN search trade-offs (recall vs latency), distance metrics, vector normalization, brute-force exact search for correctness validation. **Complexity**: Intermediate (3-4 weeks). **References**: HNSW paper (Malkov & Yashunin), hnswlib source, Milvus architecture, Qdrant source.

## 7. Build a Distributed KV Store

Build a distributed key-value store with consistent hashing for data partitioning (with virtual nodes to balance load), replication (configurable replication factor N), and a gossip-based membership protocol for node discovery and failure detection. Support read repair and hinted handoff for eventual consistency. Provide a `get`/`put`/`delete` client API.

**Key concepts**: Consistent hashing with virtual nodes, replication strategies (leader-based vs leaderless), gossip protocol (SWIM-style), vector clocks for conflict detection, read repair, hinted handoff, quorum reads/writes. **Complexity**: Advanced (5-7 weeks). **References**: Dynamo paper (DeCandia et al.), Riak source, Cassandra architecture, "Designing Data-Intensive Applications" Ch. 5.

> **Interview Angle**: A candidate who has built an LSM tree or MVCC system can answer storage engine design questions with real implementation experience. "How would you design a key-value store?" becomes a 10-minute walkthrough of your actual code rather than hand-waving.