# Chapter 59: Expanded Dynamic Programming

## Prerequisites

- Basic DP (knapsack, LCS, LIS, coin change)
- Recurrence relations and state transitions
- Space optimization with rolling arrays
- Basic probability concepts
- Game theory basics (Nim)

## Interview Frequency: ★★★★★

DP is the single most important topic for technical interviews. Every major company tests DP extensively. **Google** and **Meta** love probability DP and state design. **Amazon** focuses on classic patterns. **ByteDance** and **Huawei** test advanced optimizations. Probability DP and game theory DP appear at **Google**, **Two Sigma**, and **Jane Street**. The meta-skills (how to identify DP, how to design states, how to debug) are invaluable for every interview.

| Topic | Frequency | Typical Companies | Difficulty |
|---|---|---|---|
| Probability DP | ★★★★ | Google, Two Sigma, Jane Street | Hard |
| Game DP | ★★★ | Google, competitive programming | Medium-Hard |
| Broken Profile DP | ★★ | Competitive programming | Hard |
| Aliens Trick | ★★ | Google, advanced interviews | Hard |
| Slope Optimization | ★★ | Competitive programming | Hard |
| State Design | ★★★★★ | All companies | Medium |
| Transition Design | ★★★★★ | All companies | Medium |
| Space Optimization | ★★★★ | All companies | Medium |
| DP Debugging | ★★★★★ | All companies | N/A |

---

## 59.1 Probability DP

Probability DP computes expected values or probabilities of outcomes in stochastic processes. The key insight: the DP state represents a situation, and transitions are weighted by probabilities.

### When to Use

- Expected number of steps to reach a goal
- Probability of winning a game with randomness
- Expected cost/profit under uncertainty

### Common Patterns

| Pattern | State | Transition |
|---|---|---|
| Expected steps | `E[s]` = expected steps from state s | `E[s] = 1 + Σ p(s→s') × E[s']` |
| Win probability | `P[s]` = prob of winning from s | `P[s] = Σ p(s→s') × P[s']` |
| Expected reward | `R[s]` = expected reward from s | `R[s] = reward(s) + Σ p(s→s') × R[s']` |

### Example 1: Expected Dice Throws

What is the expected number of dice throws to reach position N starting from 0, where each throw moves you 1-6 steps forward?

```cpp
#include <iostream>
#include <vector>
#include <iomanip>

// E[i] = expected throws from position i to reach n
// E[n] = 0 (already there)
// E[i] = 1 + (E[i+1] + E[i+2] + ... + E[i+6]) / 6
double expectedDiceThrows(int n) {
    std::vector<double> E(n + 1, 0.0);
    
    for (int i = n - 1; i >= 0; i--) {
        E[i] = 1.0; // This throw
        for (int d = 1; d <= 6; d++) {
            int next = std::min(i + d, n);
            E[i] += E[next] / 6.0;
        }
    }
    
    return E[0];
}

int main() {
    for (int n : {10, 20, 30}) {
        std::cout << "Expected throws to reach " << n << ": " 
                  << std::fixed << std::setprecision(4) 
                  << expectedDiceThrows(n) << "\n";
    }
    return 0;
}
```

### Example 2: Coin Flip Game

Alice and Bob flip a fair coin alternately. Alice wins if she gets heads before Bob gets tails. What is Alice's win probability?

