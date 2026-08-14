# Redis Cluster Architecture

## Overview

Redis Cluster is Redis's native horizontal scaling solution, providing sharding and high availability without a proxy layer. This document covers the internal mechanics: hash slot assignment, the Gossip protocol, replication, Sentinel, and when to use each approach.

> **Relation to other docs:** For a quick overview of cluster hash slots, see [patterns-and-internals.md](./patterns-and-internals.md). For persistence mechanisms that interact with replication, see [persistence.md](./persistence.md).

## Redis Cluster: Hash Slots

Redis Cluster shards data across **16384 hash slots** (0-16383). Every key is assigned to a slot via:

```
slot = CRC16(key) % 16384
```

Each master node owns a contiguous range of slots. Clients or cluster nodes route commands to the correct node based on the slot.

### Hash Tags

For multi-key operations (e.g., `MGET`, `SUNION`, Lua scripts), all keys must be on the same node. **Hash tags** allow grouping related keys:

```
user:{1001}:profile  → slot for "1001"
user:{1001}:sessions → slot for "1001"  (same slot!)
user:1002:profile    → slot for "user:1002:profile"  (different slot)
```

Only the content within `{}` is hashed. This is essential for atomic multi-key operations.

### Key Migration

When resharding, slots are moved between nodes. During migration, both the source and destination nodes track the slot's state:

1. **Importing**: Destination node accepts writes for the migrating slot but returns `ASK` redirection for reads not yet migrated
2. **Migrating**: Source node returns `MOVED` redirection to the destination for keys already moved

Clients must follow `MOVED` (update their slot map permanently) and `ASK` (one-time redirection with `ASKING` command). This is handled automatically by smart clients (redis-cli, Jedis, Lettuce, go-redis).

## Node Communication: Gossip Protocol

Redis Cluster nodes communicate via a **gossip protocol** over a dedicated bus (port = data port + 10000). Each node maintains information about every other node.

### Gossip Message Types

| Message | Purpose | Frequency |
|---------|---------|-----------|
| **PING** | Exchange node state, slot config, epoch | Every second (to random node) |
| **PONG** | Reply to PING or MEET | On receipt |
| **MEET** | Join a new node to the cluster | Manual (`CLUSTER MEET`) |
| **FAIL** | Broadcast that a node is failed | On failure confirmation |

### Gossip Headers (exchanged in every PING/PONG)

Each gossip message includes:

```
Node: id, ip:port, flags (MASTER/REPLICA/FAIL/PFAIL/NOADDR)
Config Epoch: monotonically increasing version for slot ownership
  Slot Bitmap: which 16384 bits = which slots this node owns
  State: slots_in_bits[], slaveof, ping_sent, pong_recv, config_epoch
  Gossip section: info about 10 random other nodes (for rumor propagation)
```

### Failure Detection

```
Node A pings Node B
  ↓ (no PONG within cluster_node_timeout, default 15s)
A marks B as PFAIL (possibly failed) — local state only
  ↓ (A gossips B's PFAIL status to C and D)
C and D also mark B as PFAIL
  ↓ (majority of masters agree B is PFAIL)
B is marked as FAIL (globally) — triggers failover
```

A node needs a **majority of masters** to agree on PFAIL before marking FAIL. This prevents a single misbehaving node from incorrectly declaring others failed.

## Replication: Master-Slave

### Async Replication Mechanics

```
Master                          Replica
  │                               │
  │── Full Resync (initial) ────→│  (RDB snapshot + buffer)
  │                               │
  │── REPLCONF ACK ──────────────│  ← periodic ack
  │                               │
  │── Write Command ──→(apply)──→│  (replication stream)
  │                               │
  │── REPLCONF ACK ──────────────│  ← confirms offset received
  │                               │
```

- Replication is **asynchronous**: the master does not wait for replica acks before acknowledging writes
- Replicas send `REPLCONF ACK` with the replication offset they've processed
- Master tracks `repl_backlog` (a circular buffer of recent write commands) for partial resyncs
- If a replica disconnects and reconnects within `repl_backlog_size`, it does a **partial resync** (catches up from the backlog) instead of a full RDB resync

### Replication Lag Metrics

- `repl_backlog_size`: Size of the replication backlog (default 1MB)
- `master_repl_offset`: Master's current replication offset
- `slave_repl_offset`: Replica's current replication offset
- `lag` = `master_repl_offset - slave_repl_offset`: bytes the replica is behind

## Sentinel: Monitoring and Failover

Redis Sentinel provides **automatic failover** for non-cluster Redis setups (master-replica without sharding).

### Sentinel Architecture

```
               Sentinel 1 ──┐
                              ├── Gossip among Sentinels
               Sentinel 2 ──┤
                              │
               Sentinel 3 ──┘
                              │
              ┌───────────────┘
              ▼
         Monitor Master
              │
       ┌──────┴──────┐
    Replica 1    Replica 2
```

### Failover Process

