# Appendix B: Complexity Cheat Sheet

A comprehensive reference for the time and space complexity of every major data structure, algorithm, and operation.

---

## Notation

| Symbol | Meaning |
|--------|---------|
| O(1) | Constant |
| O(log n) | Logarithmic |
| O(n) | Linear |
| O(n log n) | Linearithmic |
| O(n²) | Quadratic |
| O(n³) | Cubic |
| O(2ⁿ) | Exponential |
| O(n!) | Factorial |

---

## 1. Array Operations

| Operation | Time | Space | Notes |
|-----------|------|-------|-------|
| Access by index | O(1) | O(1) | |
| Search (unsorted) | O(n) | O(1) | Linear scan |
| Search (sorted) | O(log n) | O(1) | Binary search |
| Insert at end | O(1)* | O(1)* | Amortized for dynamic arrays |
| Insert at position | O(n) | O(1) | Shifts elements |
| Delete at end | O(1) | O(1) | |
| Delete at position | O(n) | O(1) | Shifts elements |
| Copy | O(n) | O(n) | |

---

## 2. Linked List Operations

### Singly Linked List

| Operation | Time | Space |
|-----------|------|-------|
| Access by index | O(n) | O(1) |
| Search | O(n) | O(1) |
| Insert at head | O(1) | O(1) |
| Insert at tail | O(n) | O(1) | O(1) with tail pointer |
| Insert after node | O(1) | O(1) | If you have the node |
| Delete head | O(1) | O(1) |
| Delete node | O(n) | O(1) | Need to find predecessor |
| Delete with given node | O(1) | O(1) | Copy next, delete next |

### Doubly Linked List

| Operation | Time | Space |
|-----------|------|-------|
| Access by index | O(n) | O(1) |
| Search | O(n) | O(1) |
| Insert at head/tail | O(1) | O(1) |
| Insert after/before node | O(1) | O(1) |
| Delete head/tail | O(1) | O(1) |
| Delete node | O(1) | O(1) | If you have the node |

---

## 3. Stack and Queue

| Operation | Stack | Queue | Deque |
|-----------|-------|-------|-------|
| Push | O(1) | O(1) | O(1) |
| Pop | O(1) | O(1) | O(1) |
| Top/Front/Back | O(1) | O(1) | O(1) |
| Search | O(n) | O(n) | O(n) |
| Size | O(1) | O(1) | O(1) |

---

## 4. Hash Table

| Operation | Average | Worst | Notes |
|-----------|---------|-------|-------|
| Insert | O(1) | O(n) | Worst: all collisions |
| Delete | O(1) | O(n) | |
| Search | O(1) | O(n) | |
| Iterate | O(n) | O(n) | |

---

## 5. Binary Heap / Priority Queue

| Operation | Time | Notes |
|-----------|------|-------|
| Insert | O(log n) | Bubble up |
| Extract min/max | O(log n) | Bubble down |
| Peek | O(1) | |
| Decrease key | O(log n)* | With index tracking |
| Build from array | O(n) | Heapify |
| Merge two heaps | O(n) | |
| Delete arbitrary | O(n) | O(log n) with index |

---

## 6. Binary Search Tree (BST)

### Balanced BST (AVL, Red-Black, etc.)

| Operation | Average | Worst (balanced) | Worst (unbalanced) |
|-----------|---------|-------------------|---------------------|
| Search | O(log n) | O(log n) | O(n) |
| Insert | O(log n) | O(log n) | O(n) |
| Delete | O(log n) | O(log n) | O(n) |
| Min/Max | O(log n) | O(log n) | O(n) |
| Successor/Predecessor | O(log n) | O(log n) | O(n) |
| In-order traversal | O(n) | O(n) | O(n) |
| K-th smallest | O(log n)* | O(log n)* | O(n) |

*Augmented BST with subtree sizes.

### C++ `std::set` / `std::map` (Red-Black Tree)

| Operation | Time |
|-----------|------|
| Insert | O(log n) |
| Erase | O(log n) |
| Find | O(log n) |
| Count | O(log n) |
| Lower bound | O(log n) |
| Upper bound | O(log n) |
| Size | O(1) |
| Iteration (next element) | O(1) amortized |

