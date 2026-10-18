# ORM vs Query Builder vs Raw SQL: Who Owns the Query Text?

## Overview

"ORM or raw SQL?" is framed as productivity versus control, but the real question is **who owns the query text** — and therefore who is responsible when the database does something surprising. An ORM generates SQL from object operations: the developer states intent ("load the user's orders"), and a library composes the statement, maps rows back into objects, and tracks changes. A query builder makes the developer compose SQL from composable fragments — still generated, but shape-visible and closer to what the planner sees. Raw SQL moves ownership entirely into the developer's hands: the text that reaches the server is the text that was reviewed.

None of the three is a beginner trap or an expert badge. ORMs exist because mapping rows to objects and tracking changes by hand is genuinely error-prone at CRUD scale; query builders exist because string-concatenated SQL is an injection factory; raw SQL exists because some queries — reporting, window functions, bulk transformations — are unnatural to express as object graphs at all. This page runs the [handbook framework](./index.md) across all three. The preview: **an ORM buys development velocity by hiding SQL, and the bill arrives as N+1 queries, leaky abstractions, and generated statements the query planner cannot serve well; raw SQL buys control and pays in mapping, testing, and maintenance boilerplate; the query builder is the explicitly priced middle**.

## Step 1: The Problem and Its Constraints

The workload: an application persists domain objects, reads them back, and occasionally runs aggregations over millions of rows. Constraints that decide where query ownership should sit:

- **Query mix.** Mostly point reads and writes by primary key (CRUD), or mostly complex joins, aggregations, and reports? An ORM's sweet spot is the former; the latter is where its generated SQL starts fighting the planner (see [query planner](../../dbms/query-planner.md)).
- **Team and skill distribution.** Is SQL fluency widespread, or concentrated in a few people? Ownership models that don't match team skills decay into "nobody looks at the generated SQL."
- **Schema governance.** Who evolves the schema? ORM-bundled migrations (Django, ActiveRecord) centralize it; hand-written migrations (Flyway-style) keep the database authoritative.
- **Performance surface.** Hot paths with strict latency budgets need statements that use exactly the right index; see [indexing strategy](../../dbms/indexing-strategy.md) for what "right" means.
- **Transaction scope.** Business operations spanning several tables and isolation-sensitive invariants need explicit transaction boundaries — see [database isolation assumptions](../assumptions-hunt/database-isolation.md) for what implicit boundaries hide.

## Step 2: The Mechanisms

### Option 1: The ORM — generated SQL from object operations

- **Identity map and unit of work.** The session keeps one object instance per row and tracks dirtied fields; on flush, it emits the minimal UPDATE. Two loads of the same row return the same in-memory object. This is the mechanism behind both the productivity win (no hand-written change tracking) and a characteristic failure (a session cache that quietly serves stale data across queries within one unit of work).
- **Lazy loading.** Associations load on first access. `user.getOrders()` issues a query *at access time*, not at load time. Combined with a loop over users, this is the N+1 mechanism — one query for the list, one per element for the association. Eager-loading options (`JOIN FETCH`, `select_related`, `include()`) and batching loaders (the dataloader pattern) exist precisely because the default is per-access.
- **Impedance mismatch as a leak.** Objects have identity and graphs; relational rows have keys and joins. The ORM papers over this, and the papering-over leaks: collection loading semantics differ between providers, flushing order is a library decision, and "just one property access" in a serializer triggers a query nobody budgeted for.
- **Dialect abstraction.** The same model classes generate Postgres or MySQL SQL. The abstraction is real for portable CRUD — and thin at the edges, where dialect differences (upsert syntax, returning clauses, index hints) break through anyway.

### Option 2: The query builder — SQL with structure

- **Composable fragments.** Conditions, joins, and projections are method calls on an expression tree; the builder renders dialect-specific text. `select(...).where(and_(...))` is SQL with structure — parameterization is automatic (the injection defense is structural, not disciplinary), and the resulting statement's shape is visible in code review.
- **What it does not do.** No identity map, no change tracking, no lazy loading. The builder solves the *text generation* problem and leaves mapping, caching, and transaction scope to the caller — which is exactly why it ages better than ORMs on complex projects: fewer invisible mechanisms.
- **The middle's real cost.** Dynamic query composition is where builders shine (filters assembled from user input); but every row still needs explicit mapping code, and the boundary between "complex query" and "should be a stored view or a reporting query" gets policed by convention rather than tooling.

### Option 3: Raw SQL — ownership without intermediaries

