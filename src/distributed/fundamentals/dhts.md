# Distributed Hash Tables: Ring Geometry, Stabilization, and What Actually Shipped

A distributed hash table gives you the `put(key, value)` / `get(key)` interface of a
hash map spread across N unreliable machines, with no coordinator: a routing overlay
answers "which node owns this key" in a logarithmic number of hops. The 2001-2002
wave of papers (Chord, Kademlia, Pastry, Tapestry) settled the toolkit -- hashed IDs
on a shared keyspace, O(log N) per-node routing state, local repair under churn.
Scope split: Kademlia's XOR metric and k-buckets have their own page
([Kademlia DHT](../advanced/kademlia-dht.md)); placement hashing without multi-hop
routing lives in [Consistent Hashing](../partitioning/consistent-hashing.md),
[Rendezvous Hashing](../advanced/rendezvous-hashing.md), and
[Jump Consistent Hashing](../advanced/jump-consistent-hashing.md). This page works
the Chord line end to end: ring geometry, finger tables, stabilization, replication
on successors, and how the surviving systems actually use these ideas.

## The Chord Ring

Chord (Stoica, Morris, Karger, Kaashoek, Balakrishnan -- SIGCOMM 2001) hashes both
nodes and keys into the same m-bit identifier space, viewed as a circle. Consistent
hashing assigns key k to `successor(k)` -- the first node clockwise from k -- so the
successor pointer alone is already a *correct* (if slow) routing table: follow it at
most N steps and you reach any key's owner. Everything else in Chord is acceleration
on top of that one invariant. Load balancing is probabilistic: with O(log N) virtual
nodes per real node, every machine handles a fair share with high probability --
Cassandra later shipped exactly this as "vnodes" (see below).

```text
        ids mod 2^m, drawn as a circle (node n's perspective)

                     [n + 2^7]
                   .            .
               [n+2^6]           [n+2^5]
                 |                  |
      key k --> [k]                [n+2^4]
                   .            .
                     [n]  <-- start here

  successor(n) : first node clockwise after n; owns arc (n, succ(n)]
  finger[i]    : first node at/after n + 2^(i-1),  i = 1..m
  lookup(k)    : hop to closest finger preceding k; fall back to successor
```

## Finger Tables and the O(log N) Hop Count

Node n keeps a finger table of m entries: `finger[i] = successor(n + 2^(i-1))`. The
covered intervals double in size -- the first finger spans 1 identifier, the last
spans half the ring. In a system with N nodes only about log2(N) of the m slots hold
*distinct* nodes, so per-node state stays logarithmic even though the table is
indexed by ID bits.

The lookup walks `closest_preceding_finger(target)`: at each node, forward the query
to the farthest finger that does not overshoot the target; if none helps, step to
the successor. The hop-count argument is arithmetic: following the finger for the
highest remaining 1-bit of the distance fixes that bit and strictly decreases the
distance, so finger-hops equal the number of 1-bits in the distance. A random
~log2(N)-bit distance has about half its bits set, so the expected finger count is
~(1/2) log2(N).

| Routing state | Entries per node | Lookup cost (N nodes) | Correctness when stale |
| --- | --- | --- | --- |
| Successor pointer only | 1 | O(N) worst case | always correct, just slow |
| Successor list of r | r | O(N) worst case; survives r-1 consecutive failures | correct if any listed successor lives |
| Fingers added | m = ID bits, ~log2(N) distinct | O(log N) w.h.p.; ~(1/2) log2 N expected | degrades to successor-only walking |

## Join, Leave, and Stabilization

Churn is the normal case in the overlays Chord was built for, so repair is a loop,
not an event:

- **Join**: a newcomer finds its successor via a bootstrap node (one lookup of its
  own ID), then copies key/value pairs its new arc takes ownership of from that
  successor. Its predecessor learns about it lazily.
