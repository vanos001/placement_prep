# Automatic Indexing: What-If Analysis, Recommendation Engines, and Self-Tuning Index Selection

Indexes are the highest-leverage, most frequently wrong performance decision in a database. They are chosen for a *workload*, and workloads drift: the query mix that justified an index in March is not the mix in September, and no `CREATE INDEX` statement expires. This chapter treats index selection as what it actually is — a continuous optimization problem — and works through the three layers every serious answer needs: **what-if analysis** (simulate an index without paying for it), **recommendation engines** (generate and rank candidates from a workload), and **closed-loop automation** (create, verify, and roll back automatically). Every external claim below was verified against fetched documentation this session, and every SQL output was produced by running the query.

## Why Index Selection Never Sits Still

Three forces make manual index selection a treadmill. First, **combinatorics**: an index is an ordered subset of columns (plus optionality like INCLUDE columns and partial predicates); with 20 plausible columns the candidate space is astronomical, and multi-index interactions (one index making another redundant, two single-column indexes combining for a merge join... or not) mean you cannot reason about indexes one at a time. Second, **cost asymmetry**: a missing index costs one query's latency; a wrong index costs every insert, update, and delete on the table, forever, plus the storage. Third, **workload rot**: deployments add queries faster than reviews retire indexes, and skewed data distributions drift seasonally.

The industry's answer has matured through three generations, articulated in the research that still underpins every product today. Chaudhuri and Narasayya's AutoAdmin work at Microsoft introduced the what-if abstraction [1], later survey work framed self-tuning as a closed loop [3], and production systems now run that loop continuously — with Azure SQL Database documenting an end-to-end create-verify-revert cycle [4].

## What-If Analysis: The Core Abstraction

The key insight of the AutoAdmin "what-if" utility [1]: to evaluate a candidate index you do not need to *build* it — you need the optimizer to *cost* it. Build the candidate's metadata (key columns, statistics estimated from the underlying data), inject it into the optimizer's enumeration, and ask for the plan cost of each workload query with and without it. The estimated cost delta, summed over the workload, is the candidate's benefit. This turns an unbearably expensive search (build each candidate, run the workload, measure) into a purely planning-time exercise.

HypoPG brings exactly this to PostgreSQL as an extension [2]. Its documentation defines the mechanism plainly: "A hypothetical, or virtual, index is an index that does not really exist, and therefore does not cost CPU, disk or any resource to create. They are useful to find out whether specific indexes can increase the performance for problematic queries, since you can discover if PostgreSQL will use these indexes or not without having to spend resources to create them." [2] Two implementation subtleties from the same documentation are interview gold:

- Hypothetical indexes are usable only in estimation, not execution: "since the hypothetical indexes doesn't really exists, HypoPG makes sure they will only be used using a simple EXPLAIN statement (without the ANALYZE option)." [2] `EXPLAIN ANALYZE` would actually run the query — and the index isn't there.
- HypoPG can also **hide** a real index (`hypopg_hide_index(oid)`), letting you ask the inverse question: *what happens to the plan if this index disappears?* — the essential tool for safe index retirement [2].

The documentation's own worked example shows the shape of the result. On a 100,000-row table with no index, `EXPLAIN SELECT val FROM hypo WHERE id = 1` costs `0.00..1791.00` (sequential scan). After `SELECT * FROM hypopg_create_index('CREATE INDEX ON hypo (id)')`, the same EXPLAIN reports `Index Scan using <18284>btree_hypo_id on hypo (cost=0.04..8.06)` — the optimizer *would* use such an index. The verification step closes the loop: `EXPLAIN ANALYZE` still shows a sequential scan with "Rows Removed by Filter: 99999", proving the hypothetical index influenced planning only [2].

What-if analysis has a structural limitation that interviewers probe: the benefit estimate is only as good as the optimizer's **cost model and statistics**. If the model mis-prices an index (as it can under heavy skew), the what-if analysis confidently recommends something that doesn't help. That is why production auto-indexing (below) treats "the optimizer says it helps" as a hypothesis to verify, not a decision.

