# Chapter 143: Knowledge Aids and Quick Reference

## Last-Minute Revision Guide

---

## 143.1 What Is a Knowledge Aid?

A **knowledge aid** is a condensed, high-signal reference designed for rapid recall during interviews, contests, or revision. Unlike tutorials that teach from scratch, knowledge aids assume familiarity and focus on **pattern recognition**, **decision shortcuts**, and **common pitfalls**.

**Motivation:** In a 45-minute interview, you have ~2 minutes to identify the right technique. A mental decision tree turns that from guesswork into systematic elimination.

---

## 143.2 Algorithm Decision Tree

When you see a problem, run through this tree to narrow your approach:

```
Is input sorted or can you sort it?
├─ Yes → Binary Search, Two Pointers, Merge-based
└─ No
   ├─ Need contiguous subarray? → Sliding Window, Prefix Sum, Kadane's
   ├─ Need subsequence (not contiguous)? → DP
   ├─ Graph structure? → BFS / DFS / Dijkstra / Union-Find
   ├─ Tree structure? → DFS / DP on trees / LCA
   ├─ Optimization (min/max)? → DP / Greedy / Binary Search on Answer
   ├─ Counting? → DP / Combinatorics / Inclusion-Exclusion
   ├─ n ≤ 20 (small)? → Bitmask DP / Backtracking / Meet-in-the-Middle
   ├─ n ≤ 1000? → O(n²) DP possible
   └─ n ≤ 10⁶? → O(n log n) required
```

### Decision Flowchart (Text Version)

| Clue in Problem | Likely Technique | Time Complexity |
|---|---|---|
| "Sorted array" | Binary Search | O(log n) |
| "Top k" / "k-th smallest" | Heap / Quickselect | O(n log k) / O(n) avg |
| "Shortest path" (unweighted) | BFS | O(V + E) |
| "Shortest path" (weighted, non-negative) | Dijkstra | O((V+E) log V) |
| "Shortest path" (negative edges) | Bellman-Ford | O(VE) |
| "All pairs shortest" | Floyd-Warshall | O(V³) |
| "Connected components" | DFS / Union-Find | O(V + E) / O(α(n)) |
| "Cycle detection" | DFS coloring / Floyd's | O(V + E) |
| "Interval scheduling" | Greedy (sort by end) | O(n log n) |
| "Palindrome" | Two pointers / DP | O(n) / O(n²) |
| "Serialize tree" | BFS / Preorder + marker | O(n) |
| "Random access, fast insert/delete" | Hash map | O(1) avg |

---

## 143.3 STL Quick Reference (C++)

| Need | STL Container / Algorithm | Notes |
|---|---|---|
| Sorted container | `set`, `map` | O(log n) insert/erase/find |
| Fast lookup | `unordered_set`, `unordered_map` | O(1) avg, O(n) worst |
| Priority queue (max) | `priority_queue<T>` | Default is max-heap |
| Priority queue (min) | `priority_queue<T, vector<T>, greater<T>>` | Use `greater` comparator |
| Min/Max element | `min_element`, `max_element` | O(n) |
| Sort | `sort`, `stable_sort` | O(n log n), `stable_sort` preserves order |
| Binary search | `lower_bound`, `upper_bound` | Requires sorted range |
| Next permutation | `next_permutation` | Returns false at last permutation |
| Accumulate | `accumulate(begin, end, init)` | Use `0LL` for `long long` |
| Unique elements | `unique` | Must sort first; returns new end iterator |
| Reverse | `reverse` | O(n) |
| Rotate | `rotate` | O(n) |
| Partial sort | `partial_sort`, `nth_element` | `nth_element` is O(n) |
| Count | `count`, `count_if` | O(n) |
| Find | `find`, `find_if` | O(n) |
| Remove (erase-remove) | `remove` + `erase` | Don't use `erase` alone on value |

### Python Equivalents

| Need | Python | Notes |
|---|---|---|
| Sorted container | `sortedcontainers.SortedList` | pip install sortedcontainers |
| Fast lookup | `set()`, `dict()` | O(1) avg |
| Priority queue | `heapq` (min-heap) | Use negative values for max |
| Sort | `sorted()`, `.sort()` | `sorted` returns new list |
| Binary search | `bisect_left`, `bisect_right` | From `bisect` module |
| Default dict | `collections.defaultdict` | Auto-initializes missing keys |
| Counter | `collections.Counter` | Counts occurrences |
| Deque | `collections.deque` | O(1) append/pop from both ends |

