# Chapter 42: Z Algorithm

The Z Algorithm is another linear-time string matching algorithm, often considered simpler and more intuitive than KMP. It constructs a **Z array** where `Z[i]` is the length of the longest substring starting at position `i` that is also a prefix of the string. Like KMP, it achieves O(n + m) time for pattern matching, but the Z array construction is arguably easier to understand and implement.

---

## 42.1 Z Array

### 42.1.1 Definition

Given a string `s` of length `n`, the Z array is an array `Z[0..n-1]` where:

- `Z[0]` is defined as 0 (or n, depending on convention — we use 0 here since the entire string is trivially a prefix of itself).
- For `i > 0`: `Z[i]` = the length of the longest substring starting at position `i` that matches a prefix of `s`. In other words, `Z[i]` is the largest `k` such that `s[0..k-1] == s[i..i+k-1]`.

### 42.1.2 Example

For `s = "aabxaabxcaab"`:

| i | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|----|----|
| s | a | a | b | x | a | a | b | x | c | a | a  | b  |
| Z | 0 | 1 | 0 | 0 | 4 | 1 | 0 | 0 | 0 | 3 | 1  | 0  |

Explanation:
- `Z[1] = 1`: `s[1]` = 'a' matches `s[0]` = 'a', but `s[2]` = 'b' ≠ `s[1]` = 'a'. Length 1.
- `Z[4] = 4`: `s[4..7]` = "aabc" matches `s[0..3]` = "aabc". Specifically: `s[4]='a'==s[0]='a'`, `s[5]='a'==s[1]='a'`, `s[6]='b'==s[2]='b'`, `s[7]='x'==s[3]='x'`. Then `s[8]='c'≠s[4]='a'`, so Z[4]=4.
- `Z[9] = 3`: `s[9..11]` = "aab" matches `s[0..2]` = "aab". Length 3.

### 42.1.3 Why Z Array Is Useful

The Z array captures, for every position in the string, how much it matches the prefix. This is useful for:
- Pattern matching (concatenate pattern + text and look for Z values ≥ pattern length).
- Finding all occurrences of a pattern in a text.
- Solving various string problems like finding the longest prefix palindrome.

---

## 42.2 Building the Z Array

### 42.2.1 The Naive Approach — O(n²)

```cpp
#include <iostream>
#include <vector>
#include <string>
using namespace std;

vector<int> zArrayNaive(const string& s) {
    int n = s.size();
    vector<int> z(n, 0);
    for (int i = 1; i < n; i++) {
        while (i + z[i] < n && s[z[i]] == s[i + z[i]]) {
            z[i]++;
        }
    }
    return z;
}
```

This is correct but O(n²) in the worst case (e.g., "aaaa...").

### 42.2.2 The Linear Algorithm — O(n)

The key insight: maintain an interval `[l, r)` which is the rightmost Z-box (the interval starting at some position that matches the prefix). When computing `Z[i]`:

1. **If `i ≥ r`:** No information from previous computations helps. Compute Z[i] naively by comparing character by character. Update `[l, r)` if we found a new rightmost Z-box.

2. **If `i < r`:** We're inside the current Z-box. We know `s[i..r-1]` matches `s[i-l..r-l-1]` (the prefix). So we can initialize `Z[i] = min(Z[i-l], r-i)`.
   - If `Z[i-l] < r - i`: The entire Z-value is determined by the prefix — `Z[i] = Z[i-l]`.
   - If `Z[i-l] ≥ r - i`: We know at least `r - i` characters match, but we need to check further from `r` onward.

```cpp
#include <iostream>
#include <vector>
#include <string>
using namespace std;

vector<int> buildZ(const string& s) {
    int n = s.size();
    vector<int> z(n, 0);
    int l = 0, r = 0;  // [l, r) is the current Z-box

    for (int i = 1; i < n; i++) {
        if (i < r) {
            z[i] = min(r - i, z[i - l]);
        }
        // Extend naively
        while (i + z[i] < n && s[z[i]] == s[i + z[i]]) {
            z[i]++;
        }
        // Update the Z-box if we went further right
        if (i + z[i] > r) {
            l = i;
            r = i + z[i];
        }
    }
    return z;
}

int main() {
    string s1 = "aabxaabxcaab";
    auto z1 = buildZ(s1);
    cout << "String: " << s1 << endl;
    cout << "Z:      ";
    for (int x : z1) cout << x << " ";
    cout << endl;  // 0 1 0 0 4 1 0 0 0 3 1 0

    string s2 = "aaaaaa";
    auto z2 = buildZ(s2);
    cout << "String: " << s2 << endl;
    cout << "Z:      ";
    for (int x : z2) cout << x << " ";
    cout << endl;  // 0 5 4 3 2 1

    string s3 = "abacaba";
    auto z3 = buildZ(s3);
    cout << "String: " << s3 << endl;
    cout << "Z:      ";
    for (int x : z3) cout << x << " ";
    cout << endl;  // 0 0 1 0 3 0 1
    return 0;
}
```

