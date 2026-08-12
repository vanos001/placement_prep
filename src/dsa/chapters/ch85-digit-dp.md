# Chapter 85: Digit DP

## Prerequisites

- Dynamic programming fundamentals (Chapter 30)
- Recursion with memoization
- Bit manipulation basics (Chapter 33)
- Number theory basics

## Interview Frequency: ★★★

Digit DP is a powerful technique for counting integers in a range [L, R] that satisfy properties depending on their digits. It appears frequently in **Google**, **Amazon**, **Meta**, and competitive programming contests.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Count numbers with property | ★★★ | Medium | Classic digit DP |
| Digit sum problems | ★★ | Medium | Sum of digits as state |
| Divisibility by digits | ★★ | Medium | Remainder as state |
| Bitmask digit constraints | ★★★ | Medium | Track used digits |
| Range queries [L, R] | ★★★ | Medium | Use f(R) - f(L-1) |

---

## 85.1 What Is Digit DP?

**Digit DP** is a dynamic programming technique that processes a number **digit by digit** (from most significant to least significant) while tracking constraints imposed by the upper bound.

### The Core Problem

Given a range [L, R] and a property P, count how many integers x ∈ [L, R] satisfy P(x), where P depends on the digits of x.

Examples of properties:
- "Has digit sum equal to K"
- "Has no two consecutive equal digits"
- "Is divisible by K"
- "Contains exactly K distinct digits"
- "Has an even number of odd digits"

### Why Not Brute Force?

For R up to 10¹⁸, iterating through all numbers is impossible. Digit DP exploits the fact that numbers with the same prefix behave identically, allowing us to memoize subproblems.

---

## 85.2 Intuition: Processing Digit by Digit

Consider counting numbers ≤ 327 that have digit sum = 10.

We process from left to right:
- **Position 0 (hundreds)**: Can choose 0, 1, 2, or 3.
  - If we choose 0, 1, or 2: remaining digits are unconstrained (can be 0-9).
  - If we choose 3: remaining digits must form a number ≤ 27.
- **Position 1 (tens)**: Depends on previous choice.
- **Position 2 (ones)**: Final digit.

The **tight** flag tracks whether we're still bounded by the upper limit. If we chose 2 at position 0 (when the limit digit is 3), we're no longer tight — remaining digits can be anything 0-9.

---

## 85.3 Formal Definition

### State

```
dp[pos][tight][state] = count of valid numbers from position `pos` onward,
                        given:
                        - tight: whether we're still bounded by the upper limit
                        - state: problem-specific state (digit sum, remainder, bitmask, etc.)
```

### Transition

At each position, iterate over possible digits d from 0 to `limit`:
- `limit = upper_digit[pos]` if tight, else 9
- Update state based on the problem
- Recurse to next position with updated tight flag

### Base Case

When `pos == number_of_digits`: check if the final state satisfies the property.

### Range Query

Count in [L, R] = count(≤ R) - count(≤ L - 1)

---

## 85.4 Step-by-Step Walkthrough

### Problem: Count numbers in [1, N] with digit sum = K

Let N = 235, K = 7.

**State**: `dp[pos][sum][tight]`

**Processing**:
- Position 0 (hundreds digit, limit = 2):
  - d=0: sum=0, tight=false → free to choose 0-9 for remaining
  - d=1: sum=1, tight=false → free
  - d=2: sum=2, tight=true → must respect remaining limit "35"
- Position 1 (tens digit):
  - From (pos=1, sum=0, tight=false): d can be 0-9
  - From (pos=1, sum=2, tight=true): d can be 0-3
  - ... and so on
- Position 2 (ones digit): check if sum == K at the end

**Memoization**: Many subproblems are identical (same position, same sum, same tight). Cache them.

---

## 85.5 General Template

```cpp
#include <iostream>
#include <vector>
#include <cstring>
#include <string>
#include <functional>

long long digitDP(long long n) {
    std::string num = std::to_string(n);
    int len = num.size();

    // dp[pos][tight][...] — problem-specific dimensions
    // Use -1 for unvisited states
    // Example: dp[pos][tight][sum]
    // For memoization, we use a lambda with capture

    // This template shows the skeleton; customize the state dimension
    // for each specific problem.

    // For this example: count numbers with digit sum == K
    // (K is passed as a parameter in the actual implementation below)

    return 0; // Placeholder — see complete examples below
}
```

---

## 85.6 Example 1: Count Numbers Without Consecutive Identical Digits

**Problem**: Count numbers in [1, N] where no two adjacent digits are the same.

