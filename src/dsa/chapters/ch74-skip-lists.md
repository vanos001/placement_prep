# Chapter 74: Skip Lists

## Prerequisites

- Linked lists ([Chapter 12](ch12-linked-lists.md))
- Probability basics ([Chapter 72](ch72-probability.md))
- Binary search trees (Chapter 25)

## Interview Frequency: ★★

Skip Lists are a probabilistic alternative to balanced BSTs. They're used in **Redis**, **LevelDB**, and **Apache Lucene**. **Google** and **Amazon** occasionally ask about skip lists to test understanding of probabilistic data structures.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Skip List structure | ★★ | Medium | Multi-level linked list |
| Skip List operations | ★★ | Medium | Search, insert, delete |
| Expected height | ★ | Hard | Probability analysis |
| Comparison with BST | ★★ | Medium | When to use which |

---

## 74.1 Definition

A **Skip List** is a probabilistic data structure that allows O(log n) search, insertion, and deletion in a sorted linked list. It achieves this by maintaining multiple layers of linked lists, where each layer acts as an "express lane" for the layer below.

Formally, a skip list is a sequence of sorted linked lists L0, L1, ..., Lh where:
- L0 contains all n elements
- Li+1 contains a random subset of elements from Li
- Each element is included in Li+1 with probability p (typically p = 1/2)
- h is the maximum level, typically O(log n)

---

## 74.2 Motivation

### The Problem with Sorted Linked Lists

A sorted linked list supports O(1) insertion (once you have the position) but O(n) search because you can't binary-search a linked list — there's no random access.

### The Problem with Balanced BSTs

AVL trees and Red-Black trees guarantee O(log n) operations but are complex to implement, especially with concurrent access. Lock-free BST implementations are notoriously difficult.

### The Skip List Solution

Skip lists add "express lanes" above the base linked list. By randomly promoting some nodes to higher levels, we get expected O(log n) search with:
- **Simple implementation** — much easier than balanced BSTs
- **Natural concurrency** — lock-free implementations are straightforward
- **Probabilistic balance** — no rotations or rebalancing needed

---

## 74.3 Intuition

Think of a skip list like a book's index:

1. **Level 0** (base): Every entry — like reading every page
2. **Level 1**: Every other entry — like chapter headings
3. **Level 2**: Every 4th entry — like section headings
4. **Level k**: Every 2^k-th entry — like part divisions

To find a word, you first scan the part headings, then section headings within that part, then chapter headings within that section, then scan page by page. This is exactly how skip list search works!

**Key insight**: Instead of a perfectly balanced structure (hard to maintain), we use random coin flips to decide how many levels each node gets. On average, this gives us the same logarithmic behavior.

### Visual Example

```
HEAD ──────────────────────────→ 5 ───────────→ NULL
HEAD ───────────→ 3 ───────────→ 5 ──→ 7 ─────→ NULL
HEAD ──→ 1 ─────→ 3 ──→ 4 ─────→ 5 ──→ 7 ──→ 9 → NULL
```

- Level 2: 5 (promoted twice — coin landed heads twice)
- Level 1: 3, 5, 7 (promoted at least once)
- Level 0: 1, 3, 4, 5, 7, 9 (all elements)

---

## 74.4 Formal Explanation

### Node Structure

Each node contains:
- A value
- An array of forward pointers: `forward[0..level]`
- `forward[i]` points to the next node at level i

### Random Level Generation

Each node is assigned a random level k where:
- P(level ≥ 1) = p
- P(level ≥ 2) = p²
- P(level ≥ k) = p^k

With p = 1/2: expected number of pointers per node = 1/(1-p) = 2.

### Expected Height

The expected height of a skip list with n elements:
- E[h] = log_{1/p}(n) + O(1)
- For p = 1/2: E[h] ≈ log₂(n) + 1

### Search Algorithm

```
Search(list, target):
    node ← list.head
    for i ← maxLevel downto 0:
        while node.forward[i] ≠ NULL and node.forward[i].value < target:
            node ← node.forward[i]
    node ← node.forward[0]
    if node ≠ NULL and node.value == target:
        return node
    return NOT_FOUND
```

The search path follows the highest level as far as possible, then drops down. This is identical to binary search in spirit.

---

## 74.5 Step-by-Step Walkthrough

### Inserting into a Skip List

Insert value 6 into the skip list above:

**Step 1: Find position at each level**
- Level 2: Start at HEAD, forward → 5 (5 < 6), forward → NULL. Stop. Update[2] = 5
- Level 1: Start at 5, forward → 7 (7 > 6). Stop. Update[1] = 5
- Level 0: Start at 5, forward → 7 (7 > 6). Stop. Update[0] = 5

**Step 2: Generate random level for new node**
- Coin flip: heads (level 1), heads (level 2), tails → level = 2

**Step 3: Splice in the new node**
- At level 2: 5.forward[2] → 6, 6.forward[2] → NULL (was 5→NULL)
- At level 1: 5.forward[1] → 6, 6.forward[1] → 7 (was 5→7)
- At level 0: 5.forward[0] → 6, 6.forward[0] → 7 (was 5→7)

**Result:**
```
HEAD ──────────────────────────→ 5 ──→ 6 ──────────→ NULL
HEAD ───────────→ 3 ───────────→ 5 ──→ 6 ──→ 7 ───→ NULL
HEAD ──→ 1 ─────→ 3 ──→ 4 ─────→ 5 ──→ 6 ──→ 7 ──→ 9 → NULL
```

### Dry Run: Searching for 4

1. Start at HEAD, level 2: HEAD.forward[2] = 5. 5 > 4, drop to level 1
2. Level 1: HEAD.forward[1] = 3. 3 < 4, move to 3. 3.forward[1] = 5. 5 > 4, drop to level 0
3. Level 0: 3.forward[0] = 4. 4 = 4. **Found!**

Steps taken: 3 (vs 4 in a plain linked list). With larger lists, the difference becomes dramatic.

---

## 74.6 Complexity Analysis

| Operation | Expected | Worst Case | Space |
|---|---|---|---|
| Search | O(log n) | O(n) | O(n) |
| Insert | O(log n) | O(n) | O(n) |
| Delete | O(log n) | O(n) | O(n) |

### Why Expected O(log n)?

**Expected height**: Each level has ~half the nodes of the level below. The probability of a node having k levels is 1/2^k. The expected height is:

E[h] = Σ_{k=1}^{∞} P(level ≥ k) = Σ_{k=1}^{∞} (1/2)^k = 1 + 1 = O(log n)

More precisely, the expected height is log₂(n) + O(1).

**Expected search cost**: At each level, we skip ~half the remaining nodes. The expected number of steps per level is O(1), and there are O(log n) levels.

**Space**: Each node has an expected 2 pointers (1 + 1/2 + 1/4 + ... = 2). Total space = O(n).

### Worst Case

In the worst case (bad luck with random levels), all nodes could be at level 0, degrading to a plain linked list with O(n) search. But this happens with probability O(1/2^n), which is negligible.

---

## 74.7 Complete Implementation

### C++

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <climits>
#include <iomanip>

class SkipList {
    struct Node {
        int val;
        std::vector<Node*> next;
        Node(int v, int level) : val(v), next(level + 1, nullptr) {}
    };
    
    Node* head;
    int maxLevel;
    int currentLevel;
    int size;
    std::mt19937 rng;
    
    int randomLevel() {
        int level = 0;
        while (std::uniform_real_distribution<double>(0.0, 1.0)(rng) < 0.5 
               && level < maxLevel) {
            level++;
        }
        return level;
    }
    
public:
    SkipList(int maxLvl = 32) : maxLevel(maxLvl), currentLevel(0), size(0),
        rng(std::chrono::steady_clock::now().time_since_epoch().count()) {
        head = new Node(INT_MIN, maxLevel);
    }
    
    ~SkipList() {
        Node* curr = head;
        while (curr) {
            Node* next = curr->next[0];
            delete curr;
            curr = next;
        }
    }
    
    bool search(int val) {
        Node* curr = head;
        for (int i = currentLevel; i >= 0; i--) {
            while (curr->next[i] && curr->next[i]->val < val) {
                curr = curr->next[i];
            }
        }
        curr = curr->next[0];
        return curr && curr->val == val;
    }
    
    void insert(int val) {
        std::vector<Node*> update(maxLevel + 1, nullptr);
        Node* curr = head;
        
        for (int i = currentLevel; i >= 0; i--) {
            while (curr->next[i] && curr->next[i]->val < val) {
                curr = curr->next[i];
            }
            update[i] = curr;
        }
        
        int newLevel = randomLevel();
        if (newLevel > currentLevel) {
            for (int i = currentLevel + 1; i <= newLevel; i++) {
                update[i] = head;
            }
            currentLevel = newLevel;
        }
        
        Node* newNode = new Node(val, newLevel);
        for (int i = 0; i <= newLevel; i++) {
            newNode->next[i] = update[i]->next[i];
            update[i]->next[i] = newNode;
        }
        size++;
    }
    
