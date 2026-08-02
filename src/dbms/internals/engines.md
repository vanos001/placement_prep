# Database Engines

## Overview

A database engine (or storage engine) is the component responsible for storing, retrieving, and managing data on disk. Different engines make different tradeoffs between read performance, write performance, space efficiency, concurrency, and features. Understanding engine differences is critical for choosing the right database for your workload and for tuning performance.

This page compares the most important engines: **InnoDB** (MySQL default), **MyISAM** (legacy MySQL), **RocksDB** (Facebook), **SQLite** (embedded), and **PostgreSQL's heap storage**.

## Detailed Explanation

### Engine Classification

```mermaid
flowchart TD
    A["Database Engines"] --> B["Page-Oriented<br/>(In-place Update)"]
    A --> C["Log-Structured<br/>(Append-Only)"]
    A --> D["Embedded<br/>(Single File)"]

    B --> B1["InnoDB<br/>(B+ tree clustered)"]
    B --> B2["MyISAM<br/>(B-tree non-clustered)"]
    B --> B3["PostgreSQL Heap<br/>(heap files + B-tree indexes)"]

    C --> C1["RocksDB<br/>(LSM tree)"]

    D --> D1["SQLite<br/>(B-tree in single file)"]

    style B fill:#e1f5fe
    style C fill:#c8e6c9
    style D fill:#fff3e0
```

### InnoDB (MySQL Default)

```mermaid
flowchart TD
    subgraph InnoDB["InnoDB Architecture"]
        direction TB
        BP["Buffer Pool<br/>(caches data + index pages)"]
        RL["Redo Log<br/>(ib_logfile0, ib_logfile1)"]
        UL["Undo Log<br/>(rollback segments)"]
        IB["System Tablespace<br/>(ibdata1)"]
        UF["User Tablespaces<br/>(.ibd files, one per table)"]
        DD["Data Dictionary"]
        DL["Doublewrite Buffer"]

        BP --> RL
        BP --> UL
        BP --> IB
        BP --> UF
        BP --> DL
        DD --> IB
    end

    style BP fill:#c8e6c9
    style RL fill:#ffcdd2
    style UL fill:#fff3e0
```

**Key characteristics:**

| Feature | Detail |
|---------|--------|
| **Data structure** | B+ tree (clustered index = table) |
| **Storage format** | 16KB pages in tablespaces (.ibd files) |
| **Concurrency** | MVCC with undo logs, gap locks, next-key locks |
| **Crash recovery** | Redo log + undo log (ARIES-based) |
| **ACID** | Full ACID |
| **Foreign keys** | Supported |
| **Full-text search** | Supported (InnoDB FTS since 5.6) |
| **Compression** | Per-table compression (COMPRESSED row format) |

**Clustered Index:**
```mermaid
flowchart TD
    subgraph Clustered["InnoDB Clustered Index (PRIMARY KEY)"]
        direction TB
        R1["Row: PK=1001, name='Alice', age=30"]
        R2["Row: PK=1002, name='Bob', age=25"]
        R3["Row: PK=1003, name='Charlie', age=35"]
        R1 --> R2 --> R3
    end

    subgraph Secondary["Secondary Index (name)"]
        direction TB
        S1["'Alice' → PK=1001"]
        S2["'Bob' → PK=1002"]
        S3["'Charlie' → PK=1003"]
        S1 --> S2 --> S3
    end

    Secondary -->|"Lookup by PK"| Clustered

    style Clustered fill:#c8e6c9
    style Secondary fill:#e1f5fe
```

**Doublewrite Buffer:**
InnoDB writes dirty pages to a doublewrite buffer (sequential area) before writing to their actual location. This prevents **torn pages** (partial writes during crash):

```mermaid
sequenceDiagram
    participant BP as Buffer Pool
    participant DW as Doublewrite Buffer
    participant Data as Data File

    BP->>DW: Write page (sequential, fast)
    DW->>Data: Write page to actual location (random)
    Note over DW: If crash during random write,<br/>recover from doublewrite buffer
```

### MyISAM (Legacy MySQL)

