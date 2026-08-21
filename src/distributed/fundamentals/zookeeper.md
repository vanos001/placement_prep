# Apache ZooKeeper

Apache ZooKeeper is an open-source distributed coordination service, originally developed at Yahoo in 2008 and donated to Apache the same year. It provides a hierarchical key-value store (a "znode" tree) with strong consistency guarantees, used by many distributed systems (Kafka, Hadoop HDFS, HBase, Solr) for configuration, synchronization, and metadata. This page covers the architecture, the znode model, the ZAB consensus protocol, and the comparison to etcd and Consul.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  ZooKeeper Cluster (typically 3, 5, or 7 nodes)             │
│  ┌─────────────────────┐                                   │
│  │  Node 1 (leader)      │                                   │
│  │  - Handles writes     │                                   │
│  │  - ZAB replication    │                                   │
│  │  - In-memory + disk   │                                   │
│  └─────────────────────┘                                   │
│  ┌─────────────────────┐                                   │
│  │  Node 2 (follower)   │                                   │
│  └─────────────────────┘                                   │
│  ┌─────────────────────┐                                   │
│  │  Node 3 (follower)   │                                   │
│  └─────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
        │
        │ custom protocol (clients)
        ▼
    Kafka, HBase, HDFS NameNode HA, etc.
```

ZooKeeper uses the ZAB (ZooKeeper Atomic Broadcast) protocol for consensus, which is similar to Paxos but optimized for the primary-backup use case.

## The Znode Model

ZooKeeper stores data in a tree of "znodes" (analogous to files in a filesystem):

```text
/
├── app1
│   ├── config
│   │   ├── db_host   = "db1.example.com"
│   │   └── log_level = "info"
│   ├── members
│   │   ├── member_1  (ephemeral)
│   │   └── member_2  (ephemeral)
│   └── leader_election
│       └── lock_001   (ephemeral, sequential)
└── app2
    └── ...
```

Each znode has:
- **Path**: a unique path (like a file path).
- **Data**: a small byte array (max ~1 MB).
- **Children**: sub-znodes.
- **Stat**: metadata (version, creation time, last modification time, children count).

## Znode Types

- **Persistent**: survives client disconnect. Created with `create -e=false`.
- **Ephemeral**: deleted when the client's session ends. Created with `create -e=true`.
- **Persistent Sequential**: name has a monotonically increasing suffix. Created with `create -s=true`.
- **Ephemeral Sequential**: both ephemeral and sequential.

Ephemeral znodes are the basis for:
- Service registration (ephemeral znode per service instance; gone if instance dies).
- Locks (ephemeral znode per lock holder).

Sequential znodes are the basis for:
- Leader election (the lowest-numbered sequential znode wins).
- Distributed queues (FIFO ordering).

## Watches

Clients can set a "watch" on a znode:

```bash
# Watch for changes to /app1/config
[zk: localhost:2181] get -w /app1/config
db1.example.com

# (blocks until the znode changes)

WATCHER::

WatchedEvent state:SyncConnected type:NodeDataChanged path:/app1/config
```

Watches are one-shot — after firing, the client must re-set the watch to see future changes. This prevents the "thundering herd" of too many watchers being notified per change.

Watches can be on:
- Data changes (znode's value modified).
- Children changes (a child added/removed).
- Existence (znode created/deleted).

## The ZAB Protocol

ZAB (ZooKeeper Atomic Broadcast) is the consensus protocol. It's similar to Paxos but optimized for the primary-backup model:

1. **Leader election**: at startup (or on leader failure), nodes elect a leader.
2. **Discovery**: the leader discovers the latest committed state.
3. **Synchronization**: the leader brings all followers up to date.
4. **Broadcast**: the leader accepts writes, broadcasts to followers, commits on quorum ack.

A write goes through:
1. Client sends write to any node (forwarded to leader).
2. Leader proposes a write (as a ZAB message).
3. Followers ack.
4. Once quorum acks, leader commits.
5. Leader applies to state machine; followers apply asynchronously.
6. Leader returns success to client.

This is essentially Multi-Paxos with the "stable leader" optimization.

## Production Use Cases

### Hadoop HDFS NameNode HA

HDFS uses ZooKeeper for NameNode failover:
- The active NameNode holds an ephemeral znode.
- The standby watches this znode.
- If the active fails, the znode disappears; the standby takes over.

### Kafka Coordination

Kafka uses ZooKeeper (pre-2.8) for:
- Broker registration (ephemeral znode per broker).
- Topic/partition metadata.
- Consumer group coordination (since 2.4, replaced by the group coordinator).
- Controller election (the broker that's the controller).

Kafka 2.8+ supports running without ZooKeeper (KRaft mode), but most deployments still use ZooKeeper.

### HBase Coordination

HBase uses ZooKeeper for:
- RegionServer registration (ephemeral znode per RegionServer).
- Master leader election.
- Region assignment (znode per region with current location).

### Solr Cloud

Solr uses ZooKeeper for:
- Cluster metadata (collections, shards, replicas).
- Leader election (per shard).

### Distributed Locks

```java
// Acquire a lock using ephemeral sequential znodes
String myLock = zk.create("/locks/my-resource/lock-", data, 
                          CreateMode.EPHEMERAL_SEQUENTIAL);
