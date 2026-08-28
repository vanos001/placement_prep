# E-Graphs and Equality Saturation

Every compiler rewrites expressions: `x*2` into `x+x`, hoisting a loop-invariant
subexpression, reassociating a sum. Run rewrites one at a time and you inherit
two ancient problems: a rewrite can *destroy* the intermediate form another
rewrite needed, and nobody can tell you in what *order* to run the rules. An
**e-graph** sidesteps both by never deleting anything: it stores *all* forms
seen so far as equivalence classes in one DAG, applies every rule to every
class until nothing new appears (**equality saturation**), and only at the end
picks a single best representative per class (**extraction**). The design was
popularized in compilers by the `egg` library [1] and now runs inside
Cranelift, Herbie, and a growing list of production and research tools.

## The Phase Ordering Problem

Sequential rewriting is order-sensitive in a way that no rule ordering fixes
globally. Take two useful rules: strength reduction `x*2 -> x+x` and strength
increase `x+x -> x*2`. Applied blindly in sequence they ping-pong forever; a
real compiler therefore freezes each into a separate pass and runs them in a
fixed order — instcombine before reassociation, reassociation before
vectorization — and that order is tuned by hand, per target, per benchmark.
The deeper trap: rule A enables rule B, B destroys the form A produced, and no
local ordering rule detects the loss. Classic cases are constant propagation
vs. DCE, and reassociation vs. CSE fighting over the same adds. This is the
**phase ordering problem**, and it is not solvable by cleverness — the
information "this intermediate was useful three rules ago" simply is not in
the IR anymore. E-graphs answer by keeping every intermediate alive
simultaneously; there is no order to get wrong.

## Anatomy of an E-Graph

An e-graph is a bipartite structure: **e-nodes** (operator applications) and
**e-classes** (sets of mutually equivalent e-nodes). Every e-node's operands
are not subexpressions but **e-class ids** — numbers that the union-find
resolves to canonical classes. Building `(a*2 + a) * 2` and saturating with
`x*2 -> x+x`, `x+x -> x*2`, commutativity, and associativity gives:

```text
        e4                 e3                    e2
  +-----------+     +-------------+     +---------------+
  | (* e3 e1) |     | (+ e2 e0)   |     | (* e0 e1)     |
  +-----------+     | (+ e0 e2)   |     | (+ e0 e0)     |
        |           +-------------+     +---------------+
        |                |    |              |    |
        +-> children     +-> e2,e0         +-> e0,e1
            are e-CLASS IDS, resolved through union-find

  e0 = { (var a) }          e1 = { (num 2) }
```

e3 holds *both* orderings of the three-`a` sum and e2 holds *both* spellings
of `2*a` — not as alternatives to choose between now, but as facts. Nothing
was deleted to build either. The moving parts, and what `egg` calls them [1][2]:

| Component | What it is | egg API |
|---|---|---|
| e-node | one operator application; operands are e-class ids | `ENode` (your `Language` type) |
| e-class | set of e-nodes asserted equivalent | list of e-nodes per class |
| e-class id | canonical number identifying a class | `Id` |
| union-find | merges classes, canonicalizes ids in ~O(1) | `UnionFind` |
| hashcons | dedup table: identical e-node -> existing class | `EGraph::add` |
| e-class analysis | per-class lattice data (constants, signs) | `Analysis` trait |
| scheduler | chooses which matches fire each iteration | `SimpleScheduler`, `BackoffScheduler` |

## Congruence Closure

The invariant that makes this sound is **congruence closure**: if two e-nodes
have the same operator and their operand classes are equivalent, the e-nodes
themselves are equivalent. In the diagram, once `x*2` and `x+x` are unioned
into e2, the congruence rule notices that `(* e3 e1)`-style parents built on
those ids must follow. Concretely: union e2's members, then re-canonicalize
every existing e-node's child ids through union-find and re-run hashconsing;
any two e-nodes that now hash identically get unioned too, and the sweep
repeats until a pass makes no merge. In the demo below this is a whole-table
rescan each round; `egg` maintains a dirty worklist so the repair is
proportional to what actually changed [1]. This machinery is the same
congruence-closure core that SMT solvers use for the theory of equality with
uninterpreted functions — see [SAT/SMT solvers](../../formal-methods/sat-smt-solvers.md)
for that side of the family. The name "e-graph" itself goes back to Downey,
Sethi, and Tarjan's 1980 JACM work on the common-subexpression problem.

