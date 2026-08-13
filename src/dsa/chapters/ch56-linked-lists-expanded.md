# Expanded Linked Lists



## Prerequisites

- Basic linked list operations (insert, delete, traverse)
- Understanding of pointers and dynamic memory
- Familiarity with time complexity analysis

## Interview Frequency

★★★ — Linked list problems appear in interviews, but these advanced variants (skip lists, XOR linked lists, persistent lists) are less common. They demonstrate deep understanding of data structure design.

## Companies

Google, Meta, Amazon, Microsoft, Bloomberg, Oracle, database companies (skip lists in LevelDB, Redis), systems programming roles (XOR lists for memory-constrained environments).

---

## Overview

Standard linked lists are rarely the optimal choice in practice (arrays and `std::vector` win on cache performance). However, specialized linked list variants solve specific problems elegantly. This chapter covers four such variants.

| Variant | Key Idea | Search | Insert | Space Overhead | Use Case |
|---------|----------|--------|--------|---------------|----------|
| Skip List | Multiple levels of linked lists | O(log n) avg | O(log n) avg | O(n) | Probabilistic alternative to balanced BST |
| XOR Linked List | XOR of prev/next pointers | O(n) | O(1) | Half the pointer overhead | Memory-constrained doubly linked list |
| Persistent List | Immutable with structural sharing | O(log n) | O(log n) | O(log n) per update | Version history, undo systems |
| Copy-on-Write | Lazy copying | O(1) | O(n) worst | Shared until modified | Snapshots, fork operations |

---

## 1. Skip Lists

### What Is a Skip List?

A skip list is a probabilistic data structure that provides O(log n) average-case search, insert, and delete — like a balanced BST but much simpler to implement. It consists of multiple levels of sorted linked lists. The bottom level contains all elements. Each higher level contains a subset of elements, acting as "express lanes."

### Visual Representation

```
Level 3: HEAD ──────────────────────→ 50 ────────────────→ NIL
Level 2: HEAD ─────────→ 20 ────────→ 50 ────────→ 80 ──→ NIL
Level 1: HEAD ──→ 10 ──→ 20 ──→ 30 ──→ 50 ──→ 70 ──→ 80 ──→ NIL
```

Searching for 70: Start at level 3, skip to 50. Drop to level 2, skip to 80 (too far). Drop to level 1, find 70. Only 4 comparisons instead of 6 (linear search).

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <cstdlib>
#include <ctime>
#include <climits>
#include <iomanip>

class SkipList {
    struct Node {
        int val;
        std::vector<Node*> next; // next[i] = pointer at level i
        explicit Node(int v, int levels) : val(v), next(levels, nullptr) {}
    };

    Node* head;
    int max_level;
    int current_level;
    int size_;
    float probability;

    int random_level() const {
        int level = 1;
        while ((float)std::rand() / RAND_MAX < probability && level < max_level)
            ++level;
        return level;
    }

public:
    SkipList(int max_lvl = 16, float p = 0.5f)
        : max_level(max_lvl), current_level(0), size_(0), probability(p) {
        head = new Node(INT_MIN, max_level);
    }

    ~SkipList() {
        Node* curr = head;
        while (curr) {
            Node* next = curr->next[0];
            delete curr;
            curr = next;
        }
    }

    // Search for a value
    bool search(int target) const {
        Node* curr = head;
        for (int i = current_level - 1; i >= 0; --i) {
            while (curr->next[i] && curr->next[i]->val < target)
                curr = curr->next[i];
        }
        curr = curr->next[0];
        return curr && curr->val == target;
    }

    // Insert a value
    void insert(int val) {
        std::vector<Node*> update(max_level, head);
        Node* curr = head;

        // Find position at each level
        for (int i = current_level - 1; i >= 0; --i) {
            while (curr->next[i] && curr->next[i]->val < val)
                curr = curr->next[i];
            update[i] = curr;
        }

        curr = curr->next[0];

        // If val doesn't exist, insert it
        if (!curr || curr->val != val) {
            int new_level = random_level();
            if (new_level > current_level) {
                for (int i = current_level; i < new_level; ++i)
                    update[i] = head;
                current_level = new_level;
            }

            Node* new_node = new Node(val, new_level);
            for (int i = 0; i < new_level; ++i) {
                new_node->next[i] = update[i]->next[i];
                update[i]->next[i] = new_node;
            }
            ++size_;
        }
    }

