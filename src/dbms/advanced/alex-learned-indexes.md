# ALEX: Updatable Learned Indexes with Gapped Arrays

ALEX (Adaptive Learned indEX, Ding et al., SIGMOD 2020) is the write-optimized
follow-up to the read-only learned index from
[Learned Indexes](./learned-indexes.md). RMI showed that a regression model
can replace a B+ tree traversal, but its error bound holds only for the key
set it was trained on: one insert can push lookups outside it. ALEX keeps the
model-as-index idea and adds a storage layout that absorbs updates in place,
plus a cost model that decides when in-place repair costs more than
retraining. The official implementation is a header-only C++14 library
pitched as a near drop-in `std::map` replacement
([microsoft/ALEX](https://github.com/microsoft/ALEX)).

## Recap: The Recursive Model Index

RMI (Kraska et al., SIGMOD 2018, DOI 10.1145/3183713.3196909) models the
index as the CDF: for sorted keys, the position of key K is roughly CDF(K)
times the array length. A two-level RMI has a top model mapping K to one of
M sub-models, each a regression predicting the final slot. Predictions are
inexact, so each sub-model stores error bounds `[min_err, max_err]` and the
lookup ends with a bounded binary search over that window. On static
in-memory workloads this beats a B+ tree on latency and memory. The weak
spot is updates: the bounds are fixed at training time, and inserts shift
positions enough to push lookups outside them.
[Learned Indexes](./learned-indexes.md) has the full derivation, the hybrid
designs, and the follow-up skepticism.

## What ALEX Changes

Four load-bearing ideas, on top of the two-level model structure:

1. **Gapped array leaves** - keys live in a slot array with holes between
   them, so an insert shifts a few neighbors instead of rewriting a page.
2. **Model-based insertion** - the lookup model also serves inserts: jump to
   the predicted slot, expand an exponential search window (steps of 1, 2,
   4, 8) until occupied slots bracket the key, then probe inside the bracket.
3. **Shift-vs-expand strategy** - each insert either shifts keys in place or
   expands: retrain the node's model and rebuild its gapped array with fresh
   gaps (in the full system, split the node in two).
4. **A cost model** - ALEX prices expected search cost (model error) against
   expected insert cost (shift distance) and picks the cheaper action per
   node, adapting to the workload instead of fixed thresholds.

### Gapped Array Leaves

A gapped array is a sorted array with unused slots interleaved between keys.
The layout trades memory for update locality: a hole next to the insertion
point makes an insert free; no nearby hole means shifting the shorter run of
adjacent keys one slot each until a hole absorbs the move. In the ALEX paper
gaps between consecutive keys grow exponentially with their distance
(exponents kept in a compact bitmap), keeping hot insert regions sparse
without doubling memory everywhere. The knob is the load factor (occupied /
capacity): low means cheap shifts and wasted memory, high means compact but
shift-heavy.

### Shift vs Expand

| Strategy | What happens | Cost driver | Chosen when |
| --- | --- | --- | --- |
| In-place shift | Move the shorter neighbor run one slot toward the nearest hole | Shift distance | Hole nearby, model error low |
| Expand and retrain | Re-split the node: retrain models, redistribute keys into fresh gapped arrays | Node rebuild | High load factor or shift over budget |

The two failure modes pull in opposite directions: shifting too long wastes
CPU on insert-heavy workloads, expanding too eagerly burns memory on
read-heavy ones. The cost model prices both sides, so a workload that turns
insert-heavy drifts toward expansions without config changes.

## Bulk Loading

Building ALEX over a sorted batch mirrors training an RMI, then adds layout:

1. Fit the two-level model structure on the sorted keys, choosing segment
   boundaries that keep per-segment error small (greedy, bottom-up).
2. Allocate each leaf's gapped array at the target load factor and scatter
   the keys into its slots.
3. Train each leaf model on the final (key, slot) pairs - training after
   placement is what makes predictions point at real slots.

## Mechanics: Lookup, Insert, Delete

```text
Gapped array leaf node: 9 slots, 8 keys, load factor 8/9 = 0.89
model: slot = m * key + b   (trained on occupied slots)

  slot:    0     1     2     3     4     5     6     7     8
        +-----+-----+-----+-----+-----+-----+-----+-----+-----+
        | 112 | 130 | 141 | 155 | 166 | 190 | 201 |     | 224 |
        +-----+-----+-----+-----+-----+-----+-----+-----+-----+
  lookup(166): model -> slot 4; occupied, holds 166: hit
  lookup(170): model -> slot 5, holds 190 > 170; window 5 +/- 1 stops
               at 166 (slot 4) and 190 (slot 5); scan: no 170: miss
  insert(150): model -> slot 3; run 0..2 has no hole, nearest hole is
               slot 7; shift 155, 166, 190, 201 right one slot each;
               write 150 at slot 3. Shift distance: 4 keys moved.
  insert(210): model -> slot 7, a hole: drop straight in, zero shifts
```

- **Lookup**: model prediction, exponential window, bounded scan - RMI's
  three steps, except the window tolerates holes.
- **Insert**: as in the diagram; if the cheaper shift exceeds the node's
  shift budget, or no hole exists on either side, the node expands instead.
- **Delete**: clear the slot, decrement the key count - no tombstone, no
  shifting; the freed hole serves later inserts.
- **Range scan**: occupied slots are ordered, so the scan walks them left to
  right; sibling pointers continue it across leaves.

## Reported Results

From the paper abstract (arXiv:1905.08898, verified wording):

| Comparison | Workload | Verified claim |
| --- | --- | --- |
| ALEX vs B+Tree | read-write mix | beats B+Tree by up to 4.1x, never worse, up to 2,000x smaller index size |
| ALEX vs RMI (Kraska) | read-only | up to 2.2x throughput, up to 15x smaller index size |

Two cautions when quoting these. The memory claim is *index size*, not
end-to-end database footprint. And the baselines are an optimized in-memory
B+ tree and the original RMI, with integer-like keys - the regime
[Advanced Index Structures](./index-advanced.md) calls learned indexes' home
turf, not a general verdict on B+ trees (see
[B-Trees and Database Indexing](../../dsa/chapters/ch77-btrees.md) for what
the disk-resident baseline does).

## Limitations

- **Out-of-distribution keys.** Models extrapolate badly: keys far outside
  the training range land far from their predicted slot, the search window
  grows, and tail latency approaches linear scan until the node expands and
  retrains. String and compound keys need a numeric encoding first, which
  weakens the CDF-model assumption further. The demo below shows the drift.
- **Non-monotone inserts.** Random-order inserts exhaust holes around the
  middle of nodes; append-only keys are the easy case and rarely shift.
- **Gap overhead.** Holes are dead space by design; the load factor is a
  standing tax, and expansions briefly need room for old and new arrays.
- **Concurrency.** The paper's design is single-threaded; multicore scaling
  is its own problem - XIndex (Tang et al., PPoPP 2020) is the standard
  follow-up. PGM-index, the compressed static alternative, is covered in
  [Learned Indexes](./learned-indexes.md). Where the index sits relative to
  scans and vectorized operators:
  [Advanced Execution Engines](./execution-engines.md).

## Demo: A Mini Gapped Array with Model-Based Inserts

A single-node, stdlib-only sketch of the mechanics above: least-squares
linear model, bulk load at ~50% density, model-based inserts with a shift
budget, expanding re-splits when shifting stops being cheap. `drift()` is
the max distance between predicted and actual slot - what ALEX's cost model
reacts to.

```python
# Mini ALEX-style gapped array leaf: linear model + model-based inserts.
import random


class GappedNode:
    def __init__(self, keys, slots_per_key=2):  # bulk load
        keys = sorted(keys)
        self.num_slots = max(len(keys) * slots_per_key + 1, 8)
        self.slots = [None] * self.num_slots
        for i, k in enumerate(keys):
            self.slots[i * slots_per_key] = k
        self.num_keys = len(keys)
        self._train()

    def _train(self):                           # least-squares fit
        pts = [(k, i) for i, k in enumerate(self.slots) if k is not None]
        mk = sum(k for k, _ in pts) / len(pts)
        ms = sum(s for _, s in pts) / len(pts)
        var = sum((k - mk) ** 2 for k, _ in pts)
        cov = sum((k - mk) * (s - ms) for k, s in pts)
        self.slope = cov / var if var else 0.0
        self.intercept = ms - self.slope * mk

    def predict(self, key):                     # model-based jump
        p = int(self.slope * key + self.intercept)
        return min(max(p, 0), self.num_slots - 1)

    def drift(self):    # max |predicted - actual| slot = staleness
        return max(abs(self.slope * k + self.intercept - i)
                   for i, k in enumerate(self.slots) if k is not None)

    def locate(self, key):  # exponential window (1,2,4,..) around model
        p = self.predict(key)
        step, lo = 1, p
        while lo > 0 and (self.slots[lo] is None or self.slots[lo] > key):
            lo = max(p - step, 0)
            step *= 2
        step, hi = 1, p
        while hi < self.num_slots - 1 and \
                (self.slots[hi] is None or self.slots[hi] < key):
            hi = min(p + step, self.num_slots - 1)
            step *= 2
        i = lo
        while i <= hi and (self.slots[i] is None or self.slots[i] < key):
            i += 1
        return i if i <= hi else hi + 1

    def insert(self, key, budget):  # model jump, shift cheaper run
        i = self.locate(key)
        if i < self.num_slots and self.slots[i] == key:
            return 0, False                     # duplicate
        if i < self.num_slots and self.slots[i] is None:
            self.slots[i] = key                 # hole: zero shifts
            self.num_keys += 1
            return 0, False
        lfree = next((j for j in range(i - 1, -1, -1)
                      if self.slots[j] is None), None)
        rfree = next((j for j in range(i + 1, self.num_slots)
                      if self.slots[j] is None), None)
        if lfree is None and rfree is None:
            return 0, self.expand(key)          # no hole anywhere
        cl = sum(self.slots[j] is not None
                 for j in range(lfree + 1, i)) if lfree is not None else None
        cr = sum(self.slots[j] is not None
                 for j in range(i, rfree)) if rfree is not None else None
        left = rfree is None or (lfree is not None and cl <= cr)
        shift = cl if left else cr
        if shift > budget:
            return 0, self.expand(key)          # cheaper to expand
        if left:                                # move left run left
            for j in range(lfree, i - 1):
                self.slots[j] = self.slots[j + 1]
            self.slots[i - 1] = key
        else:                                   # move right run right
            for j in range(rfree, i, -1):
                self.slots[j] = self.slots[j - 1]
            self.slots[i] = key
        self.num_keys += 1
        return shift, False

    def expand(self, key):  # expanding re-split: retrain + rebuild
        keys = sorted([k for k in self.slots if k is not None] + [key])
        self.num_slots = len(keys) * 2 + 1
        self.slots = [None] * self.num_slots
        for i, k in enumerate(keys):
            self.slots[i * 2] = k
        self.num_keys = len(keys)
        self._train()
        return True


def main():
    random.seed(42)
    node = GappedNode(random.sample(range(10_000, 20_000), 64))
    print("=== after bulk load (64 keys, 2 slots/key) ===")
    print("slots: %d  keys: %d  load factor: %.3f" %
          (node.num_slots, node.num_keys, node.num_keys / node.num_slots))
    print("model drift, max |predicted - actual| slot: %.1f" % node.drift())
    total, peak, moves, splits = 0, 0, 0, 0
    for k in random.sample(range(0, 30_000), 300):  # non-monotone inserts
        s, expanded = node.insert(k, budget=8)
        if expanded:
            splits += 1
        else:
            total += s
            peak = max(peak, s)
            moves += 1
    print("\n=== after 300 random inserts (shift budget 8) ===")
    print("slots: %d  keys: %d  load factor: %.3f" %
          (node.num_slots, node.num_keys, node.num_keys / node.num_slots))
    print("model drift, max |predicted - actual| slot: %.1f" % node.drift())
    print("in-place inserts: %d  expanding re-splits: %d" % (moves, splits))
    print("shift distance: avg %.2f slots, max %d" % (total / moves, peak))
    keys = sorted(k for k in node.slots if k is not None)
    assert keys == sorted(keys) and \
        all(node.locate(k) < node.num_slots and
            node.slots[node.locate(k)] == k for k in keys)
    print("post-check: %d/%d lookups hit, slots sorted: True" %
          (len(keys), len(keys)))


if __name__ == "__main__":
    main()
```

Real output (Python 3, seed 42; executed twice, diffed - identical):

```text
=== after bulk load (64 keys, 2 slots/key) ===
slots: 129  keys: 64  load factor: 0.496
model drift, max |predicted - actual| slot: 9.5

=== after 300 random inserts (shift budget 8) ===
slots: 657  keys: 363  load factor: 0.553
model drift, max |predicted - actual| slot: 40.9
in-place inserts: 294  expanding re-splits: 6
shift distance: avg 0.67 slots, max 7
post-check: 363/363 lookups hit, slots sorted: True
```

Reading the numbers: random inserts land out of training order, so drift
grows from 9.5 to 40.9 slots between re-splits. Six of the 300 inserts hit
the expand path once shifts got too expensive (294 in-place, one of them an
ignored duplicate: 64 + 293 + 6 = 363 stored keys), while the average
in-place insert moved well under one key. Keep inserts cheap by shifting;
pay for accumulated drift in occasional retrain-and-rebuild bursts.

## References

- Ding et al., [ALEX: An Updatable Adaptive Learned Index](https://doi.org/10.1145/3318464.3389711) (SIGMOD 2020; DOI verified via Crossref)
- Ding et al., [ALEX preprint, arXiv:1905.08898](https://arxiv.org/abs/1905.08898) (source of the quoted performance claims)
- Kraska et al., [The Case for Learned Index Structures](https://doi.org/10.1145/3183713.3196909) (SIGMOD 2018; DOI verified via Crossref)
- [microsoft/ALEX](https://github.com/microsoft/ALEX) (official C++ implementation; README links the paper PDF)
- Tang et al., [XIndex](https://doi.org/10.1145/3332466.3374547) (PPoPP 2020, concurrent learned index; DOI verified via Crossref)
- [Open Data Structures](https://opendatastructures.org/) (free textbook covering B-trees and external-memory searching)
