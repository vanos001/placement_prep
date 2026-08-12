# Chapter 145: Approximation Algorithms

## Prerequisites
- Greedy algorithms
- LP basics ([Chapter 151](ch151-linear-programming.md))
- NP-completeness ([Chapter 96](ch96-np-approximation.md))
- Dynamic programming (Chapter 50)
- Graph algorithms (Chapter 70)

## Interview Frequency: ★★

Approximation algorithms provide provable guarantees for NP-hard problems. Understanding them is important for system design interviews where exact solutions are infeasible.

| Problem | Ratio | Technique | Time |
|---|---|---|---|
| Vertex Cover | 2 | Greedy | O(V+E) |
| Set Cover | ln(n) | Greedy | O(n²) |
| Metric TSP | 3/2 | Christofides | O(n³) |
| Knapsack | 1+ε | FPTAS | O(n²/ε) |
| Max Cut | 0.5 | Random | O(V+E) |

---

## Definition

An algorithm is **α-approximate** if for all inputs:
- Minimization: ALG(I) ≤ α · OPT(I)
- Maximization: ALG(I) ≥ α · OPT(I) (where α ≤ 1)

A **PTAS** (Polynomial-Time Approximation Scheme) achieves (1+ε)-approximation for any ε > 0, in polynomial time (but possibly exponential in 1/ε).

An **FPTAS** (Fully PTAS) is polynomial in both n and 1/ε.

## Motivation

Many real-world problems are NP-hard. We need solutions that:
1. Run in polynomial time
2. Are provably close to optimal
3. Are simple enough to implement and maintain

Why approximation matters in practice:

- **Large-scale optimization**: In logistics, scheduling, and network design, problem instances can have millions of variables. Exact solvers (ILP, SAT) can take hours or days. Approximation algorithms deliver near-optimal solutions in seconds.
- **Online systems**: Search engines, ad platforms, and recommendation systems need to make decisions in milliseconds. An approximation algorithm with a proven bound is far more valuable than an exact algorithm that times out.
- **Resource allocation**: Cloud providers use approximation algorithms for bin packing (VM placement) and set cover (service deployment). A 2× approximation means at most twice the cost — often acceptable when the alternative is no solution at all.
- **Competitive analysis**: When designing online algorithms, approximation ratios give worst-case guarantees. A 2-competitive algorithm never does worse than 2× the offline optimum, regardless of the input sequence.
- **Robustness**: Approximation algorithms tend to be simpler and more robust than exact solvers. Fewer edge cases, fewer numerical issues, easier to debug.

**When to use approximation vs. heuristics**: Heuristics (simulated annealing, genetic algorithms) often perform well in practice but offer no guarantees. Approximation algorithms trade some practical performance for provable bounds. In safety-critical or financially-sensitive applications, the guarantee matters.

## Intuition

Approximation algorithms trade optimality for speed, but with a guarantee. "I don't know the exact answer, but I know my answer is at most 2× worse than optimal."

The key insight is the **greediness-optimality spectrum**:
- **Brute force**: Try all possibilities → optimal but exponential time
- **Dynamic programming**: Exploit structure → optimal for some problems (e.g., knapsack with small weights)
- **Approximation**: Sacrifice a provable factor → polynomial time with bounded error
- **Heuristics**: Sacrifice guarantees entirely → fast but no worst-case bound

The approximation ratio captures the "price of polynomial time." For vertex cover, we pay at most 2× the optimal cost to get an O(V+E) algorithm instead of an exponential one. For set cover, we pay O(ln n) — which grows very slowly (ln(1,000,000) ≈ 14).

**Why not always use the best ratio?** Better approximation ratios often come with higher constants, more complex implementations, and harder correctness proofs. The 2-approximation for vertex cover is simple, fast, and easy to explain — often more valuable in practice than a 1.999-approximation that requires semidefinite programming.

---

## 145.1 Vertex Cover — 2-Approximation

### Problem

