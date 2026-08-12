# Chapter 14: Binary Search Trees

A **Binary Search Tree (BST)** is a binary tree that maintains a powerful ordering property: for every node, all values in its left subtree are smaller, and all values in its right subtree are larger. This property enables efficient search, insertion, and deletion in O(log n) time on average. BSTs are the foundation for many data structures (sets, maps, databases) and are heavily tested in interviews.

---

## 14.1 BST Property

### The Invariant

For every node `N` in a BST:

```
All values in N's left subtree  <  N->val  <  All values in N's right subtree
```

This is a **recursive** property — it must hold for every node in the tree, not just the root.

### Why It Enables Efficient Search

Because of the ordering property, at each node we can eliminate half the tree:
- If `target < node->val`, search only the left subtree.
- If `target > node->val`, search only the right subtree.
- If `target == node->val`, found!

This is exactly binary search, but on a tree structure.

### Example BST

```
        8
       / \
      3   10
     / \    \
    1   6    14
       / \   /
      4   7 13
```

**Verification:**
- Node 8: left subtree {1,3,4,6,7} < 8 < right subtree {10,13,14} ✓
- Node 3: left subtree {1} < 3 < right subtree {4,6,7} ✓
- Node 6: left subtree {4} < 6 < right subtree {7} ✓
- Node 10: no left child < 10 < right subtree {13,14} ✓
- Node 14: left subtree {13} < 14 < no right child ✓

### Inorder Traversal Produces Sorted Order

A key property: **inorder traversal of a BST always produces a sorted sequence**.

```
Inorder of the above BST: 1, 3, 4, 6, 7, 8, 10, 13, 14
```

This property is used to validate BSTs and extract sorted data.

---

## 14.2 Operations

### Search

```cpp
#include <iostream>
#include <stdexcept>

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

// Search for a value in BST
// Time: O(h), Space: O(h) recursive / O(1) iterative
// h = O(log n) for balanced, O(n) for skewed
TreeNode* search(TreeNode* root, int target) {
    if (!root || root->val == target) return root;
    
    if (target < root->val) {
        return search(root->left, target);
    } else {
        return search(root->right, target);
    }
}

// Iterative search
TreeNode* searchIterative(TreeNode* root, int target) {
    TreeNode* curr = root;
    while (curr) {
        if (target == curr->val) return curr;
        else if (target < curr->val) curr = curr->left;
        else curr = curr->right;
    }
    return nullptr;
}
```

### Insert

```cpp
#include <iostream>

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

// Insert a value into BST
// Time: O(h), Space: O(h) recursive
TreeNode* insert(TreeNode* root, int val) {
    if (!root) return new TreeNode(val);
    
    if (val < root->val) {
        root->left = insert(root->left, val);
    } else if (val > root->val) {
        root->right = insert(root->right, val);
    }
    // If val == root->val, do nothing (no duplicates)
    
    return root;
}

// Iterative insert
TreeNode* insertIterative(TreeNode* root, int val) {
    TreeNode* node = new TreeNode(val);
    if (!root) return node;
    
    TreeNode* curr = root;
    TreeNode* parent = nullptr;
    
    while (curr) {
        parent = curr;
        if (val < curr->val) curr = curr->left;
        else if (val > curr->val) curr = curr->right;
        else return root; // Duplicate, return unchanged
    }
    
    if (val < parent->val) parent->left = node;
    else parent->right = node;
    
    return root;
}
```

**Dry Run: Insert 5 into the BST:**

```
Start at root 8: 5 < 8, go left
At node 3: 5 > 3, go right
At node 6: 5 < 6, go left
At node 4: 5 > 4, go right
NULL → insert 5 here

        8
       / \
      3   10
     / \    \
    1   6    14
       / \   /
      4   7 13
       \
        5
```

### Delete

Deletion in a BST has three cases:

| Case | Description | Action |
|------|-------------|--------|
| **Leaf node** | No children | Simply remove |
| **One child** | Only left or right child | Replace node with its child |
| **Two children** | Both left and right children | Replace with inorder successor (smallest in right subtree) |

