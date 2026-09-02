# Online Schema Change

Online schema change (OSC) is the practice of altering a database's schema (adding columns, indexes, changing types) while the database continues to serve traffic. The naive approach — `ALTER TABLE` with an exclusive lock — blocks all writes for the duration of the change, which can be hours for large tables. This page covers the copy-back approach (pt-online-schema-change, gh-ost), the native online DDL (MySQL 8, PostgreSQL 11+), and the consistency challenges.

## Why Online Schema Change Matters

A naive `ALTER TABLE ADD COLUMN` on a 100 GB table in MySQL can take hours, during which the table is locked and writes fail. For a production database serving user traffic, this is unacceptable.

Online schema change techniques keep the table writable during the migration. The cost is more complex logic and longer total migration time (typically 2-5× the naive time), but the application stays online.

## The Copy-Back Approach

The classic algorithm (used by pt-online-schema-change and gh-ost):

1. Create a "shadow" table with the new schema:
   ```sql
   CREATE TABLE _orders_new LIKE orders;
   ALTER TABLE _orders_new ADD COLUMN new_col INT;
   ```

2. Install triggers on the original table that capture INSERT/UPDATE/DELETE and apply the changes to the shadow table:
   ```sql
   CREATE TRIGGER orders_ai AFTER INSERT ON orders
   FOR EACH ROW INSERT INTO _orders_new (...) VALUES (NEW.id, NEW.customer_id, ..., NEW.new_col);
   -- similar for UPDATE and DELETE
   ```

3. Copy data from original to shadow in chunks:
   ```sql
   INSERT INTO _orders_new (id, customer_id, ...) SELECT id, customer_id, NULL
   FROM orders WHERE id > X AND id <= X + 1000;
   ```
   This processes 1000 rows at a time, sleeping between chunks to avoid overloading the DB.

4. Once the copy catches up to the present (no lag), atomically rename:
   ```sql
   RENAME TABLE orders TO _orders_old, _orders_new TO orders;
   DROP TABLE _orders_old;
   ```

The RENAME is atomic in MySQL; it takes <1 second. After the rename, the shadow table is the new "live" table.

## pt-online-schema-change (Percona)

pt-online-schema-change (pt-osc) is Percona's tool, part of `percona-toolkit`. It implements the copy-back approach with triggers.

Pros:
- Mature (10+ years).
- Handles most ALTER TABLE operations.
- Throttles based on replication lag (avoids overwhelming replicas).

Cons:
- Uses triggers, which add 20-50% overhead to writes during the migration.
- The shadow table's triggers fire on every write, slowing production.
- Cannot be paused (a failed migration requires manual cleanup).

## gh-ost (GitHub Online Schema Change)

GitHub developed gh-ost in 2016 to avoid the trigger overhead. It uses a different approach:

1. Create a shadow table (same as pt-osc).
2. **No triggers**: instead, gh-ost connects to the database as a replication replica (a "binlog applier").
3. The original table's binlog events are read; the events are applied to the shadow table.
4. gh-ost also does the chunked copy for historical data.

Pros:
- No trigger overhead (writes to the original table are unaffected).
- Can be paused (the binlog stream just stops; resumed when ready).
- No need for triggers; works on databases that don't support them.

Cons:
- Requires binlog (the DB must have `binlog_format=ROW`).
- The migration is slower than pt-osc (extra binlog read step).
- More complex setup.

For most production MySQL deployments, gh-ost is the standard.

## Native Online DDL

MySQL 8 (2018) added significant online DDL improvements:
- `ALGORITHM=INPLACE`: the ALTER is done in-place, without a shadow table.
- `ALGORITHM=INSTANT`: the ALTER is instant (only metadata change).

```sql
ALTER TABLE orders ADD COLUMN new_col INT, ALGORITHM=INSTANT;
-- Returns in <1 second, no table copy.
```

`INSTANT` works for:
- Adding columns at the end of the table.
- Dropping columns (MySQL 8.0.29+).
- Setting default values.

It doesn't work for:
- Adding an index (requires `INPLACE`).
- Changing a column's type (requires `COPY`).

