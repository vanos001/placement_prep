# Chapter 75: Persistent Data Structures

## Prerequisites

- Segment trees
- Binary search trees
- Pointers and memory management

## Interview Frequency: ★★★

Persistent data structures preserve previous versions after modifications. They appear in **Google** and **ByteDance** interviews, particularly for problems involving historical queries.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Persistent array | ★★★ | Medium | Copy-on-write |
| Persistent segment tree | ★★★★ | Hard | Versioned queries |
| Persistent BST | ★★ | Hard | Versioned operations |

---

## 75.1 Concept

A **persistent** data structure keeps all previous versions accessible after updates. The key technique is **copy-on-write**: only create new nodes along the update path, sharing unchanged subtrees with previous versions.

```
Version 0:     1
              / \
             2   3

Version 1 (update left to 5):
             1'      ← new root
            / \
           5   3     ← shared with v0
```

---

## 75.2 Persistent Array

```cpp
#include <iostream>
#include <vector>

struct Node {
    int val;
    Node *left, *right;
    Node(int v) : val(v), left(nullptr), right(nullptr) {}
    Node(Node* l, Node* r) : left(l), right(r), val(0) {}
};

// Build persistent array
Node* build(const std::vector<int>& arr, int lo, int hi) {
    if (lo == hi) return new Node(arr[lo]);
    int mid = (lo + hi) / 2;
    return new Node(build(arr, lo, mid), build(arr, mid + 1, hi));
}

// Update: returns new root
Node* update(Node* prev, int lo, int hi, int pos, int val) {
    if (lo == hi) return new Node(val);
    int mid = (lo + hi) / 2;
    if (pos <= mid)
        return new Node(update(prev->left, lo, mid, pos, val), prev->right);
    else
        return new Node(prev->left, update(prev->right, mid + 1, hi, pos, val));
}

// Query
int query(Node* node, int lo, int hi, int pos) {
    if (lo == hi) return node->val;
    int mid = (lo + hi) / 2;
    if (pos <= mid) return query(node->left, lo, mid, pos);
    return query(node->right, mid + 1, hi, pos);
}

int main() {
    std::vector<int> arr = {1, 2, 3, 4, 5};
    int n = arr.size();
    
    // Version 0
    Node* v0 = build(arr, 0, n - 1);
    
    // Version 1: update index 2 to 10
    Node* v1 = update(v0, 0, n - 1, 2, 10);
    
    // Version 2: update index 0 to 20
    Node* v2 = update(v1, 0, n - 1, 0, 20);
    
    std::cout << "Version 0: ";
    for (int i = 0; i < n; i++) std::cout << query(v0, 0, n - 1, i) << " ";
    std::cout << "\n";
    
    std::cout << "Version 1: ";
    for (int i = 0; i < n; i++) std::cout << query(v1, 0, n - 1, i) << " ";
    std::cout << "\n";
    
    std::cout << "Version 2: ";
    for (int i = 0; i < n; i++) std::cout << query(v2, 0, n - 1, i) << " ";
    std::cout << "\n";
    
    return 0;
}
```

---

## 75.3 Persistent Segment Tree

Each update creates O(log n) new nodes. Total space: O(n + Q log n).

```cpp
#include <iostream>
#include <vector>

struct PSTNode {
    int val;
    PSTNode *left, *right;
    PSTNode(int v = 0) : val(v), left(nullptr), right(nullptr) {}
    PSTNode(PSTNode* l, PSTNode* r) : left(l), right(r) {
        val = (l ? l->val : 0) + (r ? r->val : 0);
    }
};

PSTNode* build(int lo, int hi) {
    if (lo == hi) return new PSTNode(0);
    int mid = (lo + hi) / 2;
    return new PSTNode(build(lo, mid), build(mid + 1, hi));
}

PSTNode* update(PSTNode* prev, int lo, int hi, int pos, int val) {
    if (lo == hi) return new PSTNode(prev->val + val);
    int mid = (lo + hi) / 2;
    if (pos <= mid)
        return new PSTNode(update(prev->left, lo, mid, pos, val), prev->right);
    else
        return new PSTNode(prev->left, update(prev->right, mid + 1, hi, pos, val));
}

int query(PSTNode* node, int lo, int hi, int ql, int qr) {
    if (!node || qr < lo || hi < ql) return 0;
    if (ql <= lo && hi <= qr) return node->val;
    int mid = (lo + hi) / 2;
    return query(node->left, lo, mid, ql, qr) + 
           query(node->right, mid + 1, hi, ql, qr);
}

int main() {
    std::vector<int> arr = {1, 2, 3, 4, 5};
    int n = arr.size();
    
    // Build version 0 (all zeros)
    PSTNode* root0 = build(0, n - 1);
    
    // Version 1: add arr values one by one
    std::vector<PSTNode*> roots = {root0};
    for (int i = 0; i < n; i++) {
        roots.push_back(update(roots.back(), 0, n - 1, i, arr[i]));
    }
    
    // Range sum queries on different versions
    // Version 3 has values [1, 2, 3, 0, 0]
    std::cout << "Version 3, range [0, 2] sum: " 
              << query(roots[3], 0, n - 1, 0, 2) << "\n"; // 1+2+3 = 6
    
    // Version 5 has values [1, 2, 3, 4, 5]
    std::cout << "Version 5, range [1, 4] sum: " 
              << query(roots[5], 0, n - 1, 1, 4) << "\n"; // 2+3+4+5 = 14
    
    return 0;
}
```

