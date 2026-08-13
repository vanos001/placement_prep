# Chapter 57: Expanded Trees

## Prerequisites

- Binary Search Trees (BST) and balanced BST concepts
- Segment Trees and lazy propagation
- Basic graph theory (DFS, BFS, tree traversals)
- Recursion and divide-and-conquer
- Dynamic programming fundamentals

## Interview Frequency: ★★★★

Advanced tree structures appear frequently in interviews at top-tier companies. Heavy-Light Decomposition and Euler Tour are favorites at **Google**, **Meta**, and **Amazon** for hard-level problems. Tree DP is ubiquitous across all companies. Persistent data structures appear at **Google** and **Microsoft**. Centroid Decomposition shows up in competitive programming-oriented interviews at **ByteDance** and **Yandex**.

| Topic | Frequency | Typical Companies | Difficulty |
|---|---|---|---|
| Treap | ★★★ | Google, Meta | Medium-Hard |
| Splay Tree | ★★ | Research labs | Hard |
| Cartesian Tree | ★★★ | Google, Amazon | Medium |
| B-Tree / B+ Tree | ★★★★ | Database companies, Amazon | Medium |
| Persistent Segment Tree | ★★★ | Google, ByteDance | Hard |
| Wavelet Tree | ★★ | Competitive programming | Hard |
| Euler Tour | ★★★★ | Google, Meta, Amazon | Medium |
| HLD | ★★★★ | Google, Meta, ByteDance | Hard |
| Centroid Decomposition | ★★★ | ByteDance, Yandex | Hard |
| Tree DP | ★★★★★ | All companies | Medium-Hard |
| Tree Isomorphism | ★★ | Google | Medium |
| LCA | ★★★★★ | All companies | Medium |

---

## 57.1 Treap (Randomized BST)

A **Treap** (tree + heap) is a randomized binary search tree that maintains BST property on keys and heap property on random priorities. The key insight: by assigning random priorities, the expected height is O(log n), giving expected O(log n) operations without complex balancing logic.

### When to Use

- You need a balanced BST with simpler implementation than AVL/Red-Black trees
- You want expected O(log n) without deterministic guarantees
- You need to split/merge trees efficiently (implicit treaps)

### When NOT to Use

- When worst-case O(log n) is required (use AVL or Red-Black tree)
- When deterministic behavior is needed (randomization introduces variance)
- Simple sorted data → use `std::set`

### Design Trade-offs

| Aspect | Treap | AVL | Red-Black Tree | std::set |
|---|---|---|---|---|
| Balance guarantee | Expected O(log n) | Worst-case O(log n) | Worst-case O(log n) | Implementation-defined |
| Insert/Delete | Expected O(log n) | O(log n) | O(log n) | O(log n) |
| Split/Merge | O(log n) expected | Complex | Complex | Not supported |
| Implementation | Simple | Complex | Very complex | N/A (library) |
| Space | O(n) | O(n) | O(n) | O(n) |

### Complete Implementation

```cpp
#include <iostream>
#include <random>
#include <chrono>
#include <vector>
#include <algorithm>

struct TreapNode {
    int key;
    int priority;
    int size;
    TreapNode* left;
    TreapNode* right;
    
    TreapNode(int k) : key(k), priority(rng()), size(1), 
                        left(nullptr), right(nullptr) {}
    
    static std::mt19937 rng;
    
    void update() {
        size = 1 + (left ? left->size : 0) + (right ? right->size : 0);
    }
};

std::mt19937 TreapNode::rng(std::chrono::steady_clock::now()
    .time_since_epoch().count());

// Split treap into two: keys <= k go to left, keys > k go to right
std::pair<TreapNode*, TreapNode*> split(TreapNode* root, int k) {
    if (!root) return {nullptr, nullptr};
    
    if (root->key <= k) {
        auto [left, right] = split(root->right, k);
        root->right = left;
        root->update();
        return {root, right};
    } else {
        auto [left, right] = split(root->left, k);
        root->left = right;
        root->update();
        return {left, root};
    }
}

// Merge two treaps where all keys in left < all keys in right
TreapNode* merge(TreapNode* left, TreapNode* right) {
    if (!left) return right;
    if (!right) return left;
    
    if (left->priority > right->priority) {
        left->right = merge(left->right, right);
        left->update();
        return left;
    } else {
        right->left = merge(left, right->left);
        right->update();
        return right;
    }
}

TreapNode* insert(TreapNode* root, int key) {
    auto [left, right] = split(root, key);
    TreapNode* node = new TreapNode(key);
    return merge(merge(left, node), right);
}

TreapNode* erase(TreapNode* root, int key) {
    auto [left, mid_right] = split(root, key - 1);
    auto [mid, right] = split(mid_right, key);
    // mid contains all nodes with key == key; remove one
    if (mid) {
        // Remove the root of mid by merging its children
        mid = merge(mid->left, mid->right);
    }
    return merge(merge(left, mid), right);
}

// k-th smallest (1-indexed)
int kth(TreapNode* root, int k) {
    if (!root) return -1;
    int leftSize = root->left ? root->left->size : 0;
    if (k <= leftSize) return kth(root->left, k);
    if (k == leftSize + 1) return root->key;
    return kth(root->right, k - leftSize - 1);
}

// Count of elements <= x
int countLessEqual(TreapNode* root, int x) {
    if (!root) return 0;
    if (root->key <= x) {
        int leftSize = root->left ? root->left->size : 0;
        return leftSize + 1 + countLessEqual(root->right, x);
    }
    return countLessEqual(root->left, x);
}

void inorder(TreapNode* root) {
    if (!root) return;
    inorder(root->left);
    std::cout << root->key << " ";
    inorder(root->right);
}

void cleanup(TreapNode* root) {
    if (!root) return;
    cleanup(root->left);
    cleanup(root->right);
    delete root;
}

int main() {
    TreapNode* root = nullptr;
    
    // Insert elements
    for (int x : {5, 3, 7, 1, 4, 6, 8, 2}) {
        root = insert(root, x);
    }
    
    std::cout << "Inorder: ";
    inorder(root);
    std::cout << "\n";
    
    std::cout << "3rd smallest: " << kth(root, 3) << "\n";
    std::cout << "Count <= 4: " << countLessEqual(root, 4) << "\n";
    
    root = erase(root, 3);
    std::cout << "After erasing 3: ";
    inorder(root);
    std::cout << "\n";
    
    cleanup(root);
    return 0;
}
```

