# PostgreSQL Advanced Features

## JSONB

Binary JSON with indexing support:

```sql
-- Store and query JSON
CREATE TABLE events (data JSONB);
INSERT INTO events VALUES ('{"type": "click", "page": "/home", "user": {"id": 1}}');

-- Query operators
SELECT * FROM events WHERE data->>'type' = 'click';           -- text extraction
SELECT * FROM events WHERE data->'user'->>'id' = '1';         -- nested
SELECT * FROM events WHERE data @> '{"type": "click"}';       -- containment
SELECT * FROM events WHERE data ? 'page';                      -- key exists

-- GIN index for fast JSONB queries
CREATE INDEX idx_events_data ON events USING GIN (data);
```

## Array Types

```sql
CREATE TABLE posts (
  id SERIAL PRIMARY KEY,
  title TEXT,
  tags TEXT[]
);

INSERT INTO posts VALUES (1, 'Hello', ARRAY['python', 'web']);

-- Array operators
SELECT * FROM posts WHERE 'python' = ANY(tags);
SELECT * FROM posts WHERE tags @> ARRAY['web'];
SELECT * FROM posts WHERE array_length(tags, 1) > 2;

-- Unnest
SELECT id, unnest(tags) as tag FROM posts;
```

## Full-Text Search

```sql
-- Create tsvector column
ALTER TABLE articles ADD COLUMN fts tsvector;
UPDATE articles SET fts = to_tsvector('english', title || ' ' || body);

-- Create GIN index
CREATE INDEX idx_fts ON articles USING GIN (fts);

-- Search
SELECT * FROM articles WHERE fts @@ to_tsquery('english', 'postgresql & performance');

-- Ranking
SELECT *, ts_rank(fts, query) as rank
FROM articles, to_tsquery('english', 'postgresql & performance') as query
WHERE fts @@ query ORDER BY rank DESC;
```

## Window Functions

```sql
-- Running total
SELECT date, amount, SUM(amount) OVER (ORDER BY date) as running_total
FROM sales;

-- Rank within groups
SELECT *, ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC) as rank
FROM employees;

-- Moving average
SELECT date, amount,
  AVG(amount) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as ma7
FROM sales;

-- Lag/Lead
SELECT date, amount,
  LAG(amount) OVER (ORDER BY date) as prev_day,
  amount - LAG(amount) OVER (ORDER BY date) as change
FROM sales;
```

## EXPLAIN ANALYZE

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT e.name, d.name FROM employees e
JOIN departments d ON e.dept_id = d.id
WHERE e.salary > 50000;

-- Key things to look for:
-- Seq Scan vs Index Scan vs Index Only Scan
-- Actual rows vs Planned rows (big difference = stale stats)
-- Nested Loop vs Hash Join vs Merge Join
-- Buffers: shared hit (cache) vs read (disk)
```

## Indexes

| Type | Best For | Use Case |
|---|---|---|
| B-tree | Equality, range | Default, most queries |
| Hash | Equality only | Large text equality |
| GiST | Geometric, full-text | PostGIS, tsvector |
| GIN | Array, JSONB, full-text | `@>`, `@@`, `ANY()` |
| BRIN | Large ordered tables | Timestamps, sequential IDs |

```sql
-- Partial index
CREATE INDEX idx_active_users ON users(email) WHERE active = true;

-- Expression index
CREATE INDEX idx_lower_email ON users(lower(email));

-- Covering index (INCLUDE)
CREATE INDEX idx_covering ON users(dept_id) INCLUDE (name, salary);
```

## Replication

### Streaming Replication
```
Primary → WAL Stream → Replica (hot standby, read-only)
```

### Logical Replication
```
Publication (publisher) → Subscription (subscriber)
- Selective: specific tables
- Bidirectional possible
- Schema changes not replicated
```

## Connection Pooling

```bash
# pgBouncer configuration
[databases]
mydb = host=127.0.0.1 port=5432 dbname=mydb

