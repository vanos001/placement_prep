# Chapter 9: Backtracking

Backtracking is a systematic method for solving constraint satisfaction problems. It is essentially recursion with the ability to "undo" choices — when a partial solution is found to be invalid, the algorithm backtracks to a previous state and tries a different path. Backtracking is one of the most frequently tested topics in coding interviews, appearing in problems involving combinations, permutations, subsets, and constraint satisfaction.

---

## 9.1 The Backtracking Framework

### The Core Idea

Backtracking explores the **state space tree** — a tree where each node represents a partial solution and each branch represents a choice. The algorithm:

1. **Makes a choice** at the current state
2. **Recursively explores** the consequences of that choice
3. **Undoes the choice** (backtracks) to explore other alternatives

This is often called the **choose-explore-unchoose** pattern.

### The Template

```
function backtrack(state, choices):
    if state is a complete solution:
        record/process state
        return
    
    for each choice in choices:
        if choice is valid given current state:
            apply choice to state        // CHOOSE
            backtrack(state, new choices) // EXPLORE
            undo choice from state       // UNCHOOSE
```

### State Space Tree

Consider generating all subsets of {1, 2, 3}:

```
                        []
                   /          \
            include 1        exclude 1
              /                    \
           [1]                     []
          /    \                /      \
    inc 2   exc 2          inc 2     exc 2
      /        \             /          \
   [1,2]      [1]         [2]          []
   /   \      / \         / \          / \
 inc3 exc3 inc3 exc3   inc3 exc3   inc3 exc3
  /     \    /    \      /    \       /    \
[1,2,3][1,2][1,3] [1] [2,3] [2]   [3]    []
```

Each path from root to leaf represents one subset. Backtracking explores this tree depth-first, pruning branches when a choice is invalid.

### When to Use Backtracking

| Problem Type | Examples |
|-------------|----------|
| **Generate all combinations** | Subsets, combinations |
| **Generate all orderings** | Permutations |
| **Constraint satisfaction** | N-Queens, Sudoku |
| **Path finding** | Word search, maze solving |
| **Game solving** | Solving puzzles |

---

## 9.2 Subsets

### Problem: Generate All Subsets

Given a set of distinct integers, return all possible subsets.

**Approach: Brute Force**

The brute force approach would be to generate all \\(2^n\\) possible combinations by iterating through binary representations:

```cpp
#include <iostream>
#include <vector>

// Brute force using bit manipulation
// Time: O(n * 2^n), Space: O(n * 2^n)
std::vector<std::vector<int>> subsetsBruteForce(const std::vector<int>& nums) {
    int n = nums.size();
    std::vector<std::vector<int>> result;
    
    for (int mask = 0; mask < (1 << n); ++mask) {
        std::vector<int> subset;
        for (int i = 0; i < n; ++i) {
            if (mask & (1 << i)) {
                subset.push_back(nums[i]);
            }
        }
        result.push_back(subset);
    }
    return result;
}
```

**Approach: Backtracking**

```cpp
#include <iostream>
#include <vector>

// Backtracking approach
// Time: O(n * 2^n), Space: O(n) recursion depth
void subsetsBacktrack(const std::vector<int>& nums, int start,
                      std::vector<int>& current,
                      std::vector<std::vector<int>>& result) {
    // Every state is a valid subset — record it
    result.push_back(current);
    
    for (int i = start; i < nums.size(); ++i) {
        // CHOOSE: include nums[i]
        current.push_back(nums[i]);
        
        // EXPLORE: generate subsets starting from i+1
        subsetsBacktrack(nums, i + 1, current, result);
        
        // UNCHOOSE: remove nums[i]
        current.pop_back();
    }
}

std::vector<std::vector<int>> subsets(const std::vector<int>& nums) {
    std::vector<std::vector<int>> result;
    std::vector<int> current;
    subsetsBacktrack(nums, 0, current, result);
    return result;
}

int main() {
    std::vector<int> nums = {1, 2, 3};
    auto result = subsets(nums);
    
    std::cout << "All subsets:\n";
    for (const auto& subset : result) {
        std::cout << "{ ";
        for (int v : subset) std::cout << v << " ";
        std::cout << "}\n";
    }
    return 0;
}
```

