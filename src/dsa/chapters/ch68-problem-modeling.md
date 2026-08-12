# Chapter 68: Problem Modeling and Abstraction

## Prerequisites

- Algorithmic thinking (Chapter 67)
- Basic graph theory
- Basic DP

## Interview Frequency: ★★★★★

Problem modeling is the skill of translating a real-world or abstract problem into a formal computational model. This is tested implicitly in every interview—**Google**, **Meta**, and **Amazon** especially value candidates who can clearly model problems before coding.

| Skill | Frequency | Difficulty | Notes |
|---|---|---|---|
| Graph modeling | ★★★★★ | Medium | Entities as nodes, relations as edges |
| State modeling | ★★★★ | Medium-Hard | For DP, BFS on states |
| Constraint modeling | ★★★★ | Medium | Identifying what limits the solution |
| Mathematical modeling | ★★★ | Medium | Formulating as math problem |

---

## 68.1 Graph Modeling

Many problems that don't look like graph problems can be modeled as graphs.

### Modeling Checklist

```
□ What are the entities? → Nodes
□ What are the relationships? → Edges
□ What are we looking for? → Path, connectivity, coloring, matching
□ Is the graph weighted? → Dijkstra, Bellman-Ford
□ Is the graph directed? → Topological sort, SCC
□ Are there constraints? → Capacity (flow), color (coloring)
```

### Classic Modeling Examples

| Problem | Nodes | Edges | Algorithm |
|---|---|---|---|
| Word Ladder | Words | Differ by 1 letter | BFS |
| Course Schedule | Courses | Prerequisites | Topological sort |
| Social Network | People | Friendships | BFS for distance |
| Task Scheduling | Tasks | Dependencies | Topological sort |
| Sudoku | Cells | Constraints | Backtracking |
| Rubik's Cube | States | Moves | BFS for shortest |
| Maze | Cells | Adjacent cells | BFS/DFS |

### Example: Course Schedule

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

// Model: Courses = nodes, prerequisites = directed edges
// Question: Can we finish all courses? → Is the graph a DAG?
// Algorithm: Topological sort (if possible, no cycle)

bool canFinish(int numCourses, std::vector<std::vector<int>>& prerequisites) {
    std::vector<std::vector<int>> adj(numCourses);
    std::vector<int> inDegree(numCourses, 0);
    
    for (auto& pre : prerequisites) {
        adj[pre[1]].push_back(pre[0]);
        inDegree[pre[0]]++;
    }
    
    std::queue<int> q;
    for (int i = 0; i < numCourses; i++) {
        if (inDegree[i] == 0) q.push(i);
    }
    
    int count = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        count++;
        for (int v : adj[u]) {
            if (--inDegree[v] == 0) q.push(v);
        }
    }
    
    return count == numCourses;
}

int main() {
    std::vector<std::vector<int>> prereqs1 = {{1, 0}, {0, 1}};
    std::cout << "Can finish (cycle): " << canFinish(2, prereqs1) << "\n";
    
    std::vector<std::vector<int>> prereqs2 = {{1, 0}, {2, 0}, {3, 1}, {3, 2}};
    std::cout << "Can finish (DAG): " << canFinish(4, prereqs2) << "\n";
    
    return 0;
}
```

---

## 68.2 State Modeling for DP

The key to DP is choosing the right state representation.

### State Design Process

```
1. What information do I need to make the next decision?
2. Can I represent this as a tuple of integers?
3. How many possible states are there? (Must be polynomial)
4. Can I reduce the state space?
```

### State Design Patterns

| Pattern | State | Example |
|---|---|---|
| Position | `dp[i]` | LIS, max subarray |
| Position + capacity | `dp[i][w]` | Knapsack |
| Two positions | `dp[i][j]` | LCS, edit distance |
| Interval | `dp[l][r]` | Matrix chain |
| Bitmask | `dp[mask]` | TSP |
| Profile | `dp[row][profile]` | Tiling |
| Tree node + state | `dp[u][color]` | Tree coloring |

### Example: Minimum Cost to Climb Stairs

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Model: dp[i] = minimum cost to reach step i
// Transition: dp[i] = cost[i] + min(dp[i-1], dp[i-2])
// Base: dp[0] = cost[0], dp[1] = cost[1]

int minCostClimbingStairs(const std::vector<int>& cost) {
    int n = cost.size();
    if (n <= 1) return 0;
    
    std::vector<int> dp(n);
    dp[0] = cost[0];
    dp[1] = cost[1];
    
    for (int i = 2; i < n; i++) {
        dp[i] = cost[i] + std::min(dp[i-1], dp[i-2]);
    }
    
    return std::min(dp[n-1], dp[n-2]);
}

int main() {
    std::vector<int> cost = {10, 15, 20};
    std::cout << "Min cost: " << minCostClimbingStairs(cost) << "\n";
    
    std::vector<int> cost2 = {1, 100, 1, 1, 1, 100, 1, 1, 100, 1};
    std::cout << "Min cost: " << minCostClimbingStairs(cost2) << "\n";
    
    return 0;
}
```

