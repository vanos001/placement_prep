# Chapter 141: Data Structure Selection Cheat Sheet

## Prerequisites
- Basic data structures (arrays, linked lists, trees, hash maps)
- Complexity analysis (Big-O notation)

## Interview Frequency: ★★★★★

Choosing the right data structure is often the single most impactful decision in solving a problem efficiently. This chapter provides a systematic framework for making that choice.

---

## 141.1 The Decision Framework

When faced with a problem, ask these questions in order:

1. **What operations do I need?** (insert, delete, search, min/max, range query, etc.)
2. **What are the constraints?** (n ≤ 10³ vs n ≤ 10⁶ vs n ≤ 10⁹)
3. **Do I need ordering?** (sorted traversal, predecessor/successor)
4. **Do I need persistence?** (undo operations, snapshots)
5. **What are the time/space trade-offs?**

---

## 141.2 By Operation Needed

| Need | Data Structure | Time |
|---|---|---|
| Fast lookup by key | Hash map | O(1) avg |
| Ordered elements | BST (set/map) | O(log n) |
| Min/Max element | Heap (priority queue) | O(1) peek / O(log n) insert |
| K-th element | Order statistic tree | O(log n) |
| Range sum | Fenwick / Segment tree | O(log n) |
| Range min/max | Sparse table / Seg tree | O(1) / O(log n) |
| Range update | Lazy segment tree | O(log n) |
| Union/Find | DSU | O(α(n)) |
| Prefix operations | Prefix sum array | O(1) |
| String matching | Trie / Aho-Corasick | O(m) / O(n+m) |
| LRU Cache | Hash map + doubly linked list | O(1) |
| Median | Two heaps | O(1) peek |
| Sliding window min | Monotonic deque | O(1) amortized |

---

## 141.3 Detailed Comparisons

### Array vs Linked List

| Criterion | Array | Linked List |
|---|---|---|
| Random access | O(1) ✓ | O(n) ✗ |
| Insert at front | O(n) ✗ | O(1) ✓ |
| Insert at end | O(1) amortized | O(1) with tail |
| Memory | Contiguous (cache-friendly) | Scattered (cache-unfriendly) |
| Size | Fixed (or costly resize) | Dynamic |

**Choose array when:** You need random access, iteration, or cache performance.
**Choose linked list when:** You need frequent insertions/deletions at arbitrary positions without shifting.

### Hash Map vs BST (Ordered Map)

| Criterion | Hash Map | BST (std::map) |
|---|---|---|
| Lookup | O(1) avg | O(log n) |
| Insert | O(1) avg | O(log n) |
| Delete | O(1) avg | O(log n) |
| Ordered traversal | ✗ | ✓ |
| Range queries | ✗ | ✓ |
| Memory overhead | High (buckets + load factor) | Low (pointers) |
| Worst case | O(n) with bad hash | O(log n) guaranteed (balanced) |

**Choose hash map when:** You only need key-value lookups and don't care about order.
**Choose BST when:** You need sorted order, range queries, or predecessor/successor operations.

### Segment Tree vs Fenwick Tree (BIT)

| Criterion | Segment Tree | Fenwick Tree |
|---|---|---|
| Range sum | O(log n) | O(log n) |
| Point update | O(log n) | O(log n) |
| Range update | O(log n) with lazy | O(log n) with trick |
| Range min/max | O(log n) | ✗ (not directly) |
| Implementation | Complex (~80 lines) | Simple (~20 lines) |
| Memory | 4n | n |
| 2D support | Possible but complex | Easy |

**Choose Fenwick when:** You only need prefix sums or point updates with range queries.
**Choose segment tree when:** You need range min/max, lazy propagation, or complex operations.

### Heap vs BST

| Criterion | Heap | BST |
|---|---|---|
| Find min/max | O(1) | O(log n) |
| Insert | O(log n) | O(log n) |
| Delete min/max | O(log n) | O(log n) |
| Search arbitrary | O(n) | O(log n) |
| Sorted traversal | O(n log n) | O(n) |
| Implementation | Simple (array) | Complex (rotations) |