### Implicit Treap

An implicit treap uses the "size" as the implicit key, enabling array-like operations (insert at position, erase at position, reverse range) in O(log n).

```cpp
#include <iostream>
#include <random>
#include <chrono>
#include <utility>

struct ImplicitTreap {
    int val;
    int priority;
    int size;
    bool reversed;
    ImplicitTreap *left, *right;
    
    ImplicitTreap(int v) : val(v), priority(rand()), size(1), 
                           reversed(false), left(nullptr), right(nullptr) {}
    
    void push() {
        if (reversed) {
            reversed = false;
            std::swap(left, right);
            if (left) left->reversed ^= true;
            if (right) right->reversed ^= true;
        }
    }
    
    void update() {
        size = 1;
        if (left) { left->push(); size += left->size; }
        if (right) { right->push(); size += right->size; }
    }
};

int getSize(ImplicitTreap* t) { return t ? t->size : 0; }

std::pair<ImplicitTreap*, ImplicitTreap*> split(ImplicitTreap* t, int pos) {
    if (!t) return {nullptr, nullptr};
    t->push();
    if (getSize(t->left) >= pos) {
        auto [l, r] = split(t->left, pos);
        t->left = r;
        t->update();
        return {l, t};
    } else {
        auto [l, r] = split(t->right, pos - getSize(t->left) - 1);
        t->right = l;
        t->update();
        return {t, r};
    }
}

ImplicitTreap* merge(ImplicitTreap* l, ImplicitTreap* r) {
    if (!l) return r;
    if (!r) return l;
    l->push(); r->push();
    if (l->priority > r->priority) {
        l->right = merge(l->right, r);
        l->update();
        return l;
    } else {
        r->left = merge(l, r->left);
        r->update();
        return r;
    }
}

// Reverse range [l, r)
ImplicitTreap* reverseRange(ImplicitTreap* t, int l, int r) {
    auto [left, mid_right] = split(t, l);
    auto [mid, right] = split(mid_right, r - l);
    if (mid) mid->reversed ^= true;
    return merge(merge(left, mid), right);
}

void print(ImplicitTreap* t) {
    if (!t) return;
    t->push();
    print(t->left);
    std::cout << t->val << " ";
    print(t->right);
}

int main() {
    ImplicitTreap* root = nullptr;
    for (int i = 1; i <= 10; i++) {
        root = merge(root, new ImplicitTreap(i));
    }
    
    std::cout << "Original: ";
    print(root);
    std::cout << "\n";
    
    root = reverseRange(root, 2, 7);
    std::cout << "After reverse [2,7): ";
    print(root);
    std::cout << "\n";
    
    return 0;
}
```

---

## 57.2 Splay Tree

A **Splay Tree** is a self-adjusting BST where recently accessed elements are moved to the root via a series of rotations called **splaying**. It achieves amortized O(log n) for all operations without storing balance factors or colors.

### The Splay Operation

The splay operation moves a node to the root using three cases:
1. **Zig**: Single rotation (node's parent is root)
2. **Zig-Zig**: Double rotation in same direction (node and parent are both left or both right children)
3. **Zig-Zag**: Double rotation in different directions

### When to Use

- When temporal locality exists (recently accessed items accessed again soon)
- When simplicity of implementation matters
- When amortized bounds are acceptable

### When NOT to Use

- When worst-case per-operation guarantee is needed
- When the access pattern is adversarial (can cause O(n) per operation)
- Real-time systems where amortized bounds don't help

### Complete Implementation

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
                // Zig step
                if (x == p->left) rotateRight(p);
                else rotateLeft(p);
            } else if (x == p->left && p == g->left) {
                // Zig-zig (left-left)
                rotateRight(g);
                rotateRight(p);
            } else if (x == p->right && p == g->right) {
                // Zig-zig (right-right)
                rotateLeft(g);
                rotateLeft(p);
            } else if (x == p->right && p == g->left) {
                // Zig-zag (left-right)
                rotateLeft(p);
                rotateRight(g);
            } else {
                // Zig-zag (right-left)
                rotateRight(p);
                rotateLeft(g);
            }
        }
    }
    
