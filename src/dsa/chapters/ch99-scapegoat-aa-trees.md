# Chapter 99: Scapegoat Trees and AA Trees

## Prerequisites
- BST basics ([Chapter 14](ch14-bst.md))
- AVL trees (Chapter 16)
- Tree rotations

## Interview Frequency: ★

Simpler balanced BST alternatives. Rarely asked directly but good to know as they demonstrate different approaches to balancing. Understanding them shows breadth of knowledge in interviews.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Scapegoat tree | ★ | Medium | Rebuild subtrees |
| AA tree | ★ | Medium | Red-black simplification |
| Comparison | ★ | Easy | Trade-offs between approaches |

---

## Definition

**Scapegoat trees** and **AA trees** are balanced BSTs that simplify the implementation of self-balancing:

- **Scapegoat tree**: Maintains balance by rebuilding unbalanced subtrees from scratch (no rotations during insertion)
- **AA tree**: A simplified red-black tree where red nodes can only be right children, reducing cases from dozens to just two operations (skew and split)

## Motivation

AVL and Red-Black trees are correct but complex. Implementing them correctly requires handling many cases. Scapegoat and AA trees offer:

| Feature | Scapegoat | AA Tree | AVL | Red-Black |
|---|---|---|---|---|
| Rotations on insert | None | 2 simple ops | ≤2 | ≤3 |
| Balance guarantee | Amortized O(log n) | Worst-case O(log n) | Worst-case O(log n) | Worst-case O(log n) |
| Extra storage | Subtree size | Level (int) | Height/balance | Color (1 bit) |
| Implementation complexity | Simple | Very simple | Moderate | Complex |
| Rebuilds | Yes (occasional) | No | No | No |

## Intuition

- **Scapegoat**: "This subtree is too fat — let me rebuild it from scratch." Like reorganizing a messy bookshelf entirely rather than moving books one by one.
- **AA tree**: "Red nodes must be right children — no exceptions." This single rule eliminates most of the complexity of red-black trees.

---

## 99.1 Scapegoat Trees

### Definition

A scapegoat tree is a BST that maintains balance by detecting when a node's subtree becomes too unbalanced, then rebuilding that subtree into a perfectly balanced tree. The unbalanced node is called the **scapegoat**.

### Balance Condition

A node is a scapegoat if:
```
size(child) > α × size(parent)
```
where α is a constant in (0.5, 1), typically 0.5 to 0.75.

After an insertion that creates a node at depth d, if d > log_{1/α}(n), walk up from the inserted node to find a scapegoat and rebuild its subtree.

### How Rebuilding Works

1. **Flatten** the subtree into a sorted array (inorder traversal)
2. **Build** a perfectly balanced tree from the sorted array (median as root)

This produces a tree of minimum height for that number of nodes.

### Step-by-Step Walkthrough

Insert sequence: 1, 2, 3, 4, 5 (α = 0.75)

```
After insert 1:  1 (depth 0, fine)
After insert 2:  1→2 (depth 1, fine)
After insert 3:  1→2→3 (depth 2)
  n=3, log_{1/0.75}(3) ≈ 3.8, depth 2 < 3.8, fine
After insert 4:  1→2→3→4 (depth 3)
  n=4, log_{1/0.75}(4) ≈ 4.8, depth 3 < 4.8, fine
After insert 5:  1→2→3→4→5 (depth 4)
  n=5, log_{1/0.75}(5) ≈ 5.6, depth 4 < 5.6, fine

Using α = 0.5 for a clearer example:
After insert 5:  n=5, log_2(5) ≈ 2.3, depth 4 > 2.3 → SCAPEGOAT!
  Walk up from 5: check 4 (size 2, parent size 5, 2 > 0.5*5=2.5? No)
  Check 3 (size 3, parent size 5, 3 > 0.5*5=2.5? YES → Scapegoat!)
  Rebuild subtree rooted at 3: [1,2,3,4,5] → balanced tree with root 3
```

### Dry Run — Rebuild Process

Subtree to rebuild (inorder): [1, 2, 3, 4, 5]