```cpp
#include <iostream>
#include <vector>
#include <iomanip>

// dp[i][j] = probability of reaching state (i heads for Alice, j tails for Bob)
// Alice wins if she gets 1 head first
// Bob wins if he gets 1 tail first

// Simpler: P(Alice wins) = P(H on 1st) + P(T then H) + P(T T then H) + ...
// = 1/2 + 1/4 × 1/2 + ... = Σ (1/2)^(2k+1) = 2/3

double aliceWinProb() {
    // With n consecutive heads needed for Alice, m consecutive tails for Bob
    // State: (consecutiveH, consecutiveT, whoseTurn)
    int n = 1, m = 1; // Alice needs 1 head, Bob needs 1 tail
    
    // dp[h][t][turn] = probability of Alice winning
    // h = consecutive heads so far (0 to n)
    // t = consecutive tails so far (0 to m)
    // turn = 0 (Alice) or 1 (Bob)
    std::vector<std::vector<std::vector<double>>> 
        dp(n + 1, std::vector<std::vector<double>>(m + 1, std::vector<double>(2, -1)));
    
    // Simple analytical: P = 1/2 + 1/2 * 1/2 * P
    // P = 1/2 / (1 - 1/4) = 2/3
    return 2.0 / 3.0;
}

// More complex version: Alice needs k consecutive heads
double aliceWinProbConsecutive(int k) {
    // State: (a, b, turn)
    // a = Alice's consecutive heads (0 to k)
    // b = Bob's consecutive tails (0 to k)
    // turn: 0 = Alice, 1 = Bob
    int K = k;
    std::vector<std::vector<std::vector<double>>> 
        dp(K + 1, std::vector<std::vector<double>>(K + 1, std::vector<double>(2, -1.0)));
    
    auto solve = [&](auto& self, int a, int b, int turn) -> double {
        if (a == K) return 1.0;  // Alice wins
        if (b == K) return 0.0;  // Bob wins
        if (dp[a][b][turn] >= 0) return dp[a][b][turn];
        
        double result;
        if (turn == 0) { // Alice's turn
            // Heads (prob 0.5): a increases by 1, Bob's turn
            // Tails (prob 0.5): a resets to 0, Bob's turn
            result = 0.5 * self(self, a + 1, b, 1) + 
                     0.5 * self(self, 0, b, 1);
        } else { // Bob's turn
            // Tails (prob 0.5): b increases by 1, Alice's turn
            // Heads (prob 0.5): b resets to 0, Alice's turn
            result = 0.5 * self(self, a, b + 1, 0) + 
                     0.5 * self(self, a, 0, 0);
        }
        
        return dp[a][b][turn] = result;
    };
    
    return solve(solve, 0, 0, 0);
}

int main() {
    std::cout << std::fixed << std::setprecision(6);
    std::cout << "Alice win prob (k=1): " << aliceWinProbConsecutive(1) << "\n";
    std::cout << "Alice win prob (k=2): " << aliceWinProbConsecutive(2) << "\n";
    std::cout << "Alice win prob (k=3): " << aliceWinProbConsecutive(3) << "\n";
    
    return 0;
}
```

### Example 3: Random Walk on a Line

A particle starts at position 0 on a line of length N. Each step, it moves +1 or -1 with equal probability. What is the expected number of steps to reach either end?

```cpp
#include <iostream>
#include <vector>
#include <iomanip>

// E[i] = expected steps from position i to reach 0 or n
// E[0] = E[n] = 0
// E[i] = 1 + 0.5 * E[i-1] + 0.5 * E[i+1]
// Rearranging: E[i] = (2 + E[i-1] + E[i+1]) / 2
// This gives: E[i] = i * (n - i)

long long randomWalkExpected(int n, int start) {
    // Analytical: E[i] = i * (n - i)
    return (long long)start * (n - start);
}

// Verify with DP
double randomWalkDP(int n, int start) {
    // System of linear equations: E[i] = 1 + 0.5*E[i-1] + 0.5*E[i+1]
    // With E[0] = E[n] = 0
    // Solution: E[i] = i * (n - i)
    
    std::vector<double> E(n + 1, 0.0);
    
    // Iterative method (Gauss-Seidel style)
    for (int iter = 0; iter < 10000; iter++) {
        for (int i = 1; i < n; i++) {
            E[i] = 1.0 + 0.5 * E[i - 1] + 0.5 * E[i + 1];
        }
    }
    
    return E[start];
}

int main() {
    std::cout << std::fixed << std::setprecision(2);
    
    int n = 10;
    for (int s = 1; s < n; s++) {
        std::cout << "Position " << s << ": analytical=" 
                  << randomWalkExpected(n, s) 
                  << ", DP=" << randomWalkDP(n, s) << "\n";
    }
    
    return 0;
}
```

---

## 59.2 Game DP (Nim and Grundy Numbers)

### Nim Game

In Nim, there are several piles of stones. Two players alternate turns, removing any number of stones from a single pile. The player who takes the last stone wins (normal play).

**Key theorem**: The first player wins if and only if the XOR of all pile sizes is non-zero.