    // Remove a value
    bool remove(int val) {
        std::vector<Node*> update(max_level, nullptr);
        Node* curr = head;

        for (int i = current_level - 1; i >= 0; --i) {
            while (curr->next[i] && curr->next[i]->val < val)
                curr = curr->next[i];
            update[i] = curr;
        }

        curr = curr->next[0];

        if (curr && curr->val == val) {
            for (int i = 0; i < current_level; ++i) {
                if (update[i]->next[i] != curr) break;
                update[i]->next[i] = curr->next[i];
            }
            delete curr;

            // Reduce current_level if top levels are empty
            while (current_level > 0 && !head->next[current_level - 1])
                --current_level;
            --size_;
            return true;
        }
        return false;
    }

    // Display the skip list
    void display() const {
        std::cout << "Skip List (size=" << size_ << ", levels=" << current_level << "):\n";
        for (int i = current_level - 1; i >= 0; --i) {
            Node* curr = head->next[i];
            std::cout << "Level " << i << ": HEAD";
            while (curr) {
                std::cout << " → " << curr->val;
                curr = curr->next[i];
            }
            std::cout << " → NIL\n";
        }
    }

    int size() const { return size_; }
};

int main() {
    std::srand(42);

    SkipList sl;
    std::vector<int> values = {3, 6, 7, 9, 12, 19, 21, 25, 26, 30};

    for (int v : values) sl.insert(v);
    sl.display();

    std::cout << "\nSearch 19: " << (sl.search(19) ? "FOUND" : "NOT FOUND") << "\n";
    std::cout << "Search 20: " << (sl.search(20) ? "FOUND" : "NOT FOUND") << "\n";

    sl.remove(19);
    std::cout << "\nAfter removing 19:\n";
    std::cout << "Search 19: " << (sl.search(19) ? "FOUND" : "NOT FOUND") << "\n";
    sl.display();
}
```

### Complexity Analysis

| Operation | Average | Worst Case | Notes |
|-----------|---------|------------|-------|
| Search | O(log n) | O(n) | With high probability O(log n) |
| Insert | O(log n) | O(n) | Includes random level generation |
| Delete | O(log n) | O(n) | |
| Space | O(n) | O(n log n) | Expected O(n) |

### Why Skip Lists?

| Aspect | Skip List | Balanced BST (Red-Black) |
|--------|-----------|--------------------------|
| Implementation | Simple | Complex (rotations) |
| Balance | Probabilistic | Guaranteed |
| Range queries | Easy (follow level 0) | Need in-order traversal |
| Concurrency | Easy (lock individual levels) | Hard (rotations affect many nodes) |
| Cache behavior | Moderate | Moderate |
| Determinism | Randomized | Deterministic |

### Interview Application

Skip lists are used in production systems:
- **Redis** uses skip lists for sorted sets
- **LevelDB/RocksDB** uses skip lists for memtables
- **Apache Lucene** uses skip lists for posting lists

**Q: "Why would you use a skip list instead of a balanced BST?"**

Answers:
1. **Simpler implementation** — no rotations, no complex balancing logic
2. **Better concurrency** — you can lock individual levels independently
3. **Easier range queries** — just follow the bottom level
4. **Probabilistic balance is "good enough"** — O(log n) with overwhelming probability

---

## 2. XOR Linked Lists

### What Is It?

An XOR linked list is a doubly linked list that uses only one pointer per node instead of two. Each node stores `XOR(prev, next)` — the XOR of the addresses of the previous and next nodes. This halves the pointer overhead.

### How It Works

Given nodes A ↔ B ↔ C:
- B stores: `addr(A) XOR addr(C)`
- To traverse forward from B: `next = B.xor_ptr XOR addr(A)` → gives `addr(C)`
- To traverse backward from B: `prev = B.xor_ptr XOR addr(C)` → gives `addr(A)`

### Complete Implementation

```cpp
#include <iostream>
#include <cstdint>
#include <vector>

class XORLinkedList {
    struct Node {
        int val;
        Node* xor_ptr; // XOR of prev and next
        Node(int v) : val(v), xor_ptr(nullptr) {}
    };

    Node* head;
    Node* tail;
    int size_;

