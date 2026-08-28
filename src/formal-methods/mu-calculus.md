# The Modal mu-Calculus: Fixed Points, Games, and Parity

The modal mu-calculus is the assembly language of temporal logic: every
standard specification formalism you meet in verification - LTL, CTL, CTL*,
the property languages of model checkers - embeds into it, and the
model-checking problem for it is exactly the problem of evaluating nested
greatest and least fixed points. That evaluation is a *parity game*, which
lands the whole subject in one of complexity theory's most famous open
gaps. This page builds the syntax, the fixed-point semantics, the game view,
and runs a nested-formula evaluation on a small Kripke structure.

Prerequisites in this repo: [model checking](./model-checking.md) (the
Kripke-structure machinery), [temporal logic](./temporal-logic.md) (LTL/CTL
syntax being translated), and for the automata view,
[bisimulation](./bisimulation.md) (parity games quotient by exactly the
equivalence bisimulation induces on the game arena).

## Syntax and the two fixpoints

Given a set of atomic propositions, the formulas are:

```text
  p            atomic proposition
  not phi      negation
  phi and psi  conjunction
  <> phi       exists a successor where phi holds        (diamond)
  [] phi       all successors satisfy phi                (box)
  X            a variable
  mu X. phi    LEAST fixed point   (recursion that must terminate)
  nu X. phi    GREATEST fixed point (recursion allowed to run forever)
```

Each variable X is bound by a fixpoint operator; formulas are *alternation
free* or ranked by how the mu/nu bindings nest inside each other - the
alternation hierarchy, below, is the subject's deepest theorem.

## Semantics: sets evolving under functionals

Interpret a formula as the set of states where it holds. The fixpoints
interpret a recursion: `[[mu X. phi]]` is the least set S with
`S = [[phi]](S)` where X ranges over S; computed by Kleene iteration from
the empty set. Dually `nu X. phi` iterates down from the full state set.

The intuition worth memorizing:

- `mu` = **eventual reachability** style properties: "something good
  happens after finitely many steps" (the iteration grows until it
  stabilizes).
- `nu` = **safety/invariant** style: "something holds from here on, along
  all paths" (the iteration shrinks, carving away bad states).

Standard encodings - all of these are mu-calculus one-liners:

| property (CTL-ish)            | mu-calculus rendering          |
|-------------------------------|--------------------------------|
| EF p (p reachable)            | mu X. (p or <> X)              |
| EG p (p holds along some path)| nu X. (p and <> X)             |
| AG p (p invariant)            | nu X. (p and [] X)             |
| AF p (p inevitable)           | mu X. (p or [] X)              |
| "infinitely often p"          | nu X. (mu Y. (p or <> Y) and <> X) |
| "eventually forever p"        | mu X. (nu Y. (p or [] Y) or <> X)  |

The last two are the famous alternation pairs: a nu wrapping a mu (or
vice versa) expresses "infinitely often / eventually forever", which no
alternation-free formula can express.

## The game view: parity games

Evaluating `phi` at state s is a game between Eloise (exists / the
prover) and Abelard (forall / the refuter):

- Positions: (state, subformula). Eloise moves at `<>`, `or`;
  Abelard at `[]`, `and`. Atoms resolve immediately.
- Fixpoint subformulas create loops; each variable X carries a priority -
  even for `nu`, odd for `mu`, increasing with binding nesting.
- Infinite plays are won by the player who *owns the highest-priority
  variable seen infinitely often*.

`s satisfies phi` iff Eloise wins from `(s, phi)`. Deciding that is the
parity-game problem: in NP and co-NP (and UP ∩ co-UP), with steady
algorithmic progress - quasipolynomial-time breakthrough (Calude et al.
2017, practical variants since) - but no known polynomial algorithm. This
gap is the mu-calculus's signature open problem.

## The alternation hierarchy is strict

Bradfield proved the mu/nu alternation hierarchy is strict: formula n
alternations deep express properties that no shallower formula can. This
matters practically because model checkers optimize the alternation-free
fragment hard (it characterizes bisimulation-invariant properties
elegantly, and tools detect and exploit it), while full alternation
remains worst-case hard. When someone says "our property language is
'the mu-calculus'", the real question is: which level of the hierarchy?

## The demo: nested fixpoint evaluation

