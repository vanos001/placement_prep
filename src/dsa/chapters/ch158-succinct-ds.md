# Chapter 158: Succinct Data Structures

## Prerequisites
- Bit manipulation
- Binary trees and tries
- Basic data structures (arrays, linked lists, trees)
- Information theory basics

## Interview Frequency: ★

Succinct data structures use space proportional to the information-theoretic minimum — typically n + o(n) bits — while supporting efficient queries. They are critical in systems where memory is the bottleneck: search engines, genomic databases, large-scale indexing, and embedded systems. While rarely asked in interviews, understanding them demonstrates mastery of space-efficient computing.

---

## 158.1 Motivation and Intuition

### The Space Problem

Standard data structures waste space. A balanced BST with n nodes uses O(n) pointers, each taking log n bits. For a billion integers, that's gigabytes of pointer overhead alone.

**Information-theoretic lower bound**: To represent one of C possible objects, you need at least log₂(C) bits.

| Structure | # of possible objects | Lower bound | Typical usage |
|---|---|---|---|
| n-bit vector | 2ⁿ | n bits | n bits (optimal!) |
| Binary tree, n nodes | C(n) ≈ 4ⁿ/√(πn³) | ~2n bits | ~64n bits (with pointers) |
| Permutation of {1..n} | n! | n log₂n bits | ~32n log n bits |
| Subset of {1..n} | 2ⁿ | n bits | ~32n bits |

The gap between lower bound and typical usage is enormous. Succinct data structures close this gap.

### What "Succinct" Means

A data structure is **succinct** if it uses n + o(n) bits of space, where n is the information-theoretic lower bound. The o(n) "overhead" supports efficient operations.

**Spectrum**:
- **Implicit**: Uses exactly the information-theoretic minimum (no overhead). Operations may be slow.
- **Succinct**: Uses n + o(n) bits. Operations are O(1) or O(polylog n).
- **Compact**: Uses O(n) bits (constant factor more than optimal).
- **Traditional**: Uses O(n log n) bits or more.

### Real-World Analogy

Think of a library. Traditional data structures are like a library where each book has a full-page description card. Succinct data structures are like a library where the catalog is printed in tiny font on the bookshelf edges — you can still find any book quickly, but the catalog takes almost no space.

---

## 158.2 Information-Theoretic Lower Bounds

### Bitvector

A bitvector of n bits represents one of 2ⁿ possible states. Lower bound: n bits. We already achieve this trivially.

### Binary Trees

The number of distinct binary trees with n nodes is the Catalan number:

```
C(n) = (2n)! / ((n+1)! × n!) ≈ 4ⁿ / (√π × n^(3/2))
```

Lower bound: log₂(C(n)) ≈ 2n - O(log n) bits.

**Practical representation**: Pointer-based trees use ~64n bits (3 pointers × 64 bits each). That's 32× the lower bound!

### Permutations

A permutation of {1, ..., n} requires log₂(n!) ≈ n log₂ n - 1.44n bits.

An array of n integers (each 32 bits) uses 32n bits, which is ~32/log₂n times the lower bound.

### Subsets

A subset of {1, ..., n} can be any of 2ⁿ possibilities. Lower bound: n bits. A bitvector achieves this exactly.

---

## 158.3 Rank and Select on Bitvectors

These two operations are the foundation of all succinct data structures.

### Definitions

Given a bitvector B[0..n-1]:

| Operation | Definition | Example (B = 101101001) |
|---|---|---|
| **Rank₁(i)** | Number of 1s in B[0..i] | Rank₁(5) = 4 (positions 0,2,3,5) |
| **Rank₀(i)** | Number of 0s in B[0..i] | Rank₀(5) = 2 (positions 1,4) |
| **Select₁(k)** | Position of the (k+1)-th 1 | Select₁(2) = 3 (3rd 1) |
| **Select₀(k)** | Position of the (k+1)-th 0 | Select₀(1) = 4 (2nd 0) |

### Achieving O(1) Time

