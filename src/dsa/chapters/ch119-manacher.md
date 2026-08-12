# Chapter 119: Manacher's Algorithm

## Prerequisites
- Palindromes, string basics ([Chapter 102](ch102-wavelet-trees.md))
- Two-pointer technique ([Chapter 107](ch107-hld-centroid-applications.md))

## Interview Frequency: ★★★

Find all palindromic substrings in O(n). **Google** and **Amazon** test this. It's the kind of algorithm that's hard to invent under pressure but beautiful once you understand it.

---

## 119.1 Definition and Motivation

### What is a Palindrome?

A string that reads the same forwards and backwards: `racecar`, `abba`, `a`.

### The Problem

Given a string `s`, find:
1. The longest palindromic substring
2. All palindromic substrings
3. The count of palindromic substrings

### Naïve Approach: O(n³)

For every pair (i, j), check if s[i..j] is a palindrome.

```python
def longest_palindrome_naive(s):
    n = len(s)
    best = ""
    for i in range(n):
        for j in range(i, n):
            sub = s[i:j+1]
            if sub == sub[::-1] and len(sub) > len(best):
                best = sub
    return best
```

### Better: Expand Around Center — O(n²)

Every palindrome has a center. For each possible center, expand outward while characters match.

```python
def expand(s, left, right):
    while left >= 0 and right < len(s) and s[left] == s[right]:
        left -= 1
        right += 1
    return s[left+1:right]

def longest_palindrome_expand(s):
    best = ""
    for i in range(len(s)):
        odd = expand(s, i, i)       # Odd-length palindromes
        even = expand(s, i, i+1)    # Even-length palindromes
        best = max(best, odd, even, key=len)
    return best
```

This is O(n²) — good, but Manacher's does it in O(n).

---

## 119.2 The Key Insight

When expanding around center `i`, if we've already found a large palindrome centered at some `j < i`, we can **reuse** that information.

### Mirror Property

If there's a palindrome centered at `C` with right boundary `R`, then for any position `i` inside this palindrome, its **mirror** position `i' = 2C - i` has already computed the palindrome radius at `i'`.

```
     L        C        R
     |--------|--------|
          i'      i
```

The palindrome at `i` is at least as large as the palindrome at `i'`, **but** it can't extend past `R` (we haven't verified characters beyond `R` yet).

### Three Cases

1. **i is outside the current palindrome** (i > R): We know nothing, expand naively.
2. **i is inside, and mirror palindrome fits** (i' palindrome doesn't cross L): `d[i] = d[i']`
3. **i is inside, but mirror palindrome crosses L**: `d[i] = R - i` (limited by boundary), then expand further.

---

## 119.3 The Algorithm

Manacher's works on a transformed string to handle both odd and even length palindromes uniformly.

### Transformation

Insert a special character between every pair of characters and at the ends:

```
"abba" → "^#a#b#b#a#$"
"abc"  → "^#a#b#c#$"
```

Now every palindrome has odd length in the transformed string.

### Code

**C++ (Standard Implementation)**

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

// Returns array where d1[i] = radius of odd palindrome centered at i
// d2[i] = radius of even palindrome centered between i-1 and i
std::pair<std::vector<int>, std::vector<int>> manacher(const std::string& s) {
    int n = s.size();
    std::vector<int> d1(n), d2(n);
    
    // Odd length palindromes
    for (int i = 0, l = 0, r = -1; i < n; i++) {
        int k = (i > r) ? 1 : std::min(d1[l + r - i], r - i + 1);
        while (i - k >= 0 && i + k < n && s[i - k] == s[i + k]) k++;
        d1[i] = k--;
        if (i + k > r) { l = i - k; r = i + k; }
    }
    
    // Even length palindromes
    for (int i = 0, l = 0, r = -1; i < n; i++) {
        int k = (i > r) ? 0 : std::min(d2[l + r - i + 1], r - i + 1);
        while (i - k - 1 >= 0 && i + k < n && s[i - k - 1] == s[i + k]) k++;
        d2[i] = k--;
        if (i + k > r) { l = i - k - 1; r = i + k; }
    }
    
    return {d1, d2};
}

