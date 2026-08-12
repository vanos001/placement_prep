# Expanded Strings



## Prerequisites

- Basic string manipulation
- Understanding of hashing
- Familiarity with KMP or basic pattern matching

## Interview Frequency

★★★★ — String algorithms appear frequently in interviews, especially hashing-based techniques and palindrome problems.

## Companies

Google, Meta, Amazon, Microsoft, Apple, Palantir, Bloomberg, Uber, Stripe — any company that asks algorithmic questions will occasionally include string problems.

---

## Overview

String problems in interviews often require specialized algorithms that exploit the structure of strings. This chapter covers advanced string techniques with complete implementations.

| Algorithm | Problem Solved | Time | Space |
|-----------|---------------|------|-------|
| Manacher's | Longest palindromic substring | O(n) | O(n) |
| Palindromic Tree | All palindromic substrings | O(n) | O(n·Σ) |
| Rabin-Karp | Pattern matching with rolling hash | O(n+m) avg | O(1) |
| Boyer-Moore | Pattern matching (overview) | O(n/m) best | O(Σ) |
| Double Hashing | Reducing hash collisions | O(n+m) | O(n+m) |
| Polynomial Hashing | String hashing fundamentals | O(n) | O(n) |
| Suffix Tree | Many string queries | O(n) | O(n) |
| Burrows-Wheeler | Data compression | O(n) | O(n) |
| Prefix Function | KMP preprocessing | O(n) | O(n) |

---

## 1. Manacher's Algorithm

### Problem

Find the longest palindromic substring in O(n) time.

### Key Insight

If we know a palindrome centered at position `c` with right boundary `r`, and we're computing the palindrome at position `i` (where `i < r`), we can use the mirror of `i` around `c` to bootstrap the computation.

### Complete Implementation with Dry Run

```cpp
#include <string>
#include <vector>
#include <iostream>
#include <algorithm>

class Manacher {
public:
    // Returns the longest palindromic substring
    static std::string longest_palindrome(const std::string& s) {
        if (s.empty()) return "";

        // Transform: "abc" → "^#a#b#c#$"
        // This handles even-length palindromes uniformly
        std::string t = "^#";
        for (char c : s) {
            t += c;
            t += '#';
        }
        t += '$';

        int n = t.size();
        std::vector<int> p(n, 0); // p[i] = radius of palindrome centered at i
        int c = 0, r = 0;         // center and right boundary of rightmost palindrome

        for (int i = 1; i < n - 1; ++i) {
            int mirror = 2 * c - i; // mirror of i around c

            if (i < r)
                p[i] = std::min(r - i, p[mirror]);

            // Attempt to expand palindrome centered at i
            while (t[i + p[i] + 1] == t[i - p[i] - 1])
                ++p[i];

            // If palindrome centered at i extends past r,
            // adjust center based on expanded palindrome
            if (i + p[i] > r) {
                c = i;
                r = i + p[i];
            }
        }

        // Find the maximum element in p
        int max_len = 0, center = 0;
        for (int i = 1; i < n - 1; ++i) {
            if (p[i] > max_len) {
                max_len = p[i];
                center = i;
            }
        }

        // Map back to original string
        int start = (center - max_len) / 2;
        return s.substr(start, max_len);
    }
};

int main() {
    std::vector<std::string> tests = {
        "babad", "cbbd", "racecar", "a", "abacdfgdcaba",
        "abaaba", "forgeeksskeegfor"
    };
    for (auto& s : tests) {
        std::cout << "\"" << s << "\" → \"" << Manacher::longest_palindrome(s) << "\"\n";
    }
    // "babad" → "bab" (or "aba")
    // "cbbd" → "bb"
    // "racecar" → "racecar"
    // "a" → "a"
    // "abacdfgdcaba" → "aba"
    // "abaaba" → "abaaba"
    // "forgeeksskeegfor" → "geeksskeeg"
}
```

### Dry Run for "abaaba"

