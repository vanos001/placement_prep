# Chapter 31: Dynamic Programming Patterns

Once you understand DP fundamentals, the next step is recognizing **patterns**. Interview problems rarely ask you to implement a textbook algorithm — they present novel problems that map to known patterns. This chapter covers the major DP patterns you'll encounter, each with template code, complexity analysis, and worked examples.

---

## 31.1 Linear DP

Linear DP problems involve a sequence (array, string) where `dp[i]` depends on a constant number of previous states.

### Template

```cpp
dp[0] = base_case;
for (int i = 1; i < n; ++i) {
    dp[i] = f(dp[i-1], dp[i-2], ...);
}
```

### Longest Increasing Subsequence (LIS)

**Problem**: Find the length of the longest strictly increasing subsequence.

#### O(n²) DP Approach

**State**: `dp[i]` = length of LIS ending at index `i`.

**Recurrence**: `dp[i] = max(dp[j] + 1)` for all `j < i` where `nums[j] < nums[i]`.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int lis_dp(const std::vector<int>& nums) {
    int n = nums.size();
    if (n == 0) return 0;
    
    std::vector<int> dp(n, 1);  // Every element is an LIS of length 1
    int max_len = 1;
    
    for (int i = 1; i < n; ++i) {
        for (int j = 0; j < i; ++j) {
            if (nums[j] < nums[i]) {
                dp[i] = std::max(dp[i], dp[j] + 1);
            }
        }
        max_len = std::max(max_len, dp[i]);
    }
    return max_len;
}

int main() {
    std::vector<int> nums = {10, 9, 2, 5, 3, 7, 101, 18};
    std::cout << "LIS length: " << lis_dp(nums) << "\n";  // Output: 4
    return 0;
}
```

#### O(n log n) with Binary Search

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int lis_binary_search(const std::vector<int>& nums) {
    // tails[i] = smallest tail element for increasing subsequence of length i+1
    std::vector<int> tails;
    
    for (int num : nums) {
        auto it = std::lower_bound(tails.begin(), tails.end(), num);
        if (it == tails.end()) {
            tails.push_back(num);
        } else {
            *it = num;
        }
    }
    return tails.size();
}

int main() {
    std::vector<int> nums = {10, 9, 2, 5, 3, 7, 101, 18};
    std::cout << "LIS length (O(n log n)): " << lis_binary_search(nums) << "\n";
    return 0;
}
```

**Key insight**: `tails` is always sorted. For each new element, either extend the longest subsequence or replace the first element that's ≥ current element.

### House Robber

**Problem**: Given an array of house values, maximize the sum of robbed houses where no two adjacent houses can be robbed.

**State**: `dp[i]` = max money robbing houses `0..i`.

**Recurrence**: `dp[i] = max(dp[i-1], dp[i-2] + nums[i])`

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int rob(const std::vector<int>& nums) {
    int n = nums.size();
    if (n == 0) return 0;
    if (n == 1) return nums[0];
    
    int prev2 = 0;          // dp[i-2]
    int prev1 = nums[0];    // dp[i-1]
    
    for (int i = 1; i < n; ++i) {
        int curr = std::max(prev1, prev2 + nums[i]);
        prev2 = prev1;
        prev1 = curr;
    }
    return prev1;
}

int main() {
    std::vector<int> nums1 = {1, 2, 3, 1};
    std::vector<int> nums2 = {2, 7, 9, 3, 1};
    std::cout << "Rob " << rob(nums1) << "\n";  // 4
    std::cout << "Rob " << rob(nums2) << "\n";  // 12
    return 0;
}
```

### Decode Ways

**Problem**: A message consists of letters A-Z encoded as "1"-"26". Given a string of digits, count the number of ways to decode it.

**State**: `dp[i]` = number of ways to decode `s[0..i-1]`.

**Recurrence**:
- If `s[i-1] != '0'`: `dp[i] += dp[i-1]` (single digit)
- If `s[i-2..i-1]` forms 10-26: `dp[i] += dp[i-2]` (two digits)

```cpp
#include <iostream>
#include <string>
#include <vector>

