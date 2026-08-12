# Chapter 41: KMP Algorithm

The Knuth-Morris-Pratt (KMP) algorithm is a linear-time string matching algorithm. While the naive approach to finding a pattern in a text takes O(n·m) time (where n is the text length and m is the pattern length), KMP achieves O(n + m) by preprocessing the pattern to avoid redundant comparisons. The key insight is the **failure function** (also called the LPS — Longest Proper Prefix which is also Suffix — array), which tells us exactly how far back we can safely skip when a mismatch occurs.

---

## 41.1 The Failure Function (LPS Array)

### 41.1.1 Definition

The LPS array (Longest Proper Prefix which is also Suffix) for a pattern `p` of length `m` is an array `lps[0..m-1]` where `lps[i]` is the length of the longest proper prefix of `p[0..i]` which is also a suffix of `p[0..i]`.

"Proper" means the prefix cannot be the entire string itself.

**Example:** For pattern = "ABABAC":

| i | p[0..i] | Proper Prefixes | Proper Suffixes | Longest Match | lps[i] |
|---|---------|-----------------|-----------------|---------------|--------|
| 0 | A | {} | {} | none | 0 |
| 1 | AB | {A} | {B} | none | 0 |
| 2 | ABA | {A, AB} | {BA, A} | A | 1 |
| 3 | ABAB | {A, AB, ABA} | {BAB, AB, B} | AB | 2 |
| 4 | ABABA | {A, AB, ABA, ABAB} | {BABA, ABA, BA, A} | ABA | 3 |
| 5 | ABABAC | {A, AB, ABA, ABAB, ABABA} | {BABAC, ABAC, BAC, AC, C} | none | 0 |

So `lps = [0, 0, 1, 2, 3, 0]`.

### 41.1.2 What It Represents

When we're matching the pattern against the text and a mismatch occurs at position `j` in the pattern, `lps[j-1]` tells us the next position in the pattern to try — we don't need to go all the way back to the beginning. The characters before `lps[j-1]` are guaranteed to match because they're a prefix that matches the suffix we've already seen.

---

## 41.2 Building the LPS Array

### 41.2.1 Algorithm

```cpp
#include <iostream>
#include <vector>
#include <string>
using namespace std;

vector<int> buildLPS(const string& pattern) {
    int m = pattern.size();
    vector<int> lps(m, 0);

    int len = 0;  // length of the previous longest prefix-suffix
    int i = 1;

    while (i < m) {
        if (pattern[i] == pattern[len]) {
            len++;
            lps[i] = len;
            i++;
        } else {
            if (len != 0) {
                // Fall back to the previous longest prefix-suffix
                len = lps[len - 1];
                // Don't increment i — try again with the new len
            } else {
                lps[i] = 0;
                i++;
            }
        }
    }
    return lps;
}

int main() {
    string pattern = "ABABAC";
    auto lps = buildLPS(pattern);
    cout << "Pattern: " << pattern << endl;
    cout << "LPS:     ";
    for (int x : lps) cout << x << " ";
    cout << endl;  // 0 0 1 2 3 0

    string pattern2 = "AABAACAABAA";
    auto lps2 = buildLPS(pattern2);
    cout << "Pattern: " << pattern2 << endl;
    cout << "LPS:     ";
    for (int x : lps2) cout << x << " ";
    cout << endl;  // 0 1 0 1 2 0 1 2 3 4 5

    string pattern3 = "AAACAAAAAC";
    auto lps3 = buildLPS(pattern3);
    cout << "Pattern: " << pattern3 << endl;
    cout << "LPS:     ";
    for (int x : lps3) cout << x << " ";
    cout << endl;  // 0 1 2 0 1 2 3 3 3 4
    return 0;
}
```

### 41.2.2 Dry Run: Building LPS for "ABABAC"

