# Chapter 95: Advanced Bit Manipulation

## Prerequisites

- Bit manipulation basics (AND, OR, XOR, shifts)
- Binary number representation
- Basic understanding of dynamic programming

## Interview Frequency: ★★★

Advanced bit tricks appear in **Google** and **Amazon** interviews for optimization problems. They are particularly common in competitive programming and system-level interviews.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Subset enumeration | ★★★ | Medium | Iterate all subsets |
| Bit DP | ★★★★ | Medium | State compression |
| De Bruijn sequences | ★ | Hard | Bit scanning |
| Popcount tricks | ★★★ | Easy | Count set bits |
| XOR applications | ★★★ | Medium | Pair finding, parity |
| Bitmask tricks | ★★★ | Medium | Common patterns |

---

## Definition

**Bit manipulation** uses bitwise operators (AND, OR, XOR, NOT, shifts) to perform computations directly on binary representations. Advanced bit manipulation involves techniques like subset enumeration, state compression DP, and clever XOR applications that solve problems more efficiently than naive approaches.

## Motivation

Many problems have small constraints (n ≤ 20) where exponential algorithms are acceptable. Bit manipulation allows us to:
- Represent sets as integers (compact, cache-friendly)
- Enumerate subsets efficiently using submask iteration
- Compress DP states into single integers
- Solve certain problems in O(1) using precomputed tables

## Intuition

Think of a bitmask as a light switch panel with n switches. Each switch (bit) is either on (1) or off (0). The entire panel state is a single integer. This compact representation lets us enumerate all possible configurations by counting from 0 to 2^n - 1.

---

## 95.1 Subset Enumeration

### Definition

Given a set of n elements, enumerate all 2^n subsets using bitmasks. Each bit in an integer represents whether an element is included.

### Motivation

Subset enumeration is fundamental to many algorithms: brute-force search, meet-in-the-middle, inclusion-exclusion, and DP over subsets.

### Formal Explanation

For a set S = {0, 1, ..., n-1}:
- Each subset corresponds to a bitmask m ∈ [0, 2^n)
- Element i is in the subset iff bit i of m is set
- Total subsets: 2^n

### Step-by-Step Walkthrough

For n = 3 (set {0, 1, 2}):
```
mask  binary  subset
0     000     {}
1     001     {0}
2     010     {1}
3     011     {0,1}
4     100     {2}
5     101     {0,2}
6     110     {1,2}
7     111     {0,1,2}
```

### Submask Enumeration

Enumerate all submasks of a given mask m. The trick: `sub = (sub - 1) & m` iterates through all submasks in decreasing order.

**Why it works**: Subtracting 1 flips the lowest set bit and all bits below it. ANDing with m keeps only bits that are in m.

### Dry Run

For mask = 0b1101 (decimal 13, set {0, 2, 3}):
```
sub = 13 (1101) → {0,2,3}
sub = 12 (1100) → {2,3}
sub = 9  (1001) → {0,3}
sub = 8  (1000) → {3}
sub = 5  (0101) → {0,2}
sub = 4  (0100) → {2}
sub = 1  (0001) → {0}
sub = 0  (0000) → stop
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>

int main() {
    int n = 4;
    int fullMask = (1 << n) - 1;

    // Enumerate all 2^n subsets
    std::cout << "All subsets of {0,1,2,3}:\n";
    for (int mask = 0; mask <= fullMask; mask++) {
        std::cout << "{";
        bool first = true;
        for (int i = 0; i < n; i++) {
            if (mask & (1 << i)) {
                if (!first) std::cout << ",";
                std::cout << i;
                first = false;
            }
        }
        std::cout << "}\n";
    }

    // Enumerate submasks of a mask
    int mask = 0b1101; // {0, 2, 3}
    std::cout << "\nSubmasks of {0,2,3}:\n";
    for (int sub = mask; sub; sub = (sub - 1) & mask) {
        std::cout << "  " << sub << " (";
        for (int i = 0; i < 4; i++)
            if (sub & (1 << i)) std::cout << i;
        std::cout << ")\n";
    }

    return 0;
}
```

### Python Implementation

