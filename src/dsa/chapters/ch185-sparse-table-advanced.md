# Chapter 185: Sparse Table — Advanced Techniques

The **sparse table** answers **Range Minimum Queries (RMQ)** in **O(1)** after O(n log n) preprocessing. It works for any **idempotent** operation (min, max, gcd, lcm, bitwise AND/OR) where `f(a, a) = a`.

---

## Core Structure

Precompute `st[k][i]` = result of the operation on the range `[i, i + 2^k - 1]`.

```cpp
const int LOG = 20;
int st[LOG][MAXN];
int log2[MAXN];

void build(vector<int>& a) {
    int n = a.size();
    log2[1] = 0;
    for (int i = 2; i <= n; i++) log2[i] = log2[i / 2] + 1;

    for (int i = 0; i < n; i++) st[0][i] = a[i];
    for (int k = 1; k < LOG; k++)
        for (int i = 0; i + (1 << k) <= n; i++)
            st[k][i] = min(st[k-1][i], st[k-1][i + (1 << (k-1))]);
}

int query(int l, int r) {
    int k = log2[r - l + 1];
    return min(st[k][l], st[k][r - (1 << k) + 1]);
}
```

**Complexity:** Preprocessing O(n log n), query O(1), space O(n log n).

---

## Walkthrough

Array: `[3, 1, 4, 1, 5, 9, 2, 6]`. Query RMQ(2, 6).

| k | Range length | st[k][2] |
|---|---|---|
| 0 | 1 | a[2] = 4 |
| 1 | 2 | min(4, 1) = 1 |
| 2 | 4 | min(1, 5) = 1 |

Query(2,6): length=5, k=floor(log₂5)=2. Answer = min(st[2][2], st[2][3]) = min(1, 1) = **1**.

---

## Sparse Table vs Segment Tree

| Feature | Sparse Table | Segment Tree |
|---|---|---|
| Query time | O(1) | O(log n) |
| Preprocessing | O(n log n) | O(n) |
| Updates | Not supported (static) | O(log n) |
| Operations | Idempotent only | Any associative op |
| Space | O(n log n) | O(n) |

---

## Extensions

- **2D Sparse Table:** O(1) RMQ on matrices — O(nm log n log m) space.
- **Disjoint Sparse Table:** Supports queries where the range midpoint is unknown — useful for offline RMQ with overlapping ranges.
- **GCD/LCM queries:** gcd is idempotent, so sparse table works directly.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Using sparse table for sum queries | Sum is not idempotent; overlapping ranges double-count |
| Trying to update the array | Sparse table is static; use segment tree instead |
| Off-by-one in query | `r - (1<<k) + 1` ensures non-overlapping coverage |

---

## Practice Problems

| # | Problem | Hint |
|---|---|---|
| 1 | Range Minimum Query (SPOJ RMQSQ) | Build sparse table for min |
| 2 | GCD on Subarrays | gcd is idempotent — use sparse table |
| 3 | LCA with RMQ (Euler tour) | Reduce LCA to RMQ via Euler tour + depth array |
| 4 | Sparse Table with OR | Bitwise OR is idempotent |
| 5 | 2D Minimum on Submatrix | Extend to 2D sparse table |
| 6 | Static Range Frequency | Combine with coordinate compression |

---

## See Also

- [Chapter 20: Sparse Table — Fundamentals](ch20-sparse-table.md)
- [Chapter 18: Segment Tree](ch18-segment-tree.md)
- [Chapter 21: Binary Lifting & LCA](ch21-binary-lifting-lca.md)
- [Chapter 181: Fenwick Tree — Advanced](ch181-fenwick-tree-advanced.md)
