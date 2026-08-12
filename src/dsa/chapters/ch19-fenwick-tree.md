# Chapter 19: Fenwick Tree (Binary Indexed Tree)

## 19.1 Motivation

The **Fenwick Tree**, also known as a **Binary Indexed Tree (BIT)**, was invented by Peter M. Fenwick in 1994. It provides an elegant, space-efficient solution for maintaining prefix sums with point updates.

### The Problem

Given an array, support two operations:
1. **Update**: Change the value at a specific index
2. **Prefix Query**: Compute the sum of elements from index 0 to index i

| Approach | Update | Prefix Query | Space |
|----------|--------|--------------|-------|
| Plain array | O(1) | O(n) | O(n) |
| Prefix sum array | O(n) | O(1) | O(n) |
| Segment tree | O(log n) | O(log n) | O(4n) |
| **Fenwick tree** | **O(log n)** | **O(log n)** | **O(n)** |

The Fenwick tree achieves the same time complexity as a segment tree but with:
- **Simpler code** (often 10-15 lines)
- **Less memory** (exactly n elements, not 4n)
- **Better constants** (fewer operations per query/update)

### When to Use Fenwick Tree

- Point update + prefix/range sum queries
- Counting inversions
- Counting elements less than a given value
- Any problem that can be reduced to prefix sums

**Limitation**: Fenwick trees are naturally suited for prefix operations. For arbitrary range operations (min, max, GCD) with range updates, segment trees are more flexible.

---

## 19.2 Structure

### Binary Representation and the Least Significant Bit

The key to understanding the Fenwick tree lies in the **least significant bit (LSB)** of an index.

For a 1-indexed array, the LSB of index `i` is `i & (-i)`:

```
i (decimal)  i (binary)  LSB (i & -i)
1            0001        1
2            0010        2
3            0011        1
4            0100        4
5            0101        1
6            0110        2
7            0111        1
8            1000        8
9            1001        1
10           1010        2
11           1011        1
12           1100        4
```

**What does LSB tell us?** The index `i` in the Fenwick tree is responsible for a range of `LSB(i)` elements ending at `i`.

### How the Tree is Structured

In a Fenwick tree, each index `i` stores the sum of a specific range of the original array:

```
Index 1 (LSB=1):  stores sum of arr[1..1]     (1 element)
Index 2 (LSB=2):  stores sum of arr[1..2]     (2 elements)
Index 3 (LSB=1):  stores sum of arr[3..3]     (1 element)
Index 4 (LSB=4):  stores sum of arr[1..4]     (4 elements)
Index 5 (LSB=1):  stores sum of arr[5..5]     (1 element)
Index 6 (LSB=2):  stores sum of arr[5..6]     (2 elements)
Index 7 (LSB=1):  stores sum of arr[7..7]     (1 element)
Index 8 (LSB=8):  stores sum of arr[1..8]     (8 elements)
```

### Visual Diagram (1-indexed)

For array `[0, 1, 2, 3, 4, 5, 6, 7]` (index 0 unused):

```
Fenwick tree structure:

Index:   1    2    3    4    5    6    7    8
Covers: [1] [1,2] [3] [1..4] [5] [5,6] [7] [1..8]

Parent-child relationships (parent = i + LSB(i)):
- 1 → 2 → 4 → 8
- 3 → 4 → 8
- 5 → 6 → 8
- 7 → 8

Children of index i (children = i - LSB(i), i - LSB(i) - LSB(that), ...):
- 8 covers [1..8], children: 4, 6, 7
- 4 covers [1..4], children: 2, 3
- 6 covers [5..6], children: 5
```

**The insight**: The Fenwick tree is organized by the binary representation of indices. Each bit position corresponds to a "level" in the tree, and the LSB determines the range size.

---

## 19.3 Operations

### Core Operations

1. **Prefix Query (sum from 1 to i)**: Start at index `i`, repeatedly subtract `LSB(i)` and accumulate.

2. **Point Update (add value to index i)**: Start at index `i`, repeatedly add `LSB(i)` and update.

These two operations are **duals** of each other — one walks "up" the tree by adding LSB, the other walks "down" by subtracting LSB.

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <cassert>

