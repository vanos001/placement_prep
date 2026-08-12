# Chapter 70: Computational Models and Complexity Classes

## Prerequisites

- Basic algorithms and complexity (Chapter 1)
- Mathematical maturity
- Graph theory basics (Chapter 18)

## Interview Frequency: ★★

Understanding computational models and complexity classes helps you recognize when a problem is fundamentally hard and when to stop looking for a polynomial solution. **Google** and research-oriented companies occasionally test this knowledge.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| P vs NP | ★★ | Hard | Fundamental CS theory |
| NP-Completeness | ★★ | Hard | Reduction techniques |
| Approximation | ★★ | Medium | When exact is intractable |
| Online algorithms | ★★ | Medium | Streaming, competitive ratio |

---

## 70.1 Definition

A **computational model** is a mathematical abstraction of a computer that defines what operations are allowed and how much they cost. Different models lead to different complexity measures for the same problem.

A **complexity class** is a set of problems that share a common resource bound (time, space, nondeterminism, etc.) under a given computational model.

Understanding these concepts is essential for:
- **Recognizing intractable problems** — knowing when to stop searching for efficient exact algorithms
- **Choosing the right approach** — approximation, heuristics, or parameterized algorithms
- **Communicating difficulty** — "this problem is NP-hard" is precise and universally understood

---

## 70.2 Motivation

### Why Computational Models Matter

The same algorithm can have different complexity depending on the model:
- **Comparison sorting**: Ω(n log n) in the comparison model, but O(n) with radix sort (different model)
- **Graph algorithms**: O(m + n) with adjacency lists, O(n²) with adjacency matrices
- **Integer sorting**: O(n log log n) with van Emde Boas trees (word RAM model)

### Why Complexity Classes Matter

In interviews and real projects, you need to quickly assess:
1. Is this problem solvable in polynomial time?
2. If not, what's the best we can do?
3. Are there special cases that are easier?

Without understanding complexity classes, you might waste days trying to find an efficient algorithm for an NP-hard problem.

---

## 70.3 Intuition

Think of computational models as "what your machine can do in one step":

| Model | One Step = | Good For |
|---|---|---|
| **Comparison model** | Compare two elements | Sorting lower bounds |
| **RAM** | Any basic operation | General algorithms |
| **Word RAM** | Operation on w-bit words | Bit manipulation |
| **Turing machine** | Read/write one symbol | Theoretical foundations |
| **External memory** | Read/write one block | Disk-based algorithms |

Complexity classes are like "difficulty tiers":

| Class | Intuition | Example |
|---|---|---|
| **P** | "Easy" — solved quickly | Sorting, shortest path |
| **NP** | "Easy to check" — verify quickly | Sudoku, factoring |
| **NP-Complete** | "Hardest in NP" — if you solve one, you solve all | SAT, TSP |
| **NP-Hard** | "At least as hard as NP-C" | Halting problem |
| **PSPACE** | "Needs polynomial memory" | Two-player games |

**Key insight**: P ⊆ NP is obvious (if you can solve it quickly, you can verify quickly). Whether P = NP is the million-dollar question — can every problem with efficiently verifiable solutions also be solved efficiently?

---

## 70.4 Formal Explanation

### Computational Models

#### RAM (Random Access Machine)

The standard model for algorithm analysis:
- **Operations**: arithmetic, comparison, assignment, array access — all O(1)
- **Memory**: unbounded, random access
- **Word size**: typically O(log n) bits
- **Cost measure**: number of operations

This is the model used in most algorithm textbooks and competitive programming.

#### Word RAM

Extends RAM with word-level operations:
- Words are w bits (typically w ≥ log n)
- Bitwise operations on words: O(1)
- Arithmetic on words: O(1)
- Important for: hashing, bit manipulation, van Emde Boas trees

**Why it matters**: Some algorithms (radix sort, counting sort) achieve O(n) time only in the word RAM model, not the comparison model.

#### External Memory Model

For data too large for main memory:
- **Memory**: M words of fast cache, unlimited slow disk
- **Transfer**: B words per block transfer
- **Cost measure**: number of block transfers (I/O complexity)
- **Goal**: minimize I/O, not CPU operations

**Why it matters**: When processing terabytes of data, disk I/O dominates. Algorithms like external merge sort are designed for this model.

#### Turing Machine

The foundational model of computation:
- Infinite tape of cells
- Read/write head that moves left or right
- Finite state control
- Deterministic or nondeterministic