```mermaid
flowchart TD
    subgraph MyISAM["MyISAM Storage"]
        direction TB
        MYD["MYD file<br/>(data, unsorted heap)"]
        MYI["MYI file<br/>(B-tree indexes)"]
        FRM["FRM file<br/>(table definition)"]

        MYI -->|"Pointer (row offset)"| MYD
    end

    style MYD fill:#ffcdd2
    style MYI fill:#e1f5fe
```

**Key characteristics:**

| Feature | Detail |
|---------|--------|
| **Data structure** | B-tree indexes pointing to heap-ordered data |
| **Concurrency** | Table-level locking (no row-level locks) |
| **Crash recovery** | None (crash-unsafe!) |
| **ACID** | No (no transactions) |
| **Foreign keys** | Not supported |
| **Full-text search** | Supported (earlier than InnoDB) |
| **Compression** | Read-only compressed tables (myisampack) |

**Why MyISAM is obsolete:**
- Table-level locking → poor concurrent write performance
- No crash recovery → data corruption on crash
- No transactions → no rollback, no isolation
- No foreign keys → no referential integrity

**When it was relevant:** Read-heavy workloads with no concurrent writes. The FULLTEXT index support was a differentiator before InnoDB added it.

### PostgreSQL Heap Storage

PostgreSQL uses a fundamentally different architecture from InnoDB:

```mermaid
flowchart TD
    subgraph PG["PostgreSQL Storage Architecture"]
        direction TB
        HEAP["Heap Files<br/>(unordered tuple storage)"]
        IDX["B-tree Indexes<br/>(separate from data)"]
        TOAST["TOAST Tables<br/>(large values, out-of-line)"]
        WAL2["WAL (Write-Ahead Log)"]
        CLOG["CLOG (Commit Log)<br/>(transaction status)"]

        IDX -->|"TID (page, offset)"| HEAP
        HEAP -->|"Large values"| TOAST
    end

    style HEAP fill:#e1f5fe
    style IDX fill:#c8e6c9
    style TOAST fill:#fff3e0
```

**Key characteristics:**

| Feature | Detail |
|---------|--------|
| **Data structure** | Heap files (unordered) + B-tree indexes (default) |
| **Storage format** | 8KB pages with tuple headers |
| **Concurrency** | MVCC via tuple versioning (no undo logs) |
| **Crash recovery** | WAL with ARIES-like protocol |
| **ACID** | Full ACID |
| **Indexes** | B-tree, Hash, GiST, GIN, BRIN, SP-GiST |
| **Compression** | TOAST for large values; pg_compression extensions |

**MVCC in PostgreSQL (tuple versioning):**
```mermaid
flowchart TD
    subgraph MVCC["PostgreSQL MVCC"]
        direction TB
        T1["Tuple: (1, 'Alice')<br/>xmin=100, xmax=∞<br/>(created by txn 100, not deleted)"]
        T2["Tuple: (1, 'Alice_old')<br/>xmin=50, xmax=100<br/>(created by txn 50, deleted by txn 100)"]
    end

    Note["Each tuple has xmin (creator) and xmax (deleter)<br/>Readers check visibility against their snapshot"]

    style T1 fill:#c8e6c9
    style T2 fill:#ffcdd2
```

