# PostgreSQL Advanced Features

## JSONB

Binary JSON with indexing support:

```json
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

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)
- [Use The Index, Luke](https://use-the-index-luke.com/)
