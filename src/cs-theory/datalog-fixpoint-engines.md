# Datalog and Fixpoint Engines -- Recursion as Least-Model Computation

> Related: [Logic](./logic.md), [Sets, Relations & Functions](./sets-relations-functions.md), [Computability](./computability.md), [Query Optimizers](../dbms/advanced/query-optimizers.md), [Network Verification](../networks/advanced/network-verification.md)

## Why a query language needs a fixpoint

SQL answers acyclic questions well. Ask "is node A connected to node B?" or
"which variables may point to the same heap cell?" and no fixed join order
suffices: the answer needs a relation defined in terms of itself, iterated
until it stops growing. That limit is a **fixpoint**, and Datalog's execution
model is exactly "evaluate rules to the fixpoint of their consequence
operator" -- the same engine shape runs static analysis (Souffle), network
checking (Batfish), and incremental streams (Materialize).

## The language: Horn clauses, no function symbols

A Datalog program is a finite set of **Horn clauses**: disjunctions with at
most one positive literal, written as rules.

```text
rule    H :- B1, ..., Bn.      head H holds whenever all body atoms hold
fact    F.                     a rule with empty body (n = 0)
EDB     extensional relations: given facts, like base tables
IDB     intensional relations: defined by rules -- and allowed to recurse
safe    every variable in the head occurs in some positive body atom
```

Safety (range restriction) guarantees every derived tuple is built from
constants in the EDB, so the universe of possible tuples is finite. Two
bookkeeping properties follow:

- **No function symbols.** Terms are variables or constants only (unlike
  Prolog), so the Herbrand base -- all ground atoms -- is finite and every
  strategy terminates. With function symbols you get a Turing-complete
  language: undecidability, not useful expressiveness
  ([Computability](./computability.md)).
- **Positivity.** Body atoms are all positive; negation and aggregates break
  monotonicity unless tamed (below).

## Least-model semantics via Knaster-Tarski

For a program P define the **immediate consequence operator** on sets of
ground facts: `T_P(I) = I union { H | some ground instance H :- B1,...,Bn of
a rule has every Bi in I }`. T_P is **monotone** (I <= J implies T_P(I) <=
T_P(J)): more premises never retract conclusions. Ground facts form a
complete lattice, so **Knaster-Tarski** applies: a monotone operator on a
complete lattice has a least fixpoint, equal to the intersection of all
pre-fixpoints. Van Emden and Kowalski (1976) showed this is the **least
Herbrand model** -- the minimal set of facts making P true:

```text
   P(HB): power set of the Herbrand base, subset order
   top:    { all ground atoms }      over-approximation
      |  \                           T_P climbs from bottom and
      |   \                          cannot overshoot the least model:
   lfp -+-> least Herbrand model     iteration is add-only (inflationary)
   bottom:  { }                      = union of T_P^i(empty), starts here
```

T_P is also **continuous** and the lattice finite: iteration from the empty
set stabilizes after finitely many rounds, so termination is a theorem.

## Bottom-up evaluation: naive, then semi-naive

The direct implementation is **naive evaluation**: repeatedly evaluate
*every* rule over the *full* database, add new tuples, stop when a round
adds nothing. Correct by construction; wasteful, since every round
re-derives every tuple already known.

**Semi-naive evaluation** (Bancilhon, 1986) notes that a derivation using
only old facts was found in an earlier round. Keep a **delta relation**
`d_tc` of tuples newly added to `tc` in the previous round; rewrite each
recursive rule to require at least one delta premise:

```text
tc(X,Y) :- d_tc(X,Z), tc(Z,Y).       new source side joins full target side
tc(X,Y) :- tc_old(X,Z), d_tc(Z,Y).   full minus delta joins new target side
```

The `tc_old` split (full relation minus delta) prevents double-counting
derivations with two new premises. Round 0 evaluates the non-recursive rules
once; later rounds join deltas against full relations; termination is the
first empty delta. The demo below measures the savings.

## Top-down evaluation: SLD resolution and the magic-set bridge

Prolog evaluates Horn clauses **top-down**: SLD resolution picks a body
literal, unifies it with clause heads, recurses into subgoals, backtracks.
On pure Datalog SLD is complete and terminating -- a finite Herbrand base
yields finitely many subgoals up to renaming -- but it re-solves identical
subgoals exponentially often without **tabling** (memoized answers, XSB
style). The asymmetries:

| Dimension | Bottom-up (fixpoint) | Top-down (SLD + tabling) |
|-----------|----------------------|--------------------------|
| Work driven by | Whole database | Query / demand |
| Termination | Theorem (finite HB) | Fair selection + tabling |
| Repeated subgoals | Never (set semantics) | Tabling prevents them |
| Incremental updates | Natural (delta relations) | Awkward |
| Unification/indexing | Join + index selection | Term unification |

**Magic-set rewriting** gets the best of both: synthetic `magic` predicates
encode the query's bindings, so a bottom-up engine computes only
demand-relevant tuples -- a top-down strategy compiled into bottom-up
machinery. Souffle ships it; `WITH RECURSIVE` engines use cousins.