- **Stabilize**: periodically ask your successor for its predecessor; if that
  predecessor sits between you and your successor (someone joined in between), adopt
  it. Each stabilize doubles as a `notify` letting the successor fix its own
  predecessor pointer; the paper's evaluation ran stabilize every 30 seconds.
- **Fix fingers**: periodically re-resolve a random finger slot so the table heals
  gradually instead of flapping.
- **Leave/failure**: detected by the stabilize loop; replace a dead successor with
  the first live entry from the successor list, and lookups continue.

The SIGCOMM paper's complexity statement: in steady state each node knows O(log N)
others and resolves lookups in O(log N) messages; a join or leave triggers no more
than O(log^2 N) messages with high probability. The journal version (IEEE/ACM
Transactions on Networking, 2003) adds the full proofs, including that after
arbitrary joins one stabilization pass per node restores the ring in O(log N)
expected rounds -- why stabilize loops beat event-driven global reconfiguration.

## Failures and Replication on Successors

A single successor pointer is a single point of failure, so Chord nodes keep a
**successor list** of r nodes, refreshed by the same stabilize traffic. The paper's
Theorems 7-8 quantify the payoff: even if every node in an initially stable ring
fails independently with probability 1/2, `find_successor` still returns the closest
living successor with high probability for adequate r, because r successors all
fail simultaneously only with probability p^r. The same list powers replication:
store each key on its r successors, reads use the first live replica, and the node
tracking the list knows when the replica set changed -- which is when new copies
get propagated.

| Per-node failure prob p | r = 2 | r = 4 | r = 8 |
| --- | --- | --- | --- |
| 0.01 | 1.0e-04 | 1.0e-08 | 1.0e-16 |
| 0.05 | 2.5e-03 | 6.3e-06 | 3.9e-11 |
| 0.10 | 1.0e-02 | 1.0e-04 | 1.0e-08 |

Read the table like an SRE: with r = 4 replicas and 5% failure probability, the
chance a key's whole replica set is down is ~6e-06 -- but only if failures are
independent. Correlated failures break p^r; placement diversity carries the
guarantee, not the exponent.

## A Family of Geometries

Chord is one point in a design space; geometry fixes the routing table's shape and failure behavior:

| Family | Geometry | Routing rule | State per node | Lookup hops | Canonical systems |
| --- | --- | --- | --- | --- | --- |
| Ring | 1-D circle mod 2^m | closest preceding finger | m fingers + r successors | O(log N) w.h.p. | Chord |
| XOR subtree | 160/256-bit IDs | XOR distance, one bucket per bit scale | ~log2(N) non-empty k-buckets | O(log N) rounds | Kademlia ([own page](../advanced/kademlia-dht.md)) |
| Prefix | hypercube-like digits | fix one prefix digit per hop | log base 2^b N routing rows | O(log N) | Pastry, Tapestry |
| Butterfly | randomized butterfly | constant degree, random levels | O(1) edges | O(log N) expected | Viceroy (PODC 2002) |

Pastry and Tapestry descend from Plaxton-style randomized hypercubes; Viceroy proved
Chord's bound is reachable with constant per-node state. Kademlia won in deployment:
its symmetry makes routing-state maintenance a side effect of ordinary traffic.

## Placement Layer vs Routing Layer

A recurring interview trap: Cassandra is called a "DHT" because it uses a consistent hashing ring, yet has **no multi-hop routing at all**. The two layers are independent:

| Layer | Question it answers | Multi-hop? | Mechanisms |
| --- | --- | --- | --- |
| Placement | which nodes own key k | no | consistent hashing + vnodes; rendezvous hashing for site-scoped sets; jump consistent hash for shrinking node sets |
| Routing | how to reach the owner without global knowledge | yes | Chord fingers, Kademlia buckets, Pastry prefix tables |

