# Abstract Interpretation

Executing a program on all possible inputs is impossible; executing it on one input tells you nothing about the others. Abstract interpretation (Cousot & Cousot, POPL 1977) resolves this by running the program **simultaneously on all inputs, but with a lossy arithmetic**: real numbers become signs or intervals, sets of states become single abstract states, and program semantics becomes a monotone function whose least fixpoint is computed on a finite (or controlled) structure. The result is the only kind of guarantee static analysis can honestly give: *if the analysis says the property holds, it holds on every real execution* - soundness by construction - while anything the analysis cannot prove is reported as a potential alarm.

The theory explains and unifies essentially every flow-sensitive compiler analysis (constant propagation, live variables, range analysis) and underlies certified industrial analyzers such as Astree. This page builds the theory from concrete to abstract, shows why naive iteration diverges, and runs a real interval-domain interpreter that survives the divergence via widening and narrowing.

## Concrete semantics is a fixpoint equation

Take a small imperative language. The concrete collecting semantics maps each program point to the **set of environments** (variable -> value) reachable there. Assignment is a function on sets, branch joins are union, and a loop `while c do s` at entry `X0` satisfies:

```text
        X  =  X0  U  body(X)          least fixpoint: lfp(body U entry)
   iteration: X1 = X0 U body(X0), X2 = X0 U body(X1), ...
```

The least fixpoint is exactly what we want ("every state ever seen at the loop head"), and Kleene iteration from the empty set converges to it - but only in the limit: the chain may be strictly increasing forever. Everything interesting in static analysis follows from one question: *how do we compute (an over-approximation of) this fixpoint in finite time over a structure we can represent?*

## Galois connections: the contract between two worlds

An abstraction is a pair of monotone maps between the concrete lattice `C` (e.g., sets of environments, ordered by inclusion) and an abstract lattice `A` (e.g., intervals, ordered componentwise), tied together by an adjunction:

```text
          alpha                          gamma
   concrete C  -----------------> abstract A  -----------------> concrete C
   (sets)         best abstraction  (intervals)   concretization

   soundness contract:   alpha(c) <= a   iff   c <= gamma(a)
   equivalence:          gamma(alpha(c)) >= c   for every concrete c
```

`alpha` (abstraction) sends a set of values to its tightest interval; `gamma` (concretization) says which concrete values an abstract value stands for. The Galois contract makes `alpha(S)` the **best** abstraction of `S` - no precision is lost by the choice of representation, only by the domain itself. Once abstraction functions `F#` on `A` satisfy `alpha . F <= F# . alpha` (or simply `gamma(F#(x#)) >= F(gamma(x#))`, the concretization-only form most practical analyzers use), Tarski/Kleene give:

```text
   lfp(F)  <=  gamma(lfp(F#))
```

i.e., computing the fixpoint of the *abstract* transfer functions and concretizing yields a sound over-approximation of the concrete one. Soundness is no longer a per-analysis argument; it is inherited from the domain and the transfer functions.

## Sign analysis: the smallest useful domain

Abstract values need a lattice. For signs it is tiny, and transfer functions are defined by truth tables (e.g., `pos + pos = pos`, `pos + neg = any`, `pos * neg = neg`):

```text
                 any (top)
                /    |    \
             neg   zero   pos
                \    |    /
              bottom (no state)
```

Division by zero checking becomes: is `zero` impossible in the denominator's abstract value? Sign analysis proves it cheaply, but cannot prove `x in [1, 1000]`. Choosing the domain *is* choosing the price/precision curve.

## Intervals, and why naive iteration diverges

The interval domain abstracts each variable to `[lo, hi]` (bounds may be infinite; the empty interval is bottom). Joins are componentwise min/max, transfer functions compute bound arithmetic, e.g. `[a,b] + [c,d] = [a+c, b+d]` and `x*x = [min(lo*lo,hi*hi), max(lo*lo,hi*hi)]` with care for sign crossings.