1. **SDOWN (Subjective Down)**: A single Sentinel marks the master as down (no PONG within `down-after-milliseconds`)
2. **ODOWN (Objective Down)**: `quorum` Sentinels agree the master is down
3. **Failover election**: Sentinels use Raft-like protocol to elect a leader Sentinel to perform failover
4. **Replica promotion**: Leader Sentinel sends `SLAVEOF NO ONE` to the selected replica
5. **Reconfiguration**: Leader Sentinel sends `SLAVEOF new_master` to remaining replicas
6. **Config update**: Clients are notified of the new master via Pub/Sub (`+switch-master` channel)

## Cluster vs Sentinel Comparison

| Aspect | Redis Cluster | Sentinel |
--------|--------------|----------|
| **Sharding** | Yes (16384 hash slots) | No (single master) |
| **Max keys** | Limited by total node memory | Limited by single node memory |
| **Failover** | Automatic (Gossip-based) | Automatic (Sentinel-based) |
| **Multi-key ops** | Only within same hash slot | No restriction |
| **Client requirements** | Smart client (slot-aware) | Any client (single endpoint) |
| **Deployment complexity** | Higher (≥6 nodes recommended) | Lower (3 Sentinels + master + replica) |
| **Transactional support** | Limited (keys must be in same slot) | Full (single node) |
| **Pub/Sub** | Routed to correct node | Works normally |
| **Best for** | Large datasets, horizontal scaling | HA for single-node workloads |

## Redis on Flash

Redis on Flash (RoF) stores frequently accessed keys in memory and less frequently accessed values on SSD/Flash:

- Keys and metadata: always in DRAM
- Values: stored on Flash, with a DRAM cache for hot values
- Uses `redis-rof` module (fork of Redis with Intel Optane integration)
- Useful when the dataset exceeds available DRAM but is smaller than Flash capacity
- Tradeoff: ~10x lower cost per GB vs all-DRAM, but higher latency for cold values (~100μs vs ~1μs)

## Sharding Strategies

| Strategy | Mechanism | Client-Side or Proxy? |
----------|-----------|----------------------|
| **Redis Cluster** | Built-in 16384 hash slots | Client-side routing (smart client) |
| **Client-side sharding** | Application hashes keys to nodes | Client-side (manual) |
| **Twemproxy** | Proxy with consistent hashing | Proxy (single point of failure) |
| **Predixy** | Proxy with multi-threading | Proxy |
| **Redis Cluster + Envoy** | Envoy as L7 proxy to cluster | Proxy (no SPOF with multiple Envoy instances) |
| **Codis** | Proxy + ZooKeeper/etcd for slot management | Proxy |

Redis Cluster is now the recommended approach for production sharding. Proxies like Twemproxy are legacy solutions with single points of failure and limited protocol support (no Lua scripting, no pub/sub routing).

## Interview Questions

**Q: How does Redis Cluster route a command to the correct node?**
A: The client computes `CRC16(key) % 16384` to determine the slot, then checks its local slot-to-node mapping (cached from `CLUSTER SLOTS`). It sends the command directly to the owning node. If the slot has migrated, the node returns a `MOVED` error with the new node address. The client updates its mapping and retries. Smart clients (Jedis, Lettuce, go-redis) handle this automatically.

**Q: What is the difference between `MOVED` and `ASK` redirection?**
A: `MOVED` means the slot has been **permanently** reassigned to another node. The client updates its slot map permanently. `ASK` means the slot is being **migrated** — the key exists on the target node but the slot hasn't fully moved yet. The client sends a one-time `ASKING` command to the target node before the actual command, without updating its slot map.

**Q: How does Sentinel decide when to fail over?**
A: (1) A Sentinel marks the master as SDOWN (subjectively down) if no PONG within `down-after-milliseconds`. (2) It gossips this to other Sentinels. (3) When `quorum` (default 2) Sentinels agree, the master is ODOWN (objectively down). (4) Sentinels elect a leader via Raft-like protocol. (5) The leader selects the best replica (by `replica-priority`, then by replication offset) and promotes it to master.

**Q: Why does Redis Cluster require at least 3 master nodes?**
A: Redis Cluster uses a majority-based failure detection and failover protocol. With 3 masters, any single node failure can be detected by the remaining 2 (majority = 2 out of 3). With 2 masters, a network partition could cause each side to have 1 master, and neither can achieve majority, preventing failover. The recommended minimum is 3 masters + 3 replicas = 6 nodes.

**Q: How is partial resync more efficient than full resync in replication?**
A: After a replica disconnects, the master maintains a `repl_backlog` (circular buffer, default 1MB) of recent write commands. If the replica reconnects and its `repl_offset` is still within the backlog, it receives only the missed commands (partial resync) instead of a full RDB snapshot. If the offset has been evicted from the backlog (long disconnection or small backlog), a full resync (RDB transfer) is required.

**Q: When would you choose Sentinel over Redis Cluster?**
A: Choose Sentinel when: (1) your dataset fits on a single node, (2) you need multi-key transactions (Lua scripts, pipelines) without hash tag constraints, (3) simplicity is prioritized. Choose Cluster when: (1) the dataset exceeds single-node memory, (2) you need horizontal write scalability, (3) you can tolerate hash slot constraints for multi-key operations.

## References

- [Redis Cluster Specification](https://redis.io/docs/reference/cluster-spec/)
- [Redis Sentinel Documentation](https://redis.io/docs/management/sentinel/)
- [Redis Replication](https://redis.io/docs/management/replication/)