int num_decodings(const std::string& s) {
    int n = s.size();
    if (n == 0 || s[0] == '0') return 0;
    
    int prev2 = 1;  // dp[0]
    int prev1 = 1;  // dp[1]
    
    for (int i = 2; i <= n; ++i) {
        int curr = 0;
        // Single digit decode
        if (s[i - 1] != '0') {
            curr += prev1;
        }
        // Two digit decode
        int two_digit = (s[i - 2] - '0') * 10 + (s[i - 1] - '0');
        if (two_digit >= 10 && two_digit <= 26) {
            curr += prev2;
        }
        prev2 = prev1;
        prev1 = curr;
    }
    return prev1;
}

int main() {
    std::cout << num_decodings("12") << "\n";    // 2: "AB" or "L"
    std::cout << num_decodings("226") << "\n";   // 3: "BZ", "VF", "BBF"
    std::cout << num_decodings("06") << "\n";    // 0: leading zero
    return 0;
}
```

---

## 31.2 Knapsack DP

Knapsack problems are among the most common DP patterns. They all share a similar structure: given a set of items and a capacity, optimize some objective.

### 0/1 Knapsack

Each item can be taken or not. **This is the foundation.**

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Returns maximum value achievable
int knapsack_01(const std::vector<int>& weights, const std::vector<int>& values,
                int capacity) {
    int n = weights.size();
    std::vector<int> dp(capacity + 1, 0);
    
    for (int i = 0; i < n; ++i) {
        for (int w = capacity; w >= weights[i]; --w) {
            dp[w] = std::max(dp[w], dp[w - weights[i]] + values[i]);
        }
    }
    return dp[capacity];
}

int main() {
    std::vector<int> w = {1, 3, 4, 5};
    std::vector<int> v = {1, 4, 5, 7};
    std::cout << "0/1 Knapsack: " << knapsack_01(w, v, 7) << "\n";  // 9
    return 0;
}
```

### Unbounded Knapsack

Each item can be taken unlimited times. **Only change**: iterate `w` forward instead of backward.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int knapsack_unbounded(const std::vector<int>& weights, 
                       const std::vector<int>& values, int capacity) {
    int n = weights.size();
    std::vector<int> dp(capacity + 1, 0);
    
    for (int i = 0; i < n; ++i) {
        for (int w = weights[i]; w <= capacity; ++w) {  // Forward!
            dp[w] = std::max(dp[w], dp[w - weights[i]] + values[i]);
        }
    }
    return dp[capacity];
}

int main() {
    std::vector<int> w = {1, 3, 4, 5};
    std::vector<int> v = {1, 4, 5, 7};
    std::cout << "Unbounded Knapsack: " << knapsack_unbounded(w, v, 7) << "\n";
    return 0;
}
```

### Bounded Knapsack

Each item has a limited count. Convert to 0/1 knapsack by binary splitting: split count `k` into groups of 1, 2, 4, ..., remainder.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int knapsack_bounded(std::vector<int> weights, std::vector<int> values,
                     std::vector<int> counts, int capacity) {
    // Binary splitting
    std::vector<int> new_weights, new_values;
    for (int i = 0; i < (int)weights.size(); ++i) {
        int k = counts[i];
        for (int power = 1; k > 0; power <<= 1) {
            int take = std::min(power, k);
            new_weights.push_back(weights[i] * take);
            new_values.push_back(values[i] * take);
            k -= take;
        }
    }
    return knapsack_01(new_weights, new_values, capacity);
}
```

### Subset Sum

**Problem**: Can we pick a subset of numbers that sums to target?

This is 0/1 knapsack with `values = weights` and `capacity = target`.

