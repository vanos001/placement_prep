# Chapter 173: Sqrt Decomposition and Mo's Algorithm

## 1. Introduction

**Sqrt decomposition** is a powerful technique that partitions data into blocks of size approximately √n, enabling efficient updates and queries by combining precomputed block-level information with brute-force within blocks. **Mo's algorithm** builds on this foundation to answer offline range queries in O((n + q)√n) time by cleverly ordering queries to minimize pointer movement.

### Why Should You Care?

- **Range Queries with Updates**: Handle range sum, min, max, and frequency queries efficiently.
- **Offline Query Processing**: Answer batches of range queries faster than naive approaches.
- **Competitive Programming**: Mo's algorithm is a staple in ICPC, Codeforces, and OI contests.
- **D-Query Problems**: Count distinct elements in a range — a classic Mo's application.
- **Alternative to Segment Trees**: Simpler to implement for many problems, with comparable performance.

---

## 2. Sqrt Decomposition Fundamentals

### 2.1 Core Idea

Given an array of size n, divide it into blocks of size B ≈ √n. Precompute a summary (sum, min, max, etc.) for each block. For a query on range [L, R]:

1. Process elements from L to the end of its block (left fragment).
2. Process complete blocks entirely within [L, R] using precomputed values.
3. Process elements from the start of R's block to R (right fragment).

This gives O(√n) per query instead of O(n).

### 2.2 Block Structure

```
Array:  [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8]
Blocks (B=4):
  Block 0: [3, 1, 4, 1]  → sum = 9
  Block 1: [5, 9, 2, 6]  → sum = 22
  Block 2: [5, 3, 5, 8]  → sum = 21

Query [2, 9] (0-indexed):
  Left fragment: [4, 1] (indices 2,3 in Block 0)
  Full blocks: Block 1 (sum = 22)
  Right fragment: [5, 3] (indices 8,9 in Block 2)
  Total = 4+1 + 22 + 5+3 = 35
```

### 2.3 Choosing Block Size

The optimal block size is B = ⌈√n⌉. This balances:
- Number of blocks: n/B ≈ √n
- Elements per block: B ≈ √n
- Left/right fragments: at most 2B ≈ 2√n elements
- Full blocks to process: at most n/B ≈ √n blocks

Total per query: O(B + n/B) = O(√n).

---

## 3. Sqrt Decomposition for Range Queries

### 3.1 Range Sum Query

**Problem**: Given an array A[0..n-1], answer Q queries of the form "sum of A[L..R]", with point updates.

**Approach**:
- Maintain block sums `block[i]` for each block i.
- Query: sum left fragment + sum of full blocks + sum right fragment.
- Update: modify A[i] and update `block[i / B]`.

**Complexity**:
- Build: O(n)
- Query: O(√n)
- Update: O(1)

### 3.2 Range Minimum Query

Replace block sums with block minimums. For a query:
- Take min of left fragment elements, full block minimums, and right fragment elements.

### 3.3 Range GCD Query

Each block stores the GCD of its elements. For a query:
- GCD of left fragment elements, full block GCDs, and right fragment elements.

---

## 4. Mo's Algorithm

### 4.1 Motivation

Consider answering Q queries of the form "count distinct elements in A[L..R]". With sqrt decomposition alone, we'd need O(√n) per query. But Mo's algorithm achieves O((n + q)√n) total for all queries by:

1. Sorting queries in a specific order.
2. Maintaining a "current range" [curL, curR].
3. Moving the range boundaries incrementally to answer each query.

### 4.2 The Algorithm

**Step 1**: Read all queries. Each query is (L, R, index).

**Step 2**: Sort queries by:
- Primary key: block of L (i.e., L / B)
- Secondary key: R (ascending if block is even, descending if odd — this is the "odd-even optimization")

**Step 3**: Initialize curL = 0, curR = -1 (empty range), answer = 0.

**Step 4**: For each query (L, R) in sorted order:
- While curL > L: curL--, add A[curL]
- While curR < R: curR++, add A[curR]
- While curL < L: remove A[curL], curL++
- While curR > R: remove A[curR], curR--
- Record answer for this query.

### 4.3 Why It Works

The key insight is that by sorting queries by block of L, we limit how much curL moves (at most B = √n per query, and at most n total within a block). The R pointer sweeps monotonically within each block (or alternates with odd-even optimization), giving at most n moves per block and n√n total.

**Total pointer moves**: O(n√n + q√n) = O((n + q)√n).

### 4.4 Odd-Even Optimization

Instead of always sorting R in ascending order, sort R in:
- Ascending order for even-numbered blocks of L.
- Descending order for odd-numbered blocks.