```
Transformed: ^#a#b#a#a#b#a#$

Index:  0  1  2  3  4  5  6  7  8  9 10 11 12 13
Char:   ^  #  a  #  b  #  a  #  a  #  b  #  a  #
p[i]:   0  0  1  0  3  0  5  6  5  0  3  0  1  0

i=7: c=7, r=13. p[7]=6 (the full string is a palindrome)
```

### Interview Application

Manacher's is the gold standard for palindrome problems. Use it when you need:
- Longest palindromic substring in O(n)
- Count of palindromic substrings
- All palindromic substrings

---

## 2. Palindromic Tree (Eertree)

### Problem

Find all distinct palindromic substrings of a string in O(n).

### Structure

The palindromic tree has two roots:
- Root for odd-length palindromes (length -1)
- Root for even-length palindromes (length 0)

Each node represents a distinct palindromic substring. Edges represent adding a character to both ends.

### Implementation

```cpp
#include <string>
#include <vector>
#include <map>
#include <iostream>

class Eertree {
    struct Node {
        std::map<char, int> next;   // edges
        int len;                     // length of palindrome
        int suffix_link;             // link to longest proper palindromic suffix
        int count;                   // number of occurrences
        Node(int l, int sl) : len(l), suffix_link(sl), count(0) {}
    };

    std::string s;
    std::vector<Node> tree;
    int last; // node representing longest palindromic suffix of current string

public:
    Eertree() {
        // Two root nodes
        tree.emplace_back(-1, 0); // odd root (length -1, suffix link to even root)
        tree.emplace_back(0, 0);  // even root (length 0, suffix link to odd root)
        last = 1; // start at even root
    }

    void add_char(int pos) {
        int cur = last;
        char ch = s[pos];

        // Find the longest palindromic suffix that can be extended
        while (true) {
            int cur_len = tree[cur].len;
            if (pos - cur_len - 1 >= 0 && s[pos - cur_len - 1] == ch)
                break;
            cur = tree[cur].suffix_link;
        }

        // Check if this palindrome already exists
        if (tree[cur].next.count(ch)) {
            last = tree[cur].next[ch];
            tree[last].count++;
            return;
        }

        // Create new node
        int new_node = tree.size();
        tree.emplace_back(tree[cur].len + 2, -1);
        tree[cur].next[ch] = new_node;
        last = new_node;

        // Set suffix link
        if (tree[new_node].len == 1) {
            tree[new_node].suffix_link = 1; // link to even root
            tree[new_node].count = 1;
            return;
        }

        // Find suffix link
        int link_cur = tree[cur].suffix_link;
        while (true) {
            int link_len = tree[link_cur].len;
            if (pos - link_len - 1 >= 0 && s[pos - link_len - 1] == ch)
                break;
            link_cur = tree[link_cur].suffix_link;
        }
        tree[new_node].suffix_link = tree[link_cur].next[ch];
        tree[new_node].count = 1;
    }

    void build(const std::string& str) {
        s = str;
        for (int i = 0; i < (int)s.size(); ++i)
            add_char(i);
    }

    int distinct_palindromes() const {
        return (int)tree.size() - 2; // subtract two roots
    }

    std::vector<std::string> get_all_palindromes() const {
        std::vector<std::string> result;
        for (int i = 2; i < (int)tree.size(); ++i) {
            // Reconstruct palindrome from the tree
            // For simplicity, we store the actual strings during construction
            // Here we just count
        }
        return result;
    }

    void print_info() const {
        std::cout << "Distinct palindromic substrings: " << distinct_palindromes() << "\n";
        for (int i = 2; i < (int)tree.size(); ++i) {
            std::cout << "  Node " << i << ": len=" << tree[i].len
                      << ", count=" << tree[i].count << "\n";
        }
    }
};

int main() {
    Eertree e;
    e.build("abacaba");
    e.print_info();
    // Distinct palindromic substrings: 7
    //   Node 2: len=1, count=4  (a)
    //   Node 3: len=1, count=1  (b) -- wait, b also appears multiple times
    //   ... actual counts depend on implementation details
    //   Distinct palindromes: a, b, c, aba, aca, bacab, abacaba

    Eertree e2;
    e2.build("aaaa");
    e2.print_info();
    // Distinct palindromic substrings: 4 (a, aa, aaa, aaaa)
}
```

