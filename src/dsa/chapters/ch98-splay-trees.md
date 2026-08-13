# Chapter 98: Splay Trees

## Prerequisites
- Binary search trees ([Chapter 14](ch14-bst.md))
- Tree rotations ([Chapter 14](ch14-bst.md))
- Amortized analysis basics

## Interview Frequency: ★★

Splay trees are self-adjusting BSTs where recently accessed elements move to the root. **Google** and research labs test splay tree concepts, especially the amortized analysis and the dynamic optimality conjecture.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Splay operation | ★★ | Medium | Zig, Zig-Zig, Zig-Zag |
| Amortized analysis | ★ | Hard | Potential method |
| Applications | ★★ | Medium | Caching, sequences |
| Delete operation | ★★ | Medium | Splay then remove |
| Dynamic optimality | ★ | Hard | Open conjecture |

---

## Definition

A **splay tree** is a self-adjusting binary search tree that moves accessed elements to the root using a sequence of rotations called **splaying**. Unlike AVL or Red-Black trees, splay trees store no balance information — they achieve O(log n) amortized time through the splay operation alone.

## Motivation

Why use splay trees when AVL and Red-Black trees guarantee O(log n) worst-case?

1. **Simplicity**: No balance factors, colors, or height tracking
2. **Adaptivity**: Automatically adapts to access patterns (temporal locality)
3. **Amortized optimality**: Conjectured to be as good as any other BST for any access sequence
4. **Space**: No extra storage per node for balance info

## Intuition

Imagine a library where you always put the book you just read back on the top shelf. Books you read frequently end up near the top (fast access), while rarely-read books drift to the bottom. Splay trees do the same: frequently accessed nodes naturally migrate toward the root.

---

## 98.1 The Splay Operation

### Definition

Splaying moves a node x to the root through a sequence of rotations. The specific rotation depends on x's position relative to its parent and grandparent.

### Three Cases

| Case | Condition | Action |
|---|---|---|
| **Zig** | Parent is root | Single rotation |
| **Zig-Zig** | x and parent are both left (or both right) children | Rotate grandparent, then parent |
| **Zig-Zag** | x is right child, parent is left child (or vice versa) | Rotate parent, then rotate grandparent |

### Why Zig-Zig Order Matters

