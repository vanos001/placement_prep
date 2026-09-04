# EXISTS vs IN: Semi and Anti Joins Done Right

"Has this customer ordered at all?" and "which customers have never ordered?"
are not join questions in SQL's syntax, but they are join questions in the
engine: both compile down to **semi-join** and **anti-join**, the two join
types no SQL dialect lets you write directly. SQL Server's own documentation
describes the optimizer "using types of logical join operations that can't be
directly expressed with Transact-SQL syntax, such as semi joins and anti semi
joins." You reach them through three surface forms — `IN`, `EXISTS`, and
`LEFT JOIN ... IS NULL` — and the forms are **not** interchangeable: they have
different NULL semantics (one of them is silently wrong on nullable data) and
different plan shapes.

Semantics of the underlying predicates are in [Subqueries](./subqueries.md)
and [Correlated Subqueries](./correlated-subqueries.md); the NULL model that
explains the famous `NOT IN` trap is in [NULL Semantics](../null-semantics.md).

## The operators SQL won't let you write

- A **semi-join** returns each row of the left input *at most once*, namely
  when the right input contains at least one matching row. Columns of the
  right input are never visible.
- An **anti-join** returns each row of the left input exactly when the right
  input contains **no** matching row.

Both are one-sided projections of the join relational operator: the output
cardinality is bounded by the *left* input, which is why they never
duplicate rows — the property that plain joins lose. SQL Server's showplan
reference documents them as real operators (`Left Semi Join`,
`Left Anti Semi Join`) that appear in plans for `EXISTS`/`IN` queries even
though no T-SQL syntax produces them.

## IN and EXISTS: equivalent on paper, different contracts

For a top-level `WHERE` filter, `x IN (SELECT y FROM b)` and
`EXISTS (SELECT 1 FROM b WHERE b.y = x)` keep exactly the same rows —
including with NULLs, because both reduce to "some `b.y` equals `x`." The
contracts differ, and the differences show up elsewhere:

- **IN takes a value expression on the left; EXISTS takes a boolean
  subquery.** `IN` cannot express a range correlation
  (`EXISTS (... WHERE o.ts BETWEEN a.from AND a.to)` has no IN form).
- **EXISTS discards the select list.** PostgreSQL documents that the subquery
  "is evaluated to determine whether it returns any rows" and "will generally
  only be executed long enough to determine whether at least one row is
  returned, not all the way to completion" — the subquery short-circuits on
  the first match. `SELECT 1` is a convention, not an optimization.
- **The boolean value itself can differ.** With no equal value and a NULL
  present on the right, `IN` evaluates to NULL (see below), while
  `EXISTS` evaluates to FALSE. Inside a `CASE` expression or a `CHECK`
  constraint that distinction is observable; under `WHERE` both are
  not-true and filter identically.

The at-most-once property is the semi-join guarantee in action. With three
`orders` rows pointing at one customer:

```sql
SELECT count(*) FROM customers c JOIN orders o ON o.customer_id = c.id;  -- 3
SELECT count(*) FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);        -- 1
SELECT count(*) FROM customers c
WHERE c.id IN (SELECT customer_id FROM orders);                          -- 1
```

An inner join is the wrong tool for membership questions precisely because
it multiplies; `DISTINCT` patches it, but the semi-join forms need no
patching.

## How the optimizer rewrites them

Modern optimizers do not run `IN`/`EXISTS` as loops; they *decorrelate*.
The idea goes back to Kim's 1982 algorithm for nested-query optimization
(see References), and it matured into the subquery-to-join conversions every
major engine performs today:

- `EXISTS` / `IN (subquery)` in a WHERE clause → **semi-join**.
- `NOT EXISTS` → **anti-join**.
- Correlated scalar subqueries → join + aggregation (where legal).

PostgreSQL's optimizer README describes exactly this: join trees must account
for "IN or EXISTS WHERE clauses that were converted to semijoins or
antijoins," which also *restricts join order* (a semi-join's right side can't
be referenced above the join). SQL Server made this orthogonal and
composable in the optimizer described by Galindo-Legaria & Joshi (2001), and
Elhemali et al. (2007) detail how its anti-semi-joins preserve three-valued
logic. MySQL applies a family of **semi-join transformations** (materialization,
FirstMatch, LooseScan, DuplicateWeedout) to IN/EXISTS predicates — see the
MySQL 8.0 manual's subquery-optimization chapter.

The physical operator is then chosen by cost, not by surface syntax:

- **Hash semi-join**: build a hash table on (usually) the smaller side's
  join key, probe per row of the other side, stop at the first hit. One pass
  over each input — `O(|A| + |B|)`.
- **Nested-loop semi-join with an index**: for each left row, an index seek
  into the right side that terminates on the first match. Wins when the left
  side is small and selective and the right side carries an index on the join
  key — the classic "one customer detail page" pattern.
- **Anti-join materialization**: an anti-join must be able to prove *absence*
  of a match, so a hash anti-join consumes its full build side before the
  first output row (a pipeline breaker). When `NOT IN` cannot become an
  anti-join at all, engines fall back to a materialized subplan probed per
  outer row — see the PostgreSQL cliff below.

Conversion is not unconditional: PostgreSQL refuses to pull up subqueries
with `LIMIT`/`OFFSET`, volatile functions, or correlations it cannot express
as joins — those keep the per-row subplan shape. *Syntax that looks identical
can run as a join or as a loop, depending on subtleties the planner decides.*

## NOT IN: the three-valued-logic trap

`x NOT IN (s1, ..., sn)` is defined as `x <> s1 AND ... AND x <> sn`. Under
three-valued logic, if any comparison yields NULL, the whole conjunction can
never be TRUE: `NULL AND FALSE` is FALSE, `NULL AND TRUE` is NULL, and `WHERE`
keeps only TRUE. Therefore:

| situation | `x NOT IN (S)` |
|---|---|
| equal value in S | FALSE — row dropped |
| no equal value, no NULLs anywhere | TRUE — row kept |
| no equal value, **any NULL in S** | NULL — row dropped |
| `x` itself NULL | NULL — row dropped (even with NULL-free S) |

PostgreSQL's documentation states the consequence verbatim: "if there are no
equal right-hand values and at least one right-hand row yields null, the
result of the NOT IN construct will be null, not true." One NULL in the
subquery makes the *entire result empty* — no error, no warning:

```sql
-- orders.customer_id contains one NULL (guest checkout)
SELECT count(*) FROM customers c
WHERE c.id NOT IN (SELECT o.customer_id FROM orders o);   -- 0 rows. Always.

SELECT count(*) FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);  -- correct
```

Why is `NOT EXISTS` safe? Its inner predicate is an *equality*: a NULL
`customer_id` never equals any id, so the NULL order matches nobody, and
"customer has no matching order" stays TRUE. `NOT IN` flips the polarity of
the same comparisons, and `NOT` over NULL stays NULL — the filter dies. This
is the single most-cited NULL trap in production SQL; the reasoning is in
[NULL Semantics](../null-semantics.md) and the PostgreSQL wiki's "Don't Do
This" entry carries it as a lint rule.

Note the asymmetry: with a NULL on the *left*, `x IN (...)` loses only that
one row — the list's NULLs cannot affect other rows. It is specifically
**NOT IN** that collapses globally: one NULL on the right, and *every* row
is lost.

## LEFT JOIN ... IS NULL: the third anti-join

```sql
-- Safe when customers.id is NOT NULL: any matched row has
-- o.customer_id = c.id, so o.customer_id cannot be NULL there.
SELECT c.id FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.customer_id IS NULL;
```

This is a genuine anti-join *provided the tested column cannot be NULL on
any row that satisfies the join predicate* — most precisely: the right
table's primary key, or the join key itself when the left key is NOT NULL.
Testing a nullable column produces false positives: if an order row matched
but its `status` happens to be NULL, the row is indistinguishable from "no
order" (verified shape: with orders `(10, 'open'), (10, NULL)`, both
customers with id 10 come back as "no orders" under
`WHERE o.status IS NULL`, while `NOT EXISTS` returns none). Two more
properties matter:

- **No early-out, full match enumeration.** An anti-join needs only
  existence information; the `LEFT JOIN` form must produce — then filter
  out — *every* matching pair, so the right side is fully consumed and all
  matches enumerated before the filter drops them. A nested-loop `NOT
  EXISTS` can instead stop at the first match per outer row. At scale the
  outer-join form is usually the slowest of the three.
- **Left-side NULL keys are reported as missing** — same as `NOT EXISTS` (a
  NULL join key matches nothing). Whether that is the intended answer is a
  business question; neither form warns you.

## What each form is worth at scale