**Dry Run:**

```
Call: backtrack(nums, start=0, current=[])
  result: [[]]
  i=0: current=[1]
    Call: backtrack(nums, start=1, current=[1])
      result: [[], [1]]
      i=1: current=[1,2]
        Call: backtrack(nums, start=2, current=[1,2])
          result: [[], [1], [1,2]]
          i=2: current=[1,2,3]
            Call: backtrack(nums, start=3, current=[1,2,3])
              result: [[], [1], [1,2], [1,2,3]]
            current=[1,2]
          (i loop ends)
        current=[1]
      i=2: current=[1,3]
        Call: backtrack(nums, start=3, current=[1,3])
          result: [[], [1], [1,2], [1,2,3], [1,3]]
        current=[1]
      (i loop ends)
    current=[]
  i=1: current=[2]
    ... (similar pattern)
```

### Subsets II: With Duplicates

When the input may contain duplicates, we must avoid generating duplicate subsets.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Subsets with duplicates
// Key: sort the array, skip duplicates at the same recursion level
void subsetsWithDup(std::vector<int>& nums, int start,
                    std::vector<int>& current,
                    std::vector<std::vector<int>>& result) {
    result.push_back(current);
    
    for (int i = start; i < nums.size(); ++i) {
        // Skip duplicates: if nums[i] == nums[i-1] and i > start,
        // we've already explored this branch at this level
        if (i > start && nums[i] == nums[i - 1]) continue;
        
        current.push_back(nums[i]);
        subsetsWithDup(nums, i + 1, current, result);
        current.pop_back();
    }
}

std::vector<std::vector<int>> subsetsWithDup(std::vector<int>& nums) {
    std::sort(nums.begin(), nums.end());
    std::vector<std::vector<int>> result;
    std::vector<int> current;
    subsetsWithDup(nums, 0, current, result);
    return result;
}

int main() {
    std::vector<int> nums = {1, 2, 2};
    auto result = subsetsWithDup(nums);
    
    std::cout << "Subsets with duplicates:\n";
    for (const auto& subset : result) {
        std::cout << "{ ";
        for (int v : subset) std::cout << v << " ";
        std::cout << "}\n";
    }
    // Output: {}, {1}, {1,2}, {1,2,2}, {2}, {2,2}
    return 0;
}
```

---

## 9.3 Permutations

### Problem: Generate All Permutations

Given a collection of distinct integers, return all possible permutations.

**Approach: Brute Force**

Generate all arrangements by selecting elements one by one:

```cpp
#include <iostream>
#include <vector>

// Brute force: try every position for every element
// Uses a visited array to track which elements are in the current permutation
void permuteBruteForce(const std::vector<int>& nums,
                       std::vector<bool>& used,
                       std::vector<int>& current,
                       std::vector<std::vector<int>>& result) {
    if (current.size() == nums.size()) {
        result.push_back(current);
        return;
    }
    for (int i = 0; i < nums.size(); ++i) {
        if (used[i]) continue;
        used[i] = true;
        current.push_back(nums[i]);
        permuteBruteForce(nums, used, current, result);
        current.pop_back();
        used[i] = false;
    }
}
```

**Approach: Backtracking with Swapping**

A more elegant approach swaps elements in place:

```cpp
#include <iostream>
#include <vector>

// Backtracking using swap
// Time: O(n! * n), Space: O(n) recursion depth
void permute(std::vector<int>& nums, int start,
             std::vector<std::vector<int>>& result) {
    if (start == nums.size()) {
        result.push_back(nums);
        return;
    }
    for (int i = start; i < nums.size(); ++i) {
        std::swap(nums[start], nums[i]);     // CHOOSE
        permute(nums, start + 1, result);     // EXPLORE
        std::swap(nums[start], nums[i]);     // UNCHOOSE
    }
}

std::vector<std::vector<int>> permute(std::vector<int>& nums) {
    std::vector<std::vector<int>> result;
    permute(nums, 0, result);
    return result;
}

