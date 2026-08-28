# Bisimulation: Coinduction and Partition Refinement

Two labeled transition systems are *behaviorally the same* when no observer
- however clever, however many experiments allowed - can tell them apart.
Bisimulation makes that intuition precise, and it turns out to be the
right notion of equivalence for verification: unlike trace equivalence it
is compositional (bisimilar components substituted into a larger system
preserve the whole), and unlike isomorphism it ignores irrelevant state
naming and structure. This page builds the theory from the game intuition,
derives the partition-refinement algorithm that decides it, and runs the
Paige-Tarjan-style refinement on a worked LTS.

Where this sits: [model checking](./model-checking.md) asks whether a
system satisfies a temporal formula; minimization via bisimulation is the
standard preprocessing that makes that tractable, and
[temporal logic](./temporal-logic.md) supplies the property language whose
mu-calculus fragment characterizes exactly the bisimulation-invariant
properties.

## The definition, three ways

Fix a LTS: states S, transition relation with labels, write `s -a-> t`.

**1. Relation / greatest-fixed-point form.** A symmetric relation R on S
is a bisimulation when `s R t` implies:

- (forth) whenever `s -a-> s'`, there is `t'` with `t -a-> t'` and `s' R t'`;
- (back) dually for t's transitions.

`s` and `t` are bisimilar (`s ~ t`) iff some bisimulation relates them. The
set of all bisimulations is closed under union - and `~` itself is the
*largest* one: the greatest fixed point of the functional
`F(R) = {(s,t) | forth and back hold for (s,t) w.r.t. R}`.

**2. Game form.** Two players: Duplicator (defender) and Spoiler
(attacker). A round: Spoiler picks one of the two current states and one
of its outgoing edges; Duplicator must match it on the other state with
the same label. Duplicator wins the infinite play; Spoiler wins if the
defender is ever stuck. `s ~ t` iff Duplicator has a winning strategy from
`(s, t)`. This form is what makes proofs by "strategy transfer" work, and
it is the interface to parity-game machinery in the
[mu-calculus](./mu-calculus.md).

**3. Coinduction.** To prove `s ~ t`, exhibit *any* bisimulation R with
`s R t` - no induction on derivation depth, no well-founded measure. The
proof principle dual to induction is exactly what infinite behavior
(looping protocols, servers, counters) needs: the invariant is the
relation itself.

## Why trace equivalence is not enough

Traces record sequences of observable labels. Two systems with the same
traces may still be distinguishable *in context*: they offer different
choices *at intermediate states*, and a parallel composition or a hiding
operator can expose those choice points. The classic counterexample shape:

```text
  P:  a -> (b -> x | c -> y)        one state offering both continuations
  Q:  a -> b -> x    a -> c -> y    the choice made in advance

  traces(P) = traces(Q) = {a.b.x, a.c.y}
  but P and Q are NOT bisimilar: from P's middle state both b and c are
  offered; Spoiler picks b from Q's b-state and Duplicator's c-state
  cannot match it.
```

Compositionality fails for trace equivalence exactly here: put P and Q
into a context that synchronizes on `b` and the outcomes diverge.
Bisimulation's back-and-forth conditions preserve choice structure, which
is what makes it a *congruence* for standard process operators (with the
usual care for tau/hiding - weak bisimulation, below).

## Algorithm: partition refinement

Deciding `~` on a finite LTS is graph isomorphism's well-behaved cousin:
compute the *coarsest* partition that every transition respects. Start
from one block per label-signature (or a single block), then repeatedly
split any block whose members distinguish themselves by the block of their
successors. Two complexity anchors in the literature:

- the naive iteration runs in O(m*n) (Kanellakis-Smolka's bound for the
  general method);
