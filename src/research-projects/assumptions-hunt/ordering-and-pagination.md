# Ordering and Pagination Assumptions: What `ORDER BY ... LIMIT` Silently Promises

## Overview

Pagination looks like the safest query shape in existence: sort some rows, take twenty, hand back a "next page" link. Each step hides an assumption that fails in production with rows appearing twice, rows never appearing, pages slowing as the user scrolls, and IDs trusted to remember when something happened. This chapter audits five: that `ORDER BY` alone makes output order deterministic, that `LIMIT/OFFSET` pagination is safe under concurrent writes, that auto-increment IDs order by insertion time, that a deep `OFFSET` is merely a bigger scan, and that "stable sort" means the same thing everywhere — including inside the database, where the SQL standard promises nothing about ties.

The failures share one root: an ordering must be a *total order*, and most keys people pick — timestamps, status codes, surnames — are not. When the key does not distinguish rows, some other agent (planner, sort implementation, parallelism degree) picks an order, changes it between runs, and cuts page boundaries through tie groups in ways no single-threaded laptop test reproduces. The corrected toolkit is small — a unique tie-breaker as the last sort key, keyset ("seek") pagination instead of offsets, explicit NULL ordering, and identifiers that identify rows rather than moments — developed below with arithmetic and concrete scenarios, in the collection's five-step pattern.

## Assumption 1: "ORDER BY Makes the Output Order Deterministic"

### The taught rule

Add `ORDER BY` to a query and the rows come back in a well-defined, repeatable order.

### The hidden assumptions

- `ORDER BY` defines a *total order only if its key is unique across rows*. A sort on `status`, `created_at`, or `last_name` is a partial order: rows with equal keys are mutually unordered, and the engine may emit them in any sequence.
- The engine's choice for tied rows is not fixed even for one query: it can differ between execution plans (index scan versus sort node), between memory and external-merge paths, between parallel degrees, and between versions.
- "Stable sort" does not rescue this at the database level: the SQL standard does not require `ORDER BY` to be stable, no major engine promises it, and stability of the underlying routine evaporates exactly when a sort spills to disk or runs in parallel workers.

### Counterexample

An activity feed sorts by `created_at`, filled by a nightly bulk import, so thousands of rows share identical timestamps, and the backend paginates with `LIMIT 20 OFFSET n`. During development the sort fits in memory and returns ties by physical row order; in production the table outgrew `work_mem`, the sort spills to disk, and ties come out in merge-dependent order. Every page boundary inside a tie group slices it differently per request: item A appears on page 3 and again on page 4, item B on no page at all. Users report "duplicates in my feed"; nothing logs an error, because every query succeeded. The fix is one column: `ORDER BY created_at DESC, id DESC` — the unique primary key as final key turns the partial order into a total order, and page boundaries become reproducible.

### What changes when the assumption is removed

Corrected statement: *`ORDER BY` yields a deterministic, repeatable order if and only if the full key list is unique per row — in practice, a unique column (typically the primary key) appended as the last sort key.* This is not style; it is the precondition for every mechanism built on the query's order. The [composite index](../../dbms/indexing/composite-index.md) whose columns match the sort makes the tie-breaker free: `(created_at DESC, id DESC)` serves the query without a sort node at all.

### Consequences

"Is this query's output order guaranteed?" is a precise seniority probe: the expected answer separates key cardinality from the guarantee, names the missing tie-breaker, and volunteers that the standard promises nothing about ties. In code review, a non-unique final sort key is a defect in any query that is paginated, diffed, or resumed.

## Assumption 2: "LIMIT/OFFSET Pagination Is Safe"

### The taught rule

Client asks for page *n*; the backend runs `LIMIT 20 OFFSET (n-1)*20` — the simplest pagination there is and the default in most frameworks.

### The hidden assumptions