Find the smallest set of vertices such that every edge has at least one endpoint in the set.

### Algorithm

For each edge, if neither endpoint is covered, add both to the cover.

### Step-by-Step Walkthrough

Consider this graph with 7 vertices and 7 edges:

```
    0 --- 1 --- 3
    |     |     |
    2     4 --- 5
          |
          6
```

Edges: (0,1), (0,2), (1,3), (1,4), (3,5), (4,5), (4,6)

**Step 1**: Process edge (0,1) — neither 0 nor 1 is covered.
→ Add both 0 and 1 to cover. Cover = {0, 1}. Mark edges (0,1), (0,2), (1,3), (1,4) as touched.

**Step 2**: Process edge (0,2) — 0 is already covered.
→ Skip.

**Step 3**: Process edge (1,3) — 1 is already covered.
→ Skip.

**Step 4**: Process edge (1,4) — 1 is already covered.
→ Skip.

**Step 5**: Process edge (3,5) — neither 3 nor 5 is covered.
→ Add both 3 and 5 to cover. Cover = {0, 1, 3, 5}. Mark edges (3,5), (4,5) as touched.

**Step 6**: Process edge (4,5) — 5 is already covered.
→ Skip.

**Step 7**: Process edge (4,6) — neither 4 nor 6 is covered.
→ Add both 4 and 6 to cover. Cover = {0, 1, 3, 4, 5, 6}.

**Result**: Cover size = 6. Optimal cover = {1, 4, 5, 0} has size 4 (or {1, 4, 5, 2}, etc.). Ratio = 6/4 = 1.5 ≤ 2. ✓

Notice the algorithm picks both endpoints of each "selected" edge, which is wasteful — but guarantees at most 2× optimal.

### Why It's 2-Approximate

Let M be the set of edges selected by the algorithm (edges where both endpoints were uncovered). These edges form a matching — no two share an endpoint. Each edge in M needs at least one endpoint in any vertex cover, so OPT ≥ |M|. Our cover has exactly 2|M| vertices, so ALG = 2|M| ≤ 2·OPT.

### C++ Implementation

```cpp
#include <iostream>
#include <vector>

std::vector<int> approxVertexCover(
    const std::vector<std::pair<int,int>>& edges, int n) {
    std::vector<bool> covered(n, false);
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
    std::vector<std::pair<int,int>> edges = {{0,1},{0,2},{1,3},{2,4},{3,5}};
    auto cover = approxVertexCover(edges, 6);
    std::cout << "Vertex cover: ";
    for (int v : cover) std::cout << v << " ";
    std::cout << "\nSize: " << cover.size() << "\n";
    return 0;
}
```

### Python Implementation

```python
def approx_vertex_cover(edges, n):
    covered = [False] * n
    cover = []
    for u, v in edges:
        if not covered[u] and not covered[v]:
            cover.extend([u, v])
            covered[u] = covered[v] = True
    return cover

edges = [(0,1),(0,2),(1,3),(2,4),(3,5)]
cover = approx_vertex_cover(edges, 6)
print(f"Vertex cover: {cover}, size: {len(cover)}")
```

### Java Implementation

```java
import java.util.*;

public class VertexCover2Approx {
    public static List<Integer> approxVertexCover(List<int[]> edges, int n) {
        boolean[] covered = new boolean[n];
        List<Integer> cover = new ArrayList<>();
        for (int[] e : edges) {
            int u = e[0], v = e[1];
            if (!covered[u] && !covered[v]) {
                cover.add(u);
                cover.add(v);
                covered[u] = covered[v] = true;
            }
        }
        return cover;
    }

    public static void main(String[] args) {
        List<int[]> edges = List.of(
            new int[]{0,1}, new int[]{0,2}, new int[]{1,3},
            new int[]{2,4}, new int[]{3,5}
        );
        List<Integer> cover = approxVertexCover(edges, 6);
        System.out.println("Vertex cover: " + cover);
        System.out.println("Size: " + cover.size());
    }
}
```