---

## 7. Trie (Prefix Tree)

Let L = length of the string.

| Operation | Time | Space |
|-----------|------|-------|
| Insert | O(L) | O(L) per word |
| Search | O(L) | O(1) |
| Prefix search | O(L) | O(1) |
| Delete | O(L) | O(1) |
| Autocomplete | O(L + k) | k = number of results |

**Space:** O(ALPHABET_SIZE × N × L) worst case, much less with path compression.

---

## 8. Union-Find (Disjoint Set Union)

| Operation | Amortized | Worst (no optimization) |
|-----------|-----------|-------------------------|
| Find | O(α(n)) ≈ O(1) | O(n) |
| Union | O(α(n)) ≈ O(1) | O(n) |
| Connected | O(α(n)) ≈ O(1) | O(n) |
| Build (n elements) | O(n) | O(n) |

**With path compression + union by rank:** α(n) is the inverse Ackermann function, effectively ≤ 4 for all practical n.

---

## 9. Segment Tree

| Operation | Time | Space |
|-----------|------|-------|
| Build | O(n) | O(n) |
| Point update | O(log n) | O(1) |
| Range query | O(log n) | O(1) |
| Range update (lazy) | O(log n) | O(1) |
| K-th element (with merge sort tree) | O(log²n) | O(n log n) |

---

## 10. Fenwick Tree (Binary Indexed Tree)

| Operation | Time | Space |
|-----------|------|-------|
| Build | O(n log n) | O(n) |
| Point update | O(log n) | O(1) |
| Prefix sum query | O(log n) | O(1) |
| Range update + point query | O(log n) | O(1) |
| Range update + range query | O(log n) | O(n) |

---

## 11. Sparse Table

| Operation | Time | Space |
|-----------|------|-------|
| Build | O(n log n) | O(n log n) |
| Query (idempotent: min, max, gcd) | O(1) | |
| Query (non-idempotent: sum) | O(log n) | |

---

## 12. Sorting Algorithms

| Algorithm | Best | Average | Worst | Space | Stable | In-Place |
|-----------|------|---------|-------|-------|--------|----------|
| Bubble Sort | O(n) | O(n²) | O(n²) | O(1) | Yes | Yes |
| Selection Sort | O(n²) | O(n²) | O(n²) | O(1) | No | Yes |
| Insertion Sort | O(n) | O(n²) | O(n²) | O(1) | Yes | Yes |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes | No |
| Quick Sort | O(n log n) | O(n log n) | O(n²) | O(log n) | No | Yes |
| Heap Sort | O(n log n) | O(n log n) | O(n log n) | O(1) | No | Yes |
| Counting Sort | O(n + k) | O(n + k) | O(n + k) | O(k) | Yes | No |
| Radix Sort | O(d(n + k)) | O(d(n + k)) | O(d(n + k)) | O(n + k) | Yes | No |
| Bucket Sort | O(n + k) | O(n + k) | O(n²) | O(n + k) | Yes | No |
| Tim Sort | O(n) | O(n log n) | O(n log n) | O(n) | Yes | No |
| Intro Sort | O(n log n) | O(n log n) | O(n log n) | O(log n) | No | Yes |

**C++ `std::sort`:** Intro Sort (hybrid of quicksort, heapsort, insertion sort). O(n log n) worst case.

---

## 13. Graph Algorithms

### Traversal

| Algorithm | Time | Space | Notes |
|-----------|------|-------|-------|
| BFS | O(V + E) | O(V) | Queue-based |
| DFS | O(V + E) | O(V) | Stack/recursion |
| Iterative DFS | O(V + E) | O(V) | Explicit stack |

### Shortest Path

| Algorithm | Time | Space | Constraints |
|-----------|------|-------|-------------|
| Dijkstra (binary heap) | O((V + E) log V) | O(V) | Non-negative weights |
| Dijkstra (Fibonacci heap) | O(V log V + E) | O(V) | Non-negative weights |
| Bellman-Ford | O(VE) | O(V) | Negative edges OK |
| SPFA (average) | O(E) | O(V) | Can be O(VE) worst case |
| Floyd-Warshall | O(V³) | O(V²) | All-pairs |
| BFS (unweighted) | O(V + E) | O(V) | Unit weights |
| DAG shortest path | O(V + E) | O(V) | DAG only |
| A* | O(E) avg | O(V) | With heuristic |

