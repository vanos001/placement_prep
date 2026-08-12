# Chapter 80: Advanced Heaps

## Prerequisites

- Basic heap (binary heap)
- Priority queue operations

## Interview Frequency: ★★

Advanced heap variants offer better amortized complexities for specific operations. They appear in **Google** interviews and competitive programming.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Binomial Heap | ★★ | Medium | Merge in O(log n) |
| Fibonacci Heap | ★ | Hard | Decrease-key in O(1) |
| Pairing Heap | ★★ | Medium | Practical alternative |

---

## 80.1 Binomial Heap

A binomial heap is a collection of binomial trees with distinct orders.

**Key properties**:
- Merge: O(log n)
- Insert: O(1) amortized
- Extract-min: O(log n)
- Decrease-key: O(log n)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

struct BinomialNode {
    int key, degree;
    BinomialNode *child, *sibling, *parent;
    BinomialNode(int k) : key(k), degree(0), child(nullptr), 
                           sibling(nullptr), parent(nullptr) {}
};

class BinomialHeap {
    BinomialNode* head;
    
    BinomialNode* mergeTrees(BinomialNode* t1, BinomialNode* t2) {
        if (t1->key > t2->key) std::swap(t1, t2);
        t2->parent = t1;
        t2->sibling = t1->child;
        t1->child = t2;
        t1->degree++;
        return t1;
    }
    
    BinomialNode* mergeHeaps(BinomialNode* h1, BinomialNode* h2) {
        if (!h1) return h2;
        if (!h2) return h1;
        
        BinomialNode* newHead = nullptr;
        BinomialNode** curr = &newHead;
        
        while (h1 && h2) {
            if (h1->degree <= h2->degree) {
                *curr = h1;
                h1 = h1->sibling;
            } else {
                *curr = h2;
                h2 = h2->sibling;
            }
            curr = &((*curr)->sibling);
        }
        *curr = h1 ? h1 : h2;
        
        // Consolidate trees with same degree
        if (!newHead) return nullptr;
        
        BinomialNode *prev = nullptr, *curr2 = newHead, *next = curr2->sibling;
        while (next) {
            if (curr2->degree != next->degree || 
                (next->sibling && next->sibling->degree == curr2->degree)) {
                prev = curr2;
                curr2 = next;
            } else if (curr2->key <= next->key) {
                curr2->sibling = next->sibling;
                curr2 = mergeTrees(curr2, next);
            } else {
                if (prev) prev->sibling = next;
                else newHead = next;
                next = mergeTrees(next, curr2);
                curr2 = next;
            }
            next = curr2->sibling;
        }
        
        return newHead;
    }
    
public:
    BinomialHeap() : head(nullptr) {}
    
    void insert(int key) {
        BinomialNode* node = new BinomialNode(key);
        head = mergeHeaps(head, node);
    }
    
    int getMin() {
        int minVal = INT_MAX;
        BinomialNode* curr = head;
        while (curr) {
            minVal = std::min(minVal, curr->key);
            curr = curr->sibling;
        }
        return minVal;
    }
    
    void merge(BinomialHeap& other) {
        head = mergeHeaps(head, other.head);
        other.head = nullptr;
    }
};

int main() {
    BinomialHeap h1, h2;
    for (int x : {10, 20, 5, 15}) h1.insert(x);
    for (int x : {3, 8, 12, 25}) h2.insert(x);
    
    std::cout << "H1 min: " << h1.getMin() << "\n";
    std::cout << "H2 min: " << h2.getMin() << "\n";
    
    h1.merge(h2);
    std::cout << "Merged min: " << h1.getMin() << "\n";
    
    return 0;
}
```

---

## 80.2 Fibonacci Heap

Fibonacci heaps achieve optimal amortized complexities for priority queue operations. Used in Dijkstra's algorithm for O(E + V log V) time.

**Key idea**: Lazy structure — insert and merge just add to root list. Consolidation happens only on extract-min.

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <climits>

struct FibNode {
    int key, degree;
    bool marked;
    FibNode *child, *left, *right, *parent;
    FibNode(int k) : key(k), degree(0), marked(false), 
                      child(nullptr), left(this), right(this), parent(nullptr) {}
};

class FibonacciHeap {
    FibNode* minNode;
    int n;
    
    void insertIntoList(FibNode*& list, FibNode* node) {
        if (!list) {
            list = node;
            node->left = node->right = node;
        } else {
            node->right = list->right;
            node->left = list;
            list->right->left = node;
            list->right = node;
        }
    }
    
    void removeFromList(FibNode* node) {
        node->left->right = node->right;
        node->right->left = node->left;
    }
    
    FibNode* mergeLists(FibNode* a, FibNode* b) {
        if (!a) return b;
        if (!b) return a;
        FibNode* aRight = a->right;
        a->right = b->right;
        b->right->left = a;
        b->right = aRight;
        aRight->left = b;
        return a->key < b->key ? a : b;
    }
    
    void link(FibNode* y, FibNode* x) {
        removeFromList(y);
        y->left = y->right = y;
        y->parent = x;
        insertIntoList(x->child, y);
        x->degree++;
        y->marked = false;
    }
    
    void consolidate() {
        int maxDegree = (int)(log2(n) / log2(1.618)) + 2;
        std::vector<FibNode*> A(maxDegree, nullptr);
        
        std::vector<FibNode*> rootNodes;
        FibNode* curr = minNode;
        if (curr) {
            do {
                rootNodes.push_back(curr);
                curr = curr->right;
            } while (curr != minNode);
        }
        
        for (FibNode* w : rootNodes) {
            FibNode* x = w;
            int d = x->degree;
            while (d < (int)A.size() && A[d]) {
                FibNode* y = A[d];
                if (x->key > y->key) std::swap(x, y);
                link(y, x);
                A[d] = nullptr;
                d++;
            }
            if (d < (int)A.size()) A[d] = x;
        }
        
        minNode = nullptr;
        for (FibNode* node : A) {
            if (node) {
                node->left = node->right = node;
                insertIntoList(minNode, node);
                if (!minNode || node->key < minNode->key) minNode = node;
            }
        }
    }
    
public:
    FibonacciHeap() : minNode(nullptr), n(0) {}
    
    void insert(int key) {
        FibNode* node = new FibNode(key);
        minNode = mergeLists(minNode, node);
        if (node->key < minNode->key) minNode = node;
        n++;
    }
    
    int getMin() { return minNode ? minNode->key : INT_MAX; }
    
    int extractMin() {
        FibNode* z = minNode;
        if (!z) return INT_MAX;
        
        // Add children to root list
        if (z->child) {
            FibNode* child = z->child;
            do {
                FibNode* next = child->right;
                child->parent = nullptr;
                insertIntoList(minNode, child);
                child = next;
            } while (child != z->child);
        }
        
        removeFromList(z);
        if (z == z->right) {
            minNode = nullptr;
        } else {
            minNode = z->right;
            consolidate();
        }
        n--;
        int result = z->key;
        delete z;
        return result;
    }
    
    void merge(FibonacciHeap& other) {
        minNode = mergeLists(minNode, other.minNode);
        n += other.n;
        other.minNode = nullptr;
        other.n = 0;
    }
    
    int size() { return n; }
};

int main() {
    FibonacciHeap fh;
    for (int x : {10, 3, 7, 1, 15, 5}) fh.insert(x);
    
    std::cout << "Min: " << fh.getMin() << "\n"; // 1
    std::cout << "Extract min: " << fh.extractMin() << "\n"; // 1
    std::cout << "Min: " << fh.getMin() << "\n"; // 3
    
    FibonacciHeap fh2;
    for (int x : {2, 8, 4}) fh2.insert(x);
    fh.merge(fh2);
    std::cout << "After merge, min: " << fh.getMin() << "\n"; // 2
    
    return 0;
}
```

