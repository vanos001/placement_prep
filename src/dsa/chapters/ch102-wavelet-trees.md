# Chapter 102: Wavelet Trees

## Prerequisites
- Segment trees
- Binary search
- Divide and conquer
- Bit manipulation basics

## Interview Frequency: ★★

Wavelet trees are a powerful data structure that answer **range frequency**, **range quantile**, and **range rank** queries in O(log σ) time, where σ is the size of the value domain. They are a staple in competitive programming and appear occasionally in advanced algorithm interviews.

> **Key Insight:** A wavelet tree recursively partitions the value range, storing bitmaps at each level to track which elements go left or right. This enables answering queries by traversing the tree from root to leaf.

| Query | Time | Description |
|---|---|---|
| Count x in [l,r] | O(log σ) | Range frequency |
| K-th smallest in [l,r] | O(log σ) | Range quantile |
| Count ≤ x in [l,r] | O(log σ) | Range rank |
| Range sum of elements ≤ x | O(log σ) | Weighted rank |

---

## 102.1 What Problem Does It Solve?

Consider this scenario: you have an array `A[0..n-1]` and need to answer many queries of the form:

- "How many times does value `x` appear in `A[l..r]`?"
- "What is the k-th smallest element in `A[l..r]`?"
- "How many elements in `A[l..r]` are ≤ x?"

**Naive approaches:**
- For each query, scan the range → O(n) per query. Too slow for many queries.
- Precompute prefix frequency arrays for each value → O(nσ) space. Too much memory.

**Wavelet trees** solve all of these in **O(log σ)** per query with **O(n log σ)** total space.

---

## 102.2 Intuition

Think of a wavelet tree as a **decision tree for values**:

1. The root covers the entire value range `[lo, hi]`.
2. It splits the range at the midpoint `mid = (lo + hi) / 2`.
3. Values ≤ `mid` go to the left child; values > `mid` go to the right child.
4. At each node, a **bitmap** (prefix-sum array) records how many of the first `i` elements went left.
5. The process recurses until we reach a single value (leaf).

When answering a query on range `[l, r]`:
- The bitmap tells us **exactly which sub-range** to pass to the left child and which to the right child.
- We never need to look at the original array again — the bitmaps carry all the information.

### Visual Example

For array `A = [3, 1, 4, 1, 5, 9, 2, 6]` with values in `[1, 9]`:

```
Root [1,9], mid=5
  Left child [1,5]:  elements ≤ 5 → [3,1,4,1,5,2]
  Right child [6,9]: elements > 5 → [9,6]
    Left child [1,3], mid=2
      Left child [1,2]: [1,1,2]
      Right child [3,3]: [3]
    Right child [4,5], mid=4
      Left child [4,4]: [4]
      Right child [5,5]: [5]
    Left child [6,7], mid=6
      Left child [6,6]: [6]
      Right child [7,7]: []
    Right child [8,9], mid=8
      Left child [8,8]: []
      Right child [9,9]: [9]
```

---

## 102.3 Formal Definition

A **wavelet tree** for array `A[0..n-1]` with values in range `[lo, hi]` is a binary tree where:

- Each node corresponds to a value range `[lo, hi]`.
- The root covers the full range.
- If `lo < hi`, let `mid = ⌊(lo + hi) / 2⌋`:
  - Left child covers `[lo, mid]`
  - Right child covers `[mid+1, hi]`
  - A prefix-sum array `B[0..n]` is stored where `B[i]` = number of elements among the first `i` that are ≤ `mid`
- If `lo == hi`, the node is a leaf.

The tree has height `⌈log₂ σ⌉` where `σ = hi - lo + 1`.

---

## 102.4 Operations Walkthrough

### K-th Smallest in [l, r]

**Goal:** Find the k-th smallest (0-indexed) element in `A[l..r]`.

**Algorithm:**
1. Start at root with range [l, r].
2. Compute `inLeft = B[r+1] - B[l]` (how many elements in [l,r] go left).
3. If `k < inLeft`: recurse left with mapped indices `[B[l], B[r+1]-1]`.
4. Else: recurse right with mapped indices `[l - B[l], r - B[r+1]]` and `k - inLeft`.
5. When reaching a leaf, return `lo`.

**Why it works:** The bitmap lets us "project" the range [l, r] into the left and right children without ever touching the original array. Each level halves the value range.

### Count of x in [l, r]

**Algorithm:**
1. Traverse from root toward the leaf containing `x`.
2. At each node, map [l, r] to the appropriate child using B.
3. At the leaf, the answer is `r - l + 1`.