class FenwickTree {
private:
    std::vector<long long> tree;
    int n;

public:
    // Constructor: initialize with zeros
    explicit FenwickTree(int size) : n(size), tree(size + 1, 0) {}

    // Constructor: build from array (O(n) construction)
    explicit FenwickTree(const std::vector<int>& arr)
        : n(static_cast<int>(arr.size())), tree(arr.size() + 1, 0) {
        // Method 1: O(n log n) — simple
        // for (int i = 0; i < n; ++i) {
        //     add(i + 1, arr[i]);
        // }

        // Method 2: O(n) — optimal
        for (int i = 0; i < n; ++i) {
            tree[i + 1] = arr[i];
        }
        for (int i = 1; i <= n; ++i) {
            int parent = i + (i & (-i));
            if (parent <= n) {
                tree[parent] += tree[i];
            }
        }
    }

    // Add val to element at index i (1-indexed)
    // Time: O(log n)
    void add(int i, long long val) {
        while (i <= n) {
            tree[i] += val;
            i += i & (-i);  // Move to parent: i += LSB(i)
        }
    }

    // Prefix sum: sum of elements from 1 to i (1-indexed)
    // Time: O(log n)
    long long prefixSum(int i) const {
        long long sum = 0;
        while (i > 0) {
            sum += tree[i];
            i -= i & (-i);  // Move to next range: i -= LSB(i)
        }
        return sum;
    }

    // Range sum: sum of elements from l to r (1-indexed, inclusive)
    // Time: O(log n)
    long long rangeSum(int l, int r) const {
        return prefixSum(r) - prefixSum(l - 1);
    }

    // Update: set element at index i to val (1-indexed)
    // Time: O(log n) — requires knowing the current value
    void set(int i, long long val) {
        long long current = rangeSum(i, i);
        add(i, val - current);
    }
};

int main() {
    // Example: 1-indexed array [1, 3, 5, 7, 9, 11]
    std::vector<int> arr = {1, 3, 5, 7, 9, 11};
    FenwickTree ft(arr);

    // Prefix sums
    std::cout << "Prefix sum [1..3]: " << ft.prefixSum(3) << "\n";  // 1+3+5 = 9
    std::cout << "Prefix sum [1..6]: " << ft.prefixSum(6) << "\n";  // 36

    // Range sums
    std::cout << "Range sum [2..4]: " << ft.rangeSum(2, 4) << "\n";  // 3+5+7 = 15

    // Update: add 10 to index 3
    ft.add(3, 10);

    std::cout << "Prefix sum [1..3] after add: " << ft.prefixSum(3) << "\n";  // 1+3+15 = 19
    std::cout << "Range sum [2..4] after add: " << ft.rangeSum(2, 4) << "\n";  // 3+15+7 = 25

    return 0;
}
```

### Python — Fenwick Tree

```python
class FenwickTree:
    def __init__(self, arr):
        self.n = len(arr)
        self.tree = [0] * (self.n + 1)
        # O(n) construction
        for i in range(self.n):
            self.tree[i + 1] = arr[i]
        for i in range(1, self.n + 1):
            parent = i + (i & (-i))
            if parent <= self.n:
                self.tree[parent] += self.tree[i]

    def add(self, i, val):
        """Add val to element at index i (1-indexed)."""
        while i <= self.n:
            self.tree[i] += val
            i += i & (-i)

    def prefix_sum(self, i):
        """Prefix sum from 1 to i (1-indexed)."""
        s = 0
        while i > 0:
            s += self.tree[i]
            i -= i & (-i)
        return s

    def range_sum(self, l, r):
        """Range sum from l to r (1-indexed, inclusive)."""
        return self.prefix_sum(r) - self.prefix_sum(l - 1)


if __name__ == "__main__":
    arr = [1, 3, 5, 7, 9, 11]
    ft = FenwickTree(arr)

    print(f"Prefix sum [1..3]: {ft.prefix_sum(3)}")  # 9
    print(f"Prefix sum [1..6]: {ft.prefix_sum(6)}")  # 36
    print(f"Range sum [2..4]: {ft.range_sum(2, 4)}")  # 15

    ft.add(3, 10)
    print(f"Prefix sum [1..3] after add: {ft.prefix_sum(3)}")  # 19
    print(f"Range sum [2..4] after add: {ft.range_sum(2, 4)}")  # 25
