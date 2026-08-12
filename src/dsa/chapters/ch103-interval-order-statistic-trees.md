# Chapter 103: Interval Trees and Order Statistic Trees

## Prerequisites
- Binary search trees, augmentation technique
- Understanding of balanced BSTs (AVL, Red-Black)
- Basic set operations

## Interview Frequency: ★★

Augmented BSTs extend standard binary search trees with additional information to support specialized queries. Interval trees handle overlapping interval queries; order statistic trees support rank and selection operations.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Interval tree | ★★ | Medium | Overlapping intervals, scheduling |
| Order statistic tree | ★★★ | Medium | K-th element, rank queries |
| Augmentation technique | ★★ | Medium | General BST enhancement pattern |
| Segment tree (related) | ★★★ | Medium | Range queries on arrays |

---

## 103.1 Motivation: Why Augment BSTs?

Standard BSTs support: insert, delete, search — all in O(log n). But many real-world problems need more:

**Problem 1**: Given n time intervals, find all intervals that overlap with [10, 15].
- Naive: check every interval → O(n)
- Interval tree: O(log n + k) where k = number of overlapping intervals

**Problem 2**: Find the 5th smallest element in a dynamic set.
- Naive: sort and index → O(n log n)
- Order statistic tree: O(log n) per query

**Key insight**: Augmentation stores extra information at each node, maintained during insert/delete, enabling richer queries.

---

## 103.2 The Augmentation Pattern

The standard augmentation approach (from CLRS):

1. **Choose an augmentation**: decide what extra data to store
2. **Maintain it**: update the data during insert/delete/rotation
3. **Use it**: implement the new query using the augmented data

**Invariants**:
- Augmented data at node x depends only on x's key, x's children's augmented data
- Maintaining augmentation adds O(1) work per structural change

---

## 103.3 Interval Tree

### Definition

An **interval tree** stores intervals [lo, hi] and supports:
- **Insert**: add an interval
- **Delete**: remove an interval
- **Find all overlapping**: given a point or interval, return all stored intervals that overlap it

### Structure

Each node stores:
- `lo`, `hi`: the interval
- `max_hi`: maximum hi value in the subtree (the augmentation)
- Left, right children (BST ordered by `lo`)

### Key Property

`max_hi` = max of (node.hi, left.max_hi, right.max_hi)

This tells us the rightmost endpoint in the subtree.

### Search Algorithm

To find intervals overlapping point `x`:

```
Search(node, x):
    if node is null: return
    if node.lo <= x <= node.hi: report node.interval
    if node.left != null AND node.left.max_hi >= x:
        // Left subtree might contain overlapping intervals
        Search(node.left, x)
    Search(node.right, x)  // Always check right
```

**Why this works**: If `left.max_hi < x`, no interval in the left subtree can reach x (all end before x). So we can skip the entire left subtree.

---

## 103.4 Interval Tree Walkthrough

### Building the Tree

Insert intervals: [15,20], [10,30], [17,19], [5,20], [12,15]

```
Step 1: Insert [15,20]
    [15,20] max=20

Step 2: Insert [10,30]
         [15,20] max=30
        /
    [10,30] max=30

Step 3: Insert [17,19]
         [15,20] max=30
        /         \
    [10,30]     [17,19] max=19

Step 4: Insert [5,20]
              [15,20] max=30
             /         \
         [10,30]     [17,19]
        /
    [5,20] max=20

Step 5: Insert [12,15]
              [15,20] max=30
             /         \
         [10,30]     [17,19]
        /       \
    [5,20]   [12,15]
```

### Query: Find intervals overlapping point 14

```
Start at root [15,20]: 14 not in [15,20]
  left.max_hi = 30 >= 14 → go left
  
At [10,30]: 14 in [10,30] → REPORT
  left.max_hi = 20 >= 14 → go left
  
At [5,20]: 14 in [5,20] → REPORT
  left is null → skip
  
  go right (null) → done
  
Back to [10,30]: go right
At [12,15]: 14 in [12,15] → REPORT
  left is null, right is null → done

Result: {[10,30], [5,20], [12,15]}
```

