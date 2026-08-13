# Chapter 123: Regular Expression and Wildcard Matching

## Prerequisites
- Dynamic programming basics, string manipulation, recursion

## Interview Frequency: ★★★★

Pattern matching with wildcards and regular expressions is a classic interview problem at **Google**, **Meta**, **Amazon**, **Microsoft**, and **Apple**. It tests DP design, state machine understanding, and edge case handling. Two variants dominate interviews: **wildcard matching** (with `?` and `*`) and **regex matching** (with `.` and `*`).

---

## 123.1 Motivation

Pattern matching is everywhere:
- **File systems**: `*.txt`, `file?.log`
- **Search engines**: Query patterns with wildcards
- **Compilers**: Lexical analysis uses regex
- **Databases**: SQL `LIKE` operator (`%` and `_`)
- **Input validation**: Email, phone number patterns

Understanding how to implement matching from scratch (without built-in regex engines) is a fundamental skill.

---

## 123.2 Problem 1: Wildcard Matching

**Problem**: Given a string `s` and a pattern `p`, determine if `p` matches `s` entirely.

**Pattern characters**:
- `?` — matches exactly one character
- `*` — matches any sequence of characters (including empty)
- Any other character — matches itself

**Examples**:
| s | p | Match? | Explanation |
|---|---|---|---|
| "aa" | "a" | ❌ | Pattern doesn't cover full string |
| "aa" | "*" | ✅ | `*` matches "aa" |
| "cb" | "?a" | ❌ | `?` matches 'c', but 'b' ≠ 'a' |
| "adceb" | "*a*b" | ✅ | `*` matches "adc", `a` matches 'a', `*` matches "e", `b` matches 'b' |
| "acdcb" | "a*c?b" | ❌ | No way to match |

### Intuition

The key challenge is `*`. It can match 0, 1, 2, ..., n characters. We need to try all possibilities, but DP avoids recomputation.

**State**: `dp[i][j]` = does `s[0..i-1]` match `p[0..j-1]`?

**Transitions**:
1. If `p[j-1] == '?'` or `p[j-1] == s[i-1]`: `dp[i][j] = dp[i-1][j-1]`
2. If `p[j-1] == '*'`: `dp[i][j] = dp[i][j-1]` (match empty) OR `dp[i-1][j]` (match one more char)
3. Otherwise: `dp[i][j] = false`

### Step-by-Step Walkthrough

s = "adceb", p = "*a*b"

```
Initialize dp[0][0] = true (empty matches empty)

Handle leading *'s:
dp[0][1] = true  (p[0]='*', match empty)
dp[0][2] = false (p[1]='a', can't match empty string)
dp[0][3] = false
dp[0][4] = false
dp[0][5] = false

Fill row by row:

i=1 (s[0]='a'):
  j=1 (p[0]='*'): dp[1][1] = dp[1][0] || dp[0][1] = false || true = true
  j=2 (p[1]='a'): dp[1][2] = dp[0][1] && ('a'=='a') = true
  j=3 (p[2]='*'): dp[1][3] = dp[1][2] || dp[0][3] = true || false = true
  j=4 (p[3]='b'): dp[1][4] = dp[0][3] && ('a'=='b') = false
  j=5 (p[4]='*'): dp[1][5] = dp[1][4] || dp[0][5] = false || false = false

i=2 (s[1]='d'):
  j=1: dp[2][1] = dp[2][0] || dp[1][1] = true
  j=2: dp[2][2] = dp[1][1] && ('d'=='a') = false
  j=3: dp[2][3] = dp[2][2] || dp[1][3] = false || true = true
  j=4: dp[2][4] = dp[1][3] && ('d'=='b') = false
  j=5: dp[2][5] = dp[2][4] || dp[1][5] = false

i=3 (s[2]='c'):
  j=1: dp[3][1] = true
  j=2: dp[3][2] = dp[2][1] && ('c'=='a') = false
  j=3: dp[3][3] = dp[3][2] || dp[2][3] = true
  j=4: dp[3][4] = dp[2][3] && ('c'=='b') = false
  j=5: dp[3][5] = dp[3][4] || dp[2][5] = false

i=4 (s[3]='e'):
  j=1: dp[4][1] = true
  j=2: dp[4][2] = false
  j=3: dp[4][3] = dp[4][2] || dp[3][3] = true
  j=4: dp[4][4] = dp[3][3] && ('e'=='b') = false
  j=5: dp[4][5] = dp[4][4] || dp[3][5] = false

i=5 (s[4]='b'):
  j=1: dp[5][1] = true
  j=2: dp[5][2] = false
  j=3: dp[5][3] = dp[5][2] || dp[4][3] = true
  j=4: dp[5][4] = dp[4][3] && ('b'=='b') = true  ← match!
  j=5: dp[5][5] = dp[5][4] || dp[4][5] = true    ← final answer!

Result: dp[5][5] = true ✅
```

