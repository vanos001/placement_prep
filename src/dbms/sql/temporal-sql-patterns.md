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

## Bitemporal Tables: Valid Time Meets Assertion Time

Everything above versions facts along **one** axis. The moment an auditor
asks "*and* what did you believe on March 3rd about the state on March
1st?", one axis stops being enough. The introductory model (valid vs
transaction time, one schema sketch) is in [Temporal & Streaming
Databases](../advanced/temporal-streaming.md); this section works the 4D
model, the correction workflow, the four query quadrants, and the
engineering reasons bitemporal tables are rare in practice.

### Two axes, four dimensions

- **Valid time** `[vt_from, vt_to)`: when the fact was true *in reality*
  (the insured event's date, the rate's effective period). The application
  asserts it; the database cannot know it.
- **Assertion (transaction) time** `[at_from, at_to)`: when the database
  *believed* the row. Only the system may assign it — typically at commit —
  and it is monotone, unlike valid time, which can be corrected backwards.

A bitemporal fact is a record valid in one interval **and** asserted in
another — a rectangle in the (valid, assertion) plane, which is why this is
called the 4D model. The conceptual primary key of a bitemporal fact is
**(entity, valid period, assertion period)**: two rows may share the same
entity and even the same valid period, and still be different facts if they
were believed at different times. Implementations commonly store
`(entity, vt_from, at_from)` as the physical key and reconstruct the
interval ends by chain closure (`at_to` = the next assertion's `at_from`,
open rows carry the +∞ sentinel), which is exactly the SCD-2 chain
discipline of the previous sections applied to the second axis.

### The correction workflow: history is append-only

A late-arriving correction must never `UPDATE` the value of a historical
row — that destroys the very history the table exists to preserve. Instead
it **closes the old assertion interval and inserts a new row**: same
entity, corrected value (and possibly corrected valid period), `at_from` =
now. Both axes stay intact: the old row answers "what did we believe
then?", the new one "what do we believe now?".

Worked example — a claim's payout is asserted as 100 on day 1
(`2024-06-01`) and corrected to 150 on day 5 (`2024-06-05`). Run with
Python's `sqlite3` module this session (the `sqlite3` CLI was not used;
every output below is pasted from that run):

```sql
CREATE TABLE claim_payout (
  claim_id TEXT    NOT NULL,
  payout   NUMERIC NOT NULL,
  vt_from  TEXT    NOT NULL,          -- valid time: when true in reality
  vt_to    TEXT    NOT NULL,          -- half-open [vt_from, vt_to)
  at_from  TEXT    NOT NULL,          -- assertion time: when the DB believed it
  at_to    TEXT    NOT NULL,          -- '9999-12-31' = still believed
  PRIMARY KEY (claim_id, vt_from, at_from)
);
-- day 1: payout asserted as 100
INSERT INTO claim_payout VALUES ('CLM-9',100,'2024-06-01','9999-12-31','2024-06-01','9999-12-31');
-- day 5: corrected to 150 -> close old assertion, append new assertion row
UPDATE claim_payout SET at_to='2024-06-05' WHERE claim_id='CLM-9' AND at_to='9999-12-31';
INSERT INTO claim_payout VALUES ('CLM-9',150,'2024-06-01','9999-12-31','2024-06-05','9999-12-31');
```

```text
--- full history (2 rows, append-only) ---
('CLM-9', 100, '2024-06-01', '9999-12-31', '2024-06-01', '2024-06-05')
('CLM-9', 150, '2024-06-01', '9999-12-31', '2024-06-05', '9999-12-31')

--- Q1: what did we believe on day 3? (as-of assertion time) ---
SELECT ... WHERE at_from<='2024-06-03' AND at_to>'2024-06-03'
→ ('CLM-9', 100, '2024-06-01', '2024-06-05')

--- Q2: what is true now? (current-of-now) ---
SELECT ... WHERE at_to='9999-12-31'
→ ('CLM-9', 150, '2024-06-05')
```

Note the day-3 query returns the *closed* row — the correction on day 5
did not retroactively rewrite the day-3 belief; it only closed that
assertion's interval going forward in assertion time.

### The four query quadrants

Combining an assertion-time predicate (current vs as-of) with a valid-time
predicate (current vs as-of) gives four questions, and in a
finance/compliance interview you should be able to name all four — each is
a different regulatory product:

| valid \ assertion | current assertion (`at_to = '9999-12-31'`) | as-of assertion `t` |
|---|---|---|
| **current valid** (covers now) | **(d)** the payout as it stands today | **(c)** what the day-3 snapshot believed about "now" — stale by construction |
| **as-of valid** day 3 | **(a)** what we *now* believe was true on day 3 — the corrected history | **(b)** what the day-3 snapshot believed about day 3 — the audit point |

Ran this session (same fixture): (a) → 150, (b) → 100, (c) → 100, (d) →
150. Quadrant (b) is the regulator's question ("what did you report, when
asked?"), quadrant (a) is the restatement, and the (a)−(b) delta is the
restatement ledger. Quadrant (c) exposes a subtlety: a day-3 snapshot's
"open" valid interval extends to ∞, so it claims knowledge of the future
that may since have been corrected — never join (c)-style rows to current
reference data without asserting both axes.

**Retraction semantics.** A correction says "the value was wrong"; a
retraction says "the fact never existed." Two encodings: **closed
intervals** — shrink the row's `vt_to` so the fact stops covering the
disputed period — or **negation rows**: an explicit row asserting absence
(`payout = NULL` or `kind='retraction'`) for the disputed valid period.
Negation rows preserve the full decision trail and make every assertion
change an insert, at the cost of query logic that must distinguish "no
row" from "row asserting absence" — the same distinction as tombstones vs
missing keys in [versioned stores](../advanced/mvcc-internals.md).

### Why this is hard in production

- **Assertion time must be captured by the system, not the caller.** An
  application-supplied `at_from` inherits clock skew and batch lies: a
  backfill loading June's data in July would assert `at_from` = June,
  destroying the axis's monotonicity. SQL Server's system-versioned
  tables assign period columns at the engine level, and its documentation
  is explicit about the granularity: "all rows inserted within a single
  transaction have the same UTC time recorded in the column corresponding
  to the start of the SYSTEM_TIME period" (Microsoft Learn, [Temporal
  tables](https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-tables?view=sql-server-ver17)) — commit-time, not
  statement-time, semantics. Where the engine cannot do this (PostgreSQL
  core has no SQL:2011 system versioning), triggers or the ingest pipeline
  must be the *only* writers of the column — which is why hand-rolled
  bitemporal tables rot.
- **Indexing two ranges.** Hot paths: `(entity, at_from, at_to)` for the
  current-of-now probe and the wider `(entity, vt…, at…)` shape for
  quadrant queries. The same `tstzrange` + GiST machinery that enforces
  SCD-2 above enforces "no overlapping *open* assertions per entity" —
  note that overlapping assertions across history are *legal* (that is
  the point), so a naive `&&` exclusion over both axes is wrong; constrain
  only currently-believed rows (`WHERE at_to = '9999-12-31'`, a partial
  constraint).
- **Unbounded growth.** Every correction adds a row and never removes one.
  Pruning is an audit-policy decision, not an engineering one: keep open
  assertions + a bounded assertion window (e.g. 7 years) + periodic
  snapshots, compacting chains older than the regulatory horizon — with
  the compacted state itself *asserted*, so the pruning is discoverable.