This prevents the R pointer from "snaking" back and forth, reducing total movement.

---

## 5. Add and Remove Operations

### 5.1 Design Principle

For Mo's algorithm to work, we need:
- `add(i)`: Include A[i] in the current range, update the answer.
- `remove(i)`: Exclude A[i] from the current range, update the answer.

Both must run in O(1) amortized.

### 5.2 Example: Count of Each Element

```python
freq = defaultdict(int)  # frequency of each value
distinct = 0  # count of distinct elements

def add(i):
    global distinct
    if freq[A[i]] == 0:
        distinct += 1
    freq[A[i]] += 1

def remove(i):
    global distinct
    freq[A[i]] -= 1
    if freq[A[i]] == 0:
        distinct -= 1
```

### 5.3 Example: Range Sum (with Mo's)

```python
current_sum = 0

def add(i):
    global current_sum
    current_sum += A[i]

def remove(i):
    global current_sum
    current_sum -= A[i]
```

---

## 6. Application: D-Query (SPOJ DQUERY)

### 6.1 Problem Statement

Given an array of n integers and q queries [L, R], find the number of distinct elements in A[L..R].

### 6.2 Solution with Mo's Algorithm

1. Each query is (L, R, idx).
2. Sort by Mo's ordering.
3. Maintain frequency array and distinct count.
4. Answer each query after adjusting the range.

### 6.3 Walkthrough

```
Array: [1, 2, 1, 3, 2, 1]
Queries: [0,4], [1,3], [2,5]

Block size B = 3 (⌈√6⌉)

Queries after sorting:
  (0, 4, 0) → block 0, R=4
  (1, 3, 1) → block 0, R=3
  (2, 5, 2) → block 0, R=5

Processing:
  Start: curL=0, curR=-1, distinct=0

  Query (0,4):
    Extend to [0,4]: add(0), add(1), add(2), add(3), add(4)
    freq: {1:2, 2:2, 3:1}, distinct=3 ✓

  Query (1,3):
    Shrink from left: remove(0) → freq: {1:1, 2:2, 3:1}, distinct=3
    Shrink from right: remove(4) → freq: {1:1, 2:1, 3:1}, distinct=3
    Answer: 3 ✓

  Query (2,5):
    Shrink from left: remove(1) → freq: {1:1, 2:1, 3:1}, distinct=3
    Extend right: add(5) → freq: {1:2, 2:1, 3:1}, distinct=3
    Answer: 3 ✓
```

---

## 7. Application: Range Inversion Count

### 7.1 Problem

Count inversions (pairs i < j with A[i] > A[j]) in range [L, R].

### 7.2 Approach

Maintain a Fenwick tree over values. When adding element at index i:
- Count how many existing elements are greater than A[i] → these are new inversions where A[i] is the right element.
- Count how many existing elements are less than A[i] → these are inversions where A[i] is the left element.

With coordinate compression, each add/remove is O(log n), giving O((n + q)√n log n) total.

---

## 8. Complexity Analysis

### 8.1 Sqrt Decomposition

| Operation | Time | Space |
|-----------|------|-------|
| Build | O(n) | O(n) |
| Range query | O(√n) | O(1) |
| Point update | O(1) | O(1) |

### 8.2 Mo's Algorithm

| Aspect | Complexity |
|--------|------------|
| Sorting queries | O(q log q) |
| Processing all queries | O((n + q)√n) |
| Per query (amortized) | O(√n) |
| Space | O(n) |

### 8.3 With O(1) Add/Remove

Mo's algorithm is O((n + q)√n) total. If add/remove costs O(f), the total becomes O((n + q)√n · f).

---

## 9. Code Implementations

### 9.1 C++ — Sqrt Decomposition (Range Sum)

```cpp
#include <bits/stdc++.h>
using namespace std;

class SqrtDecomp {
    vector<int> arr, block;
    int n, B;

public:
    SqrtDecomp(const vector<int>& a) : arr(a), n(a.size()) {
        B = (int)ceil(sqrt(n));
        block.resize(B, 0);
        for (int i = 0; i < n; i++)
            block[i / B] += arr[i];
    }

    void update(int idx, int val) {
        block[idx / B] += val - arr[idx];
        arr[idx] = val;
    }

    int query(int L, int R) {
        int sum = 0;
        int startBlock = L / B, endBlock = R / B;

        if (startBlock == endBlock) {
            for (int i = L; i <= R; i++)
                sum += arr[i];
        } else {
            // Left fragment
            for (int i = L; i < (startBlock + 1) * B; i++)
                sum += arr[i];
            // Full blocks
            for (int b = startBlock + 1; b < endBlock; b++)
                sum += block[b];
            // Right fragment
            for (int i = endBlock * B; i <= R; i++)
                sum += arr[i];
        }
        return sum;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, q;
    cin >> n >> q;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    SqrtDecomp sd(a);
    while (q--) {
        int type, l, r;
        cin >> type >> l >> r;
        if (type == 1) {
            sd.update(l, r);
        } else {
            cout << sd.query(l, r) << "\n";
        }
    }
    return 0;
}
```

