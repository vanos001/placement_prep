# Kademlia DHT: XOR Routing in Practice

Most peer-to-peer overlays from the early 2000s are footnotes. Kademlia is not: it is
the routing layer under BitTorrent's mainline DHT (BEP-5), IPFS/libp2p's KadDHT, and
Ethereum's node discovery protocol v5. The paper by Maymounkov and Mazieres (IPTPS 2002)
is short, but nearly every design decision in it maps to a production behavior you can
still observe in packet captures today. This page works through the mechanics that made
it stick: the XOR metric, LRU k-buckets, the iterative lookup, and where the design
bends under attack.

## The XOR Metric and Why It Beats Numeric Difference

Every node and every key is an ID in the same space. Kademlia's paper uses 160-bit IDs;
later systems widened it (libp2p and Ethereum discv5 use 256-bit). Distance is defined
as bitwise XOR:

```
d(a, b) = a XOR b          (interpreted as an unsigned integer)
```

XOR is a true metric: `d(a,a) = 0`, it is symmetric, and it satisfies the triangle
inequality `d(x,z) <= d(x,y) + d(y,z)`. Two properties in the paper do the real work:

| Property | Paper's definition | Consequence in the protocol |
| --- | --- | --- |
| Unidirectionality | For any point x and distance A > 0 there is exactly one y with d(x,y) = A | All lookups for the same key converge along the same path, regardless of who starts them, so caching (key,value) pairs along the path actually relieves hot spots |
| Symmetry | d(a,b) = d(b,a) | A node that hears about you can file you away in its own table; incoming traffic maintains routing state for free |

Unidirectionality deserves a second look. Under a directed metric, everyone searching
for key K must eventually funnel through the same neighborhood of IDs, which is exactly
why one cached copy of a popular value absorbs demand. Compare with DHTs that route on
numeric difference `|a - b|` in part of the keyspace and XOR in another: lookup paths
stop lining up, and caches stop paying for themselves.

The second, less advertised consequence of symmetry: every RPC a node sends updates the
recipient's k-buckets, and every reply updates the sender's. Routing tables are
maintained as a side effect of doing work, which is why bucket-refresh traffic stays
low in healthy networks.

## 160 Bits of Keyspace, 160 Buckets, k Contacts Each

Each node keeps, for every distance scale, a list of up to `k` contacts whose XOR
distance falls in `[2^i, 2^(i+1))` (the paper uses `k = 20`). There is one bucket per
bit position, so a full table covers the entire 160-bit space with no overlap:

```
node 1100... (self)

bucket 0   [2^0, 2^1)        ...1          1 node  (the single nearest neighbor)
bucket 1   [2^1, 2^2)        ..x1          up to k nodes
bucket 2   [2^2, 2^3)        .xx1x         up to k nodes
   ...
bucket 158 [2^158, 2^159)    far half-space minus the last quarter
bucket 159 [2^159, 2^160)    half of the entire keyspace   <- fills first
```

The shape is lopsided on purpose: half of all random IDs land in bucket 159, a quarter
in bucket 158, and so on, so distant buckets fill up while the nearest buckets stay
mostly empty. With N uniform nodes only about `log2(N)` buckets hold anything. The lab
at the end of this page measures that directly: 1,000 simulated nodes average 10.3
non-empty buckets, matching `log2(1000) ~= 9.97`.

### The LRU Rule and the Liveness Argument

Each bucket is ordered by time last seen -- least-recently seen at the head,
most-recently seen at the tail. The update rule from the paper:

1. Any message from a contact moves it to the tail of its bucket.
2. A new contact enters the tail of an unfilled bucket.
3. A new contact for a FULL bucket triggers a ping of the head (least-recently seen):
   - head replies -> move head to tail, discard the new contact;
   - head is dead -> evict it, insert the new contact at the tail.

Rule 3 is the interesting one: incumbents get the benefit of the doubt. The
justification is empirical. The authors analyze Gnutella trace data collected by
Saroiu et al. and plot the probability of a node remaining online another hour as a
function of its current uptime: the longer a node has been up, the more likely it is to
stay up another hour. Keeping the oldest live contacts therefore maximizes the chance
that a bucket's members are still reachable. A side effect is DoS resistance -- an
attacker cannot flush routing state by flooding the network with fresh node IDs, since
new nodes are only admitted when old ones die.

A verification note that saves embarrassment: the frequently repeated claim that the
paper reports a "1,359-hour median session" is not in the paper at all -- a full-text
scan finds no such number. The paper's actual claim is the qualitative uptime-vs-survival
curve above. Independent measurements of the era cut the other way: Qiao and Bustamante
(USENIX ATC 2006) measured Overnet (a Kademlia deployment) and found a median session
length of roughly 8,100 seconds -- about 2.25 hours -- with 80% of sessions under
29,700 seconds. The LRU heuristic still works under that churn, but any capacity plan
for a Kademlia network should assume hour-scale sessions, not month-scale ones.

