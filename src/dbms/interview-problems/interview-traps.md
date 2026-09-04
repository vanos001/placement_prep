# SQL Interview Traps: Queries That Look Right but Aren't

These are the traps that survive into production because the query *runs*,
returns *plausible* rows, and fails only on data shapes the author didn't
have on their screen. Each entry follows the same anatomy: what looks right,
what actually happens, and the fix. Deep background lives in the linked
pages; this page is the consolidated map interviewers walk through in
screening rounds.

## COUNT(*) vs COUNT(column)

```sql
SELECT COUNT(*), COUNT(manager_id) FROM employees;
--              100                 62
```

`COUNT(*)` counts rows; `COUNT(col)` counts rows where `col IS NOT NULL`.
Both are correct queries — the trap is using `COUNT(col)` to answer a
"how many rows" question on a nullable column, or reporting "COUNT(*) is
slower" from folklore. Engines special-case `COUNT(*)` (no column
dereference, and InnoDB's optimized primary-key-only traversal), so it is
usually the *cheapest* of the two. `COUNT(DISTINCT col)` also drops NULLs —
relevant when a NULL means "unknown", not "zero".

## NOT IN + NULL: the empty-result bug

```sql
SELECT name FROM shipments
WHERE invoice_id NOT IN (SELECT invoice_id FROM invoices);
-- 0 rows — forever — if invoices contains ONE NULL invoice_id
```

With a NULL in the subquery, every `invoice_id NOT IN (...)` comparison
evaluates to UNKNOWN (three-valued logic — see
[Null Semantics](../null-semantics.md)), so `WHERE` filters everything out.
The result is not "wrong rows"; it is *silently no rows*, which reads as a
data problem rather than a query bug. `NOT EXISTS` is immune:

```sql
SELECT name FROM shipments s
WHERE NOT EXISTS (SELECT 1 FROM invoices i WHERE i.invoice_id = s.invoice_id);
```

`NOT EXISTS` also plans better in most engines (anti-join). Make it the
default; use `NOT IN` only when the column is provably `NOT NULL`.

## LEFT JOIN quietly degraded to INNER JOIN

```sql
SELECT c.name, sum(o.amount)
FROM customers c
LEFT JOIN orders o ON o.cust_id = c.id
WHERE o.currency = 'USD'          -- ← kills the LEFT JOIN
GROUP BY c.name;
```

The WHERE clause runs *after* the join; customers with no USD orders have
NULL in `o.currency`, NULL fails the predicate, and the row disappears —
you wrote a left join and got an inner join. The fix moves the predicate
into the join condition (`LEFT JOIN orders o ON o.cust_id = c.id AND
o.currency = 'USD'`), or tests the NULL explicitly (`WHERE o.id IS NULL`
for the anti-join case). The same trap inverted: `ON c.id = c.id`-style
typos in inner joins produce silent cartesian explosion instead of errors.

## Duplicate multiplication, and DISTINCT as a band-aid

Joining order lines to shipments (both many-to-one from different sides)
multiplies rows; `sum(amount)` is now wrong and the fix people reach for is
`SELECT DISTINCT` — which masks the fan-out instead of fixing it, and
silently merges legitimate duplicate rows (a "bad data" symptom turned into
a query). The correct reflex: aggregate each side *before* joining, or
prove the relationship is 1:1. Worked examples are in
[Join Problems](./join-problems.md).

## GROUP BY mistakes

- **Selecting non-grouped columns.** Standard SQL forbids it; MySQL allows
  it with arbitrary per-group values unless `ONLY_FULL_GROUP_BY` is set
  (default since 5.7) — and the *deterministic-looking* result on small
  test data hides the nondeterminism on real data.
- **WHERE vs HAVING.** `WHERE` filters rows before grouping (can use
  indexes); `HAVING` filters groups after aggregation (cannot). Putting
  row filters in `HAVING` wastes the aggregation input; putting group
  filters in `WHERE` is a syntax error.
- **GROUP BY expression mismatch.** `GROUP BY DATE(created_at)` with
  `SELECT created_at` groups by day but selects the raw timestamp — the
  displayed value is one arbitrary row's timestamp. Group and project the
  same expression.

## LAST_VALUE and the default window frame

```sql
SELECT LAST_VALUE(salary) OVER (ORDER BY month) ...   -- WRONG frame
```

The default frame with `ORDER BY` is
`RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, so `LAST_VALUE`
returns the current row's value — the function looks broken but the frame
is the bug. Fix:
`ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`. Frame
semantics, ties, and the GROUPS mode are dissected in
[Window Functions](../sql/window-functions.md); the sibling trap (running
totals that double-count ties) comes from the same default frame.

## Non-SARGable predicates: functions that disable indexes

```sql
WHERE DATE(created_at) = '2026-01-01'   -- scans; applies function per row
WHERE created_at >= '2026-01-01' AND created_at < '2026-01-02'  -- seeks
```

A predicate is SARGable (search-argument-able) when the column stands
*unwrapped* on the indexed side. Functions, implicit casts
(`varchar_col = 123`), and leading-wildcard `LIKE '%x'` all defeat B-tree
range descent (see [B+ Tree](../indexing/b-plus-tree.md) for why: the
index orders by the raw value, so a transformed value has no position in
the index). The implicit-cast variant is nastiest — it *also* can silently
change semantics (string→number comparison rules).

## Composite index column order

`(a, b)` serves `WHERE a = ?`, `a = ? AND b = ?` — and `b = ?` alone gets
nothing but a full scan. Order matters most under mixed predicates: equalty
columns first, then the range column last (a range stops the second
column's usefulness). Covered with examples in
[Composite Index](../indexing/composite-index.md) and
[Index Tuning](../indexing/tuning.md). The interview version: "the index
exists — why isn't it used?" is usually either non-SARGability or column
order, and `EXPLAIN` answers which.

## Correlated subqueries that should be joins

```sql
SELECT c.name,
       (SELECT max(amount) FROM orders o WHERE o.cust_id = c.id) AS top
