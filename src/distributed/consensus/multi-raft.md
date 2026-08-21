# Multi-Raft

Multi-Raft is the partitioned-Raft architecture introduced by Cockroach Labs (CockroachDB, 2015) and PingCAP (TiKV, 2016) to run thousands of independent Raft groups on the same cluster. Each Raft group (a "region" in TiKV, a "range" in CockroachDB) replicates its own log and elects its own leader. By partitioning data into small ranges and assigning each to a Raft group, the cluster achieves horizontal scalability for both storage and consensus throughput. This page covers the partitioning model, the per-group state, the leader-rebalancing strategy, and the trade-offs that distinguish Multi-Raft from sharded Multi-Paxos.

## Why Multi-Raft Exists

A single Raft group has a stable leader that processes all writes. The leader's CPU and the network egress from the leader's machine become the throughput ceiling for the whole group. On modern hardware, a single Raft group saturates around 100,000 writes/second — and that's the maximum a Raft-based cluster can do *without* partitioning.

Sharding solves this: split the data into N partitions, each with its own Raft group, and the cluster can do N × 100k = millions of writes/second. CockroachDB and TiKV take this approach, with N ranging from a few thousand to over 100,000 on a single cluster.

## The Range Model

Both CockroachDB and TiKV use ordered key ranges as the partition unit:

```text
Keyspace:
0x0000 ────────── 0x1000 ────────── 0x2000 ────────── 0x3000 ──── ... ──── 0xFFFF
   ↑                  ↑                  ↑                  ↑
  Range 1            Range 2            Range 3            Range 4
   {A,B,C}           {A,C,D}            {B,D,E}            {C,D,E}
```

Each range is a Raft group with its own leader, its own log, and its own replica set (typically 3 replicas). The replicas are placed on different physical machines for fault tolerance.

The partitioning is dynamic: when a range grows beyond a threshold (typically 64-96 MB), it splits into two. When adjacent ranges become small (after deletes), they merge. This dynamic partitioning is the central architectural decision that makes Multi-Raft practical.

## Per-Group State

Each Raft group has:

| State | Description |
|-------|-------------|
| `RaftLog` | An append-only log of entries; each entry has `(term, index, data)` |
| `HardState` | `current_term`, `vote_for`, `commit_index` — persisted to disk |
| `SoftState` | `leader_id`, `state` (follower/candidate/leader) — in-memory only |
| `ProgressTracker` | Per-replica `match_index`, `next_index`, `state` (Probe/Replicate/Snapshot) |
| `RegionMeta` | `range_id`, `start_key`, `end_key`, `replicas[]`, `epoch` — the partitioning metadata |

The per-group memory footprint is roughly 1-10 KB on the leader (less on followers), allowing tens of thousands of groups per machine.

## The Heartbeat Problem

Multi-Raft's central scalability challenge is heartbeats. Classical Raft sends a heartbeat from the leader to each follower every 50-100 ms. For a cluster with 100,000 ranges and 3 replicas each, the heartbeat traffic alone is 100,000 × 3 × 1 message × 10/sec = 3,000,000 messages/sec across the cluster. That is the network's saturation point.

Multi-Raft systems solve this with **batched heartbeats**:

```text
Leader L1 manages groups 1-1000 on the same physical machine M_A.
Follower F1 (also on M_A for groups 1-1000) needs to receive 1000 heartbeats per ~50ms.

Solution: M_A sends a single "coalesced heartbeat" message to F1
covering all 1000 groups. This single message contains:
  - latest_term per group (compact)
  - latest_commit_index per group
  - any new entries that need to be replicated

Total messages per 50ms tick: O(N_groups × replicas_per_group) / coalesce_factor
                              = O(100,000 × 3) / 1000 = 300 per machine per tick.
```

CockroachDB's `coalesce-heartbeats` flag and TiKV's `raft_heartbeat-tick-interval` and per-machine coalescing both implement this strategy.

## Leader Placement

The leader of each range is responsible for serving reads and writes for that range. Two key questions:

1. **Where should each leader be?** Reads benefit from local leaders; CPU and network bandwidth are the leader's bottleneck. CockroachDB uses "range rebalancing" to spread leaders evenly across the cluster.
2. **What happens when a leader fails?** The range's leader must be re-elected. With 100,000 ranges, an average of 1000 leader elections per minute is normal on a busy cluster.

The rebalancing algorithm samples leader placement across the cluster every few seconds and moves leader leases to balance load. Moves are done via Raft leadership transfer (a leader can explicitly transfer leadership to a specific follower by sending a `TimeoutNow` RPC).

## Read Local with Leader Leases

A subtle optimization: most Multi-Raft systems use **leader leases** rather than the textbook "all reads go through the leader" model. The leader holds a time-based lease on each range; during the lease, the leader can serve reads locally without an RTT to followers, because no other replica can become leader until the lease expires.

```text
Time:    0s       lease start           lease end
Leader:  |========= lease ===============|
         |       read ok       read ok    |
                                   |        read fails — leader election

Follower F (no lease): cannot serve linearizable reads. Can serve stale reads
                       with timestamp "T_lease_start" if the application allows.
```

