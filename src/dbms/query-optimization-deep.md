# Query Optimization Deep Dive

A SQL query is a *declaration* of what data you want, not a
*procedure* for how to get it. The job of the query optimizer is to
close that gap: take a declarative SQL statement and produce a
physical execution plan — a tree of operators, each with a chosen
algorithm — that returns the right rows in the minimum time. This is
the hardest piece of software inside a relational database, harder
in practice than the storage engine or the transaction manager,
because the search space of plans is combinatorially explosive and
the cost estimates that drive it depend on data distributions the
optimizer cannot see directly.

This page walks the pipeline: parse → logical plan → physical plan
→ cost model → join ordering → classic rewrites → EXPLAIN ANALYZE →
prepared statements. References throughout point at PostgreSQL docs
(production-grade open-source optimizer), Petrov's *Database
Internals*, and Winand's *SQL Performance Explained*.

## From SQL to a Logical Plan

The parser produces an abstract syntax tree; the planner's first
job is to convert that AST into a **logical plan**, which is a tree
of relational-algebra operators: selection (σ), projection (π), join
(⋈), aggregation (γ), sort, union, etc. SQL is sugar over relational
algebra — almost every SQL construct has a one-to-one translation.

```
SQL:                                  Relational Algebra:
SELECT c.name, SUM(o.total)           π c.name, γ SUM(o.total)
FROM   customers c                              ⋈
JOIN   orders    o ON c.id = o.cust_id                σ c.region='EU'
WHERE  c.region = 'EU'                       ⋈ customers ⨝ orders
GROUP BY c.name                                  (c.id = o.cust_id)
ORDER BY SUM(o.total) DESC;
```

A logical plan says *what* to compute but not *how*. The selection
`σ c.region = 'EU'` doesn't yet know whether to use a sequential
scan, an index scan, or a bitmap scan. The join doesn't know whether
to be a nested loop, a hash join, or a sort-merge join. Those are
**physical** choices, made later.

## The Physical Plan: Access Methods + Join Algorithms

The physical planner walks the logical tree and assigns an
implementation to every leaf and every internal node. For a leaf
(table scan), the choices in PostgreSQL are:

| Access method            | Use case                                   |
|--------------------------|--------------------------------------------|
| Seq Scan                 | Small table, or unselective predicate     |
| Index Scan               | Selective predicate on an indexed column   |
| Bitmap Heap Scan         | Predicate matches many rows but not most  |
| Index Only Scan          | All projected columns fit in the index    |
| Tid Scan                 | `WHERE ctid = '(0,1)'`                     |
| Sample Scan              | `TABLESAMPLE`                              |

For each join node, the choices are nested-loop, hash, or
sort-merge. Each has a cost profile:

```
Nested loop:    for each row r in outer:
                   for each row s in inner:
                      if match(r, s): emit
                cost: |outer| * cost(inner_lookup)
                best when inner has a useful index and outer is small

Hash join:      build a hash table from the smaller side,
                probe with the larger side
                cost: |build| + |probe|  (in-memory)
                best when the smaller side fits in memory

Sort-merge:     sort both sides on the join key, merge
                cost: N log N + M log M + N + M
                best when both sides are already sorted (an index
                can return sorted data), or when the join is an
                inequality like a BETWEEN
```

Petrov's *Database Internals* (Chapter 4) walks through these in
the context of a generic query engine; the PostgreSQL specifics are
in the EXPLAIN documentation.

## The Cost Model: I/O + CPU

Every physical operator returns a **cost** and a **cardinality**.
PostgreSQL's `cost` field is a synthetic unit, defined as:

```
cost = seq_page_cost * seq_pages
     + random_page_cost * random_pages    (default 4.0 vs 1.0)
     + cpu_tuple_cost * tuples
     + cpu_index_tuple_cost * index_tuples
     + qualification_operator_cost * tuples_tested
```

`seq_page_cost` and `random_page_cost` model the I/O cost (a
random read is 4× a sequential read on rotational storage; on NVMe
this ratio is closer to 1.1, and you should lower the parameter).
The CPU costs are small constants that model comparison work; they
dominate only when everything is in RAM.

The harder input is **cardinality** — how many rows each operator
returns. The optimizer uses statistics collected by `ANALYZE`:
per-column histograms (most-common values, equal-width buckets),
`distinct` estimates, and correlation with the physical row order.
Multi-column estimates are notoriously bad because PostgreSQL
default statistics don't track column correlations. You can raise
`default_statistics_target` to 1000+ or use `CREATE STATISTICS` for
functional/dependencies between columns.

The famous failure mode: a query plan that worked great on 10k rows
suddenly degrades on 10M rows because the cardinality estimate was
off by 100× and the optimizer picked a hash join whose build side
no longer fits in `work_mem`. The plan was "right" given the
estimates — the estimates were wrong.

