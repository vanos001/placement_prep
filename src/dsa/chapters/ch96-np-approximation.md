# Chapter 96: NP-Completeness and Approximation Algorithms

## Prerequisites

- Complexity theory basics (P, NP, NP-Hard)
- Algorithm design paradigms (greedy, dynamic programming)
- Graph algorithms
- Reduction concepts

## Interview Frequency: ★★

Understanding NP-completeness helps recognize when to stop searching for exact polynomial-time solutions and pivot to approximation or heuristic approaches. **Google**, **Amazon**, **Meta**, and research-oriented companies test this to evaluate algorithmic maturity.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| NP-Complete recognition | ★★ | Hard | Know the classic NP-C problems |
| Polynomial reductions | ★★ | Hard | Proving problems are NP-C |
| Approximation algorithms | ★★ | Medium | Near-optimal solutions with guarantees |
| Heuristics & metaheuristics | ★★★ | Medium | Practical approaches |
| FPTAS / PTAS | ★ | Hard | Approximation schemes |

---

## 96.1 What Is NP-Completeness?

### Definition

- **P**: Class of problems solvable in polynomial time by a deterministic Turing machine.
- **NP**: Class of problems whose solutions can be *verified* in polynomial time.
- **NP-Hard**: At least as hard as the hardest problems in NP (not necessarily in NP).
- **NP-Complete**: In NP *and* NP-Hard. The intersection.

A problem is **NP-Complete** if:
1. It is in NP (solutions are verifiable in polynomial time)
2. Every problem in NP can be reduced to it in polynomial time

### The P vs NP Question

- **P = NP?** is the most important open question in computer science
- Most experts believe P ≠ NP (some problems are inherently hard)
- If P = NP, most cryptography breaks, and optimization becomes easy
- A $1,000,000 Millennium Prize awaits the answer

### Motivation

Why study NP-completeness?

1. **Recognize hardness**: If your problem is NP-Complete, stop looking for a polynomial exact algorithm
2. **Redirect effort**: Focus on approximation, heuristics, or special cases
3. **Reduction tool**: Show that your new problem is at least as hard as known hard problems
4. **Interview signal**: Demonstrates theoretical maturity and practical awareness

---

## 96.2 Common NP-Complete Problems

### The Classic Set

| Problem | Input | Question | Application |
|---|---|---|---|
| **SAT** | Boolean formula | Is it satisfiable? | Circuit verification |
| **3-SAT** | 3-CNF formula | Is it satisfiable? | Foundation of NP-C proofs |
| **CLIQUE** | Graph G, integer k | Does G have a clique of size k? | Social network analysis |
| **VERTEX COVER** | Graph G, integer k | Does G have a vertex cover of size k? | Network security |
| **INDEPENDENT SET** | Graph G, integer k | Does G have an IS of size k? | Resource allocation |
| **HAMILTONIAN PATH** | Graph G | Does G visit every vertex exactly once? | Routing |
| **TSP (decision)** | Graph G, bound B | Is there a tour of cost ≤ B? | Logistics |
| **SUBSET SUM** | Set S, target t | Does any subset sum to t? | Finance, scheduling |
| **GRAPH COLORING** | Graph G, integer k | Is G k-colorable? | Map coloring, register allocation |
| **PARTITION** | Set S | Can S be split into two equal-sum subsets? | Load balancing |

### 3-SAT: The Gateway Problem

3-SAT is the starting point for many NP-completeness proofs. A 3-CNF formula is a conjunction (AND) of clauses, where each clause is a disjunction (OR) of exactly 3 literals.

**Example**: (x₁ ∨ ¬x₂ ∨ x₃) ∧ (¬x₁ ∨ x₂ ∨ x₄) ∧ (x₂ ∨ ¬x₃ ∨ ¬x₄)

**Question**: Is there an assignment of true/false to each variable that makes the entire formula true?