    bool erase(int val) {
        std::vector<Node*> update(maxLevel + 1, nullptr);
        Node* curr = head;
        
        for (int i = currentLevel; i >= 0; i--) {
            while (curr->next[i] && curr->next[i]->val < val) {
                curr = curr->next[i];
            }
            update[i] = curr;
        }
        
        curr = curr->next[0];
        if (!curr || curr->val != val) return false;
        
        for (int i = 0; i <= currentLevel; i++) {
            if (update[i]->next[i] != curr) break;
            update[i]->next[i] = curr->next[i];
        }
        
        while (currentLevel > 0 && !head->next[currentLevel]) {
            currentLevel--;
        }
        
        delete curr;
        size--;
        return true;
    }
    
    void print() {
        for (int i = currentLevel; i >= 0; i--) {
            std::cout << "Level " << i << ": ";
            Node* curr = head->next[i];
            while (curr) {
                std::cout << curr->val << " ";
                curr = curr->next[i];
            }
            std::cout << "\n";
        }
    }
    
    int getSize() const { return size; }
};

int main() {
    SkipList sl;
    
    for (int x : {3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5}) {
        sl.insert(x);
    }
    
    std::cout << "Skip List structure:\n";
    sl.print();
    
    std::cout << "\nSearch results:\n";
    for (int x : {1, 3, 5, 7, 9}) {
        std::cout << "  Search " << x << ": " 
                  << (sl.search(x) ? "found" : "not found") << "\n";
    }
    
    sl.erase(3);
    std::cout << "\nAfter erasing 3:\n";
    std::cout << "  Search 3: " << (sl.search(3) ? "found" : "not found") << "\n";
    
    return 0;
}
```

### Python

```python
import random

class Node:
    def __init__(self, val, level):
        self.val = val
        self.next = [None] * (level + 1)

class SkipList:
    def __init__(self, max_level=32, p=0.5):
        self.max_level = max_level
        self.p = p
        self.header = Node(float('-inf'), max_level)
        self.level = 0
        self.size = 0
    
    def random_level(self):
        lvl = 0
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl
    
    def search(self, val):
        curr = self.header
        for i in range(self.level, -1, -1):
            while curr.next[i] and curr.next[i].val < val:
                curr = curr.next[i]
        curr = curr.next[0]
        return curr is not None and curr.val == val
    
    def insert(self, val):
        update = [None] * (self.max_level + 1)
        curr = self.header
        
        for i in range(self.level, -1, -1):
            while curr.next[i] and curr.next[i].val < val:
                curr = curr.next[i]
            update[i] = curr
        
        new_level = self.random_level()
        if new_level > self.level:
            for i in range(self.level + 1, new_level + 1):
                update[i] = self.header
            self.level = new_level
        
        new_node = Node(val, new_level)
        for i in range(new_level + 1):
            new_node.next[i] = update[i].next[i]
            update[i].next[i] = new_node
        self.size += 1
    
    def erase(self, val):
        update = [None] * (self.max_level + 1)
        curr = self.header
        
        for i in range(self.level, -1, -1):
            while curr.next[i] and curr.next[i].val < val:
                curr = curr.next[i]
            update[i] = curr
        
        curr = curr.next[0]
        if curr is None or curr.val != val:
            return False
        
        for i in range(self.level + 1):
            if update[i].next[i] != curr:
                break
            update[i].next[i] = curr.next[i]
        
        while self.level > 0 and self.header.next[self.level] is None:
            self.level -= 1
        
        self.size -= 1
        return True
    
    def display(self):
        for i in range(self.level, -1, -1):
            curr = self.header.next[i]
            vals = []
            while curr:
                vals.append(str(curr.val))
                curr = curr.next[i]
            print(f"Level {i}: {' -> '.join(vals)}")


if __name__ == "__main__":
    sl = SkipList()
    for x in [3, 6, 7, 9, 12, 19, 17, 26, 21, 25]:
        sl.insert(x)
    
    print("Skip List:")
    sl.display()
    
    print(f"\nSearch 19: {sl.search(19)}")
    print(f"Search 15: {sl.search(15)}")
    
    sl.erase(19)
    print(f"\nAfter erasing 19:")
    print(f"Search 19: {sl.search(19)}")
    sl.display()
