# Chapter 77: B-Trees and Database Indexing

## Prerequisites
- Binary search trees ([Chapter 14](ch14-bst.md))
- Disk I/O concepts

## Interview Frequency: ★★★

B-Trees are the foundation of database indexing. **Amazon**, **Google**, and database companies test B-Tree knowledge for system design interviews.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| B-Tree structure | ★★★ | Medium | Multi-way search tree |
| B-Tree operations | ★★★ | Medium | Insert, delete, search |
| B+ Tree | ★★★ | Medium | Leaf-linked variant |
| Disk I/O analysis | ★★ | Medium | Why B-Trees for disks |

---

## Definition

A **B-Tree** of order m is a self-balancing search tree where:
- Each node has at most m children and m-1 keys
- Each non-root node has at least ⌈m/2⌉ children
- All leaves are at the same depth
- Keys within each node are sorted

A **B+ Tree** is a variant where:
- All data resides in leaf nodes (internal nodes only store keys for routing)
- Leaf nodes are linked together (enabling efficient range scans)

## Motivation

Disk access is ~100,000× slower than memory access. B-Trees minimize disk I/O by:
- Having high fanout (many children per node → short tree)
- Each node fits in one disk page (typically 4KB)
- Tree height is O(log_m n), which is tiny for large m

| Order m | Height for 10^9 keys | Disk reads |
|---|---|---|
| 100 | 5 | 5 |
| 500 | 4 | 4 |
| 1000 | 3 | 3 |

## Intuition

A B-Tree is like a book index. Instead of one key per page (like a BST), you have many keys per page. You open one page, scan through its keys to find which "sub-page" to go to, then open that. With 1000 keys per page, you can index a billion entries in just 3 page reads.

---

## 77.1 B-Tree Properties

### Invariants

1. Every node has at most m children
2. Every non-root internal node has at least ⌈m/2⌉ children
3. The root has at least 2 children (if not a leaf)
4. All leaves are at the same depth
5. A node with k children has k-1 keys

### Why These Rules Work

- Rule 2 ensures nodes don't get too empty (wastes space)
- Rule 4 ensures balanced height (all searches take the same time)
- Rule 5 ensures keys are distributed across the tree

---

## 77.2 B-Tree Search

Search is like BST search but with multiple keys per node:
1. In the current node, find the key range the target falls into
2. If found, return
3. Otherwise, follow the appropriate child pointer
4. Repeat until found or reach a leaf

### Dry Run

B-Tree of order 5 (max 4 keys per node):
```
         [10, 20, 30]
        /    |    |   \
  [1,5] [12,15] [22,25] [35,40]
```

Search for 22:
1. At root [10,20,30]: 22 > 20 and < 30 → go to 3rd child
2. At [22,25]: found 22!

Search for 16:
1. At root [10,20,30]: 16 > 10 and < 20 → go to 2nd child
2. At [12,15]: 16 > 15 → not found (leaf)

---

## 77.3 B-Tree Insertion

1. Search for the correct leaf node
2. Insert the key in sorted order
3. If the node overflows (> m-1 keys), **split**:
   - Take the median key, push it up to the parent
   - Split remaining keys into two nodes
4. If the parent overflows, split recursively
5. If the root splits, create a new root

### Dry Run — Insert 25 into order-3 B-Tree

```
Initial:    [10]
           /    \
        [5]    [15, 20]

Insert 25: Goes to right leaf [15, 20] → [15, 20, 25] → OVERFLOW!

Split: median = 20, push up
        [10, 20]
       /    |    \
     [5]  [15]  [25]

Root [10, 20] has 2 keys, order 3 allows max 2 → OK (order 3 means max 2 keys, 3 children)
```

---

## 77.4 B-Tree Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

template <int ORDER>
class BTree {
    struct Node {
        std::vector<int> keys;
        std::vector<Node*> children;
        bool leaf;
        Node(bool isLeaf) : leaf(isLeaf) {}
    };

    Node* root;

    void splitChild(Node* parent, int idx) {
        Node* full = parent->children[idx];
        Node* newNode = new Node(full->leaf);
        int mid = ORDER / 2;

        for (int i = mid + 1; i < (int)full->keys.size(); i++)
            newNode->keys.push_back(full->keys[i]);

        if (!full->leaf) {
            for (int i = mid + 1; i <= (int)full->children.size() - 1; i++)
                newNode->children.push_back(full->children[i]);
            full->children.resize(mid + 1);
        }

        parent->keys.insert(parent->keys.begin() + idx, full->keys[mid]);
        parent->children.insert(parent->children.begin() + idx + 1, newNode);
        full->keys.resize(mid);
    }

    void insertNonFull(Node* node, int key) {
        int i = node->keys.size() - 1;

        if (node->leaf) {
            node->keys.push_back(0);
            while (i >= 0 && node->keys[i] > key) {
                node->keys[i + 1] = node->keys[i];
                i--;
            }
            node->keys[i + 1] = key;
        } else {
            while (i >= 0 && node->keys[i] > key) i--;
            i++;
            if ((int)node->children[i]->keys.size() == ORDER - 1) {
                splitChild(node, i);
                if (key > node->keys[i]) i++;
            }
            insertNonFull(node->children[i], key);
        }
    }