### 9.2 C++ — Mo's Algorithm (D-Query)

```cpp
#include <bits/stdc++.h>
using namespace std;

const int MAXN = 30005;
int freq[1000006];  // assuming values up to 10^6
int distinct = 0;

void add(int val) {
    if (freq[val] == 0) distinct++;
    freq[val]++;
}

void remove(int val) {
    freq[val]--;
    if (freq[val] == 0) distinct--;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    int q;
    cin >> q;
    struct Query { int l, r, idx; };
    vector<Query> queries(q);
    for (int i = 0; i < q; i++) {
        cin >> queries[i].l >> queries[i].r;
        queries[i].l--; queries[i].r--;
        queries[i].idx = i;
    }

    int B = (int)ceil(sqrt(n));
    sort(queries.begin(), queries.end(), [&](const Query& a, const Query& b) {
        int blockA = a.l / B, blockB = b.l / B;
        if (blockA != blockB) return blockA < blockB;
        return (blockA & 1) ? a.r > b.r : a.r < b.r;
    });

    vector<int> ans(q);
    int curL = 0, curR = -1;

    for (auto& qr : queries) {
        while (curL > qr.l) add(a[--curL]);
        while (curR < qr.r) add(a[++curR]);
        while (curL < qr.l) remove(a[curL++]);
        while (curR > qr.r) remove(a[curR--]);
        ans[qr.idx] = distinct;
    }

    for (int i = 0; i < q; i++)
        cout << ans[i] << "\n";

    return 0;
}
```

### 9.3 Python — Mo's Algorithm

```python
import sys
from math import sqrt, ceil

def mo_algorithm(n, arr, queries):
    """Answer range distinct count queries using Mo's algorithm."""
    q = len(queries)
    B = max(1, ceil(sqrt(n)))

    # Add query index
    indexed = [(l, r, i) for i, (l, r) in enumerate(queries)]

    # Sort by Mo's ordering
    def mo_key(query):
        block = query[0] // B
        return (block, query[1] if block % 2 == 0 else -query[1])

    indexed.sort(key=mo_key)

    freq = {}
    distinct = 0
    cur_l, cur_r = 0, -1
    ans = [0] * q

    def add(i):
        nonlocal distinct
        v = arr[i]
        if v not in freq:
            freq[v] = 0
        if freq[v] == 0:
            distinct += 1
        freq[v] += 1

    def remove(i):
        nonlocal distinct
        v = arr[i]
        freq[v] -= 1
        if freq[v] == 0:
            distinct -= 1

    for l, r, idx in indexed:
        while cur_l > l:
            cur_l -= 1
            add(cur_l)
        while cur_r < r:
            cur_r += 1
            add(cur_r)
        while cur_l < l:
            remove(cur_l)
            cur_l += 1
        while cur_r > r:
            remove(cur_r)
            cur_r -= 1
        ans[idx] = distinct

    return ans

if __name__ == "__main__":
    n = int(input())
    arr = list(map(int, input().split()))
    q = int(input())
    queries = []
    for _ in range(q):
        l, r = map(int, input().split())
        queries.append((l - 1, r - 1))
    result = mo_algorithm(n, arr, queries)
    print("\n".join(map(str, result)))
```

### 9.4 Java — Sqrt Decomposition (Range Minimum Query)

