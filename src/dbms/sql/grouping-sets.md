# GROUPING SETS, ROLLUP, and CUBE: Multi-Dimensional Aggregation

One `GROUP BY` answers one question: "total sales per region." Dashboards answer
hundreds at once — per region, per month, per region-and-month, plus a grand
total — and running four separate `GROUP BY` queries means four scans, four
sorts, and four result sets the application must stitch together. The
`GROUPING SETS` family (SQL:1999) makes the multi-dimensional aggregation a
single declarative statement that the engine can compute in one pass.
This page covers the semantics, the NULL-ambiguity problem, the `GROUPING()` /
`GROUPING_ID()` bitmasks, how engines execute it, and the traps interviews probe.

Where plain OLAP warehousing and star schemas live, see
[OLTP vs OLAP & Data Warehousing](../analytics/README.md); pre-aggregated
rollup tables as a physical-design choice are in
[Denormalization](../normalization/denormalization.md).

## The semantics: one GROUP BY, many grouping sets

A grouping set is any subset of the GROUP BY columns (including the empty set).
`GROUPING SETS ((a,b), (a), (b), ())` aggregates the input once per listed set
and concatenates the outputs — exactly as if four queries had been run and
`UNION ALL`-ed, but the engine scans the input once and may share the sort or
hash across sets.

```sql
SELECT brand, size, sum(sales) AS s
FROM items_sold
GROUP BY GROUPING SETS ((brand), (size), ());
```

```text
 brand | size | sum
-------+------+-----
 Foo   |      |  30     -- grouped by brand only
 Bar   |      |  20
       | L    |  15     -- grouped by size only
       | M    |  35
       |      |  50     -- empty set: the grand total
```

Two semantic details matter more than the syntax:

- **Columns absent from a set are replaced by NULL** in that set's rows. The
  empty set `()` aggregates everything into one grand-total row — and it is
  emitted even when the input is empty (the same rule as a bare aggregate
  query).
- **Order of output is not defined.** `ROLLUP` results arriving in
  "drill-path" order is a common illusion caused by sort-based execution;
  adding an `ORDER BY` changes the plan, often destroying the shared-sort
  optimization.

## ROLLUP and CUBE are shorthand

`ROLLUP ( e1, e2, e3 )` expands to the list plus all **prefixes** plus the
empty set — the hierarchy drill-down path (company → division → department →
total). `CUBE ( e1, e2, e3 )` expands to **all 2^n subsets** — every
combination of dimensions, which is why a 12-column cube is a mistake rather
than a query: 4096 grouping sets, most of them meaningless.

```sql
ROLLUP(a, b, c)  =  GROUPING SETS ((a,b,c), (a,b), (a), ())
CUBE(a, b, c)    =  GROUPING SETS ((a,b,c), (a,b), (a,c), (a),
                                   (b,c),   (b),   (c),   ())
```

Composite elements act as single units:

```sql
ROLLUP( (a,b), c )   =  GROUPING SETS ((a,b,c), (a,b), ())
CUBE( (a,b), (c,d) ) =  GROUPING SETS ((a,b,c,d), (a,b), (c,d), ())
```

Finally, **multiple grouping items multiply**: `GROUP BY a, CUBE(b,c)` produces
the Cartesian product of `{a}` with the cube's sets. `GROUP BY ROLLUP(a,b),
ROLLUP(a,c)` yields 9 sets, three of them duplicates — PostgreSQL 16+ can
deduplicate them with `GROUP BY DISTINCT ROLLUP(a,b), ROLLUP(a,c)`, which is
not the same as `SELECT DISTINCT` (that would also collapse legitimately
duplicate output rows).

## The NULL ambiguity problem

A subtotal row's NULL means "all values collapsed"; a data NULL means "value
unknown." They are indistinguishable in the output:

```sql
-- Was this row "brand = NULL" from the data, or the brand-subtotal row?
-- You cannot tell from (brand, size, sum) alone.
```

This is not a rendering bug — it is a lossy encoding. Every real dashboard that
sends grouping-set output to the client must solve it, and SQL standardizes the
solution as a bitmask:

## GROUPING() and GROUPING_ID(): the row's coordinate system

`GROUPING(a, b, ...)` returns an integer bitmask: bit *k* is 1 if the *k*-th
argument **was not** part of the grouping set for this row, 0 if it was.
PostgreSQL assigns the rightmost argument the least-significant bit.

```sql
SELECT make, model, GROUPING(make, model) AS g, sum(sales)
FROM items_sold
GROUP BY ROLLUP(make, model);
```

```text
 make  | model | g | sum
