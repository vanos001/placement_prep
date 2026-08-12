# Chapter 118: Bitset DP and Memory Optimization

## Prerequisites
- Bit manipulation (Chapter 15)
- Dynamic programming basics (Chapter 40–45)
- Space complexity analysis
- Binary number representation

## Interview Frequency: ★★

Bitset optimization is a powerful technique that leverages CPU-level parallelism to speed up certain DP problems by a factor of 64. It appears in competitive programming and occasionally in interviews at **Google**, **Meta**, and **Jane Street** for its clever use of hardware-level parallelism.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Bitset subset sum | ★★ | Medium | Classic application |
| Rolling array | ★★★ | Medium | Common space optimization |
| Hirschberg's algorithm | ★ | Hard | Linear space with reconstruction |
| Bitmask DP | ★★★ | Medium | State compression |
| Profile DP | ★ | Hard | Grid-based state compression |

---

## 118.1 What Is Bitset Optimization?

### Definition

**Bitset optimization** replaces a boolean DP array with a bitset (packed array of bits), enabling bitwise operations to process 64 (or more) states simultaneously in a single CPU cycle.

### Motivation

Consider the classic subset sum problem: given n items with weights, can we achieve a total weight of exactly S?

**Standard DP**: O(nS) time, O(S) space
**Bitset DP**: O(nS/64) time, O(S/64) space

The speedup comes from the fact that a `std::bitset<100000>` stores 100000 bits in 1563 64-bit words. A single bitwise OR operation processes 64 boolean states at once.

### Intuition

Think of a bitset as a set of integers. If `dp` represents all achievable sums, then adding item with weight `w` means:

```
new_dp = dp | (dp << w)
```

This says: "the new set of achievable sums is the old set, plus the old set shifted by w." The `|` merges both possibilities, and `<<` is the shift — it's like adding w to every element in the set.

### When to Use Bitset DP

Bitset DP works when:
1. DP states are **boolean** (reachable or not)
2. Transitions involve **union/shift** operations
3. The state space is **dense** (many states are true)
4. You need a **constant factor** speedup (64× on 64-bit systems)

---

## 118.2 Subset Sum with Bitset

### Problem

Given n positive integers and a target sum S, determine which sums from 0 to S are achievable using a subset of the given numbers.

### Standard Approach (O(nS))

```cpp
#include <iostream>
#include <vector>

std::vector<bool> subsetSumStandard(const std::vector<int>& arr, int S) {
    std::vector<bool> dp(S + 1, false);
    dp[0] = true;
    for (int x : arr)
        for (int s = S; s >= x; s--)
            if (dp[s - x]) dp[s] = true;
    return dp;
}
```

### Bitset Approach (O(nS/64))

```cpp
#include <iostream>
#include <vector>
#include <bitset>

const int MAXS = 100001;

std::bitset<MAXS> subsetSumBitset(const std::vector<int>& arr) {
    std::bitset<MAXS> dp;
    dp[0] = 1;  // sum 0 is achievable
    for (int x : arr)
        dp |= dp << x;  // add x to all achievable sums
    return dp;
}

int main() {
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6};
    
    auto dp = subsetSumBitset(arr);
    
    std::cout << "Achievable sums: ";
    for (int s = 0; s <= 31; s++)
        if (dp[s]) std::cout << s << " ";
    std::cout << "\n";
    
    std::cout << "Can make sum 10: " << dp[10] << "\n";
    std::cout << "Can make sum 13: " << dp[13] << "\n";
    std::cout << "Can make sum 31: " << dp[31] << "\n";
    std::cout << "Can make sum 100: " << dp[100] << "\n";
    
    return 0;
}
```

### Dry Run

arr = {3, 1, 4}

Step 0: dp = {0} → bitset: ...00000001 (only bit 0 set)

Step 1: x = 3
- dp << 3: ...00001000 (shift right by 3: bit 3 set)
- dp |= dp << 3: ...00001001 (bits 0 and 3 set)
- Achievable sums: {0, 3}