```

### Java

```java
import java.util.Random;

public class SkipList {
    private static class Node {
        int val;
        Node[] next;
        Node(int val, int level) {
            this.val = val;
            this.next = new Node[level + 1];
        }
    }
    
    private Node header;
    private int maxLevel;
    private int currentLevel;
    private int size;
    private Random rng;
    
    public SkipList(int maxLevel) {
        this.maxLevel = maxLevel;
        this.currentLevel = 0;
        this.size = 0;
        this.rng = new Random();
        this.header = new Node(Integer.MIN_VALUE, maxLevel);
    }
    
    public SkipList() { this(32); }
    
    private int randomLevel() {
        int level = 0;
        while (rng.nextDouble() < 0.5 && level < maxLevel) {
            level++;
        }
        return level;
    }
    
    public boolean search(int val) {
        Node curr = header;
        for (int i = currentLevel; i >= 0; i--) {
            while (curr.next[i] != null && curr.next[i].val < val) {
                curr = curr.next[i];
            }
        }
        curr = curr.next[0];
        return curr != null && curr.val == val;
    }
    
    public void insert(int val) {
        Node[] update = new Node[maxLevel + 1];
        Node curr = header;
        
        for (int i = currentLevel; i >= 0; i--) {
            while (curr.next[i] != null && curr.next[i].val < val) {
                curr = curr.next[i];
            }
            update[i] = curr;
        }
        
        int newLevel = randomLevel();
        if (newLevel > currentLevel) {
            for (int i = currentLevel + 1; i <= newLevel; i++) {
                update[i] = header;
            }
            currentLevel = newLevel;
        }
        
        Node newNode = new Node(val, newLevel);
        for (int i = 0; i <= newLevel; i++) {
            newNode.next[i] = update[i].next[i];
            update[i].next[i] = newNode;
        }
        size++;
    }
    
    public boolean erase(int val) {
        Node[] update = new Node[maxLevel + 1];
        Node curr = header;
        
        for (int i = currentLevel; i >= 0; i--) {
            while (curr.next[i] != null && curr.next[i].val < val) {
                curr = curr.next[i];
            }
            update[i] = curr;
        }
        
        curr = curr.next[0];
        if (curr == null || curr.val != val) return false;
        
        for (int i = 0; i <= currentLevel; i++) {
            if (update[i].next[i] != curr) break;
            update[i].next[i] = curr.next[i];
        }
        
        while (currentLevel > 0 && header.next[currentLevel] == null) {
            currentLevel--;
        }
        
        size--;
        return true;
    }
    
    public void print() {
        for (int i = currentLevel; i >= 0; i--) {
            System.out.print("Level " + i + ": ");
            Node curr = header.next[i];
            while (curr != null) {
                System.out.print(curr.val + " ");
                curr = curr.next[i];
            }
            System.out.println();
        }
    }
    