**State**: `dp[pos][last_digit][tight]`
- `pos`: current position
- `last_digit`: the digit placed at the previous position (0-9, or -1 for start)
- `tight`: bounded flag

### C++ Implementation

```cpp
#include <iostream>
#include <cstring>
#include <string>

using namespace std;

long long dp[20][11][2]; // pos, last_digit (10 = no previous), tight
string num;

long long solve(int pos, int lastDigit, bool tight) {
    if (pos == (int)num.size()) return 1; // Valid number formed

    if (dp[pos][lastDigit][tight] != -1) return dp[pos][lastDigit][tight];

    long long result = 0;
    int limit = tight ? num[pos] - '0' : 9;

    for (int d = 0; d <= limit; d++) {
        if (d == lastDigit) continue; // Skip consecutive same digit
        result += solve(pos + 1, d, tight && (d == limit));
    }

    return dp[pos][lastDigit][tight] = result;
}

long long countNoConsecutive(long long n) {
    num = to_string(n);
    memset(dp, -1, sizeof(dp));
    return solve(0, 10, true); // 10 = no previous digit
}

int main() {
    long long L = 1, R = 1000;
    cout << "Count in [1, " << R << "] without consecutive identical digits: "
         << countNoConsecutive(R) << "\n";

    // Range query
    L = 100; R = 500;
    cout << "Count in [" << L << ", " << R << "]: "
         << countNoConsecutive(R) - countNoConsecutive(L - 1) << "\n";

    return 0;
}
```

### Python Implementation

```python
from functools import lru_cache

def count_no_consecutive(n: int) -> int:
    num = str(n)

    @lru_cache(maxsize=None)
    def solve(pos: int, last_digit: int, tight: bool) -> int:
        if pos == len(num):
            return 1

        limit = int(num[pos]) if tight else 9
        result = 0

        for d in range(0, limit + 1):
            if d == last_digit:
                continue
            result += solve(pos + 1, d, tight and (d == limit))

        return result

    return solve(0, 10, True)  # 10 = no previous digit

if __name__ == "__main__":
    print(f"Count in [1, 1000]: {count_no_consecutive(1000)}")
    print(f"Count in [100, 500]: {count_no_consecutive(500) - count_no_consecutive(99)}")
```

### Java Implementation

```java
import java.util.*;

public class DigitDPNoConsecutive {
    static long[][][] dp;
    static String num;

    static long solve(int pos, int lastDigit, boolean tight) {
        if (pos == num.length()) return 1;

        int tightIdx = tight ? 1 : 0;
        if (dp[pos][lastDigit][tightIdx] != -1) return dp[pos][lastDigit][tightIdx];

        long result = 0;
        int limit = tight ? num.charAt(pos) - '0' : 9;

        for (int d = 0; d <= limit; d++) {
            if (d == lastDigit) continue;
            result += solve(pos + 1, d, tight && (d == limit));
        }

        return dp[pos][lastDigit][tightIdx] = result;
    }

    static long countNoConsecutive(long n) {
        num = Long.toString(n);
        dp = new long[num.length()][11][2];
        for (long[][] arr2 : dp)
            for (long[] arr1 : arr2)
                Arrays.fill(arr1, -1);
        return solve(0, 10, true);
    }

    public static void main(String[] args) {
        System.out.println("Count in [1, 1000]: " + countNoConsecutive(1000));
        System.out.println("Count in [100, 500]: " +
            (countNoConsecutive(500) - countNoConsecutive(99)));
    }
}
```

---

## 85.7 Example 2: Count Numbers Where Digit Sum Equals K

**Problem**: Count numbers in [1, N] where the sum of digits equals K.

**State**: `dp[pos][sum][tight]`

### C++ Implementation

```cpp
#include <iostream>
#include <cstring>
#include <string>

using namespace std;

long long dp[20][200][2]; // pos, sum, tight
string num;
int targetSum;

long long solve(int pos, int sum, bool tight) {
    if (pos == (int)num.size()) return sum == targetSum ? 1 : 0;

    if (dp[pos][sum][tight] != -1) return dp[pos][sum][tight];

    long long result = 0;
    int limit = tight ? num[pos] - '0' : 9;

    for (int d = 0; d <= limit; d++) {
        if (sum + d > targetSum) break; // Pruning
        result += solve(pos + 1, sum + d, tight && (d == limit));
    }

    return dp[pos][sum][tight] = result;
}

long long countWithDigitSum(long long n, int k) {
    num = to_string(n);
    targetSum = k;
    memset(dp, -1, sizeof(dp));
    return solve(0, 0, true);
}

int main() {
    long long N = 1000;
    int K = 10;
    cout << "Count in [1, " << N << "] with digit sum = " << K << ": "
         << countWithDigitSum(N, K) << "\n";

    // Range query
    long long L = 100, R = 500;
    K = 15;
    cout << "Count in [" << L << ", " << R << "] with digit sum = " << K << ": "
         << countWithDigitSum(R, K) - countWithDigitSum(L - 1, K) << "\n";

    return 0;
}
```