## Stratified negation and stratified aggregates

Add `p(X) :- edge(X,Y), not q(X,Y)` with q recursive and T_P stops being
monotone: facts can *retract* conclusions, the iteration can oscillate, and
`p :- not p` has no consistent model. **Stratification** partitions IDB
predicates into strata where negation may reference only *lower* strata;
within a stratum, positivity restores monotonicity, so Knaster-Tarski
applies per layer:

```text
stratum 2:  win(X) :- move(X,Y), not win(Y).    negation looks DOWN
            (strata 0-1 reach fixpoint first, then derive winners once)
stratum 1:  reachable(X,Y) :- edge(X,Y).
            reachable(X,Y) :- reachable(X,Z), edge(Z,Y).
stratum 0:  edge facts (EDB)
```

Stratifiable programs have a unique model independent of the chosen
stratification, computed one fixpoint per stratum; the **well-founded
semantics** handles the rest with a third truth value. Aggregates hit the
same wall: `count` and `sum` over non-negative values are monotone and can
run inside the fixpoint, but `min`, `max`, and `avg` are not -- a smaller
newly derived minimum invalidates the earlier "final" aggregate. Engines
force aggregates into a **higher stratum** than what they consume (Souffle
rejects lower-stratum aggregates at compile time): finish the inner
fixpoint, then aggregate once. Hence "Dijkstra inside a Datalog rule" is not
free, and cost-weighted reachability systems (Batfish) widen the language.

## Joins are index selection

Strip the logic and each rule body is a conjunctive query; semi-naive makes
it a two-input join of a delta against a full relation. The performance
question is **which physical index serves each join**: `d_tc(X,Z)` joined
with `tc(Z,Y)` needs tc indexed on Z; `tc(X,Z)` joined with `d_tc(Z,Y)` needs
the delta indexed on Z. Souffle keeps multiple index layouts per relation and
picks one per (rule, binding pattern), with automatic index selection
available. For rules joining three-plus relations, worst-case optimal joins
(leapfrog triejoin) replace pairwise plans -- see
[Query Optimizers](../dbms/advanced/query-optimizers.md), whose LogicBlox row
is a Datalog engine with an LFTJ join kernel.

## Souffle: compiling Datalog to parallel C++

Souffle (souffle-lang.github.io) is the workhorse open-source Datalog engine
for static analysis. Its distinctive move is **synthesis** -- compiling the
program instead of interpreting it, via successive Futamura projections, so
runtime work is hoisted into compile time:

```text
.dl program + facts
  |  parse, semantic checks (safety, stratification)
  v
AST / IR -- transforms --> magic-set rewriting, component specialization
  v
relational algebra machine (semi-naive fixpoint as abstract machine;
  |                         IDB = static program, EDB = its input)
  v
templatized C++ --> g++ / clang --> native parallel executable
                    (-j N threads; no persistent DB storage)
```

The docs frame it precisely: semi-naive evaluation plays the interpreter's
role; specialization projects the interpretation away. Souffle also runs as
an interpreter for fast turnaround, and ships provenance output,
auto-tuning, and a C++ embedding interface.

## Where fixpoint engines run in production

- **Pointer analysis.** Andersen's inclusion-based analysis is a textbook
  Datalog program: base facts for `p = &q`, plus copy and load/store rules --
  load/store makes derivation recursive (aliasing creates copy edges, which
  create more aliases). Doop (Smaragdakis/Bravenboer) expressed families of
  context-sensitive analyses as Datalog variants; bddbddb (Lam et al.)
  packed relations into BDDs to exploit fixpoint sharing. Interview pitch:
  thousands of lines of imperative analysis collapse into statable rules.
- **Taint tracking.** Sources, sinks, and propagators are facts; propagation
  through assignments and aliasing has the same recursive shape as pointer
  analysis, so taint rides the same engine in one more stratum.
- **Network verification.** Batfish encoded routing-protocol semantics (OSPF,
  BGP route selection) in LogiQL, a Datalog dialect on LogicBlox, and derives
  the data plane as that program's fixpoint; properties are then queries over
  the result. History and detail: [Network
  Verification](../networks/advanced/network-verification.md) -- same
  fixpoint engine, different domain.
