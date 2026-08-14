# String Algorithms: A Unified Guide

This chapter surveys the major string algorithms you need for interviews and competitive programming. Individual algorithms (KMP, Z-Algorithm, Aho-Corasick, etc.) are covered in dedicated chapters; here we focus on **when to use which**, their relationships, and comparison.

---

## Pattern Matching Algorithms

### KMP Algorithm (Knuth-Morris-Pratt)

**Intuition:** When a mismatch occurs at position `j` in the pattern, we already know the first `j` characters match. KMP precomputes the longest proper prefix that is also a suffix (LPS array) to avoid re-examining known-matched characters.

```cpp
vector<int> computeLPS(const string& pat) {
    int n = pat.size();
    vector<int> lps(n, 0);
    for (int i = 1, len = 0; i < n; ) {
        if (pat[i] == pat[len]) lps[i++] = ++len;
        else if (len) len = lps[len - 1];
        else lps[i++] = 0;
    }
    return lps;
}

vector<int> kmpSearch(const string& text, const string& pat) {
    vector<int> lps = computeLPS(pat);
    vector<int> matches;
    for (int i = 0, j = 0; i < text.size(); ) {
        if (text[i] == pat[j]) { i++; j++; }
        if (j == pat.size()) { matches.push_back(i - j); j = lps[j - 1]; }
        else if (i < text.size() && text[i] != pat[j]) {
            if (j) j = lps[j - 1]; else i++;
        }
    }
    return matches;
}
```

**Complexity:** O(n + m) time, O(m) space. Never backtracks on text — critical for stream processing.

**Interview use:** "Find all occurrences of a pattern in a text" when you need guaranteed O(n + m) and cannot afford hash collisions.

---

### Z Algorithm

Computes an array `Z[i]` = length of longest substring starting at `i` that matches a prefix of the string. Concatenate `pattern + '$' + text` and the Z-values at positions >= m+1 give match lengths.

```python
def z_algorithm(s):
    n = len(s)
    z = [0] * n
    l = r = 0
    for i in range(1, n):
        if i <= r:
            z[i] = min(r - i + 1, z[i - l])
        while i + z[i] < n and s[z[i]] == s[i + z[i]]:
            z[i] += 1
        if i + z[i] - 1 > r:
            l, r = i, i + z[i] - 1
    return z

def z_search(text, pattern):
    z = z_algorithm(pattern + '$' + text)
    m = len(pattern)
    return [i - m - 1 for i in range(m + 1, len(z)) if z[i] == m]
```

**Complexity:** O(n + m) time, O(n + m) space. Simpler to implement than KMP for many people.

---

### Rabin-Karp (Rolling Hash)

Uses hashing to compare pattern against text windows in O(1) per position after preprocessing.

```cpp
long long computeHash(const string& s, long long base, long long mod) {
    long long h = 0;
    for (char c : s) h = (h * base + c) % mod;
    return h;
}

vector<int> rabinKarp(const string& text, const string& pat) {
    long long base = 257, mod = 1e9 + 7;
    int n = text.size(), m = pat.size();
    long long patHash = computeHash(pat, base, mod);
    long long txtHash = computeHash(text.substr(0, m), base, mod);
    long long power = 1;
    for (int i = 0; i < m - 1; i++) power = (power * base) % mod;

    vector<int> matches;
    if (txtHash == patHash && text.substr(0, m) == pat) matches.push_back(0);
    for (int i = 1; i <= n - m; i++) {
        txtHash = ((txtHash - text[i-1] * power) * base + text[i + m - 1]) % mod;
        if (txtHash < 0) txtHash += mod;
        if (txtHash == patHash && text.substr(i, m) == pat)
            matches.push_back(i);
    }
    return matches;
}
```

**Collision handling:** Use double hashing (two different moduli), or verify matches against actual strings. For interviews, always mention collision probability.

**Complexity:** O(n + m) average, O(nm) worst case. Best when searching multiple patterns or when you need approximate matching.

---

### Aho-Corasick (Multi-Pattern Matching)

Builds a trie of all patterns with failure links (similar to KMP's LPS but across a trie). Matches all patterns against text in a single pass.

**Complexity:** O(total pattern length) to build, O(text length + number of matches) to search. Ideal when you have many patterns to find simultaneously.

**Interview use:** Given a list of keywords and a document, find all occurrences of any keyword.

---

### Manacher's Algorithm

Finds all palindromic substrings in O(n). Maintains a rightmost palindrome boundary and mirrors previously computed radii.

```python
def manacher(s):
    # Transform: insert '|' between characters
    t = '|'.join('^{}$'.format(s))
    n = len(t)
    p = [0] * n
    center = right = 0
    for i in range(1, n - 1):
        mirror = 2 * center - i
        if i < right:
            p[i] = min(right - i, p[mirror])
        while t[i + p[i] + 1] == t[i - p[i] - 1]:
            p[i] += 1
        if i + p[i] > right:
            center, right = i, i + p[i]
    return p  # p[i] = radius of palindrome centered at i
```

**Complexity:** O(n) time, O(n) space. Linear-time palindrome finding — a rare interview question but impressive to know.

---

### Suffix Arrays and Suffix Trees (Overview)

**Suffix Array:** Sorted array of all suffix indices. Enables binary search for patterns in O(m log n), LCP queries in O(1) with RMQ preprocessing. Construction: O(n log n) via doubling or O(n) via SA-IS.

**Suffix Tree:** Compressed trie of all suffixes. Supports pattern matching in O(m), longest repeated substring, longest common substring of two strings, and many stringology problems. O(n) construction (Ukkonen's algorithm) but high constant factor.

---

## Comparison Table

| Algorithm | Preprocessing | Query | Best For |
|---|---|---|---|
| KMP | O(m) | O(n + m) total | Single pattern, guaranteed linear |
| Z Algorithm | O(m) | O(n + m) total | Single pattern, simpler code |
| Rabin-Karp | O(m) | O(n) average | Multiple patterns, approximate match |
| Aho-Corasick | O(|P|) | O(n + output) | Multiple patterns simultaneously |
| Manacher's | O(n) | O(n) total | All palindromic substrings |
| Suffix Array | O(n log n) | O(m log n) per pattern | Complex string queries, LCP |
| Suffix Tree | O(n) | O(m) per pattern | Theoretical optimal, many queries |

---

## Interview Questions

1. **Given a string `s` and pattern `p`, find all starting indices of `p` in `s`.** Which algorithm would you use and why? What if `p` contains wildcards?

2. **Find the longest palindromic substring.** Compare the O(n²) expand-around-center approach with Manacher's O(n) approach. When would you prefer the simpler solution?

3. **Given a dictionary of 1000 words and a document, find all words that appear in the document.** Design the optimal solution using Aho-Corasick. What is the time complexity?

4. **Explain why KMP never backtracks on the text pointer.** Prove that the LPS array guarantees no missed matches.

5. **When would Rabin-Karp be preferred over KMP?** Discuss trade-offs in terms of expected vs. worst-case performance and ease of implementation.

6. **How does the rolling hash work for substring comparison?** Derive the hash update formula and explain modular arithmetic's role.

7. **Design a system to detect plagiarism between two documents.** Which string algorithms would you use? Discuss suffix array / LCP approaches.

8. **Compare suffix arrays and suffix trees.** When would you choose one over the other? Discuss space vs. time trade-offs.

9. **Implement a function to find the shortest unique substring of every prefix of a string.** How would suffix arrays help?

10. **Given two strings, find their longest common substring in O(n log n) time.** Describe the suffix array + LCP approach.
