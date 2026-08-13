# Chapter 148: Parameterized Algorithms

## Prerequisites
- NP-completeness, graph algorithms, combinatorial optimization, recursion and branching

## Interview Frequency: ★★

Parameterized algorithms are a framework for solving NP-hard problems by isolating the exponential explosion to a *parameter* k, rather than the input size n. This allows tractable solutions when k is small, even though the problem is NP-hard in general. They are essential in combinatorial optimization, bioinformatics, network design, and compiler optimization. Companies like Google, Microsoft Research, and IBM Research use parameterized techniques for real-world NP-hard instances.

---

## 148.1 Motivation

Many NP-hard problems have inputs where a specific quantity (like the size of a solution) is small. Classical complexity treats all inputs uniformly — an O(n^k) algorithm is "polynomial" but useless if k = 10 and n = 1000. Parameterized complexity asks: **can we confine the exponential blowup to k alone?**

**Example**: Vertex Cover — find the smallest set of vertices that covers all edges. If the optimal cover has size k, a branching algorithm runs in O(2^k · n) time. For k = 20 and n = 10^6, that's about 10^6 · 10^6 = 10^{12} — feasible with pruning, whereas brute-force C(n, k) is astronomical.

---

## 148.2 Key Definitions

| Term | Definition | Notation |
|---|---|---|
| **Parameter** | An integer k derived from the input | Usually solution size |
| **FPT** (Fixed-Parameter Tractable) | Solvable in f(k) · n^{O(1)} time | The gold standard |
| **XP** | Solvable in n^{f(k)} time | Polynomial for fixed k, but exponent depends on k |
| **W[1]** | Believed not FPT | Parameterized analogue of NP-hard |
| **Kernel** | Equivalent instance of size g(k) | Used for preprocessing |
| **Bounded search tree** | Recursion tree with ≤ f(k) leaves | Core FPT technique |

---

## 148.3 FPT vs XP — The Critical Difference

| Class | Time Complexity | Example | Practical? |
|---|---|---|---|
| FPT | f(k) · n^{O(1)} | Vertex Cover in O(2^k · n) | ✅ Yes, for small k |
| XP | n^{f(k)} | Clique in O(n^k) | ❌ Exponential in k |
| W[1]-hard | Believed not FPT | k-Clique, k-Dominating Set | ❌ No FPT algorithm known |

**Intuition**: FPT means "hardness is entirely in k." XP means "hardness leaks into n." FPT is the parameterized equivalent of "polynomial time."

---

## 148.4 Technique 1: Branching (Bounded Search Trees)

The most intuitive FPT technique. At each step, make a bounded number of choices that reduce k.

### Vertex Cover — O(2^k · n)

**Algorithm**:
1. Pick any uncovered edge (u, v).
2. Any vertex cover must include u or v.
3. Branch: include u (remove u and its incident edges, k → k-1) or include v (same).
4. Base case: k = 0 and no edges remain → success. k = 0 and edges remain → failure.

**Recursion tree**: At most 2^k leaves. Each node does O(n) work. Total: O(2^k · n).

### Step-by-Step Walkthrough

Graph: edges {(0,1), (1,2), (2,3), (3,4)}, k = 2

```
Pick edge (0,1):
├─ Include 0: remove edges (0,1). Remaining: {(1,2), (2,3), (3,4)}, k=1
│   Pick edge (1,2):
│   ├─ Include 1: remove (1,2). Remaining: {(2,3), (3,4)}, k=0 → FAIL
│   └─ Include 2: remove (1,2),(2,3). Remaining: {(3,4)}, k=0 → FAIL
│   → Both fail, backtrack
└─ Include 1: remove (0,1),(1,2). Remaining: {(2,3), (3,4)}, k=1
    Pick edge (2,3):
    ├─ Include 2: remove (2,3). Remaining: {(3,4)}, k=0 → FAIL
    └─ Include 3: remove (2,3),(3,4). Remaining: {}, k=0 → SUCCESS
    → Cover = {1, 3}
```

---

## 148.5 Technique 2: Kernelization

**Definition**: A *kernelization algorithm* is a polynomial-time procedure that reduces an instance (I, k) to an equivalent instance (I', k') where |I'| ≤ g(k) and k' ≤ k.

**Why it matters**: After kernelization, apply any algorithm (even exponential) to the small kernel. It's a form of preprocessing with guarantees.