## Candidate Generation and Workload Compression

What-if analysis answers "is this index good?"; recommendation engines must answer "which indexes should I even consider?" for a workload of thousands of distinct queries. The classical pipeline from the AutoAdmin lineage [1] has three stages:

1. **Syntactic candidate generation.** For each query, extract the access paths the optimizer already wanted: equality predicates (leading columns), range predicates (trailing columns), ORDER BY / GROUP BY columns, and columns projected for index-only scans. This bounds the space to plausible candidates.
2. **Workload compression.** Thousands of queries collapse into a few hundred *query classes* with similar access requirements; pick representatives and weight them by frequency and cost share. Evaluating 200 candidates against 300 classes is tractable; against 50,000 raw queries it is not.
3. **Candidate consolidation.** Closely-related candidates get merged — Chaudhuri and Narasayya's "index merging" work (ICDE 1999) [5] formalizes combining two candidate indexes into one that serves both access paths, trading a little of each one's efficiency for one less index of write overhead.

The final selection is an optimization problem, and it is worth stating it precisely (it makes a superb senior-interview framing): choose the subset S of candidates maximizing total workload benefit Σ benefit(i) subject to a budget Σ cost(i) ≤ B, where cost is storage **plus a write-overhead term** that scales with the table's update rate. This is 0/1 knapsack — NP-hard in general, but instance sizes are small (tens of candidates), so exact dynamic programming or good approximations work; a worked example with real numbers appears in the section "Index Selection as Knapsack" below. The framing matters because it makes the write budget *first-class*: an index that costs more in update overhead than it saves in reads is a net loss no matter how good its lookup looks.

## Production Auto-Indexing: Azure SQL's Closed Loop

Azure SQL Database documents a full closed-loop system, and its published behavior [4] is the cleanest available specification of what "automatic indexing" must include. Three tunables cover the lifecycle (`ALTER DATABASE CURRENT SET AUTOMATIC_TUNING (CREATE_INDEX = ON, DROP_INDEX = ON);`):

- **CREATE INDEX** — the documentation states it "identifies indexes that might improve performance of your workload, creates indexes, and automatically verifies that performance of queries has improved." Note the resource guards baked into the same paragraph: the system considers available space and won't recommend an index if it would push space utilization past 90% of the database maximum, and it won't even consider tables whose clustered index or heap exceeds 10 GB. Creation happens in "a period of low utilization" and is retried there if it fails [4].
- **DROP INDEX** — "Drops unused (over the last 90 days) and duplicate indexes. Unique indexes, including indexes supporting primary key and unique constraints, are never dropped." The option also self-disables for workloads using index hints or partition switching [4].
- **FORCE_LAST_GOOD_PLAN** — automatic plan correction: "identifies Azure SQL queries using an execution plan that is slower than the previous good plan, and forces queries to use the last known good plan instead of the regressed plan" [4]. This is the safety net for the *plan regression* risk that new indexes create (a new index can flip an existing query to a plan that is better on estimated cost but worse in reality).

The verification discipline is the part to internalize. Per the documentation, autonomous application validates that "there exists a positive gain to workload performance, and if there's no significant performance improvement detected or if performance regresses, the system automatically reverts the changes that were made," with validation taking "from 30 minutes to 72 hours, taking longer for less frequently executing queries" [4]. Read that range again: *72 hours*. Verification latency is bounded by how long you must wait to observe enough executions of every affected query — a volume-driven property no engineering can shortcut. Also note the documented caveat that recommendations applied manually via T-SQL do **not** get the validation-and-revert machinery [4] — the loop is the value, not the creation.

## Why the Missing-Index DMV's Advice Can Be Wrong

SQL Server exposes a cheaper signal: the missing-index DMVs. `sys.dm_db_missing_index_details` "returns detailed information about missing indexes," with `equality_columns` listing "columns that contribute to equality predicates of the form: table.column = constant_value" and `inequality_columns` for predicates like `table.column > constant_value` [6]. It is a *compiler-internal gripe log*: every time the optimizer compiles a query and wishes for an index, it records one row.