We need n + o(n) extra bits to support O(1) rank/select.

**Block-based approach**:

1. Divide B into blocks of size b = (log n)²/2
2. Store rank at each block boundary: O(n/b × log n) = O(n / log n) bits = o(n)
3. Within a block, use a precomputed lookup table of size 2^b = O(√n) entries

**For select**: Use superblocks (larger blocks) with binary search, plus a lookup table within superblocks.

### Dry Run: Rank Computation

Given B = [1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1] (n=12)

Block size b = 3 (simplified for illustration)

```
Blocks: [1,0,1] [1,0,1] [0,0,1] [1,0,1]
Block ranks:     0       2       4       6

Rank(7): block = 7/3 = 2, block rank = 4
         Scan B[6..7]: B[6]=0, B[7]=0 → add 0
         Rank(7) = 4

Rank(9): block = 9/3 = 3, block rank = 6
         Scan B[9..9]: B[9]=1 → add 1
         Rank(9) = 7
```

### Complexity

| Operation | Time | Extra Space |
|---|---|---|
| Rank | O(1) | o(n) bits |
| Select | O(1) | o(n) bits |

---

## 158.4 LOUDS: Level-Order Unary Degree Sequence

LOUDS represents a tree in 2n + o(n) bits while supporting O(1) child/parent queries.

### Encoding

1. Perform BFS traversal of the tree
2. For each node with d children, encode d 1s followed by a 0
3. The root is preceded by 110 (convention)

**Example**: Tree with root having 3 children, first child has 2 children:

```
Tree:
        A (3 children)
       /|\
      B C D (B has 2 children)
     / \
    E   F

BFS order: A, B, C, D, E, F
Degrees:   3, 2, 0, 0, 0, 0

Encoding: 1 1 1 1 0  1 1 0  0  0  0  0
          ^^^^^^^^    ^^^^
          A:3→1110    B:2→110

Full: 11 1110 110 0 0 0 0
      ^^ (start marker)
```

### Operations on LOUDS

Using rank/select on the bitvector:

- **Node to bit position**: node i → position of the i-th 0 in the bitvector
- **Child(i, j)**: The j-th child of node i is at a specific bit position derived from rank
- **Parent(i)**: Find which 1-block contains the position of node i

All O(1) with rank/select.

### Why 2n + o(n) bits?

Each of n nodes contributes exactly one 0 and d 1s (where d is the degree). Total 1s = n-1 (for a tree with n nodes, there are n-1 edges). Total 0s = n. So the bitvector has 2n-1 bits ≈ 2n bits.

---

## 158.5 Wavelet Trees

A wavelet tree is a succinct structure for rank/select on sequences over alphabet Σ.

### Construction

Given a sequence S[0..n-1] over alphabet {0, 1, ..., σ-1}:

1. Build a balanced binary tree on the alphabet
2. Each internal node stores a bitvector: for elements in its range, 0 = goes left, 1 = goes right
3. Leaves correspond to individual alphabet symbols

### Operations

| Operation | Time | Description |
|---|---|---|
| Access(i) | O(log σ) | Read S[i] |
| Rank(c, i) | O(log σ) | Count occurrences of c in S[0..i] |
| Select(c, k) | O(log σ) | Position of k-th occurrence of c |
| Range quantile query | O(log σ) | k-th smallest in S[l..r] |

### Example

S = "abracadabra", Σ = {a, b, c, d, r}, σ = 5

```
              [a,b,c,d,r]
             /           \
        [a,b,c]         [d,r]
        /     \         /   \
      [a,b]   [c]     [d]   [r]
      /   \
    [a]   [b]
```

Root bitvector: a→0, b→0, c→0, d→1, r→1
So root BV = [0,0,1,0,1,0,0,0,1,0,1,0] for "abracadabra"

Rank queries propagate down the tree, using bitvector rank at each level.

### Wavelet Matrix

A variant that reorders levels based on bit significance rather than alphabet order. Better for multi-dimensional data and succinct representations.

