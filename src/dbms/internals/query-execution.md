# Query Execution Models

## Overview

Once the query optimizer produces a physical plan (a tree of operators), the **execution engine** must evaluate that plan and produce results. The choice of execution model affects memory usage, latency for the first row, and the ability to parallelize. This document covers the three major models and their tradeoffs.

> **Relation to other docs:** For how the optimizer *chooses* the plan, see [query-optimization.md](./query-optimization.md). For the join algorithms used *within* operators, see [join-algorithms.md](./join-algorithms.md).

## Volcano (Iterator) Model

The Volcano model, also called the **iterator model**, is the most widely used execution model in modern databases (PostgreSQL, MySQL, SQLite).

### Core Interface

Every operator in the plan tree implements a uniform three-method interface:

```
Operator Interface:
  open()   → Initialize state, open child operators
  next()   → Return next tuple, or EOF (end of file)
  close()  → Release resources, close child operators
```

### Execution Flow

```
                SELECT name, salary
                FROM employees
                WHERE salary > 100000

Plan tree:
              [Project]
             name, salary
                  │
              [Filter]
           salary > 100000
                  │
              [SeqScan]
              employees

Execution (pull-based):
  Project.next() calls Filter.next()
    Filter.next() calls SeqScan.next()
      SeqScan.next() returns row
    Filter evaluates predicate, passes matching row up
  Project extracts name, salary, returns to client
```

Each `next()` call pulls one tuple from the child. Control flows **bottom-up**: the root operator calls `next()` on its children, which call `next()` on *their* children, and so on.

### Characteristics

| Aspect | Detail |
|--------|--------|
| **Memory** | O(depth) — only one tuple per operator on the stack at a time |
| **First row latency** | Low — returns the first matching row immediately |
| **Intermediate results** | Not materialized; re-computed if a parent calls next() multiple times (generally not an issue in tree plans) |
| **Implementation** | Simple, modular, each operator is independent |
| **Used by** | PostgreSQL, MySQL, SQLite, CockroachDB |

### Volcano in PostgreSQL

PostgreSQL's executor is a textbook Volcano implementation. Each plan node is a C struct with an `ExecProcNode()` function pointer (equivalent to `next()`). The `ExecScan()` function dispatches to the node's specific `Exec*` function.

## Materialization Model

In the materialization model, each operator **fully evaluates** its output and writes it to a temporary storage (memory or disk) before the parent operator begins processing.

```
Plan tree:
  [Sort] → [Hash Join] → [SeqScan A] + [SeqScan B]

Execution:
  Step 1: SeqScan A materializes all rows → temp_A
  Step 2: SeqScan B materializes all rows → temp_B
  Step 3: Hash Join reads temp_A, builds hash table, probes with temp_B
  Step 4: Sort reads hash join output, sorts fully → temp_sorted
  Step 5: Return temp_sorted to client
```

### Characteristics

| Aspect | Detail |
|--------|--------|
| **Memory** | O(intermediate result size) — can be very large |
| **First row latency** | High — must complete the entire subtree first |
| **Throughput** | Can be better for bulk operations (sorting, hashing) due to sequential access |
| **Used by** | Often combined with Volcano — hash join and sort operators materialize internally |

The materialization model is rarely used as the **entire** execution strategy. Instead, most databases use Volcano as the outer framework, and individual operators (sort, hash join, hash aggregate) materialize their inputs internally as a performance optimization.

## Comparison

| Aspect | Volcano (Iterator) | Materialization |
|--------|-------------------|-----------------|
| **Control flow** | Pull (top-down demand) | Push (bottom-up, all at once) |
| **First row latency** | Low | High |
| **Memory usage** | Minimal per-operator | Can be large (intermediate results) |
| **Operator abstraction** | Uniform interface (open/next/close) | Each operator is custom |
| **Code complexity** | Low | Low |
| **Best for** | Interactive queries, LIMIT, cursors | Batch processing, full result sets |

## Parallel Query Execution

Modern databases exploit multi-core CPUs by parallelizing query execution across worker processes or threads.

### PostgreSQL Parallel Query

```
                    Gather (leader process)
                   /        |         \
             Worker 1  Worker 2  Worker 3
                |         |         |
            Partial   Partial   Partial
            SeqScan   SeqScan   SeqScan
            (pages    (pages    (pages
             0-3333)  3334-6667) 6668-9999)
```