```cpp
#include <iostream>
#include <vector>
#include <string>

struct Clause {
    int l1, l2, l3;  // positive = variable, negative = negation
};

// Brute-force 3-SAT solver (exponential — only for small instances)
bool solve3SAT(int n, const std::vector<Clause>& clauses) {
    // Try all 2^n assignments
    for (int mask = 0; mask < (1 << n); mask++) {
        bool allSatisfied = true;
        for (auto& c : clauses) {
            bool clauseResult = false;
            for (int lit : {c.l1, c.l2, c.l3}) {
                int var = abs(lit) - 1;
                bool val = (mask >> var) & 1;
                if (lit < 0) val = !val;
                clauseResult |= val;
            }
            if (!clauseResult) { allSatisfied = false; break; }
        }
        if (allSatisfied) {
            std::cout << "Satisfying assignment: ";
            for (int i = 0; i < n; i++)
                std::cout << "x" << (i+1) << "=" << ((mask >> i) & 1) << " ";
            std::cout << "\n";
            return true;
        }
    }
    return false;
}

int main() {
    // (x1 ∨ ¬x2 ∨ x3) ∧ (¬x1 ∨ x2 ∨ x3)
    std::vector<Clause> clauses = {{1, -2, 3}, {-1, 2, 3}};
    if (!solve3SAT(3, clauses))
        std::cout << "No satisfying assignment found\n";
    return 0;
}
```

---

## 96.3 Polynomial Reductions

### What Is a Reduction?

Problem A **reduces to** problem B (written A ≤ₚ B) if:
1. There's a polynomial-time function that transforms any instance of A into an instance of B
2. The answer to A is "yes" iff the answer to the transformed B is "yes"

### The Reduction Chain

To prove a new problem X is NP-Complete:
1. Show X is in NP
2. Pick a known NP-Complete problem Y
3. Show Y ≤ₚ X (reduce Y to X)

Classic chain: SAT → 3-SAT → CLIQUE → VERTEX COVER → INDEPENDENT SET

### Example: CLIQUE ≤ₚ VERTEX COVER

**Claim**: A graph G has a clique of size k iff its complement G̅ has a vertex cover of size n-k.

**Proof sketch**:
- If S is a clique in G, then every edge in G̅ has at least one endpoint outside S (since all edges inside S exist in G, not G̅). So V-S is a vertex cover of G̅.
- If C is a vertex cover in G̅, then every non-edge in G has at least one endpoint in C. So V-C is a clique in G.

```cpp
#include <iostream>
#include <vector>
#include <set>

// Check if 'verts' forms a clique in graph 'adj'
bool isClique(const std::vector<std::set<int>>& adj,
              const std::vector<int>& verts) {
    for (int i = 0; i < (int)verts.size(); i++)
        for (int j = i + 1; j < (int)verts.size(); j++)
            if (adj[verts[i]].count(verts[j]) == 0) return false;
    return true;
}

// Check if 'verts' is a vertex cover in graph 'edges'
bool isVertexCover(const std::vector<std::pair<int,int>>& edges,
                   const std::set<int>& cover) {
    for (auto& [u, v] : edges)
        if (!cover.count(u) && !cover.count(v)) return false;
    return true;
}

int main() {
    // Triangle (clique of size 3) in K3
    std::vector<std::set<int>> adj(3);
    adj[0] = {1, 2};
    adj[1] = {0, 2};
    adj[2] = {0, 1};
    
    std::cout << "Is {0,1,2} a clique? " << isClique(adj, {0, 1, 2}) << "\n";
    
    // Complement has no edges → empty set is vertex cover of size 0 = 3-3
    std::vector<std::pair<int,int>> complementEdges;  // empty for K3
    std::set<int> emptyCover;
    std::cout << "Is {} a vertex cover of complement? "
              << isVertexCover(complementEdges, emptyCover) << "\n";
    
    return 0;
}
```

---

## 96.4 Approximation Algorithms

### Why Approximate?

When a problem is NP-Complete, we have three practical choices:
1. **Exact exponential**: Works for small inputs (n ≤ 25)
2. **Approximation**: Get a solution within a guaranteed ratio of optimal
3. **Heuristic**: Get a "usually good" solution with no formal guarantee

