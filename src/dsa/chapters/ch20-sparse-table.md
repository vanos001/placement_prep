# Chapter 20: Sparse Table

## 20.1 Motivation

### Static Range Queries

Many problems ask for range queries on an array that **never changes**. For static arrays, we can preprocess information to answer queries in O(1) time.

The **Sparse Table** is a data structure that answers **idempotent** range queries in O(1) time after O(n log n) preprocessing.

**Idempotent operations**: An operation `f` is idempotent if `f(a, a) = a`. Examples:
- Minimum: `min(a, a) = a` ✓
- Maximum: `max(a, a) = a` ✓
- GCD: `gcd(a, a) = a` ✓
- Bitwise AND/OR: `a & a = a`, `a | a = a` ✓
- **Sum: `a + a ≠ a`** ✗ (NOT idempotent!)

### The Preprocessing Tradeoff

| Method | Preprocess | Query | Space | Notes |
|--------|-----------|-------|-------|-------|
| Brute force | O(1) | O(n) | O(n) | No preprocessing |
| Prefix sums | O(n) | O(1) | O(n) | Only for sums |
| Segment tree | O(n) | O(log n) | O(4n) | Handles updates |
| **Sparse table** | **O(n log n)** | **O(1)** | **O(n log n)** | **Static only, idempotent** |

The sparse table trades preprocessing time and space for O(1) queries. This is ideal when:
- The array is static (no updates)
- You need many queries (q >> n)
- The operation is idempotent

---

## 20.2 Construction

### The Key Idea

Precompute the answer for every range of length `2^j` starting at every index `i`.

Define `st[i][j]` = result of the operation on the range `[i, i + 2^j - 1]`, which is `2^j` elements starting at index `i`.

**Recurrence:**
```
st[i][0] = arr[i]                              (ranges of length 1)
st[i][j] = f(st[i][j-1], st[i + 2^(j-1)][j-1])  (ranges of length 2^j)
```

This splits a range of length `2^j` into two overlapping ranges of length `2^(j-1)`.

### Visual Diagram

For array `[2, 5, 3, 8, 1, 9, 4, 6]` with operation = min:

```
j=0 (length 1):  [2] [5] [3] [8] [1] [9] [4] [6]
j=1 (length 2):  [2,5] [3,5] [1,3] [1,8] [1,4] [4,6] ...
j=2 (length 4):  [1,2,3,5] [1,1,3,8] [1,1,4,6] ...
j=3 (length 8):  [1,2,3,5,1,8,9,4] → min = 1
```

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <functional>
#include <algorithm>
#include <climits>

class SparseTable {
private:
    std::vector<std::vector<int>> st;
    std::vector<int> logTable;
    int n;
    int maxLog;

public:
    // Build sparse table for range minimum query
    explicit SparseTable(const std::vector<int>& arr) {
        n = static_cast<int>(arr.size());
        maxLog = n > 0 ? static_cast<int>(std::log2(n)) + 1 : 0;

        // Precompute logarithms for O(1) lookup
        logTable.resize(n + 1);
        logTable[1] = 0;
        for (int i = 2; i <= n; ++i) {
            logTable[i] = logTable[i / 2] + 1;
        }

        // Build the sparse table
        st.assign(n, std::vector<int>(maxLog));

        // j = 0: ranges of length 1
        for (int i = 0; i < n; ++i) {
            st[i][0] = arr[i];
        }

        // j = 1, 2, ..., maxLog-1: ranges of length 2^j
        for (int j = 1; j < maxLog; ++j) {
            for (int i = 0; i + (1 << j) <= n; ++i) {
                st[i][j] = std::min(st[i][j - 1], st[i + (1 << (j - 1))][j - 1]);
            }
        }
    }

    // Range minimum query [l, r] inclusive — O(1)
    int query(int l, int r) const {
        int len = r - l + 1;
        int j = logTable[len];

        // Two overlapping ranges of length 2^j cover [l, r]
        // Range 1: [l, l + 2^j - 1]
        // Range 2: [r - 2^j + 1, r]
        return std::min(st[l][j], st[r - (1 << j) + 1][j]);
    }
};