### Python — Persistent Segment Tree

```python
class PSTNode:
    __slots__ = ['val', 'left', 'right']

    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def build(lo, hi):
    if lo == hi:
        return PSTNode(0)
    mid = (lo + hi) // 2
    left = build(lo, mid)
    right = build(mid + 1, hi)
    return PSTNode(left.val + right.val, left, right)


def update(prev, lo, hi, pos, val):
    if lo == hi:
        return PSTNode(prev.val + val)
    mid = (lo + hi) // 2
    if pos <= mid:
        return PSTNode(0, update(prev.left, lo, mid, pos, val), prev.right)
    else:
        return PSTNode(0, prev.left, update(prev.right, mid + 1, hi, pos, val))


def query(node, lo, hi, ql, qr):
    if node is None or qr < lo or hi < ql:
        return 0
    if ql <= lo and hi <= qr:
        return node.val
    mid = (lo + hi) // 2
    return query(node.left, lo, mid, ql, qr) + query(node.right, mid + 1, hi, ql, qr)


def kth_smallest(root_l, root_r, lo, hi, k):
    """Find k-th smallest in range using two version roots."""
    if lo == hi:
        return lo
    mid = (lo + hi) // 2
    left_count = root_r.left.val - root_l.left.val
    if k <= left_count:
        return kth_smallest(root_l.left, root_r.left, lo, mid, k)
    return kth_smallest(root_l.right, root_r.right, mid + 1, hi, k - left_count)


if __name__ == "__main__":
    arr = [1, 2, 3, 4, 5]
    n = len(arr)

    # Build version 0 (all zeros)
    root0 = build(0, n - 1)

    # Create versions by adding elements one by one
    roots = [root0]
    for i in range(n):
        roots.append(update(roots[-1], 0, n - 1, i, arr[i]))

    # Version 3 has values [1, 2, 3, 0, 0]
    print(f"Version 3, range [0, 2] sum: {query(roots[3], 0, n-1, 0, 2)}")  # 6

    # Version 5 has values [1, 2, 3, 4, 5]
    print(f"Version 5, range [1, 4] sum: {query(roots[5], 0, n-1, 1, 4)}")  # 14

    # K-th smallest in range [1, 4] (sorted: 2, 3, 4, 5)
    # 2nd smallest = 3
    print(f"K-th smallest in [1,4] k=2: {kth_smallest(roots[1], roots[5], 0, n-1, 2)}")  # 3
```

### Java — Persistent Segment Tree

```java
public class PersistentSegmentTree {
    static class Node {
        int val;
        Node left, right;
        Node(int val, Node left, Node right) {
            this.val = val; this.left = left; this.right = right;
        }
    }

    static Node build(int lo, int hi) {
        if (lo == hi) return new Node(0, null, null);
        int mid = (lo + hi) / 2;
        Node left = build(lo, mid);
        Node right = build(mid + 1, hi);
        return new Node(left.val + right.val, left, right);
    }

    static Node update(Node prev, int lo, int hi, int pos, int val) {
        if (lo == hi) return new Node(prev.val + val, null, null);
        int mid = (lo + hi) / 2;
        if (pos <= mid)
            return new Node(0, update(prev.left, lo, mid, pos, val), prev.right);
        else
            return new Node(0, prev.left, update(prev.right, mid + 1, hi, pos, val));
    }

    static int query(Node node, int lo, int hi, int ql, int qr) {
        if (node == null || qr < lo || hi < ql) return 0;
        if (ql <= lo && hi <= qr) return node.val;
        int mid = (lo + hi) / 2;
        return query(node.left, lo, mid, ql, qr) +
               query(node.right, mid + 1, hi, ql, qr);
    }

    static int kthSmallest(Node rootL, Node rootR, int lo, int hi, int k) {
        if (lo == hi) return lo;
        int mid = (lo + hi) / 2;
        int leftCount = rootR.left.val - rootL.left.val;
        if (k <= leftCount)
            return kthSmallest(rootL.left, rootR.left, lo, mid, k);
        return kthSmallest(rootL.right, rootR.right, mid + 1, hi, k - leftCount);
    }

    public static void main(String[] args) {
        int[] arr = {1, 2, 3, 4, 5};
        int n = arr.length;

        Node root0 = build(0, n - 1);
        Node[] roots = new Node[n + 1];
        roots[0] = root0;
        for (int i = 0; i < n; i++) {
            roots[i + 1] = update(roots[i], 0, n - 1, i, arr[i]);
        }

        System.out.println("Version 3, range [0, 2] sum: " + query(roots[3], 0, n-1, 0, 2));  // 6
        System.out.println("Version 5, range [1, 4] sum: " + query(roots[5], 0, n-1, 1, 4));  // 14
        System.out.println("K-th smallest in [1,4] k=2: " + kthSmallest(roots[1], roots[5], 0, n-1, 2));  // 3
    }
}
```