### Approximation Ratio

An algorithm has **approximation ratio** α (α ≥ 1 for minimization) if:

```
ALG(I) / OPT(I) ≤ α  for all instances I
```

For maximization problems, the ratio is OPT(I) / ALG(I) ≤ α, or equivalently ALG(I) ≥ OPT(I)/α.

Smaller α = better approximation. α = 1 means exact.

### Common Approximation Results

| Problem | Ratio | Algorithm | Key Idea |
|---|---|---|---|
| Vertex Cover | 2 | Greedy | Pick both endpoints of each edge |
| Set Cover | ln(n) | Greedy | Pick set covering most uncovered elements |
| Max Cut | 0.5 | Random | Random partition + local search |
| TSP (metric) | 2 | MST-based | Shortcut Euler tour |
| TSP (metric) | 1.5 | Christofides | MST + perfect matching |
| Knapsack | 1+ε | FPTAS | Scale and round values |
| Makespan (identical machines) | 2 | LPT | Longest Processing Time first |

---

## 96.5 Vertex Cover: 2-Approximation

### Problem

Given a graph G = (V, E), find the smallest set of vertices S such that every edge has at least one endpoint in S.

### Algorithm

```
APPROX-VERTEX-COVER(G):
    S = ∅
    E' = E
    while E' ≠ ∅:
        pick any edge (u, v) ∈ E'
        S = S ∪ {u, v}
        remove all edges incident to u or v from E'
    return S
```

### Why It's a 2-Approximation

- Let OPT be the optimal vertex cover size
- The algorithm picks edges that don't share endpoints (a maximal matching)
- Each edge in the matching needs at least one endpoint in any cover
- So OPT ≥ |matching| = k
- The algorithm picks 2k vertices
- Therefore ALG = 2k ≤ 2·OPT

```cpp
#include <iostream>
#include <vector>
#include <set>
#include <algorithm>

struct Edge { int u, v; };

std::vector<int> approxVertexCover(int n, std::vector<Edge> edges) {
    std::vector<bool> covered(n, false);
    std::vector<int> cover;
    
    for (auto& e : edges) {
        if (!covered[e.u] && !covered[e.v]) {
            cover.push_back(e.u);
            cover.push_back(e.v);
            covered[e.u] = covered[e.v] = true;
        }
    }
    
    return cover;
}

// Exact vertex cover via brute force (for comparison)
int exactVertexCover(int n, const std::vector<Edge>& edges) {
    int best = n;
    for (int mask = 0; mask < (1 << n); mask++) {
        int cnt = __builtin_popcount(mask);
        if (cnt >= best) continue;
        bool isCover = true;
        for (auto& e : edges) {
            if (!((mask >> e.u) & 1) && !((mask >> e.v) & 1)) {
                isCover = false;
                break;
            }
        }
        if (isCover) best = cnt;
    }
    return best;
}

int main() {
    int n = 6;
    std::vector<Edge> edges = {
        {0, 1}, {0, 2}, {1, 3}, {2, 3}, {2, 4}, {3, 5}, {4, 5}
    };
    
    auto cover = approxVertexCover(n, edges);
    int opt = exactVertexCover(n, edges);
    
    std::cout << "Approximate vertex cover (" << cover.size() << " vertices): ";
    for (int v : cover) std::cout << v << " ";
    std::cout << "\nOptimal vertex cover: " << opt << " vertices\n";
    std::cout << "Approximation ratio: " << (double)cover.size() / opt << "\n";
    
    return 0;
}
```

### Dry Run

Graph: 6 vertices, edges {(0,1), (0,2), (1,3), (2,3), (2,4), (3,5), (4,5)}

Step 1: Pick (0,1) → cover = {0,1}, remove edges (0,1), (0,2), (1,3)
Step 2: Remaining edges: (2,3), (2,4), (3,5), (4,5). Pick (2,3) → cover = {0,1,2,3}, remove (2,3), (2,4), (3,5)
Step 3: Remaining: (4,5). Pick (4,5) → cover = {0,1,2,3,4,5}

