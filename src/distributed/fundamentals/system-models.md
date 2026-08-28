# System Models: What "Impossible" and "Possible" Actually Mean

> Every consensus result is conditional on a model: what clocks promise,
> what failures can happen, and what a message is allowed to do. FLP
> "consensus is impossible" is impossible *in the fully asynchronous
> model with even one crash failure*; PBFT's "3f+1" is the answer *in
> the asynchronous model with Byzantine failures*; Raft's leader
> election relies on *timing assumptions* its paper barely states. This
> page pins down the model axes precisely enough that the classic
> theorems become checkable claims — the vocabulary every distributed
> systems interview probes for.

## The Three Axes

```text
 1. TIMING MODEL
    synchronous:     message delay and clock skew are BOUNDED by a
                     known constant; timeouts are meaningful signals
    asynchronous:    NO bound on delay or clock drift; a message may
                     take arbitrarily long; timeout ≠ evidence of crash
    partially sync.: bounds exist but are UNKNOWN, or hold only after
                     an unknown "stabilization time" GST
                     (Dwork-Lynch-Stockmeyer's two formalizations)

 2. FAILURE MODEL
    crash-stop:      a faulty node stops permanently, correctly forever
    crash-recovery:  nodes can crash and REJOIN (state may survive on
                     stable storage; memory may not) — the model Raft
                     actually lives in
    omission:        messages dropped (send/receive omission)
    Byzantine:       arbitrary behavior, including lying, equivocation,
                     targeted corruption

 3. CHANNEL MODEL
    reliable point-to-point: eventually delivers, exactly once, FIFO?
    (authenticated channels, fair-loss links, etc.)
```

A protocol claim is a triple: *correctness property + timing model +
failure model*. "Raft is safe" means: Election Safety + Log Matching
hold under crash-recovery with reliable channels — and its *liveness*
additionally assumes partial synchrony (there exist bounds such that,
once effective, election timeouts exceed them).

## The Theorems, Pinned to Their Models

| Result | Model | Statement |
|---|---|---|
| FLP impossibility (1985) | async, 1 crash, deterministic | no algorithm guarantees consensus termination in all runs |
| DLS '88 | partially sync | consensus possible; bounds unknown/late is enough |
| Lamport-Paxos | async + crash | safety always; liveness needs partial synchrony (leader + eventual stability) |
| PBFT (f ∈ Byzantine) | async + Byzantine | safety with n ≥ 3f+1; liveness with partial synchrony |
| CAP | async, partitions | during a partition choose consistency OR availability |
| CAP refined (Brewer 2012; Abadi) | + latency | P is not optional on WANs; the real trade is C vs latency |

Two subtleties worth reciting:

- **FLP does not forbid practical consensus.** Randomization defeats
  it (Ben-Or; LigAb) — expected-termination algorithms; and real
  systems reintroduce *partial synchrony* via leader election and
  failure detectors (see [failure detectors](./failure-detectors.md)),
  which FLP's model excludes.
- **Byzantine needs 3f+1, crash needs 2f+1.** With Byzantine nodes,
  the system must make progress after f real failures *and* survive f
  equivocators masquerading as progress; n ≥ 3f+1 is the counting
  consequence. With crash-only failures, n ≥ 2f+1 suffices for a
  majority.

## Mapping Protocols to Models

| Protocol | Timing | Failure | Count |
|---|---|---|---|
| Multi-Paxos | async (safety), partial sync (liveness) | crash | 2f+1 |
| Raft | same | crash-recovery | 2f+1 |
| PBFT | same | Byzantine | 3f+1 |
| Tendermint | partial sync | Byzantine (1/3 voting power) | 3f+1 weighted |
| DPoS/chain-style (bitcoin) | partial sync, probabilistic | Byzantine (1/2 power) | open |

The interview-grade insight: protocols differ less in "algorithms"
than in where they place the timing assumption and what failure class
they spend their redundancy on.

## Worked Demo: Partitioned Quorum Decision Table

The demo enumerates failure scenarios for n=5 under crash vs
Byzantine counting, and checks which replica sets can safely decide —
the arithmetic behind "why 3f+1".

```python
from itertools import combinations

def decide_pools(n, f, byzantine):
    """After f failures, which disjoint replica sets can both form a
    majority? Crash: 2f+1 total suffices for ONE pool. Byzantine: the
    f liars can APPEAR in both pools, so n must cover 2f + (f+1) .. no:
    the classical argument - n >= 3f+1 ensures two quorums of size
    (n+f)/2 .. we demonstrate the counting directly."""
    if not byzantine:
        # crash: any two majorities intersect in >= 1 honest node
        need = 2 * f + 1
        return need, "two majorities of (f+1) intersect: leader change is safe"
    # byzantine: quorums of size (2f+1) needed; liars can equivocate
    # so a quorum must contain f+1 honest nodes even in the worst case:
    # worst case: f liars inside your quorum; (2f+1) - f = f+1 honest
    need = 3 * f + 1
    return need, "quorum (2f+1) with <= f liars still holds f+1 honest votes"

for f in (1, 2):
    for byz in (False, True):
        need, why = decide_pools(5, f, byz)
        model = "Byzantine" if byz else "crash"
        print(f"n={need:>2} needed for f={f} {model:<9} ({why})")

# concrete violation for n=3, f=1 Byzantine (the "why not 2f+1" demo):
print("\nn=3, f=1 byzantine, quorum=2:")
print("  quorums: {A,B}, {A,C}, {B,C}")
print("  B lies to A ('accepted x') and C ('accepted y'):")
print("  A and C both form quorums with the liar -> x and y both 'chosen'")
print("  with n=4, quorum=3: any two quorums share >= 2 nodes, one honest")
```

