# Weighted Quorums and Vote Assignment

> The majority rule treats every node as equal — but real systems
> don't have equal nodes. A 3-datacenter deployment with 4 replicas in
> the big region and 1 in the small one should not let the small
> region veto every write, nor should the big region's four nodes each
> carry a full vote. Weighted quorums (Garcia-Molina & Barbara, 1985)
> generalize voting: assign each node a number of votes, define read
> and write quorum thresholds, and choose the assignment. This page
> covers the vote algebra, ROWA and its traps, and the tunable-quorum
> continuum Dynamo-style systems popularized.

## The Vote Conditions

Give node i weight `w_i`; total votes `W = Σ w_i`. A write quorum
collects `w` votes, a read quorum `r` votes. For the read/write
protocol to be safe (any read quorum intersects any write quorum, and
any two write quorums intersect):

```text
 w > W/2          (two writes always share a node)
 r + w > W        (a read always meets the latest write)
 (r <= W, w <= W) (quorums must be collectable)
```

Majority quorums are the special case `w_i = 1, r = w = ⌊W/2⌋ + 1`.

## ROWA and the Vote-Inflation Trap

Read-One-Write-All: `r = 1, w = W` — reads are instant, writes need
every node. Perfectly safe... and perfectly fragile: one dead replica
stops all writes, and every new node must get a vote or silently fall
out of the intersection requirement.

Gifford's weight trick and the "votes-withghosts" pattern: an
unavailable-but-trusted site can be *assigned votes that are counted
only for read quorums* — the practical middle ground. The general
result (Garcia-Molina & Barbara): **there is always a vote assignment
that survives the failure of any minority of nodes** — but finding
the assignment that maximizes availability for a given r/w profile is
a nontrivial optimization (their paper gives the dynamic-programming
treatment).

## Dynamo-Style Tunable Quorums

Dynamo (DeCandia et al., SOSP 2007) turned the algebra into a
per-request knob: `R` and `W` as counts of *coordinators' replies*
(with N replicas per key):

```text
 N = 3, W = 2, R = 2:  classic quorum; eventual consistency window
                       exists between a write acked by 2 and the 3rd
 N = 3, W = 1, R = 1:  "eventual" mode: fastest, weakest
 N = 3, W = 3, R = 1:  write-all/read-one (ROWA-shaped)
 R + W > N            => strong (quorum) reads see the latest write
 R + W <= N           => eventual; conflicts resolved by vector-clock
                         reconciliation (see [vector clocks])
```

Note the difference from the vote model: Dynamo's R/W are replica
*counts*, not vote weights — all replicas weigh 1. Weighted voting
generalizes when replicas are heterogeneous (a beefy replica could
carry 3 votes, a Raspberry replica 1) — mostly of theoretical interest
today, because heterogeneous weights complicate partition analysis
without helping latency.

## Availability Arithmetic

For homogeneous node-up probability p, the write availability of a
w-of-N weighted scheme is the binomial tail; the interesting result is
that vote assignment can *trade* read vs write availability along the
r+w > W frontier. The demo sweeps the frontier for N=5.

## Worked Demo: The r+w Frontier

The demo enumerates (r, w) pairs satisfying safety for N=5, computes
read/write availability at p=0.95, and shows the hot-vote problem:
which node sits in the most quorums.

```python
from itertools import combinations
from math import comb

N, p = 5, 0.95

def avail(q):
    """P(at least q of N up)."""
    return sum(comb(N, k) * p**k * (1-p)**(N-k) for k in range(q, N+1))

print(f"{'(r,w)':>7} {'safe':>5} {'read avail':>11} {'write avail':>12}")
for r in range(1, N+1):
    for w in range(1, N+1):
        if r + w > N and w > N/2:
            print(f"({r},{w})  {'yes':>5} {avail(r):11.4f} {avail(w):12.4f}")

# hot-vote: with W=1..5 write quorum sizes, how often is node 0 the
# pivot of intersection? For uniform quorums it's symmetric; the real
# hot-vote problem arises with WEIGHTS. Demonstrate: weights (3,1,1,1,1)
W_votes = [3, 1, 1, 1, 1]     # node 0 heavyweight
wq = 4                        # write quorum 4 votes, r = 2 votes
# write quorums: node0 + any two lightweights, or all four lightweights
wq_list = [[0,1,2],[0,1,3],[0,1,4],[0,2,3],[0,2,4],[0,3,4],[1,2,3,4]]
from collections import Counter
c = Counter()
for q in wq_list:
    for nd in q:
        c[nd] += 1
print("\nvote weights:", W_votes, " write-quorum threshold: 4 votes")
print("appearances in write quorums:", dict(sorted(c.items())))
```