Approximate cover: 6 vertices. Optimal: 3 (e.g., {2,3,5} or {0,3,4}). Ratio: 6/3 = 2. ✓

---

## 96.6 Set Cover: ln(n)-Approximation

### Problem

Given a universe U and a collection of subsets S₁, S₂, ..., Sₘ, find the fewest subsets whose union is U.

### Greedy Algorithm

```
APPROX-SET-COVER(U, S):
    C = ∅
    covered = ∅
    while covered ≠ U:
        pick Sᵢ that maximizes |Sᵢ \ covered|
        C = C ∪ {Sᵢ}
        covered = covered ∪ Sᵢ
    return C
```

### Why ln(n) Approximation

The greedy choice always picks the set covering the most uncovered elements. Analysis shows this achieves a ratio of H(n) ≈ ln(n), where H(n) is the n-th harmonic number.

This is essentially **optimal** — unless P=NP, no polynomial algorithm can do better than (1-o(1))·ln(n).

```cpp
#include <iostream>
#include <vector>
#include <set>
#include <algorithm>

std::vector<int> approxSetCover(const std::set<int>& universe,
                                 const std::vector<std::set<int>>& sets) {
    std::set<int> covered;
    std::vector<int> selected;
    std::vector<bool> used(sets.size(), false);
    
    while (covered != universe) {
        int bestIdx = -1, bestGain = 0;
        for (int i = 0; i < (int)sets.size(); i++) {
            if (used[i]) continue;
            int gain = 0;
            for (int x : sets[i])
                if (!covered.count(x)) gain++;
            if (gain > bestGain) {
                bestGain = gain;
                bestIdx = i;
            }
        }
        
        if (bestIdx == -1) break;  // Can't cover everything
        
        used[bestIdx] = true;
        selected.push_back(bestIdx);
        for (int x : sets[bestIdx]) covered.insert(x);
    }
    
    return selected;
}

int main() {
    std::set<int> universe = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    std::vector<std::set<int>> sets = {
        {1, 2, 3, 8},        // S0
        {1, 2, 3, 4, 5},     // S1
        {4, 5, 7},           // S2
        {5, 6, 7},           // S3
        {6, 7, 8, 9, 10},    // S4
        {8, 9, 10}           // S5
    };
    
    auto selected = approxSetCover(universe, sets);
    
    std::cout << "Selected sets: ";
    for (int idx : selected) std::cout << "S" << idx << " ";
    std::cout << "\nTotal sets used: " << selected.size() << "\n";
    
    // Verify coverage
    std::set<int> covered;
    for (int idx : selected)
        for (int x : sets[idx]) covered.insert(x);
    std::cout << "Elements covered: " << covered.size() << "/" << universe.size() << "\n";
    
    return 0;
}
```

### Dry Run

Universe: {1..10}. Sets: S0={1,2,3,8}, S1={1,2,3,4,5}, S2={4,5,7}, S3={5,6,7}, S4={6,7,8,9,10}, S5={8,9,10}

Step 1: S1 covers 5 new elements (best). Select S1. Covered: {1,2,3,4,5}
Step 2: S4 covers 5 new elements (best). Select S4. Covered: {1,2,3,4,5,6,7,8,9,10}
Done! 2 sets selected. Optimal is also 2 (S1+S4). Ratio: 1.0

---

## 96.7 TSP Approximation (Metric Case)

### Problem

Given a complete graph with metric distances (triangle inequality), find the shortest tour visiting all vertices.

### MST-Based 2-Approximation

1. Find a Minimum Spanning Tree (MST)
2. Double all edges to get an Eulerian graph
3. Find an Eulerian tour
4. Shortcut repeated vertices to get a Hamiltonian tour

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

struct Point { double x, y; };

double dist(const Point& a, const Point& b) {
    double dx = a.x - b.x, dy = a.y - b.y;
    return sqrt(dx*dx + dy*dy);
}