## Join Order: Left-Deep vs Bushy

For an N-way join, the number of possible binary join trees is the
Catalan number `C(N-1)` for left-deep trees, much larger for bushy
trees. PostgreSQL's dynamic-programming join planner explores all
left-deep orderings (and, since 12, full bushy trees) up to
`geqo_threshold` (default 12) tables. Beyond that, it falls back to
the GEQO genetic algorithm because DP becomes O(3^N).

```
Left-deep tree (the common shape):

              ⋈
             / \
            ⋈   D
           / \
          ⋈   C
         / \
        A   B

Bushy tree (parallel-friendly, more choices to evaluate):

              ⋈
             / \
            ⋈   ⋈
           / \ / \
          A  B C  D
```

Left-deep trees are convenient because the outer side can stream
into the inner side without materializing — the inner side becomes
an "index probe" in a nested loop. Bushy trees are better when
neither side of a join is small enough to be the outer and a hash
join can use both sides' hash tables in parallel. Modern
vectorized engines (DuckDB, ClickHouse, Peloton) lean toward
bushy because they pipeline through vectorized operators.

The dominant heuristic for the planner: **join the most selective
pairs first**. A join that filters out 90% of rows early shrinks
the cardinalities of every subsequent join. A common interview
answer ("start with the smallest table") is wrong when the smallest
table is the dimension of a star schema and the fact table is
highly filtered — there, you want the fact table's selective
predicate first.

## Predicate Pushdown

The single most important rewrite the optimizer does. If a query
has `WHERE` predicates and joins, push the predicates as close to
the leaves as possible so each input to the join is already small.

```
Before pushdown:                  After pushdown:

   π                              π
   ⋈  <─σ here                    ⋈
  / \                            / \
 ⋈   σ region='EU'              σ    σ region='EU'
/ \   |                        |     |
σ  σ  customers                π     π
|  |                           |     |
orders products                orders products
```

This is what makes `JOIN ... ON c.id = o.cust_id WHERE c.region
= 'EU'` cheap. The predicate is on `customers`, but the planner
applies it before the join — and now the join's outer side is 10
rows instead of 1M. A decent optimizer will also propagate the
implied constraint `c.id = o.cust_id AND c.region = 'EU'` into
`o.cust_id IN (SELECT id FROM customers WHERE region='EU')` if
that helps, though most engines stop at transitive closure on
equality keys.

Predicate pushdown is also why you write views with `WHERE` and
not `HAVING`: the `WHERE` is pushed into the inner scan, the
`HAVING` runs after the aggregation when the rowset has already
been computed.

## Column Pruning

A logical plan includes every column referenced anywhere in the
query, including subqueries and views. The optimizer prunes columns
the query doesn't actually need. A 100-column wide table scanned
by `SELECT name FROM users WHERE id = 42` only needs `id` (for the
predicate) and `name` (for the projection). In a column-store, that
is a 100× I/O reduction. In a row-store, it's still a CPU win
because tuple deformeding for two columns is cheaper than for
100.

The corollary: `SELECT *` is the enemy. The optimizer can prune
columns, but it can only prune what isn't referenced; `SELECT *`
references all of them. The planner is also unable to drop columns
that might be needed by a trigger, a CHECK constraint, or a
generated column dependency — so a `SELECT *` on a wide table
inside a hot path is a real performance loss.

## Subquery Flattening

A SQL query with a subquery in the FROM list, or an `IN`/`EXISTS`
subquery, is conceptually a nested execution. In practice, the
optimizer rewrites it into a join or semi-join whenever it can.
The rules are:

- Subqueries in `FROM` are flattened into the parent join graph
  (PostgreSQL: `pull_up_subqueries`).
- `IN`/`EXISTS` are rewritten as `Semi Join` (one row from the
  outer side per matching inner side, no duplicates).
- `NOT IN`/`NOT EXISTS` are rewritten as `Anti Join`.
- Scalar subqueries in the SELECT list may be flattened if the
  planner can prove they return at most one row.

```sql
SELECT c.name
FROM   customers c
WHERE  c.id IN (SELECT cust_id FROM orders WHERE total > 1000);
-- Flattened to:
SELECT c.name
FROM   customers c
SEMI JOIN orders o ON (c.id = o.cust_id AND o.total > 1000);
```

This is the reason correlated subqueries aren't as catastrophic as
textbook cost models suggest — they get rewritten before they hit
the executor. The trap is when flattening *fails*: an uncorrelated
subquery with a `LIMIT`, a `GROUP BY` on a function, or a `UNION`
inside the subquery blocks flattening and the planner falls back
to "init plan once, execute per outer row". Watch for
`SubPlan` or `InitPlan` in `EXPLAIN` output — those are unflattened
and probably slow.

## EXPLAIN and EXPLAIN ANALYZE