```
Build balanced:
  mid = 2, root = 3
  left:  build([1, 2]) → mid=0, root=1, right=2
  right: build([4, 5]) → mid=0, root=4, right=5

Result:
      3
     / \
    1   4
     \   \
      2   5
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

struct Node {
    int key, size;
    Node *left, *right;
    Node(int k) : key(k), size(1), left(nullptr), right(nullptr) {}
};

class ScapegoatTree {
    Node* root;
    double alpha;

    int getSize(Node* n) { return n ? n->size : 0; }

    void updateSize(Node* n) {
        if (n) n->size = 1 + getSize(n->left) + getSize(n->right);
    }

    // Flatten tree to sorted array of node pointers
    void flatten(Node* n, std::vector<Node*>& nodes) {
        if (!n) return;
        flatten(n->left, nodes);
        nodes.push_back(n);
        flatten(n->right, nodes);
    }

    // Build balanced tree from sorted array of nodes
    Node* buildBalanced(std::vector<Node*>& nodes, int lo, int hi) {
        if (lo > hi) return nullptr;
        int mid = (lo + hi) / 2;
        Node* n = nodes[mid];
        n->left = buildBalanced(nodes, lo, mid - 1);
        n->right = buildBalanced(nodes, mid + 1, hi);
        updateSize(n);
        return n;
    }

    Node* rebuild(Node* subtree) {
        std::vector<Node*> nodes;
        flatten(subtree, nodes);
        return buildBalanced(nodes, 0, nodes.size() - 1);
    }

    // Returns depth of inserted node
    Node* insert(Node* node, int key, int depth, Node*& scapegoat, int& scapegoatDepth) {
        if (!node) {
            Node* n = new Node(key);
            if (depth > scapegoatDepth) {
                scapegoatDepth = depth;
            }
            return n;
        }

        if (key < node->key)
            node->left = insert(node->left, key, depth + 1, scapegoat, scapegoatDepth);
        else if (key > node->key)
            node->right = insert(node->right, key, depth + 1, scapegoat, scapegoatDepth);
        else
            return node;  // Duplicate

        updateSize(node);

        // Check if this node is a scapegoat
        int maxSize = std::max(getSize(node->left), getSize(node->right));
        if (maxSize > alpha * node->size) {
            scapegoat = node;
        }

        return node;
    }

public:
    ScapegoatTree(double a = 0.75) : root(nullptr), alpha(a) {}

    void insert(int key) {
        Node* scapegoat = nullptr;
        int maxDepth = 0;
        root = insert(root, key, 0, scapegoat, maxDepth);

        // Check if depth exceeds threshold
        if (maxDepth > log(getSize(root)) / log(1.0 / alpha)) {
            if (scapegoat == nullptr) scapegoat = root;
            // Rebuild the scapegoat
            if (scapegoat == root) {
                root = rebuild(root);
            } else {
                // Find parent of scapegoat and rebuild
                // For simplicity, rebuild root if scapegoat is root
                // In practice, you'd track the parent
                root = rebuild(root);
            }
        }
    }

    bool search(int key) {
        Node* curr = root;
        while (curr) {
            if (key == curr->key) return true;
            curr = (key < curr->key) ? curr->left : curr->right;
        }
        return false;
    }

    int size() { return getSize(root); }

    void inorder(Node* n, std::vector<int>& result) {
        if (!n) return;
        inorder(n->left, result);
        result.push_back(n->key);
        inorder(n->right, result);
    }

    std::vector<int> toSorted() {
        std::vector<int> result;
        inorder(root, result);
        return result;
    }
};

int main() {
    ScapegoatTree tree(0.75);
    for (int x : {10, 5, 15, 3, 7, 12, 20, 1, 4, 6, 8}) tree.insert(x);

    std::cout << "Size: " << tree.size() << "\n";
    for (int x : {7, 15, 100})
        std::cout << "Search " << x << ": " << tree.search(x) << "\n";

    auto sorted = tree.toSorted();
    std::cout << "Sorted: ";
    for (int x : sorted) std::cout << x << " ";
    std::cout << "\n";

    return 0;
}
```

