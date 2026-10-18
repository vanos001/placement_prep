# Input Constraints: The Assumptions Algorithms Make About Their Inputs

## Overview

Algorithm descriptions come with an implicit input contract: the array is sorted, the numbers are small, the string is ASCII, the data fits in RAM, the input is not empty. None of these contracts is written down in the pseudocode, which is why they survive from lecture notes into production code without ever being examined. This chapter audits the most consequential input-side assumptions, breaks each with a concrete counterexample, and states the corrected rule.

The pattern here repeats: the algorithm is correct for the inputs the textbook imagined. The bug enters when production supplies an input the textbook never imagined — an array of a billion elements, a sum that exceeds the accumulator's width, a UTF-8 string, or an empty file.

## Assumption 1: "Binary Search Just Needs a Sorted Array"

### The taught rule

Binary search finds a key in a sorted array in O(log n) time: compare against the middle element, discard the half that cannot contain the key, repeat.

### The hidden assumptions

The one-sentence rule hides at least four preconditions:

- **Sortedness under a consistent order.** The array must be sorted according to the *same* comparison used during the search, and that comparison must be a total (strict weak) order.
- **A valid total order at all.** Floating-point `NaN` violates it: every comparison with `NaN` is false, so a sorted float array containing `NaN` breaks the discard-half logic, and in C++ a comparator violated by `NaN` makes `std::sort` itself undefined behavior because it requires a strict weak ordering.
- **Indices that fit the index type.** Array indices must be representable in the type used to hold `low`, `high`, and `mid`.
- **An overflow-safe midpoint.** `(low + high) / 2` must compute the mathematical midpoint — which it does not when the sum overflows.

Each assumption is invisible in the demo because the demo array has eight elements, a correct comparator, and an `int` midpoint that never comes near `2^31 - 1`.

### Counterexample: the JDK's nine-year overflow bug

Joshua Bloch's June 2, 2006 post on the Google Research blog — "Extra, Extra - Read All About It: Nearly All Binary Searches and Mergesorts are Broken" — documents the canonical failure. The standard binary search contained:

```java
int mid = (low + high) / 2;   // buggy version
```

The post states the failure condition precisely: the bug manifests "if the sum of `low` and `high` is greater than the maximum positive int value (2^31 - 1)". The sum overflows to a negative value, stays negative after division by two, and the search then indexes the array with a negative `mid`: in Java it throws `ArrayIndexOutOfBoundsException`; in C it performs an out-of-bounds access with unpredictable results. Bloch notes this can happen "for arrays whose length (in elements) is 2^30 or greater (roughly a billion elements)" — and that the JDK version he wrote himself "was reported to Sun recently when it broke someone's program, after lying in wait for nine years or so".

The arithmetic is easy to verify: with `low = high = 2^30`, the sum is `2^31`, which exceeds `2^31 - 1`; in two's-complement 32-bit arithmetic it wraps to `-2^31`, and `mid` becomes `-2^30`.

The fixes from the post, all overflow-safe:

```java
int mid = low + ((high - low) / 2);   // no sum of large values
int mid = (low + high) >>> 1;         // unsigned shift in Java
```

In C/C++, where `>>>` does not exist, cast before adding so the addition happens in unsigned arithmetic: `mid = ((unsigned int)low + (unsigned int)high) >> 1;` (unsigned overflow is defined to wrap, unlike signed overflow).

### What changes when the assumption is removed

The corrected statement: *binary search performs O(log n) comparisons, provided the input is sorted under the comparator's order and the midpoint is computed without overflow*. When the comparator is not a total order (NaN), sort first, then search, and decide explicitly what the search should do with incomparable values. When indices can exceed the type's range (two billion elements, or pointer differences), use a wider type or the offset form of the midpoint.

### Consequences

This is the most famous "your trivial code has a bug" interview probe, and it generalizes: every expression that aggregates sizes, counts, offsets, or timestamps is one large-but-legal input away from the same failure. Candidates who know the bug also know why `(low + high) >>> 1` is safe in Java but `>> 1` after signed addition is not.

## Assumption 2: "Quicksort Partition Maintains Its Invariant"

### The taught rule

Partition the array around a pivot so that everything left compares less and everything right compares greater; recurse on both sides. Expected O(n log n).