### Count of elements ≤ x in [l, r]

**Algorithm:**
1. Traverse from root toward the leaf containing `x`.
2. At each node where we go right, add `B[r+1] - B[l]` to the answer (those are all ≤ mid, hence ≤ x).
3. At the leaf, add the remaining count.

---

## 102.5 Dry Run

**Array:** `[3, 1, 4, 1, 5, 9, 2, 6]`, values in `[1, 9]`

**Query:** K-th smallest in [0, 7] with k=3 (0-indexed, so 4th smallest)

```
Step 1: Root [1,9], mid=5, l=0, r=7
  B = [0,1,2,2,3,4,4,4,4]  (prefix count of ≤5)
  inLeft = B[8] - B[0] = 4 - 0 = 4
  k=3 < 4 → go LEFT
  New: l=B[0]=0, r=B[8]-1=3, range=[1,5]

Step 2: Node [1,5], mid=3, l=0, r=3
  Sub-array here: [3,1,4,1] → partitioned: [3,1,1] left, [4] right
  B = [0,1,2,2,3]
  inLeft = B[4] - B[0] = 3 - 0 = 3
  k=3 ≥ 3 → go RIGHT
  New: l=0-B[0]=0, r=3-B[4]=0, k=3-3=0, range=[4,5]

Step 3: Node [4,5], mid=4, l=0, r=0
  Sub-array here: [4]
  B = [0,1]
  inLeft = B[1] - B[0] = 1
  k=0 < 1 → go LEFT
  New: l=B[0]=0, r=B[1]-1=0, range=[4,4]

Step 4: Leaf [4,4] → return 4
```

**Result:** 4th smallest in [0,7] = **4** ✓ (sorted: [1,1,2,3,4,5,6,9])

---

## 102.6 Complexity Analysis

| Operation | Time | Space |
|---|---|---|
| Build | O(n log σ) | O(n log σ) |
| K-th smallest | O(log σ) | O(1) extra |
| Range count | O(log σ) | O(1) extra |
| Range rank (≤ x) | O(log σ) | O(1) extra |

Where:
- `n` = array length
- `σ` = value domain size (hi - lo + 1)
- `log σ` = height of the wavelet tree

**Space breakdown:** Each level stores a bitmap of size O(n), and there are O(log σ) levels.

**Comparison with alternatives:**

| Structure | Build | K-th smallest | Space |
|---|---|---|---|
| Wavelet tree | O(n log σ) | O(log σ) | O(n log σ) |
| Merge sort tree | O(n log n) | O(log² n) | O(n log n) |
| Persistent seg tree | O(n log σ) | O(log σ) | O(n log σ) |
| Mo's algorithm | — | O(√n) | O(n) |

---

## 102.7 Implementation

### C++ — Full Wavelet Tree

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class WaveletTree {
    int lo, hi;
    std::vector<int> b; // b[i] = count of elements going left from first i
    WaveletTree *left, *right;

public:
    WaveletTree(std::vector<int>::iterator from, std::vector<int>::iterator to,
                int x, int y) : lo(x), hi(y), left(nullptr), right(nullptr) {
        if (from == to || lo == hi) return;
        int mid = (lo + hi) / 2;
        auto f = [mid](int x) { return x <= mid; };
        b.reserve(to - from + 1);
        b.push_back(0);
        for (auto it = from; it != to; it++)
            b.push_back(b.back() + f(*it));

        auto pivot = std::stable_partition(from, to, f);
        left = new WaveletTree(from, pivot, lo, mid);
        right = new WaveletTree(pivot, to, mid + 1, hi);
    }

    // K-th smallest in [l, r] (0-indexed)
    int kth(int l, int r, int k) {
        if (lo == hi) return lo;
        int inLeft = b[r + 1] - b[l];
        if (k < inLeft)
            return left->kth(b[l], b[r + 1] - 1, k);
        return right->kth(l - b[l], r - b[r + 1], k - inLeft);
    }

    // Count of elements <= k in [l, r]
    int LTE(int l, int r, int k) {
        if (l > r || k < lo) return 0;
        if (hi <= k) return r - l + 1;
        int lb = b[l], rb = b[r + 1];
        return left->LTE(lb, rb - 1, k)
             + right->LTE(l - lb, r - rb, k);
    }

    // Count of element k in [l, r]
    int count(int l, int r, int k) {
        if (l > r || k < lo || k > hi) return 0;
        if (lo == hi) return r - l + 1;
        int lb = b[l], rb = b[r + 1];
        int mid = (lo + hi) / 2;
        if (k <= mid) return left->LTE(lb, rb - 1, k);
        return right->count(l - lb, r - rb, k);
    }

    ~WaveletTree() { delete left; delete right; }
};