int main() {
    std::vector<int> arr = {2, 5, 3, 8, 1, 9, 4, 6};
    SparseTable st(arr);

    std::cout << "Min [0,3]: " << st.query(0, 3) << "\n";  // min(2,5,3,8) = 2
    std::cout << "Min [2,5]: " << st.query(2, 5) << "\n";  // min(3,8,1,9) = 1
    std::cout << "Min [0,7]: " << st.query(0, 7) << "\n";  // min(2,5,3,8,1,9,4,6) = 1
    std::cout << "Min [4,6]: " << st.query(4, 6) << "\n";  // min(1,9,4) = 1

    return 0;
}
```

### Construction Dry Run

Array: `[2, 5, 3, 8, 1, 9, 4, 6]` (n = 8, maxLog = 3)

**j = 0 (length 1):**
```
st[0][0] = 2
st[1][0] = 5
st[2][0] = 3
st[3][0] = 8
st[4][0] = 1
st[5][0] = 9
st[6][0] = 4
st[7][0] = 6
```

**j = 1 (length 2):**
```
st[0][1] = min(st[0][0], st[1][0]) = min(2, 5) = 2
st[1][1] = min(st[1][0], st[2][0]) = min(5, 3) = 3
st[2][1] = min(st[2][0], st[3][0]) = min(3, 8) = 3
st[3][1] = min(st[3][0], st[4][0]) = min(8, 1) = 1
st[4][1] = min(st[4][0], st[5][0]) = min(1, 9) = 1
st[5][1] = min(st[5][0], st[6][0]) = min(9, 4) = 4
st[6][1] = min(st[6][0], st[7][0]) = min(4, 6) = 4
```

**j = 2 (length 4):**
```
st[0][2] = min(st[0][1], st[2][1]) = min(2, 3) = 2
st[1][2] = min(st[1][1], st[3][1]) = min(3, 1) = 1
st[2][2] = min(st[2][1], st[4][1]) = min(3, 1) = 1
st[3][2] = min(st[3][1], st[5][1]) = min(1, 4) = 1
st[4][2] = min(st[4][1], st[6][1]) = min(1, 4) = 1
```

### Space Complexity Analysis

The sparse table stores `n × log₂(n)` entries:
- n = 10^5: about 10^5 × 17 = 1.7 million integers
- n = 10^6: about 10^6 × 20 = 20 million integers

This fits comfortably in memory (about 80 MB for n = 10^6 with 4-byte integers).

---

## 20.3 Range Minimum Query — The Overlapping Intervals Technique

The magic of the sparse table's O(1) query lies in the **overlapping intervals technique**.

### Why Overlapping Works for Idempotent Operations

To query the minimum of range `[l, r]` (length = r - l + 1):

1. Find the largest `k` such that `2^k ≤ (r - l + 1)`, i.e., `k = ⌊log₂(r - l + 1)⌋`
2. Take the minimum of two ranges of length `2^k`:
   - Range 1: `[l, l + 2^k - 1]` (starts at l)
   - Range 2: `[r - 2^k + 1, r]` (ends at r)

These two ranges **overlap**, but that's fine! Because `min(a, a) = a`. The minimum of the two ranges is the same as the minimum of their union, which covers the entire query range.

```
Query [2, 6] on array [2, 5, 3, 8, 1, 9, 4, 6]:
  length = 5, k = floor(log2(5)) = 2, 2^k = 4

  Range 1: [2, 5] → min(3, 8, 1, 9) = 1
  Range 2: [3, 6] → min(8, 1, 9, 4) = 1

  Answer: min(1, 1) = 1

  Visual:    [2  5  3  8  1  9  4  6]
                   |--------|           Range 1: [2,5]
                      |--------|        Range 2: [3,6]
                   |=====|=====|        Query: [2,6] covered!
```

### Dry Run: Query [1, 5]

Array: `[2, 5, 3, 8, 1, 9, 4, 6]`
Query: min of [1, 5] = min(5, 3, 8, 1, 9) = 1

```
length = 5 - 1 + 1 = 5
k = floor(log2(5)) = 2
2^k = 4