### Query: Find intervals overlapping interval [16, 18]

For interval overlap, check if stored interval overlaps [16, 18]:
- Overlap condition: lo ≤ 18 AND 16 ≤ hi

Same traversal, but check overlap instead of containment.

---

## 103.5 Order Statistic Tree

### Definition

An **order statistic tree** (OST) is a BST augmented with subtree sizes. Each node stores:
- `key`: the value
- `size`: number of nodes in the subtree rooted at this node
- Left, right children

### Key Operations

1. **Select(k)**: Find the k-th smallest element (0-indexed)
2. **Rank(x)**: Find the number of elements smaller than x

### Size Maintenance

After every insert, delete, or rotation:
```
node.size = 1 + left.size + right.size
```

(Null children have size 0.)

---

## 103.6 Select Operation

Find the k-th smallest element (0-indexed):

```
Select(node, k):
    leftSize = node.left ? node.left.size : 0
    
    if k < leftSize:
        return Select(node.left, k)
    if k == leftSize:
        return node.key
    return Select(node.right, k - leftSize - 1)
```

**Intuition**: The left subtree contains `leftSize` elements smaller than node.key. If k < leftSize, the answer is in the left subtree. If k == leftSize, the answer is the current node. Otherwise, skip the left subtree and current node.

### Walkthrough

Tree after inserting 20, 10, 30, 5, 15, 25, 35:

```
           20(size=7)
          /          \
      10(size=3)    30(size=3)
      /      \      /      \
   5(size=1) 15  25(size=1) 35(size=1)
```

**Select(root, 4)** (5th smallest, 0-indexed):
```
At 20: leftSize = 3, k = 4
  4 > 3 → go right, k = 4 - 3 - 1 = 0
  
At 30: leftSize = 1, k = 0
  0 < 1 → go left
  
At 25: leftSize = 0, k = 0
  0 == 0 → return 25

Answer: 25 (the 5th smallest)
```

**Select(root, 0)** (minimum):
```
At 20: leftSize = 3, k = 0
  0 < 3 → go left
  
At 10: leftSize = 1, k = 0
  0 < 1 → go left
  
At 5: leftSize = 0, k = 0
  0 == 0 → return 5

Answer: 5
```

---

## 103.7 Rank Operation

Find the number of elements smaller than x:

```
Rank(node, x):
    if node is null: return 0
    if x <= node.key:
        return Rank(node.left, x)
    leftSize = node.left ? node.left.size : 0
    return leftSize + 1 + Rank(node.right, x)
```

### Walkthrough

**Rank(root, 15)** (how many elements < 15?):
```
At 20: 15 <= 20 → go left

At 10: 15 > 10 → leftSize = 1, go right
  rank = 1 + 1 + Rank(right, 15)

At 15: 15 <= 15 → go left

At null: return 0

Backtrack: rank = 1 + 1 + 0 = 2

Answer: 2 (elements 5 and 10 are smaller than 15)
```

**Rank(root, 25)**:
```
At 20: 25 > 20 → leftSize = 3, go right
  rank = 3 + 1 + Rank(right, 25)

At 30: 25 <= 30 → go left

At 25: 25 <= 25 → go left

At null: return 0

Backtrack: rank = 3 + 1 + 0 = 4

Answer: 4 (elements 5, 10, 15, 20 are smaller than 25)
```

---

## 103.8 Insert and Delete with Augmentation

### Insert

Standard BST insert, then update sizes on the path back up:

```
Insert(node, key):
    if node is null: return new Node(key, size=1)
    if key < node.key: node.left = Insert(node.left, key)
    else: node.right = Insert(node.right, key)
    node.size = 1 + size(node.left) + size(node.right)
    return node
```

### Delete

Standard BST delete, then update sizes:

```
Delete(node, key):
    // Standard BST deletion...
    // After removing node, update sizes on path back up
    node.size = 1 + size(node.left) + size(node.right)
    return node
```

