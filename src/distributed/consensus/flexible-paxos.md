# Flexible Paxos: Quorum Intersection Revisited

> Every Paxos textbook starts with "a majority" as if majorities were
> the point. They aren't. The point is *intersection*: the quorum of
> nodes that elects a leader (phase 1) must intersect the quorum that
> commits a value (phase 2), so the new leader is guaranteed to see
> every decision the old one made. Flexible Paxos (Howard, Malkhi &
> Spiegelman, OPODIS 2016) observes that nothing forces the two quorum
> systems to be the same size — and the whole design space of
> asymmetric quorums opens up. This page works the safety argument,
> the design space, and the systems (Fast Paxos, WPaxos) that had been
> accidentally living inside it.

## The Traditional Story, Stated Carefully

Multi-Paxos safety argument, phrased for what Flexible Paxos will
replace:

```text
 Phase 1 (prepare/elect):  leader gathers votes from a quorum Q1,
                            learning the highest-numbered accepted value
 Phase 2 (accept/commit):  leader replicates a value to a quorum Q2

 SAFETY: a value chosen in slot k remains chosen across leader change.
         The new leader's Q1 must contain at least one acceptor that
         participated in the old leader's Q2 for slot k.
         => Q1 ∩ Q2 ≠ ∅ (for every pair of quorums)
```

With Q1 = Q2 = majority, intersection is automatic — but the
*constraint* was never "both are majorities". It is only that the
families intersect pairwise. Generalize: let E1 be the size of phase-1
quorums (election) and E2 the size of phase-2 quorums (commit). For
the natural homogeneous family where any E1-sized set and any E2-sized
set must intersect:

```text
  E1 + E2 > n        (pigeonhole: two sets whose sizes sum to > n
                      cannot be disjoint)
```

So for n = 5: majority/majority (3,3) is just one point in a space that
also contains (1,5), (2,4), (4,2), (5,1), (3,3) — and for non-uniform
quorum *systems* (grids, weights) the space is larger still.

## Why Asymmetry Is Useful

The two phases have opposite performance personalities:

- **Phase 2 (commit) runs per value, on the hot path.** Its latency is
  your write latency; its size is your write amplification.
- **Phase 1 (election) runs once per leader term.** It is rare —
  paying more for it is nearly free in steady state.

Hence the production-friendly asymmetry: *grow E1, shrink E2*. With
n = 5, (E1, E2) = (4, 2): every commit writes to only 2 nodes, while
elections must gather 4 votes. Commits got cheaper and elections stay
rare — availability of *commits* (needs 2 of 5 alive) improves, while
availability of *elections* (needs 4 of 5) worsens. That tradeoff is a
real product decision: if failures are usually failures of nodes not
in the current leader's chosen commit set, small E2 with large E1 can
be a win; if you fear partitions that leave 3 of 5 up, it is a loss.

The symmetric choice (1, 5) — commit to *all*, elect from *any one* —
is "read-one/write-all", and (E1=2, E2=4) resembles ROWA with a
repair-witness. All of these live in one safety envelope.

## Prior Art Reinterpreted

- **Fast Paxos** (Lamport, 2006): fast rounds accept to 3n/4 while
  recovery uses majority — precisely Flexible Paxos with
  (E1 = ⌊n/2⌋+1, E2 = ⌊3n/4⌋+1). Fast Paxos derived its 3n/4 by
  collision-probability arguments; Flexible Paxos shows it as one
  point of the general tradeoff curve.
- **WPaxos** (Ailijiang, Charapko & Demirbas, 2017): wide-area Paxos
  with *agile per-object leaders*; each object's leader commits within
  its local zone's quorum (small E2, low WAN latency) while Stealing/
  Rebalancing phases use wider quorums (large E1) to hand leadership
  across zones. Flexible quorums per phase are the enabling grammar.
- **Grid quorum systems**: arrange n nodes in a √n × √n grid; read
  quorum = one full column, write quorum = one full row. Column ∩ row
  = exactly one node: E1 = √n, E2 = √n, n = √n × √n — both quorums far
  below majority, intersection preserved by structure rather than
  size. (Cost: any two column-readers can collide on write availability
  analysis, and a single row+column node failure pattern can block
  writes.)

## Availability Math

For homogeneous quorums of sizes (E1, E2) with each node independently
up with probability p, the commit path is available when ≥ E2 of n are
up. The Flexible Paxos constraint means shrinking E2 forces growing E1
— elections become the fragile phase. The demo tabulates this.

## Worked Demo: The Design Space for n = 5

The demo enumerates all (E1, E2) pairs satisfying safety for n = 5,
computes commit/elect availability under p = 0.9 per node, and runs a
tiny linearizability check: with (E1, E2) violating intersection, it
constructs the classic lost-value execution.

```python
from itertools import combinations

n, p = 5, 0.9

def availability(qsize):
    """P(at least qsize of n nodes up), Binomial CDF."""
    from math import comb
    return sum(comb(n, k) * p**k * (1-p)**(n-k) for k in range(qsize, n+1))

print(f"{'(E1,E2)':>9} {'safe?':>6} {'elect avail':>12} {'commit avail':>13}")
for e1 in range(1, n+1):
    for e2 in range(1, n+1):
        safe = e1 + e2 > n
        print(f"({e1},{e2})   {str(safe):>6} {availability(e1):12.4f} "
              f"{availability(e2):13.4f}")

# Linearizability counterexample for an unsafe pair (E1=1, E2=1, n=2):
# A commits x=1 to node a; A stalls. B elects via node b (E1=1,
# sees nothing), commits x=2 to node b (E2=1). Both quorums satisfied,
# histories are incomparable -> lost update.
print()
print("unsafe (1,1) execution on n=2:")
print("  A: commit(x=1) -> node a          [quorum size 1 OK]")
print("  B: prepare()   -> node b          [E1=1: learns nothing]")
print("  B: commit(x=2) -> node b          [quorum size 1 OK]")
print("  final: a says x=1, b says x=2 -> inconsistent")
```

