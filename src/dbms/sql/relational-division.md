# Relational Division and Set Containment in SQL

Relational division answers "find the rows whose related set **contains all
elements** of another set": customers who ordered *every* product in a
category, students who took all courses required for a major, patients who
received all drugs in a protocol. It is the SQL form of universal
quantification (∀) — the one logical operator SQL has no direct syntax for —
which is why it is simultaneously one of the most common interview problems
and one of the least-written queries in production code.

The existential case (∃: "ordered *some* product") is a join or a
`semi join` — see [Correlated Subqueries](./correlated-subqueries.md) and
[Joins](./joins.md). This page is about the universal case: the division
operator, its SQL encodings, the NULL and empty-set edge cases that break the
naive encodings, and what the query plan looks like.

## The operator, formally

In relational algebra, division `R ÷ S` returns tuples `r` of `R` such that
for **every** tuple `s` in `S`, `(r, s)` appears in `R`. `R` is the "dividend"
(order lines), `S` the "divisor" (the target product list), and the result
carries the dividend's non-divisor attributes.

```text
   R (orders)              S (wanted products)
  ┌────┬─────────┐           ┌─────────┐
  │cust│ product │           │ product │
  ├────┼─────────┤           ├─────────┤
  │ ann│ pen     │    ÷      │ pen     │   =   ┌──────┐
  │ ann│ pencil  │           │ pencil  │       │ cust │
  │ bob│ pen     │           └─────────┘       ├──────┤
  │ bob│ paper   │                             │ ann  │
  └────┴─────────┘                             └──────┘
   ann matches both divisor rows                bob misses 'pencil'
```

Note what the result *is*: the complement of an anti-join over the negated
predicate. "ann matches all" = "no wanted product exists that ann missed."
That single identity generates most SQL encodings.

## Encoding 1: double NOT EXISTS (the exact one)

```sql
SELECT DISTINCT o.cust_id
FROM orders o
WHERE NOT EXISTS (          -- no wanted product exists...
      SELECT 1 FROM wanted w
      WHERE NOT EXISTS (    -- ...that this customer is missing
            SELECT 1 FROM orders o2
            WHERE o2.cust_id = o.cust_id
              AND o2.product = w.product));
```

This is the classical textbook form (Celko calls it the "nested NOT EXISTS")
and it is **exact under every SQL corner case**:

- *Empty divisor* (`wanted` has no rows): the inner `NOT EXISTS` is vacuously
  false for every customer → **every customer is returned**. That is the
  mathematically correct answer to "matches all of nothing" and the one
  almost every candidate gets wrong when writing the COUNT variant.
- *NULLs in the divisor or join columns*: UNKNOWN never satisfies `NOT
  EXISTS`'s inner test, so rows with NULL keys are handled consistently
  (a NULL product can never match, so any customer "missing" only NULL
  products still qualifies) — the [three-valued logic](../null-semantics.md)
  works for you here instead of against you.

The optimizer rewrites this as an **anti-join inside an anti-join** (or a
grouped LEFT-JOIN-IS-NULL plan). With an index on
`orders(cust_id, product)` the per-customer probe is an index-only scan; the
whole query becomes roughly `O(|R| log |S|)` instead of a nested loop.

## Encoding 2: COUNT comparison (the practical one)

```sql
SELECT o.cust_id
FROM orders o
JOIN wanted w ON w.product = o.product
GROUP BY o.cust_id
HAVING COUNT(DISTINCT o.product) = (SELECT COUNT(*) FROM wanted);
```

The idea: join customer orders against the wanted list, count *distinct*
matched products, compare to the divisor's cardinality. Three details decide
whether this is correct:

1. **`COUNT(DISTINCT o.product)`, not `COUNT(o.product)`** — duplicate order
   lines inflate the count and create false positives. This is the single
   most common bug in this pattern and mirrors the
   [join duplicate multiplication](../interview-problems/join-problems.md)
   problem.
2. **The empty divisor**: `COUNT(*) = 0`, and no customer survives the
   `JOIN wanted` — so the result is *empty*, whereas the mathematical answer
   is *everyone*. If the divisor can be empty, this encoding is wrong unless
   you special-case it.
3. **NULL join keys never match**, so customers with NULL products silently
   drop out of the join — usually the desired semantics, but worth stating
   in an interview.

COUNT-division is the form to reach for when the engine materializes the
grouped join cheaply (hash join + hash aggregate) and `DISTINCT` is
unnecessary because both `orders(cust_id, product)` and `wanted(product)` are
already unique.

## Encoding 3: set comparison as a first-class operator

Some engines let you compare sets directly, which reads exactly like the
algebra:

```sql
-- PostgreSQL: arrays / EXCEPT trick
SELECT o.cust_id
FROM orders o JOIN wanted w ON w.product = o.product
GROUP BY o.cust_id
HAVING array_agg(DISTINCT o.product ORDER BY o.product)
     = ARRAY(SELECT product FROM wanted ORDER BY product);

-- Engines with EXCEPT: matched set minus divisor set is empty
SELECT c.cust_id FROM customers c
WHERE NOT EXISTS (
  SELECT product FROM wanted
  EXCEPT
  SELECT product FROM orders o WHERE o.cust_id = c.cust_id);
```

