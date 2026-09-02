# Database Indexing Strategy

Indexes are the single biggest lever you have over query latency in a
relational database. A sequential scan of a 100-million-row table is a
matter of minutes; the same query against a well-chosen B+tree returns in
milliseconds. Yet most production systems carry the wrong indexes — too
many on writes, too few on the hot read paths, and the right columns in
the wrong order. Markus Winand's *SQL Performance Explained* (and the
companion site *Use The Index, Luke!*) makes one argument in 250 pages:
**index for the `WHERE`, not the `SELECT`**. The rest of this page is the
implications of that sentence.

We go through the index types that show up in real systems — B+tree,
covering, composite, partial, hash, GIN, GiST, BRIN — and then talk about
the maintenance cost you pay on every `INSERT`, `UPDATE`, and `DELETE`.

## The B+tree Index

The B+tree is the default in PostgreSQL (`btree`), MySQL/InnoDB
(`KEY`), SQL Server (clustered and nonclustered), and Oracle
(normal B-tree). It is a balanced tree where **only the leaf nodes
store row data**; interior nodes store only routing keys. That gives
two properties you will lean on every day:

1. **O(log N) lookups** with a small constant. For a 100M-row table on
   a B+tree of height 4 and 8 KiB pages, each lookup is at most 4 page
   reads — about 32 KiB of I/O on a cold cache.
2. **Range scans are sequential**. Leaves are linked in a doubly-linked
   list, so once you land on the first matching leaf, you walk sideways
   to read the rest. A `WHERE ts BETWEEN '2024-01-01' AND
   '2024-01-31'` becomes a one-directional walk, not a tree descent per
   row.

```
                  Interior node (routing keys only)
                 /         |          |          \
              leaf ────── leaf ───── leaf ───── leaf     ← doubly-linked
              (k1..k100)  (k101..k200) ...              ← row pointers
```

The non-leaf branching factor for a 4-byte integer key and 8-byte
page-pointer is roughly `(8192 - 24) / (4 + 8) ≈ 680` children per
node. Two interior levels already cover ~460k leaves × ~200 rows/leaf
≈ 90M rows in 3 page reads. This is why B+trees "just work" up to
terabyte-scale tables — until they don't, which is the moment the
predicate can't use the leading column.

## The Composite Index and Why Column Order Matters

A composite index on `(a, b, c)` is *not* three independent indexes.
It is one B+tree sorted lexicographically on `(a, b, c)`. The
planner can use it for:

- `WHERE a = ?`                     ✓ uses the index
- `WHERE a = ? AND b = ?`           ✓ uses the index, tighter range
- `WHERE a = ? AND b = ? AND c = ?` ✓ uses the index, exact match
- `WHERE b = ?`                     ✗ cannot use the index (no
                                     prefix match)
- `WHERE a = ? AND c = ?`           ~ partial use: filters on `a`,
                                     then needs to fetch rows to
                                     test `c` (in PostgreSQL, an
                                     "index filter")

The rule: **equality columns first, then range columns, then
order-by columns.** For `WHERE tenant_id = ? AND created_at BETWEEN
? AND ? ORDER BY created_at DESC`, the ideal order is
`(tenant_id, created_at)`. Reversed `(created_at, tenant_id)` is
useless for the `tenant_id` equality because `created_at` comes
first.

A common mistake: an analyst asks "show me the latest order per
customer" and gets `Seq Scan` because the only index is on
`(customer_id, created_at)` with no `DESC`. PostgreSQL 11+ can scan
a B+tree backward at the same cost as forward, so `DESC` is free
here — but only if the index is in a single sort direction. A
multi-direction `ORDER BY customer_id ASC, created_at DESC` needs
an explicit `CREATE INDEX ... ON orders (customer_id, created_at
DESC)`.

## The Covering Index (INCLUDE Columns)

Once the planner finds the matching rows via the index, it has two
options: stop there (an **index-only scan**) if every column the
query needs lives in the index, or fetch each row from the heap
(a **bitmap heap scan** or **fetch from heap**). The second costs an
extra random page read per row, which on a cold cache is the
difference between 2 ms and 200 ms.

A covering index deliberately stores columns the query *projects*
but does not *filter* on. PostgreSQL syntax:

```sql
CREATE INDEX orders_by_customer ON orders (customer_id)
    INCLUDE (order_total, created_at);

-- This query no longer touches the heap:
EXPLAIN SELECT customer_id, order_total, created_at
FROM   orders
WHERE  customer_id = 42;
--  Index Only Scan using orders_by_customer
--    Heap Fetches: 0
```

