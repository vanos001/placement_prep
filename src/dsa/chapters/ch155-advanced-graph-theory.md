# Chapter 155: Advanced Graph Theory

## Prerequisites
- Graph algorithms, linear algebra, basic topology

## Interview Frequency: ★

Advanced graph theory topics are primarily for **research roles**, **PhD interviews**, and **specialized system design** at companies like **Google Research**, **Microsoft Research**, and **Meta FAIR**. They rarely appear in standard coding interviews but are essential for understanding modern algorithmic breakthroughs.

---

## 155.1 Expander Graphs

### Definition

An **expander graph** is a sparse graph that has strong connectivity properties. Formally, a family of graphs {Gₙ} is a (c, ε)-expander if every Gₙ has n vertices, maximum degree ≤ c, and for every subset S of vertices with |S| ≤ n/2:

```
|N(S) \ S| ≥ ε|S|
```

where N(S) is the set of neighbors of S.

### Motivation

Expander graphs are the "Swiss army knife" of theoretical computer science. They appear in:
- **Error-correcting codes**: LDPC codes use expander graphs for efficient encoding/decoding
- **Derandomization**: Expanders help convert randomized algorithms to deterministic ones
- **Communication networks**: Expander-based topologies have low diameter and high fault tolerance
- **PCP constructions**: Used in proofs of the PCP theorem
- **Pseudorandom generators**: Nisan-Wigderson generator uses expanders

### Intuition

Think of an expander as a graph that is "almost complete" in terms of connectivity but uses very few edges. Any subset of vertices has many edges going outside it—you can't "trap" a random walk in a small region.

### Formal Explanation

**Cheeger constant** (edge expansion): h(G) = min_{S, |S|≤n/2} |E(S, V\S)| / |S|

A graph family is an expander if h(G) ≥ ε > 0 for some fixed ε.

**Spectral characterization**: A d-regular graph G is an expander iff its second-largest eigenvalue λ₂ satisfies:

```
λ₂ < d - δ  for some constant δ > 0
```

The **spectral gap** d - λ₂ measures expansion quality.

### Properties

| Property | Value |
|---|---|
| Diameter | O(log n) |
| Random walk mixing time | O(log n) |
| Edge expansion | Ω(1) |
| Vertex expansion | Ω(1) |
| Spectral gap | Ω(1) |

### Code: Computing Expansion Ratio

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <algorithm>
#include <cmath>
#include <numeric>

class ExpanderAnalyzer {
public:
    // Heuristic expansion ratio estimation via random subsets
    static double expansionRatio(const std::vector<std::vector<int>>& adj, int trials = 200) {
        int n = adj.size();
        double bestRatio = 1.0;
        std::mt19937 rng(42);

        for (int trial = 0; trial < trials; trial++) {
            // Random subset S of size n/2
            std::vector<bool> inS(n, false);
            std::vector<int> perm(n);
            std::iota(perm.begin(), perm.end(), 0);
            std::shuffle(perm.begin(), perm.end(), rng);

            for (int i = 0; i < n / 2; i++)
                inS[perm[i]] = true;

            int cutEdges = 0, volS = 0;
            for (int u = 0; u < n; u++) {
                if (inS[u]) {
                    volS += adj[u].size();
                    for (int v : adj[u])
                        if (!inS[v]) cutEdges++;
                }
            }

            if (volS > 0) {
                double ratio = (double)cutEdges / std::min(volS, 2 * n - volS);
                bestRatio = std::min(bestRatio, ratio);
            }
        }
        return bestRatio;
    }