### Python Implementation

```python
import math

class ScapegoatTree:
    def __init__(self, alpha=0.75):
        self.alpha = alpha
        self.root = None
        self.size = 0

    class Node:
        def __init__(self, key):
            self.key = key
            self.left = self.right = None

    def _size(self, node):
        if not node:
            return 0
        return 1 + self._size(node.left) + self._size(node.right)

    def _flatten(self, node, nodes):
        if not node:
            return
        self._flatten(node.left, nodes)
        nodes.append(node)
        self._flatten(node.right, nodes)

    def _build_balanced(self, nodes, lo, hi):
        if lo > hi:
            return None
        mid = (lo + hi) // 2
        node = nodes[mid]
        node.left = self._build_balanced(nodes, lo, mid - 1)
        node.right = self._build_balanced(nodes, mid + 1, hi)
        return node

    def _rebuild(self, node):
        nodes = []
        self._flatten(node, nodes)
        return self._build_balanced(nodes, 0, len(nodes) - 1)

    def insert(self, key):
        # Standard BST insert
        if not self.root:
            self.root = self.Node(key)
            self.size = 1
            return

        path = []
        curr = self.root
        while curr:
            path.append(curr)
            if key < curr.key:
                curr = curr.left
            elif key > curr.key:
                curr = curr.right
            else:
                return  # Duplicate

        new_node = self.Node(key)
        parent = path[-1]
        if key < parent.key:
            parent.left = new_node
        else:
            parent.right = new_node
        self.size += 1

        # Check for scapegoat
        max_depth = len(path)
        threshold = math.log(self.size) / math.log(1.0 / self.alpha)
        if max_depth > threshold:
            # Find scapegoat (first node where child size > alpha * node size)
            for i in range(len(path) - 1, -1, -1):
                node = path[i]
                left_size = self._size(node.left)
                right_size = self._size(node.right)
                node_size = left_size + right_size + 1
                if max(left_size, right_size) > self.alpha * node_size:
                    # Rebuild this node
                    if i == 0:
                        self.root = self._rebuild(node)
                    else:
                        parent = path[i - 1]
                        if parent.left == node:
                            parent.left = self._rebuild(node)
                        else:
                            parent.right = self._rebuild(node)
                    break

    def search(self, key):
        curr = self.root
        while curr:
            if key == curr.key:
                return True
            curr = curr.left if key < curr.key else curr.right
        return False

# Example
tree = ScapegoatTree(0.75)
for x in [10, 5, 15, 3, 7, 12, 20, 1, 4, 6, 8]:
    tree.insert(x)
for x in [7, 15, 100]:
    print(f"Search {x}: {tree.search(x)}")
```

### Java Implementation

