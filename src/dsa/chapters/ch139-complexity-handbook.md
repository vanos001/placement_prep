# Chapter 139: Complexity Handbook

## Prerequisites
- Basic understanding of algorithms
- Familiarity with Big-O notation

## Interview Frequency: ★★★★★

This chapter is a comprehensive reference for time and space complexity of common algorithms and data structures. Use it to quickly look up complexities when designing solutions or analyzing performance.

---

## 139.1 Understanding Complexity

### Big-O Notation

| Notation | Name | Meaning |
|---|---|---|
| O(1) | Constant | Doesn't depend on input size |
| O(log n) | Logarithmic | Halves the problem each step |
| O(n) | Linear | Proportional to input size |
| O(n log n) | Linearithmic | Efficient sorting complexity |
| O(n²) | Quadratic | Nested loops over input |
| O(n³) | Cubic | Triple nested loops |
| O(2^n) | Exponential | Doubles with each input element |
| O(n!) | Factorial | Permutations |

### Amortized vs Average

- **Amortized:** The average cost per operation over a sequence (e.g., dynamic array push_back is O(1) amortized, though individual resizes are O(n))
- **Average:** Expected cost assuming some input distribution (e.g., quicksort is O(n log n) average)
- **Worst case:** Maximum possible cost for any input of size n

### Common Misconceptions

| Statement | Reality |
|---|---|
| "O(n²) is always slower than O(n log n)" | For small n, constants matter more |
| "O(1) means fast" | O(1) could be a very large constant |
| "Worst case is the common case" | Average case often dominates in practice |
| "Space complexity doesn't matter" | Memory is a real constraint |

---

## 139.2 Sorting Algorithms

| Algorithm | Best | Average | Worst | Space | Stable | In-Place |
|---|---|---|---|---|---|---|
| Bubble Sort | O(n) | O(n²) | O(n²) | O(1) | Yes | Yes |
| Selection Sort | O(n²) | O(n²) | O(n²) | O(1) | No | Yes |
| Insertion Sort | O(n) | O(n²) | O(n²) | O(1) | Yes | Yes |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes | No |
| Quick Sort | O(n log n) | O(n log n) | O(n²) | O(log n) | No | Yes |
| Heap Sort | O(n log n) | O(n log n) | O(n log n) | O(1) | No | Yes |
| Counting Sort | O(n+k) | O(n+k) | O(n+k) | O(k) | Yes | No |
| Radix Sort | O(d(n+k)) | O(d(n+k)) | O(d(n+k)) | O(n+k) | Yes | No |
| Tim Sort | O(n) | O(n log n) | O(n log n) | O(n) | Yes | No |

**Key:** n = number of elements, k = range of values, d = number of digits

### When to Use Which Sort

| Situation | Best Choice |
|---|---|
| General purpose | Quick Sort (in-place) or Merge Sort (stable) |
| Nearly sorted data | Insertion Sort or Tim Sort |
| Small n (< 50) | Insertion Sort |
| Need stability | Merge Sort or Tim Sort |
| Integer keys in small range | Counting Sort |
| Integer keys with many digits | Radix Sort |
| Memory constrained | Heap Sort (in-place, O(1) extra) |
| Guaranteed O(n log n) | Merge Sort or Heap Sort |

---

## 139.3 Data Structure Operations

### Arrays and Lists

| Operation | Dynamic Array | Singly Linked List | Doubly Linked List |
|---|---|---|---|
| Access by index | O(1) | O(n) | O(n) |
| Search | O(n) | O(n) | O(n) |
| Insert at front | O(n) | O(1) | O(1) |
| Insert at back | O(1) amortized | O(1) with tail | O(1) with tail |
| Insert at middle | O(n) | O(n) to find + O(1) | O(n) to find + O(1) |
| Delete at front | O(n) | O(1) | O(1) |
| Delete at back | O(1) | O(n) | O(1) |
| Delete at middle | O(n) | O(n) to find + O(1) | O(n) to find + O(1) |

### Hash Tables

| Operation | Average | Worst Case |
|---|---|---|
| Insert | O(1) | O(n) |
| Search | O(1) | O(n) |
| Delete | O(1) | O(n) |

