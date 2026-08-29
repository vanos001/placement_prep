# Alloy: Relational Models Bounded by SAT

Alloy, developed by Daniel Jackson's group at MIT, is a lightweight modeling language built on first-order **relational logic** extended with transitive closure. A model is a handful of declarations plus first-order constraints, and analysis is fully automatic: every formula is translated by the **Kodkod** engine into a Boolean satisfiability (SAT) problem over a **bounded universe**. Where TLA+ (see [TLA+](./tla-plus.md)) asks what a system may *do over time*, classic Alloy asks a structural question: is there a small instance in which my data model violates this invariant? That framing made Alloy the go-to tool for data models, metamodels, access-control policies, and API design exploration, and its SAT backbone is the same technology covered in [SAT and SMT Solvers](./sat-smt-solvers.md).

Three ideas carry this whole page:

1. **Everything is a relation.** Sets are relations of arity 1; fields are relations of arity 2 and up; joins and transitive closure do the work that code would otherwise do.
2. **Analysis is bounded search.** The Analyzer never proves an unbounded theorem. It looks for a counterexample inside a scope and reports either a concrete instance or "no counterexample up to this scope."
3. **Counterexamples are the product.** A failing `check` hands you a rendered instance you can inspect; a passing `check` means much less than a proof, which is the subject of its own section below.

## Everything Is a Relation

An Alloy model declares `sig`s (sets of indivisible atoms) and fields (relations whose first column comes from the sig). There is no class hierarchy, no code, no state machine: just structure and constraints. The relational operators, all ASCII, do the heavy lifting:

| Operator | Reads as | Meaning for relations r, s |
|----------|----------|----------------------------|
| `r + s` | union | set of tuples in either |
| `r & s` | intersection | tuples in both |
| `r - s` | difference | tuples in r not in s |
| `r -> s` | product | all pairs (a, b) with a in r, b in s |
| `x.r` | join | relational image: r-successors of x |
| `~r` | transpose | every tuple reversed |
| `^r` | closure | one or more r-steps (transitive closure) |
| `*r` | closure | zero or more r-steps (reflexive-transitive) |
| `no / some / lone / one r` | multiplicity | r empty / nonempty / at most one tuple / exactly one |

Transitive closure is the notable addition over plain first-order logic: `n.^parent` means "all proper ancestors of n," and it is what lets you state acyclicity and reachability in one line. Quantifiers range over atoms, keeping the logic decidable under a finite scope; the few supported higher-order idioms (existentially quantified sets) are Skolemized before solving. Alloy 5 and earlier had no built-in notion of time at all - a model describes one snapshot, and if you wanted traces you encoded sequences by hand. Alloy 6 changes that (see below).

## The Analyzer Pipeline: Model to CNF to Instance

```text
        model.als
            |  parse + type check
            v
   relational formula
            |                      bounds: for each sig, a set of
            v                      candidate atoms (the scope);
   Kodkod translation              integer bitwidth; atom names
            |
            v
   CNF + symmetry-breaking predicates
            |
            v
     SAT solver (CDCL) ---------> SAT:   instance (rendered by the visualizer)
            |                     UNSAT: no counterexample within the scope
            v
   unsat-core extraction (optional, for debugging over-constraints)
```

Kodkod (Torlak and Jackson, TACAS 2007) is the engine inside the Analyzer. It takes the relational formula plus per-sig *bounds*, encodes atoms as SAT variables and relation tuples as bit-matrix variables, and adds **symmetry-breaking predicates** so that isomorphic permutations of atoms are not re-explored. Because the whole problem lands in propositional logic, the Analyzer inherits CDCL performance and, crucially, produces *models* (witness instances), not just yes/no answers. This is a different tradeoff from the explicit-state enumeration described in [Model Checking](./model-checking.md): SAT-based bounded analysis explores a combinatorial space of *structures*, not a reachable state space.

The **scope** is the knob that makes this finite. `check P for 5` gives every top-level sig up to 5 atoms; you can override per sig (`for 5 but exactly 1 Root`), and `for 5 but exactly 2 A` forces an exact count. The scope is also the honest boundary of every claim the tool makes.

