# Pattern-Defeating Quicksort and the Modern Adaptive Sort

Every standard library shipped essentially the same unstable sort for two
decades: median-of-3 quicksort with an introsort-style depth limit. Then in
2016 Orson Peters released **pdqsort** — pattern-defeating quicksort — and the
stdlibs switched: Go 1.19 rewrote `sort.Sort` around it, Rust's
`sort_unstable` was built on it until 1.81 swapped in ipnsort/driftsort, and
Boost.Sort ships `pdqsort.hpp`. The idea is not a new partition; it is a bag
of cheap detections exploiting *order that is already there* — ascending
runs, descending runs, all-equal blocks — so realistic inputs sort in O(n)
while a bounded heapsort fallback keeps the worst case at O(n log n). This
page walks the mechanisms from the C++ source
([orlp/pdqsort](https://github.com/orlp/pdqsort)) and measures them in Python;
the stable family (Timsort, driftsort) is a different lineage — see
[ch05-sorting](../chapters/ch05-sorting.md) and
[parallel sorting](./parallel-sorting.md).

## The adaptive lineage in one picture

Introsort (Musser, 1997) added the depth limit that quicksort always lacked;
pdqsort keeps the limit and adds downward adaptation:

```text
      input guarantee exploited?          algorithm
      none (random data)                  plain median-of-3 quicksort
      adversarial pivots (depth>limit)    introsort/pdqsort -> heapsort
      ascending/descending runs           pdqsort: partial insertion sort,
                                          early exit, ~n comparisons
      all-equal blocks (dups)             pdqsort: partition_left fast path
      small range (< 24)                  both: plain insertion sort
```

## Mechanism 1: the pivot ladder (median-of-3, then ninther)

`pdqsort_loop` starts like the classic: below `insertion_sort_threshold = 24`
it insertion-sorts (guarded on the leftmost recursion, unguarded after). Above
`ninther_threshold = 128` the pivot is **Tukey's ninther** — the median of
three medians, four `sort3` networks over the thirds of the range:

```text
   sort3(b[0], b[m], b[-1])    // medians of outer/inner triads (x3 below)
   sort3(b[1], b[m-1], b[-2]); sort3(b[2], b[m+1], b[-3])
   sort3(b[m-1], b[m], b[m+1]) // median of the three medians
   swap(b[0], b[m])            // ninther lands at b[0] = pivot
```

A median-of-3 sees only 3 samples — enough to defeat; the ninther samples 9
positions through 12 comparisons and is provably better on structured data
like organ-pipes. Below 128 elements median-of-3 wins: cache effects dominate
pivot quality.

## Mechanism 2: the pattern defeat (already-partitioned check)

`partition_right` returns `(pivot_pos, already_partitioned)`: while scanning
it counts swaps, and **zero** swaps means the range was already sorted around
the pivot. If both sides then pass `partial_insertion_sort` — an insertion
sort allowed at most `partial_insertion_sort_limit = 8` moved elements total
(pdqsort.h accumulates the *distance moved*, never resets) — the subrange is
finished. On a fully ascending or descending array this fires at the top of
the first partition: O(n) comparisons, zero recursion. The check is free
bookkeeping the partition loop already does; false positives cost ≤8 moves.

## Mechanism 3: the equal-elements fast path (partition_left)

Duplicates are the other pattern. If `!leftmost && pivot <= *(begin-1)` — the
pivot equals the element the previous partition left at the boundary — no
element in `[begin, end)` is smaller than that neighbor. pdqsort switches to
`partition_left` (**equals go left**, greater right) and loops on the right
side only: the left is all-equal, i.e. sorted. n equal elements become O(n).

## Mechanism 4: the bounded bad-pivot budget (break patterns, then heapsort)

After partitioning, pdqsort checks for a **highly unbalanced** split — either
side smaller than `size / 8`. If so, `bad_allowed` (initialized to `log2(n)`)
decrements; at zero it falls back to `make_heap` + `sort_heap`, guaranteeing
O(n log n). Before giving up it *shuffles* the two small sides
(`iter_swap(begin, begin + l_size/4)` and friends), destroying the patterns
adversarial sequences rely on. That is the "name-defeating" part most
explanations miss: pattern defeat is two-directional — keep good patterns,
destroy bad ones so the same trick cannot win twice. (Balanced partitions
skip the shuffle and run mechanism 2.)

The branchless build (`pdqsort_branchless`, for default `std::less` over
cheaply-copyable types) replaces the partition with **block partitioning**:
two 64-element blocks (`block_size = 64`) scanned with swap-bitsets and
out-of-place buffering hide load latency and remove data-dependent branches
from the hot loop. Go's port drops this ("without the optimizations from
BlockQuicksort"): `sort.Interface` calls an interface method per comparison,
so branchless tricks cannot apply.

## Who ships what (verified, August 2026)

| Library | Unstable sort | pdqsort status | Source checked |
|---|---|---|---|
| Go `sort` (since 1.19) | pdqsort, no block partition | in production | go1.19 release notes + `src/sort/zsortinterface.go` comments |
| Rust `core::slice` (until 1.80) | pdqsort | replaced in 1.81 | 1.80.1 `sort.rs` header: "based on Orson Peters' pattern-defeating quicksort"; 1.81 notes: "Replace sort implementations with stable driftsort and unstable ipnsort" |
| libc++ `std::sort` | `__introsort` + bitset block partition (`__block_size = 64`) | block-partition lineage | `libcxx/include/__algorithm/sort.h` |
| Boost.Sort | `boost::sort::pdqsort` | in production | `include/boost/sort/pdqsort/pdqsort.hpp` |

The Rust replacement is instructive: ipnsort keeps the pdq ideas (pattern
defeat, heapsort fallback) while specializing on element size — adaptation
keeps evolving after adoption.

## Measuring the mechanisms

The Python port below implements the four mechanisms faithfully (constants
copied from `pdqsort.h`) and instruments comparisons, swaps, depth, and which
exits fired — all deterministic.

```python
# Mini-pdqsort vs plain median-of-3 quicksort (no adaptations). Constants from
# orlp/pdqsort pdqsort.h: ins<24, ninther>128, pis-limit=8, bad=log2(n).
# Simplified: block partitioning omitted; sorted() stands in for heapsort.
import math
CMP = SWP = 0
def less(a, b):
    global CMP; CMP += 1; return a < b
def swap(a, i, j):
    global SWP; SWP += 1; a[i], a[j] = a[j], a[i]

def partial_insertion(a, lo, hi, limit=8):       # pdqsort.h L124-146: total-move budget
    moved = 0
    for cur in range(lo + 1, hi):
        j = cur
        while j > lo and less(a[j], a[j - 1]): swap(a, j, j - 1); j -= 1
        if j < cur:
            moved += cur - j
            if moved > limit: return False
    return True

def median3(a, lo, hi):                          # median of 3 into a[lo]
    m = lo + (hi - lo) // 2
    if less(a[m], a[lo]): swap(a, m, lo)
    if less(a[hi - 1], a[lo]): swap(a, hi - 1, lo)
    if less(a[hi - 1], a[m]): swap(a, hi - 1, m)
    swap(a, lo, m)

def ninther(a, lo, hi):                          # Tukey ninther, pdqsort.h L416
    m = lo + (hi - lo) // 2
    def s3(x, y, z):
        if less(a[y], a[x]): swap(a, x, y)
        if less(a[z], a[x]): swap(a, x, z)
        if less(a[z], a[y]): swap(a, y, z)
    s3(lo, m, hi - 1); s3(lo + 1, m - 1, hi - 2)
    s3(lo + 2, m + 1, hi - 3); s3(m - 1, m, m + 1)
    swap(a, lo, m)

def partition_right(a, lo, hi):                  # Sedgewick-Hoare, pivot=a[lo]
    pivot = a[lo]; i, j = lo, hi; swaps = 0
    while True:
        i += 1
        while i < hi and less(a[i], pivot): i += 1
        j -= 1
        while j > lo and less(pivot, a[j]): j -= 1
        if i >= j: break
        swap(a, i, j); swaps += 1
    swap(a, lo, j); return j, swaps == 0         # clean = pattern detected
def partition_left(a, lo, hi):                   # equals LEFT, greater RIGHT
    pivot, i = a[lo], lo
    for j in range(lo + 1, hi):
        if not less(pivot, a[j]): i += 1; swap(a, i, j)
    swap(a, lo, i); return i                     # left side is all-equal

STATS = {"heap": 0, "defeat": 0, "eq": 0}
def pdq(a, lo, hi, bad, leftmost=True, depth=0):
    DEPTH[0] = max(DEPTH[0], depth)
    while hi - lo > 24:                          # insertion_sort_threshold
        (ninther if hi - lo > 128 else median3)(a, lo, hi)
        if not leftmost and not less(a[lo - 1], a[lo]):
            STATS["eq"] += 1; lo = partition_left(a, lo, hi) + 1; continue
        piv, clean = partition_right(a, lo, hi)
        if piv - lo < (hi - lo) // 8 or hi - (piv + 1) < (hi - lo) // 8:  # unbalanced
            bad -= 1
            if bad == 0: STATS["heap"] += 1; a[lo:hi] = sorted(a[lo:hi]); break
            for s, e in ((lo, piv), (piv + 1, hi)):         # break patterns
                if e - s >= 24:
                    swap(a, s, s + (e - s) // 4); swap(a, e - 1, e - 1 - (e - s) // 4)
        elif clean and partial_insertion(a, lo, piv) and partial_insertion(a, piv + 1, hi):
            STATS["defeat"] += 1; break
        pdq(a, lo, piv, bad, leftmost, depth + 1)
        lo, leftmost = piv + 1, False
    if hi - lo <= 24: partial_insertion(a, lo, hi, 1 << 60)  # plain insertion

def plain(a, lo, hi, depth=0):                   # Mo3 quicksort, no adaptations
    DEPTH[0] = max(DEPTH[0], depth)
    while hi - lo > 24:
        median3(a, lo, hi)
        piv, _ = partition_right(a, lo, hi)
        plain(a, lo, piv, depth + 1); lo = piv + 1
    if hi - lo <= 24: partial_insertion(a, lo, hi, 1 << 60)  # plain insertion

def lcg(n, seed=42):                             # deterministic pseudo-random
    x = seed; out = []
    for _ in range(n):
        x = (x * 6364136223846793005 + 1442695040888963407) % (1 << 64); out.append(x % 1000)
    return out
N = 512; DEPTH = [0]
patterns = {"sorted": list(range(N)), "reversed": list(range(N, 0, -1)),
            "organ-pipe": list(range(N // 2)) + list(range(N // 2, 0, -1)),
            "constant": [7] * N, "sawtooth": [i % 32 for i in range(N)], "lcg-random": lcg(N)}
print(f"n={N}  ins<24 ninther>128 pis<=8 bad<=log2(n)={int(math.log2(N))}")
print(f"{'pattern':<12}{'pdq cmp':>9}{'pdq swp':>9}{'plain cmp':>11}{'plain swp':>11}  exits")
for name, p in patterns.items():
    a1, a2 = list(p), list(p)
    for k in ("heap", "defeat", "eq"): STATS[k] = 0
    CMP = SWP = 0; DEPTH[0] = 0
    pdq(a1, 0, len(a1), int(math.log2(N)))
    c1, s1, d1 = CMP, SWP, DEPTH[0]
    ex = f"heap={STATS['heap']} defeat={STATS['defeat']} eq={STATS['eq']}"
    CMP = SWP = 0; DEPTH[0] = 0
    plain(a2, 0, len(a2))
    c2, s2, d2 = CMP, SWP, DEPTH[0]
    assert a1 == sorted(p) and a2 == sorted(p), name
    print(f"{name:<12}{c1:>9}{s1:>9}{c2:>11}{s2:>11}  {ex}  depth {d1}/{d2}")
```

```text
n=512  ins<24 ninther>128 pis<=8 bad<=log2(n)=9
pattern       pdq cmp  pdq swp  plain cmp  plain swp  exits
sorted           1034        2       3107         62  heap=0 defeat=1 eq=0  depth 0/5
reversed         1568      274       3107        320  heap=0 defeat=2 eq=0  depth 1/5
organ-pipe       6504     2468       9505       2456  heap=0 defeat=0 eq=0  depth 6/9
constant         1551      981       3102       1311  heap=0 defeat=0 eq=4  depth 5/5
sawtooth         4525     1597       4838       1485  heap=0 defeat=0 eq=0  depth 5/5
lcg-random       5067     2461       5327       2579  heap=0 defeat=0 eq=0  depth 5/5
```

On `sorted`, the defeat fires once at the top level: 1,034 comparisons vs
3,107 for plain, 2 swaps, **zero recursion** — the O(n)-ish behavior the
header comment promises; `reversed` follows (defeat=2). On `constant`, the
equal-elements path fires instead (eq=4 chained skips). On `lcg-random`
there is no structure to find and pdq pays ~5% overhead — the price of the
insurance. Organ-pipe is the instructive middle case: no early exit fires
(its first partition swaps, so the clean check fails), yet the ninther pivot
still cuts comparisons from 9,505 to 6,504. The heapsort fallback never
triggers here — its `log2(n)` budget exists for adversarial constructions
like Musser's median-of-3 killers, which these generators cannot produce.

## When it loses

Three honest caveats. On random data with an expensive comparator, the
detection bookkeeping is pure overhead — one reason Go dropped block
partitioning for interface comparators. The defeat check recognizes
*partitioned* structure, not general runs (a rotated sorted array gets no
early exit). And for objects with expensive moves (`std::string`, large
structs), the swap-heavy Hoare partition can lose to a stable merge-based
sort — compare [ch05-sorting](../chapters/ch05-sorting.md).

## Interview questions

**Q1. What exactly makes pdqsort "pattern-defeating"?**
A. Two opposite tricks: (1) detect *good* patterns — zero swaps in a
partition plus a successful 8-move partial insertion sort finishes the range
in near-linear time; (2) destroy *bad* ones — after an unbalanced partition,
swap elements at the quarter points of both sides so the same pivot-killer
construction cannot win twice.

**Q2. Why a heapsort fallback if pdqsort already shuffles after bad splits?**
A. Shuffling is a heuristic; an adversarial input could survive one round.
The `bad_allowed = log2(n)` budget bounds bad partitions before the heapsort
fallback, pinning the worst case at O(n log n) — introsort's guarantee,
preserved.

**Q3. Why did Go port pdqsort but not its block partitioning?**
A. Block partitioning (64-slot blocks with swap bitsets, branchless loops)
pays off only with an inlined, branch-predictable `operator<`. Go's
`sort.Interface` calls an interface method per comparison, so the port keeps
the adaptations and drops the micro-optimization.

## References

1. Orson R. L. Peters, *Pattern-defeating Quicksort*, arXiv:2106.05123, 2021 — https://arxiv.org/abs/2106.05123 (title/author verified via arXiv API)
2. orlp/pdqsort — reference C++11 implementation (constants quoted from `pdqsort.h`) — https://github.com/orlp/pdqsort
3. Go 1.19 release notes, "sort" section: "rewritten to use pattern-defeating quicksort" — https://go.dev/doc/go1.19
4. Go source, `src/sort/zsortinterface.go` (pdqsort port comments; no BlockQuicksort) — https://raw.githubusercontent.com/golang/go/go1.19/src/sort/zsortinterface.go
5. Rust 1.81.0 release notes (driftsort/ipnsort replacement) — https://blog.rust-lang.org/2024/09/05/Rust-1.81.0/ and https://releases.rs/docs/1.81.0/; pre-replacement pdqsort in 1.80.1 `library/core/src/slice/sort.rs` — https://raw.githubusercontent.com/rust-lang/rust/1.80.1/library/core/src/slice/sort.rs
7. libc++ `__algorithm/sort.h` (`__introsort`, `__block_size = 64` bitset partition) — https://raw.githubusercontent.com/llvm/llvm-project/main/libcxx/include/__algorithm/sort.h
8. Boost.Sort, `pdqsort.hpp` — https://github.com/boostorg/sort
9. J. R. Musser, *Introspective Sorting and Selection Algorithms*, Software: Practice and Experience 27(8), 1997 — DOI 10.1002/(sici)1097-024x(199708)27:8<983::aid-spe117>3.0.co;2-# (Crossref-verified)