```python
def all_subsets(n):
    """Generate all 2^n subsets of {0, 1, ..., n-1}."""
    for mask in range(1 << n):
        subset = [i for i in range(n) if mask & (1 << i)]
        yield subset

def submasks(mask):
    """Enumerate all submasks of mask (excluding 0)."""
    sub = mask
    while sub:
        yield sub
        sub = (sub - 1) & mask

# Example
print("All subsets of {0,1,2}:")
for s in all_subsets(3):
    print(f"  {s}")

print("\nSubmasks of 0b1101:")
for s in submasks(0b1101):
    print(f"  {s:04b} = {s}")
```

### Java Implementation

```java
import java.util.*;

public class SubsetEnumeration {
    public static void main(String[] args) {
        int n = 4;
        int fullMask = (1 << n) - 1;

        // All subsets
        System.out.println("All subsets of {0,1,2,3}:");
        for (int mask = 0; mask <= fullMask; mask++) {
            List<Integer> subset = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                if ((mask & (1 << i)) != 0) subset.add(i);
            }
            System.out.println(subset);
        }

        // Submasks
        int mask = 0b1101;
        System.out.println("\nSubmasks of {0,2,3}:");
        for (int sub = mask; sub > 0; sub = (sub - 1) & mask) {
            List<Integer> s = new ArrayList<>();
            for (int i = 0; i < 4; i++) {
                if ((sub & (1 << i)) != 0) s.add(i);
            }
            System.out.println(s);
        }
    }
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| All subsets | O(2^n × n) | O(n) per subset |
| Submask enumeration | O(2^k) where k = popcount(m) | O(1) |

---

## 95.2 Popcount Tricks

### Definition

**Popcount** (population count) counts the number of set bits (1s) in a binary number.

### Motivation

Popcount appears in:
- Hamming distance computation
- Counting active features in bitmasks
- Checking if a number is a power of 2

### Key Tricks

| Expression | Effect |
|---|---|
| `x & (x - 1)` | Clear lowest set bit |
| `x & (-x)` | Isolate lowest set bit |
| `x ^ (x - 1)` | Set all bits from LSB to lowest set bit |
| `(x & (x-1)) == 0` | Check if x is power of 2 (or 0) |

### Dry Run

For x = 0b11010110 (214):
```
x          = 11010110
x - 1      = 11010101
x & (x-1)  = 11010100  ← cleared bit 1
x & (-x)   = 00000010  ← isolated bit 1
```

### C++ Implementation

```cpp
#include <iostream>
#include <bitset>

int popcount_manual(int x) {
    int count = 0;
    while (x) {
        x &= x - 1; // Clear lowest set bit
        count++;
    }
    return count;
}

int main() {
    int x = 0b11010110;
    std::cout << "Binary: " << std::bitset<8>(x) << "\n";
    std::cout << "Popcount (manual): " << popcount_manual(x) << "\n";
    std::cout << "Popcount (builtin): " << __builtin_popcount(x) << "\n";

    // Lowest set bit
    int lowest = x & (-x);
    std::cout << "Lowest set bit: " << std::bitset<8>(lowest) << "\n";

    // Is power of 2?
    int p = 16;
    std::cout << p << " is power of 2: " << ((p & (p - 1)) == 0) << "\n";

    // Swap without temp
    int a = 5, b = 9;
    a ^= b; b ^= a; a ^= b;
    std::cout << "After swap: a=" << a << " b=" << b << "\n";

    return 0;
}
```

### Python Implementation

```python
def popcount(x):
    """Count set bits using Brian Kernighan's algorithm."""
    count = 0
    while x:
        x &= x - 1  # Clear lowest set bit
        count += 1
    return count

# Python 3.10+ has int.bit_count()
x = 0b11010110
print(f"Binary: {x:08b}")
print(f"Popcount: {popcount(x)}")
print(f"builtin: {x.bit_count()}")
print(f"Lowest set bit: {(x & -x):08b}")
print(f"16 is power of 2: {16 & 15 == 0}")
```

### Java Implementation

```java
public class PopcountTricks {
    public static int popcount(int x) {
        int count = 0;
        while (x != 0) {
            x &= x - 1;  // Clear lowest set bit
            count++;
        }
        return count;
    }