public:
    SplayTree() : root(nullptr) {}
    
    void insert(int key) {
        SplayNode* node = new SplayNode(key);
        if (!root) {
            root = node;
            return;
        }
        
        SplayNode* curr = root;
        SplayNode* parent = nullptr;
        while (curr) {
            parent = curr;
            if (key < curr->key) curr = curr->left;
            else curr = curr->right;
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
            else if (key < curr->key) curr = curr->left;
            else curr = curr->right;
        }
        if (last) splay(last);
        return last && last->key == key;
    }
    
    void erase(int key) {
        if (!search(key)) return;
        
        SplayNode* leftSub = root->left;
        SplayNode* rightSub = root->right;
        
        if (leftSub) leftSub->parent = nullptr;
        if (rightSub) rightSub->parent = nullptr;
        
        delete root;
        
        if (!leftSub) {
            root = rightSub;
        } else {
            // Splay the maximum in left subtree
            root = leftSub;
            SplayNode* maxNode = leftSub;
            while (maxNode->right) maxNode = maxNode->right;
            splay(maxNode);
            root->right = rightSub;
            if (rightSub) rightSub->parent = root;
        }
    }
    
    void inorder(SplayNode* node) {
        if (!node) return;
        inorder(node->left);
        std::cout << node->key << " ";
        inorder(node->right);
    }
    
    void print() {
        inorder(root);
        std::cout << "\n";
    }
    
    SplayNode* getRoot() { return root; }
};

int main() {
    SplayTree tree;
    for (int x : {10, 5, 15, 3, 7, 12, 20}) {
        tree.insert(x);
    }
    
    std::cout << "Tree: ";
    tree.print();
    
    tree.search(7);
    std::cout << "After searching 7, root = " 
              << tree.getRoot()->key << "\n";
    
    tree.erase(5);
    std::cout << "After erasing 5: ";
    tree.print();
    
    return 0;
}
```

---

## 57.3 Cartesian Tree

A **Cartesian Tree** constructed from an array has two properties:
1. **Heap property**: Parent value ≤ children's values (min-heap variant)
2. **Inorder traversal**: Recovers the original array

The crucial insight: **the LCA of two nodes in a Cartesian Tree gives the minimum element in the corresponding range of the original array**, making it a bridge to the Range Minimum Query (RMQ) problem.

### Construction in O(n)

```cpp
#include <iostream>
#include <vector>
#include <stack>

struct CartNode {
    int val, idx;
    CartNode *left, *right;
    CartNode(int v, int i) : val(v), idx(i), left(nullptr), right(nullptr) {}
};

// Build Cartesian Tree in O(n) using a monotone stack
CartNode* buildCartesianTree(const std::vector<int>& arr) {
    int n = arr.size();
    if (n == 0) return nullptr;
    
    std::stack<CartNode*> st;
    
    for (int i = 0; i < n; i++) {
        CartNode* node = new CartNode(arr[i], i);
        CartNode* last = nullptr;
        
        while (!st.empty() && st.top()->val > arr[i]) {
            last = st.top();
            st.pop();
        }
        
        node->left = last;
        if (!st.empty()) {
            st.top()->right = node;
        }
        st.push(node);
    }
    
    // Bottom of stack is root
    while (st.size() > 1) st.pop();
    return st.top();
}

// LCA in Cartesian Tree = RMQ on original array
// For production, preprocess with binary lifting for O(log n) LCA
// Or use ±1 RMQ for O(1) with O(n) preprocessing

void printTree(CartNode* node, int depth = 0) {
    if (!node) return;
    printTree(node->right, depth + 1);
    for (int i = 0; i < depth; i++) std::cout << "  ";
    std::cout << node->val << "(i=" << node->idx << ")\n";
    printTree(node->left, depth + 1);
}

int main() {
    std::vector<int> arr = {3, 2, 6, 1, 9, 7, 4, 8, 5};
    
    CartNode* root = buildCartesianTree(arr);
    
    std::cout << "Cartesian Tree:\n";
    printTree(root);
    
    // The LCA of index 2 and index 6 in the Cartesian Tree
    // gives the minimum in arr[2..6] = min(6,1,9,7,4) = 1
    
    return 0;
}
```

### RMQ ↔ LCA Reduction

The equivalence between RMQ and LCA on Cartesian trees is fundamental:

| Problem | Reduction |
|---|---|
| RMQ → LCA | Build Cartesian Tree, find LCA |
| LCA → RMQ | Euler Tour + RMQ on depth array |
| Both → ±1 RMQ | Specialized O(1) solution |

This means any O(n + Q) RMQ solution gives O(n + Q) LCA, and vice versa.

---

## 57.4 B-Tree

A **B-Tree** of order `m` is a self-balancing multi-way search tree where:
- Each node has at most `m` children and `m-1` keys
- Each non-root node has at least `⌈m/2⌉` children
- All leaves are at the same depth

B-Trees are the backbone of **database indexing** and **filesystem metadata** because they minimize disk I/O by packing many keys into each node.

### When to Use

- Disk-based storage where I/O is the bottleneck
- Database indices (MySQL InnoDB, PostgreSQL)
- Filesystem directories (NTFS, HFS+, ext4 indirect blocks)

### When NOT to Use

- In-memory data where pointer overhead dominates (use BST)
- Write-heavy workloads with small records (LSM trees may be better)

### Key Design Insight

Each node maps to one disk page. By making nodes large (e.g., 4KB pages), we keep tree height extremely low:

| Order m | Height for 1 billion keys | Disk reads |
|---|---|---|
| 100 | 5 | 5 |
| 500 | 4 | 4 |
| 1000 | 3 | 3 |

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
        Node* fullChild = parent->children[idx];
        Node* newChild = new Node(fullChild->leaf);
        int mid = ORDER / 2;
        
        // Move keys from fullChild to newChild
        for (int i = mid + 1; i < (int)fullChild->keys.size(); i++) {
            newChild->keys.push_back(fullChild->keys[i]);
        }
        
        // Move children if not leaf
        if (!fullChild->leaf) {
            for (int i = mid + 1; i <= (int)fullChild->children.size() - 1; i++) {
                newChild->children.push_back(fullChild->children[i]);
            }
            fullChild->children.resize(mid + 1);
        }
        
        // Push median key up
        parent->keys.insert(parent->keys.begin() + idx, fullChild->keys[mid]);
        parent->children.insert(parent->children.begin() + idx + 1, newChild);
        
        fullChild->keys.resize(mid);
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
};

int main() {
    BTree<5> tree; // Order 5 B-Tree
    for (int x : {10, 20, 5, 6, 12, 30, 7, 17, 3, 1, 25, 40, 50}) {
        tree.insert(x);
    }
    
    for (int x : {6, 15, 25, 50}) {
        std::cout << "Search " << x << ": " 
                  << (tree.search(x) ? "found" : "not found") << "\n";
    }
    
    return 0;
}
```