-------+-------+---+-----
 Foo   | GT    | 0 |  10     -- both columns grouped (detail row)
 Foo   | Tour  | 0 |  20
 Bar   | City  | 0 |  15
 Bar   | Sport | 0 |   5
 Foo   |       | 1 |  30     -- model collapsed (make-subtotal)
 Bar   |       | 1 |  20
       |       | 3 |  50     -- both collapsed (grand total)
```

With the mask, labels and client-side pivoting become deterministic:

```sql
SELECT CASE GROUPING(make, model)
         WHEN 0 THEN 'detail'
         WHEN 1 THEN 'make subtotal'
         WHEN 3 THEN 'grand total'
       END AS row_type,
       coalesce(make, '<all>') AS make_label,
       sum(sales)
FROM items_sold
GROUP BY ROLLUP(make, model);
```

Engine naming differs and interviews use the differences as gotchas:

| Engine | Multi-arg function | Notes |
|---|---|---|
| PostgreSQL, Oracle, SQL Server | `GROUPING(a,b,...)` / `GROUPING_ID(a,b,...)` | SQL Server's `GROUPING_ID` concatenates per-arg bits into one integer; `GROUPING()` takes exactly one argument |
| MySQL | `GROUPING()` (8.0+) | `WITH ROLLUP` only — no `CUBE`, no `GROUPING SETS` |
| Spark SQL | `GROUPING__ID` (no underscore) | legacy Hive naming; bit order differs from `GROUPING_ID` — a classic migration bug |
| Snowflake | `GROUPING_ID(...)` | grouping-bit conventions documented per-engine |

**Interview trap:** in Spark, `GROUPING__ID`'s bit for a column is the inverse
of what most engineers assume, and the bit order follows the *column position
in the group-by list*, reversed relative to SQL Server's convention. Porting
dashboard filters across engines silently mislabels subtotal rows.

## How engines execute it

Execution strategy determines performance more than syntax:

- **Sort-based (PostgreSQL default):** sort once on the superset of grouping
  columns, then aggregate "on the fly" for every prefix that is a leading
  subset of the sort key. A `ROLLUP(a,b,c)` costs one sort + one scan; the
  plan shape is `Sort → GroupAggregate` with incremental grouping. Arbitrary
  `GROUPING SETS ((b),(a))` that share no prefix structure can force repeated
  sorts — the engine either re-sorts per set or materializes a tuplestore.
- **Hash-based (Spark, SQL Server, Snowflake):** one shuffle/hash per grouping
  set, or a single pass with a composite key `(set_id, dims)`. Spark's
  `Expand` operator *duplicates every input row N times* — once per grouping
  set, tagged with a `groupByIndex` column — then runs one normal hash
  aggregate. A cube over 4 dimensions makes Spark read 16× more rows through
  the aggregate; this is why pre-partitioning and column pruning matter so
  much in Spark cube jobs.
- **Pre-aggregation / storage-level:** materialized views, Kimball
  aggregate-fact ("rollup") tables, or engine features (Snowflake materialized
  views; ClickHouse materialized views) precompute the hot cube slices. When
  the query pattern is fixed (e.g., region×month rollups refreshed nightly),
  storing subtotals beats recomputing them — the classic trade-off in
  [Denormalization](../normalization/denormalization.md).

```text
Spark plan (GROUPING SETS (brand), (size), ()):

Exchange (hash)                          ← 3× row duplication happens here
  +- Expand [sales, brand, null, 0],     ← every row emitted 3 times
             [sales, null, size, 1],
             [sales, null, null, 2]
      +- Scan items_sold