The `EXCEPT` form is the double-`NOT EXISTS` written as a set difference; its
advantage is legibility (the plan and the edge cases are identical). The
`array_agg = ARRAY(...)` form additionally verifies *order-insensitive set
equality* via comparison operators that PostgreSQL defines for arrays — but
it silently produces a *distinct* comparison, and cost grows with set size;
treat it as a reporting-layer trick, not an OLTP pattern.

## The plan shape, and why indexes decide the cost

```text
PostgreSQL plan (double NOT EXISTS):

Hash Anti Join
  ->  Seq Scan on orders o
  ->  Hash Anti Join                      ← inner: "missed products"
        ->  Seq Scan on wanted w
        ->  Index Only Scan using orders_cust_prod
              Index Cond: (cust_id = o.cust_id)
```

Two anti-joins nested. If `wanted` is small and static, the planner builds it
into a hash table once and probes per customer — near-linear in `|R|`. If the
divisor is a *parameter* (e.g., "products in cart X"), the same plan shape
holds with a different outer source. Without the composite index on
`(cust_id, product)` (note the order: filter-then-match, per the
[composite index](../indexing/composite-index.md) column rule), the inner
probe degenerates into repeated scans and the COUNT variant is usually faster
despite its weaker semantics.

For static divisors queried at high frequency, the complementary design is a
*containment index*: keep a per-customer sorted product-set column (or a
[bitmap](../indexing/bitmap-index.md)) and check `@>` containment — that is
exactly the trade PostgreSQL's GIN indexes make available for arrays and
JSONB (see [GIN](../indexing/gin.md)).

## Variations interviews actually ask

**Division with residuals (what's missing).** "Return each customer and the
products they haven't ordered." One anti-join, no grouping — but candidates
often conflate it with division. Show both and state the difference: division
returns *qualifiers*; the residual returns *violations*.

**Partial division.** "Customers who ordered at least 3 of the 5 protocol
drugs." Replace `= COUNT(*)` with `>= 3` in the COUNT encoding, or use
`GROUPING`-style thresholds. The double-`NOT EXISTS` encoding cannot express
thresholds at all — a genuine reason to prefer COUNT-division in practice.

**Exact-set division.** "Customers whose *entire* product history is exactly
the wanted set — nothing more." Division tests superset (⊆ wanted); add the
converse: no `orders.product` outside `wanted`
(`NOT EXISTS (SELECT 1 FROM orders o WHERE o.cust_id = c.cust_id AND o.product NOT IN (SELECT product FROM wanted))`
— with the usual [NOT IN + NULL](./subqueries.md) hazard, or better, `NOT
EXISTS ... NOT EXISTS`).

**Division in reverse: quantifiers over time.** "Users active in *every*
month of 2025" — same encodings, divisor = the month list. This is where the
pattern pays its rent in analytics: retention cliffs, feature adoption
coverage, and compliance checks ("every transaction in the period has a
matched KYC record") are all divisions.

## Key Takeaways

- Division = universal quantification; every encoding is a negated
  existential ("no divisor element is missing").
- Double `NOT EXISTS` is exact for empty divisors and NULL keys; the COUNT
  encoding is shorter but silently wrong on empty divisors and inflates on
  duplicate rows unless `COUNT(DISTINCT)` is used.
- The plan is anti-join (×2) with index probes; a composite
  `(filter_col, match_col)` index is what keeps it linear-ish.
- Empty-divisor semantics ("all of nothing" = everything) is the canonical
  interview discriminator between candidates who memorized and candidates
  who understand.

## Cross-References

- [Correlated Subqueries](./correlated-subqueries.md) — EXISTS/NOT EXISTS execution and decorrelation.
- [Null Semantics](../null-semantics.md) — three-valued logic behind the edge cases.
- [Composite Index](../indexing/composite-index.md) — index design for the inner probe.
- [GIN Index](../indexing/gin.md) — containment queries over array-valued columns.
- [Join Problems](../interview-problems/join-problems.md) — duplicate-multiplication bugs that break COUNT-division.

## References

- E. F. Codd, "[A Relational Model of Data for Large Shared Data Banks](https://doi.org/10.1145/362384.362685)", *Communications of the ACM* 13(6), 1970 — defines the relational algebra whose division operator SQL emulates.
- Joe Celko, "[Relational Division](https://doi.org/10.1016/B978-0-12-800761-7.00034-6)", Chapter 24 in *Joe Celko's SQL for Smarties*, 5th ed., Morgan Kaufmann, 2015 — the standard treatment of every division encoding, including Todd's division and the empty-divisor edge cases.
- C. J. Date, "Divine Division" and "On the Notion of Logical Difference", in *Logic and Databases: The Roots of Relational Theory*, Trafford, 2007 — precise semantics including division's relation to universal quantification.
- PostgreSQL Documentation, "[Table Expressions](https://www.postgresql.org/docs/current/queries-table-expressions.html)" and "[Array Comparisons](https://www.postgresql.org/docs/current/functions-comparisons.html)" — `EXCEPT` and array set-equality operators used by Encoding 3.