```cpp
#include <iostream>

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

// Find the minimum node in a subtree (leftmost node)
TreeNode* findMin(TreeNode* root) {
    while (root->left) {
        root = root->left;
    }
    return root;
}

// Delete a value from BST
// Time: O(h), Space: O(h)
TreeNode* deleteNode(TreeNode* root, int key) {
    if (!root) return nullptr;
    
    if (key < root->val) {
        root->left = deleteNode(root->left, key);
    } else if (key > root->val) {
        root->right = deleteNode(root->right, key);
    } else {
        // Found the node to delete
        
        // Case 1 & 2: Zero or one child
        if (!root->left) {
            TreeNode* temp = root->right;
            delete root;
            return temp;
        }
        if (!root->right) {
            TreeNode* temp = root->left;
            delete root;
            return temp;
        }
        
        // Case 3: Two children
        // Find inorder successor (smallest in right subtree)
        TreeNode* successor = findMin(root->right);
        root->val = successor->val;
        // Delete the successor from right subtree
        root->right = deleteNode(root->right, successor->val);
    }
    return root;
}
```

**Dry Run: Delete 3 from the BST:**

```
Original:
        8
       / \
      3   10
     / \    \
    1   6    14
       / \   /
      4   7 13

Find 3: has two children.
Inorder successor of 3 = 4 (minimum in right subtree).
Replace 3 with 4.
Delete 4 from right subtree (4 has one child: 7 → actually no children here).

        8
       / \
      4   10
     / \    \
    1   6    14
       /    /
      7   13
```

### Complete BST Implementation

```cpp
#include <iostream>
#include <vector>
#include <stdexcept>

class BST {
    struct TreeNode {
        int val;
        TreeNode* left;
        TreeNode* right;
        TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
    };

    TreeNode* root;

    // Helper: recursive insert
    TreeNode* insert(TreeNode* node, int val) {
        if (!node) return new TreeNode(val);
        if (val < node->val) node->left = insert(node->left, val);
        else if (val > node->val) node->right = insert(node->right, val);
        return node;
    }

    // Helper: find minimum
    TreeNode* findMin(TreeNode* node) {
        while (node->left) node = node->left;
        return node;
    }

    // Helper: recursive delete
    TreeNode* deleteNode(TreeNode* node, int key) {
        if (!node) return nullptr;
        if (key < node->val) node->left = deleteNode(node->left, key);
        else if (key > node->val) node->right = deleteNode(node->right, key);
        else {
            if (!node->left) { TreeNode* t = node->right; delete node; return t; }
            if (!node->right) { TreeNode* t = node->left; delete node; return t; }
            TreeNode* succ = findMin(node->right);
            node->val = succ->val;
            node->right = deleteNode(node->right, succ->val);
        }
        return node;
    }

    // Helper: recursive search
    TreeNode* search(TreeNode* node, int val) {
        if (!node || node->val == val) return node;
        if (val < node->val) return search(node->left, val);
        return search(node->right, val);
    }

    // Helper: inorder traversal
    void inorder(TreeNode* node, std::vector<int>& result) {
        if (!node) return;
        inorder(node->left, result);
        result.push_back(node->val);
        inorder(node->right, result);
    }

    // Helper: free tree
    void freeTree(TreeNode* node) {
        if (!node) return;
        freeTree(node->left);
        freeTree(node->right);
        delete node;
    }

public:
    BST() : root(nullptr) {}
    ~BST() { freeTree(root); }

    void insert(int val) { root = insert(root, val); }
    void erase(int val) { root = deleteNode(root, val); }
    bool contains(int val) { return search(root, val) != nullptr; }

    std::vector<int> inorderTraversal() {
        std::vector<int> result;
        inorder(root, result);
        return result;
    }

    int findMin() {
        if (!root) throw std::runtime_error("Tree is empty");
        return findMin(root)->val;
    }
};

int main() {
    BST bst;
    
    // Build BST
    std::vector<int> values = {8, 3, 10, 1, 6, 14, 4, 7, 13};
    for (int v : values) bst.insert(v);
    
    std::cout << "Inorder: ";
    for (int v : bst.inorderTraversal()) std::cout << v << " ";
    std::cout << "\n"; // 1 3 4 6 7 8 10 13 14
    
    std::cout << "Contains 6: " << (bst.contains(6) ? "yes" : "no") << "\n";
    std::cout << "Contains 99: " << (bst.contains(99) ? "yes" : "no") << "\n";
    std::cout << "Min: " << bst.findMin() << "\n";
    
    bst.erase(3);
    std::cout << "After erase 3: ";
    for (int v : bst.inorderTraversal()) std::cout << v << " ";
    std::cout << "\n"; // 1 4 6 7 8 10 13 14
    
    return 0;
}
```

### Complexity Summary

| Operation | Average (Balanced) | Worst (Skewed) |
|-----------|-------------------|----------------|
| Search | O(log n) | O(n) |
| Insert | O(log n) | O(n) |
| Delete | O(log n) | O(n) |
| Find Min/Max | O(log n) | O(n) |
| Inorder traversal | O(n) | O(n) |

---

## 14.3 BST Validation