```

The `Expand`-then-aggregate trick is worth remembering in interviews because
it shows grouping sets are *syntax over a row-multiplication + aggregate
pipeline* — nothing more exotic than a `GROUP BY` on `(set_id, dims)`. The same
rewrite is what analysts do by hand with `UNION ALL`, and the optimizer can
even convert a grouping-set query back into multi-child `Aggregate` with
common subplan reuse.

## Realistic interview problems

**1. Totals without NULLs leaking into joins.** A dashboard joins the
grouping-set result back to a dimension table on `brand`. Subtotal rows
(NULL brand) fan out against every brand row — the classic
[duplicate multiplication](../interview-problems/join-problems.md) bug.
Fix: filter each level (`WHERE GROUPING(brand) = 0`) or join with
`brand IS NOT NULL` guardrails.

**2. Top-N products per region plus a per-region "OTHER" bucket — with the
grand total consistent.** Combine `GROUPING SETS` for the total with a
windowed top-N:
`GROUP BY GROUPING SETS ((region, product), (region), ())` then
`ROW_NUMBER() OVER (PARTITION BY region ORDER BY s DESC)` — collapsing
"other" *after* the aggregate preserves the exact total; aggregating first
and summing the tail in a second pass is usually cleaner than trying to do
both in one statement.

**3. Empty input must still show the grand total.** `GROUP BY GROUPING SETS(())`
emits one row over an empty input (matching bare-aggregate semantics), while
`GROUP BY GROUPING SETS ((a), ())` emits only the grand total. Interviewers
use this to check whether candidates understand that an empty grouping set is
an aggregate over *all* rows, not "no rows."

**4. HAVING vs the mask.** `HAVING sum(sales) > 100` filters every level
including subtotals; `HAVING (GROUPING(size) = 1 OR sum(sales) > 100)` keeps
all subtotal rows regardless of their sums. Knowing that `HAVING` runs
*after* each grouping set's aggregation makes these predicates reason-able
rather than memorized.

## Key Takeaways

- `GROUPING SETS` = "aggregate per listed subset, concatenate"; `ROLLUP` =
  prefixes (hierarchies), `CUBE` = power set (2^n sets — dimension-count
  explosion is real).
- A subtotal NULL and a data NULL are indistinguishable without
  `GROUPING()`/`GROUPING_ID()` — dashboards that skip the mask are
  shipping mislabeled rows.
- Execution: PostgreSQL shares one sort for prefix-structured sets; Spark
  expands rows N× before aggregating; fixed rollup patterns should be
  materialized instead.
- MySQL supports only `WITH ROLLUP`; bit conventions of `GROUPING_ID` differ
  per engine — verify before porting.

## Cross-References

- [Window Functions](./window-functions.md) — ranking inside aggregated results; complementary, not overlapping.
- [Denormalization](../normalization/denormalization.md) — pre-computed rollup tables vs on-the-fly cubes.
- [OLTP vs OLAP & Data Warehousing](../analytics/README.md) — where grouping-set queries live in the workload.
- [Columnar Formats](../advanced/columnar-formats.md) — why columnar engines make wide cubes cheaper.
- [Classic Problems](../interview-problems/classic-problems.md) — companion interview problem sets.

## References

- J. Gray, S. Chaudhuri, A. Bosworth, A. Layman, D. Reichart, M. Venkatrao, F. Pellow, H. Pirahesh, "[Data Cube: A Relational Aggregation Operator Generalizing Group-By, Cross-Tab, and Sub-Totals](https://doi.org/10.1023/A:1009726021843)", *Data Mining and Knowledge Discovery* 1(1), 1997 (also ICDE 1996, [doi:10.1109/ICDE.1996.492099](https://doi.org/10.1109/ICDE.1996.492099)) — the CUBE/ROLLUP paper.
- PostgreSQL Documentation, "[GROUPING SETS, CUBE, and ROLLUP](https://www.postgresql.org/docs/current/queries-table-expressions.html)" and "[Grouping Operations](https://www.postgresql.org/docs/current/functions-aggregate.html)" — exact semantics of `GROUPING()`, composite elements, and `GROUP BY DISTINCT`.
- Microsoft Learn, "[GROUP BY (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/queries/select-group-by-transact-sql)" and "[GROUPING (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/functions/grouping-transact-sql)".
- Apache Spark, "[Aggregate Functions / GROUP BY](https://spark.apache.org/docs/latest/sql-ref-syntax-qry-select-groupby.html)" — documents `Expand`-based execution and `GROUPING__ID`.
- Snowflake Documentation, "[GROUP BY](https://docs.snowflake.com/en/sql-reference/constructs/group-by)" — grouping sets and `GROUPING_ID` conventions.
- Oracle Database 19c SQL Reference, "[SELECT](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/SELECT.html)" — `ROLLUP`/`CUBE`/`GROUPING_ID` in Oracle.