---

## 123.3 Problem 2: Regular Expression Matching

**Problem**: Given a string `s` and a pattern `p`, determine if `p` matches `s` entirely.

**Pattern characters**:
- `.` — matches exactly one character
- `*` — matches zero or more of the **preceding** element
- Any other character — matches itself

**Critical difference from wildcard**: `*` is NOT standalone. It modifies the preceding character. `a*` means "zero or more a's". `.*` means "zero or more of any character."

**Examples**:
| s | p | Match? | Explanation |
|---|---|---|---|
| "aa" | "a" | ❌ | Pattern doesn't cover full string |
| "aa" | "a*" | ✅ | `a*` matches "aa" (two a's) |
| "ab" | ".*" | ✅ | `.*` matches everything |
| "aab" | "c*a*b" | ✅ | `c*` matches "", `a*` matches "aa", `b` matches "b" |
| "mississippi" | "mis*is*p*." | ❌ | `p*` can't match "ppi" |

### Intuition

**State**: `dp[i][j]` = does `s[0..i-1]` match `p[0..j-1]`?

**Transitions**:
1. If `p[j-1] == '*'`:
   - **Option A**: Match zero occurrences of `p[j-2]` → `dp[i][j] = dp[i][j-2]`
   - **Option B**: If `p[j-2] == '.'` or `p[j-2] == s[i-1]`, match one more → `dp[i][j] = dp[i-1][j]`
2. If `p[j-1] == '.'` or `p[j-1] == s[i-1]`: `dp[i][j] = dp[i-1][j-1]`
3. Otherwise: `dp[i][j] = false`

### Step-by-Step Walkthrough

s = "aab", p = "c*a*b"

```
Initialize: dp[0][0] = true

Handle * patterns for empty string:
dp[0][1] = false (p[0]='c', no match)
dp[0][2] = dp[0][0] = true  (p[1]='*', c* matches empty)
dp[0][3] = false (p[2]='a', no match)
dp[0][4] = dp[0][2] = true  (p[3]='*', a* matches empty)
dp[0][5] = false (p[4]='b', no match)

i=1 (s[0]='a'):
  j=1 (p[0]='c'): dp[1][1] = false
  j=2 (p[1]='*'): dp[1][2] = dp[1][0] || (dp[0][2] && 'c'=='a') = false
  j=3 (p[2]='a'): dp[1][3] = dp[0][2] && ('a'=='a') = true
  j=4 (p[3]='*'): dp[1][4] = dp[1][2] || (dp[0][4] && 'a'=='a') = true
  j=5 (p[4]='b'): dp[1][5] = dp[0][4] && ('a'=='b') = false

i=2 (s[1]='a'):
  j=1: false
  j=2: dp[2][2] = dp[2][0] || (dp[1][2] && 'c'=='a') = false
  j=3: dp[2][3] = dp[1][2] && ('a'=='a') = false
  j=4: dp[2][4] = dp[2][2] || (dp[1][4] && 'a'=='a') = true
  j=5: dp[2][5] = dp[1][4] && ('a'=='b') = false

i=3 (s[2]='b'):
  j=1: false
  j=2: dp[3][2] = false
  j=3: dp[3][3] = dp[2][2] && ('b'=='a') = false
  j=4: dp[3][4] = dp[3][2] || (dp[2][4] && 'a'=='b') = false
  j=5: dp[3][5] = dp[2][4] && ('b'=='b') = true  ← final answer!

Result: dp[3][5] = true ✅
```

---

## 123.4 C++ Implementation — Both Problems

```cpp
#include <iostream>
#include <string>
#include <vector>

class PatternMatcher {
public:
    // Wildcard matching: ? matches any single char, * matches any sequence
    static bool wildcardMatch(const std::string& s, const std::string& p) {
        int n = s.size(), m = p.size();
        std::vector<std::vector<bool>> dp(n + 1, std::vector<bool>(m + 1, false));
        dp[0][0] = true;
        
        // Handle leading *'s
        for (int j = 1; j <= m; j++)
            if (p[j-1] == '*') dp[0][j] = dp[0][j-1];
        
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= m; j++) {
                if (p[j-1] == '*') {
                    // * matches empty (dp[i][j-1]) or one more char (dp[i-1][j])
                    dp[i][j] = dp[i][j-1] || dp[i-1][j];
                } else if (p[j-1] == '?' || s[i-1] == p[j-1]) {
                    dp[i][j] = dp[i-1][j-1];
                }
            }
        }
        
        return dp[n][m];
    }
    
    // Regex matching: . matches any single char, * matches zero+ of preceding
    static bool regexMatch(const std::string& s, const std::string& p) {
        int n = s.size(), m = p.size();
        std::vector<std::vector<bool>> dp(n + 1, std::vector<bool>(m + 1, false));
        dp[0][0] = true;
        
        // Handle patterns like a*, a*b*, a*b*c* for empty string
        for (int j = 2; j <= m; j++)
            if (p[j-1] == '*') dp[0][j] = dp[0][j-2];
        
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= m; j++) {
                if (p[j-1] == '*') {
                    // Match zero occurrences
                    dp[i][j] = dp[i][j-2];
                    // Match one more if preceding char matches
                    if (p[j-2] == '.' || p[j-2] == s[i-1])
                        dp[i][j] = dp[i][j] || dp[i-1][j];
                } else if (p[j-1] == '.' || s[i-1] == p[j-1]) {
                    dp[i][j] = dp[i-1][j-1];
                }
            }
        }
        
        return dp[n][m];
    }
    
    // Space-optimized wildcard matching — O(n) space
    static bool wildcardMatchOptimized(const std::string& s, const std::string& p) {
        int n = s.size(), m = p.size();
        std::vector<bool> prev(m + 1, false), curr(m + 1, false);
        prev[0] = true;
        
        for (int j = 1; j <= m; j++)
            if (p[j-1] == '*') prev[j] = prev[j-1];
        
        for (int i = 1; i <= n; i++) {
            curr[0] = false;
            for (int j = 1; j <= m; j++) {
                if (p[j-1] == '*') {
                    curr[j] = curr[j-1] || prev[j];
                } else if (p[j-1] == '?' || s[i-1] == p[j-1]) {
                    curr[j] = prev[j-1];
                } else {
                    curr[j] = false;
                }
            }
            std::swap(prev, curr);
        }
        
        return prev[m];
    }
};

int main() {
    // Wildcard tests
    std::cout << "=== Wildcard Matching ===" << std::endl;
    std::cout << "\"aa\" vs \"a\": " << PatternMatcher::wildcardMatch("aa", "a") << "\n";     // 0
    std::cout << "\"aa\" vs \"*\": " << PatternMatcher::wildcardMatch("aa", "*") << "\n";     // 1
    std::cout << "\"cb\" vs \"?a\": " << PatternMatcher::wildcardMatch("cb", "?a") << "\n";   // 0
    std::cout << "\"adceb\" vs \"*a*b\": " << PatternMatcher::wildcardMatch("adceb", "*a*b") << "\n"; // 1
    std::cout << "\"acdcb\" vs \"a*c?b\": " << PatternMatcher::wildcardMatch("acdcb", "a*c?b") << "\n"; // 0
    
    // Regex tests
    std::cout << "\n=== Regex Matching ===" << std::endl;
    std::cout << "\"aa\" vs \"a*\": " << PatternMatcher::regexMatch("aa", "a*") << "\n";       // 1
    std::cout << "\"ab\" vs \".*\": " << PatternMatcher::regexMatch("ab", ".*") << "\n";       // 1
    std::cout << "\"aab\" vs \"c*a*b\": " << PatternMatcher::regexMatch("aab", "c*a*b") << "\n"; // 1
    std::cout << "\"mississippi\" vs \"mis*is*p*.\": " 
              << PatternMatcher::regexMatch("mississippi", "mis*is*p*.") << "\n"; // 0
    
    // Space-optimized tests
    std::cout << "\n=== Optimized Wildcard ===" << std::endl;
    std::cout << "\"adceb\" vs \"*a*b\": " << PatternMatcher::wildcardMatchOptimized("adceb", "*a*b") << "\n"; // 1
    
    return 0;
}
```

---

## 123.5 Python Implementation

```python
from typing import List


def wildcard_match(s: str, p: str) -> bool:
    """
    Wildcard matching with ? and *.
    ? matches any single character.
    * matches any sequence of characters (including empty).
    """
    n, m = len(s), len(p)
    dp = [[False] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = True
    
    # Handle leading *'s
    for j in range(1, m + 1):
        if p[j - 1] == '*':
            dp[0][j] = dp[0][j - 1]
    
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if p[j - 1] == '*':
                # Match empty or extend match by one character
                dp[i][j] = dp[i][j - 1] or dp[i - 1][j]
            elif p[j - 1] == '?' or s[i - 1] == p[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
    
    return dp[n][m]


def regex_match(s: str, p: str) -> bool:
    """
    Regular expression matching with . and *.
    . matches any single character.
    * matches zero or more of the preceding element.
    """
    n, m = len(s), len(p)
    dp = [[False] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = True
    
    # Handle patterns like a*, a*b* for empty string
    for j in range(2, m + 1):
        if p[j - 1] == '*':
            dp[0][j] = dp[0][j - 2]
    
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if p[j - 1] == '*':
                # Zero occurrences of the preceding element
                dp[i][j] = dp[i][j - 2]
                # One more occurrence if preceding matches
                if p[j - 2] == '.' or p[j - 2] == s[i - 1]:
                    dp[i][j] = dp[i][j] or dp[i - 1][j]
            elif p[j - 1] == '.' or s[i - 1] == p[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
    
    return dp[n][m]


def wildcard_match_space_optimized(s: str, p: str) -> bool:
    """Space-optimized wildcard matching using O(m) space."""
    n, m = len(s), len(p)
    prev = [False] * (m + 1)
    prev[0] = True
    
    for j in range(1, m + 1):
        if p[j - 1] == '*':
            prev[j] = prev[j - 1]
    
    for i in range(1, n + 1):
        curr = [False] * (m + 1)
        for j in range(1, m + 1):
            if p[j - 1] == '*':
                curr[j] = curr[j - 1] or prev[j]
            elif p[j - 1] == '?' or s[i - 1] == p[j - 1]:
                curr[j] = prev[j - 1]
        prev = curr
    
    return prev[m]


def demo():
    print("=== Wildcard Matching ===")
    tests = [
        ("aa", "a", False),
        ("aa", "*", True),
        ("cb", "?a", False),
        ("adceb", "*a*b", True),
        ("acdcb", "a*c?b", False),
        ("", "*", True),
        ("", "?", False),
        ("abc", "abc", True),
        ("abc", "a?c", True),
        ("abc", "a*d", False),
    ]
    for s, p, expected in tests:
        result = wildcard_match(s, p)
        status = "✅" if result == expected else "❌"
        print(f"  {status} wildcard_match('{s}', '{p}') = {result}")
    
    print("\n=== Regex Matching ===")
    regex_tests = [
        ("aa", "a", False),
        ("aa", "a*", True),
        ("ab", ".*", True),
        ("aab", "c*a*b", True),
        ("mississippi", "mis*is*p*.", False),
        ("", "a*", True),
        ("", ".*", True),
        ("a", "ab*", True),
        ("bbbba", ".*a*a", True),
    ]
    for s, p, expected in regex_tests:
        result = regex_match(s, p)
        status = "✅" if result == expected else "❌"
        print(f"  {status} regex_match('{s}', '{p}') = {result}")
    
    print("\n=== Space-Optimized ===")
    print(f"  wildcard_match_optimized('adceb', '*a*b') = {wildcard_match_space_optimized('adceb', '*a*b')}")


demo()
```

---

## 123.6 Java Implementation

```java
public class PatternMatcher {
    
    // Wildcard matching: ? and *
    public static boolean wildcardMatch(String s, String p) {
        int n = s.length(), m = p.length();
        boolean[][] dp = new boolean[n + 1][m + 1];
        dp[0][0] = true;
        
        for (int j = 1; j <= m; j++)
            if (p.charAt(j - 1) == '*')
                dp[0][j] = dp[0][j - 1];
        
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= m; j++) {
                char pc = p.charAt(j - 1);
                if (pc == '*') {
                    dp[i][j] = dp[i][j - 1] || dp[i - 1][j];
                } else if (pc == '?' || s.charAt(i - 1) == pc) {
                    dp[i][j] = dp[i - 1][j - 1];
                }
            }
        }
        
        return dp[n][m];
    }
    
    // Regex matching: . and *
    public static boolean regexMatch(String s, String p) {
        int n = s.length(), m = p.length();
        boolean[][] dp = new boolean[n + 1][m + 1];
        dp[0][0] = true;
        
        for (int j = 2; j <= m; j++)
            if (p.charAt(j - 1) == '*')
                dp[0][j] = dp[0][j - 2];
        
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= m; j++) {
                char pc = p.charAt(j - 1);
                if (pc == '*') {
                    dp[i][j] = dp[i][j - 2];
                    char prev = p.charAt(j - 2);
                    if (prev == '.' || prev == s.charAt(i - 1))
                        dp[i][j] = dp[i][j] || dp[i - 1][j];
                } else if (pc == '.' || s.charAt(i - 1) == pc) {
                    dp[i][j] = dp[i - 1][j - 1];
                }
            }
        }
        
        return dp[n][m];
    }
    
    // Space-optimized wildcard matching
    public static boolean wildcardMatchOptimized(String s, String p) {
        int n = s.length(), m = p.length();
        boolean[] prev = new boolean[m + 1];
        prev[0] = true;
        
        for (int j = 1; j <= m; j++)
            if (p.charAt(j - 1) == '*')
                prev[j] = prev[j - 1];
        
        for (int i = 1; i <= n; i++) {
            boolean[] curr = new boolean[m + 1];
            for (int j = 1; j <= m; j++) {
                char pc = p.charAt(j - 1);
                if (pc == '*') {
                    curr[j] = curr[j - 1] || prev[j];
                } else if (pc == '?' || s.charAt(i - 1) == pc) {
                    curr[j] = prev[j - 1];
                }
            }
            prev = curr;
        }
        
        return prev[m];
    }
    
    public static void main(String[] args) {
        System.out.println("=== Wildcard Matching ===");
        System.out.println(wildcardMatch("aa", "a"));           // false
        System.out.println(wildcardMatch("aa", "*"));           // true
        System.out.println(wildcardMatch("adceb", "*a*b"));     // true
        
        System.out.println("\n=== Regex Matching ===");
        System.out.println(regexMatch("aa", "a*"));             // true
        System.out.println(regexMatch("ab", ".*"));             // true
        System.out.println(regexMatch("aab", "c*a*b"));         // true
        System.out.println(regexMatch("mississippi", "mis*is*p*.")); // false
    }
}
```

---

## 123.7 Complexity Analysis

| Problem | Time | Space | Space-Optimized |
|---|---|---|---|
| Wildcard Matching | O(n · m) | O(n · m) | O(m) |
| Regex Matching | O(n · m) | O(n · m) | O(m) possible |

Where n = len(s), m = len(p).

**Why O(n·m)?**: We fill an (n+1) × (m+1) table. Each cell takes O(1) work.

**Space optimization**: Each row depends only on the current and previous row. Use two 1D arrays (or even one with careful ordering).

---

## 123.8 Common Mistakes and Edge Cases

1. **Empty string with empty pattern**: Should return true.
2. **Empty string with `*`**: Should return true (`*` matches empty).
3. **Empty string with `?`**: Should return false (`?` needs a character).
4. **Leading `*` in regex**: `*` without a preceding character is invalid in standard regex, but some problems allow it.
5. **Consecutive `*` in wildcard**: `**` is equivalent to `*`. Can be preprocessed away.
6. **Regex `a*` vs wildcard `*`**: Very different! `a*` matches zero or more a's. `*` matches anything.

### Preprocessing for Wildcard

```python
def preprocess_wildcard(p: str) -> str:
    """Remove consecutive *'s: '**' → '*'"""
    result = []
    for c in p:
        if c == '*' and result and result[-1] == '*':
            continue
        result.append(c)
    return ''.join(result)
```

---

## 123.9 Recursive Solution with Memoization

```python
from functools import lru_cache

def regex_match_memo(s: str, p: str) -> bool:
    """Recursive regex matching with memoization."""
    
    @lru_cache(maxsize=None)
    def dp(i: int, j: int) -> bool:
        # Base case: both exhausted
        if j == len(p):
            return i == len(s)
        
        # Check if next pattern char is *
        if j + 1 < len(p) and p[j + 1] == '*':
            # Try matching zero occurrences
            if dp(i, j + 2):
                return True
            # Try matching one more occurrence
            while i < len(s) and (p[j] == '.' or s[i] == p[j]):
                if dp(i + 1, j + 2):
                    return True
                i += 1
            return False
        
        # No *: match single character
        if i < len(s) and (p[j] == '.' or s[i] == p[j]):
            return dp(i + 1, j + 1)
        
        return False
    
    return dp(0, 0)
```

---

## 123.10 Greedy Solution for Wildcard Matching

For wildcard matching (not regex), a greedy two-pointer approach works in O(n + m) time and O(1) space:

```python
def wildcard_match_greedy(s: str, p: str) -> bool:
    """Greedy O(n+m) solution for wildcard matching."""
    si = pi = 0
    star_pi = -1  # Position of last * in pattern
    star_si = -1  # Position in string when last * was matched
    
    while si < len(s):
        if pi < len(p) and (p[pi] == '?' or p[pi] == s[si]):
            si += 1
            pi += 1
        elif pi < len(p) and p[pi] == '*':
            star_pi = pi
            star_si = si
            pi += 1  # Try matching empty first
        elif star_pi != -1:
            # Backtrack: let * match one more character
            pi = star_pi + 1
            star_si += 1
            si = star_si
        else:
            return False
    
    # Remaining pattern must be all *
    while pi < len(p) and p[pi] == '*':
        pi += 1
    
    return pi == len(p)
```

**Note**: This greedy approach works for wildcards but NOT for regex matching, because regex `*` modifies the preceding element rather than matching independently.

---

## 123.11 Exercises

1. **Easy**: Implement wildcard matching that also supports `[abc]` character classes (match any character in the set).

2. **Medium**: Modify the regex matcher to support `+` (one or more of preceding) in addition to `*`.

3. **Medium**: Implement a function that counts the number of substrings of `s` that match pattern `p` (not necessarily full match).

4. **Hard**: Implement wildcard matching with `*`, `?`, and `**` (where `**` matches including path separators, like glob patterns).

5. **Hard**: Design an algorithm that finds the shortest string that matches both pattern p1 and pattern p2 (intersection of two regular languages).

---

## 123.12 Interview Questions

1. **Q**: What is the difference between wildcard `*` and regex `*`?
   **A**: Wildcard `*` is standalone — it matches any sequence of characters. Regex `*` is a modifier — it means "zero or more of the preceding element." So `a*b` in wildcard means "anything, then a, then anything, then b." In regex, it means "zero or more a's, then b."

2. **Q**: Can you solve wildcard matching in O(n + m) time?
   **A**: Yes! Use a greedy two-pointer approach. Track the last `*` position and the string position when that `*` was encountered. When a mismatch occurs, backtrack to the last `*` and let it match one more character. This works because `*` is standalone in wildcard matching.

3. **Q**: Why doesn't the greedy approach work for regex matching?
   **A**: In regex, `*` modifies the preceding element. When we see `a*`, we can't independently decide how many a's to match — it depends on what comes after. The interaction between the preceding element and the rest of the pattern requires DP to handle correctly.

4. **Q**: How would you handle `**` in a glob pattern (like in file systems)?
   **A**: `**` matches any number of path components (including `/`). Preprocess: collapse consecutive `*` into a single `*` for regular matching, but treat `**` specially when it spans directory boundaries. Use a state machine that tracks whether we're inside a `**` context.

5. **Q**: How do you optimize space from O(n·m) to O(m)?
   **A**: Since each row of the DP table depends only on the current and previous row, maintain two 1D arrays. For even better optimization in wildcard matching, use the greedy O(n+m) approach.

---

## 123.13 Cross-References

- **Chapter 89 (String Matching)**: KMP, Rabin-Karp for simpler patterns
- **Chapter 90 (Trie)**: Trie-based pattern matching
- **Chapter 97 (Pattern Recognition)**: When to use DP vs greedy
- **Chapter 102 (Advanced DP)**: DP optimization techniques
- **Chapter 45 (Backtracking)**: Recursive solutions with pruning

---

## Summary

| Problem | Key Insight | Time | Space |
|---|---|---|---|
| Wildcard `?` `*` | `*` = match empty OR extend | O(nm) | O(m) |
| Regex `.` `*` | `*` modifies preceding; zero or more | O(nm) | O(m) |
| Wildcard greedy | Two pointers + backtrack to last `*` | O(n+m) | O(1) |
| Regex recursive | Memoize (i, j) state | O(nm) | O(nm) |