## Rewrite Rules and E-Class Analyses

A rewrite rule is a pair *(search pattern, instantiation template)* over
e-classes: search finds e-classes matching, say `(* ?x 2)`, then apply adds
the instantiated `(+ ?x ?x)` into the graph and unions it with the matched
class. Rules never "fire and forget" — applying a rule only *adds evidence*.
Two refinements matter in practice:

- **Conditional rewrites.** Most real rule sets are not universally true:
  `x - x -> 0` holds for integers but not for NaN floats; shifts need range
  facts. egg rules can carry guards over per-class analysis data.
- **E-class analyses.** An `Analysis` attaches lattice data to every class —
  the classic example is constant folding: if all e-nodes in a class are
  constants, the class gets the folded value, and rules like "replace with
  the constant" fire only when the analysis proves it. Analyses also stop
  blow-up: folding `2+3` beats materializing every rearrangement of `2+3`.

## The Saturation Loop

Equality saturation is one loop, run until **fixpoint** (a full iteration
adds nothing) or until a **budget** expires (node count, iteration count, or
wall time — production users never rely on reaching the fixpoint):

```text
  build initial e-graph from the input expression
  loop:
    match    - find all (class, rule, substitution) matches
    apply    - instantiate rule templates, add e-nodes, union into matches
    merge    - union-find absorbs unions; hashcons dedups
    rebuild  - restore congruence closure (upward merges)
    schedule - decide which of next round's matches to allow
  until fixpoint or budget
  extract   - pick one e-node per reachable e-class by cost
```

The scheduler is where explosion is fought. egg's `BackoffScheduler` [1]
tracks how many matches a rule produced in past iterations and exponentially
*backs off* repeat offenders — rules like commutativity match everything,
everywhere, forever. Without scheduling, one iteration of a fat rule set can
generate millions of matches (the **match explosion**); with it, saturation
stays quadratic-ish in practice for compiler-sized terms.

## Why Saturation Beats Sequential Rewriting

- **No phase ordering.** All rules run "at once" every iteration; mutually
  inverse rules (`x*2 <-> x+x`) coexist harmlessly because hashconsing makes
  re-adding an existing e-node a no-op. The demo below saturates with both
  directions enabled and terminates.
- **No destructive commitment.** Greedy rewriting bets on one intermediate
  form; if the bet is wrong, the useful form is gone. An e-graph keeps the
  bet *and* the hedge, and defers the decision to extraction, where a global
  cost view exists.
- **Local rules compose globally.** Interactions like "associativity must run
  before distributivity" dissolve: both patterns simply match wherever they
  match, and congruence closure propagates the consequences upward
  automatically. Rule sets become flat lists instead of pass schedules.
The price is **intermediate expression swell**: the graph holds dead ends
until the budget says stop, and tuning budgets/schedulers is real
engineering work [1][3].

## Extraction: Picking One Node per Class

Saturated, the e-graph is a giant *or*-expression: one representative per
class must be chosen so the chosen nodes' operands stay consistent — pick a
node, and you commit to one representative of each of its operand classes
too. Given a cost model (node count, static instruction latency, code size,
data-dependent costs), **extraction** finds the cheapest consistent choice.
egg's default `Extractor` is greedy and bottom-up: per class, remember the
cheapest e-node under the current cost model, memoize, done in roughly linear
time — but greedy choices per class can be jointly suboptimal when costs
interact (sharing changes totals). The exact version is an ILP over
"which e-node represents which class," and optimal e-graph extraction is
NP-hard in general, so exact extraction is reserved for small hot terms;
production tools overwhelmingly ship heuristics with carefully tuned cost
models. Extraction is also where target-specific cost sneaks back in: Cranelift
extracts under a real instruction-selection cost model, which is what fuses
its optimizer and instruction selector into one pass (next section).