Step 2: x = 1
- dp << 1: ...00010010 (bits 1 and 4 set)
- dp |= dp << 1: ...00011011 (bits 0, 1, 3, 4 set)
- Achievable sums: {0, 1, 3, 4}

Step 3: x = 4
- dp << 4: ...110110000 (bits 4, 5, 7, 8 set)
- dp |= dp << 4: ...110111011 (bits 0, 1, 3, 4, 5, 7, 8 set)
- Achievable sums: {0, 1, 3, 4, 5, 7, 8}

### Complexity Analysis

| Approach | Time | Space |
|---|---|---|
| Standard DP | O(nS) | O(S) |
| Bitset DP | O(nS/64) | O(S/64) |
| Speedup | 64× | 64× |

---

## 118.3 Counting Subset Sum

### Problem

Count the number of subsets that sum to exactly S.

### Why Bitset Doesn't Work Here

Bitset only tracks boolean reachability (yes/no). For counting, we need to store the *number* of ways, which requires integer arithmetic, not bitwise operations.

### Standard DP Solution

```cpp
#include <iostream>
#include <vector>

long long countSubsetSum(const std::vector<int>& arr, int S) {
    std::vector<long long> dp(S + 1, 0);
    dp[0] = 1;  // one way to make sum 0: empty set
    
    for (int x : arr)
        for (int s = S; s >= x; s--)
            dp[s] += dp[s - x];
    
    return dp[S];
}

int main() {
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6};
    
    for (int target : {10, 13, 20, 31}) {
        std::cout << "Ways to make sum " << target << ": "
                  << countSubsetSum(arr, target) << "\n";
    }
    
    return 0;
}
```

### Complexity

- Time: O(nS)
- Space: O(S)
- Note: Can be optimized with rolling array (Section 118.5)

---

## 118.4 Advanced Bitset Applications

### Application 1: Graph Reachability (Transitive Closure)

Compute which nodes are reachable from each node in a directed graph.

```cpp
#include <iostream>
#include <vector>
#include <bitset>

const int MAXN = 1000;

void transitiveClosure(std::vector<std::bitset<MAXN>>& reach, int n) {
    // Floyd-Warshall with bitsets
    for (int k = 0; k < n; k++)
        for (int i = 0; i < n; i++)
            if (reach[i][k])
                reach[i] |= reach[k];
}

int main() {
    int n = 5;
    std::vector<std::bitset<MAXN>> reach(n);
    
    // Graph: 0->1, 0->2, 1->3, 2->3, 3->4
    reach[0][1] = reach[0][2] = 1;
    reach[1][3] = 1;
    reach[2][3] = 1;
    reach[3][4] = 1;
    
    // Each node reaches itself
    for (int i = 0; i < n; i++) reach[i][i] = 1;
    
    transitiveClosure(reach, n);
    
    for (int i = 0; i < n; i++) {
        std::cout << "Node " << i << " reaches: ";
        for (int j = 0; j < n; j++)
            if (reach[i][j]) std::cout << j << " ";
        std::cout << "\n";
    }
    
    return 0;
}
```

### Why This Is Faster

Standard Floyd-Warshall: O(n³) with inner loop doing O(1) per pair.
Bitset Floyd-Warshall: O(n³/64) because `reach[i] |= reach[k]` processes n bits in O(n/64) word operations.

### Application 2: Bipartite Matching (Hopcroft-Karp Bitset)

Speed up BFS/DFS in Hopcroft-Karp by using bitsets for adjacency.