```java
import java.util.*;

public class SqrtDecompRMQ {
    private int[] arr, block;
    private int n, B;

    public SqrtDecompRMQ(int[] a) {
        n = a.length;
        B = (int) Math.ceil(Math.sqrt(n));
        arr = a.clone();
        block = new int[B];
        Arrays.fill(block, Integer.MAX_VALUE);
        for (int i = 0; i < n; i++)
            block[i / B] = Math.min(block[i / B], arr[i]);
    }

    public void update(int idx, int val) {
        arr[idx] = val;
        int b = idx / B;
        block[b] = Integer.MAX_VALUE;
        int start = b * B, end = Math.min(start + B, n);
        for (int i = start; i < end; i++)
            block[b] = Math.min(block[b], arr[i]);
    }

    public int query(int L, int R) {
        int res = Integer.MAX_VALUE;
        int startBlock = L / B, endBlock = R / B;

        if (startBlock == endBlock) {
            for (int i = L; i <= R; i++)
                res = Math.min(res, arr[i]);
        } else {
            for (int i = L; i < (startBlock + 1) * B; i++)
                res = Math.min(res, arr[i]);
            for (int b = startBlock + 1; b < endBlock; b++)
                res = Math.min(res, block[b]);
            for (int i = endBlock * B; i <= R; i++)
                res = Math.min(res, arr[i]);
        }
        return res;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt(), q = sc.nextInt();
        int[] a = new int[n];
        for (int i = 0; i < n; i++) a[i] = sc.nextInt();
        SqrtDecompRMQ sd = new SqrtDecompRMQ(a);
        while (q-- > 0) {
            int type = sc.nextInt(), l = sc.nextInt(), r = sc.nextInt();
            if (type == 1) sd.update(l, r);
            else System.out.println(sd.query(l, r));
        }
    }
}
```

### 9.5 Java — Mo's Algorithm

```java
import java.util.*;

public class MoAlgorithm {
    static int[] freq;
    static int distinct = 0;

    static void add(int val) {
        if (freq[val] == 0) distinct++;
        freq[val]++;
    }

    static void remove(int val) {
        freq[val]--;
        if (freq[val] == 0) distinct--;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n = sc.nextInt();
        int[] a = new int[n];
        for (int i = 0; i < n; i++) a[i] = sc.nextInt();

        int q = sc.nextInt();
        int[][] queries = new int[q][3]; // l, r, idx
        int maxVal = 0;
        for (int i = 0; i < q; i++) {
            queries[i][0] = sc.nextInt() - 1;
            queries[i][1] = sc.nextInt() - 1;
            queries[i][2] = i;
        }

        int B = (int) Math.ceil(Math.sqrt(n));
        Arrays.sort(queries, (a1, b1) -> {
            int blockA = a1[0] / B, blockB = b1[0] / B;
            if (blockA != blockB) return blockA - blockB;
            return (blockA % 2 == 0) ? a1[1] - b1[1] : b1[1] - a1[1];
        });

        freq = new int[1000006];
        int[] ans = new int[q];
        int curL = 0, curR = -1;

        for (int[] qr : queries) {
            int l = qr[0], r = qr[1], idx = qr[2];
            while (curL > l) add(a[--curL]);
            while (curR < r) add(a[++curR]);
            while (curL < l) remove(a[curL++]);
            while (curR > r) remove(a[curR--]);
            ans[idx] = distinct;
        }

        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < q; i++) sb.append(ans[i]).append('\n');
        System.out.print(sb);
    }
}
```

---

## 10. Advanced Variants

### 10.1 Mo's Algorithm with Updates (Mo's with Modification)

When the array has both queries and point updates:
- Sort by (block of L, block of R, time).
- Block size: B = n^{2/3}
- Complexity: O(n^{5/3})

### 10.2 Mo's on Trees

Convert tree queries to array queries using Euler tour. A subtree query becomes a contiguous range. A path query requires more careful handling with in/out times and LCA.

### 10.3 Mo's with Hilbert Curve Ordering

Instead of block-based sorting, use Hilbert curve order for query sorting. This often gives better practical performance:

```cpp
inline long long hilbertOrder(int x, int y, int pow = 21, int rotate = 0) {
    if (pow == 0) return 0;
    int h = 1 << (pow - 1);
    int sector = (x < h) ? ((y < h) ? 0 : 3) : ((y < h) ? 1 : 2);
    sector = (sector + rotate) & 3;
    int nx = x & (x ^ h), ny = y & (y ^ h);
    int nrot = (rotate + [3, 0, 0, 1][sector]) & 3;
    long long sub = hilbertOrder(nx, ny, pow - 1, nrot);
    return ((long long)sector << (2 * pow - 2)) | sub;
}
```

---

## 11. Dry Run: Complete Example

### Problem
Array: [4, 2, 2, 4, 3, 1, 2]
Queries: count distinct in [0,6], [1,4], [2,5]

B = 3 (⌈√7⌉)

### Step 1: Sort Queries
- (0, 6, 0): block 0, R=6
- (1, 4, 1): block 0, R=4
- (2, 5, 2): block 0, R=5

Sorted by (block, R ascending): (0,6), (1,4), (2,5)