**Choose heap when:** You only need the min or max element (priority queue).
**Choose BST when:** You need search, sorted traversal, or arbitrary deletions.

### Stack vs Queue vs Deque

| Structure | Order | Use Case |
|---|---|---|
| Stack | LIFO | DFS, parentheses matching, undo, monotonic stack |
| Queue | FIFO | BFS, level-order traversal, sliding window |
| Deque | Both ends | Sliding window min/max, monotonic deque |

---

## 141.4 By Problem Pattern

### Pattern: "Find something in a collection"
- **Unsorted, many lookups** → Hash set/map
- **Sorted** → Binary search on array, or BST
- **Need order statistics** → Order statistic tree or sorted set

### Pattern: "Maintain running min/max"
- **All elements** → Heap (priority queue)
- **Sliding window** → Monotonic deque
- **With deletion** → Two heaps or balanced BST with lazy deletion

### Pattern: "Range queries on array"
- **Static array, range sum** → Prefix sum array
- **Static array, range min** → Sparse table (O(1) query)
- **Dynamic array, range sum** → Fenwick tree
- **Dynamic array, range min** → Segment tree
- **Range updates** → Lazy segment tree

### Pattern: "Grouping and connectivity"
- **Merge sets, check connectivity** → DSU (Union-Find)
- **Graph traversal** → Adjacency list + BFS/DFS

### Pattern: "String operations"
- **Single pattern matching** → KMP or Z-algorithm
- **Multiple pattern matching** → Aho-Corasick
- **Prefix queries** → Trie
- **Suffix queries** → Suffix array or suffix automaton

### Pattern: "Cache / Eviction"
- **LRU** → Hash map + doubly linked list
- **LFU** → Hash map + frequency buckets

---

## 141.5 Complexity Quick Reference

| Data Structure | Build | Insert | Delete | Search | Space |
|---|---|---|---|---|---|
| Dynamic Array | O(1) | O(1) amortized | O(n) | O(n) | O(n) |
| Hash Map | O(n) | O(1) avg | O(1) avg | O(1) avg | O(n) |
| Balanced BST | O(n log n) | O(log n) | O(log n) | O(log n) | O(n) |
| Heap | O(n) | O(log n) | O(log n) | O(n) | O(n) |
| Trie | O(n·m) | O(m) | O(m) | O(m) | O(n·m) |
| Segment Tree | O(n) | O(log n) | O(log n) | O(log n) | O(4n) |
| Fenwick Tree | O(n log n) | O(log n) | O(log n) | O(log n) | O(n) |
| DSU | O(n) | O(α(n)) union | — | O(α(n)) find | O(n) |

---

## 141.6 Example: Choosing for a Real Problem

**Problem:** Given an array of n integers, answer q queries of the form "what is the sum of elements from index l to r?" The array may be updated between queries.

**Analysis:**
- Need range sum → prefix sum (static) or Fenwick/segment tree (dynamic)
- Array is updated → prefix sum won't work
- Only need sum (not min/max) → Fenwick tree is sufficient and simpler
- n, q ≤ 10⁵ → O(log n) per operation is fine

**Decision:** Fenwick tree (BIT)

**C++ Implementation:**

```cpp
#include <vector>
using namespace std;

class FenwickTree {
    vector<int> tree;
    int n;
public:
    FenwickTree(int n) : n(n), tree(n + 1, 0) {}
    
    void update(int i, int delta) {
        for (++i; i <= n; i += i & (-i))
            tree[i] += delta;
    }
    
    int query(int i) {
        int sum = 0;
        for (++i; i > 0; i -= i & (-i))
            sum += tree[i];
        return sum;
    }
    
    int rangeQuery(int l, int r) {
        return query(r) - query(l - 1);
    }
};
```