---

## 143.4 Common Mistakes and Fixes

| Category | Mistake | Fix |
|---|---|---|
| **Overflow** | Using `int` for large products | Use `long long` (C++) or Python's arbitrary ints |
| **Off-by-one** | `for (i=0; i<=n; i++)` when `i<n` was intended | Check loop bounds with small examples |
| **Uninitialized** | Using uninitialized variables | Initialize everything; use `{}` or `= 0` |
| **Iterator invalidation** | Erasing from container while iterating | Use erase-remove idiom or reverse iteration |
| **Signed/unsigned** | Comparing `int` with `size_t` | Cast explicitly or use consistent types |
| **Missing base case** | DP without n=0 or n=1 case | Always write base cases first |
| **Wrong comparison** | Sort with unstable comparator | Ensure strict weak ordering |
| **Stack overflow** | Deep recursion (n > 10⁴) | Convert to iterative or increase stack size |
| **Modular arithmetic** | Forgetting to mod after multiplication | Mod at every intermediate step |
| **Floating point** | Comparing doubles with `==` | Use `abs(a-b) < epsilon` |
| **Graph indexing** | 0-indexed vs 1-indexed confusion | Clarify at start, adjust accordingly |
| **String indexing** | Off-by-one in substring | `s[i:j]` in Python is `[i, j)` |

---

## 143.5 Complexity Cheat Sheet

### Time Complexity Classes

| Bound | Typical Algorithms | Max n |
|---|---|---|
| O(1) | Hash lookup, stack push/pop | Any |
| O(log n) | Binary search, segment tree | 10¹⁸ |
| O(√n) | Trial division, sqrt decomposition | 10¹² |
| O(n) | Linear scan, BFS, Union-Find | 10⁷ |
| O(n log n) | Merge sort, Dijkstra, segment tree build | 10⁶ |
| O(n²) | Floyd-Warshall, simple DP | 5000 |
| O(n³) | Matrix chain, Floyd-Warshall | 500 |
| O(2ⁿ) | Subset enumeration | 20-25 |
| O(n!) | Permutation enumeration | 10-11 |

### Space Complexity Notes

- Python lists: ~28 bytes per element overhead
- C++ vectors: ~4 bytes per int, ~8 bytes per pointer
- For n = 10⁶: ~4 MB for int array, ~8 MB for long long array
- 2D DP: n×m table uses O(n×m) space; often reducible to O(m) with rolling array

---

## 143.6 Pattern Recognition Templates

### Two Pointers

```cpp
// Sorted array: find pair with target sum
int left = 0, right = n - 1;
while (left < right) {
    int sum = arr[left] + arr[right];
    if (sum == target) { /* found */ break; }
    else if (sum < target) left++;
    else right--;
}
```

```python
# Sorted array: find pair with target sum
left, right = 0, len(arr) - 1
while left < right:
    s = arr[left] + arr[right]
    if s == target:
        break  # found
    elif s < target:
        left += 1
    else:
        right -= 1
```

```java
// Sorted array: find pair with target sum
int left = 0, right = arr.length - 1;
while (left < right) {
    int sum = arr[left] + arr[right];
    if (sum == target) { break; } // found
    else if (sum < target) left++;
    else right--;
}
```

### Sliding Window

```cpp
// Longest subarray with sum <= k
int left = 0, sum = 0, maxLen = 0;
for (int right = 0; right < n; right++) {
    sum += arr[right];
    while (sum > k) sum -= arr[left++];
    maxLen = max(maxLen, right - left + 1);
}
```

```python
# Longest subarray with sum <= k
left = s = max_len = 0
for right in range(len(arr)):
    s += arr[right]
    while s > k:
        s -= arr[left]
        left += 1
    max_len = max(max_len, right - left + 1)
```

```java
// Longest subarray with sum <= k
int left = 0, sum = 0, maxLen = 0;
for (int right = 0; right < n; right++) {
    sum += arr[right];
    while (sum > k) sum -= arr[left++];
    maxLen = Math.max(maxLen, right - left + 1);
}
```

### Binary Search on Answer

```cpp
// Minimum value that satisfies condition
int lo = minPossible, hi = maxPossible;
while (lo < hi) {
    int mid = lo + (hi - lo) / 2;
    if (condition(mid)) hi = mid;    // mid works, try smaller
    else lo = mid + 1;               // mid too small
}
// lo is the answer
```

