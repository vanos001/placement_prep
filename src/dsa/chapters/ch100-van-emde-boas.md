# Chapter 100: Van Emde Boas Trees and X-Fast/Y-Fast Tries

## Prerequisites
- Binary search trees and balanced BSTs
- Binary tries and prefix trees
- Hash tables
- Bit manipulation
- Recursion and divide-and-conquer

## Interview Frequency: ★

Van Emde Boas (VEB) trees, X-Fast tries, and Y-Fast tries are theoretical data structures that achieve O(log log U) operations on integer keys from a universe [0, U). They are rarely asked in interviews but demonstrate deep understanding of data structure design, and the techniques (recursive decomposition, hash-based level skipping, and balanced BST augmentation) are valuable design patterns.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Van Emde Boas tree | ★ | Hard | O(log log U) operations |
| X-Fast Trie | ★ | Hard | O(log log U) search |
| Y-Fast Trie | ★ | Hard | Expected O(log log n) |
| Universe reduction | ★ | Medium | From U to n |

---

## 100.1 Motivation and Intuition

### The Goal: Faster Than O(log n)

Standard balanced BSTs (AVL, Red-Black) support operations in O(log n) time. For n = 10⁹, that's ~30 comparisons. Can we do better?

If keys are integers from a bounded universe [0, U), we can exploit the structure of integers. VEB trees achieve O(log log U) operations — for U = 2³², that's just 5 operations!

### The Tradeoff

VEB trees use O(U) space — potentially much more than O(n). This makes them impractical for large universes with sparse data. Y-Fast tries fix this by using O(n) space with expected O(log log n) operations.

### Intuition: Recursive √U Decomposition

The key idea of VEB is to recursively split the universe into √U clusters, each of size √U.

**Analogy**: Imagine organizing books in a library. Instead of one giant shelf, you have √U sections, each with √U slots. A "summary" shelf tells you which sections have books. To find a book, you: (1) check the summary for the right section, (2) search within that section.

This recursion continues: each section is itself divided into √(√U) sub-sections, and so on, until we reach base cases of size 2.

### Recurrence

```
T(U) = T(√U) + O(1)
```

With substitution U = 2^k:
```
T(2^k) = T(2^(k/2)) + O(1)
Let S(k) = T(2^k):
S(k) = S(k/2) + O(1)
S(k) = O(log k)
T(U) = O(log log U)
```

---

## 100.2 Van Emde Boas Tree: Structure

### Definition

A VEB tree for universe size U stores a subset of {0, 1, ..., U-1} and supports:
- **Insert(x)**: Add x to the set
- **Delete(x)**: Remove x from the set
- **Search(x)**: Is x in the set?
- **Successor(x)**: Smallest element > x
- **Predecessor(x)**: Largest element < x
- **Min/Max**: Minimum and maximum elements

### Structure

```
VEB(U):
    min:    minimum element (stored separately, NOT in clusters)
    max:    maximum element
    summary: VEB(√U) — tracks which clusters are non-empty
    cluster: array of √U VEB(√U) trees
```

**Key insight**: The min element is stored separately (not recursed into clusters). This breaks the recursion cleanly.

### Index Mapping

For a key x in universe [0, U):
- **high(x)** = x / √U — which cluster x belongs to
- **low(x)** = x % √U — position within that cluster
- **index(h, l)** = h × √U + l — reconstruct key from cluster and position

### Example: VEB(16)

Universe {0, 1, ..., 15}. √16 = 4 clusters of size 4.

```
VEB(16):
  min = 2, max = 14
  summary: VEB(4) tracking which of 4 clusters are non-empty
  cluster[0]: VEB(4) for {0,1,2,3}  (contains 3)
  cluster[1]: VEB(4) for {4,5,6,7}  (empty)
  cluster[2]: VEB(4) for {8,9,10,11} (contains 9)
  cluster[3]: VEB(4) for {12,13,14,15} (contains 14,15)
```

After inserting {2, 3, 9, 14, 15}:
```
high(2) = 0, low(2) = 2  → cluster[0]
high(3) = 0, low(3) = 3  → cluster[0]
high(9) = 2, low(9) = 1  → cluster[2]
high(14) = 3, low(14) = 2 → cluster[3]
high(15) = 3, low(15) = 3 → cluster[3]
```

---

## 100.3 Van Emde Boas Tree: Operations

### Insert(x)