**Worst case occurs with many hash collisions.** With a good hash function and resizing, average case dominates.

### Trees

| Operation | BST (balanced) | BST (unbalanced) | Heap | Trie |
|---|---|---|---|---|
| Insert | O(log n) | O(n) | O(log n) | O(m) |
| Search | O(log n) | O(n) | O(n) | O(m) |
| Delete | O(log n) | O(n) | O(log n) | O(m) |
| Min/Max | O(log n) | O(n) | O(1) | O(m·k) |
| Successor | O(log n) | O(n) | O(n) | O(m·k) |

**m** = key length (for Trie), **k** = alphabet size

### Stacks and Queues

| Operation | Stack | Queue | Deque |
|---|---|---|---|
| Push/Enqueue | O(1) | O(1) | O(1) |
| Pop/Dequeue | O(1) | O(1) | O(1) |
| Peek | O(1) | O(1) | O(1) |
| Search | O(n) | O(n) | O(n) |

### Priority Queues

| Operation | Binary Heap | Fibonacci Heap | Sorted Array |
|---|---|---|---|
| Insert | O(log n) | O(1) amortized | O(n) |
| Extract Min | O(log n) | O(log n) amortized | O(1) |
| Peek Min | O(1) | O(1) | O(1) |
| Decrease Key | O(log n) | O(1) amortized | O(n) |
| Merge | O(n) | O(1) | O(n) |

---

## 139.4 Graph Algorithms

### Traversal

| Algorithm | Time | Space | Use Case |
|---|---|---|---|
| BFS | O(V+E) | O(V) | Shortest path (unweighted), level order |
| DFS | O(V+E) | O(V) | Cycle detection, topological sort, connected components |

### Shortest Path

| Algorithm | Time | Space | Constraints |
|---|---|---|---|
| BFS | O(V+E) | O(V) | Unweighted |
| Dijkstra | O((V+E)log V) | O(V) | Non-negative weights |
| Bellman-Ford | O(VE) | O(V) | Negative weights, detects negative cycles |
| Floyd-Warshall | O(V³) | O(V²) | All pairs, dense graphs |
| SPFA | O(VE) avg | O(V) | Negative weights (faster in practice) |

### Minimum Spanning Tree

| Algorithm | Time | Space | Notes |
|---|---|---|---|
| Kruskal | O(E log E) | O(V) | Sort edges, use DSU |
| Prim (binary heap) | O((V+E)log V) | O(V) | Better for dense graphs |
| Prim (Fibonacci heap) | O(E + V log V) | O(V) | Theoretically optimal |

### Other Graph Algorithms

| Algorithm | Time | Space | Purpose |
|---|---|---|---|
| Topological Sort | O(V+E) | O(V) | Ordering in DAG |
| SCC (Kosaraju) | O(V+E) | O(V) | Strongly connected components |
| SCC (Tarjan) | O(V+E) | O(V) | Strongly connected components |
| Articulation Points | O(V+E) | O(V) | Find cut vertices |
| Bridges | O(V+E) | O(V) | Find cut edges |
| Bipartite Check | O(V+E) | O(V) | 2-coloring |
| Max Flow (Dinic) | O(V²E) | O(V+E) | Network flow |
| Max Flow (Edmonds-Karp) | O(VE²) | O(V+E) | Network flow (simpler) |
| Hopcroft-Karp | O(E√V) | O(V) | Bipartite matching |

---

## 139.5 Common Recurrences

| Recurrence | Solution | Example Algorithm |
|---|---|---|
| T(n) = T(n/2) + O(1) | O(log n) | Binary search |
| T(n) = T(n/2) + O(n) | O(n) | Median finding, quickselect avg |
| T(n) = T(n-1) + O(1) | O(n) | Linear scan |
| T(n) = T(n-1) + O(n) | O(n²) | Selection sort, insertion sort worst |
| T(n) = 2T(n/2) + O(1) | O(n) | Tree traversal |
| T(n) = 2T(n/2) + O(n) | O(n log n) | Merge sort, quicksort avg |
| T(n) = 2T(n/2) + O(n²) | O(n²) | Certain divide-and-conquer |
| T(n) = 2T(n-1) + O(1) | O(2^n) | Fibonacci (naive), Tower of Hanoi |
| T(n) = T(n-1) + T(n-2) + O(1) | O(φ^n) ≈ O(1.618^n) | Fibonacci (naive recursive) |
| T(n) = 4T(n/2) + O(n) | O(n²) | Karatsuba-like (without optimization) |
| T(n) = T(n/2) + O(log n) | O(log²n) | Certain search problems |