    // XOR two pointers
    static Node* XOR(Node* a, Node* b) {
        return reinterpret_cast<Node*>(
            reinterpret_cast<uintptr_t>(a) ^ reinterpret_cast<uintptr_t>(b)
        );
    }

public:
    XORLinkedList() : head(nullptr), tail(nullptr), size_(0) {}

    ~XORLinkedList() {
        Node* curr = head;
        Node* prev = nullptr;
        while (curr) {
            Node* next = XOR(prev, curr->xor_ptr);
            delete curr;
            prev = curr;
            curr = next;
        }
    }

    // Push to front
    void push_front(int val) {
        Node* node = new Node(val);
        node->xor_ptr = XOR(nullptr, head); // prev=null, next=head
        if (head) {
            // head's prev was nullptr, now it's node
            head->xor_ptr = XOR(node, XOR(nullptr, head->xor_ptr));
        } else {
            tail = node;
        }
        head = node;
        ++size_;
    }

    // Push to back
    void push_back(int val) {
        Node* node = new Node(val);
        node->xor_ptr = XOR(tail, nullptr); // prev=tail, next=null
        if (tail) {
            // tail's next was nullptr, now it's node
            tail->xor_ptr = XOR(XOR(tail->xor_ptr, nullptr), node);
        } else {
            head = node;
        }
        tail = node;
        ++size_;
    }

    // Traverse forward
    std::vector<int> forward() const {
        std::vector<int> result;
        Node* curr = head;
        Node* prev = nullptr;
        while (curr) {
            result.push_back(curr->val);
            Node* next = XOR(prev, curr->xor_ptr);
            prev = curr;
            curr = next;
        }
        return result;
    }

    // Traverse backward
    std::vector<int> backward() const {
        std::vector<int> result;
        Node* curr = tail;
        Node* next = nullptr;
        while (curr) {
            result.push_back(curr->val);
            Node* prev = XOR(next, curr->xor_ptr);
            next = curr;
            curr = prev;
        }
        return result;
    }

    int size() const { return size_; }

    // Pop from front
    int pop_front() {
        if (!head) throw std::runtime_error("Empty list");
        int val = head->val;
        Node* old_head = head;
        Node* new_head = XOR(nullptr, head->xor_ptr);
        if (new_head) {
            new_head->xor_ptr = XOR(old_head, XOR(nullptr, new_head->xor_ptr));
        } else {
            tail = nullptr;
        }
        head = new_head;
        delete old_head;
        --size_;
        return val;
    }

    // Delete a specific value (first occurrence)
    bool remove(int val) {
        Node* curr = head;
        Node* prev = nullptr;
        while (curr) {
            if (curr->val == val) {
                Node* next = XOR(prev, curr->xor_ptr);
                if (prev) {
                    prev->xor_ptr = XOR(XOR(prev->xor_ptr, curr), next);
                } else {
                    head = next;
                }
                if (next) {
                    next->xor_ptr = XOR(prev, XOR(curr, next->xor_ptr));
                } else {
                    tail = prev;
                }
                delete curr;
                --size_;
                return true;
            }
            Node* next = XOR(prev, curr->xor_ptr);
            prev = curr;
            curr = next;
        }
        return false;
    }
};

int main() {
    XORLinkedList list;

    list.push_back(1);
    list.push_back(2);
    list.push_back(3);
    list.push_back(4);
    list.push_back(5);

    std::cout << "Forward:  ";
    for (int x : list.forward()) std::cout << x << " ";
    std::cout << "\n"; // 1 2 3 4 5

    std::cout << "Backward: ";
    for (int x : list.backward()) std::cout << x << " ";
    std::cout << "\n"; // 5 4 3 2 1

    list.push_front(0);
    std::cout << "After push_front(0): ";
    for (int x : list.forward()) std::cout << x << " ";
    std::cout << "\n"; // 0 1 2 3 4 5

    list.remove(3);
    std::cout << "After remove(3): ";
    for (int x : list.forward()) std::cout << x << " ";
    std::cout << "\n"; // 0 1 2 4 5

    std::cout << "Pop front: " << list.pop_front() << "\n"; // 0
    std::cout << "After pop: ";
    for (int x : list.forward()) std::cout << x << " ";
    std::cout << "\n"; // 1 2 4 5
}
```

### Memory Savings

| Structure | Pointers per Node | For 1M nodes (64-bit) |
|-----------|-------------------|----------------------|
| Doubly Linked List | 2 (prev + next) | 16 MB |
| XOR Linked List | 1 (XOR of prev and next) | 8 MB |

### Limitations

1. **Debugging is hard** — you can't simply print the list by following pointers
2. **Not thread-safe** — XOR is not atomic
3. **Garbage collection incompatible** — GC can't trace XOR pointers
4. **Random access is impossible** — you need a starting point and must traverse

### Interview Application

XOR linked lists demonstrate:
- Bit manipulation creativity
- Understanding of pointer arithmetic
- Memory optimization trade-offs

**Q: "When would you use an XOR linked list in practice?"**

Almost never in modern systems. The memory savings are negligible compared to the debugging difficulty and incompatibility with garbage collectors. However, they appear in:
- Embedded systems with extreme memory constraints
- Interview questions to test pointer manipulation skills

---

## 3. Persistent Lists

### What Is a Persistent Data Structure?

A persistent data structure preserves previous versions of itself when modified. Every "modification" creates a new version while keeping the old one intact.

### Structural Sharing

Instead of copying the entire list for each version, we share unchanged parts between versions.

```
Version 0: A → B → C → D

