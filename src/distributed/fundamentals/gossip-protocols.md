# Gossip Dissemination Dynamics: Push, Pull, and the O(log N) Tail

Most distributed-systems texts describe gossip in one sentence: "nodes exchange state
with random peers until everyone converges." That sentence hides the engineering
content: how many rounds does convergence take, who should call whom -- the informed
(push) or the uninformed (pull) -- what does fanout k buy, and why does the last 1% of
the cluster always lag? This page works through those dynamics quantitatively, with a
seeded simulation you can rerun, and maps them onto four production systems.

Scope note: the survey overview lives in [Gossip Protocol](./gossip.md); the
reconciliation layer that repairs anything gossip misses lives in
[Anti-Entropy](../advanced/anti-entropy.md), [Merkle Sync](../advanced/merkle-sync.md),
and [SWIM and Failure Detection](./swim-membership.md).

## Why Epidemic Propagation Instead of a Spanning Tree

A fixed spanning tree is the "obvious" broadcast fabric: n-1 messages per broadcast,
depth equal to tree height. But the root and internal nodes are hot spots and failure
points, membership must be known before the tree is built, and churn forces constant
reconstruction. Epidemic propagation trades wasted messages (duplicates are common)
for O(log N) broadcast depth, no single point of failure, and churn immunity, since
each round re-samples fresh random peers. The idealized doubling phase:

```text
round:    1     2     3     4     5    ...    r           r + t
informed: 1  -> 2  -> 4  -> 8  -> 16  ...  -> ~N/2  ->     N
          \____________ log2(N) rounds ________/   \_ clearance _\
```

No coordination produces this: random contacts supply the expansion. The interesting
question -- the one Demers et al. answered -- is what happens after the doubling
phase, when most contacts hit nodes that already know the rumor.

## Three Contact Modes (Demers et al., 1987)

Demers et al. were maintaining Xerox's Clearinghouse name service (on the order of 150
replicated sites) and wanted update propagation that required almost nothing from the
network below. They analyzed two flavors: **anti-entropy** -- replica pairs eventually
compare full state and reconcile, terminating only when identical (the reliable
workhorse, with its own page: [Anti-Entropy](../advanced/anti-entropy.md)); and
**rumor mongering** -- a hot update spreads like an infection but each site's interest
decays (old rumors are forwarded with a shrinking probability), so the update dies out
and stragglers are mopped up later by anti-entropy. Within either flavor the per-round
contact can be:

| Mode | Who initiates a contact | What a contact costs | Where it wins |
| --- | --- | --- | --- |
| Push | Informed node sends state to a random peer | Proportional to informed set | Early rounds: contacts land in virgin territory |
| Pull | Uninformed node polls a random peer | Proportional to the whole cluster | Late rounds: probing pressure concentrates on the uninformed |
| Push-pull | Every node exchanges with a random peer, both directions | Sum of the two | Fastest round counts; the default in production designs |

Push-only weakens as the informed fraction approaches 1: nearly all traffic becomes
duplicate deliveries and the last few stragglers are found slowly. Pull-only has the
mirror-image weakness: when almost nobody is informed, nearly every probe misses.
Push-pull gets the good half of each phase, which is why every production design since
favors it.

## Round Counts: The Exponential Climb and the Logarithmic Tail

For the classic random-phone-call model on a complete graph of n nodes, theory gives:

| Regime | Result | Attribution |
| --- | --- | --- |
| Push-only spread time | log2(n) + ln(n) + O(log log n) rounds w.h.p. | Pittel, 1987 |
| Push-pull spread time | O(log n) rounds w.h.p. | Karp et al., 2000 |
| Push-pull message cost | O(n log log n) transmissions w.h.p. -- far below push-only's ~n log n | Karp et al., 2000 |

The ln(n) term is the *tail*: clearing the last handful of nodes takes logarithmically
many extra rounds, because random contacts rarely land on the uninformed remnant. The
shape of the whole process:

```text
informed
  N |                          .................  <- slow last 1% (the tail)
    |                     .
    |                .        exponential climb: ~log2(N) rounds
    |        .
    |    . .
  1 |__1__________________________________________
        rounds
```

Fanout k (k contacts per node per round) multiplies message cost by k but cuts round
counts roughly toward log_{k+1}(N). Since a round is one gossip interval (usually 1
second), rounds are the wall-clock bottleneck -- so production pays fanout 2-3.

## A Seeded Simulation (Model)

The script below is a **MODEL**, not a real protocol run: complete graph, synchronized
rounds, uniform random peer choice, node 0 starts infected, identities exchangeable
under uniform sampling. It is deterministic -- `random.seed(7)`.

```python
import math
import random
random.seed(7)  # deterministic
TRIALS = 400
def spread(mode, n, f):
    """MODEL: complete graph, synchronized rounds, node 0 starts infected.
    Returns (rounds, contacts, rounds_to_99pct)."""
    informed, rounds, contacts = 1, 0, 0
    r99, hit = 0, math.ceil(0.99 * n)
    while informed < n:
        rounds += 1
        newly = set()
        if "push" in mode:              # each informed node calls f peers
            for _ in range(informed * f):
                contacts += 1
                v = random.randrange(n)
                if v >= informed:
                    newly.add(v)
        if "pull" in mode:              # each uninformed node polls f peers
            for u in range(informed, n):
                for _ in range(f):
                    contacts += 1
                    if random.randrange(n) < informed:
                        newly.add(u)
                        break
        if informed < hit <= informed + len(newly):
            r99 = rounds
        informed += len(newly)
    return rounds, contacts, r99
def run(mode, n, f):
    """Averages over TRIALS seeded runs; contacts are per informed-capable node."""
    tot = [0, 0, 0]
    for _ in range(TRIALS):
        for i, v in enumerate(spread(mode, n, f)):
            tot[i] += v
    return tot[0] / TRIALS, tot[1] / TRIALS / n, tot[2] / TRIALS

for n in (256, 1024):
    print("N=%d  log2(N)=%.1f  log2(N)+ln(N)=%.2f" % (n, math.log2(n), math.log2(n) + math.log(n)))
    for mode in ("push", "pull", "push-pull"):
        r, c, _ = run(mode, n, 1)
        print("  %-9s fanout=1  avg rounds %5.2f   avg contacts/node %6.2f" % (mode, r, c))

print()
print("Tail check, push-only fanout=1:")
for n in (256, 1024):
    r, c, r99 = run("push", n, 1)
    print("  N=%4d  rounds to 99%% %5.2f   rounds to 100%% %5.2f   tail %5.2f" % (n, r99, r, r - r99))
print()
print("Fanout sweep, push-pull, N=1024:")
for f in (1, 2, 4):
    r, c, _ = run("push-pull", 1024, f)
    print("  fanout=%d  rounds %5.2f   contacts/node %6.2f" % (f, r, c))
```

Output (real run of the script above):

```text
N=256  log2(N)=8.0  log2(N)+ln(N)=13.55
  push      fanout=1  avg rounds 14.65   avg contacts/node   6.56
  pull      fanout=1  avg rounds 11.52   avg contacts/node   8.10
  push-pull fanout=1  avg rounds  7.64   avg contacts/node   7.64
N=1024  log2(N)=10.0  log2(N)+ln(N)=16.93
  push      fanout=1  avg rounds 18.05   avg contacts/node   7.94
  pull      fanout=1  avg rounds 13.75   avg contacts/node  10.06
  push-pull fanout=1  avg rounds  9.20   avg contacts/node   9.20

Tail check, push-only fanout=1:
  N= 256  rounds to 99% 13.21   rounds to 100% 14.71   tail  1.51
  N=1024  rounds to 99% 15.14   rounds to 100% 18.06   tail  2.92

Fanout sweep, push-pull, N=1024:
  fanout=1  rounds  9.16   contacts/node   9.16
  fanout=2  rounds  6.20   contacts/node  11.95
  fanout=4  rounds  4.87   contacts/node  17.96
```