| form | NULL-safe? | reads all of B? | plan | verdict |
|---|---|---|---|---|
| `IN (SELECT ...)` | yes (as filter) | build side, hashed | semi-join (or hashed subplan) | fine for membership |
| `EXISTS` (correlated) | yes | can early-out per row | semi-join / nested loop | default choice |
| `NOT EXISTS` | **yes** | build side for hash | anti-join | **the safe anti-join** |
| `NOT IN (SELECT ...)` | **no** | full subplan, maybe per row | subplan, often O(N²) | avoid on nullable columns |
| `LEFT JOIN ... IS NULL` | yes (with NOT NULL test col) | full right side | outer join + filter | legacy; usually slowest |

PostgreSQL is the instructive outlier: its planner converts `EXISTS`/`IN`
sublinks to semi/anti joins, but **not** `NOT IN (SELECT ...)` — the wiki
states plainly that "the planner can't transform it into an anti-join, and so
it becomes either a hashed Subplan or a plain Subplan," that the hashed
subplan is allowed "only ... for small result sets," and that the plain
subplan is "horrifically slow (in fact O(N²)) — performance can look good in
small-scale tests but then slow down by 5 or more orders of magnitude once a
size threshold is crossed." The `EXPLAIN` manual shows both shapes for the
same predicate: `(NOT (ANY (unique1 = (hashed SubPlan 1).col1)))` versus an
`ALL` subplan that "runs the subplan again for each row of the outer query."
Constant lists are the exception: PostgreSQL 15 added a hash lookup for
`NOT IN` with many constants. SQL Server, by contrast, will use an anti
semi-join for `NOT IN`, but must then layer explicit NULL-guard logic on the
join to keep three-valued semantics (the "null-aware" anti semi join of
Elhemali et al.) — the cost moves, the semantics never change.

Practical corollaries:

- Index the *right* side's join key (`orders(customer_id)`): it turns
  correlated `EXISTS` probes into O(log n) seeks and gives the hash build
  side an index-only scan.
- Put the small/selective relation on the driving side — a semi-join's
  cardinality is bounded by it.
- A hash anti-join's memory profile is the full build side; if B is huge and
  A is tiny, keep A as the probe side or budget `work_mem` for the hash —
  the same spill mechanics as in
  [Hash Join](../query-processing/hash-join.md).

## Edge cases and code-review linting

- **`NOT IN` over a nullable column is a bug, not a style choice.** Lint
  rule: flag `NOT IN (SELECT ...)` unless every column involved is declared
  `NOT NULL`; prefer `NOT EXISTS`. Same rule for row constructors —
  `(a, b) NOT IN (SELECT x, y ...)` inherits the trap from *either* column.
- **Empty IN lists from application code.** `WHERE id IN ()` is a syntax
  error in PostgreSQL and MySQL; SQLite accepts it and evaluates it as
  never-true. Code that builds lists dynamically must short-circuit: emit
  `WHERE 1 = 0` (or skip the query) when the list is empty. `NOT IN` with an
  empty list is vacuously TRUE — every row qualifies.
- **The forgotten correlation.** `EXISTS (SELECT 1 FROM orders)` with no
  WHERE clause is TRUE for every outer row — a copy-paste bug that turns an
  anti-join into a no-op filter. Review for the correlated predicate, not
  the keyword.
- **Subqueries with side effects.** Because EXISTS short-circuits,
  PostgreSQL warns it is "unwise to write a subquery that has side effects"
  (sequence calls, DML via functions) — whether they execute is
  unpredictable.
- **`IN`/`NOT IN` with constants is fine.** The NULL trap needs a NULL to
  bite; a literal list without NULLs is safe, and `NOT IN (1, 2, 3)` is the
  idiomatic "exclude these" form (the PostgreSQL wiki concurs).

## Interview Problems

### Problem 1 — Customers with no orders, three ways

*Schema:* `customers(id, name)`, `orders(id, customer_id, status)`; some
`orders.customer_id` are NULL (guest checkout). "Return customers with zero
orders — explain which formulations are correct, and which the optimizer
likes."

```sql
-- (a) NOT IN: wrong result on this data. The single NULL customer_id
-- makes the NOT IN predicate NULL for every customer => 0 rows.
SELECT c.id FROM customers c
WHERE c.id NOT IN (SELECT o.customer_id FROM orders o);

-- (b) NOT EXISTS: correct for any data; anti-join; the answer to give.
SELECT c.id FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);

-- (c) LEFT JOIN / IS NULL: correct only because we test o.id, which is
-- NOT NULL in orders; testing the nullable o.customer_id would be unsafe:
SELECT c.id FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.id IS NULL;
```