### 42.2.3 Dry Run: Building Z Array for "aabxaabxcaab"

```
s = "aabxaabxcaab"
z = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
l=0, r=0

i=1: i >= r (1 >= 0), so compute naively.
  s[0]='a' == s[1]='a' → z[1]++
  s[1]='a' != s[2]='b' → stop. z[1]=1.
  i+z[1]=2 > r=0 → l=1, r=2.
  z = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

i=2: i >= r (2 >= 2), compute naively.
  s[0]='a' != s[2]='b' → stop. z[2]=0.
  z = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

i=3: i >= r (3 >= 2), compute naively.
  s[0]='a' != s[3]='x' → stop. z[3]=0.
  z = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

i=4: i >= r (4 >= 2), compute naively.
  s[0]='a' == s[4]='a' → z[4]++
  s[1]='a' == s[5]='a' → z[4]++
  s[2]='b' == s[6]='b' → z[4]++
  s[3]='x' == s[7]='x' → z[4]++
  s[4]='a' != s[8]='c' → stop. z[4]=4.
  i+z[4]=8 > r=2 → l=4, r=8.
  z = [0, 1, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0]

i=5: i < r (5 < 8), so z[5] = min(r-i, z[5-l]) = min(3, z[1]) = min(3, 1) = 1.
  Extend: i+z[5]=6, s[1]='a' != s[6]='b' → stop. z[5]=1.
  z = [0, 1, 0, 0, 4, 1, 0, 0, 0, 0, 0, 0]

i=6: i < r (6 < 8), z[6] = min(2, z[2]) = min(2, 0) = 0.
  Extend: s[0]='a' != s[6]='b' → stop. z[6]=0.
  z = [0, 1, 0, 0, 4, 1, 0, 0, 0, 0, 0, 0]

i=7: i < r (7 < 8), z[7] = min(1, z[3]) = min(1, 0) = 0.
  Extend: s[0]='a' != s[7]='x' → stop. z[7]=0.
  z = [0, 1, 0, 0, 4, 1, 0, 0, 0, 0, 0, 0]

i=8: i >= r (8 >= 8), compute naively.
  s[0]='a' != s[8]='c' → stop. z[8]=0.
  z = [0, 1, 0, 0, 4, 1, 0, 0, 0, 0, 0, 0]

i=9: i >= r (9 >= 8), compute naively.
  s[0]='a' == s[9]='a' → z[9]++
  s[1]='a' == s[10]='a' → z[9]++
  s[2]='b' == s[11]='b' → z[9]++
  end of string → stop. z[9]=3.
  i+z[9]=12 > r=8 → l=9, r=12.
  z = [0, 1, 0, 0, 4, 1, 0, 0, 0, 3, 0, 0]

i=10: i < r (10 < 12), z[10] = min(2, z[1]) = min(2, 1) = 1.
  Extend: i+z[10]=11, s[1]='a' != s[11]='b' → stop. z[10]=1.
  z = [0, 1, 0, 0, 4, 1, 0, 0, 0, 3, 1, 0]

i=11: i < r (11 < 12), z[11] = min(1, z[2]) = min(1, 0) = 0.
  Extend: s[0]='a' != s[11]='b' → stop. z[11]=0.
  z = [0, 1, 0, 0, 4, 1, 0, 0, 0, 3, 1, 0]

Final Z = [0, 1, 0, 0, 4, 1, 0, 0, 0, 3, 1, 0] ✓
```

**Complexity:** O(n) time. The key observation: the `while` loop at each position `i` extends `r` by at least 1 (if `i ≥ r`) or doesn't execute at all (if `i < r` and `Z[i-l] < r-i`). Since `r` only moves forward and is bounded by `n`, the total work in all `while` loops is O(n). Space: O(n).

---

## 42.3 Pattern Matching Using Z Array

### 42.3.1 The Concatenation Trick