That origin explains every failure mode, and this list is a complete interview answer to "why shouldn't you just apply everything the DMV suggests?":

- **No cost model.** The DMV records a *want*, never a *worth*. It knows nothing about frequency-weighted benefit, so a query run once per day contributes the same suggestion as one run 10,000 times per minute. (Group/usage-stats DMVs add counts, but still no cost model.)
- **No column-order intelligence.** `equality_columns` is a comma-separated set; a suggested index on `(b, a)` and one on `(a, b)` look equivalent to the DMV while behaving very differently for ranges. The documentation's own shape (equality first, then inequality, then INCLUDE) is a heuristic, not an optimization.
- **Volatile and bounded.** The data "is updated when a query is optimized by the query optimizer, and is not persisted" — it is lost at engine restart — and "the result set for this DMV is limited to 600 rows" [6]. A recommendation pipeline built on it must persist snapshots and aggregate them itself.
- **Write cost is invisible.** The DMV never says what the index will cost every writer on the table.
- **Overlapping suggestions.** Multiple compiled queries produce near-duplicate suggestions that differ in one column; applying all of them builds redundant indexes.

The DMV is therefore a *candidate generator* — exactly stage 1 of the pipeline above — and the fence between generating candidates and applying them is where self-discipline lives.

## The Safety Engineering: Write Budget, Staging, Rollback

Automatic indexing is less about choosing indexes than about making index changes safe. Four mechanisms recur:

**Write-overhead budgeting.** Every index multiplies write work. Our own measurement on this chapter's fixture (below): 50,000 inserts took 32 ms without a secondary index and 54 ms with one — 1.69× — on an in-memory SQLite table where index maintenance is pathologically cheap relative to production. At production write rates the multiplier is a capacity line item, which is why the Azure CREATE INDEX advisor carries its own storage guards [4] and why the knapsack formulation includes a write term rather than treating storage as the only cost.

**Staged visibility.** The dangerous moment of an index is its activation, so systems stage it: PostgreSQL's `CREATE INDEX CONCURRENTLY` can leave an `INVALID` index that is being maintained but not yet chosen (see [online schema change](online-schema-change.md)); conceptually invisible/hypothetical states (HypoPG [2]) go further and keep the index out of *everything* except what-if planning. The pattern generalizes: decouple *maintained* (keep it up to date) from *selectable* (the optimizer may use it) so each can be enabled independently.

**Plan-regression containment.** A new index changes plan choices for queries you never intended to touch. The countermeasure is the last-known-good-plan mechanism [4]: detect per-query regression after the change, force the previous plan, and treat the index as still-under-trial until the forced plans are understood.

**Automatic rollback.** Because verification compares before/after workload behavior, the same comparison can trigger reversal: "if performance regresses, the system automatically reverts the changes that were made" [4]. A team that cannot state its rollback trigger ("if p99 of the protected queries degrades by X% for Y minutes") does not have an automation story — it has a faster way to accumulate risk.

## A Verification Loop You Can Run

The following experiment ran on SQLite (Python 3.12, in-session) and reproduces every claim above. Fixture: 500,000 orders over 50,000 customers; the hot query is `SELECT * FROM orders WHERE cust_id = 1234 AND status = 'pending'`.

```sql
EXPLAIN QUERY PLAN SELECT * FROM orders
WHERE cust_id = 1234 AND status = 'pending';
-- (2, 0, 216, 'SCAN orders')                      -- full scan
-- median of 5 runs: 20.98 ms

CREATE INDEX idx_orders_cust_status ON orders(cust_id, status);

EXPLAIN QUERY PLAN SELECT * FROM orders
WHERE cust_id = 1234 AND status = 'pending';
-- (3, 0, 62, 'SEARCH orders USING INDEX idx_orders_cust_status (cust_id=? AND status=?)')
-- median of 5 runs: 0.01 ms
```

