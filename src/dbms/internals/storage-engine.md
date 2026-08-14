# Storage Engine Internals

## Overview

A storage engine is responsible for mapping logical rows (tuples) onto physical disk pages, managing how those pages are cached in memory, and coordinating with the WAL system to ensure durability. This document covers the low-level mechanics: page layouts, tuple identification, buffer pool management, and how different engines implement these primitives.

> **Relation to other docs:** For a high-level engine comparison (InnoDB vs MyISAM vs PostgreSQL), see [engines.md](./engines.md). For the WAL protocol itself, see [wal.md](./wal.md).

## Pages and Page Layout

All page-oriented databases (InnoDB, PostgreSQL, SQLite) divide disk files into fixed-size **pages**. The page is the unit of I/O, locking, and WAL granularity.

| Database | Default Page Size | Configurable? |
|----------|------------------|--------------|
| **PostgreSQL** | 8 KB | Yes (`--with-blocksize`, compile-time) |
| **InnoDB** | 16 KB | Yes (`innodb_page_size`: 4K, 8K, 16K, 32K, 64K) |
| **SQLite** | 4 KB | Yes (`PRAGMA page_size`) |
| **SQL Server** | 8 KB | No |

### PostgreSQL Heap Page Layout

```
+------------------------------------------+
| PageHeaderData (24 bytes)                 |
|  pd_lsn: LSN of last change              |
|  pd_checksum: page integrity              |
|  pd_special: offset to special space      |
|  pd_lower: end of free space              |
|  pd_upper: start of free space            |
|  pd_pagesize_version                      |
+------------------------------------------+
| ItemIdData[] (line pointers, 4 bytes each)|
|  [offset, length] pointing to tuples      |
+------------------------------------------+
|            Free Space                      |
+------------------------------------------+
| Tuple data (grows from bottom up)         |
|  Tuple N                                  |
|  Tuple N-1                                |
|  ...                                      |
+------------------------------------------+
| Special space (index-specific data)       |
+------------------------------------------+
```

Key design: **line pointers** (ItemIdData) sit at the top of the page and grow downward; tuple data is appended from the bottom growing upward. Free space is in the middle. This allows tuples to be moved within the page (e.g., during HOT updates) without changing the line pointer index that external references use.

### InnoDB Page Layout

```
+------------------------------------------+
| FIL Header (38 bytes)                    |
|  FIL_PAGE_LSN, FIL_PAGE_OFFSET,          |
|  FIL_PAGE_PREV, FIL_PAGE_NEXT           |
|  (doubly-linked list of pages)           |
+------------------------------------------+
| Page Header (56 bytes)                   |
|  Index-level metadata                    |
+------------------------------------------+
| Infimum + Supremum Records               |
|  (virtual min/max for B+ tree leaf)      |
+------------------------------------------+
| User Records (B+ tree leaf entries)      |
|  Stored in sorted order by PK             |
+------------------------------------------+
| Free Space                               |
+------------------------------------------+
| Page Directory (sparse index of slots)   |
+------------------------------------------+
| FIL Trailer (8 bytes)                    |
|  LSN + checksum for torn-page detection  |
+------------------------------------------+
```

InnoDB pages are organized as a doubly-linked list (via `FIL_PAGE_PREV`/`FIL_PAGE_NEXT`), and each page maintains a page directory for binary search within the page.

## Tuples and Tuple IDs (CTID)

### PostgreSQL CTID

Every PostgreSQL tuple is identified by a **CTID** (Current Tuple ID), a pair `(block_number, offset_number)`:

- **block_number**: Which page in the heap file (0-indexed)
- **offset_number**: Which line pointer within that page (1-indexed)

```sql
SELECT ctid, * FROM users WHERE id = 42;
-- Output: ctid = (0, 5)  -- page 0, line pointer 5
```

CTIDs are used by indexes to point back to heap tuples. When a tuple is updated in PostgreSQL (which creates a new tuple version due to MVCC), the CTID changes. This is why PostgreSQL indexes point to CTIDs rather than primary keys — but it also means index entries become stale after updates, requiring VACUUM to clean up.

### InnoDB Tuple Identification

InnoDB uses a **clustered index** — the primary key IS the data. Secondary indexes store `(secondary_key, primary_key)` pairs. There is no CTID equivalent; the primary key serves as the stable tuple identifier.

| Aspect | PostgreSQL | InnoDB |
|--------|-----------|--------|
| **Tuple location** | CTID `(page, offset)` | Primary key in clustered B+ tree |
| **Index → data pointer** | CTID (changes on update) | Primary key (stable) |
| **Update behavior** | New tuple, new CTID | In-place if fits, else page split |
| **Stale index entries** | Yes, need VACUUM | No (PK is stable) |

## Buffer Pool Management

The buffer pool is an in-memory cache of database pages. It is the single most important memory structure for performance — every data access goes through it.

### Buffer Pool Structure

```
+------------------------------------------+
| Buffer Pool Array                         |
|  [frame_0] [frame_1] ... [frame_N-1]    |
|  Each frame holds one page                |
|  Plus metadata:                          |
|    - page_id (tablespace + page number)  |
|    - dirty flag                          |
|    - pin_count (how many users)          |
|    - LRU/LFU state                        |
|    - pageLSN (for WAL integration)       |
+------------------------------------------+
```

### Page Replacement Policies

| Policy | Algorithm | Used By | Notes |
|--------|-----------|---------|-------|
| **Clock (Generalized LRU)** | Circular list with reference bits | PostgreSQL | Default; `shared_buffers` controls size |
| **LRU with midpoint insertion** | New pages at midpoint, frequently accessed promoted to front | InnoDB | 5/8 young + 3/8 old sublists (configurable via `innodb_old_blocks_pct`) |
| **Clock sweep** | Hand sweeps circular list, decrements ref bits | Many academic systems | Simpler variant |

