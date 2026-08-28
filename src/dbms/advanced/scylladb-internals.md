# ScyllaDB Internals: Thread-per-Core Shared-Nothing on Seastar

Cassandra's architecture spends a shocking fraction of its CPU on
coordination: lock contention, cross-core cache coherence, thread
context switches, and executor queues - the overhead of running a
distributed database's I/O stack on a kernel-thread-per-request model.
ScyllaDB's founding bet was to rebuild the same data model on a
**thread-per-core, shared-nothing** runtime (Seastar) where each core is
a self-contained mini-database: no locks, no cross-core state sharing,
no syscalls in the hot path. This page covers the architectural
consequences - token ownership, shard-local storage, I/O scheduling -
that make ScyllaDB a different machine under the same CQL surface.

The Cassandra baseline: [cassandra-architecture](../nosql/cassandra-architecture.md)
covers the data model, gossip, and consistency levels that ScyllaDB
inherits; [lsm-tree deep dive](../../storage/advanced/lsm-tree-deep.md)
covers the storage engine family both use.

## Seastar: the runtime that changes the rules

Seastar's programming model has three rules:

1. **One thread per core, pinned** - no thread migrations, no scheduler
   jitter; the core count is the parallelism.
2. **No shared state** - threads (shards) communicate by explicit
   message passing (`sharded<T>` services, futures). A data structure
   belongs to exactly one shard; sharing means sending a message, which
   makes the cost visible in the code instead of hidden in cache-coherence
   traffic.
3. **Futures/promises instead of blocking** - every I/O is async from
   the API down; no thread pools, no blocking syscalls (Seastar
   implements its own userspace network and disk stacks on DPDK/io_uring
   or epoll/aio).