```

### Java — Fenwick Tree

```java
public class FenwickTree {
    private long[] tree;
    private int n;

    public FenwickTree(int[] arr) {
        this.n = arr.length;
        this.tree = new long[n + 1];
        // O(n) construction
        for (int i = 0; i < n; i++) {
            tree[i + 1] = arr[i];
        }
        for (int i = 1; i <= n; i++) {
            int parent = i + (i & (-i));
            if (parent <= n) {
                tree[parent] += tree[i];
            }
        }
    }

    public void add(int i, long val) {
        while (i <= n) {
            tree[i] += val;
            i += i & (-i);
        }
    }

    public long prefixSum(int i) {
        long sum = 0;
        while (i > 0) {
            sum += tree[i];
            i -= i & (-i);
        }
        return sum;
    }

    public long rangeSum(int l, int r) {
        return prefixSum(r) - prefixSum(l - 1);
    }

    public static void main(String[] args) {
        int[] arr = {1, 3, 5, 7, 9, 11};
        FenwickTree ft = new FenwickTree(arr);

        System.out.println("Prefix sum [1..3]: " + ft.prefixSum(3));  // 9
        System.out.println("Prefix sum [1..6]: " + ft.prefixSum(6));  // 36
        System.out.println("Range sum [2..4]: " + ft.rangeSum(2, 4));  // 15

        ft.add(3, 10);
        System.out.println("Prefix sum [1..3] after add: " + ft.prefixSum(3));  // 19
        System.out.println("Range sum [2..4] after add: " + ft.rangeSum(2, 4));  // 25
    }
}
```

### Dry Run: Prefix Query

Array: `[1, 3, 5, 7, 9, 11]` (1-indexed)
Fenwick tree: `[0, 1, 4, 5, 16, 9, 20, 7, 36]`

**Query: prefixSum(5)** — sum of elements 1 through 5 = 1+3+5+7+9 = 25

```
i = 5 (binary: 101, LSB = 1)
  sum += tree[5] = 9
  i = 5 - 1 = 4

i = 4 (binary: 100, LSB = 4)
  sum += tree[4] = 16
  i = 4 - 4 = 0

i = 0 → stop

Result: 9 + 16 = 25 ✓
```

**Why does this work?**
- tree[5] = sum of arr[5..5] = 9 (the element at index 5)
- tree[4] = sum of arr[1..4] = 1+3+5+7 = 16
- Together: 9 + 16 = 25 = sum of arr[1..5]

### Dry Run: Point Update

**Update: add 10 to index 3**

```
i = 3 (binary: 011, LSB = 1)
  tree[3] += 10 → tree[3] = 5 + 10 = 15
  i = 3 + 1 = 4

i = 4 (binary: 100, LSB = 4)
  tree[4] += 10 → tree[4] = 16 + 10 = 26
  i = 4 + 4 = 8

i = 8 (binary: 1000, LSB = 8)
  tree[8] += 10 → tree[8] = 36 + 10 = 46
  i = 8 + 8 = 16

i = 16 > n → stop
```

Updated tree: `[0, 1, 4, 15, 26, 9, 20, 7, 46]`

Verification: prefixSum(3) = tree[3] + tree[2] = 15 + 4 = 19 = 1+3+15 ✓

### Bit Manipulation Explanation

```cpp
// Get the least significant bit (LSB)
int lsb(int i) {
    return i & (-i);
}

// Why does i & (-i) work?
// -i is the two's complement of i: flip all bits, then add 1
// This isolates the rightmost set bit

// Example: i = 12 = 1100 in binary
// -i     = ...0100 in two's complement
// i & -i = 0100 = 4 = LSB(12)

// Walk to parent (for update):
// i += LSB(i)  →  jumps over the range this index covers

// Walk to next range (for query):
// i -= LSB(i)  →  removes the range this index covers
```

### Finding the Parent and Children

```cpp
// Parent of index i (for update traversal):
// parent(i) = i + (i & (-i))

// Children of index i (for query traversal):
// child(i) = i - (i & (-i))