## sig, fact, pred, assert, check: A File-System Model

The canonical Alloy example is a file system, and it is worth walking through in full because it exercises every construct:

```text
sig Node { parent: lone Node, entries: set Node }
one sig Root extends Node {}

fact RootNoParent { no Root.parent }
fact Coherent     { parent = ~entries }        // parent mirrors containment
fact Acyclic      { all n: Node | n not in n.^parent }

assert NoOrphans { all n: Node - Root | some n.parent }
check NoOrphans for 3
```

| Construct | Role |
|-----------|------|
| `sig` | declares a set of atoms; its body declares fields (relations) |
| `one sig ... extends` | singleton subsig; here Root exists in every instance |
| `fact` | a constraint assumed true of every instance - an axiom, not a claim |
| `pred` | a named, parameterized constraint, reusable by commands |
| `assert` | a claimed consequence of the facts, submitted for testing |
| `check` | command: search the scope for an instance that violates an assert |
| `run` | command: search for any instance satisfying a pred (a sanity check) |

`check NoOrphans for 3` returns a counterexample, not an error: a two-node file system where neither node has a parent and `entries` is empty. Nothing in the facts forbids it - `Acyclic` and `RootNoParent` are satisfied vacuously by a degenerate forest. The standard fix is to promote the invariant into a fact:

```text
fact Reachable { all n: Node - Root | Root in n.^parent }
```

With `lone Node` and acyclicity, "every non-root node has some parent" and "Root reaches every node" are equivalent: every parent chain terminates (finite, acyclic, at most one parent per node), and only Root is allowed to be parentless. The mini analyzer below reproduces both the failure and the fix, including the exact instance the Analyzer would render.

## What "Checked at Scope 3" Does and Does Not Mean

This is the part practitioners get wrong most often, so it deserves precision:

- **A counterexample is a theorem.** If the Analyzer hands you an instance, that instance really satisfies all facts and really violates the assertion. This direction is unconditional.
- **A pass is bounded.** UNSAT at scope 3 says nothing about scopes 4, 5, and beyond, because scope is not monotone. Example: "some node has two distinct children" is unsatisfiable at scope 2 but satisfiable at scope 3 - a check that passed at 2 would fail at 3. Passing is evidence, not proof.
- **The small scope hypothesis is doing the work.** Jackson's empirical claim, argued throughout *Software Abstractions*, is that design flaws that matter typically manifest in tiny instances. That claim is a heuristic, and a well-supported one, but it is the load-bearing assumption of the entire method.
- **Guard against vacuity.** An over-constrained model - too many facts - can pass every `check` because no instance satisfies it at all. Before trusting a pass, `run` a predicate you expect to be satisfiable and confirm the model is non-empty.
- **Unbounded claims need other machinery.** Proving an invariant for all scopes requires induction or fixed-point arguments; [the mu-calculus](./mu-calculus.md) is the standard framework, and SAT-based k-induction and interpolation (covered in [SAT and SMT Solvers](./sat-smt-solvers.md)) are the practical bridge.

## Alloy 6: Temporal Logic and Lasso Traces

Alloy 6 is the major release that brought time into the language, integrating the design pioneered by the **Electrum** analyzer (Brunel, Chemouil, Cunha, and Macedo, ASE 2018). Concretely, the release notes define these additions:

- **Mutable signatures and fields.** The `var` keyword marks state that changes over time; anything without `var` is static and constant across a trace. The value of an expression in the next state is written `e'`.
- **Linear temporal operators.** `always`, `eventually`, `after`, `before`, `historically`, `once`, `until`, and `releases`; the docs note that `after` and `until` alone can define all the future-time connectives.
- **Instances are traces.** An instance is an infinite sequence of states, represented as a **lasso trace**: a finite prefix whose last state loops back to an earlier state. Since the last state may loop to itself, the representation is fully general for finite-state systems.
- **A time horizon in the scope.** Analyses bound the number of transitions explored; `for 10 steps` is equivalent to `for 1..10 steps`, and if no step count is given the default is 10. An open-ended horizon (`m.. steps`) requires SMT-based solving and is expensive.