---

## 80.3 Pairing Heap

A simpler alternative to Fibonacci heaps with excellent practical performance. The simpler structure makes it faster in practice despite similar or slightly worse theoretical bounds.

**Key operations**: Merge by linking one tree as child of the other. Decrease-key by cutting subtree and merging back.

```cpp
#include <iostream>
#include <climits>
#include <vector>

struct PairNode {
    int key;
    PairNode *child, *sibling, *prev; // prev = left sibling or parent
    PairNode(int k) : key(k), child(nullptr), sibling(nullptr), prev(nullptr) {}
};

class PairingHeap {
    PairNode* root;
    
    PairNode* merge(PairNode* a, PairNode* b) {
        if (!a) return b;
        if (!b) return a;
        if (a->key > b->key) std::swap(a, b);
        // Make b the leftmost child of a
        b->sibling = a->child;
        if (a->child) a->child->prev = b;
        a->child = b;
        b->prev = a;
        return a;
    }
    
    // Two-pass merge (merge pairs, then merge results)
    PairNode* twoPassMerge(PairNode* first) {
        if (!first || !first->sibling) return first;
        
        PairNode *a = first, *b = first->sibling;
        PairNode* rest = b->sibling;
        a->sibling = b->sibling = nullptr;
        a->prev = b->prev = nullptr;
        
        return merge(merge(a, b), twoPassMerge(rest));
    }
    
public:
    PairingHeap() : root(nullptr) {}
    
    void insert(int key) {
        root = merge(root, new PairNode(key));
    }
    
    int getMin() { return root ? root->key : INT_MAX; }
    
    int extractMin() {
        if (!root) return INT_MAX;
        int result = root->key;
        PairNode* old = root;
        root = twoPassMerge(root->child);
        if (root) root->prev = nullptr;
        delete old;
        return result;
    }
    
    // Decrease key: cut subtree and merge back
    void decreaseKey(PairNode* node, int newKey) {
        node->key = newKey;
        if (node == root) return;
        
        // Cut from parent/sibling
        if (node->prev->child == node) {
            node->prev->child = node->sibling;
        } else {
            node->prev->sibling = node->sibling;
        }
        if (node->sibling) node->sibling->prev = node->prev;
        node->sibling = nullptr;
        node->prev = nullptr;
        
        root = merge(root, node);
    }
    
    bool empty() { return root == nullptr; }
};

int main() {
    PairingHeap ph;
    for (int x : {10, 3, 7, 1, 15, 5}) ph.insert(x);
    
    std::cout << "Min: " << ph.getMin() << "\n"; // 1
    std::cout << "Extract min: " << ph.extractMin() << "\n"; // 1
    std::cout << "Min: " << ph.getMin() << "\n"; // 3
    std::cout << "Extract min: " << ph.extractMin() << "\n"; // 3
    std::cout << "Min: " << ph.getMin() << "\n"; // 5
    
    return 0;
}
```

---

## Summary

| Heap | Insert | Extract-Min | Decrease-Key | Merge |
|---|---|---|---|---|
| Binary | O(log n) | O(log n) | O(log n) | O(n) |
| Binomial | O(1) amort | O(log n) | O(log n) | O(log n) |
| Fibonacci | O(1) | O(log n) amort | O(1) amort | O(1) |
| Pairing | O(1) | O(log n) amort | O(log log n)* | O(1) |