    bool search(Node* node, int key) {
        if (!node) return false;
        int i = 0;
        while (i < (int)node->keys.size() && key > node->keys[i]) i++;
        if (i < (int)node->keys.size() && key == node->keys[i]) return true;
        if (node->leaf) return false;
        return search(node->children[i], key);
    }

    void print(Node* node, int depth) {
        if (!node) return;
        std::string indent(depth * 2, ' ');
        std::cout << indent << "[";
        for (int i = 0; i < (int)node->keys.size(); i++) {
            if (i) std::cout << ",";
            std::cout << node->keys[i];
        }
        std::cout << "]\n";
        if (!node->leaf)
            for (auto child : node->children)
                print(child, depth + 1);
    }

public:
    BTree() : root(nullptr) {}

    void insert(int key) {
        if (!root) {
            root = new Node(true);
            root->keys.push_back(key);
            return;
        }
        if ((int)root->keys.size() == ORDER - 1) {
            Node* newRoot = new Node(false);
            newRoot->children.push_back(root);
            splitChild(newRoot, 0);
            root = newRoot;
        }
        insertNonFull(root, key);
    }

    bool search(int key) { return search(root, key); }

    void print() { print(root, 0); }
};

int main() {
    BTree<5> tree;
    for (int x : {10, 20, 5, 6, 12, 30, 7, 17, 3, 1, 25, 40, 50})
        tree.insert(x);

    std::cout << "B-Tree structure:\n";
    tree.print();

    for (int x : {6, 15, 25, 50})
        std::cout << "Search " << x << ": "
                  << (tree.search(x) ? "found" : "not found") << "\n";

    return 0;
}
```

### Python Implementation

```python
class BTree:
    class Node:
        def __init__(self, leaf=False):
            self.keys = []
            self.children = []
            self.leaf = leaf

    def __init__(self, order=5):
        self.order = order
        self.root = self.Node(leaf=True)

    def _split_child(self, parent, idx):
        full = parent.children[idx]
        mid = self.order // 2
        new_node = self.Node(leaf=full.leaf)

        new_node.keys = full.keys[mid+1:]
        if not full.leaf:
            new_node.children = full.children[mid+1:]
            full.children = full.children[:mid+1]

        parent.keys.insert(idx, full.keys[mid])
        parent.children.insert(idx + 1, new_node)
        full.keys = full.keys[:mid]

    def insert(self, key):
        root = self.root
        if len(root.keys) == self.order - 1:
            new_root = self.Node()
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root
        self._insert_non_full(self.root, key)

    def _insert_non_full(self, node, key):
        i = len(node.keys) - 1
        if node.leaf:
            node.keys.append(0)
            while i >= 0 and node.keys[i] > key:
                node.keys[i+1] = node.keys[i]
                i -= 1
            node.keys[i+1] = key
        else:
            while i >= 0 and node.keys[i] > key:
                i -= 1
            i += 1
            if len(node.children[i].keys) == self.order - 1:
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            self._insert_non_full(node.children[i], key)

    def search(self, key):
        return self._search(self.root, key)

    def _search(self, node, key):
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1
        if i < len(node.keys) and key == node.keys[i]:
            return True
        if node.leaf:
            return False
        return self._search(node.children[i], key)

# Example
tree = BTree(5)
for x in [10, 20, 5, 6, 12, 30, 7, 17, 3, 1, 25, 40, 50]:
    tree.insert(x)
for x in [6, 15, 25, 50]:
    print(f"Search {x}: {'found' if tree.search(x) else 'not found'}")
```

### Java Implementation

```java
import java.util.*;

public class BTree {
    static final int ORDER = 5;

    static class Node {
        List<Integer> keys = new ArrayList<>();
        List<Node> children = new ArrayList<>();
        boolean leaf;
        Node(boolean leaf) { this.leaf = leaf; }
    }

    Node root = new Node(true);

    void splitChild(Node parent, int idx) {
        Node full = parent.children.get(idx);
        Node newNode = new Node(full.leaf);
        int mid = ORDER / 2;

        newNode.keys.addAll(full.keys.subList(mid + 1, full.keys.size()));
        if (!full.leaf) {
            newNode.children.addAll(full.children.subList(mid + 1, full.children.size()));
            full.children = new ArrayList<>(full.children.subList(0, mid + 1));
        }

        parent.keys.add(idx, full.keys.get(mid));
        parent.children.add(idx + 1, newNode);
        full.keys = new ArrayList<>(full.keys.subList(0, mid));
    }

    void insert(int key) {
        if (root.keys.size() == ORDER - 1) {
            Node newRoot = new Node(false);
            newRoot.children.add(root);
            splitChild(newRoot, 0);
            root = newRoot;
        }
        insertNonFull(root, key);
    }

