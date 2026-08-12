# Chapter 113: Profile DP (Broken Profile DP)

## Prerequisites
- Bitmask DP, Grid Problems, Dynamic Programming

## Interview Frequency: ★★

---

## 113.1 What Is Profile DP?

**Profile DP** (also called **Broken Profile DP** or **Contour DP**) is a technique for counting configurations on grids by encoding the state of a "frontier" as a bitmask. The frontier is the boundary between processed and unprocessed cells.

**Key idea:** When filling a grid row by row (or column by column), you only need to know which cells in the current row are already occupied. This "profile" of occupied cells is encoded as a bitmask.

**Motivation:** Grid tiling problems (domino, tromino, L-shaped tiles) have exponential state spaces. Profile DP reduces the state to O(2^m) where m is the smaller grid dimension, making them tractable for m ≤ 20.

---

## 113.2 Intuition: The Frontier

Imagine filling a grid cell by cell, left to right, top to bottom:

```
Filled:     Processing:     Unfilled:
X X X       X X ?           . . .
X X X       ? ? ?           . . .
X X X       ? ? ?           . . .
```

The **profile** (frontier) is the boundary between filled and unfilled:
- Cells above the frontier are completely determined
- Cells below the frontier are untouched
- Cells on the frontier may be partially filled (e.g., a vertical domino extends down)

The profile tells us which cells in the current row are "blocked" by tiles extending from the row above.

---

## 113.3 Domino Tiling

### Problem

Count the number of ways to tile an N × M grid with 1 × 2 dominoes (horizontal or vertical).

### State Definition

`dp[row][mask]` = number of ways to tile the grid up to cell (row, col) where `mask` represents which cells in the current row are already occupied by vertical dominoes extending from the previous row.

- `mask` has M bits
- Bit j is 1 if cell (row, j) is already filled by a vertical domino from above
- Bit j is 0 if cell (row, j) is empty and needs to be filled

### Transitions

When processing cell (row, col):

**Case 1: Cell is already filled (mask bit is 1)**
- Move to next cell: `dp[row][col+1][mask] += dp[row][col][mask]`

**Case 2: Cell is empty (mask bit is 0)**

Option A: Place horizontal domino (if col+1 < M and bit col+1 is 0)
```
new_mask = mask | (1 << (col+1))
dp[row][col+1][new_mask] += dp[row][col][mask]
```

Option B: Place vertical domino (if row+1 < N)
```
new_mask = mask | (1 << col)
dp[row+1][col][new_mask] += dp[row][col][mask]
```

Actually, the standard approach processes cell by cell and "clears" the bit when a cell is filled by a horizontal domino or passes to the next row.

### Simplified Transition

Process each cell (row, col) in order:

```
If bit col in mask is 1:
    → This cell is already filled (vertical domino from above)
    → Clear the bit: new_mask = mask ^ (1 << col)
    → Move to (row, col+1)

If bit col in mask is 0:
    → Option 1: Place horizontal domino (needs col+1 < M, bit col+1 is 0)
        → Set bit col+1: new_mask = mask | (1 << (col+1))
        → Move to (row, col+1)
    → Option 2: Place vertical domino (needs row+1 < N)
        → Keep mask as is (bit stays 0, will be filled from above in next row)
        → Move to (row, col+1), but the bit represents next row's profile
```

### Dry Run: 2×3 Grid

Grid dimensions: N=2 rows, M=3 columns

**Processing order:** (0,0), (0,1), (0,2), (1,0), (1,1), (1,2)

**Step-by-step:**

| Step | Cell | Mask | Action | New Mask | Ways |
|---|---|---|---|---|---|
| 0 | (0,0) | 000 | Start | - | 1 |
| 1 | - | 000 | Place H domino at (0,0)-(0,1) | 010 | 1 |
| 1 | - | 000 | Place V domino at (0,0)-(1,0) | 001 | 1 |
| 2 | (0,1) | 010 | Bit 1 set, clear it | 000 | 1 |
| 2 | (0,1) | 001 | Place H domino at (0,1)-(0,2) | 101 | 1 |
| 2 | (0,1) | 001 | Place V domino at (0,1)-(1,1) | 011 | 1 |
| 3 | (0,2) | 000 | Place V domino at (0,2)-(1,2) | 100 | 1 |
| 3 | (0,2) | 101 | Bit 2 set, clear it | 001 | 1 |
| 3 | (0,2) | 011 | Bit 2 set, clear it | 010 | 1 |
| ... | ... | ... | ... | ... | ... |

Final answer: `dp[1][0][000]` = **3 ways** (verified: 3 horizontal, or 2 vertical + 1 horizontal, etc.)

### Code