The key insight: in the Zig-Zig case, we rotate the **grandparent first**, then the parent. This is counter-intuitive (we'd expect to rotate the closer node first), but it's essential for the amortized O(log n) bound. Rotating in the wrong order degrades to O(n) amortized.

### Step-by-Step Walkthrough

Consider inserting nodes 1-7 in order. Since the chapter's `insert()` splays each newly inserted node to the root, the tree is a degenerate LEFT chain with 7 at the root:

```
After inserting 1,2,3,4,5,6,7 (each insert splays the new node to root):
                7
               /
              6
             /
            5
           /
          4
         /
        3
       /
      2
     /
    1

Searching for 1: splay(1) brings 1 to the root via Zig-Zig rotations.
  Step 1: Zig-Zig at (1,2,3) → rotate 3, then 2
  Step 2: Zig-Zig at (1,4,5) → rotate 5, then 4
  Step 3: Zig-Zig at (1,6,7) → rotate 7, then 6

Result: balanced tree with 1 at root
```

### Dry Run of Splay Cases

```
Zig (parent is root):
    p          x
   / \   →   / \
  x   C     A   p
 / \           / \
A   B         B   C

Zig-Zig (both left children):
        g              x
       / \            / \
      p   D    →     A   p
     / \                / \
    x   C              B   g
   / \                    / \
  A   B                  C   D

Zig-Zag (left-right):
      g              x
     / \            / \
    A   p    →     /   \
       / \        g     p
      x   D      / \   / \
     / \         A  B  C  D
    B   C
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>

struct SplayNode {
    int key;
    SplayNode *left, *right, *parent;
    SplayNode(int k) : key(k), left(nullptr), right(nullptr), parent(nullptr) {}
};

class SplayTree {
    SplayNode* root;

    void rotateLeft(SplayNode* x) {
        SplayNode* y = x->right;
        if (y) {
            x->right = y->left;
            if (y->left) y->left->parent = x;
            y->parent = x->parent;
        }
        if (!x->parent) root = y;
        else if (x == x->parent->left) x->parent->left = y;
        else x->parent->right = y;
        if (y) y->left = x;
        x->parent = y;
    }

    void rotateRight(SplayNode* x) {
        SplayNode* y = x->left;
        if (y) {
            x->left = y->right;
            if (y->right) y->right->parent = x;
            y->parent = x->parent;
        }
        if (!x->parent) root = y;
        else if (x == x->parent->left) x->parent->left = y;
        else x->parent->right = y;
        if (y) y->right = x;
        x->parent = y;
    }

    void splay(SplayNode* x) {
        while (x->parent) {
            SplayNode* p = x->parent;
            SplayNode* g = p->parent;
            if (!g) {
                // Zig
                if (x == p->left) rotateRight(p);
                else rotateLeft(p);
            } else if (x == p->left && p == g->left) {
                // Zig-Zig (both left)
                rotateRight(g);
                rotateRight(p);
            } else if (x == p->right && p == g->right) {
                // Zig-Zig (both right)
                rotateLeft(g);
                rotateLeft(p);
            } else if (x == p->right && p == g->left) {
                // Zig-Zag (left-right)
                rotateLeft(p);
                rotateRight(g);
            } else {
                // Zig-Zag (right-left)
                rotateRight(p);
                rotateLeft(g);
            }
        }
    }

public:
    SplayTree() : root(nullptr) {}

    void insert(int key) {
        SplayNode* node = new SplayNode(key);
        if (!root) { root = node; return; }
        SplayNode* curr = root;
        SplayNode* parent = nullptr;
        while (curr) {
            parent = curr;
            curr = (key < curr->key) ? curr->left : curr->right;
        }
        node->parent = parent;
        if (key < parent->key) parent->left = node;
        else parent->right = node;
        splay(node);
    }

    bool search(int key) {
        SplayNode* curr = root;
        SplayNode* last = nullptr;
        while (curr) {
            last = curr;
            if (key == curr->key) break;
            curr = (key < curr->key) ? curr->left : curr->right;
        }
        if (last) splay(last);
        return last && last->key == key;
    }

    SplayNode* getRoot() { return root; }
};

int main() {
    SplayTree tree;
    for (int x : {10, 5, 15, 3, 7, 12, 20}) tree.insert(x);
    std::cout << "Search 7: " << tree.search(7) << "\n";
    std::cout << "Root after search: " << tree.getRoot()->key << "\n";
    std::cout << "Search 100: " << tree.search(100) << "\n";
    return 0;
}
```

### Python Implementation

```python
class SplayNode:
    def __init__(self, key):
        self.key = key
        self.left = self.right = self.parent = None

class SplayTree:
    def __init__(self):
        self.root = None

    def _rotate_left(self, x):
        y = x.right
        if y:
            x.right = y.left
            if y.left: y.left.parent = x
            y.parent = x.parent
        if not x.parent: self.root = y
        elif x == x.parent.left: x.parent.left = y
        else: x.parent.right = y
        if y: y.left = x
        x.parent = y

    def _rotate_right(self, x):
        y = x.left
        if y:
            x.left = y.right
            if y.right: y.right.parent = x
            y.parent = x.parent
        if not x.parent: self.root = y
        elif x == x.parent.left: x.parent.left = y
        else: x.parent.right = y
        if y: y.right = x
        x.parent = y

    def _splay(self, x):
        while x.parent:
            p = x.parent
            g = p.parent
            if not g:
                if x == p.left: self._rotate_right(p)
                else: self._rotate_left(p)
            elif x == p.left and p == g.left:
                self._rotate_right(g)
                self._rotate_right(p)
            elif x == p.right and p == g.right:
                self._rotate_left(g)
                self._rotate_left(p)
            elif x == p.right and p == g.left:
                self._rotate_left(p)
                self._rotate_right(g)
            else:
                self._rotate_right(p)
                self._rotate_left(g)

    def insert(self, key):
        node = SplayNode(key)
        if not self.root:
            self.root = node
            return
        curr = self.root
        parent = None
        while curr:
            parent = curr
            curr = curr.left if key < curr.key else curr.right
        node.parent = parent
        if key < parent.key: parent.left = node
        else: parent.right = node
        self._splay(node)

    def search(self, key):
        curr = self.root
        last = None
        while curr:
            last = curr
            if key == curr.key: break
            curr = curr.left if key < curr.key else curr.right
        if last: self._splay(last)
        return last and last.key == key

# Example
tree = SplayTree()
for x in [10, 5, 15, 3, 7, 12, 20]:
    tree.insert(x)
print(f"Search 7: {tree.search(7)}")
print(f"Root: {tree.root.key}")
```

### Java Implementation

```java
public class SplayTree {
    static class Node {
        int key;
        Node left, right, parent;
        Node(int k) { key = k; }
    }

    private Node root;

    private void rotateLeft(Node x) {
        Node y = x.right;
        if (y != null) {
            x.right = y.left;
            if (y.left != null) y.left.parent = x;
            y.parent = x.parent;
        }
        if (x.parent == null) root = y;
        else if (x == x.parent.left) x.parent.left = y;
        else x.parent.right = y;
        if (y != null) y.left = x;
        x.parent = y;
    }

    private void rotateRight(Node x) {
        Node y = x.left;
        if (y != null) {
            x.left = y.right;
            if (y.right != null) y.right.parent = x;
            y.parent = x.parent;
        }
        if (x.parent == null) root = y;
        else if (x == x.parent.left) x.parent.left = y;
        else x.parent.right = y;
        if (y != null) y.right = x;
        x.parent = y;
    }

    private void splay(Node x) {
        while (x.parent != null) {
            Node p = x.parent, g = p.parent;
            if (g == null) {
                if (x == p.left) rotateRight(p);
                else rotateLeft(p);
            } else if (x == p.left && p == g.left) {
                rotateRight(g); rotateRight(p);
            } else if (x == p.right && p == g.right) {
                rotateLeft(g); rotateLeft(p);
            } else if (x == p.right && p == g.left) {
                rotateLeft(p); rotateRight(g);
            } else {
                rotateRight(p); rotateLeft(g);
            }
        }
    }

    public void insert(int key) {
        Node node = new Node(key);
        if (root == null) { root = node; return; }
        Node curr = root, parent = null;
        while (curr != null) {
            parent = curr;
            curr = key < curr.key ? curr.left : curr.right;
        }
        node.parent = parent;
        if (key < parent.key) parent.left = node;
        else parent.right = node;
        splay(node);
    }

    public boolean search(int key) {
        Node curr = root, last = null;
        while (curr != null) {
            last = curr;
            if (key == curr.key) break;
            curr = key < curr.key ? curr.left : curr.right;
        }
        if (last != null) splay(last);
        return last != null && last.key == key;
    }

    public static void main(String[] args) {
        SplayTree tree = new SplayTree();
        for (int x : new int[]{10, 5, 15, 3, 7, 12, 20}) tree.insert(x);
        System.out.println("Search 7: " + tree.search(7));
        System.out.println("Root: " + tree.root.key);
    }
}
```

---

## 98.2 Properties and Complexity

| Operation | Amortized | Worst Case |
|---|---|---|
| Search | O(log n) | O(n) |
| Insert | O(log n) | O(n) |
| Delete | O(log n) | O(n) |
| Access sequence (m ops) | O(m log n) total | — |

**Key insight**: While individual operations can be O(n), any sequence of m operations on an n-node splay tree takes O(m log n) total time.

### Why Amortized O(log n)?

The proof uses the **potential method**. Define the potential Φ as the sum of log₂ of subtree sizes:
```
Φ = Σ log₂(size(x))  for all nodes x
```

Each splay step (Zig, Zig-Zig, Zig-Zag) can be shown to amortize to O(log n) when accounting for the potential change. The key lemma (Access Lemma): splaying a node x in a tree of size n costs at most O(log n) amortized.

---

## 98.3 Splay Tree Deletion

To delete a node with key k:
1. Splay k to the root
2. Remove the root
3. Splay the maximum of the left subtree to the root of the left subtree
4. Attach the right subtree as the right child of the new root

```cpp
void remove(int key) {
    if (!root) return;
    search(key);  // Splays key to root
    if (root->key != key) return;  // Not found

    SplayNode* left = root->left;
    SplayNode* right = root->right;
    delete root;

    if (!left) {
        root = right;
        if (root) root->parent = nullptr;
    } else {
        root = left;
        root->parent = nullptr;
        // Splay max of left subtree
        SplayNode* maxLeft = root;
        while (maxLeft->right) maxLeft = maxLeft->right;
        splay(maxLeft);
        maxLeft->right = right;
        if (right) right->parent = maxLeft;
    }
}
```

---

## 98.4 Applications

### 1. Cache / LRU-like Behavior

Splay trees naturally implement a "move-to-front" heuristic. Recently accessed items are at the root, providing O(1) access for hot data.

### 2. Sequence Operations (Order-Statistic Tree)

With subtree size augmentation, splay trees support:
- Access k-th element: O(log n) amortized
- Split and merge: O(log n) amortized
- Range operations on sequences

### 3. Dynamic Optimality Conjecture

**Conjecture**: Splay trees are dynamically optimal — for any sequence of m accesses to n keys, splay trees are within a constant factor of the best possible BST for that sequence.

This remains unproven (one of the most famous open problems in data structures). The conjecture implies that splay trees automatically adapt to any access pattern.

---

## 98.5 Comparison with Other Balanced BSTs

| Feature | Splay | AVL | Red-Black | Treap |
|---|---|---|---|---|
| Balance guarantee | Amortized | Worst-case | Worst-case | Expected |
| Extra storage | None | Height | Color | Priority |
| Self-adjusting | Yes | No | No | No |
| Temporal locality | Yes | No | No | No |
| Implementation | Simple | Moderate | Complex | Simple |
| Worst-case op | O(n) | O(log n) | O(log n) | O(log n) exp. |

---

## Exercises

1. **Implement delete**: Complete the splay tree delete operation. Test with a sequence of insertions and deletions, verifying the tree remains a valid BST.

2. **Bottom-up splay**: The implementation above uses top-down splaying (splay during search). Implement bottom-up splaying (find the node first, then splay up). Compare performance.

3. **Subtree size augmentation**: Add a `size` field to each node and implement `select(k)` (find k-th smallest element) and `rank(x)` (find rank of element x).

4. **Split and Merge**: Implement `split(root, key)` that splits the tree into two trees (keys ≤ key and keys > key) and `merge(left, right)` that merges two trees.

5. **Access sequence**: Generate a sequence of accesses with temporal locality (e.g., zipf distribution). Compare splay tree performance against AVL tree. Measure total comparisons.

6. **Amortized analysis**: For a splay tree with n=7 nodes, trace the splay of the deepest node. Count the rotations and verify the amortized cost is O(log n).

---

## Interview Questions

1. **Q: Why are splay trees called "self-adjusting"?**
   A: Unlike AVL or Red-Black trees that maintain explicit balance information (heights, colors), splay trees adjust their structure purely through the splay operation on access. No metadata is stored per node.

2. **Q: What is the amortized complexity of splay tree operations? How is it proven?**
   A: O(log n) per operation, proven using the potential method. The potential function Φ = Σ log₂(size(x)) ensures that expensive operations (long splays) decrease the potential, "paying" for future cheap operations.

3. **Q: Why does the Zig-Zig case rotate the grandparent first?**
   A: Rotating the grandparent first is essential for the amortized bound. It ensures the depth of the splayed node decreases by 2 (not just 1), which is needed for the potential function to decrease enough. Rotating parent first gives O(n) amortized.

4. **Q: What is the dynamic optimality conjecture?**
   A: Splay trees are conjectured to be within a constant factor of the best possible BST for any access sequence. This would make them optimal among all BSTs. It's one of the most famous open problems in data structures.

5. **Q: When would you choose a splay tree over an AVL tree?**
   A: When the access pattern has temporal locality (recently accessed items are accessed again soon), or when simplicity of implementation matters more than worst-case guarantees. AVL is preferred when worst-case O(log n) is required.

6. **Q: Can splay trees degrade to O(n) per operation?**
   A: Yes, for individual operations. A single search in a degenerate splay tree can take O(n). But the amortized cost over any sequence is O(log n) per operation.

---

## Cross-References

- [Chapter 13: Trees](ch13-trees.md) — Tree fundamentals: traversals, recursion, and basic tree properties
- [Chapter 14: Binary Search Trees](ch14-bst.md) — The foundation; splay trees are a self-adjusting variant of BSTs
- [Chapter 99: Scapegoat and AA Trees](ch99-scapegoat-aa-trees.md) — Other simple balanced BST alternatives
- [Chapter 75: Persistent Data Structures](ch75-persistent-ds.md) — Splay trees can be made persistent via path copying
- [Chapter 157: Link-Cut Trees](ch157-link-cut-trees.md) — Sleator-Tarjan's dynamic trees use splay operations for path decomposition

---

## Summary

| Property | Value |
|---|---|
| Balance | Self-adjusting (no stored balance info) |
| Amortized | O(log n) per operation |
| Worst case | O(n) per operation |
| Key operation | Splay (Zig, Zig-Zig, Zig-Zag rotations) |
| Best for | Temporal locality, caching, sequences |
| Space | No extra per-node storage |
| Open problem | Dynamic optimality conjecture |