**Python Implementation:**

```python
class FenwickTree:
    def __init__(self, n):
        self.n = n
        self.tree = [0] * (n + 1)
    
    def update(self, i, delta):
        i += 1
        while i <= self.n:
            self.tree[i] += delta
            i += i & (-i)
    
    def query(self, i):
        s = 0
        i += 1
        while i > 0:
            s += self.tree[i]
            i -= i & (-i)
        return s
    
    def range_query(self, l, r):
        return self.query(r) - self.query(l - 1)
```

**Java Implementation:**

```java
class FenwickTree {
    int[] tree;
    int n;
    
    FenwickTree(int n) {
        this.n = n;
        this.tree = new int[n + 1];
    }
    
    void update(int i, int delta) {
        for (i++; i <= n; i += i & (-i))
            tree[i] += delta;
    }
    
    int query(int i) {
        int sum = 0;
        for (i++; i > 0; i -= i & (-i))
            sum += tree[i];
        return sum;
    }
    
    int rangeQuery(int l, int r) {
        return query(r) - query(l - 1);
    }
}
```

---

## 141.7 Common Mistakes

1. **Using hash map when order matters** — Hash maps don't guarantee iteration order in most languages.
2. **Using BST for simple lookups** — If you don't need ordering, a hash map is faster.
3. **Using array when frequent insertions are needed** — Each insertion shifts O(n) elements.
4. **Over-engineering with segment tree** — If the array is static, prefix sums are simpler and faster.
5. **Forgetting about worst-case hash performance** — Use balanced BSTs when worst-case guarantees matter.
6. **Not considering memory constraints** — Segment trees use 4x memory; hash maps have high overhead.

---

## 141.8 Exercises

1. **Design a data structure** that supports insert, delete, and getRandom in O(1). *Hint: combine array with hash map.*

2. **Design a data structure** for a sliding window that supports addRight, removeLeft, and getMin, all in O(1). *Hint: monotonic deque.*

3. **Given q queries** of type "add number to set" and "find number closest to x", which data structure would you use? *Hint: balanced BST (std::set in C++, TreeSet in Java).*

4. **Implement an LFU cache** with O(1) get and put. *Hint: hash map + frequency buckets + doubly linked list.*

5. **Given a grid of size n×m**, answer queries "how many 1s in sub-rectangle (r1,c1) to (r2,c2)?" after point updates. *Hint: 2D Fenwick tree.*

---

## 141.9 Interview Questions

1. **"Design a hit counter"** that counts hits in the past 5 minutes. → Circular buffer or deque with timestamps.

2. **"Find the median of a stream"** as numbers arrive one by one. → Two heaps (max-heap for lower half, min-heap for upper half).

3. **"Design Twitter"** — show the 10 most recent tweets from people you follow. → Hash map of user → tweets + merge k sorted lists with heap.

4. **"Implement a phone directory"** with prefix search. → Trie.

5. **"Range sum query with updates"** — Fenwick tree or segment tree.

---

## 141.10 Cross-References

- **Hash Maps:** Chapter on Hashing
- **Binary Search Trees:** Chapter on BSTs
- **Segment Trees:** Chapter on Segment Trees
- **Fenwick Trees:** Chapter on Binary Indexed Trees
- **Heaps:** Chapter on Priority Queues
- **Tries:** Chapter on Trie
- **DSU:** Chapter on Union-Find
- **Monotonic Stack/Deque:** Chapter on Monotonic Structures

---

## Summary

| Decision | Best Choice |
|---|---|
| Fast lookup, no order | Hash map |
| Need sorted order | BST (balanced) |
| Min/Max only | Heap |
| Range sum (static) | Prefix sum |
| Range sum (dynamic) | Fenwick tree |
| Range min/max (dynamic) | Segment tree |
| Connectivity | DSU |
| String prefix search | Trie |
| Sliding window min | Monotonic deque |
| LRU cache | Hash map + DLL |