Version 1 (insert X after B):
          A → B → X → C → D
               ↘
                C → D  (shared with V0)
```

### Implementation

```cpp
#include <iostream>
#include <vector>
#include <memory>

template<typename T>
class PersistentList {
    struct Node {
        T val;
        std::shared_ptr<Node> next;
        Node(T v, std::shared_ptr<Node> n = nullptr) : val(v), next(n) {}
    };

    std::shared_ptr<Node> head;
    int size_;

    explicit PersistentList(std::shared_ptr<Node> h, int s) : head(h), size_(s) {}

public:
    PersistentList() : head(nullptr), size_(0) {}

    // Create new version with element prepended (O(1))
    PersistentList push_front(const T& val) const {
        return PersistentList(std::make_shared<Node>(val, head), size_ + 1);
    }

    // Create new version with first element removed (O(1))
    PersistentList pop_front() const {
        if (!head) throw std::runtime_error("Empty list");
        return PersistentList(head->next, size_ - 1);
    }

    // Access front element
    const T& front() const {
        if (!head) throw std::runtime_error("Empty list");
        return head->val;
    }

    // Create new version with element at index replaced (O(n))
    PersistentList update(int index, const T& val) const {
        if (index < 0 || index >= size_)
            throw std::out_of_range("Index out of range");

        // Copy nodes from head to index, share the rest
        auto new_head = std::make_shared<Node>(head->val);
        auto curr_new = new_head;
        auto curr_old = head->next;

        for (int i = 1; i <= index; ++i) {
            if (i == index) {
                curr_new->next = std::make_shared<Node>(val, curr_old->next);
            } else {
                curr_new->next = std::make_shared<Node>(curr_old->val);
                curr_new = curr_new->next;
                curr_old = curr_old->next;
            }
        }
        return PersistentList(new_head, size_);
    }

    // Convert to vector for display
    std::vector<T> to_vector() const {
        std::vector<T> result;
        auto curr = head;
        while (curr) {
            result.push_back(curr->val);
            curr = curr->next;
        }
        return result;
    }

    int size() const { return size_; }
    bool empty() const { return size_ == 0; }
};

