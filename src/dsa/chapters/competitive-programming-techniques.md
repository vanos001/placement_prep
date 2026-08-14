# Competitive Programming Techniques

A practical toolkit of techniques that bridge the gap between textbook algorithms and solving hard problems efficiently. Many of these appear in interviews at top companies.

---

## Coordinate Compression

When values are large but sparse (e.g., coordinates up to 10^9 but only 10^5 distinct values), map them to a dense range [0, n).

```cpp
vector<int> compress(vector<int> a) {
    vector<int> sorted_a = a;
    sort(sorted_a.begin(), sorted_a.end());
    sorted_a.erase(unique(sorted_a.begin(), sorted_a.end()), sorted_a.end());
    for (int& x : a)
        x = lower_bound(sorted_a.begin(), sorted_a.end(), x) - sorted_a.begin();
    return a; // now values in [0, n)
}
```

**Complexity:** O(n log n). Essential before using values as array indices or segment tree positions.

---

## Fast I/O

### C++
```cpp
#include <bits/stdc++.h>
using namespace std;
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // All cin/cout are now fast
}
```

For maximum speed with scanf/printf or custom read functions. Fast I/O can be 5-10x faster than default `cin`/`cout`.

### Python
```python
import sys
input = sys.stdin.readline
print = sys.stdout.write  # careful: requires string argument
```

---

## Prefix Sums and Difference Arrays

**Prefix sum:** `pref[i] = sum(arr[0..i-1])`. Query range sum [l, r] in O(1): `pref[r+1] - pref[l]`.

**2D prefix sum:** Query sum of any submatrix in O(1) after O(nm) preprocessing.

**Difference array:** For range updates `arr[l..r] += val`, apply `diff[l] += val, diff[r+1] -= val`, then prefix-sum to reconstruct.

```python
# Range add, then point query
def range_add(diff, l, r, val):
    diff[l] += val
    diff[r + 1] -= val

def build(arr, diff):
    arr[0] = diff[0]
    for i in range(1, len(arr)):
        arr[i] = arr[i-1] + diff[i]
```

---

## Two Pointers and Sliding Window

**Two pointers:** Move two indices through an array to solve in O(n) what would be O(n^2) with nested loops. Works when the problem has a monotone property.

**Sliding window:** Maintain a window [l, r] with some invariant. Expand right, shrink left as needed.

Common patterns: longest subarray with sum <= k, minimum window substring, count subarrays with exactly k distinct elements (atMost(k) - atMost(k-1)).

---

## Binary Search on Answer

When the answer is monotone (if x works, then all y >= x also work, or vice versa), binary search on the answer value and check feasibility.

```python
def binary_search_answer():
    lo, hi = 0, 10**18  # search space
    while lo < hi:
        mid = (lo + hi) // 2
        if feasible(mid):  # O(n) or O(n log n) check
            hi = mid
        else:
            lo = mid + 1
    return lo
```

**Examples:** Minimum maximum subarray sum after splitting into k parts, maximum minimum distance, smallest maximum weight capacity.

---

## Meet in the Middle

When n is too large for O(2^n) but n/2 is feasible: split into two halves, enumerate all 2^(n/2) subsets of each, combine.

```python
def subset_sum_half(arr, target):
    n = len(arr)
    left, right = arr[:n//2], arr[n//2:]
    left_sums = [sum(1 << i & mask and left[i] for i in range(len(left))) for mask in range(1 << len(left))]
    right_sums = [sum(1 << i & mask and right[i] for i in range(len(right))) for mask in range(1 << len(right))]
    right_sums.sort()
    # For each left_sum, binary search complement in right_sums
    best = 0
    for ls in left_sums:
        idx = bisect_right(right_sums, target - ls)
        if idx > 0:
            best = max(best, ls + right_sums[idx - 1])
    return best
```

**Complexity:** O(2^(n/2) * n) — feasible for n up to 40.

---

## Mo's Algorithm

Answer offline range queries on a static array by sorting queries in a specific order and maintaining a current answer while moving pointers.

Sort queries by (block of L, R if block is even else -R). Each move of L or R costs O(1) to update. Total complexity: O((n + q) * sqrt(n)).

---

## Square Root Decomposition

Divide an array into blocks of size sqrt(n). Point queries are O(1) with O(sqrt(n)) updates, or range queries in O(sqrt(n)) with O(1) updates. Simpler to implement than segment trees but slower.

---

## Constructive Algorithms

Problems asking you to build a structure (permutation, graph, array) satisfying constraints. Strategies:

- **Work backwards:** If the final state is constrained, think about what the last step must be
- **Greedy construction:** Build incrementally, fixing one element at a time
- **Pattern identification:** Try small cases, find the pattern, generalize
- **Swap-based:** Start with any valid configuration and swap to reach the target

---

## Game Theory: Nim and Sprague-Grundy

**Nim:** n piles of stones. Players alternate removing any positive number from one pile. XOR of all pile sizes = 0 means losing position (P-position).

**Sprague-Grundy theorem:** Any impartial game is equivalent to a Nim heap. Compute the Grundy number (mex of reachable Grundy values) for each position. XOR of Grundy values determines the winner.

```python
from functools import lru_cache

def grundy(state):
    """Compute Grundy number for a game state."""
    reachable = set()
    for move in moves(state):
        reachable.add(grundy(move))
    g = 0
    while g in reachable:
        g += 1
    return g  # mex
```

---

## Combinatorics Essentials

**Inclusion-Exclusion:** `|A union B union C| = |A| + |B| + |C| - |A cap B| - |A cap C| - |B cap C| + |A cap B cap C|`. Generalizes to n sets.

**Generating functions:** Encode a sequence as coefficients of a polynomial. The coefficient of x^k in the product of generating functions counts combinations summing to k.

**nCr mod p:** Precompute factorials and inverse factorials in O(n). `C(n,r) = fact[n] * invFact[r] * invFact[n-r] % p`.

---

## Computational Geometry Basics

**Orientation (cross product):** `cross(OA, OB) = (A.x - O.x)(B.y - O.y) - (A.y - O.y)(B.x - O.x)`. Positive = counterclockwise, zero = collinear, negative = clockwise.

**Convex hull (Andrew's monotone chain):** O(n log n). Sort by x, build lower and upper hulls using a stack. The orientation test determines whether to pop.

**Polygon area (shoelace):** `Area = |sum(x[i]*y[i+1] - x[i+1]*y[i])| / 2`.

---

## Interview Questions

1. **Given n points, find the smallest axis-aligned rectangle covering k points.** Use sliding window after sorting by x-coordinate.

2. **Given an array, find the number of subarrays with sum exactly k.** Use prefix sums + hashmap.

3. **Design a system to process range minimum queries.** Compare segment tree, sparse table, and square root decomposition.

4. **Two players take turns removing 1-3 stones from a pile. Determine the winner.** Compute Grundy numbers. What if there are multiple piles?

5. **Count the number of permutations of [1..n] where no element is in its original position (derangements).** Use inclusion-exclusion.

6. **Find the maximum XOR of any two elements in an array.** Use a trie (O(32n)).

7. **Given a set of intervals, find the point covered by the maximum number of intervals.** Use a sweep line with a difference array.

8. **Given n up to 30, find if any subset sums to target.** Use meet in the middle.

9. **Find the convex hull of a set of 2D points.** Implement Andrew's algorithm and explain the orientation test.

10. **Process q range sum queries on a static array efficiently.** Compare prefix sums (O(1) query, no updates), BIT (O(log n) with updates), and Mo's algorithm (offline).