The catch is loops. Analyze:

```c
i = 0;
while (i < n) { i = i + 1; }     // n unknown, n in [5, 10]
```

Each chaotic-iteration round joins one more body pass into the loop head: `[0,0]`, `[0,1]`, `[0,2]`, ... The interval lattice has **infinite height**, so the ascending chain never stabilizes - the analyzer literally cannot terminate. This is not an implementation bug; it is the price of the domain. The fix is a pair of operators with special properties:

- **Widening** `x # y`: an operator that, given an ascending sequence, forces it to jump to a finite number of steps - e.g., keep stable bounds, replace every grown bound with `+inf`/`-inf`. Any fixpoint computed with widening still over-approximates `lfp` (it only *adds* states), so soundness survives; precision may not.
- **Narrowing** `x . y`: applied after stabilization, it takes a few *decreasing* steps (`meet` with one more transfer pass) to claw precision back - e.g., refining `[0, +inf)` against the loop condition gives `[0, 9]` inside the body and `[5, 10]` after exit.
- Practical refinements: **threshold widening** (grow bounds only to a finite set of interesting constants instead of infinity), **widening delay** (iterate exactly a few times before widening first), and widening points placed at loop heads only.

## A runnable interval-domain interpreter

The interpreter below covers assignment, sequence, and `while` over the interval domain, with three modes: naive chaotic iteration, widening, and guard-aware narrowing. It is self-contained; run it with `python3`:

```python
NEG, POS = float("-inf"), float("inf")

def add(a, b): return (a[0] + b[0], a[1] + b[1])
def sub(a, b): return (a[0] - b[1], a[1] - b[0])

def evl(e, st):
    if e[0] == "num": return (float(e[1]), float(e[1]))
    if e[0] == "var": return st[e[1]]
    a, b = evl(e[1], st), evl(e[2], st)
    return {"add": add, "sub": sub}[e[0]](a, b)

def join(a, b):
    return {v: (min(a[v][0], b[v][0]), max(a[v][1], b[v][1])) for v in a}

def meet(a, b):
    r = {}
    for v in a:
        lo, hi = max(a[v][0], b[v][0]), min(a[v][1], b[v][1])
        if lo > hi: return None
        r[v] = (lo, hi)
    return r

def widen(o, n):
    return {v: (o[v][0] if n[v][0] >= o[v][0] else NEG,
                o[v][1] if n[v][1] <= o[v][1] else POS) for v in o}

def refine(st, cond, positive):
    x, y = cond[1][1], cond[2][1]
    s = dict(st)
    if positive:
        s[x] = (s[x][0], min(s[x][1], s[y][1] - 1))
        s[y] = (max(s[y][0], s[x][0] + 1), s[y][1])
    else:
        s[x] = (max(s[x][0], s[y][0]), s[x][1])
        s[y] = (s[y][0], min(s[y][1], s[x][1]))
    for v in s:
        if s[v][0] > s[v][1]: return None
    return s

def run(stmt, st, mode, head=None):
    t = stmt[0]
    if t == "assign":
        r = dict(st); r[stmt[1]] = evl(stmt[2], st); return r
    if t == "seq":
        return run(stmt[2], run(stmt[1], st, mode), mode)
    # t == "while": return (head state, exit state, rounds, converged?)
    entry = st
    head = entry if head is None else head
    traj, rounds = [], 0
    while True:
        rounds += 1
        inn = refine(head, stmt[1], True) if mode == "narrow" else head
        out = run(stmt[2], inn, mode) if inn else None
        new = join(entry, out) if out else entry
        if new == head:
            exit_st = refine(head, stmt[1], False)
            return head, exit_st, traj, rounds, True
        if mode == "narrow":              # narrowing: descend only
            new = meet(head, new)
            if new is None or rounds > 64:
                exit_st = refine(head, stmt[1], False)
                return head, exit_st, traj, rounds, False
            head = new
        elif mode == "naive":             # plain chaotic iteration (diverges)
            traj.append(fmt(head))
            if rounds > 10000:
                exit_st = refine(head, stmt[1], False)
                return head, exit_st, traj, rounds, False
            head = new
        else:                             # widening: jump, never creep
            if rounds > 10000:
                exit_st = refine(head, stmt[1], False)
                return head, exit_st, traj, rounds, False
            head = widen(head, new)

def fmt(st):
    out = []
    for v in sorted(st):
        lo, hi = st[v]
        lo = ("-inf" if lo == NEG else str(int(lo)))
        hi = ("+inf" if hi == POS else str(int(hi)))
        out.append("%s=[%s, %s]" % (v, lo, hi))
    return " ".join(out)

# i = 0; while (i < n) { i = i + 1; }
loop = ("while", ("lt", ("var", "i"), ("var", "n")),
        ("assign", "i", ("add", ("var", "i"), ("num", 1))))
env = {"i": (0.0, 0.0), "n": (5.0, 10.0)}

print("program: i = 0; while (i < n) { i = i + 1; }   n in [5, 10]")
h1, _, tr, k1, _ = run(loop, env, "naive")
print("naive:  no fixpoint after %d rounds, head %s and climbing" % (k1, fmt(h1)))
print("        trajectory:", " ".join(tr[:4]), "...")
h2, _, _, k2, _ = run(loop, env, "widen")
print("widen:  fixpoint after %d rounds, head %s" % (k2, fmt(h2)))
h3, ex3, _, k3, _ = run(loop, env, "narrow", head=h2)
print("narrow: stabilized after %d more rounds, head %s, exit %s"
      % (k3, fmt(h3), fmt(ex3)))
```

