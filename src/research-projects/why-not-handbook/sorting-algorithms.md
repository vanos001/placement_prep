# Sorting Algorithms: QuickSort vs MergeSort vs HeapSort vs Timsort/pdqsort vs Radix

## Overview

Every serious sorting algorithm is n log n in the average case, so the interesting question is never the exponent — it is what the algorithm does in the worst case, what it does to your memory bus, whether it preserves the order of equal keys, and what happens when the input is *almost* sorted already (which is what real data usually is). Production libraries do not ship textbook quicksort, mergesort, or heapsort: C++'s `std::sort` is introsort (a guarded quicksort hybrid), Python and Java ship Timsort for objects, Rust ships pdqsort, and Java uses dual-pivot quicksort for primitives. Understanding *why* each hybrid exists — and when the non-hybrid "loser" is the right pick — is the actual interview test.

This page applies the [handbook framework](./index.md) to five families: quicksort, mergesort, heapsort, the adaptive hybrids (Timsort, pdqsort), and the non-comparison sorts (counting, radix).

## The Lower Bound and Why It Matters

Comparison sorting requires Ω(n log n) comparisons in the worst case: any comparison sort is a decision tree with n! leaves, and a binary tree with n! leaves has height Ω(log(n!)) ≈ Ω(n log n) (CLRS, Chapter 8.1). Two consequences drive everything else on this page. First, no comparison sort can beat n log n worst-case, so the differentiators must be constants, memory, stability, adaptivity, and worst-case behavior. Second, the bound is *for comparison sorts* — counting and radix sort never compare keys, they index by key digits, so they can run in O(n + k) or O(n·w) and legitimately beat n log n when their preconditions hold. "Comparison sorts are optimal" is true only inside that family; the family boundary is the first thing to check.

## Mechanisms

| Family | Core mechanism | Best | Average | Worst | Extra memory | Stable? | Adaptive? |
|--------|----------------|------|---------|-------|--------------|---------|-----------|
| QuickSort (Hoare, 1962) | Partition around a pivot; recurse on sides | O(n log n) | O(n log n) | O(n²) | O(log n) stack (avg) | No (typical) | Slightly (via pivot choice) |
| MergeSort | Split, sort halves, merge two sorted runs | O(n log n) | O(n log n) | O(n log n) | O(n) buffer | **Yes** | No (classic) |
| HeapSort | Build max-heap; repeatedly extract max into the tail | O(n log n) | O(n log n) | O(n log n) | O(1) | No | No |
| Timsort (Peters, CPython) | Find/collapse natural runs; merge with galloping | O(n) | O(n log n) | O(n log n) | O(n) | **Yes** | **Strong** |
| pdqsort (Orson Peters) | Pattern-defeating quicksort: introsort guard + block partitioning + insertion finish | O(n) | O(n log n) | O(n log n) | O(log n) | No | **Yes** |
| Counting / radix | Histogram buckets / digit-wise stable passes | O(n + k) | O(n + k) | O(n + k) | O(n + k) | Yes (LSD radix) | No |

Mechanism details that explain the columns:

- **Quicksort** is in-place, cache-friendly, and branch-light in its inner partition loop, which is why it dominates benchmarks on random data. Its worst case is structural: bad pivots (first element on sorted input, all-equal keys without 3-way partitioning) split 0/n−1, giving quadratic time — and with naive recursion, O(n) stack depth, i.e., a stack overflow. Median-of-three pivoting, 3-way partitioning for duplicate-heavy inputs (Bentley & McIlroy, 1993), and recursing on the smaller side first are the standard armor — but none of them is a guarantee, which is why introsort exists.
- **Mergesort** divides cleanly and merges linearly, so its worst case *is* its average case: guaranteed n log n with perfect access patterns (sequential reads, sequential writes). The price is an O(n) auxiliary buffer and, for linked-data or disk workloads, that price is usually worth it — external sorting is mergesort's territory because sequential runs are exactly what disks and tapes like.
- **Heapsort** sifts values between the ends of an implicit binary tree laid over the array: parent at i, children at 2i and 2i+1. Every sift-down jumps indices by powers of two, so each access lands on a different cache line and the hardware prefetcher cannot help. It achieves O(1) memory and a hard n log n worst case by spending cache locality — heapsort is the textbook demonstration that two O(n log n) algorithms can differ by a large constant in opposite directions depending on the hardware.
- **Timsort** exploits the fact that real data has pre-sorted runs. It scans for natural ascending/descending runs (reversing descents), extends short ones to a minimum run length with binary insertion sort, then merges runs with a stack of invariants and "galloping" mode that exponentiates into the longer run when one side keeps winning. On fully sorted or reversed input it is O(n); on random input it is mergesort with mild overhead. Stability is preserved by careful merge ordering — a hard requirement for sorting objects by multiple keys.
- **pdqsort** is what happens when you fix quicksort's worst cases *and* add adaptivity: introsort-style recursion-depth guard falls back to heapsort, a partition-quality check detects degenerate patterns and breaks them with a random pivot, block-partitioning removes most branches from the partition loop, and already-sorted partitions trigger an O(n) best case with partial insertion sort. It is in-place and unstable, making it the default "unstable sort" in Rust's standard library and a popular C++ replacement (see [pdqsort deep dive](../../dsa/advanced/pdqsort.md) and the [orlp/pdqsort](https://github.com/orlp/pdqsort) repository).

## Why Introsort Exists

Musser's introsort ("Introspective Sorting and Selection Algorithms", 1997) is the canonical answer to "quicksort is fastest, so why not use it?". Its insight: quicksort's O(n²) worst case is detectable *from inside the algorithm*. Track recursion depth; if it exceeds 2·log₂(n) — impossible for a healthy partition split — stop recursing and run heapsort on that subrange, converting the quadratic blowup into a guaranteed n log n with negligible overhead on good inputs. Add insertion sort for small subarrays (below ~16–24 elements, constant-factor sorting is dominated by call overhead and insertion sort wins) and you get `std::sort`'s actual contract: O(n log n) worst case with quicksort-level average speed. The deeper lesson generalizes: **hybrids exist because every mechanism has a detectable failure signature, and switching mechanisms when the signature appears is cheaper than paying one mechanism's worst case everywhere.**

## Adaptivity, Branch Prediction, and the Hardware Dimension

Real-world inputs are rarely random: logs are nearly sorted, event streams arrive mostly in order, and re-sorts after small edits are mostly-correct. Adaptive algorithms convert that structure into linear-time behavior — Timsort on a sorted array does one run-detection pass and stops; pdqsort detects the sorted partition and finishes with insertion sort. On branch prediction: quicksort's partition loop is one comparison-branch per element, easily predicted on random data but mispredicted in patterns; pdqsort's block partitioning gathers comparisons into branchless SIMD-style passes precisely to keep the core's pipeline full. Heapsort, as noted, loses by cache behavior at equal complexity. The interview-worthy summary: **at equal asymptotics, the ranking on real hardware is decided by memory access pattern, branch predictability, and adaptivity to input structure — in that order.**

## When Non-Comparison Sorts Win — and Their Hidden Costs

Counting and radix sort beat the lower bound by not comparing: counting sort builds a histogram of key values (O(n + k) for range k) then places elements by prefix sums; LSD radix sort performs w stable counting passes on w digits (O(w·(n + b)) for base b). They win decisively when: keys are integers or short fixed strings; n is large and k/w is small relative to log n; and stability is available where needed. Sorting 10⁸ 32-bit integers, radix passes in a handful of linear scans that no comparison sort matches.

The hidden costs, mechanism by mechanism:

- **Key-type restriction.** Radix needs keys decomposable into digits with a total order reconstructible from digit order. Floats require sign-bit tricks (flip for negatives), and arbitrary user comparators are simply unsupported. If sorting by "any comparator", you are in comparison-land.
- **Pass overhead and memory.** Each radix pass writes the entire array to a new buffer (or permutes in place with cycle walks): w full-array writes. Counting sort's histogram is O(k) — sorting by a 64-bit key range is absurd without bucketing. Poor cache behavior on large key spaces (random bucket writes) can erase the theoretical win; multi-pass radix with small bases (256) exists to keep histograms cache-resident.
- **No adaptivity, no partial sorting.** Radix always processes all digits of all elements: sorting 10⁹ keys where the top 10 are needed is a job for heapselect/partial sort, not radix. And on nearly-sorted input radix gains nothing, while Timsort/pdqsort finish in linear time.
- **Stability requirements dictate direction.** LSD radix requires a stable inner sort; MSD radix sorts high digits first but needs recursion management. The stability that counting passes need is exactly what the simple bucket-write mechanism provides — get it wrong and equal keys come out reordered, silently breaking multi-key sorts.

## Edge Cases and Counterexamples

- **Naive quicksort's collapse is a two-for-one failure**: first-element pivot on sorted input gives O(n²) time *and* O(n) recursion depth — the stack overflow arrives with the quadratic blowup. Both are fixed by median-of-three plus tail-call elimination on the larger side, and structurally prevented by introsort's depth guard.
- **"Mergesort is always stable" needs a caveat**: stability comes from the merge preferring the left run on ties. Implement it with `<=` on the wrong side or merge right-into-left, and equal-key order silently breaks — a bug that surfaces only as wrong multi-key sort results, hard to catch in tests.
- **Heapsort wins when memory, not time, is the axis**: O(1) auxiliary memory and a guaranteed n log n make it the fallback inside introsort and the right choice in embedded/memory-capped contexts where a mergesort buffer would OOM.
- **Timsort on adversarial input**: run-merging heuristics were originally exploitable to trigger worst-case merges (there is a known crafted-input line of work on Timsort's invariants); modern implementations added the run-stack invariant checks precisely to bound this. Adaptive shortcuts deserve the same adversarial scrutiny as any other mechanism.
- **Radix loses quietly**: sorting strings of wildly varying length (long-tail keys) makes w large and dominant — comparison sorts that early-exit on first differing character beat digit passes that process every digit of every key. The "O(n)" in radix is O(n·w), and w is workload-dependent.

## Decision Framework: Workload → Algorithm

| Workload signature | Choose | Why |
|--------------------|--------|-----|
| Generic unknown data, in-memory | Introsort / pdqsort (`std::sort`, Rust sort) | Quicksort speed with a hard n log n worst case |
| Sorting objects where equal keys must keep order | Timsort (or mergesort) | Stability required; Timsort adds adaptivity |
| Nearly-sorted / reversals / concatenated runs | Timsort or pdqsort | Adaptive: O(n) on structure, n log n otherwise |
| Memory-capped, no O(n) buffer allowed | Heapsort (or in-place introsort) | O(1) extra memory, guaranteed bound |
| External / streaming / disk-based | Mergesort | Sequential access pattern matches storage; runs compose |
| Huge n, integer or fixed-width keys | LSD radix (or counting) | Beats the comparison lower bound; linear passes |
| Small n (≲ 16–32) inside any algorithm | Insertion sort | Lowest constant; this is why hybrids finish with it |
| Duplicates dominate | 3-way quicksort | Splits equals out; avoids O(n²) on all-equal inputs |
| Need only top-k, not full order | Heap-based partial sort | Skip the full n log n entirely |
| Parallel / many-core | Parallel mergesort or samplesort | Merge tree and partitioning parallelize cleanly ([parallel sorting](../../dsa/advanced/parallel-sorting.md)) |

Ordered checklist: (1) stability needed? → Timsort/mergesort family; (2) key type supports digit decomposition and n is huge? → radix/counting; (3) memory budget forbids O(n) auxiliary? → heapsort/introsort; (4) input has known structure (nearly sorted)? → adaptive sorts; (5) else → library introsort/pdqsort, and be ready to say *why the library ships a hybrid*.

## Interview Questions

1. **Why does `std::sort` use introsort instead of plain quicksort?** Quicksort's O(n²) worst case (bad pivots) and O(n) stack depth are real failure modes. Introsort monitors recursion depth — beyond 2·log₂(n) it switches to heapsort on the subrange, converting the worst case to O(n log n) — and finishes small subranges with insertion sort for constants. It keeps quicksort's cache-friendly average and adds a hard guarantee.
2. **Heapsort has the same worst case as mergesort and O(1) memory. Why isn't it the default?** Its sift-down jumps by index powers of two across the array, so each step hits a new cache line and the prefetcher cannot help; mergesort streams sequentially. Equal asymptotics, very different memory behavior — heapsort survives as introsort's in-place escape hatch, not the primary.
3. **When and how does radix sort beat the Ω(n log n) bound, and what does it cost?** The bound applies only to comparison sorts. Radix never compares: it makes w stable digit passes, O(w·(n + b)). It wins for huge n with fixed-width integer keys. Costs: key-type restriction (floats/signs need tricks), w full-array buffer writes, no adaptivity or partial ordering, and O(w) can dominate for variable-length keys.
4. **Your sort must be stable. Why does that eliminate quicksort and heapsort, and what do you pick?** Stability requires equal keys to retain input order; quicksort's long-range swaps and heapsort's sift-downs reorder equal keys arbitrarily and patching them is expensive. Pick Timsort (stable, adaptive, O(n) on nearly-sorted) or plain mergesort — and if implementing mergesort yourself, keep the left-run-on-ties merge ordering, because stability lives exactly there.
5. **What is "adaptive" sorting, and why does it matter more in production than in textbooks?** Adaptive sorts exploit existing order: Timsort detects natural runs, pdqsort detects sorted partitions — both drop to O(n) on nearly-sorted input. Production data (logs, event streams, incremental re-sorts) is nearly sorted far more often than random, so adaptivity is routinely the dominant constant-factor win — and a useful reminder that workload structure, not the exponent, decides the winner.

## Key Takeaways

- All comparison sorts are Ω(n log n) worst case, so real differentiators are stability, memory, adaptivity, and hardware behavior — not exponents.
- Quicksort: fastest average, cache-friendly, but quadratic worst case without guards. Mergesort: guaranteed n log n, stable, O(n) buffer, king of external sorting. Heapsort: O(1) memory and hard bounds, paid for in cache misses.
- Introsort exists because quicksort's failure signature (excess recursion depth) is detectable at runtime; pdqsort extends the same idea to pattern degeneracies and adds an O(n) best case. Hybrids beat monoliths.
- Timsort/pdqsort convert real-world input structure (nearly-sorted runs) into linear time — often the biggest practical win of all.
- Radix/counting escape the comparison bound by indexing digits, and pay in key-type restrictions, w buffer passes, and zero adaptivity; their O(n) is O(n·w).
- The decision is workload-shaped: stability, memory cap, structure of input, key type, and partial-ordering needs — in roughly that order.

## Cross-References

- [Sorting chapter](../../dsa/chapters/ch05-sorting.md) — tutorial mechanics of all five families.
- [Complexity Analysis](../../dsa/chapters/ch03-complexity-analysis.md) — the decision-tree lower-bound argument in full.
- [pdqsort Deep Dive](../../dsa/advanced/pdqsort.md) — block partitioning and pattern defeating in detail.
- [Parallel Sorting](../../dsa/advanced/parallel-sorting.md) — how mergesort and samplesort scale across cores.
- [Complexity Claims: Assumptions Hunt](../assumptions-hunt/complexity-claims.md) — the average-case assumptions behind "quicksort is O(n log n)".
- [Arrays vs Linked Lists](./arrays-vs-linked-lists.md) — sibling comparison: memory layout and cache behavior in depth.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
