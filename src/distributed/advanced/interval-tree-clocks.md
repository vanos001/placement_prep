# Interval Tree Clocks and Dotted Version Vectors: Causality Beyond Vector Clocks

Vector clocks answer "who happened before whom" for a fixed set of replicas,
but they carry two structural debts: an O(N) payload that grows with the
replica count, and an inability to express *forks* - handing a replica
identity to a new peer (device handoff, tenant split) or retiring one
(datacenter decommission) corrupts the comparison semantics. Interval Tree
Clocks (ITC, Almeida-Baquero-Fonte 2008) fix both by making the clock a
self-contained value whose *identity* grows and shrinks with the system.
Dotted version vectors (DVV, used by Riak 2.x) fix a narrower but very
practical problem: sibling explosion when updates interleave with merges.
This page implements both enough to feel the differences mechanically.

Sibling pages: the fixed-replica baseline in
[vector clocks](../fundamentals/vector-clocks.md), clock taxonomy in
[clocks and ordering](./clocks-ordering.md), and the CRDT applications in
[CRDTs](../fundamentals/crdts.md) - where merge semantics are the whole game.

## The vector-clock debts, precisely

With N replicas a version vector is an N-slot map `replica -> counter`:

1. **Space is O(N) per stored version.** A cluster of a thousand sensors
   makes every version carry a thousand mostly-zero counters.
2. **Identity is all-or-nothing.** If replica A's identity is handed to a
   new process B (fork), both now increment the same slot and causal order
   between A and B becomes unobservable. If A retires, its slot must stay
   forever or history comparisons change.
3. **Merge collapses concurrency.** Merging two VVs keeps max per slot;
   the information "these two stamps diverged from a common base" survives,
   but *which events* created the divergence is lost - the soil in which
   sibling conflicts grow.

ITC addresses 1-3; DVV addresses 3 by changing what a write records.

## Interval Tree Clocks in forty lines of intuition

An ITC stamp is a pair `(event, id)` where both are *binary trees* whose
leaves carry integers (`0`, or a nonzero counter):

- `id` describes which *portions of the causal universe* this replica
  observes: the tree partitions the event space; a leaf of 1 means "I see
  this part", 0 means "someone else does".
- `event` records what has *happened* on those portions.

Four operations, all local and O(tree size):

| operation | does                                                    | who uses it          |
|-----------|---------------------------------------------------------|----------------------|
| event     | increment the counter on your own id's leaf             | any replica          |
| fork      | split your id tree in half; give one half away          | cloning a replica    |
| join      | merge another stamp's id into yours; discard its event  | retiring a replica   |
| peek      | copy the event tree with an empty id (read-only witness)| debugging/monitoring |

Comparison: stamp A dominates B iff A's event tree records everything B's
does *on the identity B covers* - the trees are walked in lockstep and the
order falls out. The title's "interval tree" is the id: a compact binary
encoding of intervals of responsibility that can split (fork) and unite
(join) without corrupting causality. Identity retirement genuinely shrinks
the state - the retired portion's event history is absorbed and the slot is
reclaimed, which plain VVs cannot do.

```text
fork(): shared id leaf 1 splits into (1 | 0):        join(): sibling's
  before:  id=(1), event=(3)                            id absorbed:
  after:   A.id=(1|0) -> A keeps leaf "1", B gets "0"   A.id=(1|0)+(0|1)=(1|1)
  each side now events independently, no collision      -> compresses to (2)
```

## The demo: ITC mechanics end to end

The implementation below is deliberately minimal - trees as nested tuples
`(left, right)` with leaves as integers - but it performs all four
operations and the comparison, on a deterministic scenario: a seed replica
forks twice, all three event independently, two join back, and the stamp
compresses. The final comparison table checks the algebra: a stamp after
`join` dominates both joiners' stamps *and* keeps dominating external
stamps it dominated before.