```cpp
#include <iostream>
#include <vector>

bool can_partition(const std::vector<int>& nums, int target) {
    std::vector<bool> dp(target + 1, false);
    dp[0] = true;
    
    for (int num : nums) {
        for (int s = target; s >= num; --s) {
            dp[s] = dp[s] || dp[s - num];
        }
    }
    return dp[target];
}

int main() {
    std::vector<int> nums = {1, 5, 11, 5};
    int sum = 0;
    for (int n : nums) sum += n;
    
    if (sum % 2 == 0 && can_partition(nums, sum / 2)) {
        std::cout << "Can partition into equal subsets\n";
    } else {
        std::cout << "Cannot partition\n";
    }
    return 0;
}
```

### Knapsack Template Summary

| Type | Inner Loop Direction | Item Reuse |
|------|---------------------|-----------|
| 0/1 Knapsack | Backward (`w` from cap to weight) | Once |
| Unbounded Knapsack | Forward (`w` from weight to cap) | Unlimited |
| Bounded Knapsack | Binary split → 0/1 | Limited |

---

## 31.3 Interval DP

Interval DP solves problems on contiguous subarrays. The state is typically `dp[i][j]` representing the answer for the subarray from index `i` to `j`.

### Template

```cpp
for (int len = 2; len <= n; ++len) {           // Length of interval
    for (int i = 0; i + len - 1 < n; ++i) {   // Start index
        int j = i + len - 1;                    // End index
        for (int k = i; k < j; ++k) {           // Split point
            dp[i][j] = optimize(dp[i][j], dp[i][k] + dp[k+1][j] + cost(i, k, j));
        }
    }
}
```

### Matrix Chain Multiplication

**Problem**: Given dimensions of matrices, find the minimum number of scalar multiplications to compute the product.

For matrices A₁(A×B), A₂(B×C), A₃(C×D):
- (A₁A₂)A₃ costs A×B×C + A×C×D
- A₁(A₂A₃) costs B×C×D + A×B×D

These can differ significantly!

```cpp
#include <iostream>
#include <vector>
#include <climits>

int matrix_chain(const std::vector<int>& dims) {
    int n = dims.size() - 1;  // number of matrices
    // dp[i][j] = min cost to multiply matrices i through j
    std::vector<std::vector<int>> dp(n, std::vector<int>(n, 0));
    
    for (int len = 2; len <= n; ++len) {
        for (int i = 0; i + len - 1 < n; ++i) {
            int j = i + len - 1;
            dp[i][j] = INT_MAX;
            for (int k = i; k < j; ++k) {
                int cost = dp[i][k] + dp[k + 1][j] 
                         + dims[i] * dims[k + 1] * dims[j + 1];
                dp[i][j] = std::min(dp[i][j], cost);
            }
        }
    }
    return dp[0][n - 1];
}

int main() {
    // Matrices: 10x30, 30x5, 5x60
    std::vector<int> dims = {10, 30, 5, 60};
    std::cout << "Min multiplications: " << matrix_chain(dims) << "\n";
    // (10x30 * 30x5) * 5x60 = 10*30*5 + 10*5*60 = 1500 + 3000 = 4500
    // 10x30 * (30x5 * 5x60) = 30*5*60 + 10*30*60 = 9000 + 18000 = 27000
    return 0;
}
```

**Complexity**: O(n³) time, O(n²) space.

### Burst Balloons

**Problem**: Given `n` balloons with numbers, bursting balloon `i` earns `nums[i-1] * nums[i] * nums[i+1]` coins. Find the maximum coins.

**Key insight**: Think in reverse — which balloon is burst **last** in each interval?

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int max_coins(std::vector<int>& nums) {
    // Add boundary balloons with value 1
    int n = nums.size();
    std::vector<int> a(n + 2, 1);
    for (int i = 0; i < n; ++i) {
        a[i + 1] = nums[i];
    }
    n += 2;
    
    // dp[i][j] = max coins from bursting balloons between i and j (exclusive)
    std::vector<std::vector<int>> dp(n, std::vector<int>(n, 0));
    
    for (int len = 2; len < n; ++len) {
        for (int i = 0; i + len < n; ++i) {
            int j = i + len;
            for (int k = i + 1; k < j; ++k) {
                dp[i][j] = std::max(dp[i][j], 
                    dp[i][k] + dp[k][j] + a[i] * a[k] * a[j]);
            }
        }
    }
    return dp[0][n - 1];
}

