# Plan Caching, Parameter Sniffing, and Plan Instability

Planning a query costs real time — a few microseconds for trivial statements,
milliseconds for 20-table joins with subqueries — and OLTP workloads execute
the *same statement shape* millions of times with different literals. Plan
caches exist so that cost is paid once. The cache, however, makes the plan
*older than the data*: statistics move, parameter distributions differ, and a
plan chosen for one execution is silently reused for executions where it is
catastrophically wrong. Parameter sniffing, plan instability, and reoptimization
are the three names for that gap.

The planner's cost model and join selection are covered in
[Query Optimization Deep Dive](../query-optimization-deep.md) (including the
prepared-statement pipeline) and [Cost Estimation](./cost-estimation.md);
runtime-adaptive engines are in
[Adaptive Query Execution](../advanced/adaptive-query-execution.md). This page
is about the cache itself: keys, lifetimes, invalidation, per-engine policies,
and the interview staples (sniffing, generic-vs-custom plans, plan forcing).

## What is cached, and under what key

The plan cache maps a *statement template* to a compiled plan. The key is not
the SQL text but a normalized form of it:

- **SQL Server** hashes the statement text into a `sql_handle`; two queries
  differing only in literal values may still be separate entries unless
  parameterization applies. Ad-hoc workloads notoriously flood the cache with
  single-use plans — hence `optimize for ad hoc workloads`, which stores a
  compiled-plan stub and compiles fully only on the second execution.
- **PostgreSQL** caches plans per prepared statement *per session* (plus
  per-relation cached plans invalidated by catalog changes). There is no
  cross-session plan cache: `PREPARE` in one session is invisible in another.
  The extended-protocol (`libpq`, JDBC with `prepareThreshold`) uses the same
  machinery implicitly — which is why "the app got slower in production"
  often traces to prepared statements the developer never wrote explicitly.
- **Oracle** stores cursors in the shared pool keyed by the SQL text; cursor
  sharing (`EXACT` by default) decides whether differing literals produce new
  child cursors or reuse one.
- **MySQL** does *not* cache prepared-statement plans — server-side prepare
  stores only parse metadata, and every execution is optimized afresh. A
  defensible answer to "how do you fix parameter sniffing in MySQL" is
  "you mostly can't; it re-plans every time" — the interview point being
  that not every engine has the disease, only the cure trade-offs.

The cache is also a memory consumer: SQL Server's plan cache competes with
the buffer pool for the same memory. Cache bloat from unparameterized SQL is
therefore a *data* problem as much as a CPU problem.

## Invalidation: when a cached plan must die

A plan references physical objects and statistics; when those change, cached
plans depending on them are invalidated. The standard invalidators:

| Trigger | Example |
|---|---|
| Schema change | `ALTER TABLE ... ADD COLUMN`, index create/drop |
| Statistics refresh | `ANALYZE` (PostgreSQL), auto-update-stats (SQL Server) |
| Setting changes | `SET enable_seqscan = off`, isolation level, parallelism options |
| Engine version / cardinality estimator | SQL Server CE-version-per-database; PostgreSQL major upgrades |

Two production pathologies come straight from this list:

- **Stats-update storms.** `ANALYZE` completes → thousands of statements
  re-plan at once → CPU cliff. Staggering maintenance or relying on
  auto-stats thresholds changes the *timing* of compile spikes, not their
  existence.
- **Regression after upgrades.** A new optimizer version re-plans everything
  once, and one expensive query per hundred gets a worse plan — the classic
  reason upgrades are gated on Query Store / plan-regression dashboards.

## Parameter sniffing: the mechanism

A plan is compiled *for some parameter values*. If the planner peeks at the
actual values of the first execution, the plan is optimal for that value's
statistics bucket and arbitrary for others:

```sql
-- orders(status): 1,000,000 'shipped' rows; 50 'pending' rows
CREATE PROCEDURE get_orders @status AS varchar(20) AS
  SELECT * FROM orders WHERE status = @status;

-- first call: @status = 'pending'  → nested-loop + index seek  (perfect)
-- second call: @status = 'shipped' → same cached plan, now 10^6 index
--                                     seeks + 10^6 key lookups  (disaster)
```

The plan is not "wrong"; it is *specialized*. The bug is the silent reuse.
The standard fixes form a spectrum:

| Fix | Effect | Cost |
|---|---|---|
| `OPTION (RECOMPILE)` (statement-level) | fresh plan per execution, values peeked | planning CPU per call |
| `OPTIMIZE FOR UNKNOWN` | plan for average density across the histogram | mediocre-for-everything plan |
| `OPTIMIZE FOR (@status = 'shipped')` | plan for the known-hot value | bad for the tail |
| Local variable copy | pre-2014 folklore: disables value peeking | subtle, version-dependent |
| Multi-plan (see below) | plan per distribution class | dispatcher overhead |

**Interview-grade detail:** which fix applies depends on the *distribution*.
Two sharply different value classes with stable frequencies → per-class plans.
Skewed-but-mostly-one-class → optimize for the hot class. Fully recompiled
statements are the right answer only when planning is cheap relative to the
execution (otherwise you have traded a bad plan for a busy CPU).

## PostgreSQL: generic vs custom plans

