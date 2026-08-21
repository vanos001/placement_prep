# Spanner

Spanner is Google's globally-distributed, externally-consistent database, originally described in OSDI 2012 and substantially extended (e.g., Spanner SQL, distributed SQL queries, the Disks-as-Logs storage redesign) in subsequent papers. It is the database behind Google Ads, Google Play, and the production datastore for multi-region applications that need serializable transactions across continents. This page covers the TrueTime-based commit protocol, the Paxos-replicated tablet model, and the SQL query execution layer.

## Why Spanner Exists

Before Spanner, Google's applications used sharded MySQL (the "Megastore" layer above Bigtable). Megastore provided ACID within a "entity group" but cross-group transactions were async and slow. AdS, which updates many groups per impression, hit the ceiling hard.

Spanner solves this by providing **external consistency** (linearizability + serializability) at a global scale, with a Paxos commit latency of ~10-15 ms within a region and ~100 ms across continents. This is the strongest consistency model any production database offers.

## The Tablet Model

Spanner stores data in "tablets" (not to be confused with Android tablets — these are storage partitions). Each tablet is a Paxos-replicated group:

```text
Keyspace (ordered by key):
0x0000 ──── 0x1000 ──── 0x2000 ──── 0x3000 ──── ... ──── 0xFFFF
   ↑           ↑           ↑           ↑
Tablet 1    Tablet 2    Tablet 3    Tablet 4
{Replicas:  {Replicas:  {Replicas:  {Replicas:
 A, B, C}   A, D, E}    B, D, F}    C, E, F}}
```

Each tablet has 3+ replicas (typically 5 for cross-region configurations), distributed across datacenters. The tablet's Paxos group elects a leader; the leader holds a "leader lease" (default 10 seconds) and serves all writes for that tablet.

A Spanner cluster has hundreds of thousands of tablets. Tablet splitting is automatic when a tablet exceeds ~4 GB or has a high write rate; merging happens when neighboring tablets become small after deletes.

## The Tablet Layout and Directory

Tablets contain multiple "directories" (originally called "sub-tablets"), which are the unit of data movement. A directory is a contiguous key range, possibly small (e.g., all rows for a particular user). The `DirectoryName` is hashed and placed via the `DirectoryPlacementPolicy` to control locality (e.g., "this user's data should be in the EU and US-East regions").

A tablet can host many directories, but a directory's data is always within a single tablet. This separation lets Spanner move "hot" directories between tablets for load balancing, without moving all of a tablet's data.

## The Commit Protocol: Two-Phase Commit + Paxos

A distributed transaction in Spanner touches multiple tablets. The protocol is:

```text
Step 1: Choose a coordinator tablet (often the first write's tablet).
Step 2: Acquire locks on each participating tablet.
        Locks are Paxos-replicated: the lock is recorded in the tablet's Paxos log.
Step 3: The coordinator picks a commit timestamp s.
        s must satisfy:
          s > T_abs (the absolute time of the PREPARE message, by TrueTime)
          s > any earlier timestamp on the same tablet
        Each tablet reports its "last-observed" timestamp (in_safe_ts) to the coordinator.
        s = max(coordinator's T_abs, max of in_safe_ts from each participant)
Step 4: Coordinator writes the COMMIT record to its Paxos log (timestamp s).
Step 5: Each participant writes its COMMIT record (timestamp s) and releases locks.
Step 5: Coordinator replies to client.
```

The cleverness is in Step 3: Spanner doesn't wait for TrueTime uncertainty to elapse before assigning s. It assigns s at commit time, then **waits** before committing to ensure that no other Paxos group could have committed with a later timestamp. The wait is `commit-wait = TT.after(s)` — typically 4-7 ms with current TrueTime uncertainty.

## TrueTime and External Consistency

Spanner's external consistency rests on TrueTime, an API that returns time as an interval `[T_earliest, T_latest]` rather than a point. The interval's width is the *uncertainty* in the time estimate — typically 1-7 ms in production datacenters (driven by network delays and clock drift between GPS receivers and the CPUs using them).

The commit-wait rule guarantees:

1. The commit timestamp s is assigned before COMMIT is written.
2. No replica can see the COMMIT until the Paxos round completes (which takes longer than TrueTime uncertainty).
3. By the time another Paxos group's leader assigns a timestamp, s + uncertainty has elapsed, so the new timestamp must be > s.

This is the **commit-wait rule**: wait until `TT.after(s)` is true before releasing locks or returning to the client. The rule ensures that no concurrent transaction can pick a timestamp that would violate external consistency.

## Paxos Leader Leases and Read Freshness

Each tablet's Paxos leader holds a lease on its leadership (default 10 seconds). The lease is renewable by quorum vote every few seconds. While the lease is valid:

- The leader can serve reads locally without consulting followers (the lease proves it's still the leader).
- The leader can assign timestamps for reads up to `now + lease_remaining`, knowing no other replica could have a later timestamp.

For non-leader reads (reads served by a follower replica), the follower can serve reads up to the timestamp where it has applied all writes from the leader — `last_applied_index`. This is the Safe TimeBound (TB) for follower reads.

## SQL Query Execution

Spanner SQL (introduced 2017) is a distributed SQL query engine layered on top of the row-level storage:

```text
SQL Query "SELECT * FROM orders JOIN users ON orders.user_id = users.id
           WHERE users.country = 'IN' AND orders.total > 1000"
  │
  ▼
Query Compiler (calcite-based)
  │ - Parse, type-check
  │ - Logical plan: Join(Scan(orders), Scan(users))
  │ - Cost-based optimization: pick join order, broadcast vs. shuffle
  │
  ▼
Distributed Plan
  │ - Distributed HashJoin:
  │     1. Scan users, filter country='IN', ship to all join partitions
  │     2. Scan orders, filter total>1000, hash-partition on user_id
  │     3. Local HashJoin at each join partition
  │
  ▼
Execution
  │ - Each join partition runs on a "remote" stage (a set of CPU workers)
  │ - Intermediate results shipped via RPC
  │ - Final results aggregated by a single-stage "result" worker
```

The query engine vectorizes execution (similar to other modern SQL engines — see the [Vectorized Execution](../dbms/advanced/vectorized-execution.md) page) and pushes filters and projections down to the storage layer for early pruning.

## Schema and Data Types

Spanner schemas are strongly typed:

```sql
CREATE TABLE Orders (
    order_id   INT64 NOT NULL,
    user_id    INT64 NOT NULL,
    total      FLOAT64 NOT NULL,
    created_at TIMESTAMP NOT NULL,
    status     STRING(20),
) PRIMARY KEY (order_id, user_id);

CREATE TABLE Users (
    id         INT64 NOT NULL,
    name       STRING(100) NOT NULL,
    country    STRING(2) NOT NULL,
) PRIMARY KEY (id);

CREATE INTERLEAVE TABLE OrderItems ON PARENT Orders (
    item_id    INT64 NOT NULL,
    sku        STRING(20) NOT NULL,
    quantity   INT64 NOT NULL,
) PRIMARY KEY (order_id, user_id, item_id);
```

The `INTERLEAVE` clause is Spanner's data-co-localization primitive: `OrderItems` rows are physically stored adjacent to their parent `Orders` row, making `SELECT * FROM Orders JOIN OrderItems ON Orders.order_id = OrderItems.order_id WHERE Orders.order_id = ?` a single-tablet read (typically).

## Commits and the Paxos Log

Each Paxos group maintains a write-ahead log (WAL). Writes are first written to the WAL (via Paxos), then applied to the in-memory B-tree. The WAL is the source of truth: a replica that crashes and recovers reads the WAL from the leader and replays it.

The WAL is structured as a series of log records, each containing:

- The record's Paxos ballot (term in Raft terms).
- The record's index in the log.
- The set of mutations (write batches).
- The timestamp assigned to the batch.

Crash recovery is straightforward: replay the WAL from the last applied index. This is why Spanner's write latency is dominated by the Paxos RTT (typically 5-10 ms), not by storage I/O.

## Common Pitfalls

1. **Choosing commit timestamps naively.** The commit timestamp s is not just `now()`; it's `max(now, in_safe_ts of all participants)`. A naïve implementation that uses just `now` breaks external consistency under clock skew.
2. **Not handling TrueTime uncertainty growth.** If TrueTime uncertainty grows beyond 7 ms (network issue with GPS receiver), commit-wait latency grows proportionally. Production code must monitor `TT.uncertainty()` and alert if it exceeds a threshold.
3. **Forgetting that leader leases are time-based.** A Spanner leader that holds a 10-second lease can serve reads up to `now + 10s`. But if the leader's lease expires and a new leader takes over, the new leader must wait for the old lease to expire before serving reads — otherwise it might read stale data. This is the "leader-lease hand-off" problem and is why Spanner's leader leases are exclusive.
4. **Hot keys bottlenecking a single tablet.** Even with 100,000 tablets, a hot key (e.g., a counter for the most popular ad) is in exactly one tablet, and that tablet's leader handles all writes. The standard mitigation is "counter shards": split the counter into N virtual shards, write to a different shard per request, and aggregate reads.
5. **Cross-region transactions paying the cross-region RTT.** A transaction touching US and EU tablets pays the cross-region Paxos RTT (~100 ms) per phase. For latency-sensitive workloads, place the tablets in the same region (via DirectoryPlacementPolicy) or accept the latency.

## References

- [Spanner: Google's Globally-Distributed Database](https://research.google/pubs/pub39966/) (OSDI 2012)
- [Spanner: Becoming a SQL System](https://research.google/pubs/pub47702/) (SIGMOD 2017)
- James C. Corbett et al., "[Spanner: TrueTime, Locks, and External Consistency](https://www.youtube.com/watch?v=ql666uYU3qk)" (Google talk)
- [Spanner documentation](https://cloud.google.com/spanner/docs/)
- [The Calvin paper](https://cs.yale.edu/homes/thaas/papers/calvin.pdf) (blogs and corollary)
- [CockroachDB: The Resilience of Geo-Distributed OLTP](https://www.cockroachlabs.com/docs/stable/architecture/overview.html) — open-source comparison