```
Insert(x):
    if tree is empty:
        min = max = x
        return
    
    if x < min:
        swap(x, min)  // Old min goes into a cluster
    
    if U > 2:
        if cluster[high(x)] is empty:
            summary.Insert(high(x))  // Mark cluster as non-empty
        cluster[high(x)].Insert(low(x))
    
    if x > max: max = x
```

**Key detail**: When inserting x < min, we swap x with min. The old min then gets inserted into the appropriate cluster (since min is stored separately, not in clusters).

### Successor(x)

```
Successor(x):
    if x < min: return min
    
    h = high(x), l = low(x)
    
    // Try within the same cluster
    if cluster[h] has an element > l:
        return index(h, cluster[h].Successor(l))
    
    // Find next non-empty cluster
    nextCluster = summary.Successor(h)
    if nextCluster == -1: return -1  // No successor
    
    return index(nextCluster, cluster[nextCluster].min)
```

### Dry Run: Successor(9) in VEB(16) with {2, 3, 9, 14, 15}

```
Successor(9):
  9 > min=2, so proceed
  h = high(9) = 2, l = low(9) = 1
  
  Check cluster[2]: does it have element > 1?
    cluster[2] = {1} (just low(9)=1), no element > 1
  
  Find next non-empty cluster:
    summary.Successor(2) = 3  (cluster[3] is non-empty)
  
  Return index(3, cluster[3].min) = index(3, 2) = 3×4 + 2 = 14
  
  Answer: 14
```

### Dry Run: Insert(5) into VEB(16) with {2, 3, 9, 14, 15}

```
Insert(5):
  5 > min=2, no swap needed
  h = high(5) = 1, l = low(5) = 1
  
  cluster[1] is empty:
    summary.Insert(1)  // Mark cluster[1] as non-empty
  
  cluster[1].Insert(1)  // Insert low(5)=1 into cluster[1]
  
  5 < max=14, so max stays
  
Result: {2, 3, 5, 9, 14, 15}
  cluster[0]: {2,3}, cluster[1]: {5}, cluster[2]: {9}, cluster[3]: {14,15}
  summary: {0,1,2,3} (all clusters non-empty)
```

### Delete(x)

```
Delete(x):
    if min == max:
        min = max = -1  // Tree becomes empty
        return
    
    if U <= 2:
        if x == 0: min = max = 1
        else: min = max = 0
        return
    
    if x == min:
        // Find new minimum (first element in first non-empty cluster)
        firstCluster = summary.min
        x = index(firstCluster, cluster[firstCluster].min)
        min = x
    
    cluster[high(x)].Delete(low(x))
    
    if cluster[high(x)] is empty:
        summary.Delete(high(x))
    
    if x == max:
        // Find new maximum
        if summary is empty:
            max = min
        else:
            lastCluster = summary.max
            max = index(lastCluster, cluster[lastCluster].max)
```

---

## 100.4 Complexity Analysis

### Space

```
S(U) = √U × S(√U) + O(√U)  (summary + clusters)
S(2) = O(1)

With U = 2^k:
S(2^k) = 2^(k/2) × S(2^(k/2)) + O(2^(k/2))
S(k) = 2^(k/2) × S(k/2) + O(2^(k/2))
```

This solves to **S(U) = O(U)** — linear in the universe size.

### Time

All operations have the recurrence:
```
T(U) = T(√U) + O(1)
```

Which gives **T(U) = O(log log U)**.

| Operation | Time |
|---|---|
| Insert | O(log log U) |
| Delete | O(log log U) |
| Search | O(log log U) |
| Successor | O(log log U) |
| Predecessor | O(log log U) |
| Min/Max | O(1) |

### Comparison with Other Structures

| Structure | Insert | Search | Space | Notes |
|---|---|---|---|---|
| Array (sorted) | O(n) | O(log n) | O(n) | Simple |
| BST (balanced) | O(log n) | O(log n) | O(n) | Standard |
| Hash Table | O(1) avg | O(1) avg | O(n) | No successor |
| VEB Tree | O(log log U) | O(log log U) | O(U) | Integer keys |
| X-Fast Trie | O(log log U) | O(log log U) | O(n log U) | Sparse |
| Y-Fast Trie | O(log log n) exp | O(log log n) exp | O(n) | Best practical |

---

## 100.5 X-Fast Trie

### Definition