- Positional pagination assumes the ordered sequence is *frozen between requests*: the offset is a position in an order, not a reference to a row, so any insert or delete upstream shifts every later position while a user reads.
- It inherits Assumption 1: with a non-unique sort key, positions are not even well-defined between two executions of the same query.
- The contract question — what should happen when the data moves — has no default answer: rows get skipped (an insert lands before the offset) or shown twice (a delete upstream pulls rows back), and the client cannot detect either.
- Deep offsets are not just "a bigger scan": the engine must produce and sort every row up to the offset, then throw it away — cost grows linearly with depth while the payload stays constant.

### Counterexample

Worked numbers on both failure modes. *Drift:* a user is on page 50 (`OFFSET 980`); a batch job inserts 30 rows upstream; the next page skips 30 rows they never see, and pressing back re-serves rows 960–980 with 30 different rows. *Cost:* page 5,000 with page size 20 is `OFFSET 99,980`; the engine walks and orders 100,000 rows to return 20 — per request — and it is exactly the deepest scrollers who generate the most expensive queries. Keyset fixes both at once: `WHERE (created_at, id) < (:last_created_at, :last_id) ORDER BY created_at DESC, id DESC LIMIT 20`, which the B-tree serves directly at any depth — constant cost per page, immune to upstream inserts, with the cursor encoding a position rather than a count.

### What changes when the assumption is removed

Corrected statement: *offset pagination is safe only over an effectively frozen, totally ordered dataset — which describes small admin screens, not user-facing feeds.* Default to keyset (cursor) pagination for anything that scrolls, keep offsets for bounded, low-concurrency interfaces, and expose an opaque cursor (base64 of the key tuple) so clients cannot do arithmetic on positions. The [API contracts](api-contracts.md) chapter audits the published side: what a pagination field promises once clients depend on it.

### Consequences

"Why does page 10,000 of my API take 4 seconds while page 1 takes 40 ms?" has a one-line answer (the engine sorts offset+limit rows) and a two-line fix (keyset over a matching composite index). Generalizing: any API that lets clients address data by *position* inherits every concurrent mutation of that position's neighborhood.

## Assumption 3: "Auto-Increment IDs Order by Insertion Time"

### The taught rule

The sequence-assigned primary key increases, so id 101 was inserted after id 100 — row order tells you event order.

### The hidden assumptions

- A sequence hands out numbers at *statement* time, but visibility happens at *commit* time — different moments under concurrency. Transaction A can allocate id 100, stall, and commit after transaction B allocated and committed id 101; a reader using id order as time order reconstructs history wrongly.
- Rolled-back transactions still consume sequence values, so id gaps are normal and carry no information: id 100 may simply not exist — InnoDB's default `innodb_autoinc_lock_mode=2` and PostgreSQL sequences both produce them.
- Bulk inserts allocate in batches and multi-threaded loaders interleave arbitrarily, so allocation order across loaders does not match arrival order, and replica lag adds a second reorder after the fact.

### Counterexample

An orders table uses a bigserial primary key; a support tool displays "events for this order sorted by id" to reconstruct the timeline. During an incident, the payments worker retried a slow transaction: it allocated id 50,000 early, blocked on a lock for four seconds, and committed after the fulfillment worker's id 50,007. The tool shows fulfillment before payment for an order whose payment *created* the fulfillment — the retry's stall inverted the timeline without any clock being wrong. The corrected claim is narrower: `id` order equals *allocation* order for committed rows, nothing more. When time matters, store it explicitly (`created_at` with timezone) and still sort `created_at, id`: the id remains the tie-breaker from Assumption 1, and the temporal claim lives in a column with documented semantics.

### What changes when the assumption is removed

Corrected statement: *an auto-increment id identifies a row and approximates allocation order; it is neither a clock nor a causal order, and any consumer that derives "before/after" or "how long ago" from id differences assumes a single serializer that batches nothing, rolls back nothing, and never stalls.* Where allocation-order traces matter (debugging insert hotspots), pair the id with a recorded commit timestamp — PostgreSQL's `pg_xact_commit_timestamp` exists for exactly this.

### Consequences

"Can two observers see id 100 commit after id 101?" separates candidates who treat sequences as clocks from those who separate allocation from visibility. The same distinction returns one layer up in the [Snowflake versus UUID comparison](../why-not-handbook/snowflake-vs-uuid.md): even time-stamped IDs order by *generation*, not commit, and worker clock skew reappears there.

