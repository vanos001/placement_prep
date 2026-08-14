# Advanced Dynamic Programming Paradigms

Beyond standard DP patterns (knapsack, LIS, grid), several paradigms appear in hard interview problems and competitive programming. This chapter covers the most important ones with a focus on interview applicability.

---

## Bitmask DP / State Compression DP

### Core Idea

When the state space is small enough (typically n <= 20), represent subsets as bitmasks where bit `i` indicates whether element `i` is included. This converts set-based states into integer indices.

### Classic Example: Traveling Salesman Problem

Find the minimum cost to visit all cities exactly once and return to the start.

```cpp
// dp[mask][i] = min cost to reach city i, having visited cities in mask
int tsp(const vector<vector<int>>& dist) {
    int n = dist.size();
    const int INF = 1e9;
    vector<vector<int>> dp(1 << n, vector<int>(n, INF));
    dp[1][0] = 0; // start at city 0, only city 0 visited

    for (int mask = 1; mask < (1 << n); mask++) {
        for (int u = 0; u < n; u++) {
            if (!(mask & (1 << u)) || dp[mask][u] == INF) continue;
            for (int v = 0; v < n; v++) {
                if (mask & (1 << v)) continue; // already visited
                int nextMask = mask | (1 << v);
                dp[nextMask][v] = min(dp[nextMask][v], dp[mask][u] + dist[u][v]);
            }
        }
    }
    // Return to city 0 from any ending city
    int ans = INF;
    int fullMask = (1 << n) - 1;
    for (int i = 1; i < n; i++)
        ans = min(ans, dp[fullMask][i] + dist[i][0]);
    return ans;
}
```

**Complexity:** O(2^n * n^2) time, O(2^n * n) space. Practical for n <= 20. Use `__builtin_popcount` to iterate over subset sizes efficiently.

**Common variants:** Minimum Hamiltonian path (no return), maximum weight matching in general graphs, minimum vertex cover on small graphs.

---

## Digit DP

### Core Idea

Count numbers in a range [L, R] satisfying a digit-based property. Process digits from most significant to least significant, tracking tight constraints and accumulated state.

```python
def count_numbers(L, R):
    """Count numbers in [L, R] where the sum of digits is divisible by 9."""
    def solve(num):
        s = str(num)
        n = len(s)
        from functools import lru_cache

        @lru_cache(None)
        def dp(pos, tight, sum_mod):
            if pos == n:
                return 1 if sum_mod % 9 == 0 else 0
            limit = int(s[pos]) if tight else 9
            total = 0
            for d in range(limit + 1):
                total += dp(pos + 1, tight and d == limit, (sum_mod + d) % 9)
            return total

        return dp(0, True, 0)

    return solve(R) - solve(L - 1)
```

**Complexity:** O(number of digits * states * 10). The key insight: `[L, R]` = `f(R) - f(L-1)`. State includes position, tight flag, and problem-specific tracking (digit sum, leading zeros, etc.).

---

## Interval DP

### Core Idea

DP over intervals [i, j]. Subproblems merge by splitting intervals. The order of processing matters: iterate by increasing interval length.

### Classic Example: Matrix Chain Multiplication

```cpp
int matrixChain(const vector<int>& dims) {
    int n = dims.size() - 1; // n matrices
    vector<vector<int>> dp(n, vector<int>(n, 0));
    // dp[i][j] = min cost to multiply matrices i..j

    for (int len = 2; len <= n; len++) {        // interval length
        for (int i = 0; i <= n - len; i++) {   // start
            int j = i + len - 1;                 // end
            dp[i][j] = INT_MAX;
            for (int k = i; k < j; k++) {        // split point
                dp[i][j] = min(dp[i][j],
                    dp[i][k] + dp[k+1][j] + dims[i] * dims[k+1] * dims[j+1]);
            }
        }
    }
    return dp[0][n - 1];
}
```

**Complexity:** O(n^3) time, O(n^2) space. Knuth optimization reduces to O(n^2) when the optimal split point is monotonic.

**Other interval DP problems:** Optimal BST, burst balloons, stone merging, palindrome partitioning.

---

## Tree DP

### Core Idea

DP on trees processes subtrees bottom-up (post-order traversal). State typically includes information from the current node's children.

### Example: Maximum Independent Set

```python
def max_independent_set(n, adj):
    """Maximum set of vertices with no two adjacent."""
    def dfs(u, parent):
        include = 1  # include u
        exclude = 0  # exclude u
        for v in adj[u]:
            if v == parent:
                continue
            child_inc, child_exc = dfs(v, u)
            include += child_exc   # can't include children
            exclude += max(child_inc, child_exc)  # take best from each child
        return (include, exclude)

    inc, exc = dfs(0, -1)
    return max(inc, exc)
```

### Example: Tree Diameter

```python
def tree_diameter(n, adj):
    diameter = 0
    def dfs(u, parent):
        nonlocal diameter
        max1 = max2 = 0  # two longest downward paths
        for v in adj[u]:
            if v == parent:
                continue
            h = dfs(v, u) + 1
            if h > max1:
                max2, max1 = max1, h
            elif h > max2:
                max2 = h
        diameter = max(diameter, max1 + max2)
        return max1
    dfs(0, -1)
    return diameter
```

**Complexity:** O(n) time for both. Tree DP is O(n) because each node is processed once with its children's results.

**Common patterns:** Rerooting DP (compute DP for all roots), DP on trees with diameter constraints, subtree counting with combinatorics.

---

## DP Optimizations — When to Use Which

| Optimization | Condition | Complexity Reduction | Example |
|---|---|---|---|
| Monotonic Queue | `dp[i] = min/max(dp[j])` with j in a sliding window | O(n) from O(n * window) | Sliding window maximum DP |
| Convex Hull Trick | `dp[i] = min(dp[j] + a[i]*b[j])` with monotone slopes | O(n log n) from O(n^2) | Divide and conquer with linear cost |
| Divide & Conquer Opt | Optimal split point is monotone | O(n log n) from O(n^2) | Partition DP |
| Knuth Opt | Quadrangle inequality + monotonicity | O(n^2) from O(n^3) | Matrix chain, optimal BST |

**Decision guide:**
- If transitions involve a **range** of previous states → monotonic queue
- If the cost is **linear in a query value** → convex hull trick
- If the problem has **optimal substructure with monotone split** → divide & conquer or Knuth

---

## Interview Questions

1. **Solve the TSP for n=15 cities.** Implement bitmask DP. What is the time complexity? Can you optimize space to O(2^n)?

2. **Count numbers between 1 and 10^18 where no two adjacent digits are the same.** Use digit DP. What state do you need?

3. **Given n matrices with dimensions, find the minimum multiplication cost.** Implement interval DP. How would you reconstruct the optimal parenthesization?

4. **Find the maximum sum of non-adjacent nodes in a binary tree.** Implement tree DP. What if the tree is not binary?

5. **A company has n projects and n teams. Each team can do one project with cost c[i][j]. Minimize total cost such that every project is assigned.** This is an assignment problem — how does it relate to bitmask DP?

6. **When would you use divide & conquer DP optimization vs. Knuth optimization?** Explain the conditions and give an example of each.

7. **Count numbers in [L, R] that are palindromic in decimal.** Design the digit DP approach.

8. **Given a tree, find the minimum number of vertices to remove so that no path has more than k vertices.** How would you model this with tree DP?

9. **Explain how to reconstruct the TSP tour from the DP table.** What additional information do you need to track?

10. **Compare interval DP with segment tree approaches.** When is each more appropriate? Give an example where interval DP is the natural choice.