```cpp
#include <iostream>
#include <vector>
#include <bitset>

const int MAXN = 1000;

// Bitset-optimized bipartite matching
int bpm(const std::vector<std::bitset<MAXN>>& adj,
        int n, int m,
        std::vector<int>& matchR) {
    std::vector<int> matchL(n, -1);
    matchR.assign(m, -1);
    int result = 0;
    
    for (int u = 0; u < n; u++) {
        std::vector<bool> visited(m, false);
        
        // DFS to find augmenting path
        std::function<bool(int)> dfs = [&](int u) -> bool {
            for (int v = 0; v < m; v++) {
                if (adj[u][v] && !visited[v]) {
                    visited[v] = true;
                    if (matchR[v] < 0 || dfs(matchR[v])) {
                        matchL[u] = v;
                        matchR[v] = u;
                        return true;
                    }
                }
            }
            return false;
        };
        
        if (dfs(u)) result++;
    }
    return result;
}

int main() {
    int n = 4, m = 4;
    std::vector<std::bitset<MAXN>> adj(n);
    
    // Bipartite graph edges
    adj[0][0] = adj[0][1] = 1;
    adj[1][0] = 1;
    adj[2][1] = adj[2][2] = 1;
    adj[3][2] = adj[3][3] = 1;
    
    std::vector<int> matchR;
    int maxMatch = bpm(adj, n, m, matchR);
    
    std::cout << "Maximum matching: " << maxMatch << "\n";
    for (int v = 0; v < m; v++)
        if (matchR[v] != -1)
            std::cout << "  L" << matchR[v] << " - R" << v << "\n";
    
    return 0;
}
```

### Application 3: Number of Distinct Subsequences

Count distinct subsequences of a string using bitset to track character positions.

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <bitset>

// Count distinct subsequences (not substrings)
long long distinctSubsequences(const std::string& s) {
    int n = s.size();
    std::vector<long long> dp(n + 1, 0);
    dp[0] = 1;  // empty subsequence
    
    std::vector<int> last(256, -1);
    
    for (int i = 0; i < n; i++) {
        dp[i + 1] = 2 * dp[i];
        if (last[s[i]] != -1)
            dp[i + 1] -= dp[last[s[i]]];
        last[s[i]] = i;
    }
    
    return dp[n] - 1;  // exclude empty subsequence
}

int main() {
    std::vector<std::string> tests = {"abc", "aaa", "abab", "abcdef"};
    for (auto& s : tests)
        std::cout << "\"" << s << "\": " << distinctSubsequences(s)
                  << " distinct subsequences\n";
    return 0;
}
```

---

## 118.5 Rolling Array (Space Optimization)

### Problem

Many DP problems use a 2D table dp[n][m], but only the previous row is needed to compute the current row. The **rolling array** technique reduces space from O(n×m) to O(m).

### Motivation

- 0/1 Knapsack: dp[i][w] depends on dp[i-1][w] and dp[i-1][w-wᵢ]
- LCS: dp[i][j] depends on dp[i-1][j-1], dp[i-1][j], dp[i][j-1]
- Edit Distance: similar dependencies

### Key Insight

If dp[i] only depends on dp[i-1], we only need two rows. If we process in the right order, we can use a single row.

For 0/1 Knapsack (maximization, each item used at most once):
- Process weights in **reverse** order: dp[w] = max(dp[w], dp[w-wᵢ] + vᵢ)
- This ensures dp[w-wᵢ] still holds the value from the previous row

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// 0/1 Knapsack with O(W) space
int knapsack01(const std::vector<int>& weights, const std::vector<int>& values, int W) {
    int n = weights.size();
    std::vector<int> dp(W + 1, 0);
    
    for (int i = 0; i < n; i++)
        for (int w = W; w >= weights[i]; w--)  // reverse order!
            dp[w] = std::max(dp[w], dp[w - weights[i]] + values[i]);
    
    return dp[W];
}

// Unbounded knapsack (each item can be used multiple times)
int knapsackUnbounded(const std::vector<int>& weights, const std::vector<int>& values, int W) {
    int n = weights.size();
    std::vector<int> dp(W + 1, 0);
    
    for (int i = 0; i < n; i++)
        for (int w = weights[i]; w <= W; w++)  // forward order!
            dp[w] = std::max(dp[w], dp[w - weights[i]] + values[i]);
    
    return dp[W];
}

int main() {
    std::vector<int> w = {2, 3, 4, 5};
    std::vector<int> v = {3, 4, 5, 6};
    int W = 8;
    
    std::cout << "0/1 Knapsack (O(W) space): " << knapsack01(w, v, W) << "\n";
    std::cout << "Unbounded Knapsack: " << knapsackUnbounded(w, v, W) << "\n";
    
    // Demonstrate the difference
    std::cout << "\n--- 0/1 Knapsack Detail ---\n";
    std::vector<int> dp(W + 1, 0);
    for (int i = 0; i < (int)w.size(); i++) {
        std::cout << "After item " << i << " (w=" << w[i] << ", v=" << v[i] << "): ";
        for (int j = W; j >= w[i]; j--)
            dp[j] = std::max(dp[j], dp[j - w[i]] + v[i]);
        for (int j = 0; j <= W; j++) std::cout << dp[j] << " ";
        std::cout << "\n";
    }
    
    return 0;
}
```

