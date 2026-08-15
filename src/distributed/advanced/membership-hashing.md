# Distributed Membership & Advanced Hashing

> **Reference papers**: Karger et al. (1997) consistent hashing; Thaler & Naini (2018) rendezvous hashing; Lamping & Vingron (2014) jump consistent hash; Zhuang et al. (2011) SWIM; John et al. (2019) Hydra

## Consistent Hashing: Production Details

See [consistent hashing basics](../partitioning/consistent-hashing.md). This section covers implementation concerns and alternatives.

### Virtual Nodes (VNodes)

A single physical node is mapped to multiple points on the hash ring (typically 100-1000 vnodes per physical node). This solves two problems:

1. **Non-uniform key distribution**: with a small number of physical nodes, some nodes may get significantly more keys than others due to hash collisions. VNodes smooth this out statistically.
2. **Granular rebalancing**: when a node is added/removed, only its vnodes' key ranges move, and each vnode holds a small fraction of the total keys.

```
Physical node A has vnodes: {A_1, A_2, ..., A_100}
Physical node B has vnodes: {B_1, B_2, ..., B_100}

Hash ring (512 total vnodes, 100 per node):
  ... A_17 B_42 A_73 B_8 A_55 B_91 ...

Add node C (100 vnodes):
  Only ~1/6 of vnodes (≈85 of 512) need to move to C's vnodes
  Each vnode holds ~0.2% of keys → minimal data movement
```

### Hash Function Choice

Production consistent hashing uses non-cryptographic hash functions for speed:

| Hash Function | Speed | Distribution Quality | Used By |
---------------|-------|---------------------|----------|
| MurmurHash3 | Very fast | Excellent | Cassandra, Redis Cluster |
| xxHash | Extremely fast | Excellent | Modern replacements |
| CityHash | Very fast | Good | Google (internal) |
| SipHash | Fast | Good, DoS-resistant | Rust default |
| SHA-1/256 | Slow | Cryptographic | Rarely (overkill) |

## Rendezvous Hashing (Highest Random Weight)

Also called **HRW hashing**. Instead of a ring, for each key, compute `hash(key, node)` for every node and pick the **highest hash value**.

### Algorithm

```python
def get_node(key, nodes):
    best_node = None
    best_weight = -1
    for node in nodes:
        weight = hash(f"{key}:{node}")  # hash the (key, node) pair
        if weight > best_weight:
            best_weight = weight
            best_node = node
    return best_node
```

### Properties

- **O(n) lookup**: must hash against all n nodes (vs. O(log n) for consistent hashing with sorted vnodes)
- **Minimal disruption**: when a node is added/removed, only keys that mapped to that node change
- **No virtual nodes needed**: the hash function naturally distributes keys uniformly
- **Naturally weighted**: assign each node multiple entries in the node list to give it proportionally more keys

### Comparison with Consistent Hashing

| Property | Consistent Hashing | Rendezvous Hashing |
----------|-------------------|-------------------|
| Lookup cost | O(log n) with tree | O(n) |
| Rebalancing granularity | Depends on vnodes | Optimal (minimal movement) |
| Virtual nodes needed | Yes (for uniformity) | No |
| Implementation complexity | Medium (ring + vnodes) | Very simple |
| Best for | Large n (thousands of nodes) | Small to medium n (< 1000) |

## Jump Consistent Hashing

**Jump consistent hash** (Lamping & Vingron, 2014) is a remarkable algorithm that maps keys to buckets in O(1) time and O(1) space, with minimal disruption when buckets are added.

### Algorithm

```python
import hashlib, struct

def jump_hash(key, num_buckets):
    b = -1  # candidate bucket
    j = 0   # fingerprint
    key_bytes = str(key).encode()
    h = struct.unpack('<Q', hashlib.md5(key_bytes).digest()[:8])[0]
    
    while j < num_buckets:
        b = j
        j = int(((b + 1) / ((h / (2**32)) + 1)) * num_buckets)
        # Using the fraction of h as a "random" number to skip buckets
    
    return b
```

### Key Properties

- **O(1) space**: no ring, no vnodes, no node list
- **O(log n) time** in expectation (not O(1) — the loop runs O(log n) times on average)
- **Uniform distribution**: provably uniform under reasonable hash assumptions
- **Minimal disruption**: when going from `n` to `n+1` buckets, only `1/(n+1)` fraction of keys move
- **Limitation**: doesn't support removal of buckets (only addition) or weighted buckets

### Where Used

- **Google's internal load balancers** (reportedly)
- Any system that needs simple, uniform, one-way-growing hash assignment

## Distributed Membership Protocols

### Gossip-Based Membership (Epidemic Protocols)

Nodes periodically exchange their membership view with randomly chosen peers. Information spreads through the cluster like an epidemic — hence the name.

```
  Round 1: A knows {A,B,C}. A gossips with D.
    → D learns {A,B,C}
  Round 2: D knows {A,B,C,D}. D gossips with E.
    → E learns {A,B,C,D}
  Round 3: E gossips with F.
    → F learns {A,B,C,D,E}

  Infection spread: O(log n) rounds to reach all n nodes
```

### SWIM: Scalable Weakly-consistent Infection-style Membership

**SWIM** (Zhuang et al., 2011) is a membership protocol that detects failures in O(1) time (constant, independent of cluster size) while keeping the failure detection suspicion rate low.

#### Components

1. **Failure detection**: a node `A` pings node `B`. If `B` doesn't respond within a timeout, `A` asks a random third node `C` to ping `B` (indirect probe). If `C` also fails, `B` is suspected.
2. **Dissemination**: membership changes (joins, leaves, suspicions) are piggybacked on ping/ack messages, creating an infection-style spread.
3. **Suspect → Dead transition**: after a configurable timeout without confirmation, a suspected node is declared dead.