---

## 57.5 B+ Tree

A **B+ Tree** is a variant of the B-Tree where:
- **All data resides in leaf nodes** (internal nodes only store keys for routing)
- **Leaf nodes are linked** for efficient range queries
- Internal nodes can hold more keys → shorter tree

### B-Tree vs B+ Tree

| Feature | B-Tree | B+ Tree |
|---|---|---|
| Data location | Internal + leaf | Leaf only |
| Leaf linkage | No | Yes (linked list) |
| Range queries | Slow (tree traversal) | Fast (leaf scan) |
| Internal node capacity | Smaller (stores data) | Larger (keys only) |
| Point queries | Slightly faster | Slightly slower (always go to leaf) |
| Used by | MongoDB (WiredTiger) | MySQL InnoDB, PostgreSQL |

B+ Trees dominate in databases because range queries (`SELECT * WHERE x BETWEEN a AND b`) just scan the linked leaf list once the starting point is found.

---

## 57.6 Persistent Segment Tree

A **Persistent Segment Tree** preserves previous versions after updates using **copy-on-write**: only create new nodes along the update path, sharing unchanged subtrees with previous versions.

### When to Use

- Query historical versions of data
- Offline range queries with time dimension
- K-th smallest in range (using persistent frequency tree)

### Space Analysis

Each update creates O(log n) new nodes. For Q updates: O((n + Q) log n) space.

### Complete Implementation

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

// Build initial tree
PSTNode* build(int lo, int hi) {
    if (lo == hi) return new PSTNode(0);
    int mid = (lo + hi) / 2;
    return new PSTNode(build(lo, mid), build(mid + 1, hi));
}

// Update: returns new root (previous version unchanged)
PSTNode* update(PSTNode* prev, int lo, int hi, int pos, int val) {
    if (lo == hi) return new PSTNode(prev->val + val);
    int mid = (lo + hi) / 2;
    if (pos <= mid) {
        return new PSTNode(update(prev->left, lo, mid, pos, val), 
                          prev->right);
    } else {
        return new PSTNode(prev->left, 
                          update(prev->right, mid + 1, hi, pos, val));
    }
}

// Query: range sum
int query(PSTNode* node, int lo, int hi, int ql, int qr) {
    if (!node || qr < lo || hi < ql) return 0;
    if (ql <= lo && hi <= qr) return node->val;
    int mid = (lo + hi) / 2;
    return query(node->left, lo, mid, ql, qr) + 
           query(node->right, mid + 1, hi, ql, qr);
}

// K-th smallest using two version roots
int kthSmallest(PSTNode* rootL, PSTNode* rootR, int lo, int hi, int k) {
    if (lo == hi) return lo;
    int mid = (lo + hi) / 2;
    int leftCount = rootR->left->val - rootL->left->val;
    if (k <= leftCount) {
        return kthSmallest(rootL->left, rootR->left, lo, mid, k);
    }
    return kthSmallest(rootL->right, rootR->right, mid + 1, hi, k - leftCount);
}

int main() {
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6};
    int n = arr.size();
    int maxVal = 10; // value range [1, maxVal]
    
    // Build version 0 (empty)
    PSTNode* root0 = build(1, maxVal);
    
    // Create versions: root[i] = state after inserting arr[0..i-1]
    std::vector<PSTNode*> roots = {root0};
    for (int i = 0; i < n; i++) {
        roots.push_back(update(roots.back(), 1, maxVal, arr[i], 1));
    }
    
    // Query: how many elements in arr[l..r] are <= x?
    // Use prefix sums: count(l, r, x) = query(roots[r+1], x) - query(roots[l], x)
    
    int l = 2, r = 5; // arr[2..5] = {4, 1, 5, 9}
    std::cout << "Range [" << l << "," << r << "]: ";
    for (int i = l; i <= r; i++) std::cout << arr[i] << " ";
    std::cout << "\n";
    
    // Count elements <= 5
    int count = query(roots[r + 1], 1, maxVal, 1, 5) - 
                query(roots[l], 1, maxVal, 1, 5);
    std::cout << "Count <= 5: " << count << "\n";
    
    // K-th smallest in range [l, r]
    int k = 2;
    int kth = kthSmallest(roots[l], roots[r + 1], 1, maxVal, k);
    std::cout << k << "-th smallest in [" << l << "," << r << "]: " << kth << "\n";
    
    return 0;
}
```

### Classic Application: K-th Smallest in Range

Given an array, answer queries "what is the k-th smallest element in arr[l..r]?" in O(log n) per query with O(n log n) preprocessing.

**Technique**: Coordinate compression + persistent segment tree where each version adds one more element.

---

## 57.7 Wavelet Tree (Overview)

A **Wavelet Tree** is a data structure that answers range frequency queries in O(log σ) time, where σ is the size of the alphabet.

**Key queries supported:**
- Count occurrences of value `x` in range `[l, r]`
- K-th smallest element in range `[l, r]`
- Count elements ≤ `x` in range `[l, r]`
- Range quantile queries

**How it works**: Recursively partition the value range, storing bitmaps at each level to track which elements go left/right.

| Query | Time | Space |
|---|---|---|
| Range count(x) | O(log σ) | O(n log σ) |
| K-th smallest in [l,r] | O(log σ) | O(n log σ) |
| Range ≤ x count | O(log σ) | O(n log σ) |

Wavelet trees are powerful for competitive programming but rare in interviews due to implementation complexity.

---

## 57.8 Euler Tour Technique

The **Euler Tour** flattens a tree into an array by recording each node when we first visit it (entry) and when we leave it (exit). This converts subtree queries into range queries on the flat array.

### Flattening Process

```cpp
#include <iostream>
#include <vector>