### Rotation (for balanced trees)

After a rotation, update sizes of the two nodes involved:

```
RightRotate(y):
    x = y.left
    y.left = x.right
    x.right = y
    y.size = 1 + size(y.left) + size(y.right)
    x.size = 1 + size(x.left) + size(x.right)
    return x
```

---

## 103.9 Complexity Analysis

### Interval Tree

| Operation | Time | Space | Notes |
|---|---|---|---|
| Build (from sorted) | O(n log n) | O(n) | Sort + build |
| Insert | O(log n) | O(1) | BST insert + update max |
| Delete | O(log n) | O(1) | BST delete + update max |
| Find all overlapping point x | O(log n + k) | O(k) | k = results |
| Find all overlapping interval | O(log n + k) | O(k) | k = results |
| Find any overlapping | O(log n) | O(1) | Stop at first |

### Order Statistic Tree

| Operation | Time | Space | Notes |
|---|---|---|---|
| Insert | O(log n) | O(1) | BST insert + update sizes |
| Delete | O(log n) | O(1) | BST delete + update sizes |
| Select(k) | O(log n) | O(1) | Walk by subtree size |
| Rank(x) | O(log n) | O(1) | Accumulate left sizes |
| Min/Max | O(log n) | O(1) | BST min/max |
| Successor/Predecessor | O(log n) | O(1) | BST successor |

---

## 103.10 Code: Complete Implementations

### C++: Interval Tree

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

struct Interval {
    int lo, hi;
    bool overlaps(const Interval& other) const {
        return lo <= other.hi && other.lo <= hi;
    }
    bool contains(int x) const {
        return lo <= x && x <= hi;
    }
};

struct ITNode {
    Interval interval;
    int maxHi;
    ITNode *left, *right;
    ITNode(Interval iv) : interval(iv), maxHi(iv.hi), left(nullptr), right(nullptr) {}
};

class IntervalTree {
    ITNode* root;

    ITNode* insert(ITNode* node, Interval iv) {
        if (!node) return new ITNode(iv);
        if (iv.lo < node->interval.lo)
            node->left = insert(node->left, iv);
        else
            node->right = insert(node->right, iv);
        node->maxHi = std::max({node->maxHi, iv.hi,
                                 node->left ? node->left->maxHi : 0,
                                 node->right ? node->right->maxHi : 0});
        return node;
    }

    void findOverlapping(ITNode* node, int x, std::vector<Interval>& result) const {
        if (!node) return;
        if (node->interval.contains(x))
            result.push_back(node->interval);
        if (node->left && node->left->maxHi >= x)
            findOverlapping(node->left, x, result);
        findOverlapping(node->right, x, result);
    }

    void findOverlappingInterval(ITNode* node, Interval query,
                                  std::vector<Interval>& result) const {
        if (!node) return;
        if (node->interval.overlaps(query))
            result.push_back(node->interval);
        if (node->left && node->left->maxHi >= query.lo)
            findOverlappingInterval(node->left, query, result);
        if (node->interval.lo <= query.hi)
            findOverlappingInterval(node->right, query, result);
    }

    void inorder(ITNode* node) const {
        if (!node) return;
        inorder(node->left);
        std::cout << "[" << node->interval.lo << "," << node->interval.hi
                  << "] max=" << node->maxHi << "\n";
        inorder(node->right);
    }

public:
    IntervalTree() : root(nullptr) {}

    void insert(int lo, int hi) {
        root = insert(root, {lo, hi});
    }

    std::vector<Interval> findOverlapping(int x) const {
        std::vector<Interval> result;
        findOverlapping(root, x, result);
        return result;
    }

    std::vector<Interval> findOverlappingInterval(int lo, int hi) const {
        std::vector<Interval> result;
        findOverlappingInterval(root, {lo, hi}, result);
        return result;
    }

    void display() const {
        inorder(root);
    }
};

