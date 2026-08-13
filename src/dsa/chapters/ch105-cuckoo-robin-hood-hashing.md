# Chapter 105: Cuckoo Hashing and Robin Hood Hashing

## Prerequisites
- Hash tables ([Chapter 101](ch101-rope-gap-buffer.md))
- Hash functions ([Chapter 102](ch102-wavelet-trees.md))
- Amortized analysis

## Interview Frequency: ★

Advanced hashing techniques. Show deep understanding of hash table internals. Rarely asked directly, but knowing these demonstrates mastery of data structures.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Cuckoo hashing | ★ | Medium | Worst-case O(1) lookup |
| Robin Hood hashing | ★ | Medium | Variance reduction |

---

## 105.1 Definition and Motivation

### The Problem with Standard Hash Tables

Standard open-addressing hash tables suffer from:
- **Clustering**: Elements cluster together, increasing probe lengths
- **Worst-case O(n)**: If all elements hash to the same bucket
- **Unpredictable performance**: Probe lengths vary wildly

### What These Techniques Solve

| Technique | Key Advantage | Tradeoff |
|---|---|---|
| **Cuckoo Hashing** | Worst-case O(1) lookup | More complex insertion |
| **Robin Hood Hashing** | Low variance in probe lengths | Slightly slower on average |

---

## 105.2 Cuckoo Hashing

### The Idea

Named after the cuckoo bird (which pushes other eggs out of the nest), cuckoo hashing uses **two hash functions** and **two tables**. When a collision occurs, the existing element is **evicted** to its alternate location.

### How It Works

1. **Insert(key)**:
   - Compute `h1(key)` and `h2(key)`
   - If `table1[h1(key)]` is empty, place key there
   - Otherwise, evict the existing key to its alternate location
   - Repeat until an empty slot is found or a cycle is detected (rehash needed)

2. **Search(key)**: Check only `table1[h1(key)]` and `table2[h2(key)]` → **O(1) worst case!**

3. **Delete(key)**: Mark the slot as empty → **O(1)**

### Step-by-Step Walkthrough

Insert keys: 10, 20, 30, 40, 50

**Step 1**: Insert 10
- h1(10) = 3, table1[3] is empty → place 10 at table1[3]

**Step 2**: Insert 20
- h1(20) = 7, table1[7] is empty → place 20 at table1[7]

**Step 3**: Insert 30
- h1(30) = 3, table1[3] has 10 → evict 10
- h2(10) = 5, table2[5] is empty → place 10 at table2[5]
- Place 30 at table1[3]

**Step 4**: Insert 40
- h1(40) = 7, table1[7] has 20 → evict 20
- h2(20) = 2, table2[2] is empty → place 20 at table2[2]
- Place 40 at table1[7]

**Step 5**: Insert 50
- h1(50) = 3, table1[3] has 30 → evict 30
- h2(30) = 8, table2[8] is empty → place 30 at table2[8]
- Place 50 at table1[3]

Final state:
```
table1: [_, _, _, 50, _, _, _, 40, _, _]
table2: [_, _, 20, _, _, 10, _, _, 30, _]
```

### Code

**C++**

```cpp
#include <iostream>
#include <vector>
#include <functional>
#include <random>

class CuckooHash {
    std::vector<int> table1, table2;
    int size;
    int count;
    
    // Simple hash functions (in practice, use better ones)
    int h1(int key) const { return ((key * 2654435761u) >> 16) % size; }
    int h2(int key) const { return ((key * 2246822519u) >> 16) % size; }
    
    void rehash() {
        int oldSize = size;
        std::vector<int> old1 = table1, old2 = table2;
        size *= 2;
        table1.assign(size, -1);
        table2.assign(size, -1);
        count = 0;
        for (int x : old1) if (x != -1) insert(x);
        for (int x : old2) if (x != -1) insert(x);
    }
    
public:
    CuckooHash(int n) : size(n * 2), count(0), table1(n * 2, -1), table2(n * 2, -1) {}
    
    bool insert(int key) {
        if (search(key)) return true;
        
        for (int i = 0; i < size; i++) {
            int idx1 = h1(key);
            if (table1[idx1] == -1) { table1[idx1] = key; count++; return true; }
            std::swap(key, table1[idx1]);
            
            int idx2 = h2(key);
            if (table2[idx2] == -1) { table2[idx2] = key; count++; return true; }
            std::swap(key, table2[idx2]);
        }
        
        rehash();
        return insert(key);
    }
    
    bool search(int key) const {
        int idx1 = h1(key);
        int idx2 = h2(key);
        return table1[idx1] == key || table2[idx2] == key;
    }
    
    bool remove(int key) {
        int idx1 = h1(key);
        if (table1[idx1] == key) { table1[idx1] = -1; count--; return true; }
        int idx2 = h2(key);
        if (table2[idx2] == key) { table2[idx2] = -1; count--; return true; }
        return false;
    }
    
    int size_used() const { return count; }
};

int main() {
    CuckooHash ch(10);
    for (int x : {10, 20, 30, 40, 50}) {
        ch.insert(x);
        std::cout << "Inserted " << x << "\n";
    }
    
    for (int x : {20, 35, 50})
        std::cout << "Search " << x << ": " << (ch.search(x) ? "found" : "not found") << "\n";
    
    ch.remove(20);
    std::cout << "After removing 20, search 20: " << (ch.search(20) ? "found" : "not found") << "\n";
    
    return 0;
}
```

