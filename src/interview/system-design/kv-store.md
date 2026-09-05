# Design a Key-Value Store

> **Difficulty:** ⭐⭐⭐ | **Asked at:** Amazon (DynamoDB), Google, Meta | **Time:** 45 minutes

## 🎯 Problem Statement

Design a distributed key-value store like DynamoDB, Redis Cluster, or etcd that:
- Supports put(key, value) and get(key) operations
- Handles high throughput with low latency
- Scales horizontally across many nodes
- Provides configurable consistency

---

## Step 1: Requirements

### Functional Requirements
1. put(key, value) — Store a key-value pair
2. get(key) → value — Retrieve value by key
3. delete(key) — Remove a key-value pair
4. TTL support — Auto-expire keys

### Non-Functional Requirements
| Requirement | Target |
|------------|--------|
| Latency | < 10ms for reads, < 50ms for writes |
| Throughput | 1M+ operations/sec |
| Availability | 99.99% |
| Durability | Data never lost |
| Scalability | Petabytes of data, thousands of nodes |

---

## Step 2: High-Level Design

### Single Node Design

```
┌─────────────────────────────────────────┐
│              KV Store Node              │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │     In-Memory Hash Map          │    │
│  │  (primary data structure)       │    │
│  └──────────────┬──────────────────┘    │
│                 │                       │
│  ┌──────────────▼──────────────────┐    │
│  │     Write-Ahead Log (WAL)       │    │
│  │  (durability on disk)           │    │
│  └──────────────┬──────────────────┘    │
│                 │                       │
│  ┌──────────────▼──────────────────┐    │
│  │     SSTable / LSM Tree          │    │
│  │  (persistent storage)           │    │
│  └─────────────────────────────────┘    │
│                                         │
└─────────────────────────────────────────┘

Write Path:
1. Write to WAL (append-only, fast)
2. Update in-memory hash map
3. Return success
4. Periodically flush to SSTable

Read Path:
1. Check in-memory hash map → Hit? Return
2. Check SSTables (newest to oldest) → Found? Return
3. Return not found
```

---

## Step 3: Deep Dive

### Data Partitioning — Consistent Hashing

```
Problem: How to distribute keys across N nodes?

Solution: Consistent Hashing

Hash Ring:
          Node A (0°)
           ╱    ╲
         ╱        ╲
  Node D ◄────────► Node B
  (270°)   ╲    ╱   (90°)
           ╲  ╱
         Node C (180°)

Key Placement:
  hash(key) → position on ring → first node clockwise

Adding Node E (between A and B):
  Only keys between A and E need to move (not all keys)

Virtual Nodes:
  Each physical node → multiple virtual nodes on ring
  Node A → A1, A2, A3, A4 (spread around ring)
  Better load distribution, handles uneven node capacities
```

```python
import hashlib
import bisect

class ConsistentHash:
    def __init__(self, nodes, virtual_nodes=150):
        self.ring = {}
        self.sorted_keys = []
        self.virtual_nodes = virtual_nodes

        for node in nodes:
            self.add_node(node)

    def add_node(self, node):
        for i in range(self.virtual_nodes):
            key = self._hash(f"{node}:{i}")
            self.ring[key] = node
            bisect.insort(self.sorted_keys, key)

    def get_node(self, key):
        if not self.ring:
            return None
        hash_val = self._hash(key)
        idx = bisect.bisect_right(self.sorted_keys, hash_val)
        if idx == len(self.sorted_keys):
            idx = 0
        return self.ring[self.sorted_keys[idx]]

    def _hash(self, key):
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
```

### Replication

```
Replication Factor = 3 (store each key on 3 nodes)

N1 (primary) ──replicate──→ N2 (secondary) ──replicate──→ N3 (secondary)

Strategy: Choose N-1 successor nodes on the hash ring

Consistency Levels:
┌─────────────┬────────────────────────────────────────────┐
│ Level       │ Behavior                                   │
├─────────────┼────────────────────────────────────────────┤
│ ONE         │ Return after 1 replica confirms            │
│ QUORUM      │ Return after (N/2 + 1) replicas confirm   │
│ ALL         │ Return after all N replicas confirm        │
│ LOCAL_QUORUM│ Quorum within local data center            │
└─────────────┴────────────────────────────────────────────┘

Trade-off:
  ONE    → Fast, but possible data loss
  QUORUM → Balance of speed and safety (recommended)
  ALL    → Slowest, strongest consistency
```