**Space**: n⌈log σ⌉ + o(n⌈log σ⌉) bits.

---

## 158.6 FM-Index

The FM-Index enables pattern matching in compressed text. It combines:
- **Burrows-Wheeler Transform (BWT)**: A reversible transformation of the text
- **Rank/Select**: On the BWT column

### How It Works

1. Build the BWT of text T (using suffix array)
2. Store the BWT column as a succinct bitvector with rank support
3. Store the first column F (just the character counts — implicit)
4. Pattern matching uses LF-mapping: given BWT[i], find F[j] where j = Rank(BWT[i], i)

### Pattern Matching (Backward Search)

```
Search(pattern P in FM-Index):
    lo = 0, hi = n - 1
    for i = |P|-1 down to 0:
        c = P[i]
        lo = C[c] + Rank(c, lo - 1) + 1
        hi = C[c] + Rank(c, hi)
        if lo > hi: return NOT FOUND
    return [lo, hi]  // SA range containing all occurrences
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Build FM-Index | O(n) | nH_k + o(n) bits |
| Count pattern P | O(|P|) | — |
| Locate occurrences | O(|P| + occ × log^(1+ε) n) | — |

Where H_k is the k-th order empirical entropy of the text.

**Application**: The BWT-based aligner BWA uses FM-Index to align DNA reads to a reference genome in compressed space.

---

## 158.7 Rank/Select on Non-Binary Alphabets

For sequences over larger alphabets:

| Structure | Space | Rank | Select |
|---|---|---|---|
| Direct bitvector | n log σ | O(log σ) | O(log σ) |
| Wavelet tree | n log σ + o(n log σ) | O(log σ) | O(log σ) |
| Alphabet partitioning | n log σ + o(n) | O(log log σ) | O(log log σ) |

---

## 158.8 Implementations

### C++: Succinct Bitvector with Rank/Select

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <cassert>

class SuccinctBitvector {
    std::vector<uint64_t> words;       // Packed bits
    std::vector<uint32_t> rankBlocks;  // Rank at block boundaries
    int n;                              // Number of bits
    int blockBits;                      // Bits per block
    int superBlockBits;                 // Bits per superblock
    std::vector<uint32_t> superRankBlocks;
    
    static int popcount(uint64_t x) {
        return __builtin_popcountll(x);
    }
    
public:
    SuccinctBitvector(const std::vector<int>& bits) : n(bits.size()) {
        // Pack bits into 64-bit words
        int numWords = (n + 63) / 64;
        words.resize(numWords, 0);
        for (int i = 0; i < n; i++) {
            if (bits[i])
                words[i / 64] |= (1ULL << (i % 64));
        }
        
        // Block size: (log n)^2 / 4 bits
        blockBits = std::max(1, (int)(std::log2(n) * std::log2(n) / 4));
        superBlockBits = blockBits * 32;
        
        // Build rank blocks
        rankBlocks.push_back(0);
        uint32_t count = 0;
        for (int i = 0; i < n; i++) {
            if (bits[i]) count++;
            if ((i + 1) % blockBits == 0)
                rankBlocks.push_back(count);
        }
        
        // Build superblocks
        superRankBlocks.push_back(0);
        count = 0;
        for (int i = 0; i < n; i++) {
            if (bits[i]) count++;
            if ((i + 1) % superBlockBits == 0)
                superRankBlocks.push_back(count);
        }
    }
    
    // O(1) rank: count 1s in B[0..i]
    int rank1(int i) const {
        if (i < 0) return 0;
        if (i >= n) i = n - 1;
        
        int superBlock = i / superBlockBits;
        int r = superRankBlocks[superBlock];
        
        int blockStart = superBlock * superBlockBits / blockBits;
        int block = i / blockBits;
        for (int b = blockStart; b < block; b++)
            r += rankBlocks[b + 1] - rankBlocks[b]; // Could be precomputed
        
        // Count within block using word-level popcount
        int wordStart = block * blockBits / 64;
        int wordEnd = i / 64;
        for (int w = wordStart; w < wordEnd; w++)
            r += popcount(words[w]);
        
        // Count remaining bits
        int lastWord = i / 64;
        int lastBit = i % 64;
        uint64_t mask = (1ULL << (lastBit + 1)) - 1;
        r += popcount(words[lastWord] & mask);
        
        return r;
    }
    
    // O(1) select: find position of k-th 1 (0-indexed)
    // Simplified O(log n) binary search version
    int select1(int k) const {
        if (k < 0) return -1;
        k++; // 1-indexed
        
        // Binary search on superblocks
        int lo = 0, hi = (int)superRankBlocks.size() - 1;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            if ((int)superRankBlocks[mid] < k)
                lo = mid + 1;
            else
                hi = mid;
        }
        
        int start = lo * superBlockBits;
        int base = (lo > 0) ? superRankBlocks[lo - 1] : 0;
        
        // Linear scan within superblock
        for (int i = start; i < n && i < start + superBlockBits; i++) {
            int word = i / 64;
            int bit = i % 64;
            if (words[word] & (1ULL << bit)) {
                base++;
                if (base == k) return i;
            }
        }
        return -1;
    }
    
    int rank0(int i) const { return i + 1 - rank1(i); }
};

int main() {
    std::vector<int> bits = {1,0,1,1,0,1,0,0,1,1,0,1};
    SuccinctBitvector bv(bits);
    
    std::cout << "Bitvector: 1 0 1 1 0 1 0 0 1 1 0 1\n\n";
    std::cout << "rank1(5)  = " << bv.rank1(5)  << "  (expected 4)\n";
    std::cout << "rank1(8)  = " << bv.rank1(8)  << "  (expected 5)\n";
    std::cout << "rank0(5)  = " << bv.rank0(5)  << "  (expected 2)\n";
    std::cout << "select1(2)= " << bv.select1(2) << "  (expected 3)\n";
    std::cout << "select1(4)= " << bv.select1(4) << "  (expected 5)\n";
    
    return 0;
}
```