**Python**

```python
class CuckooHash:
    def __init__(self, capacity=16):
        self.size = capacity
        self.table1 = [None] * self.size
        self.table2 = [None] * self.size
        self.count = 0
    
    def _h1(self, key):
        return ((key * 2654435761) >> 16) % self.size
    
    def _h2(self, key):
        return ((key * 2246822519) >> 16) % self.size
    
    def _rehash(self):
        old1, old2 = self.table1, self.table2
        self.size *= 2
        self.table1 = [None] * self.size
        self.table2 = [None] * self.size
        self.count = 0
        for x in old1:
            if x is not None:
                self.insert(x)
        for x in old2:
            if x is not None:
                self.insert(x)
    
    def insert(self, key):
        if self.search(key):
            return
        
        current = key
        for _ in range(self.size):
            idx1 = self._h1(current)
            if self.table1[idx1] is None:
                self.table1[idx1] = current
                self.count += 1
                return
            current, self.table1[idx1] = self.table1[idx1], current
            
            idx2 = self._h2(current)
            if self.table2[idx2] is None:
                self.table2[idx2] = current
                self.count += 1
                return
            current, self.table2[idx2] = self.table2[idx2], current
        
        self._rehash()
        self.insert(current)
    
    def search(self, key):
        return (self.table1[self._h1(key)] == key or 
                self.table2[self._h2(key)] == key)
    
    def remove(self, key):
        idx1 = self._h1(key)
        if self.table1[idx1] == key:
            self.table1[idx1] = None
            self.count -= 1
            return True
        idx2 = self._h2(key)
        if self.table2[idx2] == key:
            self.table2[idx2] = None
            self.count -= 1
            return True
        return False

ch = CuckooHash()
for x in [10, 20, 30, 40, 50]:
    ch.insert(x)
    print(f"Inserted {x}")

for x in [20, 35]:
    print(f"Search {x}: {'found' if ch.search(x) else 'not found'}")
```

**Java**

```java
public class CuckooHash {
    private int[] table1, table2;
    private int size, count;
    
    public CuckooHash(int capacity) {
        size = capacity * 2;
        table1 = new int[size];
        table2 = new int[size];
        java.util.Arrays.fill(table1, -1);
        java.util.Arrays.fill(table2, -1);
        count = 0;
    }
    
    private int h1(int key) { return ((key * 2654435761) >>> 16) % size; }
    private int h2(int key) { return ((key * 2246822519) >>> 16) % size; }
    
    public boolean insert(int key) {
        if (search(key)) return true;
        
        for (int i = 0; i < size; i++) {
            int idx1 = h1(key);
            if (table1[idx1] == -1) { table1[idx1] = key; count++; return true; }
            int tmp = table1[idx1]; table1[idx1] = key; key = tmp;
            
            int idx2 = h2(key);
            if (table2[idx2] == -1) { table2[idx2] = key; count++; return true; }
            tmp = table2[idx2]; table2[idx2] = key; key = tmp;
        }
        
        rehash();
        return insert(key);
    }
    
    public boolean search(int key) {
        return table1[h1(key)] == key || table2[h2(key)] == key;
    }
    
    public boolean remove(int key) {
        if (table1[h1(key)] == key) { table1[h1(key)] = -1; count--; return true; }
        if (table2[h2(key)] == key) { table2[h2(key)] = -1; count--; return true; }
        return false;
    }
    
    private void rehash() { /* double size and reinsert all */ }
    
    public static void main(String[] args) {
        CuckooHash ch = new CuckooHash(10);
        for (int x : new int[]{10, 20, 30, 40, 50}) ch.insert(x);
        System.out.println("Search 20: " + ch.search(20));  // true
        System.out.println("Search 35: " + ch.search(35));  // false
    }
}
```