[pgbouncer]
listen_port = 6432
pool_mode = transaction    # session | transaction | statement
max_client_conn = 1000
default_pool_size = 20
```

## Interview Questions

**Q: What is MVCC and how does it work in PostgreSQL?**
A: Multi-Version Concurrency Control — each row has xmin/xmax transaction IDs. Readers see a consistent snapshot without locking. Updates create new row versions, old versions are marked dead. VACUUM reclaims dead tuple space. Enables concurrent reads/writes without blocking.

**Q: When would you use GIN vs GiST indexes?**
A: GIN (Generalized Inverted Index) for exact match within composite values: JSONB containment, array overlap, full-text search. GiST for geometric/range data and lossy full-text. GIN is faster for lookups; GiST supports more data types and is faster to update.

**Q: How does streaming replication work?**
A: Primary ships WAL records to replicas in real-time. Replicas apply WAL to stay in sync. Replicas are read-only (hot standby). Lag depends on network and write volume. Synchronous replication guarantees no data loss but adds latency.

## Beyond B-Tree: The PostgreSQL Index Type Catalog

B-tree internals: [../indexing/b-plus-tree.md](../indexing/b-plus-tree.md); index selection strategy: [../indexing-strategy.md](../indexing-strategy.md). Here only the PostgreSQL-specific catalog. The docs: "PostgreSQL provides several index types: B-tree, Hash, GiST, SP-GiST, GIN, BRIN, and the extension bloom," each "best suited to different types of indexable clauses."

### GIN — inverted index, fastupdate, pending list

GIN holds "a separate entry for each component value" of composite data — it powers JSONB containment (`@>`), array operators, and full-text matching (structure: [../indexing/gin.md](../indexing/gin.md)). One row insert fans out into many index inserts, so "GIN is capable of postponing much of this work by inserting new tuples into a temporary, unsorted list of pending entries," merged at vacuum or when the list exceeds `gin_pending_list_limit`. Costs: a large pending list "will slow searches significantly," and an oversized one triggers "an immediate cleanup cycle" on one unlucky update. Set `fastupdate = off` when consistent read latency beats write speed; bulk loads leave a pending list that every search scans until vacuum drains it.

### GiST vs SP-GiST

"GiST indexes are not a single kind of index, but rather an infrastructure" — balanced trees storing conservative summaries (bounding boxes, ranges), lossy matches rechecked against the heap, KNN via `<->`. "SP-GiST is an abbreviation for space-partitioned GiST" and supports "non-balanced data structures, such as quad-trees, k-d trees, and radix trees (tries)" — recursion over *disjoint* partitions. Heuristic: overlapping regions (geometries, intervals) → GiST; partitionable, non-overlapping data (points, tries) → SP-GiST. See [../indexing/gist.md](../indexing/gist.md).

### BRIN — block-range summaries for append-only giants

BRIN "store[s] summaries about the values stored in consecutive physical block ranges," so it is "most effective for columns whose values are well-correlated with the physical order of the table rows" — a 1 TB time-series table gets a BRIN measured in megabytes (sizing: [../indexing-strategy.md](../indexing-strategy.md)). The `pages_per_range` tradeoff: "the smaller the number, the larger the index becomes..., but at the same time the summary data stored can be more precise and more data blocks can be skipped." New ranges stay unsummarized until a summarization run (vacuum, or off-by-default `autosummarize`). Scramble physical order and BRIN silently degrades to full scans (Problem 3).

### Hash

"Hash indexes store a 32-bit hash code derived from the value of the indexed column. Hence, such indexes can only handle simple equality comparisons." Tuples hold just the 4-byte hash — smaller than B-trees on long keys; single-column, no uniqueness, no ranges. Version trap: PG 9.6 docs warned "Hash index operations are not presently WAL-logged"; current docs say hash indexes are "fully crash recoverable" — WAL-logging arrived in PostgreSQL 10. Details: [../indexing/hash-index.md](../indexing/hash-index.md).

### Partial, expression, and INCLUDE

- **Partial**: "an index built over a subset of a table... defined by a conditional expression (called the predicate)." Rationale: skip common values — "there is no point in keeping those rows in the index at all" — which also "speed[s] up many table update operations."
- **Expression**: the index key "can be a function or scalar expression" — canonical case `lower(email)`; the expression "must be computed for each row insertion and non-HOT update."
- **INCLUDE (PG11+)**: "columns which will be included in the index as non-key columns... an index-only scan can return the contents of non-key columns without having to visit the index's table." Payload, not search keys; not part of uniqueness. Covering-index tradeoffs: [../indexing/covering-index.md](../indexing/covering-index.md).

## Declarative Partitioning

"PostgreSQL allows you to declare that a table is divided into partitions" by RANGE (time/ID series), LIST (region/tenant), or HASH (uncorrelated keys) over a partition key; each partition is a real, independently indexable table.

**Pruning**: the planner "examine[s] the definition of each partition and prove[s] that the partition need not be scanned" — and pruning happens "not only during the planning of a given query, but also during its execution," covering PREPARE parameters, subqueries, and nested-loop parameters (visible as "Subplans Removed" in EXPLAIN). Subtlety: pruning is "driven only by the constraints defined implicitly by the partition keys, not by the presence of indexes."

**Rolling windows**: ATTACH integrates a pre-built table; DETACH retires old data — "the detached partition continues to exist as a standalone table." `DETACH CONCURRENTLY` uses "a reduced lock level to avoid blocking other sessions" but is "not allowed if the partitioned table contains a default partition." A DEFAULT partition catches strays but "will be scanned" whenever a new partition is defined — skip that scan with a matching CHECK constraint. Partitioning (one server) ≠ sharding (many): [../../distributed/partitioning/range.md](../../distributed/partitioning/range.md), [../../distributed/partitioning/hash.md](../../distributed/partitioning/hash.md).

## Logical Replication

"Logical replication uses a publish and subscribe model with one or more subscribers subscribing to one or more publications on a publisher node." Pipeline: "The walsender process starts logical decoding" of WAL with the standard output plugin (pgoutput), filtered per publication, applied in transactional order. Onboarding is snapshot-then-stream: "PostgreSQL takes a snapshot of the table's data on the publisher database and copies it to the subscriber."

Documented use cases read like interview answers: incremental change feeds, "Consolidating multiple databases into a single one (for example for analytical purposes)," "Replicating between different major versions of PostgreSQL," cross-platform replication, selective table sharing.

Versus physical streaming ([../advanced/replication-strategies.md](../advanced/replication-strategies.md), incl. MySQL binlog internals): physical replays raw WAL onto byte-identical replicas; logical decodes row-level changes, so the subscriber may differ in layout, indexes, or major version. The price: "The database schema and DDL commands are not replicated... Subsequent schema changes would need to be kept in sync manually," and sequences are not replicated. Row-level decoding makes this the standard CDC feed — pair with an outbox per [../../backend/patterns/cdc-outbox.md](../../backend/patterns/cdc-outbox.md); an orphaned replication slot pins WAL forever.

## Parallel Query

"When the optimizer determines that parallel query is the fastest execution strategy for a particular query, it will create a query plan that includes a Gather or Gather Merge node." The Gather's child is "the portion of the plan that will be executed in parallel"; the leader runs it too but "must also read all of the tuples generated by the workers." Gather Merge means workers emit sorted output for the leader's "order-preserving merge."

Limits form a three-knob budget: workers per Gather are "limited to at most max_parallel_workers_per_gather" (default 2; "Setting this value to 0 disables parallel query execution"), from a pool bounded by `max_worker_processes` and `max_parallel_workers` — so "it is possible for a parallel query to run with fewer workers than planned, or even with no workers at all." Concurrent OLAP queries oversubscribe that pool fast.

What blocks parallelism: "The query writes any data or locks any database rows"; "The query might be suspended during execution... a cursor created using DECLARE CURSOR will never use a parallel plan"; "The query uses any function marked PARALLEL UNSAFE" (user-defined functions default to UNSAFE); and queries nested inside an already-parallel query. Maintenance parallelizes too — "CREATE INDEX when building a B-tree, GIN, or BRIN index, and VACUUM without FULL option" (`max_parallel_maintenance_workers`) — and aggregation is two-stage (Partial → Finalize Aggregate), disfavoring high-cardinality GROUP BYs.

## JSONB Internals

"jsonb data is stored in a decomposed binary format... significantly faster to process, since no reparsing is needed. jsonb also supports indexing" (unlike `json` text).

**TOAST**: "PostgreSQL uses a fixed page size (commonly 8 kB), and does not allow tuples to span multiple pages... large field values are compressed and/or broken up into multiple physical rows" — chunked into a companion TOAST table behind an 18-byte pointer, capped at 1 GB. Consequence: reading any field of a TOASTed jsonb document detoasts the whole value; any update rewrites the entire document plus its TOAST chain.

**Indexing**: GIN is the access method; "jsonb_path_ops supports fewer operators but offers better performance for those operators" and much smaller indexes — but no key-exists (`?`) queries.

**SQL/JSON**: `jsonb_path_query(target jsonb, path jsonpath)` implements the standard path language — "similarly to XPath expressions used for access to XML content."

**When not to use JSONB**: hot equality/range-predicted fields, foreign keys, per-column planner statistics, or high-rate field updates (whole-value rewrites kill HOT) — use columns. JSONB fits schema-optional attributes and semi-structured payloads.

## Full-Text Search

`tsvector` (normalized lexemes) + `tsquery` + `@@` + a GIN index is the core loop; ranking via `ts_rank` (inverted-index theory: [../../search/fundamentals.md](../../search/fundamentals.md)). For user input, "websearch_to_tsquery is a simplified version of to_tsquery with an alternative syntax, similar to the one used by web search engines" — crucially, "this function will never raise syntax errors, which makes it possible to use raw user-supplied input for search." `to_tsquery` throws on malformed input; never feed it raw user text.

## The Extensions Ecosystem

- **pg_stat_statements**: "tracking planning and execution statistics of all SQL statements executed by a server" — the first stop for top-total-time queries; needs `shared_preload_libraries` (a restart).
- **pgvector**: `vector` type + ANN indexes inside PostgreSQL — [../../llm/advanced/pgvector.md](../../llm/advanced/pgvector.md); HNSW internals: [../../search/hnsw.md](../../search/hnsw.md).
- **PostGIS**: the GiST-based geospatial extension with KNN search.

## Autovacuum Tuning Essentials

MVCC version storage and VACUUM mechanics: [../advanced/mvcc-internals.md](../advanced/mvcc-internals.md). The PG-specific knobs:

- **Trigger** = `autovacuum_vacuum_threshold` (default 50) + `autovacuum_vacuum_scale_factor` × rows — "The default is 0.2 (20% of table size)." On 100 M rows that is 20 M dead tuples before vacuuming starts; cap with `autovacuum_vacuum_max_threshold` (100 M) and set per-table storage parameters — 0.01–0.05 scale factors for hot big tables.
- **Insert-only tables** trigger via `autovacuum_vacuum_insert_scale_factor` ("The default is 0.2 (20% of unfrozen pages in table)") so append-only tables still freeze.
- **Wraparound**: 32-bit XIDs mean a long-running cluster "would suffer transaction ID wraparound... In short, catastrophic data loss"; it "will refuse to assign new XIDs once there are fewer than three million transactions left until wraparound." `autovacuum_freeze_max_age` (200 M) forces anti-wraparound vacuums even with autovacuum off; `vacuum_failsafe_age` (1.6 billion) is VACUUM's "strategy of last resort."
- **Monitor**: `n_dead_tup` vs threshold, `last_autovacuum`, and long-running transactions pinning the vacuum horizon.

## Interview Problems (Worked)

**1. jsonb vs normalized for a semi-joined 100 GB table.** Argue from access paths. Normalize when hot fields carry equality/range predicates (B-tree beats GIN), need FKs, or need planner statistics; keep JSONB when attributes vary per row and queries are containment-style. Best answer: hybrid — extract the 2–3 hot predicates into generated columns with B-tree indexes, leave the tail as JSONB with `jsonb_path_ops`; note TOAST pressure. *Red flag:* "always normalize" without an access-path argument.

**2. Rolling 90-day partition lifecycle.** Daily RANGE partitions on event time; pre-create tomorrow's partition nightly; at day 90, `DETACH PARTITION ... CONCURRENTLY` (no transaction blocks; forbidden with a DEFAULT partition — plan accordingly). ATTACH fast-path: pre-create equivalent indexes ("if a valid equivalent index already exists in the partition, it will be attached") and prove bounds with CHECK constraints to skip validation scans. Queries must filter on time to prune — runtime pruning shows as "Subplans Removed." *Red flags:* DELETE-based retention (dead-tuple flood); forgetting DETACH leaves a standalone table.

**3. Why is my BRIN useless after rewrites?** BRIN summaries describe *physical* block ranges; selectivity depends on column-to-physical-order correlation. VACUUM FULL rewrites the heap — correlation destroyed, every range's [min,max] spans the whole domain, nothing prunes. Fix: `REINDEX` the BRIN after the rewrite; prefer ordinary vacuum for bloat (VACUUM FULL takes ACCESS EXCLUSIVE); `CLUSTER` on time or reload in order; consider `autosummarize` and `pages_per_range`. *Red flags:* "reindex the heap"; treating this as fragmentation rather than a broken core assumption.

## Key Takeaways

- GIN amortizes fan-out writes via the pending list (`fastupdate`, `gin_pending_list_limit`); drain with vacuum or disable it.
- GiST summarizes overlapping space; SP-GiST partitions disjoint space; BRIN dies with sort-order correlation; hash is WAL-logged only since PG10.
- Partial/expression/INCLUDE indexes specialize and shrink; INCLUDE enables index-only scans.
- Pruning works at plan and execution time; ATTACH/DETACH make retention O(partition), not O(table).
- Logical replication decodes WAL to row changes (upgrades, CDC); DDL/sequences stay manual; watch replication slots.
- Parallel query: Gather/Gather Merge, ≤ `max_parallel_workers_per_gather`, blocked by writes, cursors, PARALLEL UNSAFE.
- jsonb is TOASTed as one value — read-all/rewrite-all; index with GIN.
- Autovacuum trigger = threshold + scale factor; per-table overrides for big tables; wraparound is the catastrophic mode.

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)
- [Use The Index, Luke](https://use-the-index-luke.com/)
1. PostgreSQL, "[Index Types](https://www.postgresql.org/docs/current/indexes-types.html)" — access-method catalog.
2. PostgreSQL, "[GIN Indexes](https://www.postgresql.org/docs/current/gin.html)" — fastupdate, pending list, jsonb opclasses.
3. PostgreSQL, "[Hash Indexes](https://www.postgresql.org/docs/current/hash-index.html)" — crash-recoverable hash indexes.
4. PostgreSQL 9.6, "[Index Types](https://www.postgresql.org/docs/9.6/indexes-types.html)" — pre-10 "not presently WAL-logged" hash behavior.
5. PostgreSQL, "[SP-GiST Indexes](https://www.postgresql.org/docs/current/spgist.html)" — space-partitioned trees.
6. PostgreSQL, "[BRIN Indexes](https://www.postgresql.org/docs/current/brin.html)" — pages_per_range, summarization.
7. PostgreSQL, "[Partial Indexes](https://www.postgresql.org/docs/current/indexes-partial.html)".
8. PostgreSQL, "[Indexes on Expressions](https://www.postgresql.org/docs/current/indexes-expressional.html)".
9. PostgreSQL, "[CREATE INDEX](https://www.postgresql.org/docs/current/sql-createindex.html)" — INCLUDE clause.
10. PostgreSQL, "[Table Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)" — methods, pruning.
11. PostgreSQL, "[ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)" — ATTACH/DETACH, CONCURRENTLY.
12. PostgreSQL, "[Logical Replication](https://www.postgresql.org/docs/current/logical-replication.html)" — model, use cases.
13. PostgreSQL, "[Logical Replication Architecture](https://www.postgresql.org/docs/current/logical-replication-architecture.html)" — walsender/pgoutput/apply.
14. PostgreSQL, "[Restrictions](https://www.postgresql.org/docs/current/logical-replication-restrictions.html)" — DDL not replicated.
15. PostgreSQL, "[Logical Decoding](https://www.postgresql.org/docs/current/logicaldecoding.html)".
16. PostgreSQL, "[Parallel Query](https://www.postgresql.org/docs/current/parallel-query.html)".
17. PostgreSQL, "[How Parallel Query Works](https://www.postgresql.org/docs/current/how-parallel-query-works.html)" — Gather/Gather Merge, worker limits.
18. PostgreSQL, "[When Can Parallel Query Be Used?](https://www.postgresql.org/docs/current/when-can-parallel-query-be-used.html)" — blockers.
19. PostgreSQL, "[Resource Consumption](https://www.postgresql.org/docs/current/runtime-config-resource.html)" — parallel worker knobs.
20. PostgreSQL, "[JSON Types](https://www.postgresql.org/docs/current/datatype-json.html)" — json vs jsonb.
21. PostgreSQL, "[TOAST](https://www.postgresql.org/docs/current/storage-toast.html)".
22. PostgreSQL, "[JSON Functions](https://www.postgresql.org/docs/current/functions-json.html)" — jsonb_path_query, SQL/JSON path.
23. PostgreSQL, "[Controlling Text Search](https://www.postgresql.org/docs/current/textsearch-controls.html)" — websearch_to_tsquery, ranking.
24. PostgreSQL, "[pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html)".
25. PostgreSQL, "[Automatic Vacuuming](https://www.postgresql.org/docs/current/runtime-config-autovacuum.html)" — scale factors, freeze ages.
26. PostgreSQL, "[Routine Vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)" — wraparound.
27. PostgreSQL, "[Parallel Plans](https://www.postgresql.org/docs/current/parallel-plans.html)" — parallel aggregation/append.

## Cross-References

- [../indexing/b-plus-tree.md](../indexing/b-plus-tree.md) — B-tree internals · [../indexing-strategy.md](../indexing-strategy.md) — index selection + BRIN sizing.
- [../indexing/gin.md](../indexing/gin.md) · [../indexing/gist.md](../indexing/gist.md) · [../indexing/hash-index.md](../indexing/hash-index.md) · [../indexing/covering-index.md](../indexing/covering-index.md) — per-method deep dives.
- [../advanced/mvcc-internals.md](../advanced/mvcc-internals.md) — MVCC, VACUUM, wraparound · [../advanced/replication-strategies.md](../advanced/replication-strategies.md) — physical vs logical replication, MySQL binlog.
- [../../distributed/partitioning/range.md](../../distributed/partitioning/range.md) · [../../distributed/partitioning/hash.md](../../distributed/partitioning/hash.md) — partitioning as data distribution (sharding).
- [../../backend/patterns/cdc-outbox.md](../../backend/patterns/cdc-outbox.md) — CDC / transactional outbox.
- [../../search/fundamentals.md](../../search/fundamentals.md) — inverted index + ranking theory · [../../search/hnsw.md](../../search/hnsw.md) + [../../llm/advanced/pgvector.md](../../llm/advanced/pgvector.md) — ANN search, pgvector.
