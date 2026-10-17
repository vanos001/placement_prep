# Follow-up Tree: Quicksort and Partitioning

## Overview

"How does quicksort work?" looks like the friendliest opener in the algorithms interview, and it is precisely because of that friendliness that it escalates so well. The textbook answer takes thirty seconds; each rung after it — partition scheme, worst case, duplicates, guards, stack depth, parallelism — probes a different layer of the same ten lines of code. This page walks the ladder rung by rung: for each follow-up, what it tests, how to reason through it, and the answer with its edge cases. The comparison page [Sorting Algorithms Compared](../why-not-handbook/sorting-algorithms.md) covers when to pick quicksort at all; here we assume quicksort was picked and drill into what happens inside it.

## The Opening Question

**"How does quicksort work?"**

The expected core answer: quicksort is a divide-and-conquer sort. Pick a *pivot* element, *partition* the array so that everything less than the pivot precedes it and everything greater follows it, then recursively sort the two sides. Nothing is "merged" afterward — unlike merge sort, all the work happens before the recursion, inside the partition step.

Why this answer is correct: it states the invariant that carries the whole algorithm — after partitioning, the pivot is in its final sorted position and never moves again. Every rung of the ladder is a variation on that invariant. It also names the performance contract honestly: **O(n log n) on average, O(n²) in the worst case, in-place (O(log n) stack), not stable**. Stating worst and average together, unprompted, is the sentence that invites the interviewer to climb instead of ambush — the distinction between the two cases is exactly what the next rungs are about. The mechanics and proofs live in [Sorting](../../dsa/chapters/ch05-sorting.md) and [Complexity Analysis](../../dsa/chapters/ch03-complexity-analysis.md); the chain here is about *why* each rung exists.

## Follow-up 1: Lomuto or Hoare — Does the Partition Scheme Matter?

**What it tests:** whether "quicksort" is one algorithm or a family, and whether you know the two partition schemes well enough to predict their behavior on hostile inputs.

**How to reason:** compare the schemes on four axes — where the pivot sits, how many swaps, behavior on equal keys, and what the recursion splits on.

**Answer.** *Lomuto* partition walks one scan index through the array with the pivot at the end, maintaining the boundary `i` of the "≤ pivot" region: when the scan sees an element ≤ pivot it swaps it to the boundary and advances it. It is simple, does exactly one pass, and puts the pivot in its exact final slot — but it performs a swap on *every* element that is ≤ pivot, and with all-equal keys the boundary swallows the whole array: each partition splits into (n−1, 0), giving O(n²) comparisons *and* swaps on input that is already perfectly uniform.

*Hoare* partition starts two pointers at the ends and moves them inward until each is stopped by an element that belongs on the other side (strictly less / strictly greater), then swaps them; it returns a *split point* where the left side is ≤ pivot and the right side is ≥ pivot — the pivot itself is **not** in its final position, so the recursion is `[lo..j]` and `[j+1..hi]`, not around the pivot. Two consequences matter at interviews: on all-equal keys the pointers stop on every element and cross near the middle, so the split stays balanced and the comparisons stay O(n log n) (with many useless swaps, which [Bentley & McIlroy, "Engineering a Sort Function", 1993] engineered away); and getting the loop conditions wrong with a pivot taken from the wrong end causes an infinite loop or an O(n) thrash on two-element inputs — the classic implementation bug.

| Axis | Lomuto | Hoare |
|---|---|---|
| Pivot placement | Ends in final sorted position | Split point only; pivot may move later |
| Swaps on random data | More (swap per ≤ pivot element) | Fewer (~3× fewer per Bentley–McIlroy) |
| All-equal keys | Splits (n−1, 0) → O(n²) | Splits ~in half → O(n log n) comparisons |
| Simplicity | Trivial to write correctly | Off-by-one traps; loop conditions subtle |
| Typical use | Teaching, small scripts | Production library cores |

The interview signal is the last row inverted: production libraries build on the *harder* scheme precisely because the easy one has the pathological duplicate behavior the next rung explores.

## Follow-up 2: When Is It O(n²), and Who Can Force It?

**What it tests:** the adversariality axis — whether you know the worst case is not just "bad luck" but something inputs, including ordinary ones, can force.