FROM customers c;      -- one subquery evaluation per customer...
```

...unless the optimizer decorrelates it into a semi-join or aggregation
join, which PostgreSQL does transparently and some engines do not. The
symptom is linear-in-rows execution time that no index fixes; the fix is
rewriting as a `GROUP BY` join or a window function over one scan. When
decorrelation *does* happen, `EXPLAIN` shows the removed subquery node —
details in [Correlated Subqueries](../sql/correlated-subqueries.md).

## CTE materialization surprises

Historically (PostgreSQL ≤ 11, and today in MySQL 8.0), a CTE was always an
optimization fence: the inner query materialized fully, with no predicate
pushdown and no index use from the outer query. Modern PostgreSQL treats
CTEs as inlineable unless recursive, side-effecting, or referenced more
than once — `MATERIALIZED` / `NOT MATERIALIZED` force the old behavior
explicitly. Two interview-visible consequences: a `LIMIT` inside an
inlined CTE can be violated by outer rewrites, and "add a CTE, got 100×
slower" on older engines is the fence, not the CTE itself.

## Lock escalation and deadlock traps

- **Lock escalation**: SQL Server promotes thousands of row/page locks to a
  table lock around the 5,000-lock threshold — a bulk `UPDATE` that "was
  fine in test" blocks *everything* in production. Row-vs-page-vs-table
  locking is in [Lock-based Protocols](../transactions/lock-based.md).
- **Deadlock by inconsistent order**: two transactions touching
  `(A, B)` and `(B, A)` — the canonical fix is a global lock ordering
  convention, plus detecting (not preventing) the rest; see
  [Deadlock Detection](../../concurrency/deadlock-detection.md).
- **Long transactions**: an uncommitted transaction holds locks *and*
  (in MVCC engines) pins versions that vacuum cannot collect — one idle
  session degrades the whole database. See
  [MVCC Internals](../advanced/mvcc-internals.md).

## Assorted one-liners

- **`UNION` vs `UNION ALL`**: `UNION` deduplicates — often destroying
  legitimate duplicates *and* adding a sort/hash; if duplicates are
  impossible by construction, `UNION ALL` is both faster and honest.
- **`ORDER BY` in a subquery/view is ignored** (without `LIMIT`); the outer
  query's order is what executes.
- **`LIMIT` without `ORDER BY`** returns an arbitrary set of rows — correct
  on your test data only until parallelism changes the scan order.
- **Integer division** (`1/2 = 0`) and float money comparisons: use
  `DECIMAL`/`NUMERIC` for money; floats compare by rounding.
- **`OFFSET` pagination** reads and discards all skipped rows — O(offset);
  keyset pagination (`WHERE id > last_seen ORDER BY id LIMIT n`) is the fix.
- **Statement timeout vs lock timeout**: waiting forever on a lock and
  waiting forever on a query are different configuration knobs, and mixing
  them up is how "the API timed out but the UPDATE kept running" happens.

## Key Takeaways

- The traps share one shape: semantics differ from intuition only on
  *unseen data shapes* (NULLs, ties, fan-out, skew) — so test on shapes,
  not volumes.
- `NOT EXISTS` over `NOT IN`, join predicates in `ON` not `WHERE`, explicit
  window frames, SARGable predicates, equality-first index order: five
  defaults that eliminate half this list.
- `DISTINCT`, `UNION`, and non-deterministic GROUP BY output are usually
  *symptoms* of an upstream fan-out bug — find the fan-out.
- Every trap here has an `EXPLAIN`-observable signature; "why is this
  slow/wrong" answers should always end at the plan.

## Cross-References

- [Null Semantics](../null-semantics.md) — three-valued logic behind NOT IN, COUNT(col), joins.
- [Window Functions](../sql/window-functions.md) — frames, ties, LAST_VALUE.
- [Join Problems](./join-problems.md) — fan-out and duplicate-multiplication problem sets.
- [Lock-based Protocols](../transactions/lock-based.md) and [Deadlock Detection](../../concurrency/deadlock-detection.md) — locking traps.
- [MVCC Internals](../advanced/mvcc-internals.md) — long-transaction and vacuum degradation.
- [Common Failures](../../failure-modes/common-failures.md) — the reliability-side failure catalog.

## References

- PostgreSQL Documentation, "[Row Type Comparison](https://www.postgresql.org/docs/current/functions-comparisons.html)" and "[SELECT queries with WITH](https://www.postgresql.org/docs/current/queries-with.html)" — NOT IN three-valued semantics and CTE materialization rules.
- MySQL Reference Manual, "[Server SQL Modes: ONLY_FULL_GROUP_BY](https://dev.mysql.com/doc/refman/8.0/en/sql-mode.html#sqlmode_only_full_group_by)" — nondeterministic bare-column semantics.
- C. J. Date, *SQL and Relational Theory*, 2nd ed., O'Reilly, 2011 — how NULLs and duplicates undermine closure and correctness in everyday SQL.