## Assumption 4: "A Deep OFFSET Is Just a Bigger Scan"

### The taught rule

Offsets cost extra work, but it is linear housekeeping — accept a little latency for deep pages, or cap the UI at page 100 and move on.

### The hidden assumptions

- The "bigger scan" is not a scan of the *result* but through the full sort pipeline: for any non-trivial filter, the engine evaluates the filter, orders the survivors, and discards `offset` rows — per page, per request, per user.
- The cost curve intersects capacity discontinuities: a sort that fits in memory on page 1 spills to disk by page 5,000, so latency steps off a cliff where the planner changes strategy — capacity planning at page-1 depths measures the wrong regime.
- Offset positions are consistent *within a single request only*; multi-page exports that advance the offset while data changes produce overlaps and gaps even without churn, corrupting the export.

### Counterexample

An analytics export iterates `LIMIT 1000 OFFSET k*1000` over a 40-million-row table, ordered by a non-indexed expression. Page 1 sorts 1,000 rows; page 39,999 sorts 40 million rows and discards all but 1,000 — total work is a quadratic series (roughly 800 billion row-visits) for a dataset of 40 million. The keyset rewrite visits each row once: 40 million. That quadratic-to-linear gap is the structural content of this assumption: positional addressing re-pays all prior work per page.

### What changes when the assumption is removed

Corrected statement: *offset cost is not a per-page constant but a per-page re-payment of everything before the page — quadratic in total for full exports; keyset cost is per-page constant, linear in total.* The defenses: keyset cursors as the default (Assumption 2), bounded page depth for interactive UIs, and for full exports a snapshot-and-stream design or an export path that does not traverse user-facing pagination at all.

### Consequences

"Why not just cap the UI at 100 pages?" is the trap: it fixes the symptom while exports, integrations, and scrapers keep generating the quadratic load. The senior answer names the cost model, the capacity cliff, and the alternative addressing scheme — and can derive the sum.

## Assumption 5: "Stable Sort Behaves the Same Everywhere"

### The taught rule

A stable sort preserves the input order of equal elements, so sorting twice — or in two systems — gives the same answer.

### The hidden assumptions

- Stability is a *property of an implementation*, not of sorting. Python's `sorted` is stable (Timsort); Java's `Collections.sort` is stable but primitive-array `Arrays.sort` is not (dual-pivot quicksort); C's `qsort` promises nothing; parallel and external sorts usually lose stability for speed.
- SQL engines sit entirely outside the stability contract: the standard defines the order of rows with distinct keys only, so within a tie group the engine may permute freely — across plans, versions, and replicas with different parallelism.
- NULL ordering is the sharpest edge of "same everywhere": PostgreSQL sorts NULLs as *larger* (last under ASC by default), while MySQL and SQLite sort NULLs *first* under ASC. A query migrated verbatim between engines silently moves every NULL row from one end of the result to the other.

### Counterexample

A reporting query is ported from PostgreSQL to MySQL without review: `ORDER BY priority ASC` where `priority` is nullable. Under PostgreSQL, unassigned rows (NULL priority) appear *last*; under MySQL they appear *first* — and they are exactly the rows the report's "escalate these" section is populated from, so the migrated report escalates the unassigned backlog first. No error, no warning, one line of SQL, wrong report. The fix is explicit: `ORDER BY priority ASC NULLS LAST` plus the tie-breaker id — the corrected query states its NULL and tie behavior instead of inheriting whatever the engine picked.

### What changes when the assumption is removed

Corrected statement: *a repeatable order is achieved by construction, not by convention: unique final key, explicit NULL placement, and no reliance on sort stability — in the database, in language runtimes, or in hand-written merges.* When two systems must produce identical orders (a replayer, a snapshot differ), sort on a serialized canonical key rather than trusting two implementations to agree on ties.

### Consequences