int main() {
    PersistentList<int> v0; // Version 0: empty

    auto v1 = v0.push_front(3);  // Version 0: [], Version 1: [3]
    auto v2 = v1.push_front(2);  // Version 2: [2, 3]
    auto v3 = v2.push_front(1);  // Version 3: [1, 2, 3]

    // All versions still accessible!
    std::cout << "V0: ";
    for (int x : v0.to_vector()) std::cout << x << " ";
    std::cout << "\n"; // empty

    std::cout << "V1: ";
    for (int x : v1.to_vector()) std::cout << x << " ";
    std::cout << "\n"; // 3

    std::cout << "V2: ";
    for (int x : v2.to_vector()) std::cout << x << " ";
    std::cout << "\n"; // 2 3

    std::cout << "V3: ";
    for (int x : v3.to_vector()) std::cout << x << " ";
    std::cout << "\n"; // 1 2 3

    // Modify V2 without affecting V3
    auto v2b = v2.push_front(0); // V2b: [0, 2, 3]
    std::cout << "V2b: ";
    for (int x : v2b.to_vector()) std::cout << x << " ";
    std::cout << "\n"; // 0 2 3

    std::cout << "V3 (unchanged): ";
    for (int x : v3.to_vector()) std::cout << x << " ";
    std::cout << "\n"; // 1 2 3

    // Update at index
    auto v3b = v3.update(1, 99); // Replace element at index 1
    std::cout << "V3b (index 1 → 99): ";
    for (int x : v3b.to_vector()) std::cout << x << " ";
    std::cout << "\n"; // 1 99 3

    std::cout << "V3 (unchanged): ";
    for (int x : v3.to_vector()) std::cout << x << " ";
    std::cout << "\n"; // 1 2 3
}
```

### Space Analysis

| Operation | Time | New Space Used |
|-----------|------|---------------|
| `push_front` | O(1) | O(1) — one new node |
| `pop_front` | O(1) | O(0) — reuse existing |
| `update(i)` | O(i) | O(i) — copy nodes 0..i |

After *m* operations on a list of size *n*, total space is O(n + m) — each operation creates at most O(n) new nodes, but shared nodes are counted once.

### Interview Application

Persistent lists are useful for:
- **Undo systems:** Each version is a snapshot; undo reverts to a previous version
- **Functional programming:** Immutable data structures are fundamental
- **Version control:** Git-like systems use structural sharing
- **Concurrent access:** Immutable structures are inherently thread-safe

**Q: "How do you implement undo/redo efficiently?"**

Use persistent data structures. Each action creates a new version. Undo is just referencing the previous version. Redo is referencing the next version. No copying needed — structural sharing keeps space O(n + m).

---

## 4. Copy-on-Write (CoW)

### What Is It?

Copy-on-Write is a lazy copying strategy. Instead of immediately copying data when creating a new version, we share the data and only copy when a modification is made.

### Implementation

```cpp
#include <iostream>
#include <memory>
#include <vector>

template<typename T>
class CoWList {
    struct Data {
        std::vector<T> elements;
        Data() = default;
        Data(const std::vector<T>& e) : elements(e) {}
    };

    std::shared_ptr<Data> data;

    // Ensure we have our own copy (not shared)
    void ensure_unique() {
        if (!data) {
            data = std::make_shared<Data>();
            return;
        }
        if (data.use_count() > 1) {
            // Shared — make a copy before modifying
            data = std::make_shared<Data>(data->elements);
        }
    }

public:
    CoWList() : data(std::make_shared<Data>()) {}
    CoWList(std::initializer_list<T> init) : data(std::make_shared<Data>(init)) {}

    // Read access — no copy
    const T& operator[](int idx) const {
        return data->elements[idx];
    }

    int size() const {
        return data ? data->elements.size() : 0;
    }

    // Write access — copy if shared
    void push_back(const T& val) {
        ensure_unique();
        data->elements.push_back(val);
    }

    void pop_back() {
        ensure_unique();
        data->elements.pop_back();
    }

    void set(int idx, const T& val) {
        ensure_unique();
        data->elements[idx] = val;
    }

    // Create a snapshot (share the data)
    CoWList snapshot() const {
        CoWList copy;
        copy.data = data; // Share the same data
        return copy;
    }

    // How many snapshots share this data?
    int reference_count() const {
        return data.use_count();
    }

    void print(const std::string& name = "") const {
        if (!name.empty()) std::cout << name << ": ";
        std::cout << "[";
        for (int i = 0; i < size(); ++i) {
            if (i > 0) std::cout << ", ";
            std::cout << (*this)[i];
        }
        std::cout << "] (refs=" << reference_count() << ")\n";
    }
};

