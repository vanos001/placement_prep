# Chapter 166: Master Indexes

## Quick Reference Indexes for the Entire Book

This chapter provides multiple cross-referenced indexes to help you quickly find algorithms, data structures, patterns, complexity classes, and formulas. Use it as a lookup companion while solving problems.

---

## How to Use These Indexes

- **Algorithm Index**: Look up an algorithm by name to find its chapter, time complexity, and space complexity.
- **Data Structure Index**: Compare data structures by their operation complexities.
- **Pattern Recognition Index**: Given a problem keyword, find the technique you should apply.
- **Complexity Index**: Given a constraint on n, determine the maximum algorithm complexity you can afford.
- **Formula Index**: Quick lookup for mathematical formulas used across the book.

---

## Algorithm Index

### Sorting Algorithms

| Algorithm | Chapter | Time (Avg) | Time (Worst) | Space | Stable |
|---|---|---|---|---|---|
| Bubble Sort | 5 | O(n²) | O(n²) | O(1) | Yes |
| Selection Sort | 5 | O(n²) | O(n²) | O(1) | No |
| Insertion Sort | 5 | O(n²) | O(n²) | O(1) | Yes |
| Merge Sort | 5 | O(n log n) | O(n log n) | O(n) | Yes |
| QuickSort | 5 | O(n log n) | O(n²) | O(log n) | No |
| Heap Sort | 5 | O(n log n) | O(n log n) | O(1) | No |
| Counting Sort | 5 | O(n + k) | O(n + k) | O(k) | Yes |
| Radix Sort | 5 | O(d(n + k)) | O(d(n + k)) | O(n + k) | Yes |
| Tim Sort | 5 | O(n log n) | O(n log n) | O(n) | Yes |

### Searching Algorithms

| Algorithm | Chapter | Time | Space | Notes |
|---|---|---|---|---|
| Binary Search | 6 | O(log n) | O(1) | Requires sorted input |
| Ternary Search | 6 | O(log n) | O(1) | Unimodal functions |
| Exponential Search | 6 | O(log n) | O(1) | Unbounded search |
| Interpolation Search | 6 | O(log log n) avg | O(1) | Uniform distribution |
| Fibonacci Search | 6 | O(log n) | O(1) | No division needed |

### Graph Algorithms

| Algorithm | Chapter | Time | Space | Use Case |
|---|---|---|---|---|
| DFS | 23 | O(V + E) | O(V) | Traversal, connectivity |
| BFS | 24 | O(V + E) | O(V) | Shortest path (unweighted) |
| Topological Sort | 25 | O(V + E) | O(V) | DAG ordering |
| Dijkstra | 26 | O((V+E) log V) | O(V) | Single-source shortest path |
| Bellman-Ford | 82 | O(VE) | O(V) | Negative edges |
| Floyd-Warshall | 82 | O(V³) | O(V²) | All-pairs shortest path |
| Kruskal | 27 | O(E log E) | O(V) | MST |
| Prim | 27 | O((V+E) log V) | O(V) | MST |
| Tarjan SCC | 81 | O(V + E) | O(V) | Strongly connected components |
| Kosaraju | 81 | O(V + E) | O(V) | Strongly connected components |
| Dinic | 83 | O(V²E) | O(V + E) | Max flow |
| Hopcroft-Karp | 112 | O(E√V) | O(V + E) | Bipartite matching |
| A* Search | 65 | O(E log V) | O(V) | Heuristic shortest path |
| Johnson | 82 | O(V² log V + VE) | O(V²) | All-pairs (sparse) |

### String Algorithms