    public static void main(String[] args) {
        int x = 0b11010110;
        System.out.println("Binary: " + Integer.toBinaryString(x));
        System.out.println("Popcount (manual): " + popcount(x));
        System.out.println("Popcount (builtin): " + Integer.bitCount(x));
        System.out.println("Lowest set bit: " + Integer.toBinaryString(x & (-x)));
        System.out.println("16 is power of 2: " + ((16 & 15) == 0));
    }
}
```

---

## 95.3 Bit DP (State Compression)

### Definition

**Bit DP** uses a bitmask as a DP state dimension, typically to represent which elements have been "used" or "visited". This is applicable when n ≤ 20 (since 2^20 ≈ 10^6 states).

### Motivation

Many combinatorial optimization problems (TSP, assignment, Hamiltonian path) have exponential brute-force solutions. Bit DP reduces the state space by encoding which elements are processed into a single integer.

### The Traveling Salesman Problem (TSP)

**Problem**: Given n cities and distances between them, find the shortest tour visiting all cities exactly once and returning to the start.

**DP State**: `dp[mask][u]` = minimum cost to visit exactly the cities in `mask`, ending at city `u`.

**Transition**: For each unvisited city `v`:
```
dp[mask | (1<<v)][v] = min(dp[mask | (1<<v)][v], dp[mask][u] + dist[u][v])
```

### Step-by-Step Walkthrough

For 4 cities with distances:
```
dist = [[0,10,15,20],[10,0,35,25],[15,35,0,30],[20,25,30,0]]
```

```
Initial: dp[0001][0] = 0 (start at city 0, only city 0 visited)

From mask=0001, u=0:
  dp[0011][1] = 0 + 10 = 10  (go to city 1)
  dp[0101][2] = 0 + 15 = 15  (go to city 2)
  dp[1001][3] = 0 + 20 = 20  (go to city 3)

From mask=0011, u=1:
  dp[0111][2] = 10 + 35 = 45  (go to city 2)
  dp[1011][3] = 10 + 25 = 35  (go to city 3)

From mask=0101, u=2:
  dp[0111][1] = 15 + 35 = 50  (go to city 1)
  dp[1101][3] = 15 + 30 = 45  (go to city 3)

... (continue until all masks processed)

Final: min over u≠0 of dp[1111][u] + dist[u][0]
  dp[1111][1] + dist[1][0] = ... 
  dp[1111][2] + dist[2][0] = ...
  dp[1111][3] + dist[3][0] = ...
Result: 80 (tour: 0→1→3→2→0)
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

int tsp(const std::vector<std::vector<int>>& dist) {
    int n = dist.size();
    int fullMask = (1 << n) - 1;
    std::vector<std::vector<int>> dp(1 << n, std::vector<int>(n, INT_MAX));

    dp[1][0] = 0; // Start at node 0

    for (int mask = 1; mask <= fullMask; mask++) {
        for (int u = 0; u < n; u++) {
            if (!(mask & (1 << u)) || dp[mask][u] == INT_MAX) continue;
            for (int v = 0; v < n; v++) {
                if (mask & (1 << v)) continue;
                int newMask = mask | (1 << v);
                dp[newMask][v] = std::min(dp[newMask][v],
                                          dp[mask][u] + dist[u][v]);
            }
        }
    }

    int result = INT_MAX;
    for (int u = 1; u < n; u++)
        result = std::min(result, dp[fullMask][u] + dist[u][0]);

    return result;
}

int main() {
    std::vector<std::vector<int>> dist = {
        {0, 10, 15, 20},
        {10, 0, 35, 25},
        {15, 35, 0, 30},
        {20, 25, 30, 0}
    };

    std::cout << "TSP min cost: " << tsp(dist) << "\n"; // 80

    return 0;
}
```

### Python Implementation

```python
import sys

def tsp(dist):
    """Solve TSP using bitmask DP. Returns minimum tour cost."""
    n = len(dist)
    full_mask = (1 << n) - 1
    INF = sys.maxsize

    # dp[mask][u] = min cost to visit cities in mask, ending at u
    dp = [[INF] * n for _ in range(1 << n)]
    dp[1][0] = 0  # Start at city 0

    for mask in range(1, full_mask + 1):
        for u in range(n):
            if not (mask & (1 << u)) or dp[mask][u] == INF:
                continue
            for v in range(n):
                if mask & (1 << v):
                    continue
                new_mask = mask | (1 << v)
                dp[new_mask][v] = min(dp[new_mask][v],
                                      dp[mask][u] + dist[u][v])

    # Return to city 0
    return min(dp[full_mask][u] + dist[u][0] for u in range(1, n))

