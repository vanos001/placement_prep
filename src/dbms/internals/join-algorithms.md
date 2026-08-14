# Join Algorithms — Deep Dive

## Overview

Join algorithms are the computational backbone of relational query processing. While [query-optimization.md](./query-optimization.md) covers the optimizer's high-level join selection, this document dives into the mechanics, cost estimation, and edge cases of each algorithm.

> **Key insight:** The optimizer doesn't just pick a join algorithm — it picks the join algorithm **for each pair** in a multi-join query, based on cardinality estimates, available indexes, and memory availability.

## Nested Loop Join (NLJ)

### Variants

#### 1. Simple (Naive) Nested Loop

```
for each row r in R:              -- outer table
    for each row s in S:          -- inner table (full scan every time!)
        if r.key == s.key:
            emit(r, s)
```

**Cost:** O(|R| × |S|) comparisons. Always the worst option unless one relation is tiny (a few rows). The inner table is scanned from disk for *every* outer row.

#### 2. Index Nested Loop Join

```
for each row r in R:              -- outer table
    index_lookup(S, key=r.key)    -- use B-tree index on S.key
    for each matching s:
        emit(r, s)
```

**Cost:** O(|R| × log(|S|) + |R| × k) where k is the average number of matches per outer row. This is efficient when the outer relation is small or the inner relation has a suitable index. PostgreSQL strongly favors this when an index is available.

#### 3. Block Nested Loop Join (BNLJ)

When no index exists and the inner table is too large to fit in memory, BNLJ reduces I/O by loading blocks of the outer table into memory:

```
for each block B_R of R:          -- load one block of R into memory
    for each block B_S of S:      -- stream through S
        for each r in B_R:
            for each s in B_S:
                if r.key == s.key:
                    emit(r, s)
```

**Cost (I/O):** O(|R|/M + |R|/M × |S|) page reads, where M = number of buffer pages available. With M buffer pages, we load M-2 pages of R at a time (reserving 1 page each for input and output). This is significantly better than simple NLJ when tables don't fit in memory.

| Variant | Cost (I/O) | Best When |
|---------|-----------|-----------|
| Simple NLJ | O(|R| × |S|) pages | One table has ≤1 row |
| Index NLJ | O(|R| × log |S|) | Inner table has index on join key |
| Block NLJ | O((|R|/M) × |S| + |R|) | No index, tables larger than memory |

## Hash Join

The hash join is the workhorse for large equi-joins. It operates in two phases and is the preferred algorithm when both relations are large and no useful index exists.

### Build Phase

```
1. Choose the SMALLER relation as the build input
2. Scan the build relation, compute hash(join_key)
3. Insert into in-memory hash table: hash → [matching rows]
4. If the build relation exceeds memory → use partitioning (see below)
```

### Probe Phase

```
1. Scan the probe relation (the larger one)
2. For each row, compute hash(join_key)
3. Look up the hash bucket in the hash table
4. For each match, compare actual join keys (hash collisions possible)
5. Emit matching pairs
```

### Grace Hash Join (Partitioned)

When the build relation doesn't fit in memory, the hash join falls back to **partitioning**:

```
Phase 1: Partition both relations
  - Apply hash(join_key) % N_partitions to each row
  - Write partition i of R and partition i of S to disk
  - Each partition pair (R_i, S_i) should fit in memory

Phase 2: For each partition pair (R_i, S_i):
  - Build hash table from R_i (in memory)
  - Probe with S_i
  - Emit matches
```

If even a single partition doesn't fit in memory, it can be **recursively partitioned** (hybrid hash join). PostgreSQL triggers a multi-batch hash join (its term for Grace hash join) when `work_mem` is insufficient.

### Skew Handling

**Skew** occurs when some join key values appear far more frequently than others, causing hash bucket overflow:

| Skew Type | Detection | Handling |
|-----------|-----------|----------|
| Build-side skew | Bucket exceeds memory threshold | Recursive partitioning on that bucket |
| Probe-side skew | Many probes hit same bucket | No special handling (just slower) |

PostgreSQL tracks skew buckets separately and stores them in memory even during multi-batch hash joins to avoid excessive disk I/O for hot keys.

### Cost Estimation

```
Total cost = (build_rel_pages × seq_page_cost)
           + (probe_rel_pages × seq_page_cost)
           + (total_tuples × cpu_tuple_cost)
           + (hash_table_build_cost)

Where:
  - One sequential scan of each relation (or partition)
  - Per-tuple CPU cost for hashing and comparison
  - Memory allocation for hash table (tracked by work_mem)
```

In PostgreSQL, `EXPLAIN ANALYZE` shows `Batches` for a hash join — more than 1 batch means it spilled to disk.

## Sort-Merge Join

The sort-merge join is preferred when both inputs are already sorted on the join key (e.g., from an index scan or a prior ORDER BY), or when the result must be sorted anyway.

### Algorithm

```
1. Sort R on join_key (if not already sorted)
2. Sort S on join_key (if not already sorted)
3. Merge phase:
   i, j = 0, 0
   while i < |R| and j < |S|:
       if R[i].key == S[j].key:
           emit all matching pairs (handle duplicates)
           advance both
       elif R[i].key < S[j].key:
           i += 1
       else:
           j += 1
```

### Handling Duplicates