---

## 105.3 Robin Hood Hashing

### The Idea

In standard open addressing, some elements travel far from their ideal position while others stay close. **Robin Hood hashing** reduces this inequality: when inserting, if the new element has traveled **farther** from its ideal position than the existing element, **swap them**.

"Steal from the rich (close to ideal) and give to the poor (far from ideal)."

### Key Insight

By equalizing probe lengths, the **maximum probe length** becomes O(log n) with high probability, instead of O(n) for standard hashing.

### How It Works

**Insert(key)**:
1. Compute ideal position `h(key)`
2. Probe linearly from `h(key)`
3. At each slot:
   - If empty: place key
   - If existing element has **shorter** probe distance: swap and continue inserting the displaced element
   - Otherwise: continue probing

**Search(key)**:
1. Start at `h(key)` and probe linearly
2. If we find key: return it
3. If the current slot's probe distance is **less than** our probe distance: key doesn't exist (it would have been swapped earlier)
4. If we reach an empty slot: key doesn't exist

### Code

**C++**

```cpp
#include <iostream>
#include <vector>
#include <optional>

class RobinHoodHash {
    struct Entry {
        int key;
        int probe_dist;  // Distance from ideal position
        bool occupied;
        Entry() : key(0), probe_dist(0), occupied(false) {}
    };
    
    std::vector<Entry> table;
    int size;
    int count;
    
    int hash(int key) const { return ((key * 2654435761u) >> 16) % size; }
    
    void rehash() {
        std::vector<Entry> old = table;
        size *= 2;
        table.assign(size, Entry());
        count = 0;
        for (auto& e : old)
            if (e.occupied) insert(e.key);
    }
    
public:
    RobinHoodHash(int capacity = 16) : size(capacity), count(0), table(capacity) {}
    
    void insert(int key) {
        if (count * 2 >= size) rehash();
        
        int pos = hash(key);
        int dist = 0;
        Entry incoming{key, dist, true};
        
        while (true) {
            if (!table[pos].occupied) {
                table[pos] = incoming;
                count++;
                return;
            }
            
            // Robin Hood: swap if incoming has traveled farther
            if (incoming.probe_dist > table[pos].probe_dist) {
                std::swap(incoming, table[pos]);
            }
            
            if (table[pos].key == key) return; // Already exists
            
            pos = (pos + 1) % size;
            incoming.probe_dist++;
        }
    }
    
    bool search(int key) const {
        int pos = hash(key);
        int dist = 0;
        
        while (true) {
            if (!table[pos].occupied) return false;
            if (dist > table[pos].probe_dist) return false; // Would have been swapped
            if (table[pos].key == key) return true;
            pos = (pos + 1) % size;
            dist++;
        }
    }
    
    void remove(int key) {
        int pos = hash(key);
        int dist = 0;
        
        while (true) {
            if (!table[pos].occupied) return;
            if (dist > table[pos].probe_dist) return;
            if (table[pos].key == key) {
                // Shift subsequent elements back
                table[pos].occupied = false;
                count--;
                int next = (pos + 1) % size;
                while (table[next].occupied && table[next].probe_dist > 0) {
                    table[pos] = table[next];
                    table[pos].probe_dist--;
                    table[next].occupied = false;
                    pos = next;
                    next = (next + 1) % size;
                }
                return;
            }
            pos = (pos + 1) % size;
            dist++;
        }
    }
    
    double avg_probe_length() const {
        int total = 0;
        for (auto& e : table)
            if (e.occupied) total += e.probe_dist;
        return count > 0 ? (double)total / count : 0;
    }
};

int main() {
    RobinHoodHash rh;
    for (int x : {10, 20, 30, 40, 50, 60, 70}) {
        rh.insert(x);
        std::cout << "Inserted " << x << "\n";
    }
    
    for (int x : {20, 35, 60})
        std::cout << "Search " << x << ": " << (rh.search(x) ? "found" : "not found") << "\n";
    
    std::cout << "Average probe length: " << rh.avg_probe_length() << "\n";
    
    return 0;
}
```