**How to reason:** the recurrence is T(n) = T(k) + T(n−1−k) + O(n). Ask what values of k make that quadratic, then ask what inputs produce those k values.

**Answer.** The worst case needs maximally unbalanced splits. Three ordinary ways to get them:

1. **Sorted (or reverse-sorted) input with a naive pivot.** First- or last-element pivots on sorted input split (n−1, 0) every time. Comparisons sum to n−1 + n−2 + … + 1 = n(n−1)/2 — about **5×10⁹ comparisons at n = 100,000**, versus roughly n·log₂n ≈ 1.7×10⁶ for balanced splits. Nearly-sorted data is not exotic: it is what you get appending to an already-sorted log or re-sorting a mostly-ordered feed. Median-of-three pivot selection kills this particular case but not the next one.
2. **All-equal keys under Lomuto.** Follow-up 1's result: duplicates are the quiet killer, and real workloads have duplicates.
3. **An adversarial input.** If the pivot is chosen as a function of element *values* only (median-of-three included), [McIlroy, "A Killer Adversary for Quicksort", 1999] constructs inputs that force O(n²) *by reordering comparisons adaptively* — the adversary answers each comparison in whatever way keeps the pivot worst, and no value-based pivot rule escapes. This is why libraries either randomize (making worst-case inputs data-independent, a probabilistic rather than absolute guarantee) or add the structural guards of Follow-up 4. The deeper lesson — the average case is a claim about a distribution, and someone can choose the inputs — is the theme of [Average vs Worst Case](../misconceptions/average-case-complexity.md) and [Complexity Claims Under Input Control](../assumptions-hunt/complexity-claims.md).

One more edge case that is not about comparisons: the worst case also maximizes **recursion depth**. Naive recursion on both sides needs O(n) stack — a stack overflow, not just slowness. The fix is structural and belongs in the next rung.

## Follow-up 3: The Input Is Mostly Duplicates — Now What?

**What it tests:** whether you reach for a structural fix (a different partition invariant) instead of a knob (a different pivot rule) when the failure is caused by the invariant itself.

**How to reason:** the problem is that equal elements carry no ordering information, yet two-way partitioning forces each of them into a side. Ask what partition would let them stay together.