### Dry Run: 0/1 Knapsack

Items: (w=2, v=3), (w=3, v=4), (w=4, v=5), (w=5, v=6). Capacity W=8.

Initial: dp = [0, 0, 0, 0, 0, 0, 0, 0, 0]

After item 0 (w=2, v=3):
- Process w=8→2: dp[8]=max(0, dp[6]+3)=3, dp[6]=max(0, dp[4]+3)=3, dp[4]=max(0, dp[2]+3)=3, dp[2]=max(0, dp[0]+3)=3
- dp = [0, 0, 3, 0, 3, 0, 3, 0, 3]

After item 1 (w=3, v=4):
- dp[8]=max(3, dp[5]+4)=7, dp[7]=max(0, dp[4]+4)=7, dp[6]=max(3, dp[3]+4)=7, dp[5]=max(0, dp[2]+4)=7, dp[3]=max(0, dp[0]+4)=4
- dp = [0, 0, 3, 4, 3, 7, 7, 7, 7]

After item 2 (w=4, v=5):
- dp[8]=max(7, dp[4]+5)=8, dp[7]=max(7, dp[3]+5)=9, dp[6]=max(7, dp[2]+5)=8, dp[4]=max(3, dp[0]+5)=5
- dp = [0, 0, 3, 4, 5, 7, 8, 9, 8]

After item 3 (w=5, v=6):
- dp[8]=max(8, dp[3]+6)=10, dp[7]=max(9, dp[2]+6)=9, dp[6]=max(8, dp[1]+6)=8, dp[5]=max(7, dp[0]+6)=7
- dp = [0, 0, 3, 4, 5, 7, 8, 9, 10]

Result: dp[8] = 10 (items 0 and 2: weight 2+4=6, value 3+5=8? No: items 1 and 3: weight 3+5=8, value 4+6=10) ✓

---

## 118.6 Hirschberg's Algorithm

### Problem

Compute the LCS (Longest Common Subsequence) of two strings in O(n) space while still recovering the full LCS (not just its length).

### Key Idea

Combine divide-and-conquer with the space-optimized LCS DP. The standard LCS DP gives O(nm) time, O(m) space for the *length*. Hirschberg adds a clever split:

1. Split string A into two halves: A[1..m/2] and A[m/2+1..m]
2. Compute LCS forward on A[1..m/2] and B
3. Compute LCS backward on A[m/2+1..m] and B
4. Find the split point in B that maximizes the sum of LCS lengths
5. Recurse on both halves

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

// Compute one row of LCS DP
std::vector<int> lcsRow(const std::string& a, const std::string& b,
                         std::vector<int>& prev) {
    int m = b.size();
    std::vector<int> curr(m + 1, 0);
    for (int j = 0; j < (int)a.size(); j++) {
        for (int k = 1; k <= m; k++) {
            if (a[j] == b[k-1]) curr[k] = prev[k-1] + 1;
            else curr[k] = std::max(prev[k], curr[k-1]);
        }
        prev = curr;
    }
    return curr;
}