List<String> locks = zk.getChildren("/locks/my-resource", false);
Collections.sort(locks);
if (myLock.endsWith(locks.get(0))) {
    // I'm the lowest-numbered; I have the lock.
    // Do the work.
    zk.delete(myLock, -1);
} else {
    // Wait for the previous znode to be deleted.
    String prevLock = "/locks/my-resource/" + locks.get(
        Collections.binarySearch(locks, myLock.substring(myLock.lastIndexOf('/') + 1)) - 1);
    zk.exists(prevLock, true);  // Set watch
    // (Block until watch fires)
    // I now have the lock.
    // Do the work.
    zk.delete(myLock, -1);
}
```

This is the canonical "lock with fairness" pattern — locks are granted in FIFO order.

## Production Performance

ZooKeeper's performance on a 5-node cluster:
- Write throughput: ~10K writes/sec.
- Read latency: ~1 ms (cached locally).
- Write latency: ~5 ms (consensus round-trip).
- Storage: in-memory (typically <1 GB).

ZooKeeper is fast for read-heavy workloads (any follower can serve reads). Writes are slower (consensus round-trip).

## Comparison to etcd and Consul

| Aspect | ZooKeeper | etcd | Consul |
|--------|-----------|------|--------|
| Origin | Yahoo 2008 | CoreOS 2013 | HashiCorp 2014 |
| Consensus | ZAB (Paxos-like) | Raft | Raft |
| API | Custom binary | gRPC + REST | HTTP/gRPC |
| Watch granularity | Per-znode | Per-key + prefix | Per-key + prefix |
| Ephemeral nodes | Yes | Leases | Leases |
| Multi-DC | Limited (no native support) | Limited | First-class |
| Production users | Hadoop, Kafka, Solr, HBase | Kubernetes | Service discovery, mesh |

ZooKeeper is the oldest; etcd is more modern; Consul is the most feature-rich.

## Common Pitfalls

1. **Forgetting that ZooKeeper needs an odd number of nodes.** Even-numbered clusters have no quorum advantage over odd. Use 3 or 5.

2. **Forgetting that znode data is small (1 MB max).** For large data, store in HDFS or S3 and put a pointer in ZooKeeper.

3. **Forgetting that watches are one-shot.** After a watch fires, the client must re-register. Naive code may miss intermediate changes.

4. **Forgetting that ephemeral nodes depend on the session.** A network partition may cause the session to expire (znodes disappear). Use long session timeouts (30-60 seconds) for production.

5. **Forgetting that ZooKeeper doesn't scale writes well.** All writes go through the leader; ~10K writes/sec is the typical max. Don't use ZooKeeper as a high-throughput data store.

6. **Forgetting to clean up old znodes.** Persistent znodes accumulate; clean up unused ones periodically.

## References

- [Apache ZooKeeper documentation](https://zookeeper.apache.org/doc/current/)
- Hunt et al., "[ZooKeeper: Wait-free Coordination for Internet-Scale Systems](https://www.usenix.org/legacy/event/atc10/tech/full_papers/Hunt.pdf)" (USENIX ATC 2010)
- [ZooKeeper: Reliable Coordination Service](https://zookeeper.apache.org/doc/r3.8.0/zookeeperOver.html)
- [ZAB: ZooKeeper Atomic Broadcast](https://zookeeper.apache.org/doc/r3.8.0/zookeeperHierarchical.html)
- [ZooKeeper recipes for locks, leader election](https://zookeeper.apache.org/doc/r3.8.0/recipes.html)
- [Curator: ZooKeeper client library (Apache)](https://curator.apache.org/)
- [Kafka KRaft (without ZooKeeper)](https://developer.confluent.io/blog/kafka-without-zookeeper-a-gateway-to-kafka-3-0/)
- [LWN: ZooKeeper overview (2020)](https://lwn.net/Articles/820130/)
