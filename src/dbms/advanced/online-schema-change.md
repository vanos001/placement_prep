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

## Online Index Builds and the Lock Spectrum

The native-DDL summary above hides a spectrum. Every engine's "online" story is really an answer to two questions: which moments still take a blocking lock, and what happens when those moments queue behind long-running transactions. Index builds are the case study — the operation you run most often on a live table — and the three big engines solve it three different ways.

### PostgreSQL: CREATE INDEX CONCURRENTLY

`CREATE INDEX CONCURRENTLY` builds an index without blocking writes by paying with time. The index is entered into the system catalogs as an "invalid" index in one transaction, then two table scans happen in two more transactions; before each scan, the build must wait for existing transactions that have modified the table to terminate. After the second scan it must additionally wait out every transaction whose snapshot predates that scan — including transactions from concurrent index builds on other tables, if the indexes involved are partial or have columns that are not simple column references — before finally marking the index valid. Two scans are the minimum for a no-lock build: the first captures a snapshot of the table, the second picks up rows that changed while it ran, and the waits before each scan are what bound what the second scan has to catch up.

Three consequences. **Failure is sticky**: if a problem arises while scanning — a deadlock, or a uniqueness violation while building a unique index — the command fails but leaves behind an INVALID index, which queries ignore ("it might be incomplete") but which still consumes update overhead on every write; `\d` reports it as INVALID, and the recommended recovery is to drop it and run `CREATE INDEX CONCURRENTLY` again. **It cannot run inside a transaction block** (a regular `CREATE INDEX` can) — the multi-transaction dance above is the reason. And **unique builds enforce early**: the uniqueness constraint is already being checked against other transactions from the moment the second scan begins, so applications can see uniqueness violations before the index is usable — or even when the build ultimately fails.

The production stall: the build waits for every transaction that could potentially modify or use the table. A day-old reporting query, an idle `BEGIN` in a console session, or an abandoned prepared transaction parks the build at its wait phase indefinitely — the table keeps taking writes that the second scan will have to chase, and the new index is unusable until the old transactions die. When a concurrent build looks stuck, look for the oldest transaction on the table, not for the index builder.

### InnoDB: ALGORITHM, LOCK, the Online Log, and the MDL Stall

`ALTER TABLE` on InnoDB picks one of three algorithms: `COPY` rebuilds the table row by row and permits no concurrent DML; `INPLACE` avoids the copy but may still rebuild in place, taking an exclusive metadata lock briefly during the preparation and execution phases while typically permitting concurrent DML; `INSTANT` (8.0.12+) modifies metadata in the data dictionary only. The `LOCK` clause is the concurrency contract you request: `LOCK=NONE` permits queries and DML, `LOCK=SHARED` permits queries only, `LOCK=EXCLUSIVE` blocks both, and if the requested level is not available the operation halts immediately — which is exactly why you should spell out `, ALGORITHM=INPLACE, LOCK=NONE` on hot tables rather than letting a "safe-looking" statement silently degrade to a locking path.

An online index build reads the table and fills the new index while DML continues; the concurrent changes are recorded in a temporary online log — one per index being created or table being altered — and applied to the new index as the build drains it. The log is bounded by `innodb_online_alter_log_max_size` (default 134217728 bytes = 128 MiB); if concurrent DML overflows it, the ALTER fails with `DB_ONLINE_LOG_TOO_BIG` and uncommitted concurrent DML is rolled back. Raising the limit buys headroom at the cost of a longer final apply window — the locked phase at the end when the log drains. And DML wins at the end: if concurrent transactions wrote values the new definition rejects (a duplicate while a unique index builds, a NULL while a primary key is added), the operation fails at the very end, the changes made by concurrent DML take precedence, and the ALTER is effectively rolled back.

`INSTANT ADD COLUMN` is the flagship: metadata-only, no rebuild, since 8.0.12; any position in the table, plus instant `DROP COLUMN`, since 8.0.29. Limits worth memorizing: no INSTANT on `ROW_FORMAT=COMPRESSED` tables, tables with a FULLTEXT index, or the data-dictionary tablespace; MySQL checks the max row size when adding; each instant add/drop consumes a row version and the limit is 64 versions per table (`INFORMATION_SCHEMA.INNODB_TABLES.TOTAL_ROW_VERSIONS`, reset to 0 by a table-rebuilding ALTER or `OPTIMIZE TABLE`) — after which INSTANT is rejected and a COPY/INPLACE rebuild is required.

The failure mode that gets people is the brief exclusive metadata lock at the start and end of an otherwise-online DDL. The DDL must wait for every transaction touching the table to finish, and while it waits, every subsequent query on that table queues behind it — the wait is not brief if the blocker isn't leaving. `lock_wait_timeout` (default 31536000 seconds — one year) governs how long the DDL waits before giving up with `ER_LOCK_WAIT_TIMEOUT`, so a single uncommitted `autocommit=0` session can hold a hot table hostage:

```text
t=0     session A opens a transaction on orders, then idles
t=10:00 ALTER TABLE orders ADD INDEX ..., ALGORITHM=INPLACE starts;
        it needs a brief exclusive metadata lock and waits for session A
t=10:00 every new SELECT on orders queues behind the pending exclusive
        MDL — latency climbs, connection pools exhaust
t=14:00 performance_schema.metadata_locks identifies session A;
        killing it drains the queue
```

The defense is operational: keep transactions short, set a sane `lock_wait_timeout` on DDL sessions, and check `performance_schema.metadata_locks` (it shows which sessions hold locks and which are blocked) before blaming InnoDB.

### SQL Server: ONLINE = ON and the Temp Mapping Index

SQL Server's `ONLINE = ON` index build works on source and target structures at once: user INSERT/UPDATE/DELETE on the source are applied to both the preexisting indexes and the target being built; the target is marked write-only and isn't used until the operation commits. For operations that create, drop, or rebuild a clustered index, the engine also maintains a temporary mapping index, which concurrent transactions use to determine which records to clean up in the new indexes when source rows are updated or deleted. The operation runs in three phases — preparation (a snapshot of the table is defined via row versioning; concurrent writes are blocked for a short period), build (data is scanned, sorted, and bulk-loaded into the target while DML applies to both), and final (all uncommitted write transactions must complete first; a schema-modification lock replaces the source with the target for a short window). Same lesson as InnoDB: online means concurrent DML with brief boundary locks, not lock-free.

Two SQL Server gotchas. `ONLINE = ON` is not available in every edition — the documentation's own example says "Set ONLINE = OFF to execute this example on editions other than Enterprise Edition", which quietly turns a planned online operation into a blocking one if you're not on the right SKU. And clustered index operations on tables with `image`/`ntext`/`text` LOB columns must run offline. Since the resumable option (`RESUMABLE = ON`), an interrupted build can pause and resume after failures or disk exhaustion instead of restarting — the same capability gh-ost gives MySQL.

### Verification and the Failure Protocol

Whatever the mechanism, a migration is not done until the data is verified:

1. **Count and checksum.** Compare row counts between the source and the shadow structure (or between primary and replica); per-chunk checksums catch silent divergence that counts miss.
2. **Check the index state.** PostgreSQL: an INVALID leftover index is ignored by queries but taxes every write — drop it and rebuild. MySQL: a failed online DDL rolls back, but a repeated failure usually means the workload conflicts with the new definition (log overflow, or DML producing values the new definition rejects).
3. **Fall back to the external tools** when the native path can't give you the guarantees you need: [pt-online-schema-change](#pt-online-schema-change-percona) and [gh-ost](#gh-ost-github-online-schema-change) take over for operations that can't run INPLACE/INSTANT (type changes force COPY), for tables where even the brief MDL window at the DDL boundaries is unacceptable, and for busy tables that would overflow the online log.

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
- [PostgreSQL: CREATE INDEX](https://www.postgresql.org/docs/current/sql-createindex.html) — the CONCURRENTLY two-scan/wait-phase description, INVALID-index-on-failure semantics, and the transaction-block prohibition.
- [MySQL 8.0: ALTER TABLE Statement](https://dev.mysql.com/doc/refman/8.0/en/alter-table.html) — COPY/INPLACE/INSTANT algorithm semantics and the brief exclusive metadata lock in the preparation/execution phases.
- [MySQL 8.0: Online DDL Performance and Concurrency](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-performance.html) — `LOCK=NONE/SHARED/DEFAULT/EXCLUSIVE` clause semantics.
- [MySQL 8.0: Online DDL Failure Conditions](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-failure-conditions.html) — the exclusive-lock wait at the initial/final phases, `DB_ONLINE_LOG_TOO_BIG`, and the DML-takes-precedence rollback.
- [MySQL 8.0: InnoDB Startup Options and System Variables](https://dev.mysql.com/doc/refman/8.0/en/innodb-parameters.html) — `innodb_online_alter_log_max_size` (default 128 MiB) and the overflow behavior.
- [MySQL 8.0: Metadata Locking](https://dev.mysql.com/doc/refman/8.0/en/metadata-locking.html) — MDLs held to transaction end, DDL blocked until release, and the `performance_schema.metadata_locks` table.
- [MySQL 8.0: Server System Variables](https://dev.mysql.com/doc/refman/8.0/en/server-system-variables.html) — `lock_wait_timeout` (default 31536000 s, `ER_LOCK_WAIT_TIMEOUT`).
- [Microsoft: Perform index operations online](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/perform-index-operations-online) and [Microsoft: How online index operations work](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/how-online-index-operations-work) — source/target/temporary-mapping-index structures, the three phases with their lock modes, and the edition note.
- [Microsoft: Guidelines for online index operations](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/guidelines-for-online-index-operations) — LOB restrictions and resumable (`RESUMABLE = ON`) index operations.
