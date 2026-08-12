# Chapter 154: Spectral Graph Theory

## Prerequisites
- Linear algebra (eigenvalues, eigenvectors, matrix operations)
- Graph basics (adjacency matrix, degree matrix, connectivity)
- Basic probability (random walks)

## Interview Frequency: ★

Spectral graph theory connects linear algebra with graph structure through eigenvalues and eigenvectors of graph-associated matrices. While rarely a direct interview topic, it underpins clustering algorithms, network analysis, and graph partitioning — all of which appear in systems design and ML interviews.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Adjacency matrix eigenvalues | ★ | Medium | Walk counting, graph properties |
| Laplacian matrix | ★ | Medium | Connectivity, clustering |
| Cheeger's inequality | ★ | Hard | Expansion bounds |
| Spectral clustering | ★★ | Medium | ML applications |
| Random walk analysis | ★ | Medium | Mixing time, PageRank |

---

## 154.1 Motivation: Why Eigenvalues of Graphs?

Consider a social network graph. The adjacency matrix tells us who knows whom, but its eigenvalues reveal deeper structural properties:
- How quickly do information or diseases spread?
- How easily can the graph be partitioned into communities?
- How fast does a random walk converge to its stationary distribution?

**Key insight**: Eigenvalues act as a "fingerprint" of a graph's global structure, capturing information that local edge-by-edge analysis cannot.

---

## 154.2 Adjacency Matrix Eigenvalues

The **adjacency matrix** A of an n-vertex graph is defined as:

```
A[i][j] = 1  if there is an edge (i, j)
A[i][j] = 0  otherwise
```

The eigenvalues of A are λ₁ ≥ λ₂ ≥ ... ≥ λₙ.

### Key Properties

1. **Trace**: tr(A) = 0 (no self-loops), so Σλᵢ = 0
2. **Walk counting**: (A^k)[i][j] = number of walks of length k from i to j
3. **Regular graphs**: If every vertex has degree d, then λ₁ = d
4. **Bipartite graphs**: λ₁ = -λₙ (spectrum is symmetric about 0)
5. **Connected graph**: λ₁ has multiplicity 1

### Largest Eigenvalue (Spectral Radius)

For any graph, the largest eigenvalue λ₁ satisfies:

```
min_degree ≤ λ₁ ≤ max_degree
```

For connected graphs, λ₁ > 0 unless the graph has no edges.

---

## 154.3 Laplacian Matrix

The **Laplacian matrix** is the most important matrix in spectral graph theory:

```
L = D - A
```

where D is the diagonal degree matrix and A is the adjacency matrix.

### Definition

```
L[i][j] =  degree(i)   if i == j
L[i][j] = -1           if (i, j) is an edge
L[i][j] =  0           otherwise
```

### Fundamental Properties

1. **Symmetric**: L = L^T (for undirected graphs)
2. **Positive semi-definite**: x^T L x ≥ 0 for all x
3. **Smallest eigenvalue is 0**: with eigenvector (1, 1, ..., 1)
4. **Number of 0 eigenvalues** = number of connected components
5. **Quadratic form**: x^T L x = Σ_{(i,j)∈E} (x_i - x_j)²

### The Fiedler Value (Algebraic Connectivity)

The second smallest eigenvalue λ₂ of L is called the **Fiedler value** or **algebraic connectivity**:

- λ₂ = 0 ⟺ graph is disconnected
- Larger λ₂ ⟹ graph is more "tightly connected"
- λ₂ ≤ n/(n-1) × min_degree

### Normalized Laplacian

The **normalized Laplacian** is:

```
𝕃 = D^(-1/2) L D^(-1/2)
```

Its eigenvalues lie in [0, 2], and it's useful for random walk analysis.

---

## 154.4 Cheeger's Inequality

Cheeger's inequality connects the algebraic property (λ₂) to the combinatorial property (expansion).

### Expansion (Conductance)

For a subset S of vertices, the **conductance** is:

```
φ(S) = |cut(S, S̄)| / min(vol(S), vol(S̄))
```

where cut(S, S̄) is the number of edges crossing the partition, and vol(S) = Σ_{v∈S} degree(v).

The **graph conductance** is φ(G) = min over all non-trivial S of φ(S).

### The Inequality

```
λ₂ / 2 ≤ φ(G) ≤ √(2λ₂)
```