`EXPLAIN` shows the chosen plan and the estimated costs and
cardinalities. `EXPLAIN ANALYZE` actually executes the plan and
reports the real cost and cardinalities, plus timing per node.

```
EXPLAIN ANALYZE
SELECT c.name, SUM(o.total)
FROM   customers c
JOIN   orders    o ON c.id = o.cust_id
WHERE  c.region = 'EU'
GROUP BY c.name;

→  HashAggregate  (cost=1234.56..1250.00 rows=200 width=40)
        (actual time=45.23..46.10 rows=187 loops=1)
    Group Key: c.name
    Planned Rows: 200  Actual Rows: 187   ← estimate close
    ->  Hash Join  (cost=400.00..1200.00 rows=3000 width=40)
            (actual time=12.34..40.50 rows=2987 loops=1)
        Hash Cond: (c.id = o.cust_id)
        ->  Seq Scan on customers c  (cost=0.00..200.00 rows=50 width=36)
                (actual time=0.50..5.00 rows=48 loops=1)
                Filter: (region = 'EU')
                Rows Removed by Filter: 9952   ← 99% filtered, seq scan OK
        ->  Hash  (cost=200.00..200.00 rows=10000 width=12)
                (actual time=10.00..10.00 rows=10000 loops=1)
                Buckets: 16384  Batches: 1  Memory Usage: 480kB
            ->  Seq Scan on orders o  (cost=0.00..200.00 ...)
                    (actual time=0.20..7.00 rows=10000 loops=1)
Planning Time: 1.234 ms
Execution Time: 46.50 ms
```

Two columns matter more than the rest: **Planned Rows vs Actual
Rows**. When they disagree by an order of magnitude, the
cardinality estimate is wrong and you should `ANALYZE` the table or
raise statistics. When the *plan* shape is wrong, the estimate is
right but the cost model is misleading you — tune
`random_page_cost` or `work_mem`.

The other give-away is the **loops** field. A nested loop with
`loops=10000` and `actual time=0.01..0.02` is 200 ms of work, not
0.02 ms — multiply per-node time by `loops`.

## Prepared Statements: Parameterized vs Adaptive Plans

A prepared statement is `PREPARE q AS SELECT ... WHERE id = $1`
and then `EXECUTE q(42)`. The optimization happens once at
`PREPARE` time, then the plan is reused for every `EXECUTE`. The
benefit: parse + optimize happen once per session. The cost: the
planner doesn't know the parameter values when picking the plan,
only their types.

This creates a **parameterized plan** that has to be good for *any*
value of `$1`. If your data is skewed — 99% of queries filter on
`status = 'shipped'` (which should seq-scan) but 1% on
`status = 'pending'` (which should index-scan) — a single generic
plan is mediocre for both. PostgreSQL 12+ mitigates this with a
**generic + custom plan mix**: the first five executions build
custom plans (with the literal values), then the planner compares
the average custom-plan cost to the generic-plan cost and locks
into the generic plan if it's within 10%. This is the
`plan_cache_mode` setting.

```sql
PREPARE q(text) AS SELECT * FROM orders WHERE status = $1;

-- First five EXECUTEs each build a custom plan with the actual
-- value; PostgreSQL records their costs.
EXECUTE q('pending');
EXECUTE q('shipped');
...

-- From the sixth EXECUTE on, the planner reuses one generic plan.
-- If you want to force custom plans per call:
SET plan_cache_mode = 'force_custom_plan';
```

The general rule: short-lived statements (ad-hoc queries) don't
benefit much from prepared plans because the parse cost is tiny
compared to execution; long-lived statements on the hot path
benefit enormously. The trap is plan-skew workloads (the
`status` example above) — test both modes.

## Comparison: Logical vs Physical vs Adaptive

| Stage            | Input            | Output         | Decides                       |
|------------------|------------------|----------------|-------------------------------|
| Parser           | SQL text         | AST            | Syntax                        |
| Logical planner  | AST              | Rel-alg tree   | Relational meaning            |
| Physical planner | Rel-alg tree     | Operator tree  | Algorithms, access paths     |
| Cost model       | Stats, params    | Cost numbers   | Cheap vs expensive           |
| Adaptive runtime | Actual cardinality | Re-plan      | Fix wrong estimates (12c+)   |

PostgreSQL's adaptive planning is conservative; Oracle's adaptive
plans (since 12c) can switch join methods and parallelism at
runtime based on observed cardinality. SQL Server has "adaptive
joins" since 2017. The trend in the 2020s is to move more of the
optimizer's decisions into the runtime — the cost model's
estimates are the main source of bad plans, and runtime decisions
remove that source entirely at the cost of overhead.

## Pitfalls

1. **Stale statistics.** `ANALYZE` is run by `autovacuum` with a
   default threshold of 10% rows changed. On a fast-growing
   append-only table, that's too rare. Run `ANALYZE` after every
   bulk load.
