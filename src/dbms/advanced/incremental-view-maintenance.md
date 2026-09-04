# Materialized View Maintenance and Incremental Computation

A materialized view is a **caching contract**: the application promises a read pattern (the same expensive query over and over), the database promises precomputed answers, and the fine print is *who pays to keep the stored result correct, and when*. When a base table changes, the stored result is wrong by exactly the effect of that change; every maintenance strategy is a schedule for paying off that error: recompute everything (deferred refresh), recompute in-line with the write (synchronous maintenance), or recompute only the affected slice (incremental view maintenance, IVM). This page covers the refresh strategies real engines ship, the classical IVM algorithms (counting, delta propagation, aggregate decomposition), the hard cases (DISTINCT, outer joins, min/max), the modern streaming incarnations (Materialize, Flink, warehouse MVs), and the cost model that decides when a materialized view is the wrong tool. For the application-cache counterpart, see [Advanced Caching Strategies](../caching/advanced-caching.md); materialized views are the general form of that problem, solved where the invalidation key is known exactly: the query plan itself.

## Refresh strategies: who pays, and when

| Strategy | Cost timing | Freshness | Shipping examples |
|---|---|---|---|
| Eager / synchronous (ON COMMIT, indexed views) | every commit, inside the transaction | exact | SQL Server indexed views, Oracle `REFRESH ON COMMIT` |
| Deferred / on-demand | explicit `REFRESH` command | stale by choice | PostgreSQL `REFRESH MATERIALIZED VIEW`, Oracle `ON DEMAND` |
| Periodic / scheduled | cron or job scheduler | stale by up to one period | Oracle refresh groups, warehouse MV refresh jobs |
| Incremental (true IVM) | at every change, but proportional to the *delta* | exact (or bounded-stale) | SQL Server indexed views (deltas), Materialize, Flink, BigQuery MVs |

### PostgreSQL: deferred refresh, all or nothing

PostgreSQL has the simplest contract. `CREATE MATERIALIZED VIEW` stores the query result and remembers the query so it can be re-run; the stored rows change only via `REFRESH MATERIALIZED VIEW`, which "completely replaces the contents of a materialized view." Without options the refresh takes an **exclusive lock**: readers block, because the old contents are discarded first and there is no snapshot of the result to serve while the backing query runs. `CONCURRENTLY` avoids locking out readers, and its restrictions tell you exactly why it is harder:

```sql
-- CONCURRENTLY requires:
--  1. at least one UNIQUE index on the view, using only column names,
--     no expressions, no WHERE clause (must cover ALL rows)
--  2. the view must already be populated (not WITH NO DATA)
--  3. only ONE concurrent refresh at a time per view
CREATE MATERIALIZED VIEW dept_summary AS
SELECT dept_id, COUNT(*) AS emp_count, SUM(salary) AS total_salary
FROM employees GROUP BY dept_id
WITH NO DATA;                                  -- created unscannable

CREATE UNIQUE INDEX ON dept_summary (dept_id); -- prerequisite for CONCURRENTLY
REFRESH MATERIALIZED VIEW CONCURRENTLY dept_summary;
```

The unique-index requirement is not bureaucracy: a concurrent refresh needs to **diff** the new result against the stored one and apply per-row changes so readers always see a complete, valid snapshot. A diff requires a key. Non-concurrent refresh instead swaps the whole heap — cheaper for a mostly-changed view, catastrophic for a 40-minute recompute on a live dashboard. Two more doc details: `WITH NO DATA` leaves the view *unscannable* (queries against it error until the first refresh — a common production surprise), and `REFRESH MATERIALIZED VIEW` is documented as a PostgreSQL extension — refresh semantics were never standardized, so every engine's contract differs.

### SQL Server: synchronous maintenance, restricted definitions