| Algorithm | Chapter | Time | Space | Use Case |
|---|---|---|---|---|
| KMP | 41 | O(n + m) | O(m) | Pattern matching |
| Z Algorithm | 42 | O(n + m) | O(n + m) | Pattern matching |
| Rabin-Karp | 40 | O(n + m) avg | O(1) | Multiple pattern matching |
| Aho-Corasick | 46 | O(n + m + z) | O(nm) | Multi-pattern matching |
| Suffix Array | 44 | O(n log n) | O(n) | Suffix sorting |
| Suffix Automaton | 45 | O(n) | O(n) | All substrings |
| Manacher | 119 | O(n) | O(n) | All palindromes |
| Suffix Tree | 87 | O(n) | O(n) | Generalized suffix queries |
| Palindromic Tree | 88 | O(n) | O(n) | Distinct palindromic substrings |
| BWT/FM-Index | 120 | O(n) build, O(m) query | O(n) | Compressed full-text search |

### Number Theory

| Algorithm | Chapter | Time | Use Case |
|---|---|---|---|
| Sieve of Eratosthenes | 67 | O(n log log n) | Prime generation |
| GCD (Euclidean) | 67 | O(log min(a,b)) | Greatest common divisor |
| Modular Exponentiation | 67 | O(log n) | Fast power |
| Miller-Rabin | 67 | O(k log²n) | Primality test |
| Pollard's Rho | 67 | O(n^{1/4}) | Factorization |

### Optimization & Approximation

| Algorithm | Chapter | Time | Use Case |
|---|---|---|---|
| Gale-Shapley | 162 | O(n²) | Stable matching |
| Held-Karp (TSP) | 149 | O(2^n · n²) | Exact TSP |
| Karger's Min Cut | 150 | O(n² log n) runs | Min cut |
| Simplex | 151 | Exponential worst | Linear programming |
| Hungarian | 84 | O(n³) | Assignment problem |

---

## Data Structure Index

### Basic Structures

| Structure | Chapter | Insert | Delete | Search | Space |
|---|---|---|---|---|---|
| Array | 4 | O(1) end | O(1) end | O(n) | O(n) |
| Dynamic Array | 4 | O(1) amort | O(1) end | O(n) | O(n) |
| Linked List | 12 | O(1) head | O(1) given node | O(n) | O(n) |
| Doubly Linked List | 12 | O(1) | O(1) given node | O(n) | O(n) |
| Stack | 10 | O(1) | O(1) top | O(n) | O(n) |
| Queue | 11 | O(1) | O(1) front | O(n) | O(n) |
| Deque | 11 | O(1) | O(1) both ends | O(n) | O(n) |

### Hash-Based Structures

| Structure | Chapter | Insert | Delete | Search | Space |
|---|---|---|---|---|---|
| Hash Map | 7 | O(1) avg | O(1) avg | O(1) avg | O(n) |
| Hash Set | 7 | O(1) avg | O(1) avg | O(1) avg | O(n) |
| Bloom Filter | 80 | O(k) | N/A | O(k) | O(m bits) |
| Cuckoo Hashing | 7 | O(1) worst | O(1) worst | O(1) worst | O(n) |

### Tree Structures

| Structure | Chapter | Insert | Delete | Search | Space |
|---|---|---|---|---|---|
| BST (unbalanced) | 14 | O(h) | O(h) | O(h) | O(n) |
| AVL Tree | 14 | O(log n) | O(log n) | O(log n) | O(n) |
| Red-Black Tree | 76 | O(log n) | O(log n) | O(log n) | O(n) |
| B-Tree | 77 | O(log n) | O(log n) | O(log n) | O(n) |
| Treap | 57 | O(log n) | O(log n) | O(log n) | O(n) |
| Splay Tree | 75 | O(log n) amort | O(log n) amort | O(log n) amort | O(n) |
| Skip List | 74 | O(log n) | O(log n) | O(log n) | O(n) |

### Priority Queue Structures

| Structure | Chapter | Insert | Extract-Min | Decrease-Key | Space |
|---|---|---|---|---|---|
| Binary Heap | 15 | O(log n) | O(log n) | O(log n) | O(n) |
| Fibonacci Heap | 15 | O(1) amort | O(log n) amort | O(1) amort | O(n) |
| Binomial Heap | 15 | O(1) amort | O(log n) | O(log n) | O(n) |
| Pairing Heap | 15 | O(1) | O(log n) amort | O(log n) amort | O(n) |