int main() {
    std::string s = "abacaba";
    auto [d1, d2] = manacher(s);
    
    // Longest palindromic substring
    int maxLen = 0, center = 0;
    for (int i = 0; i < (int)s.size(); i++) {
        if (2 * d1[i] - 1 > maxLen) { maxLen = 2 * d1[i] - 1; center = i; }
        if (2 * d2[i] > maxLen) { maxLen = 2 * d2[i]; center = i; }
    }
    
    std::cout << "Longest palindrome length: " << maxLen << "\n";
    
    // Count all palindromic substrings
    long long count = 0;
    for (int x : d1) count += x;  // d1[i] odd-length palindromes centered at i
    for (int x : d2) count += x;  // d2[i] even-length palindromes centered at i
    std::cout << "Count of palindromes: " << count << "\n";
    
    return 0;
}
```

**Python**

```python
def manacher(s):
    n = len(s)
    d1 = [0] * n  # Odd-length palindromes
    d2 = [0] * n  # Even-length palindromes
    
    # Odd length
    l, r = 0, -1
    for i in range(n):
        k = 1 if i > r else min(d1[l + r - i], r - i + 1)
        while i - k >= 0 and i + k < n and s[i - k] == s[i + k]:
            k += 1
        d1[i] = k
        k -= 1
        if i + k > r:
            l, r = i - k, i + k
    
    # Even length
    l, r = 0, -1
    for i in range(n):
        k = 0 if i > r else min(d2[l + r - i + 1], r - i + 1)
        while i - k - 1 >= 0 and i + k < n and s[i - k - 1] == s[i + k]:
            k += 1
        d2[i] = k
        k -= 1
        if i + k > r:
            l, r = i - k - 1, i + k
    
    return d1, d2

def longest_palindrome(s):
    d1, d2 = manacher(s)
    max_len, center = 0, 0
    for i in range(len(s)):
        if 2 * d1[i] - 1 > max_len:
            max_len, center = 2 * d1[i] - 1, i
        if 2 * d2[i] > max_len:
            max_len, center = 2 * d2[i], i
    # Extract the palindrome
    if max_len % 2 == 1:
        radius = d1[center]
        return s[center - radius + 1: center + radius]
    else:
        radius = d2[center]
        return s[center - radius: center + radius]

s = "abacaba"
d1, d2 = manacher(s)
print(f"Longest palindrome: {longest_palindrome(s)}")  # "abacaba"
print(f"Count of palindromes: {sum(d1) + sum(d2)}")     # 12
```

**Java**

```java
public class Manacher {
    // Returns d1 (odd radii) and d2 (even radii)
    public static int[][] manacher(String s) {
        int n = s.length();
        int[] d1 = new int[n], d2 = new int[n];
        
        // Odd
        for (int i = 0, l = 0, r = -1; i < n; i++) {
            int k = (i > r) ? 1 : Math.min(d1[l + r - i], r - i + 1);
            while (i - k >= 0 && i + k < n && s.charAt(i - k) == s.charAt(i + k)) k++;
            d1[i] = k--;
            if (i + k > r) { l = i - k; r = i + k; }
        }
        
        // Even
        for (int i = 0, l = 0, r = -1; i < n; i++) {
            int k = (i > r) ? 0 : Math.min(d2[l + r - i + 1], r - i + 1);
            while (i - k - 1 >= 0 && i + k < n && s.charAt(i - k - 1) == s.charAt(i + k)) k++;
            d2[i] = k--;
            if (i + k > r) { l = i - k - 1; r = i + k; }
        }
        
        return new int[][]{d1, d2};
    }
    
