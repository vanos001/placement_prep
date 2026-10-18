# "O(n log n) always beats O(n²)"

## Overview

This page examines the claim that an asymptotically better algorithm is
therefore a faster program. Big-O ranks *growth rates on an idealized
machine as n goes to infinity*; every real execution happens at a finite n
with constants, memory-hierarchy effects, and input shape attached.
Standard libraries know this — CPython's sort and Java's `TimSort`
deliberately use the "worse" O(n²) algorithm for small or nearly-sorted
inputs. This page states the claim fairly and walks through counterexamples
whose arithmetic actually works.

## The Claim, Stated Fairly

The strongest common form of the claim is: "An O(n log n) algorithm is
always faster than an O(n²) algorithm on the same input. Therefore
replacing an O(n²) implementation with an O(n log n) one can never slow a
program down, and a reviewer can demand the swap unconditionally." This is
exactly the reasoning behind a large fraction of "your sort is naive"
review comments, and exactly what an interviewer probes with "when would
you *not* use merge sort?"

The claim deserves its fairness because the kernel is real: asymptotic
dominance is a theorem. For costs c₁(n) = a·n log₂ n and c₂(n) = b·n², the
inequality c₂(n) > c₁(n) holds for all n beyond a crossover point n₀, no
matter how large a and b are. The question is whether a statement about
n > n₀ honestly compresses to "always".

## Verdict

**False.** Big-O is an n→∞ statement on a unit-cost machine; at finite n the
race is decided by constants and input shape. On nearly-sorted input at
realistic sizes, the O(n²) algorithm beats the O(n log n) one by a wide
margin — an outcome inverted, not merely unimproved — and mainstream
standard libraries ship the O(n²) algorithm on purpose.

## Why People Believe It

The kernel of truth is threefold. First, the mathematics is correct: divide
the two costs and you get b·n / (a·log₂ n), which grows without bound, so
there is a crossover n₀ beyond which the quadratic algorithm loses forever.
Second, the experience agrees more often than not: at the sizes people
usually test (thousands or more, random data), the O(n log n)
implementation wins, and every contest timeout has taught the same lesson.
Third, the claim is a rational default: with no information about constants
or data, picking the better growth rate is the right bet.

What disappears in compression is the quantifier "for n > n₀" and the
assumption that both implementations carry similar constants and see
similar data. Growth rates rank *families of curves*, not *programs*.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "O(n log n) is faster" | Cost ∝ n log n beats cost ∝ n² for n > n₀, where n₀ depends on the constant factors |
| "At my input size" | At finite n, constants, cache behavior, and implementation quality decide |
| "On my input" | Adaptive algorithms exploit existing order; "n²" algorithms are often O(n + I) in the number of inversions I |
| "On any machine" | Big-O assumes a unit-cost RAM; real machines have caches, allocation costs, and memory traffic |

The precise statement: asymptotics tell you which cost *curve* eventually
wins. They are silent about where "eventually" starts and about everything
below the crossover. Two concrete implementations at a concrete n are
compared by measurement or careful operation counting — not by big-O class.

## Where It Breaks

**Nearly-sorted input, realistic size — the arithmetic.** Insertion sort
performs O(n + I) work, where I is the number of inversions (pairs out of
order). Take n = 100,000 records sorted except for 10,000 elements
inserted near their correct positions, giving I ≈ 10,000. Insertion sort
does roughly n + I ≈ 110,000 key operations; merge sort does its
~n·log₂ n ≈ 1,700,000 comparisons no matter what the data looks like. The
"naive" O(n²) algorithm is about 15× cheaper. This is not a corner case:
audit logs, event streams, and time-ordered data arrive nearly sorted —
exactly the regime where this failure appears in production.

**Small n — the libraries vote.** For n = 32 on random input, merge sort
performs about 129 comparisons (worst case n·log₂ n − n + 1 for a power of
two) and insertion sort about n²/4 = 256 — but merge sort pays for
recursion, a merge buffer, and scattered access, while insertion sort runs
a tight, cache-friendly loop of shifts. The constants overwhelm a 2×
comparison gap at this size. The libraries respond by not even attempting
merges: per Tim Peters' `listsort.txt` description, CPython sorts arrays
shorter than 64 elements entirely by binary insertion sort, and tunes the
minimum run length into the 32–64 range for larger arrays. Java's
`TimSort` does the same below its `MIN_MERGE` threshold of 32. C++
`std::sort` (introsort, Musser 1997) and `pdqsort` both drop to insertion
sort for small partitions. When every major library deliberately selects
the O(n²) algorithm, "always beats" is falsified by the reference
implementations themselves.

**Hidden costs the unit-cost model ignores.** Merge sort needs an O(n)
work buffer: allocating it and reading it out of cache order is time the
in-place neighbor never spends. Quicksort and insertion sort get their
speed from sequential access and inner loops small enough to predict or
vectorize. A big-O claim that silently assumes all memory operations cost
the same is a claim about a machine that does not exist.

