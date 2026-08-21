# Spanner SQL Execution

Spanner's SQL layer (introduced in 2014 and described in the 2017 SIGMOD paper "Spanner: Becoming a SQL System") sits on top of the Paxos-replicated tablet storage. It supports standard SQL (with extensions like STRUCT, ARRAY, and proto-typed columns), distributed joins, vectorized execution, and parallel query execution across thousands of tablets. This page covers the SQL compilation pipeline, the distributed execution model, and the cost model that makes Spanner's distributed SQL practical.

## The Compilation Pipeline

A SQL query goes through five phases:

```text
SQL text
  │
  ▼
1. Lexer/parser (ZetaSQL, Google's SQL parser)
  │   - Tokenizes, builds AST
  │   - Resolves names (table/column references)
  │
  ▼
2. Logical plan
  │   - AST → algebra (Scan/Filter/Join/Aggregate)
  │   - View merging, predicate pushdown, subquery flattening
  │
  ▼
3. Optimizer (Cascades-style, ~80 rules)
  │   - Join reordering
  │   - Push-down of filters and projections
  │   - Choice of join algorithm (Hash vs. Merge vs. Cross-Apply)
  │   - Choice of scan path (table scan vs. index)
  │
  ▼
4. Physical plan (distributed)
  │   - Distributed across tablets via hash/range partitioning
  │   - Identifies pipeline breakers (sort, agg, hash join)
  │   - Generates RPC plan operators
  │
  ▼
5. Execution
  │   - Each stage runs on a set of CPU workers
  │   - Intermediate results shipped via RPC
  │   - Final stage returns results to client
```

The optimizer is **cost-based**: each rule application has an estimated cost (I/O + CPU + network), and the optimizer picks the cheapest. Cost estimates come from per-table statistics (row count, histogram, distinct value count).

## Distributed Execution Model

A Spanner SQL plan is a DAG of **stages**, each running on multiple workers:

```text
                   Stage 1: Scan(orders, filter=total>100)
                            (parallel across 1000 tablets)
                            ↓ emit batches of (order_id, total) tuples
                            ↓ via RPC
                   Stage 2: HashJoin(customers, scan_orders,
                                      on=customer_id)
                            (parallel on 100 workers, hash on customer_id)
                            ↓ emit joined tuples
                            ↓ via RPC
                   Stage 3: HashAgg(group_by=region,
                                     sum=total)
                            (parallel on 50 workers, hash on region)
                            ↓ emit (region, sum) pairs
                            ↓ via RPC
                   Stage 4: Sort(region, sum DESC)
                            ↓ emit top 10
                            ↓
                  Result stage (1 worker)
                            ↓
                       Send to client
```

Each stage:
- Has a **distribution** (parallelism and partitioning key).
- Receives input from upstream stages via RPC.
- Emits output to downstream stages via RPC.
- May buffer intermediates to disk if they exceed memory.

The stage boundaries are **pipeline breakers**: stages where the operator must consume all input before producing output. Sort, HashAgg, and HashJoin are pipeline breakers. Filter, Project, and Map are not — they pass tuples through as they arrive.

## Vectorized Execution

Each operator processes batches of tuples (~1024 per batch) rather than one tuple per call. The execution engine:

```text
Operator::Next(batch_out) {
    batch_in = child->Next();
    if (batch_in.size == 0) return 0;
    
    // SIMD: filter all 1024 tuples in ~5 instructions
    mask = SIMD_filter(batch_in.age, >, 30);
    
    // Selection vector: indices of surviving tuples
    batch_out = project(batch_in, mask);
    return batch_out.size;
}
```

The vectorized model achieves 10-100× the throughput of the classical Volcano model (one tuple per `next()`) for analytical workloads. For more on the vectorized execution model, see the [Vectorized Execution](./vectorized-execution.md) page.

## Distributed Join Strategies

Spanner supports three join algorithms, chosen by the optimizer:

### 1. Hash Join

The "build" side is read into memory as a hash table; the "probe" side streams through, looking up matches. Best when one side is small enough to fit in memory.

```text
Build side (smaller)             Probe side (larger)
   │                                │
   ▼                                ▼
HashPartition(N) by join_key     HashPartition(N) by join_key
   │                                │
   ▼                                ▼
For each partition p:              For each partition p:
  Build hash table                  For each tuple t:
                                      Look up in hash table
                                      Emit matches
```

The hash partitioning is the key: both sides are partitioned by the join key, so all matching tuples land on the same worker. Spanner uses this when the build side fits in ~100 MB of memory.

### 2. Distributed Merge Join

Both sides are sorted by the join key. Two sorted streams are merged in lockstep. Best when both sides are already sorted (e.g., primary-key joins).

```text
Side A (sorted)            Side B (sorted)
   │                          │
   ▼                          ▼
Stream A: a1, a2, a3, ...   Stream B: b1, b2, b3, ...
   │                          │
   └──── merge join ──────────┘
              │
              ▼
        (a1, b1), (a2, b1), (a3, b2), ...
```