---

## 145.2 Set Cover — ln(n)-Approximation

### Problem

Given a universe U and a collection of sets S₁, ..., Sₘ, find the minimum number of sets whose union is U.

### Algorithm

Greedy: repeatedly pick the set covering the most uncovered elements.

### Dry Run

Universe U = {1, 2, 3, 4, 5, 6}

| Index | Set |
|-------|-----|
| S₁ | {1, 2, 3} |
| S₂ | {2, 4} |
| S₃ | {3, 5} |
| S₄ | {4, 5, 6} |
| S₅ | {1, 6} |

**Step 1**: All elements uncovered = {1,2,3,4,5,6}. Count coverage:
- S₁ covers 3, S₂ covers 2, S₃ covers 2, S₄ covers 3, S₅ covers 2
- Tie between S₁ and S₄. Pick S₁ (covers {1,2,3}).
- Chosen = {S₁}. Remaining = {4,5,6}.

**Step 2**: Uncovered = {4,5,6}. Count coverage:
- S₂ covers {4} → 1, S₃ covers {5} → 1, S₄ covers {4,5,6} → 3, S₅ covers {6} → 1
- Best is S₄ (covers 3 elements). Pick S₄.
- Chosen = {S₁, S₄}. Remaining = {}.

**Result**: All elements covered with 2 sets: {S₁, S₄}. Optimal is also 2 sets (e.g., {S₁, S₄}). Ratio = 2/2 = 1.0. ✓

**Another example** (worst case): U = {1,2,...,6}, S₁ = {1,2,3,4,5}, S₂ = {6}, S₃ = {1}, S₄ = {2}, S₅ = {3}, S₆ = {4}, S₇ = {5}.
- Greedy picks S₁ (5 elements), then S₂ (1 element). Total = 2 sets.
- Optimal is also {S₁, S₂} = 2 sets. But if sets are more fragmented, greedy can do up to H(n) ≈ ln(n) times worse.

### Why It's ln(n)-Approximate

The proof uses the harmonic number H(n). Each greedy step covers at least a 1/k fraction of remaining elements (where k is the optimal number of sets). After k·H(n) steps, all elements are covered. Since H(n) ≈ ln(n), the ratio is O(ln n). This is tight — there exist instances where greedy uses Θ(ln n) times the optimal number of sets.

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <set>

std::vector<int> greedySetCover(
    const std::vector<std::set<int>>& sets, const std::set<int>& universe) {
    std::set<int> uncovered = universe;
    std::vector<int> chosen;
    std::vector<bool> used(sets.size(), false);

    while (!uncovered.empty()) {
        int best = -1, bestCover = 0;
        for (int i = 0; i < (int)sets.size(); i++) {
            if (used[i]) continue;
            int cover = 0;
            for (int x : sets[i])
                if (uncovered.count(x)) cover++;
            if (cover > bestCover) { bestCover = cover; best = i; }
        }
        if (best == -1) break;
        used[best] = true;
        chosen.push_back(best);
        for (int x : sets[best]) uncovered.erase(x);
    }
    return chosen;
}

int main() {
    std::vector<std::set<int>> sets = {{0,1,2},{1,3},{2,4},{3,5},{4,5}};
    std::set<int> universe = {0,1,2,3,4,5};
    auto cover = greedySetCover(sets, universe);
    std::cout << "Set cover indices: ";
    for (int i : cover) std::cout << i << " ";
    std::cout << "\n";
    return 0;
}
```

### Java Implementation

```java
import java.util.*;

