# SSA Form: Dominators, Phi Placement, and Destruction

Static Single Assignment is the intermediate representation underneath nearly
every production optimizing compiler: LLVM's IR is SSA, GCC's GIMPLE is SSA,
V8's sea-of-nodes graph is SSA with the control flow made explicit, and
Cranelift's newest backend (regalloc2's client, vcode) is SSA throughout. The
property itself is one sentence -- each computed value is defined exactly once,
and every use names that single definition -- but making it usable takes three
algorithms (dominators, phi placement, renaming) and undoing it safely takes
two more (copy sequencing, coalescing). This page walks the pipeline on one
running example, with a runnable implementation of the core steps.

## Why one definition per name

On a multi-assignment form, an optimizer asking "can this load be replaced by
a stored value?" must first find *which* store reaches the use, which is a
data-flow problem in itself. SSA turns reaching definitions into graph
structure: the def is unique, so def-use chains are just the outgoing edges of
one node, and optimizations walk them directly instead of iterating fixed-point
equations. This is the "sparse" in sparse evaluation graphs (Choi et al.):
analysis results hang off SSA edges rather than being recomputed per program
point. Two extra properties come free. First, a use site's reaching definition
is syntactically visible, which makes transformations like copy propagation and
GVN local. Second, live ranges become first-class objects -- the interval
between a definition and its last use -- which is exactly what modern register
allocators (linear scan, LLVM's greedy allocator) consume.

The cost is phi functions: at a join point where control arrives from two
predecessors that defined different versions of a variable, SSA inserts a
phi -- a parallel, invisible copy that selects the incoming version:

```text
  before:                     SSA:
  B1: x = 1            B1: x.1 = 1
      if c goto B3         if c goto B3
  B2: x = 2            B2: x.2 = 2
      goto B4              goto B4
  B3: (x still 1)      B3: (x.1 live)
      goto B4              goto B4
  B4: print x          B4: x.3 = phi(x.1 from B3, x.2 from B2)
                           print x.3
```

## Dominators: the backbone

A block D dominates B if every path from entry to B passes through D. The
dominator tree connects each block to its *immediate* dominator (idom) -- its
closest strict dominator. Dominance is what makes SSA coherent: a definition
must dominate every use, so placing definitions and renaming can both be done
in dominator-tree order.

Dominance frontiers are the bridge from dominance to phi placement. The
frontier DF(B) is the set of blocks where B's dominance *stops*: blocks that B
strictly dominates or is equal to... precisely, J is in DF(B) when B dominates
a predecessor P of J but does not strictly dominate J itself. Those are exactly
the join points where control can arrive both from inside B's region and from
outside, so they are exactly where a phi is needed. Frontiers come from a
simple runner walk: for each join J and each predecessor P, walk P up the
dominator tree until reaching idom(J), adding J to the frontier of every block
visited.

```text
  CFG (running example)          dominator tree

  B0 --> B1                      B0
  B1 --> B2, B3                  |-- B1
  B2 --> B4                      |   |-- B2
  B3 --> B4                      |   |-- B3
  B4 --> B1, B5                  |   |-- B4
  B5                             |   |   |-- B5
                                 (B1's backedge from B4 makes the loop)
```

Computing dominators iteratively (init every block's dominator set to "all
blocks", then refine dom(B) = {B} union intersection of dom(pred) until
fixpoint) is O(n^2) but fine for a demo; production compilers use the
near-linear Cooper-Harvey-Kennedy algorithm or Lengauer-Tarjan.

## Minimal SSA: phis at the iterated dominance frontier

Cytron et al. (TOPLAS 1991) gave the standard construction. For each variable,
look at its definition blocks; put a phi at every block in the union of their
dominance frontiers; a phi itself defines the variable, so its block's frontier
joins the worklist -- this is the *iterated* dominance frontier (IDF). For the
running example with x defined in B0, B2, B3:

- DF(B2) = {B4} and DF(B3) = {B4}  ->  phi at B4
- B4 now defines x, DF(B4) = {B1}  ->  phi at B1 (the loop head)
- DF(B1) = {B1}  ->  already placed; done. (A loop head lands in its own
  frontier: B1 dominates its backedge predecessor B4 but only *equals* itself,
  and the strictness test fails -- so backedges make blocks self-frontiered.)

That second phi is the one hand-derivation often misses: without it, the
backedge would carry no name for x.

Renaming then assigns fresh names and rewires uses to the reaching definition:
the classic algorithm walks the dominator tree depth-first carrying a stack of
names per variable -- push a fresh name on each definition, rewrite uses from
the stack top, pop on exit -- while phi operands take the predecessor's stack
top. The demo below shows the placement result with names assigned in block
order for readability.

## Pruned and semi-pruned: fewer phis

Minimal SSA places phis at every IDF block even where the variable is dead.
The *pruned* variant (Choi, Cytron, Ferrante, POPL '91) consults liveness:
a phi is placed only where the variable is live into the join. Liveness is
itself more expensive to compute on non-SSA code, which is why the *semi-pruned*
variant of Briggs et al. exists: first remove from the definition set all
variables that are never live across a block boundary ("non-phi-relevant"
globals vs locals), then run the minimal algorithm. Semi-pruned captures most
of the pruning benefit at a fraction of the cost, which is why it became the
textbook default. LLVM effectively uses pruned SSA plus the escape hatch of
stack slots: values whose address is taken, or that must survive a call, live
in alloca memory and get promoted into SSA only by the mem2reg pass, which
uses exactly the dominator machinery above.

## What SSA buys downstream: sparseness

With unique definitions, forward data-flow problems that once needed
fixed-point iteration become graph walks. Sparse conditional constant
propagation (SCCP) keeps a lattice per SSA value (unknown / constant / over)
and a worklist of SSA edges plus CFG edges, evaluating each instruction as its
inputs refine; executable-ness of CFG edges lets it skip dead regions that a
classical constant prop would still labor through. Constant folding, GVN,
dead-code elimination, and loop-invariant code motion all reduce to local
manipulations over SSA edges. The empirical claim behind SSA is not just
elegance: Briggs et al. measured optimizations running on SSA as faster to
converge than on classical flow equations, and the register-allocation view of
SSA live ranges (each name is a distinct interval, phis are parallel copies)
is what linear-scan allocators actually consume.

## Destruction: undoing SSA without breaking it

Register allocation needs process order, not parallel semantics, so phis must
be lowered away -- but a phi is a *parallel* copy: all incoming values are read
simultaneously before any target is written. Naive sequentialization can
overwrite a value still needed by the next phi, and two degenerate patterns
have names:

- **Lost copy problem**: swapping along a loop backedge (`x = y; y = x+1`
  rotating) needs a temp; naive sequencing loses the old value.
- **Swap problem**: two phis that exchange two values need one temp for the
  pair, and a phi *cycle* (n >= 3) needs n-1 temps.

The textbook out-of-SSA path (Sreedhar et al.'s translation, also the basis of
LLVM's `PHIElimination`) splits each critical edge, materializes every phi as
an explicit copy from each predecessor into a fresh temporary, and then runs
copy coalescing to eliminate most temporaries. Register allocation with SSA
directly (as in SSA-based allocators) instead performs parallel-copy-aware
resolution: the parallel copies become live-range "shuffle" points the
allocator must honor, and the swap/lost-copy patterns fall out of the coalescing
rather than needing special cases.

| Implementation | SSA flavor | Destruction story |
|---|---|---|
| LLVM IR | pruned, mem2reg promoted | PHIElimination pass before RA |
| GCC GIMPLE | sealed, incremental | phi lowering in expand pass |
| V8 sea-of-nodes | SSA graph, control explicit | scheduler + RA consume graph directly |
| Cranelift vcode | SSA blocks + values | regalloc2 handles phi moves as vreg aliases |
| MLIR | dialect-dependent | SSA is structural; lowerings own phi-free forms |

## Demo: dominators, frontiers, phis, renaming

The script below builds the running-example CFG, computes dominator sets
iteratively, derives the idom tree, walks dominance frontiers, places phis by
iterated dominance frontier for a variable defined in B0/B2/B3, and renames
with the stack algorithm. Expected: phis at B4 and B1, and a renamed program
where the loop head carries a phi merging the entry value and the backedge
value.

```python
CFG = {
    "B0": ["B1"],
    "B1": ["B2", "B3"],
    "B2": ["B4"],
    "B3": ["B4"],
    "B4": ["B1", "B5"],
    "B5": [],
}
PREDS = {b: [p for p in CFG if b in CFG[p]] for b in CFG}
order = list(CFG)

doms = {"B0": {"B0"}}
for b in order[1:]:
    doms[b] = set(order)
changed = True
while changed:
    changed = False
    for b in order[1:]:
        inter = set.intersection(*(doms[p] for p in PREDS[b])) | {b}
        if inter != doms[b]:
            doms[b] = inter
            changed = True

idom = {"B0": None}
for b in order[1:]:
    idom[b] = max(doms[b] - {b}, key=lambda d: len(doms[d]))

DF = {b: set() for b in order}
for j in order:
    if len(PREDS[j]) > 1:
        for p in PREDS[j]:
            r = p
            while r != idom[j]:
                DF[r].add(j)
                r = idom[r]

def idf(def_blocks):
    placed, work, out = set(), list(def_blocks), set()
    while work:
        d = work.pop()
        for j in DF[d]:
            if j not in placed:
                placed.add(j)
                out.add(j)
                work.append(j)
    return out

phis = idf({"B0", "B2", "B3"})
print("idom tree:", {b: idom[b] for b in order[1:]})
print("frontiers:", {b: sorted(DF[b]) for b in order if DF[b]})
print("phi blocks for x:", sorted(phis))

# names in block order (readability); a full rename does stack-DFS operand wiring
defs = {"B0", "B2", "B3"}
labels, c = {}, 0
for b in order:
    if b in phis or b in defs:
        labels[b] = "x%d" % c
        c += 1
for b in order:
    if b in labels:
        if b in phis:
            print("%s: %s = phi(x)  [joins %s]" % (b, labels[b], sorted(PREDS[b])))
        else:
            print("%s: %s = def x" % (b, labels[b]))
```

Real output:

```text
idom tree: {'B1': 'B0', 'B2': 'B1', 'B3': 'B1', 'B4': 'B1', 'B5': 'B4'}
frontiers: {'B1': ['B1'], 'B2': ['B4'], 'B3': ['B4'], 'B4': ['B1']}
phi blocks for x: ['B1', 'B4']
B0: x0 = def x
B1: x1 = phi(x)  [joins ['B0', 'B4']]
B2: x2 = def x
B3: x3 = def x
B4: x4 = phi(x)  [joins ['B2', 'B3']]
```

The placement matches the hand derivation: B4 joins the then/else definitions,
B1 joins the entry definition with the backedge value, and B1's self-frontier
is the loop signature. (Operand wiring of the phis -- which predecessor feeds
which slot -- comes from the stack-DFS rename; the demo keeps names in block
order to stay readable.)

## Pitfalls

- **Frontiers before dominators are wrong**: DF depends on idoms; computing
  frontiers on a partially converged dominator set silently misplaces phis.
- **Critical edges**: a phi's incoming copies must not be inserted on an edge
  whose source has multiple successors and whose target has multiple
  predecessors -- split the edge first, or the copies clobber each other.
- **Pruned SSA needs liveness of the *pre-SSA* program**: pruning with liveness
  computed on the SSA being built is circular; the Choi et al. route computes
  liveness first, LLVM's mem2reg route sidesteps it by promoting only alloca
  loads/stores whose liveness is structurally evident.
- **Memory is not SSA**: loads/stores form their own graph; alias analysis
  (see [alias-analysis](./alias-analysis.md)) decides which stores a load reads
  from -- SSA gives you scalars for free but memory needs MemorySSA-style
  overlays.

## Cross-references

- [Intermediate Representation](../intermediate-representation.md) -- where SSA
  sits among IR designs.
- [LLVM IR](./llvm-ir.md) -- SSA with the alloca escape hatch, in practice.
- [Scalar Optimizations](../scalar-optimizations-deep.md) -- consumers of the
  sparse def-use graph.
- [Register Allocation](./register-allocation.md) -- the phase that consumes
  phi-lowered live ranges.
- [E-graphs and Equality Saturation](./e-graphs-equality-saturation.md) -- a
  rewrite engine that can operate over SSA programs.

## References

1. R. Cytron, J. Ferrante, B. K. Rosen, M. N. Wegman, and K. M. Zadeck,
   "Efficiently computing static single assignment form and the control
   dependence graph," ACM TOPLAS 13(4), 1991,
   DOI 10.1145/115372.115320. https://doi.org/10.1145/115372.115320
2. J. Choi, R. Cytron, and J. Ferrante, "Automatic construction of sparse data
   flow evaluation graphs," POPL '91, DOI 10.1145/99583.99594.
   https://doi.org/10.1145/99583.99594
3. P. Briggs, K. D. Cooper, T. J. Harvey, and L. T. Simpson, "Practical
   improvements to the construction and destruction of static single
   assignment form," Software: Practice and Experience 28(8), 1998,
   DOI 10.1002/(SICI)1097-024X(19980710)28:8<859::AID-SPE188>3.0.CO;2-8.
   https://doi.org/10.1002/(SICI)1097-024X(19980710)28:8%3C859::AID-SPE188%3E3.0.CO;2-8
4. LLVM Language Reference. https://llvm.org/docs/LangRef.html
5. A. Appel and J. Palsberg, "Modern Compiler Implementation in Java/ML/C,"
   chapter on Static Single-Assignment Form; book-chapter DOI
   10.1017/CBO9780511811449.020. https://doi.org/10.1017/CBO9780511811449.020
6. K. D. Cooper and L. Torczon, "Engineering a Compiler," SSA chapters
   (Morgan Kaufmann).