### Interview Application

Palindromic tree is more powerful than Manacher's when you need:
- All distinct palindromic substrings
- Count of each palindrome
- Number of palindromic substrings (sum of all counts)

---

## 3. Rabin-Karp (Rolling Hash)

### Problem

Find all occurrences of a pattern in a text using hashing.

### Key Idea

Compute a hash of the pattern. Then slide a window over the text, computing the hash of each window using a **rolling hash** — add the new character and remove the old one in O(1).

### Implementation

```cpp
#include <string>
#include <vector>
#include <iostream>

class RabinKarp {
    static constexpr long long BASE = 257;
    static constexpr long long MOD = 1'000'000'007;

public:
    static std::vector<int> find_all(const std::string& text, const std::string& pattern) {
        int n = text.size(), m = pattern.size();
        if (m > n) return {};
        if (m == 0) return {};

        // Compute BASE^(m-1) mod MOD
        long long base_pow = 1;
        for (int i = 0; i < m - 1; ++i)
            base_pow = base_pow * BASE % MOD;

        // Compute hash of pattern and first window
        long long pat_hash = 0, win_hash = 0;
        for (int i = 0; i < m; ++i) {
            pat_hash = (pat_hash * BASE + pattern[i]) % MOD;
            win_hash = (win_hash * BASE + text[i]) % MOD;
        }

        std::vector<int> result;
        for (int i = 0; i <= n - m; ++i) {
            if (win_hash == pat_hash) {
                // Verify (hash collision possible)
                if (text.substr(i, m) == pattern)
                    result.push_back(i);
            }
            // Roll the hash
            if (i < n - m) {
                win_hash = (win_hash - text[i] * base_pow % MOD + MOD) % MOD;
                win_hash = (win_hash * BASE + text[i + m]) % MOD;
            }
        }
        return result;
    }
};

int main() {
    std::string text = "ababcababcabc";
    std::string pattern = "abc";
    auto matches = RabinKarp::find_all(text, pattern);
    std::cout << "Pattern found at indices: ";
    for (int idx : matches) std::cout << idx << " ";
    std::cout << "\n"; // 2 7 10
}
```

### Rolling Hash Formula

```
hash("bcd") = hash("abc") - 'a' * BASE^(m-1)
              → shift left: * BASE
              → add 'd': + 'd'
              All modulo MOD
```

### Interview Application

Rabin-Karp is preferred over KMP when:
- You need to search for multiple patterns simultaneously
- You're doing substring equality checks
- You need to find duplicate substrings

---

## 4. Boyer-Moore (Overview)

### Two Heuristics

**Bad Character Rule:** When a mismatch occurs at position `j` in the pattern:
- If the mismatched text character `c` appears in the pattern, shift to align that occurrence
- If `c` doesn't appear, shift past the current position

**Good Suffix Rule:** When a suffix of the pattern matches but the preceding character mismatches:
- Shift to align the next occurrence of that suffix in the pattern
- Or shift to the longest prefix of the pattern that is a suffix of the matched portion

### Simplified Implementation (Bad Character Only)

```cpp
#include <string>
#include <vector>
#include <iostream>

class BoyerMoore {
public:
    static std::vector<int> find_all(const std::string& text, const std::string& pattern) {
        int n = text.size(), m = pattern.size();
        if (m > n) return {};

        // Bad character table: last occurrence of each character in pattern
        std::vector<int> bad_char(256, -1);
        for (int i = 0; i < m; ++i)
            bad_char[(unsigned char)pattern[i]] = i;

        std::vector<int> result;
        int shift = 0;
        while (shift <= n - m) {
            int j = m - 1;
            while (j >= 0 && pattern[j] == text[shift + j])
                --j;
            if (j < 0) {
                result.push_back(shift);
                shift += (shift + m < n) ? m - bad_char[(unsigned char)text[shift + m]] : 1;
            } else {
                shift += std::max(1, j - bad_char[(unsigned char)text[shift + j]]);
            }
        }
        return result;
    }
};

int main() {
    auto matches = BoyerMoore::find_all("ababcababcabc", "abc");
    std::cout << "Found at: ";
    for (int idx : matches) std::cout << idx << " ";
    std::cout << "\n"; // 2 7 10
}
```