int main() {
    std::vector<int> nums = {3, 1, 5, 8};
    std::cout << "Max coins: " << max_coins(nums) << "\n";  // 167
    return 0;
}
```

---

## 31.4 Tree DP

Tree DP applies dynamic programming on tree structures. The state often includes the node and whether it's included/excluded.

### Maximum Independent Set on Tree

**Problem**: Select a subset of nodes such that no two selected nodes are adjacent, maximizing the sum.

**State**: For each node, track two values:
- `dp[node][0]` = max sum when `node` is NOT selected
- `dp[node][1]` = max sum when `node` IS selected

**Recurrence**:
- `dp[node][0] = sum(max(dp[child][0], dp[child][1]))` for all children
- `dp[node][1] = node.val + sum(dp[child][0])` for all children

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

struct TreeNode {
    int val;
    std::vector<int> children;
};

class TreeDP {
    std::vector<TreeNode> tree;
    std::vector<std::vector<int>> dp;
    
    void dfs(int node, int parent) {
        dp[node][0] = 0;          // Not selected
        dp[node][1] = tree[node].val;  // Selected
        
        for (int child : tree[node].children) {
            if (child == parent) continue;
            dfs(child, node);
            dp[node][0] += std::max(dp[child][0], dp[child][1]);
            dp[node][1] += dp[child][0];
        }
    }
    
public:
    int solve(int root) {
        int n = tree.size();
        dp.assign(n, std::vector<int>(2, 0));
        dfs(root, -1);
        return std::max(dp[root][0], dp[root][1]);
    }
    
    TreeDP(const std::vector<TreeNode>& t) : tree(t) {}
};

int main() {
    // Tree:    1
    //        / | \
    //       2  3  4
    //      / \
    //     5   6
    std::vector<TreeNode> tree(7);
    tree[1] = {10, {2, 3, 4}};
    tree[2] = {5, {1, 5, 6}};
    tree[3] = {8, {1}};
    tree[4] = {3, {1}};
    tree[5] = {4, {2}};
    tree[6] = {6, {2}};
    
    TreeDP solver(tree);
    std::cout << "Max independent set: " << solver.solve(1) << "\n";
    return 0;
}
```

### Tree Diameter via DP

**Problem**: Find the longest path in a tree.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class TreeDiameter {
    std::vector<std::vector<std::pair<int,int>>> adj;
    int diameter = 0;
    
    // Returns the longest path from node going downward
    int dfs(int node, int parent) {
        int max1 = 0, max2 = 0;  // Two longest paths from children
        
        for (auto& [child, weight] : adj[node]) {
            if (child == parent) continue;
            int child_path = dfs(child, node) + weight;
            if (child_path > max1) {
                max2 = max1;
                max1 = child_path;
            } else if (child_path > max2) {
                max2 = child_path;
            }
        }
        
        diameter = std::max(diameter, max1 + max2);
        return max1;
    }
    
public:
    TreeDiameter(int n) : adj(n) {}
    
    void add_edge(int u, int v, int w) {
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    }
    
    int solve(int root = 0) {
        dfs(root, -1);
        return diameter;
    }
};

int main() {
    TreeDiameter td(5);
    td.add_edge(0, 1, 2);
    td.add_edge(0, 2, 3);
    td.add_edge(1, 3, 4);
    td.add_edge(1, 4, 1);
    
    std::cout << "Tree diameter: " << td.solve() << "\n";  // 9 (3-0-1-3)
    return 0;
}
```

---

## 31.5 Bitmask DP

Bitmask DP uses a bitmask to represent which elements have been processed. This is essential when the state involves a **subset** of elements.

### When to Use Bitmask DP

- The problem involves selecting a subset or permutation of elements.
- `n` is small (typically ≤ 20, since 2^20 ≈ 10^6).
- The state needs to track which elements are "used."

### Travelling Salesman Problem (TSP)

**Problem**: Visit all cities exactly once and return to the starting city, minimizing total distance.

**State**: `dp[mask][i]` = minimum cost to visit the set of cities represented by `mask`, currently at city `i`.

```cpp
#include <iostream>
#include <vector>
#include <climits>
#include <algorithm>

