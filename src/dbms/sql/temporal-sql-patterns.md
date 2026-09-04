# Temporal SQL Patterns: As-of Joins, Interval Overlap, and SCD Type 2

Time is a dimension every production table quietly has. Orders change status,
prices move daily, employees change departments, and the query "what did the
world look like at *t*?" or "which price was in effect when this order was
placed?" must be answered from versioned tables without a bug. This page is
the SQL problem-solving toolkit: the overlap predicate and its nine
sub-relations, as-of / point-in-time joins, interval merging and union,
half-open interval discipline, and the database constraints that make
interval correctness *structural* rather than application-hoped.

The engine-level features (SQL:2011 system-versioned tables, bitemporal
models) are covered in [Temporal & Streaming Databases](../advanced/temporal-streaming.md);
the warehouse-modeling side of SCDs is in
[Slowly Changing Dimensions](../../data-engineering/slowly-changing-dimensions.md).

## The interval overlap predicate, precisely

Two half-open intervals `[s1, e1)` and `[s2, e2)` overlap **iff**:

```sql
s1 < e2 AND s2 < e1        -- half-open form
-- closed form adds equality: s1 <= e2 AND s2 <= e1
```

That single line replaces the four-case case-analysis (before / meets /
overlaps / contains / contained) people draw on whiteboards — Allen's interval
algebra names the thirteen possible relations between two intervals, and the
inequality above is exactly "not (disjoint-before or disjoint-after)". Getting
the *strictness* right is the entire game:

```text
[s1,e1)  |----|        [s1,e1) |----|        |----| [s1,e1)
[s2,e2)      |----|    [s2,e2)      |----|   [s2,e2) |----|
  s1 < e2 AND s2 < e1     → overlap      → no overlap (touching ≠ overlapping)
```

With `BETWEEN` (closed on both ends), back-to-back bookings
(`10:00–11:00` then `11:00–12:00`) are reported as overlapping — the classic
double-booking false positive. Half-open `[start, end)` intervals make
"meets" false and compose cleanly: adjacent intervals share endpoints without
overlapping, and `end = start` of the next version in SCD chains.

## As-of joins: point-in-time lookup

The workhorse query of every pricing, FX, and configuration system: for each
fact row, find the version of the reference table that was **in effect at the
fact's timestamp**. Two encodings dominate:

```sql
-- (a) inequality join (e.g. PostgreSQL, Spark, DuckDB)
SELECT o.order_id, o.ts, p.price
FROM orders o
JOIN price_history p
  ON p.item = o.item
 AND o.ts >= p.valid_from
 AND o.ts <  p.valid_to;

-- (b) LATERAL with ORDER BY ... LIMIT 1 (works when versions are sparse)
SELECT o.order_id, o.ts, p.price
FROM orders o
CROSS JOIN LATERAL (
  SELECT price FROM price_history ph
  WHERE ph.item = o.item AND ph.valid_from <= o.ts
  ORDER BY ph.valid_from DESC
  LIMIT 1
) p;
```

Why both exist: encoding (a) assumes every fact's timestamp falls inside some
recorded version (`valid_to` chains close every gap). That is an *invariant*
of well-built SCD-2 tables — enforced by constraint, see below — and the
planner turns the range join into a merge or hash-by-key plus range filter.
Encoding (b) needs only `valid_from` (versions before you exist), handles
facts predating the first version (no match → drop or default), and is the
only robust choice when versions are *event-sourced* rather than maintained.

**Open intervals at the end** (`valid_to IS NULL` or `valid_to =
'infinity'`) are the other invariant decision. Both work; mixing them in one
column is a bug factory. If you use NULL, every predicate grows a
`(p.valid_to IS NULL OR o.ts < p.valid_to)` disjunct — which kills simple
index range scans unless you store a sentinel (`'infinity'::timestamptz`,
which PostgreSQL compares normally).

## Interval union and "current balance as of t"

Computing *net state* from intervals — coverage of a contract, balance
history, seat availability — needs union/merge semantics, not just join
semantics. The general recipe (in depth, with the net-depth trick, in
[Gaps and Islands](./gaps-and-islands.md)):

1. Explode interval boundaries into events (`+1` at start, `−1` at end).
2. Running-sum the events → `depth`.
3. Islands are `depth > 0` spans (union) or exactly-1 spans (disjoint
   decomposition).

```sql
-- Union of possibly-overlapping coverages [s,e):
WITH ev AS (
  SELECT id, s AS ts, 1 AS d FROM coverage
  UNION ALL
  SELECT id, e, -1 FROM coverage
),
run AS (
  SELECT id, ts, d,
         sum(d) OVER (PARTITION BY id ORDER BY ts, d) AS depth
  FROM ev
)
SELECT id, ts AS covered_from,
       lead(ts) OVER (PARTITION BY id ORDER BY ts) AS covered_to
FROM run
WHERE depth > 0;
```

The `ORDER BY ts, d` tiebreak (ends before starts at the same instant) is
what makes abutting intervals merge instead of flickering out — half-open
discipline again.