- **The statement is the artifact.** Reviewed, tested, and tuned as text. `EXPLAIN ANALYZE` output maps one-to-one to the statement under review — no translation layer between what you wrote and what the planner received (see [query planner dataflow](../connection-atlas/query-planner-dataflow.md)).
- **Mapping is manual or thin.** Row-to-object code is boilerplate; every schema change touches every affected query. This is the honest cost — raw SQL scales with query count, and its maintenance surface grows linearly.
- **Where it is not optional.** Window functions, recursive CTEs, lateral joins, `GROUPING SETS`, and bulk set operations exist in the database's language, not in any object model. Forcing them through an ORM escape hatch (`query.raw(...)`) means the ORM was never going to own them anyway. The [SQL track](../../dbms/sql/README.md) is the repository-side home for that vocabulary.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | ORM | Query builder | Raw SQL |
|----------|-----|---------------|---------|
| Development velocity at CRUD | Highest: mapping, change tracking, migrations bundled | Medium: explicit mapping still required | Lowest: every statement and mapping hand-written |
| SQL shape visibility | Hidden until you opt into logging | Visible as composed fragments | Identical to what the planner sees |
| N+1 exposure | Structural (lazy loading defaults) | None (no implicit loads) | None |
| Injection safety | Parameterized by design | Parameterized by design | Safe only with disciplined parameter binding |
| Complex analytics | Escape hatch; impedance fight | Awkward but possible | Native |
| Dialect portability | Real for portable CRUD | Real per fragment | Manual per statement |
| Migration story | Bundled, model-driven | Mixed | Hand-written, DB-authoritative |
| Planner cooperation | Unpredictable — generated text decides | Predictable, reviewable | Direct |
| Signature failure | N+1 under load; stale session cache; bulk ops issued row-by-row | None structural — misuse is visible | Boilerplate sprawl; injection when discipline lapses |

**The N+1 mechanism deserves the arrow drawn.** Lazy loading defers the association query to property access; a serializer walking a list of 100 users accesses `orders` per user; the ORM issues 101 statements where one join would do. Under low traffic this is invisible; at p99 under load it is the top table-lock on the whole request. The fix menu — eager loading, batched loaders (one `WHERE id IN (...)` per association), or restructuring the read — exists in every major ORM, but choosing it requires noticing the mechanism in the first place, which is why ORM logs and statement counts belong in development defaults, not production forensics.

## Step 4: When Each Wins

**The ORM wins** when the application is CRUD-dominated: point reads and writes by key, forms, admin panels, standard web backends. Change tracking, validation hooks, and bundled migrations genuinely save weeks; the query shapes are simple enough that generated SQL matches what you would have written. A team of application developers without deep SQL expertise is the target audience — and the right one.

**The query builder wins** when queries are dynamic and safety-critical but mapping machinery is unwanted: search endpoints with optional filters, dashboards with user-driven grouping, ETL steps. It is also the correct default for teams that want ORM-free clarity without string-building risk.

**Raw SQL wins** when the statement is the hard part: reporting and analytics (window functions, recursive CTEs, complex aggregations), bulk operations, migration and backfill scripts, and any hot path where a specific index plan is a requirement. Performance-critical read paths in high-traffic services are commonly hand-written SQL even inside ORM-heavy codebases — the ORM is the default, and the hot path is the exception that gets reviewed.

## Step 5: Edge Cases and Counterexamples

- **ORM-generated SQL that defeats indexes.** Wrapping an indexed column in a function — `WHERE lower(email) = ?` generated from a normalized-field setting — cannot use a plain B-tree index on `email` (see [B+tree](../../dbms/indexing/b-plus-tree.md) mechanics); the fix is an expression index, which the model layer usually cannot express. Implicit type casts are the second classic: an ORM binding a string parameter against an integer column forces per-row casts in engines that would otherwise use the index. Both failures look like "the database is slow" and are actually "the generated text changed the predicate."
- **Bulk operations issued row-by-row.** An ORM's unit of work flushes one UPDATE per dirty object unless batch settings are configured; a loop updating 10,000 rows becomes 10,000 statements plus 10,000 round trips. The same operation as one `UPDATE ... FROM` is orders of magnitude faster. Session-level caches make it worse: each flushed row may invalidate identity-map entries.
- **Deep pagination through generated OFFSET.** `ORDER BY id OFFSET 100000 LIMIT 20` — a common ORM pagination idiom — makes the planner materialize and discard 100,000 rows per page (see [index tuning](../../dbms/indexing/tuning.md) for keyset alternatives). The abstraction hid the cost shape until the p99 page load.
- **Prepared statement plan caching interacts with generated SQL.** ORMs that inline literal values fragment the plan cache (each distinct literal is a new statement to parse and plan — see [plan caching](../../dbms/query-processing/plan-caching.md)); ORMs that parameterize everything sometimes defeat partition pruning or generic-plan switches that a hand-written statement with explicit types would benefit from. The planner sees the text the ORM wrote — the abstraction boundary is exactly there.
- **The session cache lies at transaction boundaries.** Inside one unit of work, a second query for the same row may return the in-memory object from the identity map rather than fresh database state — correct within the transaction's snapshot, surprising across them. Debugging sessions that "see" deleted rows are almost always identity-map artifacts, not isolation bugs.
- **Raw SQL's failure is a process failure.** Schema drift between hand-written queries and ORM-managed migrations surfaces at runtime instead of compile time; typed query builders and integration tests exist because raw SQL's ownership model has no type system checking it. The counterexample cuts both ways: the ORM's compile-time safety is real, and so is its ceiling.

