# Chapter 186: Hamiltonian Paths & Cycles

A **Hamiltonian path** visits every vertex exactly once. A **Hamiltonian cycle** is such a path that returns to the start. Both are **NP-complete**, meaning no polynomial-time algorithm is known for general graphs.

---

## NP-Completeness

Hamiltonian path/cycle is NP-complete even for grid graphs and planar graphs of max degree 3. The decision problem ("does a Hamiltonian path exist?") reduces from 3-SAT. This means:

- For small n (n ≤ 20), exponential algorithms are feasible.
- For large n, look for special graph structure or use heuristics.

---

## Held-Karp: DP over Subsets — O(2ⁿ · n²)

The standard exact algorithm. State: `dp[mask][v]` = minimum cost to visit the subset `mask` of vertices, ending at vertex `v`.

```cpp
const int INF = 1e9;
int dp[1 << 20][20];
int n;
vector<vector<int>> dist;

int hamiltonian(int start) {
    memset(dp, 0x3f, sizeof dp);
    dp[1 << start][start] = 0;

    for (int mask = 1; mask < (1 << n); mask++) {
        for (int u = 0; u < n; u++) {
            if (!(mask & (1 << u))) continue;
            if (dp[mask][u] >= INF) continue;
            for (int v = 0; v < n; v++) {
                if (mask & (1 << v)) continue;
                int nmask = mask | (1 << v);
                dp[nmask][v] = min(dp[nmask][v], dp[mask][u] + dist[u][v]);
            }
        }
    }

    int ans = INF;
    int full = (1 << n) - 1;
    for (int u = 0; u < n; u++)
        ans = min(ans, dp[full][u]);
    return ans;
}
```

**Complexity:** O(2ⁿ · n²) time, O(2ⁿ · n) space. Feasible for n ≤ 20.

---

## Walkthrough

4 vertices, adjacency matrix:
```
    0   1   2   3
0 [ 0   10  15  20]
1 [ 10  0   35  25]
2 [ 15  35  0   30]
3 [ 20  25  30  0 ]
```

Start at 0. Build up subsets:
- `dp[0001][0]` = 0
- `dp[0011][1]` = 10, `dp[0101][2]` = 15, `dp[1001][3]` = 20
- `dp[0111][2]` = min(dp[0011][1]+35, dp[0101][0]+15) = 45
- Continue until `dp[1111][*]` → minimum tour cost.

---

## Variations

| Variant | Approach |
|---|---|
| Decision problem (exists?) | Same DP, check if any dp[full][v] < ∞ |
| Path (not cycle) | Same DP, no return edge needed |
| Count paths | Use `long long`, sum instead of min |
| Dirac's theorem | If every vertex has degree ≥ n/2 in an undirected graph, Hamiltonian cycle exists |
| Ore's theorem | If deg(u)+deg(v) ≥ n for all non-adjacent pairs, cycle exists |

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Using n=25 with O(2ⁿ · n²) | Too slow; cap at n ≤ 20 or use bitset optimization |
| Confusing Hamiltonian with Eulerian | Hamiltonian = visit each **vertex** once; Eulerian = traverse each **edge** once |
| Not using symmetry to halve search | For cycles, fix the starting vertex |

---

## Practice Problems

| # | Problem | Hint |
|---|---|
| 1 | Traveling Salesman (classic) | Held-Karp DP over subsets |
| 2 | Hamiltonian Path Exists? (LeetCode 980) | DP with bitmask on grid |
| 3 | Bitmask DP — permutation counting | Count paths covering all vertices |
| 4 | Shortest Hamiltonian Path (AtCoder) | Remove cycle constraint, use same DP |
| 5 | Grid Hamiltonian Path | Backtracking with pruning; check Dirac/Ore conditions first |
| 6 | Hamiltonian Cycle in Tournament Graph | Every tournament has a Hamiltonian path (Rédei's theorem) |

---

## See Also

- [Chapter 09: Backtracking](ch09-backtracking.md)
- [Chapter 30: DP Fundamentals](ch30-dp-fundamentals.md)
- [Chapter 96: NP-Completeness & Approximation](ch96-np-approximation.md)
- [Chapter 149: Exponential Algorithms](ch149-exponential-algorithms.md)