Real output:
```text
  (E1,E2)  safe?  elect avail  commit avail
(1,1)    False       1.0000        1.0000
(1,2)    False       1.0000        0.9995
(1,3)    False       1.0000        0.9914
(1,4)    False       1.0000        0.9185
(1,5)     True       1.0000        0.5905
(2,1)    False       0.9995        1.0000
(2,2)    False       0.9995        0.9995
(2,3)    False       0.9995        0.9914
(2,4)     True       0.9995        0.9185
(2,5)     True       0.9995        0.5905
(3,1)    False       0.9914        1.0000
(3,2)    False       0.9914        0.9995
(3,3)     True       0.9914        0.9914
(3,4)     True       0.9914        0.9185
(3,5)     True       0.9914        0.5905
(4,1)    False       0.9185        1.0000
(4,2)     True       0.9185        0.9995
(4,3)     True       0.9185        0.9914
(4,4)     True       0.9185        0.9185
(4,5)     True       0.9185        0.5905
(5,1)     True       0.5905        1.0000
(5,2)     True       0.5905        0.9995
(5,3)     True       0.5905        0.9914
(5,4)     True       0.5905        0.9185
(5,5)     True       0.5905        0.5905

unsafe (1,1) execution on n=2:
  A: commit(x=1) -> node a          [quorum size 1 OK]
  B: prepare()   -> node b          [E1=1: learns nothing]
  B: commit(x=2) -> node b          [quorum size 1 OK]
  final: a says x=1, b says x=2 -> inconsistent
```

Read the asymmetry off the table. (4,2) keeps commit availability at
0.9914 (2 of 5 up suffices) but elections now need 4 of 5: elect
availability drops to 0.9185 — the availability you traded for cheap
commits lives in the election path. (2,3) is the mirror image the
other way: robust elections (0.9995), commits needing 3 of 5
(0.9995) — nearly majority-like. And the diagonal (3,3) recovers
classical majority. The rows marked False are unsafe: no quorum
relabeling can rescue (1,1)-(1,4) etc., because E1 + E2 <= n admits
disjoint election/commit sets — the lost-update execution at the
bottom shows the violation concretely.

## Interview Questions

1. State the exact safety condition Flexible Paxos relaxes.
   (Not "quorums must be majorities" but "every phase-1 quorum must
   intersect every phase-2 quorum"; majority is one solution, not the
   constraint.)
2. Under (E1, E2) = (4, 2) with n = 5, what breaks first: your ability
   to commit, or to elect a leader? (Elect — you need 4 of 5 up; that
   is the availability you traded away for 2-node commits.)
3. Why is Fast Paxos a special case? (Its fast-round quorum 3n/4 and
   recovery majority satisfy Q1 ∩ Q2 ≠ ∅ without either being a
   majority.)
4. How do grid quorum systems intersect without any quorum reaching
   n/2 + 1? (Structural intersection: rows and columns of a grid
   always cross; safety comes from shape, not size.)
5. A team proposes (E1, E2) = (2, 4) for n = 5 "because writes rarely
   fail". What is your objection? (Elections now need only 2 nodes —
   two partitioned minority nodes can each elect a leader; with
   disjoint E2s of size 4... actually (2,4) is safe; the objection is
   liveness churn: cheap elections mean more spurious leadership
   changes during partial failures, each stalling commits.)

## References

- Howard, H., Malkhi, D., Spiegelman, A. *Flexible Paxos: Quorum
  Intersection Revisited*. OPODIS 2016. arXiv:1608.06696.
  https://arxiv.org/abs/1608.06696 (probed 200)
- Lamport, L. *Fast Paxos*. Distributed Computing 19(2), 2006.
  https://doi.org/10.1007/s00446-006-0005-x (verified via Crossref)
- Ailijiang, A., Charapko, A., Demirbas, M. *WPaxos: Wide Area Network
  Flexible Consensus*. arXiv:1703.08905.
  https://arxiv.org/abs/1703.08905 (probed 200)
- Naor, M., Wool, A. *The Load, Capacity, and Availability of Quorum
  Systems*. SIAM J. Computing 27(2), 1998 — the general theory of
  quorum-system properties used above.
  https://doi.org/10.1137/S0097539795281232 (verified via Crossref)
- Lamport, L. *Paxos Made Simple*. ACM SIGACT News 32(4), 2001 — the
  canonical phase-1/phase-2 framing. https://lamport.azurewebsites.net/pubs/paxos-simple.pdf
  (probed 200)

## Cross-References

- [Paxos](./paxos.md) — the classic protocol this generalizes.
- [Multi-Paxos](./multi-paxos.md) — the majority-quorum deployment the
  relaxation starts from.
- [ePaxos](./epaxos.md) — another way off the leader path: per-object
  ordering via dependencies.
- [Quorum systems (Maekawa)](../fundamentals/distributed-mutex.md) —
  structural intersection in a different corner of the field.