int tsp(const std::vector<std::vector<int>>& dist) {
    int n = dist.size();
    int full_mask = (1 << n) - 1;
    
    // dp[mask][i] = min cost to visit cities in mask, ending at city i
    std::vector<std::vector<int>> dp(1 << n, std::vector<int>(n, INT_MAX));
    dp[1][0] = 0;  // Start at city 0
    
    for (int mask = 1; mask <= full_mask; ++mask) {
        for (int u = 0; u < n; ++u) {
            if (dp[mask][u] == INT_MAX) continue;
            if (!(mask & (1 << u))) continue;  // u must be in mask
            
            for (int v = 0; v < n; ++v) {
                if (mask & (1 << v)) continue;  // v must not be in mask
                int new_mask = mask | (1 << v);
                dp[new_mask][v] = std::min(dp[new_mask][v], 
                                           dp[mask][u] + dist[u][v]);
            }
        }
    }
    
    // Return to city 0
    int ans = INT_MAX;
    for (int i = 0; i < n; ++i) {
        if (dp[full_mask][i] != INT_MAX) {
            ans = std::min(ans, dp[full_mask][i] + dist[i][0]);
        }
    }
    return ans;
}

int main() {
    std::vector<std::vector<int>> dist = {
        {0, 10, 15, 20},
        {10, 0, 35, 25},
        {15, 35, 0, 30},
        {20, 25, 30, 0}
    };
    std::cout << "TSP cost: " << tsp(dist) << "\n";  // 80
    return 0;
}
```

**Complexity**: O(2^n × n²) time, O(2^n × n) space.

### Assignment Problem

**Problem**: Assign `n` workers to `n` tasks, one per worker, minimizing total cost.

This is a direct application of bitmask DP with `dp[mask][i]` = min cost to assign the first `i` workers to tasks in `mask`.

---

## 31.6 Digit DP

Digit DP counts numbers in a range [L, R] satisfying some digit-based constraint. The key idea is to count numbers digit by digit, tracking whether we're still bounded by the original number.

### Template

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <cstring>

class DigitDP {
    std::string num;
    std::vector<std::vector<long long>> memo;
    
    // pos: current digit position
    // tight: 1 if still bounded by num's digits, 0 if already smaller
    // sum: accumulated digit sum (or whatever constraint)
    long long solve(int pos, int tight, int sum) {
        if (pos == (int)num.size()) {
            // Check constraint — here we count all valid numbers
            return 1;
        }
        
        if (memo[pos][tight] != -1 && !tight) return memo[pos][tight];
        
        int limit = tight ? (num[pos] - '0') : 9;
        long long result = 0;
        
        for (int digit = 0; digit <= limit; ++digit) {
            int new_tight = tight && (digit == limit);
            // Apply constraint here (e.g., digit sum condition)
            result += solve(pos + 1, new_tight, sum + digit);
        }
        
        if (!tight) memo[pos][tight] = result;
        return result;
    }
    
public:
    long long count(long long n) {
        num = std::to_string(n);
        memo.assign(num.size() + 1, std::vector<long long>(2, -1));
        return solve(0, 1, 0);
    }
};

int main() {
    DigitDP solver;
    // Count numbers from 0 to 999
    std::cout << "Count [0, 999]: " << solver.count(999) << "\n";
    return 0;
}
```

### Example: Count Numbers with Digit Sum = K