// Hirschberg's algorithm: O(nm) time, O(m) space
std::string hirschberg(const std::string& a, const std::string& b) {
    int n = a.size(), m = b.size();
    
    if (n == 0) return "";
    if (m == 0) return "";
    if (n == 1) {
        if (b.find(a[0]) != std::string::npos) return a;
        return "";
    }
    
    int mid = n / 2;
    
    // Forward: LCS of a[0..mid-1] and b
    std::vector<int> dp1(m + 1, 0);
    std::string a1 = a.substr(0, mid);
    lcsRow(a1, b, dp1);
    
    // Backward: LCS of a[mid..n-1] reversed and b reversed
    std::vector<int> dp2(m + 1, 0);
    std::string a2 = a.substr(mid);
    std::string a2rev(a2.rbegin(), a2.rend());
    std::string brev(b.rbegin(), b.rend());
    lcsRow(a2rev, brev, dp2);
    
    // Find optimal split point in b
    int bestK = 0, bestSum = 0;
    for (int k = 0; k <= m; k++) {
        int sum = dp1[k] + dp2[m - k];
        if (sum > bestSum) { bestSum = sum; bestK = k; }
    }
    
    // Recurse on both halves
    std::string left = hirschberg(a.substr(0, mid), b.substr(0, bestK));
    std::string right = hirschberg(a.substr(mid), b.substr(bestK));
    
    return left + right;
}

int main() {
    std::string a = "ABCBDAB";
    std::string b = "BDCABA";
    
    std::string lcs = hirschberg(a, b);
    std::cout << "LCS of \"" << a << "\" and \"" << b << "\": \"" << lcs << "\"\n";
    std::cout << "Length: " << lcs.size() << "\n";
    
    // Standard LCS length for verification
    int n = a.size(), m = b.size();
    std::vector<std::vector<int>> dp(n+1, std::vector<int>(m+1, 0));
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= m; j++) {
            if (a[i-1] == b[j-1]) dp[i][j] = dp[i-1][j-1] + 1;
            else dp[i][j] = std::max(dp[i-1][j], dp[i][j-1]);
        }
    std::cout << "Standard LCS length: " << dp[n][m] << "\n";
    
    return 0;
}
```

### Complexity

| Method | Time | Space | Reconstructs LCS? |
|---|---|---|---|
| Standard DP | O(nm) | O(nm) | Yes (backtracking) |
| Rolling array | O(nm) | O(m) | No (only length) |
| Hirschberg | O(nm) | O(m) | Yes! |

---

## 118.7 Profile DP (State Compression on Grids)

### Problem

Place dominoes on an n×m grid to cover all cells. Count the number of valid tilings.

### Key Idea

Process the grid column by column. The "profile" is a bitmask representing which cells in the current column are already covered by dominoes extending from the previous column.

```cpp
#include <iostream>
#include <vector>
#include <cstring>

const int MAXN = 12;
const int MAXM = 12;

// Count domino tilings of n x m grid
long long countTilings(int n, int m) {
    // dp[col][profile] = number of ways to tile columns 0..col-1
    // where profile is a bitmask of which cells in column col are already filled
    std::vector<std::vector<long long>> dp(m + 1, std::vector<long long>(1 << n, 0));
    dp[0][0] = 1;
    
    for (int col = 0; col < m; col++) {
        for (int mask = 0; mask < (1 << n); mask++) {
            if (dp[col][mask] == 0) continue;
            
            // Try to fill column 'col' given the profile 'mask'
            // mask bit = 1 means cell is already filled (from previous column)
            // We need to fill all cells with mask bit = 0
            
            std::function<void(int, int)> fill = [&](int row, int nextMask) {
                if (row == n) {
                    dp[col + 1][nextMask] += dp[col][mask];
                    return;
                }
                
                if (mask & (1 << row)) {
                    // Cell already filled, move to next row
                    fill(row + 1, nextMask);
                } else {
                    // Option 1: Place vertical domino (covers this cell and cell below)
                    if (row + 1 < n && !(mask & (1 << (row + 1))))
                        fill(row + 2, nextMask);
                    
                    // Option 2: Place horizontal domino (covers this cell, extends to next column)
                    fill(row + 1, nextMask | (1 << row));
                }
            };
            
            fill(0, 0);
        }
    }
    
    return dp[m][0];
}