    void insertNonFull(Node node, int key) {
        int i = node.keys.size() - 1;
        if (node.leaf) {
            node.keys.add(0);
            while (i >= 0 && node.keys.get(i) > key) {
                node.keys.set(i + 1, node.keys.get(i));
                i--;
            }
            node.keys.set(i + 1, key);
        } else {
            while (i >= 0 && node.keys.get(i) > key) i--;
            i++;
            if (node.children.get(i).keys.size() == ORDER - 1) {
                splitChild(node, i);
                if (key > node.keys.get(i)) i++;
            }
            insertNonFull(node.children.get(i), key);
        }
    }

    boolean search(Node node, int key) {
        if (node == null) return false;
        int i = 0;
        while (i < node.keys.size() && key > node.keys.get(i)) i++;
        if (i < node.keys.size() && key == node.keys.get(i)) return true;
        if (node.leaf) return false;
        return search(node.children.get(i), key);
    }

    public static void main(String[] args) {
        BTree tree = new BTree();
        for (int x : new int[]{10,20,5,6,12,30,7,17,3,1,25,40,50})
            tree.insert(x);
        for (int x : new int[]{6,15,25,50})
            System.out.println("Search " + x + ": " + tree.search(tree.root, x));
    }
}
```

### Complexity

| Operation | Time | Disk I/O |
|---|---|---|
| Search | O(log_m n) | O(log_m n) |
| Insert | O(log_m n) | O(log_m n) |
| Delete | O(log_m n) | O(log_m n) |
| Range query (B+ Tree) | O(log_m n + k) | O(log_m n + k) |

---

## 77.5 B-Tree vs B+ Tree

| Feature | B-Tree | B+ Tree |
|---|---|---|
| Data location | Internal + leaf | Leaf only |
| Leaf linkage | No | Yes (linked list) |
| Range queries | Slow | Fast (scan leaves) |
| Internal node capacity | Smaller | Larger |
| Used by | MongoDB | MySQL, PostgreSQL |

### Why B+ Trees Win for Databases

1. **Range queries**: Scan leaves via linked list — no tree traversal needed
2. **More keys per internal node**: No data pointers, just keys → higher fanout → shorter tree
3. **Cache friendly**: Sequential leaf access is prefetchable
4. **Predictable performance**: All data at the same depth

---

## 77.6 B-Tree Deletion

Deletion is more complex than insertion:
1. **Key in leaf**: Simply remove it
2. **Key in internal node**: Replace with predecessor/successor, then delete that
3. **Underflow** (too few keys): Borrow from sibling or merge with sibling

---

## Exercises

1. **Implement B-Tree deletion**: Handle all cases — leaf deletion, internal deletion, borrowing from siblings, and merging siblings.

2. **B+ Tree**: Implement a B+ Tree with linked leaves. Support range queries that return all keys in [lo, hi].

3. **Disk simulation**: Simulate disk I/O by counting node accesses. Compare B-Tree (order 100) vs BST for 10^6 keys.

4. **Bulk loading**: Implement bottom-up B-Tree construction from a sorted array. Compare with repeated insertion.

5. **Concurrent B-Tree**: Research how databases implement concurrent access to B-Trees (latch coupling, B-link trees).

---

## Interview Questions

1. **Q: Why are B-Trees preferred over BSTs for databases?**
   A: B-Trees minimize disk I/O by having high fanout (many keys per node). A B-Tree with order 1000 can index 1 billion keys in 3 disk reads, while a BST would need 30.

2. **Q: What's the difference between B-Tree and B+ Tree?**
   A: B+ Trees store data only in leaves and link leaves together. Internal nodes only store routing keys. This enables efficient range queries (scan linked leaves) and higher fanout (internal nodes are smaller).

3. **Q: How does B-Tree insertion handle overflow?**
   A: When a node has m keys (overflow), split it: take the median key, push it to the parent, and split the remaining keys into two nodes. If the parent overflows, split recursively. If the root splits, create a new root.

4. **Q: What order m should a B-Tree use?**
   A: Choose m so that one node fits in a disk page. For 4KB pages and 8-byte keys: m ≈ 4096/8 = 512. The exact choice depends on the key size, pointer size, and metadata per node.

5. **Q: How do B-Trees handle range queries?**
   A: Standard B-Trees require traversing from root for each key. B+ Trees scan leaves sequentially via linked list, making range queries O(log_m n + k) where k is the result size.

---

## Cross-References

- [Chapter 14: Binary Search Trees](ch14-bst.md) — The foundation; B-Trees generalize BSTs to multi-way
- [Chapter 74: Skip Lists](ch74-skip-lists.md) — Alternative to B-Trees for in-memory indexing
- [Chapter 105: Cuckoo and Robin Hood Hashing](ch94-hashing-deep-dive.md) — Alternative indexing for exact-match queries

---

## Summary

| Property | B-Tree | B+ Tree |
|---|---|---|
| Search | O(log_m n) | O(log_m n) |
| Insert | O(log_m n) | O(log_m n) |
| Range query | O(n) | O(log_m n + k) |
| Disk I/O | Minimal | Minimal |
| Best for | General indexing | Range-heavy workloads |