### Problem: Is a Binary Tree a Valid BST?

A common mistake is only checking that `node->left->val < node->val < node->right->val`. This is **not sufficient** — the BST property must hold for ALL descendants, not just immediate children.

**Incorrect approach:**
```
     5
    / \
   1   7
      / \
     4   8

This passes the local check (4 < 7 and 8 > 7),
but 4 is in the right subtree of 5, and 4 < 5. INVALID BST!
```

### Approach 1: Min/Max Range

Pass down the valid range for each node:

```cpp
#include <iostream>
#include <climits>

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

// Validate BST using range checking
// Time: O(n), Space: O(h)
bool isValidBST(TreeNode* root, long long minVal, long long maxVal) {
    if (!root) return true;
    
    if (root->val <= minVal || root->val >= maxVal) return false;
    
    return isValidBST(root->left, minVal, root->val) &&
           isValidBST(root->right, root->val, maxVal);
}

bool isValidBST(TreeNode* root) {
    return isValidBST(root, LLONG_MIN, LLONG_MAX);
}
```

### Approach 2: Inorder Traversal

Since inorder traversal of a BST produces a sorted sequence, we can check that each element is greater than the previous:

```cpp
#include <iostream>
#include <climits>

// Validate BST using inorder traversal
// Time: O(n), Space: O(h)
bool isValidBSTInorder(TreeNode* root, long long& prev) {
    if (!root) return true;
    
    // Check left subtree
    if (!isValidBSTInorder(root->left, prev)) return false;
    
    // Check current node
    if (root->val <= prev) return false;
    prev = root->val;
    
    // Check right subtree
    return isValidBSTInorder(root->right, prev);
}

bool isValidBSTInorder(TreeNode* root) {
    long long prev = LLONG_MIN;
    return isValidBSTInorder(root, prev);
}
```

### Approach 3: Iterative Inorder

```cpp
#include <iostream>
#include <stack>
#include <climits>

bool isValidBSTIterative(TreeNode* root) {
    std::stack<TreeNode*> stk;
    TreeNode* curr = root;
    long long prev = LLONG_MIN;
    
    while (curr || !stk.empty()) {
        while (curr) {
            stk.push(curr);
            curr = curr->left;
        }
        curr = stk.top();
        stk.pop();
        
        if (curr->val <= prev) return false;
        prev = curr->val;
        
        curr = curr->right;
    }
    return true;
}
```

---

## 14.4 Balanced BSTs

### Why Balance Matters

A BST can degrade to a linked list if elements are inserted in sorted order:

```
Insert 1, 2, 3, 4, 5 into a BST:

1           1             1               1                 1
 \           \             \               \                 \
  2           2             2               2                 2
                          /               / \               / \
                         3               3   3             3   3
                                                        /   \
                                                       4     4
                                                              \
                                                               5

Height = n → all operations become O(n)!
```

A balanced BST maintains height O(log n), guaranteeing O(log n) operations.

### What Makes a BST "Balanced"?

| Definition | Requirement | Examples |
|-----------|-------------|---------|
| **Height-balanced** | Height difference ≤ 1 for every node | AVL tree |
| **Weakly balanced** | Height = O(log n) | Red-Black tree |
| **Weight-balanced** | Subtree sizes differ by at most a constant factor | Weight-balanced BST |

---

## 14.5 AVL Trees

An **AVL tree** (named after Adelson-Velsky and Landis) is a self-balancing BST where the **height difference** between left and right subtrees is at most 1 for every node.

### Balance Factor

```
balanceFactor(node) = height(node->left) - height(node->right)
```

A node is balanced if `|balanceFactor| <= 1`.

### Rotations

When an insertion or deletion causes imbalance, we perform **rotations** to restore balance.

There are four cases:

#### LL Case (Left-Left) → Right Rotation

```
Before:        After:
    30            20
   /             /  \
  20           10    30
 /
10
```

```cpp
// Right rotation
TreeNode* rotateRight(TreeNode* y) {
    TreeNode* x = y->left;
    TreeNode* T2 = x->right;
    
    x->right = y;
    y->left = T2;
    
    return x; // x is the new root
}
```

#### RR Case (Right-Right) → Left Rotation

```
Before:        After:
10               20
  \             /  \
  20          10    30
    \
    30
```

```cpp
// Left rotation
TreeNode* rotateLeft(TreeNode* x) {
    TreeNode* y = x->right;
    TreeNode* T2 = y->left;
    
    y->left = x;
    x->right = T2;
    
    return y; // y is the new root
}
```

#### LR Case (Left-Right) → Left Rotation then Right Rotation