class EulerTour {
    int n, timer;
    std::vector<std::vector<int>> adj;
    std::vector<int> tin, tout, flat;
    
    void dfs(int u, int p) {
        tin[u] = timer;
        flat[timer] = u;
        timer++;
        for (int v : adj[u]) {
            if (v != p) {
                dfs(v, u);
            }
        }
        tout[u] = timer - 1;
    }
    
public:
    EulerTour(int n) : n(n), timer(0), adj(n), tin(n), tout(n), flat(n) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    void build(int root) {
        dfs(root, -1);
    }
    
    // Subtree of u corresponds to flat[tin[u]..tout[u]]
    std::pair<int, int> subtreeRange(int u) {
        return {tin[u], tout[u]};
    }
    
    bool isAncestor(int u, int v) {
        return tin[u] <= tin[v] && tout[v] <= tout[u];
    }
};

// Combined with Segment Tree for subtree queries
// Example: subtree sum, subtree max, etc.

int main() {
    //       0
    //      / \
    //     1   2
    //    /|   |
    //   3  4  5
    
    EulerTour et(6);
    et.addEdge(0, 1);
    et.addEdge(0, 2);
    et.addEdge(1, 3);
    et.addEdge(1, 4);
    et.addEdge(2, 5);
    
    et.build(0);
    
    auto [l, r] = et.subtreeRange(1);
    std::cout << "Subtree of 1: range [" << l << ", " << r << "]\n";
    
    std::cout << "0 is ancestor of 5: " << et.isAncestor(0, 5) << "\n";
    std::cout << "1 is ancestor of 5: " << et.isAncestor(1, 5) << "\n";
    
    return 0;
}
```

### Applications

| Query Type | Technique | Time |
|---|---|---|
| Subtree sum | Euler Tour + Segment Tree | O(log n) per query |
| Subtree update | Euler Tour + Lazy Seg Tree | O(log n) per update |
| Is ancestor? | Euler Tour (check tin/tout ranges) | O(1) |
| Path queries | Euler Tour + HLD (see below) | O(log² n) |

---

## 57.9 Heavy-Light Decomposition (HLD)

**Heavy-Light Decomposition** partitions a tree's edges into heavy and light chains such that any root-to-leaf path crosses at most O(log n) chains. Combined with a segment tree on each chain, this enables efficient path queries.

### Key Concept

For each non-leaf node, designate the child with the largest subtree as the **heavy child**. All other children are **light children**. The edge to the heavy child is a **heavy edge**; others are **light edges**.

**Critical property**: Any path from root to a node crosses at most O(log n) light edges.

### When to Use

- Path queries (sum, max, min) between arbitrary nodes
- Path updates (add value to all nodes on path)
- LCA queries (combined with segment tree)

### When NOT to Use

- Subtree-only queries (Euler Tour is simpler)
- Static trees with no queries (just do DFS)
- When O(n) per query is acceptable

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class HLD {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<int> parent, depth, heavy, head, pos, sz;
    std::vector<int> seg;
    int timer;
    
    int dfs(int u, int p) {
        parent[u] = p;
        sz[u] = 1;
        int maxSize = 0;
        for (int v : adj[u]) {
            if (v != p) {
                depth[v] = depth[u] + 1;
                int subSize = dfs(v, u);
                sz[u] += subSize;
                if (subSize > maxSize) {
                    maxSize = subSize;
                    heavy[u] = v;
                }
            }
        }
        return sz[u];
    }
    
    void decompose(int u, int h) {
        head[u] = h;
        pos[u] = timer++;
        if (heavy[u] != -1) {
            decompose(heavy[u], h); // Continue heavy chain
        }
        for (int v : adj[u]) {
            if (v != parent[u] && v != heavy[u]) {
                decompose(v, v); // Start new chain
            }
        }
    }
    
    // Segment tree operations
    void segUpdate(int idx, int val, int node, int lo, int hi) {
        if (lo == hi) {
            seg[node] = val;
            return;
        }
        int mid = (lo + hi) / 2;
        if (idx <= mid) segUpdate(idx, val, 2 * node, lo, mid);
        else segUpdate(idx, val, 2 * node + 1, mid + 1, hi);
        seg[node] = seg[2 * node] + seg[2 * node + 1];
    }
    
    int segQuery(int ql, int qr, int node, int lo, int hi) {
        if (qr < lo || hi < ql) return 0;
        if (ql <= lo && hi <= qr) return seg[node];
        int mid = (lo + hi) / 2;
        return segQuery(ql, qr, 2 * node, lo, mid) + 
               segQuery(ql, qr, 2 * node + 1, mid + 1, hi);
    }
    
public:
    HLD(int n) : n(n), adj(n), parent(n), depth(n), heavy(n, -1), 
                 head(n), pos(n), sz(n), seg(4 * n, 0), timer(0) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    void build(int root) {
        dfs(root, -1);
        decompose(root, root);
    }
    
    // Update node value
    void update(int u, int val) {
        segUpdate(pos[u], val, 1, 0, n - 1);
    }
    
    // Query on path from u to root (can be extended to u-v)
    int queryPath(int u, int v) {
        int result = 0;
        while (head[u] != head[v]) {
            if (depth[head[u]] < depth[head[v]]) std::swap(u, v);
            result += segQuery(pos[head[u]], pos[u], 1, 0, n - 1);
            u = parent[head[u]];
        }
        if (depth[u] > depth[v]) std::swap(u, v);
        result += segQuery(pos[u], pos[v], 1, 0, n - 1);
        return result;
    }
    
    int lca(int u, int v) {
        while (head[u] != head[v]) {
            if (depth[head[u]] < depth[head[v]]) std::swap(u, v);
            u = parent[head[u]];
        }
        return depth[u] < depth[v] ? u : v;
    }
};

int main() {
    //       0
    //      / \
    //     1   2
    //    /|   |
    //   3  4  5
    
    HLD hld(6);
    hld.addEdge(0, 1);
    hld.addEdge(0, 2);
    hld.addEdge(1, 3);
    hld.addEdge(1, 4);
    hld.addEdge(2, 5);
    
    hld.build(0);
    
    // Set node values
    for (int i = 0; i < 6; i++) hld.update(i, i + 1); // values 1-6
    
    // Path query from 3 to 5: 3→1→0→2→5 = 4+2+1+3+6 = 16
    std::cout << "Path sum 3 to 5: " << hld.queryPath(3, 5) << "\n";
    
    std::cout << "LCA(3, 5): " << hld.lca(3, 5) << "\n";
    
    return 0;
}
```