The NULLS-first/NULLS-last divergence is a compact interview question: it requires knowing the engines differ, that the default is documented per engine (PostgreSQL's [SELECT documentation](https://www.postgresql.org/docs/current/sql-select.html) states its NULLS LAST default under ASC), and that the portable query is the explicit one. The same construction-over-convention principle explains why a random identifier such as UUIDv4 wrecks [clustered index locality](https://dev.mysql.com/doc/refman/8.0/en/innodb-index-types.html) — the engine can no longer predict where the next row sorts.

## Interview Questions

1. **A feed paginated with `ORDER BY created_at LIMIT 20` shows duplicates across pages. Diagnose and fix.** `created_at` is not unique, so ties make the order non-deterministic and page boundaries cut tie groups differently per request. Fix: `ORDER BY created_at DESC, id DESC`, preferably keyset on the same tuple.
2. **Why does page 5,000 cost more than page 1 under OFFSET, and what is the asymptotic difference versus keyset?** OFFSET re-sorts and discards all rows before the page, so per-page cost grows with depth and full-export work is quadratic; keyset seeks into the index at the cursor — constant per page, linear in total.
3. **Can id 100 commit after id 101? What does id order actually mean?** Yes — sequences allocate at statement time, visibility happens at commit, and rollbacks leave gaps. Id order equals allocation order for committed rows; it is not a clock or a causal order.
4. **Where do NULLs sort, and how do you make the answer portable?** PostgreSQL: last under ASC by default; MySQL and SQLite: first. Portability comes from explicit `NULLS FIRST/LAST` plus a unique tie-breaker, since the standard only fixes rows with distinct keys.
5. **Your UUIDv4-keyed table has slow inserts and a bloated clustered index. Why?** Random keys insert at random B-tree positions, splitting pages at ~50% fill and thrashing the buffer pool. Time-ordered identifiers (Snowflake/ULID/UUIDv7) restore locality at the cost of leaking timing and needing coordination.

## Key Takeaways

- An order is total only if its key list ends in a unique column; otherwise the engine chooses tie order and every mechanism built on the order inherits the nondeterminism.
- Positional pagination claims the dataset is frozen; under concurrent writes it skips and duplicates rows, and under depth it re-pays all prior work per page.
- Auto-increment ids approximate allocation order, not time: commits reorder, rollbacks leave gaps, loaders interleave. Temporal claims belong in timestamp columns, with the id as tie-breaker.
- Keyset pagination with an opaque cursor is the default for user-facing ordering; offsets belong to small, bounded, low-concurrency surfaces.
- Stability and NULL placement are implementation properties, not sorting properties: specify NULLS FIRST/LAST and tie-breakers explicitly.
- Random identifiers trade index locality for unguessability; time-ordered ids trade it back — a storage and privacy decision, not a naming detail.

## Cross-References

- [API contracts](api-contracts.md) — the published side of the same assumptions.
- [Database isolation](database-isolation.md) — what concurrent transactions do to the frozen dataset a paginator assumes.
- [Caching](caching.md) — why the deepest pages are the most expensive, least cached traffic.
- [Follow-up tree: database indexes](../followup-tree/database-indexes.md) — escalation from a slow ordering query to index design.
- [Misconception: relational DBs don't scale](../misconceptions/relational-dbs-dont-scale.md) — offset cost and tie-breakers as the concrete mechanisms.
- [Composite indexes](../../dbms/indexing/composite-index.md) — the structure that makes a tie-broken sort an index scan.
- [NULL semantics](../../dbms/null-semantics.md) — per-engine NULL ordering and portability.
- [Index structures](../connection-atlas/db-indexes-data-structures.md) — B-tree ordering versus external sort.
- [Snowflake versus UUID](../why-not-handbook/snowflake-vs-uuid.md) — the locality-versus-unguessability id trade.
- PostgreSQL's [SELECT reference](https://www.postgresql.org/docs/current/sql-select.html), [LIMIT clause](https://www.postgresql.org/docs/current/queries-limit.html), and MySQL's [LIMIT optimization](https://dev.mysql.com/doc/refman/8.0/en/limit-optimization.html) and [clustered index](https://dev.mysql.com/doc/refman/8.0/en/innodb-index-types.html) pages — official documentation for the engine-specific claims.