The `INCLUDE` columns are stored only at the leaf, not the interior
nodes, so they don't bloat the routing tree. SQL Server has the same
syntax; in MySQL 8.0 you write `CREATE INDEX ... (customer_id,
order_total, created_at)` and the engine treats the trailing
columns as "covering". InnoDB's clustered index already covers
every column (it *is* the table), so covering indexes are mostly
relevant for secondary indexes on InnoDB.

The heap-fetch counter in `EXPLAIN ANALYZE` is the tell: if it is
nonzero, the visibility map doesn't yet know that all of the rows
are visible to all transactions. Run `VACUUM` more often, or
reconsider whether the index actually covers.

## The Partial Index (WHERE Clause)

Indexes cost writes. If 90% of your orders are "shipped" and only
10% are "pending", an index on `WHERE status = 'pending'` is ten
times smaller than a full index and ten times cheaper to maintain
per row that isn't pending. PostgreSQL syntax:

```sql
CREATE INDEX orders_pending
    ON orders (customer_id, created_at)
    WHERE status = 'pending';

-- Only matches when the planner can prove status='pending':
SELECT * FROM orders
WHERE customer_id = 7 AND status = 'pending';
--  Index Scan using orders_pending
```

A partial index is also a **constraint**: the planner will only use
it if it can prove the query predicate implies the index predicate.
That means literal equality (`status = 'pending'`) is fine; a
parameter (`status = $1`) will not be able to use the partial index
unless the planner knows the parameter at plan time. Partial indexes
also serve as a cheap unique constraint:

```sql
CREATE UNIQUE INDEX one_active_subscription_per_user
    ON subscriptions (user_id)
    WHERE status = 'active';
```

You cannot express "at most one active subscription per user" with a
plain `UNIQUE` constraint; the partial unique index is the standard
workaround.

## The Hash Index

A hash index is a flat hash table on disk: `O(1)` equality lookup,
no range support, no ordering. In PostgreSQL, hash indexes were
unsafe under replication before 10 and have been crash-safe and WAL-
logged since. They remain niche because the speed advantage over a
B+tree on equality is rarely worth losing range scans and
`ORDER BY`. Use a hash index when:

- The only access pattern is `WHERE key = ?`.
- The key distribution is uniform (no skew to one bucket).
- You need to fit a larger working set than a B+tree of the same
  key width would, because hash indexes don't store keys, just
  hashes.

In practice you almost never beat a B+tree with a hash index in a
general-purpose database. The hash indexes you encounter in the wild
are usually in key-value engines (memcached, Redis, DynamoDB's
internal hash) where equality is the only operation.

## The GIN and GiST Indexes (PostgreSQL)

PostgreSQL ships two extension frameworks that look like indexes but
behave like inverted files: **GIN** (Generalized Inverted Index) and
**GiST** (Generalized Search Tree). They are the reason PostgreSQL
has the best full-text and geospatial indexing in the open-source
world.

**GIN** is the right choice when one row maps to *many* index keys.
The classical case is full-text search: a row's `tsvector` contains
many lexemes, and you want to find rows containing the lexeme
`'database'` fast. GIN stores a posting list per lexeme and is
essentially an inverted index.

```sql
CREATE INDEX docs_fts ON documents USING gin (to_tsvector('english', body));

SELECT id FROM documents
WHERE to_tsvector('english', body) @@ to_tsquery('database & index');
--  Bitmap Index Scan on docs_fts
```

GIN is fast to query, slow to update (each insert touches many
posting lists), so it's typically run with `fastupdate = on`, which
batches inserts into a pending list until the list fills a page.

**GiST** is a balanced tree of "union" predicates — it's not a B-tree
but a lossy spatial tree. It is used for `box`, `polygon`, `cidr`,
and the PostGIS `geometry` types. The defining feature is that an
entry's key in the tree is a *bounding box* that contains all keys in
its subtree. Range queries (`WHERE geom && ?`) walk the tree pruning
subtrees whose bounding boxes don't intersect.

| Type     | Best for                | Insert cost | Query cost       | Lossy? |
|----------|-------------------------|-------------|------------------|--------|
| btree    | equality, range, sort   | low         | O(log N)         | no     |
| hash     | equality only           | low         | O(1)             | no     |
| gin      | full-text, arrays, json | high        | O(1) per key     | no     |
| gist     | spatial, range types    | medium      | O(log N) + check | yes    |
| brin     | time-series, append-only| very low    | O(N/page ratio)  | yes    |

## The BRIN Index (Time-Series)