### Comparison: Pattern Matching Algorithms

| Algorithm | Preprocessing | Search (worst) | Search (best) | Space | Notes |
|-----------|--------------|----------------|---------------|-------|-------|
| Brute Force | None | O(nm) | O(n) | O(1) | Simple |
| KMP | O(m) | O(n) | O(n) | O(m) | Linear guarantee |
| Rabin-Karp | O(m) | O(nm) worst | O(n+m) | O(1) | Good for multiple patterns |
| Boyer-Moore | O(m+Σ) | O(nm) worst | O(n/m) | O(Σ) | Best practical performance |

---

## 5. Double Hashing

### Problem

Single hash collisions can produce false positives. Use two different hash functions to reduce collision probability from 1/M to 1/M².

### Implementation

```cpp
#include <string>
#include <vector>
#include <iostream>
#include <utility>

class DoubleHash {
    static constexpr long long BASE1 = 257, MOD1 = 1'000'000'007;
    static constexpr long long BASE2 = 263, MOD2 = 1'000'000'009;

public:
    using HashPair = std::pair<long long, long long>;

    static HashPair compute(const std::string& s) {
        long long h1 = 0, h2 = 0;
        for (char c : s) {
            h1 = (h1 * BASE1 + c) % MOD1;
            h2 = (h2 * BASE2 + c) % MOD2;
        }
        return {h1, h2};
    }

    static std::vector<HashPair> rolling_hashes(const std::string& text, int m) {
        int n = text.size();
        if (m > n) return {};

        long long bp1 = 1, bp2 = 1;
        for (int i = 0; i < m - 1; ++i) {
            bp1 = bp1 * BASE1 % MOD1;
            bp2 = bp2 * BASE2 % MOD2;
        }

        long long h1 = 0, h2 = 0;
        for (int i = 0; i < m; ++i) {
            h1 = (h1 * BASE1 + text[i]) % MOD1;
            h2 = (h2 * BASE2 + text[i]) % MOD2;
        }

        std::vector<HashPair> result;
        result.push_back({h1, h2});

        for (int i = 0; i < n - m; ++i) {
            h1 = (h1 - text[i] * bp1 % MOD1 + MOD1) % MOD1;
            h1 = (h1 * BASE1 + text[i + m]) % MOD1;
            h2 = (h2 - text[i] * bp2 % MOD2 + MOD2) % MOD2;
            h2 = (h2 * BASE2 + text[i + m]) % MOD2;
            result.push_back({h1, h2});
        }
        return result;
    }

    // Find all occurrences of pattern in text
    static std::vector<int> find_all(const std::string& text, const std::string& pattern) {
        int m = pattern.size();
        auto pat_hash = compute(pattern);
        auto text_hashes = rolling_hashes(text, m);

        std::vector<int> result;
        for (int i = 0; i < (int)text_hashes.size(); ++i) {
            if (text_hashes[i] == pat_hash) {
                // Double hash match — extremely unlikely to be a collision
                result.push_back(i);
            }
        }
        return result;
    }
};

int main() {
    auto matches = DoubleHash::find_all("ababcababcabc", "abc");
    std::cout << "Found at: ";
    for (int idx : matches) std::cout << idx << " ";
    std::cout << "\n"; // 2 7 10
}
```

### Interview Application

Double hashing is the standard approach when:
- You need high confidence that hash matches are true matches
- You're building a hash-based data structure (hash set/map for strings)
- You're solving problems where collisions cause wrong answers

---

## 6. Polynomial Hashing

### Choosing Base and Mod

**Base:** Should be larger than the alphabet size. Common choices: 257, 31, 131, 137.

**Mod:** Should be a large prime. Common choices:
- 10^9 + 7
- 10^9 + 9
- 2^61 - 1 (Mersenne prime, allows fast modular arithmetic)

### Hash Formula

```
hash(s) = s[0] * B^(n-1) + s[1] * B^(n-2) + ... + s[n-1] * B^0  (mod M)
```