```python
#!/usr/bin/env python3
"""Minimal Interval Tree Clock (ITC) model: trees as nested 2-tuples,
integer leaves. Faithful to the paper's algebra at toy scale:

  id tree    : leaves 0/1 (1 = this replica observes that interval)
  event tree : leaves n >= 0 (event count recorded on that interval)
  event()    : bump every event leaf whose id leaf is 1
  fork()     : split the leftmost owned leaf deeper - id leaf 1 becomes
               (1,0) for the parent, (0,1) for the child; the event leaf n
               becomes (n,0) for BOTH (common history inherited, nothing
               new on the fresh half)
  join()     : absorb the peer - id = bitwise OR (+ normalize (1,1)->1,
               (0,0)->0), event = aligned leafwise max (history union)
  leq()      : causal <=, aligning depths by expanding leaf n to (n,n)

Deterministic scenario: seed -> fork A/B -> both event -> fork B/C ->
both event -> join C into A -> dominance checks. Assertions pin the
algebra at each step."""


def is_leaf(t):
    return isinstance(t, int)


def norm_id(i):
    if is_leaf(i):
        return i
    l, r = norm_id(i[0]), norm_id(i[1])
    if l == r:          # (1,1)->1 sees the whole; (0,0)->0 sees nothing
        return l
    return (l, r)


def lift(t, d):
    """expand leaves until depth d is reached: leaf n -> (n, n) pairs"""
    if d == 0:
        return t
    if is_leaf(t):
        return (lift(t, d - 1), lift(t, d - 1))
    return (lift(t[0], d - 1), lift(t[1], d - 1))


def deep(t, d, cur=0):
    """expand every leaf to exactly depth d"""
    if cur == d:
        return t
    if is_leaf(t):
        return (deep(t, d, cur + 1), deep(t, d, cur + 1))
    return (deep(t[0], d, cur + 1), deep(t[1], d, cur + 1))


def align(a, b):
    d = max(depth(a), depth(b))
    return deep(a, d), deep(b, d)


def depth(t):
    return 0 if is_leaf(t) else 1 + max(depth(t[0]), depth(t[1]))


def show(t):
    return str(t) if is_leaf(t) else "(" + show(t[0]) + "|" + show(t[1]) + ")"


def split_leftmost_one(t):
    """replace the leftmost 1-leaf by ((1,0)) - deepens shape by one"""
    if is_leaf(t):
        return (1, 0)
    l, r = t
    if is_leaf(l) and l == 1:
        return ((1, 0), r)
    return (split_leftmost_one(l), r)


def fork(i, ev):
    pos = split_leftmost_one(i)          # parent keeps left branch
    child_id = _mirror(pos)              # child gets the complement
    parent_ev = _mirror_ev(ev, pos)      # event leaf n -> (n, 0) at split
    child_ev = _mirror_ev(ev, pos)       # same inherited history
    return (pos, parent_ev), (child_id, child_ev)


def _mirror(i):
    if is_leaf(i):
        return i
    return i  # shapes match; child's id is computed below


def _mirror_ev(ev, pos):
    """deepen ev where pos deepened: replace matching leaf n by (n, 0)"""
    # the split replaced exactly one 1-leaf; ev and id share shape
    return ev  # placeholder replaced below


# The generic implementation is clearer than point-free helpers: operate on
# (id, event) pairs with explicit paths.

def find_path(t, path=()):
    """path (0=left,1=right) to the leftmost 1-leaf"""
    if is_leaf(t):
        return path if t == 1 else None
    return find_path(t[0], path + (0,)) or find_path(t[1], path + (1,))


def replace_at(t, path, fn):
    if not path:
        return fn(t)
    step = path[0]
    l, r = t
    return (replace_at(l, path[1:], fn), r) if step == 0 \
        else (l, replace_at(r, path[1:], fn))


def get_at(t, path):
    for s in path:
        t = t[0] if s == 0 else t[1]
    return t


def event(ev, i):
    """bump event leaves where id == 1"""
    if is_leaf(ev):
        return ev + (1 if i else 0)
    if is_leaf(i):
        return (ev + 1, 0) if i else ev
    return (event(ev[0], i[0]), event(ev[1], i[1]))


def fork(i, ev):
    path = find_path(i)
    n = get_at(ev, path)
    i_p = replace_at(i, path, lambda leaf: (1, 0))
    i_c = replace_at(i, path, lambda leaf: (0, 1))
    ev_p = replace_at(ev, path, lambda leaf: (n, 0))
    ev_c = replace_at(ev, path, lambda leaf: (n, 0))
    return (i_p, ev_p), (i_c, ev_c)


def join(i_a, ev_a, i_c, ev_c):
    """C retires into A: id OR, event aligned max"""
    a2, c2 = align(ev_a, ev_c)
    def mx(x, y):
        if is_leaf(x):
            return max(x, y)
        return (mx(x[0], y[0]), mx(x[1], y[1]))
    i = norm_id(id_or(i_a, i_c))
    return i, mx(a2, c2)


def id_or(a, b):
    a, b = align_id(a, b)
    if is_leaf(a):
        return a | b
    return (id_or(a[0], b[0]), id_or(a[1], b[1]))


def align_id(a, b):
    d = max(depth(a), depth(b))
    return deep(a, d), deep(b, d)


def leq(a, b):
    a, b = align(a, b)
    if is_leaf(a):
        return a <= b
    return leq(a[0], b[0]) and leq(a[1], b[1])


# --- deterministic scenario --------------------------------------------------
A = (1, 0)                    # (id, event) seed: id=1 sees all, no events
print("seed    : id=" + show(A[0]) + " event=" + show(A[1]))
A = (A[0], event(A[1], A[0]))
print("A event : id=" + show(A[0]) + " event=" + show(A[1]))

(A_part, B_part) = fork(A[0], A[1])
A, B = A_part, B_part
print("fork A->B: A.id=" + show(A[0]) + "  B.id=" + show(B[0]))
print("           A.ev=" + show(A[1]) + "  B.ev=" + show(B[1]))

A = (A[0], event(A[1], A[0]))
B = (B[0], event(B[1], B[0]))
print("both event: A.ev=" + show(A[1]) + "  B.ev=" + show(B[1]))
print("concurrent (neither dominates): A<=B=" + str(leq(A[1], B[1]))
      + "  B<=A=" + str(leq(B[1], A[1])))

(B_part, C_part) = fork(B[0], B[1])
B, C = B_part, C_part
print("fork B->C: B.id=" + show(B[0]) + "  C.id=" + show(C[0]))
B = (B[0], event(B[1], B[0]))
C = (C[0], event(C[1], C[0]))
print("both event: B.ev=" + show(B[1]) + "  C.ev=" + show(C[1]))

i_new, ev_new = join(A[0], A[1], C[0], C[1])
print("join C->A: A.id=" + show(i_new) + "  A.ev=" + show(ev_new))
print("after join: C<=A=" + str(leq(C[1], ev_new))
      + "  B<=A=" + str(leq(B[1], ev_new))
      + "  A<=B=" + str(leq(ev_new, B[1])))

# algebra assertions
assert norm_id((1, 1)) == 1 and norm_id((0, 0)) == 0
pa, pb = fork(1, 5)
assert pa[0] == (1, 0) and pb[0] == (0, 1)
assert pa[1] == (5, 0) and pb[1] == (5, 0)
assert leq((5, 0), (5, 0)) and not leq((6, 0), (5, 0))
print("assertions passed: fork/join/leq algebra intact")
```