### Vertex Cover — 2k Kernel (Buss Reduction)

**Rule**: If any vertex has degree > k, it *must* be in any cover of size ≤ k (otherwise all its neighbors must be, giving > k vertices). Remove it and decrement k.

After removing all high-degree vertices, if more than k² edges remain, no cover of size ≤ k exists (each of k vertices covers ≤ k edges).

**Result**: At most k² edges and 2k vertices → kernel of size O(k²).

### Walkthrough

Graph with n = 100, edges from vertex 0 to all others (star graph), k = 3.

1. Vertex 0 has degree 99 > 3. **Must** include 0. Remove it, k = 2.
2. No edges remain. Cover = {0}, size 1 ≤ 3. ✅

---

## 148.6 Technique 3: Color Coding

**Problem**: Find a simple path of length k in a graph.

**Idea**: Randomly color each vertex with one of k colors. A colorful path (all colors distinct) of length k exists iff a k-path exists. Probability that a fixed k-path is colorful: k!/k^k ≥ e^{-k}.

**Algorithm**: Repeat O(e^k) random colorings. For each, use DP to find a colorful path in O(2^k · n) time.

**Total time**: O(e^k · 2^k · n · log n) — FPT in k!

### Deterministic Version

Use k-perfect hash families to derandomize. Achieves O(2^{O(k)} · n · log n) deterministically.

---

## 148.7 Technique 4: Iterative Compression

Used for problems like Feedback Vertex Set (FVS).

**Idea**: Build the solution incrementally. Given a solution of size k+1 for vertices {v_1, ..., v_{i+1}}, compress it to a solution of size ≤ k for the same vertex set.

**Feedback Vertex Set**: Given a graph, find the smallest set of vertices whose removal makes the graph acyclic.

**Algorithm sketch**:
1. Order vertices v_1, ..., v_n.
2. Start with FVS = {} for the empty graph.
3. For each v_i, add v_i to the current FVS (now size ≤ k+1).
4. Try all 2^{k+1} subsets of the current FVS as candidates. Check each.

**Time**: O(2^k · n · m) — FPT!

---

## 148.8 Full C++ Implementation — Vertex Cover FPT

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <climits>

// FPT Vertex Cover with branching
class VertexCoverFPT {
    int n;
    std::vector<std::set<int>> adj;
    
public:
    VertexCoverFPT(int n) : n(n), adj(n) {}
    
    void addEdge(int u, int v) {
        adj[u].insert(v);
        adj[v].insert(u);
    }
    
    // Returns minimum vertex cover size, or k+1 if > k
    int solve(int k) {
        if (k < 0) return INT_MAX;
        
        // Find an uncovered edge
        int u = -1, v = -1;
        for (int i = 0; i < n; i++) {
            if (!adj[i].empty()) {
                u = i;
                v = *adj[i].begin();
                break;
            }
        }
        if (u == -1) return 0; // No edges
        
        // Branch on u
        auto adjBackup = adj;
        int degU = adj[u].size();
        removeVertex(u);
        int coverWithU = solve(k - 1);
        adj = adjBackup;
        
        // Branch on v
        adjBackup = adj;
        removeVertex(v);
        int coverWithV = solve(k - 1);
        adj = adjBackup;
        
        int result = 1 + std::min(coverWithU, coverWithV);
        return (result > k) ? k + 1 : result;
    }
    
private:
    void removeVertex(int v) {
        for (int neighbor : adj[v]) {
            adj[neighbor].erase(v);
        }
        adj[v].clear();
    }
};

int main() {
    // Example: Path graph 0-1-2-3-4
    VertexCoverFPT vc(5);
    vc.addEdge(0, 1);
    vc.addEdge(1, 2);
    vc.addEdge(2, 3);
    vc.addEdge(3, 4);
    
    for (int k = 0; k <= 4; k++) {
        vc = VertexCoverFPT(5);
        vc.addEdge(0, 1); vc.addEdge(1, 2);
        vc.addEdge(2, 3); vc.addEdge(3, 4);
        int result = vc.solve(k);
        std::cout << "k=" << k << ": "
                  << (result <= k ? "YES (size " + std::to_string(result) + ")" : "NO")
                  << "\n";
    }
    // Expected: k=0 NO, k=1 NO, k=2 YES (cover = {1,3} or {2,3})
    
    return 0;
}
```

---

## 148.9 Python Implementation

```python
from typing import List, Set, Tuple