int main() {
    CoWList<int> original = {1, 2, 3, 4, 5};
    original.print("Original"); // [1, 2, 3, 4, 5] (refs=1)

    // Create snapshot — shares data
    auto snap = original.snapshot();
    original.print("Original"); // [1, 2, 3, 4, 5] (refs=2)
    snap.print("Snapshot");     // [1, 2, 3, 4, 5] (refs=2)

    // Modify original — triggers copy
    original.push_back(6);
    original.print("Original"); // [1, 2, 3, 4, 5, 6] (refs=1)
    snap.print("Snapshot");     // [1, 2, 3, 4, 5] (refs=1)

    // Modify snapshot — triggers copy
    snap.set(0, 99);
    snap.print("Snapshot");     // [99, 2, 3, 4, 5] (refs=1)
    original.print("Original"); // [1, 2, 3, 4, 5, 6] (refs=1) — unchanged

    // Multiple snapshots
    auto s1 = original.snapshot();
    auto s2 = original.snapshot();
    auto s3 = original.snapshot();
    original.print("Original"); // refs=4

    s1.push_back(100); // Triggers copy
    original.print("Original"); // refs=3
    s1.print("S1");             // refs=1
}
```

### When Copy-on-Write Shines

| Scenario | Without CoW | With CoW |
|----------|------------|----------|
| Create 100 snapshots of a 1GB dataset | 100 GB memory | 1 GB + small overhead |
| Modify 1 snapshot | No copy needed | 1 copy (1 GB) |
| Read-only snapshots | Same as above | Zero copies |

### Interview Application

CoW is used in:
- **Fork() in Unix:** Parent and child share memory pages; copy only on write
- **String implementations:** `std::string` in some STL implementations uses CoW (though C++11 made this harder due to `[]` returning `const char&`)
- **Databases:** Snapshots for consistent reads
- **File systems:** ZFS, Btrfs use CoW for snapshots

**Q: "How would you implement a system that needs frequent snapshots of large data?"**

Copy-on-Write. Share the underlying data, copy only when modification occurs. This gives O(1) snapshot creation and amortized O(1) reads, with copies only on writes.

---

## Comparison Table

| Feature | Standard DLL | Skip List | XOR List | Persistent | CoW |
|---------|-------------|-----------|----------|------------|-----|
| Search | O(n) | O(log n) avg | O(n) | O(n) | O(n) |
| Insert | O(1) at known pos | O(log n) avg | O(1) at known pos | O(1) push_front | O(1) append |
| Delete | O(1) at known pos | O(log n) avg | O(1) at known pos | O(1) pop_front | O(1) pop_back |
| Space per node | 2 ptrs | ~2 ptrs avg | 1 ptr | Shared nodes | Shared data |
| Thread safety | No | Partial (lock levels) | No | Inherently safe | Copy on write |
| Random access | O(n) | O(log n) avg | O(n) | O(n) | O(1) |
| Version history | No | No | No | Yes | Yes (snapshots) |
| Implementation | Simple | Moderate | Moderate | Moderate | Simple |

---

## Design Decisions

### When NOT to Use Skip Lists

- When you need guaranteed O(log n) → use a balanced BST
- When the dataset is small → simple sorted array + binary search
- When you need cache-friendly search → B-tree or sorted array
- When the problem is simple → don't over-engineer

### When NOT to Use XOR Linked Lists

- Almost always. The memory savings are minimal in modern systems
- When you need debugging capability
- When using garbage collection
- When thread safety matters

### When NOT to Use Persistent Lists

- When you don't need version history → use regular list
- When memory is extremely constrained → each update creates new nodes
- When you need O(1) random access → use persistent array (rope structure)

### When NOT to Use Copy-on-Write

- When writes are very frequent → copying overhead dominates
- When the data is small → copying is cheap, CoW adds complexity
- When you need fine-grained sharing → CoW is all-or-nothing per object

### Trade-offs Summary

| Decision | Gain | Cost |
|----------|------|------|
| Skip List over BST | Simpler code, better concurrency | Probabilistic, slightly more space |
| XOR List over DLL | Half the pointer space | Debugging nightmare, not GC-compatible |
| Persistent over Mutable | Full version history | More space (shared nodes), slower updates |
| CoW over Eager Copy | Cheap snapshots | Write amplification, complexity |

---

## Summary

Advanced linked list variants solve specific problems that standard linked lists don't address well:

1. **Skip Lists** — probabilistic O(log n) operations with simpler code than balanced BSTs. Used in databases and distributed systems.
2. **XOR Linked Lists** — clever memory optimization that halves pointer overhead. Primarily an interview curiosity.
3. **Persistent Lists** — immutable with structural sharing. Essential for functional programming and undo systems.
4. **Copy-on-Write** — lazy copying for efficient snapshots. Used in OS kernels, databases, and file systems.

In interviews, skip lists are the most likely to be asked about (especially at database companies). Persistent lists and CoW demonstrate understanding of advanced design patterns. XOR linked lists test pointer manipulation skills.