### Step 2: Process
```
curL=0, curR=-1, distinct=0, freq={}

Query (0,6): Extend to [0,6]
  add(4): freq={4:1}, distinct=1
  add(2): freq={4:1,2:1}, distinct=2
  add(2): freq={4:1,2:2}, distinct=2
  add(4): freq={4:2,2:2}, distinct=2
  add(3): freq={4:2,2:2,3:1}, distinct=3
  add(1): freq={4:2,2:2,3:1,1:1}, distinct=4
  add(2): freq={4:2,2:3,3:1,1:1}, distinct=4
  Answer: 4

Query (1,4): Shrink [0,6] → [1,4]
  remove(0): freq={4:1,2:3,3:1,1:1}, distinct=4
  remove(6): freq={4:1,2:2,3:1,1:1}, distinct=4
  remove(5): freq={4:1,2:2,3:1,1:0}, distinct=3
  Answer: 3

Query (2,5): Expand [1,4] → [2,5]
  remove(1): freq={4:1,2:1,3:1}, distinct=3
  add(5): freq={4:1,2:1,3:1,1:1}, distinct=4
  Answer: 4
```

Results: [4, 3, 4] ✓

---

## 12. Common Pitfalls

1. **Off-by-one errors**: Be careful with 0-indexed vs 1-indexed ranges.
2. **Block size**: Using n instead of √n gives O(n) per query — defeating the purpose.
3. **Not handling left == right**: When L and R are in the same block, use brute force.
4. **Integer overflow**: Sum queries on large arrays may overflow 32-bit integers.
5. **Mo's ordering**: Forgetting the odd-even optimization can double runtime.

---

## 13. When to Use What

| Technique | Best For | Time per Query |
|-----------|----------|----------------|
| Sqrt Decomposition | Static range queries with point updates | O(√n) |
| Mo's Algorithm | Offline range queries with O(1) add/remove | O(√n) amortized |
| Mo's with Updates | Offline queries + updates | O(n^{2/3}) |
| Segment Tree | Online range queries | O(log n) |
| Fenwick Tree | Prefix/range sums | O(log n) |

---

## 14. Exercises

### Basic
1. Implement range sum query using sqrt decomposition.
2. Implement range minimum query using sqrt decomposition.
3. Solve the "D-Query" problem on SPOJ using Mo's algorithm.

### Intermediate
4. Count inversions in each range [L, R] using Mo's algorithm.
5. Find the mode (most frequent element) in each range using Mo's.
6. Implement Mo's algorithm with updates for a problem with both query types.

### Advanced
7. Use Mo's algorithm on trees for path queries.
8. Implement Hilbert curve ordering and compare performance.
9. Solve a problem requiring Mo's with O(log n) add/remove (e.g., range median).

---

## 15. Interview Questions

1. **Q**: What is the time complexity of Mo's algorithm?
   **A**: O((n + q)√n) total, O(√n) per query amortized. Sorting takes O(q log q).

2. **Q**: When would you choose Mo's algorithm over a segment tree?
   **A**: When queries are offline, add/remove operations are O(1), and the problem involves counting or frequency queries that are hard to decompose for segment trees.

3. **Q**: What is the odd-even optimization in Mo's algorithm?
   **A**: Sort R in ascending order for even blocks of L and descending for odd blocks. This prevents the R pointer from oscillating, roughly halving the total movement.

4. **Q**: Can Mo's algorithm handle updates?
   **A**: Yes, with "Mo's with modification" (block size n^{2/3}), but it's slower: O(n^{5/3}).

5. **Q**: What happens if add/remove is O(log n) instead of O(1)?
   **A**: Total complexity becomes O((n + q)√n log n). Still viable for most competitive programming constraints.

---

## 16. Cross-References

- **Chapter 18 (Segment Tree)**: Online alternative for range queries.
- **Chapter 19 (Fenwick Tree)**: Efficient for prefix/range sum queries.
- **Chapter 20 (Sparse Table)**: O(1) query for static RMQ.
- **Chapter 62 (Offline Algorithms)**: Mo's algorithm is a key offline technique.
- **Chapter 76 (Advanced Segment Trees)**: Persistent and lazy segment trees.
- **Chapter 130 (Coordinate Compression)**: Often needed with Mo's for value-based operations.

---

## 17. Summary

Sqrt decomposition is a versatile technique that trades O(log n) online queries for simpler O(√n) offline solutions. Mo's algorithm extends this idea to batch query processing, achieving near-linear total time for many problems. The key requirements are:

1. **O(1) add/remove operations** for the current range.
2. **Offline queries** (all queries known in advance).
3. **No updates** (or limited updates with Mo's with modification).

When these conditions are met, Mo's algorithm provides a clean, efficient solution that's often easier to implement than segment trees for complex range queries.