```python
# Minimum value that satisfies condition
lo, hi = min_possible, max_possible
while lo < hi:
    mid = (lo + hi) // 2
    if condition(mid):
        hi = mid       # mid works, try smaller
    else:
        lo = mid + 1   # mid too small
# lo is the answer
```

```java
// Minimum value that satisfies condition
int lo = minPossible, hi = maxPossible;
while (lo < hi) {
    int mid = lo + (hi - lo) / 2;
    if (condition(mid)) hi = mid;
    else lo = mid + 1;
}
// lo is the answer
```

---

## 143.7 Interview Checklist

```
□ Clarify problem (2 min)
   - Input format, constraints, edge cases
   - Ask about duplicates, negatives, empty input
□ Work examples by hand (2 min)
   - At least 2 examples: normal + edge case
   - Trace through your intended approach
□ State approach + complexity (2 min)
   - "I'll use X because Y, time O(?), space O(?)"
   - Mention alternatives and why you chose this one
□ Code cleanly (10 min)
   - Meaningful variable names
   - Handle edge cases inline
   - Don't premature-optimize
□ Trace through example (2 min)
   - Walk through code with your example
   - Check off-by-one, boundary conditions
□ Test edge cases (2 min)
   - Empty input, single element, all same, sorted reverse
   - Integer overflow for large inputs
□ Discuss optimizations (if time)
   - Can you do better time? Better space?
   - Any preprocessing that helps?
```

---

## 143.8 Contest Quick Tips

| Tip | Explanation |
|---|---|
| Read all problems first | Spend 5 min reading; start with the easiest |
| Use fast I/O in C++ | `ios_base::sync_with_stdio(false); cin.tie(NULL);` |
| Python: use `sys.stdin` | `input()` is slow for large input |
| Precompute when possible | Factorials, powers, prefix sums |
| Modular arithmetic | Always mod after multiplication: `(a * b) % MOD` |
| Print intermediate results | Debug by printing state at key points |
| Don't overthink | If stuck 10 min, move to next problem |
| Template code | Have Union-Find, segment tree, etc. ready |

---

## 143.9 Language-Specific Gotchas

### C++

| Gotcha | Details |
|---|---|
| `vector<bool>` | Not a real vector; bit-packed; use `vector<char>` for speed |
| `map` vs `unordered_map` | `map` is O(log n), `unordered_map` is O(1) avg but can TLE with bad hash |
| `endl` vs `"\n"` | `endl` flushes; use `"\n"` for speed |
| Global arrays | Initialize to 0 by default; local arrays are garbage |
| `__builtin_popcount` | GCC built-in for bit counting |

### Python

| Gotcha | Details |
|---|---|
| Recursion limit | Default 1000; use `sys.setrecursionlimit(300000)` |
| Integer overflow | No issue; Python has arbitrary precision |
| List vs deque | `deque` for O(1) front operations |
| Dictionary ordering | Dicts preserve insertion order (Python 3.7+) |
| `range` is lazy | Doesn't create a list in Python 3 |

### Java

| Gotcha | Details |
|---|---|
| `Scanner` vs `BufferedReader` | `BufferedReader` is much faster |
| `Integer.MAX_VALUE` | Use for infinity in DP |
| `Arrays.sort` | Uses dual-pivot quicksort for primitives |
| Autoboxing | `int` vs `Integer`; prefer primitives in tight loops |
| `StringBuilder` | Use for string concatenation in loops |

---

## 143.10 Cross-References

| Topic | Related Chapter |
|---|---|
| Binary Search | Chapter 3 |
| Two Pointers | Chapter 5 |
| Sliding Window | Chapter 7 |
| Dynamic Programming | Chapter 20-30 |
| Graph Algorithms | Chapter 40-55 |
| Trees | Chapter 60-70 |
| Number Theory | Chapter 80-85 |
| Segment Trees | Chapter 90 |
| Interview Strategies | Chapter 150 |

---

## Summary

| Section | Purpose |
|---|---|
| Decision Tree | Map problem → technique in <2 min |
| STL Reference | Quick lookup for C++/Python APIs |
| Common Mistakes | Avoid the top 12 pitfalls |
| Complexity Cheat Sheet | Know your limits |
| Pattern Templates | Copy-paste-ready code |
| Interview Checklist | Structured 20-min approach |
| Contest Tips | Maximize score under time pressure |

**Key Insight:** The best interview performers don't know more algorithms — they **recognize patterns faster**. Use this chapter as a mental model to build that recognition.