A Block Range Index (BRIN) keeps, for each range of `pages_per_range`
consecutive heap pages (default 128), the min and max of the indexed
column. For an append-only time-series table where rows are inserted
in `time` order, a BRIN index on `time` is essentially free: each
range's min and max is a tight bound, and a query for `time BETWEEN
'2024-09-01' AND '2024-09-30'` skips every range whose `[min, max]`
falls outside the predicate.

```
Heap pages:   |---block 1---|---block 2---|---block 3---| ... |
BRIN ranges:  min/max of column per pages_per_range=128 pages

Range 0:  [2024-01-01, 2024-01-05]   skip (out of query range)
Range 1:  [2024-02-28, 2024-03-04]   skip
Range 2:  [2024-08-29, 2024-09-02]   read — partial overlap
Range 3:  [2024-09-03, 2024-09-08]   read — full overlap
```

A BRIN index for 1 TB of metrics data is a few megabytes. The
trade-off: BRIN only works when the data is roughly sorted on disk
the same way the predicate filters. A heap-randomized table gives
BRIN no pruning power because every range has a wide `[min, max]`.
In that case, you need a B+tree — and the B+tree will be huge.

## Index-Only Scans

The single best thing an index can do for you is to make the heap
irrelevant. A query plan that says `Index Only Scan` does not touch
the heap at all — every column it needs is in the index, and the
visibility map confirms every row is visible to all current
transactions. The visibility check matters: without it, the index
alone can't tell if a row's latest version is the one the query
should see.

Two preconditions:

1. Every column the query *reads* is in the index (key columns or
   `INCLUDE` columns).
2. The page is "all visible" per the visibility map — vacuumed and
   not currently being modified.

If preconditions hold, you get an `Index Only Scan`. If the columns
hold but the visibility is missing, you get `Index Only Scan` with a
nonzero `Heap Fetches` counter, which means the planner pays random
I/O for visibility checks anyway. If the columns don't hold, the
plan degrades to `Index Scan` (random fetch per row) or `Bitmap
Heap Scan` (sorted batch fetch).

## The Principle: Index the WHERE, Not the SELECT

The most common indexing mistake is to index the columns you `SELECT`
rather than the columns you `WHERE` on. A query like:

```sql
SELECT customer_id, order_total, created_at
FROM   orders
WHERE  customer_id = 42;
```

…needs an index on `customer_id`. Many engineers, seeing `order_total`
and `created_at` in the SELECT list, create an index on
`(order_total, created_at)`. That index is useless for this query —
the planner will do a sequential scan instead. The index on
`customer_id` (or `(customer_id) INCLUDE (order_total, created_at)`
if you want a covering scan) is the one that helps.

Winand's mental model: an index is for finding rows, not for showing
them. You sort, group, and filter on the indexed columns; you
*project* whatever you like after the rows are found. A 5-column
covering index on the SELECT list with no predicate columns is a
maintenance cost with zero benefit.

## The Maintenance Cost

Every index is a B+tree that must stay sorted when rows change. The
cost per write is roughly:

- **INSERT**: one B+tree insert per index (one leaf split per ~200
  inserts, plus the parent chain rewrite, but amortized O(1)).
- **DELETE**: one B+tree delete per index (mark the entry, vacuum
  later).
- **UPDATE**: one delete + one insert per index whose key column
  changed. If the key column didn't change, some engines (InnoDB on a
  secondary index) can avoid the rewrite; PostgreSQL always rewrites
  the tuple and the index entries.

A table with one primary key plus 7 secondary indexes pays roughly
8 B+tree writes per `INSERT`. At 10k inserts/sec, that is 80k
B+tree writes per second — a real disk throughput problem on a
single SSD. OLTP systems routinely run with 3-5 indexes per hot
table, not 10. Drop the indexes you don't need; one company I worked
with dropped 14 unused indexes from a 200M-row table and cut write
latency by 40%.

The signal that you are over-indexed:

- `pg_stat_user_indexes.idx_scan` is near zero for some index
  (nobody queries the path).
- `pg_stat_user_indexes.idx_tup_read` is high but `idx_tup_fetch` is
  low (the index is being read but not used to fetch rows; possibly
  the planner picking the wrong index).
- The ratio of `n_tup_ins` to `n_tup_upd` is high relative to
  `idx_scan` (writes dwarf reads).

Maintenance isn't just at write time. PostgreSQL runs `autovacuum`
to reclaim dead tuples; every index has to be cleaned up too. A
table with 20 indexes means 20 indexes to scan during vacuum — and
`VACUUM` is one of the most common causes of latency spikes on
OLTP systems.

## Pitfalls

1. **Indexing the SELECT list.** An index on `(name, email)` for
   `SELECT name, email FROM users WHERE id = 42` is a no-op; you
   wanted an index on `id`.
2. **Composite index in the wrong order.** `(created_at,
   customer_id)` is useless for `WHERE customer_id = ?` because
   the leading column doesn't appear in the predicate.
3. **Function in the predicate breaks the index.**
   `WHERE lower(email) = 'x@y.com'` will not use an index on
   `(email)`. Use an expression index:
   `CREATE INDEX ON users (lower(email))` or a generated column.
4. **Type coercion on the indexed column.** `WHERE customer_id::text
   = '42'` will not use the integer index. Bind parameters with
   the right type.
5. **Implicit `<>` predicates.** `WHERE status <> 'shipped'` cannot
   use a partial index defined with `WHERE status = 'pending'`.
   The planner can't prove implication.
6. **Over-indexing a write-heavy table.** Each index is a B+tree
   write per `INSERT`/`UPDATE`. Audit `pg_stat_user_indexes`
   periodically and drop indexes with `idx_scan = 0`.
7. **Forgetting to run `ANALYZE` after a big load.** The planner's
   cardinality estimates are stale and it picks a seq scan on a
   table that now has 100M rows. `ANALYZE` after every bulk load.

## Interview Questions

### Q: When is a sequential scan faster than an index scan?

When the index is unselective — the predicate matches a large
fraction of the table. PostgreSQL's cutoff is roughly 5-10% of
rows: below that, an index scan wins; above, sequential I/O and a
bitmap scan (or pure seq scan) win. The exact crossover depends on
`random_page_cost` (default 4.0 in PostgreSQL) versus
`seq_page_cost` (1.0). On NVMe, lowering `random_page_cost` to
`1.1` reflects reality and shifts the crossover to ~50% of rows.

### Q: A composite index on `(a, b)` — can it serve `WHERE b = ?`?

In general no, because the B+tree is sorted on `a` first. PostgreSQL
9.6+ has "skip scan" optimization for some cases (constant `a` with
multiple known values), and 14+ can do index-only skip scans on
`DISTINCT` queries, but a plain `WHERE b = ?` will seq scan. Add a
second index on `(b)` or reorder.

### Q: When would you choose a BRIN over a B+tree?

When the table is append-only, sorted on disk by the indexed column
(typically a `time` column), and the queries are range scans. BRIN
indexes are tiny (KB to MB) where a B+tree would be gigabytes. The
moment data is heap-randomized, BRIN loses all pruning power.

### Q: How do you decide whether to use a covering index or just
two separate indexes?

A covering index wins when the same query is the hot path and
the projected columns are stable. Two indexes win when the
projection changes between queries or the projected column set is
too wide. Covering indexes bloat the leaf; an `INCLUDE` list of 10
wide columns on a 100M-row table is real disk space and real write
cost.

## References

- PostgreSQL Documentation, "[Index Types](https://www.postgresql.org/docs/current/indexes-types.html)" — B-tree, Hash, GIN, GiST, BRIN, SP-GiST with operational notes.
- PostgreSQL Documentation, "[Indexes](https://www.postgresql.org/docs/current/indexes.html)" — introduction, partial indexes, expression indexes, and index-only scan preconditions.
- PostgreSQL Documentation, "[Index-Only Scans](https://www.postgresql.org/docs/current/indexes-index-only-scans.html)" — the visibility map precondition and the `Heap Fetches` explain output.
- Markus Winand, *Use The Index, Luke!*, "[The Where Clause](https://use-the-index-luke.com/sql/where-clause)" — the canonical statement of the "index the WHERE, not the SELECT" principle, with worked examples.
- Markus Winand, *SQL Performance Explained*, [use-the-index-luke.com](https://use-the-index-luke.com/) — the book form of the site. Chapters on concatenation, range, and partial indexes are required reading for any engineer touching a database.
- PostgreSQL Documentation, "[BRIN Indexes](https://www.postgresql.org/docs/current/brin.html)" — block-range index internals and the `pages_per_range` knob.
- PostgreSQL Documentation, "[GIN Indexes](https://www.postgresql.org/docs/current/gin-intro.html)" and "[GiST Indexes](https://www.postgresql.org/docs/current/gist-intro.html)" — fastupdate, pending lists, and lossy operators.

## Related Topics

- [Indexing: B+tree](./indexing/b-plus-tree.md) — the structure this page assumes.
- [Indexing: Covering Index](./indexing/covering-index.md) — `INCLUDE` columns in depth.
- [Indexing: Composite Index](./indexing/composite-index.md) — column ordering rules.
- [Query Optimization Deep Dive](./query-optimization-deep.md) — how the planner picks among the indexes described here.
- [Internals: LSM Trees](./internals/lsm-trees.md) — the alternative to B+trees used by RocksDB, Cassandra, and DynamoDB.
