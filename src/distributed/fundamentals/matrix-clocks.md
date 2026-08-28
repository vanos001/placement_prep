# Matrix Clocks: Tracking What Everyone Knows About Everyone

> A [vector clock](./vector-clocks.md) answers "what does process `i`
> know?" A matrix clock answers "what does process `i` know about what
> process `j` knows?" — for every `i`, `j`. That second-order knowledge
> is what garbage collection, consistent dumps, and termination
> detection actually need, and it is the only family in the
> [clock survey](../advanced/clocks-ordering.md) with quadratic state.
> This page defines the clock, walks the receive rule that summaries
> get subtly wrong, and runs a demo where a vector says "seen" but only
> a matrix can say "everyone has seen it."

## The Knowledge Hierarchy in One Table

Each clock family adds one level of introspection over the previous:

| Clock | State at process `i` | Question it can answer | Cost to carry |
|-------|----------------------|------------------------|---------------|
| [Lamport scalar](./lamport.md) | one integer | "is `a` before `b`?" (one direction only) | O(1) |
| [Vector](./vector-clocks.md) | `N` integers | "has `i` seen `k`'s event?" | O(N) |
| Matrix | `N²` integers | "does `i` know that `j` has seen `k`'s event?" | O(N²) |

The matrix cell `MC[i][j][k]` is defined as:

```text
MC[i][j][k] = the number of process k's events that process i
              believes process j is aware of
```

Two structural consequences worth memorizing:

- **Row `i` is `i`'s own vector clock** — `MC[i][i][k]` is what `i`
  has itself seen; the diagonal-as-rows slice reproduces the vector.
- **Column `k` is gossip about `k`** — `MC[i][j][k]` over varying `j`
  tells `i` how far `k`'s history has propagated, the quantity
  stability checks consume.

## The Algorithm, Including the Rule Summaries Omit

Send and receive look like the vector algorithm plus a merge loop —
but the receive has a step naive implementations drop, and without it
the matrix silently under-reports knowledge:

```text
local event at i:                      MC[i][i][i] += 1

send from i to j:                      MC[i][i][i] += 1
                                       attach a copy of MC[i]

receive at j from i:                   # 1. absorb the sender's knowledge row
                                       for all r: MC[j][j][r] =
                                             max(MC[j][j][r], MC_in[i][r])
                                       # 2. merge every belief row
                                       for all l, r: MC[j][l][r] =
                                             max(MC[j][l][r], MC_in[l][r])
                                       # 3. the receive is an event too
                                       MC[j][j][j] += 1
```