## The Iterative Lookup and the Concurrency Parameter alpha

The core primitive is FIND_NODE: ask a node for the k contacts it knows that are
closest to some target ID. Everything else (finding values, storing, refreshing) is a
lookup in disguise. The lookup is iterative -- the initiator talks to many nodes
directly rather than forwarding through the overlay -- with `alpha` queries in flight
(the paper's example is 3):

```
initiator                          network (distance to target shrinks each round)

  | round 1: FIND_NODE -> {a1, a2, a3}      chosen from closest non-empty bucket
  |<-- k closest contacts each
  |
  | round 2: merge replies, keep closest k seen,
  |          send FIND_NODE to alpha not-yet-queried among them
  |                 target's subtree          <- once a queried node sits "near"
  |                    /          \              the target, replies are drawn
  |              closer           closer       from its own k closest contacts
  |                |               |
  | round j: no unqueried node among the closest k remains  ->  stop
```

Termination condition, verbatim behavior from the paper: the lookup ends when the
initiator has queried and received responses from the k closest nodes it has seen. If a
round fails to produce any node closer than the closest already seen, the initiator
falls back to querying ALL unqueried members of that closest set. Failed-to-respond
nodes are parked, not deleted; they rejoin consideration if they answer later.

What does alpha buy? With `alpha = 1` the lookup degenerates into Chord-like sequential
hopping: minimal messages, maximum wall-clock latency, and no tolerance for a slow peer
blocking progress. Raising alpha to 3 trades a modest increase in total RPCs for
roughly a factor-of-2-3 fewer sequential rounds, because each round fans out across
independent prefixes of the keyspace. The lab below measures both (p50 rounds 22 -> 9
at alpha=3 on 1,000 nodes) -- the RPC totals differ by under 20%.

### The O(log N) Hop Math

The distance-halving argument: if the current closest known node is at distance D from
the target, that node's own k closest contacts include nodes at distance at most D/2
(one of its buckets exactly brackets the target's subtree). Each round therefore at
least halves the distance once the candidate set reaches the target's neighborhood, and
halving a 160-bit distance takes at most 160 rounds even from the worst starting
point -- but starting from your own routing table you already know contacts in every
distance scale, so the bound collapses to `O(log N)` rounds for N nodes: you descend
the implicit binary tree one consistent prefix at a time.

The paper's proof sketch sharpens the tail: once the closest single node is found,
finding the remaining k-1 costs no more than the bucket depth around that node, which
is `a constant + log2(k)` steps with overwhelming probability. Total messages for a
lookup are `O(k log N)` in the worst case, but the *sequential round* count -- which is
what latency-sensitive systems feel -- is the `O(log N)` / `O(log N + log k)` figure.
For BitTorrent's mainline DHT with millions of nodes, a typical lookup lands in the
single-digit round counts.

## Store, Republish, Refresh, Join

- **STORE**: to publish (key, value), locate the k closest nodes to the key and send
  each a STORE. The publisher republishes every 24 hours; pairs expire after 24 hours
  without republication, bounding stale index data. Applications with longer-lived
  values pick longer expiries.
- **FIND_VALUE**: identical to FIND_NODE except a node holding the value returns it
  instead of contacts.
- **Bucket refresh**: request traffic normally keeps buckets fresh, but a bucket that
  has seen no lookup for the past hour must be refreshed by looking up a random ID
  inside its range. This also heals the "closest bucket" problem where a node's own
  neighborhood goes quiet.
- **Join**: insert the bootstrap node, look up your own ID (which populates the far
  buckets and announces you to your future neighbors), then refresh all buckets.
- **Caching**: because unidirectionality makes every lookup for key K visit the same
  nodes, those nodes see the traffic and can cache the value; the paper suggests
  caching outside the closest k so that eviction of the "official" store does not
  destroy the cache.

## What Runs on Kademlia Today

| Deployment | ID size | k | Notes |
| --- | --- | --- | --- |
| BitTorrent mainline DHT (BEP-5) | 160-bit (same space as infohashes) | 8 | UDP KRPC, bencoded; queries ping, find_node, get_peers, announce_peer; a node is "good" only if heard from in the last 15 minutes; announce requires a token obtained from get_peers to blunt forged announces |
| IPFS / libp2p KadDHT | 256-bit (SHA-256 of public key) | 20 | Client/server modes; server mode required to answer lookups for others (see the IPFS page) |
| Ethereum discv5 | 256-bit (secp256k1 public key) | 16 (bucket target) | UDP, handshake + encrypted records; FINDNODE takes log2 distances so a query asks for nodes at 2^i buckets; keyspace arithmetic is XOR over 256-bit IDs |

One naming trap: the BitTorrent DHT is BEP-5 ("DHT Protocol", "distributed sloppy hash
table"). BEP-52 is the BitTorrent Protocol v2 spec and has nothing to do with the DHT.
BEP-5's own concessions to practice are worth noticing: k drops from 20 to 8 (index
entries are ephemeral peer contacts, not files), and the token returned by get_peers
must be echoed in announce_peer, so a store request requires a prior lookup round --
the DHT equivalent of a capability.

## Attacks and Hardening

The structural weakness is that node IDs are (mostly) self-assigned. An attacker who
can choose IDs controls *who sits near a key*:

- **Eclipse attacks**: fill a victim's routing view (or a key's k closest set) with
  adversarial nodes, then you see the victim's lookups, serve stale values, or simply
  drop them. Heilman, Kendler, Zohar and Goldberg's USENIX Security 2015 paper
  demonstrated full eclipse attacks on Bitcoin's P2P network and showed hardening via
  deterministic eviction and randomized table entries -- the same lesson transfers to
  any Kademlia network: never let a peer choose its own routing-table position freely,
  and keep old, battle-tested contacts (Kademlia's LRU already helps).
- **Sybil attacks**: fabricate enough IDs to occupy the k closest slots of a target
  key. Defenses constrain ID acquisition; S/Kademlia (Baumgart and Mies, ICPADS 2007)
  proposes securing node-ID assignment (cryptographic puzzles or certificate-bound
  IDs) plus redundant lookups over disjoint paths so one clique cannot silence a key.
- **Built-in frictions**: the 160-bit random RPC ID echoed in every reply raises the
  cost of address forgery; the full-bucket ping rule rejects new nodes while incumbents
  live; the token rule in BEP-5 ties STORE to a recent FIND round.
- **Seen in production, not in the paper**: NAT'd and client-mode nodes that accept
  lookups but cannot answer them (libp2p forces explicit server mode), stale buckets
  after long partitions, and bootstrap-node concentration at join time.

## Lab: Hops on a Simulated 1,000-Node Overlay

The simulation builds real k-bucket tables (bucket i = contacts at XOR distance
`[2^i, 2^(i+1))`, k = 20) for 1,000 nodes with random 160-bit IDs, then runs 300
iterative FIND_NODE lookups per alpha setting and checks how many of the true k closest
nodes each lookup returns:

```python
#!/usr/bin/env python3
"""Mini Kademlia over a simulated 1000-node 160-bit ID space.

Builds real k-bucket routing tables (k=20), then runs iterative
FIND_NODE lookups and measures the hop (round) distribution for
alpha = 1 vs alpha = 3 concurrent queries.
"""
import math
import random

B = 160          # ID bits
K = 20           # replication parameter / bucket size
ALPHAS = [1, 3]
N_NODES = 1000
LOOKUPS = 300
SEED = 42

random.seed(SEED)
ids = list({random.getrandbits(B) for _ in range(2 * N_NODES)})[:N_NODES]  # unique 160-bit IDs
dist = lambda a, b: (a ^ b) if a != b else 0

# ---- routing tables: bucket i holds contacts with distance in [2^i, 2^(i+1)) ----
buckets = []
for u in ids:
    order = sorted((dist(u, v), v) for v in ids if v != u)
    table = {}
    for d, v in order:
        b = d.bit_length() - 1                       # floor(log2(distance))
        table.setdefault(b, [])
        if len(table[b]) < K:
            table[b].append(v)
    buckets.append(table)

by_id = {v: i for i, v in enumerate(ids)}
nonempty = sum(1 for t in buckets for b in t.values() if b)
print(f"nodes={N_NODES}  k={K}  ids={B} bits")
print(f"routing tables: mean non-empty buckets per node = {nonempty / N_NODES:.2f}"
      f"  (log2(N) ~= {math.log2(N_NODES):.2f})")

def k_closest_of(node, target, k):
    t = buckets[by_id[node]]
    allc = [v for b in t.values() for v in b] + [node]
    return sorted(allc, key=lambda v: dist(v, target))[:k]

def lookup(initiator, target, alpha):
    cand = sorted(k_closest_of(initiator, target, 2 * K), key=lambda v: dist(v, target))
    seen = {initiator}
    queried, rounds, rpcs = set(), 0, 0
    while True:
        fringe = [v for v in cand if v not in queried][:alpha]
        if not fringe:
            break
        rounds += 1
        for v in fringe:
            queried.add(v)
            rpcs += 1
            cand += k_closest_of(v, target, K)
        cand = sorted(set(cand) - seen, key=lambda w: dist(w, target))
        topk = cand[:K]
        if all(w in queried for w in topk):
            break
    topk = cand[:K]
    truth = sorted((v for v in ids if v != initiator), key=lambda v: dist(v, target))[:K]
    hit = len(set(topk) & set(truth)) / K
    return rounds, rpcs, hit

rng = random.Random(SEED)
print(f"lookups={LOOKUPS} per alpha; success = |returned k  AND  true k closest| / k\n")
hdr = f"{'alpha':>5} {'p50 rounds':>10} {'p95 rounds':>10} {'max':>4} {'mean rpcs':>9} " \
      f"{'success':>8}"
print(hdr)
for alpha in ALPHAS:
    res = [lookup(rng.choice(ids), rng.getrandbits(B), alpha) for _ in range(LOOKUPS)]
    rounds = sorted(r for r, _, _ in res)
    hits = sum(h for _, _, h in res) / LOOKUPS
    mean_rpcs = sum(c for _, c, _ in res) / LOOKUPS
    p = lambda q: rounds[min(len(rounds) - 1, int(q * LOOKUPS))]
    print(f"{alpha:>5} {p(0.50):>10} {p(0.95):>10} {rounds[-1]:>4} "
          f"{mean_rpcs:>9.1f} {hits:>7.1%}")
print("\ntheory: each hop at least halves the XOR distance once k=20 contacts cover")
print("the target's subtree, so expected hops ~ log2(N)/log2(branching) ~ few, not N.")
```

Real output (Python 3.12):

```text
nodes=1000  k=20  ids=160 bits
routing tables: mean non-empty buckets per node = 10.29  (log2(N) ~= 9.97)
lookups=300 per alpha; success = |returned k  AND  true k closest| / k

alpha p50 rounds p95 rounds  max mean rpcs  success
    1         22         23   24      21.5  100.0%
    3          9         10   11      25.8  100.0%

theory: each hop at least halves the XOR distance once k=20 contacts cover
the target's subtree, so expected hops ~ log2(N)/log2(branching) ~ few, not N.
```

Read the two headline numbers like an interviewer would: the ~10.3 non-empty buckets
per node confirm the `log2(N)` routing-table density prediction, and the alpha=1 ->
alpha=3 comparison shows concurrency cutting sequential rounds from 22 to 9 (2.4x)
while total RPCs rise only from 21.5 to 25.8 (20%). Lookups return the exact k closest
set in both cases -- correctness is independent of concurrency, latency is not.

## Related Pages and Where to Go Next

- Hashing at the edge of the keyspace: [Rendezvous Hashing](./rendezvous-hashing.md)
  and [Membership & Hashing](./membership-hashing.md) cover single-hop alternatives.
- Keeping replicas consistent once a value is found:
  [Anti-Entropy Protocols](./anti-entropy.md) and
  [Merkle Tree Synchronization](./merkle-sync.md).
- The deployed system view: [IPFS and Filecoin](../../blockchain/ipfs-filecoin.md)
  (libp2p KadDHT modes, provider records) and
  [Decentralized Infrastructure](../../blockchain/decentralized-infra.md).

## References

1. P. Maymounkov, D. Mazieres. "Kademlia: A Peer-to-peer Information System Based on
   the XOR Metric." IPTPS 2002. <https://pdos.csail.mit.edu/~petar/papers/maymounkov-kademlia-lncs.pdf>
   (proceedings version: <https://link.springer.com/chapter/10.1007/978-3-540-45172-3_12>)
2. BitTorrent.org. "BEP 5: The DHT Protocol."
   <https://www.bittorrent.org/beps/bep_0005.html>
3. I. Baumgart, S. Mies. "S/Kademlia: A Practicable Approach Towards Secure Key-Based
   Routing." ICPADS 2007. <https://doi.org/10.1109/ICPADS.2007.4447808>
4. E. Heilman, A. Kendler, A. Zohar, S. Goldberg. "Eclipse Attacks on Bitcoin's
   Peer-to-Peer Network." USENIX Security 2015.
   <https://www.usenix.org/system/files/conference/usenixsecurity15/sec15-paper-heilman.pdf>
5. Y. Qiao, F. Bustamante. "Structured and Unstructured Overlays under the
   Microscope." USENIX ATC 2006.
   <https://www.usenix.org/legacyurl/structured-and-unstructured-overlays-under-microscope-measurement-based-view-two-p2p-syste>
6. Ethereum devp2p spec. "Node Discovery Protocol v5 -- wire protocol."
   <https://github.com/ethereum/devp2p/blob/master/discv5/discv5-wire.md>