**Python**

```python
class RobinHoodHash:
    def __init__(self, capacity=16):
        self.size = capacity
        self.table = [None] * self.size  # (key, probe_dist) or None
        self.count = 0
    
    def _hash(self, key):
        return ((key * 2654435761) >> 16) % self.size
    
    def _rehash(self):
        old = self.table
        self.size *= 2
        self.table = [None] * self.size
        self.count = 0
        for entry in old:
            if entry is not None:
                self.insert(entry[0])
    
    def insert(self, key):
        if self.count * 2 >= self.size:
            self._rehash()
        
        pos = self._hash(key)
        dist = 0
        incoming = (key, dist)
        
        while True:
            if self.table[pos] is None:
                self.table[pos] = incoming
                self.count += 1
                return
            
            # Robin Hood: swap if incoming has traveled farther
            if incoming[1] > self.table[pos][1]:
                incoming, self.table[pos] = self.table[pos], incoming
            
            if self.table[pos][0] == key:
                return  # Already exists
            
            pos = (pos + 1) % self.size
            incoming = (incoming[0], incoming[1] + 1)
    
    def search(self, key):
        pos = self._hash(key)
        dist = 0
        
        while True:
            if self.table[pos] is None:
                return False
            if dist > self.table[pos][1]:
                return False  # Would have been swapped
            if self.table[pos][0] == key:
                return True
            pos = (pos + 1) % self.size
            dist += 1

rh = RobinHoodHash()
for x in [10, 20, 30, 40, 50, 60, 70]:
    rh.insert(x)
    print(f"Inserted {x}")

for x in [20, 35, 60]:
    print(f"Search {x}: {'found' if rh.search(x) else 'not found'}")
```

---

## 105.4 Dry Run: Robin Hood Hashing

Table size = 8, hash function: `h(x) = x % 8`

Insert: 10, 18, 26, 34, 42

**Step 1**: Insert 10
- h(10) = 2, table[2] empty → place (10, 0)

**Step 2**: Insert 18
- h(18) = 2, table[2] has (10, 0)
- dist(18) = 0, dist(10) = 0, no swap
- table[3] empty → place (18, 1)

**Step 3**: Insert 26
- h(26) = 2, table[2] has (10, 0)
- dist(26) = 0, dist(10) = 0, no swap
- table[3] has (18, 1), dist(26) = 1, dist(18) = 1, no swap
- table[4] empty → place (26, 2)

**Step 4**: Insert 34
- h(34) = 2, table[2] has (10, 0)
- dist(34) = 0, dist(10) = 0, no swap
- table[3] has (18, 1), dist(34) = 1, dist(18) = 1, no swap
- table[4] has (26, 2), dist(34) = 2, dist(26) = 2, no swap
- table[5] empty → place (34, 3)

**Step 5**: Insert 42
- h(42) = 2, table[2] has (10, 0)
- dist(42) = 0, dist(10) = 0, no swap
- table[3] has (18, 1), dist(42) = 1, dist(18) = 1, no swap
- table[4] has (26, 2), dist(42) = 2, dist(26) = 2, no swap
- table[5] has (34, 3), dist(42) = 3, dist(34) = 3, no swap
- table[6] empty → place (42, 4)

Now insert 2 (h(2) = 2):
- table[2] has (10, 0), dist(2) = 0, dist(10) = 0, no swap
- table[3] has (18, 1), dist(2) = 1, dist(18) = 1, no swap
- ...
- table[6] has (42, 4), dist(2) = 4, dist(42) = 4, no swap
- table[7] empty → place (2, 5)

Now insert 50 (h(50) = 2), **with Robin Hood swap**:
- table[2] has (10, 0), dist(50) = 0, dist(10) = 0, no swap
- table[3] has (18, 1), dist(50) = 1, dist(18) = 1, no swap
- ...
- table[6] has (42, 4), dist(50) = 4, dist(42) = 4, no swap
- table[7] has (2, 5), dist(50) = 5, dist(2) = 5, no swap
- table[0] empty → place (50, 6)

The Robin Hood benefit: if we had a collision where the new element had traveled farther, it would swap, keeping probe lengths balanced.