    public static void main(String[] args) {
        String s = "abacaba";
        int[][] result = manacher(s);
        int[] d1 = result[0], d2 = result[1];
        
        int maxLen = 0;
        for (int i = 0; i < s.length(); i++) {
            maxLen = Math.max(maxLen, 2 * d1[i] - 1);
            maxLen = Math.max(maxLen, 2 * d2[i]);
        }
        System.out.println("Longest palindrome length: " + maxLen); // 7
        
        long count = 0;
        for (int x : d1) count += x;
        for (int x : d2) count += x;
        System.out.println("Count of palindromes: " + count); // 12
    }
}
```

---

## 119.4 Dry Run

String: `s = "abacaba"`, n = 7

### Odd-length palindromes (d1)

| i | s[i] | l | r | Initial k | Final d1[i] | Palindrome |
|---|---|---|---|---|---|---|
| 0 | a | 0 | -1 | 1 | 1 | "a" |
| 1 | b | 1 | 1 | 1 | 1 | "b" |
| 2 | a | 1 | 3 | 1→2 | 2 | "aba" |
| 3 | c | 2 | 4 | 1→4 | 4 | "abacaba" |
| 4 | a | 0 | 6 | 2 | 2 | "aba" |
| 5 | b | 5 | 5 | 1 | 1 | "b" |
| 6 | a | 6 | 6 | 1 | 1 | "a" |

**Walkthrough for i = 3** (the key step):
- l=1, r=3, so i=3 ≤ r=3
- Mirror: l + r - i = 1 + 3 - 3 = 1, d1[1] = 1
- k = min(1, 3 - 3 + 1) = min(1, 1) = 1
- Check s[3-1]='b' vs s[3+1]='b' → match, k=2
- Check s[3-2]='a' vs s[3+2]='a' → match, k=3
- Check s[3-3]='?' — out of bounds, stop. Wait, s[0]='a', s[6]='a' → match, k=4
- Check s[3-4] — out of bounds, stop
- d1[3] = 4, update l=0, r=6

### Even-length palindromes (d2)

All d2[i] = 0 for "abacaba" (no even-length palindromes).

### Results

- Longest odd palindrome: d1[3] = 4 → length = 2·4 - 1 = 7 → "abacaba"
- Count of palindromes: sum(d1) + sum(d2) = (1+1+2+4+2+1+1) + 0 = 12

---

## 119.5 Complexity Analysis

| Metric | Value |
|---|---|
| **Time** | O(n) |
| **Space** | O(n) |

### Why O(n)?

The right boundary `r` only moves forward (never backward). Each character comparison moves `r` forward by 1. Since `r` can move at most `n` positions, the total number of comparisons is O(n).

This is the same amortized analysis as the KMP algorithm — the "work" variable only increases.

---

## 119.6 Applications

### 1. Longest Palindromic Substring

The most direct application. Find the maximum `d1[i]` or `d2[i]`.

### 2. Count Palindromic Substrings

```python
def count_palindromes(s):
    d1, d2 = manacher(s)
    return sum(d1) + sum(d2)
```

Each `d1[i]` counts the number of odd-length palindromes centered at `i`. Each `d2[i]` counts even-length ones.

### 3. Longest Palindromic Subsequence (via LCS)

This is different from substring! For subsequence, use LCS with the reversed string: O(n²) DP.

### 4. Palindrome Partitioning

Find the minimum cuts to partition a string into palindromes. Manacher's helps identify all palindromic substrings in O(n), then use DP for the partitioning.

```python
def min_palindrome_partitions(s):
    d1, d2 = manacher(s)
    n = len(s)
    min_cuts = list(range(n))  # Worst case: cut after every character
    
    for i in range(n):
        # Odd-length palindromes centered at i
        for k in range(d1[i]):
            left = i - k
            min_cuts[i + k] = min(min_cuts[i + k], (min_cuts[left - 1] if left > 0 else -1) + 1)
        # Even-length palindromes centered at i
        for k in range(d2[i]):
            left = i - k - 1
            min_cuts[i + k] = min(min_cuts[i + k], (min_cuts[left] if left >= 0 else -1) + 1)
    
    return min_cuts[n - 1]