public class SetCoverGreedy {
    public static List<Integer> greedySetCover(List<Set<Integer>> sets, Set<Integer> universe) {
        Set<Integer> uncovered = new HashSet<>(universe);
        List<Integer> chosen = new ArrayList<>();
        boolean[] used = new boolean[sets.size()];

        while (!uncovered.isEmpty()) {
            int best = -1, bestCover = 0;
            for (int i = 0; i < sets.size(); i++) {
                if (used[i]) continue;
                int cover = 0;
                for (int x : sets.get(i))
                    if (uncovered.contains(x)) cover++;
                if (cover > bestCover) { bestCover = cover; best = i; }
            }
            if (best == -1) break;
            used[best] = true;
            chosen.add(best);
            uncovered.removeAll(sets.get(best));
        }
        return chosen;
    }

    public static void main(String[] args) {
        List<Set<Integer>> sets = List.of(
            Set.of(0,1,2), Set.of(1,3), Set.of(2,4), Set.of(3,5), Set.of(4,5)
        );
        Set<Integer> universe = Set.of(0,1,2,3,4,5);
        List<Integer> cover = greedySetCover(sets, universe);
        System.out.println("Set cover indices: " + cover);
    }
}
```

---

## 145.3 Metric TSP — 3/2-Approximation (Christofides)

### Algorithm

1. Find MST
2. Find odd-degree vertices in MST
3. Find minimum weight perfect matching on odd-degree vertices
4. Combine into Eulerian graph
5. Find Eulerian tour, shortcut to Hamiltonian cycle

### Guarantee

3/2 × OPT for metric TSP (triangle inequality holds).

### Complexity

- MST: O(E log V) with Kruskal/Prim
- Minimum weight perfect matching: O(V³) with Edmonds' algorithm
- Eulerian tour: O(V + E)
- **Total**: O(V³) dominated by matching

---

## 145.4 Knapsack FPTAS

### Idea

Round values to multiples of ε·max(v)/n, then solve with DP.

### Why It Works

By rounding values to a coarser scale, the DP table has O(n²/ε) entries instead of O(n·max(v)). The rounding introduces at most ε·OPT error, giving a (1+ε)-approximation.

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

int knapsackFPTAS(const std::vector<int>& weights, const std::vector<int>& values,
                   int capacity, double epsilon) {
    int n = weights.size();
    int maxVal = *std::max_element(values.begin(), values.end());
    double scale = epsilon * maxVal / n;

    std::vector<int> scaledValues(n);
    for (int i = 0; i < n; i++)
        scaledValues[i] = (int)(values[i] / scale);

    int maxScaled = n * n / (int)(epsilon * n);
    std::vector<int> dp(maxScaled + 1, INT_MAX);
    dp[0] = 0;

    for (int i = 0; i < n; i++)
        for (int v = maxScaled; v >= scaledValues[i]; v--)
            if (dp[v - scaledValues[i]] != INT_MAX)
                dp[v] = std::min(dp[v], dp[v - scaledValues[i]] + weights[i]);

    int result = 0;
    for (int v = maxScaled; v >= 0; v--)
        if (dp[v] <= capacity) { result = v; break; }

    return (int)(result * scale);
}

int main() {
    std::vector<int> w = {2, 3, 4, 5};
    std::vector<int> v = {3, 4, 5, 6};
    std::cout << "FPTAS knapsack: " << knapsackFPTAS(w, v, 8, 0.1) << "\n";
    return 0;
}
```

### Java Implementation

```java
import java.util.*;

public class KnapsackFPTAS {
    public static int knapsackFPTAS(int[] weights, int[] values, int capacity, double epsilon) {
        int n = weights.length;
        int maxVal = Arrays.stream(values).max().getAsInt();
        double scale = epsilon * maxVal / n;

        int[] scaledValues = new int[n];
        for (int i = 0; i < n; i++)
            scaledValues[i] = (int)(values[i] / scale);

        int maxScaled = (int)(n * n / (epsilon * n));
        int[] dp = new int[maxScaled + 1];
        Arrays.fill(dp, Integer.MAX_VALUE);
        dp[0] = 0;

        for (int i = 0; i < n; i++)
            for (int v = maxScaled; v >= scaledValues[i]; v--)
                if (dp[v - scaledValues[i]] != Integer.MAX_VALUE)
                    dp[v] = Math.min(dp[v], dp[v - scaledValues[i]] + weights[i]);

        int result = 0;
        for (int v = maxScaled; v >= 0; v--)
            if (dp[v] <= capacity) { result = v; break; }

        return (int)(result * scale);
    }

    public static void main(String[] args) {
        int[] w = {2, 3, 4, 5};
        int[] v = {3, 4, 5, 6};
        System.out.println("FPTAS knapsack: " + knapsackFPTAS(w, v, 8, 0.1));
    }
}
```

