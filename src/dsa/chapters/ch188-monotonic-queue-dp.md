# Chapter 188: Monotonic Queue/Deque Optimization

A **monotonic deque** maintains elements in monotonic (increasing or decreasing) order. It is the key to solving **sliding window maximum/minimum** in O(n) and optimizing certain DP transitions from O(n²) to O(n).

---

## Sliding Window Maximum in O(n)

Given an array and window size k, find the maximum in every window.

```cpp
vector<int> slidingMax(const vector<int>& a, int k) {
    deque<int> dq; // stores indices, values in decreasing order
    vector<int> result;
    for (int i = 0; i < (int)a.size(); i++) {
        // Remove elements outside the window
        while (!dq.empty() && dq.front() <= i - k) dq.pop_front();
        // Maintain decreasing order
        while (!dq.empty() && a[dq.back()] <= a[i]) dq.pop_back();
        dq.push_back(i);
        if (i >= k - 1) result.push_back(a[dq.front()]);
    }
    return result;
}
```

**Complexity:** O(n) time (each element pushed and popped at most once), O(k) space.

---

## Walkthrough

Array: `[3, 1, 4, 1, 5, 9, 2]`, k = 3.

| i | a[i] | Deque (indices) | Window max |
|---|---|---|---|
| 0 | 3 | [0] | — |
| 1 | 1 | [0, 1] | — |
| 2 | 4 | [2] | 4 |
| 3 | 1 | [2, 3] | 4 |
| 4 | 5 | [4] | 5 |
| 5 | 9 | [5] | 9 |
| 6 | 2 | [5, 6] | 9 |

---

## DP Optimization: Monotone Queue Convex Hull Trick

When a DP transition has the form:

``ndp[i] = min over j in [i-k, i-1] of (dp[j] + cost(j, i))```

and the cost satisfies a **monotonicity condition** on the optimal transition point, a monotonic deque maintains candidate indices. This reduces the inner loop from O(k) to O(1) amortized.

Typical structure:

```cpp
for (int i = 1; i <= n; i++) {
    while (!dq.empty() && i - dq.front() > k) dq.pop_front();
    ndp[i] = dp[dq.front()] + cost(dq.front(), i);
    while (!dq.empty() && dp[dq.back()] >= dp[i]) dq.pop_back();
    dq.push_back(i);
}
```

---

## Multi-Set Alternative

When monotonicity of the deque property doesn't hold (arbitrary insertions and deletions), use a `multiset` (C++) or `SortedDict` (Python). Insertion and deletion are O(log n).

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Popping from wrong end | Max deque: pop smaller from **back**, expired from **front** |
| Forgetting to check window bounds | Always pop front when index is out of range |
| Using monotonic queue for non-monotonic costs | Verify the DP cost function satisfies the monotonicity requirement |

---

## Practice Problems

| # | Problem | Hint |
|---|---|
| 1 | Sliding Window Maximum (LeetCode 239) | Classic deque problem |
| 2 | Shortest Subarray with Sum at Least K (LeetCode 862) | Monotonic deque on prefix sums |
| 3 | Jump Game VI (LeetCode 1696) | DP + monotonic deque for max dp[j] in range |
| 4 | Constrained Subsequence Sum (LeetCode 1425) | DP with deque, track max in last k |
| 5 | Largest Subarray with Length K (variant) | Maintain deque of candidates |
| 6 | Rectangle Area in Histogram | Use monotonic stack (variant) — same principle |

---

## See Also

- [Chapter 38: Monotonic Queue](ch38-monotonic-queue.md)
- [Chapter 117: Monotone Queue Optimization](ch117-monotone-queue-optimization.md)
- [Chapter 37: Monotonic Stack](ch37-monotonic-stack.md)
- [Chapter 35: Sliding Window](ch35-sliding-window.md)