```cpp
#include <iostream>
#include <vector>
#include <numeric>

bool nimWin(const std::vector<int>& piles) {
    int xorSum = 0;
    for (int p : piles) xorSum ^= p;
    return xorSum != 0;
}

// Find the winning move (if exists)
std::pair<int, int> nimWinningMove(const std::vector<int>& piles) {
    int xorSum = 0;
    for (int p : piles) xorSum ^= p;
    
    if (xorSum == 0) return {-1, -1}; // No winning move
    
    for (int i = 0; i < (int)piles.size(); i++) {
        int target = piles[i] ^ xorSum;
        if (target < piles[i]) {
            // Take (piles[i] - target) stones from pile i
            return {i, piles[i] - target};
        }
    }
    return {-1, -1};
}

int main() {
    std::vector<int> piles = {3, 5, 7};
    
    std::cout << "Piles: ";
    for (int p : piles) std::cout << p << " ";
    std::cout << "\n";
    
    std::cout << "XOR sum: " << (piles[0] ^ piles[1] ^ piles[2]) << "\n";
    std::cout << (nimWin(piles) ? "First" : "Second") << " player wins.\n";
    
    auto [pile, take] = nimWinningMove(piles);
    if (pile != -1) {
        std::cout << "Winning move: take " << take << " from pile " << pile << "\n";
    }
    
    return 0;
}
```

### Proof of Nim Strategy

The proof uses the **Sprague-Grundy theorem**:

1. Define `mex(S)` = minimum excludant of set S = smallest non-negative integer not in S
2. Grundy number of a single Nim pile of size n is `G(n) = n`
3. Grundy number of a game composed of independent subgames is the XOR of individual Grundy numbers
4. Position is losing (P-position) iff Grundy number is 0

### Grundy Numbers for General Games

```cpp
#include <iostream>
#include <vector>
#include <set>
#include <algorithm>

// Grundy number for a subtraction game:
// Players can remove 1, 2, or 3 stones from a pile
// Last player to move wins
int grundySubtraction(int n, const std::vector<int>& moves) {
    std::vector<int> g(n + 1, 0);
    
    for (int i = 1; i <= n; i++) {
        std::set<int> reachable;
        for (int m : moves) {
            if (m <= i) {
                reachable.insert(g[i - m]);
            }
        }
        // mex
        int mex = 0;
        while (reachable.count(mex)) mex++;
        g[i] = mex;
    }
    
    return g[n];
}

int main() {
    std::vector<int> moves = {1, 2, 3};
    
    std::cout << "Grundy numbers (subtraction {1,2,3}):\n";
    for (int i = 0; i <= 10; i++) {
        int g = grundySubtraction(i, moves);
        std::cout << "G(" << i << ") = " << g << "\n";
    }
    
    // Multi-pile subtraction game: XOR of Grundy numbers
    std::vector<int> piles = {5, 3, 8};
    int xorSum = 0;
    for (int p : piles) {
        xorSum ^= grundySubtraction(p, moves);
    }
    std::cout << "\nPiles: 5, 3, 8\n";
    std::cout << "XOR of Grundy numbers: " << xorSum << "\n";
    std::cout << (xorSum ? "First" : "Second") << " player wins.\n";
    
    return 0;
}
```

---

## 59.3 DP on Broken Profile (Domino Tiling)

**Broken Profile DP** solves tiling problems where we need to fill a grid with dominoes (or other shapes). The "profile" represents the boundary between filled and unfilled cells.

### Classic Problem

Count the number of ways to tile an N×M grid with 1×2 dominoes.

### State Definition

`dp[i][mask]` where:
- `i` = current row being processed
- `mask` = bitmask representing which cells in row i are already filled by dominoes extending from row i-1

```cpp
#include <iostream>
#include <vector>
#include <cstring>

long long dominoTiling(int n, int m) {
    // Ensure m is the smaller dimension for efficiency
    if (n < m) std::swap(n, m);
    
    // dp[mask] = number of ways to fill up to current column
    // mask has m bits, bit j = 1 means cell (current_row, j) is filled
    int maxMask = 1 << m;
    std::vector<long long> dp(maxMask, 0), next(maxMask, 0);
    dp[0] = 1;
    
    for (int col = 0; col < n; col++) {
        for (int row = 0; row < m; row++) {
            std::fill(next.begin(), next.end(), 0);
            for (int mask = 0; mask < maxMask; mask++) {
                if (dp[mask] == 0) continue;
                
                if (mask & (1 << row)) {
                    // Cell (row, col) is already filled from above
                    // Just pass through
                    next[mask ^ (1 << row)] += dp[mask];
                } else {
                    // Cell (row, col) is empty
                    // Option 1: Place horizontal domino (row, col) to (row, col+1)
                    // This fills the cell in the current mask
                    if (col + 1 < n) {
                        next[mask | (1 << row)] += dp[mask];
                    }
                    
                    // Option 2: Place vertical domino (row, col) to (row+1, col)
                    if (row + 1 < m && !(mask & (1 << (row + 1)))) {
                        next[mask | (1 << (row + 1))] += dp[mask];
                    }
                }
            }
            dp = next;
        }
    }
    
    return dp[0];
}

int main() {
    for (int n = 1; n <= 8; n++) {
        for (int m = 1; m <= 8; m++) {
            if (n * m % 2 != 0) continue; // Odd area can't be tiled
            std::cout << n << "x" << m << ": " << dominoTiling(n, m) << " ways\n";
        }
    }
    
    return 0;
}
```