### Conflict Resolution

```
Problem: Network partition → two nodes accept different writes for same key

Solution 1: Last Write Wins (LWW)
├── Use timestamp to determine winner
├── Simple, but may lose writes
└── Used by: Cassandra (default)

Solution 2: Vector Clocks
├── Track causal ordering of events
├── Detect conflicts, let application resolve
└── Used by: Amazon Dynamo (2007 paper), Riak. (AWS DynamoDB the product uses LWW + conditional writes, not vector clocks.)

Vector Clock Example:
  Node A writes: VC = {A:1}
  Node B writes: VC = {B:1}  (concurrent!)
  Node C sees both: VC = {A:1, B:1} → CONFLICT detected
  Application resolves: merge values or pick one
```

### Storage Engine — LSM Tree

```
Write Path (LSM Tree):
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Write   │────→│ MemTable │────→│ WAL      │
│ Request  │     │ (sorted) │     │ (disk)   │
└──────────┘     └────┬─────┘     └──────────┘
                      │ (when full)
               ┌──────▼─────┐
               │  SSTable   │  (sorted, immutable)
               │  Level 0   │
               └──────┬─────┘
                      │ (compaction)
               ┌──────▼─────┐
               │  SSTable   │
               │  Level 1   │
               └──────┬─────┘
                      │
               ┌──────▼─────┐
               │  SSTable   │
               │  Level 2   │
               └────────────┘

Read Path:
1. Check MemTable
2. Check Bloom Filter (skip SSTable if key definitely not there)
3. Check SSTables Level 0 → 1 → 2

Compaction:
├── Size-Tiered: Merge SSTables of similar size
└── Leveled: Merge into levels with size limits
```

### Handling Failures

```
Detection: Gossip Protocol
├── Each node periodically pings random peers
├── If no response after N pings → mark as suspect
├── If no response after 2N pings → mark as failed
└── Failure info propagated to all nodes

Temporary Failures: Hinted Handoff
├── If target node is down, write to a nearby node
├── Nearby node stores "hint" (temporary copy)
├── When target recovers → replay hints
└── Ensures writes aren't lost during brief outages

Permanent Failures: Anti-Entropy with Merkle Trees
├── Each node maintains Merkle tree of its data
├── Compare trees with replica nodes
├── Only sync differing branches
└── Efficient synchronization of large datasets
```

### Replication Model: Dynamo's Descendants

The diagrams above compress the machinery into the word "quorum." The interview-grade answer is the actual Dynamo design [1], because nearly every AP key-value store since 2007 — Cassandra, Riak, and the cloud-native descendants — is its descendant. The paper's interface statement is the best one-sentence summary of the model: "The get(key) operation locates the object replicas associated with the key in the storage system and returns a single object or a list of objects with conflicting versions along with a context" [1]. The *interface itself* admits multiple versions: a store at Dynamo's availability targets cannot always know which value is latest, so get() returns a set plus context rather than a single truth.

**Coordinator and preference list.** "A node handling a read or write operation is known as the coordinator. Typically, this is the first among the top N nodes in the preference list" [1] — the N nodes clockwise from the key's ring position. Membership failures bend the list rather than failing the request: "Read and write operations involve the first N healthy nodes in the preference list, skipping over those that are down or inaccessible" [1]. That sentence is where the availability comes from.

**The quorum arithmetic — and its honest caveat.** The classic line: "Setting R and W such that R + W > N yields a quorum-like system. In this model, the latency of a get (or put) operation is dictated by the slowest of the R (or W) replicas" [1]. Two points deserve unpacking. First, the paper deliberately says *quorum-like*: R + W > N guarantees the read set intersects the write set, but replica intersection is not ordering — nothing forces the intersecting replica to hold the newest value unless conflicts are detected (vector clocks) or writes are serialized by one leader. Second, low W quietly erodes durability: "low values of W and R can increase the risk of inconsistency as write requests are deemed successful and returned to the clients even if they are not processed by a majority of the replicas" [1]. The system's own framing is eventual: "Dynamo provides eventual consistency, which allows for updates to be propagated to all replicas asynchronously" [1]. So (R + W > N) is a replica-overlap guarantee, not a linearizability proof.