**Why it matters**: Defines the theoretical limits of computation. The Church-Turing thesis states that anything computable is computable by a Turing machine.

---

### Complexity Classes

#### P (Polynomial Time)

**Definition**: Problems solvable by a deterministic Turing machine in O(n^k) time for some constant k.

**Formal**: P = ∪_{k≥0} DTIME(n^k)

**Examples**:
- Sorting: O(n log n)
- Shortest path: O(V²) or O(E + V log V)
- Maximum flow: O(VE²)
- Linear programming: polynomial (ellipsoid method)

#### NP (Nondeterministic Polynomial Time)

**Definition**: Problems where a "yes" answer can be verified in polynomial time given a certificate (proof).

**Formal**: NP = ∪_{k≥0} NTIME(n^k)

**Equivalently**: Solvable in polynomial time by a nondeterministic Turing machine.

**Examples**:
- SAT: given an assignment, verify in O(n) time
- Hamiltonian path: given a path, verify it visits all vertices
- Graph coloring: given a coloring, verify no adjacent vertices share a color
- Subset sum: given a subset, verify the sum equals target

#### NP-Complete

**Definition**: A problem X is NP-Complete if:
1. X ∈ NP
2. For every problem Y ∈ NP, Y reduces to X in polynomial time

**Implication**: If any NP-Complete problem has a polynomial algorithm, then P = NP.

**Classic NP-Complete problems**:

| Problem | Input | Question | Reduction From |
|---|---|---|---|
| SAT | Boolean formula | Satisfiable? | Circuit SAT |
| 3-SAT | 3-CNF formula | Satisfiable? | SAT |
| Clique | Graph, k | Clique of size k? | 3-SAT |
| Vertex Cover | Graph, k | Cover of size k? | Clique |
| Hamiltonian Path | Graph | Visits all vertices? | Vertex Cover |
| Subset Sum | Integers, target | Subset sums to target? | 3-SAT |
| Partition | Integers | Split into equal halves? | Subset Sum |
| Graph Coloring | Graph, k | k-colorable? | 3-SAT |

#### NP-Hard

**Definition**: At least as hard as NP-Complete. Does not need to be in NP (may not even be decidable).

**Examples**:
- Halting problem (undecidable)
- TSP optimization (not just decision)
- General game playing (PSPACE-hard)

#### PSPACE

**Definition**: Problems solvable with polynomial space (unlimited time).

**Relationship**: P ⊆ NP ⊆ PSPACE ⊆ EXPTIME

**Examples**:
- QBF (quantified Boolean formula)
- Two-player games (chess, go — with polynomial board)

---

## 70.5 Step-by-Step: Proving NP-Completeness

To prove a problem X is NP-Complete:

**Step 1**: Show X ∈ NP
- Give a polynomial-time verification algorithm
- Show that given a certificate, you can verify it in O(n^k) time

**Step 2**: Choose a known NP-Complete problem Y

**Step 3**: Show Y ≤_p X (Y reduces to X in polynomial time)
- Give a polynomial-time function f that transforms instances of Y to instances of X
- Show: y ∈ Y ⟺ f(y) ∈ X

### Example: Proving Clique is NP-Complete

**Step 1**: Clique ∈ NP
- Certificate: a set of k vertices
- Verify: check all pairs are connected — O(k²) time

**Step 2**: Reduce from 3-SAT

**Step 3**: Given 3-SAT formula with m clauses, construct graph G:
- For each literal in each clause, create a vertex
- Connect two vertices if they are in different clauses AND are not negations of each other
- Set k = m (number of clauses)

**Claim**: 3-SAT is satisfiable ⟺ G has a clique of size m.

**Proof sketch**:
- If satisfiable: pick one true literal per clause → they form a clique (all compatible)
- If clique of size m: one vertex per clause → consistent truth assignment

---

## 70.6 Dry Run: Identifying Problem Difficulty

**Problem**: Given a graph G and integer k, does G have an independent set of size k?

**Step 1**: Is it in NP?
- Certificate: set S of k vertices
- Verify: check no two vertices in S are adjacent — O(k²)
- Yes, it's in NP

**Step 2**: Is it NP-Hard?
- Known: Vertex Cover is NP-Complete
- Observation: S is an independent set ⟺ V-S is a vertex cover
- Reduction: G has independent set of size k ⟺ G has vertex cover of size n-k
- Yes, it's NP-Hard

