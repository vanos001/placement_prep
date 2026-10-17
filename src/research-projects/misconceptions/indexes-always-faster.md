# "Indexes always make databases faster"

## Overview

"Add an index" is the most universally recommended database optimization, and
the recommendation is usually right — which is exactly why its boundary is
worth mapping. Indexes speed up *selective* reads at the price of slower
writes, extra storage, dependence on the planner's statistics, and occasional
planner misestimates. This page works through the regimes where an index
wins, the regimes where it is ignored, and the regimes where it actively
hurts, with arithmetic that holds up and references to the PostgreSQL
documentation that describes the behavior directly.

## The Claim, Stated Fairly

The strongest common form: "An index turns an O(n) table scan into an O(log n)
lookup, so any query touching an indexed column gets faster; adding indexes is
therefore always safe and usually free." The claim deserves fairness because
the first half is a real algorithmic fact: B-tree descent over 1,000,000 rows
touches about 20 pages, and that is precisely what an index does for an
equality or range predicate with good selectivity.

## Verdict

**Context-dependent.** Indexes make selective reads faster, but they tax every
write, consume memory and storage, and depend on the planner choosing them;
for low-selectivity predicates, tiny tables, or write-heavy workloads they are
neutral at best and harmful at worst.

## Why People Believe It

The kernel of truth is the B-tree arithmetic above, multiplied by experience:
the first index on a slow query is often a 100× or 1,000× win, and that
experience generalizes. Two further props hold the belief up. First, the
planner usually *protects* the read path: if an index would not help, the
planner scans the table instead, so the read side rarely gets worse — which
makes it feel like indexes have no downside. Second, textbooks describe
indexes in their happy regime, and most production tables are large with
selective predicates, so most indexes added in practice do help.

What is lost: every index is also a write-path obligation, a memory resident,
and a suggestion (not a command) to the planner. The claim is not false so
much as it silently changes the subject from "reads" to "the database".

## The Correct Formulation

| Dimension | Claim says | Actually |
|---|---|---|
| Read path | Always faster | Faster when the predicate is selective and the planner's estimates agree; planner may correctly choose a seq scan |
| Write path | Unmentioned | Every INSERT/UPDATE touches the heap plus every index (write amplification); more indexes, slower writes |
| Small tables | Faster | A table of a few pages is scanned in a handful of sequential reads; index descent can cost more |
| Storage/memory | Unmentioned | Each index is a full secondary structure that competes for buffer cache |
| Redundancy | Unmentioned | Index on (a) is redundant given one on (a, b) for most queries, yet still paid for on every write |

The precise read-path statement: an index helps when the fraction of rows
matching the predicate is small enough that "find matching index entries +
fetch their heap rows" beats "read the whole table sequentially". PostgreSQL
documents this directly: the planner compares costs, with a default
`seq_page_cost` of 1.0 and `random_page_cost` of 4.0, reflecting that random
heap fetches are more expensive than sequential ones.

## Where It Breaks

**Low selectivity.** A 5-page table of 100 rows, query
`WHERE status = 'active'` matching 80 rows. Sequential scan: 5 page reads.
Index scan: ~3–4 B-tree page reads plus one random heap fetch per matching
row — up to 80 page touches, roughly 16× the sequential cost. The planner
should refuse the index; whether it does depends on up-to-date statistics.
Stale stats say "a few rows" while reality has 80% — the planner picks the
index and the query regresses. PostgreSQL's planner statistics documentation
describes exactly this failure mode and `ANALYZE` as the countermeasure.

**Write amplification.** A table with the heap plus 5 secondary indexes does
at least 6 B-tree/heap writes per INSERT, before page splits and WAL records.
Bulk-loading 10,000,000 rows into an indexed table pays that tax 10,000,000
times; the same load into an unindexed table followed by one index build is
dramatically cheaper. Write-heavy OLTP tables with indexes nobody queries pay
this tax on every single row, forever.

**Cache displacement.** A 4 GB index for a rarely used query pushes 4 GB of
*useful* pages out of the buffer cache. The indexed query got faster; the
other 95% of the workload got slower. "The database is faster" was measured
on one query and lost on the aggregate.