2. **`SELECT *`** forces the optimizer to scan and materialize every
   column, defeating column pruning and widening the row that
   flows through every operator.
3. **Holding uncorrelated subqueries unflattened.** A `LIMIT` inside
   a subquery prevents flattening; remove the `LIMIT` or rewrite as
   a join.
4. **Forgetting `ANALYZE` after a major change.** Adding an index
   or `ALTER TABLE` can leave planner stats stale; the new index
   won't get picked because the planner doesn't trust it.
5. **Trusting `EXPLAIN` over `EXPLAIN ANALYZE`.** Cost numbers in
   `EXPLAIN` are estimates; only `ANALYZE` gives ground truth.
6. **One generic plan for skewed workloads.** Test with
   `plan_cache_mode = 'force_custom_plan'` and benchmark.
7. **Setting `work_mem` too low.** Hash joins that spill to disk
   are catastrophic; a query that took 50 ms with `work_mem=64MB`
   can take 5 s with `work_mem=4MB` and the plan looks identical in
   plain `EXPLAIN`.

## Interview Questions

### Q: Walk through what happens between `SELECT` and result rows.

Parse → logical plan (rel-alg tree) → rewrite (subquery
flattening, predicate pushdown, column pruning) → physical plan
(assign each operator an algorithm) → cost model picks the
cheapest physical plan via dynamic programming over join orders
→ executor runs the plan, often pipelined.

### Q: When does PostgreSQL pick a Hash Join vs a Nested Loop?

Hash join when (a) the join is equi-join, (b) the smaller side fits
in `work_mem`, and (c) the inner side has no useful index for
the join key. Nested loop when the inner side has a selective index
on the join key (each probe is one or two page reads), or when the
outer side is small enough that the `O(N×M)` work is still cheap.
Sort-merge when both sides are already sorted (an index returns
sorted rows) or the join is an inequality.

### Q: How would you diagnose a slow query?

`EXPLAIN (ANALYZE, BUFFERS)` — look for (1) where the actual time
is spent, (2) where Planned Rows and Actual Rows diverge, (3)
whether the buffers were mostly hits or misses, (4) whether the
join type is right for the cardinalities. Fix the cardinality first
(`ANALYZE`, raise statistics), then look at indexes, then at
`work_mem`.

### Q: Why is a prepared statement slower than the same ad-hoc query?

A generic plan can't peek at parameter values. If the parameter
distribution is skewed, the generic plan is mediocre for both
sides of the distribution. Force custom planning or rewrite as
dynamic SQL.

## References

- PostgreSQL Documentation, "[Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)" — node types, cost fields, `loops`, `buffers`, and the meaning of `Planned Rows` vs `Actual Rows`.
- PostgreSQL Documentation, "[Planner and Optimizer](https://www.postgresql.org/docs/current/planner-optimizer.html)" — how the planner explores join orders, GEQO, and the genetic algorithm fallback.
- PostgreSQL Documentation, "[Statistics Used by the Planner](https://www.postgresql.org/docs/current/planner-stats.html)" — `pg_statistics`, `default_statistics_target`, `CREATE STATISTICS` for multi-column correlations.
- Alex Petrov, *Database Internals: A Deep Dive into How Distributed Data Systems Work* (O'Reilly, 2019), Chapter 4 "Query Planning" and Chapter 5 "Execution" — the algorithmic foundation common to PostgreSQL, MySQL, and SQLite.
- Markus Winand, *SQL Performance Explained*, [use-the-index-luke.com](https://use-the-index-luke.com/) — chapters on "The Join Operation", "Predicate Evaluation", and "Clustered & Non-Clustered Indexes" explain the cardinality-vs-cost interaction that drives plan choice.
- PostgreSQL Documentation, "[PREPARE](https://www.postgresql.org/docs/current/sql-prepare.html)" — parameterized plans, custom vs generic plan selection, `plan_cache_mode`.
- Tom Lane, "[Postgres Explain Plans](https://www.postgresql.org/docs/current/using-explain.html)" talk notes — the canonical explanation of `loops` and per-node timing.

## Related Topics

- [Query Processing: Optimization](./query-processing/optimization.md) — the chapter this deep dive extends.
- [Query Processing: Cost Estimation](./query-processing/cost-estimation.md) — the cost model in isolation.
- [Indexing Strategy](./indexing-strategy.md) — the access methods the physical planner picks among.
- [Advanced: Cascades Optimizer](./advanced/cascades-optimizer.md) — the next-generation optimizer architecture.
- [Advanced: Volcano Optimizer](./advanced/volcano-optimizer.md) — the classical extensible optimizer framework.
- [Query Processing: Joins](./query-processing/joins.md) — nested loop, hash, sort-merge in isolation.