```cpp
#include <iostream>
#include <vector>
#include <cstring>

long long dominoTiling(int n, int m) {
    if (n < m) std::swap(n, m); // minimize mask size
    int maxMask = 1 << m;
    std::vector<long long> dp(maxMask, 0), next(maxMask, 0);
    dp[0] = 1;
    
    for (int row = 0; row < n; row++) {
        for (int col = 0; col < m; col++) {
            std::fill(next.begin(), next.end(), 0);
            for (int mask = 0; mask < maxMask; mask++) {
                if (dp[mask] == 0) continue;
                
                if (mask & (1 << col)) {
                    // Cell already filled from above, clear bit
                    next[mask ^ (1 << col)] += dp[mask];
                } else {
                    // Option 1: Place horizontal domino
                    if (col + 1 < m && !(mask & (1 << (col + 1)))) {
                        next[mask | (1 << (col + 1))] += dp[mask];
                    }
                    // Option 2: Place vertical domino
                    next[mask | (1 << col)] += dp[mask];
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
            if (n * m % 2 == 0) {
                std::cout << n << "x" << m << ": " 
                          << dominoTiling(n, m) << " ways\n";
            }
        }
    }
    return 0;
}
```

```python
def domino_tiling(n, m):
    """Count ways to tile n x m grid with 1x2 dominoes."""
    if n < m:
        n, m = m, n  # minimize mask size
    
    max_mask = 1 << m
    dp = [0] * max_mask
    dp[0] = 1
    
    for row in range(n):
        for col in range(m):
            nxt = [0] * max_mask
            for mask in range(max_mask):
                if dp[mask] == 0:
                    continue
                
                if mask & (1 << col):
                    # Cell already filled from above
                    nxt[mask ^ (1 << col)] += dp[mask]
                else:
                    # Option 1: Place horizontal domino
                    if col + 1 < m and not (mask & (1 << (col + 1))):
                        nxt[mask | (1 << (col + 1))] += dp[mask]
                    # Option 2: Place vertical domino
                    nxt[mask | (1 << col)] += dp[mask]
            
            dp = nxt
    
    return dp[0]

# Example
for n in range(1, 9):
    for m in range(1, 9):
        if n * m % 2 == 0:
            print(f"{n}x{m}: {domino_tiling(n, m)} ways")
```

```java
public class DominoTiling {
    public static long dominoTiling(int n, int m) {
        if (n < m) { int temp = n; n = m; m = temp; }
        int maxMask = 1 << m;
        long[] dp = new long[maxMask];
        long[] next = new long[maxMask];
        dp[0] = 1;
        
        for (int row = 0; row < n; row++) {
            for (int col = 0; col < m; col++) {
                java.util.Arrays.fill(next, 0);
                for (int mask = 0; mask < maxMask; mask++) {
                    if (dp[mask] == 0) continue;
                    
                    if ((mask & (1 << col)) != 0) {
                        next[mask ^ (1 << col)] += dp[mask];
                    } else {
                        if (col + 1 < m && (mask & (1 << (col + 1))) == 0) {
                            next[mask | (1 << (col + 1))] += dp[mask];
                        }
                        next[mask | (1 << col)] += dp[mask];
                    }
                }
                long[] temp = dp; dp = next; next = temp;
            }
        }
        return dp[0];
    }
    
    public static void main(String[] args) {
        for (int n = 1; n <= 8; n++)
            for (int m = 1; m <= 8; m++)
                if (n * m % 2 == 0)
                    System.out.printf("%dx%d: %d ways%n", n, m, dominoTiling(n, m));
    }
}
```

---

## 113.4 L-Tromino Tiling

### Problem

Count ways to tile an N × M grid with L-shaped trominoes (3 cells in an L shape). Each L-tromino covers exactly 3 cells.

### Additional State

L-trominoes have 4 orientations:
```
XX  XX  X.  .X
X.  .X  XX  XX
```

The profile needs extra bits to track which cells are partially filled.

### State

For L-trominoes, the mask may need M+1 bits or additional encoding to handle the extra shapes. The transitions are more complex but follow the same frontier principle.

### Complexity

- **Time:** O(N × M × 2^(M+1)) due to extra states
- **Space:** O(2^(M+1))

---

## 113.5 Profile DP with Additional Constraints

### Chess Piece Placement

**Problem:** Place non-attacking knights on an N × M board.

**Profile:** Bitmask of M bits, bit j = 1 if a knight is placed in column j of the current row.

**Transition:** When adding a knight at column j, ensure:
- No knight at column j-2 or j+2 in the previous row (knight attacks)
- No knight at column j-1 or j+1 in the row before previous (knight attacks)

This requires tracking **two rows** of profile: `dp[row][mask_curr][mask_prev]`.

### Walls and Obstacles

If some cells are blocked, simply skip transitions that would place tiles on blocked cells.

---

## 113.6 General Template