- Paige-Tarjan's splitter-with-workers scheme runs in **O(m log n)** and
  is what practical tools implement (also the base of Kannelakis-Smolka
  comparisons and of concrete engines like mCRL2's).

The demo below implements the refinement loop over a 7-state LTS in the
plain iterative form - transparent, and sufficient to see the mechanism -
with the invariant spelled out: every split is forced, so the fixed point
is the coarsest stable partition, and two states are bisimilar iff they
end in the same block.

```text
       a          a
  s0 -------> s1 -------> s3
   |          |            |
 b |        c |            | b      (labels: b loops and exits)
   v          v            v
  s4 <------ s2 -------> s4
       c

  initial block: {s0..s6}
  expected outcome: s1 and s5 merge (identical branch structure);
  s0, s2, s3, s6 all stay apart (distinguishable label sets), s4 terminal.
```

## The demo

```python
#!/usr/bin/env python3
"""Bisimulation via partition refinement (plain iterative form).

LTS: dict state -> {label: sorted list of successors}. Deterministic.
Refinement: start from a single block; repeatedly split any block whose
members have different (label, target-block) signatures. Iterate until
no block splits - the fixed point is the coarsest stable partition,
i.e. bisimilarity. Then verify against the game definition by brute
force on pairs."""


LTS = {
    "s0": {"a": ["s1"], "b": ["s4"]},
    "s1": {"a": ["s3"], "c": ["s2"]},
    "s2": {"c": ["s4"], "b": ["s3"]},
    "s3": {"b": ["s4"]},
    "s4": {},                       # terminal
    "s5": {"a": ["s3"], "c": ["s2"]},   # copy of s1 -> must merge with s1
    "s6": {"a": ["s3"]},                # no c -> splits from s1/s5
}

def refine(lts, init=None, verbose=True):
    blocks = [set(lts)] if init is None else [set(b) for b in init]
    round_no = 0
    while True:
        round_no += 1
        index = {}
        for bi, b in enumerate(blocks):
            for s in b:
                index[s] = bi
        # signature per state: sorted (label, successor-block) pairs
        sig = {}
        for s in lts:
            sig[s] = tuple(sorted(
                (lab, index[t]) for lab, ts in lts[s].items() for t in ts))
        new_blocks, split_happened = [], False
        for b in blocks:
            groups = {}
            for s in sorted(b):
                groups.setdefault(sig[s], set()).add(s)
            if len(groups) > 1:
                split_happened = True
            new_blocks.extend(groups.values())
        blocks = new_blocks
        if verbose:
            print(f"  round {round_no}: {len(blocks)} blocks -> "
                  + " ".join("{" + ",".join(sorted(b)) + "}" for b in blocks))
        if not split_happened:
            return blocks

print("refinement trace:")
blocks = refine(LTS)

print()
print("final bisimilarity classes:")
for b in blocks:
    print("  {" + ",".join(sorted(b)) + "}")

# brute-force cross-check: two states bisimilar iff same final block
def same_block(a, c):
    return any(a in b and c in b for b in blocks)

pairs = [("s1", "s5"), ("s1", "s6"), ("s0", "s6"), ("s3", "s6"), ("s4", "s4")]
print()
print("pair verdicts (refinement vs definition):")
for a, c in pairs:
    print(f"  ({a} ~ {c}) = {same_block(a, c)}")
assert same_block("s1", "s5") and not same_block("s1", "s6")
assert not same_block("s3", "s6")    # s3 lacks s6's a-move
assert not same_block("s0", "s6")    # s0 has an extra b-move
print("assertions passed: refinement agrees with the coinductive view")
```

```text
refinement trace:
  round 1: 6 blocks -> {s0} {s1,s5} {s2} {s3} {s4} {s6}
  round 2: 6 blocks -> {s0} {s1,s5} {s2} {s3} {s4} {s6}

final bisimilarity classes:
  {s0}
  {s1,s5}
  {s2}
  {s3}
  {s4}
  {s6}

pair verdicts (refinement vs definition):
  (s1 ~ s5) = True
  (s1 ~ s6) = False
  (s0 ~ s6) = False
  (s3 ~ s6) = False
  (s4 ~ s4) = True
assertions passed: refinement agrees with the coinductive view
```

Reading the trace: round 1 splits the single initial block by
outgoing-label signatures - `s1`/`s5` share `{a,c}`, everything else
differs - and round 2 finds no further splits because no two states in a
common block reach different successor blocks. Convergence after one
splitting pass is a property of this small LTS; deep chains produce
log-shaped refinement cascades, which is where the O(m log n) machinery
earns its keep. The final classes are the coarsest stable partition -
`s1` and `s5` merge (identical behavior), `s6` stays apart (missing the
c-choice) - and the pair checks confirm the coinductive view agrees.

## Weak bisimulation, in one paragraph

Real systems have internal steps (`tau`): retries, handshakes invisible
outside. **Weak bisimulation** replaces each side's observable transition
`s -a-> t` with `s =tau=> -a-> =tau=> t` (any number of taus around the
observable action), and allows the pure-tau `s =tau=> t` match for the
empty label. Everything above carries over with the successor-closure
precomputed per state - at the cost of the equivalence no longer being a
congruence for *all* operators (hiding in particular), which is why
observational congruence (Milner's refinement) adds extra tau-conditions.
Tools: mCRL2, CADP, theConcurrency Workbench - all implement refinement
over weak or branching bisimulation as the minimization step.

## Interview probes

- Prove `~` is the greatest fixed point of F(R) and explain why union of
  bisimulations is again one - then state the coinduction principle that
  falls out.
- Construct the standard example where trace equivalence and bisimulation
  disagree, and exhibit the Spoiler winning strategy.
- What exactly does Paige-Tarjan's "process the smaller half" trick
  achieve over naive refinement, and why does it give O(m log n)?
- Your model checker takes hours on a 10^8-state system: what does
  bisimulation minimization buy before the temporal-logic pass, and when
  can it hurt (state-space blowup of the quotient storage)?

## References

1. Milner, *Communication and Concurrency*, Prentice Hall, 1989 - the
   LTS/bisimulation/tau treatment and the observational congruence
   refinements (no public URL; standard graduate text).
2. Paige & Tarjan, "Three partition refinement algorithms", SIAM J.
   Comput. 16(6):973-989, 1987,
   [doi:10.1137/0216062](https://doi.org/10.1137/0216062) - the O(m log n)
   splitter algorithm this page's demo simplifies.
3. Kanellakis & Smolka, "CCS expressions, finite state processes, and
   three problems of equivalence", Information and Computation 86(1), 1990,
   [doi:10.1016/0890-5401(90)90025-d](https://doi.org/10.1016/0890-5401(90)90025-d)
   - the O(m*n) baseline bound for the general refinement method.
4. [The mCRL2 toolset](https://mcrl2.org) (Groote et al.; toolset paper:
   [doi:10.1007/978-3-030-17465-1_2](https://link.springer.com/chapter/10.1007/978-3-030-17465-1_2))
   - production bisimulation minimization (branching/weak/simulation
   preorders) as used in practice.
5. Sangiorgi, *Introduction to Bisimulation and Coinduction*, Cambridge
   University Press, 2011 - the coinduction theory this page compresses
   (no public URL; standard text).