// Prim's MST + Euler tour shortcut for 2-approx TSP
std::vector<int> approxTSP(const std::vector<Point>& pts) {
    int n = pts.size();
    std::vector<double> minDist(n, 1e18);
    std::vector<int> parent(n, -1);
    std::vector<bool> inMST(n, false);
    minDist[0] = 0;
    
    // Prim's MST
    for (int iter = 0; iter < n; iter++) {
        int u = -1;
        for (int v = 0; v < n; v++)
            if (!inMST[v] && (u == -1 || minDist[v] < minDist[u]))
                u = v;
        inMST[u] = true;
        for (int v = 0; v < n; v++) {
            if (!inMST[v]) {
                double d = dist(pts[u], pts[v]);
                if (d < minDist[v]) { minDist[v] = d; parent[v] = u; }
            }
        }
    }
    
    // Build adjacency list of MST
    std::vector<std::vector<int>> adj(n);
    for (int v = 1; v < n; v++) {
        adj[v].push_back(parent[v]);
        adj[parent[v]].push_back(v);
    }
    
    // DFS to get tour order (shortcut of Euler tour)
    std::vector<int> tour;
    std::vector<bool> visited(n, false);
    std::vector<int> stack = {0};
    while (!stack.empty()) {
        int u = stack.back(); stack.pop_back();
        if (visited[u]) continue;
        visited[u] = true;
        tour.push_back(u);
        for (int v : adj[u])
            if (!visited[v]) stack.push_back(v);
    }
    tour.push_back(0);  // return to start
    return tour;
}

int main() {
    std::vector<Point> pts = {{0,0}, {1,0}, {1,1}, {0,1}, {0.5, 0.5}};
    auto tour = approxTSP(pts);
    
    double totalDist = 0;
    std::cout << "Tour: ";
    for (int i = 0; i < (int)tour.size(); i++) {
        std::cout << tour[i] << " ";
        if (i > 0) totalDist += dist(pts[tour[i-1]], pts[tour[i]]);
    }
    std::cout << "\nTotal distance: " << totalDist << "\n";
    
    return 0;
}
```

### Why 2-Approximation?

- MST cost ≤ OPT (a tour minus one edge is a spanning tree)
- Doubled MST is Eulerian, its cost = 2·MST ≤ 2·OPT
- Shortcutting (triangle inequality) can only decrease cost
- So tour cost ≤ 2·MST ≤ 2·OPT

---

## 96.8 Knapsack FPTAS

### Problem

Given items with weights and values, and a knapsack capacity W, maximize total value.

### Fully Polynomial Time Approximation Scheme (FPTAS)

An FPTAS gives a (1+ε)-approximation in time polynomial in both n and 1/ε.

**Key idea**: Scale and round item values to reduce the DP state space.

```
1. Let V = max value of any item
2. Scale: v'ᵢ = ⌊vᵢ · n / (ε·V)⌋
3. Run DP with scaled values (smaller range → faster)
4. The result is within (1+ε) of optimal
```

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

// Exact 0/1 knapsack O(nW)
int knapsackExact(const std::vector<int>& w, const std::vector<int>& v, int W) {
    int n = w.size();
    std::vector<int> dp(W + 1, 0);
    for (int i = 0; i < n; i++)
        for (int j = W; j >= w[i]; j--)
            dp[j] = std::max(dp[j], dp[j - w[i]] + v[i]);
    return dp[W];
}

// FPTAS for knapsack
int knapsackFPTAS(const std::vector<int>& w, const std::vector<int>& v,
                  int W, double epsilon) {
    int n = w.size();
    int maxV = *max_element(v.begin(), v.end());
    
    // Scale factor
    double K = (epsilon * maxV) / n;
    if (K < 1) K = 1;
    
    // Scale values
    std::vector<int> scaledV(n);
    for (int i = 0; i < n; i++)
        scaledV[i] = (int)floor(v[i] / K);
    
    // DP on scaled values
    int maxScaledSum = 0;
    for (int x : scaledV) maxScaledSum += x;
    
    std::vector<int> dp(maxScaledSum + 1, W + 1);
    dp[0] = 0;
    
    for (int i = 0; i < n; i++) {
        for (int s = maxScaledSum; s >= scaledV[i]; s--) {
            if (dp[s - scaledV[i]] + w[i] <= W)
                dp[s] = std::min(dp[s], dp[s - scaledV[i]] + w[i]);
        }
    }
    
    // Find maximum achievable scaled value
    int best = 0;
    for (int s = maxScaledSum; s >= 0; s--) {
        if (dp[s] <= W) { best = s; break; }
    }
    
    return (int)(best * K);  // Approximate original value
}

int main() {
    std::vector<int> w = {2, 3, 4, 5};
    std::vector<int> v = {3, 4, 5, 6};
    int W = 8;
    
    int exact = knapsackExact(w, v, W);
    int approx = knapsackFPTAS(w, v, W, 0.1);
    
    std::cout << "Exact optimal: " << exact << "\n";
    std::cout << "FPTAS (ε=0.1): " << approx << "\n";
    std::cout << "Ratio: " << (double)exact / approx << "\n";
    
    return 0;
}
```

