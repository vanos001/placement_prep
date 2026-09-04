# LATERAL Joins and CROSS APPLY: Correlated Joins Done Right

Every FROM item in a standard SQL query is an *independent* input: the engine
evaluates it once, and it may not mention any other FROM item. `LATERAL` removes
that restriction in one precise, narrow way: a FROM item marked `LATERAL` may
reference columns of FROM items to its **left**, and is re-evaluated for each of
their rows. It is the FROM-clause version of a correlated subquery — one that
returns a *table* instead of a scalar, can be joined, can use `ORDER BY ... LIMIT`,
and can call set-returning functions. SQL Server has shipped the same capability
under different names since 2005 (`CROSS APPLY` / `OUTER APPLY`); MySQL added the
standard spelling in 8.0.14.

The scalar-subquery cousin — per-row evaluation, the N+1 problem, decorrelation
into semi-joins — is in [Correlated Subqueries](./correlated-subqueries.md) and
[EXISTS vs IN](./exists-vs-in.md). This page is about the join form.

## What LATERAL actually changes

In SQL-92, derived tables must be *constant* over the query's duration. The MySQL
manual states it plainly: "A derived table cannot normally refer to (depend on)
columns of preceding tables in the same FROM clause. As of MySQL 8.0.14, a derived
table may be defined as a lateral derived table to specify that such references are
permitted." Sneak a lateral reference past the parser and it fails at resolution
time — MySQL: `ERROR 1054: Unknown column 'salesperson.id'`; PostgreSQL:
`ERROR: invalid reference to FROM-clause entry for table "s"` — the parser's
resolution failure in `parse_relation.c`. The message confuses because the alias
`s` *is* in scope at the top level; the point is that the subquery could not see it.

`LATERAL` makes the FROM list ordered and parameterized left-to-right. PostgreSQL's
manual gives the exact contract:

> The LATERAL key word can precede a sub-SELECT FROM item. This allows the
> sub-SELECT to refer to columns of FROM items that appear before it in the FROM
> list. (Without LATERAL, each sub-SELECT is evaluated independently and so cannot
> cross-reference any other FROM item.)

and the evaluation rule:

> for each row of the FROM item providing the cross-referenced column(s), the
> LATERAL item is evaluated using that row or row set's values of the columns.
> The resulting row(s) are joined as usual with the rows they were computed from.

Three sharp edges in the standard's semantics (PostgreSQL and MySQL document them
the same way):

- **References are left-only, never forward.** A lateral item sees only items
  earlier in the FROM list (or on the left-hand side of a JOIN it sits on the
  right-hand side of). `X RIGHT JOIN LATERAL Y` is syntactically legal but Y may
  not reference X — the source tables "must be INNER or LEFT joined to the LATERAL
  item, else there would not be a well-defined set of rows from which to compute
  each set of rows for the LATERAL item."
- **Function calls in FROM are implicitly lateral.** `LATERAL` before a
  function-call FROM item "is a noise word, because the function expression can
  refer to earlier FROM items in any case" — `unnest(some_array_column)` was
  always row-wise.