How to read it against the theory anchors:

- Push-only at N=1024 takes 18.05 rounds, ~8 past the log2(N) climb; ~3 of those go to
clearing the final 1%, and the tail grows with N (1.51 -> 2.92 from 256 to 1024 nodes)
-- the logarithmic clearance in Pittel's and Karp et al.'s bounds.
- Pull beats push on rounds (13.75 vs 18.05) because probing pressure concentrates on
the uninformed set, at the price of wasted probes (10.06 contacts/node); it would look
worse if informed nodes also polled, as in the phone-call model.
- Push-pull lands at 9.20 rounds, essentially the log2(N) doubling bound with both
directions helping; at fanout 1 its contact count equals its round count -- rounds,
not messages, are the resource to reason about in synchronous gossip.
- The fanout sweep tracks log_{fanout+1}(N) closely: 9.16 / 6.20 / 4.87 measured vs
10.0 / 6.33 / 5.01 idealized, with linear contact growth; returns diminish fast past
fanout 2-4.

## Beyond Rumor Spreading: Aggregation, Partial Views, Broadcast Trees

**Aggregate gossip (push-sum).** Random contacts can also compute. Kempe, Dobra, and
Gehrke showed that nodes holding pairs (s, w) can estimate a global sum or average:
each round a node halves its pair and sends one half to a random peer; after O(log n)
rounds w.h.p. every node's ratio s/w converges to the global value. No coordinator, no
need to know n -- cluster-wide averages with membership-grade churn tolerance.

**Partial membership (HyParView).** Full-member gossip costs O(n) state and traffic
per node. HyParView keeps an *active view* of roughly log n + k nodes (the actual
fanout) plus a larger passive view of spares; failures promote from passive to active,
and symmetric active views let gossip traffic itself repair the overlay. The paper
demonstrates reliable broadcast under very high failure rates.

**Epidemic broadcast trees (PlumTree).** PlumTree recovers the spanning tree's message
economy without its fragility: eager messages flow on a dynamically *stable* tree,
lazy messages (fingerprints only) on redundant links, and when the tree breaks the
epidemic flood reconstructs it. This tree-plus-gossip hybrid is what libp2p's
gossipsub implements for IPFS pubsub: a per-topic mesh of degree D=6 (bounds 4-12)
forwarding full messages plus gossip about message ids beyond the mesh to heal
cheaply; gossipsub v1.1 layers peer scoring on the same machinery.

## Where This Runs in Production

| System | Gossip's job | Concrete parameter or quote (verified) |
| --- | --- | --- |
| Apache Cassandra | Cluster membership and failure detection | One round per second: `Gossiper.intervalInMillis = 1000` in Gossiper.java; docs describe "membership and failure detection via a gossip protocol" |
| HashiCorp Consul (memberlist) | LAN and WAN membership pools | Docs: "LAN gossip pool is enabled by default. It communicates with all nodes in a single datacenter to share membership information"; separate WAN pool links datacenters; built on SWIM |
| Redis Cluster | Node discovery and health flags over the cluster bus | Cluster spec: the gossip section "only contains information about a few random nodes among the set of nodes known to the sender"; a node is trusted only when an already-trusted node gossips about it |
| libp2p gossipsub (IPFS) | PubSub message dissemination | Spec defaults: mesh degree D=6, D_low=4, D_high=12, 1 s heartbeat; v1.1 adds score-based gossip emission |

The pattern: each pairs the epidemic layer with something reliable beneath it --
Cassandra with Merkle-tree repair, memberlist with SWIM's probe/suspect state machine,
Redis with configuration epochs, gossipsub with IHAVE grafting. Dissemination is fast
but probabilistic; the partner converts "eventually" into "definitely."