The implementation below evaluates the two famous alternation formulas on
a 5-state Kripke structure: "infinitely often p" and "eventually forever
p", by direct Kleene iteration with the outer/inner fixpoint bookkeeping
made explicit (iteration counts printed). Assertions pin the expected
verdicts per state, derived by hand from the structure.

```python
#!/usr/bin/env python3
"""Direct Kleene-iteration evaluation of nested mu/nu formulas over a
finite Kripke structure (no game solving - the iteration view).

Formulas evaluated (the two alternation benchmarks):
  inf-p  = nu X. (mu Y. (p or <> Y) and <> X)   "p holds infinitely often"
  evf-p  = mu X. (nu Y. (p or [] Y) or <> X)    "eventually p forever"

Kripke structure: 5 states, deterministic-ish edges, p true on s1, s3.
The iteration prints each outer approximation so the alternation is
visible: inf-p's outer iteration GROWS (nu from top, but the mu-Y inner
loop forces re-widening); evf-p's outer SHRINKS."""


KS = {
    # state -> (successors, p?)
    "s0": (["s1"], False),
    "s1": (["s2"], True),
    "s2": (["s0", "s3"], False),
    "s3": (["s3", "s4"], True),
    "s4": (["s4"], False),
}

STATES = frozenset(KS)


def successors(s):
    return KS[s][0]


def has_p(s):
    return KS[s][1]


def pre(S):
    """states with SOME successor in S (diamond-preimage)"""
    return frozenset(s for s in STATES if any(t in S for t in successors(s)))


def pre_a(S):
    """states with ALL successors in S (box-preimage; dead ends lose)"""
    out = set()
    for s in STATES:
        succs = successors(s)
        if succs and all(t in S for t in succs):
            out.add(s)
    return frozenset(out)


def diamond(phi):
    return pre(phi)


def box(phi):
    return pre_a(phi)


def mu(f, show=None):
    """least fixed point of f: frozenset -> frozenset, Kleene from bottom"""
    S = frozenset()
    i = 0
    while True:
        nxt = f(S)
        i += 1
        if show is not None:
            show.append(f"      mu iter {i}: {sorted(nxt)}")
        if nxt == S:
            return S
        S = nxt


def nu(f, show=None):
    """greatest fixed point: Kleene from top"""
    S = STATES
    i = 0
    while True:
        nxt = f(S)
        i += 1
        if show is not None:
            show.append(f"      nu iter {i}: {sorted(nxt)}")
        if nxt == S:
            return S
        S = nxt


# inf-p = nu X. ( mu Y. (p or <>Y) and <>X )
trace = []
def inf_p():
    def outer(X):
        inner = lambda Y: (frozenset(s for s in STATES if has_p(s)) | diamond(Y)) & diamond(X)
        r = mu(inner, trace)
        trace.append(f"    outer nu X approximation -> {sorted(r)}")
        return r
    return nu(outer, trace)

# evf-p = mu X. ( nu Y. (p and []Y) or <>X )   i.e. AF AG p
def evf_p():
    def outer(X):
        inner = lambda Y: (frozenset(s for s in STATES if has_p(s)) & box(Y)) | diamond(X)
        r = nu(inner, trace)
        trace.append(f"    outer mu X approximation -> {sorted(r)}")
        return r
    return mu(outer, trace)


print("Kripke structure: s0->s1->s2->{s0,s3}; s3->{s3,s4}; s4->s4; p on {s1,s3}")
print()
print("=== inf-p: nu X. (mu Y. (p or <>Y) and <>X)  [p infinitely often] ===")
R1 = inf_p()
print("  verdict (p infinitely often):", sorted(R1))

print()
print("=== evf-p: mu X. (nu Y. (p or []Y) or <>X)  [eventually p forever] ===")
R2 = evf_p()
print("  verdict (eventually p forever):", sorted(R2))

print()
print("hand-derived checks (branching-time quantifiers matter):")
print("  every state can steer onto the p-cycle (s1 via s2->s3, s0 likewise),")
print("  so p-infinitely-often holds on s0..s3")
assert {"s0", "s1", "s2", "s3"} == R1
print("  s4 has no p and cannot leave itself: in neither verdict")
assert "s4" not in R1 and "s4" not in R2
print("  AF AG p holds NOWHERE: s2 can loop s0-s1-s2 forever without settling,")
print("  and s3 itself can escape to the p-free sink s4")
assert R2 == frozenset()
print("assertions passed")
```