### Profile DP State Design

| Tiling Shape | Profile Width | Mask Meaning |
|---|---|---|
| 1×2 domino | m bits | 1 = filled from above |
| 2×1 domino | m bits | 1 = filled from left |
| L-shaped tromino | m bits + extra state | 1 = filled, with special handling |
| 2×2 square | m bits | 1 = filled from above/left |

---

## 59.4 Aliens Trick (Parametric Search)

**Aliens Trick** (also called Lagrangian relaxation) converts a constrained optimization into an unconstrained one by adding a penalty term. It's used when:

- We want to optimize `f(x)` subject to `g(x) = k`
- Direct DP with the constraint is too expensive
- `f(x) + λ × g(x)` is easier to optimize

### When to Use

- "Find the best solution using exactly K segments/operations"
- The unconstrained version (any number of segments) is solvable
- Binary search on the penalty λ

### Example: Divide array into exactly K subarrays to minimize maximum subarray sum

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>
#include <functional>

// Aliens trick: find min max-subarray-sum when dividing into exactly K subarrays
// We binary search on lambda (penalty per subarray)
// Minimize: max(subarray_sum) + lambda * (number_of_subarrays)
// When lambda is large, we use fewer subarrays; when small, more

struct Result {
    long long cost;
    int segments;
};

Result solve(const std::vector<int>& arr, long long lambda) {
    int n = arr.size();
    // dp[i] = min cost to cover first i elements
    // cost of a segment [j, i] = max(0, sum[j..i]) + lambda
    // Actually for this problem: minimize (max subarray sum) + lambda * K
    // This is trickier; let's use a simpler example.
    
    // Simpler: divide into subarrays to minimize sum of (max of each subarray)
    // with penalty lambda per subarray
    long long dp = lambda; // Cost for empty prefix with 1 segment
    long long maxVal = 0;
    int segs = 1;
    
    // Greedy: each element starts new segment if adding it increases cost
    // This is a simplification; general case needs proper DP
    
    return {dp, segs};
}

// Better example: Minimize sum of squared deviations with exactly K clusters
// Or: Partition array into K subarrays, minimize sum of costs

// Let's do: partition array into K subarrays, minimize sum of (max - min) for each
// Or even simpler: minimize sum of range for each subarray

// Cleanest example: Weighted job scheduling with exactly K jobs
// Or: Divide array into K groups, minimize total penalty

// Here's a clean implementation of the aliens trick pattern:
struct AliensResult {
    long long value;
    int count; // Number of segments used
};

AliensResult aliensDP(const std::vector<int>& arr, long long penalty) {
    int n = arr.size();
    // dp[i] = minimum cost to process arr[0..i-1]
    // Each segment has cost = sum of elements + penalty
    // We want to minimize total cost
    
    // For this example: cost of segment [l, r] = sum(arr[l..r])^2
    // With penalty per segment
    
    // Simplified: cost of segment [l, r] = (sum)^2
    // Total cost = sum of costs + penalty * number_of_segments
    
    std::vector<long long> dp(n + 1, LLONG_MAX);
    std::vector<int> segCount(n + 1, 0);
    dp[0] = -penalty; // Compensate for the first segment
    
    for (int i = 1; i <= n; i++) {
        long long sum = 0;
        for (int j = i; j >= 1; j--) {
            sum += arr[j - 1];
            long long cost = sum * sum + penalty;
            if (dp[j - 1] + cost < dp[i]) {
                dp[i] = dp[j - 1] + cost;
                segCount[i] = segCount[j - 1] + 1;
            }
        }
    }
    
    return {dp[n], segCount[n]};
}