```text
sig User {}
var sig Token { var holder: lone User }

assert TokensRecycled { always (all t: Token | eventually no t.holder) }
check TokensRecycled for 10 steps
```

One subtlety worth memorizing: a formula in a fact, assert, or command is interpreted at the *initial state* of the trace, so past-time connectives are only useful inside the scope of a future-time one (`always (... historically ...)`), and `before` is always false in the first state. Models that use no `var` constructs keep exactly the old static semantics, so Alloy 6 is backward compatible by construction.

## Picking Between Alloy, TLA+, and Model Checkers

| Aspect | Alloy | TLA+ / TLC | Explicit-state model checking |
|--------|-------|------------|-------------------------------|
| Native subject | structure of a single state | behavior: states and actions | transition system over time |
| Engine | Kodkod -> SAT (bounded) | explicit-state enumeration | enumerative or BDD-based checkers |
| Time in language | none pre-6; lasso traces in 6 | native temporal logic | CTL / LTL semantics |
| Counterexample form | a rendered instance | a behavior (trace) | a witness / trace |
| A passing result means | no counterexample up to the scope | no violation in explored states | property holds for the given model |
| Sweet spot | data models, config, policies | distributed protocols | hardware, protocol state machines |

Practical guidance: reach for Alloy when the bug class is *structural* - an invariant over data that some small configuration breaks - and when a counterexample *instance* is more useful than a counterexample *trace*. Reach for TLA+ (again, [TLA+](./tla-plus.md)) when interleaving, message reordering, and failure semantics are the story, since TLA+'s action semantics handle those natively. The gap narrows at small scale: Alloy 6's temporal layer makes short behavioral models entirely practical, and teams often use both - Alloy to sanity-check the data model, TLA+ to check the protocol around it.

## The Analyzer's Search, Reproduced by Hand