Merge join is the only join that doesn't need to buffer the entire build side, so it's preferred for very large joins where neither side fits in memory.

### 3. Cross Apply (a.k.a. Nested Loop Join with subquery)

For each tuple on the "outer" side, execute a subquery that fetches matching tuples from the "inner" side. Best when the inner side is an index lookup (e.g., "for each order, look up the customer by primary key").

```sql
SELECT * FROM orders o, customers c WHERE o.customer_id = c.id;
```

Becomes (conceptually):

```text
For each order o:
    c = SELECT * FROM customers WHERE id = o.customer_id;
    Emit (o, c);
```

Cross Apply is the preferred join when the inner side is an indexed lookup that returns 0 or 1 row. It's much faster than a hash join for high-cardinality joins (one order per customer = millions of lookups).

## Interleaved Tables

Spanner's `INTERLEAVE` clause co-locates child rows with their parent rows. A `SELECT * FROM orders JOIN order_items ON orders.id = order_items.order_id` can be served by a single tablet scan when `order_items` is interleaved in `orders`:

```sql
CREATE TABLE orders (id INT64, customer_id INT64) PRIMARY KEY (id);
CREATE TABLE order_items (
  order_id INT64,
  item_id INT64,
  sku STRING(20),
  quantity INT64
) PRIMARY KEY (order_id, item_id), INTERLEAVE IN PARENT orders;
```

The interleaving means `order_items` rows are physically stored adjacent to their parent `orders` row. A query that joins them is a single-tablet read.

For non-interleaved joins, Spanner distributes the work across multiple workers and uses RPC to ship intermediate results. The optimizer picks the algorithm (Hash/Merge/Cross Apply) based on cardinality estimates.

## Cardinality Estimation

The optimizer's cost model depends on cardinality estimates. Spanner maintains:

- **Per-table row counts**: refreshed periodically by the optimizer.
- **Column histograms**: top-N values + bucketed distribution.
- **Distinct value counts**: for join cardinality estimation.

For estimates, Spanner uses both classical statistics and learned models (since 2020): a machine-learned model trained on past query execution statistics predicts the cardinality of new queries. The learned model is more accurate than the classical statistics for complex queries.

## Cost Model

Each operator has a cost function:

```text
Cost(op) = startup_cost + per_tuple_cost * cardinality
            + per_byte_io * bytes_read
            + per_rpc_cost * rpc_count
```

The RPC cost is significant: each RPC has ~100 µs of latency, so a plan that does 1000 RPCs per query adds 100 ms of latency. The optimizer prefers plans with fewer RPCs, even at the cost of more local compute.

For example, a 2-table join can be:

- **Hash join** (1 RPC per partition): 100 partitions × 1 RPC = 100 RPCs.
- **Cross apply** (1 RPC per outer tuple): 1M outer tuples × 1 RPC = 1M RPCs.

For a query that returns 1M joined tuples, Cross Apply is 10,000× more RPCs than Hash Join, and the optimizer correctly picks Hash Join.

## Common Pitfalls

1. **Using secondary indexes without thought.** A secondary index forces an extra RPC per row read (the index scan + the table fetch). For range queries that scan many rows, a table scan is faster.

2. **Forgetting that INTERLEAVE is not a join optimization.** INTERLEAVE optimizes physical storage, not query plans. A query that doesn't use the parent's primary key won't benefit from interleaving.

3. **Cross-Apply on a high-cardinality join.** A query that does 1M customer-id lookups will be slow because of the 1M RPCs. Use a hash join instead.

4. **Not setting `LIMIT` early.** Without `LIMIT`, the optimizer estimates cardinality as if all rows are returned. Adding `LIMIT 10` lets the optimizer pick a plan that returns 10 rows quickly.

5. **Hash aggregations with skew.** A group-by on a low-cardinality column (e.g., `country` with 200 values) hash-partitions to 200 keys, but if 80% of rows are in `country='US'`, one worker is overwhelmed. Use `skew handling` or repartition.

## References

- [Spanner: Becoming a SQL System](https://research.google/pubs/pub47702/) (SIGMOD 2017)
- Wilson Wu et al., "[Spanner: A New SQL System](https://research.google/pubs/pub46902/)" (VLDB 2014)
- [ZetaSQL: Spanner's SQL parser and analyzer](https://github.com/google/zetasql)
- [Spanner SQL documentation](https://cloud.google.com/spanner/docs/query-statistics)
- [Spanner SQL query plans](https://cloud.google.com/spanner/docs/query-plans)
- [Spanner: Distributed SQL Execution (Google Cloud Next 2019)](https://www.youtube.com/watch?v=AlizeZsghZo)
- Goetz Graefe, "[Volcano/Cascades query optimization](https://www.cse.iitb.ac.in/infolab/Data/Courses/CS632/2007-Papers/Cascades-graefe.pdf)" — the framework Spanner uses