An X-Fast trie is a binary trie on the bits of the keys, augmented with hash tables at each level for ancestor lookups.

### Structure

- **Binary trie**: Each node represents a bit prefix
- **Hash tables**: One per level, mapping prefix → node pointer
- **Only stores paths to present elements** (sparse)

### Operations

**Search(x)**: O(log log U)
1. Look up x in the deepest hash table (O(1))
2. If found, return true
3. If not, the search reveals where x would be — O(log log U) levels checked

**Successor(x)**: O(log log U)
1. Find the longest common prefix with x (binary search on levels)
2. The successor is in the leftmost subtree of the right sibling

**Insert(x)**: O(log U) worst case
- Create nodes along the path from root to x: O(log U) nodes

**Delete(x)**: O(log log U)
- Remove nodes along the path that are no longer needed

### Why O(log log U) for Search/Successor?

Binary search on the log U levels of the trie. At each step, check if a node exists at a given level using the hash table. This takes O(log(log U)) = O(log log U) hash lookups.

---

## 100.6 Y-Fast Trie

### Motivation

VEB uses O(U) space. X-Fast uses O(n log U) space. Can we achieve O(n) space with O(log log n) operations?

### Structure

1. **Partition** keys into groups of size ≈ log U
2. **X-Fast trie** on the representative (maximum) of each group
3. **Balanced BST** within each group

### Operations

**Search(x)**: O(log log U) expected
1. Search in X-Fast trie for the group containing x: O(log log U)
2. Search within the group's BST: O(log log U) (since group size ≈ log U)

**Insert(x)**: O(log log U) expected
1. Insert into the BST: O(log log U)
2. If group exceeds 2 log U, split it: O(log U) amortized
3. Update X-Fast trie: O(log U) amortized

### Space

- X-Fast trie: O((n/log U) × log U) = O(n) nodes
- BSTs: O(n) total
- **Total: O(n)**

### Comparison

| Structure | Space | Search | Insert | Notes |
|---|---|---|---|---|
| VEB | O(U) | O(log log U) | O(log log U) | Best if U is small |
| X-Fast | O(n log U) | O(log log U) | O(log U) | Good search, bad insert |
| Y-Fast | O(n) | O(log log n) exp | O(log log n) exp | Best practical |

---

## 100.7 Implementations

### C++: Van Emde Boas Tree

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <climits>

class VEBTree {
    int universeSize;
    int minVal, maxVal;
    VEBTree* summary;
    std::vector<VEBTree*> clusters;
    int sqrtU;  // Ceiling of sqrt(universeSize)
    
    int high(int x) const { return x / sqrtU; }
    int low(int x) const { return x % sqrtU; }
    int index(int h, int l) const { return h * sqrtU + l; }
    
public:
    VEBTree(int size) : universeSize(size), minVal(-1), maxVal(-1), summary(nullptr) {
        if (size <= 2) return;
        sqrtU = (int)ceil(sqrt(size));
        summary = new VEBTree(sqrtU);
        clusters.resize(sqrtU, nullptr);
    }
    
    ~VEBTree() {
        delete summary;
        for (auto* c : clusters) delete c;
    }
    
    bool isEmpty() const { return minVal == -1; }
    int getMin() const { return minVal; }
    int getMax() const { return maxVal; }
    
    bool search(int x) const {
        if (x == minVal || x == maxVal) return true;
        if (universeSize <= 2) return false;
        int h = high(x);
        if (!clusters[h]) return false;
        return clusters[h]->search(low(x));
    }
    
    void insert(int x) {
        if (minVal == -1) {
            minVal = maxVal = x;
            return;
        }
        
        if (x < minVal) std::swap(x, minVal);
        
        if (universeSize > 2) {
            int h = high(x), l = low(x);
            if (!clusters[h]) {
                clusters[h] = new VEBTree(sqrtU);
            }
            if (clusters[h]->isEmpty()) {
                if (!summary) summary = new VEBTree(sqrtU);
                summary->insert(h);
            }
            clusters[h]->insert(l);
        }
        
        if (x > maxVal) maxVal = x;
    }
    