int main() {
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6};
    WaveletTree wt(arr.begin(), arr.end(), 1, 9);

    // 2nd smallest in [0, 4] = sorted({3,1,4,1,5})[1] = 3
    std::cout << "2nd smallest in [0,4]: " << wt.kth(0, 4, 1) << "\n";

    // 3rd smallest in [2, 6] = sorted({4,1,5,9,2})[2] = 4
    std::cout << "3rd smallest in [2,6]: " << wt.kth(2, 6, 2) << "\n";

    // Count of elements <= 4 in [0, 7]
    std::cout << "Elements <= 4 in [0,7]: " << wt.LTE(0, 7, 4) << "\n";

    // Count of 1 in [0, 7]
    std::cout << "Count of 1 in [0,7]: " << wt.count(0, 7, 1) << "\n";

    return 0;
}
```

### Python — Wavelet Tree

```python
class WaveletTree:
    def __init__(self, data, lo, hi):
        self.lo = lo
        self.hi = hi
        self.b = [0]
        self.left = self.right = None

        if lo == hi or not data:
            return

        mid = (lo + hi) // 2
        left_data = []
        right_data = []
        for x in data:
            if x <= mid:
                left_data.append(x)
                self.b.append(self.b[-1] + 1)
            else:
                right_data.append(x)
                self.b.append(self.b[-1])

        self.left = WaveletTree(left_data, lo, mid)
        self.right = WaveletTree(right_data, mid + 1, hi)

    def kth(self, l, r, k):
        """K-th smallest (0-indexed) in original range [l, r]."""
        if self.lo == self.hi:
            return self.lo
        in_left = self.b[r + 1] - self.b[l]
        if k < in_left:
            return self.left.kth(self.b[l], self.b[r + 1] - 1, k)
        return self.right.kth(
            l - self.b[l], r - self.b[r + 1], k - in_left
        )

    def lte(self, l, r, k):
        """Count elements <= k in range [l, r]."""
        if l > r or k < self.lo:
            return 0
        if self.hi <= k:
            return r - l + 1
        lb, rb = self.b[l], self.b[r + 1]
        return (self.left.lte(lb, rb - 1, k) +
                self.right.lte(l - lb, r - rb, k))

    def count(self, l, r, k):
        """Count occurrences of k in range [l, r]."""
        if l > r or k < self.lo or k > self.hi:
            return 0
        if self.lo == self.hi:
            return r - l + 1
        mid = (self.lo + self.hi) // 2
        lb, rb = self.b[l], self.b[r + 1]
        if k <= mid:
            return self.left.count(lb, rb - 1, k)
        return self.right.count(l - lb, r - rb, k)


if __name__ == "__main__":
    arr = [3, 1, 4, 1, 5, 9, 2, 6]
    wt = WaveletTree(arr, 1, 9)

    print(f"2nd smallest in [0,4]: {wt.kth(0, 4, 1)}")   # 3
    print(f"3rd smallest in [2,6]: {wt.kth(2, 6, 2)}")   # 4
    print(f"Elements <= 4 in [0,7]: {wt.lte(0, 7, 4)}")  # 5
    print(f"Count of 1 in [0,7]: {wt.count(0, 7, 1)}")   # 2
```

### Java — Wavelet Tree

```java
import java.util.*;

public class WaveletTree {
    private int lo, hi;
    private int[] b;
    private WaveletTree left, right;

    public WaveletTree(int[] data, int lo, int hi) {
        this.lo = lo;
        this.hi = hi;
        if (lo == hi || data.length == 0) {
            b = new int[]{0};
            return;
        }

        int mid = (lo + hi) / 2;
        List<Integer> leftData = new ArrayList<>();
        List<Integer> rightData = new ArrayList<>();
        b = new int[data.length + 1];

        for (int i = 0; i < data.length; i++) {
            if (data[i] <= mid) {
                leftData.add(data[i]);
                b[i + 1] = b[i] + 1;
            } else {
                rightData.add(data[i]);
                b[i + 1] = b[i];
            }
        }

        left = new WaveletTree(leftData.stream().mapToInt(x -> x).toArray(), lo, mid);
        right = new WaveletTree(rightData.stream().mapToInt(x -> x).toArray(), mid + 1, hi);
    }