---

## 105.5 Complexity Analysis

### Cuckoo Hashing

| Operation | Expected | Worst Case |
|---|---|---|
| Search | O(1) | **O(1)** |
| Insert | O(1) amortized | O(n) if rehash needed |
| Delete | O(1) | O(1) |
| Space | O(n) | O(n) |

**Key property**: Search is always O(1) because we check exactly 2 positions.

### Robin Hood Hashing

| Operation | Expected | Worst Case |
|---|---|---|
| Search | O(1) | O(log n) whp |
| Insert | O(1) | O(log n) whp |
| Delete | O(1) | O(log n) whp |
| Space | O(n) | O(n) |

**Key property**: Maximum probe length is O(log n) with high probability (much better than standard hashing's O(n) worst case).

---

## 105.6 Comparison

| Feature | Standard Open Addressing | Cuckoo Hashing | Robin Hood Hashing |
|---|---|---|---|
| Search worst case | O(n) | **O(1)** | O(log n) |
| Insert complexity | O(1) amortized | O(1) amortized | O(1) expected |
| Deletion | Lazy deletion | Direct | Direct |
| Cache behavior | Good | Poor (two tables) | Good |
| Load factor | < 1 | < 0.5 | < 1 |
| Variance | High | Low | **Very low** |

---

## 105.7 When to Use Each

### Use Cuckoo Hashing When:
- You need **guaranteed O(1) lookup** (real-time systems)
- Lookups are much more frequent than insertions
- You can afford the extra space (two tables)

### Use Robin Hood Hashing When:
- You want **consistent performance** (low variance)
- Cache efficiency matters
- You need high load factors (> 0.7)

### Use Standard Hashing When:
- Simplicity is preferred
- Average case performance is sufficient
- You don't need worst-case guarantees

---

## 105.8 Exercises

### Conceptual

1. **Why is cuckoo hashing search O(1)?** What makes it different from standard open addressing?
2. **How does Robin Hood hashing reduce variance?** Explain the "steal from the rich" mechanism.
3. **What happens in cuckoo hashing when a cycle is detected during insertion?** How is it resolved?

### Implementation

4. **Implement cuckoo hashing** with proper rehashing when cycles are detected.
5. **Implement Robin Hood hashing** with deletion that maintains the Robin Hood invariant.
6. **Benchmark** cuckoo hashing vs Robin Hood hashing vs standard hashing at various load factors.

### Challenge

7. **Stash-based cuckoo hashing**: Add a small "stash" (4-8 elements) to reduce rehash probability. Implement and analyze.
8. **Cuckoo hashing with more than 2 tables**: Implement with 3 hash functions and compare the maximum load factor.

---

## 105.9 Interview Questions

1. **Q**: How does cuckoo hashing achieve O(1) lookup?
   **A**: It uses two hash functions and two tables. A key can only be in one of two positions, so we check both in O(1).

2. **Q**: What happens when cuckoo hashing can't insert an element?
   **A**: If the eviction chain forms a cycle, we rehash with new hash functions and a larger table. This happens with very low probability when load factor < 0.5.

3. **Q**: How does Robin Hood hashing differ from standard linear probing?
   **A**: During insertion, if the new element has traveled farther from its ideal position than the existing element, they swap. This equalizes probe lengths and reduces the maximum probe length to O(log n).

4. **Q**: What's the advantage of Robin Hood hashing for cache performance?
   **A**: It keeps elements closer to their ideal positions, which means sequential probing stays within a smaller memory region, improving cache hit rates.

5. **Q**: When would you choose cuckoo hashing over Robin Hood hashing?
   **A**: When you need guaranteed O(1) lookup (e.g., real-time systems). Robin Hood has O(log n) worst-case lookup.

---

## 105.10 See Also

- [Chapter 7: Hashing](ch07-hashing.md) — Hash table fundamentals: collision handling, load factors, and basic hash map operations.
- [Chapter 94: Hashing Deep Dive](ch94-hashing-deep-dive.md) — Universal hashing, perfect hashing, locality-sensitive hashing, and consistent hashing.
- [Chapter 134: Consistent Hashing](ch134-consistent-hashing.md) — Distributed hash tables and load balancing across servers.
- [Chapter 79: Probabilistic Data Structures](ch79-probabilistic-ds.md) — Bloom filters and other hash-based probabilistic structures.