```cpp
#include <iostream>
#include <string>
#include <vector>

class DigitSumDP {
    std::string num;
    int target;
    std::vector<std::vector<std::vector<long long>>> memo;
    
    long long solve(int pos, int tight, int sum) {
        if (pos == (int)num.size()) {
            return sum == target ? 1 : 0;
        }
        
        if (memo[pos][tight][sum] != -1) return memo[pos][tight][sum];
        
        int limit = tight ? (num[pos] - '0') : 9;
        long long result = 0;
        
        for (int digit = 0; digit <= limit; ++digit) {
            if (sum + digit > target) break;
            int new_tight = tight && (digit == limit);
            result += solve(pos + 1, new_tight, sum + digit);
        }
        
        return memo[pos][tight][sum] = result;
    }
    
public:
    long long count(long long n, int k) {
        num = std::to_string(n);
        target = k;
        int max_sum = 9 * num.size();
        memo.assign(num.size() + 1, 
                    std::vector<std::vector<long long>>(2, 
                    std::vector<long long>(max_sum + 1, -1)));
        return solve(0, 1, 0);
    }
};

int main() {
    DigitSumDP solver;
    // Count numbers from 0 to 999 with digit sum = 5
    std::cout << "Count [0, 999] with digit sum 5: " << solver.count(999, 5) << "\n";
    return 0;
}
```

---

## 31.7 Profile DP

Profile DP (also called "plug DP" or "profile on grid") solves problems on grids where the state encodes a "profile" of the boundary between processed and unprocessed regions.

### Domino Tiling

**Problem**: Count the number of ways to tile an `m × n` grid with 2×1 dominoes.

For small `m` (e.g., m ≤ 10), we can use bitmask DP where each column is a bitmask indicating which cells are covered.

```cpp
#include <iostream>
#include <vector>

int domino_tiling(int m, int n) {
    // dp[j][mask] = ways to tile columns 0..j-1 completely, 
    //               with column j partially filled according to mask
    int full = (1 << m) - 1;
    std::vector<std::vector<int>> dp(n + 1, std::vector<int>(1 << m, 0));
    dp[0][0] = 1;
    
    for (int j = 0; j < n; ++j) {
        for (int mask = 0; mask <= full; ++mask) {
            if (dp[j][mask] == 0) continue;
            // Try to fill column j+1 starting from state mask
            // Use DFS to enumerate valid placements
            std::vector<int> next(1 << m, 0);
            
            // Recursive function to try all placements in column j
            // This is complex — simplified version for m=2:
            if (m == 2) {
                // Case 1: place vertical domino in column j+1
                dp[j + 1][mask ^ full] += dp[j][mask];
                // Case 2: place horizontal dominoes
                if (mask == 0) {
                    dp[j + 1][0] += dp[j][mask];  // Two horizontal
                }
            }
        }
    }
    return dp[n][0];
}

// General solution using DFS for profile transitions
int domino_tiling_general(int m, int n) {
    int full = (1 << m) - 1;
    std::vector<int> dp(1 << m, 0), next(1 << m, 0);
    dp[0] = 1;
    
    for (int col = 0; col < n; ++col) {
        for (int row = 0; row < m; ++row) {
            std::fill(next.begin(), next.end(), 0);
            for (int mask = 0; mask <= full; ++mask) {
                if (dp[mask] == 0) continue;
                bool bit = mask & (1 << row);
                if (bit) {
                    // Cell is already filled, move on
                    next[mask ^ (1 << row)] += dp[mask];
                } else {
                    // Cell is empty
                    // Option 1: place vertical domino (if row+1 < m and next row empty)
                    if (row + 1 < m && !(mask & (1 << (row + 1)))) {
                        next[mask | (1 << (row + 1))] += dp[mask];
                    }
                    // Option 2: place horizontal domino (extends to next column)
                    next[mask | (1 << row)] += dp[mask];
                }
            }
            dp = next;
        }
    }
    return dp[0];
}

int main() {
    std::cout << "2x3 tiling: " << domino_tiling_general(2, 3) << "\n";  // 3
    std::cout << "3x4 tiling: " << domino_tiling_general(3, 4) << "\n";  // 11
    return 0;
}
```

---

## 31.8 DP Optimization

When the basic DP is O(n³) and you need O(n²), or O(n²) and you need O(n log n), various optimization techniques apply.

### Knuth's Optimization

**Applicable when**: The recurrence is `dp[i][j] = min(dp[i][k] + dp[k][j]) + cost(i, j)` and the cost function satisfies the **quadrangle inequality**.