    // Compute spectral gap (approximate) via power iteration
    static double spectralGap(const std::vector<std::vector<int>>& adj) {
        int n = adj.size();
        // Normalize adjacency matrix for d-regular graph
        int d = adj[0].size();  // Assume regular

        // Power iteration for second eigenvalue
        std::mt19937 rng(42);
        std::vector<double> v(n), w(n);
        for (int i = 0; i < n; i++)
            v[i] = std::normal_distribution<double>(0, 1)(rng);

        // Remove component along first eigenvector (all-ones)
        double sum = 0;
        for (double x : v) sum += x;
        sum /= n;
        for (double& x : v) x -= sum;

        // Normalize
        double norm = 0;
        for (double x : v) norm += x * x;
        norm = std::sqrt(norm);
        for (double& x : v) x /= norm;

        // Power iterations
        for (int iter = 0; iter < 100; iter++) {
            // w = A * v / d
            std::fill(w.begin(), w.end(), 0.0);
            for (int u = 0; u < n; u++)
                for (int v_idx : adj[u])
                    w[v_idx] += v[u] / d;

            // Remove first eigenvector component
            sum = 0;
            for (double x : w) sum += x;
            sum /= n;
            for (double& x : w) x -= sum;

            // Rayleigh quotient
            double lambda = 0;
            for (int i = 0; i < n; i++) lambda += v[i] * w[i];

            // Normalize
            norm = 0;
            for (double x : w) norm += x * x;
            norm = std::sqrt(norm);
            if (norm < 1e-10) break;
            for (int i = 0; i < n; i++) v[i] = w[i] / norm;

            if (iter == 99) return lambda;  // Second eigenvalue
        }
        return 0;
    }
};

// Generate random d-regular graph
std::vector<std::vector<int>> randomRegularGraph(int n, int d, std::mt19937& rng) {
    std::vector<std::vector<int>> adj(n);
    for (int i = 0; i < n; i++) {
        while ((int)adj[i].size() < d) {
            int v = std::uniform_int_distribution<int>(0, n - 1)(rng);
            if (v != i && std::find(adj[i].begin(), adj[i].end(), v) == adj[i].end()
                && (int)adj[v].size() < d) {
                adj[i].push_back(v);
                adj[v].push_back(i);
            }
        }
    }
    return adj;
}

int main() {
    std::mt19937 rng(42);
    int n = 100, d = 3;
    auto adj = randomRegularGraph(n, d, rng);

    double expansion = ExpanderAnalyzer::expansionRatio(adj);
    double lambda2 = ExpanderAnalyzer::spectralGap(adj);

    std::cout << "Random 3-regular graph (n=100):\n";
    std::cout << "  Expansion ratio: " << expansion << "\n";
    std::cout << "  Second eigenvalue: " << lambda2 << "\n";
    std::cout << "  Spectral gap: " << (d - lambda2) << "\n";
    std::cout << "  Good expander: " << (d - lambda2 > 0.5 ? "Yes" : "No") << "\n";

    return 0;
}
```

---

## 155.2 Planar Separator Theorems

### Definition

A **separator** of a graph G is a set of vertices S whose removal disconnects G into components each of size ≤ αn (for some α < 1).

### Lipton-Tarjan Planar Separator Theorem

**Theorem**: Every planar graph with n vertices has a separator of size O(√n) that splits the graph into components each of size ≤ 2n/3.

### Motivation

This theorem enables divide-and-conquer on planar graphs with O(√n) overhead instead of O(n). Many NP-hard problems become polynomial on planar graphs using this technique.

### Applications

| Problem | General Graph | Planar Graph |
|---|---|---|
| Vertex cover | O(2ⁿ) | O(2^{O(√n)}) |
| Independent set | O(2ⁿ) | O(2^{O(√n)}) |
| TSP | O(2ⁿ · n²) | O(2^{O(√n)} · n) |
| Graph coloring | O(3ⁿ) | O(2^{O(√n)}) |

### Algorithm: Finding Planar Separator

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cmath>
#include <set>

class PlanarSeparator {
public:
    // Simplified Lipton-Tarjan separator finder
    // For actual planar graphs, need BFS layering
    static std::vector<int> findSeparator(
        const std::vector<std::vector<int>>& adj, int n) {

        // BFS layering from an arbitrary root
        std::vector<int> level(n, -1);
        std::vector<int> parent(n, -1);
        std::queue<int> q;

        int root = 0;
        level[root] = 0;
        q.push(root);

        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (level[v] == -1) {
                    level[v] = level[u] + 1;
                    parent[v] = u;
                    q.push(v);
                }
            }
        }

        // Find level that splits graph roughly in half
        int maxLevel = *std::max_element(level.begin(), level.end());
        int targetSize = n / 2;

        // Count vertices per level
        std::vector<int> levelCount(maxLevel + 1, 0);
        for (int l : level) levelCount[l]++;

        // Find separator levels
        int cumSum = 0;
        std::vector<int> separator;
        for (int l = 0; l <= maxLevel; l++) {
            if (cumSum >= targetSize / 2 && cumSum <= targetSize) {
                // Levels l-1, l, l+1 form the separator
                for (int i = 0; i < n; i++) {
                    if (level[i] >= l - 1 && level[i] <= l + 1)
                        separator.push_back(i);
                }
                break;
            }
            cumSum += levelCount[l];
        }

        return separator;
    }
};

int main() {
    // Grid graph (planar)
    int rows = 5, cols = 5;
    int n = rows * cols;
    std::vector<std::vector<int>> adj(n);

    for (int r = 0; r < rows; r++) {
        for (int c = 0; c < cols; c++) {
            int u = r * cols + c;
            if (r + 1 < rows) { adj[u].push_back((r+1)*cols + c); adj[(r+1)*cols + c].push_back(u); }
            if (c + 1 < cols) { adj[u].push_back(r*cols + c + 1); adj[r*cols + c + 1].push_back(u); }
        }
    }

    auto separator = PlanarSeparator::findSeparator(adj, n);
    std::cout << "Grid " << rows << "x" << cols << " separator size: "
              << separator.size() << " (expected O(√" << n << ") ≈ "
              << (int)std::sqrt(n) << ")\n";

    return 0;
}
```