Range 1: [1, 4] → st[1][2] = min(5,3,8,1) = 1
Range 2: [2, 5] → st[2][2] = min(3,8,1,9) = 1

Answer: min(1, 1) = 1 ✓
```

### Why This Doesn't Work for Sum

For sum queries, overlapping intervals give the wrong answer because `sum(a, a) = 2a ≠ a`.

```
Sum of [2, 6]:
  Range 1: [2, 5] → sum(3, 8, 1, 9) = 21
  Range 2: [3, 6] → sum(8, 1, 9, 4) = 22
  Overlap: [3, 5] → sum(8, 1, 9) = 18 (counted twice!)

  The sum would be 21 + 22 - 18 = 25 (if we could subtract)
  But sparse table doesn't store enough info for this subtraction.
```

For sum queries, use a prefix sum array (O(1) query) or a segment tree/Fenwick tree (O(log n) query with updates).

---

## 20.4 Applications

### Application 1: Range Maximum Query

Identical to RMQ but with `max` instead of `min`:

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

class MaxSparseTable {
private:
    std::vector<std::vector<int>> st;
    std::vector<int> logTable;
    int n, maxLog;

public:
    explicit MaxSparseTable(const std::vector<int>& arr) {
        n = static_cast<int>(arr.size());
        maxLog = n > 0 ? static_cast<int>(std::log2(n)) + 1 : 0;

        logTable.resize(n + 1);
        logTable[1] = 0;
        for (int i = 2; i <= n; ++i) {
            logTable[i] = logTable[i / 2] + 1;
        }

        st.assign(n, std::vector<int>(maxLog));
        for (int i = 0; i < n; ++i) st[i][0] = arr[i];

        for (int j = 1; j < maxLog; ++j) {
            for (int i = 0; i + (1 << j) <= n; ++i) {
                st[i][j] = std::max(st[i][j - 1], st[i + (1 << (j - 1))][j - 1]);
            }
        }
    }

    int query(int l, int r) const {
        int j = logTable[r - l + 1];
        return std::max(st[l][j], st[r - (1 << j) + 1][j]);
    }
};

int main() {
    std::vector<int> arr = {2, 5, 3, 8, 1, 9, 4, 6};
    MaxSparseTable st(arr);

    std::cout << "Max [0,3]: " << st.query(0, 3) << "\n";  // 8
    std::cout << "Max [2,5]: " << st.query(2, 5) << "\n";  // 9
    std::cout << "Max [0,7]: " << st.query(0, 7) << "\n";  // 9

    return 0;
}
```

### Application 2: Range GCD Query

GCD is idempotent: `gcd(a, a) = a`. So the sparse table works perfectly.

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>

class GCDSparseTable {
private:
    std::vector<std::vector<int>> st;
    std::vector<int> logTable;
    int n, maxLog;

    static int gcd(int a, int b) {
        while (b) { a %= b; std::swap(a, b); }
        return a;
    }

public:
    explicit GCDSparseTable(const std::vector<int>& arr) {
        n = static_cast<int>(arr.size());
        maxLog = n > 0 ? static_cast<int>(std::log2(n)) + 1 : 0;

        logTable.resize(n + 1);
        logTable[1] = 0;
        for (int i = 2; i <= n; ++i) logTable[i] = logTable[i / 2] + 1;

        st.assign(n, std::vector<int>(maxLog));
        for (int i = 0; i < n; ++i) st[i][0] = arr[i];

        for (int j = 1; j < maxLog; ++j) {
            for (int i = 0; i + (1 << j) <= n; ++i) {
                st[i][j] = gcd(st[i][j - 1], st[i + (1 << (j - 1))][j - 1]);
            }
        }
    }

    int query(int l, int r) const {
        int j = logTable[r - l + 1];
        return gcd(st[l][j], st[r - (1 << j) + 1][j]);
    }
};

