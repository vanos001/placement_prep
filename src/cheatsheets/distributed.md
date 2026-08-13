# Distributed Systems Cheat Sheet

## CAP Theorem

```
Pick 2 of 3: Consistency, Availability, Partition Tolerance
Since P is inevitable → Choose CP or AP

CP: ZooKeeper, HBase, MongoDB (strong consistency, may reject requests)
AP: Cassandra, DynamoDB, CouchDB (always available, eventual consistency)
```

## Consistency Models

| Model | Guarantee | Example |
|-------|-----------|---------|
| Linearizable | Real-time ordering | ZooKeeper |
| Sequential | Total order, no real-time | Raft |
| Causal | Cause-effect preserved | MongoDB |
| Read-your-writes | See own writes | User profiles |
| Eventual | Converges eventually | Cassandra |

## Consensus Algorithms

| Algorithm | Fault Tolerance | Complexity | Use |
|-----------|----------------|------------|-----|
| Paxos | f < n/2 | Hard to understand | Theory |
| Raft | f < n/2 | Understandable | etcd, CockroachDB |
| ZAB | f < n/2 | Similar to Raft | ZooKeeper |
| PBFT | f < n/3 (Byzantine) | O(n²) | Blockchain |

## Raft States

```
Follower → (timeout) → Candidate → (majority votes) → Leader
Leader → (term higher) → Follower
Candidate → (higher term seen) → Follower

Log Replication: Leader receives → appends → replicates → commits (majority ack)
```

## Replication Strategies

| Strategy | Latency | Consistency | Data Loss Risk |
|----------|---------|-------------|----------------|
| Synchronous | High | Strong | None |
| Asynchronous | Low | Eventual | Possible |
| Semi-sync | Medium | Hybrid | Minimal |
| Chain | Variable | Strong | Depends on position |
| Quorum (NRW) | Configurable | Tunable | W + R > N ensures consistency |

## Quorum Formula

```
N = total replicas
W = write quorum
R = read quorum

Strong consistency if: W + R > N
Example: N=3, W=2, R=2 → guaranteed consistency
```

## Partitioning

| Strategy | Pros | Cons |
|----------|------|------|
| Hash | Even distribution | Range queries hard |
| Range | Range queries efficient | Hotspots possible |
| Consistent Hashing | Minimal redistribution | Complexity |

## Consistent Hashing

```
Ring of 0 to 2^32 - 1
Server → hash → position on ring
Key → hash → walk clockwise → nearest server
Virtual nodes: multiple positions per server for balance
```

## Failure Detection

```
Heartbeat: Periodic "I'm alive" messages
Timeout: No heartbeat → suspect failure
Gossip: Peer-to-peer state propagation
Phi Accrual: Adaptive failure detector (Cassandra)
```

## Distributed Transactions

| Protocol | Blocking | Rounds | Use |
|----------|----------|--------|-----|
| 2PC | Yes (coordinator failure) | 2 | Traditional DB |
| 3PC | No (theoretically) | 3 | Rarely used |
| Saga | No | N (compensating) | Microservices |
| TCC | No | 3 | Business transactions |

## Message Delivery Guarantees

| Guarantee | Meaning | Implementation |
|-----------|---------|----------------|
| At-most-once | May lose messages | Fire and forget |
| At-least-once | May duplicate | Retry + ack |
| Exactly-once | No loss, no dup | Idempotent + dedup |

## Key Distributed Systems

| System | Type | Consensus | CAP |
|--------|------|-----------|-----|
| Kafka | Log/messaging | ISR (Raft-like) | AP→CP |
| Cassandra | Wide-column | Gossip | AP |
| ZooKeeper | Coordination | ZAB | CP |
| etcd | KV store | Raft | CP |
| CockroachDB | SQL | Raft | CP |
| DynamoDB | KV/document | Vector clocks | AP |

## Interview Quick Tips

1. Always discuss failure modes (network partition, node crash, split brain)
2. Explain consistency trade-offs clearly
3. Know when to use CP vs AP
4. Draw the architecture with data flow arrows
5. Mention monitoring, alerting, and recovery