## Pitfalls

- **Counting rounds but not bandwidth.** Fanout 4 quarters round counts yet multiplies
  total messages by 4 on the climb; budget both (see the sweep above).
- **Run-and-forget without anti-entropy.** Rumor mongering that never dies floods the
cluster with duplicates forever; that dies too fast silently drops stragglers -- the
decay probability is a real tuning decision.
- **Non-uniform peer selection.** The O(log N) bounds assume uniform random contacts;
  buggy shuffling (sticky neighbors, partial shuffles) quietly degrades doubling into
  something linear-ish.
- **Late joiners and partitions.** A node learns nothing it does not pull or receive;
  rejoin-after-partition is the same problem. Periodic anti-entropy exists for this --
  never tune gossip intervals as if they gave delivery guarantees.
- **Epidemic amplification of stale state.** Gossip spreads whatever you feed it,
  including outdated node state; version everything exchanged (generation numbers,
  [Vector Clocks](./vector-clocks.md), [CRDTs](./crdts.md)) so old state loses
  deterministically.
- **Confusing dissemination with lookup.** Gossip floods toward everyone; a DHT routes
  toward the data's owner in O(log N) hops with constant per-hop fanout. Different
  questions -- compare [Kademlia DHT](../advanced/kademlia-dht.md).

## References

1. A. Demers et al. *Epidemic Algorithms for Replicated Database Maintenance.* PODC 1987. https://doi.org/10.1145/41840.41841
2. B. Pittel. *On Spreading a Rumor.* SIAM J. Applied Mathematics 47(1), 1987. https://doi.org/10.1137/0147013
3. R. Karp, C. Schindelhauer, S. Shenker, B. Vocking. *Randomized Rumor Spreading.* FOCS 2000. https://doi.org/10.1109/SFCS.2000.892324
4. D. Kempe, A. Dobra, J. Gehrke. *Gossip-Based Computation of Aggregate Information.* FOCS 2003. https://doi.org/10.1109/SFCS.2003.1238221
5. A. Das, I. Gupta, A. Motivala. *SWIM: Scalable Weakly-consistent Infection-style Process Group Membership Protocol.* DSN 2002. https://doi.org/10.1109/DSN.2002.1028914
6. N. Carvalho, J. Pereira, L. Rodrigues. *HyParView: A Membership Protocol for Reliable Gossip-Based Broadcast.* DSN 2007. https://doi.org/10.1109/DSN.2007.56
7. J. Leitao, J. Pereira, L. Rodrigues. *Epidemic Broadcast Trees.* SRDS 2007. https://doi.org/10.1109/SRDS.2007.27
8. libp2p. *gossipsub v1.0 spec* (defaults D=6, D_low=4, D_high=12) and *v1.1* (peer-scored gossip). https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.0.md
9. HashiCorp. *Consul Architecture: Gossip Protocol.* https://developer.hashicorp.com/consul/docs/architecture/gossip
10. Redis. *Redis Cluster Specification* (gossip on the cluster bus). https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/
11. Apache Cassandra. `Gossiper.java` (`intervalInMillis = 1000`). https://github.com/apache/cassandra/blob/cassandra-5.0/src/java/org/apache/cassandra/gms/Gossiper.java

## Related Topics

- [Gossip Protocol](./gossip.md) -- survey-level overview and interview framing
- [Anti-Entropy](../advanced/anti-entropy.md) -- the reliable reconciliation layer
- [SWIM and Failure Detection](./swim-membership.md) -- infection-style membership, phi-accrual detection
- [Membership and Hashing](../advanced/membership-hashing.md) -- consistent/rendezvous hashing on gossip membership
- [Kademlia DHT](../advanced/kademlia-dht.md) -- the routed-lookup alternative to epidemic flooding