The 2,000× improvement is selectivity doing the work (`cust_id` picks ~10 rows). The write-cost half of the ledger, measured the same session: 50,000 inserts into an equivalent table cost 32 ms with no secondary index and 54 ms with one — the 1.69× multiplier quoted above.

The `ANALYZE` step demonstrates what statistics change — and what they don't. Adding an index on the low-selectivity column `status` (values split ≈ 500,000 / 166,667 per value per `sqlite_stat1` after `ANALYZE`), a `COUNT(*)` still plans as a covering-index scan even after statistics exist:

```sql
CREATE INDEX idx_orders_status ON orders(status);
ANALYZE;
SELECT tbl, idx, stat FROM sqlite_stat1 WHERE idx LIKE '%status%';
-- ('orders', 'idx_orders_status', '500000 166667')

EXPLAIN QUERY PLAN SELECT COUNT(*) FROM orders WHERE status = 'pending';
-- (3, 0, 187, 'SEARCH orders USING COVERING INDEX idx_orders_status (status=?)')
```

That is not a planner mistake — it is the lesson: at 33% selectivity a *covering* index scan still reads less than the wide table, so the cost model (with real statistics) keeps the index. "Low selectivity ⇒ full scan" is a heuristic; the planner runs costs, and auto-indexing tools that hard-code heuristics in place of the cost model will disagree with it.

## Index Selection as Knapsack

State the problem with four candidates and a 50 GB storage budget (benefit = estimated workload time saved; write overhead folded into the benefit numbers for clarity):

| Candidate | Benefit (ms saved) | Cost (GB) |
|---|---|---|
| I1 | 120 | 20 |
| I2 | 80 | 10 |
| I3 | 90 | 25 |
| I4 | 30 | 5 |

Enumerated exactly (python3, this session): the optimum is **I1 + I3 + I4 = 240 ms at 50.0 GB**. The intuitive greedy — take candidates by benefit-per-GB density (I2 at 8.0, then I4 at 6.0, then I1 at 6.0, then I3 at 3.6) — selects I2 + I1 + I4 = 230 ms and stops with 15 GB of budget stranded because I3 no longer fits. Greedy by density is not wrong by much here, but the gap is structural: knapsack optima often require *skipping* an attractive early pick to afford a combination later. With tens of candidates, exact DP is cheap; with hundreds, branch-and-bound. Either way, "sort by benefit density" alone is a junior answer once the budget binds.

## Interview Problems