Real output:

```text
program: i = 0; while (i < n) { i = i + 1; }   n in [5, 10]
naive:  no fixpoint after 10001 rounds, head i=[0, 10000] n=[5, 10] and climbing
        trajectory: i=[0, 0] n=[5, 10] i=[0, 1] n=[5, 10] i=[0, 2] n=[5, 10] i=[0, 3] n=[5, 10] ...
widen:  fixpoint after 2 rounds, head i=[0, +inf] n=[5, 10]
narrow: stabilized after 2 more rounds, head i=[0, 10] n=[5, 10], exit i=[5, 10] n=[5, 10]
```

Read the three phases as the whole story of the field: naive iteration provably never terminates on this 3-line loop; widening terminates in 2 rounds but the invariant `i <= 10` is flooded to `+inf`; narrowing plus guard refinement (`i < n` in the body, `i >= n` on the exit edge) recovers `i in [0, 10]` at the head and - the payoff - proves *after the loop* that `5 <= i <= 10`, i.e., the loop ran at least 5 and at most 10 times. That last fact is an unbounded-inputs theorem derived from about 40 lines of arithmetic.

## Soundness vs precision

Soundness says: every concrete execution is described by the final abstract state (`gamma(F#*) >= concrete`). It is absolute and cheap to keep - widen as brutally as you like. Precision says: the description is tight enough to be useful. Every engineering decision in a real analyzer (widening thresholds, delay, domain selection, partitioning of paths, trace partitioning by loop iteration counters) buys precision while paying compile time. False alarms are precisely the sound residue the domain could not squeeze out; a *missing* alarm is a soundness bug (wrong transfer function, unsound widening, mishandled aliasing or NaNs) and is the only fatal defect class.

## Relational domains: paying to remember variable interactions

Intervals are **non-relational**: they join `x in [0,10]`, `y in [0,10]` at a branch to `[0,10]x[0,10]`, forgetting `x == y`. Relational domains track constraints across variables:

| Domain | Form of invariant | Cost per join/transfer | Typical use |
| --- | --- | --- | --- |
| Intervals | `lo <= x <= hi` per variable | O(n) | Ranges, array bounds |
| Octagons | `+-x +- y <= c` (pairwise) | O(n^3) closure, O(n^2) memory | Pointer diffs, loop bounds |
| Polyhedra | general linear inequalities `sum(a_i x_i) <= c` | worst-case exponential | Max precision, small n |
| Congruences / ellipses | `x = a mod k`, quadratic forms | medium | Alignment, crypto code |

Octagons (Mine) close a constraint graph with a Floyd-Warshall-style shortest-path pass, so `x <= y + c` automatically implies `x - z <= c + (y - z)`; polyhedra (Cousot & Halbwachs, POPL'78) are exact for linear invariants but join explodes convexity. Industrial analyzers are *product* analyzers: intervals for speed, octagons for relational invariants, plus special-purpose domains (bit vectors, NULLness, unpacked structs) glued at each program point.

## Where it sits relative to dataflow and model checking

Classic dataflow analysis (Kildall's monotone framework, liveness, available expressions) is abstract interpretation with the lattice and transfer functions as the analysis definition - abstract interpretation supplies the *semantic justification* (why is the meet-over-all-paths solution approximated soundly?) and the machinery (Galois connections, widening) that dataflow texts handle by ad-hoc safety arguments. Model checking works in the opposite direction: it explores the exact state space of a (usually finite) transition system, proving or disproving a temporal property with counterexamples; abstract interpretation over-approximates and never produces counterexamples. Predicate abstraction + CEGAR (SLAM, BLAST) interpolates: abstract-interpretation-style fixpoints over predicates, model checking the induced finite automaton, refining predicates from spurious counterexamples. A modern cousin is the eBPF verifier, which is essentially a per-instruction abstract interpreter over register value abstractions (see `linux/kernel/tracing/ebpf-verifier.md`).

## Industrial tools

- **Astree** (Cousot, Cousot, Feret, Mauborgne, Mine, Monniaux, Rival; now AbsInt): domain-product analyzer for embedded C; famously proved absence of runtime errors on Airbus flight-control code (over 100k lines) with no false alarms after iterative domain refinement; qualifiable under DO-178C.
- **Polyspace** (MathWorks): abstract-interpretation-based Prover/Checker for C/C++, same family of numeric domains, focused on MISRA-style verification.
- **MOPSA** (LIP6/Inria): open modular analyzer framework where each property gets its own abstract domain and analyses cooperate through domain product.
- **Frama-C/Eva**: value-analysis plugin in the Frama-C framework, intervals + eva domains, widely used for safety-critical C.

## Interview lens

- *Why can't the analyzer just iterate until stable?* Interval lattice has infinite height; the chain `[0,k]` never stabilizes. Termination requires widening (or a finite-height domain, which costs precision).
- *Widening loses `i <= 10`; how do industrial tools get it back?* Narrowing passes, threshold widening at constants appearing in guards, and trace partitioning by the iteration counter - all still sound because they only refine between sound over-approximations.
- *Why is ECC-style "the analysis missed it" different from a false alarm?* A false alarm is sound imprecision (safe); a missed bug is unsoundness - a broken transfer function or abstraction, and it invalidates the certification argument entirely.

## References

- Cousot & Cousot, "Abstract Interpretation: A Unified Lattice Model for Static Analysis of Programs by Construction or Approximation of Fixpoints", POPL 1977 - <https://dl.acm.org/doi/10.1145/512950.512973>
- MIT 16.399 "Abstract Interpretation" (P. Cousot's full course notes and slides) - <https://web.mit.edu/16.399/www>
- D. Monniaux, "Completeness in Static Analysis by Abstract Interpretation" (practitioner's view of precision) - <https://arxiv.org/abs/2211.09572>
- Astree product page (AbsInt), incl. DO-178C qualification material - <https://www.absint.com/astree/>
- MOPSA analyzer project page - <https://mopsa.lip6.fr>
