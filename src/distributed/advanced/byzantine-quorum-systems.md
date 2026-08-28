# Byzantine Quorum Systems: Masking, Disseminating, and the Q2 Conditions

A crash-fault quorum system only has to guarantee that any two quorums *touch*
(then read-write intersection gives you the latest write). Once servers can
lie - arbitrary Byzantine behavior - touching is not enough: the intersection
may consist entirely of faulty servers that echo the stale, or the forged,
value. Byzantine quorum systems fix this by sizing intersections so that
*honest witnesses always survive* inside them. This page gives the two
classical constructions (disseminating and masking quorum systems from
Malkhi-Reiter), the exact threshold arithmetic that makes `3b+1` and `4b+1`
tight, and the ways the model leaks when pushed into real deployments.

Scope note: this page assumes the *crash-fault* counterpart - read repair,
sloppy quorums, dynamo-style configurations - is already familiar; see
[quorum systems](./quorum-systems.md) for that treatment. Consensus machines
that happen to use these same quorum sizes internally (PBFT's `2b+1` of
`3b+1`) are covered in [PBFT](../consensus/pbft.md); DAG-based protocols that
lean on certified quorum intersections in their mempool layer are in
[Narwhal and Bullshark](../consensus/narwhal-bullshark.md).

## The setup and the adversary

n servers, at most b of them Byzantine: they may deviate arbitrarily - send
different values to different peers, collude, forge timestamps. Clients (the
readers/writers of replicated data) are assumed *non-faulty* in the base
model; the case of Byzantine clients needs extra machinery (see "pairing"
below). A **fail-prone system** B is the family of sets that can contain all
faulty servers; the threshold case collapses this to "any set of size b".

A **quorum system** Q is a set family with pairwise intersection; a
**b-disseminating** or **b-masking** quorum system strengthens what the
intersection must contain:

| property          | condition on every pair Q1, Q2 in Q   | what it buys                                              |
|-------------------|---------------------------------------|-----------------------------------------------------------|
| crash quorum      | Q1 and Q2 intersect (>= 1 element)     | a write is seen by every read                             |
| b-disseminating   | abs(Q1 and Q2) >= b + 1                | >= 1 honest server in every write-read intersection       |
| b-masking         | abs(Q1 and Q2) >= 2b + 1               | >= b + 1 honest servers; honest majority masks b liars    |

(All conditions pair with the availability requirement that a quorum still
exists after b failures - for threshold systems, q <= n - b.)

Why the names: in a **disseminating** system a written value *disseminates*
to at least one correct server in every later read quorum - the read will
retrieve the write as long as the *client* is honest and simply picks a value
properly. In a **masking** system the intersection carries b+1 correct
servers, a majority among honest ones, so the protocol can *mask* up to b
Byzantine servers answering with garbage during the read - this is what you
need when clients cannot be trusted to do authentication-by-majority
themselves, or when stale/liar servers must be outvoted at read time.

## The threshold arithmetic, exactly

For threshold systems (every q-subset of n is a quorum), the minimum
intersection of two distinct quorums is `2q - n`. Plugging into the
conditions:

- **b-disseminating** needs `2q - n >= b + 1` and `q <= n - b`. The tight
  solution is `n = 3b + 1, q = 2b + 1`: intersection = `2(2b+1) - (3b+1) =
  b + 1`. This is exactly PBFT's commit quorum shape, and the same numbers
  every BFT protocol quotes.
- **b-masking** needs `2q - n >= 2b + 1` and `q <= n - b`. Tight solution:
  `n = 4b + 1, q = 3b + 1`, intersection = `2(3b+1) - (4b+1) = 2b + 1`, of
  which `b + 1` are honest in the worst placement.

The near-misses matter as much as the bounds: `n = 3b + 1` with a
crash-style majority `q = 2b + 1`... wait, for b=1: n=4, q=3 gives
intersection 2 >= b+1=2 (dissemination works) but 2 < 2b+1=3 (masking
impossible) - one honest witness survives, but a single liar can outvote it
at read time. And shrinking the quorum to `q = b + 1` destroys even
dissemination: n=5, b=1, q=3 has minimum intersection 1, and that one server
can be the faulty one - no honest witness, values silently diverge. The demo
below enumerates *all* quorum pairs for small systems and confirms both the
tight families and these near-misses exhaustively.