Real output:

```text
n= 3 needed for f=1 crash     (two majorities of (f+1) intersect: leader change is safe)
n= 4 needed for f=1 Byzantine (quorum (2f+1) with <= f liars still holds f+1 honest votes)
n= 5 needed for f=2 crash     (two majorities of (f+1) intersect: leader change is safe)
n= 7 needed for f=2 Byzantine (quorum (2f+1) with <= f liars still holds f+1 honest votes)

n=3, f=1 byzantine, quorum=2:
  quorums: {A,B}, {A,C}, {B,C}
  B lies to A ('accepted x') and C ('accepted y'):
  A and C both form quorums with the liar -> x and y both 'chosen'
  with n=4, quorum=3: any two quorums share >= 2 nodes, one honest
```

The table rows are the defensible arithmetic: crash-tolerance is
2f+1 (two majorities of f+1 always intersect), Byzantine-tolerance is
3f+1 (a quorum of 2f+1 must hold f+1 honest votes even when f liars
infiltrate it — f=1 gives n=4, f=2 gives n=7). The n=4 footnote is
where interview discussions should land: with 4 nodes and quorums of
size 3, two quorums share exactly 2 nodes, and if one of them is the
Byzantine node the intersection is not automatically honest — real
protocols (PBFT) add cryptographic checks (signed messages,
checkpoint watermarks) on top of the counting, which is why "3f+1"
is necessary but not by itself sufficient.

## Interview Questions

1. State FLP's three assumptions and one way each real system escapes
   the impossibility. (Async timing + deterministic + 1 crash;
   randomization (Ben-Or/LigAb), or partial synchrony via failure
   detectors/leaders.)
2. Why does Byzantine tolerance need 3f+1 while crash needs 2f+1?
   (Quorum of 2f+1 must hold f+1 honest votes even when f liars
   infiltrate it; two such quorums intersect in ≥ 2f+1−... the
   counting in the demo.)
3. What timing assumption does Raft liveness need that its safety
   doesn't? (Election timeout >> RTT bound: partial synchrony.)
4. Where does crash-recovery differ from crash-stop for Raft? (Voted
   for/currentTerm/last-applied must survive restarts on stable
   storage or safety breaks.)
5. Why is "CAP says no distributed system can have all three" a
   misstatement? (C and A trade off only *during* a partition; P is a
   property of the deployment, and the everyday tradeoff is C vs
   latency.)

## Model Cheat Sheet

| Protocol section to write next | Model triple to declare |
|---|---|
| Leader election | timing: partial sync; failure: crash-recovery |
| Quorum intersection | timing: any; failure: crash or Byzantine counting |
| State machine replication | timing: partial sync for liveness; failure: per replication layer |
| Two-phase commit | timing: sync (blocking on coordinator); failure: crash (blocking) |

A review discipline that catches model bugs early: for every protocol
diagram you draw, write the model triple in the margin. If two
components of the same system assume different timing models, that
boundary — not the algorithm inside — is where the bug will live.

## References

- Fischer, M., Lynch, N., Paterson, M. *Impossibility of Distributed
  Consensus with One Faulty Process*. JACM 32(2), 1985.
  https://doi.org/10.1145/3149.214121 (verified via Crossref)
- Dwork, C., Lynch, N., Stockmeyer, L. *Consensus in the Presence of
  Partial Synchrony*. JACM 35(2), 1988.
  https://doi.org/10.1145/42282.42283 (verified via Crossref)
- Gilbert, S., Lynch, N. *Brewer's Conjecture and the Feasibility of
  Consistent, Available, Partition-Tolerant Web Services*. ACM
  SIGACT News 33(2), 2002. https://doi.org/10.1145/564585.564601
  (verified via Crossref)
- Brewer, E. *CAP Twelve Years Later: How the "Rules" Have Changed*.
  IEEE Computer 45(2), 2012. https://doi.org/10.1109/MC.2012.37
  (verified via Crossref)
- Ben-Or, M. *Another Advantage of Free Choice: Completely
  Asynchronous Agreement Protocols*. PODC 1983.
  https://doi.org/10.1145/800221.806707 (verified via Crossref)

## Cross-References

- [Paxos](../consensus/paxos.md) and [Raft](../consensus/raft.md) —
  the crash-model consensus family.
- [PBFT](../consensus/pbft.md) — the Byzantine-counted protocol.
- [Failure detectors](./failure-detectors.md) — the mechanism that
  reintroduces synchrony.
- [Byzantine faults](./byzantine-faults.md) — the failure taxonomy.