// Find minimum cost with exactly K segments using aliens trick
long long aliensTrick(const std::vector<int>& arr, int k) {
    // Binary search on penalty
    long long lo = -1e12, hi = 1e12;
    long long answer = 0;
    
    while (lo <= hi) {
        long long mid = lo + (hi - lo) / 2;
        auto result = aliensDP(arr, mid);
        
        if (result.count >= k) {
            // Too many segments, increase penalty
            answer = result.value - mid * k;
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    
    return answer;
}

int main() {
    std::vector<int> arr = {1, 3, 2, 4, 1, 5, 2};
    int k = 3;
    
    std::cout << "Array: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << "\n";
    std::cout << "Minimum cost with " << k << " segments: " 
              << aliensTrick(arr, k) << "\n";
    
    return 0;
}
```

### Aliens Trick Pattern

```
1. Define: f(x) = what we want to minimize, g(x) = number of segments
2. Define: h(λ) = min over all x of [f(x) + λ * g(x)]
3. Binary search λ such that the optimal g(x) = K
4. Answer = h(λ) - λ * K
```

---

## 59.5 Slope Optimization (Overview)

**Slope Optimization** (also called Convex Hull Trick) speeds up DP transitions of the form:

```
dp[i] = min(dp[j] + b[j] * a[i]) for j < i
```

where the transition is a linear function of `a[i]` with slope `b[j]` and intercept `dp[j]`.

### Key Idea

Maintain a convex hull of lines. For each query point `a[i]`, find the line that gives minimum value. If queries are monotonic, use a deque for O(1) amortized per transition.

### When to Use

- DP transition is linear in the query variable
- Naive O(n²) is too slow
- Slopes are monotonic (enables deque optimization)

```cpp
#include <iostream>
#include <vector>
#include <deque>
#include <climits>

// Example: dp[i] = min(dp[j] + (sum[i] - sum[j])^2) for j < i
// Expand: dp[j] + sum[i]^2 - 2*sum[i]*sum[j] + sum[j]^2
// = (dp[j] + sum[j]^2) + sum[i]^2 - 2*sum[i]*sum[j]
// Line: y = m*x + b where m = -2*sum[j], x = sum[i], b = dp[j] + sum[j]^2

struct Line {
    long long m, b; // y = mx + b
    long long eval(long long x) const { return m * x + b; }
    
    // Check if intersection with l2 is to the left of intersection with l1
    // (for maintaining lower hull with decreasing slopes)
    static bool bad(const Line& l1, const Line& l2, const Line& l3) {
        // (l3.b - l1.b) * (l1.m - l2.m) <= (l2.b - l1.b) * (l1.m - l3.m)
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
               Line::bad(hull[hull.size()-2], hull[hull.size()-1], newLine)) {
            hull.pop_back();
        }
        hull.push_back(newLine);
    }
    
    // Query minimum at x (assumes x queries are monotonic increasing)
    long long query(long long x) {
        while (hull.size() >= 2 && hull[1].eval(x) <= hull[0].eval(x)) {
            hull.pop_front();
        }
        return hull[0].eval(x);
    }
};

// Solve: divide array into groups, minimize sum of (group_sum)^2
long long solve(const std::vector<int>& arr, int k) {
    int n = arr.size();
    std::vector<long long> sum(n + 1, 0);
    for (int i = 0; i < n; i++) sum[i + 1] = sum[i] + arr[i];
    
    // dp[i] = min cost to partition arr[0..i-1] into any number of groups
    // dp[i] = min(dp[j] + (sum[i] - sum[j])^2) for j < i
    
    std::vector<long long> dp(n + 1, LLONG_MAX);
    dp[0] = 0;
    
    for (int g = 1; g <= k; g++) {
        ConvexHullTrick cht;
        std::vector<long long> newDp(n + 1, LLONG_MAX);
        
        for (int i = 0; i <= n; i++) {
            if (i >= g) {
                cht.addLine(-2 * sum[i], dp[i] + sum[i] * sum[i]);
            }
            if (i > 0) {
                newDp[i] = cht.query(sum[i]) + sum[i] * sum[i];
            }
        }
        dp = newDp;
    }
    
    return dp[n];
}

int main() {
    std::vector<int> arr = {1, 3, 2, 4, 1, 5};
    int k = 3;
    
    std::cout << "Min cost to partition into " << k << " groups: " 
              << solve(arr, k) << "\n";
    
    return 0;
}
```

---

## 59.6 DP State Design Principles

Choosing the right DP state is the most critical skill. Here's a systematic approach.

### The State Design Checklist

```
1. What information do I need to make the next decision?
2. Can I identify the "current position" in the problem?
3. What constraints exist? (Each constraint may add a dimension)
4. Can I reduce dimensions? (Is some information derivable from others?)
5. Is the state space polynomial? If not, can I use bitmask/other tricks?
```

### State Design Patterns

| Pattern | State | Example |
|---|---|---|
| Linear sequence | `dp[i]` = best for prefix [0..i] | LIS, maximum subarray |
| Two sequences | `dp[i][j]` = best for prefixes | LCS, edit distance |
| Knapsack | `dp[i][w]` = best value with capacity w | 0/1 knapsack |
| Interval | `dp[l][r]` = best for subarray [l..r] | Matrix chain, palindrome |
| Tree | `dp[u][state]` = best for subtree | Tree coloring |
| Bitmask | `dp[mask]` = best for visited set | TSP, Hamiltonian path |
| Profile | `dp[i][profile]` = best for row i | Tiling problems |
| Probability | `dp[state]` = expected value/probability | Random processes |

### How to Derive the State

**Step 1**: Identify the subproblem
- "What is the answer for a smaller version of the problem?"

**Step 2**: Choose the "free variable"
- What changes as we solve subproblems? (Index, capacity, count, etc.)

**Step 3**: Verify optimal substructure
- Can the optimal solution be built from optimal sub-solutions?

**Step 4**: Verify overlapping subproblems
- Do the same subproblems appear in multiple solutions?

**Step 5**: Count states
- Is the number of states polynomial? If not, reconsider.

### Common Mistakes

| Mistake | Example | Fix |
|---|---|---|
| State too small | `dp[i]` for two-sequence problem | Add dimension: `dp[i][j]` |
| State too large | `dp[i][j][k]` when `k` is derivable | Remove redundant dimension |
| Missing dimension | Forgetting "remaining capacity" | Add constraint as dimension |
| Wrong transition | Not considering all choices | Enumerate all possibilities |

---

## 59.7 Transition Design

### How to Derive Recurrence Relations

**Step 1**: Define the state clearly
```
dp[x] = optimal answer for subproblem x
```

**Step 2**: Identify the "last decision"
- What is the last choice that leads to the optimal solution?

**Step 3**: Enumerate all possible last decisions
```
dp[x] = optimal over all choices c:
    cost(c) + dp[previous_state(c)]
```

**Step 4**: Handle base cases

### Example: Deriving LCS Recurrence

```
State: dp[i][j] = LCS of s1[0..i-1] and s2[0..j-1]

Last decision: What to do with s1[i-1] and s2[j-1]?

Options:
1. Skip s1[i-1]: dp[i][j] = dp[i-1][j]
2. Skip s2[j-1]: dp[i][j] = dp[i][j-1]
3. Match s1[i-1] = s2[j-1]: dp[i][j] = dp[i-1][j-1] + 1

Recurrence:
dp[i][j] = max(dp[i-1][j], dp[i][j-1], dp[i-1][j-1] + 1 if s1[i-1]==s2[j-1])
```

### Transition Design Patterns

| Pattern | Transition | Example |
|---|---|---|
| Take or skip | `dp[i] = max(skip, take)` | Knapsack |
| Extend or restart | `dp[i] = max(dp[i-1]+a[i], a[i])` | Max subarray |
| Match or mismatch | `dp[i][j] = max(skip1, skip2, match)` | LCS |
| Split point | `dp[l][r] = min over k: dp[l][k] + dp[k+1][r] + cost` | Matrix chain |
| Add element | `dp[i] = best(dp[j] + transition(j,i))` | LIS |

---

## 59.8 Space Optimization

### Rolling Array (Space: O(n) → O(1) or O(W))

When the DP only depends on the previous row, we can reduce space from O(n×m) to O(m).

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Classic 0/1 Knapsack with space optimization
int knapsackOptimized(const std::vector<int>& weights, 
                       const std::vector<int>& values, int capacity) {
    int n = weights.size();
    std::vector<int> dp(capacity + 1, 0);
    
    for (int i = 0; i < n; i++) {
        // Traverse backwards to avoid using the same item twice
        for (int w = capacity; w >= weights[i]; w--) {
            dp[w] = std::max(dp[w], dp[w - weights[i]] + values[i]);
        }
    }
    
    return dp[capacity];
}

// LCS with O(min(n,m)) space
int lcsOptimized(const std::string& s1, const std::string& s2) {
    int n = s1.size(), m = s2.size();
    if (n < m) return lcsOptimized(s2, s1); // Ensure m is smaller
    
    std::vector<int> prev(m + 1, 0), curr(m + 1, 0);
    
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            if (s1[i-1] == s2[j-1]) {
                curr[j] = prev[j-1] + 1;
            } else {
                curr[j] = std::max(prev[j], curr[j-1]);
            }
        }
        std::swap(prev, curr);
        std::fill(curr.begin(), curr.end(), 0);
    }
    
    return prev[m];
}

int main() {
    // Knapsack
    std::vector<int> w = {2, 3, 4, 5};
    std::vector<int> v = {3, 4, 5, 6};
    std::cout << "Knapsack: " << knapsackOptimized(w, v, 8) << "\n";
    
    // LCS
    std::cout << "LCS: " << lcsOptimized("ABCBDAB", "BDCAB") << "\n";
    
    return 0;
}
```

### Hirschberg's Technique (Space: O(n) with full reconstruction)

Hirschberg's algorithm computes LCS (and similar DP) in O(n×m) time but only O(min(n,m)) space, while still recovering the full optimal solution.

**Key idea**: Divide and conquer. Find the optimal split point in the middle row using forward and backward DP, then recurse on both halves.

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

class Hirschberg {
    static std::vector<int> lcsRow(const std::string& s1, const std::string& s2) {
        int n = s1.size(), m = s2.size();
        std::vector<int> prev(m + 1, 0), curr(m + 1, 0);
        
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= m; j++) {
                if (s1[i-1] == s2[j-1]) curr[j] = prev[j-1] + 1;
                else curr[j] = std::max(prev[j], curr[j-1]);
            }
            std::swap(prev, curr);
            std::fill(curr.begin(), curr.end(), 0);
        }
        return prev;
    }
    
    static std::vector<int> lcsRowReverse(const std::string& s1, const std::string& s2) {
        std::string r1(s1.rbegin(), s1.rend());
        std::string r2(s2.rbegin(), s2.rend());
        auto row = lcsRow(r1, r2);
        std::reverse(row.begin(), row.end());
        return row;
    }
    