int main() {
    for (int n = 1; n <= 8; n++)
        for (int m = 1; m <= 8; m++)
            if (n * m % 2 == 0)
                std::cout << n << "x" << m << ": "
                          << countTilings(n, m) << " tilings\n";
    
    return 0;
}
```

### Dry Run: 2×3 Grid

Grid: 2 rows, 3 columns. Profile = 2 bits (one per row).

Initial: dp[0][00] = 1

Column 0, mask=00:
- Row 0 not filled:
  - Vertical domino (rows 0,1): fill(2, 00) → dp[1][00] += 1
  - Horizontal domino: fill(1, 01) → row 1 not filled:
    - Horizontal domino: fill(2, 11) → dp[1][11] += 1

Column 1, mask=00:
- Same as column 0: dp[2][00] += 1, dp[2][11] += 1

Column 1, mask=11:
- Both rows filled: fill(0, 00) → fill(2, 00) → dp[2][00] += 1

Column 2, mask=00:
- dp[3][00] += dp[2][00] = 2+1 = 3

Column 2, mask=11:
- dp[3][00] += dp[2][11] = 1

Result: dp[3][00] = 3. Correct! (2×3 grid has exactly 3 domino tilings)

---

## 118.8 Bitmask DP for TSP

### Problem

Given n cities and distances between them, find the shortest tour visiting all cities exactly once.

### State

dp[mask][i] = minimum cost to visit all cities in bitmask `mask`, currently at city `i`.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

int tspBitmask(const std::vector<std::vector<int>>& dist) {
    int n = dist.size();
    int fullMask = (1 << n) - 1;
    
    // dp[mask][i] = min cost to visit cities in mask, ending at i
    std::vector<std::vector<int>> dp(1 << n, std::vector<int>(n, INT_MAX));
    dp[1][0] = 0;  // start at city 0
    
    for (int mask = 1; mask <= fullMask; mask++) {
        for (int u = 0; u < n; u++) {
            if (!(mask & (1 << u))) continue;  // u not in mask
            if (dp[mask][u] == INT_MAX) continue;
            
            for (int v = 0; v < n; v++) {
                if (mask & (1 << v)) continue;  // v already visited
                int newMask = mask | (1 << v);
                dp[newMask][v] = std::min(dp[newMask][v],
                                          dp[mask][u] + dist[u][v]);
            }
        }
    }
    
    // Find minimum cost to visit all cities and return to start
    int ans = INT_MAX;
    for (int u = 0; u < n; u++)
        if (dp[fullMask][u] != INT_MAX)
            ans = std::min(ans, dp[fullMask][u] + dist[u][0]);
    
    return ans;
}

int main() {
    std::vector<std::vector<int>> dist = {
        {0, 10, 15, 20},
        {10, 0, 35, 25},
        {15, 35, 0, 30},
        {20, 25, 30, 0}
    };
    
    std::cout << "Shortest TSP tour: " << tspBitmask(dist) << "\n";
    // Expected: 80 (0→1→3→2→0 or 0→2→3→1→0)
    
    return 0;
}
```

### Dry Run

4 cities. fullMask = 1111₂ = 15.

dp[0001][0] = 0 (start at city 0)

mask=0001, u=0:
- v=1: dp[0011][1] = min(∞, 0+10) = 10
- v=2: dp[0101][2] = min(∞, 0+15) = 15
- v=3: dp[1001][3] = min(∞, 0+20) = 20

mask=0011, u=0: dp=∞, skip
mask=0011, u=1: dp=10
- v=2: dp[0111][2] = min(∞, 10+35) = 45
- v=3: dp[1011][3] = min(∞, 10+25) = 35

mask=0101, u=0: dp=∞, skip
mask=0101, u=2: dp=15
- v=1: dp[0111][1] = min(∞, 15+35) = 50
- v=3: dp[1101][3] = min(∞, 15+30) = 45