### Python Implementation

```python
from functools import lru_cache

def count_with_digit_sum(n: int, k: int) -> int:
    num = str(n)

    @lru_cache(maxsize=None)
    def solve(pos: int, current_sum: int, tight: bool) -> int:
        if pos == len(num):
            return 1 if current_sum == k else 0

        limit = int(num[pos]) if tight else 9
        result = 0

        for d in range(0, limit + 1):
            if current_sum + d > k:
                break
            result += solve(pos + 1, current_sum + d, tight and (d == limit))

        return result

    return solve(0, 0, True)

if __name__ == "__main__":
    print(f"Count in [1, 1000] with digit sum = 10: {count_with_digit_sum(1000, 10)}")
    print(f"Count in [100, 500] with digit sum = 15: "
          f"{count_with_digit_sum(500, 15) - count_with_digit_sum(99, 15)}")
```

---

## 85.8 Example 3: Count Numbers Divisible by K

**Problem**: Count numbers in [1, N] where the number itself is divisible by K.

**State**: `dp[pos][remainder][tight]`

### C++ Implementation

```cpp
#include <iostream>
#include <cstring>
#include <string>

using namespace std;

long long dp[20][10000][2]; // pos, remainder, tight
string num;
int divisor;

long long solve(int pos, int rem, bool tight) {
    if (pos == (int)num.size()) return rem == 0 ? 1 : 0;

    if (dp[pos][rem][tight] != -1) return dp[pos][rem][tight];

    long long result = 0;
    int limit = tight ? num[pos] - '0' : 9;

    for (int d = 0; d <= limit; d++) {
        int newRem = (rem * 10 + d) % divisor;
        result += solve(pos + 1, newRem, tight && (d == limit));
    }

    return dp[pos][rem][tight] = result;
}

long long countDivisibleBy(long long n, int k) {
    num = to_string(n);
    divisor = k;
    memset(dp, -1, sizeof(dp));
    return solve(0, 0, true);
}

int main() {
    long long N = 1000;
    int K = 7;
    cout << "Count in [1, " << N << "] divisible by " << K << ": "
         << countDivisibleBy(N, K) << "\n";
    return 0;
}
```

---

## 85.9 Example 4: Count Numbers with Exactly K Distinct Digits

**Problem**: Count numbers in [1, N] that use exactly K distinct digits.

**State**: `dp[pos][tight][mask]` — where `mask` is a bitmask of digits used (10 bits).

### C++ Implementation

```cpp
#include <iostream>
#include <cstring>
#include <string>
#include <bitset>

using namespace std;

long long dp[20][2][1024]; // pos, tight, mask (10 bits for digits 0-9)
string num;
int targetDistinct;

long long solve(int pos, bool tight, int mask) {
    if (pos == (int)num.size()) {
        int count = __builtin_popcount(mask);
        return count == targetDistinct ? 1 : 0;
    }

    int tightIdx = tight ? 1 : 0;
    if (dp[pos][tightIdx][mask] != -1) return dp[pos][tightIdx][mask];

    long long result = 0;
    int limit = tight ? num[pos] - '0' : 9;

    for (int d = 0; d <= limit; d++) {
        int newMask = mask | (1 << d);
        // Pruning: if we already have more than target distinct digits, skip
        if (__builtin_popcount(newMask) > targetDistinct) continue;
        result += solve(pos + 1, tight && (d == limit), newMask);
    }

    return dp[pos][tightIdx][mask] = result;
}

long long countWithKDistinct(long long n, int k) {
    num = to_string(n);
    targetDistinct = k;
    memset(dp, -1, sizeof(dp));
    return solve(0, true, 0);
}

int main() {
    long long N = 10000;
    for (int k = 1; k <= 5; k++) {
        cout << "Count in [1, " << N << "] with exactly " << k << " distinct digits: "
             << countWithKDistinct(N, k) << "\n";
    }
    return 0;
}
```

---

## 85.10 Example 5: Sum of Digit Sums in Range

**Problem**: Find the sum of digit sums of all numbers in [1, N].