### Python: Wavelet Tree

```python
class WaveletTree:
    """
    Wavelet tree for rank/select on sequences over arbitrary alphabets.
    
    Supports:
        - access(i): O(log σ)
        - rank(c, i): O(log σ)
        - select(c, k): O(log σ)
        - range_count(l, r, c): O(log σ)
    """
    
    def __init__(self, data, lo=None, hi=None):
        if lo is None:
            lo = min(data)
        if hi is None:
            hi = max(data)
        
        self.lo = lo
        self.hi = hi
        self.n = len(data)
        
        if lo == hi or not data:
            self.bv = []
            self.left = self.right = None
            return
        
        mid = (lo + hi) // 2
        
        # Bitvector: 0 = goes left (≤ mid), 1 = goes right (> mid)
        self.bv = [0] * (len(data) + 1)
        left_data = []
        right_data = []
        
        for i, val in enumerate(data):
            if val <= mid:
                self.bv[i + 1] = self.bv[i]
                left_data.append(val)
            else:
                self.bv[i + 1] = self.bv[i] + 1
                right_data.append(val)
        
        # Build prefix sum of bitvector for rank queries
        self.bv_prefix = [0] * (len(data) + 1)
        for i in range(len(data)):
            self.bv_prefix[i + 1] = self.bv_prefix[i] + (1 if data[i] > mid else 0)
        
        self.left = WaveletTree(left_data, lo, mid) if left_data else None
        self.right = WaveletTree(right_data, mid + 1, hi) if right_data else None
    
    def _rank(self, i):
        """Number of elements > mid in data[0..i-1]."""
        return self.bv_prefix[i]
    
    def access(self, i):
        """Return data[i]. O(log σ)"""
        if self.lo == self.hi:
            return self.lo
        
        mid = (self.lo + self.hi) // 2
        # Check if data[i] went left or right
        right_count = self._rank(i + 1)
        left_count = (i + 1) - right_count
        
        if self.bv_prefix[i + 1] == self.bv_prefix[i]:
            # Went left
            return self.left.access(left_count - 1) if self.left else self.lo
        else:
            # Went right
            return self.right.access(right_count - 1) if self.right else self.hi
    
    def rank(self, c, i):
        """Count occurrences of c in data[0..i]. O(log σ)"""
        if self.lo == self.hi:
            return i + 1
        
        mid = (self.lo + self.hi) // 2
        if c <= mid:
            new_i = (i + 1) - self._rank(i + 1) - 1  # Map to left subtree
            return self.left.rank(c, new_i) if self.left and new_i >= 0 else 0
        else:
            new_i = self._rank(i + 1) - 1  # Map to right subtree
            return self.right.rank(c, new_i) if self.right and new_i >= 0 else 0
    
    def select(self, c, k):
        """Find position of (k+1)-th occurrence of c. O(log σ)"""
        if self.lo == self.hi:
            return k  # All elements at this level are c
        
        mid = (self.lo + self.hi) // 2
        if c <= mid:
            pos = self.left.select(c, k) if self.left else -1
            if pos < 0: return -1
            # Map back: count how many right elements are before this position
            # This is simplified; full implementation needs inverse rank
            return self._select_map_left(pos)
        else:
            pos = self.right.select(c, k) if self.right else -1
            if pos < 0: return -1
            return self._select_map_right(pos)
    
    def _select_map_left(self, pos):
        """Map position in left subtree back to original array."""
        # Binary search for smallest i where left_count(i) > pos
        lo, hi = 0, self.n
        while lo < hi:
            mid = (lo + hi) // 2
            left_count = mid - self._rank(mid)
            if left_count <= pos:
                lo = mid + 1
            else:
                hi = mid
        return lo - 1
    
    def _select_map_right(self, pos):
        """Map position in right subtree back to original array."""
        lo, hi = 0, self.n
        while lo < hi:
            mid = (lo + hi) // 2
            right_count = self._rank(mid)
            if right_count <= pos:
                lo = mid + 1
            else:
                hi = mid
        return lo - 1

if __name__ == "__main__":
    data = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
    wt = WaveletTree(data)
    
    print(f"Data: {data}")
    print(f"access(3) = {wt.access(3)}  (expected 1)")
    print(f"access(5) = {wt.access(5)}  (expected 9)")
    print(f"rank(5, 8) = {wt.rank(5, 8)}  (expected 2)")
    print(f"rank(1, 3) = {wt.rank(1, 3)}  (expected 2)")
    print(f"select(5, 0) = {wt.select(5, 0)}  (expected 4)")
```