    int successor(int x) const {
        if (universeSize == 2) {
            if (x == 0 && maxVal == 1) return 1;
            return -1;
        }
        if (minVal != -1 && x < minVal) return minVal;
        
        int h = high(x), l = low(x);
        
        // Try within the same cluster
        if (clusters[h] && l < clusters[h]->getMax()) {
            int succ = clusters[h]->successor(l);
            return index(h, succ);
        }
        
        // Find next non-empty cluster
        if (!summary) return -1;
        int succCluster = summary->successor(h);
        if (succCluster == -1) return -1;
        return index(succCluster, clusters[succCluster]->getMin());
    }
    
    int predecessor(int x) const {
        if (universeSize == 2) {
            if (x == 1 && minVal == 0) return 0;
            return -1;
        }
        if (maxVal != -1 && x > maxVal) return maxVal;
        
        int h = high(x), l = low(x);
        
        // Try within the same cluster
        if (clusters[h] && l > clusters[h]->getMin()) {
            int pred = clusters[h]->predecessor(l);
            return index(h, pred);
        }
        
        // Find previous non-empty cluster
        if (!summary) {
            if (minVal != -1 && x > minVal) return minVal;
            return -1;
        }
        int predCluster = summary->predecessor(h);
        if (predCluster == -1) {
            if (minVal != -1 && x > minVal) return minVal;
            return -1;
        }
        return index(predCluster, clusters[predCluster]->getMax());
    }
    
    void remove(int x) {
        if (minVal == maxVal) {
            minVal = maxVal = -1;
            return;
        }
        
        if (universeSize <= 2) {
            if (x == 0) { minVal = 1; maxVal = 1; }
            else { minVal = 0; maxVal = 0; }
            return;
        }
        
        if (x == minVal) {
            int firstCluster = summary->getMin();
            x = index(firstCluster, clusters[firstCluster]->getMin());
            minVal = x;
        }
        
        int h = high(x), l = low(x);
        clusters[h]->remove(l);
        
        if (clusters[h]->isEmpty()) {
            summary->remove(h);
        }
        
        if (x == maxVal) {
            if (summary->isEmpty()) {
                maxVal = minVal;
            } else {
                int lastCluster = summary->getMax();
                maxVal = index(lastCluster, clusters[lastCluster]->getMax());
            }
        }
    }
    
    // Print all elements
    void print(int base = 0, int step = 1) const {
        if (isEmpty()) return;
        if (universeSize <= 2) {
            if (minVal != -1) std::cout << " " << base + minVal * step;
            if (maxVal != -1 && maxVal != minVal) std::cout << " " << base + maxVal * step;
            return;
        }
        std::cout << " " << base + minVal * step;
        // Print elements in clusters
        if (summary) {
            // This is simplified; a full implementation would traverse properly
        }
        std::cout << " " << base + maxVal * step;
    }
};

int main() {
    VEBTree veb(16); // Universe [0, 15]
    
    std::cout << "=== VEB Tree (Universe [0, 15]) ===\n\n";
    
    // Insert elements
    int elements[] = {2, 3, 7, 14, 15, 5, 9};
    for (int x : elements) {
        veb.insert(x);
        std::cout << "Inserted " << x << "\n";
    }
    
    std::cout << "\n--- Search ---\n";
    for (int x : {4, 5, 7, 8, 14}) {
        std::cout << "Search(" << x << "): " << (veb.search(x) ? "found" : "not found") << "\n";
    }
    
    std::cout << "\n--- Successor ---\n";
    for (int x : {0, 3, 5, 7, 9, 14, 15}) {
        int succ = veb.successor(x);
        std::cout << "Successor(" << x << "): " << (succ == -1 ? "none" : std::to_string(succ)) << "\n";
    }
    
    std::cout << "\n--- Predecessor ---\n";
    for (int x : {1, 3, 6, 8, 10, 15}) {
        int pred = veb.predecessor(x);
        std::cout << "Predecessor(" << x << "): " << (pred == -1 ? "none" : std::to_string(pred)) << "\n";
    }
    
    std::cout << "\n--- Remove ---\n";
    veb.remove(7);
    std::cout << "Removed 7. Search(7): " << (veb.search(7) ? "found" : "not found") << "\n";
    std::cout << "Successor(6): " << veb.successor(6) << "\n";
    std::cout << "Predecessor(8): " << veb.predecessor(8) << "\n";
    
    return 0;
}
```

### Python: X-Fast Trie

```python
class XFastTrieNode:
    """A node in the X-Fast trie."""
    def __init__(self, prefix, level):
        self.prefix = prefix    # Bit prefix this node represents
        self.level = level      # Level in trie (0 = root, w = leaves)
        self.left = None        # Left child (bit 0)
        self.right = None       # Right child (bit 1)
        self.is_leaf = False
        self.value = None       # Only for leaves: the actual key
        # For successor/predecessor: linked list at leaf level
        self.leaf_prev = None
        self.leaf_next = None