SQL Server indexed views go the opposite way: create a **unique clustered index** on a view and every subsequent `INSERT`/`UPDATE`/`DELETE` on the base tables maintains the view *inside the same transaction* — the read is always exact, and the write pays. The documented restrictions keep that synchronous maintenance implementable and correct: the view must be created `WITH SCHEMABINDING` (base tables cannot change out from under the maintenance plan), be deterministic, reference only base tables in the same database (no other views), and with `GROUP BY` it must select `COUNT_BIG(*)`, cannot use `HAVING`, and may index only `GROUP BY` columns. `COUNT_BIG(*)` is the textbook auxiliary quantity bought for maintenance: a bare `SUM` cannot distinguish an empty group from nulls, and maintaining sums on delete requires knowing the group's size.

Automatic query rewrite to indexed views is deliberately narrow: "automatic use of an indexed view by the query optimizer is supported only in specific editions" (Enterprise; on Standard you must query the view by name with the `NOEXPAND` hint). Why so limited? Matching an arbitrary query to a stored view is expensive and can be wrong-footed by expressions, non-determinism, and statistics; aggressive rewriting also commits the engine to maintaining the rewrite's correctness conditions (see Snowflake/BigQuery below). The pragmatic reading: in SQL Server, plan to use indexed views explicitly.

### Oracle: fast refresh with materialized view logs, rewrite on request

Oracle's implementation is the most complete classical one. Materialized views refresh `COMPLETE` (re-execute the defining query), `FAST` (apply deltas), or `FORCE` (fast if possible, else complete), `ON COMMIT` (synchronous) or `ON DEMAND` (scheduled via `DBMS_REFRESH` refresh groups). FAST refresh is powered by **materialized view logs** on each master table — auxiliary tables recording `INSERT`/`UPDATE`/`DELETE` deltas, keyed by primary key or rowid. This is the counting algorithm made into a product: the log is the delta store, the refresh job is the delta propagator, and the log is what makes deletes maintainable for aggregates. Oracle also ships **query rewrite**: `ENABLE QUERY REWRITE` lets the optimizer transform "a user request written in terms of master tables into a semantically equivalent request that includes one or more materialized views."

### MySQL: no materialized views — build summary tables

MySQL has never shipped materialized views; its manual documents views only as virtual tables (updatable views, `CHECK OPTION`, view restrictions — no stored results, no refresh). The production pattern is a hand-rolled **summary table** maintained by triggers — exactly the IVM sketch of the next section. This is not a limitation to apologize for: it makes the maintenance contract explicit and tunable (defer writes to a queue, batch deltas, refresh off-hours) instead of implicit in the engine.

## Incremental view maintenance: the algorithms

**The problem.** Given view `V = Q(R1,...,Rn)` and a delta `ΔR` (insertions `+` and deletions `−`) applied to one base relation, compute `ΔV` such that `V' = V ⊎ ΔV` equals `Q(R')` — without evaluating `Q` over the whole database. Blakeley, Larson, and Tompa (1986) established the pruning idea: **an update is irrelevant to the view if its old and new rows join with no view-producing combinations**. Concretely, for an SPJ view `V = π(R ⋈ S)`: an insert of `r ∈ R` contributes exactly `π(r ⋈ S)` new rows; a delete of `r` removes exactly `π(r ⋈ S)`. Delta propagation is therefore just "run the join with the delta on one side":

```
ΔV(+) = (R ⋈ ΔS)  ∪  (ΔR ⋈ S)  ∪  (ΔR ⋈ ΔS)      -- inserts
ΔV(−) = (R' ⋈ (−ΔS)) ∪ ((−ΔR) ⋈ S')              -- deletes, against NEW states
```