To find all occurrences of pattern `p` in text `t`, construct the string `p + "$" + t` (where `$` is a delimiter not in either string), compute the Z array, and look for positions where `Z[i] ≥ len(p)`.

```cpp
#include <iostream>
#include <vector>
#include <string>
using namespace std;

vector<int> buildZ(const string& s) {
    int n = s.size();
    vector<int> z(n, 0);
    int l = 0, r = 0;
    for (int i = 1; i < n; i++) {
        if (i < r) {
            z[i] = min(r - i, z[i - l]);
        }
        while (i + z[i] < n && s[z[i]] == s[i + z[i]]) {
            z[i]++;
        }
        if (i + z[i] > r) {
            l = i;
            r = i + z[i];
        }
    }
    return z;
}

vector<int> zSearch(const string& text, const string& pattern) {
    vector<int> result;
    int m = pattern.size();
    if (m == 0 || m > (int)text.size()) return result;

    string combined = pattern + "$" + text;
    vector<int> z = buildZ(combined);

    for (int i = m + 1; i < (int)combined.size(); i++) {
        if (z[i] >= m) {
            result.push_back(i - m - 1);  // convert to text index
        }
    }
    return result;
}

int main() {
    string text = "ABABDABACDABABCABAB";
    string pattern = "ABABCABAB";

    auto matches = zSearch(text, pattern);
    cout << "Text:    " << text << endl;
    cout << "Pattern: " << pattern << endl;
    cout << "Found at: ";
    for (int idx : matches) cout << idx << " ";
    cout << endl;  // 9

    string text2 = "AAAAABAAABA";
    string pattern2 = "AAAB";
    auto matches2 = zSearch(text2, pattern2);
    cout << "Found at: ";
    for (int idx : matches2) cout << idx << " ";
    cout << endl;  // 1 7

    string text3 = "ABABABAB";
    string pattern3 = "ABAB";
    auto matches3 = zSearch(text3, pattern3);
    cout << "Found at: ";
    for (int idx : matches3) cout << idx << " ";
    cout << endl;  // 0 2 4
    return 0;
}
```

### 42.3.2 Dry Run: Pattern Matching with Z

For text = "ABABABAB", pattern = "ABAB":

```
combined = "ABAB$ABABABAB"  (length 13)
            0123456789...

Z[0]  = 0
Z[1]  = 0  (B ≠ A)
Z[2]  = 2  (AB matches AB, then A ≠ $)
Z[3]  = 0  (B ≠ A)
Z[4]  = 0  ($ ≠ A)
Z[5]  = 4  (ABAB matches ABAB, then A ≠ $)
Z[6]  = 0  (B ≠ A)
Z[7]  = 4  (ABAB matches ABAB, then A ≠ $)
Z[8]  = 0  (B ≠ A)
Z[9]  = 4  (ABAB matches ABAB, end of string)
Z[10] = 0  (B ≠ A)
Z[11] = 2  (AB matches AB, end of string)
Z[12] = 0  (B ≠ A)

Z = [0, 0, 2, 0, 0, 4, 0, 4, 0, 4, 0, 2, 0]

m=4. Check positions m+1=5 onward:
i=5:  Z[5]=4  >= 4 → match at 5-4-1=0  ✓ ("ABAB" at index 0)
i=7:  Z[7]=4  >= 4 → match at 7-4-1=2  ✓ ("ABAB" at index 2)
i=9:  Z[9]=4  >= 4 → match at 9-4-1=4  ✓ ("ABAB" at index 4)

Result: [0, 2, 4] ✓
```

**Complexity:** O(n + m) time for the Z array construction and search. O(n + m) space for the combined string and Z array.

---

## 42.4 Applications

### 42.4.1 Count Occurrences of a Pattern

Already covered — the Z search naturally finds all occurrences. The count is just the size of the result vector.

```cpp
#include <iostream>
#include <vector>
#include <string>
using namespace std;

vector<int> buildZ(const string& s) {
    int n = s.size();
    vector<int> z(n, 0);
    int l = 0, r = 0;
    for (int i = 1; i < n; i++) {
        if (i < r) z[i] = min(r - i, z[i - l]);
        while (i + z[i] < n && s[z[i]] == s[i + z[i]]) z[i]++;
        if (i + z[i] > r) { l = i; r = i + z[i]; }
    }
    return z;
}

int countOccurrences(const string& text, const string& pattern) {
    string combined = pattern + "$" + text;
    auto z = buildZ(combined);
    int count = 0;
    int m = pattern.size();
    for (int i = m + 1; i < (int)combined.size(); i++) {
        if (z[i] >= m) count++;
    }
    return count;
}

int main() {
    cout << countOccurrences("abababab", "ab") << endl;    // 4
    cout << countOccurrences("aaaa", "aa") << endl;         // 3
    cout << countOccurrences("hello", "xyz") << endl;       // 0
    return 0;
}
```