class VertexCoverFPT:
    """FPT algorithm for Vertex Cover using bounded search tree."""
    
    def __init__(self, n: int):
        self.n = n
        self.adj: List[Set[int]] = [set() for _ in range(n)]
    
    def add_edge(self, u: int, v: int):
        self.adj[u].add(v)
        self.adj[v].add(u)
    
    def solve(self, k: int) -> int:
        """Returns min vertex cover size, or k+1 if > k."""
        if k < 0:
            return float('inf')
        
        # Find an uncovered edge
        u, v = -1, -1
        for i in range(self.n):
            if self.adj[i]:
                u = i
                v = next(iter(self.adj[i]))
                break
        
        if u == -1:  # No edges
            return 0
        
        # Branch: include u
        backup = [s.copy() for s in self.adj]
        self._remove_vertex(u)
        with_u = self.solve(k - 1)
        self.adj = backup
        
        # Branch: include v
        backup = [s.copy() for s in self.adj]
        self._remove_vertex(v)
        with_v = self.solve(k - 1)
        self.adj = backup
        
        result = 1 + min(with_u, with_v)
        return min(result, k + 1)
    
    def _remove_vertex(self, v: int):
        for neighbor in list(self.adj[v]):
            self.adj[neighbor].discard(v)
        self.adj[v].clear()


def demo():
    vc = VertexCoverFPT(5)
    for u, v in [(0,1), (1,2), (2,3), (3,4)]:
        vc.add_edge(u, v)
    
    for k in range(5):
        vc_copy = VertexCoverFPT(5)
        for u, v in [(0,1), (1,2), (2,3), (3,4)]:
            vc_copy.add_edge(u, v)
        result = vc_copy.solve(k)
        status = f"YES (size {result})" if result <= k else "NO"
        print(f"k={k}: {status}")

demo()
```

---

## 148.10 Java Implementation

```java
import java.util.*;

public class VertexCoverFPT {
    private int n;
    private Set<Integer>[] adj;
    
    @SuppressWarnings("unchecked")
    public VertexCoverFPT(int n) {
        this.n = n;
        this.adj = new HashSet[n];
        for (int i = 0; i < n; i++) adj[i] = new HashSet<>();
    }
    
    public void addEdge(int u, int v) {
        adj[u].add(v);
        adj[v].add(u);
    }
    
    public int solve(int k) {
        if (k < 0) return Integer.MAX_VALUE;
        
        int u = -1, v = -1;
        for (int i = 0; i < n; i++) {
            if (!adj[i].isEmpty()) {
                u = i;
                v = adj[i].iterator().next();
                break;
            }
        }
        if (u == -1) return 0;
        
        // Branch on u
        Set<Integer>[] backup = cloneAdj();
        removeVertex(u);
        int withU = solve(k - 1);
        adj = backup;
        
        // Branch on v
        backup = cloneAdj();
        removeVertex(v);
        int withV = solve(k - 1);
        adj = backup;
        
        int result = 1 + Math.min(withU, withV);
        return Math.min(result, k + 1);
    }
    
    private void removeVertex(int v) {
        for (int neighbor : new ArrayList<>(adj[v])) {
            adj[neighbor].remove(v);
        }
        adj[v].clear();
    }
    
    @SuppressWarnings("unchecked")
    private Set<Integer>[] cloneAdj() {
        Set<Integer>[] copy = new HashSet[n];
        for (int i = 0; i < n; i++) copy[i] = new HashSet<>(adj[i]);
        return copy;
    }
    