### Complexity

| Operation | Time |
|---|---|
| Build | O(n) |
| Path query | O(log² n) |
| Path update | O(log² n) |
| Subtree query | O(log n) (use Euler Tour + segment tree) |
| LCA | O(log n) |

---

## 57.10 Centroid Decomposition

**Centroid Decomposition** is a divide-and-conquer technique on trees. The **centroid** is a node whose removal splits the tree into components each of size ≤ n/2. Recursively decompose each component.

### Key Property

Any node-to-node path passes through at most O(log n) centroids, enabling efficient path counting.

### When to Use

- Count paths with certain properties (e.g., paths of length k)
- Distance queries between arbitrary nodes
- Problems where divide-and-conquer on trees is natural

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class CentroidDecomp {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<bool> removed;
    std::vector<int> sz;
    
    int getSubtreeSize(int u, int p) {
        sz[u] = 1;
        for (int v : adj[u]) {
            if (v != p && !removed[v]) {
                sz[u] += getSubtreeSize(v, u);
            }
        }
        return sz[u];
    }
    
    int findCentroid(int u, int p, int treeSize) {
        for (int v : adj[u]) {
            if (v != p && !removed[v] && sz[v] > treeSize / 2) {
                return findCentroid(v, u, treeSize);
            }
        }
        return u;
    }
    
    void decompose(int u, int depth = 0) {
        int treeSize = getSubtreeSize(u, -1);
        int centroid = findCentroid(u, -1, treeSize);
        
        removed[centroid] = true;
        
        // Process centroid at this level
        // Example: compute distances from centroid to all nodes in its component
        // Then answer path queries through this centroid
        
        for (int v : adj[centroid]) {
            if (!removed[v]) {
                decompose(v, depth + 1);
            }
        }
    }
    
public:
    CentroidDecomp(int n) : n(n), adj(n), removed(n, false), sz(n) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    void build() {
        decompose(0);
    }
};