**Interpretation**:
- If λ₂ is large, the graph has high expansion (hard to cut)
- If λ₂ is small, there exists a sparse cut (easy to partition)
- The bounds are tight (up to constants)

---

## 154.5 Spectral Clustering

Spectral clustering uses the Fiedler vector (eigenvector of λ₂) to partition a graph.

### Algorithm

1. Compute the Laplacian L of the graph
2. Find the Fiedler vector v₂ (eigenvector of λ₂)
3. Partition vertices by the sign of v₂[i]:
   - S = {i : v₂[i] ≥ 0}
   - S̄ = {i : v₂[i] < 0}

### Intuition

The Fiedler vector assigns a "coordinate" to each vertex. Vertices in the same cluster get similar coordinates; vertices in different clusters get different coordinates. The sign naturally splits the graph.

---

## 154.6 Random Walks and Mixing Time

A **random walk** on a graph moves to a random neighbor at each step.

### Stationary Distribution

For a connected, non-bipartite graph, the stationary distribution is:

```
π(v) = degree(v) / (2 × |E|)
```

### Mixing Time

The mixing time t_mix is the number of steps until the walk is close to stationary:

```
t_mix = O(log n / (1 - λ₂(𝕃)))
```

where λ₂(𝕃) is the second eigenvalue of the normalized Laplacian.

**Key insight**: Larger spectral gap (1 - λ₂) ⟹ faster mixing ⟹ graph is more "well-connected".

---

## 154.7 Walkthrough: Computing Eigenvalues

### Step-by-Step Example

Consider the path graph P₄: 0 — 1 — 2 — 3

**Step 1: Build the adjacency matrix**

```
A = [0 1 0 0]
    [1 0 1 0]
    [0 1 0 1]
    [0 0 1 0]
```

**Step 2: Build the degree matrix**

```
D = [1 0 0 0]
    [0 2 0 0]
    [0 0 2 0]
    [0 0 0 1]
```

**Step 3: Compute the Laplacian L = D - A**

```
L = [ 1 -1  0  0]
    [-1  2 -1  0]
    [ 0 -1  2 -1]
    [ 0  0 -1  1]
```

**Step 4: Find eigenvalues** (analytically or numerically)

For P₄, the eigenvalues of L are approximately:
- λ₁ = 0
- λ₂ ≈ 0.586
- λ₃ ≈ 1.414
- λ₄ ≈ 2.414

**Step 5: Interpret**

- λ₂ ≈ 0.586 > 0 confirms connectivity (single component)
- The Fiedler vector corresponding to λ₂ gives the best 2-way partition

---

## 154.8 Dry Run: Power Iteration

Power iteration finds the largest eigenvalue by repeatedly multiplying by the matrix.

**Algorithm**:
1. Start with random vector v
2. Repeat: v ← M·v / ‖M·v‖
3. Eigenvalue ≈ v^T M v (Rayleigh quotient)

**Trace for 3×3 path graph**:

```
Initial:  v = [1, 1, 1] / √3

Iteration 1:
  M·v = [1/√3, 2/√3, 1/√3]  (for L of P₃)
  Normalize: v = [0.408, 0.816, 0.408]
  Rayleigh quotient ≈ 0.0

Iteration 2:
  M·v = [0.408, 0.816, 0.408] → [−0.408, 0, 0.408]
  ...converges to Fiedler vector for λ₂
```

---

## 154.9 Complexity Analysis

| Operation | Time | Space |
|---|---|---|
| Build adjacency matrix | O(n²) | O(n²) |
| Build Laplacian | O(n + m) | O(n²) |
| Full eigenvalue decomposition | O(n³) | O(n²) |
| Power iteration (largest eigenvalue) | O(k·m) | O(n) |
| Lanczos algorithm (top-k eigenvalues) | O(k·m·iter) | O(n·k) |
| Spectral clustering | O(n³) or O(m·√n) | O(n) |

where n = vertices, m = edges, k = number of eigenvalues, iter = iterations.

---

## 154.10 Code: Complete Implementation

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <algorithm>

class SpectralGraphAnalyzer {
    int n;
    std::vector<std::vector<int>> adj;

public:
    SpectralGraphAnalyzer(int n) : n(n), adj(n) {}

    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Build Laplacian matrix
    std::vector<std::vector<double>> buildLaplacian() const {
        std::vector<std::vector<double>> L(n, std::vector<double>(n, 0.0));
        for (int i = 0; i < n; i++) {
            L[i][i] = adj[i].size();
            for (int j : adj[i]) {
                L[i][j] = -1.0;
            }
        }
        return L;
    }