### 42.4.2 Longest Prefix Palindrome

Find the length of the longest prefix of a string that is also a palindrome.

**Key insight:** `s[0..k-1]` is a palindrome if and only if `s[0..k-1] == reverse(s)[n-k..n-1]`. Using the concatenation trick with `s + "#" + reverse(s)`, we can check this for all `k` in O(n).

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
using namespace std;

vector<int> buildZ(const string& s) {
    int n = s.size();
    vector<int> z(n, 0);
    int l = 0, r = 0;
    for (int i = 1; i < n; i++) {
        if (i < r) z[i] = min(r - i, z[i - l]);
        while (i + z[i] < n && s[z[i]] == s[i + z[i]]) z[i]++;
        if (i + z[i] > r) { l = i; r = i + z[i]; }
    }
    return z;
}

// Find the longest prefix of s that is a palindrome
// Method: s[0..k-1] is a palindrome iff s[0..k-1] == reverse(s[0..k-1])
//                                   iff s[0..k-1] == reverse(s)[n-k..n-1]
//
// Construct combined = s + "#" + reverse(s)
// For position (n+1+j) in combined (where j ranges over reverse(s)):
//   Z[n+1+j] = longest prefix match starting at reverse(s)[j]
//   If Z[n+1+j] >= (n-j), then reverse(s)[j..n-1] == s[0..n-j-1]
//   i.e., s[n-1-j..0] (reversed, length n-j) == s[0..n-j-1]
//   Setting k = n-j: s[0..k-1] == reverse(s[0..k-1]), so s[0..k-1] is a palindrome.
//
// We iterate j from 0 to n-1 (i.e., k from n down to 1) and return the first match.
int longestPrefixPalindrome(const string& s) {
    if (s.empty()) return 0;
    string rev = s;
    reverse(rev.begin(), rev.end());
    string combined = s + "#" + rev;
    auto z = buildZ(combined);
    int n = s.size();
    for (int j = n - 1; j >= 0; j--) {
        if (z[n + 1 + j] >= n - j) {
            return n - j;
        }
    }
    return 1;  // single character is always a palindrome
}

int main() {
    cout << longestPrefixPalindrome("aacecaaa") << endl;  // 7
    cout << longestPrefixPalindrome("abcd") << endl;       // 1
    cout << longestPrefixPalindrome("aba") << endl;        // 3
    cout << longestPrefixPalindrome("abacaba") << endl;    // 7
    return 0;
}
```

**Dry run for s = "aacecaaa":**
```
s   = "aacecaaa"  (n=8)
rev = "aaacecaa"
combined = "aacecaaa#aaacecaa"  (length 17)

