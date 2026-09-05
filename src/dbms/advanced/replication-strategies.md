# Database Replication Strategies

Replication is the act of copying writes from one database to
another. The reasons are never "because we can" — they are
redundancy (a node can fail without losing data), read scaling
(distribute reads across many nodes), geographic locality (serve
requests from a region close to the user), and operational
isolation (run a heavy analytics query on a replica without
slowing the primary). Every replication strategy trades latency,
durability, and conflict-handling against each other. Pick wrong
and you get either data loss on failover or writes that take
seconds to commit.

This page goes through the strategies you'll meet in production:
synchronous (1-safe, 2-safe), asynchronous (log shipping,
streaming), semi-synchronous, logical, multi-master, and read
replicas. Gray & Reuter's *Transaction Processing* and
Kleppmann's *Designing Data-Intensive Applications* are the two
textbooks that anchor the vocabulary; the PostgreSQL and MySQL
documentation give the production implementation specifics.

## The Fundamental Tradeoff: RPO vs RTO vs Commit Latency

A replication strategy answers three questions on every write:

- **How many copies of this write exist before the client is told
  "committed"?** (durability / RPO — Recovery Point Objective, the
  amount of data you can lose.)
- **How long does the commit wait?** (commit latency.)
- **What happens if the primary fails before all replicas have
  the write?** (failover semantics / RTO — Recovery Time Objective,
  the time until the system is back serving writes.)

These three are coupled. A fully synchronous strategy (every
replica acks before commit) minimizes RPO but maximizes commit
latency — every commit waits for the slowest replica. A fully
asynchronous strategy (no replica acks) minimizes commit latency
but maximizes RPO — a primary that crashes between commit and
replication has lost the most recent writes. Everything in
between is a knob.

## Synchronous Replication: 1-safe vs 2-safe

Gray & Reuter's taxonomy defines two safety levels for synchronous
replication:

- **1-safe**: the primary commits *before* sending the write to
  the replica. The transaction is durable on the primary only. If
  the primary crashes between commit and replication, the replica
  doesn't have the write — and on failover, those committed
  transactions are *lost*. The "1" refers to one durable copy.
- **2-safe**: the primary sends the write to the replica, waits for
  the replica to acknowledge, *then* commits. Both primary and
  replica have the write before the client is told "committed". On
  failover, no committed transaction is lost. The cost: every
  commit waits for a network round-trip to the replica.

```
1-safe (commit-then-replicate):

  Client ──write──▶ Primary
                     │
                     │ commit (returns to client)
                     ▼
                  Replicate ─▶ Replica
                                  │
                                  │ ack (async)
                                  ▼
                          (Replica durable)

  ── If primary crashes here, the write is committed but the
     replica doesn't have it. Failover loses it.

2-safe (replicate-then-commit):

  Client ──write──▶ Primary
                     │
                     │ Replicate ─▶ Replica
                     │                  │
                     │◀─── ack ──────────│
                     ▼
                  commit (returns to client)

  ── Both primary and replica durable before client sees
     "committed". No data loss on failover.
```

PostgreSQL's `synchronous_standby_names` implements 2-safe:

```sql
-- On the primary:
ALTER SYSTEM SET synchronous_standby_names = 'FIRST 2 (replica1, replica2)';
ALTER SYSTEM SET synchronous_commit = on;
SELECT pg_reload();
```

With `FIRST 2`, the primary waits for the first 2 named standbys
to flush and acknowledge before the commit returns. If one of
those standbys is unreachable, every write blocks until the
standby recovers or is removed from the list. This is why
synchronous replication is rarely used outside of single-datacenter
or low-latency cross-AZ setups: a cross-region synchronous commit
is 50-100 ms, and that's per write, not per transaction.

## Asynchronous Replication: Log Shipping and Streaming

The asynchronous modes don't wait for the replica before commit.
The replica gets the write eventually. Two flavors:

**Log shipping**: the primary periodically ships a chunk of its
write-ahead log (WAL in PostgreSQL, redo log in InnoDB, oplog in
MongoDB) to the replica, which replays it. The lag is the shipping
interval — typically seconds to minutes. PostgreSQL's
`archive_mode` + `restore_command` is the canonical example:

```
Primary                            Standby
─────                              ───────
WAL segments written                archive_recovery reads
→ archived to S3/object store   →   segments, replays each
                                    (lag = archive interval + replay)
```

Pros: simple, works across slow links (S3 as the transport),
decouples primary and standby. Cons: lag in minutes; failover
loses those minutes; can't load-balance reads onto the standby
without accepting that they're stale.

**Streaming replication**: the primary streams WAL records over a
TCP connection as soon as they're produced; the standby applies
them. Lag is typically milliseconds to a second. PostgreSQL's
streaming replication is the default for hot standbys; MySQL's
binlog replication is the equivalent.

```
Primary                            Standby
─────                              ───────
WAL writer flushes record          walsender → walreceiver
→ walsender sends over TCP   →     writes to WAL, applies
                                    (lag = milliseconds)
```

The catch: streaming replication only works while the standby is
connected. If the standby drops, the primary accumulates WAL until
`wal_keep_size` is exhausted (then disconnects the standby). To
recover a standby that fell behind, you have to fall back to log
shipping from a base backup — the very thing streaming was
supposed to avoid.

## Semi-Synchronous Replication

A middle ground: the primary waits for **N** replicas to
acknowledge before declaring commit, but not *all* replicas. Used
to balance commit latency against durability.

MySQL has built-in semi-synchronous replication since 5.5. With
`rpl_semi_sync_master_wait_for_slave_count = 1` (default), the
primary waits for one slave to acknowledge; with the option set to
N, it waits for N. If those slaves don't acknowledge within
`rpl_semi_sync_master_timeout` (default 10 s), the primary
degrades to asynchronous replication rather than blocking
commits forever.

```
Primary ──write──▶ replicate ─▶ replica1 ─ack──▶ ┐
                                  replica2 ─ack──▶ ┤── commit (after 2 acks)
                                  replica3 (slow)  │   (if timeout: degrade to async)
                                                   ▼
                                                 COMMIT
```

PostgreSQL's `synchronous_standby_names = 'ANY 2 (a, b, c)'` does
the same thing — wait for any 2 of 3 named standbys.

The knobs to tune:

- **N, the number of acks**: 1 minimizes commit latency; 2+ adds
  redundancy. The classic setup is `N = 2` across 2 AZs.
- **Timeout before degrade**: too short → frequent degrades
  defeat the point of being semi-synchronous. Too long → a
  stalled replica stalls the whole primary.
- **Wait policy**: "after-sync" (replica has flushed to its own
  WAL) vs "after-apply" (replica has applied the change). The
  former is faster; the latter gives stronger read-your-writes
  on the replica.

## Logical Replication

Physical replication ships bytes of WAL — same page-level changes
on the standby. Logical replication ships **decoded operations**:
"INSERT row (1, 'alice')" rather than "modify byte 0x42 of page
1234". This breaks the requirement that primary and standby be
byte-identical, which is the unlock.

```
Primary: WAL bytes                    Logical decoding plugin
   ▼                                     (pgoutput, test_decoding)
   ├─────► output plugin decodes WAL ──▶ logical change records
                                              │
                                              ▼
                                       Publication (set of tables)
                                              │
                                              ▼ (TCP, slot-based)
                                       Subscription on target DB
                                              │
                                              ▼
                                       Apply to target tables
```

PostgreSQL 10+ has native logical replication:

```sql
-- On the primary (publisher):
CREATE PUBLICATION my_pub FOR TABLE users, orders;

-- On the target (subscriber):
CREATE SUBSCRIPTION my_sub
    CONNECTION 'host=primary dbname=app'
    PUBLICATION my_pub;
```

What logical replication buys you:

- **Cross-version replication**: upgrade the standby to a new
  major version while the primary stays on the old one, then
  promote. Zero-downtime major upgrades are built on this.
- **Cross-engine replication**: decode PostgreSQL's WAL, apply to
  Kafka, ClickHouse, or another database entirely. Debezium and
  Confluent Connectors sit on this layer.
- **Selective replication**: replicate only some tables, or only
  some columns, or apply row filters (`WHERE region = 'EU'`).
- **Different schema on the target**: the target table can have
  extra columns, different indexes, even a different name. This
  is impossible with physical replication because the bytes must
  match.

What it costs:

- **No DDL replication**: schema changes must be applied manually
  on the subscriber. Add a column on the publisher, the subscriber
  doesn't know until you `ALTER TABLE` it.
- **Sequences are not replicated**: a `SERIAL` column on the
  publisher doesn't move on the subscriber. If both sides insert
  (multi-master), they will collide. You must partition sequence
  ranges.
- **Large transactions are slow**: each transaction is sent as a
  unit; a multi-GB transaction takes a long time to ship and
  apply.
- **Triggers fire on the target by default**: this can be a
  feature (audit, derived columns) or a footgun (slow apply).

## Multi-Master Replication

Multi-master lets every node accept writes. The hardest part is
**conflict resolution**: two nodes accept simultaneous updates to
the same row. Strategies:

- **Last-writer-wins (LWW)**: every write carries a timestamp;
  the later one wins. Requires synchronized clocks (Spanner's
  TrueTime, CockroachDB's hybrid logical clocks). Simple, but
  loses writes silently.
- **Conflict-free replicated data types (CRDTs)**: data
  structures (counters, sets, maps) where concurrent updates
  commute — `counter.inc(1)` on two nodes always converges to
  `+2`. Riak and Redis CRDT have these built-in. Limited to
  specific types.
- **Vector clocks + application resolution**: every write records
  its causal history; the database surfaces conflicts and the
  application picks the resolution. Dynamo (original) and Riak
  work this way. Powerful but pushes complexity to the app.
- **Distributed transactions (Calvin, Spanner)**: serialize
  writes globally so concurrent updates are impossible. The
  cost is per-write latency (Spanner commits are 5-15 ms even
  within one region).

```
Conflict resolution matrix:

Strategy            Latency   Consistency   Use case
─────────────────────────────────────────────────────────────
LWW                 low       eventual      high-volume, low-value
CRDTs               low       strong*        counters, sets
Vector clocks       medium    eventual      collaborative
Calvin/Spanner      high      serializable  financial
*for the data type's defined operations
```

Multi-master is rarely worth it. Most production multi-master
deployments are actually "active-passive with a fast failover"
dressed up — they accept writes on one node at a time. True
multi-master (CockroachDB, Spanner, TiDB, FoundationDB) buys you
write-availability and geographic write locality at the cost of
serializable-over-network latency on every commit.

## Read Replicas

The simplest and most common pattern: one primary accepts writes,
N read replicas accept reads. Writes flow synchronously or
asynchronously to replicas; clients route `SELECT`s to replicas
and `INSERT`/`UPDATE`/`DELETE`s to the primary.

```
                  ┌── read replica 1 (read-only traffic)
                  │
Primary (writes) ──┼── read replica 2 (read-only traffic)
                  │
                  └── read replica 3 (analytics, BI)
```

The wins:

- **Read throughput scales horizontally**. 10x more reads → add
  replicas.
- **Workload isolation**: heavy analytics queries hit replicas,
  the primary stays fast for OLTP.
- **Geographic read locality**: place a read replica in each
  region; users hit the local replica.

The costs:

- **Read-your-writes inconsistency**: a client writes to the
  primary, immediately reads from a replica, gets the *old*
  value because the replication hasn't caught up. Workarounds:
  read-after-write sessions (route reads to the primary for a
  few seconds after the user's last write), or causal tokens
  (PostgreSQL's `pg_logical_emit_message` + `pg_replication_slot`
  status).
- **Failover staleness**: when the primary fails, the most-
  up-to-date replica must be promoted. If the replica was
  asynchronous, the promoted node may be missing recent writes —
  those are lost.
- **Connection overhead**: each replica is a full PostgreSQL
  instance with its own connection pool, vacuum, indexes, and
  memory budget.

## MySQL Replication Internals: Binlog, GTID, Semi-Sync, and Parallel Apply

The strategy sections above describe replication in the abstract.
MySQL's implementation deserves a section of its own: it is the most
widely deployed log-based replication system in production, and each of
its major knobs — binlog format, GTID mode, the semi-sync wait point,
parallel apply — has a failure mode that shows up as a 3 a.m. incident.
The binlog is MySQL's replication substrate (the counterpart of
PostgreSQL's WAL); everything below hangs off it.

### Binlog Formats: STATEMENT vs ROW vs MIXED

- **STATEMENT (SBR)** logs the SQL statement and the replica
  re-executes it. Compact, auditable — and only safe when re-execution
  is deterministic. The manual's unsafe list includes `UUID()`,
  `RAND()`, `LOAD_FILE()`, `USER()`, `FOUND_ROWS()`, `SYSDATE()`, and
  — the classic — `DELETE ... LIMIT n` without `ORDER BY`: which rows
  the statement touches depends on the optimizer's plan, and the
  replica may pick differently.
- **ROW (RBR)** logs the rows themselves: each change event carries a
  before-image (matched when searching for the row) and an after-image
  (the changes). Determinism problems vanish because the effect, not
  the cause, is shipped. The cost is volume: row-based logging "may
  write significantly more data to the binary log; this is true even
  for statements that are rolled back".
- **MIXED** logs statements by default and switches to row-based for a
  documented list of unsafe cases (`UUID()`, loadable functions,
  `USER()`, system-variable references, and so on).

A nuance interviews love: `NOW()` does *not* break statement-based
replication, though it looks nondeterministic — "For NOW(), the binary
log includes the timestamp", so the source's value is what the replica
sees. Statement timestamps are pinned by the event stream; random
values and row-order effects are not.

`binlog_row_image` tunes ROW bloat: the default `FULL` logs all columns
of both images; `minimal` logs only changed columns plus what is needed
to identify the row; `noblob` skips unneeded BLOB/TEXT columns. That
saves disk and network but ties replica row-matching to a usable key —
a row event on a keyless table degenerates toward a table scan per
change (`slave_rows_search_algorithms` documents the search) — and it
makes downstream CDC lossy.

Direction of travel: `binlog_format` is deprecated as of MySQL 8.0.34,
"and for the row-based format to become the only logging format used by
MySQL." CDC consumers require ROW anyway: Debezium's MySQL connector
demands `binlog_format=ROW` and `binlog_row_image=FULL` — you cannot
re-derive row images from SQL text.

### GTID: Identity, Auto-Positioning, Errant Transactions

A GTID is a pair: `GTID = source_id:transaction_id`, where `source_id`
is normally the originating server's `server_uuid` and `transaction_id`
is the commit-order sequence number on that origin. Each server tracks
applied GTIDs in `gtid_executed`; `gtid_purged` is the subset committed
here but no longer present in any binlog file. The payoff is auto-skip:
"Once a transaction with a given GTID has been committed on a given
server, any attempt to execute a subsequent transaction with the same
GTID is ignored by that server." Replaying a stream twice is harmless.

Auto-positioning is where failover gets simpler. With
`SOURCE_AUTO_POSITION=1`, "in the initial connection handshake, the
replica sends a GTID set containing the transactions that it has
already received, committed, or both. The source responds by sending
all transactions recorded in its binary log whose GTID is not included
in the GTID set sent by the replica." File-based failover instead
requires computing, per replica, correct `SOURCE_LOG_FILE`/
`SOURCE_LOG_POS` coordinates on the new source. Mismatches now
fail loudly: purged-but-needed transactions raise
`ER_SOURCE_HAS_PURGED_REQUIRED_GTIDS`; a replica holding transactions
with the source's UUID that the source itself never committed refuses
to start with `ER_REPLICA_HAS_MORE_GTIDS_THAN_SOURCE`.

**Errant transactions** are transactions executed on a replica that did
not originate from the primary — a write made with `sql_log_bin=0`, a
brief promotion during a botched switchover. They poison failover
because the promoted replica carries history no other node has.
Detection is set arithmetic —
`GTID_SUBTRACT(a, b)` "returns the GTIDs from one GTID set that are not
in another"; MySQL Shell's `clusterSet.status()` automates it and
reports `"ERROR: Errant transactions detected"`. Repair is not "skip" —
`sql_replica_skip_counter` doesn't work in GTID mode; the supported
paths are cloning from the server with the best data and rejoining, or
rebuilding.

GTID mode also restricts which statements run
(`enforce_gtid_consistency`): `CREATE TABLE ... SELECT` was disallowed
before 8.0.21 (ROW logging recorded it as two transactions with two
GTIDs); temporary tables inside transactions are disallowed under
STATEMENT logging (8.0.13+ permits them under ROW/MIXED, unlogged); and
transactions mixing transactional and nontransactional engines can
break the one-GTID-per-transaction correspondence. One item the list
does *not* contain — despite circulating folklore — is `DROP TABLE` on
tables without a primary key.

### Semi-Sync Reality: AFTER_SYNC vs AFTER_COMMIT, and the Silent Fallback

The strategy section above gave semi-sync's knobs. The sharp edge is
*when* the primary waits. `rpl_semi_sync_master_wait_point` picks
between two points:

- **AFTER_SYNC (default since 5.7)**: write to the binlog, sync to
  disk, wait for the replica's acknowledgment, *then* commit to the
  storage engine and return to the client. "In the event of source
  failure, all transactions committed on the source have been
  replicated to the replica (saved to its relay log). An unexpected
  exit of the source server and failover to the replica is lossless."
  The failed source, the manual notes, must be discarded rather than
  restarted: its binlog may hold transactions it never committed.
- **AFTER_COMMIT** (the 5.5/5.6-era behavior): commit to the storage
  engine first, then wait for the ack. The loss window sits between
  commit and acknowledgment: "After the commit and before replica
  acknowledgment, other clients can see the committed transaction
  before the committing client. If something goes wrong such that the
  replica does not process the transaction... it is possible for such
  clients to see a loss of data relative to what they saw on the
  source."

Concrete AFTER_COMMIT timeline: T commits at t=0 and other sessions
can already read its effects; the replica's ack never arrives; at
t=10 s `rpl_semi_sync_master_timeout` (default 10,000 ms) expires and
the primary reverts to asynchronous replication; at t=11 s the primary
dies and the replica is promoted — every client that read T's effects
has just watched committed data evaporate. AFTER_SYNC closes this
window: nothing becomes visible before the replica holds it.

And the trap: degradation is silent. "Automatic fallback from
semisynchronous to asynchronous replication on the source means that it
is possible for the `rpl_semi_sync_master_enabled` system variable to
have a value of 1 ... even when semisynchronous replication is in fact
not operational." Alert on `Rpl_semi_sync_master_status` (0 once fallen
back) and `Rpl_semi_sync_master_no_tx` (commits not acked), not on the
enabled flag — a fleet that quietly degraded to async has traded its
RPO story away.

### Parallel Replication: LOGICAL_CLOCK, WRITESET, and Commit Order

The original replica applied transactions on one thread while the
source committed them with many; under load, replica lag is apply rate.
Multithreaded apply (`replica_parallel_workers` > 0, default 4 since
8.0.27) adds a coordinator scheduling transactions onto workers, and
the design question is who may run in parallel:

- `replica_parallel_type=DATABASE` parallelizes only transactions
  touching different databases — useless unless you partitioned the
  schema that way, and unsafe with cross-database constraints.
- `LOGICAL_CLOCK` uses dependency information the source writes into
  the binlog as two logical timestamps per transaction:
  `sequence_number` (1, 2, 3, ... per binlog file) and
  `last_committed` — "the sequence_number of the most recently
  committed transaction found to conflict with the current
  transaction. This value is always less than sequence_number."
  Transactions sharing a `last_committed` can apply concurrently; under
  COMMIT_ORDER two transactions are independent when their commit-time
  windows (between last statement and engine commit) overlap — a mirror
  of source group commit. MariaDB's parallel replication documents the
  same in-order contract for its optimistic mode.
- `WRITESET` (`binlog_transaction_dependency_tracking=WRITESET`)
  sharpens this: each row change contributes one hash per unique key to
  a write set, and "two transactions are considered conflicting if
  their write sets overlap", with DDL and foreign-key-affecting
  transactions as periodic serialization points. WRITESET at every hop
  of a multi-level replica topology keeps parallelism from decaying
  toward serial apply.

Ordering is preserved by `replica_preserve_commit_order=ON` (default
from 8.0.27): "transactions are executed and committed on the replica
in the same order as they appear in the replica's relay log" — workers
race, but the replica never externalizes a transaction out of order.
Without it, parallel apply can commit out of order and replica reads
see torn history.

`Seconds_Behind_Source` lies under parallel apply: it is NULL when the
applier is stopped or the relay log is drained with the receiver down;
it is 0 whenever the receiver is running and the relay log is exhausted
— even while the coordinator is still applying what it drained; and it
derives from event timestamps, so chained topologies fluctuate. Under a
multithreaded applier it is "based on Exec_Source_Log_Pos, and so may
not reflect the position of the most recently committed transaction".
Watch `replication_applier_status_by_worker` instead.

### Multi-Source Replication: Channels, Filters, Shard Aggregation

A multi-source replica opens one replication channel per source —
"multi-source replication enables a replica to receive transactions
from multiple immediate sources in parallel" — for the aggregation use
cases the manual lists: "Backing up multiple servers to a single server.
Merging table shards. Consolidating data from multiple servers to a
single server." Each channel must connect to a different source
(replicas are identified by server_id), and each channel gets its own
applier threads.

Two rules keep it sane. First, no conflict machinery: "Multi-source
replication does not implement any conflict detection or resolution
when applying transactions" — if two channels write the same rows, last
apply wins silently; shard aggregation works because keyspaces are
disjoint, not because MySQL prevents overlap. Second, filters are per
channel (`CHANGE REPLICATION FILTER ... FOR CHANNEL`), and in a GTID
diamond topology "with different filtering on the channels, the
database can become inconsistent and replication can hang".

## Comparison Table

| Strategy                | Commit Latency     | Data Loss (RPO) | Write Availability | Use Case                                    |
|-------------------------|--------------------|------------------|---------------------|---------------------------------------------|
| 1-safe synchronous      | local              | yes, on failover | primary only       | Single-AZ, low commit latency              |
| 2-safe synchronous      | +1 RTT to replica  | none             | primary only        | Cross-AZ financial, must-not-lose           |
| Semi-sync (N acks)      | +1 RTT, with degrade | none if N≥1 acks | primary only       | Multi-AZ, degrades on replica loss          |
| Async streaming         | local              | seconds          | primary only        | Default for read replicas                   |
| Async log shipping      | local              | minutes          | primary only        | Cold DR, slow links                         |
| Logical replication     | local              | seconds-minutes  | primary only        | Cross-version, cross-engine, selective      |
| Multi-master (LWW)      | local              | dependent on clocks | any node          | Geo-distributed, conflict-tolerant          |
| Multi-master (Calvin)   | high (global)      | none             | any node            | Strict serializable, financial               |
| Read replica            | local              | depends on primary-replica mode | primary only for writes | Read scaling, analytics isolation     |

## Pitfalls

1. **Synchronous replication across a WAN.** Commit latency
   becomes the WAN RTT; 100 ms commits will kill OLTP throughput.
   Keep synchronous replicas within an AZ or a region.
2. **Forgetting to set `wal_keep_size` for streaming replicas.**
   A replica that falls behind for any reason (network blip,
   slow apply) will exhaust the WAL retain window and disconnect;
   recovery requires a base backup.
3. **Reading from a stale replica immediately after writing.**
   Users see their own write "disappear" because the read went to
   a replica that hadn't received the change yet. Either route
   post-write reads to the primary, or use causal consistency
   tokens.
4. **Treating a hot standby as fully available during failover.**
   The promote operation takes time (seconds to tens of seconds
   for cleanup and WAL replay). Clients should retry with a
   circuit breaker, not crash.
5. **Not testing failover.** A replica that's never been promoted
   has never had its replication slots, timeline history, or
   `recovery.signal` tested in anger. Test failover quarterly at
   minimum.
6. **Logical replication without monitoring `pg_stat_subscription`.**
   A logical subscription can stall silently for hours if the
   publisher evicts the slot or the apply worker crashes. Monitor
   `latest_end_lsn` and `last_msg_receipt_time` continuously.
7. **Multi-master without an explicit conflict policy.** Pick LWW
   with monotonic clocks, CRDTs, or application resolution —
   never "let's see what happens".

## Interview Questions

### Q: When would you choose synchronous over asynchronous
replication?

When the cost of losing committed transactions on failover is
higher than the cost of the extra commit latency. Financial
transactions, orders, payments — anything where losing a
committed write is a regulatory or business disaster. The
constraint is that the synchronous replica must be reachable in
single-digit-millisecond RTT (same AZ or same region); a
cross-region synchronous replica adds 50-100 ms per commit.

### Q: How does logical replication differ from physical?

Physical ships WAL bytes; primary and standby must be the same
major version and same on-disk layout. Logical ships decoded
operations (insert, update, delete) and the target can be a
different version, different schema, or different engine
entirely. Logical is for upgrades-in-place, cross-engine
pipelines (Debezium to Kafka), and selective/table-level
replication; physical is for fast, hot standbys and read
replicas within one PostgreSQL major version.

### Q: A semi-synchronous replica becomes unreachable. What
happens?

It depends on the timeout. In MySQL semi-sync, after
`rpl_semi_sync_master_timeout` (default 10 s) the primary
degrades to asynchronous: commits return without waiting for the
replica, and the system runs the risk of losing those writes if
the primary crashes before the replica recovers. In PostgreSQL,
`FIRST N` doesn't degrade — commits block forever until at least
N replicas ack or you remove a replica from
`synchronous_standby_names`. The two systems make different
tradeoffs; pick the one that matches your failure tolerance.

### Q: How do you prevent read-your-writes inconsistency with
read replicas?

Three patterns: (1) sticky reads — for a few seconds after the
user's last write, route their reads to the primary; (2) causal
tokens — the client gets a token from the primary at write time
and sends it to the replica, which blocks the read until it has
applied that token's LSN; (3) read-the-primary — for any read
that follows immediately after a write, just go to the primary.
The first is simplest, the second is correct, the third is
fastest.

## References

- PostgreSQL Documentation, "[High Availability, Load Balancing, and Replication](https://www.postgresql.org/docs/current/high-availability.html)" — the overview chapter covering log shipping, streaming, and synchronous modes.
- PostgreSQL Documentation, "[Synchronous Replication](https://www.postgresql.org/docs/current/warm-standby.html#SYNCHRONOUS-REPLICATION)" — `synchronous_standby_names` syntax, `FIRST N` vs `ANY N`, and the `synchronous_commit` GUC.
- PostgreSQL Documentation, "[Logical Replication](https://www.postgresql.org/docs/current/logical-replication.html)" — publications, subscriptions, the `pgoutput` plugin, and the limitations (no DDL, no sequences).
- MySQL Reference Manual, "[Replication](https://dev.mysql.com/doc/refman/8.0/en/replication.html)" and "[Semisynchronous Replication](https://dev.mysql.com/doc/refman/8.0/en/replication-semisync.html)" — binlog formats, GTID, the semi-sync plugin and its timeout semantics.
- MySQL Reference Manual, "[Replication Formats](https://dev.mysql.com/doc/refman/8.0/en/replication-formats.html)", "[Mixed Binary Logging Format](https://dev.mysql.com/doc/refman/8.0/en/binary-log-mixed.html)" and "[Advantages and Disadvantages of Statement-Based and Row-Based Replication](https://dev.mysql.com/doc/refman/8.0/en/replication-sbr-rbr.html)" — the three formats, the MIXED switch conditions, the unsafe-statement list, and the 8.0.34 deprecation of `binlog_format`.
- MySQL Reference Manual, "[Replication and System Functions](https://dev.mysql.com/doc/refman/8.0/en/replication-features-functions.html)" — why `NOW()` is safe under statement-based replication: the timestamp travels in the binary log.
- MySQL Reference Manual, "[GTID Life Cycle](https://dev.mysql.com/doc/refman/8.0/en/replication-gtids-lifecycle.html)" — `gtid_executed`, `gtid_purged`, and the auto-skip rule.
- MySQL Reference Manual, "[GTID Auto-Positioning](https://dev.mysql.com/doc/refman/8.0/en/replication-gtids-auto-positioning.html)" and "[CHANGE REPLICATION SOURCE TO Statement](https://dev.mysql.com/doc/refman/8.0/en/change-replication-source-to.html)" — the GTID-set handshake that replaces file/position bookkeeping, plus `ER_SOURCE_HAS_PURGED_REQUIRED_GTIDS` and `ER_REPLICA_HAS_MORE_GTIDS_THAN_SOURCE`.
- MySQL Reference Manual, "[Restrictions on Replication with GTIDs](https://dev.mysql.com/doc/refman/8.0/en/replication-gtids-restrictions.html)" — `enforce_gtid_consistency`: `CREATE TABLE ... SELECT`, temporary tables, mixed-engine transactions, no `sql_replica_skip_counter`.
- MySQL Reference Manual, "[Stored Function Examples to Manipulate GTIDs](https://dev.mysql.com/doc/refman/8.0/en/replication-gtids-functions.html)" — `GTID_SUBTRACT` and the GTID set-arithmetic toolkit used for errant-transaction detection.
- MySQL Shell 8.0, "[Inconsistent Transaction Sets (GTID Sets) in InnoDB ClusterSet Clusters](https://dev.mysql.com/doc/mysql-shell/8.0/en/innodb-clusterset-gtid-repair.html)" — errant-transaction detection via `clusterSet.status()` (`transactionSetErrantGtidSet`) and the clone-and-rejoin repair path.
- MySQL Reference Manual, "[Replication Source Options and Variables](https://dev.mysql.com/doc/refman/8.0/en/replication-options-source.html)" — `rpl_semi_sync_master_wait_point` AFTER_SYNC/AFTER_COMMIT semantics, `rpl_semi_sync_master_timeout`, and the wait-for-slave-count fallback.
- MySQL Reference Manual, "[Semisynchronous Replication Monitoring](https://dev.mysql.com/doc/refman/8.0/en/replication-semisync-monitoring.html)" — `Rpl_semi_sync_master_status`/`no_tx` and the silent-fallback caveat.
- MySQL Reference Manual, "[Replica Server Options and Variables](https://dev.mysql.com/doc/refman/8.0/en/replication-options-replica.html)" — `replica_parallel_type`/`replica_parallel_workers`, `replica_preserve_commit_order`, and `slave_rows_search_algorithms`.
- MySQL Reference Manual, "[Binary Logging Options and Variables](https://dev.mysql.com/doc/refman/8.0/en/replication-options-binary-log.html)" — `binlog_row_image` (FULL/minimal/noblob) and `binlog_transaction_dependency_tracking` (COMMIT_ORDER/WRITESET, `last_committed`/`sequence_number`).
- MySQL Reference Manual, "[SHOW REPLICA STATUS Statement](https://dev.mysql.com/doc/refman/8.0/en/show-replica-status.html)" — `Seconds_Behind_Source` semantics and its multithreaded-applier caveats.
- MySQL Reference Manual, "[MySQL Multi-Source Replication](https://dev.mysql.com/doc/refman/8.0/en/replication-multi-source.html)" — channels, use cases, per-channel filters, and the absence of conflict resolution.
- MariaDB Knowledge Base, "[Parallel Replication](https://mariadb.com/kb/en/parallel-replication/)" — in-order vs out-of-order parallel apply and the group-commit-based conservative mode.
- Jim Gray and Andreas Reuter, *Transaction Processing: Concepts and Techniques* (Morgan Kaufmann, 1993), Chapter 12 "Crash Recovery" and the appendix on "1-safe vs 2-safe" replication — the original vocabulary for synchronous replication safety levels.
- Martin Kleppmann, *Designing Data-Intensive Applications* (O'Reilly, 2nd ed. 2025), Chapter 5 "Replication" — leader-based, leaderless, multi-leader, conflict resolution, and the replication lag problems.
- PostgreSQL Documentation, "[Replication Progress Tracking](https://www.postgresql.org/docs/current/replication-progress.html)" and "[pg_stat_replication](https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-REPLICATION-VIEW)" — the view that powers every Postgres replication dashboard.

## Related Topics

- [Distributed: Replication](../distributed/replication.md) — the introductory counterpart.
- [Distributed: Advanced Replication](../../distributed/advanced/replication-advanced.md) — statement- vs row-based replication from the distributed-systems side, plus primary-backup production details.
- [Transactions: Two-Phase Commit](../transactions/two-phase-commit.md) — how multi-node atomic commits interact with synchronous replication.
- [Internals: WAL](../internals/wal.md) — the substrate that physical and logical replication both ship.
- [Advanced: MVCC Internals](./mvcc-internals.md) — why a standby can serve reads while applying WAL: MVCC visibility.
- [Distributed: Consensus](../distributed/consensus.md) — Raft/Paxos as the substrate for modern synchronous replication.
- [Advanced: Online Schema Change](./online-schema-change.md) — logical replication as the engine behind zero-downtime schema migrations.