**Answer.** **Three-way partitioning** (Dijkstra's Dutch national flag): one pass maintains *three* regions — less than pivot, equal to pivot, greater than pivot — and the recursion excludes the middle region entirely. Two consequences: all-equal input completes in a single O(n) pass with zero recursion, and inputs with a heavy duplicate distribution drop from O(n log n) toward O(n·H) where H is the entropy of the key distribution. Bentley and McIlroy's engineering version keeps equal-to-pivot elements at both ends during the scan and swaps them into the middle afterward, achieving the same effect with fewer data moves on random data.

The generalizable move — and why interviewers love this rung — is that the *invariant* changed, not the constants. Pivot randomization redistributes the damage; three-way partitioning removes the failure mode by giving equal keys a home. When an interview twist says "the array has 10 distinct values, a billion elements," the answer is a partition with 10 regions or a keyed sort — not a faster comparison sort. (The extreme version, counting the keys instead of comparing them, is the counting sort idea; see [Divide and Conquer](../../dsa/chapters/ch39-divide-conquer.md) for where comparison sorts sit among their alternatives.)

## Follow-up 4: Production Sorts Are Not Bare Quicksort — What Do They Add?

**What it tests:** whether you know the name and mechanism of the standard safety net, which is the difference between "textbook quicksort" and `std::sort`.

**How to reason:** list the failure modes from rungs 1–3, then name the guard for each, then the guaranteed complexity after guarding.

**Answer.** The standard construction is **introsort** (Musser, "Introspective Sorting and Selection Algorithms", 1997): run quicksort, but *track the recursion depth*; if it exceeds ~2·log₂n, conclude that this input is fighting you and switch that subproblem to heapsort. Heapsort's O(n log n) worst case caps the entire algorithm: introsort is **O(n log n) worst case** while keeping quicksort's cache-friendly speed on the common path. This is what libstdc++'s and MSVC's `std::sort` do. Around the core, production sorts add: a final insertion-sort pass over small partitions (typically ≤ 16 elements, where insertion sort's constant factors win); median-of-three (or ninther) pivots to make bad splits rare; and — in modern libraries — pattern detection. pdqsort ("pattern-defeating quicksort") detects already-sorted, reverse-sorted, and heavy-duplicate prefixes and routes around them, which is why it early-exits on sorted input; the repo's [pdqsort](../../dsa/advanced/pdqsort.md) page covers its block partitioning. Java takes a related but distinct path: primitives sort with a dual-pivot quicksort (Yaroslavskiy, 2009 — two pivots, three regions, fewer data moves in practice), while objects sort with TimSort because *stability is required for objects* — quicksort's instability is acceptable only for values where you cannot observe the swap order.

Complexity claims, stated precisely: introsort is O(n log n) worst case, O(n log n) average, O(log n) stack; unguarded quicksort is O(n²) worst case and O(n log n) *expected* under random pivots — "average" there is a distribution claim, not a promise, which is the exact boundary [Adversarial Input](../assumptions-hunt/input-constraints.md) draws.

## Follow-up 5: How Do You Keep the Stack at O(log n) — and Is That Tail-Call Elimination?

**What it tests:** whether you can bound a real implementation's memory, and whether you conflate a compiler feature with a coding discipline.

**How to reason:** the stack is proportional to the depth of the recursion *you actually perform*. Ask which side must recurse and which can be a loop.

**Answer.** Always recurse on the **smaller** partition and loop on the larger one. The larger side's work continues in the same frame, so every stack frame corresponds to a side of size ≤ n/2, and depth is bounded by log₂n **even in the worst case** — this is a guarantee you build into the control flow, not a hope about the compiler. (Tail-call elimination, where a compiler rewrites a tail call into a jump, is neither necessary nor sufficient here: quicksort's second recursive call is not in tail position unless you restructure it — which is exactly what recurse-smaller-then-iterate does by hand. Saying "the compiler will TCO it" in an interview is the tell that someone has not written the loop version.) Insertion-sort cutoffs shrink the effective depth further, and the stack bound is why introsort implementations can promise O(log n) auxiliary space alongside the O(n log n) time.

The mirror-image mistake to volunteer: implementing the *iteration* on the larger side as a recursive call too costs nothing asymptotically in expectation but forfeits the worst-case stack bound — and a stack overflow in production is a crash, not a slowdown.

## Follow-up 6: Can You Parallelize It?

**What it tests:** whether the divide-and-conquer structure can be parallelized honestly — and whether you can spot the serial bottleneck in an algorithm everyone calls "parallel-friendly."

**How to reason:** draw the computation DAG. The two recursive halves are independent, but what sits *above* them?

**Answer.** The partition of the full array is an inherently sequential bottleneck at the root: until it finishes, no subproblem exists to hand out, and its cost is Θ(n) of the Θ(n log n) total. That bounds achievable speedup far below ncores for large n — the same shape as Amdahl's law, arriving from the algorithm's structure rather than a profiler. Two honest ways out, both covered in [Parallel Sorting](../../dsa/advanced/parallel-sorting.md): (1) **parallelize the partition itself** by reformulating it as a rank computation — each element's destination is computable via prefix sums, at the cost of extra passes that only pay at large scale; (2) **change the algorithm's shape** — samplesort picks many splitters first so the data falls into p independent buckets with no global partition, and parallel merge sort parallelizes both halves and the merge. The real question is whether you notice that "recursion is independent" is not the same as "the critical path is short": work-stealing over the recursion tree is easy and helps, but the root partition stays serial, and saying so out loud is the seniority signal. Why quicksort still beats equally-asymptotic sorts *serially* — sequential access and branch predictability versus heapsort's strided hops — is [Big-O Is Not Speed](../misconceptions/big-o-is-speed.md).

## How to Approach Unfamiliar Variations

The transferable template for "improve this sort" and its relatives:

1. **Ask what the workload looks like before touching the algorithm.** Size, sortedness, duplicate distribution, key range, stability requirement, memory budget, and *who controls the input*. "Mostly sorted with a long tail of duplicates" and "adversarially chosen keys" are different problems, and each names its own fix (early-exit detection vs. introsort fallback; three-way partition vs. randomized pivots).
2. **Distinguish pivot rules from partition invariants.** Pivot rules shift *probability*; partition schemes change the *failure modes*. If the pathology comes from the invariant (duplicates in two-way partitioning), only a new invariant fixes it.
3. **Name the cost model.** Comparisons, swaps, cache misses, branch misses, and parallel critical path are different currencies. Library sorts win by paying in the cheap currencies; a complexity-class argument that ignores the cost model (see [Big-O Is Not Speed](../misconceptions/big-o-is-speed.md)) is incomplete.
4. **Every guard is a fallback to a different algorithm.** Introsort = quicksort + heapsort fallback + insertion finish; pdqsort = the same shape with pattern detection. When asked to "improve" anything, a good answer has the form: fast common path, detected trigger, guaranteed fallback — and states the worst-case complexity *after* the fallback.

## Interview Questions

**Q: Why do production libraries still use quicksort variants when heapsort is O(n log n) guaranteed?**
A: Constant factors and memory behavior: quicksort's partition scans are sequential and predictable, heapsort's sift-downs jump across the array. Introsort gets both — quicksort speed on the common path, heapsort as a depth-triggered fallback that caps the worst case at O(n log n).

**Q: Your service sorts mostly-sorted timestamps and sometimes stalls badly. Hypothesis?**
A: A naive-pivot (first/last element) quicksort on nearly-sorted data hitting near-worst-case splits. Fixes in order of robustness: switch to a library introsort/pdqsort; if stuck with a hand-rolled sort, median-of-three plus a recursion-depth fallback. The diagnosis predicts the stall correlates with data order, not data size.

**Q: An interviewer asks you to sort a billion 32-bit integers in memory. Does quicksort still win?**
A: Probably not — the key range is small enough that non-comparison sorts (radix/counting) do O(n) passes with no comparison adversary, and 32-bit keys make bucket arrays cheap. The comparison-sort ladder is the wrong ladder once the cost model changes from "comparisons" to "passes over data."

**Q: Is three-way partitioning ever worse than two-way?**
A: On duplicate-free data it does slightly more bookkeeping (tracking a third boundary) for the same asymptotics, which is why it is often switched on adaptively — libraries detect duplicate-heavy prefixes and switch schemes mid-sort. Stating that trade (constant-factor overhead vs. removed failure mode) is the full answer.

## Key Takeaways

- Quicksort is a *family*: pivot rule × partition scheme × guards. Every performance claim you make should specify all three.
- Lomuto is simple and quadratic on equal keys; Hoare balances duplicates but does not place the pivot; three-way partitioning removes the duplicate failure mode by changing the invariant.
- The O(n²) worst case is reachable from ordinary data (sorted, all-equal) and from adversaries (McIlroy) against any value-based pivot rule; guards — depth-triggered heapsort fallback, randomization — turn it into a bounded worst case.
- Recurse on the smaller side and iterate on the larger: an O(log n) stack by construction, not by compiler tail-call optimization.
- Parallel quicksort's root partition is a serial bottleneck; real parallel sorts either parallelize the partition (prefix ranks) or change shape (samplesort, parallel merge).

## Cross-References

- [Sorting](../../dsa/chapters/ch05-sorting.md) — the full algorithm zoo: quicksort, merge, heap, and the proofs behind each complexity claim.
- [Sorting Algorithms Compared](../why-not-handbook/sorting-algorithms.md) — the why-not decision framework for choosing among them.
- [Divide and Conquer](../../dsa/chapters/ch39-divide-conquer.md) — the recurrence structure this chain's worst-case analysis rides on.
- [Complexity Analysis](../../dsa/chapters/ch03-complexity-analysis.md) — worst, average, and amortized, derived properly.
- [pdqsort](../../dsa/advanced/pdqsort.md) — pattern-defeating quicksort: block partitioning and pattern detection internals.
- [Parallel Sorting](../../dsa/advanced/parallel-sorting.md) — samplesort, parallel merge, and the critical-path analysis of Follow-up 6.
- [Average vs Worst Case](../misconceptions/average-case-complexity.md) — the misconception this chain's rung 2 is built to expose.
- [Big-O Is Not Speed](../misconceptions/big-o-is-speed.md) — why equal asymptotics still lose by constants and memory behavior.
- [Complexity Claims Under Input Control](../assumptions-hunt/complexity-claims.md) — who chooses the inputs, and which claims survive that.
- [Adversarial Input](../assumptions-hunt/input-constraints.md) — hash flooding's identical structure: average case as a distribution claim.