    public static void main(String[] args) {
        VertexCoverFPT vc = new VertexCoverFPT(5);
        vc.addEdge(0, 1); vc.addEdge(1, 2);
        vc.addEdge(2, 3); vc.addEdge(3, 4);
        
        for (int k = 0; k <= 4; k++) {
            VertexCoverFPT copy = new VertexCoverFPT(5);
            copy.addEdge(0, 1); copy.addEdge(1, 2);
            copy.addEdge(2, 3); copy.addEdge(3, 4);
            int result = copy.solve(k);
            System.out.printf("k=%d: %s%n", k,
                result <= k ? "YES (size " + result + ")" : "NO");
        }
    }
}
```

---

## 148.11 Complexity Analysis

| Technique | Time | Space | Example Problem |
|---|---|---|---|
| Branching | O(c^k · n) | O(n + k) | Vertex Cover (c=2) |
| Kernelization | poly(n) + f(k) | O(g(k)) | Vertex Cover (2k kernel) |
| Color Coding | O(e^k · 2^k · n) | O(2^k · n) | k-Path |
| Iterative Compression | O(2^k · poly(n)) | O(n + 2^k) | Feedback Vertex Set |
| Crown Decomposition | O(3^k · n) | O(n) | Vertex Cover |

---

## 148.12 Advanced Topics

### Measure & Conquer
Assign non-uniform weights to branching decisions. Prove that each branch reduces a potential function by at least a fixed amount. Achieves tighter bounds than naive branching.

### Treewidth-Based Algorithms
Many NP-hard problems become polynomial on graphs of bounded treewidth. Dynamic programming on tree decompositions runs in O(2^{tw} · n) for many problems.

**Example**: Independent Set on graphs with treewidth tw runs in O(2^{tw} · n).

### Win/Win Strategy
If treewidth is small → use treewidth-based DP. If treewidth is large → use structural properties (large grid minor → specific decomposition). Either way, FPT.

---

## 148.13 Exercises

1. **Easy**: Show that the Feedback Vertex Set problem has an FPT algorithm with running time O(2^k · n²). Describe the branching rule.

2. **Medium**: Implement a kernelization algorithm for Vertex Cover that achieves a 2k vertex kernel using the Buss reduction rule.

3. **Medium**: Design an FPT algorithm for the k-Path problem using color coding. Analyze the success probability of a single random coloring.

4. **Hard**: Prove that k-Clique is W[1]-complete. (Hint: reduce from k-Step Nondeterministic Turing Machine.)

5. **Hard**: Implement an iterative compression algorithm for Feedback Vertex Set in O(2^k · n · m) time.

---

## 148.14 Interview Questions

1. **Q**: What is the difference between FPT and XP? Give an example of each.
   **A**: FPT: time f(k) · n^{O(1)}, e.g., Vertex Cover in O(2^k · n). XP: time n^{f(k)}, e.g., k-Clique in O(n^k). FPT confines all exponential blowup to k; XP has k in the exponent of n.

2. **Q**: Explain kernelization. Why is it useful?
   **A**: A kernelization algorithm reduces an instance (I, k) to an equivalent instance (I', k') with |I'| ≤ g(k) in polynomial time. It provides guaranteed preprocessing: after kernelization, any algorithm (even exponential) works on a small instance.

3. **Q**: How does color coding find a k-path?
   **A**: Randomly color vertices with k colors. A k-path is "colorful" if all vertices have distinct colors. Use DP over subsets of colors to find colorful paths. Repeat O(e^k) times; with high probability, at least one run detects the k-path.

4. **Q**: Is every NP-hard problem also W[1]-hard?
   **A**: No. NP-hardness and W[1]-hardness measure different things. Vertex Cover is NP-hard but FPT (not W[1]-hard under standard assumptions). k-Clique is W[1]-hard. The parameter matters.

5. **Q**: When would you use iterative compression over branching?
   **A**: Iterative compression is useful when the problem admits a natural "compression step" — given a solution of size k+1, find one of size k. It's particularly effective for problems like Feedback Vertex Set and Odd Cycle Transversal.

---

## 148.15 Cross-References

- **Chapter 97 (Pattern Recognition)**: NP-hard problems and when to use approximation
- **Chapter 69 (Graph Algorithms)**: Underlying graph techniques
- **Chapter 45 (Backtracking)**: Unparameterized version of branching
- **Chapter 88 (Dynamic Programming on Graphs)**: Treewidth-based DP
- **Chapter 156 (Dynamic Graph Algorithms)**: Maintaining graph properties dynamically

---

## Summary

| Technique | Core Idea | Time | Key Problem |
|---|---|---|---|
| Branching | Bounded choices per step | O(c^k · n) | Vertex Cover |
| Kernelization | Preprocess to size g(k) | poly(n) | Any FPT problem |
| Color Coding | Random coloring + DP | O(e^k · 2^k · n) | k-Path |
| Iterative Compression | Build solution incrementally | O(2^k · poly(n)) | FVS, OCT |
| Treewidth DP | DP on tree decomposition | O(2^{tw} · n) | IS, Coloring on bounded tw |
