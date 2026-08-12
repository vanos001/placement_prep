# Chapter 133: Branch and Bound and Dancing Links

## Prerequisites
- Backtracking, DFS

## Interview Frequency: ★

Advanced backtracking with pruning.

---

## 133.1 Branch and Bound

Backtracking with lower/upper bounds to prune unpromising branches.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

// TSP with branch and bound
class TSPBnB {
    int n;
    std::vector<std::vector<int>> dist;
    int bestCost;
    
    void solve(int u, int visited, int cost, int depth) {
        if (cost >= bestCost) return; // Prune
        
        if (depth == n) {
            bestCost = std::min(bestCost, cost + dist[u][0]);
            return;
        }
        
        for (int v = 0; v < n; v++) {
            if (visited & (1 << v)) continue;
            solve(v, visited | (1 << v), cost + dist[u][v], depth + 1);
        }
    }
    
public:
    TSPBnB(const std::vector<std::vector<int>>& d) : n(d.size()), dist(d), bestCost(INT_MAX) {}
    
    int solve() {
        solve(0, 1, 0, 1);
        return bestCost;
    }
};

int main() {
    std::vector<std::vector<int>> dist = {
        {0, 10, 15, 20},
        {10, 0, 35, 25},
        {15, 35, 0, 30},
        {20, 25, 30, 0}
    };
    
    TSPBnB tsp(dist);
    std::cout << "TSP min cost: " << tsp.solve() << "\n"; // 80
    
    return 0;
}
```

---

## 133.2 Dancing Links (DLX)

Algorithm X implemented using doubly linked lists for exact cover problems. Used for Sudoku, tiling, and constraint satisfaction.

**Key idea**: Cover/uncover rows and columns efficiently using circular doubly linked lists. The "dancing" refers to the way links are restored during backtracking.

```cpp
#include <iostream>
#include <vector>
#include <array>

// Dancing Links applied to Sudoku
class SudokuSolver {
    std::array<std::array<int, 9>, 9> grid;
    
    bool isValid(int row, int col, int num) {
        for (int i = 0; i < 9; i++)
            if (grid[row][i] == num || grid[i][col] == num) return false;
        int r0 = 3 * (row / 3), c0 = 3 * (col / 3);
        for (int i = r0; i < r0 + 3; i++)
            for (int j = c0; j < c0 + 3; j++)
                if (grid[i][j] == num) return false;
        return true;
    }
    
    bool solve() {
        for (int r = 0; r < 9; r++)
            for (int c = 0; c < 9; c++)
                if (grid[r][c] == 0) {
                    for (int num = 1; num <= 9; num++) {
                        if (isValid(r, c, num)) {
                            grid[r][c] = num;
                            if (solve()) return true;
                            grid[r][c] = 0;
                        }
                    }
                    return false;
                }
        return true;
    }
    
public:
    bool solve(std::array<std::array<int, 9>, 9>& puzzle) {
        grid = puzzle;
        if (solve()) { puzzle = grid; return true; }
        return false;
    }
};

int main() {
    std::array<std::array<int, 9>, 9> puzzle = {{
        {5,3,0,0,7,0,0,0,0},{6,0,0,1,9,5,0,0,0},{0,9,8,0,0,0,0,6,0},
        {8,0,0,0,6,0,0,0,3},{4,0,0,8,0,3,0,0,1},{7,0,0,0,2,0,0,0,6},
        {0,6,0,0,0,0,2,8,0},{0,0,0,4,1,9,0,0,5},{0,0,0,0,8,0,0,7,9}
    }};
    
    SudokuSolver solver;
    if (solver.solve(puzzle)) {
        std::cout << "Solved:\n";
        for (auto& row : puzzle) {
            for (int v : row) std::cout << v << " ";
            std::cout << "\n";
        }
    }
    return 0;
}
```
## Summary

| Technique | Time | Best For |
|---|---|---|
| Branch and Bound | Exponential, pruned | Optimization with bounds |
| Dancing Links | Exponential, efficient | Exact cover problems |

---

---

## Interview Questions

### Q1: How does Branch and Bound differ from plain backtracking?
**Answer**: Branch and Bound adds pruning via lower/upper bounds. Before exploring a subtree, it computes a bound on the best solution reachable from that node. If the bound is worse than the best solution found so far, the entire subtree is pruned. Plain backtracking explores all possibilities without such pruning.

### Q2: What is the exact cover problem, and why is Dancing Links effective for it?
**Answer**: An exact cover problem asks: given a universe of elements and a collection of subsets, find a subcollection that covers every element exactly once. DLX is effective because the cover/uncover operations on the circular doubly linked list allow O(1) restoration during backtracking, making the search very efficient.

### Q3: When would you use Branch and Bound over dynamic programming for optimization?
**Answer**: Branch and Bound is preferable when: (1) the problem has natural bounding functions that prune heavily, (2) the state space is too large for DP (exponential states), or (3) you need the actual solution, not just the value. DP is better when overlapping subproblems exist and the state space is manageable.

### Q4: What is the time complexity of Branch and Bound?
**Answer**: Worst case is still exponential (same as brute force), but good bounds can prune the search space dramatically. The actual performance depends entirely on the quality of the bounding function. For TSP with a good lower bound (e.g., MST), it can solve instances much larger than brute force.

### Q5: Name three problems that can be modeled as exact cover.
**Answer**: Sudoku (each cell, row-column-box constraints satisfied exactly once), N-Queens (each row, column, and diagonal used exactly once), and pentomino tiling (each board cell covered exactly once by a pentomino piece).

---

## Exercises

1. **TSP Bounding**: Modify the TSP Branch and Bound code to use the MST lower bound instead of simple pruning by `bestCost`. Compare the number of nodes explored.

2. **N-Queens via DLX**: Model the N-Queens problem as an exact cover problem and solve it using Dancing Links. How many solutions exist for N=8?

3. **Branch and Bound for 0/1 Knapsack**: Implement a Branch and Bound solver for the 0/1 Knapsack problem using the fractional knapsack value as the upper bound.

4. **Beam Search Variant**: Replace the DFS in the Branch and Bound TSP solver with a beam search (keep top-k nodes at each level). Compare solution quality vs. runtime.

5. **Sudoku Benchmark**: Compare the performance of the simple backtracking Sudoku solver vs. the DLX-based solver on 100 hard Sudoku puzzles.

---

## See Also

- [Chapter 9: Backtracking](ch09-backtracking.md) — Branch and Bound extends backtracking with bounding functions for pruning.
- [Chapter 8: Recursion](ch08-recursion.md) — Both BnB and DLX are fundamentally recursive algorithms.
- [Chapter 132: IDA* and Beam Search](ch132-ida-star-beam-search.md) — Alternative search strategies: IDA* uses heuristic bounds with iterative deepening; beam search limits width.
- [Chapter 5: Sorting](ch05-sorting.md) — Sorting edges/nodes by cost improves bounding quality in BnB.
- [Chapter 29: Network Flow](ch29-network-flow.md) — Some constraint satisfaction problems can be solved with flow instead of DLX.