### Java: LOUDS Encoding

```java
import java.util.*;

/**
 * LOUDS (Level-Order Unary Degree Sequence) tree representation.
 * 
 * Encodes a rooted tree in ~2n bits using BFS order.
 * Supports O(1) child/parent queries with rank/select.
 */
public class LOUDSTree {
    private int[] bits;      // The LOUDS bitvector
    private int n;           // Number of nodes
    private int[] rankBlocks; // Rank at block boundaries
    
    /**
     * Build LOUDS encoding from a tree given as adjacency lists.
     * @param children children[i] = list of children of node i (BFS order)
     */
    public LOUDSTree(List<List<Integer>> children) {
        n = children.size();
        List<Integer> bitList = new ArrayList<>();
        
        // Start marker: 110
        bitList.add(1);
        bitList.add(1);
        bitList.add(0);
        
        // BFS encoding
        Queue<Integer> queue = new LinkedList<>();
        queue.offer(0);
        
        while (!queue.isEmpty()) {
            int node = queue.poll();
            List<Integer> kids = children.get(node);
            for (int i = 0; i < kids.size(); i++) {
                bitList.add(1); // One 1 per child
                queue.offer(kids.get(i));
            }
            bitList.add(0); // Terminator
        }
        
        bits = bitList.stream().mapToInt(Integer::intValue).toArray();
        
        // Build rank blocks
        int blockSize = Math.max(1, (int)(Math.log(n) * Math.log(n)));
        List<Integer> blocks = new ArrayList<>();
        int count = 0;
        for (int i = 0; i < bits.length; i++) {
            if (bits[i] == 1) count++;
            if ((i + 1) % blockSize == 0) blocks.add(count);
        }
        rankBlocks = blocks.stream().mapToInt(Integer::intValue).toArray();
    }
    
    /**
     * Rank: count 1s in bits[0..i].
     */
    public int rank1(int i) {
        int block = (i + 1) / (rankBlocks.length > 0 ? 
            (bits.length / rankBlocks.length) : bits.length);
        int r = (block < rankBlocks.length) ? rankBlocks[block] : 0;
        int start = block * (bits.length / Math.max(1, rankBlocks.length));
        for (int j = start; j <= i; j++) r += bits[j];
        return r;
    }
    
    /**
     * Get the number of children of node i.
     */
    public int degree(int nodeIndex) {
        // Find position of the (nodeIndex+1)-th 0 (after start marker)
        int pos = select0(nodeIndex + 2); // +2 for start marker 110
        int count = 0;
        while (pos + 1 + count < bits.length && bits[pos + 1 + count] == 1) count++;
        return count;
    }
    
    /**
     * Select: find position of (k+1)-th 0 in the bitvector.
     */
    public int select0(int k) {
        int count = 0;
        for (int i = 0; i < bits.length; i++) {
            if (bits[i] == 0) {
                count++;
                if (count == k) return i;
            }
        }
        return -1;
    }
    
    public int getNodeCount() { return n; }
    public int getBitvectorLength() { return bits.length; }
    
    public static void main(String[] args) {
        // Build a sample tree:
        //       0
        //      /|\
        //     1 2 3
        //    / \
        //   4   5
        
        List<List<Integer>> children = new ArrayList<>();
        children.add(Arrays.asList(1, 2, 3)); // Node 0
        children.add(Arrays.asList(4, 5));     // Node 1
        children.add(Collections.emptyList()); // Node 2
        children.add(Collections.emptyList()); // Node 3
        children.add(Collections.emptyList()); // Node 4
        children.add(Collections.emptyList()); // Node 5
        
        LOUDSTree louds = new LOUDSTree(children);
        
        System.out.println("Nodes: " + louds.getNodeCount());
        System.out.println("Bits: " + louds.getBitvectorLength());
        System.out.println("Space per node: " + 
            String.format("%.1f", (double)louds.getBitvectorLength() / louds.getNodeCount()) + " bits");
        System.out.println("Expected ~2 bits/node for large trees");
        
        // Show degree of each node
        for (int i = 0; i < louds.getNodeCount(); i++) {
            System.out.println("Node " + i + " degree: " + louds.degree(i));
        }
    }
}
```