## Step 6: Decision Framework

1. **Is the workload CRUD-dominated with simple query shapes?** Yes → ORM; invest instead in lazy-loading discipline (eager-load lists, count statements in tests).
2. **Are queries dynamically composed from user input?** Yes → query builder; parameterization and fragment composition are exactly its design center.
3. **Is the statement the hard part — analytics, window functions, bulk transforms, hot-path index plans?** Yes → raw SQL, reviewed and tested as text.
4. **Does anyone on the team read generated SQL before production?** If no, either institute statement logging in development or accept that the ORM is making unplannable queries on your behalf.
5. **Who owns schema evolution?** Model-driven migrations fit ORM-centric teams; database-authoritative migrations (hand-written, versioned) fit raw-SQL-heavy codebases. Mixing both without a convention is how drift happens.
6. **Default in doubt:** ORM for the application's CRUD backbone, query builder for dynamic reads, raw SQL for reporting and hot paths — the hybrid is not indecision; it is matching query ownership to query shape, with the seams (where each mode's failure modes live) made explicit.

## Interview Questions

1. **Explain the N+1 problem as a mechanism, not a slogan.** Lazy loading defers association queries to first access; iterating a list of N parents accesses each association, issuing N additional statements after the initial list query. Detection is statement counting; fixes are eager loading, batched `IN` loaders, or restructuring the read. The reason it survives to production is that per-access queries look innocent in development and only multiply under real list sizes.
2. **An ORM-generated query is slow; `EXPLAIN` shows a sequential scan on an indexed column. What happened?** The generated predicate does not match the index: either the column is wrapped in a function (`lower(email) = ?`) or the parameter type forces casts, so the planner cannot use the plain B-tree index. Fixes: expression index, corrected binding types, or hand-writing the predicate. The lesson is that the planner sees the generated text — ownership of the query text is ownership of the plan.
3. **When is raw SQL not just acceptable but the only correct choice?** When the query's semantics are relational constructs no object model expresses well — window functions, recursive CTEs, lateral joins, set-based bulk operations — or when a hot path requires an exact index plan. ORMs handle these through escape hatches that are raw SQL with extra steps; owning the text directly is more honest and more reviewable.
4. **What does the query builder give you that neither the ORM nor raw SQL does?** Structural parameterization (injection safety by construction), visible statement shape in code review, and composability for dynamic filters — without identity maps, change tracking, or implicit loads. It is the explicitly-priced middle: you keep mapping boilerplate, you lose invisible machinery.
5. **Why does "the ORM hides SQL" become a production incident pattern?** Because the hidden decisions — lazy loading defaults, flush-per-row bulk behavior, OFFSET pagination, literal inlining versus parameter binding — are plan-shaping decisions made by the library, not the developer. The abstraction is leaky precisely where performance lives; teams that never look at generated SQL discover the leaks as p99 regressions.

## Key Takeaways

- The three options differ in who owns the query text: the ORM generates it from object operations, the builder composes it visibly, raw SQL is it. Performance and maintainability both follow from that ownership.
- The ORM's characteristic failures are structural, not bugs: N+1 from lazy loading, row-by-row bulk flushes, identity-map staleness, and generated predicates that defeat indexes.
- Query builders are the safety-priced middle: parameterization and composability without invisible machinery — and no N+1 because nothing loads implicitly.
- Raw SQL is mandatory vocabulary for analytics, bulk operations, and hot paths; its cost is mapping boilerplate and a maintenance surface that grows with query count.
- The planner only ever sees text. Whether that text came from a model class, a builder chain, or a hand-written string is invisible to the database — which is why reading generated SQL in development is a non-negotiable habit.

## Cross-References

- [Query Planner](../../dbms/query-planner.md) — how the server turns text into plans, and why the text matters.
- [Plan Caching](../../dbms/query-processing/plan-caching.md) — prepared statements, plan reuse, and the literal-versus-parameter interaction.
- [Indexing Strategy](../../dbms/indexing-strategy.md) — what "the generated query uses the right index" means concretely.
- [Schema Migrations](../../dbms/advanced/schema-migrations.md) — the evolution story the three ownership models each handle differently.
- [Query Planner Dataflow: Connection Atlas](../connection-atlas/query-planner-dataflow.md) — the dependency web from SQL text to executed plan.
- [Database Indexes: Follow-up Tree](../followup-tree/database-indexes.md) — escalating interview chain on index mechanics behind the slow-query cases here.
- [Database Isolation: Assumptions Hunt](../assumptions-hunt/database-isolation.md) — the transaction-scope assumptions ORM sessions and raw scripts each make implicitly.
- [B+Tree](../../dbms/indexing/b-plus-tree.md) — the index mechanics the defeated-index edge cases rely on.
- [Database Choices](./database-choices.md) — sibling page: the storage-engine choices upstream of query ownership.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