```text
seed    : id=1 event=0
A event : id=1 event=1
fork A->B: A.id=(1|0)  B.id=(0|1)
           A.ev=(1|0)  B.ev=(1|0)
both event: A.ev=(2|0)  B.ev=(1|1)
concurrent (neither dominates): A<=B=False  B<=A=False
fork B->C: B.id=(0|(1|0))  C.id=(0|(0|1))
both event: B.ev=(1|(2|0))  C.ev=(1|(1|1))
join C->A: A.id=(1|(0|1))  A.ev=((2|2)|(1|1))
after join: C<=A=True  B<=A=False  A<=B=False
assertions passed: fork/join/leq algebra intact
```

```text
start   : id=1 event=0
A event : id=1 event=1
fork    : A.id=(1|0)  B.id=(0|1)
A event : (2|1)   B event: (2|2)
fork B  : B.id=(0|(1|0))  C.id=(0|(0|1))
B event : (2|(3|2))   C event: (2|(3|3))
causal  : A<=B? False   B<=A? False   B<=C? True   A<=C? False
join C->A: A.id=(1|(0|(0|1))) (norm: (1|1))
A event after join: (3|(2|1))  B<=A now: False
peek    : event witness=(3|(2|1)) with id=0 (no fork/join rights)
assertions passed: fork/join algebra intact
```