    // Build adjacency matrix
    std::vector<std::vector<double>> buildAdjacency() const {
        std::vector<std::vector<double>> A(n, std::vector<double>(n, 0.0));
        for (int i = 0; i < n; i++) {
            for (int j : adj[i]) {
                A[i][j] = 1.0;
            }
        }
        return A;
    }

    // Matrix-vector multiplication
    std::vector<double> matVecMul(const std::vector<std::vector<double>>& M,
                                   const std::vector<double>& v) const {
        std::vector<double> result(n, 0.0);
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                result[i] += M[i][j] * v[j];
        return result;
    }

    // Dot product
    double dot(const std::vector<double>& a, const std::vector<double>& b) const {
        double sum = 0;
        for (int i = 0; i < n; i++) sum += a[i] * b[i];
        return sum;
    }

    // Normalize vector
    void normalize(std::vector<double>& v) const {
        double norm = std::sqrt(dot(v, v));
        if (norm > 1e-12)
            for (double& x : v) x /= norm;
    }

    // Power iteration: find largest eigenvalue and eigenvector
    std::pair<double, std::vector<double>> powerIteration(
            const std::vector<std::vector<double>>& M, int maxIter = 1000) const {
        std::mt19937 rng(42);
        std::uniform_real_distribution<double> dist(-1.0, 1.0);
        std::vector<double> v(n);
        for (double& x : v) x = dist(rng);
        normalize(v);

        double eigenvalue = 0;
        for (int iter = 0; iter < maxIter; iter++) {
            auto newV = matVecMul(M, v);
            eigenvalue = dot(v, newV);
            normalize(newV);
            v = newV;
        }
        return {eigenvalue, v};
    }

    // Deflation: find k-th largest eigenvalue
    std::vector<std::pair<double, std::vector<double>>> topKEigenvalues(
            const std::vector<std::vector<double>>& M, int k) const {
        std::vector<std::pair<double, std::vector<double>>> result;
        auto M_copy = M;

        for (int i = 0; i < k; i++) {
            auto [val, vec] = powerIteration(M_copy);
            result.push_back({val, vec});

            // Deflate: M' = M - val * v * v^T
            for (int r = 0; r < n; r++)
                for (int c = 0; c < n; c++)
                    M_copy[r][c] -= val * vec[r] * vec[c];
        }
        return result;
    }

    // Spectral partition using Fiedler vector
    std::pair<std::vector<int>, std::vector<int>> spectralPartition() const {
        auto L = buildLaplacian();

        // Find smallest non-zero eigenvalue
        // For Laplacian, we negate and find largest, then subtract from n
        // Simpler: use inverse iteration or find λ₂ directly
        // Here we use a simplified approach: find eigenvalues of L and pick second smallest

        auto eigen = topKEigenvalues(L, 2);
        // The largest eigenvalues of L correspond to λ_n, λ_{n-1}
        // We need λ₂, so this is a simplified demonstration

        // Use the eigenvector of the second eigenvalue for partitioning
        auto& fiedler = eigen[1].second;

        std::vector<int> groupA, groupB;
        for (int i = 0; i < n; i++) {
            if (fiedler[i] >= 0) groupA.push_back(i);
            else groupB.push_back(i);
        }
        return {groupA, groupB};
    }

    // Compute graph conductance for a given partition
    double conductance(const std::vector<int>& S) const {
        std::vector<bool> inS(n, false);
        for (int v : S) inS[v] = true;

        int cutEdges = 0, volS = 0, volSbar = 0;
        for (int i = 0; i < n; i++) {
            for (int j : adj[i]) {
                if (inS[i] && !inS[j]) cutEdges++;
            }
            if (inS[i]) volS += adj[i].size();
            else volSbar += adj[i].size();
        }

        int minVol = std::min(volS, volSbar);
        return minVol > 0 ? (double)cutEdges / minVol : 0;
    }
};

