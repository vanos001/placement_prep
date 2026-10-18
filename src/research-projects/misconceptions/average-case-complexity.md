# "Good average-case complexity guarantees good real-world performance"

## Overview

Big-O analysis is the shared language of algorithm interviews, and
average-case analysis is its most quoted dialect: quicksort is O(n log n) on
average, hash lookups are O(1) on average, so both are "fast in practice".
This page examines what that reasoning hides: averages are computed over a
distribution, real inputs are not drawn from that distribution, tails rather
than means dominate service quality, and constant factors routinely dominate
asymptotics at real-world sizes. The verdict is "incomplete" — average-case
complexity is a genuinely useful first guide, and the misconception is
treating it as a performance guarantee.

## The Claim, Stated Fairly

The strongest common form: "Quicksort is O(n log n) average case, so it will
be fast on our data; if the average case is good, the implementation is safe
to ship. Complexity analysis is how you know code will scale." This is fair:
average-case analysis correctly guided every working programmer who chose
quicksort, and the analysis is rigorous — the flaw is in the unwritten
assumption about which inputs the average is over.

## Verdict

**Incomplete.** Average-case complexity is a statement about a specified
input distribution; adversarial or skewed inputs, tail-latency requirements,
and constant factors can each break the link between "good average case" and
"good real-world performance".

## Why People Believe It

The kernel of truth is strong. For genuinely random inputs, quicksort's
expected comparisons are about 1.39 n log2 n — a real, provable average-case
result, and quicksort-with-good-pivots does beat most alternatives on random
data in practice, which is why standard libraries adopted its variants. Hash
tables really are O(1) on average for typical keys. Most workloads most of
the time resemble the assumed distribution closely enough that the average
case *is* the observed case — the reasoning works, until the day it doesn't.

Three silent assumptions do the damage: that inputs are drawn from the
textbook's distribution (uniform, random order); that the mean is the
statistic users experience (it is not — tails are); and that big-O is the
dominant term at the sizes that occur (constants and caches routinely
out-vote it).

## The Correct Formulation

Average-case complexity answers: "over this stated input distribution, what
is the expected cost?" Its usefulness stands or falls on four questions the
slogan never asks:

| Question | Why it matters |
|---|---|
| Average over *which* distribution? | Sorted, nearly-sorted, skewed (Zipf), and adversarial inputs are common in production and absent from uniform-random assumptions |
| Which statistic — mean or tail? | Service quality is p95/p99; a distribution can have a good mean and a terrible tail |
| What are the constants? | At n = 10, an O(n²) insertion sort beats an O(n log n) heapsort; asymptotics win only at scale |
| What does the adversary know? | Deterministic pivots and deterministic hash functions can be attacked once their behavior is public |

The precise form of the corrected claim: "Under distribution D, expected
cost is f(n)" — where naming D is the whole game. "Good average case" plus
"inputs resembling D" plus "mean is the right statistic" plus "n large
enough for asymptotics" is the full recipe; each elided clause is a
production incident waiting for its day.

## Where It Breaks

**Quicksort versus its inputs.** First-element-pivot quicksort on already
sorted input does n(n−1)/2 comparisons: for n = 100,000 that is ≈ 5 × 10⁹
comparisons against ≈ 1.7 × 10⁶ for the O(n log n) case (n log2 100,000 ≈
100,000 × 16.6) — a ~3,000× gap, reached by the most common real input there
is: sorted data. Median-of-3 kills the sorted case but not all cases:
McIlroy's 1999 adversary constructs inputs that force O(n²) behavior on any
deterministic pivot rule. The standard-library responses are the honest
engineering summary: introsort (Musser, 1997) switches to heapsort at depth
2·log2 n, capping the worst case at O(n log n); pdqsort adds pivot
randomization patterns and partition balancing; randomized pivots make the
adversary's job distributional rather than exact.

**Hash tables versus their keys** (see [Hash-Table Lookup](./hash-lookup-o1.md)
for the full argument): average O(1) is a statement about uniformly hashed
keys; adversarial keys all colliding make it O(n) per lookup, and the
mainstream runtimes ship hash randomization (Python) and bucket treeification
(Java 8+) as documented admissions.

**Skew beats the mean.** A key-value service where 0.1% of keys draw 40% of
traffic has a fine average lookup cost and a p99 dictated by one hot
partition's behavior. Mean-based reasoning says the service is fine;
percentile-based reasoning (and the on-call rotation) says otherwise. Real
workloads are skewed (Zipf-like) far more often than the textbook's uniform
distribution.