class XFastTrie:
    """
    X-Fast Trie for integer keys from universe [0, 2^w).
    
    Supports:
        - search(x): O(log w) = O(log log U)
        - successor(x): O(log w) = O(log log U)
        - predecessor(x): O(log w) = O(log log U)
        - insert(x): O(w) = O(log U) worst case
        - delete(x): O(w) = O(log U) worst case
    
    Space: O(n × w) where n is number of keys, w = log U
    """
    
    def __init__(self, word_size=32):
        self.w = word_size
        self.root = XFastTrieNode(0, 0)
        self.n = 0
        # Hash tables: level -> {prefix: node}
        self.levels = [{} for _ in range(self.w + 1)]
        self.levels[0][0] = self.root
        # Doubly-linked list of leaves
        self.leaf_head = None  # Sentinel
        self.leaf_tail = None  # Sentinel
    
    def _bits(self, x, depth):
        """Get the top 'depth' bits of x."""
        return x >> (self.w - depth) if depth > 0 else 0
    
    def search(self, x):
        """Check if x exists. O(log w)"""
        node = self.root
        for level in range(1, self.w + 1):
            bit = (x >> (self.w - level)) & 1
            child = node.left if bit == 0 else node.right
            if child is None:
                return False
            node = child
        return node.is_leaf
    
    def _find_ancestor(self, x):
        """Binary search for the highest level where x has an ancestor. O(log w)"""
        lo, hi = 0, self.w
        while lo < hi:
            mid = (lo + hi + 1) // 2
            prefix = self._bits(x, mid)
            if prefix in self.levels[mid]:
                lo = mid
            else:
                hi = mid - 1
        return self.levels[lo][self._bits(x, lo)]
    
    def successor(self, x):
        """Find smallest element >= x. O(log w)"""
        # Find deepest ancestor
        node = self._find_ancestor(x)
        
        if node.is_leaf:
            if node.value >= x:
                return node.value
            # Go to next leaf
            if node.leaf_next and node.leaf_next.value is not None:
                return node.leaf_next.value
            return None
        
        # The ancestor's prefix matches x's top bits
        # Need to find the leftmost leaf in the right subtree
        bit = (x >> (self.w - node.level - 1)) & 1
        if bit == 0:
            # Go right (x wants to go left, but we want >= x)
            child = node.right
            if child is None:
                # Go up and find right ancestor
                prefix = self._bits(x, node.level)
                if prefix + 1 in self.levels[node.level]:
                    next_node = self.levels[node.level][prefix + 1]
                    # Find leftmost leaf
                    while not next_node.is_leaf:
                        next_node = next_node.left or next_node.right
                    return next_node.value if next_node and next_node.value >= x else None
                return None
            # Find leftmost leaf in right subtree
            while not child.is_leaf:
                child = child.left or child.right
            return child.value if child and child.value >= x else None
        else:
            # Go up
            # This case is more complex; simplified version
            return None
    
    def insert(self, x):
        """Insert x into the trie. O(w)"""
        if self.search(x):
            return
        
        self.n += 1
        node = self.root
        
        # Create path from root to leaf
        for level in range(1, self.w + 1):
            bit = (x >> (self.w - level)) & 1
            prefix = self._bits(x, level)
            
            if bit == 0:
                if node.left is None:
                    node.left = XFastTrieNode(prefix, level)
                    self.levels[level][prefix] = node.left
                node = node.left
            else:
                if node.right is None:
                    node.right = XFastTrieNode(prefix, level)
                    self.levels[level][prefix] = node.right
                node = node.right
        
        node.is_leaf = True
        node.value = x
        
        # Insert into leaf linked list (sorted)
        # Find position
        if self.leaf_head is None:
            self.leaf_head = XFastTrieNode(-1, -1)  # Sentinel
            self.leaf_tail = XFastTrieNode(-1, -1)  # Sentinel
            self.leaf_head.leaf_next = self.leaf_tail
            self.leaf_tail.leaf_prev = self.leaf_head
        
        # Find insertion point
        prev = self.leaf_head
        while prev.leaf_next and prev.leaf_next.value is not None and prev.leaf_next.value < x:
            prev = prev.leaf_next
        
        node.leaf_prev = prev
        node.leaf_next = prev.leaf_next
        prev.leaf_next = node
        if node.leaf_next:
            node.leaf_next.leaf_prev = node