```
pattern = "ABABAC"
lps = [0, 0, 0, 0, 0, 0]
len = 0, i = 1

i=1: pattern[1]='B' vs pattern[len=0]='A' → mismatch, len==0 → lps[1]=0, i=2
     lps = [0, 0, 0, 0, 0, 0]

i=2: pattern[2]='A' vs pattern[len=0]='A' → match! len=1, lps[2]=1, i=3
     lps = [0, 0, 1, 0, 0, 0]

i=3: pattern[3]='B' vs pattern[len=1]='B' → match! len=2, lps[3]=2, i=4
     lps = [0, 0, 1, 2, 0, 0]

i=4: pattern[4]='A' vs pattern[len=2]='A' → match! len=3, lps[4]=3, i=5
     lps = [0, 0, 1, 2, 3, 0]

i=5: pattern[5]='C' vs pattern[len=3]='B' → mismatch, len!=0 → len=lps[3-1]=lps[2]=1
     Try again: pattern[5]='C' vs pattern[len=1]='B' → mismatch, len!=0 → len=lps[1-1]=lps[0]=0
     Try again: pattern[5]='C' vs pattern[len=0]='A' → mismatch, len==0 → lps[5]=0, i=6
     lps = [0, 0, 1, 2, 3, 0]

Done!
```

**Complexity:** O(m) time, O(m) space. The key to the O(m) complexity is that `len` only increases by 1 per iteration of `i`, and when it decreases, it decreases from a previously increased value. The total number of decreases cannot exceed the total number of increases, which is bounded by m.

### 41.2.3 Dry Run: Building LPS for "AAACAAAAAC"

```
pattern = "AAACAAAAAC"
lps = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
len=0, i=1

i=1: 'A'=='A' → len=1, lps[1]=1, i=2.  lps=[0,1,0,0,0,0,0,0,0,0]
i=2: 'A'=='A' → len=2, lps[2]=2, i=3.  lps=[0,1,2,0,0,0,0,0,0,0]
i=3: 'C'!='A' → len=lps[1]=1. Try: 'C'!='A' → len=lps[0]=0. Try: 'C'!='A' → lps[3]=0, i=4.
     lps=[0,1,2,0,0,0,0,0,0,0]
i=4: 'A'=='A' → len=1, lps[4]=1, i=5.  lps=[0,1,2,0,1,0,0,0,0,0]
i=5: 'A'=='A' → len=2, lps[5]=2, i=6.  lps=[0,1,2,0,1,2,0,0,0,0]
i=6: 'A'=='A' → len=3, lps[6]=3, i=7.  lps=[0,1,2,0,1,2,3,0,0,0]
i=7: 'A'!='C' → len=lps[2]=2. Try: 'A'=='A' → len=3, lps[7]=3, i=8.
     lps=[0,1,2,0,1,2,3,3,0,0]
i=8: 'A'!='C' → len=lps[2]=2. Try: 'A'=='A' → len=3, lps[8]=3, i=9.
     lps=[0,1,2,0,1,2,3,3,3,0]
i=9: 'C'=='C' → len=4, lps[9]=4, i=10.
     lps=[0,1,2,0,1,2,3,3,3,4]

Done! lps = [0, 1, 2, 0, 1, 2, 3, 3, 3, 4]
```

---

## 41.3 KMP Search

### 41.3.1 The Algorithm