public:
    static std::string solve(const std::string& s1, const std::string& s2) {
        int n = s1.size(), m = s2.size();
        
        if (n == 0) return "";
        if (m == 0) return "";
        if (n == 1) {
            if (s2.find(s1[0]) != std::string::npos) return s1;
            return "";
        }
        
        int mid = n / 2;
        
        // Forward DP for s1[0..mid-1]
        auto fwd = lcsRow(s1.substr(0, mid), s2);
        // Backward DP for s1[mid..n-1]
        auto bwd = lcsRowReverse(s1.substr(mid), s2);
        
        // Find best split point in s2
        int bestJ = 0;
        int bestSum = 0;
        for (int j = 0; j <= m; j++) {
            if (fwd[j] + bwd[j] > bestSum) {
                bestSum = fwd[j] + bwd[j];
                bestJ = j;
            }
        }
        
        // Recurse on both halves
        auto left = solve(s1.substr(0, mid), s2.substr(0, bestJ));
        auto right = solve(s1.substr(mid), s2.substr(bestJ));
        
        return left + right;
    }
};

int main() {
    std::string s1 = "ABCBDAB";
    std::string s2 = "BDCAB";
    
    std::string lcs = Hirschberg::solve(s1, s2);
    std::cout << "LCS of \"" << s1 << "\" and \"" << s2 << "\": \"" 
              << lcs << "\" (length " << lcs.size() << ")\n";
    
    return 0;
}
```

### Space Optimization Summary

| Technique | Space Reduction | Trade-off |
|---|---|---|
| Rolling array | O(n×m) → O(m) | Cannot reconstruct solution |
| Hirschberg | O(n×m) → O(m) | 2× time, can reconstruct |
| Divide & conquer | O(n²) → O(n) | 2× time |
| In-place | Various | Problem-specific |

---

## 59.9 DP Debugging

### How to Debug a Wrong DP

**Step 1: Verify the Recurrence**
- Write out the recurrence on paper
- Check base cases
- Verify with small examples by hand

**Step 2: Print the DP Table**
```cpp
void printDP(const std::vector<std::vector<int>>& dp) {
    for (int i = 0; i < dp.size(); i++) {
        for (int j = 0; j < dp[i].size(); j++) {
            std::cout << dp[i][j] << "\t";
        }
        std::cout << "\n";
    }
}
```

**Step 3: Check Iteration Order**
- Ensure dependencies are computed before they're used
- Forward DP: compute dp[i] after dp[i-1]
- Backward DP: compute dp[i] after dp[i+1]
- Interval DP: iterate by increasing length

**Step 4: Check for Off-by-One Errors**
- 0-indexed vs 1-indexed
- Inclusive vs exclusive boundaries
- Size vs last index

**Step 5: Compare with Brute Force**
```cpp
// Generate all small test cases
// Compare DP answer with brute force answer
for (int mask = 0; mask < (1 << n); mask++) {
    int bruteForce = solveByEnumeration(mask);
    int dpAnswer = solveByDP(mask);
    if (bruteForce != dpAnswer) {
        std::cout << "Mismatch for mask " << mask << ": " 
                  << bruteForce << " vs " << dpAnswer << "\n";
    }
}
```

### Common DP Bugs

| Bug | Symptom | Fix |
|---|---|---|
| Wrong base case | Wrong answer for small inputs | Check n=0, n=1 cases |
| Wrong iteration order | Dependencies not yet computed | Check which dp values are needed |
| Integer overflow | Negative or wrong large answers | Use long long |
| Off-by-one | Wrong answer, close to correct | Check indices carefully |
| Missing state | Wrong answer for some cases | Check if state captures all info |
| Wrong transition | Optimal substructure violated | Verify recurrence derivation |
| Space optimization bug | Different answer with rolling array | Check if you need the old value |

### Debugging Template

```cpp
#include <iostream>
#include <vector>
#include <cassert>