```java
import java.util.*;

public class ScapegoatTree {
    static class Node {
        int key, size;
        Node left, right;
        Node(int k) { key = k; size = 1; }
    }

    private Node root;
    private final double alpha;

    public ScapegoatTree(double alpha) { this.alpha = alpha; }

    private int size(Node n) { return n == null ? 0 : n.size; }

    private void updateSize(Node n) {
        if (n != null) n.size = 1 + size(n.left) + size(n.right);
    }

    private void flatten(Node n, List<Node> nodes) {
        if (n == null) return;
        flatten(n.left, nodes);
        nodes.add(n);
        flatten(n.right, nodes);
    }

    private Node buildBalanced(List<Node> nodes, int lo, int hi) {
        if (lo > hi) return null;
        int mid = (lo + hi) / 2;
        Node n = nodes.get(mid);
        n.left = buildBalanced(nodes, lo, mid - 1);
        n.right = buildBalanced(nodes, mid + 1, hi);
        updateSize(n);
        return n;
    }

    private Node rebuild(Node subtree) {
        List<Node> nodes = new ArrayList<>();
        flatten(subtree, nodes);
        return buildBalanced(nodes, 0, nodes.size() - 1);
    }

    public void insert(int key) {
        // Standard BST insert with path tracking
        List<Node> path = new ArrayList<>();
        if (root == null) { root = new Node(key); return; }

        Node curr = root;
        while (curr != null) {
            path.add(curr);
            if (key < curr.key) curr = curr.left;
            else if (key > curr.key) curr = curr.right;
            else return; // Duplicate
        }

        Node newNode = new Node(key);
        Node parent = path.get(path.size() - 1);
        if (key < parent.key) parent.left = newNode;
        else parent.right = newNode;

        // Update sizes along path
        for (int i = path.size() - 1; i >= 0; i--)
            updateSize(path.get(i));

        // Check for scapegoat
        int maxDepth = path.size();
        double threshold = Math.log(size(root)) / Math.log(1.0 / alpha);
        if (maxDepth > threshold) {
            for (int i = path.size() - 1; i >= 0; i--) {
                Node node = path.get(i);
                int maxSize = Math.max(size(node.left), size(node.right));
                if (maxSize > alpha * size(node)) {
                    if (i == 0) root = rebuild(root);
                    else {
                        Node p = path.get(i - 1);
                        if (p.left == node) p.left = rebuild(node);
                        else p.right = rebuild(node);
                    }
                    break;
                }
            }
        }
    }

    public boolean search(int key) {
        Node curr = root;
        while (curr != null) {
            if (key == curr.key) return true;
            curr = key < curr.key ? curr.left : curr.right;
        }
        return false;
    }

    public static void main(String[] args) {
        ScapegoatTree tree = new ScapegoatTree(0.75);
        for (int x : new int[]{10, 5, 15, 3, 7, 12, 20, 1, 4, 6, 8}) tree.insert(x);
        for (int x : new int[]{7, 15, 100})
            System.out.println("Search " + x + ": " + tree.search(x));
    }
}
```

---

## 99.2 AA Trees

### Definition

An **AA tree** is a red-black tree with one additional constraint: **red nodes can only be right children**. This eliminates the case of red nodes as left children, which dramatically simplifies the balancing logic.

### The Two Core Operations

| Operation | When | Effect |
|---|---|---|
| **Skew** | Left child has same level | Right rotation (fixes left-leaning red) |
| **Split** | Right-right grandchild has same level | Left rotation + level increment (fixes consecutive reds) |

### Level System

Instead of colors, AA trees use integer levels:
- **Level 1**: Leaf nodes (equivalent to black)
- **Level > 1**: Internal nodes
- Left children must have strictly smaller level (no left-leaning reds)
- Right grandchildren must have strictly smaller level (no consecutive reds)

### Step-by-Step Walkthrough

Insert sequence: 10, 5, 15, 3, 7, 12, 20

```
After insert 10:  (10, level 1)
After insert 5:   (10, L1) → left=(5, L1)
  skew: 5.level == 10.level → right rotate → (5, L1), right=(10, L1)
After insert 15:  (5, L1), right=(10, L1), right.right=(15, L1)
After insert 3:   (5, L1), left=(3, L1), right=(10, L1)
After insert 7:   (5, L1), left=(3, L1), left has no issues
                    right=(10, L1), right.left=(7, L1)
After insert 12:  Fine, no violations
After insert 20:  (10, L1) has right.right with same level → split!
  Split: left rotate at 10, level++ → (15, L2), left=(10, L1), right=(20, L1)
```

### Dry Run — Insert 8 into existing tree