### Range Query Structures

| Structure | Chapter | Build | Update | Query | Space |
|---|---|---|---|---|---|
| Segment Tree | 18 | O(n) | O(log n) | O(log n) | O(n) |
| Lazy Segment Tree | 18 | O(n) | O(log n) | O(log n) | O(n) |
| Fenwick Tree | 19 | O(n) | O(log n) | O(log n) | O(n) |
| Sparse Table | 20 | O(n log n) | N/A | O(1) | O(n log n) |
| Square Root Decomposition | 94 | O(n) | O(√n) | O(√n) | O(n) |
| Mo's Algorithm | 93 | — | — | O(n√n) total | O(n) |

### Specialized Structures

| Structure | Chapter | Key Operation | Time | Space |
|---|---|---|---|---|
| Trie | 16 | Insert/Search string | O(m) | O(nm) |
| DSU | 17 | Union/Find | O(α(n)) | O(n) |
| KD Tree | 78 | Nearest neighbor | O(log n) avg | O(n) |
| Van Emde Boas | 100 | Successor/Predecessor | O(log log U) | O(U) |
| Link-Cut Tree | 157 | Path/Link/Cut | O(log n) | O(n) |
| Persistent Segment Tree | 79 | Version-based query | O(log n) | O(n log n) |

---

## Pattern Recognition Index

### Problem Keywords → Technique

| Keyword / Phrase | Primary Technique | Chapter | Secondary Technique |
|---|---|---|---|
| "sorted array" | Binary Search | 6 | Two Pointers |
| "top k" / "k-th largest" | Heap | 15 | Quickselect |
| "shortest path" | BFS (unweighted) | 24 | Dijkstra (weighted) |
| "minimum cost" / "minimum operations" | DP | 30-31 | Greedy |
| "number of ways" / "count" | DP | 30-31 | Combinatorics |
| "subarray" / "contiguous" | Sliding Window | 35 | Prefix Sum |
| "subsequence" | DP | 30-31 | Binary Search (LIS) |
| "connected components" | DFS / BFS | 23-24 | Union-Find |
| "cycle detection" | DFS with colors | 23 | Union-Find |
| "topological order" | Topological Sort | 25 | DFS |
| "range query" / "range update" | Segment Tree | 18 | Fenwick Tree |
| "parentheses" / "valid expression" | Stack | 10 | DP |
| "anagram" / "frequency" | Hash Map | 7 | Sorting |
| "palindrome" | Two Pointers | 34 | Manacher |
| "permutation" / "combination" | Backtracking | 9 | Next Permutation |
| "next greater" / "next smaller" | Monotonic Stack | 37 | — |
| "sliding window max/min" | Monotonic Queue | 38 | — |
| "median" | Two Heaps | 15 | Binary Search |
| "LCA" (lowest common ancestor) | Binary Lifting | 21 | Euler Tour + RMQ |
| "path on tree" | HLD | 62 | Euler Tour |
| "count with digits" | Digit DP | 85 | — |
| "optimal k groups" | Binary Search on Answer | 6 | Alien Trick |
| "matrix chain" | Interval DP | 31 | — |
| "bitmask states" | Bitmask DP | 31 | — |
| "interval scheduling" | Greedy (sort by end) | 32 | DP |
| "minimum spanning tree" | Kruskal / Prim | 27 | — |
| "bipartite" | BFS coloring | 24 | DFS |
| "strongly connected" | Tarjan / Kosaraju | 81 | — |
| "max flow" / "min cut" | Dinic | 83 | — |
| "matching" | Hopcroft-Karp | 112 | Hungarian |
| "serialize" / "deserialize" | BFS / DFS | 23-24 | — |
| "LRU cache" | Hash Map + DLL | 89 | — |
| "sliding median" | Two Heaps | 15 | Ordered Set |
| "string matching" | KMP / Z-algo | 41-42 | Rabin-Karp |
| "multiple patterns" | Aho-Corasick | 46 | Trie |
| "all palindromes" | Manacher | 119 | Palindromic Tree |
| "suffix" queries | Suffix Array | 44 | Suffix Tree |
| "edit distance" | DP (LCS-style) | 122 | — |
| "regex" / "wildcard" | DP | 123 | NFA |