**Sloppy quorum and hinted handoff.** Strict quorum membership would make an AP store unavailable precisely when it matters: "it does not enforce strict quorum membership and instead it uses a 'sloppy quorum'; all read and write operations are performed on the first N healthy nodes from the preference list, which may not always be the first N nodes encountered while walking the consistent hashing ring" [1]. A write landing on a substitute node carries a hint naming the intended recipient and is replayed to it on recovery. The full write-path mechanics and consistency consequences live in [Hinted Handoff](../../distributed/advanced/hinted-handoff.md) — link, don't re-derive, in an interview.

**Conflict detection.** Dynamo versions objects with vector clocks: "Dynamo uses vector clocks in order to capture causality between different versions of the same object" [1], with the comparison rule "If the counters on the first object's clock are less-than-or-equal to all of the nodes in the second clock, then the first is an ancestor of the second and can be forgotten. Otherwise, the two changes are considered to be in conflict and require reconciliation" [1]. The algorithm and its truncation overhead are in [Vector Clocks](../../distributed/fundamentals/vector-clocks.md). The trade to remember: clocks preserve every branch (no lost writes) but grow with coordinator diversity — which is why last-write-wins won in most products.

**Read repair and anti-entropy.** Convergence runs on two layers. On the read path: "If stale versions were returned in any of the responses, the coordinator updates those nodes with the latest version. This process is called read repair because it repairs replicas that have missed a recent update at an opportunistic time and relieves the anti-entropy protocol from having to do it" [1]. In the background, Merkle trees make replica comparison cheap — with a design refinement that matters: "Each node maintains a separate Merkle tree for each key range (the set of keys covered by a virtual node) it hosts," and the documented cost is that "many key ranges change when a node joins or leaves the system thereby requiring the tree(s) to be recalculated" [1]. Tree-per-range bounds both the comparison cost and the blast radius of membership churn; the protocol and structure are covered in [Anti-Entropy Protocols](../../distributed/advanced/anti-entropy.md) and [Merkle Tree Synchronization](../../distributed/advanced/merkle-sync.md).

### The Storage Engine Beneath

Zoom from the cluster to one node and the same design reappears: nearly every production KV store is log-structured rather than B-tree-backed. The reason is load-shaped — a KV store's write rate is its revenue, and page-oriented B-trees turn writes into random read-modify-write cycles, while a log-structured engine converts every write into a sequential append: WAL, memtable, immutable SSTables, background compaction (the pipeline sketched above; the full architecture and amplification math are in [LSM Trees](../../dbms/internals/lsm-trees.md)). Four distributed consequences deserve airtime:

- **Delete is a write.** There is no in-place delete — deletion writes a tombstone. In a cluster this is a correctness parameter, not an implementation detail: the tombstone must survive long enough to overtake every copy of the live value, through gossip propagation, hinted-handoff replay, and replicas that were offline during the delete, before compaction may purge it. Purge too early and anti-entropy resurrects a "deleted" key; tombstone grace periods are tunables with real outages behind them.
- **Bloom filters collect the read tax.** A point read may consult many SSTables; a per-file Bloom filter (see [Bloom Filters](../../storage/bloom-filters.md)) turns "definitely absent" into hash probes instead of disk reads, which is what keeps read amplification flat as data grows.
- **Point-read vs range-scan is the modeling fork.** Hash-keyed stores (Dynamo's key model) give O(1) point lookups but no ordered scan; sorted memtables/SSTables give ordered iteration and cheap range repair for free — which is why backup and repair tooling loves sorted runs. Know which model your store uses before promising "scan."
- **Write amplification is a capacity line item.** Leveled-LSM write amplification runs ≈10–30× (computed as 1 + T×L on the [LSM Trees](../../dbms/internals/lsm-trees.md) page), so at high ingest the background compaction I/O competes with the front door — compaction lag, not CPU, is usually the first bottleneck a write-heavy KV store hits.

### Partition Placement and Rebalancing

[Consistent hashing](../../distributed/partitioning/consistent-hashing.md) answers "where does a key go." The production question is "how do ring assignments stay balanced as nodes churn" — and the naive answer loses. Dynamo shipped three strategies and measured them. Strategy 1 gave each node T random tokens: "the tokens are chosen randomly, the ranges vary in size. As nodes join and leave the system, the token set changes and consequently the ranges change" [1] — load skewed unpredictably. The final design decouples keyspace from placement: it "divides the hash space into Q equally sized partitions and the placement of partition is decoupled from the partitioning scheme," each node holding Q/S tokens, and "when a node joins the system it 'steals' tokens from nodes in the system in a way that preserves these properties" [1]. Equal partitions plus uniform tokens equalize load, and vnode counts encode capacity — a bigger node steals more tokens.

**The fixed-bucket alternative.** Pre-create a large fixed bucket count (say 10M), map bucket = hash(key) mod 10M, and keep an explicit bucket→node table in a metadata service. Rebalancing becomes moving whole buckets: data movement proportional to buckets moved, not total data. It is simple and perfectly uniform, but every request needs the table — a lookup dependency you must replicate and scale — and the bucket count is frozen at design time. Vnodes won in practice because routing is *computable* from the ring with no lookup service and vnode counts adapt to heterogeneous hardware; the same insight CRUSH formalized for Ceph (see [Ceph CRUSH](../../storage/ceph-crush.md)).

**Bootstrapping a new node.** A join is a range transfer, and the storage engine decides whether it is cheap: because SSTables are immutable files, the source ships whole sorted files for the range instead of replaying per-key operations; the old owner keeps serving and accepting writes for the range during the copy; ownership flips at a cutover point with the short delta re-synced first. Bootstrap bandwidth becomes a background cost and writes never block — one more payoff of the log-structured engine above.

**Replica placement is failure-domain-aware.** The preference list skips candidates that would co-locate replicas of one key in the same rack or availability zone — otherwise a single switch failure could remove the key's entire write quorum at once. State the constraint ("N replicas across the most distinct failure domains available") rather than assuming the ring handles it automatically.

---

## Step 4: Trade-offs

### CAP Theorem Choices

```
CP System (Consistency + Partition Tolerance):
├── Reject writes during partition if quorum can't be reached
├── Examples: HBase, MongoDB (with write concern majority)
└── Use: Financial data, inventory

AP System (Availability + Partition Tolerance):
├── Accept writes during partition, resolve conflicts later
├── Examples: Cassandra, DynamoDB, CouchDB
└── Use: Social media, shopping cart, analytics
```

### Consistency vs Latency
| Level | Write Latency | Read Latency | Consistency |
|-------|--------------|--------------|-------------|
| ONE | Lowest | Possible stale | Eventual |
| QUORUM | Medium | Fresh | Strong (probabilistic) |
| ALL | Highest | Always fresh | Strong |

## Interview Problems

**P1 (senior) — "Design get-or-put with quorums under a partitioned network: N=3, R=W=2, and the cluster splits 2 nodes + 1 node. What does each side do, and what does the client see?"**
Expected: the two-node side can form both read and write quorums and serves traffic normally. The one-node side cannot reach W=2, so it faces the CAP choice: reject writes (CP behavior) or keep accepting them via sloppy quorum — Dynamo's choice — by writing to the first healthy nodes beyond the preference list, with hints for the intended replicas. Divergent versions accumulate on both sides; vector clocks detect the concurrency when the partition heals, and read repair plus Merkle anti-entropy converge the replicas. The follow-up that separates seniors: "who decides the partition exists?" — no node can distinguish a partition from its peers dying, which is why membership (gossip) and W are policy, not fact. Rubric: junior says "the minority fails"; mid explains sloppy quorum; senior covers post-healing conflict resolution.

**P2 (mid) — "A user calls put() then immediately get() and does not see their value. Explain why and what you tell them."**
Expected: eventually consistent reads are allowed to miss recent writes — Amazon's own documentation: "When issuing eventually consistent reads to a DynamoDB table or an index, the responses might not reflect the results of a recently completed write operation. If you repeat your read request after a short time, the response should eventually return the more recent item" [2]. Causes: the get hit a replica the write hadn't reached yet (R < N with async propagation), or a stale cache. Remedies, in order of cost: read-after-write via session stickiness; a strongly consistent read — priced deliberately: "Eventually consistent reads are half the cost of strongly consistent reads" [2]; or W=N for this key class. Rubric: junior blames a bug; mid names eventual consistency; senior offers the remedy ladder and its pricing.

## References

1. DeCandia, G.; Hastorun, D.; Jampani, M.; Kakulapati, G.; Lakshman, A.; Pilchin, A.; Sivasubramanian, S.; Vosshall, P.; Vogels, W. "Dynamo: Amazon's Highly Available Key-value Store." *Proc. 21st ACM SIGOPS Symposium on Operating Systems Principles (SOSP '07)*, pp. 205–220. DOI: [10.1145/1294261.1294281](https://doi.org/10.1145/1294261.1294281) — Crossref-verified this session (title/authors/venue checked at api.crossref.org); full PDF fetched from <https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf> (HTTP 200, 16 pp.); all quoted sentences verbatim from the fetched PDF.
2. Amazon DynamoDB Developer Guide, "Read consistency" — <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html> — fetched in full this session (HTTP 200); both quoted sentences verbatim.
3. Chang, F.; Dean, J.; Ghemawat, S.; Hsieh, W. C.; Wallach, D. A.; Burrows, M.; Chandra, T.; Fikes, A.; Gruber, R. E. "Bigtable: A Distributed Storage System for Structured Data." *Proc. 7th USENIX Symposium on Operating Systems Design and Implementation (OSDI '06)*, pp. 205–218. No ACM DOI exists (USENIX publication); DOI lookup services index only the proceedings DOI of the containing volume. USENIX abstract page <https://www.usenix.org/legacy/events/osdi06/tech/chang.html> — fetched this session (HTTP 200 with a full browser UA; a bare `Mozilla/5.0` UA got 403 from the same URL, so this is a UA-gated host, not a dead link); title, author list, venue, page range, and Best Paper designation verified against the fetched page. Cited for the sorted-map data-model contrast only; no claims drawn from it.

## 🔗 Cross-References

- [Distributed File System](./dfs.md) — Similar distributed storage concepts
- [Architecture Concepts](../../cheatsheets/architecture.md) — CAP theorem, consistency models
- [DBMS Questions](../dbms-questions.md) — SQL vs NoSQL trade-offs
- [OS Questions](../os-questions.md) — File systems, I/O
- [Key-Value Store — LLD](./lld/key-value-store-lld.md) — the single-node twin: class design, API surface, and engine code; this page owns the cluster mechanics
- [LSM Trees](../../dbms/internals/lsm-trees.md) — the storage engine beneath every node; write/read/space amplification computed
- [Hinted Handoff](../../distributed/advanced/hinted-handoff.md) — the sloppy-quorum write path in full
- [Vector Clocks](../../distributed/fundamentals/vector-clocks.md) — algorithm, comparison rules, truncation cost
- [Anti-Entropy Protocols](../../distributed/advanced/anti-entropy.md) — read repair, hinted handoff, and Merkle repair as one system
- [Merkle Tree Synchronization](../../distributed/advanced/merkle-sync.md) — range-based vs key-hash trees and the sync protocol
- [Consistent Hashing](../../distributed/partitioning/consistent-hashing.md) — ring mechanics, vnode math, rebalancing
- [Quorum Replication](../../distributed/replication/quorum.md) — the formal read/write-intersection model
- [Bloom Filters](../../storage/bloom-filters.md) — the read-amplification tool the LSM read path leans on
- [Key-Value Stores (DBMS)](../../dbms/nosql/key-value.md) — the product tour: DynamoDB, Redis, embedded stores