```text
write path (masking system, n=5, b=1, q=4):
  writer sends value+hash to all 5, waits for 4 acks  ->  W = {s1,s2,s3,s4}

read path: reader contacts 4, gets (v, h) from each
  Q1 = {s1,s2,s3,s5}   intersection with W = {s1,s2,s3,s4} n Q1 = 3 servers
  worst case: s3 is Byzantine and answers with forged (v',h')
  honest pair (s1,s2) outvotes it: reader takes v whose hash
  is returned by >= q - b - 1 + 1 servers ... majority among honest
            intersection 2b+1 = 3 -> at least b+1 = 2 honest -> majority wins
```

## Byzantine clients: the pairing idea

Masking systems assume honest readers. A Byzantine *client* can simply lie
about what it read. The classical mitigation in the quorum framework is
**pairing** (Malkhi-Reiter): quorums are organized in pairs (Q, Q'), the
writer stores the data block in Q and authentication hashes in Q', and a
reader must fetch from both and check consistency. Now a lying client is
detectable by *other* clients: the hashes in Q' witness what Q returned.
The construction trades availability (both quorums of a pair must be live)
for end-to-end integrity that no client-side collusion can forge. The same
theme - separate the data path from the attestation path - recurs in
Byzantine storage designs like A2M/BFT-style trusted base, and in practice
most systems punt entirely: they authenticate *clients* cryptographically
(MACs, signatures per reply) and treat only servers as potentially Byzantine.

## Load, capacity, availability

Byzantine quorums inherit the Naor-Wool load metric: the load of a strategy
is the maximum, over servers, of the probability it is contacted; the load of
the system is the minimum over strategies. For threshold systems load = q/n,
so the tight families give:

| system                 | n     | q     | load  | availability under b faults |
|------------------------|-------|-------|-------|------------------------------|
| dissemination (b=1)    | 4     | 3     | 0.75  | one quorum survives any 1 failure |
| masking (b=1)          | 5     | 4     | 0.80  | same                          |
| dissemination (b=2)    | 7     | 5     | 0.71  | two failures tolerated        |
| masking (b=2)          | 9     | 7     | 0.78  | two failures tolerated        |

Two structural observations. First, BFT's price is visible in the load
column: a 4-node dissemination system loads every server at 75% just to be
able to read, versus 50% for the crash-fault majority quorum at n=3. Second,
non-threshold constructions exist that beat the load of threshold ones while
preserving the same Byzantine guarantees - the Malkhi-Reiter journal paper
carries explicit constructions (grid-based, "fan" systems) adapted to
Byzantine conditions, and the general theory of what load/capacity pairs are
achievable is Naor-Wool's.

## The adaptive-adversary caveat

The threshold analysis silently assumes the b faulty servers are fixed before
the protocol runs (a *static* adversary). An **adaptive** adversary that can
corrupt servers mid-protocol breaks naive deployments: it observes which
servers were in the read intersection, corrupts those specific honest
witnesses after the fact, and retroactively erases the evidence - unless the
system erases secrets (proactive recovery, periodic resharing) or the
constructions are made adaptive-safe by design. The journal version of the
Byzantine-quorum work treats this: adaptive-safe systems exist but need more
servers or cryptographic non-erasability assumptions. For a placement-prep
interview the one-line version is: ask whether "at most b" means *ever* or
*at any instant* - the two models have different lower bounds, and confusing
them is the most common design bug in byzantine-storage proposals.

## The demo: exhaustive intersection audit

```python
#!/usr/bin/env python3
r"""Quorum-intersection checker for Byzantine quorum systems.

For a threshold system over n servers -- every q-subset is a quorum --
and at most b Byzantine-faulty servers, enumerate ALL pairs of quorums
and report the worst case (equivalently: over all placements of the b
faulty servers, the adversary fills the intersection):

  min |Q1 n Q2|            smallest intersection over all quorum pairs
  min correct              smallest number of honest servers in any
                           intersection = min|Q1 n Q2| - b (floor 0)
  dissemination verdict    D-Consistency: min|Q1 n Q2| >= b+1 (the
                           intersection is never contained in a fail-prone
                           set, so at least one honest witness survives)
                           + availability q <= n - b
  masking verdict          M-Consistency: min|Q1 n Q2| >= 2b+1 elements,
                           hence >= b+1 correct ones; a value returned by
                           >= b+1 servers is therefore genuine
                           + availability q <= n - b

Pure stdlib, deterministic; exhaustive enumeration, so n is kept small.
"""
from itertools import combinations


def analyze(n, b, q):
    quorums = list(combinations(range(n), q))
    worst_int = n
    for q1, q2 in combinations(quorums, 2):
        s = len(set(q1) & set(q2))
        worst_int = min(worst_int, s)
    # worst case: the adversary places all b faulty servers inside the
    # intersection
    correct = max(0, worst_int - b)
    available = q <= n - b
    dissem = available and worst_int >= b + 1
    mask = available and worst_int >= 2 * b + 1
    return worst_int, correct, available, dissem, mask


CASES = [
    # (n, b, q, note)
    (3, 1, 2, "crash-style majority (Paxos/Raft)"),
    (4, 1, 3, "2b+1 commit quorum of n=3b+1 (PBFT-style)"),
    (4, 1, 4, "write-all-4"),
    (5, 1, 3, "byzantine quorum that is too small"),
    (5, 1, 4, "tight masking system (n = 4b+1)"),
    (7, 2, 5, "tight dissemination system (n = 3b+1)"),
    (9, 2, 7, "tight masking system (n = 4b+1)"),
]

print("threshold quorum systems: exhaustive intersection audit")
print(f"{'n':>2} {'b':>2} {'q':>2} | {'min|Q1nQ2|':>10} | {'min correct':>11} | "
      f"{'avail':>5} | {'dissem':>6} | {'mask':>4} | load | note")
print("-" * 92)
for n, b, q, note in CASES:
    wi, c, avail, dissem, mask = analyze(n, b, q)
    print(f"{n:>2} {b:>2} {q:>2} | {wi:>10} | {c:>11} | {str(avail):>5} | "
          f"{str(dissem):>6} | {str(mask):>4} | {q/n:.2f} | {note}")

# tight threshold families
print()
print("tight threshold families:")
for b in (1, 2, 3):
    n3, q3 = 3 * b + 1, (3 * b + 1 + b + 1 + 1) // 2   # ceil((n+b+1)/2)
    n4, q4 = 4 * b + 1, (4 * b + 1 + 2 * b + 1 + 1) // 2  # ceil((n+2b+1)/2)
    wi3, c3, avail3, dis3, _ = analyze(n3, b, q3)
    wi4, c4, avail4, _, mask4 = analyze(n4, b, q4)
    print(f"  b={b}: dissem n={n3}, q={q3}: min|Q1nQ2|={wi3} (need >= {b+1}), "
          f"min correct={c3}, dissem={dis3}, load={q3/n3:.2f}")
    print(f"  b={b}: mask   n={n4}, q={q4}: min|Q1nQ2|={wi4} (need >= {2*b+1}), "
          f"min correct={c4}, masking={mask4}, load={q4/n4:.2f}")

# the near-misses that justify the bounds
print()
print("near-misses (why 2f+1 / 3f+1 / 4f+1 are exact):")
for n, b, q in ((3, 1, 2), (4, 1, 3), (8, 2, 5)):
    wi, c, avail, dissem, mask = analyze(n, b, q)
    why = []
    if not avail:
        why.append(f"after {b} failures only {n-b} servers left < q={q}")
    elif not dissem:
        why.append(f"intersection {wi} < b+1={b+1}: the intersection can be "
                   f"all-Byzantine, no honest witness survives")
    elif not mask:
        why.append(f"intersection {wi} >= b+1={b+1} but < 2b+1={2*b+1}: "
                   f"only {c} honest server(s) in the worst intersection: dissemination "
                   f"works but b liars cannot be masked")
    print(f"  (n={n}, b={b}, q={q}): " + "; ".join(why))
```

```text
threshold quorum systems: exhaustive intersection audit
 n  b  q | min|Q1nQ2| | min correct | avail | dissem | mask | load | note
--------------------------------------------------------------------------------------------
 3  1  2 |          1 |           0 |  True |  False | False | 0.67 | crash-style majority (Paxos/Raft)
 4  1  3 |          2 |           1 |  True |   True | False | 0.75 | 2b+1 commit quorum of n=3b+1 (PBFT-style)
 4  1  4 |          4 |           3 | False |  False | False | 1.00 | write-all-4
 5  1  3 |          1 |           0 |  True |  False | False | 0.60 | byzantine quorum that is too small
 5  1  4 |          3 |           2 |  True |   True | True | 0.80 | tight masking system (n = 4b+1)
 7  2  5 |          3 |           1 |  True |   True | False | 0.71 | tight dissemination system (n = 3b+1)
 9  2  7 |          5 |           3 |  True |   True | True | 0.78 | tight masking system (n = 4b+1)

tight threshold families:
  b=1: dissem n=4, q=3: min|Q1nQ2|=2 (need >= 2), min correct=1, dissem=True, load=0.75
  b=1: mask   n=5, q=4: min|Q1nQ2|=3 (need >= 3), min correct=2, masking=True, load=0.80
  b=2: dissem n=7, q=5: min|Q1nQ2|=3 (need >= 3), min correct=1, dissem=True, load=0.71
  b=2: mask   n=9, q=7: min|Q1nQ2|=5 (need >= 5), min correct=3, masking=True, load=0.78
  b=3: dissem n=10, q=7: min|Q1nQ2|=4 (need >= 4), min correct=1, dissem=True, load=0.70
  b=3: mask   n=13, q=10: min|Q1nQ2|=7 (need >= 7), min correct=4, masking=True, load=0.77

near-misses (why 2f+1 / 3f+1 / 4f+1 are exact):
  (n=3, b=1, q=2): intersection 1 < b+1=2: the intersection can be all-Byzantine, no honest witness survives
  (n=4, b=1, q=3): intersection 2 >= b+1=2 but < 2b+1=3: only 1 honest server(s) in the worst intersection: dissemination works but b liars cannot be masked
  (n=8, b=2, q=5): intersection 2 < b+1=3: the intersection can be all-Byzantine, no honest witness survives
```

Note the third near-miss row: `(n=8, b=2, q=5)` is *almost* the dissemination
shape (2b+1=5 of 8) but with n one short of 3b+1=7... n=8 exceeds 7, so the
failure is the arithmetic: intersection `2q - n = 2 < b + 1 = 3`. Adding
servers without fixing q changes the intersection, not just redundancy - a
reminder that quorum tuning is a joint (n, q) decision, and the reason
"just add replicas" quietly breaks BFT guarantees in misconfigured
deployments.

## Interview probes

- State the two intersection conditions and derive the tight threshold
  families from `2q - n` alone.
- Why does a *disseminating* system not protect against a Byzantine reader,
  and which modification (pairing) repairs that, at what availability cost?
- PBFT commits with `2b+1` of `3b+1`: which of the two properties is its
  commit quorum satisfying, and what does it do about read-only operations?
- Given a static b and a required read-load bound, which non-threshold
  constructions exist, and what is the load floor for masking systems?

## References

1. Malkhi & Reiter, "Byzantine quorum systems", *Distributed Computing*
   11(4):203-213, 1998,
   [doi:10.1007/s004460050050](https://doi.org/10.1007/s004460050050) - the
   disseminating/masking definitions, constructions beyond thresholds, and
   the adaptive-adversary discussion.
2. Naor & Wool, "The load, capacity, and availability of quorum systems",
   *SIAM Journal on Computing* 27(2):423-447, 1998,
   [doi:10.1137/S0097539795281232](https://doi.org/10.1137/S0097539795281232)
   - the load metric used in the comparison table.
3. [PBFT (Castro & Liskov, OSDI 1999)](https://www.usenix.org/conference/osdi-99/practical-byzantine-fault-tolerance)
   - the `3b+1 / 2b+1` protocol shape these quorum conditions underwrite
   (usenix.org 403s direct probes from CI but the canonical page is
   search-verified live).
4. [Narwhal and Tusk paper (arXiv:2105.11827)](https://arxiv.org/abs/2105.11827)
   - modern DAG-BFT systems whose mempool certificates are exactly
   dissemination quorums; see also the companion page
   [Narwhal and Bullshark](../consensus/narwhal-bullshark.md).
5. Attiya & Welch, *Distributed Computing*, 2nd ed., Wiley 2004 - chapter 9
   for the shared-memory emulation lens on quorum read/write protocols.