### Minimum Spanning Tree

| Algorithm | Time | Space | Notes |
|-----------|------|-------|-------|
| Kruskal | O(E log E) | O(V) | Edge list + DSU |
| Prim (binary heap) | O((V + E) log V) | O(V) | Better for dense graphs |
| Prim (adjacency matrix) | O(V²) | O(V²) | Simple implementation |
| Borůvka | O(E log V) | O(V) | Parallel-friendly |

### Other Graph Algorithms

| Algorithm | Time | Space |
|-----------|------|-------|
| Topological Sort | O(V + E) | O(V) |
| Detect cycle (directed) | O(V + E) | O(V) |
| Detect cycle (undirected) | O(V + E) | O(V) |
| Strongly Connected Components (Tarjan) | O(V + E) | O(V) |
| Strongly Connected Components (Kosaraju) | O(V + E) | O(V) |
| Bridge finding | O(V + E) | O(V) |
| Articulation point finding | O(V + E) | O(V) |
| Eulerian path/circuit | O(V + E) | O(V) |
| Bipartite check | O(V + E) | O(V) |
| Max Flow (Edmonds-Karp) | O(VE²) | O(V²) |
| Max Flow (Dinic) | O(V²E) | O(V + E) |
| Max Flow (Push-Relabel) | O(V²√E) | O(V²) |
| Hungarian Algorithm | O(V³) | O(V²) |
| Tree diameter | O(V) | O(V) |
| LCA (binary lifting) | O(V log V) build, O(log V) query | O(V log V) |

---

## 14. String Algorithms

Let n = text length, m = pattern length, k = number of matches.

| Algorithm | Preprocessing | Search | Space |
|-----------|---------------|--------|-------|
| Naive | O(1) | O(nm) | O(1) |
| KMP | O(m) | O(n + k) | O(m) |
| Z Algorithm | O(n + m) | O(n + k) | O(n + m) |
| Rabin-Karp | O(m) | O(n + m) avg, O(nm) worst | O(1) |
| Aho-Corasick | O(m) | O(n + k) | O(m × ALPHABET) |
| Boyer-Moore | O(m + ALPHABET) | O(n/m) best, O(nm) worst | O(m + ALPHABET) |
| Suffix Array (SA-IS) | O(n) | O(m log n) | O(n) |
| Suffix Array (naive) | O(n log²n) | O(m log n) | O(n) |
| LCP Array (Kasai) | O(n) | | O(n) |
| Suffix Tree | O(n) | O(m + k) | O(n) |
| Manacher's | O(n) | O(n) | O(n) |

---

## 15. Dynamic Programming

| Problem Type | Time | Space | Example |
|-------------|------|-------|---------|
| 1D DP | O(n) | O(n) or O(1) | Fibonacci, climbing stairs |
| 2D DP (n×m grid) | O(nm) | O(nm) or O(m) | LCS, edit distance |
| Interval DP | O(n³) | O(n²) | Matrix chain, palindrome partition |
| Bitmask DP | O(2ⁿ × n) | O(2ⁿ) | TSP, subset problems |
| Digit DP | O(digits × states) | O(digits × states) | Count numbers with property |
| Tree DP | O(n) | O(n) | Tree diameter, independent set |
| Knapsack (0/1) | O(nW) | O(W) | |
| Knapsack (unbounded) | O(nW) | O(W) | |
| LIS (with binary search) | O(n log n) | O(n) | |
| LCS | O(nm) | O(min(n,m)) | Space-optimized |

---

## 16. Number Theory