**The crossover is real and it moves.** With constants a·n log₂ n versus
b·n², the quadratic algorithm wins until n exceeds roughly (a/b)·log₂ n.
If the "better" algorithm is a heavily generic implementation (a large)
and the "worse" one is a specialized 20-line loop (b small), the crossover
can sit in the thousands — above the input sizes of many real workloads.

## Practical Implications

- Use the platform's adaptive sort first: `sorted()` in Python,
  `Arrays.sort` for objects in Java, `std::sort` in C++, and Rust's
  `sort`/`sort_unstable` already implement the small-input and
  nearly-sorted fast paths.
- Rank candidates by asymptotics only when inputs can grow; at bounded,
  small n, constants win and measurement settles it.
- Ask about data shape before data size: sortedness, duplicates, and run
  structure change real cost more than the big-O class does.
- When a review demands an asymptotic swap, ask for the input distribution
  and a benchmark; the burden of proof scales with the constant-factor
  risk.

## Interview Questions

### Is an O(n log n) sort always faster than an O(n²) sort?

No. Big-O compares growth rates as n→∞ on a unit-cost machine; at finite n,
constants, cache behavior, and input shape decide. Counterexample:
insertion sort is O(n + I) in the number of inversions, so on 100,000
nearly-sorted records with 10,000 inversions it does ~110,000 operations
versus ~1.7 million comparisons for merge sort. Standard libraries confirm
the boundary by using insertion sort for small runs.

### Why do Timsort, introsort, and pdqsort all fall back to insertion sort for small inputs?

Because below a threshold (64 elements for the whole array in CPython, 32
for `TimSort`'s `MIN_MERGE`, small partitions in introsort), the quadratic
algorithm's constant factors — a tight shift loop, no recursion, no
allocation, sequential access — dominate the asymptotic advantage, which
has not started paying yet at those sizes. Binary insertion sort also does
only ~n log₂ n comparisons; its O(n²) term is cheap data movement.

### Your benchmark shows an O(n²) function beating the O(n log n) rewrite you proposed. What do you check before conceding?

First, the input: is it nearly sorted (adaptive behavior)? Second, the
size: is n below the crossover for these implementations' constants?
Third, allocation and locality: does the O(n log n) version pay for
buffers, recursion, or pointer chasing the old one avoids? Then decide per
regime and document the boundary instead of a verdict.

## Key Takeaways

- Big-O is a statement about growth as n→∞ on an idealized machine, not a
  speed ranking of two concrete programs at a concrete size.
- Nearly-sorted data inverts the race: O(n + I) beats unconditional
  n log n by over an order of magnitude at realistic sizes.
- Reference implementations are the standing counterexample: CPython,
  Java, C++, and Rust all deploy O(n²) algorithms by design for small or
  well-structured inputs.
- The crossover n₀ depends on constant factors; "asymptotically better"
  says nothing until n clears it.
- Correct replacement sentence: "For large, unstructured inputs the
  O(n log n) algorithm wins; for small or nearly-sorted inputs the O(n²)
  one can win — measure at your n with your data."

## Cross-References

- [Assumptions Hunt: Complexity Claims](../assumptions-hunt/complexity-claims.md)
  — the hidden assumptions inside big-O statements
- [Average-Case Complexity](./average-case-complexity.md) — why "average"
  is a distribution claim, not a promise
- [Why-Not Handbook: Sorting Algorithms](../why-not-handbook/sorting-algorithms.md)
  — the full decision among sort families this claim flattens
- [Complexity Analysis](../../dsa/chapters/ch03-complexity-analysis.md) —
  what big-O, big-Θ, and big-Ω actually promise
- [Sorting](../../dsa/chapters/ch05-sorting.md) — insertion sort, merge
  sort, and the adaptive behavior in between
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- Tim Peters. *listsort.txt* — CPython source description of Timsort:
  binary insertion sort for short arrays, minimum run length in the 32–64
  range. <https://github.com/python/cpython/blob/main/Objects/listsort.txt>
- Oracle. *Class Arrays* API documentation — `sort(Object[])` specified as
  a stable, adaptive, iterative mergesort; primitive overloads specified
  as dual-pivot quicksort.
  <https://docs.oracle.com/javase/8/docs/api/java/util/Arrays.html>
- J. L. Bentley and M. D. McIlroy. *Engineering a Sort Function*. Software:
  Practice and Experience, 1993 — the classic study of constant-factor and
  small-partition choices in production sorts.
- D. R. Musser. *Introspective Sorting and Selection Algorithms*. Software:
  Practice and Experience, 1997 — introsort's insertion-sort cutoff for
  small partitions.
- O. Petersson and A. Moffat. *A Framework for Adaptive Sorting*. Discrete
  Applied Mathematics, 1995 — inversions and adaptivity as the measure
  insertion-sort-class algorithms exploit.