int main() {
    std::vector<int> nums = {1, 2, 3};
    auto result = permute(nums);
    
    std::cout << "All permutations:\n";
    for (const auto& perm : result) {
        for (int v : perm) std::cout << v << " ";
        std::cout << "\n";
    }
    // Output: 123, 132, 213, 231, 321, 312
    return 0;
}
```

**Dry Run for `permute([1,2,3], start=0)`:**

```
permute([1,2,3], start=0)
  i=0: swap(0,0) → [1,2,3]
    permute([1,2,3], start=1)
      i=1: swap(1,1) → [1,2,3]
        permute([1,2,3], start=2) → record [1,2,3]
      i=2: swap(1,2) → [1,3,2]
        permute([1,3,2], start=2) → record [1,3,2]
        swap(1,2) → [1,2,3]
    swap(0,0) → [1,2,3]
  i=1: swap(0,1) → [2,1,3]
    permute([2,1,3], start=1)
      i=1: swap(1,1) → [2,1,3]
        permute([2,1,3], start=2) → record [2,1,3]
      i=2: swap(1,2) → [2,3,1]
        permute([2,3,1], start=2) → record [2,3,1]
        swap(1,2) → [2,1,3]
    swap(0,1) → [1,2,3]
  i=2: swap(0,2) → [3,2,1]
    ... (similar pattern)
    swap(0,2) → [1,2,3]
```

### Permutations II: With Duplicates

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

// Permutations with duplicates — avoid generating duplicate permutations
void permuteUnique(std::vector<int>& nums, int start,
                   std::vector<std::vector<int>>& result) {
    if (start == nums.size()) {
        result.push_back(nums);
        return;
    }
    // Use a set to track which values we've placed at position 'start'
    std::vector<bool> used(21, false); // assuming values in [-10, 10]
    for (int i = start; i < nums.size(); ++i) {
        // Skip if we've already placed the same value at this position
        if (used[nums[i] + 10]) continue;
        used[nums[i] + 10] = true;
        
        std::swap(nums[start], nums[i]);
        permuteUnique(nums, start + 1, result);
        std::swap(nums[start], nums[i]);
    }
}

// Alternative: sort and use index-based duplicate check
void permuteUniqueV2(std::vector<int>& nums, int start,
                     std::vector<std::vector<int>>& result) {
    if (start == nums.size()) {
        result.push_back(nums);
        return;
    }
    for (int i = start; i < nums.size(); ++i) {
        // Skip duplicates: if nums[i] == nums[j] for some j in [start, i)
        bool skip = false;
        for (int j = start; j < i; ++j) {
            if (nums[j] == nums[i]) {
                skip = true;
                break;
            }
        }
        if (skip) continue;
        
        std::swap(nums[start], nums[i]);
        permuteUniqueV2(nums, start + 1, result);
        std::swap(nums[start], nums[i]);
    }
}

int main() {
    std::vector<int> nums = {1, 1, 2};
    std::vector<std::vector<int>> result;
    permuteUniqueV2(nums, 0, result);
    
    std::cout << "Unique permutations:\n";
    for (const auto& perm : result) {
        for (int v : perm) std::cout << v << " ";
        std::cout << "\n";
    }
    // Output: 1 1 2, 1 2 1, 2 1 1
    return 0;
}
```

---

## 9.4 Combinations

### Problem: Generate All Combinations of Size K

Given `n` and `k`, return all possible combinations of `k` numbers chosen from `[1, n]`.

```cpp
#include <iostream>
#include <vector>

// Backtracking with pruning
// Time: O(C(n,k) * k), Space: O(k) recursion depth
void combine(int n, int k, int start,
             std::vector<int>& current,
             std::vector<std::vector<int>>& result) {
    if (current.size() == k) {
        result.push_back(current);
        return;
    }
    
    // PRUNING: we need (k - current.size()) more elements
    // so we can stop at n - (k - current.size()) + 1
    int remaining = k - current.size();
    for (int i = start; i <= n - remaining + 1; ++i) {
        current.push_back(i);
        combine(n, k, i + 1, current, result);
        current.pop_back();
    }
}

int main() {
    int n = 4, k = 2;
    std::vector<std::vector<int>> result;
    std::vector<int> current;
    combine(n, k, 1, current, result);
    
    std::cout << "C(" << n << "," << k << ") combinations:\n";
    for (const auto& comb : result) {
        for (int v : comb) std::cout << v << " ";
        std::cout << "\n";
    }
    // Output: 1 2, 1 3, 1 4, 2 3, 2 4, 3 4
    return 0;
}
```

