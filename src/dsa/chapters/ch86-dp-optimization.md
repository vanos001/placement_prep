# Chapter 86: DP Optimization Techniques

## Prerequisites

- Dynamic programming fundamentals
- Monotonicity and convexity concepts

## Interview Frequency: ★★★

DP optimizations reduce O(n²) transitions to O(n log n) or O(n). **Google** and competitive programming interviews test these for hard DP problems.

| Technique | Frequency | Difficulty | Original → Optimized |
|---|---|---|---|
| Convex Hull Trick | ★★★ | Hard | O(n²) → O(n log n) |
| Li Chao Tree | ★★ | Hard | O(n²) → O(n log n) |
| Knuth Optimization | ★★ | Medium | O(n³) → O(n²) |
| Divide & Conquer DP | ★★★ | Medium | O(n²) → O(n log n) |

---

## 86.1 Convex Hull Trick

Optimize DP of form: `dp[i] = min(dp[j] + b[j] * a[i])` for j < i.

Each transition is a line `y = b[j] * x + dp[j]`. Query at `x = a[i]`.

```cpp
#include <iostream>
#include <vector>
#include <deque>
#include <climits>

struct Line {
    long long m, b; // y = mx + b
    long long eval(long long x) const { return m * x + b; }
    
    // Check if intersection of (l2, l3) is left of intersection of (l1, l2)
    static bool bad(const Line& l1, const Line& l2, const Line& l3) {
        return (__int128)(l3.b - l1.b) * (l1.m - l2.m) <=
               (__int128)(l2.b - l1.b) * (l1.m - l3.m);
    }
};

class ConvexHullTrick {
    std::deque<Line> hull;
    
public:
    void addLine(long long m, long long b) {
        Line newLine = {m, b};
        while (hull.size() >= 2 &&
               Line::bad(hull[hull.size()-2], hull[hull.size()-1], newLine))
            hull.pop_back();
        hull.push_back(newLine);
    }
    
    long long query(long long x) {
        while (hull.size() >= 2 && hull[1].eval(x) <= hull[0].eval(x))
            hull.pop_front();
        return hull[0].eval(x);
    }
};

// Example: dp[i] = min(dp[j] + (sum[i] - sum[j])^2) for j < i
// Expands to: dp[j] + sum[j]^2 - 2*sum[i]*sum[j] + sum[i]^2
// Line: y = -2*sum[j] * x + (dp[j] + sum[j]^2), query at x = sum[i]

long long solve(const std::vector<int>& arr) {
    int n = arr.size();
    std::vector<long long> sum(n + 1, 0);
    for (int i = 0; i < n; i++) sum[i + 1] = sum[i] + arr[i];
    
    ConvexHullTrick cht;
    cht.addLine(0, 0); // dp[0] = 0
    
    std::vector<long long> dp(n + 1, LLONG_MAX);
    dp[0] = 0;
    
    for (int i = 1; i <= n; i++) {
        dp[i] = cht.query(sum[i]) + sum[i] * sum[i];
        cht.addLine(-2 * sum[i], dp[i] + sum[i] * sum[i]);
    }
    
    return dp[n];
}

int main() {
    std::vector<int> arr = {1, 3, 2, 4, 1, 5};
    std::cout << "Min cost: " << solve(arr) << "\n";
    return 0;
}
```

---

## 86.2 Knuth Optimization

For DP of form: `dp[l][r] = min(dp[l][k] + dp[k][r] + cost(l, r))` where the optimal k is monotone.

If `opt[l][r-1] ≤ opt[l][r] ≤ opt[l+1][r]`, we can reduce O(n³) to O(n²).

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

// Matrix chain multiplication with Knuth optimization
long long matrixChain(const std::vector<int>& dims) {
    int n = dims.size() - 1;
    std::vector<std::vector<long long>> dp(n, std::vector<long long>(n, 0));
    std::vector<std::vector<int>> opt(n, std::vector<int>(n, 0));
    
    for (int i = 0; i < n; i++) opt[i][i] = i;
    
    for (int len = 2; len <= n; len++) {
        for (int l = 0; l + len - 1 < n; l++) {
            int r = l + len - 1;
            dp[l][r] = LLONG_MAX;
            
            int start = opt[l][r-1];
            int end = (l + 1 < n) ? opt[l+1][r] : r - 1;
            start = std::max(start, l);
            end = std::min(end, r - 1);
            
            for (int k = start; k <= end; k++) {
                long long cost = dp[l][k] + dp[k+1][r] + 
                                 (long long)dims[l] * dims[k+1] * dims[r+1];
                if (cost < dp[l][r]) {
                    dp[l][r] = cost;
                    opt[l][r] = k;
                }
            }
        }
    }
    
    return dp[0][n-1];
}

int main() {
    std::vector<int> dims = {10, 30, 5, 60};
    std::cout << "Min multiplications: " << matrixChain(dims) << "\n";
    return 0;
}
```

---

## 86.3 Divide and Conquer DP

For DP of form: `dp[i][j] = min(dp[i-1][k] + cost(k, j))` where optimal k is monotone.

```cpp
#include <iostream>
#include <vector>
#include <climits>

// Example: partition array into k groups to minimize cost
// cost(l, r) = sum of elements squared (or any convex function)

