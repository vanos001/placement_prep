# Chapter 181: Fenwick Tree — Advanced Applications

The Binary Indexed Tree (BIT) supports **point update + prefix sum** in O(log n). While the basics are covered in [Chapter 19](ch19-fenwick-tree.md), this chapter explores range queries, 2D extensions, and competitive-programming tricks.

---

## Core: Point Update + Prefix Sum

A BIT stores partial sums at indices that are powers of two. Update adds a value to index `i` by propagating to ancestors; query aggregates from index `i` down to zero.

```cpp
struct BIT {
    int n; vector<long long> tree;
    BIT(int n) : n(n), tree(n + 1, 0) {}
    void update(int i, long long v) {
        for (++i; i <= n; i += i & -i) tree[i] += v;
    }
    long long query(int i) {
        long long s = 0;
        for (++i; i > 0; i -= i & -i) s += tree[i];
        return s;
    }
};
```

**Complexity:** O(log n) per operation, O(n) space.

---

## Range Queries

Range sum `[l, r]` = `query(r) - query(l-1)`. For range update + point query, invert the structure: use a BIT of *differences*.

| Operation | Method | Time |
|---|---|---|
| Point update, prefix query | Standard BIT | O(log n) |
| Point update, range query | Two BITs (range update trick) | O(log n) |
| Range update, point query | BIT on differences | O(log n) |
| Range update, range query | Two BITs | O(log n) |

---

## 2D BIT

For a matrix, nest the BIT: each node contains another BIT over the second dimension.

```cpp
struct BIT2D {
    int n, m;
    vector<vector<int>> tree;
    void update(int x, int y, int v) {
        for (int i = x; i <= n; i += i & -i)
            for (int j = y; j <= m; j += j & -j)
                tree[i][j] += v;
    }
    int query(int x, int y) {
        int s = 0;
        for (int i = x; i > 0; i -= i & -i)
            for (int j = y; j > 0; j -= j & -j)
                s += tree[i][j];
        return s;
    }
};
```

**Complexity:** O(log² n) per operation, O(n²) space.

---

## Walkthrough: Inversion Count

Given `[3, 1, 2]`, count inversions. Process right to left, querying how many elements smaller than `a[i]` have been seen.

| Step | Element | BIT state | Query (a[i]-1) | Inversions |
|---|---|---|---|---|
| 1 | 2 | [0,0,1,0] | 0 | 0 |
| 2 | 1 | [0,1,1,0] | 0 | 0 |
| 3 | 3 | [0,1,1,1] | 2 | **2** |

Result: 2 inversions (3>1, 3>2).

---

## Variations & Extensions

- **Fenwick tree on frequencies** — order-statistic tree (k-th smallest in O(log n)).
- **Persistent BIT** — query state at any prior point in time.
- **Compressed coordinates** — map values to rank when values are large but sparse.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| 1-indexed vs 0-indexed confusion | BIT is 1-indexed internally; adapt your interface |
| Forgetting coordinate compression | Always compress before using values as indices |
| Using BIT for non-invertible operations | BIT requires the operation to have an inverse (subtraction undoes addition) |

---

## Practice Problems

| # | Problem | Hint |
|---|---|---|
| 1 | Count Inversions (LeetCode / CF) | Process right-to-left, query prefix sums |
| 2 | Range Sum Query — Mutable (LeetCode 307) | Standard point update + range query |
| 3 | Count of Range Sum (LeetCode 327) | Prefix sums + BIT with coordinate compression |
| 4 | 2D Range Sum Query (LeetCode 308) | Use 2D BIT |
| 5 | K-th Number in a Range | Fenwick order-statistic tree |
| 6 | Rectangle Area II (LeetCode 850) | Sweep line + BIT |

---

## See Also

- [Chapter 19: Fenwick Tree — Fundamentals](ch19-fenwick-tree.md)
- [Chapter 18: Segment Tree](ch18-segment-tree.md)
- [Chapter 36: Prefix Sum & Difference Array](ch36-prefix-sum-diff-array.md)
- [Chapter 130: Coordinate Compression](ch130-coordinate-compression.md)