### Combination Sum

Given a set of candidate numbers (each may be used unlimited times) and a target, find all unique combinations that sum to the target.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

void combinationSum(const std::vector<int>& candidates, int target,
                    int start, std::vector<int>& current,
                    std::vector<std::vector<int>>& result) {
    if (target == 0) {
        result.push_back(current);
        return;
    }
    if (target < 0) return; // Pruning: exceeded target
    
    for (int i = start; i < candidates.size(); ++i) {
        // Pruning: since candidates are sorted, if candidates[i] > target,
        // no further candidates will work either
        if (candidates[i] > target) break;
        
        current.push_back(candidates[i]);
        // Note: we pass i (not i+1) because we can reuse the same element
        combinationSum(candidates, target - candidates[i], i, current, result);
        current.pop_back();
    }
}

int main() {
    std::vector<int> candidates = {2, 3, 6, 7};
    int target = 7;
    
    // Sort for pruning
    std::vector<int> sorted_candidates = candidates;
    std::sort(sorted_candidates.begin(), sorted_candidates.end());
    
    std::vector<std::vector<int>> result;
    std::vector<int> current;
    combinationSum(sorted_candidates, target, 0, current, result);
    
    std::cout << "Combinations that sum to " << target << ":\n";
    for (const auto& comb : result) {
        for (int v : comb) std::cout << v << " ";
        std::cout << "\n";
    }
    // Output: 2 2 3, 7
    return 0;
}
```

---

## 9.5 N-Queens

### The Problem

Place `n` queens on an `n×n` chessboard such that no two queens attack each other (no two queens share the same row, column, or diagonal).

This is one of the most classic backtracking problems and is frequently asked in interviews.

### Approach 1: Basic Backtracking

```cpp
#include <iostream>
#include <vector>
#include <string>

class NQueens {
public:
    std::vector<std::vector<std::string>> solveNQueens(int n) {
        std::vector<std::vector<std::string>> result;
        std::vector<std::string> board(n, std::string(n, '.'));
        backtrack(board, 0, result);
        return result;
    }

private:
    void backtrack(std::vector<std::string>& board, int row,
                   std::vector<std::vector<std::string>>& result) {
        if (row == board.size()) {
            result.push_back(board);
            return;
        }
        for (int col = 0; col < board.size(); ++col) {
            if (isValid(board, row, col)) {
                board[row][col] = 'Q';           // CHOOSE
                backtrack(board, row + 1, result); // EXPLORE
                board[row][col] = '.';           // UNCHOOSE
            }
        }
    }
    