---

## 145.5 Max Cut — 0.5-Approximation

### Algorithm

Randomly assign each vertex to one of two sets. Each edge is cut with probability 1/2.

### Expected Performance

E[cuts] = |E|/2 ≥ OPT/2 (since OPT ≤ |E|).

A deterministic version: assign vertices greedily to the side that maximizes cuts.

### Derandomization (Method of Conditional Expectations)

For each vertex, compute the expected number of cuts if assigned to each side (conditioned on previous assignments). Pick the side with higher expectation. This yields a deterministic 0.5-approximation.

---

## 145.6 LP Rounding for Vertex Cover

### Idea

Formulate vertex cover as an integer linear program (ILP), relax to LP, solve, and round fractional solutions.

### ILP Formulation

```
minimize  Σ x_v
subject to:
  x_u + x_v ≥ 1   for each edge (u,v)
  x_v ∈ {0, 1}     for each vertex v
```

### LP Relaxation

Replace `x_v ∈ {0, 1}` with `0 ≤ x_v ≤ 1`. This is solvable in polynomial time.

### Rounding

For each vertex v, if x_v ≥ 0.5, include v in the cover.

### Why It's 2-Approximate

- The LP solution is a lower bound: OPT ≥ OPT_LP
- Each edge (u,v) has x_u + x_v ≥ 1, so at least one of x_u, x_v ≥ 0.5
- After rounding, every edge is covered
- The number of rounded vertices is at most 2·Σ x_v = 2·OPT_LP ≤ 2·OPT

### Comparison with Greedy

| Aspect | Greedy | LP Rounding |
|--------|--------|-------------|
| Ratio | 2 | 2 |
| Time | O(V+E) | O(V³) (LP solver) |
| Simplicity | Very simple | Requires LP solver |
| Extensibility | Limited | Generalizes to set cover, multicut, etc. |

The LP rounding approach is more powerful because it generalizes: the same technique gives O(f)-approximation for f-edge-connected subgraph and other problems.

---

## Complexity Analysis

| Algorithm | Time | Space | Notes |
|-----------|------|-------|-------|
| Vertex Cover (greedy) | O(V + E) | O(V) | Single pass over edges |
| Set Cover (greedy) | O(n · m · |U|) | O(|U| + m) | n = #sets, m iterations in worst case |
| Christofides TSP | O(V³) | O(V²) | Dominated by min-weight matching |
| Knapsack FPTAS | O(n³/ε) | O(n²/ε) | DP table size depends on ε |
| Max Cut (random) | O(V + E) | O(V) | Linear time, no extra space |
| LP Rounding VC | O(V³) | O(V²) | LP solver dominates |

**Space details**:
- Vertex cover: O(V) for the `covered` boolean array
- Set cover: O(|U|) for the uncovered set + O(m) for the used array
- FPTAS: O(n²/ε) for the DP table (the bottleneck)
- LP rounding: O(V²) for the constraint matrix

---

## Exercises

1. **Implement Christofides**: Implement the 3/2-approximation for metric TSP. Test on a grid graph.

2. **Greedy vertex cover**: Implement the greedy algorithm that picks the vertex with highest degree. Compare with the 2-approximation.

3. **LP rounding**: Implement LP relaxation + rounding for set cover. Compare with the greedy approach.

4. **PTAS for knapsack**: Implement a PTAS that uses enumeration for small instances and FPTAS for large ones.