```cpp
#include <iostream>
#include <vector>
#include <string>
using namespace std;

vector<int> buildLPS(const string& pattern) {
    int m = pattern.size();
    vector<int> lps(m, 0);
    int len = 0, i = 1;
    while (i < m) {
        if (pattern[i] == pattern[len]) {
            len++;
            lps[i] = len;
            i++;
        } else {
            if (len != 0) {
                len = lps[len - 1];
            } else {
                lps[i] = 0;
                i++;
            }
        }
    }
    return lps;
}

// Returns all starting indices where pattern occurs in text
vector<int> kmpSearch(const string& text, const string& pattern) {
    vector<int> result;
    int n = text.size(), m = pattern.size();
    if (m == 0) return result;
    if (m > n) return result;

    vector<int> lps = buildLPS(pattern);

    int i = 0;  // index for text
    int j = 0;  // index for pattern

    while (i < n) {
        if (text[i] == pattern[j]) {
            i++;
            j++;
        }

        if (j == m) {
            // Found a match at index i - j
            result.push_back(i - j);
            j = lps[j - 1];  // continue searching for more matches
        } else if (i < n && text[i] != pattern[j]) {
            if (j != 0) {
                j = lps[j - 1];  // use the LPS to skip
            } else {
                i++;  // no prefix to fall back to, advance text
            }
        }
    }
    return result;
}

int main() {
    string text1 = "ABABDABACDABABCABAB";
    string pattern1 = "ABABCABAB";
    auto matches = kmpSearch(text1, pattern1);
    cout << "Text:    " << text1 << endl;
    cout << "Pattern: " << pattern1 << endl;
    cout << "Found at indices: ";
    for (int idx : matches) cout << idx << " ";
    cout << endl;  // 9

    string text2 = "AAAAABAAABA";
    string pattern2 = "AAAB";
    auto matches2 = kmpSearch(text2, pattern2);
    cout << "Found at indices: ";
    for (int idx : matches2) cout << idx << " ";
    cout << endl;  // 1 7

    string text3 = "ABABABAB";
    string pattern3 = "ABAB";
    auto matches3 = kmpSearch(text3, pattern3);
    cout << "Found at indices: ";
    for (int idx : matches3) cout << idx << " ";
    cout << endl;  // 0 2 4
    return 0;
}
```

### 41.3.2 Dry Run: KMP Search for text = "ABABDABACDABABCABAB", pattern = "ABABCABAB"

First, build LPS for "ABABCABAB":
```
lps = [0, 0, 1, 2, 0, 1, 2, 3, 4]
```

Now the search:

```
text    = A B A B D A B A C D A B A B C A B A B
pattern = A B A B C A B A B
lps     = 0 0 1 2 0 1 2 3 4

i=0, j=0: text[0]='A' == pattern[0]='A' → i=1, j=1
i=1, j=1: text[1]='B' == pattern[1]='B' → i=2, j=2
i=2, j=2: text[2]='A' == pattern[2]='A' → i=3, j=3
i=3, j=3: text[3]='B' == pattern[3]='B' → i=4, j=4
i=4, j=4: text[4]='D' != pattern[4]='C' → j=lps[3]=2
i=4, j=2: text[4]='D' != pattern[2]='A' → j=lps[1]=0
i=4, j=0: text[4]='D' != pattern[0]='A' → i=5

i=5, j=0: text[5]='A' == pattern[0]='A' → i=6, j=1
i=6, j=1: text[6]='B' == pattern[1]='B' → i=7, j=2
i=7, j=2: text[7]='A' == pattern[2]='A' → i=8, j=3
i=8, j=3: text[8]='C' != pattern[3]='B' → j=lps[2]=1
i=8, j=1: text[8]='C' != pattern[1]='B' → j=lps[0]=0
i=8, j=0: text[8]='C' != pattern[0]='A' → i=9

i=9, j=0: text[9]='D' != pattern[0]='A' → i=10

i=10, j=0: text[10]='A' == pattern[0]='A' → i=11, j=1
i=11, j=1: text[11]='B' == pattern[1]='B' → i=12, j=2
i=12, j=2: text[12]='A' == pattern[2]='A' → i=13, j=3
i=13, j=3: text[13]='B' == pattern[3]='B' → i=14, j=4
i=14, j=4: text[14]='C' == pattern[4]='C' → i=15, j=5
i=15, j=5: text[15]='A' == pattern[5]='A' → i=16, j=6
i=16, j=6: text[16]='B' == pattern[6]='B' → i=17, j=7
i=17, j=7: text[17]='A' == pattern[7]='A' → i=18, j=8
i=18, j=8: text[18]='B' == pattern[8]='B' → i=19, j=9

j==9==m → MATCH at index 19-9 = 10
j = lps[8] = 4

i=19, j=4: i==n → done

Result: [10]
```

**Complexity:** O(n + m) time. Each character in the text is examined at most once (i only increases), and each pattern position j is decreased at most as many times as it was increased. The LPS construction is O(m). Total: O(n + m). Space: O(m) for the LPS array.

---

## 41.4 Applications

### 41.4.1 Find All Occurrences

Already demonstrated above. The KMP search naturally finds all occurrences by continuing after each match.

### 41.4.2 Repeated Substring Pattern (LeetCode 459)