### The hidden assumptions

- The pivot splits the range *reasonably* — the O(n log n) bound is a statement about balanced partitions, not about the loop code.
- The partition invariant ("nothing left of the boundary is ≥ pivot") holds at every step, which the loop must maintain across swaps.
- The input is not adversarial against your pivot strategy. Median-of-three is deterministic, so a "killer" input can drive it to worst-case behavior — McIlroy's classic paper "A Killer Adversary for Quicksort" constructs such inputs explicitly.

### Counterexample: all-equal keys

Take the common Lomuto scheme with the strict comparison `a[j] < pivot` and an array of n copies of the same value. The comparison is never true, `i` never advances, and the partition returns the leftmost position: one side is empty, the other has n-1 elements. The recurrence becomes T(n) = T(n-1) + O(n), which is Θ(n²). The same degradation occurs with the `<=` variant (the split just falls out the other end). This is not exotic: sorting a column of repeated statuses or equal timestamps is an everyday input.

### What changes when the assumption is removed

Three-way partitioning (Bentley–McIlroy, or the Dutch national flag scheme) groups all keys equal to the pivot in one pass, so all-equal input finishes in O(n) — no recursion at all. Production sorts add insurance against both equal keys and adversaries: introsort (C++ `std::sort`) switches to heapsort when recursion depth exceeds a threshold, and pdqsort adds more adversary resistance on top. The corrected claim: *quicksort runs in expected O(n log n) with random pivots and degrades gracefully (not quadratically) on duplicate-heavy inputs only if partitioning is three-way or depth-capped*.

### Consequences

Interviewers use all-equal arrays as the standard quicksort follow-up; the expected answer is three-way partitioning. The deeper lesson is that a randomized or adversarial-resistant pivot strategy is a *response to a hidden assumption about input distribution*, the same family of assumption behind hash-flooding denial of service (see [complexity claims](complexity-claims.md)).

## Assumption 3: "The Sum Fits in an int"

### The taught rule

Sum the array with an accumulator: `sum += a[i]`, then compute averages, prefix sums, or totals from it.

### The hidden assumptions

- The total fits in the accumulator's width, not just each element.
- Intermediate arithmetic (especially averages computed as `sum * k / n`, or `(a + b) / 2`) also fits.
- Overflow behaves the way you expect: it wraps in Java, but in C and C++ signed overflow is undefined behavior, so the compiler is allowed to assume it never happens and optimize accordingly.

### Counterexample

Two billion 32-bit ints, each holding the value 3. The true sum is about 6.4 × 10^9, above `INT_MAX = 2,147,483,647`. Even a smaller case suffices: 2^30 elements × 3 = 3,221,225,472 — over the limit with elements that individually fit comfortably. In Java the accumulator wraps to a negative number and the "average" comes out negative; in C the overflow is undefined. The same failure hits prefix sums over revenues, byte counts, or timestamps in milliseconds.

### What changes when the assumption is removed

Accumulate in a wider type (`long`/`int64_t`), or use saturating/checked arithmetic where the runtime provides it, or state and enforce a bound on inputs. When even 64 bits is not enough (summing many 64-bit values), use 128-bit intermediates or big integers. The corrected claim: *the accumulator must be sized for the maximum possible total — n × max|element| — not for the maximum element*. Interviewers probe this with "sum an int array" and expect the candidate to ask about n and value ranges before writing `int sum`.

### Consequences

The midpoint bug in Assumption 1 and this one are the same species: correct algorithm, wrong width. Coding-interview complexity pages discuss time and memory budgets but rarely numeric budgets; add them yourself.

## Assumption 4: "The Input Fits in Memory"

### The taught rule

Load the data, index it, sort it, run dynamic programming over the whole table. Random access is free; the asymptotics assume it.

### The hidden assumptions

- The entire working set fits in RAM, so random access is cheap and uniform.
- The OS will keep the data resident; if it does not, every "O(1)" access can become a page fault.
- The complexity model is the RAM model, which has no concept of sequential versus random I/O.

### Counterexample