The script below is the pipeline of the previous sections with the SAT solver replaced by brute force, for a scope of 3 atoms. It enumerates every universe subset (Kodkod's sig bounds), every `parent` valuation satisfying `lone Node`, and every `entries` valuation; filters candidates through the four facts; and then tests the assertion - exactly what the Analyzer does, except Kodkod compiles the enumeration into CNF and lets CDCL prune instead of visiting every candidate.

```python
from itertools import combinations, product

POOL = ["N0", "N1", "N2"]   # candidate atoms; N0 plays Root
ROOT = "N0"

def ancestors(p, start):
    """Proper ancestors of start under p (the ^parent closure)."""
    seen, frontier = set(), [start]
    while frontier:
        q = p.get(frontier.pop())
        if q is not None and q not in seen:
            seen.add(q)
            frontier.append(q)
    return seen

def run_check(label, no_orphans_fact, assertion):
    explored = instances = counterexamples = 0
    first = None
    for k in range(len(POOL) + 1):
        for U in map(set, combinations(POOL, k)):        # sig bounds: any subset
            nodes = sorted(U)
            for par in product([None] + nodes, repeat=len(nodes)):
                p = dict(zip(nodes, par))                # parent: lone Node
                for bits in range(1 << len(nodes) ** 2):
                    pairs = [(a, b) for a in nodes for b in nodes]
                    ent = {pairs[i] for i in range(len(pairs))
                           if (bits >> i) & 1}           # entries: Node -> Node
                    explored += 1
                    if ROOT not in U or p.get(ROOT) is not None:
                        continue                         # Root exists, no parent
                    if any((p.get(b) == a) != ((a, b) in ent)
                           for a in nodes for b in nodes):
                        continue                         # parent = ~entries
                    if any(n in ancestors(p, n) for n in nodes):
                        continue                         # acyclic ^parent
                    if no_orphans_fact and any(n != ROOT and p.get(n) is None
                                               for n in nodes):
                        continue                         # promoted orphan fact
                    instances += 1
                    if not assertion(nodes, p):
                        counterexamples += 1
                        if first is None:
                            first = (nodes, p, ent)
    print(f"{label}")
    print(f"  candidate models explored : {explored}")
    print(f"  models satisfying facts   : {instances}")
    print(f"  counterexamples found     : {counterexamples}")
    if first is None:
        print("  result                    : no counterexample within scope 3")
    else:
        nodes, p, ent = first
        ptxt = ", ".join(f"{n}->{p.get(n)}" for n in nodes)
        print(f"  first counterexample      : Node = {nodes}")
        print(f"                              parent = {{{ptxt}}}")
        print(f"                              entries = {ent or '{}'}")
    print()

run_check("check 1: assert NoOrphans (every non-root node has a parent)",
          False, lambda ns, p: all(p.get(n) is not None for n in ns if n != ROOT))

run_check("check 2: NoOrphans promoted to fact, re-check reachability from Root",
          True, lambda ns, p: all(ROOT in ancestors(p, n) for n in ns if n != ROOT))
```

Running it prints:

```text
check 1: assert NoOrphans (every non-root node has a parent)
  candidate models explored : 33213
  models satisfying facts   : 13
  counterexamples found     : 7
  first counterexample      : Node = ['N0', 'N1']
                              parent = {N0->None, N1->None}
                              entries = {}

check 2: NoOrphans promoted to fact, re-check reachability from Root
  candidate models explored : 33213
  models satisfying facts   : 6
  counterexamples found     : 0
  result                    : no counterexample within scope 3
```

Reading the numbers like the Analyzer would: of 33,213 candidate models at scope 3, only 13 satisfy all four facts; 7 of those violate `NoOrphans`, and the first counterexample is precisely the two-node degenerate forest from the section above. Check 2 promotes the invariant into a fact, shrinking the instance space from 13 to 6; reachability then holds in every remaining instance, so the check reports no counterexample - meaning *nothing at scope 3*, per the caveats section. The 2.5x shrinkage also shows how facts, not assertions, define the universe you are really analyzing.

## Field Notes

- **Tune scopes surgically.** The candidate space grows combinatorially with each sig's scope; raise the scope on the sig implicated in a failure and keep the others small.
- **Watch integer overflow.** Alloy's integer arithmetic is bitwidth-bounded, so counts silently wrap in bitwidth-bounded models; set the bitwidth deliberately when a spec counts things.
- **Symmetry is not free luck.** The symmetry-breaking predicates Kodkod adds are sound, but declaring atoms as subsigs (`extends`) rather than flag fields lets the tool exploit symmetry better.
- **Model smell: fat facts.** If a `check` passes, try negating the assertion into a `run`-able predicate, or strip facts; an unsatisfiable model is a check that proves nothing.

## References

- Alloy project home and Alloy 6 release notes (temporal operators, lasso traces, time-horizon scopes). https://alloytools.org/ and https://alloytools.org/alloy6.html
- Alloy language reference (Alloy 6). https://alloy.readthedocs.io/
- Daniel Jackson. *Software Abstractions: Logic, Language, and Analysis*, revised edition, MIT Press (announced as published November 2011 on the project book page; the publisher's page returns 403 to scripted requests but is the canonical listing). https://alloytools.org/book.html
- Daniel Jackson, MIT CSAIL, project and publication pages. https://people.csail.mit.edu/dnj/
- Alloy analyzer source repository and releases (download page lists 6.2.0 as the latest release). https://github.com/AlloyTools/org.alloytools.alloy
- Emina Torlak and Daniel Jackson. *Kodkod: A Relational Model Finder*. TACAS 2007. https://doi.org/10.1007/978-3-540-71209-1_49
- Julien Brunel, David Chemouil, Alcino Cunha, and Nuno Macedo. *The Electrum Analyzer: Model Checking Relational First-Order Temporal Specifications*. ASE 2018. https://doi.org/10.1145/3238147.3240475
- Daniel Jackson. *Alloy: A Lightweight Object Modelling Notation*. ACM TOSEM 11(2), 2002. https://doi.org/10.1145/505145.505149
- *Practical Alloy*, an online book covering Alloy 6 temporal modeling in tutorial form. https://practicalalloy.github.io/