**Conclusion**: Independent Set is NP-Complete.

**Practical implication**: For n ≤ 20, use bitmask DP (O(2^n × n²)). For larger n, use approximation or heuristics.

---

## 70.7 Complexity Analysis

### Time Complexity of Reductions

| Reduction Type | Time | Example |
|---|---|---|
| Karp (polynomial) | O(n^k) | SAT → 3-SAT |
| Turing (polynomial) | O(n^k) oracle calls | Binary search on answer |
| Log-space | O(log n) space | Many standard reductions |

### Space Complexity Classes

| Class | Definition | Example |
|---|---|---|
| L | O(log n) space | Graph connectivity (undirected) |
| NL | O(log n) nondeterministic space | Graph reachability |
| PSPACE | Polynomial space | QBF, games |

### Randomized Classes

| Class | Definition | Example |
|---|---|---|
| BPP | Bounded-error probabilistic polynomial | Polynomial identity testing |
| RP | One-sided error | Primality testing (Miller-Rabin) |
| ZPP | Zero-error probabilistic | RP ∩ coRP |

---

## 70.8 Approximation Algorithms

When the exact solution is NP-hard, find a solution within a factor of optimal.

### Approximation Ratio

An algorithm has approximation ratio ρ(n) if for all instances:
```
cost(ALG) / cost(OPT) ≤ ρ(n)     (for minimization)
cost(OPT) / cost(ALG) ≤ ρ(n)     (for maximization)
```

### Classic Approximation Results

| Problem | Approximation Ratio | Algorithm | Complexity |
|---|---|---|---|
| Vertex Cover | 2 | Greedy (pick both endpoints) | O(E) |
| TSP (metric) | 3/2 | Christofides | O(V³) |
| Set Cover | O(ln n) | Greedy | O(nm) |
| Max Cut | 0.5 | Random assignment | O(E) |
| Knapsack | 1 + ε | FPTAS | O(n³/ε) |
| Max-SAT | 0.5 | Random assignment | O(n) |

### C++: 2-Approximation for Vertex Cover

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// 2-approximation for Vertex Cover
// Greedy: pick both endpoints of each uncovered edge
std::vector<int> approxVertexCover(const std::vector<std::vector<int>>& adj,
                                    const std::vector<std::pair<int,int>>& edges) {
    std::vector<bool> covered(adj.size(), false);
    std::vector<int> cover;
    
    for (auto& [u, v] : edges) {
        if (!covered[u] && !covered[v]) {
            cover.push_back(u);
            cover.push_back(v);
            covered[u] = covered[v] = true;
        }
    }
    
    return cover;
}

int main() {
    // Graph: 0-1, 0-2, 1-3, 2-4
    int n = 5;
    std::vector<std::vector<int>> adj(n);
    std::vector<std::pair<int,int>> edges = {{0,1}, {0,2}, {1,3}, {2,4}};
    
    for (auto& [u, v] : edges) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    auto cover = approxVertexCover(adj, edges);
    std::cout << "Approximate vertex cover: ";
    for (int v : cover) std::cout << v << " ";
    std::cout << "\nSize: " << cover.size() << " (optimal is 2: {0,1} or {0,2})\n";
    
    return 0;
}
```

### Python: Greedy Set Cover

```python
def greedy_set_cover(universe, sets):
    """O(ln n)-approximation for Set Cover."""
    covered = set()
    cover = []
    
    while covered != universe:
        # Pick the set covering the most uncovered elements
        best = max(sets, key=lambda s: len(s - covered))
        cover.append(best)
        covered |= best
    
    return cover

# Example
universe = {1, 2, 3, 4, 5}
sets = [{1, 2, 3}, {2, 4}, {3, 4}, {4, 5}]
result = greedy_set_cover(universe, sets)
print(f"Cover uses {len(result)} sets (optimal is 2)")
```

### Java: Randomized Max-SAT

```java
import java.util.Random;

public class MaxSATApprox {
    // 0.5-approximation: assign each variable randomly
    // Expected: at least half the clauses are satisfied
    public static int randomAssignment(int[][] clauses, int numVars) {
        Random rng = new Random();
        boolean[] assignment = new boolean[numVars + 1];
        for (int i = 1; i <= numVars; i++) {
            assignment[i] = rng.nextBoolean();
        }
        
        int satisfied = 0;
        for (int[] clause : clauses) {
            for (int lit : clause) {
                int var = Math.abs(lit);
                if ((lit > 0 && assignment[var]) || (lit < 0 && !assignment[var])) {
                    satisfied++;
                    break;
                }
            }
        }
        return satisfied;
    }
    