void solveLayer(const std::vector<long long>& sum, int layer, int lo, int hi,
                int optL, int optR, std::vector<std::vector<long long>>& dp) {
    if (lo > hi) return;
    
    int mid = (lo + hi) / 2;
    long long bestVal = LLONG_MAX;
    int bestK = -1;
    
    for (int k = optL; k <= std::min(mid - 1, optR); k++) {
        long long cost = sum[mid] - sum[k];
        long long val = dp[layer - 1][k] + cost * cost;
        if (val < bestVal) {
            bestVal = val;
            bestK = k;
        }
    }
    
    dp[layer][mid] = bestVal;
    
    solveLayer(sum, layer, lo, mid - 1, optL, bestK, dp);
    solveLayer(sum, layer, mid + 1, hi, bestK, optR, dp);
}

int main() {
    std::vector<int> arr = {1, 3, 2, 4, 1, 5, 2, 3};
    int n = arr.size();
    int k = 3;
    
    std::vector<long long> sum(n + 1, 0);
    for (int i = 0; i < n; i++) sum[i + 1] = sum[i] + arr[i];
    
    std::vector<std::vector<long long>> dp(k + 1, std::vector<long long>(n + 1, LLONG_MAX));
    dp[0][0] = 0;
    
    for (int layer = 1; layer <= k; layer++) {
        solveLayer(sum, layer, 1, n, 0, n - 1, dp);
    }
    
    std::cout << "Min cost to partition into " << k << " groups: " << dp[k][n] << "\n";
    
    return 0;
}
```

---

## Summary

| Technique | Condition | Time Improvement |
|---|---|---|
| Convex Hull Trick | Lines with monotone slopes/queries | O(n²) → O(n) |
| Li Chao Tree | Lines with arbitrary order | O(n²) → O(n log n) |
| Knuth Optimization | Quadrangle inequality | O(n³) → O(n²) |
| Divide & Conquer DP | Monotone opt points | O(n²) → O(n log n) |

---

## 86.4 Monge Arrays

An array A is Monge if for all i < j, k < l: A[i][k] + A[j][l] <= A[i][l] + A[j][k].

**Key property**: The row-minimum positions are non-decreasing. This enables the SMAWK algorithm to find all row minima in O(n+m).

```cpp
#include <iostream>
#include <vector>

bool isMonge(const std::vector<std::vector<int>>& A) {
    int n = A.size(), m = A[0].size();
    for (int i = 0; i < n; i++)
        for (int j = i + 1; j < n; j++)
            for (int k = 0; k < m; k++)
                for (int l = k + 1; l < m; l++)
                    if (A[i][k] + A[j][l] > A[i][l] + A[j][k])
                        return false;
    return true;
}

int main() {
    std::vector<std::vector<int>> A(5, std::vector<int>(5));
    for (int i = 0; i < 5; i++)
        for (int j = 0; j < 5; j++)
            A[i][j] = (i - j) * (i - j);
    std::cout << "Squared distance is Monge: " << isMonge(A) << "\n";
    return 0;
}
```
## 86.5 Memory Compression for DP

When DP table is too large, techniques to reduce memory:

| Technique | Memory | Applicable When |
|---|---|---|
| Rolling array | O(m) from O(nm) | Only need previous row |
| Hirschberg | O(m) from O(nm) | Need full reconstruction |
| Bitset | 64x reduction | Boolean states |
| In-place | O(1) extra | Can overwrite input |

---

### Monge Array Example

```cpp
#include <iostream>
#include <vector>

// Check if array is Monge: A[i][k] + A[j][l] <= A[i][l] + A[j][k]
// for all i < j, k < l
bool isMonge(const std::vector<std::vector<int>>& A) {
    int n = A.size(), m = A[0].size();
    for (int i = 0; i < n; i++)
        for (int j = i + 1; j < n; j++)
            for (int k = 0; k < m; k++)
                for (int l = k + 1; l < m; l++)
                    if (A[i][k] + A[j][l] > A[i][l] + A[j][k])
                        return false;
    return true;
}

// SMAWK algorithm finds row minima in O(n+m) for Monge arrays
// Key insight: Odd rows can be pruned without losing the minimum

int main() {
    // Distance matrix is Monge: A[i][j] = |i - j|
    std::vector<std::vector<int>> A(5, std::vector<int>(5));
    for (int i = 0; i < 5; i++)
        for (int j = 0; j < 5; j++)
            A[i][j] = std::abs(i - j);
    
    std::cout << "Distance matrix is Monge: " << isMonge(A) << "\\n";
    
    // Squared distance is also Monge
    for (int i = 0; i < 5; i++)
        for (int j = 0; j < 5; j++)
            A[i][j] = (i - j) * (i - j);
    
    std::cout << "Squared distance matrix is Monge: " << isMonge(A) << "\\n";
    
    return 0;
}
```

---

## See Also

- [Chapter 30: DP Fundamentals](ch30-dp-fundamentals.md) — Prerequisite: understand basic DP state design and transitions before applying optimizations.
- [Chapter 31: DP Patterns](ch31-dp-patterns.md) — Know the patterns first; optimizations apply to specific pattern families (e.g., Knuth for interval DP).
- [Chapter 85: Digit DP](ch85-digit-dp.md) — Digit DP has its own optimization techniques; matrix exponentiation can speed up linear digit DP transitions.
- [Chapter 2: Math Foundations](ch02-math-foundations.md) — Convex hull trick and Monge array properties require mathematical background.
- [Chapter 116: Alien Trick and Parametric Search](ch116-alien-trick-parametric.md) — Another powerful DP optimization technique for problems with monotonicity.
- [Chapter 117: Monotone Queue Optimization](ch117-monotone-queue-optimization.md) — Sliding window optimization for DP transitions with monotone properties.
