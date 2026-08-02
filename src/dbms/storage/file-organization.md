# File Organization

## Overview

File Organization defines how records (rows) are arranged in data files on disk. The choice of file organization affects the performance of inserts, deletes, scans, and lookups. There are three fundamental approaches: **Heap (unordered)**, **Sorted (sequential)**, and **Hashed**. Most modern databases use heap files with indexes, but understanding all three is essential for interviews.

## Detailed Explanation

### Three Fundamental File Organizations

```mermaid
flowchart TD
    A[File Organization] --> B[Heap File<br/>Unordered]
    A --> C[Sorted File<br/>Sequential]
    A --> D[Hashed File<br/>Direct]

    B --> B1[Insert: O(1)<br/>Scan: O(N)<br/>Search: O(N)]
    C --> C1[Insert: O(N)<br/>Scan: O(N)<br/>Search: O(log N)]
    D --> D1[Insert: O(1)<br/>Scan: O(N)<br/>Search: O(1)]

    style B fill:#e1f5fe
    style C fill:#c8e6c9
    style D fill:#fff3e0
```

### 1. Heap File (Unordered)

Records are stored in **no particular order**. New records are appended to the end of the file (or to the first page with free space).

```
Page 1: [Record 5] [Record 2] [Record 8] [Record 1]
Page 2: [Record 9] [Record 3] [Record 7] [Record 4]
Page 3: [Record 6] [Record 10] [_free_] [_free_]
```

**Operations:**

| Operation | Cost | Description |
|-----------|------|-------------|
| **Insert** | O(1) | Append to end or first page with space |
| **Delete** | O(N) | Scan to find record, mark as deleted |
| **Search (unindexed)** | O(N) | Full scan |
| **Search (indexed)** | O(1) lookup + 1 I/O | Via index |
| **Full Scan** | O(N) | Sequential read of all pages |

**Implementation — Page List:**
```
Header Page:
  ├── Page 1 → Page 3 → Page 5 → ...  (data pages with records)
  └── Free Page List: Page 7 → Page 12 → ...
```

**Advantages:**
- Fast inserts (append-only)
- No maintenance overhead
- Works well with indexes

**Disadvantages:**
- Full scans read all pages (including those with deleted records)
- No ordering for range queries
- Space reclamation needed after deletes

**Used by:** Most modern RDBMS (PostgreSQL, MySQL InnoDB, Oracle) as the default table storage.

### 2. Sorted File (Sequential)

Records are stored **sorted by a search key** (e.g., primary key).

```
Sorted by ID:
Page 1: [ID=1] [ID=3] [ID=5] [ID=7]
Page 2: [ID=9] [ID=11] [ID=13] [ID=15]
Page 3: [ID=17] [ID=19] [ID=21] [ID=23]
```

**Operations:**

| Operation | Cost | Description |
|-----------|------|-------------|
| **Insert** | O(N) | Find position, shift records, handle page splits |
| **Delete** | O(log N) | Binary search + mark deleted |
| **Search** | O(log N) | Binary search on pages |
| **Range Scan** | O(log N + K) | Binary search start, sequential scan K results |
| **Full Scan** | O(N) | Sequential (already sorted) |

**Binary Search on Pages:**
```python
# Find record with key = 13
low, high = 0, num_pages - 1
while low <= high:
    mid = (low + high) // 2
    page = read_page(mid)
    if page.min_key <= key <= page.max_key:
        # Search within this page
        return binary_search_in_page(page, key)
    elif key < page.min_key:
        high = mid - 1
    else:
        low = mid + 1
```

**Advantages:**
- Fast binary search: O(log N) page reads
- Efficient range queries (sequential scan from start to end key)
- Records are physically ordered

**Disadvantages:**
- Expensive inserts (may need to shift records or split pages)
- Reorganization needed as file grows/shrinks
- Only sorted by one key

**Used by:** Some systems for small lookup tables, temporary sorted files during query execution.

### 3. Hashed File (Direct)

Records are stored based on a **hash of the search key**. The hash determines which page (bucket) stores the record.

```
Hash function: h(key) = key % 4

Bucket 0: [ID=4] [ID=8] [ID=12]     (h=0)
Bucket 1: [ID=1] [ID=5] [ID=9]      (h=1)
Bucket 2: [ID=2] [ID=6] [ID=10]     (h=2)
Bucket 3: [ID=3] [ID=7] [ID=11]     (h=3)
```

**Operations:**

| Operation | Cost | Description |
|-----------|------|-------------|
| **Insert** | O(1) | Hash key, append to bucket |
| **Delete** | O(1) | Hash key, find and remove |
| **Search (equality)** | O(1) | Hash key, read bucket |
| **Range Scan** | O(N) | Must check all buckets |
| **Full Scan** | O(N) | Read all buckets |

**Handling Overflow:**
When a bucket is full, use **overflow chains**:
```
Bucket 1: [ID=1] [ID=5] [ID=9] → Overflow Page: [ID=13] [ID=17]
```

**Advantages:**
- O(1) equality lookups
- Fast inserts and deletes

**Disadvantages:**
- Range queries require full scan
- Overflow chains degrade performance
- Fixed number of buckets (resizing is expensive)
- Hash function must be well-tuned

**Used by:** Hash indexes in PostgreSQL, MySQL MEMORY engine, some temporary tables.

### Comparison Table