    public static void main(String[] args) {
        // (x1 ∨ x2) ∧ (¬x1 ∨ x3) ∧ (¬x2 ∨ ¬x3)
        int[][] clauses = {{1, 2}, {-1, 3}, {-2, -3}};
        int satisfied = randomAssignment(clauses, 3);
        System.out.println("Satisfied " + satisfied + "/" + clauses.length + " clauses");
    }
}
```

---

## 70.9 Online Algorithms

**Online algorithms** process input piece by piece without knowing future input. This contrasts with offline algorithms that see the entire input at once.

### Competitive Ratio

An online algorithm has **competitive ratio** c if:
```
ALG(requests) ≤ c × OPT(requests) + constant
```
for all request sequences.

### Classic Online Problems

| Problem | Online Algorithm | Competitive Ratio | Lower Bound |
|---|---|---|---|
| Paging (cache) | LRU | k (cache size) | k |
| Ski rental | Buy after B days | 2 | 2 |
| Secretary problem | Reject first n/e, pick next best | e ≈ 2.718 | e |
| Online matching | Greedy | 0.5 | 0.5 |
| k-server | Various | 2k-1 | 2k-1 |

### Ski Rental Problem

Rent skis for \\(1/day or buy for \\)B. How many days to rent before buying?

**Optimal strategy**: Rent for B days, then buy.
**Worst case**: You ski exactly B days → paid 2B instead of B → ratio 2.
**Proof of optimality**: No deterministic algorithm can achieve ratio < 2.

```cpp
#include <iostream>
#include <iomanip>

// Strategy: Rent for B days, then buy
int skiRentalStrategy(int B, int actualDays) {
    int cost = std::min(actualDays, B) + (actualDays > B ? B : 0);
    return cost;
}

int optimalCost(int B, int actualDays) {
    return std::min(actualDays, B);
}

int main() {
    int B = 10; // Buy price
    
    std::cout << "Ski Rental (buy price = $" << B << "):\n";
    for (int days : {5, 10, 15, 20}) {
        int alg = skiRentalStrategy(B, days);
        int opt = optimalCost(B, days);
        double ratio = (double)alg / opt;
        std::cout << "  Days=" << days << ": ALG=$" << alg 
                  << ", OPT=$" << opt << ", ratio=" 
                  << std::fixed << std::setprecision(2) << ratio << "\n";
    }
    // Worst case: days=B → ratio=2.00
    
    return 0;
}
```

### Python: Secretary Problem Simulator

```python
import random

def secretary_strategy(n, values, threshold_idx):
    """Reject first threshold_idx candidates, then pick the next best so far."""
    best_first = max(values[:threshold_idx])
    for i in range(threshold_idx, n):
        if values[i] > best_first:
            return values[i]
    return values[-1]  # Must pick last if none better

def optimal_secretary(n):
    """Optimal threshold is n/e, giving competitive ratio e."""
    threshold = int(n / 2.718)
    return threshold

def simulate(n, trials=100000):
    threshold = optimal_secretary(n)
    total_alg = 0
    total_opt = 0
    
    for _ in range(trials):
        values = random.sample(range(1, n + 1), n)
        alg = secretary_strategy(n, values, threshold)
        opt = max(values)
        total_alg += alg
        total_opt += opt
    
    ratio = total_opt / total_alg
    print(f"n={n}: ALG/OPT ratio = {ratio:.3f} (theoretical: {2.718:.3f})")

for n in [10, 50, 100, 500]:
    simulate(n)