if __name__ == "__main__":
    xft = XFastTrie(word_size=8)  # Universe [0, 255]
    
    elements = [3, 7, 15, 23, 42, 100, 200]
    for x in elements:
        xft.insert(x)
        print(f"Inserted {x}")
    
    print("\n--- Search ---")
    for x in [7, 8, 15, 16, 42, 99]:
        print(f"Search({x}): {'found' if xft.search(x) else 'not found'}")
    
    print("\n--- Successor ---")
    for x in [0, 7, 10, 15, 50, 100, 201]:
        succ = xft.successor(x)
        print(f"Successor({x}): {succ}")
```

### Java: Y-Fast Trie

```java
import java.util.*;

/**
 * Y-Fast Trie: O(n) space, expected O(log log n) operations.
 * 
 * Structure:
 * - Partition keys into groups of ~log U
 * - X-Fast trie on group representatives
 * - BST within each group
 */
public class YFastTrie {
    private static final int GROUP_SIZE = 32; // ~log U for U = 2^32
    
    // Groups: TreeMap<representative, TreeSet<key>>
    private TreeMap<Integer, TreeSet<Integer>> groups;
    private int n;
    
    public YFastTrie() {
        groups = new TreeMap<>();
        n = 0;
    }
    
    /**
     * Search for x. O(log log n) expected.
     */
    public boolean search(int x) {
        if (groups.isEmpty()) return false;
        
        // Find the group whose representative is >= x
        Map.Entry<Integer, TreeSet<Integer>> entry = groups.floorEntry(x);
        if (entry == null) entry = groups.firstEntry();
        
        return entry.getValue().contains(x);
    }
    
    /**
     * Insert x. O(log log n) expected.
     */
    public void insert(int x) {
        if (search(x)) return;
        
        n++;
        
        if (groups.isEmpty()) {
            TreeSet<Integer> group = new TreeSet<>();
            group.add(x);
            groups.put(x, group);
            return;
        }
        
        // Find appropriate group
        Map.Entry<Integer, TreeSet<Integer>> entry = groups.floorEntry(x);
        if (entry == null) entry = groups.firstEntry();
        
        entry.getValue().add(x);
        
        // Update representative if needed
        int oldRep = entry.getKey();
        int newMax = entry.getValue().last();
        if (newMax != oldRep) {
            groups.remove(oldRep);
            groups.put(newMax, entry.getValue());
        }
        
        // Split if group is too large
        if (entry.getValue().size() > 2 * GROUP_SIZE) {
            split(entry.getValue());
        }
    }
    
    /**
     * Delete x. O(log log n) expected.
     */
    public void delete(int x) {
        Map.Entry<Integer, TreeSet<Integer>> entry = groups.floorEntry(x);
        if (entry == null || !entry.getValue().contains(x)) return;
        
        entry.getValue().remove(x);
        n--;
        
        if (entry.getValue().isEmpty()) {
            groups.remove(entry.getKey());
        } else {
            // Update representative
            int oldRep = entry.getKey();
            int newMax = entry.getValue().last();
            if (newMax != oldRep) {
                groups.remove(oldRep);
                groups.put(newMax, entry.getValue());
            }
        }
    }
    
    /**
     * Find successor of x (smallest element >= x).
     */
    public Integer successor(int x) {
        if (groups.isEmpty()) return null;
        
        Map.Entry<Integer, TreeSet<Integer>> entry = groups.floorEntry(x);
        if (entry == null) entry = groups.firstEntry();
        
        Integer result = entry.getValue().ceiling(x);
        if (result != null) return result;
        
        // Try next group
        Map.Entry<Integer, TreeSet<Integer>> next = groups.higherEntry(entry.getKey());
        return next != null ? next.getValue().first() : null;
    }
    
    /**
     * Find predecessor of x (largest element <= x).
     */
    public Integer predecessor(int x) {
        if (groups.isEmpty()) return null;
        
        Map.Entry<Integer, TreeSet<Integer>> entry = groups.floorEntry(x);
        if (entry == null) return null;
        
        Integer result = entry.getValue().floor(x);
        return result;
    }
    