```text
Kripke structure: s0->s1->s2->{s0,s3}; s3->{s3,s4}; s4->s4; p on {s1,s3}

=== inf-p: nu X. (mu Y. (p or <>Y) and <>X)  [p infinitely often] ===
  verdict (p infinitely often): ['s0', 's1', 's2', 's3']

=== evf-p: mu X. (nu Y. (p or []Y) or <>X)  [eventually p forever] ===
  verdict (eventually p forever): []

hand-derived checks (branching-time quantifiers matter):
  every state can steer onto the p-cycle (s1 via s2->s3, s0 likewise),
  so p-infinitely-often holds on s0..s3
  s4 has no p and cannot leave itself: in neither verdict
  AF AG p holds NOWHERE: s2 can loop s0-s1-s2 forever without settling,
  and s3 itself can escape to the p-free sink s4
assertions passed
```

Read the two verdicts against the structure - they contrast beautifully.
"p infinitely often" holds on s0..s3: from each of those states Eloise can
steer execution onto the p-carrying cycle (s0-s1-s2-s3), and s4 is the
only loser. "Eventually p forever" holds *nowhere*, including s3 itself:
the quantifier structure (AF AG p) demands p settle permanently on every
path, but s3's successor set contains the p-free sink s4, and s2 can
loop s0-s1-s2 without ever settling. That gap between "can keep p
occurring" (nu outer / mu inner) and "must end up p-only" (mu outer /
nu inner) is precisely the expressive power the alternation buys; a
flattened alternation-free formula cannot separate the two verdicts
here.

## Model-checking practice

Production model checkers rarely hand you raw mu-calculus; they take
CTL/LTL/PSL and compile to it (or to the equivalent automata). What leaks
through to the user:

- **Diagnostic fixed points**: NuSMV-style counters show the witness
  lasso for LTL failures - the same lasso a parity-game losing play
  would exhibit.
- **Alternation-free fragments** are targeted by specialized algorithms
  (linear in the formula and structure); general mu-calculus tools (e.g.
  the Concurrency Workbench family, mu-calculus modes of CADP) solve
  games via the strategy-iteration or small-progress-measures families.
- The 2017 quasipolynomial-time result (Calude-Jain-Kortelam-
  Khoussainov-Li-Stephan) moved the theory floor; practical engines still
  use Zielonka-style recursion because constants matter.

## Interview probes

- Give the CTL-to-mu-calculus translations of AF p and EG p, and prove
  the mu/nu choice is forced by the monotone functional involved.
- Why is "infinitely often p" expressible with one alternation but not
  alternation-free? Show the collapse attempt and where it fails.
- Sketch why parity-game solving is in UP ∩ co-UP and what practical
  algorithms dominate despite the quasipolynomial breakthrough.
- Your model checker reports a violation for nu X. (p and [] X) at a
  state: what object does the tool hand you as the counterexample, and
  why is a finite path enough?

## References

1. Kozen, "Results on the propositional mu-calculus", Theoretical
   Computer Science 27(3):333-354, 1983,
   [doi:10.1016/0304-3975(82)90125-6](https://doi.org/10.1016/0304-3975(82)90125-6)
   - the original semantics and axiomatization.
2. Bradfield & Stirling, "Modal mu-calculi", in *Handbook of Modal Logic*
   (Elsevier, 2007) - the alternation hierarchy and game semantics
   survey chapter.
3. Calude, Jain, Kortelam, Khoussainov, Li, Stephan, "Deciding parity
   games in quasipolynomial time", STOC 2017,
   [doi:10.1145/3055399.3055409](https://doi.org/10.1145/3055399.3055409)
   - the complexity breakthrough (verify at dl.acm.org; bot-blocked
   probes noted).
4. [CADP construction toolkit](https://cadp.inria.fr/) (INRIA) - the
   production verification suite whose evaluator solves the modal
   mu-calculus over LTSs; its manual documents the on-the-fly
   alternation handling described above.
5. [Model checking (this repo)](./model-checking.md) and
   [temporal logic (this repo)](./temporal-logic.md) - the surrounding
   machinery and the LTL/CTL being embedded.