```

---

## 70.10 Parameterized Complexity

When a problem is NP-hard, we can sometimes find algorithms that are exponential in a parameter k but polynomial in n.

### Fixed-Parameter Tractable (FPT)

A problem is FPT with parameter k if it can be solved in O(f(k) × n^c) time, where f is any computable function and c is a constant.

**Examples**:

| Problem | Parameter | FPT Algorithm | Complexity |
|---|---|---|---|
| Vertex Cover | k (cover size) | Branching | O(2^k × n) |
| k-Clique | k | Brute force | O(n^k) — not FPT! |
| Feedback Vertex Set | k | Branching | O(3.619^k × n²) |
| Planar Dominating Set | k | Baker's method | O(2^{O(√k)} × n) |

### Why FPT Matters

If k is small (e.g., k ≤ 30), an O(2^k × n) algorithm is practical even for large n. This is the basis of parameterized algorithms in bioinformatics, network analysis, and VLSI design.

---

## 70.11 Exercises

1. **Prove that if P = NP, then NP = coNP.** Hint: coNP is the set of problems whose "no" answers can be verified in polynomial time.

2. **Show that the Hamiltonian Path problem is NP-Complete** by reducing from Hamiltonian Cycle. Given a graph G, construct G' such that G has a Hamiltonian cycle iff G' has a Hamiltonian path.

3. **Design a 2-approximation for the Max-Cut problem.** Hint: assign each vertex to a side randomly. Show the expected cut size is at least half the maximum.

4. **Implement the ski rental problem** with a randomized strategy that achieves expected competitive ratio e/(e-1) ≈ 1.58. Hint: buy on day d with probability 1/B for d < B.

5. **Prove that Vertex Cover is FPT** with parameter k (the size of the cover). Design an O(2^k × n) branching algorithm. Hint: pick an edge, branch on including either endpoint.

6. **Show that the Traveling Salesman Problem (decision version) is NP-Hard.** Hint: reduce from Hamiltonian Cycle.

7. **Design an online algorithm for the caching problem** with competitive ratio k (the cache size). Prove that no deterministic online algorithm can do better.

8. **Explain the difference between NP-Hard and NP-Complete.** Give an example of a problem that is NP-Hard but not NP-Complete.

---

## 70.12 Interview Questions

1. **What is the difference between P and NP?**
   - P: solvable in polynomial time
   - NP: verifiable in polynomial time
   - P ⊆ NP (solving is a special case of verifying)
   - P = NP? — open problem, million-dollar prize

2. **How do you prove a problem is NP-Complete?**
   - Show it's in NP (polynomial verification)
   - Reduce from a known NP-Complete problem
   - Show the reduction is polynomial-time

3. **When should you suspect a problem is NP-Hard?**
   - No polynomial algorithm after significant effort
   - Problem involves selection/optimization over subsets
   - Known similar problems are NP-Hard
   - Constraints suggest exponential search space

4. **What can you do when a problem is NP-Hard?**
   - Approximation algorithms (guaranteed ratio)
   - Heuristics (no guarantee, often good in practice)
   - Parameterized algorithms (FPT)
   - Special cases (trees, planar graphs, small n)
   - Randomized algorithms

5. **Explain the ski rental problem and its optimal strategy.**
   - Rent for \\(1/day, buy for \\)B
   - Strategy: rent for B days, then buy
   - Competitive ratio: 2 (worst case when you ski exactly B days)
   - No deterministic algorithm can do better

6. **What is an approximation algorithm? Give an example.**
   - Algorithm that returns near-optimal solution with proven ratio
   - Example: 2-approximation for Vertex Cover
   - Greedy: pick both endpoints of each uncovered edge
   - Always within 2× optimal

7. **What is the difference between NP-Complete and NP-Hard?**
   - NP-Complete: in NP AND NP-Hard
   - NP-Hard: at least as hard as NP-Complete, may not be in NP
   - Example NP-Hard but not NP-C: Halting problem (undecidable)

---

## Cross-References

- **Foundations**: Introduction to Algorithms, Time Complexity
- **Graph algorithms**: Graph Representations, Shortest Paths
- **Dynamic programming**: [DP Fundamentals](ch30-dp-fundamentals.md)
- **Greedy**: Greedy Algorithms
- **Related chapters**: [Probability for Programming](ch72-probability.md), [Probabilistic Data Structures](ch79-probabilistic-ds.md)

---

## Summary

| Concept | Key Insight | Interview Relevance |
|---|---|---|
| Computational Models | Define what's "one step" | Know your cost model |
| P vs NP | Easy to verify ≠ easy to solve | Recognize hard problems |
| NP-Complete | Reduce from known NP-C problems | Know when to give up |
| NP-Hard | At least as hard as NP-C | May not even be in NP |
| Approximation | Near-optimal for hard problems | Practical solutions |
| Online algorithms | No future knowledge | Streaming, caching |
| Parameterized | Exponential in k, polynomial in n | Small k → practical |