### Complexity

| Method | Time | Guarantee |
|---|---|---|
| Exact DP | O(nW) | Optimal |
| FPTAS | O(n³/ε) | (1+ε)-approx |
| Greedy (value/weight) | O(n log n) | No fixed ratio |

---

## 96.9 Metaheuristics: When Guarantees Aren't Enough

### Simulated Annealing

Inspired by metal cooling. Accept worse solutions with decreasing probability to escape local optima.

```
T = T_initial
while T > T_min:
    pick random neighbor solution S'
    Δ = cost(S') - cost(S)
    if Δ < 0: S = S'          # better: always accept
    else: S = S' with prob e^(-Δ/T)
    T = T * cooling_rate
```

### Genetic Algorithms

Inspired by evolution. Maintain a population of solutions, combine (crossover) and mutate them.

```
initialize population P
while not converged:
    evaluate fitness of each solution
    select parents (tournament, roulette wheel)
    create offspring via crossover
    apply mutations
    replace weakest in P with offspring
```

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <algorithm>
#include <cmath>

// Simulated Annealing for Max Cut
struct MaxCutSA {
    int n;
    std::vector<std::vector<int>> adj;
    std::mt19937 rng;
    
    MaxCutSA(int n) : n(n), adj(n), rng(42) {}
    
    void addEdge(int u, int v) { adj[u].push_back(v); adj[v].push_back(u); }
    
    int cutSize(const std::vector<int>& partition) {
        int cut = 0;
        for (int u = 0; u < n; u++)
            for (int v : adj[u])
                if (u < v && partition[u] != partition[v]) cut++;
        return cut;
    }
    
    std::vector<int> solve(int iterations) {
        std::uniform_int_distribution<int> bitDist(0, 1);
        std::uniform_real_distribution<double> probDist(0.0, 1.0);
        std::uniform_int_distribution<int> nodeDist(0, n-1);
        
        // Random initial solution
        std::vector<int> current(n);
        for (int& x : current) x = bitDist(rng);
        int currentCut = cutSize(current);
        
        std::vector<int> best = current;
        int bestCut = currentCut;
        
        double T = 10.0;
        for (int iter = 0; iter < iterations; iter++) {
            // Random neighbor: flip one bit
            int node = nodeDist(rng);
            current[node] ^= 1;
            int newCut = cutSize(current);
            
            double delta = newCut - currentCut;
            if (delta > 0 || probDist(rng) < exp(delta / T)) {
                currentCut = newCut;
                if (currentCut > bestCut) {
                    bestCut = currentCut;
                    best = current;
                }
            } else {
                current[node] ^= 1;  // revert
            }
            
            T *= 0.9999;  // cooling
        }
        
        std::cout << "Best cut size: " << bestCut << "\n";
        return best;
    }
};