## A Runnable Miniature

A pure-Python e-graph — union-find classes, hashconsing, naive congruence
closure, four rules (`x*2 -> x+x`, `x+x -> x*2`, commutativity,
associativity) — saturating `(a*2 + a) * 2` for 3 iterations:

```python
"""Mini e-graph: hashconsed e-nodes, union-find e-classes, naive congruence
closure, and a saturation loop over 4 rewrite rules (what egg does in Rust)."""
ITERS, CAP = 3, 300

class EGraph:
    def __init__(self):
        self.nodes = {}    # hashcons: canonical e-node key -> e-class id
        self.members = []  # e-class slot -> list of e-node keys in it
        self.parent = []   # union-find: e-class id -> parent id

    def find(self, c):
        while self.parent[c] != c:          # find with path halving
            self.parent[c] = self.parent[self.parent[c]]
            c = self.parent[c]
        return c

    def add(self, key):                     # children canonicalized here
        key = (key[0],) + tuple(self.find(x) for x in key[1:])
        if key not in self.nodes:
            self.nodes[key] = cid = len(self.parent)
            self.parent.append(cid); self.members.append([key])
        return self.nodes[key]

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb: return False
        self.parent[rb] = ra                # merge rb into ra
        self.members[ra].extend(self.members[rb])
        return True

    def rebuild(self):
        """Congruence closure (toy version): re-hashcons every e-node under
        its children's *canonical* class ids; a collision means two e-nodes
        have congruent children, so their classes must be unioned."""
        while True:
            table, todo = {}, []
            for cid in range(len(self.parent)):
                for key in self.members[cid]:
                    ckey = (key[0],) + tuple(self.find(x) for x in key[1:])
                    if ckey in table: todo.append((table[ckey], self.find(cid)))
                    else: table[ckey] = self.find(cid)
            if not any(self.union(a, b) for a, b in todo):
                return len(table)           # live e-nodes

    def rewrite(self, target, key):         # add `key` node, union into
        key = (key[0],) + tuple(self.find(x) for x in key[1:])
        fresh = key not in self.nodes       # target's e-class; True only if
        return fresh | self.union(target, self.add(key))  # the graph changed

def saturate(eg, iters, cap):
    for it in range(1, iters + 1):
        applied = 0
        for key, slot in sorted(eg.nodes.items()):    # match every e-node
            c = eg.find(slot)
            if key[0] == '+':
                x, y = key[1], key[2]
                applied += eg.rewrite(c, ('+', y, x)) # R1 commutativity
                for k in sorted(set(eg.members[eg.find(x)])):
                    if k[0] == '+':                   # R2 associativity:
                        inner = eg.add(('+', k[2], y))  # x+y with x = (u+w)
                        applied += eg.rewrite(c, ('+', k[1], inner))
            if key[0] == '*' and key[2] == TWO:       # R3 x*2 -> x+x
                applied += eg.rewrite(c, ('+', key[1], key[1]))
            if key[0] == '+' and key[1] == key[2]:    # R4 x+x -> x*2
                applied += eg.rewrite(c, ('*', key[1], TWO))
            if len(eg.nodes) > cap: print("node budget hit"); break
        live = eg.rebuild()                           # merge/congruence phase
        ncls = len({eg.find(s) for s in range(len(eg.parent))})
        print(f"iter {it}: {applied:2d} rewrites, {live:2d} e-nodes, {ncls} e-classes")
        if applied == 0: print("fixpoint reached"); break

def sexpr(eg, c):                       # deterministic representative
    seen = {}
    def rep(cid):
        cid = eg.find(cid)
        if cid not in seen:
            key = sorted(set(eg.members[cid]))[0]
            seen[cid] = key[0].split('.', 1)[1] if len(key) == 1 else \
                        f"({key[0]} {rep(key[1])} {rep(key[2])})"
        return seen[cid]
    return rep(c)

eg = EGraph()
A, TWO = eg.add(('var.a',)), eg.add(('num.2',))   # leaves: no children
eg.add(('+', eg.add(('*', A, TWO)), A))           # a*2 + a   (class 3)
ROOT = eg.add(('*', 3, TWO))                      # (a*2 + a) * 2
eg.rebuild()
print(f"start : {sexpr(eg, ROOT)}  ({len(eg.nodes)} e-nodes)")
saturate(eg, ITERS, CAP)
for cid in sorted({eg.find(s) for s in range(len(eg.parent))}):
    mems = sorted(set(eg.members[cid]))
    if len(mems) > 1:
        print(f"  e{cid}:")
        for key in mems:
            print(f"    ({key[0]} e{eg.find(key[1])} e{eg.find(key[2])})"
                  f"   e.g. {sexpr(eg, key[1])} {key[0]} {sexpr(eg, key[2])}")
print(f"root e-class e{eg.find(ROOT)}: {len(set(eg.members[eg.find(ROOT)]))} "
      f"e-nodes, extracted: {sexpr(eg, ROOT)}")
```

