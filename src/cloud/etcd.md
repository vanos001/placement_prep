# etcd Architecture

etcd is an open-source distributed key-value store, originally developed at CoreOS in 2013 and donated to CNCF (becoming a graduated project in 2018). It is best known as the metadata store for Kubernetes, but is also used in many other distributed systems (Rook, M3DB, patroni). etcd uses the Raft consensus algorithm for strong consistency and is designed for high availability. This page covers the architecture, the Raft protocol integration, the watch mechanism, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  etcd Cluster (typically 3 or 5 nodes)                      │
│  ┌─────────────────┐                                       │
│  │  Node 1 (leader)  │                                       │
│  │  - Receives writes│                                       │
│  │  - Replicates via  │                                       │
│  │    Raft             │                                       │
│  │  - Reads (linear)  │                                       │
│  └─────────────────┘                                       │
│  ┌─────────────────┐                                       │
│  │  Node 2 (follower)│                                       │
│  └─────────────────┘                                       │
│  ┌─────────────────┐                                       │
│  │  Node 3 (follower)│                                       │
│  └─────────────────┘                                       │
│                                                              │
│  - BoltDB (key-value store, in-memory + disk)               │
│  - WAL (write-ahead log for Raft)                            │
│  - Snapshot (periodic full state snapshot)                   │
└─────────────────────────────────────────────────────────────┘
        │
        │ gRPC API (clients)
        ▼
    Kubernetes API server, other clients
```

etcd is small (~50 MB binary) and has a simple API (CRUD on key-value pairs). Its complexity is in the Raft consensus layer.

## The Raft Protocol

etcd uses Raft for consensus. Each etcd node is a Raft server:

- **Leader**: handles all writes. Replicates to followers.
- **Followers**: receive replication from the leader, ack.
- **Candidates**: during election, request votes from other nodes.

The protocol (simplified):
1. Client sends a write to any node.
2. The node forwards to the leader (if not the leader).
3. Leader proposes the write as a Raft log entry.
4. Leader replicates to all followers.
5. Once a quorum (majority) acks, the leader commits the entry.
6. Leader applies the entry to its state machine (BoltDB).
7. Leader returns success to the client.
8. Followers apply the entry asynchronously.

This gives **strong consistency**: a committed write is durable (survives a minority of node failures) and visible to all subsequent reads.

## Linearizable Reads

By default, etcd reads are "linearizable" — they return the latest committed value. This requires:
1. The reader contacts the leader (or uses the leader's lease to verify currency).
2. The leader waits for the next Raft heartbeat (to confirm it's still the leader).
3. The leader returns the value.

This adds ~1 RTT of latency per read (the heartbeat round-trip).

For read-heavy workloads, etcd also supports "serializable" reads:
- The follower can serve the read locally (no leader check).
- The result may be stale (behind the leader by up to the Raft replication lag).

```bash
# Linearizable read (default)
etcdctl get foo

# Serializable read (faster, possibly stale)
etcdctl get foo --consistency=s
```

## The Watch Mechanism

etcd's watch lets clients subscribe to changes on a key or prefix:

```go
// Watch a key
ch := etcd.Watch(ctx, "foo")
for resp := range ch {
    for _, event := range resp.Events {
        log.Printf("Event: %s %q -> %q\n",
            event.Type, event.Kv.Key, event.Kv.Value)
    }
}
```

The watch mechanism:
1. Client opens a watch on a key range.
2. etcd streams events to the client as writes happen.
3. The client gets a continuous event log (with revision numbers).

If the client disconnects and reconnects, it can resume from the last-seen revision:
```go
ch := etcd.Watch(ctx, "foo", etcd.WithRev(rev))
```

This is critical for Kubernetes: the API server watches etcd for resource changes (pods, services, etc.) and triggers reconciliation loops.

## The Lease Mechanism

Leases are time-bounded keys that auto-expire:

```go
// Grant a lease with 30-second TTL
lease, _ := etcd.Lease.Grant(ctx, 30)

// Put a key with the lease
etcd.Put(ctx, "service/myservice", "10.0.0.1:8080", etcd.WithLease(lease.ID))

// The key auto-deletes after 30s unless the lease is kept alive
etcd.Lease.KeepAlive(ctx, lease.ID)
```

This is the basis for service discovery:
- A service registers with a lease.
- It periodically sends keep-alives.
- If the service dies, the lease expires and the key is removed.
- Watchers (other services) see the key disappear.

## Production Deployment

A 3-node etcd cluster is the minimum for HA (tolerates 1 node failure). A 5-node cluster tolerates 2 failures.

```bash
# Start an etcd node
etcd --name etcd1 \
  --data-dir /var/lib/etcd \
  --listen-client-urls https://10.0.0.1:2379 \
  --advertise-client-urls https://10.0.0.1:2379 \
  --listen-peer-urls https://10.0.0.1:2380 \
  --initial-cluster etcd1=https://10.0.0.1:2380,etcd2=https://10.0.0.2:2380,etcd3=https://10.0.0.3:2380 \
  --initial-cluster-token my-cluster \
  --initial-cluster-state new