dist = [
    [0, 10, 15, 20],
    [10, 0, 35, 25],
    [15, 35, 0, 30],
    [20, 25, 30, 0]
]
print(f"TSP min cost: {tsp(dist)}")  # 80
```

### Java Implementation

```java
import java.util.*;

public class TSPBitDP {
    public static int tsp(int[][] dist) {
        int n = dist.length;
        int fullMask = (1 << n) - 1;
        int[][] dp = new int[1 << n][n];
        for (int[] row : dp) Arrays.fill(row, Integer.MAX_VALUE);
        dp[1][0] = 0;

        for (int mask = 1; mask <= fullMask; mask++) {
            for (int u = 0; u < n; u++) {
                if ((mask & (1 << u)) == 0 || dp[mask][u] == Integer.MAX_VALUE)
                    continue;
                for (int v = 0; v < n; v++) {
                    if ((mask & (1 << v)) != 0) continue;
                    int newMask = mask | (1 << v);
                    dp[newMask][v] = Math.min(dp[newMask][v],
                                              dp[mask][u] + dist[u][v]);
                }
            }
        }

        int result = Integer.MAX_VALUE;
        for (int u = 1; u < n; u++)
            result = Math.min(result, dp[fullMask][u] + dist[u][0]);
        return result;
    }

    public static void main(String[] args) {
        int[][] dist = {{0,10,15,20},{10,0,35,25},{15,35,0,30},{20,25,30,0}};
        System.out.println("TSP min cost: " + tsp(dist)); // 80
    }
}
```

### Complexity

| Aspect | Value |
|---|---|
| Time | O(2^n × n^2) |
| Space | O(2^n × n) |
| Max n (1s time) | ~20-22 |

---

## 95.4 XOR Applications

### Motivation

XOR has unique properties that make it invaluable for certain problems:
- `a ^ a = 0` (self-cancellation)
- `a ^ 0 = a` (identity)
- XOR is commutative and associative

### Find the Unique Element

**Problem**: Every element appears twice except one. Find it.

```cpp
#include <iostream>
#include <vector>

int findUnique(const std::vector<int>& nums) {
    int result = 0;
    for (int x : nums) result ^= x;
    return result;
}

int main() {
    std::vector<int> nums = {2, 3, 5, 3, 2};
    std::cout << "Unique element: " << findUnique(nums) << "\n"; // 5
    return 0;
}
```

### Find Two Unique Elements

**Problem**: Every element appears twice except two elements. Find both.

```cpp
#include <iostream>
#include <vector>

std::pair<int,int> findTwoUnique(const std::vector<int>& nums) {
    int xorAll = 0;
    for (int x : nums) xorAll ^= x;  // a ^ b

    // Find rightmost set bit (differs between a and b)
    int diffBit = xorAll & (-xorAll);

    int a = 0, b = 0;
    for (int x : nums) {
        if (x & diffBit) a ^= x;
        else b ^= x;
    }
    return {a, b};
}

int main() {
    std::vector<int> nums = {1, 2, 3, 1, 2, 5};
    auto [a, b] = findTwoUnique(nums);
    std::cout << "Two unique: " << a << " and " << b << "\n"; // 3 and 5
    return 0;
}
```

### XOR Swap

```cpp
// Swap without temporary variable
a ^= b;
b ^= a;
a ^= b;
```

### Gray Code

Generate n-bit Gray code where consecutive values differ by exactly one bit:

```cpp
#include <iostream>
#include <vector>

std::vector<int> grayCode(int n) {
    std::vector<int> result;
    for (int i = 0; i < (1 << n); i++)
        result.push_back(i ^ (i >> 1));
    return result;
}