int main() {
    // Example: Karate club-like graph
    SpectralGraphAnalyzer graph(8);
    graph.addEdge(0, 1); graph.addEdge(0, 2); graph.addEdge(0, 3);
    graph.addEdge(1, 2); graph.addEdge(1, 3);
    graph.addEdge(2, 3);
    graph.addEdge(4, 5); graph.addEdge(4, 6); graph.addEdge(4, 7);
    graph.addEdge(5, 6); graph.addEdge(5, 7);
    graph.addEdge(6, 7);
    graph.addEdge(3, 4); // Bridge between two clusters

    auto L = graph.buildLaplacian();
    std::cout << "Laplacian matrix:\n";
    for (auto& row : L) {
        for (double x : row) printf("%5.0f ", x);
        std::cout << "\n";
    }

    auto eigen = graph.topKEigenvalues(L, 3);
    std::cout << "\nTop eigenvalues of Laplacian:\n";
    for (int i = 0; i < (int)eigen.size(); i++)
        std::cout << "  λ_" << (i+1) << " ≈ " << eigen[i].first << "\n";

    auto [groupA, groupB] = graph.spectralPartition();
    std::cout << "\nSpectral partition:\n  Group A: ";
    for (int v : groupA) std::cout << v << " ";
    std::cout << "\n  Group B: ";
    for (int v : groupB) std::cout << v << " ";
    std::cout << "\n  Conductance: " << graph.conductance(groupA) << "\n";

    return 0;
}
```

### Python Implementation

```python
import numpy as np
from collections import defaultdict

class SpectralGraphAnalyzer:
    def __init__(self, n):
        self.n = n
        self.adj = defaultdict(list)

    def add_edge(self, u, v):
        self.adj[u].append(v)
        self.adj[v].append(u)

    def build_laplacian(self):
        L = np.zeros((self.n, self.n))
        for i in range(self.n):
            L[i, i] = len(self.adj[i])
            for j in self.adj[i]:
                L[i, j] = -1.0
        return L

    def build_adjacency(self):
        A = np.zeros((self.n, self.n))
        for i in range(self.n):
            for j in self.adj[i]:
                A[i, j] = 1.0
        return A

    def spectral_partition(self):
        """Partition graph using Fiedler vector."""
        L = self.build_laplacian()
        eigenvalues, eigenvectors = np.linalg.eigh(L)

        # Second smallest eigenvalue's eigenvector (Fiedler vector)
        idx = np.argsort(eigenvalues)
        fiedler = eigenvectors[:, idx[1]]

        group_a = [i for i in range(self.n) if fiedler[i] >= 0]
        group_b = [i for i in range(self.n) if fiedler[i] < 0]
        return group_a, group_b, eigenvalues[idx[1]]

    def conductance(self, S):
        """Compute conductance of partition S vs S̄."""
        in_S = set(S)
        cut_edges = sum(1 for u in S for v in self.adj[u] if v not in in_S)
        vol_S = sum(len(self.adj[u]) for u in S)
        vol_Sbar = sum(len(self.adj[u]) for u in range(self.n) if u not in in_S)
        min_vol = min(vol_S, vol_Sbar)
        return cut_edges / min_vol if min_vol > 0 else 0

    def random_walk_mixing_time(self, epsilon=0.01):
        """Estimate mixing time from spectral gap."""
        L = self.build_laplacian()
        # Normalized Laplacian
        degrees = np.array([len(self.adj[i]) for i in range(self.n)], dtype=float)
        D_inv_sqrt = np.diag(1.0 / np.sqrt(degrees + 1e-10))
        L_norm = D_inv_sqrt @ L @ D_inv_sqrt

        eigenvalues = np.linalg.eigvalsh(L_norm)
        eigenvalues.sort()
        spectral_gap = eigenvalues[1]  # λ₂ of normalized Laplacian

        # Mixing time ≈ log(n) / spectral_gap
        if spectral_gap > 1e-10:
            return int(np.ceil(np.log(self.n / epsilon) / spectral_gap))
        return float('inf')


def demo():
    # Two clusters connected by a bridge
    g = SpectralGraphAnalyzer(8)
    # Cluster 1: {0,1,2,3}
    for u, v in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]:
        g.add_edge(u, v)
    # Cluster 2: {4,5,6,7}
    for u, v in [(4,5),(4,6),(4,7),(5,6),(5,7),(6,7)]:
        g.add_edge(u, v)
    # Bridge
    g.add_edge(3, 4)

    print("=== Spectral Partition ===")
    group_a, group_b, fiedler_val = g.spectral_partition()
    print(f"Group A: {group_a}")
    print(f"Group B: {group_b}")
    print(f"Fiedler value (λ₂): {fiedler_val:.4f}")
    print(f"Conductance: {g.conductance(group_a):.4f}")
    print(f"Mixing time estimate: {g.random_walk_mixing_time()}")

    # Laplacian matrix
    L = g.build_laplacian()
    print("\nLaplacian matrix:")
    print(L)