Cassandra assigns each physical node multiple tokens (vnodes), computes a key's
token with Murmur3, and walks the ring in the *coordinator's* head to pick the RF
replica endpoints; membership and liveness come from gossip (see
[Gossip Protocols](./gossip-protocols.md) and [SWIM](./swim-membership.md)), and any
node can coordinate because every node holds the whole ring picture. The Dynamo
lineage (see [DynamoDB](../../cloud/aws/dynamodb.md)) is the same shape: one hop,
no forwarding. Multi-hop routing earns its cost only when no node can hold the full
ring: millions of peers, adversarial churn, no operator.

## What Actually Runs

| System | ID space | What the DHT stores | Routing style | Notes from specs |
| --- | --- | --- | --- | --- |
| BitTorrent mainline DHT (BEP-5) | 160-bit, shared with infohashes | torrent -> peer contact lists | multi-hop Kademlia, k = 8 | node is "good" only if heard from within the last 15 minutes; announce requires an opaque token from get_peers |
| IPFS / libp2p KadDHT | 256-bit (SHA-256 over public keys / CIDs) | provider records + peer routing | multi-hop Kademlia | spec defines content provider advertisement and discovery; client vs server mode |
| Cassandra | 64-bit Murmur3 tokens | nothing routed -- placement only | coordinator computes replicas locally | Dynamo-style consistent hashing + vnodes, gossip membership, tunable consistency |

The pattern: DHTs store *pointers* (peers, providers, tokens), rarely bulk data -- index-in-overlay, payload-elsewhere keeps hop counts and replica lifetimes sane.

## Lab: Finger-Table Hops on a Simulated Ring

A MODEL simulation (not a real network): real finger tables over a 2^12 identifier
space, seeded, sweeping N from 64 to 1,024 nodes with 200 lookups per node:

```python
#!/usr/bin/env python3
"""Mini Chord over a 2^12 ID space (MODEL): finger i = successor(n + 2^i);
seeded lookups; mean hops vs the Chord paper's (1/2)*log2(N) expectation."""
import bisect
import math
import random

M, SPACE, SEED = 12, 1 << 12, 7          # 4096-id ring, fixed seed
SIZES, LOOKUPS = [64, 256, 1024], 200    # node sweep, lookups per node

def in_range(x, lo, hi):                 # Chord's half-open arc (lo, hi]
    return 0 < (x - lo) % SPACE <= (hi - lo) % SPACE

def build(nodes):
    return [[nodes[bisect.bisect_left(nodes, (n + (1 << i)) % SPACE) % len(nodes)]
             for i in range(M)] for n in nodes]   # finger[i] = succ(n + 2^i)

def lookup(nodes, fingers, start, key):
    hops, cur = 0, start
    for _ in range(4 * M):               # loop guard
        if cur == key:
            return hops
        s = nodes[(bisect.bisect_left(nodes, cur) + 1) % len(nodes)]
        if in_range(key, cur, s):
            return hops + 1              # final hop to owning successor
        nxt = s
        for e in reversed(fingers[bisect.bisect_left(nodes, cur)]):
            if in_range(e, cur, key):    # farthest finger not past target
                nxt = e
                break
        hops += 1
        cur = nxt
    raise RuntimeError("stuck")

rng = random.Random(SEED)
print(f"MODEL: Chord ring 2^{M} = {SPACE} ids, {LOOKUPS} seeded lookups/node\n")
print(f"{'N nodes':>7} {'mean hops':>9} {'(1/2)*log2N':>11} {'distinct fingers':>16} {'log2(N)':>7}")
for n_nodes in SIZES:
    nodes = sorted(rng.sample(range(SPACE), n_nodes))
    fingers = build(nodes)
    targets = [rng.randrange(SPACE) for _ in range(LOOKUPS)]
    total = sum(lookup(nodes, fingers, n, k) for n in nodes for k in targets)
    distinct = sum(len(set(f)) for f in fingers) / n_nodes
    print(f"{n_nodes:>7} {total/(n_nodes*LOOKUPS):>9.2f} "
          f"{0.5 * math.log2(n_nodes):>11.2f} {distinct:>16.2f} {math.log2(n_nodes):>7.0f}")
print("\ntheory: each hop fixes the highest remaining 1-bit of the distance; random")
print("distances have ~half their bits set, so expected hops ~ (1/2)*log2(N),")
print("and only ~log2(N) of the M finger slots hold distinct nodes.")
```