### InnoDB LRU with Midpoint Insertion

```
+--------+     +-------------------+     +--------+
| New    | --> | Old Sublist (3/8) | --> | Evict  |
| Pages  |     +-------------------+     | Here   |
| insert |                               +--------+
| here   |     +-------------------+     +--------+
+--------+ --> | Young Sublist(5/8)| --> | MRU    |
                +-------------------+     | (hot)  |
                                         +--------+
```

Pages are first inserted at the midpoint (head of old sublist). If accessed again within `innodb_old_blocks_time` (default 1000ms), they're promoted to the young sublist. This prevents **table scan pollution**: a full table scan brings in many pages that are accessed only once — they stay in the old sublist and are evicted quickly.

### Dirty Pages and Checkpointing

A page becomes **dirty** when it is modified in the buffer pool. Dirty pages are not immediately written to disk (no-force policy). They are written back in two scenarios:

1. **Background flushing**: A background thread (`bgwriter` in PostgreSQL, `page_cleaner` in InnoDB) periodically flushes dirty pages to keep the pool clean.
2. **Checkpoint**: A checkpoint forces all dirty pages with LSN below a threshold to disk, allowing the WAL to be truncated. See [wal.md](./wal.md) for details.

### WAL Integration with Buffer Pool

The buffer pool and WAL are tightly coupled:

```
Write path:
1. Pin the page in buffer pool (prevent eviction)
2. Write WAL record (contains page_id + change)
3. Modify page in buffer pool (mark dirty, update pageLSN)
4. Unpin the page

Flush path (buffer pool → disk):
- Before flushing a dirty page, verify: pageLSN <= flushed WAL LSN
- This enforces the WAL rule: log before data

Eviction path:
- If evicting a dirty page, it must be written to disk first
- Or: steal policy allows writing dirty uncommitted pages (requires undo)
```

## Comparison: InnoDB vs MyISAM vs PostgreSQL Heap

| Aspect | InnoDB | MyISAM | PostgreSQL Heap |
|--------|--------|--------|----------------|
| **Data organization** | Clustered B+ tree by PK | Unordered heap (MYD file) | Unordered heap files |
| **Page size** | 16 KB (configurable) | 1 KB – 16 KB (per table) | 8 KB (compile-time) |
| **Row format** | Compact, Dynamic, Redundant, Compressed | Fixed or Dynamic | Variable-length with header |
| **Free space management** | Linked list of free blocks within pages | Free block list in MYD header | Line pointers + pd_lower/pd_upper |
| **Overflow pages** | Off-page storage for long VARCHAR/BLOB | Pointer to overflow in MYD | TOAST (out-of-line storage) |
| **Buffer pool** | Yes (with LRU midpoint) | OS page cache only | Yes (with clock sweep) |
| **WAL** | Redo log + undo log | None | WAL segments |
| **Crash recovery** | ARIES-based | None (MYISAMCHK repair) | WAL replay |

## Interview Questions

**Q: What is a CTID in PostgreSQL, and why can it change?**
A: A CTID `(block, offset)` identifies a tuple's physical location in the heap file. PostgreSQL uses MVCC with tuple versioning — an UPDATE creates a new tuple version (new CTID) and marks the old one as deleted (sets `xmax`). This is why indexes store CTIDs and can become stale after updates.

**Q: Why does InnoDB use midpoint insertion in its LRU, not a standard LRU?**
A: Standard LRU suffers from table scan pollution: a full table scan pushes all hot pages out. Midpoint insertion places scanned pages in the old sublist (evicted first) and only promotes pages that are accessed again within `innodb_old_blocks_time` to the young sublist.

**Q: How does the buffer pool enforce the WAL rule during page eviction?**
A: Before writing a dirty page to disk, the buffer pool checks that the page's `pageLSN` is ≤ the last flushed WAL LSN. If not, the WAL must be flushed first. This guarantees that the WAL record describing the page change is on disk before the page itself.

**Q: What is the difference between a pin count and a dirty flag on a buffer frame?**
A: The **pin count** prevents a page from being evicted (it's "pinned" in memory by an active user). The **dirty flag** indicates the page has been modified in memory but not yet written to disk. A page can be pinned and clean, pinned and dirty, or unpinned and dirty (waiting for flush).

**Q: How does PostgreSQL's HOT (Heap-Only Tuple) update optimization work?**
A: If an UPDATE doesn't change any indexed columns, PostgreSQL can place the new tuple version on the **same heap page** and have all index entries point to the original CTID. A chain pointer links old and new versions. This avoids updating any index entries, reducing write amplification.

**Q: A buffer pool has 10,000 frames. After a large sequential scan of a 50,000-page table, what happens to the hot pages that were cached?**
A: In a naive LRU, the scan pushes all 10,000 hot pages out. In InnoDB's midpoint LRU, the scanned pages enter the old sublist and are evicted first, protecting hot pages in the young sublist. In PostgreSQL's clock sweep, scanned pages may or may not evict hot pages depending on the reference bit pattern — large scans can still cause churn, mitigated by `effective_cache_size` and sequential scan detection.

## References

- PostgreSQL: [Table Page Layout](https://www.postgresql.org/docs/current/storage-page-layout.html)
- InnoDB: [InnoDB Buffer Pool](https://dev.mysql.com/doc/refman/8.0/en/innodb-buffer-pool.html)
- *Designing Data-Intensive Applications*, Martin Kleppmann — Chapter 3 (Storage and Retrieval)