---

## 68.3 Constraint Modeling

Understanding constraints tells you what algorithm to use.

### Constraint Types

| Constraint | Implication | Technique |
|---|---|---|
| n ≤ 20 | Exponential OK | Bitmask, backtracking |
| n ≤ 500 | O(n³) OK | Floyd-Warshall, matrix chain |
| n ≤ 10^5 | O(n log n) needed | Sorting, divide & conquer |
| n ≤ 10^7 | O(n) needed | Linear scan, hash map |
| Sum ≤ 10^5 | DP on sum | Knapsack-like |
| Answer ≤ 10^9 | Binary search on answer | Parametric search |
| Graph is tree | n-1 edges, no cycles | Tree DP, LCA |
| Graph is DAG | No cycles | Topological sort |

---

## 68.4 Mathematical Modeling

Some problems are best solved by translating to mathematical formulations.

### Example: Maximum Product Subarray

**Problem**: Find the contiguous subarray with the maximum product.

**Mathematical insight**: Track both maximum AND minimum products (negative × negative = positive).

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int maxProduct(const std::vector<int>& arr) {
    int n = arr.size();
    int maxProd = arr[0];
    int currMax = arr[0];
    int currMin = arr[0];
    
    for (int i = 1; i < n; i++) {
        // If arr[i] is negative, swap max and min
        if (arr[i] < 0) std::swap(currMax, currMin);
        
        currMax = std::max(arr[i], currMax * arr[i]);
        currMin = std::min(arr[i], currMin * arr[i]);
        
        maxProd = std::max(maxProd, currMax);
    }
    
    return maxProd;
}

int main() {
    std::vector<int> arr = {2, 3, -2, 4};
    std::cout << "Max product: " << maxProduct(arr) << "\n";
    
    std::vector<int> arr2 = {-2, 0, -1};
    std::cout << "Max product: " << maxProduct(arr2) << "\n";
    
    return 0;
}
```

---

## 68.5 Implicit vs Explicit Graphs

Many problems involve **implicit graphs** where the graph structure is defined by rules rather than given explicitly.

| Problem | Explicit Graph? | Implicit Graph |
|---|---|---|
| Social network | Yes | — |
| Word ladder | No | Words connected if differ by 1 |
| Sudoku | No | States connected by valid moves |
| Rubik's cube | No | States connected by rotations |
| 8-puzzle | No | States connected by sliding tiles |

### Example: 8-Puzzle (BFS on Implicit Graph)

```cpp
#include <iostream>
#include <queue>
#include <unordered_set>
#include <string>
#include <algorithm>

// Model: Each board state is a node, valid moves are edges
// Find shortest path from initial to goal state

int solvePuzzle(std::string start, std::string goal = "123456780") {
    if (start == goal) return 0;
    
    std::queue<std::pair<std::string, int>> q;
    std::unordered_set<std::string> visited;
    
    q.push({start, 0});
    visited.insert(start);
    
    int dx[] = {0, 0, 1, -1};
    int dy[] = {1, -1, 0, 0};
    
    while (!q.empty()) {
        auto [state, dist] = q.front();
        q.pop();
        
        int zeroPos = state.find('0');
        int zx = zeroPos / 3, zy = zeroPos % 3;
        
        for (int d = 0; d < 4; d++) {
            int nx = zx + dx[d], ny = zy + dy[d];
            if (nx < 0 || nx >= 3 || ny < 0 || ny >= 3) continue;
            
            std::string next = state;
            std::swap(next[zx * 3 + zy], next[nx * 3 + ny]);
            
            if (next == goal) return dist + 1;
            if (!visited.count(next)) {
                visited.insert(next);
                q.push({next, dist + 1});
            }
        }
    }
    
    return -1; // Unsolvable
}

int main() {
    std::string start = "123405678";
    int moves = solvePuzzle(start);
    std::cout << "Minimum moves: " << moves << "\n";
    
    return 0;
}
```

---

## Summary

| Modeling Type | Key Question | Result |
|---|---|---|
| Graph | What are nodes and edges? | BFS, DFS, Dijkstra |
| State | What info needed for decisions? | DP state |
| Constraint | What limits the solution? | Complexity budget |
| Mathematical | Can I formulate as math? | Direct computation |
| Implicit | Is the graph defined by rules? | BFS on state space |