```
Before:        After Left Rot:     After Right Rot:
    30            30                   20
   /             /                    /  \
  10           20                   10    30
    \         /
    20       10
```

#### RL Case (Right-Left) → Right Rotation then Left Rotation

```
Before:        After Right Rot:    After Left Rot:
10             10                    20
  \              \                  /  \
  30             20              10    30
  /                \
 20                 30
```

### Complete AVL Tree Implementation

```cpp
#include <iostream>
#include <algorithm>
#include <vector>

class AVLTree {
    struct Node {
        int val;
        Node* left;
        Node* right;
        int height;
        Node(int v) : val(v), left(nullptr), right(nullptr), height(1) {}
    };

    Node* root;

    int height(Node* node) {
        return node ? node->height : 0;
    }

    int balanceFactor(Node* node) {
        return node ? height(node->left) - height(node->right) : 0;
    }

    void updateHeight(Node* node) {
        if (node) {
            node->height = 1 + std::max(height(node->left), height(node->right));
        }
    }

    // Right rotation
    Node* rotateRight(Node* y) {
        Node* x = y->left;
        Node* T2 = x->right;
        
        x->right = y;
        y->left = T2;
        
        updateHeight(y);
        updateHeight(x);
        
        return x;
    }

    // Left rotation
    Node* rotateLeft(Node* x) {
        Node* y = x->right;
        Node* T2 = y->left;
        
        y->left = x;
        x->right = T2;
        
        updateHeight(x);
        updateHeight(y);
        
        return y;
    }

    // Balance a node
    Node* balance(Node* node) {
        updateHeight(node);
        int bf = balanceFactor(node);
        
        // Left-heavy
        if (bf > 1) {
            if (balanceFactor(node->left) < 0) {
                // LR case: left rotation on left child
                node->left = rotateLeft(node->left);
            }
            // LL case: right rotation
            return rotateRight(node);
        }
        
        // Right-heavy
        if (bf < -1) {
            if (balanceFactor(node->right) > 0) {
                // RL case: right rotation on right child
                node->right = rotateRight(node->right);
            }
            // RR case: left rotation
            return rotateLeft(node);
        }
        
        return node;
    }

    Node* insert(Node* node, int val) {
        if (!node) return new Node(val);
        
        if (val < node->val) node->left = insert(node->left, val);
        else if (val > node->val) node->right = insert(node->right, val);
        else return node; // No duplicates
        
        return balance(node);
    }

    Node* findMin(Node* node) {
        while (node->left) node = node->left;
        return node;
    }

    Node* deleteNode(Node* node, int val) {
        if (!node) return nullptr;
        
        if (val < node->val) node->left = deleteNode(node->left, val);
        else if (val > node->val) node->right = deleteNode(node->right, val);
        else {
            if (!node->left) { Node* t = node->right; delete node; return t; }
            if (!node->right) { Node* t = node->left; delete node; return t; }
            Node* succ = findMin(node->right);
            node->val = succ->val;
            node->right = deleteNode(node->right, succ->val);
        }
        
        return balance(node);
    }

    void inorder(Node* node, std::vector<int>& result) {
        if (!node) return;
        inorder(node->left, result);
        result.push_back(node->val);
        inorder(node->right, result);
    }

    void freeTree(Node* node) {
        if (!node) return;
        freeTree(node->left);
        freeTree(node->right);
        delete node;
    }

public:
    AVLTree() : root(nullptr) {}
    ~AVLTree() { freeTree(root); }

    void insert(int val) { root = insert(root, val); }
    void erase(int val) { root = deleteNode(root, val); }

    std::vector<int> inorderTraversal() {
        std::vector<int> result;
        inorder(root, result);
        return result;
    }
};

int main() {
    AVLTree avl;
    
    // Insert elements that would cause a skewed BST
    for (int i = 1; i <= 10; ++i) {
        avl.insert(i);
    }
    
    std::cout << "AVL inorder: ";
    for (int v : avl.inorderTraversal()) std::cout << v << " ";
    std::cout << "\n";
    // Output: 1 2 3 4 5 6 7 8 9 10 (sorted, as expected)
    
    // The tree is balanced despite inserting in sorted order!
    
    avl.erase(5);
    std::cout << "After erase 5: ";
    for (int v : avl.inorderTraversal()) std::cout << v << " ";
    std::cout << "\n";
    
    return 0;
}
```

### AVL Tree Complexity

| Operation | Time | Space |
|-----------|------|-------|
| Search | O(log n) | O(log n) |
| Insert | O(log n) | O(log n) |
| Delete | O(log n) | O(log n) |
| Rotations per insert | At most 2 | — |
| Rotations per delete | At most O(log n) | — |