The consequence is predictable latency: no locks to contend on, no
kernel scheduler to fight, no cross-core cache-line bouncing (the
false-sharing tax that caps Cassandra's tail). The cost: every algorithm
must be shard-local by design, and any data that crosses shards pays an
explicit message.

## Token ownership mapped to cores

Cassandra's ring assigns token ranges to *nodes* (vnodes spread ranges
across the node's threads randomly). ScyllaDB assigns token ranges to
*shards* deterministically: a shard owns a contiguous token range, so a
given partition always lands on the same core of the replica node.

```text
  Cassandra node (vnodes):              ScyllaDB node (shard-per-range):
  core0: [t37, t1024, t5001]            core0: [t0  .. t2048)
  core1: [t88, t2048, t7710]            core1: [t2048.. t4096)
  core2: [t250, t4096, t991]            core2: [t4096.. t6143)
  (any partition hits any core;         (partition P (hash h) -> shard
   coordination + handoffs inside)       floor mapping; no handoff)
```

Shard-aware drivers take this further: the client hashes the partition
key, picks the connection to the *replica shard that owns it*, and the
request lands on the right core directly - no internal forwarding at
all. A query for partition P is served by one core end-to-end: its
row cache, memtable, SSTables, and compaction all live on that core.

## Shard-local storage engine

Each shard owns its own memtables, SSTables, commitlog segment, row
cache, and compaction workload:

- **No cross-shard compaction**: an SSTable belongs to one shard; the
  compaction manager runs per-shard with the I/O scheduler arbitrating
  between compaction, memtable flush, and reads.
- **The I/O scheduler** is the load-bearing piece: it enforces
  per-class shares (compaction vs flush vs reads) on the disk, converting
  "compaction storm slows reads" from a Cassandra outage into a
  bounded-share slowdown.
- **Row cache and key cache** are shard-local, sized per core - no
  cache-coherence protocol exists to break.

Replication stays ring-level (RF across nodes, NetworkTopologyStrategy);
each shard is a replica *sub-unit*. Raft (ScyllaDB's replacement for
Cassandra's Paxos-based LWT) manages schema and topology metadata,
running on dedicated shards.

## The demo: shard skew vs vnode skew

```python
#!/usr/bin/env python3
"""Token-to-core mapping skew: ScyllaDB contiguous shard ranges vs
Cassandra-style vnodes.

Take 1M partition hashes; map them to cores two ways:
  scylla : shard = floor(token / (TOK_MAX / n_shards))  (contiguous)
  cassandra vnodes: each core owns V random ranges; a token belongs to
  whichever core's range covers it (deterministic here via sorted
  boundary list + bisect-free linear scan kept O(1) by construction)

Report the load distribution (max/mean ratio) for both. Deterministic
(seed fixed). Pure stdlib."""
import random

N_PARTS = 1_000_000
TOK_MAX = 2**31
SEED = 42

rng = random.Random(SEED)
tokens = sorted(rng.randrange(TOK_MAX) for _ in range(N_PARTS))


def shard_counts_scylla(n_shards):
    counts = [0] * n_shards
    width = TOK_MAX // n_shards
    for t in tokens:
        counts[min(t // width, n_shards - 1)] += 1
    return counts


def shard_counts_vnodes(n_shards, v_per_shard=256):
    """random virtual nodes per core; token -> owning core"""
    bounds = []
    for core in range(n_shards):
        for _ in range(v_per_shard):
            bounds.append((rng.randrange(TOK_MAX), core))
    bounds.sort()
    owners = [c for _t, c in bounds]
    counts = [0] * n_shards
    # each token maps to the first vnode boundary >= token (circular ring
    # simplified linearly; skew behavior is the same)
    idx = 0
    for t in tokens:
        while idx < len(bounds) and bounds[idx][0] < t:
            idx += 1
        if idx >= len(bounds):
            idx = 0
        counts[owners[idx]] += 1
    return counts


def report(name, counts):
    mean = sum(counts) / len(counts)
    mx = max(counts)
    mn = min(counts)
    print(f"  {name:<28} max/mean={mx/mean:5.2f} min/mean={mn/mean:5.2f} "
          f"counts={counts}")

print(f"1M partition hashes, deterministic seed={SEED}")
for shards in (8, 16):
    print(f"--- {shards} shards/cores ---")
    report("ScyllaDB contiguous ranges", shard_counts_scylla(shards))
    report("Cassandra vnodes (V=256)", shard_counts_vnodes(shards))
print()
print("ScyllaDB's uniformity comes from hashing: uniform tokens over")
print("contiguous ranges are uniform by construction. Vnode spread adds")
print("range-overlap randomness: the max/mean ratio quantifies the")
print("hot-core problem vnode placement inflicts on caches and compaction.")
```

```text
1M partition hashes, deterministic seed=42
--- 8 shards/cores ---
  ScyllaDB contiguous ranges   max/mean= 1.00 min/mean= 0.99 counts=[125233, 125404, 124714, 124228, 125521, 125362, 124692, 124846]
  Cassandra vnodes (V=256)     max/mean= 1.10 min/mean= 0.93 counts=[125333, 137179, 131887, 116491, 119252, 121888, 121221, 126749]
--- 16 shards/cores ---
  ScyllaDB contiguous ranges   max/mean= 1.01 min/mean= 0.99 counts=[62579, 62654, 62627, 62777, 62542, 62172, 62111, 62117, 62688, 62833, 62476, 62886, 62483, 62209, 62346, 62500]
  Cassandra vnodes (V=256)     max/mean= 1.14 min/mean= 0.90 counts=[67722, 55968, 66518, 63657, 63001, 67667, 64749, 60261, 64429, 59301, 58422, 61704, 59158, 56325, 71330, 59788]

ScyllaDB's uniformity comes from hashing: uniform tokens over
contiguous ranges are uniform by construction. Vnode spread adds
range-overlap randomness: the max/mean ratio quantifies the
hot-core problem vnode placement inflicts on caches and compaction.
```

## Production notes

- **When it wins**: high ops/sec per node with tail-latency SLOs, big
  machines (the thread-per-core model shines as core counts grow),
  heavy compaction periods. The shared-nothing design scales with
  hardware rather than against it.
- **Consistency**: the same CQL consistency levels, same quorum math -
  ScyllaDB is not "more consistent", it is the same distributed
  protocol with a faster single-node path.
- **Operational differences**: no JMX-era tooling (ScyllaDB Manager,
  per-shard metrics), tablet-based replication (post-5.0) replacing
  vnode-era range ownership, and the same tombstone/GC-grace pitfalls
  as Cassandra - the data model did not change, so its dangers did not
  either.

## Interview probes

- Why does vnode-to-core randomness hurt caches and compaction, and how
  does contiguous shard ownership fix both at once?
- A partition becomes a hot key (1M ops/s). What happens on Cassandra
  vs ScyllaDB, and what shard-level mechanism can split it?
- Where does Seastar's no-blocking rule force architectural changes
  that a thread-pool database can avoid? Name three.
- What problem does Raft-based schema management solve that Paxos-based
  LWT did not?

## References

1. [ScyllaDB architecture documentation](https://opensource.docs.scylladb.com/stable/architecture/)
   - the shard-per-core ownership model and storage engine layout.
2. [Seastar](https://seastar.io/) - the shared-nothing async runtime:
   futures, sharded services, and the userspace network/disk stacks.
3. [ScyllaDB on GitHub](https://github.com/scylladb/scylladb) - the
   source of truth for the compaction manager and I/O scheduler.
4. [Cassandra architecture (this repo)](../nosql/cassandra-architecture.md)
   - the inherited data model, gossip, and consistency surface.