    public static void main(String[] args) {
        SkipList sl = new SkipList();
        int[] values = {3, 6, 7, 9, 12, 19, 17, 26, 21, 25};
        for (int v : values) sl.insert(v);
        
        System.out.println("Skip List:");
        sl.print();
        
        System.out.println("\nSearch 19: " + sl.search(19));
        System.out.println("Search 15: " + sl.search(15));
        
        sl.erase(19);
        System.out.println("\nAfter erasing 19:");
        System.out.println("Search 19: " + sl.search(19));
        sl.print();
    }
}
```

---

## 74.8 Skip List vs Balanced BST

| Aspect | Skip List | AVL/Red-Black |
|---|---|---|
| Balance | Probabilistic | Deterministic |
| Implementation | Simple (~100 lines) | Complex (~500 lines) |
| Concurrent access | Easy (lock-free) | Hard (rotations need locks) |
| Space | O(n) expected | O(n) |
| Cache behavior | Poor (pointer chasing) | Better (array-based variants) |
| Range queries | Easy (follow level 0) | Need successor pointer |
| Deletion | Simple | Complex (rebalancing) |
| Practical performance | Good (cache-unfriendly) | Good (cache-friendly) |

### When to Use Skip Lists

- **Concurrent data structures** — lock-free skip lists are practical (Java's ConcurrentSkipListMap)
- **Simple implementation needed** — much easier than balanced BSTs
- **Range queries** — naturally supported by following level 0
- **External storage** — works well with disk-based structures

### When to Use Balanced BSTs

- **Single-threaded** — slightly better constant factors
- **Cache-sensitive** — array-based BSTs have better locality
- **Deterministic guarantees needed** — worst-case O(log n) guaranteed

---

## 74.9 Real-World Applications

| System | Usage | Why Skip List? |
|---|---|---|
| Redis | Sorted sets (with modifications) | Simple, concurrent-friendly |
| LevelDB/RocksDB | Memtable implementation | Fast inserts, concurrent reads |
| Apache Lucene | Term dictionary | Efficient range queries |
| ConcurrentSkipListMap (Java) | Thread-safe sorted map | Lock-free concurrency |
| HBase | Memstore | Concurrent read/write |

---

## 74.10 Variants

### Deterministic Skip List
Uses a fixed promotion scheme instead of randomization. Guarantees O(log n) worst case but loses the simplicity advantage.

### Skip Graph
Extends skip lists to distributed settings. Each node participates in multiple levels with consistent hashing, enabling O(log n) search in a distributed network.

### Indexable Skip List
Adds a "span" to each forward pointer (number of base-level elements it skips). Supports:
- `get(index)` — find the k-th element in O(log n)
- `rank(val)` — find the position of val in O(log n)

---

## 74.11 Exercises

1. **Implement an indexable skip list** that supports `get(index)` and `rank(val)` operations in O(log n) expected time.

2. **Compare skip list and balanced BST performance** empirically. Insert n random integers, then search for m random integers. Measure and plot the time for n = 10^3, 10^4, 10^5, 10^6.

3. **Prove that the expected number of pointers in a skip list is 2n.** Hint: each node has an expected 1/(1-p) pointers when the promotion probability is p.

4. **Implement a skip list with p = 1/4** instead of 1/2. How does this affect the expected height and the number of pointers? Is it better or worse in practice?

5. **Design a lock-free skip list insert.** The key insight is that you can insert a node by first setting its forward pointers, then CAS-ing the predecessor's forward pointer. What about deletion?

6. **Implement a skip list that supports duplicate values.** How do you handle multiple elements with the same key? What changes in search, insert, and delete?

7. **Prove the expected search time is O(log n).** Use the fact that the search path can be reversed: starting from the target, count how many times we move left vs. going down a level.

---

## 74.12 Interview Questions

1. **What is a skip list and why would you use one over a balanced BST?**
   - Probabilistic alternative to balanced BSTs
   - Simpler implementation, natural concurrency
   - Expected O(log n) vs guaranteed O(log n)

2. **How does skip list search work? Walk through searching for 15 in a given skip list.**
   - Start at highest level, move right while next value < target
   - Drop down a level when can't move right
   - Continue until found or reach level 0 and miss

3. **What is the expected height of a skip list with n elements?**
   - log_{1/p}(n) + O(1) ≈ log₂(n) for p = 1/2
   - Each level halves the number of nodes

4. **How do you handle concurrent access in skip lists?**
   - Lock-free using CAS on forward pointers
   - Insert: set new node's pointers first, then CAS predecessor
   - Much simpler than concurrent BSTs (no rotations)

5. **Can a skip list degrade to O(n)? How likely is this?**
   - Yes, if all nodes end up at level 0
   - Probability: (1/2)^n — negligible for practical n
   - Can cap max level to bound worst case

6. **How would you implement range queries in a skip list?**
   - Search for lower bound, then follow level 0 pointers
   - Returns all elements in range in O(log n + k) where k is result size
   - Natural advantage over BSTs

7. **How does Redis use skip lists?**
   - Sorted sets use a modified skip list
   - Each node stores score and member
   - Allows O(log N) insert, delete, rank, and range operations

---

## Cross-References

- **Foundations**: [Linked Lists](ch12-linked-lists.md), Hashing
- **Probability**: [Probability and Expected Value](ch72-probability.md)
- **Related structures**: Balanced BSTs, Red-Black Trees
- **Applications**: [Probabilistic Data Structures](ch79-probabilistic-ds.md)
- **Concurrency**: Lock-free data structures, CAS operations

---

## Summary

| Property | Value |
|---|---|
| Search | O(log n) expected, O(n) worst |
| Insert | O(log n) expected, O(n) worst |
| Delete | O(log n) expected, O(n) worst |
| Space | O(n) expected |
| Best for | Concurrent systems, simple implementation |
| Key insight | Random promotion gives probabilistic balance |