```

---

## 119.7 Comparison with Other Approaches

| Approach | Time | Space | Notes |
|---|---|---|---|
| Brute force | O(n³) | O(1) | Check all substrings |
| Expand around center | O(n²) | O(1) | Simple, good for interviews |
| Manacher's | O(n) | O(n) | Optimal |
| Suffix array + LCP | O(n log n) | O(n) | Overkill for this problem |
| Palindrome tree (Eertree) | O(n) | O(n) | More general, supports online |

---

## 119.8 The Transformed String Approach

Some implementations use the transformed string `T = "#a#b#a#b#a#"` approach:

```python
def manacher_transformed(s):
    if not s:
        return ""
    T = '#' + '#'.join(s) + '#'
    n = len(T)
    P = [0] * n
    C, R = 0, 0
    
    for i in range(n):
        mirror = 2 * C - i
        if i < R:
            P[i] = min(R - i, P[mirror])
        
        # Expand
        while i + P[i] + 1 < n and i - P[i] - 1 >= 0 and T[i + P[i] + 1] == T[i - P[i] - 1]:
            P[i] += 1
        
        if i + P[i] > R:
            C, R = i, i + P[i]
    
    max_len = max(P)
    center = P.index(max_len)
    start = (center - max_len) // 2
    return s[start:start + max_len]
```

This is equivalent to the dual-array approach but uses a single array and transformed string.

---

## 119.9 Exercises

### Conceptual

1. **Why is Manacher's O(n)?** Explain the amortized analysis in your own words.
2. **What's the difference between `d1` and `d2`?** When would each be used?
3. **Can Manacher's handle Unicode?** What about multi-byte characters?

### Implementation

4. **Implement Manacher's** and verify it on `"abacaba"`. Print all palindromic substrings.
5. **Find the longest palindromic subsequence** (not substring) using LCS. Compare with Manacher's output.
6. **Implement palindrome partitioning** using Manacher's to find all palindromes, then DP for minimum cuts.

### Challenge

7. **Online Manacher's**: Design an algorithm that processes characters one at a time and reports the longest palindrome seen so far.
8. **Palindromic Tree (Eertree)**: Research and implement a palindromic tree that supports insertion and count of distinct palindromic substrings.

---

## 119.10 Interview Questions

1. **Q**: Find the longest palindromic substring in O(n).
   **A**: Use Manacher's algorithm. It reuses previously computed palindrome information using a mirror property.

2. **Q**: How does Manacher's achieve O(n) time?
   **A**: The right boundary `r` of the current rightmost palindrome only moves forward. Each comparison either expands the current palindrome or moves to a new center. Total comparisons = O(n).

3. **Q**: What's the difference between "palindromic substring" and "palindromic subsequence"?
   **A**: Substring is contiguous: "abcba" has palindromic substring "bcb". Subsequence can skip characters: "abcba" has palindromic subsequence "abcba" (the whole string). Substring uses Manacher's (O(n)), subsequence uses LCS (O(n²)).

4. **Q**: Can you find all palindromic substrings, not just the longest?
   **A**: Yes. `d1[i]` gives the count of odd-length palindromes centered at `i`. The total count is `sum(d1) + sum(d2)`.

5. **Q**: How would you check if a string can be rearranged into a palindrome?
   **A**: Count character frequencies. A string can be a palindrome if at most one character has an odd count. (This doesn't use Manacher's but is a common follow-up.)

---

## 119.11 Cross-References

- **String Basics**: [Chapter 102](ch102-wavelet-trees.md) — fundamental string operations
- **Two Pointers**: [Chapter 107](ch107-hld-centroid-applications.md) — expand-around-center technique
- **KMP Algorithm**: [Chapter 103](ch103-interval-order-statistic-trees.md) — similar amortized analysis
- **Suffix Arrays**: [Chapter 104](ch104-cartesian-tournament-trees.md) — alternative approach for string problems
- **Dynamic Programming**: [Chapter 109](ch109-bridge-trees-treewidth.md) — for subsequence variants
- **Palindromic Tree**: [Chapter 120](ch120-bwt-fmindex.md) — more advanced palindrome data structure