Sort 80 GB of 64-bit integers on a machine with 16 GB of RAM using in-memory quicksort. The working set exceeds RAM, so every partition pass thrashes pages; performance collapses far below the O(n log n) prediction. The same data, sorted with external merge sort — sequential runs that fit in memory, then k-way merge with sequential reads — completes in roughly one pass of reading plus one pass of writing, because it was designed for a model where sequential I/O is the cheap operation.

### What changes when the assumption is removed

You move to the external-memory model, where cost is measured in block transfers. Algorithms get redesigned around the new cost: B-trees instead of binary search trees, streaming aggregation instead of full-table materialization, windowed instead of full-history computation. The corrected claim: *for inputs larger than memory, choose algorithms whose I/O pattern is sequential and whose working set is bounded; treat "fits in memory" as an explicit precondition, not a default*. For the disk-side version of this argument, see [complexity claims](complexity-claims.md) and the external-memory chapter in the DSA track.

### Consequences

In system design interviews, "does it fit in memory?" is the first question a strong candidate asks about any data store. It separates candidates who have shipped batch jobs from candidates who have only seen LeetCode constraints.

## Assumption 5: "Strings Are ASCII"

### The taught rule

String algorithms operate on characters: length, reverse, case-fold, compare, index by position.

### The hidden assumptions

- One byte = one character. In UTF-8, characters take 1–4 bytes; `strlen` in C counts bytes, not user-perceived characters.
- Case folding is per-byte and ASCII-only.
- Byte order equals display order, so reversing bytes reverses the string.

### Counterexamples

- `"café"` in UTF-8 is 5 bytes (the `é` is two: `0xC3 0xA9`). Truncating "to 4 characters" with a byte-indexed slice cuts the `é` in half and yields invalid UTF-8.
- Reversing the UTF-8 bytes of `"é"` produces `0xA9 0xC3` — an invalid sequence. Grapheme-level content breaks the same way: an emoji made of multiple code points reversed byte-wise is garbage.
- Case-insensitive comparison per byte is wrong in both directions: `"Éclair"` and `"éclair"` differ at the first byte and compare unequal, while the Kelvin sign `K` (U+212A) is Unicode-case-equal to plain ASCII `k` despite sharing no bytes.
- In C, passing a plain `char` to `toupper`/`tolower` when it holds a negative value (the default on many platforms for bytes ≥ 0x80) is undefined behavior — the ctype functions require the value be representable as `unsigned char` or equal to `EOF`. The classic fix is the seemingly redundant cast `(unsigned char) c`.

### What changes when the assumption is removed

Exact-match algorithms (KMP, rolling hashes, suffix structures) remain correct on bytes as long as needle and haystack are compared byte-for-byte — but any *semantic* operation (case-insensitive match, search by character position, reversal, formatting) needs a Unicode-aware library operating on code points or grapheme clusters. The corrected claim: *byte-level algorithms are safe for byte-exact operations; character-level semantics require decoding first, and "length" must be defined as bytes, code points, or graphemes depending on the question*.

### Consequences

This assumption produces subtle production bugs (search that misses matches, truncation that corrupts data, sorts that ignore accents) and is a common senior-interview probe: "your palindrome checker works on LeetCode — what breaks on real user text?"

## Assumption 6: "The Input Is Non-Empty (and Has at Least Two Elements)"

### The taught rule

Initialize the answer to the first element, seed the window, start recursion. The empty and single-element cases are "trivial".

### The hidden assumptions

- There is a first element to initialize from; indexing an empty array is a crash (Java), an exception (C++ `max_element` on an empty range returns the end iterator, which is UB to dereference), or silent garbage (C).
- Division-based quantities (average, midpoint, windowed mean) have a nonzero denominator.
- Two-pointer and binary-search idioms that assume `lo < hi` terminate and return something sensible when `lo == hi` or the range is empty.

### Counterexample

A sliding-window average computes `sum / windowSize`; a stream that ends before the first full window arrives divides by zero. A "find max" that returns `a[0]` on an empty buffer reads out of bounds in C — often *appearing* to work in tests because the adjacent stack memory happens to hold plausible values. A pair-sum two-pointer scan on a one-element array either loops forever or reports a false negative, depending on whether the `lo < hi` guard was dropped for "efficiency".

### What changes when the assumption is removed