### Solving Recurrences

**Method 1: Substitution**
Guess the solution and prove by induction.

**Method 2: Recursion Tree**
Draw the tree, sum costs at each level, multiply by number of levels.

**Method 3: Master Theorem**
For T(n) = aT(n/b) + O(n^d):
- If a < b^d: T(n) = O(n^d)
- If a = b^d: T(n) = O(n^d log n)
- If a > b^d: T(n) = O(n^(log_b a))

---

## 139.6 String Algorithms

| Algorithm | Time | Space | Purpose |
|---|---|---|---|
| KMP | O(n+m) | O(m) | Single pattern matching |
| Z-Algorithm | O(n+m) | O(n+m) | Pattern matching + Z-values |
| Rabin-Karp | O(n+m) avg | O(1) | Rolling hash matching |
| Aho-Corasick | O(n+m+z) | O(m·k) | Multiple pattern matching |
| Suffix Array | O(n log n) | O(n) | Suffix sorting |
| Suffix Automaton | O(n) | O(n) | Substring queries |
| Manacher | O(n) | O(n) | Longest palindromic substring |
| Lyndon Factorization | O(n) | O(n) | Minimal rotation, string structure |

**n** = text length, **m** = pattern length, **z** = number of matches, **k** = alphabet size

---

## 139.7 Dynamic Programming

| Problem | Time | Space | Notes |
|---|---|---|---|
| Fibonacci | O(n) | O(1) | Bottom-up with two variables |
| Knapsack (0/1) | O(nW) | O(W) | W = capacity |
| Knapsack (unbounded) | O(nW) | O(W) | Items can repeat |
| LCS | O(nm) | O(min(n,m)) | Rolling array optimization |
| Edit Distance | O(nm) | O(min(n,m)) | Rolling array optimization |
| Matrix Chain | O(n³) | O(n²) | Interval DP |
| LIS | O(n log n) | O(n) | With binary search |
| Coin Change | O(nS) | O(S) | S = target sum |
| Subset Sum | O(nS) | O(S) | S = target sum |
| TSP (bitmask) | O(2^n · n²) | O(2^n · n) | n ≤ 20 |

---

## 139.8 Number Theory

| Algorithm | Time | Notes |
|---|---|---|
| GCD (Euclidean) | O(log(min(a,b))) | |
| LCM | O(log(min(a,b))) | lcm = a*b/gcd |
| Sieve of Eratosthenes | O(n log log n) | Find primes up to n |
| Modular exponentiation | O(log n) | Fast power |
| Modular inverse | O(log p) | Fermat's little theorem (p prime) |
| Extended GCD | O(log(min(a,b))) | Find x,y in ax+by=gcd |
| Miller-Rabin | O(k log²n) | Primality test |
| Pollard's Rho | O(n^(1/4)) | Factorization |

---

## 139.9 Geometry