Real output (Python 3.12, byte-identical across two runs):

```text
MODEL: Chord ring 2^12 = 4096 ids, 200 seeded lookups/node

N nodes mean hops (1/2)*log2N distinct fingers log2(N)
     64      3.84        3.00             6.36       6
    256      4.85        4.00             8.32       8
   1024      5.61        5.00            10.31      10

theory: each hop fixes the highest remaining 1-bit of the distance; random
distances have ~half their bits set, so expected hops ~ (1/2)*log2(N),
and only ~log2(N) of the M finger slots hold distinct nodes.
```

Three readings: distinct fingers sit at ~log2(N) plus a small constant (the m-slot table
compresses to logarithmic state); hops scale logarithmically (16x more nodes, ~1.5x more
hops); measured hops run ~1 above (1/2) log2(N) due to the final successor hop each lookup pays.

## Failure Modes Worth Reciting

- **Stale fingers under churn**: correctness survives (the successor pointer is the floor), latency degrades.
- **Bootstrap hot spots**: every join does a lookup through the same bootstrap node; keep bootstrap sets.
- **p^r replication math breaks on correlated failure**: placement diversity carries the guarantee, not the exponent.
- **DHTs store pointers, not payloads**: BEP-5 announces peer contacts, IPFS announces providers; bulk data moves point-to-point.

## Related Pages

- [Kademlia DHT](../advanced/kademlia-dht.md) -- XOR metric, k-bucket LRU rules, alpha-concurrent lookups.
- [Consistent Hashing](../partitioning/consistent-hashing.md) + [Jump Consistent Hashing](../advanced/jump-consistent-hashing.md) -- the placement base layer.
- [Gossip Protocols](./gossip-protocols.md) + [SWIM](./swim-membership.md) -- the membership layer every overlay sits on.
- [Anti-Entropy Protocols](../advanced/anti-entropy.md) + [IPFS and Filecoin](../../blockchain/ipfs-filecoin.md) -- replica reconciliation; the deployed KadDHT view.

## References

1. Stoica, Morris, Karger, Kaashoek, Balakrishnan. "Chord: A Scalable Peer-to-peer
   Lookup Service for Internet Applications." ACM SIGCOMM 2001.
   <https://doi.org/10.1145/383059.383071>
   (full text: <https://pdos.csail.mit.edu/papers/chord:sigcomm01/chord_sigcomm.pdf>)
2. Stoica, Morris, Liben-Nowell, Karger, Kaashoek, Dabek, Balakrishnan. "Chord: A
   Scalable Peer-to-peer Lookup Protocol for Internet Applications." IEEE/ACM
   Transactions on Networking 11(1), 2003. <https://doi.org/10.1109/TNET.2002.808407>
3. Maymounkov, Mazieres. "Kademlia: A Peer-to-peer Information System Based on the
   XOR Metric." IPTPS 2002. <https://pdos.csail.mit.edu/~petar/papers/maymounkov-kademlia-lncs.pdf>
4. BitTorrent.org. "BEP 5: The DHT Protocol." <https://www.bittorrent.org/beps/bep_0005.html>
5. libp2p Working Group. "Kademlia DHT Spec." <https://github.com/libp2p/specs/blob/master/kad-dht/README.md>
6. Apache Cassandra documentation. "Architecture -- Dynamo."
   <https://cassandra.apache.org/doc/latest/cassandra/architecture/dynamo.html>
7. Malkhi, Naor, Ratajczak. "Viceroy: A Scalable and Dynamic Emulation of the
   Butterfly." ACM PODC 2002. <https://doi.org/10.1145/571825.571857>