int main() {
    auto codes = grayCode(3);
    for (int code : codes)
        std::cout << code << " (" << std::bitset<3>(code) << ")\n";
    return 0;
}
```

---

## 95.5 Common Bitmask Patterns

| Pattern | Expression | Use Case |
|---|---|---|
| Set bit i | `mask \| (1 << i)` | Add element i |
| Clear bit i | `mask & ~(1 << i)` | Remove element i |
| Toggle bit i | `mask ^ (1 << i)` | Flip membership |
| Check bit i | `(mask >> i) & 1` | Is element i in set? |
| Count bits | `__builtin_popcount(mask)` | Size of subset |
| Lowest bit | `mask & (-mask)` | Isolate LSB |
| All subsets | `for (int s=0; s<(1<<n); s++)` | Brute force |
| Submasks | `for (int s=m; s; s=(s-1)&m)` | Subset of mask |

---

## Exercises

1. **Power of Two**: Write a function that checks if a number is a power of 2 using bit manipulation. Handle the edge case of 0.

2. **Counting Bits**: Given an integer n, return an array of length n+1 where `result[i]` is the number of 1s in the binary representation of i. Solve in O(n) time.

3. **Single Number III**: Given an array where every element appears twice except two elements, find those two elements. (Hint: XOR + partition by a differing bit.)

4. **Hamiltonian Path**: Modify the TSP code to find if a Hamiltonian path exists (not necessarily a cycle).

5. **Maximum XOR**: Given an array of integers, find the maximum XOR of any two elements. (Hint: Use a trie or bit-by-bit greedy approach.)

6. **Bitmask DP for Assignment**: Given n workers and n jobs with cost[i][j], assign each worker to exactly one job to minimize total cost. Solve using bitmask DP.

---

## Interview Questions

1. **Q: How do you count set bits in an integer?**
   A: Three approaches: (1) Loop and check each bit: O(32). (2) Brian Kernighan's: `while(x) { x &= x-1; count++; }` — O(number of set bits). (3) Built-in: `__builtin_popcount(x)` or `Integer.bitCount(x)` — O(1) on modern hardware.

2. **Q: What is the time complexity of enumerating all submasks of a mask?**
   A: O(2^k) where k is the number of set bits. Over all masks of n bits, total work is O(3^n) by the binomial theorem.

3. **Q: When is bitmask DP applicable?**
   A: When n ≤ 20 (since 2^20 ≈ 10^6), and the problem involves choosing/visiting elements where the order or subset matters. Common in TSP, assignment, Hamiltonian path, and covering problems.

4. **Q: Find the missing number in {0, 1, ..., n} given n numbers.**
   A: XOR all numbers with 0 to n. Pairs cancel, leaving the missing number. Alternatively, compute expected sum minus actual sum.

5. **Q: How do you generate Gray code?**
   A: The i-th Gray code is `i ^ (i >> 1)`. This ensures consecutive codes differ by exactly one bit. Time: O(2^n).

6. **Q: Explain the submask enumeration trick `sub = (sub-1) & mask`.**
   A: Subtracting 1 flips the lowest set bit and all lower bits. ANDing with mask clears any bits not in mask. This produces all submasks in decreasing order, visiting each exactly once.

---

## Cross-References

- [Chapter 33: Bit Manipulation](ch33-bit-manipulation.md) — Foundation: AND, OR, XOR, shifts, and basic tricks
- [Chapter 30: Dynamic Programming Fundamentals](ch30-dp-fundamentals.md) — Bit DP is a specialized DP technique
- [Chapter 128: STL Internals](ch128-stl-internals.md) — `std::bitset` for compile-time bit operations
- [Chapter 98: Splay Trees](ch98-splay-trees.md) — XOR-based hashing in tree structures
- [Chapter 145: Approximation Algorithms](ch145-approximation-algorithms.md) — TSP approximation vs exact bit DP solution

---

## Summary

| Technique | Time | Best For |
|---|---|---|
| Subset enumeration | O(2^n) | Iterate all subsets |
| Submask enumeration | O(3^n) total | Subset of subset |
| Popcount | O(1) builtin | Count bits |
| Bit DP | O(2^n × n^2) | TSP, assignment |
| XOR tricks | O(n) | Unique elements, parity |
| Gray code | O(2^n) | Consecutive single-bit change |