**Heap vs. Clustered Index:**
- PostgreSQL: Data is **heap-ordered** (tuples placed wherever there's space). Indexes point to tuples via TID (page, offset).
- InnoDB: Data is **clustered** (rows stored in PK order). Secondary indexes point to PK.
- Tradeoff: PostgreSQL's heap means updates create new tuple versions in different locations → requires VACUUM. InnoDB's clustered index means PK lookups are one hop.

### RocksDB (Facebook)

```mermaid
flowchart TD
    subgraph RocksDB["RocksDB Architecture"]
        direction TB
        WAL2["WAL (Write-Ahead Log)"]
        MT["Active Memtable<br/>(skip list)"]
        IMT["Immutable Memtable"]
        L0["Level 0 SSTables"]
        L1["Level 1 SSTables"]
        L2["Level 2 SSTables"]
        BC["Block Cache"]
        BF["Bloom Filters"]

        WAL2 --> MT
        MT -->|Full| IMT
        IMT -->|Flush| L0
        L0 -->|Compaction| L1
        L1 -->|Compaction| L2
        BC --> L0
        BC --> L1
        BF --> L0
        BF --> L1
    end

    style MT fill:#c8e6c9
    style L0 fill:#e1f5fe
    style L1 fill:#fff3e0
    style L2 fill:#ffcdd2
```

**Key characteristics:**

| Feature | Detail |
|---------|--------|
| **Data structure** | LSM tree (memtable + SSTables) |
| **Concurrency** | MVCC via snapshots, lock-free skip list |
| **Crash recovery** | WAL + memtable replay |
| **Transactions** | Optimistic and pessimistic (since 5.0) |
| **Compaction** | Level-based, Universal, FIFO |
| **Merge operators** | Custom logic for read-modify-write |
| **Column families** | Multiple independent LSM trees |

**RocksDB is used by:**
- CockroachDB (via Pebble, a Go rewrite)
- TiKV (TiDB's storage layer)
- Facebook's MyRocks (MySQL with RocksDB engine)
- Kafka Streams state stores
- YugabyteDB

### SQLite

```mermaid
flowchart TD
    subgraph SQLite["SQLite Architecture"]
        direction TB
        SF["Single File (.db)"]
        BT["B-tree Pages"]
        WAL3["WAL File (optional)"]
        JR["Journal File (rollback)"]

        SF --> BT
        SF --> WAL3
        SF --> JR
    end

    subgraph BTree["B-tree Structure"]
        direction TB
        INT["Interior Pages<br/>(keys + child pointers)"]
        LEAF["Leaf Pages<br/>(actual row data)"]
        INT --> LEAF
    end

    style SF fill:#e1f5fe
    style BT fill:#c8e6c9
```

**Key characteristics:**

| Feature | Detail |
|---------|--------|
| **Data structure** | B-tree (clustered, table = B-tree) |
| **Storage format** | Single file, pages (default 4KB) |
| **Concurrency** | Database-level locking (single writer) |
| **Crash recovery** | Journal (rollback) or WAL (write-ahead) |
| **ACID** | Full ACID |
| **Size limit** | 281 TB (theoretical) |
| **Embedded** | No server process, library linked into application |

**SQLite Journal vs. WAL mode:**
```mermaid
flowchart LR
    subgraph Journal["Journal Mode (default)"]
        direction TB
        J1["Copy original page to journal"]
        J2["Modify page in-place"]
        J3["Delete journal on commit"]
    end

    subgraph WAL2["WAL Mode"]
        direction TB
        W1["Append changes to WAL file"]
        W2["Readers use original DB + WAL"]
        W3["Checkpoint: merge WAL into DB"]
    end

    style Journal fill:#ffcdd2
    style WAL2 fill:#c8e6c9
```

| Mode | Writes | Readers block writers? | Writers block readers? |
|------|--------|----------------------|----------------------|
| **Journal** | Random I/O | Yes | Yes |
| **WAL** | Sequential I/O | No | No |

### Complete Comparison

```mermaid
flowchart TD
    subgraph Comparison["Engine Comparison Matrix"]
        direction TB
        H["Header Row"]
    end

    style Comparison fill:#f5f5f5
```

| Feature | InnoDB | MyISAM | PostgreSQL Heap | RocksDB | SQLite |
|---------|--------|--------|----------------|---------|--------|
| **Data Structure** | B+ tree (clustered) | B-tree + heap | Heap + B-tree indexes | LSM tree | B-tree (clustered) |
| **Concurrency** | MVCC + row locks | Table locks | MVCC (tuple versioning) | MVCC snapshots | Database-level locks |
| **Crash Recovery** | Redo + undo log | None | WAL | WAL + memtable replay | Journal or WAL |
| **Transactions** | Full ACID | None | Full ACID | Optimistic txn | Full ACID |
| **Write Performance** | Good (random I/O) | Good (table lock) | Good (heap append) | Excellent (sequential) | Good (single writer) |
| **Read Performance** | Excellent | Excellent (read-heavy) | Excellent | Good (with Bloom filters) | Excellent |
| **Space Efficiency** | Good | Good | Moderate (dead tuples) | Moderate (compaction) | Excellent |
| **Best For** | General OLTP | Read-only (legacy) | Complex queries, analytics | Write-heavy, KV | Embedded, mobile, IoT |
| **Used By** | MySQL, MariaDB | MySQL (legacy) | PostgreSQL | CockroachDB, TiKV, MyRocks | Android, iOS, browsers |

### When to Choose Which Engine

```mermaid
flowchart TD
    A["What's your workload?"] --> B["General OLTP<br/>(e-commerce, SaaS)"]
    A --> C["Write-Heavy<br/>(logging, metrics, events)"]
    A --> D["Read-Heavy Analytics<br/>(reporting, dashboards)"]
    A --> E["Embedded / Mobile<br/>(app local storage)"]
    A --> F["Distributed SQL<br/>(global scale)"]

    B --> B1["InnoDB or PostgreSQL"]
    C --> C1["RocksDB or Cassandra"]
    D --> D1["PostgreSQL or ClickHouse"]
    E --> E1["SQLite"]
    F --> F1["CockroachDB (Pebble) or TiDB (RocksDB)"]

    style B1 fill:#c8e6c9
    style C1 fill:#c8e6c9
    style D1 fill:#c8e6c9
    style E1 fill:#c8e6c9
    style F1 fill:#c8e6c9
```

## Cross-References

- [Database Internals Overview](./README.md) — High-level architecture
- [LSM Trees](./lsm-trees.md) — The data structure behind RocksDB
- [Compaction](./compaction.md) — How LSM engines reclaim space
- [WAL](./wal.md) — The durability mechanism shared by all engines
- [B-Tree](../indexing/b-tree.md) — The data structure behind InnoDB and PostgreSQL indexes
- [Buffer Pool](../caching/buffer-pool.md) — In-memory page caching
- [MVCC](../transactions/mvcc.md) — Concurrency control used by InnoDB and PostgreSQL

## Interview Questions

### Beginner

**Q: What is the difference between InnoDB and MyISAM?**
A: InnoDB supports transactions, row-level locking, crash recovery (redo/undo logs), and foreign keys. MyISAM has none of these — it uses table-level locking and is crash-unsafe. InnoDB is the default since MySQL 5.5 and MyISAM is essentially deprecated.

**Q: Why does PostgreSQL need VACUUM but InnoDB doesn't?**
A: PostgreSQL uses MVCC via tuple versioning — old tuple versions remain on disk until VACUUM reclaims them. InnoDB uses undo logs for MVCC — old versions are in undo log segments, not in the data pages. PostgreSQL's approach is simpler but requires periodic VACUUM to reclaim space.

**Q: What is a clustered index?**
A: A clustered index stores the actual row data in the index's leaf pages. In InnoDB, the primary key is the clustered index — the table *is* the B+ tree. Lookups by primary key are direct (one B-tree traversal). Secondary indexes store the primary key value and require a second lookup.

### Intermediate

**Q: How does PostgreSQL's MVCC differ from InnoDB's?**
A: **PostgreSQL**: Each tuple has `xmin` and `xmax` fields. Readers check these against their snapshot to determine visibility. Old versions remain in the same heap page until VACUUM removes them. **InnoDB**: Uses undo logs to reconstruct old versions. The data page always has the latest version; older versions are reconstructed from undo log segments on demand. PostgreSQL's approach is simpler but causes table bloat; InnoDB's is more complex but avoids bloat.

**Q: When would you use RocksDB instead of InnoDB?**
A: RocksDB excels at write-heavy workloads (millions of writes/sec) because LSM trees convert random I/O to sequential I/O. Use cases: time-series data, event logging, caching layers, distributed databases (CockroachDB, TiKV). InnoDB is better for mixed OLTP workloads with complex queries, foreign keys, and ad-hoc reads.

**Q: Explain SQLite's WAL mode and why it's better than journal mode.**
A: In journal mode, writers copy the original page to a journal file, modify the page in-place, and delete the journal on commit. This blocks concurrent readers. In WAL mode, writers append changes to a separate WAL file. Readers can read the original database while writers append to WAL. Checkpointing periodically merges WAL into the database. WAL mode allows concurrent readers and one writer.

### Advanced (FAANG-Level)

**Q: You're designing a new database engine for a global-scale OLTP workload. Would you choose B-tree or LSM, and why?**
A: For global-scale OLTP, I'd choose **LSM with optimizations**:
- **Writes**: LSM's sequential I/O handles high write throughput across distributed shards
- **Reads**: Mitigate with Bloom filters, block cache, and bounded compaction
- **Compaction**: Use leveled compaction for predictable read latency
- **Concurrency**: MVCC via snapshots (like RocksDB)
- **Crash recovery**: WAL + memtable replay (proven in production)

CockroachDB and TiDB both use LSM (Pebble/RocksDB) for this reason. The write amplification is acceptable because:
1. SSDs are getting cheaper and faster
2. Replication already provides durability
3. Write-heavy workloads dominate in global-scale OLTP

**Q: Compare InnoDB's doublewrite buffer with PostgreSQL's full-page writes. How do they solve the same problem differently?**
A: Both solve the **torn page** problem: if a crash occurs while writing a page, the page may be partially written (torn), and the WAL alone can't recover it because WAL records are physiological (they describe changes, not full pages).

- **InnoDB doublewrite buffer**: Writes dirty pages to a sequential buffer first, then to their actual location. If a torn page is detected during recovery, restore from the doublewrite buffer.
- **PostgreSQL full-page writes**: The first WAL record after a page is dirtied includes a full copy of the page. During recovery, if a torn page is detected, restore it from the WAL.

Tradeoff: Doublewrite buffer adds one extra sequential write per page. Full-page writes increase WAL size but avoid the extra I/O path.

**Q: A startup asks you to choose between PostgreSQL and MySQL (InnoDB) for a new SaaS product. What factors would you consider?**
A:
| Factor | PostgreSQL | MySQL/InnoDB |
|--------|-----------|-------------|
| **Query complexity** | Better (CTEs, window functions, JSON, arrays) | Good but fewer advanced features |
| **Extensions** | Rich ecosystem (PostGIS, pg_trgm, TimescaleDB) | Fewer extensions |
| **MVCC** | Tuple versioning (simpler, but VACUUM needed) | Undo logs (more complex, no bloat) |
| **Replication** | Streaming replication, logical replication | Group replication, InnoDB Cluster |
| **Ecosystem** | ORMs, cloud (RDS, Aurora, Supabase) | ORMs, cloud (RDS, Aurora, PlanetScale) |
| **JSON support** | Excellent (jsonb with indexing) | Good (JSON type since 5.7) |
| **Concurrent writes** | Good (row-level locks via MVCC) | Good (row-level locks) |

Recommendation: PostgreSQL for complex queries, analytics, and extensibility. MySQL for simpler OLTP with proven high-availability tooling (Vitess, ProxySQL).

## Common Mistakes

1. **Using MyISAM in production**: MyISAM is crash-unsafe and lacks transactions. Always use InnoDB.

2. **Assuming PostgreSQL doesn't need tuning**: `shared_buffers`, `work_mem`, `maintenance_work_mem`, `autovacuum` settings all need tuning for production workloads.

3. **Ignoring VACUUM in PostgreSQL**: Dead tuples accumulate until VACUUM runs. Without regular VACUUM, tables bloat and performance degrades.

4. **Using SQLite for concurrent write workloads**: SQLite has database-level locking for writers. Use a client-server database for concurrent writes.

5. **Choosing RocksDB for read-heavy workloads without tuning**: LSM reads can be slow without Bloom filters, block cache, and proper compaction. Always enable Bloom filters and size the block cache appropriately.

## Summary and Revision Notes

- **InnoDB**: B+ tree clustered index, MVCC via undo logs, full ACID, MySQL default
- **MyISAM**: B-tree + heap, table locks, crash-unsafe, deprecated
- **PostgreSQL Heap**: Unordered heap files + B-tree indexes, MVCC via tuple versioning, needs VACUUM
- **RocksDB**: LSM tree, write-optimized, used by CockroachDB/TiKV/MyRocks
- **SQLite**: B-tree in single file, embedded, WAL mode for concurrent reads
- **Clustered index**: Row data stored in index order (InnoDB, SQLite)
- **Heap storage**: Row data stored wherever there's space (PostgreSQL)
- **Doublewrite buffer**: InnoDB's torn page protection
- **VACUUM**: PostgreSQL's dead tuple reclamation (not needed in InnoDB)
- **WAL mode**: SQLite's improved concurrency over journal mode


## Cross References

- [LSM Trees](../dbms/internals/lsm-trees.md)
- [B-Tree](../dbms/indexing/b-tree.md)
- [Buffer Pool](../dbms/caching/buffer-pool.md)
- [File Organization](../dbms/storage/file-organization.md)