**P1 (mid) — "You have a time-range + key query: `WHERE tenant_id = ? AND created_at > ?` under a heavy insert workload. Choose and defend the index."**
Expected: composite `(tenant_id, created_at)` — leading equality, trailing range (a range column can't be leading unless everything before it is fixed). Defend the write cost against the insert workload: one secondary index over two columns, narrow keys, and note that a partial index (`WHERE created_at > now() - interval '30 days'`-style) can shrink it further in engines that support partial indexes. Rubric: junior names *an* index; mid gets the column order; senior raises partial indexes, the write budget, and how to verify benefit with a what-if run before building.

**P2 (senior) — "The missing-index DMV recommends 400 indexes. Walk me through your process."**
Expected: snapshot first — the DMV "is not persisted... kept only until the database engine is restarted" and is "limited to 600 rows" [6], so capture and aggregate externally. Then pipeline: cluster suggestions into classes (same table, overlapping column sets — merge aggressively [5]); weight by frequency/cost share (never raw suggestion counts); estimate benefit with what-if machinery or a test environment; apply the knapsack under a storage *and* write budget; stage the survivors (CONCURRENTLY/invisible), watch for plan regressions with last-good-plan protection, and set explicit rollback triggers. Rubric: junior applies them; mid deduplicates and weighs; senior runs the full loop including the write budget and rollback triggers.

**P3 (senior) — "Automatic indexing created an index and a day later, unrelated reports are slower. What happened and what should the system have done?"**
Expected: **plan regression** — the new index changed plan selection for existing queries (estimated-cost improvement, real-world regression). The correct machinery: automatic plan correction (force last known good plan per affected query [4]), then either revert the index or accept with the forced plans, and — structurally — why verification must cover the *whole workload's protected queries*, not just the query the index was built for (the Azure 30-min-to-72-hour validation window [4] exists precisely because low-frequency queries take that long to re-observe). Rubric: junior says "drop the index"; mid names regression; senior names detection → force → revert-with-trigger and the workload-wide verification requirement.

## Key Takeaways

- Index selection is workload subset selection under a budget; treat candidates as hypotheses, never as advice.
- What-if analysis (hypothetical indexes) is the core abstraction: optimizer-cost candidates without building them — "does not cost CPU, disk or any resource" [2] — and `EXPLAIN` (without `ANALYZE`) is its only honest instrument.
- A recommendation engine is three stages: syntactic candidate generation → workload compression → consolidation [1][5]; the missing-index DMV is stage 1 only — no cost model, not persisted, 600-row cap [6].
- Closed-loop automation = create guarded → verify against the whole workload (takes 30 min to 72 h by query frequency [4]) → revert on regression; the loop is the product, not the creation.
- Every index is a write-rate multiplier (1.69× on 50k inserts in our in-memory fixture — worse in production), so the write budget belongs *inside* the objective, and selection is knapsack: exact optimum beat benefit-density greedy by skipping an early pick.
- State your rollback trigger out loud; automation without a stated revert condition is just faster risk accumulation.

## References

1. Chaudhuri, S.; Narasayya, V. "AutoAdmin 'what-if' index analysis utility." *Proc. 1998 ACM SIGMOD*, pp. 367–378. DOI: [10.1145/276304.276337](https://doi.org/10.1145/276304.276337) — Crossref-verified (title/authors/venue) this session.
2. HypoPG documentation — "Hypothetical Indexes" and "Usage" pages — <https://hypopg.readthedocs.io/en/latest/hypothetical_indexes.html> and <https://hypopg.readthedocs.io/en/latest/usage.html> — fetched in full this session; all quoted sentences verbatim, worked-example plan outputs quoted from the documentation.
3. Chaudhuri, S. "Self-tuning Database Systems: Past, Present and Future." *LNCS 5232* (BNCOD 2008 keynote chapter). DOI: [10.1007/978-3-540-78568-2_2](https://doi.org/10.1007/978-3-540-78568-2_2) — Crossref-verified this session.
4. Microsoft Learn, "Automatic tuning in Azure SQL Database" — <https://learn.microsoft.com/en-us/azure/azure-sql/database/automatic-tuning-overview> — fetched in full this session; CREATE INDEX / DROP INDEX / FORCE_LAST_GOOD_PLAN behavior, validation window, and T-SQL quoted verbatim.
5. Chaudhuri, S.; Narasayya, V. "Index merging." *Proc. 15th ICDE*, 1999. DOI: [10.1109/ICDE.1999.754945](https://doi.org/10.1109/ICDE.1999.754945) — Crossref-verified this session.
6. Microsoft Learn, "sys.dm_db_missing_index_details (Transact-SQL)" — <https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-db-missing-index-details-transact-sql> — fetched in full this session; column semantics, non-persistence, and 600-row cap quoted verbatim.

*Note:* vendor systems for which this session could not fetch official documentation (e.g., Oracle Automatic Indexing) are deliberately not quoted or cited here rather than cited from memory; the two documented systems above carry the chapter's claims.

## Cross-References

- [Indexing Strategy](../indexing-strategy.md) — choosing column orders and index types by hand, the foundation this chapter automates
- [Query Optimization Deep Dive](../query-optimization-deep.md) — the cost model and cardinality estimation that what-if analysis depends on
- [Online Schema Change](online-schema-change.md) — building indexes without blocking writes; the INVALID/CONCURRENTLY states behind staged visibility
- [Cursors and Streaming Results](cursors-and-streaming-results.md) — the read-path counterpart: exporting and paging once the right index exists
- [MVCC Internals](mvcc-internals.md) — why long-lived cursors and uncollected versions interact with index maintenance