**State**: `dp[pos][sum][tight]` — but now we track the **sum of answers**, not just count.

This requires a slightly different DP formulation where we accumulate the answer rather than counting.

### C++ Implementation

```cpp
#include <iostream>
#include <cstring>
#include <string>

using namespace std;

// dp[pos][tight] = {count, sum_of_digit_sums}
pair<long long, long long> dp[20][2];
bool visited[20][2];
string num;

pair<long long, long long> solve(int pos, bool tight) {
    if (pos == (int)num.size()) return {1, 0}; // 1 number, digit sum 0

    int tightIdx = tight ? 1 : 0;
    if (visited[pos][tightIdx]) return dp[pos][tightIdx];

    long long totalCount = 0, totalSum = 0;
    int limit = tight ? num[pos] - '0' : 9;

    for (int d = 0; d <= limit; d++) {
        auto [cnt, s] = solve(pos + 1, tight && (d == limit));
        totalCount += cnt;
        totalSum += s + cnt * d; // Each of the cnt numbers contributes d to its digit sum
    }

    visited[pos][tightIdx] = true;
    return dp[pos][tightIdx] = {totalCount, totalSum};
}

long long sumOfDigitSums(long long n) {
    num = to_string(n);
    memset(visited, false, sizeof(visited));
    return solve(0, true).second;
}

int main() {
    long long N = 100;
    cout << "Sum of digit sums in [1, " << N << "]: " << sumOfDigitSums(N) << "\n";

    N = 1000;
    cout << "Sum of digit sums in [1, " << N << "]: " << sumOfDigitSums(N) << "\n";

    return 0;
}
```

---

## 85.11 Common Digit DP Patterns

| Problem | State Dimensions | Transition |
|---|---|---|
| Count with digit sum = K | `dp[pos][sum][tight]` | Add digit to sum |
| No consecutive same digits | `dp[pos][last][tight]` | Skip if same as last |
| Divisible by K | `dp[pos][remainder][tight]` | Update remainder: `rem = (rem*10 + d) % K` |
| Contains specific digit | `dp[pos][found][tight]` | Set `found = true` if digit matches |
| Exactly K distinct digits | `dp[pos][mask][tight]` | Update bitmask: `mask |= (1 << d)` |
| At most K distinct digits | `dp[pos][mask][tight]` | Same, with pruning |
| Sum of digit sums | `dp[pos][tight]` returning `{count, sum}` | Accumulate sum with contribution |
| Product of digits = K | `dp[pos][product][tight]` | Multiply, handle 0 carefully |
| Number is a perfect square | Check at base case | Expensive — may need sqrt check |
| Digits are non-decreasing | `dp[pos][last][tight]` | Only allow `d >= last` |

---

## 85.12 Advanced Techniques

### 1. Leading Zeros

Some problems require handling leading zeros carefully. For example, "count numbers with exactly K digits" vs "count numbers ≤ N."

**Solution**: Add a `started` flag to the state: `dp[pos][started][tight][...]`.

```cpp
// Skip leading zeros without counting them as digits
if (d == 0 && !started) {
    result += solve(pos + 1, false, tight && (d == limit), ...);
} else {
    result += solve(pos + 1, true, tight && (d == limit), ...);
}
```

### 2. Multiple Bounds

For problems with constraints on multiple numbers (e.g., "count pairs (a, b) where a + b = C"), process both numbers simultaneously with separate tight flags.

### 3. Digit DP with Bitmask

When tracking which digits have been used, a 10-bit mask suffices. This is common in problems like "count numbers that are pandigital" or "count numbers using only certain digits."

### 4. Optimizing Memory

For large ranges (10^18), the number of digits is at most 19. Use a hash map or `unordered_map` for the state if the state space is sparse.

---

## 85.13 Complexity Analysis

| Aspect | Value | Notes |
|---|---|---|
| Time | O(D × S × 10) | D = number of digits, S = state space size |
| Space | O(D × S × 2) | 2 for tight flag |
| For N ≤ 10^18 | D ≤ 19 | Very fast |
| State space examples | | |
| — Digit sum | S = O(9 × D) | Max sum = 9 × 19 = 171 |
| — Remainder mod K | S = K | Can be large if K is big |
| — Bitmask (10 digits) | S = 1024 | 2^10 |
| — Last digit | S = 11 | 0-9 plus "none" |

### Typical Runtime

For most competitive programming problems, digit DP runs in well under 1 second because:
- D ≤ 19 (for 64-bit integers)
- State space is small
- Each transition iterates over at most 10 digits