**Redundant indexes.** `(user_id, created_at)` serves most queries that
`(user_id)` would; keeping both doubles write cost for that column with no
read benefit. Unused-index cleanup (via usage statistics such as
`pg_stat_user_indexes`) is a standing task in every mature Postgres
deployment.

**Planner misestimates.** Correlated columns, skewed distributions, and
cross-type comparisons can make the planner misestimate row counts by orders
of magnitude — enough to choose an index for a predicate matching half the
table. PostgreSQL mitigates with extended statistics and better sampling, but
the responsibility to check `EXPLAIN ANALYZE` remains the engineer's.

## Practical Implications

- Index for selectivity, not for coverage: ask what fraction of rows match
  before adding an index for a predicate.
- Treat every index as a standing write tax; audit with usage statistics and
  drop what queries no longer use.
- For bulk loads, drop or defer indexes and build them after the load.
- Use partial indexes (rows matching a predicate, e.g. only unprocessed
  orders) and expression indexes (e.g. on a function of a column) to make the
  index smaller and the write tax lower — both are documented PostgreSQL
  features designed for exactly this.
- Diagnose with `EXPLAIN (ANALYZE, BUFFERS)`, keep statistics fresh, and
  remember the planner decides per query — "the index exists" is not "the
  index is used".

## Interview Questions

### When does a database correctly refuse to use an available index?

When the predicate is not selective enough: fetching many rows through an
index means many random heap fetches, which cost more (default
`random_page_cost` 4.0 vs `seq_page_cost` 1.0) than one sequential scan. Tiny
tables are also cheaper scanned. The planner makes this call from statistics.

### Your INSERT-heavy table has five secondary indexes. What is the cost model, and what would you check before dropping one?

Each insert touches the heap plus five B-trees (write amplification), plus
page splits and WAL for each. Check per-index usage statistics, whether any
index is partially redundant with a composite, and whether a partial index
could serve the same query more cheaply. Dropping one unused index is a
direct write-throughput win.

### A query regressed after a data change even though nothing in the schema changed. How can an index be involved?

Statistics went stale: the planner's row estimate no longer matches reality,
so it chose an index for a now-unselective predicate (or vice versa).
`EXPLAIN (ANALYZE, BUFFERS)` exposes the misestimate; `ANALYZE` or extended
statistics on correlated columns fixes it.

## Key Takeaways

- An index is a read-path bet paid for on the write path, in storage, and in
  buffer cache displacement — "faster" needs a subject: faster *for which
  query*, and slower *for which writes*.
- Selectivity is the dividing line; small tables and low-selectivity
  predicates belong to the sequential scan.
- The planner is a cost-based decision maker with fallible statistics, not an
  index oracle; `EXPLAIN (ANALYZE, BUFFERS)` is how you audit it.
- Partial and expression indexes exist precisely because full indexes are
  often more than the workload needs.

## Cross-References

- [Assumptions Hunt: Complexity Claims](../assumptions-hunt/complexity-claims.md)
  — where the O(log n) slogan hides its assumptions
- [Indexing Strategy](../../dbms/indexing-strategy.md) — the mechanics of
  choosing composite, partial, and covering indexes
- [Query Planner](../../dbms/query-planner.md) — how the cost model above is
  actually computed
- [Trade-offs Reference](../../trade-offs/README.md) — quick-reference
  comparison tables for these choices
- [Cache Always Improves](./cache-always-improves.md) — the buffer-cache
  displacement argument in its own right

## References

- PostgreSQL documentation. *Indexes: Partial Indexes*.
  <https://www.postgresql.org/docs/current/indexes-partial.html>
- PostgreSQL documentation. *Indexes: Indexes on Expressions*.
  <https://www.postgresql.org/docs/current/indexes-expressional.html>
- PostgreSQL documentation. *Statistics Used by the Planner*.
  <https://www.postgresql.org/docs/current/planner-stats.html>
- PostgreSQL documentation. *Query Planning: Planner Cost Constants*
  (`seq_page_cost`, `random_page_cost`).
  <https://www.postgresql.org/docs/current/runtime-config-query.html>