---

## 155.3 Minor Theory

### Definition

A graph H is a **minor** of G if H can be obtained from G by:
1. Deleting edges
2. Deleting vertices
3. Contracting edges (merging endpoints)

### Robertson-Seymour Theorem

**Theorem**: In any infinite sequence of graphs G₁, G₂, G₃, ..., there exist indices i < j such that Gᵢ is a minor of Gⱼ.

**Corollary**: Every minor-closed property can be characterized by a finite set of forbidden minors.

### Grid Minor Theorem

**Theorem**: Every graph with treewidth ≥ k contains a √k × √k grid as a minor.

### Applications

| Property | Forbidden Minors | Complexity |
|---|---|---|
| Planarity | K₅, K₃,₃ | O(n) |
| Linkless embeddable | Petersen graph family | O(n³) |
| Knotless embeddable | Unknown | Open |

### Code: Minor Testing (Simplified)

```cpp
#include <iostream>
#include <vector>
#include <set>
#include <algorithm>

class MinorTester {
public:
    // Check if H is a minor of G (brute force, exponential)
    // For large graphs, use the O(n³) Robertson-Seymour algorithm
    static bool isMinor(const std::vector<std::vector<int>>& G,
                        const std::vector<std::vector<int>>& H) {
        int n = G.size(), m = H.size();

        // Try all possible mappings from H's vertices to connected subgraphs of G
        // This is exponential—real implementations use the polynomial algorithm

        // Simplified: check if we can contract G to get H
        // Try all subsets of edges to contract
        return bruteForceMinorCheck(G, H);
    }

private:
    static bool bruteForceMinorCheck(const std::vector<std::vector<int>>& G,
                                      const std::vector<std::vector<int>>& H) {
        // Very simplified check
        int n = G.size(), m = H.size();
        if (m > n) return false;

        // Check if each vertex of H maps to a connected subgraph of G
        // that are pairwise disjoint and have edges between them matching H

        // For demonstration: check basic necessary conditions
        // H is minor of G only if |V(H)| ≤ |V(G)| and |E(H)| ≤ |E(G)|
        int edgesG = 0, edgesH = 0;
        for (auto& neighbors : G) edgesG += neighbors.size();
        for (auto& neighbors : H) edgesH += neighbors.size();
        edgesG /= 2; edgesH /= 2;

        if (edgesH > edgesG) return false;

        // K5 minor check: need at least 5 vertices with high connectivity
        if (m == 5 && edgesH == 10) {
            // Check if G has a K5 minor (non-planar test)
            return n >= 5 && hasHighConnectivity(G);
        }

        return false;  // Conservative
    }

    static bool hasHighConnectivity(const std::vector<std::vector<int>>& G) {
        // Simplified: check if any 5 vertices form a dense subgraph
        int n = G.size();
        if (n < 5) return false;

        // Check average degree
        int totalDeg = 0;
        for (auto& neighbors : G) totalDeg += neighbors.size();
        double avgDeg = (double)totalDeg / n;

        return avgDeg >= 4;  // Rough heuristic
    }
};

int main() {
    // K5 (complete graph on 5 vertices)
    std::vector<std::vector<int>> K5(5);
    for (int i = 0; i < 5; i++)
        for (int j = 0; j < 5; j++)
            if (i != j) K5[i].push_back(j);

    // Petersen graph (not planar, contains K5 minor)
    std::vector<std::vector<int>> Petersen(10);
    // Outer cycle: 0-1-2-3-4
    for (int i = 0; i < 5; i++) {
        Petersen[i].push_back((i + 1) % 5);
        Petersen[(i + 1) % 5].push_back(i);
    }
    // Inner star: 5-7-9-6-8-5
    Petersen[5].push_back(7); Petersen[7].push_back(5);
    Petersen[7].push_back(9); Petersen[9].push_back(7);
    Petersen[9].push_back(6); Petersen[6].push_back(9);
    Petersen[6].push_back(8); Petersen[8].push_back(6);
    Petersen[8].push_back(5); Petersen[5].push_back(8);
    // Spokes
    for (int i = 0; i < 5; i++) {
        Petersen[i].push_back(i + 5);
        Petersen[i + 5].push_back(i);
    }

    std::cout << "K5 has K5 minor: " << MinorTester::isMinor(K5, K5) << "\n";
    std::cout << "Petersen has K5 minor: " << MinorTester::isMinor(Petersen, K5) << "\n";

    return 0;
}
```