```
Before:    5
          / \
         3   10
            /  \
           7   15
            \
             8  ← new node

Step 1: BST insert 8 as right child of 7
Step 2: Walk back up, applying skew and split at each node

At 7: skew (no left child same level), split (no right-right same level)
At 10: skew (no issue), split (15.level == 15.level? depends on structure)
At 5: skew (no issue), split (check right-right grandchild)

Result depends on exact level assignments — AA tree handles it automatically.
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>

struct AANode {
    int key, level;
    AANode *left, *right;
    AANode(int k) : key(k), level(1), left(nullptr), right(nullptr) {}
};

class AATree {
    AANode* root;

    // Fix left-leaning red: right rotate if left child has same level
    AANode* skew(AANode* n) {
        if (n && n->left && n->left->level == n->level) {
            AANode* l = n->left;
            n->left = l->right;
            l->right = n;
            return l;
        }
        return n;
    }

    // Fix consecutive reds on right: left rotate + level++
    AANode* split(AANode* n) {
        if (n && n->right && n->right->right &&
            n->right->right->level == n->level) {
            AANode* r = n->right;
            n->right = r->left;
            r->left = n;
            r->level++;
            return r;
        }
        return n;
    }

    AANode* insert(AANode* n, int key) {
        if (!n) return new AANode(key);
        if (key < n->key) n->left = insert(n->left, key);
        else if (key > n->key) n->right = insert(n->right, key);
        else return n;  // Duplicate
        n = skew(n);
        n = split(n);
        return n;
    }

    // Find the predecessor (rightmost of left subtree)
    AANode* predecessor(AANode* n) {
        while (n->right) n = n->right;
        return n;
    }

    AANode* remove(AANode* n, int key) {
        if (!n) return nullptr;

        if (key < n->key) {
            n->left = remove(n->left, key);
        } else if (key > n->key) {
            n->right = remove(n->right, key);
        } else {
            // Found the node to delete
            if (!n->left && !n->right) {
                delete n;
                return nullptr;
            }
            if (!n->left) {
                AANode* r = n->right;
                delete n;
                return r;
            }
            if (!n->right) {
                AANode* l = n->left;
                delete n;
                return l;
            }
            // Two children: replace with predecessor
            AANode* pred = predecessor(n->left);
            n->key = pred->key;
            n->left = remove(n->left, pred->key);
        }

        // Rebalance
        // Decrease level if needed
        int expectedLeft = n->left ? n->left->level : 0;
        int expectedRight = n->right ? n->right->level : 0;
        int shouldBe = 1 + std::min(expectedLeft, expectedRight);
        if (n->level > shouldBe) {
            n->level = shouldBe;
            if (n->right && n->right->level > n->level)
                n->right->level = n->level;
        }

        n = skew(n);
        if (n->right) n->right = skew(n->right);
        if (n->right && n->right->right)
            n->right->right = skew(n->right->right);
        n = split(n);
        if (n->right) n->right = split(n->right);

        return n;
    }

public:
    AATree() : root(nullptr) {}
    void insert(int key) { root = insert(root, key); }
    void remove(int key) { root = remove(root, key); }

    bool search(int key) {
        AANode* curr = root;
        while (curr) {
            if (key == curr->key) return true;
            curr = (key < curr->key) ? curr->left : curr->right;
        }
        return false;
    }

    void inorder(AANode* n, std::vector<int>& result) {
        if (!n) return;
        inorder(n->left, result);
        result.push_back(n->key);
        inorder(n->right, result);
    }

    std::vector<int> toSorted() {
        std::vector<int> result;
        inorder(root, result);
        return result;
    }
};

int main() {
    AATree tree;
    for (int x : {10, 5, 15, 3, 7, 12, 20}) tree.insert(x);

    for (int x : {7, 15, 100})
        std::cout << "Search " << x << ": " << tree.search(x) << "\n";

    tree.remove(10);
    std::cout << "After remove 10, search 10: " << tree.search(10) << "\n";

    auto sorted = tree.toSorted();
    std::cout << "Sorted: ";
    for (int x : sorted) std::cout << x << " ";
    std::cout << "\n";

    return 0;
}
```

### Python Implementation