```python
def profile_dp(n, m, can_place, get_transitions):
    """
    General profile DP template.
    
    Args:
        n: number of rows
        m: number of columns (mask width)
        can_place: function(row, col, mask) -> bool
        get_transitions: function(row, col, mask) -> list of (new_mask, ways)
    """
    max_mask = 1 << m
    dp = [0] * max_mask
    dp[0] = 1
    
    for row in range(n):
        for col in range(m):
            nxt = [0] * max_mask
            for mask in range(max_mask):
                if dp[mask] == 0:
                    continue
                for new_mask, ways in get_transitions(row, col, mask):
                    nxt[new_mask] += dp[mask] * ways
            dp = nxt
    
    return dp[0]
```

---

## 113.7 Optimization: State Compression

### Reducing State Space

Not all 2^M masks are reachable. **Optimization:** Only iterate over reachable states.

```python
def domino_tiling_optimized(n, m):
    if n < m:
        n, m = m, n
    
    dp = {0: 1}  # Use dictionary for sparse states
    
    for row in range(n):
        for col in range(m):
            nxt = {}
            for mask, count in dp.items():
                if mask & (1 << col):
                    # Cell filled from above
                    new_mask = mask ^ (1 << col)
                    nxt[new_mask] = nxt.get(new_mask, 0) + count
                else:
                    # Horizontal domino
                    if col + 1 < m and not (mask & (1 << (col + 1))):
                        new_mask = mask | (1 << (col + 1))
                        nxt[new_mask] = nxt.get(new_mask, 0) + count
                    # Vertical domino
                    new_mask = mask | (1 << col)
                    nxt[new_mask] = nxt.get(new_mask, 0) + count
            dp = nxt
    
    return dp.get(0, 0)
```

### Symmetry Optimization

For symmetric grids (N = M), some masks are equivalent under rotation/reflection. This can reduce the state space by a constant factor.

---

## 113.8 Related Problems

| Problem | Profile Type | Notes |
|---|---|---|
| Domino tiling | M bits | 1 = filled from above |
| Tromino tiling | M bits + extra | Complex transitions |
| Knight placement | M bits per 2 rows | Knight attack pattern |
| Non-attacking rooks | M bits | No two in same row/col |
| Grid coloring | M bits × colors | Count proper colorings |
| Hamiltonian path (grid) | Complex profile | Use profile DP on thin grids |

---

## 113.9 Exercises

### Exercise 1: 3×N Domino Tiling
Write a formula for the number of ways to tile a 3 × N grid with dominoes. Verify with profile DP for N = 1 to 10.

### Exercise 2: Tromino Tiling
Implement profile DP to count ways to tile an N × M grid with L-trominoes. Handle the case where N × M is not divisible by 3.

### Exercise 3: Knights on Board
Count the number of ways to place k non-attacking knights on an N × M board using profile DP with two-row state.

### Exercise 4: Profile DP with Obstacles
Modify the domino tiling code to handle an N × M grid where some cells are blocked. The input is a grid of 0s and 1s where 1 = blocked.

### Exercise 5: Hexagonal Grid
Extend profile DP to a hexagonal grid. How does the profile change?

---

## 113.10 Interview Questions

### Q1: When do you use profile DP?
**A:** When the problem involves counting configurations on a grid, and the grid has a "thin" dimension (M ≤ 20). The profile encodes the state of the frontier between processed and unprocessed cells.

### Q2: What's the time complexity of profile DP?
**A:** O(N × M × 2^M) for a grid of size N × M. The 2^M factor comes from the bitmask states. This is efficient when M is small (≤ 20).

### Q3: How does profile DP differ from regular bitmask DP?
**A:** Regular bitmask DP operates on subsets of a set. Profile DP operates on a grid frontier. The mask represents which cells in the current row are occupied, not which elements are selected. Profile DP also processes cells in a specific order (row by row, column by column).

### Q4: Can profile DP be used for optimization problems?
**A:** Yes. Instead of counting ways, you can track minimum/maximum cost. For example, "minimum cost to tile a grid with tiles of different costs" uses `min` instead of `+` in the transition.

### Q5: How do you handle the transition from one row to the next?
**A:** After processing the last column of a row, the remaining mask (bits that are 1) represents cells in the next row that are already filled by vertical dominoes extending from the current row. This becomes the initial mask for the next row.

---

## 113.11 Cross-References

| Topic | Related Chapter |
|---|---|
| Bitmask DP | Chapter 25 |
| Grid DP | Chapter 28 |
| State Compression | Chapter 26 |
| Combinatorics (Catalan) | Chapter 82 |
| Inclusion-Exclusion | Chapter 83 |
| Matrix Exponentiation | Chapter 86 |

---

## Summary

| Aspect | Value |
|---|---|
| State | Bitmask of M bits (profile of current row) |
| Time | O(N × M × 2^M) |
| Space | O(2^M) |
| Best for | Grid tiling, chess problems, grid counting |
| Key insight | Only need frontier state, not full grid |

**Key Insight:** Profile DP exploits the fact that when filling a grid cell by cell, you only need to know which cells in the current row are "blocked" by tiles from the previous row. This reduces an exponential grid state to a manageable bitmask of width M.