| Criterion | Heap | Sorted | Hashed |
|-----------|------|--------|--------|
| **Insert** | ⭐ O(1) | ❌ O(N) | ⭐ O(1) |
| **Delete** | O(N) | O(log N) | ⭐ O(1) |
| **Equality Search** | O(N) | ⭐ O(log N) | ⭐ O(1) |
| **Range Search** | O(N) | ⭐ O(log N + K) | ❌ O(N) |
| **Full Scan** | O(N) | O(N) | O(N) |
| **Best For** | General purpose | Range queries | Point lookups |

### Modern File Organization

Most modern databases use **heap files** as the base table storage, combined with **B+ tree indexes** for efficient lookups and range scans. This gives:
- O(1) inserts (heap)
- O(log N) lookups (B+ tree index)
- O(log N + K) range scans (B+ tree index)
- Flexibility to create multiple indexes on the same table

```
Heap File + B+ Tree Index:
┌──────────────┐     ┌──────────────────┐
│ Heap Pages   │     │ B+ Tree Index    │
│ (unordered)  │◄────│ (sorted by key)  │
│              │     │                  │
│ [row5][row2] │     │    [10|20|30]    │
│ [row8][row1] │     │   /  |  \       │
│ [row3][row7] │     │ [5] [15] [25]   │
└──────────────┘     └──────────────────┘
```

### Extent-Based Allocation

Many databases allocate space in **extents** (groups of contiguous pages) rather than individual pages:

```
Extent-based allocation:
  Table A: Extent 1 (pages 1-16), Extent 2 (pages 17-32)
  Table B: Extent 3 (pages 33-48)

Benefits:
  - Sequential scans are faster (contiguous pages)
  - Reduces file fragmentation
  - Simpler space management
```

### File Organization in PostgreSQL

PostgreSQL uses a **heap file** per table with:
- **TOAST** (The Oversized-Attribute Storage Technique) for large values
- **Visibility Map** tracking which pages have all-visible tuples
- **Free Space Map** tracking available space per page

```
Table storage:
  Base:       16384 (main data file)
  FSM:        16384_fsm (free space map)
  VM:         16384_vm (visibility map)
  TOAST:      16384 (toast table for large values)
```

## Interview Questions

### Q1: Why do most databases use heap files instead of sorted files?
**Answer:** Heap files have O(1) inserts (just append), while sorted files require O(N) inserts (shifting records). Since OLTP workloads are insert-heavy, heap files are much better. The sorting disadvantage is solved by **B+ tree indexes**, which provide O(log N) lookups and sorted access without requiring the base data to be sorted. This combination (heap + indexes) gives the best of both worlds.

### Q2: When would a sorted file be better than a heap file?
**Answer:** Sorted files are better when:
1. The primary access pattern is **range queries** on the sort key (e.g., `WHERE id BETWEEN 100 AND 200`)
2. The data is **bulk-loaded** once and rarely updated (e.g., data warehouse fact tables)
3. You need **ordered output** without a sort step (e.g., `ORDER BY` on the sort key)
4. The table is small enough that insert overhead is negligible

### Q3: What is the disadvantage of hashed file organization?
**Answer:** Hashed files are terrible for **range queries** (`WHERE id BETWEEN 100 AND 200`) because the hash function distributes keys randomly across buckets. A range query must check ALL buckets, resulting in O(N) performance. Hash files also suffer from **overflow chains** when buckets fill up, degrading O(1) to O(chain_length). Finally, **resizing** the hash table (when data grows) requires rehashing everything.

### Q4: How does a heap file track free space?
**Answer:** Common approaches:
1. **Free Space Map (FSM)** — A separate file/data structure tracking how much free space each page has (PostgreSQL)
2. **Page-level free space list** — Each page tracks its own free space in the header
3. **Free page list** — A linked list of completely empty pages
4. **Bitmap** — A bitmap where each bit indicates if a page has space

When inserting, the system consults the FSM to find a page with enough space, avoiding full scans.

### Q5: What is the difference between a file and a table in a database?
**Answer:** In most databases, a table is stored in one or more files:
- **PostgreSQL**: One file per table (plus FSM, VM, TOAST files)
- **MySQL InnoDB**: Tables stored in a shared tablespace (`ibdata1`) or individual `.ibd` files
- **Oracle**: Tables stored in tablespaces, which span multiple data files

A table may also span multiple files if it grows very large (file groups in SQL Server, tablespaces in Oracle).

## Common Mistakes

- ❌ **Assuming sorted files are always better for search** — With B+ tree indexes, heap files achieve the same lookup performance
- ❌ **Forgetting that hash files can't do range queries** — This is the #1 limitation
- ❌ **Not understanding page-level storage** — Records don't cross page boundaries; page size affects everything
- ❌ **Ignoring file fragmentation** — Heap files with many deletes become fragmented, hurting scan performance
- ❌ **Confusing logical and physical organization** — Indexes provide logical ordering on physically unordered heap files

## Summary

| Organization | Insert | Search | Range | Best Use |
|-------------|--------|--------|-------|----------|
| **Heap** | O(1) | O(N) | O(N) | General purpose (with indexes) |
| **Sorted** | O(N) | O(log N) | O(log N + K) | Bulk-loaded, range-heavy |
| **Hashed** | O(1) | O(1) | O(N) | Point lookups only |

Modern databases use **heap files + B+ tree indexes** as the dominant storage strategy, combining fast inserts with efficient lookups and range scans.

## Cross-References

- [Buffer Management](./buffer-management.md) — how pages are cached in memory
- [Record Formats](./record-formats.md) — how tuples are stored within pages
- [Column Stores](./column-stores.md) — alternative column-oriented storage
- [Indexing](../indexing/) — B+ tree and other index structures
- [LSM Trees](../internals/lsm-trees.md) — alternative for write-heavy workloads