---

## 14.6 Red-Black Trees

A **Red-Black Tree** is another self-balancing BST that guarantees O(log n) operations through a set of color-based rules.

### Properties

Every node is either **red** or **black**, and the following invariants hold:

1. **Root is black.**
2. **Every leaf (NIL) is black.**
3. **If a node is red, both its children are black.** (No two consecutive red nodes.)
4. **Every path from a node to its descendant leaves has the same number of black nodes.** (Black-height property.)

These properties guarantee that the longest path is at most twice the shortest path, ensuring O(log n) height.

### Why Red-Black Trees?

| Feature | AVL Tree | Red-Black Tree |
|---------|----------|----------------|
| Balance | Strictly balanced | Approximately balanced |
| Height | ≤ 1.44 log n | ≤ 2 log n |
| Insert rotations | Up to 2 | Up to 2 |
| Delete rotations | Up to O(log n) | Up to 3 |
| Lookup speed | Faster (more balanced) | Slightly slower |
| Insert/Delete speed | Slightly slower | Faster (fewer rotations) |
| Use in STL | No | Yes (`std::map`, `std::set`) |

Red-Black trees are preferred in practice for data structures with frequent insertions/deletions because they require fewer rotations on average.

### Simplified Red-Black Tree Implementation

A full Red-Black tree implementation is complex. Here is a simplified version showing the core concepts:

```cpp
#include <iostream>
#include <vector>

enum Color { RED, BLACK };

struct RBNode {
    int val;
    Color color;
    RBNode* left;
    RBNode* right;
    RBNode* parent;
    
    RBNode(int v, Color c = RED) 
        : val(v), color(c), left(nullptr), right(nullptr), parent(nullptr) {}
};

class RedBlackTree {
    RBNode* root;
    RBNode* NIL; // Sentinel node for leaves

    void leftRotate(RBNode* x) {
        RBNode* y = x->right;
        x->right = y->left;
        if (y->left != NIL) y->left->parent = x;
        y->parent = x->parent;
        if (!x->parent) root = y;
        else if (x == x->parent->left) x->parent->left = y;
        else x->parent->right = y;
        y->left = x;
        x->parent = y;
    }

    void rightRotate(RBNode* x) {
        RBNode* y = x->left;
        x->left = y->right;
        if (y->right != NIL) y->right->parent = x;
        y->parent = x->parent;
        if (!x->parent) root = y;
        else if (x == x->parent->right) x->parent->right = y;
        else x->parent->left = y;
        y->right = x;
        x->parent = y;
    }

    // Fix violations after insertion
    void insertFixup(RBNode* z) {
        while (z->parent && z->parent->color == RED) {
            if (z->parent == z->parent->parent->left) {
                RBNode* uncle = z->parent->parent->right;
                
                if (uncle->color == RED) {
                    // Case 1: Uncle is red — recolor
                    z->parent->color = BLACK;
                    uncle->color = BLACK;
                    z->parent->parent->color = RED;
                    z = z->parent->parent;
                } else {
                    if (z == z->parent->right) {
                        // Case 2: Uncle is black, z is right child — left rotate
                        z = z->parent;
                        leftRotate(z);
                    }
                    // Case 3: Uncle is black, z is left child — right rotate
                    z->parent->color = BLACK;
                    z->parent->parent->color = RED;
                    rightRotate(z->parent->parent);
                }
            } else {
                // Symmetric cases (parent is right child)
                RBNode* uncle = z->parent->parent->left;
                
                if (uncle->color == RED) {
                    z->parent->color = BLACK;
                    uncle->color = BLACK;
                    z->parent->parent->color = RED;
                    z = z->parent->parent;
                } else {
                    if (z == z->parent->left) {
                        z = z->parent;
                        rightRotate(z);
                    }
                    z->parent->color = BLACK;
                    z->parent->parent->color = RED;
                    leftRotate(z->parent->parent);
                }
            }
        }
        root->color = BLACK;
    }

    void transplant(RBNode* u, RBNode* v) {
        if (!u->parent) root = v;
        else if (u == u->parent->left) u->parent->left = v;
        else u->parent->right = v;
        v->parent = u->parent;
    }

    RBNode* findMin(RBNode* node) {
        while (node->left != NIL) node = node->left;
        return node;
    }

    void deleteFixup(RBNode* x) {
        while (x != root && x->color == BLACK) {
            if (x == x->parent->left) {
                RBNode* w = x->parent->right;
                if (w->color == RED) {
                    w->color = BLACK;
                    x->parent->color = RED;
                    leftRotate(x->parent);
                    w = x->parent->right;
                }
                if (w->left->color == BLACK && w->right->color == BLACK) {
                    w->color = RED;
                    x = x->parent;
                } else {
                    if (w->right->color == BLACK) {
                        w->left->color = BLACK;
                        w->color = RED;
                        rightRotate(w);
                        w = x->parent->right;
                    }
                    w->color = x->parent->color;
                    x->parent->color = BLACK;
                    w->right->color = BLACK;
                    leftRotate(x->parent);
                    x = root;
                }
            } else {
                // Symmetric
                RBNode* w = x->parent->left;
                if (w->color == RED) {
                    w->color = BLACK;
                    x->parent->color = RED;
                    rightRotate(x->parent);
                    w = x->parent->left;
                }
                if (w->right->color == BLACK && w->left->color == BLACK) {
                    w->color = RED;
                    x = x->parent;
                } else {
                    if (w->left->color == BLACK) {
                        w->right->color = BLACK;
                        w->color = RED;
                        leftRotate(w);
                        w = x->parent->left;
                    }
                    w->color = x->parent->color;
                    x->parent->color = BLACK;
                    w->left->color = BLACK;
                    rightRotate(x->parent);
                    x = root;
                }
            }
        }
        x->color = BLACK;
    }

    void inorder(RBNode* node, std::vector<int>& result) {
        if (node == NIL) return;
        inorder(node->left, result);
        result.push_back(node->val);
        inorder(node->right, result);
    }

    void freeTree(RBNode* node) {
        if (node == NIL) return;
        freeTree(node->left);
        freeTree(node->right);
        delete node;
    }

public:
    RedBlackTree() {
        NIL = new RBNode(0, BLACK);
        root = NIL;
    }
    
    ~RedBlackTree() {
        freeTree(root);
        delete NIL;
    }

    void insert(int val) {
        RBNode* z = new RBNode(val);
        z->left = NIL;
        z->right = NIL;
        
        RBNode* y = nullptr;
        RBNode* x = root;
        
        while (x != NIL) {
            y = x;
            if (z->val < x->val) x = x->left;
            else if (z->val > x->val) x = x->right;
            else { delete z; return; } // No duplicates
        }
        
        z->parent = y;
        if (!y) root = z;
        else if (z->val < y->val) y->left = z;
        else y->right = z;
        
        if (!z->parent) {
            z->color = BLACK;
            return;
        }
        
        if (!z->parent->parent) return;
        
        insertFixup(z);
    }

    std::vector<int> inorderTraversal() {
        std::vector<int> result;
        inorder(root, result);
        return result;
    }
};

int main() {
    RedBlackTree rbt;
    
    for (int i = 1; i <= 15; ++i) {
        rbt.insert(i);
    }
    
    std::cout << "Red-Black Tree inorder: ";
    for (int v : rbt.inorderTraversal()) std::cout << v << " ";
    std::cout << "\n";
    // Output: 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15
    
    return 0;
}
```