int main() {
    //       0
    //      / \
    //     1   2
    //    /|   |
    //   3  4  5
    
    CentroidDecomp cd(6);
    cd.addEdge(0, 1);
    cd.addEdge(0, 2);
    cd.addEdge(1, 3);
    cd.addEdge(1, 4);
    cd.addEdge(2, 5);
    
    cd.build();
    std::cout << "Centroid decomposition built successfully.\n";
    
    return 0;
}
```

---

## 57.11 Tree DP (Comprehensive)

Tree Dynamic Programming is one of the most important techniques for tree problems. The key insight: process the tree bottom-up, combining results from children to compute the answer for each subtree.

### General Approach

1. Root the tree arbitrarily
2. Define `dp[u]` = optimal value for subtree rooted at `u`
3. For each node, combine children's DP values

### Example 1: Maximum Independent Set on Tree

Select a maximum-weight subset of nodes such that no two selected nodes are adjacent.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

struct TreeDP {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<int> val;
    // dp[u][0] = max sum in subtree u, u NOT selected
    // dp[u][1] = max sum in subtree u, u selected
    std::vector<std::array<long long, 2>> dp;
    std::vector<int> chosen; // 1 if node is in the independent set
    
    TreeDP(int n) : n(n), adj(n), val(n), dp(n), chosen(n, 0) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    void dfs(int u, int p) {
        dp[u][0] = 0;
        dp[u][1] = val[u];
        
        for (int v : adj[u]) {
            if (v == p) continue;
            dfs(v, u);
            dp[u][0] += std::max(dp[v][0], dp[v][1]);
            dp[u][1] += dp[v][0]; // If u is selected, children cannot be
        }
    }
    
    void reconstruct(int u, int p, bool parentChosen) {
        if (!parentChosen && dp[u][1] > dp[u][0]) {
            chosen[u] = 1;
        }
        for (int v : adj[u]) {
            if (v != p) {
                reconstruct(v, u, chosen[u]);
            }
        }
    }
    
    long long solve(int root) {
        dfs(root, -1);
        reconstruct(root, -1, false);
        return std::max(dp[root][0], dp[root][1]);
    }
};

int main() {
    //       0(10)
    //      / \
    //    1(5) 2(8)
    //    /|
    //  3(3) 4(7)
    
    TreeDP tree(5);
    tree.addEdge(0, 1);
    tree.addEdge(0, 2);
    tree.addEdge(1, 3);
    tree.addEdge(1, 4);
    tree.val = {10, 5, 8, 3, 7};
    
    long long ans = tree.solve(0);
    std::cout << "Max independent set: " << ans << "\n";
    
    std::cout << "Selected nodes: ";
    for (int i = 0; i < 5; i++) {
        if (tree.chosen[i]) std::cout << i << " ";
    }
    std::cout << "\n";
    
    return 0;
}
```

### Example 2: Tree Diameter (DP Approach)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int diameter = 0;

int dfs(int u, int p, const std::vector<std::vector<int>>& adj) {
    int max1 = 0, max2 = 0; // Two longest paths from u to leaves
    
    for (int v : adj[u]) {
        if (v == p) continue;
        int depth = dfs(v, u, adj) + 1;
        if (depth > max1) {
            max2 = max1;
            max1 = depth;
        } else if (depth > max2) {
            max2 = depth;
        }
    }
    
    diameter = std::max(diameter, max1 + max2);
    return max1;
}

int main() {
    //       0
    //      / \
    //     1   2
    //    /|   |
    //   3  4  5
    //       |
    //       6
    
    int n = 7;
    std::vector<std::vector<int>> adj(n);
    auto addEdge = [&](int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    };
    addEdge(0, 1); addEdge(0, 2);
    addEdge(1, 3); addEdge(1, 4);
    addEdge(2, 5); addEdge(4, 6);
    
    dfs(0, -1, adj);
    std::cout << "Tree diameter: " << diameter << "\n";
    
    return 0;
}
```

### Example 3: Subtree Size Queries

```cpp
#include <iostream>
#include <vector>

void dfs(int u, int p, const std::vector<std::vector<int>>& adj, 
         std::vector<int>& sz) {
    sz[u] = 1;
    for (int v : adj[u]) {
        if (v != p) {
            dfs(v, u, adj, sz);
            sz[u] += sz[v];
        }
    }
}

int main() {
    int n = 6;
    std::vector<std::vector<int>> adj(n);
    adj[0] = {1, 2}; adj[1] = {0, 3, 4}; adj[2] = {0, 5};
    adj[3] = {1}; adj[4] = {1}; adj[5] = {2};
    
    std::vector<int> sz(n);
    dfs(0, -1, adj, sz);
    
    for (int i = 0; i < n; i++) {
        std::cout << "Subtree size of " << i << ": " << sz[i] << "\n";
    }
    
    return 0;
}
```

### Tree DP State Design Principles

| Problem | State | Transition |
|---|---|---|
| Max independent set | `dp[u][selected/not]` | If selected, children must not be |
| Tree diameter | `dp[u]` = longest path from u to leaf | Max of two longest child paths |
| Tree coloring | `dp[u][color]` | Min over valid child colors |
| Subtree sum | `dp[u]` = sum of subtree | `dp[u] = val[u] + Σ dp[v]` |
| Vertex cover | `dp[u][covered/not]` | If not covered, parent must be |
| Dominating set | `dp[u][state]` | Three states: in set, covered by child, covered by parent |

---

## 57.12 Tree Isomorphism (AHU Algorithm)

Two rooted trees are **isomorphic** if one can be relabeled to match the other. The **AHU algorithm** assigns canonical labels (parenthesized strings or tuples) to each subtree.

### Algorithm

1. Root both trees at their centers (1 or 2 nodes)
2. Bottom-up: label each node by the sorted tuple of its children's labels
3. Two trees are isomorphic iff their root labels match

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <string>
#include <map>

std::string canonical(int u, int p, const std::vector<std::vector<int>>& adj) {
    std::vector<std::string> childLabels;
    for (int v : adj[u]) {
        if (v != p) {
            childLabels.push_back(canonical(v, u, adj));
        }
    }
    std::sort(childLabels.begin(), childLabels.end());
    std::string label = "(";
    for (auto& s : childLabels) label += s;
    label += ")";
    return label;
}

// Find center(s) of tree
std::vector<int> findCenter(int n, const std::vector<std::vector<int>>& adj) {
    std::vector<int> degree(n);
    std::vector<int> leaves;
    for (int i = 0; i < n; i++) {
        degree[i] = adj[i].size();
        if (degree[i] <= 1) leaves.push_back(i);
    }
    
    int processed = leaves.size();
    while (processed < n) {
        std::vector<int> newLeaves;
        for (int u : leaves) {
            for (int v : adj[u]) {
                if (--degree[v] == 1) newLeaves.push_back(v);
            }
        }
        leaves = newLeaves;
        processed += leaves.size();
    }
    return leaves;
}

bool areIsomorphic(int n1, const std::vector<std::vector<int>>& adj1,
                   int n2, const std::vector<std::vector<int>>& adj2) {
    if (n1 != n2) return false;
    
    auto centers1 = findCenter(n1, adj1);
    auto centers2 = findCenter(n2, adj2);
    
    // Try all center combinations (at most 2 × 2 = 4)
    for (int c1 : centers1) {
        std::string label1 = canonical(c1, -1, adj1);
        for (int c2 : centers2) {
            std::string label2 = canonical(c2, -1, adj2);
            if (label1 == label2) return true;
        }
    }
    return false;
}

int main() {
    // Tree 1:    0     Tree 2:    0
    //           / \             / \
    //          1   2           1   2
    //         /                 \
    //        3                   3
    
    std::vector<std::vector<int>> adj1(4);
    adj1[0] = {1, 2}; adj1[1] = {0, 3}; adj1[2] = {0}; adj1[3] = {1};
    
    std::vector<std::vector<int>> adj2(4);
    adj2[0] = {1, 2}; adj2[1] = {0}; adj2[2] = {0, 3}; adj2[3] = {2};
    
    std::cout << "Trees are " 
              << (areIsomorphic(4, adj1, 4, adj2) ? "" : "not ")
              << "isomorphic\n";
    
    return 0;
}
```