**Key property**: If `opt[i][j-1] ≤ opt[i][j] ≤ opt[i+1][j]` (where `opt[i][j]` is the optimal split point), we can restrict the search range.

**Complexity improvement**: O(n³) → O(n²).

```cpp
// Knuth's optimization template (for matrix chain multiplication)
#include <iostream>
#include <vector>
#include <climits>

int matrix_chain_knuth(const std::vector<int>& dims) {
    int n = dims.size() - 1;
    std::vector<std::vector<int>> dp(n, std::vector<int>(n, 0));
    std::vector<std::vector<int>> opt(n, std::vector<int>(n, 0));
    
    // Base: opt[i][i] = i
    for (int i = 0; i < n; ++i) opt[i][i] = i;
    
    for (int len = 2; len <= n; ++len) {
        for (int i = 0; i + len - 1 < n; ++i) {
            int j = i + len - 1;
            dp[i][j] = INT_MAX;
            
            // Restrict search to [opt[i][j-1], opt[i+1][j]]
            int start = (j > i) ? opt[i][j - 1] : i;
            int end = (i + 1 < n) ? opt[i + 1][j] : j;
            start = std::max(start, i);
            end = std::min(end, j - 1);
            
            for (int k = start; k <= end; ++k) {
                int cost = dp[i][k] + dp[k + 1][j] + dims[i] * dims[k + 1] * dims[j + 1];
                if (cost < dp[i][j]) {
                    dp[i][j] = cost;
                    opt[i][j] = k;
                }
            }
        }
    }
    return dp[0][n - 1];
}

int main() {
    std::vector<int> dims = {10, 30, 5, 60};
    std::cout << "Min multiplications (Knuth): " << matrix_chain_knuth(dims) << "\n";
    return 0;
}
```

### Divide and Conquer Optimization

**Applicable when**: `dp[i][j] = min(dp[i-1][k] + cost(k, j))` and `cost` satisfies the quadrangle inequality.

**Complexity improvement**: O(kn²) → O(kn log n).

The idea: compute each row of the DP table using divide and conquer, leveraging the monotonicity of optimal split points.

### Convex Hull Trick

**Applicable when**: The recurrence has the form `dp[i] = min(dp[j] + b[j] * a[i])` — a minimum of linear functions evaluated at `a[i]`.

**Complexity improvement**: O(n²) → O(n) amortized per query.

```cpp
#include <iostream>
#include <vector>
#include <deque>

struct Line {
    long long m, b;  // y = m*x + b
    long long eval(long long x) const { return m * x + b; }
    
    // Intersection x-coordinate with line other
    double intersect_x(const Line& other) const {
        return double(other.b - b) / double(m - other.m);
    }
};

class ConvexHullTrick {
    std::deque<Line> hull;
    
public:
    // Add line y = m*x + b (for minimization, add lines in decreasing slope order)
    void add_line(long long m, long long b) {
        Line new_line = {m, b};
        while (hull.size() >= 2) {
            Line last = hull.back();
            Line second_last = hull[hull.size() - 2];
            // If new line makes last line obsolete, remove it
            if (last.intersect_x(new_line) <= second_last.intersect_x(last)) {
                hull.pop_back();
            } else {
                break;
            }
        }
        hull.push_back(new_line);
    }
    
    // Query minimum y value at x (queries should be non-decreasing)
    long long query(long long x) {
        while (hull.size() >= 2 && hull[0].eval(x) >= hull[1].eval(x)) {
            hull.pop_front();
        }
        return hull[0].eval(x);
    }
};

int main() {
    // Example: dp[i] = min over j < i of (dp[j] + (sum[i] - sum[j])^2)
    // Expanding: dp[j] + sum[i]^2 - 2*sum[i]*sum[j] + sum[j]^2
    // = (dp[j] + sum[j]^2) + (-2*sum[j]) * sum[i] + sum[i]^2
    // Lines with m = -2*sum[j], b = dp[j] + sum[j]^2
    
    ConvexHullTrick cht;
    // Example: minimize cost of partitioning array
    cht.add_line(-2 * 0, 0 + 0);  // j=0: m=0, b=0
    
    std::vector<int> arr = {1, 3, 2, 4};
    std::vector<long long> prefix = {0};
    for (int x : arr) prefix.push_back(prefix.back() + x);
    
    long long dp_val = 0;
    for (int i = 1; i <= (int)arr.size(); ++i) {
        dp_val = cht.query(prefix[i]) + prefix[i] * prefix[i];
        cht.add_line(-2 * prefix[i], dp_val + prefix[i] * prefix[i]);
    }
    std::cout << "Min cost: " << dp_val << "\n";
    return 0;
}
```