... (continuing)

Final: dp[1111][1] = 10+35+30+25=... let me trace fully:
- 0→1→3→2→0: dp[0001][0]=0, dp[0011][1]=10, dp[1011][3]=35, dp[1111][2]=35+30=65, total=65+15=80
- 0→2→3→1→0: dp[0001][0]=0, dp[0101][2]=15, dp[1101][3]=45, dp[1111][1]=45+25=70, total=70+10=80

Answer: 80 ✓

### Complexity

| Approach | Time | Space |
|---|---|---|
| Brute force | O(n!) | O(n) |
| Bitmask DP | O(n²·2ⁿ) | O(n·2ⁿ) |
| Savings | Huge for n=20 | — |

---

## Summary

| Technique | Speedup | Best For | Key Insight |
|---|---|---|---|
| Bitset DP | 64× | Boolean state transitions | Parallel bitwise operations |
| Rolling array | Same time, O(m) space | Row-dependent DP | Overwrite previous row |
| Hirschberg | Same time, O(m) space | LCS reconstruction | Divide and conquer |
| Profile DP | — | Grid tilings | Column-by-column bitmask |
| Bitmask DP | — | Small n (≤20) TSP/SAT | 2ⁿ state space |

---

## Exercises

1. **Bitset Subset Sum with Negatives**: Extend the bitset subset sum to handle negative numbers. Hint: offset all indices by the maximum possible negative sum.

2. **Counting with Bitset**: Can you count the number of subsets that sum to S using bitsets? Hint: use multiple bitsets or a different encoding.

3. **Rolling Array LCS**: Implement LCS using O(min(n,m)) space while still recovering the LCS string using Hirschberg's algorithm.

4. **Profile DP: Chessboard**: Count the number of ways to place non-attacking rooks on an n×n chessboard using profile DP.

5. **Bitmask DP Optimization**: For TSP bitmask DP, implement the Held-Karp algorithm and compare its performance against brute force for n=15, 18, 20.

6. **Bitset Graph Algorithms**: Implement BFS on a graph using bitset operations. How much faster is it than standard BFS?

---

## Interview Questions

1. **Q**: When would you use bitset optimization in a DP problem?
   **A**: When DP states are boolean (reachable/not), transitions are union/shift operations, and the state space is large enough that the 64× speedup matters. Classic example: subset sum with S up to 10⁶.

2. **Q**: What's the difference between rolling array and Hirschberg's algorithm?
   **A**: Both reduce space to O(m), but rolling array can only recover the *length* of the optimal solution. Hirschberg can recover the *full solution* (e.g., the actual LCS string) using divide-and-conquer, at the cost of 2× time.

3. **Q**: How does the rolling array direction (forward vs backward) affect correctness?
   **A**: For 0/1 knapsack (each item once), process backward so dp[w-wᵢ] hasn't been updated yet (still from previous row). For unbounded knapsack (items reusable), process forward so dp[w-wᵢ] includes the current item.

4. **Q**: What's the maximum problem size for bitmask DP on TSP?
   **A**: With n≤20, 2²⁰·20² ≈ 4×10⁸ operations, which runs in a few seconds. n=25 would need 2²⁵·25² ≈ 2×10¹⁰, too slow. Practical limit is n≈20-22.

5. **Q**: Can bitset optimization be applied to non-boolean DP?
   **A**: Not directly for counting or optimization DP. However, you can sometimes decompose non-boolean problems into boolean subproblems (e.g., binary search on the answer + boolean feasibility check with bitset).

---

## Cross-References

- **Chapter 15**: Bit Manipulation — foundation for bitset operations
- **Chapter 40**: Dynamic Programming Basics — DP fundamentals
- **Chapter 43**: Knapsack Problems — classic application of rolling array
- **Chapter 44**: String DP — LCS, edit distance
- **Chapter 45**: Interval DP — another DP category
- **Chapter 70**: Graph Algorithms — bitset BFS/DFS
- **Chapter 117**: State Space Search — bitmask DP for combinatorial problems