    bool isValid(const std::vector<std::string>& board, int row, int col) {
        int n = board.size();
        // Check column above
        for (int i = 0; i < row; ++i) {
            if (board[i][col] == 'Q') return false;
        }
        // Check upper-left diagonal
        for (int i = row - 1, j = col - 1; i >= 0 && j >= 0; --i, --j) {
            if (board[i][j] == 'Q') return false;
        }
        // Check upper-right diagonal
        for (int i = row - 1, j = col + 1; i >= 0 && j < n; --i, ++j) {
            if (board[i][j] == 'Q') return false;
        }
        return true;
    }
};
```

### Approach 2: Optimized with Hash Sets

The `isValid` check above is O(n) per call. We can reduce it to O(1) using hash sets:

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <unordered_set>

class NQueensOptimized {
public:
    std::vector<std::vector<std::string>> solveNQueens(int n) {
        std::vector<std::vector<std::string>> result;
        std::vector<std::string> board(n, std::string(n, '.'));
        std::unordered_set<int> cols, diag1, diag2; // O(1) lookup
        backtrack(board, 0, cols, diag1, diag2, result);
        return result;
    }

private:
    void backtrack(std::vector<std::string>& board, int row,
                   std::unordered_set<int>& cols,
                   std::unordered_set<int>& diag1,
                   std::unordered_set<int>& diag2,
                   std::vector<std::vector<std::string>>& result) {
        int n = board.size();
        if (row == n) {
            result.push_back(board);
            return;
        }
        for (int col = 0; col < n; ++col) {
            // Key insight: for diagonal (row-col) is constant on one diagonal,
            // (row+col) is constant on the other
            if (cols.count(col) || diag1.count(row - col) || diag2.count(row + col)) {
                continue;
            }
            // CHOOSE
            board[row][col] = 'Q';
            cols.insert(col);
            diag1.insert(row - col);
            diag2.insert(row + col);
            
            // EXPLORE
            backtrack(board, row + 1, cols, diag1, diag2, result);
            
            // UNCHOOSE
            board[row][col] = '.';
            cols.erase(col);
            diag1.erase(row - col);
            diag2.erase(row + col);
        }
    }
};

int main() {
    NQueensOptimized solver;
    int n = 8;
    auto solutions = solver.solveNQueens(n);
    
    std::cout << "Found " << solutions.size() << " solutions for " 
              << n << "-Queens\n\n";
    
    // Print first solution
    if (!solutions.empty()) {
        std::cout << "First solution:\n";
        for (const auto& row : solutions[0]) {
            std::cout << row << "\n";
        }
    }
    return 0;
}
```

### Complexity Analysis

| Version | Time | Space |
|---------|------|-------|
| Basic backtracking | O(n!) | O(n^2) |
| Optimized with hash sets | O(n!) | O(n) |

The time complexity is O(n!) because:
- Row 0: n choices
- Row 1: at most n-1 choices (column conflict)
- Row 2: at most n-2 choices
- ...
- Row n-1: 1 choice

In practice, pruning eliminates many branches, so the actual runtime is much less than n!.

---

## 9.6 Sudoku Solver

### The Problem

Fill a 9×9 grid so that each row, each column, and each 3×3 box contains all digits from 1 to 9.

### Approach: Constraint Propagation + Backtracking

```cpp
#include <iostream>
#include <vector>
#include <array>

class SudokuSolver {
public:
    bool solve(std::vector<std::vector<char>>& board) {
        for (int i = 0; i < 9; ++i) {
            for (int j = 0; j < 9; ++j) {
                if (board[i][j] == '.') {
                    for (char c = '1'; c <= '9'; ++c) {
                        if (isValid(board, i, j, c)) {
                            board[i][j] = c;  // CHOOSE
                            
                            if (solve(board)) { // EXPLORE
                                return true;    // Found a solution
                            }
                            
                            board[i][j] = '.';  // UNCHOOSE (backtrack)
                        }
                    }
                    return false; // No valid digit found — must backtrack
                }
            }
        }
        return true; // All cells filled
    }

private:
    bool isValid(const std::vector<std::vector<char>>& board,
                 int row, int col, char c) {
        // Check row
        for (int j = 0; j < 9; ++j) {
            if (board[row][j] == c) return false;
        }
        // Check column
        for (int i = 0; i < 9; ++i) {
            if (board[i][col] == c) return false;
        }
        // Check 3x3 box
        int boxRow = (row / 3) * 3;
        int boxCol = (col / 3) * 3;
        for (int i = boxRow; i < boxRow + 3; ++i) {
            for (int j = boxCol; j < boxCol + 3; ++j) {
                if (board[i][j] == c) return false;
            }
        }
        return true;
    }
};

void printBoard(const std::vector<std::vector<char>>& board) {
    for (int i = 0; i < 9; ++i) {
        if (i % 3 == 0 && i != 0) std::cout << "------+-------+------\n";
        for (int j = 0; j < 9; ++j) {
            if (j % 3 == 0 && j != 0) std::cout << "| ";
            std::cout << board[i][j] << " ";
        }
        std::cout << "\n";
    }
}

int main() {
    std::vector<std::vector<char>> board = {
        {'5','3','.','.','7','.','.','.','.'},
        {'6','.','.','1','9','5','.','.','.'},
        {'.','9','8','.','.','.','.','6','.'},
        {'8','.','.','.','6','.','.','.','3'},
        {'4','.','.','8','.','3','.','.','1'},
        {'7','.','.','.','2','.','.','.','6'},
        {'.','6','.','.','.','.','2','8','.'},
        {'.','.','.','4','1','9','.','.','5'},
        {'.','.','.','.','8','.','.','7','9'}
    };
    
    std::cout << "Original Sudoku:\n";
    printBoard(board);
    
    SudokuSolver solver;
    if (solver.solve(board)) {
        std::cout << "\nSolved Sudoku:\n";
        printBoard(board);
    } else {
        std::cout << "\nNo solution exists.\n";
    }
    return 0;
}
```