- **Incremental streams.** Differential dataflow (McSherry et al., CIDR 2013)
  models collections as change streams over partially ordered timestamps and
  evaluates operators incrementally: a delta in, an output delta out,
  recursively through joins and reduces -- semi-naive generalized from
  linear rounds to arbitrary dataflow times. Naiad supplied the
  timely-dataflow runtime; Materialize builds streaming SQL on top (see
  [Temporal & Streaming Databases](../dbms/advanced/temporal-streaming.md)),
  and [McSherry's write-up](https://github.com/frankmcsherry/blog/blob/master/posts/2015-09-14.md)
  gives the author's intuition.

## Worked demo: counting derived-tuple work

The program is transitive closure (r1: `tc(X,Y) :- edge(X,Y)`;
r2: `tc(X,Y) :- tc(X,Z), tc(Z,Y)`) over a 60-node graph with hop-1/2/3
edges: 174 facts, 1770 reachable pairs -- dense, so redundant re-derivation
is the enemy. Work counts every rule-join candidate, even known pairs:

```python
from collections import defaultdict

def succ(rel):
    s = defaultdict(list)
    for (z, y) in rel: s[z].append(y)
    return s

def naive_closure(edges):
    tc, work, rounds = set(edges), 0, 0
    while True:
        rounds += 1
        nxt, cand = succ(tc), set()
        work += len(edges)                    # r1 re-run over full EDB
        for (x, z) in tc:                     # r2: tc(x,z) AND tc(z,y)
            for y in nxt[z]:
                work += 1; cand.add((x, y))
        new = cand - tc
        if not new: return tc, work, rounds
        tc |= new

def seminaive_closure(edges):
    tc, work, rounds, d = set(edges), len(edges), 1, set(edges)
    while d:
        rounds += 1
        old = tc - d                          # split avoids (d,d) twice
        cand = set()
        for src, tgt in [(d, succ(tc)), (old, succ(d))]:
            for (x, z) in src:                # d(x,z) AND tc(z,y) / old AND d
                for y in tgt[z]:
                    work += 1; cand.add((x, y))
        new = cand - tc
        tc, d = tc | new, new
    return tc, work, rounds

n = 60
edges = {(i, i + k) for i in range(n) for k in (1, 2, 3) if i + k < n}
tc_n, w_n, r_n = naive_closure(edges)
tc_s, w_s, r_s = seminaive_closure(edges)
print("Graph: %d nodes, %d edges, %d reachable pairs (|tc|)" % (n, len(edges), len(tc_n)))
print("Naive bottom-up:      %2d rounds, %6d rule-join candidates" % (r_n, w_n))
print("Semi-naive bottom-up: %2d rounds, %6d rule-join candidates" % (r_s, w_s))
print("Candidate-tuple work saved: %.1f%%" % (100.0 * (1 - w_s / float(w_n))))
print("Same least fixpoint: %s" % (tc_n == tc_s))
```

Real output (Python 3, run August 2026):

```text
Graph: 60 nodes, 174 edges, 1770 reachable pairs (|tc|)
Naive bottom-up:       6 rounds,  98384 rule-join candidates
Semi-naive bottom-up:  7 rounds,  34394 rule-join candidates
Candidate-tuple work saved: 65.0%
Same least fixpoint: True
```

Both engines compute the identical least model (last line) in a comparable
number of iterations (the delta loop runs one extra round to discover the
empty delta). The gap is the work column: naive re-joins all ~34k composable
pairs of the full 1770-tuple relation every round; semi-naive joins only
tuples new last round -- a 65% re-derivation tax on this dense closure.

## Interview angles

| Question | What the interviewer is fishing for |
|----------|-------------------------------------|
| Why does Datalog terminate but Prolog loop? | No function symbols => finite Herbrand base; the bottom-up fixpoint is inflationary. Prolog's function symbols grow terms forever. |
| What does stratified negation buy? | Restores monotonicity per stratum, so Knaster-Tarski least-model semantics survives `not`; unique model for stratifiable programs. |
| Naive vs semi-naive in one sentence? | Delta relations restrict derivations to those using at least one new fact -- same fixpoint, far fewer candidate tuples. |
| Bottom-up vs top-down trade-off? | Demand-driven vs supply-driven; magic sets compile the first into the second; tabling fixes SLD's repeated subgoals. |
| Where have you touched Datalog without knowing? | Souffle pointer/taint analysis, Batfish control-plane verification, Materialize/differential dataflow, SQL `WITH RECURSIVE`. |

## References

1. Souffle project, "Souffle: A Datalog Synthesis Tool for Static Analysis" -- documentation, including the Synthesis page on the Datalog-to-C++ pipeline: <https://souffle-lang.github.io/> and <https://souffle-lang.github.io/translate> (accessed August 2026)
2. S. Abiteboul, R. Hull, V. Vianu, *Foundations of Databases*, Addison-Wesley, 1995 -- the Datalog chapters (12-15) cover Horn-clause semantics, evaluation strategies, and stratified negation; full book freely available from the authors: <http://webdam.inria.fr/Alice/> (accessed August 2026)
3. F. McSherry, D. Murray, R. Isaacs, M. Isard, "Differential Dataflow," CIDR 2013: <https://www.cidrdb.org/cidr2013/Papers/CIDR13_Paper13.pdf> (accessed August 2026)
4. D. G. Murray et al., "Naiad: A Timely Dataflow System," SOSP 2013, DOI [10.1145/2517349.2522738](https://doi.org/10.1145/2517349.2522738) (DOI verified via Crossref, August 2026)
5. A. Fogel et al., "A General Approach to Network Configuration Analysis," NSDI 2015 (Batfish): <https://www.usenix.org/conference/nsdi15/technical-sessions/presentation/fogel> (accessed August 2026)