Given a string, check if it can be constructed by taking a substring and appending multiple copies of it.

```cpp
#include <iostream>
#include <string>
#include <vector>
using namespace std;

class Solution {
public:
    bool repeatedSubstringPattern(string s) {
        int n = s.size();
        // Build LPS array
        vector<int> lps(n, 0);
        int len = 0, i = 1;
        while (i < n) {
            if (s[i] == s[len]) {
                len++;
                lps[i] = len;
                i++;
            } else {
                if (len != 0) {
                    len = lps[len - 1];
                } else {
                    lps[i] = 0;
                    i++;
                }
            }
        }

        // The key insight:
        // If the string is made of repeated substrings, then
        // lps[n-1] gives us the length of the longest proper prefix-suffix.
        // The substring length would be n - lps[n-1].
        // If n is divisible by (n - lps[n-1]), the string is repeated.
        int longestPrefixSuffix = lps[n - 1];
        int candidateLen = n - longestPrefixSuffix;
        return longestPrefixSuffix > 0 && n % candidateLen == 0;
    }
};

int main() {
    Solution sol;
    cout << boolalpha;
    cout << sol.repeatedSubstringPattern("abab") << endl;      // true
    cout << sol.repeatedSubstringPattern("aba") << endl;       // false
    cout << sol.repeatedSubstringPattern("abcabcabcabc") << endl; // true
    cout << sol.repeatedSubstringPattern("a") << endl;         // false
    cout << sol.repeatedSubstringPattern("ababab") << endl;    // true
    return 0;
}
```