---

## 85.14 Common Pitfalls

1. **Off-by-one in range queries**: `count(L, R) = count(≤R) - count(≤L-1)`. Make sure `count(≤0)` is handled correctly.

2. **Leading zeros**: If the problem says "numbers with exactly K digits," don't count numbers with leading zeros. Use a `started` flag.

3. **Tight flag propagation**: `tight = tight && (d == limit)`. A common mistake is to forget the `&&` — once you're not tight, you stay not tight.

4. **Memoization with tight**: When `tight = true`, the state depends on the specific upper bound, so caching may not help. However, for a single query, this is fine.

5. **State explosion**: If the state has too many dimensions or large ranges, the DP table may be too large. Consider using a hash map or reducing the state.

6. **Forgetting to reset**: When solving multiple test cases, always clear the memoization table.

---

## 85.15 Exercises

### Exercise 1: Count Numbers with Even Digit Sum
Count numbers in [1, N] where the sum of digits is even.

### Exercise 2: Count Numbers Where No Digit Appears More Than Twice
Count numbers in [1, N] where each digit (0-9) appears at most twice.

### Exercise 3: Count Numbers That Are Multiples of Both 3 and 5
Count numbers in [1, N] divisible by 15, using digit DP (verify with the formula N/15).

### Exercise 4: Sum of k-th Powers of Digit Sums
For a given k, compute the sum of (digit_sum(x))^k for all x in [1, N].

### Exercise 5: Count Numbers with At Most K Distinct Digits
Count numbers in [1, N] that use at most K distinct digits. Use bitmask state.

### Exercise 6: Count "Beautiful" Numbers
A number is "beautiful" if the product of its non-zero digits equals the sum of its digits. Count beautiful numbers in [1, N].

---

## 85.16 Interview Questions

### Q1: What is the time complexity of Digit DP?
**Answer**: O(D × |state| × 10), where D is the number of digits and |state| is the size of the problem-specific state dimension. For 64-bit integers, D ≤ 19, making it very efficient.

### Q2: How do you handle the range [L, R]?
**Answer**: Compute `f(R) - f(L-1)`, where `f(N)` counts numbers in [0, N] satisfying the property. This converts the range problem into a prefix problem.

### Q3: What is the role of the "tight" flag?
**Answer**: The tight flag indicates whether the prefix we've built so far exactly matches the prefix of the upper bound. When tight = true, the current digit is limited by the corresponding digit in N. When tight = false, we can choose any digit 0-9.

### Q4: How would you count numbers in [1, 10^100] with digit sum divisible by K?
**Answer**: State: `dp[pos][remainder_of_sum_mod_K][tight]`. The number of digits is at most 100, and the remainder space is K, so the DP table is 100 × K × 2. For K ≤ 1000, this is very manageable.

### Q5: Can Digit DP handle negative numbers or floating-point numbers?
**Answer**: Not directly. Digit DP is designed for non-negative integers. For negative numbers, handle the sign separately. For floating-point, convert to integer representation or use a different approach.

### Q6: How do you optimize Digit DP when the state space is large?
**Answer**: Use a hash map instead of a fixed-size array for memoization. Also, add pruning (e.g., if the remaining digits can't possibly satisfy the constraint, return 0 early).

---

## 85.17 Cross-References

- **Chapter 30: DP Fundamentals** — Prerequisite: understand state design, transitions, and memoization before tackling digit DP.
- **Chapter 31: DP Patterns** — Digit DP is one of many DP patterns; see also bitmask DP, interval DP, and tree DP.
- **Chapter 33: Bit Manipulation** — When tracking which digits have been used, bitmask states are common in digit DP.
- **Chapter 86: DP Optimization** — Digit DP states can sometimes be optimized using matrix exponentiation or other techniques.
- **Chapter 1: Binary Search** — Some digit DP problems can be solved with binary search + digit DP (e.g., "find the k-th number with property P").
- **Chapter 34: Number Theory** — Divisibility-based digit DP problems connect to modular arithmetic.

---

## Summary

| Aspect | Detail |
|---|---|
| Technique | Process numbers digit by digit with memoization |
| State | `dp[pos][tight][problem_specific_state]` |
| Time | O(D × S × 10) where D = digits, S = state size |
| Range queries | Use `f(R) - f(L-1)` |
| Key insight | Numbers with the same prefix and state behave identically |
| Common states | Digit sum, remainder, last digit, bitmask |
| Applications | Counting, summing, and optimization over digit properties |
| Compared to brute force | Handles ranges up to 10^18 efficiently |