| Algorithm | Time | Notes |
|-----------|------|-------|
| GCD (Euclidean) | O(log(min(a,b))) | |
| LCM | O(log(min(a,b))) | lcm(a,b) = a/gcd(a,b)*b |
| Sieve of Eratosthenes | O(n log log n) | |
| Linear Sieve | O(n) | |
| Modular exponentiation | O(log n) | |
| Modular inverse (Fermat) | O(log p) | p must be prime |
| Extended Euclidean | O(log(min(a,b))) | |
| Factorization (trial) | O(√n) | |
| Factorization (Pollard's Rho) | O(n^(1/4)) | Expected |
| Miller-Rabin primality | O(k log²n) | k witnesses |
| Euler's totient | O(√n) | |
| Sieve for Euler's totient | O(n log log n) | |

---

## 17. Geometry

| Algorithm | Time |
|-----------|------|
| Convex hull (Graham scan) | O(n log n) |
| Convex hull (Andrew's monotone chain) | O(n log n) |
| Point in polygon | O(n) |
| Closest pair of points | O(n log n) |
| Line segment intersection | O(n log n) |
| Polygon area (Shoelace) | O(n) |

---

## 18. Common STL Operations

### `std::vector`

| Operation | Time |
|-----------|------|
| `push_back` | O(1) amortized |
| `pop_back` | O(1) |
| `insert` | O(n) |
| `erase` | O(n) |
| `operator[]` | O(1) |
| `at` | O(1) |
| `front` / `back` | O(1) |
| `size` / `empty` | O(1) |
| `reserve` | O(n) |
| `resize` | O(n) |
| `clear` | O(n) |
| `shrink_to_fit` | O(n) |

### `std::set` / `std::map`

| Operation | Time |
|-----------|------|
| `insert` / `emplace` | O(log n) |
| `erase` | O(log n) |
| `find` / `count` / `contains` | O(log n) |
| `lower_bound` / `upper_bound` | O(log n) |
| `size` / `empty` | O(1) |
| Iteration (next element) | O(1) amortized |

### `std::unordered_set` / `std::unordered_map`

| Operation | Average | Worst |
|-----------|---------|-------|
| `insert` / `emplace` | O(1) | O(n) |
| `erase` | O(1) | O(n) |
| `find` / `count` / `contains` | O(1) | O(n) |
| `size` / `empty` | O(1) | O(1) |
| Iteration (next element) | O(1) | O(1) |

### `std::priority_queue`

| Operation | Time |
|-----------|------|
| `push` | O(log n) |
| `pop` | O(log n) |
| `top` | O(1) |
| `size` / `empty` | O(1) |

### `std::sort`

| Operation | Time |
|-----------|------|
| `sort` | O(n log n) |
| `stable_sort` | O(n log n) |
| `partial_sort` | O(n log k) |
| `nth_element` | O(n) average |
| `is_sorted` | O(n) |
| `binary_search` | O(log n) |
| `lower_bound` / `upper_bound` | O(log n) |

---

## 19. Space Complexity Summary

| Data Structure | Space |
|----------------|-------|
| Array | O(n) |
| Linked List | O(n) |
| Hash Table | O(n) |
| BST | O(n) |
| Heap | O(n) |
| Trie | O(ALPHABET × n × L) |
| DSU | O(n) |
| Segment Tree | O(n) |
| Fenwick Tree | O(n) |
| Sparse Table | O(n log n) |
| Adjacency Matrix | O(V²) |
| Adjacency List | O(V + E) |
| Edge List | O(E) |

---

## 20. Decision Guide

| Need | Data Structure | Complexity |
|------|---------------|------------|
| Fast lookup by key | Hash Table | O(1) avg |
| Ordered traversal | BST (set/map) | O(log n) |
| Min/Max extraction | Heap (priority_queue) | O(log n) |
| Range sum query | Fenwick Tree | O(log n) |
| Range min/max query | Segment Tree | O(log n) |
| Range update + query | Segment Tree + Lazy | O(log n) |
| Disjoint sets | DSU | O(α(n)) |
| String matching | KMP / Z Algorithm | O(n) |
| Prefix queries | Trie | O(L) |
| Shortest path (non-negative) | Dijkstra | O((V+E)log V) |
| Shortest path (negative edges) | Bellman-Ford | O(VE) |
| All-pairs shortest path | Floyd-Warshall | O(V³) |
| MST | Kruskal / Prim | O(E log V) |
| Topological order | DFS / BFS | O(V + E) |
| Connected components | DFS / BFS / DSU | O(V + E) |

---

*Print this cheat sheet and keep it next to your keyboard during practice. Over time, you'll memorize it naturally.*