**Why this works:** If a string `s` of length `n` is formed by repeating a substring of length `d`, then:
- The LPS value at the last position `lps[n-1]` must be `n - d` (the longest proper prefix that's also a suffix covers all but one copy of the repeating unit).
- `n` must be divisible by `d = n - lps[n-1]`.

**Complexity:** O(n) time, O(n) space.

### 41.4.3 Shortest Palindrome (LeetCode 215)

Find the shortest palindrome by adding characters in front.

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
using namespace std;

class Solution {
public:
    string shortestPalindrome(string s) {
        // The idea: find the longest palindromic prefix of s.
        // Then we only need to add the reverse of the remaining suffix in front.
        //
        // Trick: use KMP on (s + "#" + reverse(s))
        // The LPS value at the last position tells us the length of the
        // longest palindromic prefix.

        string rev = s;
        reverse(rev.begin(), rev.end());
        string combined = s + "#" + rev;

        int n = combined.size();
        vector<int> lps(n, 0);
        int len = 0, i = 1;
        while (i < n) {
            if (combined[i] == combined[len]) {
                len++;
                lps[i] = len;
                i++;
            } else {
                if (len != 0) {
                    len = lps[len - 1];
                } else {
                    lps[i] = 0;
                    i++;
                }
            }
        }

        int palinPrefixLen = lps[n - 1];
        string suffix = s.substr(palinPrefixLen);
        reverse(suffix.begin(), suffix.end());
        return suffix + s;
    }
};

int main() {
    Solution sol;
    cout << sol.shortestPalindrome("aacecaaa") << endl;  // "aaacecaaa"
    cout << sol.shortestPalindrome("abcd") << endl;      // "dcbabcd"
    cout << sol.shortestPalindrome("aba") << endl;       // "aba"
    cout << sol.shortestPalindrome("") << endl;          // ""
    return 0;
}
```

**How it works:** By constructing `s + "#" + reverse(s)`, the LPS at the end gives us the length of the longest prefix of `s` that is also a suffix of `reverse(s)` — which is exactly the longest palindromic prefix of `s`. The `#` separator ensures we don't get matches that span across the boundary.

**Complexity:** O(n) time, O(n) space.

### 41.4.4 Implement strStr() (LeetCode 28)

```cpp
#include <iostream>
#include <string>
#include <vector>
using namespace std;

class Solution {
public:
    int strStr(string haystack, string needle) {
        if (needle.empty()) return 0;
        int n = haystack.size(), m = needle.size();
        if (m > n) return -1;

        // Build LPS
        vector<int> lps(m, 0);
        int len = 0, idx = 1;
        while (idx < m) {
            if (needle[idx] == needle[len]) {
                len++;
                lps[idx] = len;
                idx++;
            } else {
                if (len != 0) {
                    len = lps[len - 1];
                } else {
                    lps[idx] = 0;
                    idx++;
                }
            }
        }

        // KMP search
        int i = 0, j = 0;
        while (i < n) {
            if (haystack[i] == needle[j]) {
                i++; j++;
            }
            if (j == m) {
                return i - j;
            }
            if (i < n && haystack[i] != needle[j]) {
                if (j != 0) j = lps[j - 1];
                else i++;
            }
        }
        return -1;
    }
};

int main() {
    Solution sol;
    cout << sol.strStr("sadbutsad", "sad") << endl;   // 0
    cout << sol.strStr("leetcode", "leeto") << endl;  // -1
    cout << sol.strStr("hello", "ll") << endl;         // 2
    return 0;
}
```

**Complexity:** O(n + m) time, O(m) space.

---

## Interview Tips

1. **Know the LPS construction cold.** Interviewers often ask to implement KMP from scratch. The LPS construction is the tricky part — practice it until it's muscle memory.
2. **Understand why KMP is O(n+m).** The `i` pointer never decreases (text pointer only moves forward). The `j` pointer (pattern pointer) can decrease, but the total number of decreases is bounded by the total number of increases, which is ≤ n.
3. **KMP vs other string algorithms.** KMP is best for single-pattern matching. For multiple patterns, consider Aho-Corasick. For suffix-based queries, consider suffix arrays or suffix trees.
4. **The `#` separator trick** in Shortest Palindrome is a common pattern — use a character that doesn't appear in the input to prevent cross-boundary matches.

## Common Mistakes

- **Off-by-one in LPS.** `lps[i]` is the length of the longest proper prefix-suffix of `pattern[0..i]`, not an index. Don't confuse it with the position.
- **Forgetting to handle j==m before the mismatch check.** In the search loop, check `j == m` before checking for mismatches, otherwise you'll miss matches at the very end.
- **Not using the `#` separator** in Shortest Palindrome. Without it, the LPS might find a match that's not a true palindromic prefix.
- **Confusing LPS with Z-array.** They're related but different. LPS[i] = longest proper prefix of `p[0..i]` that's also a suffix. Z[i] = longest prefix match starting at position i.

## Practice Problems

1. **Repeated String Match** (LeetCode 686) — Find the minimum number of times to repeat `a` so that `b` is a substring. *Hint: Repeat `a` until its length ≥ `b`'s length + `a`'s length, then use KMP.*
2. **Longest Happy Prefix** (LeetCode 1392) — Find the longest prefix which is also a suffix. *Hint: This is exactly `lps[n-1]`.*
3. **Period of a String** — Find the smallest period. *Hint: If `lps[n-1] > 0` and `n % (n - lps[n-1]) == 0`, the period is `n - lps[n-1]`.*
4. **Count and Say** (LeetCode 38) — While not directly KMP, understanding pattern matching helps.
5. **Rotate String** (LeetCode 796) — Check if one string is a rotation of another. *Hint: Check if `s` is a substring of `goal + goal`.*

---

## See Also

- [Chapter 42: Z Algorithm](ch42-z-algorithm.md) — An alternative to KMP for pattern matching; Z-array computes the same information as the failure function but from a different perspective.
- [Chapter 44: Suffix Array](ch44-suffix-array.md) — For multiple pattern searches and substring queries; suffix arrays generalize single-pattern matching.
- [Chapter 45: Suffix Automaton](ch45-suffix-automaton.md) — A compressed automaton of all substrings; enables O(n) construction and O(m) pattern matching.
- [Chapter 46: Aho-Corasick](ch46-aho-corasick.md) — Multi-pattern matching; extends KMP's failure function to a trie of patterns.
- [Chapter 40: Rolling Hash](ch40-rolling-hash.md) — Hash-based pattern matching as an alternative to KMP; simpler but probabilistic.
- [Chapter 16: Trie](ch16-trie.md) — Aho-Corasick is built on tries; understanding trie structure is prerequisite.