PostgreSQL 11+ has similar instant capabilities for certain ALTER operations:
- Adding a column with a default value (12+).
- Adding a NOT NULL constraint that's already enforced (12+).

## The Consistency Challenge

During a long migration, the original table is being written to. The shadow table must stay in sync:

- **Triggers (pt-osc)**: every write to the original triggers a write to the shadow. Strong consistency, but high overhead.
- **Binlog applier (gh-ost)**: every write to the original is in the binlog; gh-ost reads and applies. Eventual consistency, no overhead.
- **CDC (e.g., Debezium)**: similar to gh-ost but uses an external CDC pipeline.

The trade-off: triggers give strong consistency but high overhead; binlog gives eventual consistency but low overhead. For most production migrations, eventual consistency (gh-ost) is acceptable.

## Throttling

Online schema changes must not saturate the database:

- **Replication lag**: if a replica is more than N seconds behind, the migration pauses. Avoids overwhelming replicas.
- **CPU**: if the DB's CPU is > 80%, the migration pauses. Avoids starving foreground queries.
- **Network bandwidth**: limit the migration's bandwidth to avoid saturating the DB's network.

Both pt-osc and gh-ost have throttling options. The standard configuration:
- Max 100 rows copied per second (slow but safe).
- Pause if replica lag > 30 seconds.
- Pause if CPU > 70%.

## Schema Migration in Distributed Databases

Distributed databases (CockroachDB, Spanner, TiDB) handle schema changes differently:

- The schema is replicated across the cluster's metadata store (etcd for TiDB, the cluster's internal metadata for Spanner, the Raft group for CockroachDB).
- A schema change is broadcast to all nodes; each node starts using the new schema for new queries.
- During the migration, both old and new schema versions are accepted. This is "schema versioning" — a node can serve queries with either schema.

This makes schema changes truly online, but with some constraints:
- Adding a column is fast (the new column is NULL for existing rows).
- Dropping a column is slow (the column is logically dropped but physically removed later).
- Changing a column's type requires a full table rewrite (most restrictive).

CockroachDB's schema changes are documented as the "online schema change" algorithm from the F1 paper (Google 2013).

## Common Pitfalls

1. **Forgetting that `INSTANT` ALTER has restrictions.** It only works for adding columns at the end of the table. Adding a column in the middle requires `INPLACE` (slower) or `COPY` (full table rewrite).

2. **Trigger overhead during pt-osc migrations.** A migration that takes hours means production traffic pays the trigger overhead for hours. Use gh-ost for production.

3. **Not monitoring replication lag.** A migration that pushes the replica too far behind causes the replica to fall out of sync. Throttle aggressively.

4. **Forgetting to drop the shadow table on failure.** A failed migration leaves the shadow table and triggers. Clean up before retrying.

5. **Forgetting that schema changes can break applications.** A column rename breaks queries that use the old name. Coordinate with the application deployment.

6. **Assuming ALTER is atomic.** It's not — the table is briefly unavailable during the RENAME step. For high-traffic tables, schedule the RENAME for a low-traffic window.

## References

- [Percona Toolkit: pt-online-schema-change documentation](https://docs.percona.com/percona-toolkit/pt-online-schema-change.html)
- [GitHub gh-ost: Online Schema Change for MySQL](https://github.com/github/gh-ost)
- [MySQL 8.0: Online DDL Operations](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html)
- [PostgreSQL: Altering Tables Online](https://www.postgresql.org/docs/current/sql-altertable.html)
- [CockroachDB: Online Schema Changes](https://www.cockroachlabs.com/docs/stable/online-schema-changes.html)
- Ian G. et al., "[F1: A Distributed SQL Database That Scales](http://research.google.com/pubs/pub41344.pdf)" (VLDB 2013) — Google's online schema change algorithm
- [Shlomi Noach: gh-ost design](https://github.com/github/gh-ost/blob/master/doc/why-trigger-issues.md)
- [LWN: Online schema migration (2018)](https://lwn.net/Articles/768260/)