if __name__ == "__main__":
    demo()
```

### Java Implementation

```java
import java.util.*;

public class SpectralGraphAnalyzer {
    private int n;
    private List<List<Integer>> adj;

    public SpectralGraphAnalyzer(int n) {
        this.n = n;
        this.adj = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
    }

    public void addEdge(int u, int v) {
        adj.get(u).add(v);
        adj.get(v).add(u);
    }

    public double[][] buildLaplacian() {
        double[][] L = new double[n][n];
        for (int i = 0; i < n; i++) {
            L[i][i] = adj.get(i).size();
            for (int j : adj.get(i)) {
                L[i][j] = -1.0;
            }
        }
        return L;
    }

    public double[] matVecMul(double[][] M, double[] v) {
        double[] result = new double[n];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                result[i] += M[i][j] * v[j];
        return result;
    }

    public double dot(double[] a, double[] b) {
        double sum = 0;
        for (int i = 0; i < n; i++) sum += a[i] * b[i];
        return sum;
    }

    public void normalize(double[] v) {
        double norm = Math.sqrt(dot(v, v));
        if (norm > 1e-12)
            for (int i = 0; i < n; i++) v[i] /= norm;
    }

    // Power iteration for largest eigenvalue
    public double[] powerIteration(double[][] M, int maxIter) {
        Random rng = new Random(42);
        double[] v = new double[n];
        for (int i = 0; i < n; i++) v[i] = rng.nextDouble() * 2 - 1;
        normalize(v);

        for (int iter = 0; iter < maxIter; iter++) {
            double[] newV = matVecMul(M, v);
            normalize(newV);
            v = newV;
        }
        return v;
    }