CockroachDB calls this "epoch-based leases" (leases valid for a configurable epoch). TiKV uses "leader leases" with a fixed duration (typically 1-2 seconds).

## Cross-Range Transactions

Multi-Raft's defining production challenge is transactions that span ranges. A bank transfer from account A (in range 1) to account B (in range 2) is a two-range transaction. Without coordination, range 1's leader and range 2's leader could both commit a transaction that touches both — leading to a distributed inconsistency.

The standard solution (CockroachDB, TiKV) is **distributed transactions with a coordinator**:

```text
1. Client picks a transaction TS (timestamp).
2. Client writes to range 1 (leader 1) and range 2 (leader 2).
3. Each range's leader writes the value as a "write intent" (provisional, not yet committed).
4. Client picks one of the ranges as the "coordinator" (often the range that has the primary key).
5. Coordinator commits (via Raft) the intent.
6. Coordinator notifies other ranges asynchronously to upgrade their intents to committed values.
```

The intents are stored alongside regular data and are resolved (committed or rolled back) by background processes. Reads that encounter an unresolved intent must wait or roll back the transaction.

This adds 2 extra RTTs for transactions that span ranges: 1 to acquire the write intent, 1 to commit through the coordinator. For single-range transactions, the overhead is 0.

## Snapshot and State Transfer

Each Raft group maintains its log, but the log cannot grow forever. When the log exceeds a threshold (or by default every 4 hours), the leader creates a snapshot: a serialized state machine that captures the range's KV state at a specific log index.

Followers that fall behind (e.g., a replica recovering from downtime) request a snapshot instead of replaying the entire log:

```text
Follower F (lagging):
  send ⟨MsgSnap, last_index_in_F_log⟩ to Leader L

Leader L:
  find snapshot s where s.index > last_index_in_F_log
  send ⟨MsgSnap, snapshot_data⟩ to F

Follower F:
  replace local log with snapshot
  install snapshot into state machine
  request entries after s.index from L (regular replication)
```

Snapshot installation is expensive (~100 MB range → ~1 second to apply). Multi-Raft systems throttle the number of concurrent snapshots in flight per machine (default 1-2) to avoid CPU saturation.

## Comparison to Sharded Multi-Paxos

Spanner uses sharded Multi-Paxos: ~100 Paxos groups per cluster, each group covering many tablets. CockroachDB and TiKV use Multi-Raft: ~100,000 Raft groups per cluster, each covering one range. The trade-offs:

| Aspect | Spanner (Multi-Paxos) | CockroachDB / TiKV (Multi-Raft) |
|--------|----------------------|----------------------------------|
| Group count | ~100 per cluster | ~10^4 to 10^5 per cluster |
| Group size | Large (tablets) | Small (ranges, ~64-96 MB) |
| Leader stability | ~10 seconds per lease | ~1-2 seconds per lease |
| Cross-group tx | TrueTime + 2PC | HLC + 2PC |
| Load balancing | Tablet migration via leader election | Range split/merge, leader transfer |
| Network traffic | Lower per group, higher per machine | Higher per group, lower per machine |

Multi-Paxos with large groups minimizes consensus overhead but concentrates load on a few leaders. Multi-Raft distributes load across many small groups but at the cost of higher overhead per group (heartbeats, log management, etc.).

## Common Pitfalls

1. **Heartbeat storms on clusters with many ranges.** The default Raft heartbeat interval (50-100 ms) is too aggressive for 100,000 ranges. Production clusters raise the interval to 500 ms - 1 second and rely on coalesced heartbeats.
2. **Leader placement skew.** Without active rebalancing, the cluster tends to drift toward concentration on fast machines. Monitor `leader_count` per node and rebalance.
3. **Snapshot installation saturating disk I/O.** A single 100 MB snapshot per group is fine; 100 concurrent snapshots across many groups on the same disk saturates I/O. Throttle to 1-2 concurrent snapshots per SSD.
4. **Cross-range transactions spanning many ranges.** A transaction touching 100 ranges has 100× the latency and 100× the failure probability of a single-range transaction. Minimize range span by placing related keys in the same range (via key prefix design).
5. **Forgetting to handle range merges and splits atomically.** A range split must be a single Raft decision (the new range's metadata is committed in the old range's log before the split takes effect). Otherwise, a crash mid-split can leave a "split brain" range.

## References

- [CockroachDB architecture: Range descriptors and Multi-Raft](https://www.cockroachlabs.com/docs/stable/architecture/replication.html)
- [TiKV: Multi-Raft implementation in Rust](https://tikv.org/docs/devel/concepts/architecture/)
- Ongaro-Oki, "[In Search of an Understandable Consensus Algorithm](https://raft.github.io/raft.pdf)" (USENIX ATC 2014)
- [CockroachDB: The Resilience of Geo-Distributed OLTP](https://dl.acm.org/doi/10.1145/3183713) (SIGMOD 2017)
- [TiKV: A Distributed Transactional Key-Value Database](https://sigmod-record-publications.com/productions/sigmod.sigmod-videos?videoProdId=33) (SIGMOD 2020 tutorial)
- [PingCAP's Multi-Raft design blog series](https://en.pingcap.com/blog/multi-raft/)
