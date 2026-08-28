# Database Connection Pool Deep Dive

A database connection is not cheap. A fresh TCP handshake is one
round-trip; TLS is two more; the database's startup handshake
exchanges parameter negotiation, sets the session's transaction
isolation, allocates a backend process (PostgreSQL forks a process
per connection — costs ~1-10 ms), loads catalog caches, and only
then is the connection usable. A single query round-trip on the
resulting connection costs about 0.5 ms on a LAN; the *setup*
easily costs 20-50 ms. If your service opens a fresh connection
per request, you are spending more time setting up the connection
than you are running the query.

The connection pool is the layer between application code and the
database that holds a fixed set of warm connections and lends them
out per-query. Done right, the per-query cost is a checkout
(microseconds) plus the query itself. Done wrong, it's a
production-incident generator: leaked connections, validation storms,
runaway pool growth that hits `max_connections` on the database and
breaks every other service that talks to the same cluster.

This page covers pool parameters, the connection lifecycle, leak
detection, the validation query, max-lifetime rotation, the
sizing formula, and a comparison of HikariCP, PgBouncer, and
pgcat.

## The Pool: min / max / idle

A connection pool has three primary knobs:

```
Pool population over time:

       max ──────────────────────────────────────  hard cap
              ↑                              ↑
              └──── working set ────┘        burst
       min ──────────────────────────────────────  always warm
            ↑
            startup: pool opens `min` connections
```

- **`minimumIdle` (min)**: number of connections the pool keeps
  open even when idle. Below this, the pool opens new connections
  up to the cap.
- **`maximumPoolSize` (max)**: the hard cap. Checkout blocks (or
  throws) when all `max` connections are in use and the borrow
  queue is full.
- **`idleTimeout`**: how long an idle connection above `min` is
  kept before being closed. Closes back to `min`, not zero.

Three failure modes:

- `min == max == 1`: every query waits for the previous one to
  finish. Throughput ceiling is `1 / (query_latency)`.
- `max == Integer.MAX_VALUE`: the pool grows unbounded and the
  database sees a thousand sessions — at which point
  `max_connections` on the database rejects new connections and
  the whole service goes down.
- `idleTimeout == 0`: connections never close, the pool keeps
  stale connections, and a database failover leaves the pool with
  connections pointing at a dead node.

## Connection Lifecycle: checkout → query → checkin

```
Application thread               Pool                  Database
      │                           │                       │
      ├──── borrow() ────────────▶│                       │
      │                           │  ── checkout ──▶     │
      │◀─── connection c ─────────│                       │
      │                           │                       │
      ├──── c.query("...") ─────────────────────────────▶│
      │◀─── rows ─────────────────────────────────────────│
      │                           │                       │
      ├──── release(c) ─────────▶│  ── checkin ──▶       │
      │                           │                       │
```

There are three times that matter:

1. **Borrow time**: how long the thread waits for a free
   connection. Should be sub-millisecond in steady state.
2. **In-use time**: how long the connection is checked out. This
   is the query latency, plus any time the application holds the
   connection idle (a bug — never hold a connection across a
   downstream RPC).
3. **Idle time**: how long the connection sits in the pool between
   queries. Long idle periods invite problems: the database may
   close the socket, a stateful firewall may drop the NAT entry,
  the database may fail over and leave the connection pointing at
  a dead node.

The borrow semantics in HikariCP:

```java
HikariConfig config = new HikariConfig();
config.setJdbcUrl("jdbc:postgresql://db/app");
config.setMaximumPoolSize(20);
config.setMinimumIdle(5);
config.setConnectionTimeout(2_000);   // borrow waits up to 2s
config.setIdleTimeout(600_000);        // close idle after 10 min
config.setMaxLifetime(1_800_000);      // recycle after 30 min
config.setLeakDetectionThreshold(60_000); // flag if held > 60s

HikariDataSource ds = new HikariDataSource(config);
try (Connection c = ds.getConnection()) {       // borrow
    try (PreparedStatement ps = c.prepareStatement(sql)) {
        // ... use ...
    }
}                                              // close → checkin
```

## Leak Detection

A "leaked" connection is one that was checked out and never
checked back in. The classic cause: an exception thrown between
`getConnection()` and `close()` without a `try-with-resources` or
`finally` block. The pool thinks the connection is still in use; the
database connection limit fills up over hours; eventually every
borrow throws `SQLTransientConnectionException: HikariPool-1 -
Connection is not available, request timed out after 2000ms`.

Leak detection in HikariCP prints a stack trace when a connection
is held longer than `leakDetectionThreshold`:

```
Apparent connection leak detected. Connection
org.postgresql.jdbc4.Jdbc4Connection@5a3949ab has been in use for
63001 ms. The following stack trace shows where the connection was
obtained; the application must close it.

  at com.example.UserService.updateProfile(UserService.java:45)
  at com.example.UserServlet.doPost(UserServlet.java:20)
  ...
```

Detection is a guardrail, not a fix. The actual fix is to never
hold a connection across an external call. Bad pattern:

```java
// Leaks if charge() throws and connection is not in try-with-resources
Connection c = ds.getConnection();
charge(c, userId, amount);   // ← slow HTTP call to payment service
c.commit();
c.close();
```

If `charge()` takes 5 seconds and times out, the connection is
held for 5 seconds — and the pool of 20 connections serves only
4 requests per second. The correct pattern splits the work: do
all DB work, close the connection, *then* do the HTTP call.

## Validation Query (`SELECT 1`)

When the pool hands out a connection, how does it know the
connection is still alive? Three strategies, in increasing cost:

1. **No validation** (`connectionTestQuery = null`): assume the
   connection is alive. Fastest. Breaks the moment a database
   failover or a NAT timeout drops the underlying socket — the
   application gets `Connection is closed` on its first query.
2. **`SELECT 1` (`connectionTestQuery = "SELECT 1"`)**: send a
   trivial query on every borrow. Robust but adds a round-trip
   per checkout. On a 100µs-checkout pool, this makes checkout
   500µs — 5× slower.
3. **JDBC4 `isValid()`**: the driver uses a protocol-level ping
   (in PostgreSQL, the protocol's `Sync` message; in MySQL, the
   COM_PING packet) which does not parse a query. Faster than
   `SELECT 1` and the default in modern drivers.

The defaults you want:

- `connectionTestQuery = null` and rely on `isValid()` (the
  driver's native ping). This is HikariCP's default.
- HikariCP additionally does a keep-alive ping (`housekeeping`)
  on idle connections every 30 s.

A common mistake is to set `connectionTestQuery = SELECT 1` *and*
`isValid` — both fire and you pay twice per checkout.

## Max Lifetime: Connection Rotation

Even with validation, a connection shouldn't live forever.
PostgreSQL's `max_connections` is a per-process limit, but each
session also accumulates state: prepared statements, temp tables,
advisory locks, the per-session `search_path`, GUC settings.
Long-lived connections develop drift: a service that ran a single
`SET statement_timeout = '5s'` once will keep that setting on the
connection forever, even though the next query expected the
default.

The fix is `maxLifetime` (HikariCP) / `maxLifeTime` (most pools):
every connection is closed after at most `maxLifetime` (default
30 minutes). The pool also closes connections gradually — instead
of closing all 20 at the 30-minute mark, each connection has a
jittered lifetime so at most one is closed per few seconds.

The 30-minute default is calibrated against typical cloud NAT
timeouts (AWS NLB: 350 s; GCP TCP: 600 s; AWS RDS proxy: 1800 s).
If your network kills idle TCP connections at, say, 5 minutes,
you must set `idleTimeout` below that and `maxLifetime`
significantly below that — otherwise the pool hands out a
connection that was idle for 4:59 and the first query fails.

## Pool Sizing Formula

The formula above is from the HikariCP wiki, originally by
Performance Engineer at PostgreSQL-Experts Inc., and the
Heikki Linnakangas / Kris Jenkins "Sizing your pool" post:

> `connections = (core_count * 2) + effective_spindle_count`

The reasoning: a thread that's blocked on I/O can't do useful CPU
work. If you have 4 cores, the OS can run 4 threads concurrently;
each of those threads will be blocked on I/O some fraction of the
time, so to keep the CPU busy you need roughly 2× as many in-flight
queries as cores. The `+ effective_spindle_count` accounts for disk
spindles: a query blocked on disk I/O should be able to issue
another query that uses a different spindle.

```
On a 4-core box with one SSD:
  connections = (4 * 2) + 1 = 9

On an 8-core box with two SSDs:
  connections = (8 * 2) + 2 = 18
```

Modern NVMe SSDs behave differently — they don't have spindles,
and they have parallel queues. The formula's heuristic extends to
"effective parallel I/O channels": 1 for SATA SSD, 4-8 for NVMe,
10+ for RAID arrays. In practice, **the pool size that maximizes
throughput is rarely larger than 20-30 per instance**, even on
high-core boxes. Above that, context-switching and lock contention
on the database side dominate and *throughput drops*.

The other rule, more important than the formula: **a service's
total pool size across all instances should not exceed the
database's `max_connections` minus a safety margin.** If 10
service instances each open 20 connections, that's 200 — and
PostgreSQL's default `max_connections` is 100.

## PostgreSQL Connection Limits

PostgreSQL's `max_connections` (default 100) caps the number of
concurrent backends. Every connection forks a backend process at
`postmaster` level; the backend allocates ~10 MB of memory for
catalog caches and per-process state. A box with 8 GB of RAM can
comfortably run 200-300 connections; 1000 connections will thrash
the OS scheduler and exhaust memory.

```
$ psql -c "SHOW max_connections;"
 max_connections
-----------------
 100

$ psql -c "SELECT count(*) FROM pg_stat_activity;"
 count
-------
  73        ← 73 in use; if this hits 100, new connects fail
```

A connection that's idle but checked-out still counts against
`max_connections`. The PG Bouncer reference is explicit:
*PostgreSQL connections are expensive; the pool's job is to keep
the database-side count low even when the application-side count is
high.*

## HikariCP vs PgBouncer vs pgcat

The three tools you'll meet in production serve different layers.

| Tool        | Layer                  | Why you'd use it                                  |
|-------------|------------------------|---------------------------------------------------|
| HikariCP     | In-process (JDBC)      | App-side pooling; no extra deploys; sub-µs checkout |
| PgBouncer    | Sidecar / dedicated    | Multiplex many app connections onto few DB connections; transaction-mode pooling |
| pgcat        | Sidecar / sharded      | Like PgBouncer but adds sharding and multi-tenant routing |

### HikariCP

In-process JVM pool. The fastest pool ever benchmarked for JDBC
(checkout at ~50 ns under contention via a ConcurrentBag
lock-free structure). Pros: no extra infra, perfect visibility
into per-app metrics. Cons: doesn't reduce database-side
connections — every HikariCP `max` is a real PostgreSQL backend.

The trap: 50 microservices × 20 connections = 1000 backends.
PostgreSQL default is 100. You either raise `max_connections` (and
risk OOM) or install PgBouncer.

### PgBouncer

An external connection multiplexer. Connects to PostgreSQL with a
small pool (say 25) of "server connections" and accepts thousands
of "client connections", multiplexing client traffic onto the
server pool. Three modes:

- **session pooling**: one server connection per client connection.
  Equivalent to no pooling but with a single TCP hop. Useful only
  for migration.
- **transaction pooling**: a server connection is bound to a client
  only for the duration of a transaction. On `COMMIT` the server
  connection goes back to the pool. This is the killer feature: a
  service with 1000 idle connections uses 0 server connections.
- **statement pooling**: server connection is bound per-statement.
  Breaks anything that uses session state (prepared statements,
  temp tables, `SET`, cursors). Niche.

```
Without PgBouncer:                       With PgBouncer (transaction mode):

1000 app conn ────────►  PostgreSQL       1000 app conn ────► PgBouncer ────► PostgreSQL
                        (max_conn=100)                                  (max_conn=25)
                        ↑ bursts fail                                   ↑ never fails
```

Transaction-mode pooling has caveats:

- Prepared statements (protocol-level) break: the prepare is tied
  to a server connection that's returned to the pool after the
  transaction. Use `PREPARE` SQL statements (parsed per session)
  or set `max_prepared_statements` in PgBouncer 1.21+ which adds
  protocol-level prepared statement support.
- `SET` statements don't persist. Use `SET LOCAL` inside the
  transaction.
- Advisory locks (`pg_advisory_lock`) are session-bound; they
  release at the wrong time under transaction pooling. Don't use
  them with PgBouncer in transaction mode.
- `LISTEN/NOTIFY` doesn't work; the session you registered on
  might be a different session when the notification fires.

### pgcat

A Rust-based PgBouncer alternative with first-class sharding and
multi-tenant routing: route queries for `tenant_id = 5` to shard 5,
queries for `tenant_id = 6` to shard 6. Like PgBouncer it does
transaction-mode pooling; unlike PgBouncer it can route to
different PostgreSQL clusters transparently. Used in production
at Postgres.app and several SaaS companies.

## Pitfalls

1. **Setting `max` to total app concurrency.** If you have 200
   worker threads and 50 service instances, that's 10k connections.
   Set `max` per instance based on the sizing formula, not on the
   thread count.
2. **Forgetting the `+ effective_spindle_count` term.** On an NVMe
   box, treat this as 4-8. On a SATA SSD, 1. Setting it to 0 means
   under-utilization; setting it to 100 means context-switching
   dominates.
3. **Mixing transaction-mode PgBouncer with session-state features.**
   Protocol-level prepared statements, advisory locks, `LISTEN/
   NOTICE`, and `SET` without `LOCAL` all break.
4. **Holding a connection across an RPC.** The downstream call's
   latency is charged to the pool; if downstream is slow, the
   pool fills up and the service stalls.
5. **Validation via `SELECT 1`.** Use the driver's `isValid()` and
   let the pool do a periodic keepalive. `SELECT 1` on every
   borrow is a wasted round-trip.
6. **One global pool across heterogeneous workloads.** The
   bulkhead principle applies: a slow batch job shouldn't exhaust
   the pool the API needs. Use separate pools per workload class.
7. **Raising `max_connections` instead of installing a pooler.**
   PostgreSQL at 1000 connections isn't a database anymore; it's a
   process scheduler with a database attached.

## Interview Questions

### Q: How do you size a connection pool?

Start with the formula `connections = (core_count * 2) +
effective_spindle_count`. For an 8-core box with NVMe (treat as
4 effective I/O channels), that's 20. Then sanity-check against
the database's `max_connections` divided by the number of service
instances: if the per-instance pool × instance count exceeds 80%
of `max_connections`, lower the per-instance pool or put a pooler
in front of the database. Benchmark with a steady-state load test
and watch throughput — when adding connections stops increasing
throughput (or starts decreasing), you've found the ceiling.

### Q: Why is PgBouncer transaction-mode pooling so effective?

Because most application transactions are short and most
application connections are idle. A service with 1000 connections
and 1 ms average transaction duration uses 1000 server-seconds
per second of database time — but at any instant, only a few
dozen transactions are in-flight. Transaction-mode pooling reuses
the same server connection across many clients' transactions,
matching the database-side pool to the *in-flight* count rather
than the *connected* count.

### Q: A pool reports `Connection is not available, request timed
out`. What do you do?

Three checks: (1) leak detection — is one path holding connections
longer than it should? Look for slow downstream RPCs inside a
borrowed connection. (2) saturation — is the pool just too small
for the offered load? Increase `max` and re-benchmark. (3) slow
queries — is the database actually taking seconds per query, so
the pool legitimately can't keep up? Look at `pg_stat_activity` on
the database, find the slowest queries, and fix or index them.

### Q: What's the relationship between pool size and thread count?

Decouple them. A worker thread that needs a connection will
borrow one; if the pool is smaller than the thread count, threads
queue for connections. That's fine if the work per thread is short
relative to the wait. The mistake is to set `pool max == thread
count` on the assumption that "every thread needs its own
connection" — that grows the pool past the database's capacity
for no throughput gain.

## References

- HikariCP Wiki, "[About Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)" — the canonical derivation of `connections = (core_count * 2) + effective_spindle_count`, including the disk-I/O argument and the surprising "smaller is better" recommendation.
- HikariCP Wiki, "[Code Status & Connection Lifecycle](https://github.com/brettwooldridge/HikariCP/wiki)" — the ConcurrentBag checkout algorithm and the leak-detection semantics.
- PgBouncer Documentation, "[Features](https://www.pgpbouncer.org/features)" and "[Configuring PgBouncer](https://www.pgbouncer.org/config.html)" — session/transaction/statement pooling modes, prepared-statement handling as of 1.21.
- PostgreSQL Documentation, "[Connection Settings: `max_connections`](https://www.postgresql.org/docs/current/runtime-config-connection.html#GUC-MAX-CONNECTIONS)" — the default 100, the per-backend memory cost, and the interaction with `shared_buffers`.
- pgcat Documentation, "[Overview](https://github.com/postgresml/pgcat#readme)" — transaction-mode pooling, sharding, multi-tenant routing.
- Kris Jenkins, "[HikariCP and Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)" — the original benchmark showing throughput dropping above the formula.
- PostgreSQL Documentation, "[Client Connection Setup](https://www.postgresql.org/docs/current/client-interfaces.html)" — startup handshake, parameter negotiation, the cost of a fresh connection.

## Related Topics

- [Connection Pools](../api/connection-pools.md) — the introductory counterpart.
- [Bulkhead Pattern](./bulkhead-deep.md) — per-tenant or per-dependency pools are bulkheads; the same sizing discipline applies.
- [Circuit Breaker Deep Dive](./circuit-breaker-deep.md) — the failure-side companion; pools are the capacity side.
- [PostgreSQL Internals: WAL](../../dbms/advanced/wal-internals.md) — why PostgreSQL connections are heavyweight (per-process backends).
- [Health Check Patterns](./health-check-patterns.md) — the validation-query counterpart at the application level.