```python
class AATree:
    class Node:
        def __init__(self, key):
            self.key = key
            self.level = 1
            self.left = self.right = None

    def __init__(self):
        self.root = None

    def _skew(self, node):
        if node and node.left and node.left.level == node.level:
            l = node.left
            node.left = l.right
            l.right = node
            return l
        return node

    def _split(self, node):
        if (node and node.right and node.right.right and
                node.right.right.level == node.level):
            r = node.right
            node.right = r.left
            r.left = node
            r.level += 1
            return r
        return node

    def _insert(self, node, key):
        if not node:
            return self.Node(key)
        if key < node.key:
            node.left = self._insert(node.left, key)
        elif key > node.key:
            node.right = self._insert(node.right, key)
        else:
            return node  # Duplicate
        node = self._skew(node)
        node = self._split(node)
        return node

    def insert(self, key):
        self.root = self._insert(self.root, key)

    def search(self, key):
        curr = self.root
        while curr:
            if key == curr.key:
                return True
            curr = curr.left if key < curr.key else curr.right
        return False

    def _inorder(self, node, result):
        if not node:
            return
        self._inorder(node.left, result)
        result.append(node.key)
        self._inorder(node.right, result)

    def to_sorted(self):
        result = []
        self._inorder(self.root, result)
        return result

# Example
tree = AATree()
for x in [10, 5, 15, 3, 7, 12, 20]:
    tree.insert(x)
for x in [7, 15, 100]:
    print(f"Search {x}: {tree.search(x)}")
print(f"Sorted: {tree.to_sorted()}")
```

### Java Implementation

```java
import java.util.*;

public class AATree {
    static class Node {
        int key, level;
        Node left, right;
        Node(int k) { key = k; level = 1; }
    }

    private Node root;

    private Node skew(Node n) {
        if (n != null && n.left != null && n.left.level == n.level) {
            Node l = n.left;
            n.left = l.right;
            l.right = n;
            return l;
        }
        return n;
    }

    private Node split(Node n) {
        if (n != null && n.right != null && n.right.right != null &&
            n.right.right.level == n.level) {
            Node r = n.right;
            n.right = r.left;
            r.left = n;
            r.level++;
            return r;
        }
        return n;
    }

    private Node insert(Node n, int key) {
        if (n == null) return new Node(key);
        if (key < n.key) n.left = insert(n.left, key);
        else if (key > n.key) n.right = insert(n.right, key);
        else return n;
        n = skew(n);
        n = split(n);
        return n;
    }

    public void insert(int key) { root = insert(root, key); }

    public boolean search(int key) {
        Node curr = root;
        while (curr != null) {
            if (key == curr.key) return true;
            curr = key < curr.key ? curr.left : curr.right;
        }
        return false;
    }

    private void inorder(Node n, List<Integer> result) {
        if (n == null) return;
        inorder(n.left, result);
        result.add(n.key);
        inorder(n.right, result);
    }

    public List<Integer> toSorted() {
        List<Integer> result = new ArrayList<>();
        inorder(root, result);
        return result;
    }

    public static void main(String[] args) {
        AATree tree = new AATree();
        for (int x : new int[]{10, 5, 15, 3, 7, 12, 20}) tree.insert(x);
        for (int x : new int[]{7, 15, 100})
            System.out.println("Search " + x + ": " + tree.search(x));
        System.out.println("Sorted: " + tree.toSorted());
    }
}
```

---

## 99.3 Complexity Analysis

### Scapegoat Trees

| Operation | Amortized | Worst Case |
|---|---|---|
| Search | O(log n) | O(log n) — always balanced |
| Insert | O(log n) | O(n) — rebuild cost |
| Delete | O(log n) | O(n) — rebuild cost |
| Space | O(n) | O(n) |

The amortized O(log n) for insert comes from the fact that each node participates in at most O(log n) rebuilds over its lifetime.

### AA Trees

| Operation | Worst Case | Notes |
|---|---|---|
| Search | O(log n) | Same as red-black |
| Insert | O(log n) | At most 2 rotations |
| Delete | O(log n) | At most 3 rotations |
| Space | O(n) | 1 extra int per node (level) |

AA trees have the same asymptotic complexity as red-black trees but with simpler implementation.

---

## 99.4 When to Use Which

| Scenario | Best Choice |
|---|---|
| Simple balanced BST for interviews | AA tree |
| Frequent insertions, rare queries | Scapegoat tree |
| Need worst-case guarantees | AVL or Red-Black |
| Memory-constrained | AA tree (level is small) |
| Teaching/learning balancing | Scapegoat tree (conceptually simple) |
| Standard library | Red-black (C++ `std::map`, Java `TreeMap`) |

---

## Exercises