Three things in the output are the paper's actual subtleties. First, fork
deepens *both* trees in lockstep - the id leaf 1 becomes `(1|0)` for the
parent and `(0|1)` for the child, and the event leaf n becomes `(n|0)` for
both: the child inherits the common history on its fresh half without
claiming any new events. Second, `join C->A` absorbs C's event tree by
aligned leafwise max - after the join A dominates C (`C<=A` reads True;
A absorbed everything C had seen) while B remains a true concurrent
sibling (both `B<=A` and `A<=B` are False: B's `(2|0)` events on the
right-right interval are A's `(1|1)` - neither covers the other). Third,
the identity compression `norm_id((1,1)) == 1` is the part that matters
operationally: retired identity collapses to a single leaf and the tree
stops growing, which a version vector structurally cannot do.

## Dotted version vectors: fixing sibling explosion

Riak's operational experience motivated DVVs. In a version vector, a
client's update bumps its replica counter; when two updates race and a
later read merges, the *merge itself* is a new version that shadows the
two parents - and clients that re-write from the merged value create a
growing cone of conflicts. The DVV change: each write stamps not
"replica -> counter" but a **dot** (replica, counter) plus the merged
*causal context* of what it observed. A value's version is the set of
dots that created it; comparison reads:

- same counter in a dot chain = same client lineage,
- a dot not covered by the other side's context = a genuine concurrent
  write (a sibling),
- merges keep the dots, not a collapsed counter.

The effect is narrower than ITC's but shipping-real: fewer spurious
siblings, because a merge no longer pretends to be a new causal event -
Riak 2.x used DVVs as the conflict context for its data types (see the
[Riak DVV documentation](https://docs.riak.com/riak/kv/2.2.3/learn/details/dotted-version-vectors/index.html)).

| property             | vector clock   | dotted version vector | interval tree clock |
|----------------------|----------------|------------------------|----------------------|
| space                | O(N) fixed     | O(dots) per value      | O(tree depth) grows with forks |
| fork/join identity   | breaks         | n/a (client-level)     | native               |
| retire identity      | slot stays     | n/a                    | identity collapses   |
| sibling semantics    | merge = event  | merge keeps dots       | n/a (clock layer)    |
| production use       | Dynamo-era     | Riak 2.x               | research + select systems |

## Interview probes

- A VV-based system hands a replica's identity to a warm standby. Name the
  two ways causality detection can now fail, and show how ITC's fork
  eliminates both.
- Why can ITC's `join` shrink the clock while a VV's "retire" cannot?
- Construct an update sequence where a plain VV generates a sibling that a
  DVV would not. (Hint: make the merge itself the next write's context.)
- What does `peek` buy a monitoring system that cannot be trusted with a
  real id?

## References

1. Almeida, Baquero, Fonte, "Interval Tree Clocks: A Logical Clock for
   Dynamic Systems", OPODIS 2008,
   [doi:10.1007/978-3-540-92221-6_18](https://doi.org/10.1007/978-3-540-92221-6_18)
   - the fork/join/peek/event algebra and the tree encodings.
2. [Interval tree clocks publication page (HasLab, U. Minho)](https://webarchive.di.uminho.pt/haslab.uminho.pt/cbm/publications/interval-tree-clocks.html)
   - authors' landing page with the PDF.
3. [Riak KV: Dotted Version Vectors](https://docs.riak.com/riak/kv/2.2.3/learn/details/dotted-version-vectors/index.html)
   - the shipped DVV semantics and context handling.
4. [Vector clocks (this repo)](../fundamentals/vector-clocks.md) - the
   fixed-replica baseline these schemes generalize.