Expected answer: (a) is eliminated immediately by naming the NULL; (b) is
the default; (c) is acceptable but only when the tested column is guaranteed
NOT NULL — testing `o.id` (the PK), not `o.status`. On plan: (b) gives a hash
anti-join for large inputs and an indexed nested-loop anti-join when
`customers` is small; (c) usually costs more because the engine must
null-extend and then filter.

### Problem 2 — Rows in A not in B at scale

*Question:* "Two tables of ~100M rows each (`new_import`, `existing`) must be
reconciled nightly: find keys present in the import but missing from the
existing table. Walk through the plan."

```sql
SELECT n.tenant_id, n.ext_id
FROM new_import n
WHERE NOT EXISTS (
    SELECT 1 FROM existing e
    WHERE e.tenant_id = n.tenant_id AND e.ext_id = n.ext_id
);
```

Worked solution points:

- Single-column `NOT IN` is unavailable if either column is nullable, and a
  row-constructor `NOT IN` doubles the exposure. `NOT EXISTS` with a
  two-column equality is the null-safe and plan-friendly form.
- The planner builds a hash table on `existing(tenant_id, ext_id)` — ideally
  from a covering index — and streams `new_import` as the probe side:
  `O(|A| + |B|)` time, hash-sized memory, pipeline broken at the build step.
- If `existing` is far larger than the import, reverse the roles by driving
  from the import side (as written) — the *build* side is what costs memory,
  so keep the smaller relation as the build input, which the optimizer will
  do given accurate statistics.
- The 100M/100M case is exactly where PostgreSQL's `NOT IN` cliff fires: a
  hashed subplan becomes a per-row plain subplan past the planner's size
  threshold, and the query time jumps by orders of magnitude mid-production.
  A senior answer mentions *why*: three-valued logic forbids the anti-join
  conversion unless NULL-freedom is provable.

### Problem 3 — Semi-join deduplication and correct counting

*Question:* "Count customers who paid in January without double-counting, and
flag them per row — but `payments` has one row per transaction."

```sql
-- Wrong: JOIN inflates rows (one per payment), so count(*) counts
-- transactions, not customers; COUNT(DISTINCT c.id) patches the count
-- but cannot attach a per-row flag without another pass.
SELECT count(*) FROM customers c JOIN payments p
  ON p.customer_id = c.id AND p.paid_at >= '2026-01-01';

-- Right (count): JOIN LATERAL + LIMIT 1 — one row per paying customer.
SELECT count(*) FROM customers c
JOIN LATERAL (
    SELECT 1 FROM payments p
    WHERE p.customer_id = c.id AND p.paid_at >= '2026-01-01'
    LIMIT 1
) p ON true;

-- Right (flag): EXISTS as a boolean column.
SELECT c.id,
       EXISTS (SELECT 1 FROM payments p
               WHERE p.customer_id = c.id AND p.paid_at >= '2026-01-01'
              ) AS paid_in_january
FROM customers c;
```

The `JOIN LATERAL ... LIMIT 1` form makes "at most one match per customer"
*syntactically explicit*: the inner query stops at the first index hit per
outer row, and the inner join keeps exactly the payers — semi-join semantics
spelled out in query text. In either form the inner query must actually be
correlated, or it degenerates to a constant for every row. A follow-up worth
anticipating: why not `COUNT(DISTINCT c.id)`? It repairs the count but not
the plan — the join still enumerates every payment before deduplicating,
which is wasted work the semi-join never does (see
[Funnel Analysis](./funnel-analysis.md) for the same duplication hazard in
multi-step funnel queries).

### Problem 4 — Viewed but never bought, per product

*Question:* "From `page_views(user_id, product_id, ts)` and
`purchases(user_id, product_id)`, find products with views but zero
purchases." The naive `(user_id, product_id) NOT IN (SELECT ...)` breaks if
`purchases` carries a NULL in either column (partial keys from anonymized
accounts). The correct pair-aware form:

```sql
SELECT v.product_id, count(DISTINCT v.user_id) AS viewers
FROM page_views v
WHERE NOT EXISTS (
    SELECT 1 FROM purchases p
    WHERE p.user_id = v.user_id AND p.product_id = v.product_id
)
GROUP BY v.product_id
ORDER BY viewers DESC
LIMIT 20;
```