| Algorithm | Time | Notes |
|---|---|---|
| Convex Hull (Graham scan) | O(n log n) | |
| Convex Hull (Andrew's) | O(n log n) | Simpler implementation |
| Closest Pair | O(n log n) | Divide and conquer |
| Point in Polygon | O(n) | Ray casting |
| Line Intersection | O(1) | Two lines |
| Sweep Line | O(n log n) | Many intersection/overlap problems |

---

## 139.10 Space Complexity Patterns

| Pattern | Space | Example |
|---|---|---|
| No extra space | O(1) | Two pointers, in-place algorithms |
| Hash set/map | O(n) | Caching, frequency counting |
| DP table | O(n²) or O(n) | With rolling array |
| Graph adjacency list | O(V+E) | |
| Graph adjacency matrix | O(V²) | Dense graphs |
| Recursion stack | O(depth) | DFS: O(V), balanced tree: O(log n) |
| Priority queue | O(V) | Dijkstra, Prim |
| DSU | O(V) | Union-Find |

---

## 139.11 Complexity Comparison Chart

```
Operations  | n=10    | n=100    | n=10³    | n=10⁶    | n=10⁹
────────────┼─────────┼──────────┼──────────┼──────────┼─────────
O(1)        | 1       | 1        | 1        | 1        | 1
O(log n)    | 3       | 7        | 10       | 20       | 30
O(n)        | 10      | 100      | 10³      | 10⁶      | 10⁹
O(n log n)  | 33      | 664      | 10⁴      | 2×10⁷    | 3×10¹⁰
O(n²)       | 100     | 10⁴      | 10⁶      | 10¹²     | 10¹⁸
O(n³)       | 10³     | 10⁶      | 10⁹      | 10¹⁸     | 10²⁷
O(2^n)      | 10²⁴    | 10³⁰     | 10³⁰¹    | ∞        | ∞
```

**Practical limits** (assuming 10⁸ operations/second, 1 second time limit):
- O(n) → n ≤ 10⁸
- O(n log n) → n ≤ 10⁷
- O(n²) → n ≤ 10⁴
- O(n³) → n ≤ 500
- O(2^n) → n ≤ 25

---

## 139.12 Exercises

1. **Determine the complexity** of the following code:
```cpp
for (int i = 1; i < n; i *= 2)
    for (int j = 0; j < n; j++)
        // O(1) work
```
*Answer: O(n log n) — outer loop runs log n times, inner loop runs n times.*

2. **Determine the complexity:**
```cpp
for (int i = 0; i < n; i++)
    for (int j = i; j < n; j++)
        // O(1) work
```
*Answer: O(n²) — sum of 1+2+...+n = n(n+1)/2.*

3. **What's the time complexity** of building a heap from an unsorted array? *Answer: O(n) — not O(n log n)!*

4. **Compare** the space complexity of recursive vs iterative Fibonacci. *Answer: O(n) stack vs O(1).*

5. **If an algorithm runs in O(n²) time and processes 10⁴ elements in 1 second**, how many elements can it process in 10 seconds? *Answer: ~31,623 (since (31623)² ≈ 10×(10⁴)²).*

---

## 139.13 Interview Questions

1. **"What's the time complexity of quicksort?"** — Average O(n log n), worst O(n²). Worst case happens with already sorted input and bad pivot selection.

2. **"Is O(n log n) always better than O(n²)?"** — No. For small n, the constant factor matters. Insertion sort (O(n²)) beats merge sort (O(n log n)) for n < ~50.

3. **"What's the complexity of hash table operations?"** — Average O(1), worst O(n) with many collisions. Amortized O(1) with resizing.

4. **"How do you analyze recursive algorithms?"** — Write the recurrence relation, then solve using substitution, recursion tree, or the Master Theorem.

5. **"What's the space complexity of BFS?"** — O(V) for the queue and visited set. In the worst case (star graph), the queue holds O(V) vertices.

6. **"Can an algorithm have different time and space complexity trade-offs?"** — Yes! You can often trade space for time (memoization) or time for space (recomputing).

---

## 139.14 Cross-References

- **Sorting:** Chapter on Sorting Algorithms
- **Graph Algorithms:** Chapters on BFS, DFS, Dijkstra, etc.
- **Data Structures:** Chapters on Hash Maps, Trees, Heaps, etc.
- **DP:** Chapter on Dynamic Programming
- **String Algorithms:** Chapters on KMP, Aho-Corasick, Suffix Arrays
- **Number Theory:** Chapter on Modular Arithmetic, Primes
- **Algorithm Selection:** Chapter 140 (Algorithm Selection Guide)
- **Data Structure Selection:** Chapter 141 (Data Structure Selection Guide)

---

## Summary

| Category | Key Insight |
|---|---|
| Sorting | O(n log n) is optimal for comparison sorts |
| Searching | Hash O(1) avg, BST O(log n), Array O(n) |
| Graphs | BFS/DFS O(V+E), Dijkstra O((V+E)log V) |
| DP | Depends on state count × transition cost |
| Strings | Most run in O(n) or O(n log n) |
| Recurrences | Master Theorem for T(n) = aT(n/b) + O(n^d) |
| Practical limit | ~10⁸ operations per second |