---

## 155.4 Treewidth and Tree Decomposition

### Definition

A **tree decomposition** of graph G = (V, E) is a tree T where:
1. Each node of T is a "bag" of vertices from V
2. Every vertex appears in at least one bag
3. For every edge (u,v) ∈ E, some bag contains both u and v
4. For every vertex v, the bags containing v form a connected subtree

The **width** of a tree decomposition is the size of the largest bag minus 1. The **treewidth** of G is the minimum width over all tree decompositions.

### Motivation

Many NP-hard problems become polynomial (actually linear) on graphs with bounded treewidth. This is the foundation of **fixed-parameter tractability (FPT)**.

### Complexity of NP-hard Problems by Treewidth

| Problem | Time Complexity | Treewidth tw |
|---|---|---|
| Vertex Cover | O(2^{tw} · n) | FPT |
| Independent Set | O(2^{tw} · n) | FPT |
| Dominating Set | O(3^{tw} · n) | FPT |
| Hamiltonian Cycle | O(tw^{tw} · n) | FPT |
| Graph Coloring | O(tw^{tw} · n) | FPT |
| Max Cut | O(2^{tw} · n) | FPT |

### Algorithm: Dynamic Programming on Tree Decomposition

```cpp
#include <iostream>
#include <vector>
#include <set>
#include <algorithm>
#include <climits>

class TreeDecomposition {
    int n;
    std::vector<std::vector<int>> bags;  // Tree nodes: bags of vertices
    std::vector<std::vector<int>> tree;  // Tree structure

public:
    TreeDecomposition(int n) : n(n), tree(n) {}

    void addBag(const std::vector<int>& bag) {
        bags.push_back(bag);
    }

    void addEdge(int u, int v) {
        tree[u].push_back(v);
        tree[v].push_back(u);
    }

    // DP for Vertex Cover on tree decomposition
    int vertexCover(const std::vector<std::vector<int>>& adj) {
        int numBags = bags.size();
        if (numBags == 0) return 0;

        // DP[mask] = min vertex cover size for bag configuration
        int root = 0;
        return vcDP(root, -1, adj);
    }

private:
    int vcDP(int node, int parent, const std::vector<std::vector<int>>& adj) {
        auto& bag = bags[node];
        int bagSize = bag.size();
        int best = INT_MAX;

        // Try all subsets of the bag as vertex cover
        for (int mask = 0; mask < (1 << bagSize); mask++) {
            // Check if this subset covers all edges within the bag
            bool valid = true;
            for (int i = 0; i < bagSize && valid; i++) {
                for (int j = i + 1; j < bagSize && valid; j++) {
                    int u = bag[i], v = bag[j];
                    // If edge (u,v) exists and neither is in cover
                    if (isEdge(adj, u, v) && !(mask & (1 << i)) && !(mask & (1 << j)))
                        valid = false;
                }
            }

            if (valid) {
                int cost = __builtin_popcount(mask);

                // Add costs from children (simplified: just count)
                for (int child : tree[node]) {
                    if (child != parent) {
                        cost += vcDP(child, node, adj);
                    }
                }

                best = std::min(best, cost);
            }
        }

        return best;
    }

    bool isEdge(const std::vector<std::vector<int>>& adj, int u, int v) {
        return std::find(adj[u].begin(), adj[u].end(), v) != adj[u].end();
    }
};

int main() {
    // Simple tree (treewidth = 1)
    // 0-1-2-3
    TreeDecomposition td(4);
    td.addBag({0, 1});
    td.addBag({1, 2});
    td.addBag({2, 3});
    td.addEdge(0, 1);
    td.addEdge(1, 2);

    std::vector<std::vector<int>> adj = {{1}, {0, 2}, {1, 3}, {2}};
    int vc = td.vertexCover(adj);
    std::cout << "Vertex cover size for path-4: " << vc << "\n";  // 2

    return 0;
}
```