---

## 57.13 LCA Approaches Comparison

| Method | Preprocessing | Query | Space | Notes |
|---|---|---|---|---|
| Binary Lifting | O(n log n) | O(log n) | O(n log n) | Most versatile |
| Euler Tour + RMQ | O(n log n) | O(log n) | O(n log n) | Classic |
| Euler Tour + Sparse Table | O(n log n) | O(1) | O(n log n) | Static only |
| HLD | O(n) | O(log n) | O(n) | Supports updates |
| Tarjan's Offline | O(n α(n)) | O(α(n)) per query | O(n) | DSU-based |
| ±1 RMQ Reduction | O(n) | O(1) | O(n) | Theoretical |

### Binary Lifting Implementation

```cpp
#include <iostream>
#include <vector>

class LCA {
    int n, LOG;
    std::vector<std::vector<int>> adj;
    std::vector<std::vector<int>> up;
    std::vector<int> depth;
    
    void dfs(int u, int p) {
        up[u][0] = p;
        for (int i = 1; i < LOG; i++) {
            up[u][i] = up[up[u][i-1]][i-1];
        }
        for (int v : adj[u]) {
            if (v != p) {
                depth[v] = depth[u] + 1;
                dfs(v, u);
            }
        }
    }
    
public:
    LCA(int n) : n(n), LOG(0), adj(n), depth(n) {
        int temp = n;
        while (temp > 0) { LOG++; temp /= 2; }
        LOG++;
        up.assign(n, std::vector<int>(LOG));
    }
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    void build(int root) {
        depth[root] = 0;
        dfs(root, root);
    }
    
    int query(int u, int v) {
        if (depth[u] < depth[v]) std::swap(u, v);
        
        // Lift u up to same depth as v
        int diff = depth[u] - depth[v];
        for (int i = 0; i < LOG; i++) {
            if ((diff >> i) & 1) u = up[u][i];
        }
        
        if (u == v) return u;
        
        // Binary lift both until LCA
        for (int i = LOG - 1; i >= 0; i--) {
            if (up[u][i] != up[v][i]) {
                u = up[u][i];
                v = up[v][i];
            }
        }
        
        return up[u][0];
    }
    
    int dist(int u, int v) {
        return depth[u] + depth[v] - 2 * depth[query(u, v)];
    }
};

int main() {
    //       0
    //      / \
    //     1   2
    //    /|   |
    //   3  4  5
    
    LCA lca(6);
    lca.addEdge(0, 1); lca.addEdge(0, 2);
    lca.addEdge(1, 3); lca.addEdge(1, 4);
    lca.addEdge(2, 5);
    
    lca.build(0);
    
    std::cout << "LCA(3, 4) = " << lca.query(3, 4) << "\n"; // 1
    std::cout << "LCA(3, 5) = " << lca.query(3, 5) << "\n"; // 0
    std::cout << "LCA(3, 2) = " << lca.query(3, 2) << "\n"; // 0
    std::cout << "Distance(3, 5) = " << lca.dist(3, 5) << "\n"; // 4
    
    return 0;
}
```

---

## Summary

| Technique | Key Idea | Best For |
|---|---|---|
| Treap | Randomized priorities for balance | BST with split/merge |
| Splay Tree | Splay recently accessed to root | Temporal locality |
| Cartesian Tree | Heap + inorder = array | RMQ reduction |
| B-Tree | Multi-way, disk-friendly | Database indexing |
| Persistent Seg Tree | Copy-on-write versions | Historical queries |
| Euler Tour | Flatten tree to array | Subtree queries |
| HLD | Heavy/light chain decomposition | Path queries |
| Centroid Decomposition | Divide and conquer on trees | Path counting |
| Tree DP | Bottom-up on tree structure | Optimization on trees |
| AHU Algorithm | Canonical labeling | Tree isomorphism |
| Binary Lifting | Jump pointers | LCA, k-th ancestor |