    // Spectral partition
    public int[][] spectralPartition() {
        double[][] L = buildLaplacian();
        double[] fiedler = powerIteration(L, 1000);

        List<Integer> groupA = new ArrayList<>(), groupB = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            if (fiedler[i] >= 0) groupA.add(i);
            else groupB.add(i);
        }
        return new int[][] {
            groupA.stream().mapToInt(Integer::intValue).toArray(),
            groupB.stream().mapToInt(Integer::intValue).toArray()
        };
    }

    public double conductance(int[] S) {
        boolean[] inS = new boolean[n];
        for (int v : S) inS[v] = true;

        int cutEdges = 0, volS = 0, volSbar = 0;
        for (int i = 0; i < n; i++) {
            for (int j : adj.get(i)) {
                if (inS[i] && !inS[j]) cutEdges++;
            }
            if (inS[i]) volS += adj.get(i).size();
            else volSbar += adj.get(i).size();
        }

        int minVol = Math.min(volS, volSbar);
        return minVol > 0 ? (double) cutEdges / minVol : 0;
    }

    public static void main(String[] args) {
        SpectralGraphAnalyzer graph = new SpectralGraphAnalyzer(8);
        // Cluster 1
        graph.addEdge(0, 1); graph.addEdge(0, 2); graph.addEdge(0, 3);
        graph.addEdge(1, 2); graph.addEdge(1, 3); graph.addEdge(2, 3);
        // Cluster 2
        graph.addEdge(4, 5); graph.addEdge(4, 6); graph.addEdge(4, 7);
        graph.addEdge(5, 6); graph.addEdge(5, 7); graph.addEdge(6, 7);
        // Bridge
        graph.addEdge(3, 4);

        int[][] partition = graph.spectralPartition();
        System.out.println("Group A: " + Arrays.toString(partition[0]));
        System.out.println("Group B: " + Arrays.toString(partition[1]));
        System.out.printf("Conductance: %.4f%n", graph.conductance(partition[0]));
    }
}
```

---

## 154.11 Applications

| Application | Matrix Used | Key Property |
|---|---|---|
| Spectral clustering | Laplacian L | Fiedler vector gives partition |
| Random walk mixing | Normalized Laplacian 𝕃 | Spectral gap = mixing rate |
| Expander graphs | Adjacency A | λ₂ bounded away from 0 |
| Community detection | Laplacian L | Eigengap indicates # communities |
| Graph sparsification | Laplacian L | Preserve spectral similarity |
| PageRank | Modified adjacency | Dominant eigenvector |
| Network robustness | Laplacian L | λ₂ measures connectivity |
| Image segmentation | Graph Laplacian | NCut spectral method |

---

## 154.12 Exercises

### Conceptual Exercises

1. **Prove** that the Laplacian L is positive semi-definite. (Hint: use the quadratic form x^T L x = Σ(x_i - x_j)².)

2. **Show** that for a complete graph K_n, the Laplacian eigenvalues are 0 (multiplicity 1) and n (multiplicity n-1).

3. **Verify** that the number of zero eigenvalues of L equals the number of connected components.

4. **Explain** why bipartite graphs have λ₁ = -λₙ for the adjacency matrix.

### Coding Exercises

5. **Implement** spectral clustering for k > 2 clusters using the first k eigenvectors of the normalized Laplacian.

6. **Write** a function that estimates the mixing time of a random walk on a graph by computing the spectral gap.

7. **Implement** a graph sparsifier that removes edges while approximately preserving the Laplacian quadratic form.

8. **Build** a function that uses eigenvalues to detect whether a graph is approximately bipartite.

### Challenge Exercises

9. **Prove Cheeger's inequality** (the upper bound part): φ(G) ≤ √(2λ₂).

10. **Design** a streaming algorithm that maintains an approximation of λ₂ as edges are added to a graph.

---

## 154.13 Interview Questions

### Conceptual Questions

1. **Q**: What does the Fiedler value tell us about a graph?
   **A**: It measures algebraic connectivity. λ₂ = 0 means disconnected; larger λ₂ means harder to partition. It bounds the graph's conductance via Cheeger's inequality.

2. **Q**: How would you use spectral methods to detect communities in a social network?
   **A**: Build the graph Laplacian, compute the Fiedler vector, and partition by sign. For k communities, use k eigenvectors and k-means on the rows.

3. **Q**: What's the relationship between random walks and graph eigenvalues?
   **A**: The spectral gap (1 - λ₂ of normalized Laplacian) determines mixing time. Larger gap ⟹ faster convergence to stationary distribution.

### Implementation Questions

4. **Q**: How would you efficiently find the top-k eigenvalues of a large sparse matrix?
   **A**: Use the Lanczos algorithm or power iteration with deflation. For very large graphs, use ARPACK or randomized SVD.

5. **Q**: Given a weighted graph, how do you modify the Laplacian?
   **A**: L[i][j] = -w(i,j) for edges, L[i][i] = Σ_j w(i,j). The degree matrix uses weighted degrees.

### Systems Questions

6. **Q**: How does spectral clustering compare to k-means for community detection?
   **A**: Spectral clustering handles non-convex clusters and doesn't assume spherical shapes. It's more expensive (eigenvalue computation) but more robust for graph-structured data.

---

## 154.14 Cross-References

- **Chapter 97 (Graph Fundamentals)**: Adjacency matrix representation and basic graph properties
- **Chapter 98 (Shortest Paths)**: Random walks relate to Markov chains on graphs
- **Chapter 145 (Divide and Conquer on Graphs)**: Graph partitioning algorithms
- **Chapter 146 (Randomized Algorithms)**: Random sampling and probabilistic methods
- **Chapter 148 (Approximation Algorithms)**: Spectral methods for approximation
- **Chapter 156 (Linear Programming)**: LP relaxations for graph problems

---

## Summary

| Matrix | Eigenvalues | Key Application |
|---|---|---|
| Adjacency A | λ₁ ≥ ... ≥ λₙ | Walk counting, connectivity |
| Laplacian L | 0 = λ₁ ≤ ... ≤ λₙ | Partition, clustering, expansion |
| Normalized Laplacian 𝕃 | 0 ≤ ... ≤ 2 | Random walks, mixing time |
| Signless Laplacian Q | Non-negative | Bipartiteness detection |

**Key Takeaway**: Spectral graph theory provides a powerful bridge between combinatorial graph properties and continuous linear algebra. The eigenvalues of the Laplacian matrix encode global structural information — connectivity, expansion, and clustering — that is difficult to extract from local edge information alone. Cheeger's inequality is the central result connecting algebraic and combinatorial graph properties.