`NOT EXISTS` scopes the anti-join to the exact pair, degrades gracefully on
NULLs (a NULL key matches nothing — the view simply counts as unpurchased),
and lets the planner hash the distinct purchase pairs. Follow-up questions to
expect: how the plan changes if `purchases` is tiny (hash anti-join) versus
huge with a composite index (nested-loop anti-join with early-out is
unlikely for *anti* — the hash side still must be fully read); and how this
composes with funnel queries — see [Funnel Analysis](./funnel-analysis.md)
for the event-sequence machinery that layers on top.

## Key Takeaways

- `EXISTS`/`IN` are surface syntax for semi-joins; `NOT EXISTS` for
  anti-joins. Optimizers rewrite them because semi/anti joins unlock join
  orders and hash/merge execution that per-row subplans can't use.
- `NOT IN (SELECT ...)` is null-sensitive by definition: one NULL on the
  right empties the result. It is the only one of the three anti-join forms
  with this property — and the only one PostgreSQL will not turn into a
  real anti-join.
- `LEFT JOIN ... IS NULL` is correct only when the tested column is NOT NULL
  in the right table; it also cannot early-out.
- The at-most-once property (no row multiplication) is what separates
  semi-join forms from inner joins; it is also why `EXISTS` is the tool for
  flags and membership counts.
- Lint for review: no `NOT IN (SELECT ...)` on nullable columns; guard
  dynamically-built IN lists against the empty case; require a correlated
  predicate inside every `EXISTS`.

## Cross-References

- [Subqueries](./subqueries.md) — subquery taxonomy, scalar vs table forms, IN/ANY/ALL.
- [Joins](./joins.md) — outer joins and the NULL-extension this page builds on.
- [NULL Semantics](../null-semantics.md) — three-valued logic that explains the NOT IN trap.
- [Correlated Subqueries](./correlated-subqueries.md) — the N+1 pattern semi-joins replace.
- [Relational Division](./relational-division.md) — "matches *every* row" needs division, not anti-join.
- [Interview Traps](../interview-problems/interview-traps.md) — NOT IN and other silent-failure classics.
- [Hash Join](../query-processing/hash-join.md) — build/probe mechanics behind hash semi/anti joins.

## References

- PostgreSQL Documentation, "[Subquery Expressions](https://www.postgresql.org/docs/current/functions-subquery.html)" — EXISTS/IN/NOT IN semantics, including the exact NULL wording and the short-circuit evaluation note.
- PostgreSQL Documentation, "[Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)" — SubPlan vs hashed SubPlan plans for IN/NOT IN.
- PostgreSQL Wiki, "[Don't Do This: NOT IN](https://wiki.postgresql.org/wiki/Don%27t_Do_This)" — the O(N²) subplan cliff and the NOT EXISTS rewrite rule.
- PostgreSQL source, `src/backend/optimizer/README` ([raw file](https://raw.githubusercontent.com/postgres/postgres/master/src/backend/optimizer/README)) — semijoin/antijoin conversion and join-order restrictions.
- PostgreSQL 15 Release Notes, "[General Performance](https://www.postgresql.org/docs/15/release-15.html)" — hash lookup for NOT IN with many constants.
- Microsoft Learn, "[Joins](https://learn.microsoft.com/en-us/sql/relational-databases/performance/joins)" — semi/anti semi joins as optimizer-only logical operators; [Showplan Logical and Physical Operators Reference](https://learn.microsoft.com/en-us/sql/relational-databases/showplan-logical-and-physical-operators-reference) — `Left Semi Join` / `Left Anti Semi Join`.
- MySQL 8.0 Reference Manual, "[Optimizing Subqueries](https://dev.mysql.com/doc/refman/8.0/en/optimizing-subqueries.html)" — semi-join transformations (materialization, FirstMatch, LooseScan, DuplicateWeedout).
- W. Kim, "On Optimizing an SQL-like Nested Query," ACM TODS 7(3), 1982. [DOI: 10.1145/319732.319745] — the original decorrelation algorithm.
- C. Galindo-Legaria, M. Joshi, "Orthogonal Optimization of Subqueries and Aggregation," SIGMOD 2001. [DOI: 10.1145/375663.375748] — SQL Server's subquery-to-join framework.
- M. Elhemali, C. Galindo-Legaria, T. Grabs, M. Joshi, "Execution Strategies for SQL Subqueries," SIGMOD 2007. [DOI: 10.1145/1247480.1247598] — null-aware anti-semi-join execution.