---

## 155.5 Clique-Width

### Definition

The **clique-width** of a graph G is the minimum number of labels needed to construct G using four operations:
1. **Create** a vertex with label i
2. **Disjoint union** of two labeled graphs
3. **Add edges** between all vertices with label i and label j
4. **Rename** label i to label j

### Comparison with Treewidth

| Measure | Bounded for | FPT for |
|---|---|---|
| Treewidth | Trees, series-parallel, outerplanar | MSO₂ logic |
| Clique-width | Cographs, distance-hereditary | MSO₁ logic (no edge quantification) |
| Rank-width | Same as clique-width | Similar |

### Key Results

- **Courcelle's theorem**: Any graph property expressible in MSO₂ logic can be decided in O(f(tw) · n) time on graphs with treewidth tw.
- For clique-width: MSO₁ properties can be decided in O(f(cw) · n) time.

---

## 155.6 Graph Homomorphism

### Definition

A **homomorphism** from graph G to graph H is a function f: V(G) → V(H) such that if (u,v) ∈ E(G), then (f(u), f(v)) ∈ E(H).

### Applications

- **Coloring**: A k-coloring is a homomorphism to Kₖ
- **Constraint satisfaction**: Many CSPs reduce to graph homomorphism
- **Database theory**: Conjunctive query evaluation

### Code: Homomorphism Counting

```cpp
#include <iostream>
#include <vector>
#include <functional>

// Count homomorphisms from pattern P to graph G
int countHomomorphisms(
    const std::vector<std::vector<int>>& P,
    const std::vector<std::vector<int>>& G) {

    int p = P.size(), n = G.size();
    int count = 0;

    // Try all mappings f: V(P) -> V(G)
    std::vector<int> mapping(p, -1);

    std::function<void(int)> dfs = [&](int v) {
        if (v == p) {
            // Check if mapping is a homomorphism
            for (int u = 0; u < p; u++) {
                for (int w : P[u]) {
                    if (w > u) {  // Check each edge once
                        // Edge (u, w) in P must map to edge (f(u), f(w)) in G
                        int fu = mapping[u], fw = mapping[w];
                        bool found = false;
                        for (int neighbor : G[fu]) {
                            if (neighbor == fw) { found = true; break; }
                        }
                        if (!found) return;
                    }
                }
            }
            count++;
            return;
        }

        for (int i = 0; i < n; i++) {
            mapping[v] = i;
            dfs(v + 1);
        }
    };

    dfs(0);
    return count;
}

int main() {
    // Pattern: edge (K2)
    std::vector<std::vector<int>> K2 = {{1}, {0}};

    // Target: triangle K3
    std::vector<std::vector<int>> K3 = {{1, 2}, {0, 2}, {0, 1}};

    std::cout << "Hom(K2, K3) = " << countHomomorphisms(K2, K3) << "\n";  // 6
    // Each of 3 edges × 2 orientations = 6

    // Target: path P3
    std::vector<std::vector<int>> P3 = {{1}, {0, 2}, {1}};
    std::cout << "Hom(K2, P3) = " << countHomomorphisms(K2, P3) << "\n";  // 4

    return 0;
}
```