int main() {
    IntervalTree tree;
    tree.insert(15, 20);
    tree.insert(10, 30);
    tree.insert(17, 19);
    tree.insert(5, 20);
    tree.insert(12, 15);

    std::cout << "Interval tree:\n";
    tree.display();

    std::cout << "\nIntervals containing point 14:\n";
    for (auto& iv : tree.findOverlapping(14))
        std::cout << "  [" << iv.lo << ", " << iv.hi << "]\n";

    std::cout << "\nIntervals overlapping [16, 18]:\n";
    for (auto& iv : tree.findOverlappingInterval(16, 18))
        std::cout << "  [" << iv.lo << ", " << iv.hi << "]\n";

    return 0;
}
```

### C++: Order Statistic Tree

```cpp
#include <iostream>
#include <vector>
#include <cassert>

struct OSNode {
    int key, size;
    OSNode *left, *right;
    OSNode(int k) : key(k), size(1), left(nullptr), right(nullptr) {}
};

class OrderStatisticTree {
    OSNode* root;

    int getSize(OSNode* n) const { return n ? n->size : 0; }

    void update(OSNode* n) {
        if (n) n->size = 1 + getSize(n->left) + getSize(n->right);
    }

    OSNode* insert(OSNode* node, int key) {
        if (!node) return new OSNode(key);
        if (key < node->key)
            node->left = insert(node->left, key);
        else if (key > node->key)
            node->right = insert(node->right, key);
        update(node);
        return node;
    }

    OSNode* deleteNode(OSNode* node, int key) {
        if (!node) return nullptr;
        if (key < node->key) {
            node->left = deleteNode(node->left, key);
        } else if (key > node->key) {
            node->right = deleteNode(node->right, key);
        } else {
            if (!node->left) {
                OSNode* right = node->right;
                delete node;
                return right;
            }
            if (!node->right) {
                OSNode* left = node->left;
                delete node;
                return left;
            }
            // Find successor
            OSNode* succ = node->right;
            while (succ->left) succ = succ->left;
            node->key = succ->key;
            node->right = deleteNode(node->right, succ->key);
        }
        update(node);
        return node;
    }

    int select(OSNode* node, int k) const {
        assert(node && k >= 0 && k < node->size);
        int leftSize = getSize(node->left);
        if (k < leftSize) return select(node->left, k);
        if (k == leftSize) return node->key;
        return select(node->right, k - leftSize - 1);
    }

    int rank(OSNode* node, int key) const {
        if (!node) return 0;
        if (key <= node->key) return rank(node->left, key);
        return getSize(node->left) + 1 + rank(node->right, key);
    }

    void inorder(OSNode* node) const {
        if (!node) return;
        inorder(node->left);
        std::cout << node->key << "(size=" << node->size << ") ";
        inorder(node->right);
    }

public:
    OrderStatisticTree() : root(nullptr) {}

    void insert(int key) { root = insert(root, key); }
    void erase(int key) { root = deleteNode(root, key); }

    int select(int k) const { return select(root, k); }
    int rank(int key) const { return rank(root, key); }

    int min() const {
        OSNode* n = root;
        while (n->left) n = n->left;
        return n->key;
    }

    int max() const {
        OSNode* n = root;
        while (n->right) n = n->right;
        return n->key;
    }

    int size() const { return getSize(root); }

    void display() const {
        inorder(root);
        std::cout << "\n";
    }
};

int main() {
    OrderStatisticTree ost;
    for (int x : {20, 10, 30, 5, 15, 25, 35}) ost.insert(x);

    std::cout << "Tree: ";
    ost.display();

    std::cout << "\nSelect operations:\n";
    for (int k = 0; k < ost.size(); k++)
        std::cout << "  " << k << "-th smallest: " << ost.select(k) << "\n";

    std::cout << "\nRank operations:\n";
    for (int x : {5, 10, 15, 20, 25, 30, 35})
        std::cout << "  Rank of " << x << ": " << ost.rank(x) << "\n";

    std::cout << "\nMin: " << ost.min() << ", Max: " << ost.max() << "\n";

    ost.erase(20);
    std::cout << "\nAfter deleting 20: ";
    ost.display();

    return 0;
}
```

### Python: Order Statistic Tree

```python
class OSNode:
    def __init__(self, key):
        self.key = key
        self.size = 1
        self.left = None
        self.right = None