int main() {
    std::vector<int> arr = {12, 18, 24, 30, 36, 48};
    GCDSparseTable st(arr);

    std::cout << "GCD [0,2]: " << st.query(0, 2) << "\n";  // gcd(12,18,24) = 6
    std::cout << "GCD [1,4]: " << st.query(1, 4) << "\n";  // gcd(18,24,30,36) = 6
    std::cout << "GCD [2,5]: " << st.query(2, 5) << "\n";  // gcd(24,30,36,48) = 6
    std::cout << "GCD [0,5]: " << st.query(0, 5) << "\n";  // gcd(12,18,24,30,36,48) = 6

    return 0;
}
```

### Application 3: Range AND/OR Query

Bitwise AND and OR are both idempotent: `a & a = a`, `a | a = a`.

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

class AndOrSparseTable {
private:
    std::vector<std::vector<int>> andSt, orSt;
    std::vector<int> logTable;
    int n, maxLog;

public:
    explicit AndOrSparseTable(const std::vector<int>& arr) {
        n = static_cast<int>(arr.size());
        maxLog = n > 0 ? static_cast<int>(std::log2(n)) + 1 : 0;

        logTable.resize(n + 1);
        logTable[1] = 0;
        for (int i = 2; i <= n; ++i) logTable[i] = logTable[i / 2] + 1;

        andSt.assign(n, std::vector<int>(maxLog));
        orSt.assign(n, std::vector<int>(maxLog));

        for (int i = 0; i < n; ++i) {
            andSt[i][0] = arr[i];
            orSt[i][0] = arr[i];
        }

        for (int j = 1; j < maxLog; ++j) {
            for (int i = 0; i + (1 << j) <= n; ++i) {
                andSt[i][j] = andSt[i][j - 1] & andSt[i + (1 << (j - 1))][j - 1];
                orSt[i][j] = orSt[i][j - 1] | orSt[i + (1 << (j - 1))][j - 1];
            }
        }
    }

    int queryAnd(int l, int r) const {
        int j = logTable[r - l + 1];
        return andSt[l][j] & andSt[r - (1 << j) + 1][j];
    }

    int queryOr(int l, int r) const {
        int j = logTable[r - l + 1];
        return orSt[l][j] | orSt[r - (1 << j) + 1][j];
    }
};

int main() {
    std::vector<int> arr = {7, 3, 5, 1, 6, 2, 8, 4};
    AndOrSparseTable st(arr);

    std::cout << "AND [0,3]: " << st.queryAnd(0, 3) << "\n";  // 7&3&5&1 = 1
    std::cout << "OR  [0,3]: " << st.queryOr(0, 3) << "\n";   // 7|3|5|1 = 7
    std::cout << "AND [4,7]: " << st.queryAnd(4, 7) << "\n";  // 6&2&8&4 = 0
    std::cout << "OR  [4,7]: " << st.queryOr(4, 7) << "\n";   // 6|2|8|4 = 14

    return 0;
}
```

### Application 4: Finding the Minimum Value and Its Count

Sometimes we need to know not just the minimum value but also how many times it appears in a range. This requires a modified sparse table that stores pairs.

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <climits>

class MinCountSparseTable {
private:
    // Each entry stores {minValue, count}
    std::vector<std::vector<std::pair<int, int>>> st;
    std::vector<int> logTable;
    int n, maxLog;

    static std::pair<int, int> combine(const std::pair<int, int>& a,
                                        const std::pair<int, int>& b) {
        if (a.first < b.first) return a;
        if (b.first < a.first) return b;
        return {a.first, a.second + b.second};  // Same min, add counts
    }

public:
    explicit MinCountSparseTable(const std::vector<int>& arr) {
        n = static_cast<int>(arr.size());
        maxLog = n > 0 ? static_cast<int>(std::log2(n)) + 1 : 0;

        logTable.resize(n + 1);
        logTable[1] = 0;
        for (int i = 2; i <= n; ++i) logTable[i] = logTable[i / 2] + 1;

        st.assign(n, std::vector<std::pair<int, int>>(maxLog));
        for (int i = 0; i < n; ++i) st[i][0] = {arr[i], 1};

        for (int j = 1; j < maxLog; ++j) {
            for (int i = 0; i + (1 << j) <= n; ++i) {
                st[i][j] = combine(st[i][j - 1], st[i + (1 << (j - 1))][j - 1]);
            }
        }
    }