5. **Worst-case for set cover**: Construct an instance where the greedy set cover algorithm uses Θ(ln n) times the optimal number of sets. Verify numerically.

6. **Max cut derandomization**: Implement the method of conditional expectations for max cut. Compare the deterministic result with the random algorithm on 100 random graphs.

7. **Vertex cover on trees**: Show that vertex cover on trees can be solved exactly in O(V) with DP. Compare the exact solution with the 2-approximation on random trees.

---

## Interview Questions

1. **Q: What's the difference between a PTAS and an FPTAS?**
   A: A PTAS is polynomial in n for fixed ε, but may be exponential in 1/ε. An FPTAS is polynomial in both n and 1/ε. FPTAS is stronger.

2. **Q: Why is the greedy set cover O(ln n)-approximate?**
   A: Each step covers at least a 1/k fraction of remaining elements (where k is the optimal number of sets). After k·ln(n) steps, all elements are covered. The analysis uses the harmonic number H(n) ≈ ln(n).

3. **Q: Can we do better than 2-approximation for vertex cover?**
   A: The best known is 2 - O(1/√(log n)). It's NP-hard to approximate better than 2 - ε for any constant ε (under the Unique Games Conjecture).

4. **Q: How does the random max cut algorithm achieve 0.5-approximation?**
   A: Each edge has probability 1/2 of being cut (endpoints in different sets). By linearity of expectation, E[cuts] = |E|/2. Since OPT ≤ |E|, we get E[cuts] ≥ OPT/2.

5. **Q: When would you choose an approximation algorithm over a heuristic like simulated annealing?**
   A: When you need provable guarantees. Simulated annealing works well in practice but has no worst-case bound. Approximation algorithms are preferred in safety-critical systems, financial applications, or when you need to guarantee a solution quality to stakeholders.

6. **Q: Explain the LP rounding approach for vertex cover. How does it achieve a 2-approximation?**
   A: Relax the ILP to an LP (allow fractional x_v). Solve optimally. Round all x_v ≥ 0.5 to 1. Each edge (u,v) has x_u + x_v ≥ 1, so at least one endpoint rounds to 1 — every edge is covered. The cost is at most 2·Σ x_v ≤ 2·OPT.

7. **Q: Why can't we use LP rounding to get better than 2-approximation for vertex cover?**
   A: The integrality gap of the LP relaxation is 2 — there exist instances where OPT_LP = OPT/2. For example, a triangle with uniform edge weights has OPT = 2 but OPT_LP = 1.5. Any rounding scheme based on this LP can't beat factor 2.

---

## Cross-References

- [Chapter 96: NP-Completeness](ch96-np-approximation.md) — Why we need approximation
- [Chapter 151: Linear Programming](ch151-linear-programming.md) — LP rounding techniques
- [Chapter 152: Integer Programming](ch152-integer-programming.md) — LP relaxation
- Chapter 50: Dynamic Programming — Exact knapsack solution
- Chapter 70: Graph Representations — Graph basics
- Chapter 85: Greedy Algorithms — Greedy design principles
- Chapter 97: Reductions — Problem reductions and hardness
- Chapter 140: Competitive Programming — Contest applications
- [Chapter 153: Randomized Algorithms](ch63-randomized-algorithms.md) — Randomized techniques

---

## Summary

| Problem | Ratio | Technique | Time |
|---|---|---|---|
| Vertex Cover | 2 | Greedy | O(V+E) |
| Set Cover | ln(n) | Greedy | O(n²) |
| Metric TSP | 3/2 | Christofides | O(n³) |
| Knapsack | 1+ε | FPTAS | O(n²/ε) |
| Max Cut | 0.5 | Random | O(V+E) |

**Key takeaway**: Approximation algorithms bridge the gap between intractability and practicality. They give polynomial-time solutions with provable quality guarantees — essential when exact solutions are computationally infeasible.