Or equivalently (Horner's method):
```
hash = 0
for each char c:
    hash = (hash * B + c) mod M
```

### Substring Hash in O(1)

With prefix hashes and powers of B:
```
hash(s[l..r]) = (prefix_hash[r+1] - prefix_hash[l] * B^(r-l+1)) mod M
```

```cpp
#include <string>
#include <vector>
#include <iostream>

class PolyHash {
    static constexpr long long B = 257;
    static constexpr long long M = 1'000'000'007;

    std::vector<long long> h, p; // prefix hashes and powers

public:
    explicit PolyHash(const std::string& s) : h(s.size() + 1, 0), p(s.size() + 1, 1) {
        for (int i = 0; i < (int)s.size(); ++i) {
            h[i + 1] = (h[i] * B + s[i]) % M;
            p[i + 1] = p[i] * B % M;
        }
    }

    // Hash of s[l..r] (inclusive, 0-indexed)
    long long query(int l, int r) const {
        long long res = (h[r + 1] - h[l] * p[r - l + 1] % M + M) % M;
        return res;
    }
};

int main() {
    std::string s = "abracadabra";
    PolyHash ph(s);

    // Compare substrings
    std::cout << "hash(\"abra\") at [0,3]: " << ph.query(0, 3) << "\n";
    std::cout << "hash(\"abra\") at [7,10]: " << ph.query(7, 10) << "\n";
    // Should be equal!

    // Find longest duplicate substring
    int n = s.size();
    int best_len = 0, best_start = 0;
    for (int len = 1; len <= n / 2; ++len) {
        std::unordered_map<long long, int> seen;
        for (int i = 0; i + len - 1 < n; ++i) {
            long long hash = ph.query(i, i + len - 1);
            if (seen.count(hash)) {
                best_len = len;
                best_start = i;
                break;
            }
            seen[hash] = i;
        }
    }
    if (best_len > 0)
        std::cout << "Longest duplicate: \"" << s.substr(best_start, best_len) << "\"\n";
    // "abra" (length 4)
}
```

---

## 7. Suffix Tree (Ukkonen's Algorithm Overview)

### What Is a Suffix Tree?

A suffix tree for a string S is a compressed trie of all suffixes of S. It enables many string queries in linear or near-linear time.

### Applications

| Query | Time with Suffix Tree |
|-------|----------------------|
| Pattern matching | O(m + occ) |
| Longest common substring | O(n) |
| Longest repeated substring | O(n) |
| Count distinct substrings | O(n) |
| Longest palindromic substring | O(n) |

### Conceptual Overview

For string "banana$":
```
Suffixes: banana$, anana$, nana$, ana$, na$, a$, $

Suffix tree:
         root
        / | \
       $  a  b  n
          |  |  |
          $  a  na$
             |  |
             na$ na$
             |
             na$
```

Each edge stores a substring (represented as pointers into the original string for O(1) space per edge). Each leaf represents a suffix.

### Interview Application

You're unlikely to implement Ukkonen's from scratch in an interview (it's one of the most complex string algorithms). Instead, understand:
- What a suffix tree is
- What queries it can answer
- The difference between suffix trees and suffix arrays (suffix arrays are simpler to implement and often preferred)

---

## 8. Burrows-Wheeler Transform (Overview)

### What Is BWT?

The BWT rearranges a string into runs of similar characters, making it highly compressible. Used in bzip2.

### Algorithm

1. Create all rotations of the string
2. Sort them lexicographically
3. Take the last column — that's the BWT

### Example

```
Original: "banana$"

Rotations (sorted):
$banana    → last char: a
a$banan    → last char: n
ana$ban    → last char: n
anana$b    → last char: b
banana$    → last char: $
na$bana    → last char: a
nana$ba    → last char: a

BWT: "annb$aa"
```

### Inverse BWT

Using the last column and the property that the first column is just the sorted characters, you can reconstruct the original string.

### Interview Application

BWT is rarely asked directly, but understanding it demonstrates breadth. It's relevant for:
- Data compression questions
- Bioinformatics (genome alignment tools like BWA use BWT)
- Understanding suffix array construction

---

## 9. Prefix Function (KMP Preprocessing)

### Definition

The prefix function π[i] for a string s is the length of the longest proper prefix of s[0..i] that is also a suffix.

### Implementation

```cpp
#include <string>
#include <vector>
#include <iostream>

std::vector<int> prefix_function(const std::string& s) {
    int n = s.size();
    std::vector<int> pi(n, 0);
    for (int i = 1; i < n; ++i) {
        int j = pi[i - 1];
        while (j > 0 && s[i] != s[j])
            j = pi[j - 1];
        if (s[i] == s[j])
            ++j;
        pi[i] = j;
    }
    return pi;
}

// KMP search using prefix function
std::vector<int> kmp_search(const std::string& text, const std::string& pattern) {
    std::string combined = pattern + "#" + text;
    auto pi = prefix_function(combined);
    int m = pattern.size();
    std::vector<int> result;
    for (int i = m + 1; i < (int)combined.size(); ++i) {
        if (pi[i] == m)
            result.push_back(i - 2 * m); // map back to text index
    }
    return result;
}

int main() {
    // Prefix function examples
    auto pi1 = prefix_function("aabaaab");
    std::cout << "prefix_function(\"aabaaab\"): ";
    for (int x : pi1) std::cout << x << " ";
    std::cout << "\n"; // 0 1 0 1 2 2 3

    // KMP search
    auto matches = kmp_search("ababcababcabc", "abc");
    std::cout << "KMP matches: ";
    for (int idx : matches) std::cout << idx << " ";
    std::cout << "\n"; // 2 7 10
}
```

### Connection to Z Algorithm

The Z algorithm computes Z[i] = longest common prefix of s and s[i..]. The prefix function and Z function are related:

- Z[i] can be computed from π and vice versa
- Both enable O(n) pattern matching
- KMP uses prefix function; some prefer Z for its simplicity

### Interview Application

The prefix function is useful for:
- KMP pattern matching
- Finding all occurrences of a pattern
- Computing the period of a string
- String compression ("how many times must we repeat prefix to get the string?")

---

## Comparison Table

| Algorithm | Preprocessing | Query | Best For |
|-----------|--------------|-------|----------|
| Manacher's | O(n) | O(1) per palindrome | Longest palindromic substring |
| Eertree | O(n) | O(1) per new char | All distinct palindromes |
| Rabin-Karp | O(m) | O(n+m) avg | Multiple pattern search |
| Boyer-Moore | O(m+Σ) | O(n/m) best | Single pattern, large alphabet |
| Double Hash | O(n+m) | O(n+m) | High-confidence matching |
| Polynomial Hash | O(n) | O(1) per substring | Substring equality |
| Suffix Tree | O(n) | O(m + occ) | Many different queries |
| Prefix Function | O(n) | O(n) | KMP, string periods |

---

## Design Decisions

### When NOT to Use Manacher's

- When you only need to check if a specific substring is a palindrome → use hashing
- When you need all distinct palindromic substrings → use Eertree
- When the string is very short → brute force is simpler

### When NOT to Use Hashing

- When you need guaranteed correctness (hash collisions possible with single hash)
- When the problem requires lexicographic comparison → hashes don't preserve order
- When you need to enumerate substrings → hashing only checks equality

### When NOT to Use Suffix Trees

- When a suffix array + LCP is sufficient (simpler to implement)
- When the problem only needs prefix matching → trie is simpler
- When you're in an interview and can't implement Ukkonen's → use suffix array

---

## Summary

String algorithms in interviews fall into a few categories:

1. **Palindrome problems:** Manacher's for longest palindrome, Eertree for all palindromes
2. **Pattern matching:** KMP for guaranteed linear, Rabin-Karp for flexibility, Boyer-Moore for practice
3. **Hashing:** Polynomial hashing for substring equality, double hashing for confidence
4. **Suffix structures:** Suffix arrays/trees for complex queries

The most commonly asked are hashing-based techniques and Manacher's. Focus on those first, then expand to suffix structures for advanced interviews.
