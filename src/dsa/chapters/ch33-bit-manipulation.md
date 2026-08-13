# Chapter 33: Bit Manipulation

Bit manipulation is the art of solving problems by directly operating on the binary representations of integers. It is one of the most elegant categories in competitive programming and technical interviews. Mastery of bitwise operators — AND (`&`), OR (`|`), XOR (`^`), NOT (`~`), left shift (`<<`), and right shift (`>>`) — unlocks solutions that are both time- and space-optimal. In this chapter we build from fundamentals to advanced bitmask enumeration, finish with classic interview problems, and provide complete, compilable C++17 code for every example.

---

## 33.1 Bit Basics

### 33.1.1 Binary Representation

Every non-negative integer can be represented as a sequence of bits. In C++ a 32-bit `int` stores values using 32 binary digits. For example:

```
42  = 00000000 00000000 00000000 00101010
```

The rightmost bit is the **Least Significant Bit (LSB)**, and the leftmost bit is the **Most Significant Bit (MSB)**.

| Operator | Symbol | Description |
|----------|--------|-------------|
| AND | `&` | 1 only if both bits are 1 |
| OR | `\|` | 1 if at least one bit is 1 |
| XOR | `^` | 1 if bits differ |
| NOT | `~` | Flips every bit |
| Left Shift | `<<` | Shifts bits left, fills with 0 |
| Right Shift | `>>` | Shifts bits right (arithmetic for signed) |

### 33.1.2 Two's Complement

Signed integers in C++ use two's complement representation. The MSB is the sign bit: 0 for non-negative, 1 for negative. To negate a number in two's complement:

1. Flip all bits (one's complement).
2. Add 1.

Example: `-5` in 8-bit two's complement:
```
5    = 00000101
~5   = 11111010
~5+1 = 11111011  → this is -5
```

A critical property: `-x == (~x + 1)`, which also means `x & (-x)` isolates the lowest set bit.

### 33.1.3 Basic Bit Operations in C++

```cpp
#include <iostream>
#include <bitset>
using namespace std;

int main() {
    int a = 42;  // 101010
    int b = 15;  // 001111

    cout << "a & b  = " << (a & b)  << endl;   // 10  = 1010
    cout << "a | b  = " << (a | b)  << endl;   // 47  = 101111
    cout << "a ^ b  = " << (a ^ b)  << endl;   // 37  = 100101
    cout << "~a     = " << (~a)     << endl;   // -43 (two's complement)
    cout << "a << 2 = " << (a << 2) << endl;   // 168 = 10101000
    cout << "a >> 2 = " << (a >> 2) << endl;   // 10  = 1010

    // Check if the i-th bit is set (0-indexed from LSB)
    int i = 3;
    bool bitSet = (a >> i) & 1;
    cout << "Bit " << i << " of " << a << " is " << bitSet << endl; // 1

    // Set the i-th bit
    int c = a | (1 << i);
    cout << "After setting bit " << i << ": " << c << endl;

    // Clear the i-th bit
    int d = a & ~(1 << i);
    cout << "After clearing bit " << i << ": " << d << endl;

    // Toggle the i-th bit
    int e = a ^ (1 << i);
    cout << "After toggling bit " << i << ": " << e << endl;

    return 0;
}
```

**Complexity:** All bitwise operations are O(1) on fixed-width integers.

---

## 33.2 Common Tricks

### 33.2.1 Check if a Number is a Power of Two

A power of two has exactly one set bit. The trick `n & (n - 1)` clears the lowest set bit. If the result is 0, the number was a power of two (or zero — handle the edge case).

```cpp
#include <iostream>
using namespace std;

bool isPowerOfTwo(int n) {
    return n > 0 && (n & (n - 1)) == 0;
}

int main() {
    for (int x : {1, 2, 3, 4, 16, 18, 0, -1}) {
        cout << x << " → " << (isPowerOfTwo(x) ? "YES" : "NO") << endl;
    }
    return 0;
}
```

**Dry run with n = 16:**
```
n     = 10000
n - 1 = 01111
n & (n-1) = 00000 → power of two ✓
```

**Dry run with n = 18:**
```
n     = 10010
n - 1 = 10001
n & (n-1) = 10000 ≠ 0 → not a power of two ✓
```

### 33.2.2 Count Set Bits — Brian Kernighan's Algorithm

Naively checking each bit takes O(k) where k = number of bits. Brian Kernighan's trick: repeatedly clear the lowest set bit and count how many times you do it.

```cpp
#include <iostream>
using namespace std;

int countSetBits(int n) {
    int count = 0;
    while (n) {
        n &= (n - 1);  // clear lowest set bit
        count++;
    }
    return count;
}

// Alternative: __builtin_popcount (GCC/Clang)
int countSetBitsBuiltin(int n) {
    return __builtin_popcount(n);
}

int main() {
    cout << "Set bits in 42 (101010): " << countSetBits(42) << endl;  // 3
    cout << "Set bits in 255: " << countSetBits(255) << endl;          // 8
    cout << "Builtin 42: " << countSetBitsBuiltin(42) << endl;        // 3
    return 0;
}
```

**Complexity:** O(number of set bits), which is at most O(32) = O(1) for 32-bit integers.

**Dry run with n = 42 (101010):**
| Iteration | n (binary) | n-1 (binary) | n & (n-1) | count |
|-----------|-----------|-------------|-----------|-------|
| 1 | 101010 | 101001 | 101000 | 1 |
| 2 | 101000 | 100111 | 100000 | 2 |
| 3 | 100000 | 011111 | 000000 | 3 |

### 33.2.3 Isolate the Lowest Set Bit

```cpp
int lowestSetBit(int n) {
    return n & (-n);
}
```

**Why it works:** `-n` is `~n + 1`. All bits above the lowest set bit of `n` are flipped, so the AND isolates exactly that one bit.

```
n   = 101100
-n  = 010100
n & (-n) = 000100  → the lowest set bit
```

### 33.2.4 Swap Without Temporary Variable

```cpp
#include <iostream>
using namespace std;

void swapXOR(int &a, int &b) {
    if (&a != &b) {  // avoid self-swap
        a ^= b;
        b ^= a;
        a ^= b;
    }
}

int main() {
    int x = 5, y = 9;
    cout << "Before: x=" << x << " y=" << y << endl;
    swapXOR(x, y);
    cout << "After:  x=" << x << " y=" << y << endl;
    return 0;
}
```

**Proof of correctness:**
```
a = a ^ b           → a holds a^b
b = (a^b) ^ b = a   → b now holds original a
a = (a^b) ^ a = b   → a now holds original b
```

> **Interview Tip:** While the XOR swap is a classic trick, prefer `std::swap` in production code — it's clearer and the compiler optimizes it identically. Mention the XOR swap to demonstrate knowledge, but don't advocate for it.

### 33.2.5 Other Useful Tricks

```cpp
#include <iostream>
using namespace std;

int main() {
    int n = 42;

    // Check if n is even: (n & 1) == 0
    cout << n << " is " << ((n & 1) ? "odd" : "even") << endl;

    // Multiply/divide by 2
    cout << n << " * 2 = " << (n << 1) << endl;
    cout << n << " / 2 = " << (n >> 1) << endl;

    // Toggle case of a letter
    char ch = 'A';
    cout << "Toggle '" << ch << "' → '" << (char)(ch ^ 32) << "'" << endl;
    // 'a' ^ 32 = 'A', 'A' ^ 32 = 'a'  (diff is bit 5)

    // Convert lowercase to uppercase: ch & '_'
    // Convert uppercase to lowercase: ch | ' '
    cout << "Upper 'z' → '" << (char)('z' & '_') << "'" << endl;
    cout << "Lower 'Z' → '" << (char)('Z' | ' ') << "'" << endl;

    return 0;
}
```

**Common Mistake:** Confusing `&` (bitwise AND) with `&&` (logical AND). `3 & 1` is 1, but `3 && 1` is also 1. However `2 & 1` is 0, while `2 && 1` is 1. Always use bitwise operators for bit manipulation.

---

## 33.3 Bitmask Techniques

A **bitmask** is an integer whose bits represent a set. If the i-th bit is 1, element i is in the set.

### 33.3.1 Enumerate All Subsets of a Set

For a set of n elements, there are 2^n subsets. We can enumerate them by iterating from 0 to (1 << n) - 1.

```cpp
#include <iostream>
#include <vector>
#include <string>
using namespace std;

void enumerateSubsets(const vector<string>& elements) {
    int n = elements.size();
    for (int mask = 0; mask < (1 << n); mask++) {
        cout << "{ ";
        for (int i = 0; i < n; i++) {
            if (mask & (1 << i)) {
                cout << elements[i] << " ";
            }
        }
        cout << "}" << endl;
    }
}

int main() {
    vector<string> items = {"A", "B", "C"};
    enumerateSubsets(items);
    return 0;
}
```

**Output:**
```
{ }
{ A }
{ B }
{ A B }
{ C }
{ A C }
{ B C }
{ A B C }
```

**Complexity:** O(2^n × n) — each mask is O(n) to inspect.

### 33.3.2 Checking All Subsets (SOS-style)

A common technique: iterate over all subsets of a given mask.

```cpp
#include <iostream>
using namespace std;

void enumerateSubsetsOfMask(int mask) {
    // Iterate over all submasks of 'mask'
    for (int sub = mask; sub; sub = (sub - 1) & mask) {
        cout << sub << " (binary: ";
        for (int i = 7; i >= 0; i--) cout << ((sub >> i) & 1);
        cout << ")" << endl;
    }
    cout << "0 (empty set)" << endl;
}

int main() {
    int mask = 0b1101;  // elements {0, 2, 3}
    cout << "Subsets of mask " << mask << ":" << endl;
    enumerateSubsetsOfMask(mask);
    return 0;
}
```

**How `sub = (sub - 1) & mask` works:** Subtracting 1 flips the lowest set bit and all bits below it. ANDing with `mask` keeps only the bits that are valid in the original mask. This efficiently generates all submasks in decreasing order.

### 33.3.3 Bitmask as State (DP)

Bitmasks are frequently used in dynamic programming to represent which elements have been visited/used.

```cpp
#include <iostream>
#include <vector>
#include <climits>
using namespace std;

// TSP (Traveling Salesman Problem) using bitmask DP
// dp[mask][i] = minimum cost to visit the set of cities in 'mask', ending at city i
int tsp(const vector<vector<int>>& dist) {
    int n = dist.size();
    int fullMask = (1 << n) - 1;
    vector<vector<int>> dp(1 << n, vector<int>(n, INT_MAX));

    dp[1][0] = 0;  // start at city 0, only city 0 visited

    for (int mask = 1; mask <= fullMask; mask++) {
        for (int u = 0; u < n; u++) {
            if (dp[mask][u] == INT_MAX) continue;
            if (!(mask & (1 << u))) continue;  // u must be in mask
            for (int v = 0; v < n; v++) {
                if (mask & (1 << v)) continue;  // v not yet visited
                int newMask = mask | (1 << v);
                dp[newMask][v] = min(dp[newMask][v], dp[mask][u] + dist[u][v]);
            }
        }
    }

    int ans = INT_MAX;
    for (int u = 0; u < n; u++) {
        if (dp[fullMask][u] != INT_MAX) {
            ans = min(ans, dp[fullMask][u] + dist[u][0]);  // return to start
        }
    }
    return ans;
}

int main() {
    vector<vector<int>> dist = {
        {0, 10, 15, 20},
        {10, 0, 35, 25},
        {15, 35, 0, 30},
        {20, 25, 30, 0}
    };
    cout << "Minimum TSP cost: " << tsp(dist) << endl;  // 80
    return 0;
}
```

**Complexity:** O(2^n × n^2) — the classic bitmask DP complexity for TSP.

---

## 33.4 Bitwise in Algorithms — XOR Properties

XOR has unique algebraic properties that make it indispensable:

| Property | Expression |
|----------|-----------|
| Self-inverse | `a ^ a = 0` |
| Identity | `a ^ 0 = a` |
| Commutative | `a ^ b = b ^ a` |
| Associative | `(a ^ b) ^ c = a ^ (b ^ c)` |

### 33.4.1 Finding the Unique Element

**Problem:** Every element appears twice except one. Find it.

```cpp
#include <iostream>
#include <vector>
using namespace std;

int singleNumber(const vector<int>& nums) {
    int result = 0;
    for (int x : nums) {
        result ^= x;
    }
    return result;
}

int main() {
    vector<int> nums = {2, 3, 2, 4, 4};
    cout << "Single number: " << singleNumber(nums) << endl;  // 3
    return 0;
}
```

**Why it works:** All paired elements cancel out via `a ^ a = 0`, leaving only the unique one.

### 33.4.2 XOR to Swap Two Numbers in an Array

Useful when you need to swap without extra space and the two locations might alias:

```cpp
void xorSwap(int& a, int& b) {
    if (&a != &b) {
        a ^= b ^= a ^= b;
    }
}
```

### 33.4.3 XOR to Find Two Unique Elements

If two elements appear once and all others appear twice, XOR all to get `xorVal = a ^ b`. Then partition by any set bit in `xorVal` — `a` and `b` will land in different groups.

```cpp
#include <iostream>
#include <vector>
using namespace std;

pair<int,int> twoUnique(const vector<int>& nums) {
    int xorVal = 0;
    for (int x : nums) xorVal ^= x;

    // Find rightmost set bit
    int diffBit = xorVal & (-xorVal);

    int a = 0, b = 0;
    for (int x : nums) {
        if (x & diffBit)
            a ^= x;
        else
            b ^= x;
    }
    return {a, b};
}

int main() {
    vector<int> nums = {1, 2, 1, 3, 2, 5};
    auto [a, b] = twoUnique(nums);
    cout << "Two unique: " << a << " and " << b << endl;  // 3 and 5
    return 0;
}
```

---

## 33.5 Interview Problems

### 33.5.1 Single Number (LeetCode 136)

Every element appears twice except one. Find it.

```cpp
#include <iostream>
#include <vector>
using namespace std;

class Solution {
public:
    int singleNumber(vector<int>& nums) {
        int result = 0;
        for (int x : nums) result ^= x;
        return result;
    }
};

int main() {
    Solution sol;
    vector<int> nums1 = {2, 2, 1};
    cout << sol.singleNumber(nums1) << endl;  // 1

    vector<int> nums2 = {4, 1, 2, 1, 2};
    cout << sol.singleNumber(nums2) << endl;  // 4
    return 0;
}
```

**Complexity:** O(n) time, O(1) space.

### 33.5.2 Single Number II (LeetCode 137)

Every element appears three times except one. We need to track bit counts modulo 3.

```cpp
#include <iostream>
#include <vector>
using namespace std;

class Solution {
public:
    // Approach: bit-by-bit counting
    int singleNumber(vector<int>& nums) {
        int result = 0;
        for (int i = 0; i < 32; i++) {
            int bitCount = 0;
            for (int x : nums) {
                bitCount += (x >> i) & 1;
            }
            if (bitCount % 3 != 0) {
                result |= (1 << i);
            }
        }
        return result;
    }

    // Approach: state machine (ones, twos)
    int singleNumberSM(vector<int>& nums) {
        int ones = 0, twos = 0;
        for (int x : nums) {
            ones = (ones ^ x) & ~twos;
            twos = (twos ^ x) & ~ones;
        }
        return ones;
    }
};

int main() {
    Solution sol;
    vector<int> nums = {2, 2, 3, 2};
    cout << sol.singleNumber(nums) << endl;    // 3
    cout << sol.singleNumberSM(nums) << endl;  // 3

    vector<int> nums2 = {0, 1, 0, 1, 0, 1, 99};
    cout << sol.singleNumber(nums2) << endl;    // 99
    return 0;
}
```

**Complexity:** O(32n) = O(n) time, O(1) space for the bit-counting approach. O(n) time, O(1) space for the state machine approach.

**State machine explanation:** Each bit cycles through states: 0 appearances → 1 appearance → 2 appearances → 0 appearances. `ones` tracks bits that have appeared 1 time, `twos` tracks bits that have appeared 2 times. When a bit appears for the 3rd time, it resets.

### 33.5.3 Counting Bits (LeetCode 338)

Given n, return an array where `ans[i]` is the number of 1-bits in `i`.

```cpp
#include <iostream>
#include <vector>
using namespace std;

class Solution {
public:
    // DP approach: ans[i] = ans[i >> 1] + (i & 1)
    vector<int> countBits(int n) {
        vector<int> ans(n + 1);
        for (int i = 1; i <= n; i++) {
            ans[i] = ans[i >> 1] + (i & 1);
        }
        return ans;
    }

    // Alternative: Brian Kernighan's trick
    vector<int> countBitsBK(int n) {
        vector<int> ans(n + 1);
        for (int i = 0; i <= n; i++) {
            int count = 0, x = i;
            while (x) {
                x &= (x - 1);
                count++;
            }
            ans[i] = count;
        }
        return ans;
    }
};

int main() {
    Solution sol;
    auto ans = sol.countBits(5);
    cout << "Counting bits for 0..5: ";
    for (int x : ans) cout << x << " ";
    cout << endl;  // 0 1 1 2 1 2
    return 0;
}
```

**Complexity:** O(n) time, O(n) space for DP approach.

### 33.5.4 Maximum XOR of Two Numbers (LeetCode 421)

Given an array, find the maximum XOR of any two numbers.

```cpp
#include <iostream>
#include <vector>
#include <unordered_set>
using namespace std;

class Solution {
public:
    int findMaximumXOR(vector<int>& nums) {
        int maxXor = 0;
        int mask = 0;
        // Process from MSB to LSB
        for (int i = 31; i >= 0; i--) {
            mask |= (1 << i);
            unordered_set<int> prefixes;
            for (int x : nums) {
                prefixes.insert(x & mask);
            }
            // Try to set the i-th bit in maxXor
            int candidate = maxXor | (1 << i);
            bool found = false;
            for (int p : prefixes) {
                if (prefixes.count(p ^ candidate)) {
                    found = true;
                    break;
                }
            }
            if (found) maxXor = candidate;
        }
        return maxXor;
    }
};

int main() {
    Solution sol;
    vector<int> nums1 = {3, 10, 5, 25, 2, 8};
    cout << "Max XOR: " << sol.findMaximumXOR(nums1) << endl;  // 28

    vector<int> nums2 = {14, 70, 53, 83, 49, 91, 36, 80, 92, 51, 66, 70};
    cout << "Max XOR: " << sol.findMaximumXOR(nums2) << endl;  // 127
    return 0;
}
```

**Complexity:** O(32n) = O(n) time. The greedy approach from MSB ensures we always try the best bit first.

### 33.5.5 Power of Two (LeetCode 231)

```cpp
#include <iostream>
using namespace std;

class Solution {
public:
    bool isPowerOfTwo(int n) {
        return n > 0 && (n & (n - 1)) == 0;
    }
};

int main() {
    Solution sol;
    for (int x : {1, 2, 3, 16, 0, -1, -2147483648}) {
        cout << x << " → " << (sol.isPowerOfTwo(x) ? "true" : "false") << endl;
    }
    return 0;
}
```

**Edge case:** `-2147483648` (INT_MIN) is `1000...000` in binary. `n > 0` check correctly rejects it.

---

## Interview Tips

1. **Know your operators cold.** Be able to compute `n & (n-1)`, `n & (-n)`, `~n + 1` by hand instantly.
2. **Beware of signed vs unsigned shifts.** Right-shifting a negative signed integer is implementation-defined in C++. Prefer `unsigned int` or explicit bitmasks when the sign matters.
3. **Think in terms of individual bits.** Many problems that seem mathematical can be solved bit-by-bit (e.g., Single Number II).
4. **Bitmask DP is a pattern.** When you see "small n" (≤ 20) with a subset/assignment problem, think bitmask DP.
5. **XOR tricks come up frequently.** Self-inverse property → finding unique elements, swapping, and encryption.

## Common Mistakes

- **Operator precedence:** `&` has lower precedence than `==`. Always write `(n & (n-1)) == 0`, not `n & (n-1) == 0`.
- **Overflow with shifts:** `1 << 31` on a 32-bit signed int is undefined behavior. Use `1LL << 31` or `1U << 31`.
- **Forgetting edge cases:** `isPowerOfTwo(0)` should return false. `countSetBits(0)` should return 0.
- **Self-XOR swap:** `a ^= a ^= a ^= b` is undefined behavior due to unsequenced modifications. Use a temporary or check for self-swap.

## Practice Problems

1. **Reverse Bits** (LeetCode 190) — Reverse the bits of a 32-bit unsigned integer. *Hint: Process bit by bit, or use divide-and-conquer with masks.*
2. **Bitwise AND of Numbers Range** (LeetCode 201) — Find the AND of all numbers in [m, n]. *Hint: The result keeps only the common prefix bits of m and n.*
3. **Subsets** (LeetCode 78) — Generate all subsets using bitmask enumeration. *Hint: Iterate mask from 0 to (1<<n)-1.*
4. **Sum of Two Integers** (LeetCode 371) — Add two integers without using + or -. *Hint: XOR gives sum without carry, AND gives carry bits. Shift carry left and repeat.*
5. **Maximum Product of Word Lengths** (LeetCode 318) — Use bitmasks to represent character sets for O(1) overlap checking. *Hint: Each word's character set is a 26-bit mask.*