### Optimization: Constraint Propagation

The basic approach above can be slow for hard Sudoku puzzles. A key optimization is **constraint propagation** — before trying each digit, compute which digits are actually possible for each empty cell:

```cpp
#include <iostream>
#include <vector>
#include <array>
#include <bitset>

class SudokuOptimized {
    // Track which digits are used in each row, column, and box
    std::array<std::bitset<10>, 9> rowUsed;
    std::array<std::bitset<10>, 9> colUsed;
    std::array<std::bitset<10>, 9> boxUsed;
    
    int getBoxIndex(int row, int col) {
        return (row / 3) * 3 + (col / 3);
    }
    
public:
    bool solve(std::vector<std::vector<char>>& board) {
        // Initialize constraints
        rowUsed.fill({});
        colUsed.fill({});
        boxUsed.fill({});
        
        for (int i = 0; i < 9; ++i) {
            for (int j = 0; j < 9; ++j) {
                if (board[i][j] != '.') {
                    int d = board[i][j] - '0';
                    rowUsed[i].set(d);
                    colUsed[j].set(d);
                    boxUsed[getBoxIndex(i, j)].set(d);
                }
            }
        }
        return backtrack(board);
    }

private:
    bool backtrack(std::vector<std::vector<char>>& board) {
        // Find the empty cell with the fewest candidates (MRV heuristic)
        int minCandidates = 10, bestRow = -1, bestCol = -1;
        for (int i = 0; i < 9; ++i) {
            for (int j = 0; j < 9; ++j) {
                if (board[i][j] == '.') {
                    int count = 0;
                    std::bitset<10> used = rowUsed[i] | colUsed[j] | boxUsed[getBoxIndex(i, j)];
                    for (int d = 1; d <= 9; ++d) {
                        if (!used.test(d)) ++count;
                    }
                    if (count < minCandidates) {
                        minCandidates = count;
                        bestRow = i;
                        bestCol = j;
                    }
                }
            }
        }
        
        if (bestRow == -1) return true; // No empty cell — solved!
        
        int r = bestRow, c = bestCol;
        std::bitset<10> used = rowUsed[r] | colUsed[c] | boxUsed[getBoxIndex(r, c)];
        
        for (int d = 1; d <= 9; ++d) {
            if (!used.test(d)) {
                // CHOOSE
                board[r][c] = '0' + d;
                rowUsed[r].set(d);
                colUsed[c].set(d);
                boxUsed[getBoxIndex(r, c)].set(d);
                
                if (backtrack(board)) return true;
                
                // UNCHOOSE
                board[r][c] = '.';
                rowUsed[r].reset(d);
                colUsed[c].reset(d);
                boxUsed[getBoxIndex(r, c)].reset(d);
            }
        }
        return false; // No valid digit — backtrack
    }
};
```

The **Minimum Remaining Values (MRV)** heuristic selects the cell with the fewest possible candidates first. This dramatically reduces the search space because:
- It fails fast — if any cell has 0 candidates, we discover it immediately.
- It reduces branching — fewer candidates means fewer recursive calls.

---

## 9.7 Pruning Techniques

Pruning is the art of eliminating branches in the state space tree that cannot lead to a valid solution. Good pruning can turn an exponential algorithm into a practical one.