## SCD Type 2 joins: the production checklist

The SCD-2 table (one row per version, `valid_from`/`valid_to`) is only as
good as its invariants. The interview-grade checklist:

| Invariant | Why it breaks | Enforcement |
|---|---|---|
| Chains are contiguous: `row[i].valid_to = row[i+1].valid_from` | Concurrent updates racing to close the old version and open the new one | `EXCLUDE USING gist (...) WITH &&` (below) or serial writes |
| Exactly one open row per key (`valid_to IS NULL`) | Bug in the "close old" branch | Partial unique index |
| `valid_from < valid_to` | Clock skew, midnight-edge bugs | `CHECK (valid_from < valid_to)` |
| No overlapping versions per key | Hand-rolled upserts | GiST exclusion constraint |

```sql
-- Structural enforcement (PostgreSQL): overlaps per key are impossible
CREATE TABLE price_history (
  item       text NOT NULL,
  price      numeric NOT NULL,
  valid_from timestamptz NOT NULL,
  valid_to   timestamptz NOT NULL,
  CONSTRAINT price_no_overlap
    EXCLUDE USING gist (item WITH =, tstzrange(valid_from, valid_to) WITH &&),
  CONSTRAINT price_order CHECK (valid_from < valid_to)
);
-- partial unique index for the "one open version" rule
CREATE UNIQUE INDEX one_open_version
  ON price_history (item) WHERE valid_to = 'infinity';
```

The exclusion constraint is the point interviewers want to hear: instead of
*checking* overlap at merge time (racy, see
[transaction isolation](../transactions/isolation-levels.md)), the
[GiST index](../indexing/gist.md) makes the overlapping write *fail at
commit* — correctness becomes a property of the schema, and the as-of join's
"at most one matching version" precondition is guaranteed by construction.

## Performance notes

- **The range join is the shape to fear.** `orders ⋈ price_history` on
  inequality alone can be `O(|orders| × |versions|)` before the planner
  intervenes. Modern engines have dedicated range-join / band-join
  optimizations (Spark's range join with binning, DuckDB's piecewise merge
  join) — but the general fix is the same idea as
  [join algorithms](../query-processing/joins.md): co-partition both sides on
  the key, keep per-key version lists short (merge-and-compact old
  versions), and let the within-key resolution be a scan.
- **Index shape for encoding (b):** `(item, valid_from DESC)` — the LATERAL
  per-row probe becomes an index-only "first match above a bound" lookup.
- **Time-zone handling:** store UTC, convert at presentation. A
  `date`-typed `valid_from` silently answers a different question when the
  client's timezone crosses midnight — and no constraint can save a query
  that compares `date` to `timestamptz` across a DST boundary. Timestamp
  semantics belong to the same family of assumptions as the
  [clock skew](../../distributed/fundamentals/README.md) problems in distributed
  systems: the database can only validate what it is given.

## Key Takeaways

- Overlap = `s1 < e2 AND s2 < e1` (half-open); `BETWEEN` reports touching
  intervals as overlapping and creates double-booking false positives.
- As-of joins: version-chain join when chains are constraint-complete;
  LATERAL-top-1 when they are not. Pick per invariant, not per habit.
- SCD-2 correctness is a *constraint* problem (GiST exclusion + partial
  unique index + CHECK), not an application problem.
- Interval union = eventize + running depth + islands; the `ts, d` ordering
  and head/tail gaps are the two standard edge-case killers.

## Cross-References

- [Gaps and Islands](./gaps-and-islands.md) — merge/union machinery in detail.
- [Temporal & Streaming Databases](../advanced/temporal-streaming.md) — SQL:2011 `SYSTEM VERSIONING`, bitemporal storage features.
- [Slowly Changing Dimensions](../../data-engineering/slowly-changing-dimensions.md) — SCD types 0–6 and warehouse pipeline design.
- [GiST Index](../indexing/gist.md) — the index structure behind exclusion constraints.
- [Isolation Levels](../transactions/isolation-levels.md) — why merge-time checks race without serialization.

## References

- James F. Allen, "[Maintaining Knowledge about Temporal Intervals](https://doi.org/10.1145/182.358434)", *Communications of the ACM* 26(11), 1983 — the thirteen interval relations underlying every overlap predicate.
- R. T. Snodgrass, *Developing Time-Oriented Database Applications in SQL*, Morgan Kaufmann, 2000 — [freely available from the author](https://www2.cs.arizona.edu/~rts/tdbbook.pdf); the foundational text on valid/transaction time, interval joins, and SCD-style versioning.
- Krishna Kulkarni, Jan-Eike Michels, "[Temporal features in SQL:2011](https://doi.org/10.1145/2380776.2380786)", *ACM SIGMOD Record* 41(1), 2012 — the standard's `PERIOD`/`SYSTEM VERSIONING` semantics.
- PostgreSQL Documentation, "[Range Types](https://www.postgresql.org/docs/current/rangetypes.html)" — `tstzrange`, GiST `&&` operator, and [exclusion constraints](https://www.postgresql.org/docs/current/ddl-constraints.html).