Step 1 is the one that matters: step 2 alone only updates what `j`
*believes about others* and never raises `j`'s own row, so `j` would
know an event existed while claiming not to have seen it itself.
Schwarz & Mattern's "clock matrix" and the matrix-shaped protocol in
Raynal, Schiper & Toueg's causal ordering both hinge on this
absorb-then-merge order. Conventions differ between papers (some merge
only the sender's row, some skip step 3), but all agree on the
invariant that makes the clock useful: **every entry is a lower bound
on true knowledge, and entries only grow** — so any "stable" verdict
the clock produces is safe.

## What Second-Order Knowledge Buys

### 1. Garbage collection: the stability test

A vector entry for a long-dead event can never be dropped on local
inspection alone: from its own vector, `i` cannot tell whether some
slow process still references version 7 of a key. The matrix closes
the loop. Version `v` of process `k`'s history is **stable at `i`**
when:

```text
min over j of MC[i][j][k]  >=  v
```

i.e. `i` knows that *every* process knows at least `v` of `k`'s
events. Once stable, no future comparison can depend on anything
older, so `i` may discard deltas, tombstones, and version chains below
`v` — and can *tell* `k` what it may drop. Chandy-Lamport
[snapshots](../advanced/distributed-snapshots.md) record the state;
matrix stability says when the pre-snapshot history can be reclaimed.

### 2. Consistent dumps without a global pause

A consistent dump of a multi-site database must not mix pre-update
and post-update records. With matrix clocks each site decides locally
when its slice is safe: the dump at `i` is consistent once `i`'s
latest knowledge is common knowledge (test 3), because no in-flight
update can then contradict what was copied. Schwarz & Mattern call
this the "who has to be asked" problem — the matrix answers it
without a blocking two-phase exchange.

### 3. Common-knowledge detection

The strongest statement a vector supports at `i` is "I have seen
`k`'s event." The matrix supports "I know that everyone has seen it" —
one `min` over a column — and inductively "`j` knows that `k` knows
that I have seen it." Mutual-exclusion release, lease handoff, and
"safe to delete the replicated lock record" are common-knowledge
questions in disguise. Termination detection is the canonical
instance: the system has terminated when, for all `(i, j)`,
`MC[i][j][j] ==` the true event count of `j` — everyone knows that
everyone has gone quiet.

### 4. Debugging and blame assignment

When an invariant breaks, the useful question is not "who saw what"
but "who *could have known*." A matrix snapshot at failure time
separates "the bug ran before any replica knew about the conflicting
write" (fix the protocol) from "replica 3 had second-hand proof in its
matrix and acted anyway" (fix the code).

### 5. Causal message ordering with less bookkeeping than it looks

The causal-ordering protocol of Raynal, Schiper & Toueg delays
delivery using a matrix of exactly this shape: deliver `m: i -> j`
only when `j`'s matrix shows `j` has seen everything `i` had seen at
send time — the vector's role in [causal broadcast](./crdts.md), plus
a second-order check that makes "delay until safe" decidable.

## The Overhead Ladder, Quantified

Integers piggybacked per message, by clock family:

| Clock | Piggyback | Compare | Merge on receive | Practical ceiling |
|-------|-----------|---------|------------------|-------------------|
| Scalar | 1 int | O(1) | max | any |
| Vector | N ints | O(N) | O(N) max | hundreds |
| Matrix | N² ints | O(N²) | O(N²) max | dozens |

When N² hurts there are three responses: **restrict the group**
(matrix clocks stay viable inside a Raft quorum or metadata ring while
the wide-area tier runs vectors or
[hybrid logical clocks](../advanced/hybrid-logical-clocks.md));
**compress the matrix** (most off-diagonal entries are dominated —
[interval tree clocks](../advanced/interval-tree-clocks.md) chase the
same redundancy one level down); or **lower the knowledge claim** (an
app needing only first-order knowledge should not pay for a statement
it never makes). A lower bound closes the ladder from below:
[Charron-Bost](https://doi.org/10.1016/0020-0190(91)90055-m) proved no
clock smaller than vectors can fully characterize happened-before —
matrices buy strictly more than vectors, and it cannot be bought for
less.

## Worked Demo: Stability, Common Knowledge, Termination

Four processes ring-gossip for three waves (each wave: every process
sends once, receives once). Watch what the matrix knows that the
vector does not:

```python
#!/usr/bin/env python3
"""Matrix clocks vs vector vs scalar on a 4-process ring, 3 gossip waves.

Receive rule (Schwarz & Mattern 1994), receiver j, sender i:
  1. absorb the sender's knowledge row:  MC[j][j][r] = max(MC[j][j][r], MC_in[i][r])
  2. merge every belief row elementwise: MC[j][l][r] = max(MC[j][l][r], MC_in[l][r])
  3. the receive is an event:            MC[j][j][j] += 1
"""
N = 4
NAMES = "ABCD"
WAVE = [("send", 0, 1), ("recv", 1, 0), ("send", 1, 2), ("recv", 2, 1),
        ("send", 2, 3), ("recv", 3, 2), ("send", 3, 0), ("recv", 0, 3)]

scalar = [0] * N
vector = [[0] * N for _ in range(N)]
matrix = [[[0] * N for _ in range(N)] for _ in range(N)]
boxes = [[] for _ in range(N)]          # FIFO channel buffers


def step(ev):
    i = ev[1]                            # sender on send, receiver on recv
    if ev[0] == "send":                  # tick, then ship a full matrix copy
        scalar[i] += 1; vector[i][i] += 1; matrix[i][i][i] += 1
        boxes[ev[2]].append([row[:] for row in matrix[i]])
    else:
        inc = boxes[i].pop(0)
        scalar[i] += 1
        vector[i] = [max(a, b) for a, b in zip(vector[i], inc[ev[2]])]
        vector[i][i] += 1
        for r in range(N):                                # rule 1
            matrix[i][i][r] = max(matrix[i][i][r], inc[ev[2]][r])
        for l in range(N):                                # rule 2
            for r in range(N):
                matrix[i][l][r] = max(matrix[i][l][r], inc[l][r])
        matrix[i][i][i] += 1                              # rule 3


def probe(tag):
    gc = [NAMES[k] for k in range(N) if all(matrix[0][j][k] >= vector[k][k] for j in range(N))]
    print(f"{tag}  A can GC latest versions of: {gc or 'none'}")


for w in (1, 2, 3):
    for ev in WAVE:
        step(ev)
    probe(f"after wave {w}:  A's vector={vector[0]}")

print("\nMatrix clock at A after wave 3 (row = whose knowledge, col = whose events):")
A = matrix[0]
print("       " + "".join(f"{c:>3}" for c in NAMES))
for l in range(N):
    print(f"   {NAMES[l]}   " + "".join(f"{A[l][r]:>3}" for r in range(N)))
print("   (row A is A's own knowledge == its vector clock)")

print("\nFinal per-process vectors:", {NAMES[i]: vector[i] for i in range(N)})

# Common knowledge at i: min_j MC[i][j][0] >= v -- a VECTOR can't answer this.
for v in (vector[0][0] - 1, vector[0][0]):
    ck = [NAMES[i] for i in range(N) if min(matrix[i][j][0] for j in range(N)) >= v]
    print(f"A's version {v} is common knowledge at: {ck or 'nobody'}")

lag = [(NAMES[i], NAMES[j], matrix[i][j][j], scalar[j])
       for i in range(N) for j in range(N) if matrix[i][j][j] != scalar[j]]
print(f"\nTermination check  all(i,j): MC[i][j][j] == SC[j]  ->  {not lag}")
print(f"witness of lag (i believes j has seen only x of y own events): {lag[:3]}")

print("\nPiggyback cost per message (ints):")
for n in (4, 50, 200):
    print(f"  N={n:>3}  scalar={1:<7} vector={n:<7} matrix={n * n:<7} "
          f"(matrix = {n}x vector, {n * n}x scalar)")
```

Real output:

```text
after wave 1:  A's vector=[2, 2, 2, 2]  A can GC latest versions of: ['B']
after wave 2:  A's vector=[4, 4, 4, 4]  A can GC latest versions of: ['B']
after wave 3:  A's vector=[6, 6, 6, 6]  A can GC latest versions of: ['B']

Matrix clock at A after wave 3 (row = whose knowledge, col = whose events):
         A  B  C  D
   A     6  6  6  6
   B     5  6  4  4
   C     5  6  6  4
   D     5  6  6  6
   (row A is A's own knowledge == its vector clock)

Final per-process vectors: {'A': [6, 6, 6, 6], 'B': [5, 6, 4, 4], 'C': [5, 6, 6, 4], 'D': [5, 6, 6, 6]}
A's version 5 is common knowledge at: ['A', 'D']
A's version 6 is common knowledge at: nobody

Termination check  all(i,j): MC[i][j][j] == SC[j]  ->  False
witness of lag (i believes j has seen only x of y own events): [('B', 'A', 5, 6), ('B', 'C', 4, 6), ('B', 'D', 4, 6)]

Piggyback cost per message (ints):
  N=  4  scalar=1       vector=4       matrix=16      (matrix = 4x vector, 16x scalar)
  N= 50  scalar=1       vector=50      matrix=2500    (matrix = 50x vector, 2500x scalar)
  N=200  scalar=1       vector=200     matrix=40000   (matrix = 200x vector, 40000x scalar)
```

Reading the numbers:

- **Only `B`'s versions become collectable.** `B` is quiescent after
  its wave-1 send, so knowledge of `B` catches up to `B`'s own count
  and stays there; `A`, `C`, `D` keep executing, so their latest
  versions never stabilize. Stability tracks *silence*, not recency.
- **Version 5 vs version 6.** `A`'s fifth event had three full waves
  of gossip behind it and is common knowledge at `A` and `D`; the
  sixth was the trace's final event, so nobody can yet know it
  exists, let alone that everyone knows. `B`'s *vector* `[5, 6, 4, 4]`
  says `B` saw it — and cannot say one word about who else has.
- **Termination stays undetectable here** — honest, not a bug; the
  witnesses (`B` believes `A` has seen only 5 of 6 own events) are
  exactly the entries a real detector waits on.
- **The cost line** is why this lives in research systems: at N=200
  the piggyback is 40,000 integers per message.

## When to Pay for N²

Scalar clocks order, vector clocks observe, matrix clocks certify.
Pay O(N²) only when some component must *act* on second-order
knowledge — garbage collection, checkpoint pruning, termination
detection, lease handoff — and fall back to vectors the moment the
group outgrows the budget.

## References

- Schwarz, R., Mattern, F. *Detecting Causal Relationships in Distributed Computations: In Search of the Holy Grail*. Distributed Computing 7(3), 1994 — the "clock matrix" paper; stability and GC semantics. https://doi.org/10.1007/bf02277859 (verified via Crossref)
- Raynal, M., Schiper, A., Toueg, S. *The Causal Ordering Abstraction and a Simple Way to Implement It*. Information Processing Letters 39(1), 1991 — matrix-shaped causal-delivery protocol. https://doi.org/10.1016/0020-0190(91)90008-6 (verified via Crossref)
- Fidge, C. *Logical Time in Distributed Computing Systems*. Computer 24(8), 1991 — the scalar→vector→matrix progression. https://doi.org/10.1109/2.84874 (verified via Crossref)
- Charron-Bost, B. *Concerning the Size of Logical Clocks in Distributed Systems*. Information Processing Letters 39(1), 1991 — lower bound: happened-before needs vector-sized state. https://doi.org/10.1016/0020-0190(91)90055-m (verified via Crossref)
- Mattern, F. *Virtual Time and Global States of Distributed Systems*. In: Parallel and Distributed Algorithms, North-Holland, 1989 — the global-state framework matrix clocks serve (workshop proceedings, no DOI).
- Raynal, M., Singhal, M. *Logical Time: Capturing Causality in Distributed Systems*. Computer 29(6), 1996 — survey of all three families, shared notation. https://doi.org/10.1109/2.485846 (verified via Crossref)

## Cross-References

- [Vector clocks](./vector-clocks.md) — the first-order base layer, incl. the Dynamo-style conflict demo not repeated here.
- [Lamport clocks](./lamport.md) — the O(1) scalar floor of the table.
- [Clocks & ordering survey](../advanced/clocks-ordering.md) — matrix clocks among dotted version vectors and ITCs.
- [Distributed snapshots](../advanced/distributed-snapshots.md) — Chandy-Lamport cuts that matrix stability later prunes.
- [Interval tree clocks](../advanced/interval-tree-clocks.md) — compression for the same scalability pressure.