**The counting algorithm (C).** For multisets (SQL's bags), removal is the hard part: to delete a view tuple you must know whether at least one derivation of it *survives* elsewhere in the base data. The counting method, introduced by Gupta, Mumick, and Subrahmanian in "Maintaining Views Incrementally" (SIGMOD 1993), attaches to each view tuple a **count = number of derivations** from the base relations. Deletes decrement counts and only remove the tuple at zero; inserts increment. Worked example — `V = R ⋈ S` on `R.a = S.b`, with `R = {(2,1),(2,1),(1,0)}`, `S = {(1,9)}`:

```text
View tuple τ = ((2,1),(1,0))  has cnt(τ) = 2   (two derivations via the two (2,1) rows)

DELETE one (2,1) from R:
  cnt(τ) = 2 − 1 = 1    → τ stays (it still has a derivation)
DELETE the second (2,1):
  cnt(τ) = 1 − 1 = 0    → NOW τ is removed from V
```

A `SELECT DISTINCT` view is just the counting view with the counts hidden: the distinct row must persist until its count hits zero, which is precisely why **DISTINCT (and `EXISTS`, and any duplicate-insensitive view) is not self-maintainable from the delta alone** — you cannot tell from "row `r` was deleted" whether `r` was the last derivation. Keep the counts or recompute; Griffin and Libkin's *Incremental Maintenance of Views with Duplicates* (SIGMOD 1995) formalizes exactly this multiplicity bookkeeping.

**Keys bound the maintenance cost.** Delta propagation `(ΔR ⋈ S)` is only cheap if it can *find* its join partners — the join key must be indexed on `S`. This is the operational meaning of **key-bounded maintenance**: work per update is bounded by the view rows affected, found by looking up the update's key; if propagation must scan `S`, the "incremental" maintenance is quadratic in disguise. It also bounds the counting state: only counts for keys in the update's range are touched. This is why Oracle's MV logs are keyed on primary key/rowid and why count-style auxiliary columns live in per-key rows.

**Self-joins: multiplicities bite.** For `V = R ⋈_θ R`, the set-at-a-time delta needs a third term:

```
ΔV = (ΔR ⋈ R) ∪ (R ⋈ ΔR) ∪ (ΔR ⋈ ΔR)
```

The last term matters when two rows inside the same delta join with each other (insert `{(4,1),(1,4)}` in one batch into an empty `R`: the view gains `(r1,r2)` and `(r2,r1)`, derivations between two *new* rows). Row-at-a-time propagation (triggers) gets this for free because each row is applied to a state that already includes the previous delta rows — one reason trigger designs are easier to make correct than bulk delta pipelines, and bulk pipelines faster. Within a batch, `ΔR ⋈ R` must be multiplicity-aware: inserting `k` rows that each join `m` partners adds `k·m` view tuples, not `m`. An *update* is delete-old + insert-new; careful engines propagate the changed column values directly instead.

**Aggregate views: decomposable vs not.** Maintenance difficulty is governed by the algebra of the aggregate:

| Aggregate | Delta on `+x` | Delta on `−x` | Maintainable in place? |
|---|---|---|---|
| `SUM` | `S += x` | `S -= x` | yes |
| `COUNT` | `C += 1` | `C -= 1` | yes |
| `AVG` | via `(SUM, COUNT)` | via `(SUM, COUNT)` | yes — store both |
| `MIN`/`MAX` | `if x < M: M = x` | **cannot** without aux structure | delete of the current min needs the *next* min |

`AVG` is the canonical lesson: never store the average, store the pair that generates it (why SQL Server requires `COUNT_BIG(*)` alongside aggregates, and why BigQuery stores `AVG` materialized views "as an intermediate sketch"). `MIN`/`MAX` are **incrementally maintainable on insert but not on delete**: deleting the current minimum requires knowing the second-smallest value, which no constant-size summary provides — you need a per-group ordered auxiliary structure (per-group index or top-k sketch) or a recompute. The interview-worthy generalization: *delta-maintenance is possible exactly when the aggregate is invertible (a group) or can be completed into one* (`AVG` via `SUM`/`COUNT`; `MIN` via an order statistic, at added space cost).

**Outer joins.** In `R LEFT JOIN S`, a delete on the *preserved* side (`R`) can remove a view row entirely, while a delete on the null-supplying side (`S`) can *change* a view row from its matched form back to its null-extended form — the delta is an update, not an insert/delete. Propagating it requires knowing, per `R` row, whether matched partners remain — again a count. Combined with `DISTINCT`, this is where hand-rolled IVM most often goes silently wrong.

## Modern systems: IVM as a streaming substrate

**Materialize / differential dataflow.** Materialize runs views as dataflow programs where every collection — inputs and views — is a **set of (data, timestamp, difference) triples** rather than a static table. The substrate is differential dataflow (McSherry, Murray, Isaacs, Isard, CIDR 2013) on the timely dataflow coordination layer (the same authors' Naiad, SOSP 2013). Differential dataflow programs use `map/filter/join/reduce/iterate` and "respond to arbitrary changes to initially empty input collections," acting "only where changes in collections occur, and no work elsewhere." Three consequences matter for interviews. First, **joins over arbitrarily changing inputs**: both sides of every join are maintained incrementally, so an insert into either input propagates in time proportional to the affected key neighborhood, and the view is *always current* to the frontier of ingested data (Materialize persists results "incrementally updated"). Second, **iteration** is incremental too: fixed-point computations (reachability, recursive CTEs) re-run only from the frontier — impossible for trigger designs. Third, the engine can be *self-correcting*: Materialize's write-up on "self-correcting materialized views" describes how engine upgrades or definition changes produce "output drift" repaired in-place by re-deriving the affected spans of the view — maintenance for the maintenance code.

**Flink.** Flink's Table API/SQL runs queries over **dynamic tables**; the docs state that "a continuous query on a dynamic table is very similar to a query that defines a materialized view," and guarantee that the continuous output is semantically equivalent to running the same query in batch on a snapshot. Flink operationalizes the freshness contract explicitly in **Materialized Table**s: declare a *data freshness target* and the engine launches either a streaming job (`CONTINUOUS` mode: "incrementally updates the materialized table data") or a scheduled batch job (`FULL` mode: periodic overwrite) — with the documented caveat that "freshness is not a guarantee... a target that Flink attempts to meet." That target-vs-guarantee distinction is the modern, honest version of the deferred-vs-eager table above.

**dbt-style incremental models vs true IVM.** dbt's incremental materializations re-run a query filtered to "rows created since the last run" (`is_incremental()`), then append or merge rows by a configured `unique_key`. The comparison shows what "true" IVM buys:

| Dimension | dbt incremental model | True IVM (engine/streaming) |
|---|---|---|
| Trigger | scheduled batch job | each change, continuously |
| Delta source | timestamp/column filter on the base table | the change feed itself (exact deltas) |
| Deletes/updates of old rows | easy to miss (late updates, hard deletes) | exact by construction |
| Cost per change | O(batch window recompute) | O(affected rows) |
| Infra | orchestrator + warehouse | engine maintaining state |

A timestamp filter is an *approximation* of a delta: a row updated twice in one window, or updated after it was read, produces wrong results unless the model is written defensively (lookback windows, merge on key, full-refresh policies). CDC pipelines (see [CDC and the Transactional Outbox](../../backend/patterns/cdc-outbox.md)) close the gap by feeding exact deltas — at which point you have rebuilt true IVM out of a scheduler and a queue: **dbt incremental + CDC ≈ a materialized view with a batch-period refresh SLA.**

**Warehouse MVs: BigQuery and Snowflake.** BigQuery materialized views refresh automatically — the engine "reads only the changes since the last time the view was refreshed," stores `AVG`/`ARRAY_AGG`/`APPROX_COUNT_DISTINCT` as intermediate sketches, and rewrites queries to use them transparently (the query plan shows which MV was scanned; dry runs exercise the rewrite). Snowflake's MVs are maintained by a background service and also auto-rewritten, but with a deliberately small surface: **a materialized view can query only a single table; joins (including self-joins) are not supported**, and window functions, `HAVING`, `ORDER BY`, grouping sets, and most non-decomposable aggregates are banned. The restrictions are the cost model made visible: the narrower the definition, the cheaper and more predictable the maintenance, and the safer the rewrite. Snowflake's docs also specify the read-side behavior: if a query runs before the MV is up to date, the engine "either updates the materialized view or uses the up-to-date portions of the materialized view and retrieves any required newer data from the base table" — *hybrid maintenance with a stale-read window on the background path*.

## The cache-invalidation reading

Strip the SQL and a materialized view is a cache whose invalidation key the database can compute *exactly*: when a base row changes, the affected view rows are the propagation of that row's key through the view plan — the "affected range" Blakeley et al. characterized in 1986. MVs never face the hardest application-cache problem (see [Advanced Caching Strategies](../caching/advanced-caching.md)): there is no ambient state to guess at; the delta *is* the invalidation message. Real systems then differ only in granularity: key/range propagation (trigger and MV-log designs), **dirty-region tracking** (mark the affected key range dirty, repair lazily — Snowflake's "up-to-date portions," Materialize's span repairs), and full recompute (PostgreSQL's non-concurrent refresh). Asynchronous maintenance buys stale-read windows, but the database can *quantify* the window (a timestamp frontier) and can close it at query time by fetching the missing tail from base tables, as Snowflake does.

## Cost model: read amplification vs write amplification

Let `Q` be the view query, `W` the base-table write rate, and `R` the rate of queries the view serves. Four regimes:

- **On-demand refresh (PG):** reads cost ~0 extra; every refresh costs a full `Q` evaluation (`|Q|`), and staleness grows linearly with writes between refreshes. Total: `R·0 + W·0 + |Q|/period`. Wrong tool when `Q` is huge and refreshes must be frequent.
- **Synchronous eager (SQL Server/Oracle ON COMMIT):** every write pays `ΔQ` (delta maintenance) plus transaction overhead; reads are exact and ~free. Wrong tool for write-heavy tables serving rare queries.
- **True IVM (Materialize/Flink):** writes pay `ΔQ` continuously (smooth, amortized), reads are current; the fixed cost is the always-running dataflow and its state. Wrong tool when the view is rarely queried or must be cheap when idle.
- **Periodic (warehouse MVs):** amortizes refresh cost into scheduled windows; staleness bounded by the period. The default for analytics, where "fresh to the last hour" is usually acceptable.

The crossover intuition: an MV converts **write amplification into read amplification relief**. If `R/W` (queries per write) is high and `Q` is much more expensive than `ΔQ`, the view wins decisively; as `W` grows toward `R`, the maintenance stream becomes its own workload — a standing tax. The consistency angle belongs in the same calculation: a deferred MV is not a *transactional* read — it is eventually-consistent materialized state, so correctness must not depend on it the way it depends on a same-transaction read (keep constraints and money on base tables). And because refresh semantics were never standardized, engines disagree on what "fresh" means: Oracle `ON COMMIT` is exact at commit, Snowflake's background service is *eventually* exact, BigQuery refreshes on its own schedule with a configurable `max_staleness`. Read the contract per engine; do not design against the SQL keyword.

## Interview problems

### Problem 1 — The dashboard that melts the primary

*A leaderboards/dashboard page aggregates `events` (2B rows) into per-hour rankings; the raw aggregation takes 90s, the page must render in 200ms, and events arrive at 50k writes/s. Compare: PostgreSQL materialized view, trigger-maintained summary table, streaming IVM, application cache.*

**Worked solution.** The 90s aggregation is `|Q|` — far too big to refresh per-transaction, so synchronous eager and PostgreSQL `REFRESH` are both out (a 90s exclusive refresh every minute also blocks readers without `CONCURRENTLY`). The query's real structure is **decomposable**: per-hour counts are `SUM`/`COUNT` aggregates over append-only events, so a trigger-maintained summary table (`(hour, entity, count)` upsert) gives exact reads at 200ms for ~one indexed upsert per event — key-bounded (each event touches exactly its hour/entity keys), a real but modest tax at 50k writes/s. PostgreSQL's built-in MV only earns its keep if the aggregation is *not* decomposable (e.g., windowed ranks over re-scoring); even then, refresh `CONCURRENTLY` with a unique index on `(hour, entity)` and accept a stale window. Streaming IVM (Materialize/Flink) wins when the ranking recomputes from a sliding window, deletes/corrections must reflect instantly, or many dashboards share one consistent view — the cost is a continuously-running engine. A pure application cache (Redis sorted set) is the wrong layer: it moves the IVM problem into application code without the transactional delta source and must be rebuilt on eviction. Decision rule: **cache when reads dominate and staleness is acceptable; summarize (IVM) when writes are decomposable; stream when the window itself moves.**

### Problem 2 — Implement IVM for a `SUM` view in SQL

*Base table `orders(id, region, amount)`; maintain `order_totals(region, total, n)` exactly, with triggers. Then derive `AVG` and explain why `MAX` needs more.*

**Worked solution** (logic verified on SQLite; the PostgreSQL version uses the same three triggers with `ON CONFLICT` upserts):

```sql
CREATE TABLE orders (id INT PRIMARY KEY, region TEXT, amount NUMERIC);
CREATE TABLE order_totals (
  region TEXT PRIMARY KEY,
  total  NUMERIC NOT NULL,
  n      BIGINT  NOT NULL
);

-- INSERT: create the group row or add to it (a new region may have no row yet)
CREATE TRIGGER orders_ins AFTER INSERT ON orders
FOR EACH ROW
  INSERT INTO order_totals(region, total, n) VALUES (NEW.region, NEW.amount, 1)
  ON CONFLICT (region) DO UPDATE SET total = order_totals.total + NEW.amount,
                                     n     = order_totals.n + 1;

-- DELETE: subtract (count may reach 0; keep the row or delete it — pick one policy)
CREATE TRIGGER orders_del AFTER DELETE ON orders
FOR EACH ROW
  UPDATE order_totals SET total = total - OLD.amount, n = n - 1
  WHERE region = OLD.region;

-- UPDATE: delete-old + insert-new (handles region changes AND amount changes)
CREATE TRIGGER orders_upd AFTER UPDATE OF region, amount ON orders
FOR EACH ROW EXECUTE FUNCTION apply_update();
-- body: subtract (OLD.region, OLD.amount), then upsert (NEW.region, NEW.amount)
```

`AVG` is then `total/n` — never store it. Two subtleties. (1) The triggers are **row-at-a-time**, which as shown above automatically covers self-interactions inside a multi-row statement; a bulk-delta design must reason about `(ΔR ⋈ ΔR)`-style terms. (2) The maintenance is in the same transaction as the write, so the summary is exact — but each trigger is a write amplifier on the hot path; at high rates, buffer deltas into an append-only change table and apply them in a batch job (deferred IVM), converting exactness into a monitorable staleness window. `MAX` per region cannot be maintained this way: `DELETE` of the current maximum row leaves the trigger knowing only what left, not what remains — you need a per-region ordered auxiliary structure (index on `(region, amount DESC)` and re-peek, or a top-k table): the "aggregates must be invertible or completable" rule again.

### Problem 3 — "Your MV refresh takes 40 minutes and blocks the app"

**Worked solution.** Diagnose in order. (1) *Blocking*: a PostgreSQL non-concurrent `REFRESH` holds an exclusive lock for its whole duration — switch to `CONCURRENTLY` (add the required unique index; note the one-refresh-at-a-time limitation) and schedule off-peak; if the refresh cannot fit any window, split the view by time partition and refresh only recent partitions (key-bounded maintenance by construction). (2) *Cost*: 40 minutes of recompute means `|Q| >> |ΔQ|` — check whether the aggregation is decomposable; if so, replace the full refresh with an IVM summary table (Problem 2) or an incremental-refresh product (BigQuery/Snowflake/Oracle FAST with MV logs). (3) *Architecture*: if batch-period freshness is acceptable, move the view to the warehouse layer (dbt incremental + CDC; see the outbox pattern) and let the OLTP database stop serving analytics. (4) *Contract*: write down the staleness SLA and monitor refresh lag — the outage described here is a staleness-SLO violation that silently became an availability violation.

## Common mistakes

- Treating a materialized view as transactional state: it is a cache with a maintenance schedule; never hang FK-style correctness off a deferred MV.
- Forgetting the unique index for `REFRESH ... CONCURRENTLY` in PostgreSQL (it fails at refresh time, not creation time), or shipping `WITH NO DATA` views without a first refresh.
- Maintaining `AVG` directly instead of `(SUM, COUNT)`; maintaining `MIN`/`MAX` on delete without an auxiliary ordered structure.
- Ignoring multiplicities: "delete one row" removes *as many* view derivations as the row participated in, not one.
- Shipping dbt-style timestamp filters that miss late updates or hard deletes, and calling it incremental maintenance.
- Assuming one engine's MV semantics transfer: refresh timing, rewrite behavior, and supported query shapes differ per vendor (single-table limit in Snowflake, edition-gated rewrite in SQL Server, BigQuery refresh costs).

## Cross-references

- [SQL Views](../sql/views.md) — virtual views and the basic materialized-view syntax this page builds on.
- [The RUM Conjecture](./rum-conjecture.md) — the read/update/space overhead frame; an MV is an explicit R-for-U/M trade at the schema level.
- [Advanced Caching Strategies](../caching/advanced-caching.md) — the application-cache counterpart; MVs are cache invalidation where the key set is computable.
- [CDC and the Transactional Outbox](../../backend/patterns/cdc-outbox.md) — the exact-delta source that turns post-hoc incremental models into true IVM.
- [Analytics Deep Dive](../../data-engineering/analytics.md) — warehouse context: OLAP cubes, dimensional modeling, query rewrite.
- [Stream Processing](../../data-engineering/stream-processing.md) and [Apache Flink](../../data-engineering/flink.md) — the streaming substrate behind continuous queries.
- [Temporal Streaming](./temporal-streaming.md) — watermarks and event time; freshness is measured on the event-time frontier.

## References

1. A. Gupta, I. S. Mumick, V. S. Subrahmanian. *Maintaining Views Incrementally.* SIGMOD 1993. DOI: [10.1145/170035.170066](https://doi.org/10.1145/170035.170066) — the counting algorithm and delta propagation for SPJ views.
2. J. A. Blakeley, P.-Å. Larson, F. W. Tompa. *Efficiently Updating Materialized Views.* SIGMOD 1986. DOI: [10.1145/16894.16861](https://doi.org/10.1145/16894.16861) — the "relevant updates" characterization underlying key-bounded maintenance.
3. T. Griffin, L. Libkin. *Incremental Maintenance of Views with Duplicates.* SIGMOD 1995. DOI: [10.1145/223784.223849](https://doi.org/10.1145/223784.223849) — duplicate semantics and multiplicity bookkeeping.
4. F. McSherry, D. G. Murray, R. Isaacs, M. Isard. *Differential Dataflow.* CIDR 2013. Paper PDF maintained in the implementation repo: [github.com/TimelyDataflow/differential-dataflow](https://github.com/TimelyDataflow/differential-dataflow) (title/authorship cross-checked against the official CIDR 2013 schedule, [cidrdb.org/cidr2013/CIDR2013Sched.pdf](https://www.cidrdb.org/cidr2013/CIDR2013Sched.pdf)).
5. D. G. Murray, F. McSherry, R. Isaacs, M. Isard, P. Barham, M. Abadi. *Naiad: A Timely Dataflow System.* SOSP 2013. DOI: [10.1145/2517349.2522738](https://doi.org/10.1145/2517349.2522738).
6. M. Ahmad, O. Kennedy, C. Koch, M. Nikolic. *DBToaster: Higher-order Delta Processing for Dynamic, Often Fresh, Massively Scalable Analytics.* PVLDB 5(4), 2012. DOI: [10.14778/2336664.2336670](https://doi.org/10.14778/2336664.2336670) — compile-time IVM (nested delta queries).
7. PostgreSQL documentation: [REFRESH MATERIALIZED VIEW](https://www.postgresql.org/docs/current/sql-refreshmaterializedview.html) (exclusive locking, `CONCURRENTLY` unique-index requirement, one-refresh-at-a-time) and [CREATE MATERIALIZED VIEW](https://www.postgresql.org/docs/current/sql-creatematerializedview.html) (stored result + remembered query; `WITH NO DATA`).
8. Microsoft Learn: [Create Indexed Views](https://learn.microsoft.com/en-us/sql/relational-databases/views/create-indexed-views) — `SCHEMABINDING`, determinism, `COUNT_BIG(*)` with `GROUP BY`, no `HAVING`, edition-gated automatic use and `NOEXPAND`.
9. Oracle Database 19c SQL Reference: [CREATE MATERIALIZED VIEW](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/CREATE-MATERIALIZED-VIEW.html) — `FAST`/`COMPLETE`/`FORCE`, `ON COMMIT`/`ON DEMAND`, materialized view logs, `DBMS_REFRESH`, query rewrite.
10. MySQL 8.0 Reference Manual, "[Views](https://dev.mysql.com/doc/refman/8.0/en/views.html)" chapter (dev.mysql.com returns 403 to scripted probes; page verified via search) — documents views as virtual tables only; no materialized views, hence the summary-table pattern.
11. Materialize documentation: [Views & indexes](https://materialize.com/docs/concepts/views/) ("Results are persisted in durable storage and incrementally updated") and [CREATE MATERIALIZED VIEW](https://materialize.com/docs/sql/create-materialized-view/); J. Teske, *Self-Correcting Materialized Views* ([materialize.com/blog/self-correcting-materialized-views](https://materialize.com/blog/self-correcting-materialized-views/)) — output drift and in-place re-derivation.
12. Apache Flink documentation (release 2.1): [Dynamic Tables & Continuous Queries](https://nightlies.apache.org/flink/flink-docs-release-2.1/docs/dev/table/concepts/dynamic_tables/) and [Materialized Table overview](https://nightlies.apache.org/flink/flink-docs-release-2.1/docs/dev/table/materialized-table/overview/) (`CONTINUOUS` vs `FULL` refresh; freshness as a target).
13. Google Cloud: [Materialized views introduction](https://cloud.google.com/bigquery/docs/materialized-views-intro) — automatic/incremental refresh, sketch-based `AVG`, transparent rewrite, costs.
14. Snowflake documentation: [Working with Materialized Views](https://docs.snowflake.com/en/user-guide/views-materialized) — background maintenance, automatic rewrite, single-table/no-join limitations, supported aggregates.
15. dbt Labs: [Incremental models](https://docs.getdbt.com/docs/build/incremental-models) — `is_incremental()`, row filtering, `unique_key` strategies.
16. T. Akidau. *Streaming 101: The world beyond batch.* O'Reilly, 2015: [oreilly.com/ideas/the-world-beyond-batch-streaming-101](https://www.oreilly.com/ideas/the-world-beyond-batch-streaming-101) — bounded vs unbounded data; the vocabulary for freshness targets.