---

## Complexity Index

### Constraint → Maximum Complexity

| Constraint on n | Max Complexity | Typical Approach | Example Algorithms |
|---|---|---|---|
| n ≤ 10 | O(n!) | Permutation brute force | Generate all permutations |
| n ≤ 15 | O(2^n · n) | Bitmask DP | TSP, subset DP |
| n ≤ 20 | O(2^n) | Backtracking, Meet-in-Middle | Subset sum, N-Queens |
| n ≤ 50 | O(n⁴) | High-dimensional DP | 4D interval DP |
| n ≤ 100 | O(n³) | Matrix-style DP | Floyd-Warshall, Matrix Chain |
| n ≤ 200 | O(n³) | Graph algorithms | Floyd-Warshall |
| n ≤ 500 | O(n³) | Cubic algorithms | All-pairs shortest path |
| n ≤ 1,000 | O(n²) | Quadratic DP | LIS, Edit Distance |
| n ≤ 5,000 | O(n²) | Simple DP | O(n²) DP solutions |
| n ≤ 10,000 | O(n²) | Quadratic with small constant | Bubble sort variants |
| n ≤ 100,000 | O(n log n) | Sort-based, trees | Merge sort, Segment tree |
| n ≤ 1,000,000 | O(n) | Linear scan | Hash map, two pointers |
| n ≤ 10,000,000 | O(n) | Careful linear | Sieve, counting sort |
| n ≤ 10^9 | O(√n) | Number theory | Primality, factorization |
| n ≤ 10^18 | O(log n) | Binary search, math | Fast exponentiation |

### Complexity → Max Input Size (for 1 second)

| Complexity | Max n | Notes |
|---|---|---|
| O(1) | ∞ | Constant time |
| O(log n) | 10^18 | Binary search |
| O(√n) | 10^10 | Number theory |
| O(n) | 10^7 | Linear scan |
| O(n log n) | 10^6 | Sorting |
| O(n²) | 5,000 | Nested loops |
| O(n³) | 500 | Triple nested |
| O(n⁴) | 100 | Quadruple nested |
| O(2^n) | 20 | Exponential |
| O(3^n) | 15 | Triple exponential |
| O(n!) | 10 | Factorial |
| O(n · 2^n) | 18 | Bitmask DP |

---

## Formula Index

### Combinatorics

| Formula | Expression | Chapter | Use Case |
|---|---|---|---|
| Permutation | P(n,r) = n!/(n-r)! | 68 | Ordered selection |
| Combination | C(n,r) = n!/(r!(n-r)!) | 68 | Unordered selection |
| Stars and Bars | C(n+k-1, k-1) | 68 | Distribution problems |
| Catalan Number | C(2n,n)/(n+1) | 68 | Balanced parentheses, trees |
| Inclusion-Exclusion | \|A∪B\| = \|A\|+\|B\|-\|A∩B\| | 68 | Counting with constraints |
| Derangement | D(n) = (n-1)(D(n-1)+D(n-2)) | 68 | No fixed points |

### Number Theory

| Formula | Expression | Chapter | Use Case |
|---|---|---|---|
| Euler's Totient | φ(n) = n∏(1-1/p) | 67 | Coprime counting |
| Modular Inverse | a^{-1} ≡ a^{p-2} (mod p) | 67 | Division in modular arithmetic |
| Chinese Remainder | x ≡ aᵢ (mod mᵢ) | 67 | System of congruences |
| Fermat's Little Theorem | a^{p-1} ≡ 1 (mod p) | 67 | Modular exponentiation |
| Möbius Function | μ(n) | 67 | Inclusion-exclusion on divisors |