When multiple rows in R share the same key, the merge must compare against all matching rows in S:

```
if R[i].key == S[j].key:
    # Collect all R rows with this key
    r_group = [R[i], R[i+1], ...]  (same key)
    # Collect all S rows with this key
    s_group = [S[j], S[j+1], ...]  (same key)
    # Cross product of groups
    emit cartesian_product(r_group, s_group)
    advance past both groups
```

If both sides have many duplicates of the same key, the output can explode (cartesian product of duplicate groups).

### Cost

```
Sort cost (if needed): O(|R| log |R| + |S| log |S|)
Merge cost: O(|R| + |S|)
Total (with sort): O(|R| log |R| + |S| log |S|)
Total (pre-sorted): O(|R| + |S|)  ← very fast!
```

Sort-merge is especially efficient when: (1) at least one input is already sorted, (2) the output must be sorted on the join key, (3) the join is non-equi (range join like `R.a BETWEEN S.b AND S.c`), which hash join cannot handle.

## Comparison Table

| Algorithm | Best Case | Worst Case | Memory Required | Equi-join Only? | Sorted Output? |
|-----------|-----------|------------|-----------------|-----------------|----------------|
| Simple NLJ | O(1) if one row | O(|R|×|S|) | O(1) | No | No |
| Index NLJ | O(|R| log |S|) | O(|R|×|S|) if no index | O(1) | No | No |
| Block NLJ | O((|R|/M)×|S|) | O(|R|×|S|) | O(M) pages | No | No |
| Hash Join | O(|R|+|S|) | O(|R|×|S|) with skew | O(min(|R|,|S|)) | **Yes** | No |
| Sort-Merge | O(|R|+|S|) pre-sorted | O(N log N) | O(|R|+|S|) for sort | No | **Yes** |

## Parallel Joins

Modern databases parallelize joins by partitioning work across CPU cores:

| Strategy | How It Works | Used By |
|----------|-------------|---------|
| **Partitioned hash join** | Each worker builds/probes a subset of partitions | PostgreSQL, SQL Server |
| **Parallel scan + local join** | Each worker scans a disjoint set of pages and joins locally | PostgreSQL (partial aggregates) |
| **Broadcast hash join** | Small relation broadcast to all workers; each probes locally | Spark, Trino |

PostgreSQL parallel join: The leader process opens parallel workers, assigns each worker a subset of pages from one or both relations. Each worker performs the join independently on its subset and returns partial results. The leader merges. Controlled by `parallel_setup_cost`, `parallel_tuple_cost`, and `min_parallel_table_scan_size`.

## Interview Questions

**Q: When would a hash join be worse than a nested loop join?**
A: (1) When the inner table has an index on the join key and the outer table is very small — index NLJ does O(|R| log |S|) vs hash join's O(|R| + |S|) with memory overhead. (2) When `work_mem` is too small and the hash join spills to disk, causing many I/O-heavy batches. (3) For non-equi joins (e.g., `R.a < S.b`), hash join cannot be used at all.

**Q: How does PostgreSQL decide between hash join and merge join?**
A: The optimizer estimates the cost of each plan. Merge join is preferred when: (1) both inputs are already sorted (cost = O(|R| + |S|)), (2) the output must be sorted. Hash join is preferred when: (1) inputs are unsorted and there's enough `work_mem`, (2) it's a large equi-join. The `enable_hashjoin` and `enable_mergejoin` GUCs can force one over the other for debugging.

**Q: What is the Grace hash join and why is it needed?**
A: A standard in-memory hash join requires the build relation to fit in `work_mem`. When it doesn't, the Grace hash join partitions both relations by hash(join_key) mod N into disk-based partitions. Each partition pair is then joined separately in memory. If a partition still doesn't fit, it's recursively partitioned. PostgreSQL calls this a "multi-batch" hash join.

**Q: Explain how skew breaks a hash join and how databases handle it.**
A: Skew occurs when a few join key values have disproportionately many rows. During the build phase, a single hash bucket may exceed available memory, causing a partition to spill even though overall `work_mem` is sufficient. PostgreSQL handles this by detecting "skew buckets" during the build phase and keeping them in memory across batches, while partitioning the rest. This avoids the worst-case where a single hot key forces all batches to be re-partitioned.

**Q: Can a sort-merge join handle non-equi joins? Give an example.**
A: Yes. For example, `SELECT * FROM R JOIN S ON R.timestamp BETWEEN S.start AND S.end`. This is a range join — hash join and nested loop can handle it, but sort-merge is particularly efficient if R and S are already sorted. The merge phase finds the matching range in S for each row in R using binary search within the sorted S.

**Q: What does `EXPLAIN ANALYZE` showing `Batches: 3` for a hash join tell you?**
A: It means the build relation didn't fit in `work_mem`, so PostgreSQL used 3 batches (Grace hash join). The first batch was processed in memory; batches 2 and 3 were partitioned to disk and processed in subsequent passes. This is a signal to increase `work_mem` for this query or globally.

## References

- PostgreSQL: [Hash Joins](https://www.postgresql.org/docs/current/runtime-config-query.html#RUNTIME-CONFIG-QUERY-ENABLE)
- *Database System Concepts*, Silberschatz et al. — Chapter 15 (Query Processing)
- *Database Internals*, Alex Petrov — Chapter 7 (Storage Engines: B-Trees)