    std::pair<int, int> query(int l, int r) const {
        int j = logTable[r - l + 1];
        return combine(st[l][j], st[r - (1 << j) + 1][j]);
    }
};

int main() {
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6, 5, 3};
    MinCountSparseTable st(arr);

    auto [minVal, count] = st.query(0, 4);
    std::cout << "Min [0,4]: " << minVal << " (count: " << count << ")\n";  // 1, count: 2

    auto [minVal2, count2] = st.query(5, 9);
    std::cout << "Min [5,9]: " << minVal2 << " (count: " << count2 << ")\n";  // 2, count: 1

    return 0;
}
```

### Application 5: Sparse Table for LCA (Preview)

The sparse table is a key component of the **Euler Tour + Sparse Table** approach to LCA queries (covered in Chapter 21). The idea:

1. Compute the Euler tour of the tree (visit each node multiple times)
2. Build a sparse table on the depths in the Euler tour
3. The LCA of two nodes is the node with minimum depth in the Euler tour between their first occurrences

This gives O(1) LCA queries after O(n log n) preprocessing.

---

## Generic Sparse Table Template

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <functional>
#include <climits>

template <typename T, typename Combine>
class GenericSparseTable {
private:
    std::vector<std::vector<T>> st;
    std::vector<int> logTable;
    int n, maxLog;
    T identity;
    Combine combine;

public:
    GenericSparseTable(const std::vector<T>& arr, T id, Combine comb)
        : n(static_cast<int>(arr.size())), identity(id), combine(comb) {
        maxLog = n > 0 ? static_cast<int>(std::log2(n)) + 1 : 0;

        logTable.resize(n + 1);
        logTable[1] = 0;
        for (int i = 2; i <= n; ++i) logTable[i] = logTable[i / 2] + 1;

        st.assign(n, std::vector<T>(maxLog, identity));
        for (int i = 0; i < n; ++i) st[i][0] = arr[i];

        for (int j = 1; j < maxLog; ++j) {
            for (int i = 0; i + (1 << j) <= n; ++i) {
                st[i][j] = combine(st[i][j - 1], st[i + (1 << (j - 1))][j - 1]);
            }
        }
    }

    T query(int l, int r) const {
        int j = logTable[r - l + 1];
        return combine(st[l][j], st[r - (1 << j) + 1][j]);
    }
};

int main() {
    std::vector<int> arr = {2, 5, 3, 8, 1, 9, 4, 6};

    // Range Minimum
    auto minSt = GenericSparseTable<int>(
        arr, INT_MAX, [](int a, int b) { return std::min(a, b); }
    );
    std::cout << "Min [1,5]: " << minSt.query(1, 5) << "\n";  // 1

    // Range Maximum
    auto maxSt = GenericSparseTable<int>(
        arr, INT_MIN, [](int a, int b) { return std::max(a, b); }
    );
    std::cout << "Max [1,5]: " << maxSt.query(1, 5) << "\n";  // 9

    // Range GCD
    auto gcdSt = GenericSparseTable<int>(
        arr, 0, [](int a, int b) {
            while (b) { a %= b; std::swap(a, b); }
            return a;
        }
    );
    std::vector<int> gcdArr = {12, 18, 24, 30};
    auto gcdSt2 = GenericSparseTable<int>(
        gcdArr, 0, [](int a, int b) {
            while (b) { a %= b; std::swap(a, b); }
            return a;
        }
    );
    std::cout << "GCD [0,3]: " << gcdSt2.query(0, 3) << "\n";  // 6

    return 0;
}
```

---

## Interview Tips

1. **Recognize sparse table problems**: Static array + many range queries (especially min/max/GCD) + need O(1) per query.

2. **The overlapping intervals trick**: Two ranges of length `2^k` that overlap still give the correct answer for idempotent operations. This is the core insight.