1. **Implement scapegoat delete**: The delete operation for scapegoat trees is trickier — you need to track if the tree becomes too sparse (n < α × maxSizeSinceRebuild). Implement this.

2. **AA tree delete**: Complete the AA tree delete operation shown above. Test with a sequence of insertions and deletions, verifying the tree remains a valid AA tree.

3. **Compare balancing**: Insert the sequence 1, 2, 3, ..., 1000 into an AVL tree, a scapegoat tree, and an AA tree. Count the total number of rotations/rebuilds for each.

4. **Alpha tuning**: Experiment with different α values (0.5, 0.6, 0.7, 0.75, 0.8) for scapegoat trees. Measure average insert time for random data.

5. **Verification**: Write a function that verifies a tree is a valid AA tree: check that (1) it's a BST, (2) left children have strictly smaller level, (3) right grandchildren have strictly smaller level, (4) leaves are level 1.

6. **Red-black comparison**: Implement a red-black tree and an AA tree. Insert the same random sequence into both. Compare lines of code and correctness.

---

## Interview Questions

1. **Q: What is a scapegoat tree and how does it maintain balance?**
   A: A scapegoat tree detects when an insertion creates a node that's too deep (depth > log_{1/α}(n)). It then walks up to find a "scapegoat" node whose subtree is too unbalanced and rebuilds that subtree from scratch into a perfectly balanced tree.

2. **Q: How does an AA tree simplify red-black trees?**
   A: By adding one constraint: red nodes can only be right children. This eliminates all cases where red nodes are left children, reducing the number of balancing cases from ~6 to just 2 (skew and split).

3. **Q: What are skew and split operations in AA trees?**
   A: Skew is a right rotation that fixes a left child with the same level (equivalent to a left-leaning red). Split is a left rotation + level increment that fixes a right-right grandchild with the same level (equivalent to two consecutive reds).

4. **Q: When would you choose a scapegoat tree over an AVL tree?**
   A: When implementation simplicity matters more than worst-case guarantees. Scapegoat trees have simpler insertion logic (no rotation cases) at the cost of occasional O(n) rebuilds (amortized to O(log n)).

5. **Q: What is the amortized complexity of scapegoat tree insertion? How is it proven?**
   A: O(log n) amortized. Each node participates in at most O(log n) rebuilds over its lifetime because each rebuild doubles the subtree size relative to the node's position. The total rebuild cost across all insertions is O(n log n).

6. **Q: Compare AA trees and splay trees.**
   A: AA trees have worst-case O(log n) per operation with simple skew/split. Splay trees have amortized O(log n) with no balance info but O(n) worst case. AA trees are better for predictable performance; splay trees are better for temporal locality.

---

## Cross-References

- [Chapter 13: Trees](ch13-trees.md) — Tree fundamentals: traversals, recursion, and basic tree properties
- [Chapter 14: Binary Search Trees](ch14-bst.md) — The foundation; Scapegoat and AA trees are balanced BST variants
- Chapter 16: AVL Trees — Strictly balanced BSTs; compare with AA tree simplicity
- [Chapter 98: Splay Trees](ch98-splay-trees.md) — Another self-adjusting BST; compare amortized vs worst-case guarantees
- [Chapter 74: Skip Lists](ch74-skip-lists.md) — A probabilistic alternative to balanced BSTs with simpler implementation
- [Chapter 100: Van Emde Boas Trees](ch100-van-emde-boas.md) — For integer keys in a bounded range, vEB trees achieve O(log log n)

---

## Summary

| Tree | Key Idea | Rotations | Rebuilds | Balance Guarantee |
|---|---|---|---|---|
| Scapegoat | Rebuild unbalanced subtrees | None during insert | On insertion (amortized) | Amortized O(log n) |
| AA Tree | Red only as right child | Simple skew/split | None | Worst-case O(log n) |
| AVL | Height-balanced | ≤ 2 per insert | None | Worst-case O(log n) |
| Red-Black | Color constraints | ≤ 3 per insert | None | Worst-case O(log n) |
| Splay | Splay to root | Variable | None | Amortized O(log n) |