// Example for index 8:
// Children: 8-8=0 (none), but covers indices that sum to 8:
//   8 → 4 → 2 → 1 (following child pointers)
//   8 → 6 → 4 → 2 → 1 (also valid path)
```

---

## 19.4 Range Update, Point Query

A standard Fenwick tree supports point update and prefix query. But with a clever trick, we can support **range update** and **point query** using a **difference array**.

### The Difference Array Trick

Given array `arr`, define `diff[i] = arr[i] - arr[i-1]` (with `arr[0] = 0`).

To add `val` to all elements in range `[l, r]`:
- `diff[l] += val`
- `diff[r+1] -= val`

To get `arr[i]`: just compute `prefixSum(i)` on the diff array.

```cpp
#include <iostream>
#include <vector>

class RangeUpdateFenwick {
private:
    std::vector<long long> tree;
    int n;

public:
    explicit RangeUpdateFenwick(int size) : n(size), tree(size + 2, 0) {}

    // Internal: add val to element at index i (1-indexed)
    void add(int i, long long val) {
        while (i <= n) {
            tree[i] += val;
            i += i & (-i);
        }
    }

    // Range update: add val to all elements in [l, r] (1-indexed)
    void rangeUpdate(int l, int r, long long val) {
        add(l, val);
        add(r + 1, -val);
    }

    // Point query: get value at index i (1-indexed)
    long long pointQuery(int i) const {
        long long sum = 0;
        while (i > 0) {
            sum += tree[i];
            i -= i & (-i);
        }
        return sum;
    }
};

int main() {
    // Start with array [0, 0, 0, 0, 0, 0]
    RangeUpdateFenwick ft(6);

    // Add 5 to range [2, 4]
    ft.rangeUpdate(2, 4, 5);

    // Add 3 to range [1, 3]
    ft.rangeUpdate(1, 3, 3);

    // Array is now [3, 8, 8, 5, 0, 0]
    for (int i = 1; i <= 6; ++i) {
        std::cout << "arr[" << i << "] = " << ft.pointQuery(i) << "\n";
    }

    return 0;
}
```

### Range Update + Range Query

To support **both** range update and range query simultaneously, we need **two** Fenwick trees.

The trick: maintain `B1` for the difference array and `B2` for a correction term. The prefix sum up to index `x` is:

```
prefixSum(x) = B1.prefixSum(x) * x - B2.prefixSum(x)
```

```cpp
#include <iostream>
#include <vector>

class RangeUpdateRangeQueryFenwick {
private:
    std::vector<long long> B1, B2;
    int n;

    void add(std::vector<long long>& tree, int i, long long val) {
        while (i <= n) {
            tree[i] += val;
            i += i & (-i);
        }
    }

    long long prefixSum(const std::vector<long long>& tree, int i) const {
        long long sum = 0;
        while (i > 0) {
            sum += tree[i];
            i -= i & (-i);
        }
        return sum;
    }

public:
    explicit RangeUpdateRangeQueryFenwick(int size)
        : n(size), B1(size + 2, 0), B2(size + 2, 0) {}

    // Add val to all elements in [l, r] (1-indexed)
    void rangeUpdate(int l, int r, long long val) {
        add(B1, l, val);
        add(B1, r + 1, -val);
        add(B2, l, val * (l - 1));
        add(B2, r + 1, -val * r);
    }

    // Prefix sum from 1 to i (1-indexed)
    long long prefixSum(int i) const {
        return prefixSum(B1, i) * i - prefixSum(B2, i);
    }

    // Range sum from l to r (1-indexed)
    long long rangeSum(int l, int r) const {
        return prefixSum(r) - prefixSum(l - 1);
    }
};

int main() {
    RangeUpdateRangeQueryFenwick ft(6);

    // Add 5 to range [2, 4]
    ft.rangeUpdate(2, 4, 5);

    // Add 3 to range [1, 3]
    ft.rangeUpdate(1, 3, 3);

    // Array: [3, 8, 8, 5, 0, 0]
    std::cout << "Range sum [1,3]: " << ft.rangeSum(1, 3) << "\n";  // 3+8+8 = 19
    std::cout << "Range sum [2,5]: " << ft.rangeSum(2, 5) << "\n";  // 8+8+5+0 = 21

    return 0;
}
```

---

## 19.5 2D Fenwick Tree

A 2D Fenwick tree extends the concept to a grid, supporting point updates and 2D prefix sum queries.

### Structure

For a grid of size `n × m`, the 2D Fenwick tree stores:

```
tree[i][j] = sum of a rectangle of cells determined by the LSBs of i and j
```

Operations follow the same principle but with two nested loops.

```cpp
#include <iostream>
#include <vector>