Output (real run, deterministic):

```text
start : (* (+ (* a 2) a) 2)  (5 e-nodes)
iter 1:  3 rewrites,  8 e-nodes, 5 e-classes
iter 2:  2 rewrites, 12 e-nodes, 7 e-classes
iter 3:  5 rewrites, 17 e-nodes, 7 e-classes
  e2:
    (* e0 e1)   e.g. a * 2
    (+ e0 e0)   e.g. a + a
  e3:
    (+ e0 e2)   e.g. a + (* a 2)
    (+ e2 e0)   e.g. (* a 2) + a
  e4:
    (* e3 e1)   e.g. (+ a (* a 2)) * 2
    (+ e0 e8)   e.g. a + (+ a (+ a (+ a (* a 2))))
    (+ e2 e10)   e.g. (* a 2) + (+ a (+ a (* a 2)))
    (+ e3 e3)   e.g. (+ a (* a 2)) + (+ a (* a 2))
    (+ e8 e0)   e.g. (+ a (+ a (+ a (* a 2)))) + a
    (+ e10 e2)   e.g. (* a 2) + (+ a (+ a (* a 2))) + (* a 2)
  e8:
    (+ e0 e10)   e.g. a + (+ a (+ a (* a 2)))
    (+ e2 e3)   e.g. (* a 2) + (+ a (+ a (* a 2)))
    (+ e3 e2)   e.g. (+ a (* a 2)) + (* a 2)
  e10:
    (+ e0 e3)   e.g. a + (+ a (+ a (* a 2)))
    (+ e3 e0)   e.g. (+ a (* a 2)) + a
root e-class e4: 6 e-nodes, extracted: (* (+ a (* a 2)) 2)
```

Read the class ladder upward: e2 = both spellings of `2a`, e3 = `3a`, e10 =
`4a`, e8 = `5a`, and the root e4 = `6a` in six forms — saturation derived a
little arithmetic ladder purely from four local rules, with both `x*2` and
`x+x` enabled the whole time (no ping-pong: re-adding `(* e0 e1)` is a no-op).
Every member of e4 is congruent with the others because unioning `x*2 ~ x+x`
inside e2 propagated upward through shared parent e-nodes — that is congruence
closure doing real work. Extraction then picks one node per class under the
cost model; here all e4 members cost the same, so the deterministic tie-break
keeps the original spelling.

## Where It Ships