---

## 75.4 K-th Smallest in Range

Classic application: find the k-th smallest element in arr[l..r]. This is a beautiful example of how persistent data structures enable queries that would otherwise require complex data structures.

**Key Idea**: Build a persistent segment tree where each version `roots[i]` represents the prefix `arr[0..i-1]`. The tree is built on **value coordinates** (coordinate-compressed values), not array indices. Each leaf stores the count of that value in the prefix. To query the k-th smallest in `arr[l..r]`, we compute `roots[r+1] - roots[l]` (subtracting counts) and walk down the tree.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Using persistent segment tree on values
// Each version adds one more element
// Range [l, r] corresponds to roots[r+1] - roots[l]

int kthSmallest(PSTNode* rootL, PSTNode* rootR, int lo, int hi, int k) {
    if (lo == hi) return lo;
    int mid = (lo + hi) / 2;
    int leftCount = rootR->left->val - rootL->left->val;
    if (k <= leftCount)
        return kthSmallest(rootL->left, rootR->left, lo, mid, k);
    return kthSmallest(rootL->right, rootR->right, mid + 1, hi, k - leftCount);
}

// (Using PSTNode from above)
```

**How it works**:
1. `rootR->left->val - rootL->left->val` = count of values in the left half of the value range that appear in `arr[l..r]`.
2. If `k <= leftCount`, the k-th smallest is in the left half → recurse left.
3. Otherwise, skip the left half and search for `(k - leftCount)`-th in the right half.
4. Time: O(log n) per query (walks one path from root to leaf).

---

## Summary

| Structure | Update Space | Query Time | Application |
|---|---|---|---|
| Persistent Array | O(log n) new nodes | O(log n) | Version history |
| Persistent Segment Tree | O(log n) new nodes | O(log n) | Range queries on versions |
| Persistent BST | O(log n) new nodes | O(log n) | Ordered versions |

---

## 75.5 Persistent Trees

Any tree structure can be made persistent using path copying. When modifying a node, create a new copy and recursively copy the path to the root.

**Space**: O(log n) new nodes per update for balanced trees.

**Applications**: Version control systems, undo/redo, historical queries.

### Example: Persistent Binary Search Tree

```cpp
#include <iostream>

struct PBSTNode {
    int val;
    PBSTNode *left, *right;
    PBSTNode(int v, PBSTNode* l = nullptr, PBSTNode* r = nullptr)
        : val(v), left(l), right(r) {}
};

// Insert into persistent BST — returns new root
PBSTNode* insert(PBSTNode* root, int val) {
    if (!root) return new PBSTNode(val);
    if (val < root->val)
        return new PBSTNode(root->val, insert(root->left, val), root->right);
    else if (val > root->val)
        return new PBSTNode(root->val, root->left, insert(root->right, val));
    else
        return root; // duplicate, no change
}

// Search in persistent BST
bool search(PBSTNode* root, int val) {
    if (!root) return false;
    if (val == root->val) return true;
    if (val < root->val) return search(root->left, val);
    return search(root->right, val);
}

int main() {
    PBSTNode* v0 = nullptr;              // empty tree
    PBSTNode* v1 = insert(v0, 5);        // {5}
    PBSTNode* v2 = insert(v1, 3);        // {3, 5}
    PBSTNode* v3 = insert(v2, 7);        // {3, 5, 7}
    PBSTNode* v4 = insert(v3, 1);        // {1, 3, 5, 7}

    // v1 still only has {5}
    std::cout << "v1 has 3: " << search(v1, 3) << "\n";  // 0
    std::cout << "v4 has 3: " << search(v4, 3) << "\n";  // 1

    return 0;
}
```

Each version shares most of its nodes with previous versions. Insertion creates O(log n) new nodes on average (for balanced trees) or O(n) in the worst case (for degenerate trees).