---

## 158.9 Exercises

### Conceptual Exercises

1. **Information-theoretic bound**: How many bits are needed to represent a binary tree with n nodes? How does this compare to a pointer-based representation?

2. **Rank/Select tradeoff**: Explain why we need o(n) extra bits for O(1) rank. What happens if we try to use 0 extra bits?

3. **LOUDS vs pointers**: A LOUDS-encoded tree uses ~2n bits. A pointer-based tree uses ~64n bits. What operations does LOUDS sacrifice (or make slower)?

4. **FM-Index**: Why is the BWT useful for pattern matching? Explain the LF-mapping property.

5. **Wavelet tree**: Why is the time complexity O(log σ) for rank queries? What limits the performance?

### Programming Exercises

1. **Rank without lookup tables**: Implement O(log n) rank using only the block-level rank array (no sub-block lookup). Measure the speedup when adding a lookup table.

2. **Select with binary search**: Implement O(log² n) select using rank + binary search. Compare with the O(1) version.

3. **Succinct BST**: Implement a BST that stores only the LOUDS encoding plus an array of values. Support search, min, max operations.

4. **BWT construction**: Implement the Burrows-Wheeler Transform. Verify that it's reversible.

5. **Range minimum query**: Use a succinct bitvector to support RMQ in O(1) time with 2n + o(n) bits.