- **Engine support is asymmetric.** SQL:2011 standardized system
  versioning and application-time periods (Kulkarni & Michels walk the
  semantics in the SIGMOD Record paper cited below; do not expect `FOR
  SYSTEM_TIME` alone to give
  bitemporality — combining system and application time is exactly the
  two-axis intersection above). SQL Server ships `SYSTEM_VERSIONING` with
  a managed history table; PostgreSQL's answer is the range-type
  toolkit (its docs: "Using NULL for either bound causes the range to be
  unbounded on that side" — the `±∞` sentinel discipline) plus trigger-
  or pipeline-captured columns (SQLite's [CREATE
  TRIGGER](https://www.sqlite.org/lang_createtrigger.html) documents the
  primitive most lightweight stacks reach for); the theory descends from
  Snodgrass's temporal-query-language work and Jensen & Snodgrass's
  [temporal specialization](https://doi.org/10.1109/ICDE.1992.213149).

**Interview problem (senior) — retroactive rate change.** *An insurer's
regulator demands: on day 1 the tariff was 1.2%, discovered on day 40 that
it had actually been 1.35% since day 1, and changed to 1.4% from day 45.
Model the ledger rows.* Expected: three assertion rows for one policy —
`[1.2%]` valid `[day1, ∞)` asserted `[day1, day40)`; `[1.35%]` valid
`[day1, day45)` (the retroactive correction re-dates *valid* time) asserted
`[day40, day45)`; `[1.4%]` valid `[day45, ∞)` asserted `[day45, ∞)`. The
quadrant-(b) query on day 20 returns 1.2% (what was believed), quadrant
(a) on day 20 returns 1.35% (the corrected truth), and premium
recalculation joins facts to quadrant (a) rows while regulatory reporting
replays quadrant (b) rows. Rubric: junior overwrites the rate; mid
produces three rows but re-dates assertion time instead of valid time;
senior keeps both axes straight and names the (a)/(b) split.

**Interview problem (senior) — deduplicating overlapping assertion
chains.** *A buggy backfill ran twice, so each entity has interleaved
duplicate assertion chains with equal `at_from` in places. Recover an
invariant table without losing audit history.* Expected: (1) don't delete
— move everything to a quarantine table (the quarantine itself gets an
assertion stamp); (2) define a deterministic winner per
`(entity, valid period, assertion instant)` — e.g. highest pipeline
run-id, then lexicographic payload hash — and rebuild chains by re-closing
intervals in assertion order; (3) for *equal* assertion instants, keep one
row and emit a synthetic correction row stamped with the repair time, so
the "we believed two things at once" interval is represented, not
erased; (4) prevent recurrence with the partial exclusion constraint on
open assertions (above) — the bug is precisely an invariant the schema
should have been enforcing. Rubric: junior dedups with `DISTINCT ON` and
destroys history; mid separates quarantine + deterministic replay; senior
represents the ambiguity inside the model and adds the structural
constraint.

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
- [MVCC Internals](../advanced/mvcc-internals.md) — version chains are assertion-time row versioning generalized to concurrency control.
- [Search Fundamentals](../../search/fundamentals.md) — a different flavor of "as-of" visibility: segment/refresh visibility ladders in search engines.

## References

- James F. Allen, "[Maintaining Knowledge about Temporal Intervals](https://doi.org/10.1145/182.358434)", *Communications of the ACM* 26(11), 1983 — the thirteen interval relations underlying every overlap predicate. DOI re-verified via Crossref this session.
- R. T. Snodgrass, *Developing Time-Oriented Database Applications in SQL*, Morgan Kaufmann, 2000 — [freely available from the author](https://www2.cs.arizona.edu/~rts/tdbbook.pdf) (URL fetched this session); the foundational text on valid/transaction time, interval joins, and SCD-style versioning.
- Krishna Kulkarni, Jan-Eike Michels, "[Temporal features in SQL:2011](https://doi.org/10.1145/2380776.2380786)", *ACM SIGMOD Record* 41(1), 2012 — the standard's `PERIOD`/`SYSTEM VERSIONING` semantics. DOI re-verified via Crossref this session.
- PostgreSQL Documentation, "[Range Types](https://www.postgresql.org/docs/current/rangetypes.html)" — `tstzrange`, GiST `&&` operator, and [exclusion constraints](https://www.postgresql.org/docs/current/ddl-constraints.html); fetched this session, including "Using NULL for either bound causes the range to be unbounded on that side."
- Microsoft Learn, "[Temporal tables](https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-tables?view=sql-server-ver17)" — fetched in full this session; system-managed period columns, managed history table, transaction-begin-time assignment, and `FOR SYSTEM_TIME` subclauses quoted or paraphrased from the page.
- SQLite Documentation, "[CREATE TRIGGER](https://www.sqlite.org/lang_createtrigger.html)" — fetched this session; the trigger primitive used for pipeline/trigger-captured assertion-time columns. The chapter's worked example was executed with Python's `sqlite3` module (SQLite 3.x), not the CLI.
- Christian Jensen, Richard T. Snodgrass, "[Temporal specialization](https://doi.org/10.1109/ICDE.1992.213149)", *Proc. 8th International Conference on Data Engineering (ICDE 1992)* — the semantics of granule/grouping operations on temporal values. Crossref-verified (title/authors/venue) this session.