int main() {
    MaxCutSA solver(6);
    solver.addEdge(0, 1); solver.addEdge(0, 2);
    solver.addEdge(1, 3); solver.addEdge(2, 3);
    solver.addEdge(2, 4); solver.addEdge(3, 5);
    solver.addEdge(4, 5); solver.addEdge(0, 5);
    
    auto partition = solver.solve(100000);
    std::cout << "Partition: ";
    for (int x : partition) std::cout << x << " ";
    std::cout << "\n";
    
    return 0;
}
```

---

## Summary

| Approach | When to Use | Quality Guarantee | Time |
|---|---|---|---|
| Exact (brute force) | n ≤ 20 | Optimal | O(2ⁿ) |
| Exact (DP) | Pseudo-polynomial | Optimal | O(nW) for knapsack |
| PTAS | Need (1+ε) guarantee | (1+ε) | O(n^f(1/ε)) |
| FPTAS | Need fast approximation | (1+ε) | O(n³/ε) |
| Greedy approximation | Practical, with bounds | Constant or log factor | Polynomial |
| Simulated annealing | Complex optimization | No formal guarantee | Configurable |
| Genetic algorithms | Combinatorial optimization | No formal guarantee | Configurable |

---

## Exercises

1. **Prove NP-Completeness**: Show that the Hamiltonian Cycle problem is NP-Complete by reducing from Hamiltonian Path.

2. **Implement 3-Approximation**: Design a 3-approximation algorithm for the Traveling Salesman Problem when the triangle inequality does NOT hold (hint: use MST and shortcutting with a different analysis).

3. **Set Cover Analysis**: Prove that the greedy set cover algorithm achieves an approximation ratio of H(n) = 1 + 1/2 + 1/3 + ... + 1/n.

4. **Knapsack PTAS**: Implement a PTAS (not FPTAS) for knapsack that enumerates all subsets of k items and fills the rest greedily. What is the running time?

5. **Max Cut Local Search**: Implement a local search algorithm for Max Cut that repeatedly moves a vertex from one side to the other if it improves the cut. Does this always find the global optimum?

6. **Subset Sum FPTAS**: Design an FPTAS for the Subset Sum problem similar to the knapsack FPTAS.

---

## Interview Questions

1. **Q**: What's the difference between NP-Hard and NP-Complete?
   **A**: NP-Hard means at least as hard as NP (could be harder, doesn't have to be in NP). NP-Complete is both NP-Hard AND in NP. Every NP problem reduces to an NP-Hard problem, but NP-Complete problems can also have their solutions verified in polynomial time.

2. **Q**: If someone claims to have a polynomial-time algorithm for an NP-Complete problem, what should you think?
   **A**: Either P=NP (revolutionary!), or there's a bug, or the problem instance has special structure. In practice, verify: (1) Does it handle all instances? (2) Is the complexity analysis correct? (3) Are the data structures truly polynomial?

3. **Q**: Why is the Vertex Cover greedy algorithm a 2-approximation and not better?
   **A**: The algorithm always picks both endpoints of an edge, but the optimal might need only one. In a star graph with center connected to n-1 leaves, the optimal is 1 (the center), but the algorithm picks 2 per edge. However, analysis shows it can't be worse than 2× optimal.

4. **Q**: When would you use simulated annealing over a greedy approximation?
   **A**: When the problem doesn't have a known good approximation ratio, when the instance structure allows good local optima, or when you need a solution quickly and can tolerate some randomness. SA is great for combinatorial problems like circuit design, scheduling, and protein folding.

5. **Q**: What makes a problem suitable for FPTAS vs PTAS?
   **A**: FPTAS requires the problem to have a pseudo-polynomial exact algorithm (like knapsack's O(nW) DP). The scaling trick reduces the state space. PTAS doesn't require this but may have exponential dependence on 1/ε, making it impractical for small ε.

---

## Cross-References

- **Chapter 95**: Complexity Theory — foundations of P, NP, reductions
- **Chapter 97**: Backtracking — exact exponential algorithms for NP problems
- **Chapter 98**: Branch and Bound — smarter exact search
- **Chapter 40**: Greedy Algorithms — foundation for approximation algorithms
- **Chapter 45**: Dynamic Programming — pseudo-polynomial solutions
- **Chapter 70**: Graph Algorithms — MST-based TSP approximation