PostgreSQL's prepared statements get the cleanest formulation of the
trade-off, and interviews love the specific rule ([PREPARE
docs](https://www.postgresql.org/docs/current/sql-prepare.html)):

1. Executions 1–5 use **custom plans** (parameter values known, plan specialized);
   their average estimated cost is recorded.
2. From execution 6, a **generic plan** (parameter-blind) is built; it is used
   only if its cost is not enough worse than the average custom-plan cost to
   make per-call replanning preferable.
3. `SET plan_cache_mode = force_custom_plan | force_generic_plan` overrides
   the heuristic.

The subtlety worth knowing: the comparison uses *estimated* costs with
parameter values peeked for the custom side. Estimates are exactly what
[cardinality estimation](../advanced/cardinality-estimation.md) gets wrong
under skew, so a generic plan can win the cost comparison and still be the
wrong execution choice — the scenario behind many "it's fast in psql, slow in
the app" reports (psql runs the ad-hoc text; the app uses the extended
protocol and gets the generic plan).

## Multi-plan engines: runtime reoptimization

When one plan cannot serve one query, the engine needs either *many plans* or
*adaptive execution*:

- **SQL Server 2022 Parameter Sensitive Plan Optimization** computes at
  compile time that a predicate's cardinality spans a "sensitive range," and
  emits a *dispatcher plan* that selects between specialized variants based on
  the runtime parameter — multiple plans for one statement, chosen per
  execution.
- **Oracle Adaptive Cursor Sharing** monitors child cursors per statement and
  marks them selective-class-specific after observing actual row counts.
- **Oracle Adaptive Plans / Spark AQE** take the other fork: one plan whose
  join strategy can be re-decided mid-flight once cardinalities are known —
  covered in [Adaptive Query Execution](../advanced/adaptive-query-execution.md).
- **Runtime recompile thresholds**: SQL Server recompiles statements touching
  table variables when their row counts change by more than a threshold —
  reoptimization as a bounded loop rather than a one-shot decision.

## Diagnosing plan instability in production

The workflow interviewers probe for:

1. **Confirm the shape changed.** Query Store (SQL Server) stores plans per
   query with execution history; PostgreSQL lacks this natively — capture
   `auto_explain` with `log_analyze` or diff `pg_stat_statements` timing
   shifts against `ANALYZE` timestamps.
2. **Check estimate error**, not plan aesthetics:
   `EXPLAIN ANALYZE` rows-vs-rows mismatch at the same node is the smoking
   gun (see [Execution Plans](./execution-plans.md)).
3. **Correlate with invalidation events** (stats updates, DDL, upgrades).
4. **Stabilize deliberately**: statistics on the skewed column (or extended
   statistics), plan forcing where the good plan is known, or
   reparameterization — `OPTIMIZE FOR UNKNOWN` is a *decision about the
   distribution*, so make it consciously.

## Key Takeaways

- Plan caches trade compile time for staleness; the cache key is the
  statement template, and every invalidation trigger is a schema/stats/
  setting change.
- Parameter sniffing is the *reuse* of a specialized plan, not the
  specialization; fixes are a spectrum from recompile (fresh, costly) to
  multi-plan dispatch (stable, complex).
- PostgreSQL picks generic plans after 5 custom executions by estimated-cost
  comparison — overridable with `plan_cache_mode`; MySQL has no plan cache
  at all.
- Diagnose with estimate-vs-actual rows correlated to invalidation events;
  Query Store / `auto_explain` are the tools, plan forcing the last resort.

## Cross-References

- [Query Optimization Deep Dive](../query-optimization-deep.md) — end-to-end plan pipeline and prepared-statement plans.
- [Cost Estimation](./cost-estimation.md) — histograms and selectivity that drive the plan choice.
- [Cardinality Estimation](../advanced/cardinality-estimation.md) — why estimates under skew mislead the generic/custom comparison.
- [Adaptive Query Execution](../advanced/adaptive-query-execution.md) — mid-flight reoptimization instead of multi-plan dispatch.
- [Execution Plans](./execution-plans.md) — reading EXPLAIN/EXPLAIN ANALYZE for estimate errors.

## References

- PostgreSQL Documentation, "[PREPARE](https://www.postgresql.org/docs/current/sql-prepare.html)" — the five-execution custom/generic rule and `plan_cache_mode`.
- Microsoft Learn, "[Parameter Sensitive Plan Optimization](https://learn.microsoft.com/en-us/sql/relational-databases/performance/parameter-sensitive-plan-optimization?view=sql-server-ver17)" — dispatcher plans and the sensitive-range detection in SQL Server 2022.
- Microsoft Learn, "[Optimize for ad hoc workloads](https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/optimize-for-ad-hoc-workloads-server-configuration-option)" — single-use plan stubs and cache pollution.
- Oracle Database SQL Tuning Guide, "[Improving RWP: Cursor Sharing](https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/improving-rwp-cursor-sharing.html)" — cursor sharing modes and adaptive cursor sharing.
- B. Doms, "Batch Compilation, Recompilation, and Plan Caching Issues in SQL Server 2005", Microsoft whitepaper, 2006 — the classical deep-dive on sniffing and cache behavior.