```

Key flags:
- `--data-dir`: where etcd stores data (BoltDB + snapshots + WAL).
- `--listen-peer-urls`: the URL other etcd nodes connect to (for Raft replication).
- `--listen-client-urls`: the URL clients connect to.
- `--initial-cluster`: the list of all nodes in the cluster.

## Production Performance

etcd's published performance on a 3-node cluster (NVMe SSDs):
- Write throughput: 10K writes/sec sustained.
- Read latency (linearizable): ~5 ms.
- Read latency (serializable): ~1 ms.
- Storage: ~10 GB typical for Kubernetes metadata (1000s of resources).

For comparison, ZooKeeper (a similar system) is similar in throughput but has a smaller feature set (no watch on prefixes).

## Production Use Cases

### Kubernetes Metadata Store

The dominant use: Kubernetes uses etcd to store:
- All cluster resources (pods, services, deployments, secrets, configmaps).
- Cluster state (node status, scheduling decisions).
- Watch events (for reconciliation loops).

A Kubernetes cluster typically runs a 3-node etcd cluster (often on the same nodes as the API server, with mTLS).

### Service Discovery

Services register with etcd (with a lease); clients discover via watch:

```go
// Service registers
lease, _ := etcd.Grant(ctx, 10)
etcd.Put(ctx, "services/my-svc/instance-1", "10.0.0.1:8080", etcd.WithLease(lease.ID))
// Keep-alive in background
etcd.KeepAlive(ctx, lease.ID)

// Client discovers
ch := etcd.Watch(ctx, "services/my-svc/", etcd.WithPrefix())
for resp := range ch {
    // Update local service list
}
```

### Distributed Configuration

Configuration stored in etcd, watched by services:

```go
ch := etcd.Watch(ctx, "config/myapp/", etcd.WithPrefix())
for resp := range ch {
    applyConfig(resp.Events)
}
```

This is the basis for tools like Vitess, M3DB, and CoreDNS configuration.

### Distributed Locks

```go
// Acquire a lock (with lease)
lease, _ := etcd.Grant(ctx, 60)
resp, _ := etcd.Txn(ctx).
    If(clientv3.Compare(clientv3.CreateRevision("lock/foo"), "=", 0)).
    Then(clientv3.OpPut("lock/foo", "owner", etcd.WithLease(lease.ID))).
    Else(clientv3.OpGet("lock/foo")).
    Commit()
// If resp.Succeeded, we have the lock.
```

The lock is held until the lease expires (or the holder releases it). Other clients try the same Txn; only one succeeds.

## Common Pitfalls

1. **Forgetting that etcd's quorum requires a majority.** A 3-node cluster tolerates 1 failure; a 2-node cluster tolerates 0 failures. Use odd-numbered cluster sizes.

2. **Forgetting that etcd's disk I/O is on the critical path.** Every write must be fsync'd to the WAL. Slow disk = slow etcd = slow Kubernetes. Use NVMe SSDs.

3. **Forgetting that etcd's memory grows with the data size.** A 10 GB etcd needs ~20 GB of RAM (in-memory cache). Plan capacity.

4. **Forgetting that defragmentation is needed.** etcd's BoltDB doesn't auto-defragment. Run `etcdctl defragment` periodically (every few weeks).

5. **Forgetting to back up etcd.** A lost etcd cluster = lost Kubernetes state. Take periodic snapshots (`etcdctl snapshot save`).

6. **Forgetting that watches are server-side.** The server buffers events while the client is disconnected (for ~1 hour by default). After that, the client must do a full resync.

## Comparison to ZooKeeper and Consul

| Aspect | etcd | ZooKeeper | Consul |
|--------|------|-----------|--------|
| Origin | CoreOS 2013 | Yahoo 2008 | HashiCorp 2014 |
| Consensus | Raft | ZAB (similar to Paxos) | Raft |
| API | gRPC + REST | Custom protocol | HTTP/gRPC |
| Watch on prefix | Yes | Yes (limited) | Yes |
| Lease/TTL | Yes | Ephemeral nodes | Yes |
| Service discovery | Via watch | Via watch | First-class |
| Best for | Kubernetes metadata | Hadoop, Kafka | Service discovery, config |

etcd and ZooKeeper are similar in features; etcd's API is more modern (gRPC). Consul is more focused on service discovery.

## References

- [etcd documentation](https://etcd.io/docs/)
- Ongaro & Oki, "[In Search of an Understandable Consensus Algorithm (Raft)](https://raft.github.io/raft.pdf)" (USENIX ATC 2014)
- [etcd GitHub repository](https://github.com/etcd-io/etcd)
- [etcd Performance tuning](https://etcd.io/docs/latest/tuning/)
- [etcd disaster recovery](https://etcd.io/docs/latest/admin_guide/#disaster-recovery)
- [Kubernetes: etcd maintenance](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
- [LWN: etcd internals (2018)](https://lwn.net/Articles/750830/)