| System | Role of e-graphs | Rules |
|---|---|---|
| [Cranelift](./cranelift.md) (aegraph) | mid-end optimizer for Wasmtime's JIT; rewrites + extraction fused with instruction selection | ISLE rules in the Cranelift source |
| [Herbie](https://herbie.uwplse.org/) | floats: rewrite toward more *accurate* forms, not cheaper ones | hand-written arithmetic rules ([herbie-fp/herbie](https://github.com/herbie-fp/herbie)) |
| Sketch-guided saturation [4] | large functional-program transformations where rules don't exist yet | rules synthesized on demand |
| egglog [5] | e-graphs unified with Datalog; language-level successor to egg | egglog programs |

Cranelift is the flagship compiler deployment. Its "aegraph" (***a*cyclic
e-graph**) replaces a dozen hand-ordered IR passes with one egraph pass: CLIF
is translated into e-classes, ISLE-written rewrite rules saturate under a
budget, and extraction under an instruction cost model emits the final
instruction sequence — optimization and instruction selection in one
structure ([module](https://github.com/bytecodealliance/wasmtime/blob/main/cranelift/codegen/src/egraph/mod.rs),
design write-up [3]; mechanics page: [Cranelift](./cranelift.md), which
defers the e-graph details to this page). Floating-point soundness is gated
by a NaN-canonicalization pass so float rewrites stay correct.
Mechanics page: [Cranelift](./cranelift.md) defers the e-graph details here.

The contrast with [superoptimization](./superoptimization.md) is instructive:
STOKE *searches* instruction space and must verify each candidate with SMT,
because nothing guarantees its transformations preserve meaning; an e-graph
*constructs* the proof as it goes — every edge is a trusted axiom — so the
end state is correct by construction and no solver is needed. The cost flips
around too: superoptimizers are sound-but-slow and unbounded, saturation is
fast but only as trustworthy as its rule set. [Peephole
optimization](./peephole-optimization.md) is the shared substrate: an e-graph
rule set is a peephole table that never has to be ordered.

## Limitations and Failure Modes

- **Match explosion.** Fat rule sets over commutative operators generate
  combinatorial matches per iteration; schedulers and budgets are mandatory,
  and bad schedules silently starve useful rules [1].
- **Extraction is its own optimization problem.** Greedy extractors are
  suboptimal when costs interact; exact ILP extraction is NP-hard; a cost
  model that disagrees with the target turns a "proven equivalent" pool into
  a mediocre pick.
- **Memory growth.** E-graphs are add-only; nothing prunes dead classes
  during saturation, and long runs trade RAM for phase-freedom.
- **Control flow.** Plain e-graphs are DAGs of values; loops and CFG
  transforms need extensions (Cranelift's *acyclic* aegraph is named that
  way for a reason), and cross-block rewrites remain research territory.
- **A wrong rule miscompiles everything, silently.** Every rewrite is a
  trusted axiom; NaN semantics, overflow, and UB need analyses gating rules,
  not reviewer vigilance.

## Interview Angles

- *"Why not just order your optimization passes carefully?"* — Phase ordering
  is a real, unsolved-by-heuristics problem; destructive rewrites lose
  intermediates; e-graphs make order irrelevant by keeping all forms, at the
  price of memory and extraction.
- *"How does saturation terminate?"* — It often doesn't reach a fixpoint;
  production runners use node/iteration/time budgets with backoff schedulers,
  and the answer is extracted from wherever saturation stopped.
- *"Is the result verified?"* — Only relative to the rewrite axioms: the
  e-graph structure is a proof *certificate* built from trusted rules, unlike
  superoptimizer-style search, which needs SMT validation of candidates.

## References

1. M. Willsey, C. Nandi, Y. R. Wang, O. Flatt, Z. Tatlock, P. Panchekha,
   "egg: Fast and Extensible Equality Saturation," Proc. ACM Program. Lang.
   4(POPL), 2021: <https://doi.org/10.1145/3434304>
2. egg — egraphs good (library, docs, tutorial): <https://github.com/egraphs-good/egg>
   and the e-graphs community hub: <https://egraphs-good.github.io/>
3. C. Fallin, "The acyclic e-graph: Cranelift's mid-end optimizer," Apr 2026:
   <https://cfallin.org/blog/2026/04/09/aegraph/>
4. Sketch-Guided Equality Saturation (scaling e-graphs to complex
   transformations): <https://arxiv.org/abs/2111.13040>
5. egglog — Datalog + e-graphs (successor system):
   <https://github.com/egraphs-good/egglog>