### Probability & Statistics

| Formula | Expression | Chapter | Use Case |
|---|---|---|---|
| Bayes' Theorem | P(A\|B) = P(B\|A)P(A)/P(B) | 69 | Conditional probability |
| Birthday Paradox | P ≈ 1 - e^{-n²/2d} | 69 | Hash collision probability |
| Coupon Collector | E = n·H(n) ≈ n ln n | 69 | Expected coverage |
| Linearity of Expectation | E[X+Y] = E[X]+E[Y] | 69 | Expected value computation |

### Series & Sequences

| Formula | Expression | Chapter | Use Case |
|---|---|---|---|
| Geometric Sum | a(r^n - 1)/(r - 1) | 2 | Series computation |
| Arithmetic Sum | n(a₁ + aₙ)/2 | 2 | Series computation |
| Fibonacci (closed form) | (φ^n - ψ^n)/√5 | 2 | Direct computation |
| Harmonic Number | H(n) ≈ ln n + γ | 2 | Sum of reciprocals |

### Algorithm-Specific

| Formula | Expression | Chapter | Use Case |
|---|---|---|---|
| Master Theorem | T(n) = aT(n/b) + O(n^d) | 3 | Divide & conquer recurrences |
| Expected hash chain | O(1 + n/m) | 7 | Hash table analysis |
| Height of balanced BST | O(log n) | 14 | Tree operations |
| Max edges in graph | V(V-1)/2 | 22 | Graph density |

---

## Algorithm Selection Quick Guide

### By Problem Type

| Problem Type | First Choice | When It Fails | Fallback |
|---|---|---|---|
| Find element in sorted array | Binary Search | Unsorted | Sort first, then BS |
| Shortest path (unweighted) | BFS | Weighted edges | Dijkstra |
| Shortest path (weighted, no negative) | Dijkstra | Negative edges | Bellman-Ford |
| All-pairs shortest path | Floyd-Warshall | Too large (n > 500) | Dijkstra × n |
| Minimum spanning tree | Kruskal | Dense graph | Prim |
| Maximum flow | Dinic | — | Edmonds-Karp |
| Longest increasing subsequence | Binary Search | Need actual sequence | DP O(n²) |
| Edit distance | DP O(nm) | Space too large | Hirschberg (linear space) |
| Range minimum query | Sparse Table (static) | Dynamic updates | Segment Tree |
| Range sum with updates | Fenwick Tree | Range updates too | Lazy Segment Tree |
| String matching | KMP | Multiple patterns | Aho-Corasick |
| All palindromes | Manacher | Distinct only | Palindromic Tree |
| Connectivity (static) | DFS | Dynamic edges | Union-Find |
| Top k elements | Min-heap (size k) | Need sorted output | Sort |
| Median maintenance | Two heaps | Need order statistics | Order-statistic tree |

### By Data Size

| Data Size | Recommended Structures |
|---|---|
| < 100 | Arrays, simple loops |
| 100 – 10,000 | Hash maps, arrays, sorting |
| 10,000 – 10^6 | Trees, heaps, binary search |
| 10^6 – 10^7 | Linear algorithms, hash maps |
| > 10^7 | Streaming, sampling, approximation |

---

## Cross-Reference Summary

| If You Need... | Go To |
|---|---|
| Learn a topic from scratch | Master TOC (Ch 144) → specific chapter |
| Pick the right algorithm | Algorithm Selection (Ch 140) |
| Pick the right data structure | DS Selection (Ch 141) |
| Look up a formula | Formula Handbook (Ch 138) |
| Check complexity limits | Complexity Handbook (Ch 139) |
| Match a problem pattern | Pattern Recognition (Ch 97) |
| Prepare for a specific company | Company Handbook (Ch 142) |
| Quick fact verification | Knowledge Aids (Ch 143) |
| Navigate the whole book | Master TOC (Ch 144) |