- **The standard context.** MySQL's manual attributes the feature to the standard:
  "In SQL:1999, the query becomes legal if the derived tables are preceded by the
  LATERAL keyword (which means 'this derived table depends on previous tables on its
  left side')." The 8.0.14 release notes add: "LATERAL now is a reserved word and
  cannot be used as an identifier without identifier quoting."

Dialect map:

| engine | spelling | since | notes |
|---|---|---|---|
| PostgreSQL | `[CROSS\|LEFT] JOIN LATERAL (...)`, `LATERAL fn(...)` | 9.3 | planner may decorrelate (below) |
| SQL Server | `CROSS APPLY` / `OUTER APPLY` | 2005 | APPLY is the only spelling; no `LATERAL` keyword |
| MySQL | `LATERAL` derived tables | 8.0.14 | FROM-only; join-type restrictions; `JSON_TABLE()` always treated as lateral |
| MariaDB | LATERAL derived tables | (MDEV-19078, "Support lateral derived tables") | same standard feature |

## The mental model: a correlated join *with* an optimizer

Heap Engineering's classic write-up calls it what it behaves like: "a SQL foreach
loop, in which PostgreSQL will iterate over each row in a result set and evaluate a
subquery using that row as a parameter." That is the *semantic* model, but not the
execution model: the join form hands the optimizer a real join tree to work with —
the freedom a WHERE-clause correlated subquery never gets.

The workhorse execution is a **parameterized nested loop**. PostgreSQL's optimizer
README: "The planner implements these by generating parameterized paths for any RTE
that contains lateral references":

```
Nested Loop
  -> Seq Scan on customers c
  -> Index Scan using orders_customer_created_idx on orders o
       Index Cond: o.customer_id = c.id
       Order By / Limit applied per outer row
```

The outer row's values are passed *into* the inner scan as parameters, so the inner
side is an index seek, not a scan. The README explains when this wins: "This is the
only plan type that can avoid fetching all of B... for small numbers of rows
coming from A, that will dominate every other consideration. (As A gets larger,
this gets less attractive, and eventually a merge or hash join will win instead.)"
That is the **small-outer-side rule**: cost is roughly
`|outer| × (index seek + LIMIT n rows)`, scaling with the number of groups, not
the size of the inner table. 1,000 customers × 3 rows each beats a full sort of a
100M-row orders table; 50M outer rows × any per-row subplan loses to one big sort.

The **disaster case** is the same shape with the index missing: a Seq Scan executed
once *per outer row* — `O(N × M)` tuple reads. A lateral join whose inner query
cannot use an index for the correlation is an N+1 problem wearing a join costume.

## Canonical patterns

### Top-N per group

The signature use: latest order per customer, top 3 items per user, most recent
event per session.

```sql
SELECT c.id, c.name, o.id, o.amount, o.created_at
FROM customers c
LEFT JOIN LATERAL (
    SELECT o.id, o.amount, o.created_at
    FROM orders o
    WHERE o.customer_id = c.id          -- correlation → index (customer_id, created_at DESC)
    ORDER BY o.created_at DESC
    LIMIT 1
) o ON true;
```

Three competing formulations, three different contracts:

| approach | ties on the ordering key | plan shape | notes |
|---|---|---|---|
| `LATERAL ... ORDER BY ... LIMIT 1` | one arbitrary row of the tied set | parameterized nested loop, O(G·log M) with the right index | no full-table sort; extra columns come along "for free" |
| `ROW_NUMBER() OVER (PARTITION BY ...)` (see [Window Functions](./window-functions.md)) | deterministic *iff* the OVER ORDER BY carries a tiebreaker | one full sort, then filter `rn <= 1` | O(n log n) over *all* rows; reads everything even when only the first row per group is needed |
| `DISTINCT ON` (PostgreSQL only) | "the 'first row' of each set is unpredictable unless ORDER BY is used" (manual) | sort by `(group, order)` | PG-specific; terse; ordering must cover the DISTINCT expressions as leftmost prefix |

The tie-handling difference is the subtle interview answer. `DISTINCT ON
(customer_id)` with `ORDER BY customer_id, created_at DESC` picks an *unspecified*
row among equal timestamps. The LATERAL form has the same hole — tied timestamps
return whichever row the index hands back first — and the same fix: extend the
ordering with a unique column (`created_at DESC, id DESC`). Only the window
formulation lets you *see* ties (via `RANK()`) if "all rows at the max" is what you
actually need.

### Match-to-nearest and as-of joins

"Which price was in effect when this order was placed?" — for each outer row, find
the best inner row under an order. With an index on `(item, valid_from DESC)`, a
lateral `ORDER BY valid_from DESC LIMIT 1` per row is the classic sparse-versions
as-of join; the trade-offs against range-based encodings are in [Temporal SQL
Patterns](./temporal-sql-patterns.md). Nearest-neighbor by value (`ORDER BY
abs(x - t.x) LIMIT 1`) is the same shape but needs a spatial/kNN index to stay
indexed.

### Joins against ordered aggregates

A window function aggregates over *partitions* but cannot apply a `LIMIT` inside
the aggregate or return a *set* per row. LATERAL can:

```sql
-- median order amount per customer
SELECT c.id, p.median
FROM customers c
CROSS JOIN LATERAL (
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY o.amount) AS median
    FROM orders o WHERE o.customer_id = c.id
) p;
```

"Top 3 items as an array" (`SELECT array_agg(x ORDER BY score DESC) FROM
(... LIMIT 3)`), "first event of each kind per user", per-row percentile — shapes a
window clause cannot express. See [EXISTS vs IN](./exists-vs-in.md) for the
semi-join flavor of the same trick.

### Unnesting arrays and generate_series per row

Set-returning functions in FROM are implicitly lateral, so each outer row drives
row-wise expansion with full surrounding context:

```sql
-- one row per (device, day) from each reading batch, with ordinality
SELECT d.device_id, gs.day, gs.ord
FROM devices d
CROSS JOIN LATERAL unnest(d.pending_days) WITH ORDINALITY AS gs(day, ord);

-- a calendar spine per row: bookings expanded to daily rows
SELECT b.id, g.day::date
FROM bookings b
CROSS JOIN LATERAL generate_series(b.starts_at, b.ends_at, interval '1 day') g(day);
```

PostgreSQL's manual example feeds a set-returning function with a *column*
(`LATERAL vertices(p1.poly) v1`) — impossible for a plain derived table, which
cannot see `p1`.

### JSON/JSONB row expansion

`jsonb_to_recordset` "expands the top-level JSON array of objects to a set of rows
having the composite type defined by an AS clause" — and because its argument is a
*column of the outer row*, it sits under a lateral:

```sql
SELECT u.id, rec.product_id, rec.score
FROM users u
CROSS JOIN LATERAL jsonb_to_recordset(u.recommendations)
    AS rec(product_id int, score numeric)
ORDER BY u.id, rec.score DESC;
```

Ranking over the expanded rows composes with the top-N pattern; deeper JSON
machinery is in [JSON and Arrays](./json-arrays.md).

## CROSS APPLY vs OUTER APPLY (SQL Server)

T-SQL has no `LATERAL`; it has `APPLY`. The syntax is
`left_table_source { CROSS | OUTER } APPLY right_table_source`, and the manual's
definition is the per-row contract exactly: the engine "evaluates
right_table_source against each row of the left_table_source to produce rowsets...
right_table_source can be represented approximately this way:
`TVF(left_table_source.row)`. The mapping:

- **`CROSS APPLY` ≙ `CROSS JOIN LATERAL`** (inner semantics). The manual's own
  example: with `CROSS APPLY dbo.GetReports(d.DeptMgrID)`, "if a particular
  department doesn't have any employees, there won't be any rows returned for that
  department" — zero inner rows *delete the outer row*.
- **`OUTER APPLY` ≙ `LEFT JOIN LATERAL ... ON true`**. The same example switches to
  OUTER APPLY to "produce rows for those departments without employees, which will
  produce null values" — the outer row survives, null-extended.

APPLY is not optional in T-SQL for a family of patterns:

- **Table-valued functions per row** — `CROSS APPLY dbo.fn_calc(x.col)`; TVFs cannot
  be plain join operands because their arguments are outer columns.
- **`TOP 1 ... ORDER BY` per group** — TOP, like LIMIT, is only legal in a query or
  parenthesized subquery, so "latest row per customer" needs APPLY or a window
  rewrite; DMV work (`CROSS APPLY sys.dm_exec_query_plan(cp.plan_handle)`, as in
  the manual's plan-cache example) is TVF-per-row by nature.
- **`OPENJSON`/`STRING_SPLIT` per row** — the row-wise expansion patterns above.

MySQL carries the standard's restrictions instead: a lateral derived table can
occur only in a FROM clause, and the join type is constrained by reference
direction (right operand referencing left: `INNER`, `CROSS`, or `LEFT [OUTER]
JOIN`; the mirror image allows `RIGHT [OUTER] JOIN`) — PostgreSQL's `RIGHT JOIN
LATERAL` prohibition as a parse-time check. MySQL also treats `JSON_TABLE()` joins
"as though LATERAL had been used," which is why JSON_TABLE worked before 8.0.14.

## Decorrelation: when the planner can escape the loop

A lateral join *looks* like a nested loop and sometimes *is* something better.
PostgreSQL's README: "We also allow LATERAL subqueries to be flattened (pulled up
into the parent query) by the optimizer, but only when this does not introduce
lateral references into JOIN/ON quals that would refer to relations outside the
lowest outer join at/above that qual." Three regimes exist:

1. **Flattenable** — no LIMIT/OFFSET, no aggregate, no volatile functions, and the
   lateral reference expressible as a join qual. The subquery is pulled up
   (`pull_up_simple_subquery`) and the reference becomes an ordinary join
   condition; the planner may hash- or merge-join as if you had written the join by
   hand — which is why some lateral joins have no loop in the plan at all.
2. **Parameterized path** — pullup blocked (LIMIT, aggregates, set-returning
   functions...), so the subquery stays a parameterized path: nested loop with an
   index scan inside. The *good* non-flattened case, provided an index serves the
   correlation key.
3. **Subplan** — nothing above applies; the inner query runs as a `SubPlan` probed
   per outer row, the shape WHERE-clause forms produce when decorrelation fails
   (see [EXISTS vs IN](./exists-vs-in.md)).

Even flattened laterals can force join order: pullup may create PlaceHolderVars
whose evaluation "requires that node to appear on the inside of a nestloop join
relative to the rel(s) supplying the lateral reference" — the lateral dependency is
a join-order constraint the planner cannot negotiate away.

### Reading EXPLAIN for a lateral join

The healthy signature is exactly the README's picture:

```
Nested Loop  (cost=... rows=1000 ...)
  ->  Seq Scan on customers c (rows=1000)
  ->  Limit (rows=1)
        ->  Index Scan using orders_customer_created_idx on orders o
              Index Cond: (customer_id = c.id)
```

Read it for: the outer/inner split; `Index Cond: (customer_id = c.id)` proving the
correlation became an index parameter; `Limit (rows=1)` proving the top-N ran per
outer row. Failure signatures: `Seq Scan on orders` *below* the loop (missing
index — the disaster case), or an inner rows estimate wildly off reality.

### Why row estimates for the inner side lie

Row estimates are attached to *parameterizations*, not parameter *values*. The
README is explicit that all paths of one parameterization must show "the same
rowcount" — one average number stands in for "orders of customer 7 (4 rows)" and
"orders of customer 8123 (40,000 rows)" alike. With skewed correlation keys the
per-row cost model is wrong in both directions: expensive groups are under-costed,
cheap groups can make the parameterized loop look better than a hash join. This is
why a lateral join can benchmark beautifully on a demo schema and die on production
data; the general mechanics are in [Query Planner](../query-planner.md).

## Edge cases and mistakes

- **Forgetting the keyword.** A sub-SELECT in FROM referencing a sibling without
  `LATERAL` fails at parse time: `invalid reference to FROM-clause entry`
  (PostgreSQL) or `Unknown column ... in 'where clause'` (MySQL). FROM items are
  independent by default.
- **CROSS JOIN LATERAL silently drops rows.** Zero inner rows for some outer row
  means that outer row is discarded (same for CROSS APPLY). PostgreSQL's manual
  shows the idiom for finding the dropped ones: `LEFT JOIN LATERAL
  get_product_names(m.id) pname ON true ... WHERE pname IS NULL`. A *feature* —
  "at most one match per outer row" spelled out in syntax — and a classic "why did
  my report shrink?" bug.
- **Volatile functions evaluate per row — by design and by hazard.** The per-row
  guarantee makes `LATERAL generate_series(...)` or per-row `random()` well-defined;
  it also means an accidentally-volatile inner expression can never be evaluated
  once and cached, and the planner will refuse to flatten it.
- **No forward references.** `FROM lateral_a, b` where the lateral references `b`
  fails — reorder the FROM items; left-to-right order is semantic now.
- **LATERAL in UPDATE/DELETE.** PostgreSQL's `UPDATE ... FROM from_item` "uses the
  same syntax as the FROM clause of a SELECT statement", so lateral sub-SELECTs are
  legal in UPDATE/DELETE's FROM/USING clause. The *target* table can never be a
  lateral item; reference it from inside the lateral instead.
- **Locking reaches into laterals.** "If a locking clause is applied to a view or
  sub-query, it affects all tables used in the view or sub-query." A top-level
  `FOR UPDATE` on a lateral-joined query locks the lateral's inner rows too —
  often not what "lock the customers I'm touching" meant.
- **Aggregates over the whole query.** MySQL forbids a lateral derived table from
  referencing aggregates of the query that owns its FROM clause — aggregate one
  level out, or don't.

## Interview Problems

### Problem 1 — Latest order per customer, three ways

*Schema:* `customers(id, name)`, `orders(id, customer_id, amount, created_at)`;
"return each customer with their most recent order. Write it three ways and say
which scales."

```sql
-- (a) LATERAL: parameterized nested loop
SELECT c.id, c.name, o.*
FROM customers c
LEFT JOIN LATERAL (
    SELECT * FROM orders o WHERE o.customer_id = c.id
    ORDER BY o.created_at DESC, o.id DESC LIMIT 1
) o ON true;

-- (b) Window: one full sort, then filter
SELECT * FROM (
    SELECT c.id, c.name, o.*,
           ROW_NUMBER() OVER (PARTITION BY o.customer_id
                              ORDER BY o.created_at DESC, o.id DESC) AS rn
    FROM customers c JOIN orders o ON o.customer_id = c.id
) t WHERE rn = 1;

-- (c) Correlated scalar subquery: the N+1 classic
SELECT c.id, c.name, o.*
FROM customers c JOIN orders o ON o.customer_id = c.id
WHERE o.created_at = (SELECT MAX(o2.created_at) FROM orders o2
                      WHERE o2.customer_id = c.customer_id);
```

Worked answer: (a) costs `O(G · log M)` — one index seek per group, `G` groups —
with an index on `orders(customer_id, created_at DESC)`; it never reads past each
customer's top row. (b) costs `O(n log n)` over *all* orders (sort + WindowAgg)
regardless of G; it wins when G ≈ n (one order per customer) or no composite index
exists, and it is the portable form. (c) is the trap: the scalar subquery executes
per *joined* row, and on ties at `MAX(created_at)` it returns *all* tied rows,
breaking the one-row-per-customer contract. Ties: (a)/(b) deterministic with the
`id` tiebreaker, (c) nondeterministic *and* row-multiplying.

### Problem 2 — Top 3 products per user from a JSONB scored list

*Schema:* `users(id, name, recs jsonb)` where `recs` is an array like
`[{"product_id": 7, "score": 0.92}, ...]`. "Recommend the top 3 products per
user."

```sql
SELECT u.id, u.name, top.product_id, top.score
FROM users u
CROSS JOIN LATERAL (
    SELECT rec.product_id, rec.score
    FROM jsonb_to_recordset(u.recs) AS rec(product_id int, score numeric)
    ORDER BY rec.score DESC
    LIMIT 3
) top;
```

Why LATERAL and not a window function: `jsonb_to_recordset(u.recs)` is a
set-returning function whose *argument is the outer row's column* — it cannot be
evaluated once, and a window function cannot cap a partition of a derived set at 3
rows without materializing everything. The plan is one expansion + top-3 per user,
at `O(total array elements)` — fine unless the arrays are huge, in which case
project the recommendations into a real `(user_id, product_id, score)` table with
a btree and reuse Problem 1's plan. Use `LEFT JOIN LATERAL ... ON true` if users
with empty arrays must still appear.

### Problem 3 — "This lateral join is slow: EXPLAIN shows a big inner Sequential Scan"

*Given:* a top-N-per-group lateral join over a large orders table; EXPLAIN shows
`Nested Loop -> Seq Scan on customers` and `-> Sort -> Seq Scan on orders` (or an
index scan with a giant rows estimate). Diagnose and fix.

Worked answer, in the order an interviewer expects:

1. **Correlation key has no usable index.** The inner query's
   `WHERE o.customer_id = c.id ORDER BY o.created_at DESC LIMIT 1` needs
   `orders(customer_id, created_at DESC)` (optionally `, id DESC` for deterministic
   ties). Without it, every outer row sorts or scans a chunk of `orders`: the
   O(N·M) disaster. Fix the index first — often minutes to milliseconds with *no
   query change*.
2. **Estimate pathology.** The inner-side rowcount is one number per
   parameterization (skew-blind), so whale customers can make the parameterized
   plan look expensive, or a stale `n_distinct` on the correlation column distorts
   everything downstream. Fix: `ANALYZE`, then compare the inner index scan's
   `rows=` to reality; `SET (n_distinct = ...)` for non-typical skew.
3. **The inner query isn't actually correlated.** A copy-paste bug leaving the
   WHERE clause off turns the lateral into "evaluate this full query per row" —
   no index fixes that. The EXPLAIN tell: the inner plan is identical and
   unparameterized (`Index Cond` absent).
4. **G is not actually small.** The small-outer-side rule assumed G (groups) ≪ n
   (orders). With one order per customer, the `ROW_NUMBER()` form's single sort can
   win — measure both. If the plan cannot be fixed, pre-aggregate
   (materialize latest-order-per-customer) and join the summary.

## Key Takeaways

- LATERAL turns the FROM list into an ordered, left-to-right pipeline: the lateral
  item is re-evaluated per row of everything to its left, and may reference only
  those left items. No forward references, no RIGHT-join references.
- Semantically it is a correlated subquery returning a table; execution is
  whatever the planner can get away with: flattened to a hash join when possible,
  a parameterized nested loop (index seek per outer row) when not. The optimizer
  freedom is the whole advantage over WHERE-clause correlation.
- The cost model is `|outer groups| × inner-per-row`, so index the correlation
  key and keep the outer side the small/selective one; a per-row sequential scan
  on the inner side is the classic disaster.
- SQL Server spells it CROSS APPLY (inner) / OUTER APPLY (left-outer); MySQL
  8.0.14+ implements the standard keyword; ties in top-N-per-group are
  nondeterministic in both LATERAL and DISTINCT ON unless you add a tiebreaker.
- Watch the silent row-dropping of CROSS JOIN LATERAL, per-row evaluation of
  volatile inner expressions, skew-blind inner row estimates, and locking clauses
  that reach into the lateral.

## Cross-References

- [Correlated Subqueries](./correlated-subqueries.md) — per-row evaluation and decorrelation basics this page extends into FROM.
- [EXISTS vs IN](./exists-vs-in.md) — semi/anti-join forms; the `JOIN LATERAL ... LIMIT 1` semi-join idiom.
- [Window Functions](./window-functions.md) — the ROW_NUMBER top-N alternative and its frame semantics.
- [Subqueries](./subqueries.md) — derived tables and scalar subqueries; the constant-derived-table rule LATERAL lifts.
- [Temporal SQL Patterns](./temporal-sql-patterns.md) — as-of joins: range encodings vs lateral-top-1.
- [JSON and Arrays](./json-arrays.md) — JSONB set expansion machinery used under LATERAL.
- [Interview Traps](../interview-problems/interview-traps.md) — the silent-row-dropping and tie-handling failure family.

## References

- PostgreSQL Documentation, "[SELECT](https://www.postgresql.org/docs/current/sql-select.html)" — LATERAL FROM-item semantics, per-row evaluation rule, INNER/LEFT-only restriction, LEFT JOIN LATERAL ... IS NULL example, DISTINCT ON unpredictability, locking clause applied to sub-queries.
- PostgreSQL Documentation, "[Table Expressions, §7.2.1.5 LATERAL Subqueries](https://www.postgresql.org/docs/current/queries-table-expressions.html)" — implicit laterality of function-call FROM items; set-returning-function examples.
- PostgreSQL source, `src/backend/optimizer/README` ([raw file](https://raw.githubusercontent.com/postgres/postgres/master/src/backend/optimizer/README)) — "LATERAL subqueries" (parameterized paths, pullup restrictions, PlaceHolderVars on nestloop inner side) and "Parameterized Paths" costing.
- PostgreSQL source, `src/backend/parser/parse_relation.c` ([raw file](https://raw.githubusercontent.com/postgres/postgres/master/src/backend/parser/parse_relation.c)) — the `invalid reference to FROM-clause entry` error.
- PostgreSQL Documentation, "[UPDATE](https://www.postgresql.org/docs/current/sql-update.html)" — from_item "uses the same syntax as the FROM clause of a SELECT statement."
- PostgreSQL Documentation, "[JSON Functions](https://www.postgresql.org/docs/current/functions-json.html)" / "[Set-Returning Functions](https://www.postgresql.org/docs/current/functions-srf.html)" — jsonb_to_recordset and generate_series semantics.
- Microsoft Learn, "[FROM clause plus JOIN, APPLY, PIVOT (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/queries/from-transact-sql?view=sql-server-ver17)" — `{ CROSS | OUTER } APPLY` syntax, per-row `TVF(left_table_source.row)` evaluation, CROSS/OUTER APPLY zero-rows examples.
- MySQL 8.0 Reference Manual, "[Lateral Derived Tables](https://dev.mysql.com/doc/refman/8.0/en/lateral-derived-tables.html)" — 8.0.14 introduction, FROM-only and join-type restrictions, SQL-92 vs SQL:1999 framing, JSON_TABLE treated as lateral.
- MySQL 8.0 Release Notes, "[Changes in MySQL 8.0.14](https://dev.mysql.com/doc/relnotes/mysql/8.0/en/news-8-0-14.html)" — LATERAL addition (WL #8652) and reserved-word note.
- Heap Engineering, D. Robinson, "[PostgreSQL's Powerful New Join Type: LATERAL](https://blog.heapanalytics.com/postgresqls-powerful-new-join-type-lateral/)" — the "SQL foreach loop" mental model; funnel query.
- Citus Data (Microsoft), "[Distributed execution of CTEs and complex SQL in Citus](https://www.citusdata.com/blog/2018/03/09/distributed-execution-of-ctes-and-subqueries-in-citus/)" — LEFT JOIN LATERAL funnel query pushed down in a distributed planner.
- MariaDB, JIRA [MDEV-19078](https://jira.mariadb.org/browse/MDEV-19078), "Support lateral derived tables" — MariaDB's implementation tracking issue.