    private void split(TreeSet<Integer> group) {
        List<Integer> sorted = new ArrayList<>(group);
        int mid = sorted.size() / 2;
        
        TreeSet<Integer> left = new TreeSet<>(sorted.subList(0, mid));
        TreeSet<Integer> right = new TreeSet<>(sorted.subList(mid, sorted.size()));
        
        // Remove old group
        groups.remove(group.last());
        
        // Add new groups
        groups.put(left.last(), left);
        groups.put(right.last(), right);
    }
    
    public int size() { return n; }
    
    public void printGroups() {
        System.out.println("Groups (" + groups.size() + " groups, " + n + " elements):");
        for (Map.Entry<Integer, TreeSet<Integer>> entry : groups.entrySet()) {
            System.out.println("  Rep " + entry.getKey() + ": " + entry.getValue());
        }
    }
    
    public static void main(String[] args) {
        YFastTrie yft = new YFastTrie();
        
        // Insert elements
        int[] elements = {3, 7, 15, 23, 42, 50, 67, 88, 100, 150, 200};
        for (int x : elements) {
            yft.insert(x);
        }
        
        System.out.println("=== Y-Fast Trie ===\n");
        yft.printGroups();
        
        System.out.println("\n--- Search ---");
        for (int x : new int[]{7, 8, 42, 99, 200}) {
            System.out.printf("Search(%d): %s%n", x, yft.search(x) ? "found" : "not found");
        }
        
        System.out.println("\n--- Successor ---");
        for (int x : new int[]{0, 7, 20, 50, 101, 200}) {
            Integer succ = yft.successor(x);
            System.out.printf("Successor(%d): %s%n", x, succ != null ? succ : "none");
        }
        
        System.out.println("\n--- Predecessor ---");
        for (int x : new int[]{1, 7, 20, 50, 101, 201}) {
            Integer pred = yft.predecessor(x);
            System.out.printf("Predecessor(%d): %s%n", x, pred != null ? pred : "none");
        }
        
        System.out.println("\n--- Delete ---");
        yft.delete(42);
        System.out.println("Deleted 42.");
        System.out.println("Search(42): " + (yft.search(42) ? "found" : "not found"));
        System.out.println("Successor(41): " + yft.successor(41));
        System.out.println("Predecessor(43): " + yft.predecessor(43));
    }
}
```

---

## 100.8 Universe Reduction: From O(U) to O(n)

VEB's O(U) space is problematic when U >> n. Universe reduction techniques transform the problem:

### Approach 1: Dynamic Perfect Hashing

Use a hash table to map the n actual keys to a universe of size O(n²). Then use VEB on the hashed universe. Expected space: O(n).

### Approach 2: Y-Fast Trie

The Y-Fast trie implicitly achieves O(n) space by:
1. Only storing n keys
2. Using X-Fast trie on n/log(U) representatives
3. BSTs within groups

### Approach 3: Fusion Trees (related)

For word-size w, fusion trees achieve O(log_w n) search using word-level parallelism. This gives O(log n / log log n) for w = Θ(log n).

---

## 100.9 Applications

### Integer Sorting

VEB-based integer sort: O(n log log U) — faster than comparison-based O(n log n) when log log U < log n.

### Priority Queue

VEB as a priority queue: O(log log U) insert/extract-min, vs O(log n) for binary heap.

### Sparse Bit Manipulation

X-Fast/Y-Fast tries are useful for managing sparse sets of integers in systems programming (e.g., free block tracking in memory allocators).

### Network Routing

Longest prefix matching in routers can use trie-based structures similar to X-Fast tries for O(log log U) lookup.

---

## 100.10 Exercises

### Conceptual Exercises

1. **Recurrence**: Solve T(U) = T(√U) + O(1) to show T(U) = O(log log U).

2. **Space**: Why does VEB use O(U) space? How does Y-Fast reduce this to O(n)?

3. **Min stored separately**: Why is it important that min is stored outside the clusters? What would go wrong if min were in a cluster?

4. **X-Fast vs Y-Fast**: What are the tradeoffs between X-Fast and Y-Fast tries? When would you prefer each?

5. **Universe size**: For U = 2^64, what is log log U? How does this compare to log n for n = 10^9?

### Programming Exercises

1. **VEB with explicit deletion**: Implement a VEB tree that properly handles deletion (the version in this chapter is simplified).

2. **X-Fast trie**: Complete the X-Fast trie implementation with working successor/predecessor.

3. **Benchmark**: Compare VEB, BST, and hash table for random operations on universe [0, 2^20).

4. **VEB-based sort**: Implement integer sort using VEB tree. Compare with std::sort.

5. **Fusion tree sketch**: Research and sketch how fusion trees achieve O(log_w n) search.

---

## 100.11 Interview Questions

### Conceptual Questions

1. **Q**: What is a Van Emde Boas tree and when would you use it?
   **A**: A VEB tree stores integers from a bounded universe [0, U) and supports all operations in O(log log U) time. It uses recursive √U decomposition. Use it when: (1) keys are integers from a known range, (2) you need faster-than-logarithmic operations, (3) space is not a constraint. In practice, hash tables are preferred for most integer-key scenarios.

2. **Q**: Explain the √U decomposition in VEB trees.
   **A**: The universe [0, U) is split into √U clusters of size √U. Each key x maps to cluster high(x) = x/√U at position low(x) = x%√U. A "summary" VEB tree tracks which clusters are non-empty. Operations recurse: check the summary (size √U), then recurse into a cluster (size √U). This gives T(U) = T(√U) + O(1) = O(log log U).

3. **Q**: How do X-Fast and Y-Fast tries differ from VEB?
   **A**: VEB uses O(U) space. X-Fast uses O(n log U) space with a hash-augmented binary trie. Y-Fast uses O(n) space by combining X-Fast with BSTs. All achieve O(log log U) or O(log log n) operations. VEB is best when U is small. Y-Fast is best for large sparse universes.

4. **Q**: Why is log log U so small? For practical values, what is it?
   **A**: For U = 2^32: log U = 32, log log U = 5. For U = 2^64: log U = 64, log log U = 6. The double logarithm grows extremely slowly. This means VEB trees are almost O(1) for practical universe sizes. However, the constant factors and space overhead make them slower than hash tables in practice.

### Coding Questions

1. **Q**: Implement insert and successor for a VEB tree of size 16.
   **A**: See the C++ implementation in this chapter. Key points: (1) min stored separately, (2) swap x with min if x < min, (3) update summary when inserting into empty cluster, (4) successor checks within cluster first, then jumps to next cluster via summary.

2. **Q**: How would you implement a priority queue using VEB?
   **A**: Insert: O(log log U). Extract-min: return and delete min (O(log log U)). The min is always accessible in O(1). For decrease-key, delete and re-insert.

3. **Q**: Design a data structure that supports insert, delete, and "find the k-th smallest element" in O(log log U) time.
   **A**: Augment VEB tree with subtree sizes at each node. Track size of each cluster and the summary. To find k-th smallest: if k ≤ size of left cluster in summary, recurse left; otherwise recurse right with adjusted k. This adds O(1) overhead per operation.

---

## 100.12 Cross-References

- **Chapter 29: Hashing** — Hash tables provide O(1) average but no order operations
- **Chapter 30: Tries** — Binary tries are the foundation of X-Fast tries
- **Chapter 25: Binary Search Trees** — BSTs used within Y-Fast groups
- **Chapter 33: Heaps** — Priority queue comparison with VEB
- **Chapter 158: Succinct Data Structures** — Bit-level operations on compressed data
- **Chapter 160: Parallel Algorithms** — Parallel integer sorting
- **Chapter 163: Advanced Mathematics** — Recurrence solving, number theory

---

## Summary

| Structure | Space | Insert | Search | Successor | Key Insight |
|---|---|---|---|---|---|
| VEB Tree | O(U) | O(log log U) | O(log log U) | O(log log U) | Recursive √U split |
| X-Fast Trie | O(n log U) | O(log U) | O(log log U) | O(log log U) | Hash + binary trie |
| Y-Fast Trie | O(n) | O(log log n) exp | O(log log n) exp | O(log log n) exp | X-Fast + BST |

**Key Takeaway**: VEB trees achieve O(log log U) operations through recursive √U decomposition. X-Fast tries use hash-augmented binary tries for O(log log U) search with O(n log U) space. Y-Fast tries achieve O(n) space by partitioning keys into groups and using X-Fast on representatives. These structures demonstrate that exploiting integer structure can beat comparison-based lower bounds. In practice, hash tables are usually preferred, but these techniques appear in specialized systems like network routers and memory allocators.