class OrderStatisticTree:
    def __init__(self):
        self.root = None

    @staticmethod
    def _size(node):
        return node.size if node else 0

    @staticmethod
    def _update(node):
        if node:
            node.size = 1 + OrderStatisticTree._size(node.left) + OrderStatisticTree._size(node.right)

    def insert(self, key):
        self.root = self._insert(self.root, key)

    def _insert(self, node, key):
        if not node:
            return OSNode(key)
        if key < node.key:
            node.left = self._insert(node.left, key)
        elif key > node.key:
            node.right = self._insert(node.right, key)
        self._update(node)
        return node

    def delete(self, key):
        self.root = self._delete(self.root, key)

    def _delete(self, node, key):
        if not node:
            return None
        if key < node.key:
            node.left = self._delete(node.left, key)
        elif key > node.key:
            node.right = self._delete(node.right, key)
        else:
            if not node.left:
                return node.right
            if not node.right:
                return node.left
            # Find successor
            succ = node.right
            while succ.left:
                succ = succ.left
            node.key = succ.key
            node.right = self._delete(node.right, succ.key)
        self._update(node)
        return node

    def select(self, k):
        """Find k-th smallest element (0-indexed). O(log n)"""
        assert self.root and 0 <= k < self.root.size
        node = self.root
        while node:
            left_size = self._size(node.left)
            if k < left_size:
                node = node.left
            elif k == left_size:
                return node.key
            else:
                k -= left_size + 1
                node = node.right
        raise ValueError("k out of range")

    def rank(self, key):
        """Find number of elements smaller than key. O(log n)"""
        result = 0
        node = self.root
        while node:
            if key <= node.key:
                node = node.left
            else:
                result += self._size(node.left) + 1
                node = node.right
        return result

    def find_range(self, lo, hi):
        """Find all elements in [lo, hi]. O(log n + k)"""
        result = []
        self._find_range(self.root, lo, hi, result)
        return result

    def _find_range(self, node, lo, hi, result):
        if not node:
            return
        if lo < node.key:
            self._find_range(node.left, lo, hi, result)
        if lo <= node.key <= hi:
            result.append(node.key)
        if hi > node.key:
            self._find_range(node.right, lo, hi, result)

    def inorder(self):
        result = []
        self._inorder(self.root, result)
        return result

    def _inorder(self, node, result):
        if not node:
            return
        self._inorder(node.left, result)
        result.append(node.key)
        self._inorder(node.right, result)

    def __len__(self):
        return self._size(self.root)


def demo():
    ost = OrderStatisticTree()
    for x in [20, 10, 30, 5, 15, 25, 35]:
        ost.insert(x)

    print(f"Tree (inorder): {ost.inorder()}")
    print(f"Size: {len(ost)}")

    print("\nSelect operations:")
    for k in range(len(ost)):
        print(f"  {k}-th smallest: {ost.select(k)}")

    print("\nRank operations:")
    for x in [5, 10, 15, 20, 25, 30, 35]:
        print(f"  Rank of {x}: {ost.rank(x)}")

    print(f"\nRange query [10, 25]: {ost.find_range(10, 25)}")

    ost.delete(20)
    print(f"\nAfter deleting 20: {ost.inorder()}")
    print(f"New 3rd smallest: {ost.select(3)}")


if __name__ == "__main__":
    demo()
```

### Java: Interval Tree

```java
import java.util.*;

public class IntervalTree {
    static class Interval {
        int lo, hi;
        Interval(int lo, int hi) { this.lo = lo; this.hi = hi; }
        boolean overlaps(Interval other) { return lo <= other.hi && other.lo <= hi; }
        boolean contains(int x) { return lo <= x && x <= hi; }
        public String toString() { return "[" + lo + "," + hi + "]"; }
    }