3. **Sparse table vs segment tree for RMQ**: Sparse table has O(1) query but O(n log n) space and can't handle updates. Segment tree has O(log n) query but O(n) space and handles updates. For static RMQ with many queries, sparse table wins.

4. **When to use sparse table**: Almost exclusively for static range queries where the operation is idempotent. If the array changes, use a segment tree.

5. **Precompute logarithms**: Don't call `log2()` in the query function. Precompute a lookup table for O(1) log access.

6. **Memory**: The `n × log n` table can be large. For n = 10^6, it's about 80 MB. Consider if this fits in the memory limit.

## Common Mistakes

1. **Using sparse table for sum queries**: Sum is not idempotent. The overlapping intervals technique gives wrong results for sum.

2. **Forgetting to check bounds**: In the construction, `i + (1 << j) <= n` must be strictly less than or equal. Off-by-one here causes out-of-bounds access.

3. **Using `log2()` directly**: The floating-point `log2()` can have precision issues. Use integer logarithm via a precomputed table.

4. **Wrong k computation in query**: `k = logTable[r - l + 1]`, not `k = r - l`. The log is of the range length, not the difference of indices.

5. **Index confusion**: The sparse table is typically 0-indexed for array positions but the log table is 1-indexed (since log(0) is undefined).

6. **Not considering memory limits**: For n = 10^7, the sparse table uses about 800 MB. This may exceed memory limits. Use a segment tree instead.

---

## Practice Problems

### Problem 1: Range Minimum Query — Static (SPOJ RMQSQ)
**Difficulty**: Easy
**Hint**: Build a sparse table for range minimum. Answer each query in O(1) using the overlapping intervals technique.

### Problem 2: Range GCD (Codeforces)
**Difficulty**: Medium
**Hint**: GCD is idempotent. Build a sparse table for range GCD queries.

### Problem 3: Maximum of All Subarrays of Size K (LeetCode 239)
**Difficulty**: Hard
**Hint**: Build a sparse table for range maximum. For each window of size k, query the maximum in O(1). Total: O(n log n) preprocessing + O(n) queries.

### Problem 4: Range AND/OR Queries (Various online judges)
**Difficulty**: Medium
**Hint**: Bitwise AND and OR are idempotent. Build sparse tables for both.

### Problem 5: Smallest Range Covering Elements from K Lists (LeetCode 632)
**Difficulty**: Hard
**Hint**: Merge all lists into one sorted array with list IDs. Use a sparse table for range maximum (to track which lists are covered).

### Problem 6: Count of Smaller Numbers After Self with Sparse Table variant
**Difficulty**: Hard
**Hint**: While sparse table isn't directly applicable, the binary lifting concept from sparse tables can inspire efficient solutions.

### Problem 7: Longest Continuous Subarray With Absolute Diff ≤ Limit (LeetCode 1438)
**Difficulty**: Medium
**Hint**: Use two sparse tables (one for min, one for max) with a sliding window approach.

### Problem 8: LCA using Euler Tour + Sparse Table (preview of Chapter 21)
**Difficulty**: Hard
**Hint**: Compute Euler tour of the tree. Build sparse table on depths. LCA of u and v is the node with minimum depth between their first occurrences in the Euler tour.

---

## See Also

- [Chapter 18: Segment Tree](ch18-segment-tree.md) — Supports dynamic updates; use when the array changes between queries.
- [Chapter 19: Fenwick Tree (Binary Indexed Tree)](ch19-fenwick-tree.md) — Another range query structure; BIT supports point updates with O(log n) queries.
- [Chapter 21: Binary Lifting and LCA](ch21-binary-lifting-lca.md) — Sparse table is the foundation for the O(1) LCA reduction via Euler tours.
- [Chapter 76: Advanced Segment Trees](ch76-advanced-seg-trees.md) — The RMQ ↔ LCA reduction and theoretical optimal static RMQ.

*Next chapter: [Chapter 21: Binary Lifting and Lowest Common Ancestor](ch21-binary-lifting-lca.md)*