---

## 155.7 Exercises

1. **Expander construction**: Construct a Margulis expander family and verify its expansion ratio.
2. **Planar separator**: Implement the full Lipton-Tarjan algorithm using BFS layering and nested dissection.
3. **Treewidth computation**: Implement the O(2ⁿ) algorithm for computing exact treewidth using the elimination ordering approach.
4. **Tree decomposition DP**: Solve the Independent Set problem on a graph with known treewidth.
5. **Forbidden minors**: Prove that K₅ and K₃,₃ are the forbidden minors for planarity.
6. **Clique-width**: Construct a graph with clique-width 3 but unbounded treewidth.
7. **Graph homomorphism**: Implement the color-coding algorithm for counting homomorphisms from a k-vertex pattern to an n-vertex graph in O(2^k · n) time.

---

## 155.8 Interview Questions

1. **What is an expander graph and why is it useful?**
   *Answer*: An expander is a sparse graph with strong connectivity (high edge expansion). It's useful because it combines the sparsity of a tree with the connectivity of a complete graph. Applications include error-correcting codes, derandomization, and network design.

2. **Explain the planar separator theorem.**
   *Answer*: Every planar graph has a vertex set of size O(√n) whose removal splits the graph into components each of size ≤ 2n/3. This enables divide-and-conquer algorithms with O(√n) overhead on planar graphs.

3. **What is treewidth and why does it matter?**
   *Answer*: Treewidth measures how "tree-like" a graph is. Trees have treewidth 1, planar graphs have treewidth O(√n). Many NP-hard problems become linear-time on graphs with bounded treewidth via dynamic programming on tree decompositions.

4. **What is the Robertson-Seymour theorem?**
   *Answer*: In any infinite sequence of graphs, one is a minor of another. Equivalently, every minor-closed property is characterized by a finite set of forbidden minors. This was a 20-year proof involving 23 papers.

5. **How does graph minor theory relate to algorithm design?**
   *Answer*: Many graph properties are minor-closed (planarity, linkless embeddability). For such properties, the Robertson-Seymour theorem guarantees O(n³) testing algorithms. Combined with treewidth, it enables FPT algorithms for problems on excluded-minor graph families.

---

## 155.9 Cross-References

- **Chapter 23**: Graph traversal (BFS/DFS for separator finding)
- **Chapter 27**: Shortest paths (used in expander analysis)
- **Chapter 78**: Dynamic programming on graphs
- **Chapter 122**: Divide and conquer (for separator-based algorithms)
- **Chapter 150**: Randomized algorithms (random expanders)
- **Chapter 161**: Advanced geometry (planar graph algorithms)

---

## Summary

| Concept | Key Property | Application |
|---|---|---|
| Expander Graphs | Sparse + high expansion | Codes, derandomization, networks |
| Planar Separator | O(√n) separator | Divide & conquer on planar graphs |
| Minor Theory | Minor-closed properties | Robertson-Seymour, forbidden minors |
| Treewidth | Tree-like decomposition | FPT algorithms for NP-hard problems |
| Clique-width | Label-based construction | MSO₁ logic problems |
| Graph Homomorphism | Structure-preserving maps | Coloring, CSPs, databases |