Empty-input behavior becomes part of the function's contract, chosen deliberately: return an empty result (a `Maybe`/`Optional`/`null`-documented API), throw, or return a sentinel — but the choice is explicit and tested. Base cases for recursion cover n = 0 and n = 1, not just "small enough". The corrected claim: *state the behavior for empty, single-element, and maximum-size inputs as part of the specification, and let your tests hit exactly those three points plus one interior value*.

### Consequences

The DSA edge-case checklist in this repo drills exactly these boundaries because they are the most common cause of wrong-answer verdicts in contests and off-by-one bugs in production. Fuzzers find them quickly; interviews find them faster.

## Interview Questions

1. **Why is `(low + high) / 2` wrong in Java, and give two safe alternatives.** The sum can exceed `2^31 - 1` and overflow negative for arrays of roughly 2^30 or more elements — the bug Bloch documented in the JDK. Safe: `low + (high - low) / 2`, or `(low + high) >>> 1` (unsigned shift). In C, the offset form or an unsigned cast is needed because signed overflow is UB.
2. **Why does quicksort go quadratic on an array of identical elements with a standard Lomuto partition, and what fixes it?** The strict (or non-strict) comparison keeps one partition side empty, giving T(n) = T(n-1) + O(n) = Θ(n²). Three-way partitioning removes the problem entirely, giving O(n) on all-equal input; introsort-style depth caps bound the damage for other degenerate inputs.
3. **An API returns the "maximum" of a list. What questions do you ask before implementing it?** Behavior on an empty list (error, Optional, sentinel), ties (first or last), whether the input can contain NaN-like incomparable values, and the accumulator's numeric range if maxima are later summed. Each question corresponds to a hidden assumption in the naive "initialize with first element" implementation.
4. **Your string-reversal utility passed all tests but corrupted customer names in production. Diagnose.** UTF-8 multi-byte sequences reversed byte-wise become invalid byte sequences. The fix is to operate on code points or grapheme clusters with a Unicode-aware routine, or to reverse at the byte level only when the contract is explicitly byte-oriented. Tests passed because the fixtures were ASCII.
5. **When is a byte-level search algorithm (KMP, rolling hash) safe for non-ASCII text, and when not?** Safe for exact byte-for-byte matching of a UTF-8 needle in a UTF-8 haystack. Unsafe for case-insensitive matching, accent-insensitive matching, or anything defined on characters/graphemes, because those equivalences do not exist at the byte level.

## Key Takeaways

- Every algorithm carries an input contract; sorting, searching, and summation routines carry at least three each (order, bounds, width).
- The most famous algorithm bug — the JDK's binary search midpoint overflow — came from a correct algorithm meeting a bounded integer type, not from a wrong idea.
- Duplicate-heavy inputs, empty inputs, and non-ASCII text are the three cheapest boundary sets to test, and the three most commonly skipped.
- Numeric budgets (accumulator width, overflow behavior) deserve the same analysis as time and memory budgets.
- When an assumption cannot hold (input larger than memory, non-total orders), the algorithm must be replaced, not patched — external-memory and Unicode-aware designs exist precisely for these regimes.

## Cross-References

- [Binary search](../../dsa/chapters/ch06-searching.md) — the canonical algorithm whose midpoint assumption broke in the JDK.
- [Sorting](../../dsa/chapters/ch05-sorting.md) — quicksort partition schemes and their degenerate inputs.
- [DSA edge cases](../../dsa/chapters/dsa-edge-cases.md) — the boundary-input catalog this chapter assumes as background.
- [External memory algorithms](../../dsa/chapters/ch159-external-memory.md) — what changes when "input fits in memory" is false.
- [Complexity claims](complexity-claims.md) — sibling chapter auditing the cost-model assumptions behind these same algorithms.
- [Memory model](memory-model.md) — signed overflow and uninitialized memory semantics referenced in this chapter.
- [Hash lookup is O(1)](../misconceptions/hash-lookup-o1.md) — the adversarial-input counterpart for hash tables.
- [Arrays vs linked lists](../why-not-handbook/arrays-vs-linked-lists.md) — the random-access assumption examined from the data-structure-choice angle.
- [Hashing](../../cryptography/hashing.md) — keyed hashing as the defense against adversarial inputs.