**How it works:**
1. The optimizer decides to parallelize (based on table size, cost, `max_parallel_workers_per_gather`)
2. The **Gather** or **Gather Merge** node spawns N worker processes
3. Each worker gets a disjoint set of pages to scan
4. Workers execute the same plan subtree independently
5. The leader collects partial results and returns them to the client

Parallelism can be applied at multiple points in a plan:
- **Parallel Seq Scan**: Each worker scans different pages
- **Parallel Index Scan**: Each worker scans a different index range
- **Parallel Hash Join**: Workers collaborate on building and probing the hash table (shared hash table in shared memory via `dynamic_shared_memory`) 
- **Parallel Aggregate**: Each worker computes a partial aggregate; leader combines them

### Barriers and Coordination

Parallel workers communicate through shared memory segments (`dynamic_shared_memory_type` in PostgreSQL). The **Gather** node acts as a barrier: it collects all partial results before proceeding to the next plan node. This is a simple but sometimes inefficient design — more sophisticated systems (e.g., exchange operators in distributed databases) allow pipelined parallelism.

## Adaptive Query Execution

Traditional query execution is **static**: the plan is fixed at optimization time. Adaptive query execution (AQE) adjusts the plan **during execution** based on observed statistics.

| Technique | How It Works | Example |
|-----------|-------------|---------|
| **Runtime filter injection** | Build side of hash join produces a Bloom filter; send to probe side to filter early | Spark AQE |
| **Join reordering** | Switch join order if an intermediate result is much smaller than estimated | SQL Server, Spark |
| **Plan switching** | Switch from nested loop to hash join mid-execution | HyPer/Umbra (research) |
| **Memory re-allocation** | Redistribute `work_mem` among operators based on actual needs | Spark AQE |

### Spark AQE (Production Example)

```
Original plan:  BigTable ⋈ SmallTable ⋈ MediumTable
                 (hash)      (hash)      (broadcast)

After AQE observes SmallTable is actually tiny:
  - Switch MediumTable join from sort-merge to broadcast hash
  - Re-allocate memory from over-provisioned join to under-provisioned one
  - Dynamically coalesce shuffle partitions if some are too small
```

PostgreSQL does **not** currently support AQE — plans are fixed once execution begins. This is a known limitation compared to systems like Spark and Snowflake.

## Interview Questions

**Q: What is the Volcano model, and why is it the most common execution model?**
A: The Volcano (iterator) model represents each plan operator as an object with `open()`, `next()`, and `close()` methods. The root operator calls `next()` on its children to pull tuples one at a time. It's popular because: (1) low first-row latency (returns results immediately), (2) low memory usage (only one tuple per operator), (3) clean operator abstraction, (4) works well with LIMIT and cursors.

**Q: Why would a hash join operator use materialization internally within a Volcano execution framework?**
A: A hash join *must* build the entire hash table before it can probe — it can't produce any output until the build side is fully read. So internally, it materializes the build relation into a hash table in memory (or spills to disk if it doesn't fit). This is a hybrid: Volcano is the outer framework, but the hash join operator materializes its input.

**Q: How does PostgreSQL parallel query divide work among workers?**
A: For a parallel sequential scan, the leader divides the table's pages among N workers. Each worker gets a disjoint block range and scans independently. Workers send partial results to the leader via a Gather node, which collects and returns them. Parallel hash joins use shared memory so workers can collaboratively build and probe a single hash table.

**Q: What is adaptive query execution and when is it useful?**
A: AQE adjusts the execution plan at runtime based on observed statistics (e.g., actual row counts, data distribution). It's useful when the optimizer's estimates are wrong — common with skewed data, correlated predicates, or stale statistics. Spark AQE is a production example: it can switch join strategies, coalesce shuffle partitions, and re-allocate memory at runtime.

**Q: A query uses `LIMIT 10` on a table with 100 million rows. Which execution model handles this best and why?**
A: The Volcano (iterator) model is ideal here. A `LIMIT 10` node only calls `next()` 10 times on its child operator. If the child is an index scan with a matching index, it might only need to read 10 index entries and 10 data pages — never scanning the full table. In a materialization model, the entire table would be scanned and materialized before LIMIT could take effect.

## References

- PostgreSQL: [Parallel Query](https://www.postgresql.org/docs/current/parallel-query.html)
- *Volcano — An Extensible and Parallel Query Evaluation System*, Graefe (1994)
- *Database Internals*, Alex Petrov — Chapter 8 (Query Optimization)