### Red-Black Tree Insertion Cases Summary

| Case | Uncle Color | Action |
|------|-------------|--------|
| 1 | Red | Recolor parent, uncle, grandparent. Move up. |
| 2 | Black, z is right child | Left rotate on parent. |
| 3 | Black, z is left child | Recolor parent and grandparent. Right rotate on grandparent. |

---

## 14.7 STL Set and Map

The C++ STL provides associative containers backed by balanced BSTs (typically Red-Black trees).

### `std::set`

A sorted collection of unique elements.

```cpp
#include <iostream>
#include <set>
#include <string>

int main() {
    std::set<int> s = {5, 3, 8, 1, 3, 5}; // Duplicates removed
    
    std::cout << "Set: ";
    for (int x : s) std::cout << x << " ";
    std::cout << "\n"; // 1 3 5 8
    
    // Insert
    s.insert(4);
    s.insert(10);
    
    // Search
    std::cout << "Contains 4: " << (s.count(4) ? "yes" : "no") << "\n";
    std::cout << "Contains 99: " << (s.count(99) ? "yes" : "no") << "\n";
    
    // Find
    auto it = s.find(5);
    if (it != s.end()) {
        std::cout << "Found: " << *it << "\n";
    }
    
    // Erase
    s.erase(3);
    
    // Lower/upper bound
    auto lb = s.lower_bound(5);  // >= 5
    auto ub = s.upper_bound(5);  // > 5
    std::cout << "Lower bound of 5: " << *lb << "\n";
    std::cout << "Upper bound of 5: " << *ub << "\n";
    
    // Size
    std::cout << "Size: " << s.size() << "\n";
    
    return 0;
}
```