### Types of Pruning

| Technique | Description | Example |
|-----------|-------------|---------|
| **Constraint checking** | Verify partial solution is still valid | N-Queens: check diagonals before placing |
| **Sorting** | Sort input to enable early termination | Combination Sum: break if candidate > remaining |
| **Duplicate skipping** | Skip identical elements at the same level | Subsets II: skip `nums[i]` if `nums[i] == nums[i-1]` |
| **MRV heuristic** | Choose the variable with fewest options | Sudoku: pick cell with fewest candidates |
| **Bound-based pruning** | Use bounds to eliminate suboptimal branches | Branch and bound in optimization |

### Example: Word Search

Given a 2D grid of characters and a word, determine if the word exists in the grid by following adjacent cells (horizontally or vertically).

```cpp
#include <iostream>
#include <vector>
#include <string>

class WordSearch {
public:
    bool exist(std::vector<std::vector<char>>& board, const std::string& word) {
        int rows = board.size(), cols = board[0].size();
        for (int i = 0; i < rows; ++i) {
            for (int j = 0; j < cols; ++j) {
                if (backtrack(board, word, i, j, 0)) {
                    return true;
                }
            }
        }
        return false;
    }

private:
    bool backtrack(std::vector<std::vector<char>>& board,
                   const std::string& word, int row, int col, int index) {
        // Base case: all characters matched
        if (index == word.size()) return true;
        
        // Pruning: boundary check and character match
        if (row < 0 || row >= board.size() || 
            col < 0 || col >= board[0].size() ||
            board[row][col] != word[index]) {
            return false;
        }
        
        // CHOOSE: mark cell as visited
        char original = board[row][col];
        board[row][col] = '#';
        
        // EXPLORE: search in all 4 directions
        bool found = backtrack(board, word, row + 1, col, index + 1) ||
                     backtrack(board, word, row - 1, col, index + 1) ||
                     backtrack(board, word, row, col + 1, index + 1) ||
                     backtrack(board, word, row, col - 1, index + 1);
        
        // UNCHOOSE: restore cell
        board[row][col] = original;
        
        return found;
    }
};

int main() {
    std::vector<std::vector<char>> board = {
        {'A','B','C','E'},
        {'S','F','C','S'},
        {'A','D','E','E'}
    };
    
    WordSearch ws;
    std::cout << "ABCCED: " << (ws.exist(board, "ABCCED") ? "found" : "not found") << "\n";
    std::cout << "SEE: " << (ws.exist(board, "SEE") ? "found" : "not found") << "\n";
    std::cout << "ABCB: " << (ws.exist(board, "ABCB") ? "found" : "not found") << "\n";
    return 0;
}
```

### Pruning Example: Letter Combinations of a Phone Number

```cpp
#include <iostream>
#include <vector>
#include <string>

class PhoneCombinations {
    const std::vector<std::string> mapping = {
        "",     "",     "abc",  "def", "ghi", 
        "jkl",  "mno",  "pqrs", "tuv", "wxyz"
    };

public:
    std::vector<std::string> letterCombinations(const std::string& digits) {
        std::vector<std::string> result;
        if (digits.empty()) return result;
        std::string current;
        backtrack(digits, 0, current, result);
        return result;
    }

private:
    void backtrack(const std::string& digits, int index,
                   std::string& current, std::vector<std::string>& result) {
        if (index == digits.size()) {
            result.push_back(current);
            return;
        }
        int digit = digits[index] - '0';
        for (char c : mapping[digit]) {
            current.push_back(c);
            backtrack(digits, index + 1, current, result);
            current.pop_back();
        }
    }
};

int main() {
    PhoneCombinations pc;
    auto result = pc.letterCombinations("23");
    std::cout << "Combinations of '23':\n";
    for (const auto& s : result) {
        std::cout << s << " ";
    }
    std::cout << "\n";
    // Output: ad ae af bd be bf cd ce cf
    return 0;
}
```

### General Backtracking Optimization Checklist