    static class ITNode {
        Interval interval;
        int maxHi;
        ITNode left, right;
        ITNode(Interval iv) {
            interval = iv;
            maxHi = iv.hi;
        }
    }

    private ITNode root;

    public void insert(int lo, int hi) {
        root = insert(root, new Interval(lo, hi));
    }

    private ITNode insert(ITNode node, Interval iv) {
        if (node == null) return new ITNode(iv);
        if (iv.lo < node.interval.lo)
            node.left = insert(node.left, iv);
        else
            node.right = insert(node.right, iv);
        node.maxHi = Math.max(node.maxHi, iv.hi);
        if (node.left != null) node.maxHi = Math.max(node.maxHi, node.left.maxHi);
        if (node.right != null) node.maxHi = Math.max(node.maxHi, node.right.maxHi);
        return node;
    }

    public List<Interval> findOverlapping(int x) {
        List<Interval> result = new ArrayList<>();
        findOverlapping(root, x, result);
        return result;
    }

    private void findOverlapping(ITNode node, int x, List<Interval> result) {
        if (node == null) return;
        if (node.interval.contains(x))
            result.add(node.interval);
        if (node.left != null && node.left.maxHi >= x)
            findOverlapping(node.left, x, result);
        findOverlapping(node.right, x, result);
    }

    public List<Interval> findOverlappingInterval(int lo, int hi) {
        List<Interval> result = new ArrayList<>();
        findOverlappingInterval(root, new Interval(lo, hi), result);
        return result;
    }

    private void findOverlappingInterval(ITNode node, Interval query, List<Interval> result) {
        if (node == null) return;
        if (node.interval.overlaps(query))
            result.add(node.interval);
        if (node.left != null && node.left.maxHi >= query.lo)
            findOverlappingInterval(node.left, query, result);
        if (node.interval.lo <= query.hi)
            findOverlappingInterval(node.right, query, result);
    }

    public void display() {
        inorder(root);
    }

    private void inorder(ITNode node) {
        if (node == null) return;
        inorder(node.left);
        System.out.println(node.interval + " max=" + node.maxHi);
        inorder(node.right);
    }