### `std::multiset`

Allows duplicate elements.

```cpp
#include <iostream>
#include <multiset>

int main() {
    std::multiset<int> ms = {3, 1, 4, 1, 5, 9, 2, 6, 5};
    
    std::cout << "Multiset: ";
    for (int x : ms) std::cout << x << " ";
    std::cout << "\n"; // 1 1 2 3 4 5 5 6 9
    
    // Count duplicates
    std::cout << "Count of 1: " << ms.count(1) << "\n"; // 2
    std::cout << "Count of 5: " << ms.count(5) << "\n"; // 2
    
    // Erase all occurrences
    ms.erase(1);
    std::cout << "After erase(1): ";
    for (int x : ms) std::cout << x << " ";
    std::cout << "\n";
    
    // Erase single occurrence
    auto it = ms.find(5);
    if (it != ms.end()) ms.erase(it);
    std::cout << "After erase one 5: ";
    for (int x : ms) std::cout << x << " ";
    std::cout << "\n";
    
    return 0;
}
```

### `std::map`

A sorted key-value store.

```cpp
#include <iostream>
#include <map>
#include <string>

int main() {
    std::map<std::string, int> ages;
    
    // Insert
    ages["Alice"] = 30;
    ages["Bob"] = 25;
    ages.insert({"Charlie", 35});
    ages.emplace("Diana", 28);
    
    // Access
    std::cout << "Alice's age: " << ages["Alice"] << "\n";
    
    // Check existence
    if (ages.count("Bob")) {
        std::cout << "Bob exists\n";
    }
    
    // Find
    auto it = ages.find("Charlie");
    if (it != ages.end()) {
        std::cout << "Charlie: " << it->second << "\n";
    }
    
    // Iterate (sorted by key)
    std::cout << "All entries:\n";
    for (const auto& [name, age] : ages) {
        std::cout << "  " << name << ": " << age << "\n";
    }
    
    // Lower/upper bound
    auto lb = ages.lower_bound("B"); // >= "B"
    std::cout << "First entry >= 'B': " << lb->first << "\n";
    
    // Erase
    ages.erase("Bob");
    
    return 0;
}
```

### `std::multimap`

Allows duplicate keys.

```cpp
#include <iostream>
#include <map>
#include <string>

int main() {
    std::multimap<std::string, int> scores;
    
    scores.insert({"Alice", 95});
    scores.insert({"Alice", 87});
    scores.insert({"Bob", 72});
    scores.insert({"Bob", 88});
    scores.insert({"Alice", 91});
    
    // Iterate
    std::cout << "All scores:\n";
    for (const auto& [name, score] : scores) {
        std::cout << "  " << name << ": " << score << "\n";
    }
    
    // Find all of Alice's scores
    std::cout << "Alice's scores: ";
    auto [begin, end] = scores.equal_range("Alice");
    for (auto it = begin; it != end; ++it) {
        std::cout << it->second << " ";
    }
    std::cout << "\n";
    
    return 0;
}
```

### When to Use Which

| Container | Unique Keys? | Sorted? | Use Case |
|-----------|-------------|---------|----------|
| `std::set` | Yes | Yes | Unique sorted elements |
| `std::multiset` | No | Yes | Sorted elements with duplicates |
| `std::map` | Yes | Yes | Key-value pairs, sorted by key |
| `std::multimap` | No | Yes | Key-value with duplicate keys |
| `std::unordered_set` | Yes | No | Fast lookup, order doesn't matter |
| `std::unordered_map` | Yes | No | Fast key-value lookup |

### Operations Complexity

| Operation | `std::set`/`std::map` | `std::unordered_set`/`std::unordered_map` |
|-----------|----------------------|------------------------------------------|
| Insert | O(log n) | Amortized O(1) |
| Delete | O(log n) | Amortized O(1) |
| Search | O(log n) | Amortized O(1) |
| Lower/Upper bound | O(log n) | N/A |
| Iteration | O(n) sorted | O(n) unsorted |

**Rule of thumb:** Use ordered containers (`set`/`map`) when you need sorted order or range queries. Use unordered containers when you only need fast lookup.

---

## Interview Tips

1. **BST + inorder = sorted.** This is the single most important property. Use it for validation, kth element, and range queries.
2. **Know the three delete cases.** Leaf, one child, two children (replace with inorder successor).
3. **Validate with range checking, not just local comparison.** The local check `left->val < root->val < right->val` is insufficient.
4. **Understand balance.** Know why unbalanced BSTs degrade to O(n) and how self-balancing trees fix this.
5. **STL containers are your friends.** Use `std::set` and `std::map` in interviews unless asked to implement from scratch.
6. **Kth smallest/largest:** Inorder traversal gives kth smallest. Reverse inorder gives kth largest. Or use a `multiset`.