### Overview of DP Optimizations

| Optimization | Original | Optimized | Condition |
|-------------|----------|-----------|-----------|
| Knuth's | O(n³) | O(n²) | Quadrangle inequality on cost |
| Divide & Conquer | O(kn²) | O(kn log n) | Quadrangle inequality |
| Convex Hull Trick | O(n²) | O(n) amortized | Recurrence is min of linear functions |
| Monotone Queue | O(nk) | O(n) | Sliding window minimum |
| SMAWK | O(n²) | O(n) | Totally monotone matrix |

---

## Interview Tips

1. **Recognize the pattern first**. Is it linear DP? Knapsack? Interval? This determines your state definition.

2. **Bitmask DP**: If `n ≤ 20` and the problem involves subsets, think bitmask.

3. **Interval DP**: If the problem is about merging or splitting intervals, try `dp[i][j]`.

4. **Tree DP**: Post-order traversal is your friend. Process children before parent.

5. **Digit DP**: When counting numbers with digit constraints in a range [L, R], use `count(R) - count(L-1)`.

6. **Start with the simplest state** that works, then optimize space.

7. **For knapsack variants**, always ask: "Can I use items multiple times?" This determines forward vs backward iteration.

## Common Mistakes

| Mistake | Pattern | Fix |
|---------|---------|-----|
| Wrong loop order in bitmask DP | Bitmask | Iterate mask from 0 to 2^n - 1 |
| Not handling "tight" in digit DP | Digit DP | Track whether prefix matches the bound |
| Forgetting parent in tree DP | Tree DP | Pass parent parameter to avoid cycles |
| Wrong direction in knapsack | Knapsack | Backward for 0/1, forward for unbounded |
| Off-by-one in interval DP | Interval | Be careful with inclusive/exclusive bounds |

## Practice Problems

1. **Longest Increasing Subsequence** (LeetCode 300) — Linear DP + binary search
2. **Partition Equal Subset Sum** (LeetCode 416) — 0/1 Knapsack
3. **Coin Change** (LeetCode 322) — Unbounded knapsack
4. **Burst Balloons** (LeetCode 312) — Interval DP
5. **House Robber III** (LeetCode 337) — Tree DP
6. **Travelling Salesman** (SPOJ/standard) — Bitmask DP
7. **Digit Count** (LeetCode 233) — Digit DP
8. **Domino and Tromino Tiling** (LeetCode 790) — Profile DP
9. **Edit Distance** (LeetCode 72) — Classic 2D DP
10. **Palindrome Partitioning II** (LeetCode 132) — Interval DP

---

## See Also

- [Chapter 30: DP Fundamentals](ch30-dp-fundamentals.md) — The foundation: state design, transitions, memoization vs tabulation, and the DP thinking process.
- [Chapter 85: Digit DP](ch85-digit-dp.md) — When the problem involves counting numbers with digit constraints, digit DP is the go-to pattern.
- [Chapter 86: DP Optimization](ch86-dp-optimization.md) — Speed up O(n³) DP to O(n²) with Knuth's optimization, or use convex hull trick for O(n log n).
- [Chapter 33: Bit Manipulation](ch33-bit-manipulation.md) — Bitmask DP relies on bitwise operations; mastering bit manipulation is essential for subset DP.
- [Chapter 113: Profile DP](ch113-profile-dp.md) — Advanced profile DP for tiling, domino, and grid constraint problems.