**Constants and caches at real sizes.** For n ≤ ~20, insertion sort beats
quicksort — which is why Timsort and pdqsort switch to insertion sort on
small runs. An O(n log n) algorithm with pointer chasing can lose to an
O(n²) array scan that stays resident in cache; big-O counts comparisons,
hardware counts cache lines. Asymptotics decide at scale; constants and
locality decide below it, and "below it" is where a lot of production data
lives.

**Tails are the product.** A retry storm, a GC pause, or one adversarial
payload lands in the 99th percentile. Users and SLOs feel the tail; the
average-case analysis never modeled it.

## Practical Implications

- Always ask "average over what distribution?" — and then measure whether
  production inputs resemble it (sorted? skewed? attacker-influenced?).
- Prefer algorithms with bounded worst cases or randomized behavior for
  untrusted inputs: introsort/pdqsort-style fallbacks, randomized pivots,
  keyed hashes.
- Design for the tail: percentiles, not means, decide user experience; add
  admission control and timeouts so one bad input class cannot own the p99.
- Respect constants: benchmark at production sizes with production-shaped
  data; hybrid algorithms exist precisely because asymptotics mispredict at
  small n.
- Treat deterministic behavior on attacker-visible inputs as a surface:
  if the adversary can choose keys, average-case analysis over "uniform
  inputs" is describing a workload you do not have.

## Interview Questions

### Quicksort is O(n log n) average case. What inputs break it, and how do real libraries cope?

Sorted or reverse-sorted input breaks first-element pivots (n(n−1)/2
comparisons ≈ 5 × 10⁹ for n = 100,000); McIlroy's adversary breaks any
deterministic pivot rule. Libraries use introsort (heapsort fallback at
depth 2·log₂ n), median-of-k with randomized elements, and pdqsort-style
balancing — converting worst cases into bounded ones.

### What does "average case" actually average over, and why is that the key question?

Over a stated input distribution — typically uniform random orderings or
uniform hashing. Production inputs are often sorted, skewed, or adversarial,
for which the expectation is meaningless. The distribution, not the O, is
the claim's content.

### Your service's mean latency is 20 ms but p99 is 2 s. Why does average-case reasoning miss this, and what do you look for?

Averages hide bimodality: most requests hit the fast path, while cache
misses, GC pauses, hot-key contention, or rare adversarial inputs populate
the tail. Average-case complexity predicts the mean regime only; you profile
tail requests (percentile tracing) and bound the slow path.

## Key Takeaways

- Average-case complexity is a theorem about a distribution; without naming
  the distribution, it is a slogan.
- Adversarial and skewed inputs are ordinary events, not exotic: sorted data
  for quicksort, colliding keys for hash tables.
- Standard libraries encode the correction — introsort, pdqsort, hash
  randomization, treeification — because vendors concluded the average case
  alone is not shippable.
- Tails and constants, not means and asymptotics, decide most real-world
  outcomes below large n.
- The complete engineering claim: expected cost f(n) over distribution D,
  with tail bounded by g(n), constants c, at sizes n where asymptotics
  dominate — every clause is doing work.

## Cross-References

- [Assumptions Hunt: Complexity Claims](../assumptions-hunt/complexity-claims.md)
  — the systematic version of this audit
- [Hash-Table Lookup](./hash-lookup-o1.md) — the O(1)-average claim under
  the same microscope
- [Complexity Analysis](../../dsa/chapters/ch03-complexity-analysis.md) —
  where the big-O language comes from
- [Sorting Algorithms](../../dsa/chapters/ch05-sorting.md) — quicksort,
  introsort, and the hybrid designs
- [More Threads Faster](./more-threads-faster.md) — the tail-latency
  consequence of ignoring distributions in concurrency
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- D. R. Musser. *Introspective Sorting and Selection Algorithms*. Software:
  Practice and Experience 27(8), 1997. (The heapsort fallback at depth
  2·log₂ n.)
- J. L. McIlroy. *A Killer Adversary for Quicksort*. Software: Practice and
  Experience 29(4), 1999. (Inputs that defeat deterministic median-of-3.)
- O. Peters. *pdqsort — Pattern-Defeating Quicksort*.
  <https://github.com/orlp/pdqsort> (adopted in various standard libraries;
  the modern mitigation lineage.)