## Common Mistakes

| Mistake | Example | Fix |
|---------|---------|-----|
| Local-only BST validation | Only checking children, not all descendants | Use range checking or inorder traversal |
| Forgetting inorder successor has no left child | Wrong successor selection | The successor is the minimum in the right subtree |
| Not handling duplicate keys | Inserting duplicates into a set | Decide on policy: skip, count, or allow |
| Using `operator[]` on `std::map` for checking | Creates default entry if key doesn't exist | Use `find()` or `count()` instead |
| Confusing `lower_bound` and `upper_bound` | Wrong boundary for range queries | `lower_bound(x)` ≥ x, `upper_bound(x)` > x |
| Not updating heights in AVL tree | Wrong balance factor calculation | Update height after every rotation |

---

## Practice Problems

### Easy

1. **Search in a BST** — Given a BST and a value, return the subtree rooted at the value.
   - *Hint:* Standard BST search.

2. **Insert into a BST** — Insert a value into a BST and return the root.
   - *Hint:* Traverse to the correct position, create a new node.

3. **Minimum Distance Between BST Nodes** — Find the minimum absolute difference between any two nodes.
   - *Hint:* Inorder traversal. Compare each node with the previous one.

### Medium

4. **Validate Binary Search Tree** — Check if a binary tree is a valid BST.
   - *Hint:* Range checking with min/max, or inorder traversal with previous value.

5. **Kth Smallest Element in a BST** — Find the kth smallest element.
   - *Hint:* Inorder traversal. Stop at the kth element.

6. **Lowest Common Ancestor of a BST** — Find the LCA of two nodes in a BST.
   - *Hint:* If both values are less than root, go left. If both greater, go right. Otherwise, root is the LCA.

7. **Convert Sorted Array to BST** — Given a sorted array, construct a height-balanced BST.
   - *Hint:* Pick the middle element as root. Recursively build left and right subtrees.

8. **Two Sum IV - Input is a BST** — Find two elements that sum to a target.
   - *Hint:* Inorder traversal to get sorted array, then two-pointer. Or use a hash set during traversal.

### Hard

9. **Binary Search Tree Iterator** — Implement an iterator that returns the next smallest element.
   - *Hint:* Use a stack. Push all left children. On `next()`, pop and push all left children of the right child.

10. **Count of Smaller Numbers After Self** — For each element, count how many smaller elements appear after it.
    - *Hint:* Process right to left. Insert into a BST with subtree size tracking. Or use merge sort.

11. **Serialize and Deserialize BST** — Serialize a BST more efficiently than a general binary tree.
    - *Hint:* Preorder is sufficient for BST (no need for null markers if you use range checking during deserialization).

---

## Complexity Summary

| Data Structure | Search | Insert | Delete | Space | Sorted? |
|---------------|--------|--------|--------|-------|---------|
| Unbalanced BST | O(n) worst | O(n) worst | O(n) worst | O(n) | Inorder |
| AVL Tree | O(log n) | O(log n) | O(log n) | O(n) | Inorder |
| Red-Black Tree | O(log n) | O(log n) | O(log n) | O(n) | Inorder |
| `std::set` | O(log n) | O(log n) | O(log n) | O(n) | Yes |
| `std::map` | O(log n) | O(log n) | O(log n) | O(n) | Yes |
| `std::unordered_set` | O(1) avg | O(1) avg | O(1) avg | O(n) | No |
| `std::unordered_map` | O(1) avg | O(1) avg | O(1) avg | O(n) | No |

---

## See Also

- [Chapter 13: Trees](ch13-trees.md) — Tree fundamentals: traversals, recursion on trees, and basic tree properties.
- [Chapter 98: Splay Trees](ch98-splay-trees.md) — Self-adjusting BST with amortized O(log n); no explicit balance information stored.
- [Chapter 99: Scapegoat and AA Trees](ch99-scapegoat-aa-trees.md) — Simpler balanced BST alternatives with easier implementation than red-black trees.
- [Chapter 15: Heaps](ch15-heaps.md) — When you only need min/max extraction, heaps are simpler than BSTs.
- [Chapter 74: Skip Lists](ch74-skip-lists.md) — A probabilistic alternative to balanced BSTs with expected O(log n) operations.
- [Chapter 100: Van Emde Boas Trees](ch100-van-emde-boas.md) — For integer keys in a bounded range, vEB trees achieve O(log log n) operations.