    public int kth(int l, int r, int k) {
        if (lo == hi) return lo;
        int inLeft = b[r + 1] - b[l];
        if (k < inLeft)
            return left.kth(b[l], b[r + 1] - 1, k);
        return right.kth(l - b[l], r - b[r + 1], k - inLeft);
    }

    public int lte(int l, int r, int k) {
        if (l > r || k < lo) return 0;
        if (hi <= k) return r - l + 1;
        int lb = b[l], rb = b[r + 1];
        return left.lte(lb, rb - 1, k) + right.lte(l - lb, r - rb, k);
    }

    public int count(int l, int r, int k) {
        if (l > r || k < lo || k > hi) return 0;
        if (lo == hi) return r - l + 1;
        int mid = (lo + hi) / 2;
        int lb = b[l], rb = b[r + 1];
        if (k <= mid) return left.count(lb, rb - 1, k);
        return right.count(l - lb, r - rb, k);
    }

    public static void main(String[] args) {
        int[] arr = {3, 1, 4, 1, 5, 9, 2, 6};
        WaveletTree wt = new WaveletTree(arr, 1, 9);

        System.out.println("2nd smallest in [0,4]: " + wt.kth(0, 4, 1));  // 3
        System.out.println("3rd smallest in [2,6]: " + wt.kth(2, 6, 2));  // 4
        System.out.println("Elements <= 4 in [0,7]: " + wt.lte(0, 7, 4)); // 5
        System.out.println("Count of 1 in [0,7]: " + wt.count(0, 7, 1));  // 2
    }
}
```

---

## 102.8 Applications

1. **Range frequency queries** — most common use case in competitive programming.
2. **Inversion counting with range restrictions** — count inversions where values fall in a specific range.
3. **Persistent data structures** — wavelet trees can be made persistent for offline queries.
4. **Compressed data structures** — using succinct bit vectors, wavelet trees can achieve O(n log σ) bits of space.
5. **2D range queries** — wavelet trees generalize to higher dimensions.

---

## 102.9 Exercises

1. **Implement range sum query:** Modify the wavelet tree to return the sum of all elements ≤ x in range [l, r].
2. **Count elements in [a, b]:** Given range [l, r] and value range [a, b], count how many elements in A[l..r] fall in [a, b].
3. **Wavelet matrix:** Research and implement the wavelet matrix, which is a more cache-friendly variant of the wavelet tree.
4. **Persistent wavelet tree:** Make the wavelet tree persistent so you can query on any prefix of the array.
5. **Range mode query:** Use wavelet trees to find the most frequent element in a range (hint: this is hard — research the best known approach).

---

## 102.10 Interview Questions

1. **Q: What is the time complexity of a wavelet tree query?**
   A: O(log σ) where σ is the value domain size. Each level of the tree processes the query in O(1).

2. **Q: How does a wavelet tree differ from a merge sort tree?**
   A: A merge sort tree stores sorted subarrays at each segment tree node, giving O(log² n) queries. A wavelet tree uses bitmaps for O(log σ) queries but requires coordinate compression when σ is large.

3. **Q: When would you use a wavelet tree over a persistent segment tree?**
   A: Both achieve O(log σ) for range k-th smallest. Wavelet trees are simpler to implement and more cache-friendly. Persistent segment trees are more flexible for other operations.

4. **Q: Can wavelet trees handle updates?**
   A: Standard wavelet trees are static. Dynamic wavelet trees exist but are complex. For problems with updates, consider sqrt decomposition or BIT-based approaches.

5. **Q: What is the relationship between wavelet trees and Cartesian trees?**
   A: Both recursively partition the array, but wavelet trees partition by value range while Cartesian trees partition by array position (using the minimum/maximum as root). They solve different problems.

---

## 102.11 Cross-References

- **Chapter 101 (Segment Trees):** Wavelet trees use a segment-tree-like recursive structure.
- **Chapter 104 (Cartesian Trees):** Another recursive partitioning scheme for arrays.
- **Chapter 99 (BIT/Fenwick Tree):** The bitmap in a wavelet tree can use a Fenwick tree for dynamic updates.
- **Chapter 108 (Persistent Data Structures):** Persistent wavelet trees combine both techniques.
- **Chapter 15 (Binary Search):** The value-space partitioning in wavelet trees is analogous to binary search.

---

## Summary

| Property | Value |
|---|---|
| Build | O(n log σ) |
| Space | O(n log σ) |
| K-th smallest | O(log σ) |
| Range count (≤ x) | O(log σ) |
| Range frequency | O(log σ) |
| Tree height | ⌈log₂ σ⌉ |