---

## 158.10 Interview Questions

### Conceptual Questions

1. **Q**: What is the difference between a succinct and an implicit data structure?
   **A**: An implicit structure uses exactly the information-theoretic minimum space (e.g., n bits for a subset). A succinct structure uses n + o(n) bits — slightly more than optimal — but supports efficient operations. Implicit structures may require O(n) time for simple queries; succinct structures aim for O(1) or O(polylog n).

2. **Q**: How does rank support enable other operations?
   **A**: Rank is the foundation. It enables: (1) select via binary search on rank, (2) tree navigation in LOUDS, (3) pattern matching in FM-Index via LF-mapping, (4) wavelet tree queries. Nearly every succinct structure builds on rank.

3. **Q**: Why is the FM-Index space-efficient?
   **A**: It stores only the BWT column (n characters) plus rank structures (o(n) bits). The suffix array is implicit — it can be sampled sparsely. Total space is nH_k + o(n) bits, where H_k is the empirical entropy. Highly compressible texts (like English) take much less than n log σ bits.

4. **Q**: When would you use a wavelet tree vs a hash table?
   **A**: Wavelet tree when: (1) you need rank/select on a sequence, (2) memory is critical, (3) you need range queries (k-th smallest in a range). Hash table when: you only need membership queries and have ample memory. Wavelet trees are better for compressed string processing; hash tables are better for general-purpose lookups.

### Coding Questions

1. **Q**: Implement O(1) rank on a bitvector using O(n / log n) extra space.
   **A**: Use blocks of size (log n)². Store cumulative rank at each block boundary (O(n / log² n) entries × log n bits each = O(n / log n) bits). Within a block, use a lookup table indexed by the block's bit pattern.

2. **Q**: Given a binary tree, encode it in LOUDS format and implement child(i, j).
   **A**: BFS traversal, emit d 1s and 1 0 for each node with d children. Child(i, j) = position of the j-th 1 in node i's block. Use rank to find node boundaries.

3. **Q**: Implement backward search on an FM-Index for a pattern.
   **A**: Maintain [lo, hi] range. For each character c of pattern (right to left): lo = C[c] + Rank(c, lo-1) + 1, hi = C[c] + Rank(c, hi). If lo > hi, pattern not found.

---

## 158.11 Cross-References

- **Chapter 5: Bit Manipulation** — Foundation for bit-level operations used in succinct structures
- **Chapter 30: Tries** — Prefix trees that wavelet trees and FM-Index relate to
- **Chapter 87: Suffix Trees** — Suffix arrays and BWT are central to FM-Index
- **Chapter 157: Concurrent Data Structures** — Space-efficient concurrent structures
- **Chapter 160: Parallel Algorithms** — Parallel construction of succinct structures
- **Chapter 163: Advanced Mathematics** — Information theory, entropy bounds
- **Chapter 102: Bloom Filters** — Another space-efficient probabilistic structure

---

## Summary

| Structure | Space | Key Operations | Time |
|---|---|---|---|
| Bitvector + Rank/Select | n + o(n) bits | Rank, Select | O(1) |
| LOUDS | 2n + o(n) bits | Child, Parent | O(1) |
| Wavelet Tree | n log σ bits | Access, Rank, Select | O(log σ) |
| FM-Index | nH_k + o(n) bits | Pattern search | O(m) |
| Wavelet Matrix | n log σ + o(n) bits | Rank, Select | O(log σ) |

**Key Takeaway**: Succinct data structures achieve near-optimal space while maintaining efficient operations. The key insight is that a small amount of extra information (o(n) bits) can dramatically speed up queries. Rank and select on bitvectors are the fundamental building blocks. These structures are essential for memory-constrained applications like genomic indexing and large-scale search engines.