// Add these checks to your DP solution:

// 1. Assert base cases
void checkBaseCases() {
    // dp[0] should be ...
    // dp[1] should be ...
    assert(dp[0] == expectedValue0);
    assert(dp[1] == expectedValue1);
}

// 2. Assert monotonicity (if applicable)
void checkMonotonicity(const std::vector<int>& dp) {
    for (int i = 1; i < dp.size(); i++) {
        // If dp should be non-decreasing:
        assert(dp[i] >= dp[i-1]);
    }
}

// 3. Assert that each transition improves the answer
void checkTransition(int i, int j, int oldVal, int newVal) {
    if (newVal > oldVal) { // For maximization
        std::cout << "Improvement at dp[" << i << "] via j=" << j 
                  << ": " << oldVal << " -> " << newVal << "\n";
    }
}

int main() {
    // Example: verify LIS DP
    std::vector<int> arr = {10, 9, 2, 5, 3, 7, 101, 18};
    int n = arr.size();
    
    std::vector<int> dp(n, 1);
    for (int i = 1; i < n; i++) {
        for (int j = 0; j < i; j++) {
            if (arr[j] < arr[i]) {
                dp[i] = std::max(dp[i], dp[j] + 1);
            }
        }
    }
    
    int lis = *std::max_element(dp.begin(), dp.end());
    std::cout << "LIS length: " << lis << "\n"; // Should be 4
    
    // Verify: LIS should be [2, 3, 7, 101] or [2, 5, 7, 101] etc.
    
    return 0;
}
```

---

## Summary

| Technique | Key Insight | When to Use |
|---|---|---|
| Probability DP | States are outcomes, transitions weighted by probability | Expected value, win probability |
| Game DP | Grundy numbers, XOR of independent games | Nim, impartial games |
| Broken Profile | Profile = boundary state of tiling | Grid tiling problems |
| Aliens Trick | Penalize segments, binary search on penalty | Exactly K segments |
| Slope Optimization | Convex hull of linear transitions | DP with linear transitions |
| State Design | "What info do I need for next decision?" | Every DP problem |
| Transition Design | "What is the last decision?" | Every DP problem |
| Rolling Array | Only keep current and previous row | Space optimization |
| Hirschberg | Divide and conquer for reconstruction | LCS with linear space |
| DP Debugging | Print table, compare with brute force | When DP gives wrong answer |