    public static void main(String[] args) {
        IntervalTree tree = new IntervalTree();
        tree.insert(15, 20);
        tree.insert(10, 30);
        tree.insert(17, 19);
        tree.insert(5, 20);
        tree.insert(12, 15);

        System.out.println("Interval tree:");
        tree.display();

        System.out.println("\nOverlapping point 14:");
        for (Interval iv : tree.findOverlapping(14))
            System.out.println("  " + iv);

        System.out.println("\nOverlapping interval [16, 18]:");
        for (Interval iv : tree.findOverlappingInterval(16, 18))
            System.out.println("  " + iv);
    }
}
```

---

## 103.11 Applications

### Interval Tree Applications

| Application | Use Case |
|---|---|
| Calendar scheduling | Find all events in a time range |
| Computational geometry | Find all rectangles overlapping a point |
| Database range queries | Index range-based attributes |
| Resource allocation | Find conflicting reservations |
| Genomics | Find overlapping gene regions |

### Order Statistic Tree Applications

| Application | Use Case |
|---|---|
| Dynamic median | Select(n/2) |
| Percentile queries | Select(n * p/100) |
| Leaderboard | Rank to find position |
| Database ORDER BY | Dynamic sorted access |
| Inversion counting | Count elements between values |
| Dynamic quantiles | Streaming quantile estimation |

---

## 103.12 Related Structures

### Segment Tree (Comparison)

| Feature | Interval Tree | Segment Tree |
|---|---|---|
| Stored data | Arbitrary intervals | Array ranges |
| Query | Overlapping intervals | Aggregate over range |
| Update | Insert/delete intervals | Point/range update |
| Space | O(n) | O(n) |
| Time | O(log n + k) | O(log n) |

### Fenwick Tree (Comparison)

| Feature | Order Statistic Tree | Fenwick Tree |
|---|---|---|
| Dynamic insert/delete | Yes | No (fixed size) |
| Select(k) | O(log n) | O(log n) with binary search |
| Rank(x) | O(log n) | O(log n) |
| Range sum | O(log n) | O(log n) |
| Space | O(n) | O(n) |

---

## 103.13 Exercises

### Conceptual Exercises

1. **Prove** that the augmentation `max_hi` is correctly maintained after insert and delete operations.

2. **Show** that interval tree search for point x is O(log n + k) where k is the number of reported intervals.

3. **Explain** why order statistic tree's select operation is O(log n) even though it traverses a single path from root to leaf.

4. **Compare** the augmentation needed for interval trees vs order statistic trees. What's the general pattern?

### Coding Exercises

5. **Implement** an interval tree that supports finding the interval with the maximum overlap count at any point.

6. **Extend** the order statistic tree to support `select_range(k1, k2)` — return all elements between the k1-th and k2-th smallest.

7. **Implement** a persistent order statistic tree using path copying.

8. **Build** a function that uses an order statistic tree to compute the dynamic median of a stream.

### Challenge Exercises

9. **Design** an interval tree that supports stabbing queries (find all intervals containing a point) and segment queries (find all intervals contained within a range) simultaneously.

10. **Implement** a 2D range tree that supports counting points in a rectangle, using order statistic trees as secondary structures.

---

## 103.14 Interview Questions

### Conceptual Questions

1. **Q**: What's the difference between an interval tree and a segment tree?
   **A**: Interval trees store arbitrary intervals and find overlaps. Segment trees partition a fixed range and compute aggregates (sum, min, max) over subranges. Interval trees use BST + max augmentation; segment trees use a complete binary tree over array indices.

2. **Q**: How would you find the k-th smallest element in a stream of numbers?
   **A**: Maintain an order statistic tree. Insert each element as it arrives. Select(k) gives the answer in O(log n). For approximate answers, use a count-min sketch or t-digest.

3. **Q**: How does the `max_hi` augmentation help prune the search in an interval tree?
   **A**: If `left.max_hi < x`, all intervals in the left subtree end before x, so none can contain x. This lets us skip the entire left subtree, reducing the search from O(n) to O(log n + k).

### Implementation Questions

4. **Q**: How would you handle interval tree rotations in a balanced BST?
   **A**: After rotation, update `max_hi` for both rotated nodes: `max_hi = max(hi, left.max_hi, right.max_hi)`. This is O(1) per rotation.

5. **Q**: How do you implement a dynamic median using an order statistic tree?
   **A**: Maintain two OSTs: `lo` for elements ≤ median, `hi` for elements > median. Rebalance so `|lo| - |hi|` ∈ {0, 1}. Median = `lo.max()` or `(lo.max() + hi.min()) / 2`.

### Systems Questions

6. **Q**: How would you use an interval tree for a calendar application?
   **A**: Each event is an interval [start, end]. The interval tree supports: (1) find all events at time t, (2) find all events in range [t1, t2], (3) detect conflicts when adding a new event.

---

## 103.15 Cross-References

- **Chapter 9 (Binary Search Trees)**: Foundation for both structures
- **Chapter 10 (Balanced BSTs)**: AVL/Red-Black for guaranteed O(log n)
- **Chapter 104 (Segment Trees)**: Related range query structure
- **Chapter 105 (Fenwick Trees)**: Alternative for prefix/rank queries
- **Chapter 108 (Union-Find)**: Disjoint set operations
- **Chapter 112 (Heap)**: Alternative for median/percentile tracking

---

## Summary

| Structure | Key Augmentation | Key Operations | Time |
|---|---|---|---|
| Interval Tree | max_hi in subtree | Find overlapping intervals | O(log n + k) |
| Order Statistic Tree | subtree size | Select(k), Rank(x) | O(log n) |

**Key Takeaway**: Augmentation is a powerful technique that extends BSTs with additional information. The key insight is that augmented data can be maintained in O(1) extra work per structural change (insert, delete, rotation), enabling O(log n) queries for problems that would otherwise require O(n) or O(n log n).