class FenwickTree2D {
private:
    std::vector<std::vector<long long>> tree;
    int rows, cols;

    // Add val to cell (r, c) — internal helper
    void add(int r, int c, long long val) {
        for (int i = r; i <= rows; i += i & (-i)) {
            for (int j = c; j <= cols; j += j & (-j)) {
                tree[i][j] += val;
            }
        }
    }

    // Prefix sum from (1,1) to (r, c)
    long long prefixSum(int r, int c) const {
        long long sum = 0;
        for (int i = r; i > 0; i -= i & (-i)) {
            for (int j = c; j > 0; j -= j & (-j)) {
                sum += tree[i][j];
            }
        }
        return sum;
    }

public:
    FenwickTree2D(int r, int c) : rows(r), cols(c), tree(r + 1, std::vector<long long>(c + 1, 0)) {}

    // Update cell (r, c) by adding val (1-indexed)
    void update(int r, int c, long long val) {
        add(r, c, val);
    }

    // Sum of rectangle from (r1, c1) to (r2, c2) inclusive (1-indexed)
    long long rangeSum(int r1, int c1, int r2, int c2) const {
        return prefixSum(r2, c2)
             - prefixSum(r1 - 1, c2)
             - prefixSum(r2, c1 - 1)
             + prefixSum(r1 - 1, c1 - 1);
    }
};

int main() {
    // 4x4 grid
    FenwickTree2D ft(4, 4);

    // Set some values
    ft.update(1, 1, 1);
    ft.update(1, 3, 2);
    ft.update(2, 2, 3);
    ft.update(3, 1, 4);
    ft.update(3, 3, 5);
    ft.update(4, 4, 6);

    /*
    Grid:
    1  0  2  0
    0  3  0  0
    4  0  5  0
    0  0  0  6
    */

    std::cout << "Sum [1,1]-[2,2]: " << ft.rangeSum(1, 1, 2, 2) << "\n";  // 1+0+0+3 = 4
    std::cout << "Sum [1,1]-[4,4]: " << ft.rangeSum(1, 1, 4, 4) << "\n";  // 21
    std::cout << "Sum [2,2]-[4,4]: " << ft.rangeSum(2, 2, 4, 4) << "\n";  // 3+0+0+5+0+0+0+6 = 14

    // Update cell (2,2) by adding 10
    ft.update(2, 2, 10);

    std::cout << "Sum [1,1]-[2,2] after update: " << ft.rangeSum(1, 1, 2, 2) << "\n";  // 14

    return 0;
}
```

**Complexity**: Each operation is O(log n × log m) for an n × m grid.

### Python — 2D Fenwick Tree

```python
class FenwickTree2D:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.tree = [[0] * (cols + 1) for _ in range(rows + 1)]

    def _add(self, r, c, val):
        i = r
        while i <= self.rows:
            j = c
            while j <= self.cols:
                self.tree[i][j] += val
                j += j & (-j)
            i += i & (-i)

    def _prefix_sum(self, r, c):
        total = 0
        i = r
        while i > 0:
            j = c
            while j > 0:
                total += self.tree[i][j]
                j -= j & (-j)
            i -= i & (-i)
        return total

    def update(self, r, c, val):
        """Add val to cell (r, c), 1-indexed."""
        self._add(r, c, val)

    def range_sum(self, r1, c1, r2, c2):
        """Sum of rectangle (r1,c1) to (r2,c2), 1-indexed, inclusive."""
        return (self._prefix_sum(r2, c2)
                - self._prefix_sum(r1 - 1, c2)
                - self._prefix_sum(r2, c1 - 1)
                + self._prefix_sum(r1 - 1, c1 - 1))


if __name__ == "__main__":
    ft = FenwickTree2D(4, 4)
    ft.update(1, 1, 1)
    ft.update(1, 3, 2)
    ft.update(2, 2, 3)
    ft.update(3, 1, 4)
    ft.update(3, 3, 5)
    ft.update(4, 4, 6)

    print(f"Sum [1,1]-[2,2]: {ft.range_sum(1, 1, 2, 2)}")  # 4
    print(f"Sum [1,1]-[4,4]: {ft.range_sum(1, 1, 4, 4)}")  # 21
    print(f"Sum [2,2]-[4,4]: {ft.range_sum(2, 2, 4, 4)}")  # 14

    ft.update(2, 2, 10)
    print(f"Sum [1,1]-[2,2] after update: {ft.range_sum(1, 1, 2, 2)}")  # 14