Z values in the rev part (positions 9..16):
Z[9]  = 1  (a vs a, then a≠a? No, a==a, c≠c? Let's just compute the result)
...

We check j from 7 down to 0:
j=7 (k=1): Z[16] >= 1? Z[16] is the Z value at the last char of rev.
           rev[7]='a', s[0]='a'. Z[16] ≥ 1. So k=1 works. But we want the largest.
j=0 (k=8): Z[9] >= 8? Would mean entire s == rev, i.e., s is a palindrome. "aacecaaa" is not.
...
j=1 (k=7): Z[10] >= 7? rev[1..7]="aacecaa", s[0..6]="aacecaa". Yes! So k=7.

Result: 7 ✓ ("aacecaa" is a palindrome)
```

**Complexity:** O(n) time, O(n) space.

### 42.4.3 Period of a String

The **period** of a string `s` of length `n` is the smallest positive integer `d` such that `s[i] = s[i + d]` for all valid `i`. Using the Z array:

```cpp
#include <iostream>
#include <string>
#include <vector>
using namespace std;

vector<int> buildZ(const string& s) {
    int n = s.size();
    vector<int> z(n, 0);
    int l = 0, r = 0;
    for (int i = 1; i < n; i++) {
        if (i < r) z[i] = min(r - i, z[i - l]);
        while (i + z[i] < n && s[z[i]] == s[i + z[i]]) z[i]++;
        if (i + z[i] > r) { l = i; r = i + z[i]; }
    }
    return z;
}

// Find the smallest period of s
int findPeriod(const string& s) {
    int n = s.size();
    auto z = buildZ(s);
    for (int d = 1; d < n; d++) {
        if (z[d] >= n - d) {
            return d;
        }
    }
    return n;  // no smaller period, period is n itself
}

int main() {
    cout << findPeriod("abcabcabc") << endl;  // 3
    cout << findPeriod("ababab") << endl;      // 2
    cout << findPeriod("abcd") << endl;        // 4
    cout << findPeriod("aaaa") << endl;        // 1
    cout << findPeriod("aabaaab") << endl;     // 4 ("aaba" repeated)
    return 0;
}
```

**How it works:** If `d` is a period, then `s[d..n-1] == s[0..n-d-1]`, which means `Z[d] >= n - d`. We find the smallest such `d`.

**Dry run for s = "abcabcabc" (n=9):**
```
Z = [0, 0, 0, 6, 0, 0, 3, 0, 0]

d=1: Z[1]=0 >= 8? No.
d=2: Z[2]=0 >= 7? No.
d=3: Z[3]=6 >= 6? Yes! Period = 3.
```

This confirms that "abcabcabc" is built by repeating "abc" three times. The Z value at position 3 is 6, meaning `s[3..8]` matches `s[0..5]` ("abcabc"), which is exactly `n - d = 9 - 3 = 6` characters.

**Complexity:** O(n) time (Z array is O(n), and the loop is O(n) in the worst case but can short-circuit).

---

## Interview Tips

1. **Z array vs LPS (KMP).** They solve similar problems differently. Z[i] = longest prefix match starting at i. LPS[i] = longest proper prefix that's also a suffix of s[0..i]. Know both.
2. **The concatenation trick.** `pattern + "$" + text` (or `text + "$" + pattern`) is a powerful technique for converting pattern matching into Z array computation.
3. **Z array is often easier to implement.** If you have a choice, Z algorithm's construction is more intuitive — maintain the `[l, r)` box and extend.
4. **For competitive programming,** the Z algorithm is often preferred because it's shorter to code and less error-prone than KMP.

## Common Mistakes

- **Confusing Z[i] with LPS[i].** Z[i] measures prefix match starting at position i. LPS[i] measures prefix-suffix match ending at position i.
- **Forgetting the `$` separator.** Without it, matches can overlap between the pattern and text parts of the combined string, giving false positives.
- **Not handling Z[0].** By convention, Z[0] = 0 (or n). Make sure your code handles it consistently.
- **Off-by-one in the combined string.** If pattern has length m, the text starts at position m+1 (after the `$`). Adjust indices accordingly when converting back to text positions.
- **Assuming Z values are always correct.** The linear algorithm's correctness relies on the invariant that `[l, r)` is always the rightmost Z-box. If you modify the algorithm carelessly, this invariant can break.

## Practice Problems

1. **Power of Strings** — Given a string, find the smallest string `t` such that `s` is a concatenation of one or more copies of `t`. *Hint: Use Z to find the period, same as the `repeatedSubstringPattern` problem.*
2. **String Matching** — Given a text and multiple patterns, find all occurrences of each pattern. *Hint: For each pattern, use the Z concatenation trick. O(n + m) per pattern.*
3. **Longest Common Prefix** — Given two strings, find their longest common prefix. *Hint: Concatenate with `$` and check Z[m+1].*
4. **Distinct Substrings** — Count distinct substrings using Z array. *Hint: For each suffix, Z values tell you how many prefixes are shared with earlier positions.*
5. **Periodic String** — Find all periods of a string. *Hint: A value `d` is a period iff Z[d] >= n - d.*

---

## See Also

- [Chapter 41: KMP](ch41-kmp.md) — The classic single-pattern matching algorithm; KMP's failure function and Z-array capture similar information.
- [Chapter 44: Suffix Array](ch44-suffix-array.md) — LCP arrays (computed via Z-algorithm or Kasai's algorithm) are essential for suffix array applications.
- [Chapter 45: Suffix Automaton](ch45-suffix-automaton.md) — A compressed automaton of all substrings; complements Z-algorithm for more complex string queries.
- [Chapter 46: Aho-Corasick](ch46-aho-corasick.md) — Multi-pattern matching; the failure function generalizes the Z/KMP concept to multiple patterns.
- [Chapter 40: Rolling Hash](ch40-rolling-hash.md) — Another approach to string matching; simpler but probabilistic.