1. **Sort the input** when order doesn't matter — enables early termination.
2. **Use efficient data structures** for constraint checking (hash sets, bitsets).
3. **Apply the MRV heuristic** — pick the most constrained variable first.
4. **Skip duplicates** at the same recursion level to avoid redundant work.
5. **Prune early** — check constraints before making a choice, not after.
6. **Use bit manipulation** for small fixed-size sets (e.g., 9×9 Sudoku).

---

## Interview Tips

1. **Master the template.** The choose-explore-unchoose pattern is the foundation for all backtracking problems. Practice it until it becomes second nature.
2. **Always consider duplicates.** If the input may have duplicates, ask the interviewer whether duplicate results are allowed.
3. **Draw the state space tree.** For small inputs, draw the tree to understand the branching and identify pruning opportunities.
4. **Know the complexity.** Most backtracking problems are exponential, but pruning can make them practical. Be ready to analyze the complexity.
5. **Start with the brute force.** Explain the brute force approach first, then optimize with backtracking and pruning.
6. **Common patterns:** Subsets (include/exclude), Permutations (swap), Combinations (start index), Constraint satisfaction (try + undo).

## Common Mistakes

| Mistake | Example | Fix |
|---------|---------|-----|
| Forgetting to backtrack | Not undoing a choice after exploring | Always undo after recursive call |
| Wrong start index | Passing `start` instead of `i+1` in combinations | Understand when elements can be reused |
| Not handling duplicates | Generating duplicate subsets/permutations | Sort input, skip duplicates at same level |
| Modifying shared state | Using a global visited array incorrectly | Use local copies or undo changes |
| Off-by-one in bounds | Missing the last element or going out of bounds | Carefully check loop bounds |
| Early return without undoing | Returning from inside the loop without undoing | Ensure all choices are undone |

---

## Practice Problems

### Easy

1. **Generate Parentheses** — Generate all valid combinations of `n` pairs of parentheses.
   - *Hint:* Track open and close counts. Add `(` if open < n, add `)` if close < open.

2. **Binary Watch** — Given an integer `turnedOn` (number of LEDs on), return all possible times.
   - *Hint:* Backtrack over 10 LEDs (4 for hours, 6 for minutes).

### Medium

3. **Palindrome Partitioning** — Partition a string such that every substring is a palindrome.
   - *Hint:* At each position, try every possible palindrome prefix.

4. **Word Search** — Given a 2D grid and a word, determine if the word exists in the grid.
   - *Hint:* DFS from each cell, mark visited cells.

5. **Combination Sum III** — Find all combinations of `k` numbers (1-9) that sum to `n`.
   - *Hint:* Standard combination with sum constraint and pruning.

6. **Restore IP Addresses** — Given a string of digits, return all valid IP addresses.
   - *Hint:* Place 3 dots among the digits. Each segment must be 0-255.

### Hard

7. **N-Queens** — Return all distinct solutions to the N-Queens puzzle.
   - *Hint:* Place one queen per row. Use hash sets for O(1) conflict checking.

8. **Sudoku Solver** — Write a program to solve a Sudoku puzzle.
   - *Hint:* Try digits 1-9 for each empty cell. Use constraint propagation.

9. **Expression Add Operators** — Given a string of digits and a target, insert `+`, `-`, `*` to reach the target.
   - *Hint:* Track the current value and the previous operand (for multiplication handling).

---

## Complexity Summary

| Problem | Time | Space | Notes |
|---------|------|-------|-------|
| Subsets | O(n × 2^n) | O(n) | 2^n subsets, each up to size n |
| Subsets II | O(n × 2^n) | O(n) | Skip duplicates |
| Permutations | O(n! × n) | O(n) | n! permutations |
| Permutations II | O(n! × n) | O(n) | Skip duplicates |
| Combinations | O(C(n,k) × k) | O(k) | Pruning reduces search |
| Combination Sum | O(n^(T/M) × T/M) | O(T/M) | T = target, M = min candidate |
| N-Queens | O(n!) | O(n^2) | Much less with pruning |
| Sudoku Solver | O(9^m) | O(1) | m = empty cells, MRV helps |
| Word Search | O(M × N × 4^L) | O(L) | L = word length |