```

### Java — 2D Fenwick Tree

```java
public class FenwickTree2D {
    private long[][] tree;
    private int rows, cols;

    public FenwickTree2D(int rows, int cols) {
        this.rows = rows;
        this.cols = cols;
        this.tree = new long[rows + 1][cols + 1];
    }

    private void add(int r, int c, long val) {
        for (int i = r; i <= rows; i += i & (-i)) {
            for (int j = c; j <= cols; j += j & (-j)) {
                tree[i][j] += val;
            }
        }
    }

    private long prefixSum(int r, int c) {
        long sum = 0;
        for (int i = r; i > 0; i -= i & (-i)) {
            for (int j = c; j > 0; j -= j & (-j)) {
                sum += tree[i][j];
            }
        }
        return sum;
    }

    public void update(int r, int c, long val) {
        add(r, c, val);
    }

    public long rangeSum(int r1, int c1, int r2, int c2) {
        return prefixSum(r2, c2)
             - prefixSum(r1 - 1, c2)
             - prefixSum(r2, c1 - 1)
             + prefixSum(r1 - 1, c1 - 1);
    }

    public static void main(String[] args) {
        FenwickTree2D ft = new FenwickTree2D(4, 4);
        ft.update(1, 1, 1);
        ft.update(1, 3, 2);
        ft.update(2, 2, 3);
        ft.update(3, 1, 4);
        ft.update(3, 3, 5);
        ft.update(4, 4, 6);

        System.out.println("Sum [1,1]-[2,2]: " + ft.rangeSum(1, 1, 2, 2));  // 4
        System.out.println("Sum [1,1]-[4,4]: " + ft.rangeSum(1, 1, 4, 4));  // 21
        System.out.println("Sum [2,2]-[4,4]: " + ft.rangeSum(2, 2, 4, 4));  // 14

        ft.update(2, 2, 10);
        System.out.println("Sum [1,1]-[2,2] after update: " + ft.rangeSum(1, 1, 2, 2));  // 14
    }
}
```

---

## 19.6 Segment Tree vs Fenwick Tree

### Comparison Table

| Property | Segment Tree | Fenwick Tree |
|----------|-------------|--------------|
| Supported operations | Sum, min, max, GCD, any monoid | Sum (and other invertible operations) |
| Point update + range query | ✓ O(log n) | ✓ O(log n) |
| Range update + point query | ✓ with lazy propagation | ✓ with difference array trick |
| Range update + range query | ✓ with lazy propagation | ✓ with two BITs |
| Space | O(4n) | O(n) |
| Code complexity | ~50-80 lines | ~15-20 lines |
| Constant factor | Higher | Lower |
| 2D extension | Complex (segment tree of segment trees) | Simple (nested loops) |
| Merge operations | Flexible (any associative op) | Limited (mostly sums) |

### When to Use Which

**Use Fenwick Tree when:**
- You only need prefix sums with point updates
- Code simplicity matters (interviews!)
- Memory is tight
- You need 2D range sum queries
- The problem can be reduced to difference arrays

**Use Segment Tree when:**
- You need range min/max/GCD queries
- You need lazy propagation for complex range updates
- The problem requires merging arbitrary interval information
- You need more complex operations (e.g., range assignment)

### Rule of Thumb

> If a Fenwick tree can solve the problem, prefer it. If you need range min/max or complex lazy propagation, use a segment tree.

---

## Interview Tips

1. **Know the template**: The Fenwick tree has a very compact template. Be able to write it from memory in under 2 minutes.

2. **1-indexed**: Fenwick trees are naturally 1-indexed. If the problem uses 0-indexed input, add 1 to all indices.

3. **The `i & (-i)` trick**: This is the core of the Fenwick tree. Understand why it works (two's complement isolates the LSB).

4. **Prefix sum vs range sum**: `rangeSum(l, r) = prefixSum(r) - prefixSum(l-1)`. Don't forget the `-1`.

5. **Coordinate compression**: When values are large but sparse, compress them. This is especially common in "count smaller" problems.

6. **Two BITs for range update + range query**: This is a powerful technique. Know the formula: `prefixSum(x) = B1.prefixSum(x) * x - B2.prefixSum(x)`.

7. **Common pattern**: Process elements from right to left, using the BIT to count/query previously seen elements. This is the standard approach for "count of smaller numbers after self" problems.

## Common Mistakes

1. **0-indexed vs 1-indexed**: The most common bug. Fenwick trees are 1-indexed. If your array is 0-indexed, add 1 to all indices when calling BIT operations.

2. **Off-by-one in range sum**: `rangeSum(l, r) = prefixSum(r) - prefixSum(l-1)`, not `prefixSum(r) - prefixSum(l)`.

3. **Forgetting to handle index 0**: In a 1-indexed BIT, index 0 is unused. The loop in `add` goes `while (i <= n)`, and in `prefixSum` goes `while (i > 0)`.

4. **Integer overflow**: Prefix sums can be large. Use `long long` for the tree values.

5. **Using BIT for min/max queries**: Standard BIT doesn't support range min/max queries. Use a segment tree instead.

6. **Wrong LSB computation**: `i & (-i)` works for positive integers. For negative numbers or zero, the behavior is undefined.

---

## Practice Problems

### Problem 1: Range Sum Query — Mutable (LeetCode 307)
**Difficulty**: Medium
**Hint**: Build a Fenwick tree. Point update with `add`, range query with `prefixSum(r) - prefixSum(l-1)`.

### Problem 2: Count of Smaller Numbers After Self (LeetCode 315)
**Difficulty**: Hard
**Hint**: Process from right to left. Coordinate compress the values. For each element, query the BIT for count of values less than current, then update the BIT.

### Problem 3: Create Sorted Array through Instructions (LeetCode 1906)
**Difficulty**: Hard
**Hint**: For each number, the cost is `min(count of elements less than it, count of elements greater than it)`. Use a BIT to track frequencies.

### Problem 4: Count of Range Sum (LeetCode 327)
**Difficulty**: Hard
**Hint**: Compute prefix sums. For each prefix sum, count how many previous prefix sums `prev` satisfy `lower ≤ curr - prev ≤ upper`, i.e., `curr - upper ≤ prev ≤ curr - lower`. Use coordinate compression + BIT.

### Problem 5: Reverse Pairs (LeetCode 493)
**Difficulty**: Hard
**Hint**: A reverse pair is (i, j) where i < j and nums[i] > 2*nums[j]. Process from right to left. For each element, query how many previously seen elements satisfy the condition. Use coordinate compression on both `nums[j]` and `2*nums[j]`.

### Problem 6: Range Sum Query 2D — Mutable (LeetCode 308)
**Difficulty**: Hard
**Hint**: Use a 2D Fenwick tree. Each update and query is O(log n × log m).

### Problem 7: Count Good Triplets in an Array (LeetCode 2179)
**Difficulty**: Hard
**Hint**: For each element in the first permutation, count how many common elements appear before it in both permutations. Use a BIT to track positions.

### Problem 8: Minimum Number of Operations to Make Array Continuous (LeetCode 2009)
**Difficulty**: Hard
**Hint**: Sort and deduplicate. For each window of size k, count how many elements are already in range. Use a BIT or sliding window.

---

## See Also

- [Chapter 18: Segment Tree](ch18-segment-tree.md) — The more powerful sibling; supports arbitrary range operations (lazy propagation, range updates) that BIT cannot.
- [Chapter 20: Sparse Table](ch20-sparse-table.md) — O(1) static RMQ; compare the trade-offs: BIT supports updates but O(log n) queries, Sparse Table has O(1) queries but no updates.
- [Chapter 76: Advanced Segment Trees](ch76-advanced-seg-trees.md) — When BIT and basic segment trees aren't enough: 2D, persistent, and lazy variants.
- [Chapter 36: Prefix Sum and Difference Array](ch36-prefix-sum-diff-array.md) — BIT is essentially a dynamic prefix sum; understanding prefix sums is prerequisite.

*Next chapter: [Chapter 20: Sparse Table](ch20-sparse-table.md)*