Real output:

```text
  (r,w)  safe  read avail  write avail
(1,5)    yes      1.0000       0.7738
(2,4)    yes      1.0000       0.9774
(2,5)    yes      1.0000       0.7738
(3,3)    yes      0.9988       0.9988
(3,4)    yes      0.9988       0.9774
(3,5)    yes      0.9988       0.7738
(4,3)    yes      0.9774       0.9988
(4,4)    yes      0.9774       0.9774
(4,5)    yes      0.9774       0.7738
(5,3)    yes      0.7738       0.9988
(5,4)    yes      0.7738       0.9774
(5,5)    yes      0.7738       0.7738

vote weights: [3, 1, 1, 1, 1]  write-quorum threshold: 4 votes
appearances in write quorums: {0: 6, 1: 4, 2: 4, 3: 4, 4: 4}
```

The real table makes the trade legible. The only r=1 row is (1,5) —
read-one/write-ALL: writes need every node, so write availability is
the all-five-up probability (0.7738) — the ROWA fragility in one
number. As r grows and w shrinks, the burden flips: (4,3) reads at
0.9774 while writes stay at 0.9988. The balanced point (3,3) —
classical majority — sits at 0.9988 on both sides. Note which pairs
are *absent*: (1,4) fails safety because a 1-node read quorum can
miss a 4-node write entirely; the frontier r+w > 5 is exactly the
no-blind-spot condition. The weighted-vote block shows the hot-vote
effect: with node 0 carrying 3 of the 6 votes, six of the seven
minimal 4-vote write quorums include it — load and failure
criticality concentrate on the heavyweight.

## Interview Questions

1. State the two safety inequalities for vote-based quorums and why
   each is needed. (`w > W/2` — write-write intersection; `r + w > W`
   — read meets latest write.)
2. Why is ROWA unsafe against partition-free failures if a replica
   *unilaterally* leaves the write set? (A read quorum of 1 can then
   hit the stale replica — the excluded node must be excluded by
   quorum decision, not by drift.)
3. How do Dynamo's (N, R, W) relate to the vote model? (Uniform
   weights; R/W as replica counts; R+W>N is the read-meets-write
   condition restated.)
4. What is the hot-vote problem and its standard cure? (Heavyweight
   nodes appear in nearly every quorum; cure by balancing weights or
   dynamic vote reassignment — Garcia-Molina's DP over assignments.)
5. A team proposes weights (4,1,1) with W=6, w=4, r=3. Safe?
   (w=4 > 3 ✓, r+w=7 > 6 ✓ — safe; but node 0 is in every write
   quorum: single point of write-load.)

## References

- Garcia-Molina, H., Barbara, D. *How to Assign Votes in a Distributed
  System*. JACM 32(4), 1985. https://doi.org/10.1145/4221.4223
  (verified via Crossref)
- Gifford, D. *Weighted Voting for Replicated Data*. SOSP 1979.
  https://doi.org/10.1145/800215.806583 (verified via Crossref)
- DeCandia, G. et al. *Dynamo: Amazon's Highly Available Key-value
  Store*. SOSP 2007. https://doi.org/10.1145/1294261.1294281
  (verified via Crossref)
- Naor, M., Wool, A. *The Load, Capacity, and Availability of Quorum
  Systems*. SIAM J. Comput. 27(2), 1998.
  https://doi.org/10.1137/S0097539795281232 (verified via Crossref)
- Cassandra docs on consistency levels (the deployed tunable-quorum
  interface): https://cassandra.apache.org/doc/latest/cassandra/architecture/guarantees.html
  (probed 200)

## Cross-References

- [Quorum systems (Maekawa)](./distributed-mutex.md) — structural
  quorums in the mutex setting.
- [Vector clocks](./vector-clocks.md) — the conflict detector that
  makes R+W<=N modes workable.
- [Flexible Paxos](../consensus/flexible-paxos.md) — asymmetric
  quorums for consensus phases instead of reads/writes.
- [Chain replication](../replication/chain.md) — quorum-free safety by
  ordering.