```
  Node A wants to check Node B:

  1. A → B: PING
     B → A: ACK           ✓ alive

  OR:
  1. A → B: PING          (timeout)
  2. A → C: PING-REQ(B)   (C, please ping B on my behalf)
     C → B: PING
     B → C: ACK
     C → A: ACK(B)         ✓ alive (via indirect probe)

  OR:
  1. A → B: PING          (timeout)
  2. A → C: PING-REQ(B)   (timeout)
     → B is SUSPECTED
  3. After suspicion_timeout without seeing B alive:
     → B is declared DEAD
```

#### SWIM Improvements (Hydra, 2019)

- **SWIM with Suspicion Mechanism**: adds a suspicion period with configurable timeout to reduce false positives
- **Hydra**: uses a more robust dissemination protocol with explicit acknowledgments for membership changes, reducing the probability of membership divergence

#### Used By

- **HashiCorp Consul**: SWIM-based membership for the agent cluster
- **Terraform**: uses Consul's SWIM for state discovery
- **Many cloud-native systems**: as a lightweight alternative to ZooKeeper-based membership

### Membership Protocol Comparison

| Protocol | Failure Detection Time | Message Complexity | Consistency | False Positive Rate | Used By |
----------|----------------------|-------------------|-------------|--------------------|----------| 
| Heartbeat (centralized) | O(1) | O(n) per heartbeat | Strong | Low | ZooKeeper |
| Gossip | O(log n) rounds | O(1) per round per node | Eventual | Medium | Cassandra, Riak |
| SWIM | O(1) | O(1) per round per node | Weakly consistent | Low | Consul |
| Phi-accrual | Probabilistic | O(1) | Adaptive | Configurable | Akka, Cassandra |

## Leases

A **lease** is a time-bounded agreement that grants a node the right to perform some action (e.g., serve as leader). Leases have a fixed duration and must be renewed before expiration.

### Lease vs Lock

| Property | Lock | Lease |
----------|------|-------|
| Duration | Held until explicitly released | Expires after a timeout |
| Safety if holder crashes | Lock may be held forever (deadlock) | Lease expires automatically (liveness) |
| Clock dependency | No | Yes (relies on synchronized clocks) |
| Revocation | Must be explicitly revoked | Expires by itself |

### Fencing

**Fencing** prevents a stale lease/lock holder from performing operations after its lease has expired. A **fencing token** (monotonically increasing number) is assigned with each lease grant. Storage systems check the fencing token and reject operations from holders with expired tokens.

```
1. Node A acquires lease with fencing token = 5
2. Network partition isolates Node A
3. Node A's lease expires
4. Node B acquires lease with fencing token = 6
5. Node A (still isolated) tries to write with token = 5
6. Storage system rejects: 5 < 6 (current fencing token is 6)
```

## Distributed Locks: Advanced Topics

See [distributed locks basics](../fundamentals/distributed-locks.md).

### Redlock (Antirez / Redis)

Redlock uses multiple independent Redis instances (at least 5) to implement a distributed lock:

1. Client acquires the lock on a majority (N/2 + 1) of Redis instances
2. The total time to acquire must be less than the lock validity time
3. On release, the client sends unlock to all instances

#### Redlock Criticism

Martin Kleppmann's 2016 critique identifies several issues:
- **GC pauses**: a client's lock may expire during a long GC pause, allowing another client to acquire it. The first client then wakes up and writes, breaking mutual exclusion.
- **Clock jumps**: if the system clock jumps forward, locks expire prematurely.
- **Network delays**: a client might not acquire a majority in time.

#### Defense

- Use fencing tokens alongside Redlock (accept Redlock for the liveness property, fencing for safety)
- Ensure lock validity time >> typical operation time + GC pause duration
- Use a daemon process for lock management to avoid GC pauses

### Distributed Semaphores

A distributed semaphore controls access to a limited resource across multiple processes:

```python
# Fair semaphore using ZooKeeper
# N = max concurrent holders

def acquire_semaphore(zk, name, N):
    # Create an ephemeral sequential node under /semaphore/name/
    path = zk.create(f"/semaphore/{name}/lock-", ephemeral=True, sequential=True)
    my_seq = int(path.split("-")[-1])
    
    children = zk.get_children(f"/semaphore/{name}")
    children.sort()
    
    if my_seq <= int(children[N - 1].split("-")[-1]):
        return True  # I'm in the first N holders
    else:
        # Watch the N-th node in front of me
        watch_node = children[my_seq - N - 1]
        zk.get(f"/semaphore/{name}/{watch_node}", watch=True)
        # Block until that node is deleted
        return False
```

### Distributed Barriers

A distributed barrier ensures all participating processes reach a certain point before any can proceed:

1. Each process enters the barrier by creating an ephemeral node
2. A process waits until the number of barrier entries reaches `N`
3. Once all `N` have entered, all proceed
4. ZooKeeper's `Sync` operation or a watch on the barrier znode count implements this

> **Interview Angle**: "How would you implement a distributed rate limiter?" Use a distributed semaphore backed by Redis (INCR + EXPIRE) or ZooKeeper. For token bucket: store the bucket count in a shared key, increment on each request, check against limit, decrement periodically. For sliding window: use a sorted set of request timestamps, remove expired entries, check size. For high throughput: use a local token bucket that periodically refills from a distributed quota service (Redis INCRBY with TTL). Cross-reference: [distributed locks](../fundamentals/distributed-locks.md).