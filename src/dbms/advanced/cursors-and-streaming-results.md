# Cursors and Streaming Results: Reading 10M Rows Without OOM

`SELECT * FROM events` is not one operation but a negotiation about *who buffers what*. The default — run the query to completion, ship the whole result set, hold it in client memory — turns a simple read into an OOM crash the moment the result outgrows the client heap. Cursors let the client pull rows in batches while the server keeps execution state alive, at the price of held snapshots and occupied connections. This page covers the cursor model, the driver-level batching that silently defeats it, the wire protocol underneath, keyset pagination as the stateless alternative, `COPY` as the bulk escape hatch, and the set-based rewrites that usually beat row-by-row processing outright.

## Materialized Results vs Streaming: The Memory Math

Exporting a 10M-row result set at ~200 bytes per row — three strategies, three memory profiles:

| Strategy | Server memory | Client memory | Shape |
|----------|---------------|---------------|-------|
| Fully materialized (most drivers' default) | result buffer, freed early | **~2 GB** held to the end | one long transfer, then processing |
| Cursor with fetch batching (batch = 1,000) | per-batch buffer ~200 KB | ~200 KB working set | interleaved compute/transfer |
| `COPY` to stdout | sequential stream buffer | stream buffer only | fastest bulk path, no random access |

The 2 GB is *per concurrent request* — ten simultaneous exports is an OOM, not ten exports. Batching converts the working set from `result_size` to `batch_size + accumulator`. Note what batching does not change: total bytes transferred and rows scanned. It is a memory lever, not a work lever.

## The Cursor Model: DECLARE, OPEN, FETCH, CLOSE

The lifecycle is four verbs: `DECLARE` names the query, `OPEN` starts execution (in PostgreSQL's SQL-level interface, `DECLARE` opens it), `FETCH` retrieves rows relative to the cursor position, `CLOSE` releases it. PostgreSQL's reference states the purpose exactly: cursors "can be used to retrieve a small number of rows at a time out of a larger query". Three semantic axes, verbatim from the same page:

- **Sensitivity.** "Cursor sensitivity determines whether changes to the data underlying the cursor, done in the same transaction, after the cursor has been declared, are visible in the cursor. INSENSITIVE means they are not visible, ASENSITIVE means the behavior is implementation-dependent. A third behavior, SENSITIVE, meaning that such changes are visible in the cursor, is not available in PostgreSQL. In PostgreSQL, all cursors are insensitive." So: no, you cannot see your own writes through a PG cursor.
- **Scrollability.** Forward-only vs `SCROLL`, which permits `FETCH PRIOR`, `ABSOLUTE`, `BACKWARD`. Scrolling costs state — the engine must retain enough result to walk backwards — which is why "The SCROLL option should be specified when defining a cursor that will be used to fetch backwards."
- **Holdability.** `WITHOUT HOLD` (default) dies with its transaction; `WITH HOLD` survives commit — where it gets expensive, next section.

## WITH HOLD Cursors and Transaction Boundaries

A held cursor holds two different things, and confusing them is a classic senior-level error.

**A snapshot.** A regular cursor's reads run under its declaring transaction's MVCC snapshot. That snapshot's `xmin` pins the vacuum horizon: dead tuples newer than it cannot be cleaned, on *any* table, until the transaction ends. A "quick 20-minute analytics read" holding a cursor on a busy OLTP database blocks vacuum globally — the bloat mechanism is in [MVCC Internals](./mvcc-internals.md). A long-lived cursor *is* a long-running transaction.

**A materialized result.** PostgreSQL solves hold-over-commit by copying. Verbatim: "If WITH HOLD is specified and the transaction that created the cursor successfully commits, the cursor can continue to be accessed by subsequent transactions in the same session... In the current implementation, the rows represented by a held cursor are copied into a temporary file or memory area so that they remain available for subsequent transactions." So `WITH HOLD` releases the snapshot at commit (vacuum unblocked) but materializes the remaining result at that moment — a 10M-row held cursor writes ~2 GB of temp data at `COMMIT`. Restriction worth quoting: "WITH HOLD may not be specified when the query includes FOR UPDATE or FOR SHARE."

Oracle takes the opposite trade: keep fetching across commits, and if the fetch outlasts undo retention the read fails with ORA-01555 (below). Either the snapshot is pinned, the result is materialized, or the read can fail — there is no free lunch.

## Fetch Batching in Drivers: Where Good Intentions Go to Die

Cursors are engine-side; whether *your* process streams is decided by the driver, and each driver has its own betrayal mode.

**pgJDBC.** "By default, the driver collects all the results for the query at once." `setFetchSize(n)` switches to cursor mode only if preconditions hold; the one that catches everyone: "The Connection must not be in autocommit mode. The backend closes cursors at the end of transactions, so in autocommit mode the backend will have closed the cursor before anything can be fetched from it." On an autocommit connection `setFetchSize(1000)` is a silent no-op and the OOM is back. Fix: `setAutoCommit(false)` before creating the statement.

**psycopg2.** The plain `cursor()` is client-side: "the Psycopg cursor usually fetches all the records returned by the backend, transferring them to the client process." Streaming needs a *named* cursor: "Server side cursor are created in PostgreSQL using the DECLARE command and subsequently handled using MOVE, FETCH and CLOSE commands. Psycopg wraps the database server side cursor in named cursors." Two sharp edges from the same docs: iteration batches are `itersize`, "the default value of 2000"; and "Named cursors are usually created WITHOUT HOLD... It is extremely important to always close() such cursors, otherwise they will continue to hold server-side resources until the connection will be eventually closed."

**MySQL Connector/Python.** MySQL has no protocol-level SQL cursor, so the choice is buffered vs unbuffered per cursor. "After executing a query, a MySQLCursorBuffered cursor fetches the entire result set from the server and buffers the rows." The unbuffered default streams but occupies the connection: "For nonbuffered cursors, rows are not fetched from the server until a row-fetching method is called. In this case, you must be sure to fetch all rows of the result set before executing any other statements on the same connection, or an InternalError (Unread result found) exception will be raised."

**MySQL Connector/J.** The famous quirk, verbatim: "The combination of a forward-only, read-only result set, with a fetch size of Integer.MIN_VALUE serves as a signal to the driver to stream result sets row-by-row." Positive fetch sizes mean nothing without the cursor-fetch mode: "This can be done by setting the connection property useCursorFetch to true, and then calling setFetchSize(int)." The same section documents streaming's costs: "You must read all of the rows in the result set (or close it) before you can issue any other queries on the connection, or an exception will be thrown," and "The earliest the locks these statements hold can be released... is when the statement completes" — a slow consumer holds its locks for the whole scan. Memorize one more line: "MySQL does not support SQL cursors, and the JDBC driver does not emulate them, so setCursorName() has no effect."

```java
// The two MySQL streaming modes
stmt = conn.createStatement(ResultSet.TYPE_FORWARD_ONLY, ResultSet.CONCUR_READ_ONLY);
stmt.setFetchSize(Integer.MIN_VALUE);        // stream row-by-row, connection occupied

// or:
conn = DriverManager.getConnection("jdbc:mysql://host/db?useCursorFetch=true", u, p);
stmt.setFetchSize(500);                      // server-side fetch batches of 500
```

## What the Wire Actually Carries

**PostgreSQL — extended-query portals.** In the extended protocol, `Bind` produces a *portal*: "Once a portal exists, it can be executed using an Execute message. The Execute message specifies the portal name (empty string denotes the unnamed portal) and a maximum result-row count (zero meaning 'fetch all rows')." A portal is a named, partially-consumed execution; a fetch-size-limited read is repeated `Execute` messages against one portal, each leaving it *suspended* and resumable. The docs link the layers: "Named portals can also be created and accessed at the SQL command level, using DECLARE CURSOR and FETCH." Portals are per-connection state — this is what "the connection is busy" means.

**MySQL — one row per packet.** The text protocol sends a column-definitions part, then rows: "A Text Resultset is a possible COM_QUERY Response... Each row is a packet, too." The server pushes rows as fast as the client reads them, and no other statement can be interleaved on that connection while row packets are outstanding — the wire-level reason for Connector/Python's "Unread result found" error.

**SQL Server — MARS.** Per Microsoft's docs: "MARS enables the interleaved execution of multiple requests within a single connection... Note, however, that MARS is defined in terms of interleaving, not in terms of parallel execution." Interleaving happens at *yield points* — row-returning statements (`SELECT`, `FETCH`, `RECEIVE`) — so two open result sets take turns on one connection. It removes the "connection occupied by a streaming read" failure mode without adding parallelism.

## Keyset Pagination: Streaming Without Cursors

Every cursor pins server state — snapshot, plan, position. Keyset ("seek") pagination streams through a table holding *none*: the query itself is position-aware. This is the SQL half of the API design in [API Pagination](../../backend/api/api-pagination.md); here the focus is why it is the database's favorite cursor.

Why `OFFSET` degrades: `LIMIT 50 OFFSET 900000` cannot teleport — the engine walks the index in order, counting and discarding 900,000 rows, then returns 50. The discard work is linear in the offset. Measured locally (SQLite 3.53.1, file-backed DB, 1M rows, `id INTEGER PRIMARY KEY`, `LIMIT 50`, best of 5 — an illustration of the shape, not a universal benchmark):

| offset | 0 | 100,000 | 250,000 | 500,000 | 900,000 |
|--------|---|---------|---------|---------|---------|
| latency | 0.02 ms | 2.90 ms | 7.55 ms | 14.55 ms | 26.58 ms |

`EXPLAIN QUERY PLAN` shows the identical `SCAN events` plan line for every offset — the plan looks free while skipped-row work grows linearly. The keyset form replaces counting with seeking:

```sql
SELECT id, ts, payload FROM events ORDER BY id LIMIT 50;              -- page 1
SELECT id, ts, payload FROM events WHERE id > :last_id ORDER BY id LIMIT 50;
```

Its plan: `SEARCH events USING INTEGER PRIMARY KEY (rowid>?)` — a seek, measured 0.02 ms at offset 900,000. Flat at any depth, and no state survives the query, so paging composes with pools, retries, and failover.

Two mechanics make it production-grade:

- **Composite keys and tie-breaking.** Ordering by a non-unique column alone loses or duplicates rows at equal values. The resume predicate must span the full ordering: `WHERE (ts, id) < (:last_ts, :last_id) ORDER BY ts DESC, id DESC`, backed by the composite index `(ts, id)`. SQLite handles row-value comparisons (the query above ran on 3.53.1); PostgreSQL and MySQL 8.0+ do too, and the fallback is the expanded inequality pair — derivation in the API pagination page.
- **Do not emulate offsets with window functions.** `ROW_NUMBER() OVER (ORDER BY id) ... WHERE rn > 900000` must number *every* row before filtering — a full walk per page. Same DB: 592.59 ms vs 0.02 ms for the true keyset; the plan (`CO-ROUTINE page`) shows the window computation feeding the filter.

## COPY: The Bulk Escape Hatch

When the goal is "move the whole result, fast, no per-row application logic", cursors are the wrong tool. PostgreSQL's `COPY` "moves data between PostgreSQL tables and standard file-system files", and its TO direction accepts a query: `COPY (SELECT * FROM events WHERE ts < :cutoff) TO STDOUT WITH (FORMAT csv)`. Client libraries turn `TO STDOUT` into a streamed pipe (psql's `\copy`, psycopg2's `copy_expert()`, pgJDBC's `CopyManager`) — the result never materializes as a query result at all. Choose `COPY` when the consumer is a stream or file (analytics handoff, staging, backup-before-migrate); choose cursors when the consumer is application logic that needs typed rows incrementally. MySQL's analogue is `SELECT ... INTO OUTFILE` (server-side file); the in-application equivalent is Connector/J row-by-row streaming, at a slower serialization path.

## Snapshot Longevity: Cursor Stability and ORA-01555

A streaming read stretches the span between first and last fetch, and MVCC must keep every version that snapshot needs alive for the whole span. Oracle pays with undo, and when a long fetch needs overwritten undo it fails — verbatim from Oracle's error reference: "ORA-01555 snapshot too old: rollback segment number string with name 'string' too small. Cause: rollback records needed by a reader for consistent read are overwritten by other writers. Action: If in Automatic Undo Management mode, increase undo_retention setting." The general horizon mechanism and its bloat are in [MVCC Internals](./mvcc-internals.md) and [MVCC Garbage Collection](./mvcc-garbage-collection.md). The interview framing: *cursor stability* is not an isolation level — it is the guarantee that rows already fetched do not change under you, which each engine provides via its snapshot; what varies is how long the engine can keep that snapshot's data available. Fetch-across-commit on Oracle trades snapshot longevity for ORA-01555 risk; PostgreSQL's `WITH HOLD` trades it for temp-file materialization.

## The Set-Based Alternative

Often the honest answer to "how do I stream 10M rows through my app?" is "don't — move the work to the data". Row-by-row loops pay statement-level costs on every iteration: parse/plan or round-trip, plus per-row MVCC and WAL bookkeeping. Measured locally (SQLite 3.53.1, in-process — no network round-trips, so this *understates* the client-server case): applying 10,000 adjustments to 100,000 accounts, identical results:

- row-by-row loop, 10,000 `UPDATE` statements in one transaction: **15 ms**
- single `UPDATE acc SET balance = balance + a.delta FROM adjustments AS a WHERE acc.id = a.aid`: **4.9 ms**

Three times slower with zero round-trips; multiply by per-statement network latency and lock duration on a real server and the loop explodes. SQLite's docs describe the set-based form: "UPDATE-FROM is supported beginning in SQLite version 3.33.0 (2020-08-14)... The SQLite implementation strives to be compatible with PostgreSQL" — so the rewrite ports across PostgreSQL, SQL Server, and modern SQLite. The correlated-scalar-subquery `UPDATE` is the same disease disguised: the plan node literally reads `CORRELATED SCALAR SUBQUERY`, one lookup per row, degenerating to a scan per row if the predicate is unindexed. The planner-side story is in [Query Optimization Deep Dive](../query-optimization-deep.md).

## Interview Problems

### Problem 1 — Export 50M rows without OOM

*Given:* a nightly job selects ~50M rows (~10 GB serialized) from PostgreSQL and writes JSON lines to object storage; the worker was OOM-killed. Walk the fix space.

*Worked answer:* (1) Never materialize: pgJDBC needs `autoCommit=false` **and** `setFetchSize` (else silent full fetch); psycopg2 needs a named server-side cursor, not the default client-side one — client memory drops from ~10 GB to one batch. (2) If the consumer is a file, skip the app: `COPY (SELECT ...) TO STDOUT` streams server-serialized text straight to the upload pipe. (3) Batch 5–50k rows, stream into a compressed writer so the accumulator stays flat. (4) Mind the snapshot: a 40-minute read pins the vacuum horizon for 40 minutes — schedule off-peak or walk key ranges in separate short transactions. `WITH HOLD` would move 10 GB into temp files at commit — the wrong cure. Junior answer: "use fetchSize". Senior answer: "pick the streaming primitive for the consumer, and account for the snapshot's cost."

### Problem 2 — Page through a hot table without missing or duplicating rows

*Given:* a backfill walks a busy `orders` table with `ORDER BY created_at, id` keyset pagination. The reviewer says "updates will break this". Will they?

*Worked answer:* Keyset over one repeatable-read transaction is exactly-once — but that long transaction is a vacuum hazard, so real walks cross transactions. What matters is the key: rows inserted after the cursor are correctly "past the frontier" if the key is append-like; rows updated in non-key columns are invisible (fine for a backfill); an update that *changes* a key column on a not-yet-visited row can cause a skip. Fixes: make the key immutable (`id`, or `created_at` set once at insert); drive the walk off a monotonic channel (`updated_at` frontier, CDC, outbox) if updates must be seen; never use `OFFSET` + "stable sort" — it is only correct under a frozen snapshot and pays the linear skip cost. Tie-breaking with unique `id` is non-negotiable: `created_at` collisions otherwise duplicate or drop rows.

### Problem 3 — "We added setFetchSize and it got slower"

*Given:* a MySQL reporting job via Connector/J. A developer "fixed" an OOM with `setFetchSize(1000)` — memory still blew up; `setFetchSize(Integer.MIN_VALUE)` flattened memory but the job and everything sharing the connection slowed down. Diagnose.

*Worked answer:* Two silent mode changes. First, a positive fetch size alone does nothing on MySQL: the driver streams only with forward-only + read-only + `Integer.MIN_VALUE`, or `useCursorFetch=true` plus a positive size — without one of those it still buffers the whole ResultSet, hence no memory change. Second, the row-by-row mode keeps the connection fully occupied: no other query until the set is drained or closed, and locks held until the statement completes — so the streaming read serializes everything on that connection and holds locks for the scan's duration. Correct moves: `useCursorFetch=true` with a real batch size, move the export to `SELECT ... INTO OUTFILE`, or run the read on its own connection/replica so occupation and lock-holding cannot bleed into OLTP traffic.

## Key Takeaways

- Cursors trade client memory for server state: batched fetching turns a ~2 GB client buffer into one batch's working set, but the snapshot, plan, and position it pins are costs someone pays — usually vacuum.
- PostgreSQL semantics, per its docs: all cursors are insensitive; SCROLL must be declared for backward fetches; `WITH HOLD` survives commit by copying "the rows represented by a held cursor" into "a temporary file or memory area" — snapshot released, result materialized.
- Driver gotchas decide streaming in practice: pgJDBC silently falls back under autocommit; psycopg2 streams only via named cursors (`itersize` default 2000, always close them); Connector/J needs `Integer.MIN_VALUE` or `useCursorFetch=true`; Connector/Python streams by default but raises `InternalError (Unread result found)` if the result is not drained first.
- On the wire: PG portals are consumed by `Execute` messages with a max-row count; MySQL's text resultset sends each row as a packet on an otherwise-busy connection; MARS interleaves (not parallelizes) result sets on one SQL Server connection.
- Keyset pagination is the stateless cursor: `WHERE (ts, id) < (:last_ts, :last_id)` with the matching composite index seeks instead of skipping — flat latency at any depth, while `OFFSET` grows linearly (0.02 → 26.6 ms at 900k in the local experiment) and `ROW_NUMBER()` emulation is worse still (592 ms).
- `COPY ... TO STDOUT` is the bulk escape hatch — no query-result materialization, fastest serialization path — whenever the consumer is a stream or file.
- Long-running reads are MVCC events: pinned snapshots block vacuum (PostgreSQL) or risk ORA-01555 ("rollback records needed by a reader for consistent read are overwritten by other writers") in Oracle.
- Row-by-row loops pay per-statement costs thousands of times: the `UPDATE ... FROM` rewrite measured 4.9 ms vs 15 ms even in-process with no network — the gap widens with every round-trip.

## References

1. PostgreSQL Documentation, "[DECLARE](https://www.postgresql.org/docs/current/sql-declare.html)" — sensitivity ("In PostgreSQL, all cursors are insensitive"), SCROLL, WITH HOLD materialization, FOR UPDATE restriction. Fetched this session (HTTP 200).
2. PostgreSQL Documentation, "[FETCH](https://www.postgresql.org/docs/current/sql-fetch.html)" — cursor position semantics, FETCH forms. Fetched this session (HTTP 200).
3. PostgreSQL Documentation, "[Extended Query Protocol flow](https://www.postgresql.org/docs/current/protocol-flow.html)" — portal lifecycle, "maximum result-row count (zero meaning 'fetch all rows')", named portals via DECLARE CURSOR and FETCH. Fetched this session (HTTP 200).
4. PostgreSQL Documentation, "[COPY](https://www.postgresql.org/docs/current/sql-copy.html)" — "COPY moves data between PostgreSQL tables and standard file-system files"; `COPY (query) TO STDOUT`. Fetched this session (HTTP 200).
5. PostgreSQL JDBC Driver Documentation, "[Issuing a Query and Processing the Result](https://jdbc.postgresql.org/documentation/query/)" — default full fetch; "The Connection must not be in autocommit mode." Fetched this session (HTTP 200).
6. Psycopg 2 Documentation, "[Server side cursors](https://www.psycopg.org/docs/usage.html)" — named cursors, `itersize` default 2000, WITHOUT HOLD default, close-or-leak warning. Fetched this session (HTTP 200).
7. MySQL Connector/J Developer Guide, "[Implementation Notes](https://dev.mysql.com/doc/connector-j/en/connector-j-reference-implementation-notes.html)" — `setFetchSize(Integer.MIN_VALUE)` streaming, `useCursorFetch=true`, connection-occupation and lock-release caveats, "MySQL does not support SQL cursors". Fetched this session (HTTP 200).
8. MySQL Connector/Python Developer Guide, "[cursor.MySQLCursorBuffered Class](https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursorbuffered.html)" — buffered vs nonbuffered semantics, "InternalError (Unread result found)". Fetched this session (HTTP 200).
9. MySQL Server Documentation, "[Text Resultset](https://dev.mysql.com/doc/dev/mysql-server/latest/page_protocol_com_query_response_text_resultset.html)" — COM_QUERY response structure, "Each row is a packet, too". Fetched this session (HTTP 200).
10. Microsoft Learn, "[Using Multiple Active Result Sets (MARS)](https://learn.microsoft.com/en-us/sql/relational-databases/native-client/features/using-multiple-active-result-sets-mars)" — interleaved execution, yield points. Fetched this session (HTTP 200).
11. Oracle Database Error Messages, "[ORA-01555](https://docs.oracle.com/en/error-help/db/ora-01555/)" — cause/action text for snapshot-too-old. Fetched this session (HTTP 200).
12. SQLite Documentation, "[UPDATE...FROM](https://www.sqlite.org/lang_update.html)" — "UPDATE-FROM is supported beginning in SQLite version 3.33.0", PostgreSQL compatibility note. Fetched this session (HTTP 200).
13. SQLite Documentation, "[EXPLAIN QUERY PLAN](https://www.sqlite.org/eqp.html)" — "reports on the way in which the query uses database indices"; used to interpret the local experiments. Fetched this session (HTTP 200).

## Cross-References

- [MVCC Internals](./mvcc-internals.md) — the snapshot/xmin-horizon machinery a held cursor pins; why long readers bloat tables.
- [MVCC Garbage Collection](./mvcc-garbage-collection.md) — per-engine vacuum/purge and how reader horizons hold back reclamation.
- [API Pagination](../../backend/api/api-pagination.md) — the API-design half of keyset/cursor pagination: cursor encoding, Relay connection model.
- [Window Functions](../sql/window-functions.md) — the `ROW_NUMBER()` machinery behind the offset-emulation anti-pattern.
- [Isolation Levels](../transactions/isolation-levels.md) — what each isolation level guarantees a long-lived cursor's snapshot.
- [Connection Pools](../../backend/api/connection-pools.md) — why a streaming read that occupies its connection is a pool-capacity event.
- [Query Optimization Deep Dive](../query-optimization-deep.md) — the planner-side story of why set-based statements beat interpreted loops.
- [B+Tree Index](../indexing/b-plus-tree.md) — the ordered structure keyset pagination seeks through.
