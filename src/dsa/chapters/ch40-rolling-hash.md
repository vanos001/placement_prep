# Chapter 40: Rolling Hash

Rolling hash is a technique that allows us to compute the hash of a substring in O(1) time after an O(n) preprocessing step. It is the foundation of the Rabin-Karp string matching algorithm and many other string-processing problems. This chapter covers polynomial rolling hash, string matching, collision handling, and practical applications.

---

## 40.1 Polynomial Rolling Hash

### Concept

A **polynomial rolling hash** treats a string as a number in base `b` (where `b` is typically a prime like 31 or 131). Each character is a digit, and the hash is the value of this number modulo a large prime `M`.

For a string `s` of length `n`:

```
H(s) = (s[0] · b^(n-1) + s[1] · b^(n-2) + ... + s[n-1] · b^0) mod M
```

### Why "Rolling"?

The key property: if we know the hash of `s[l..r]`, we can compute the hash of `s[l..r+1]` in O(1) by:
1. Subtracting the contribution of `s[l]` (which is now the leftmost character that should be removed).
2. Shifting the remaining hash left (multiply by `b`).
3. Adding the new character `s[r+1]`.

In practice, we usually compute prefix hashes and derive substring hashes from them.

### Prefix Hash Construction

```
H(i) = (H(i-1) · b + s[i]) mod M
```

The hash of substring `s[l..r]`:

```
hash(l, r) = (H(r) - H(l-1) · b^(r-l+1)) mod M
```

We need to handle negative results by adding `M`.

### Complete Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

class RollingHash {
    static constexpr long long BASE = 131;
    static constexpr long long MOD = 1e18 + 9;  // large prime

    vector<long long> hash;     // prefix hashes
    vector<long long> power;    // powers of BASE

public:
    RollingHash(const string& s) {
        int n = s.size();
        hash.resize(n + 1, 0);
        power.resize(n + 1, 1);

        for (int i = 0; i < n; i++) {
            hash[i + 1] = (hash[i] * BASE + s[i]) % MOD;
            power[i + 1] = power[i] * BASE % MOD;
        }
    }

    // Hash of s[l..r] (0-indexed, inclusive)
    long long getHash(int l, int r) const {
        long long result = (hash[r + 1] - hash[l] * power[r - l + 1] % MOD + MOD) % MOD;
        return result;
    }
};

int main() {
    string s = "abcabcabc";
    RollingHash rh(s);

    // Verify: hash of "abc" starting at index 0 should equal hash of "abc" at index 3
    cout << "hash(0,2) = " << rh.getHash(0, 2) << "\n";
    cout << "hash(3,5) = " << rh.getHash(3, 5) << "\n";
    cout << "hash(6,8) = " << rh.getHash(6, 8) << "\n";

    // hash(0,2) == hash(3,5) == hash(6,8) since all are "abc"

    return 0;
}
```

### Dry Run

For `s = "abc"` with `BASE = 131`:

| i | s[i] | ASCII | hash[i+1] = hash[i]*131 + s[i] |
|---|------|-------|--------------------------------|
| 0 | 'a'  | 97    | 0*131 + 97 = 97                |
| 1 | 'b'  | 98    | 97*131 + 98 = 12805            |
| 2 | 'c'  | 99    | 12805*131 + 99 = 1677554       |

Hash of `s[0..2]` = `hash[3] - hash[0] * power[3]` = `1677554 - 0 * power[3]` = `1677554`.

### Double Hashing for Safety

To reduce collision probability, use two different bases and moduli:

```cpp
class DoubleRollingHash {
    static constexpr long long BASE1 = 131, BASE2 = 137;
    static constexpr long long MOD1 = 1e18 + 9, MOD2 = 1e18 + 7;

    vector<long long> h1, h2, p1, p2;

public:
    DoubleRollingHash(const string& s) {
        int n = s.size();
        h1.resize(n + 1, 0); h2.resize(n + 1, 0);
        p1.resize(n + 1, 1); p2.resize(n + 1, 1);

        for (int i = 0; i < n; i++) {
            h1[i + 1] = (h1[i] * BASE1 + s[i]) % MOD1;
            h2[i + 1] = (h2[i] * BASE2 + s[i]) % MOD2;
            p1[i + 1] = p1[i] * BASE1 % MOD1;
            p2[i + 1] = p2[i] * BASE2 % MOD2;
        }
    }

    pair<long long, long long> getHash(int l, int r) const {
        long long hash1 = (h1[r+1] - h1[l] * p1[r-l+1] % MOD1 + MOD1) % MOD1;
        long long hash2 = (h2[r+1] - h2[l] * p2[r-l+1] % MOD2 + MOD2) % MOD2;
        return {hash1, hash2};
    }
};
```

---

## 40.2 String Matching with Hash

### Problem

Given a text `T` of length `n` and a pattern `P` of length `m`, find all occurrences of `P` in `T`.

### Approach

1. Compute the hash of the pattern `P`.
2. Compute the rolling hash of every substring of `T` of length `m`.
3. For each matching hash, verify character by character (to handle collisions).

### Complete Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

class StringMatcher {
    static constexpr long long BASE = 131;
    static constexpr long long MOD = 1e18 + 9;

public:
    static vector<int> findAll(const string& text, const string& pattern) {
        int n = text.size(), m = pattern.size();
        vector<int> occurrences;

        if (m > n) return occurrences;

        // Compute pattern hash
        long long patHash = 0;
        for (char c : pattern) {
            patHash = (patHash * BASE + c) % MOD;
        }

        // Compute power
        long long power = 1;
        for (int i = 0; i < m - 1; i++) {
            power = power * BASE % MOD;
        }

        // Rolling hash over text
        long long windowHash = 0;
        for (int i = 0; i < m; i++) {
            windowHash = (windowHash * BASE + text[i]) % MOD;
        }

        // Check first window
        if (windowHash == patHash && text.substr(0, m) == pattern) {
            occurrences.push_back(0);
        }

        // Slide the window
        for (int i = 1; i <= n - m; i++) {
            // Remove leftmost character, add new rightmost character
            windowHash = ((windowHash - text[i-1] * power % MOD + MOD) * BASE + text[i + m - 1]) % MOD;

            // Verify if hash matches (check character by character to avoid false positives)
            if (windowHash == patHash) {
                // Verify
                bool match = true;
                for (int j = 0; j < m; j++) {
                    if (text[i + j] != pattern[j]) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    occurrences.push_back(i);
                }
            }
        }

        return occurrences;
    }
};

int main() {
    string text = "ababcababcabc";
    string pattern = "abc";

    vector<int> matches = StringMatcher::findAll(text, pattern);
    cout << "Pattern found at indices: ";
    for (int idx : matches) cout << idx << " ";
    cout << "\n";
    // Output: 2 7 10

    return 0;
}
```

### Complexity

- **Average case:** O(n + m) — the hash comparison is O(1), and verification is rare.
- **Worst case:** O(nm) — if many hash collisions occur (extremely unlikely with good hash parameters).

---

## 40.3 Rabin-Karp Algorithm

The Rabin-Karp algorithm is essentially the string matching approach described above, formalized as a named algorithm.

### Key Idea

Instead of comparing patterns character by character (O(m) per position), compare hash values (O(1) per position). Only do a full comparison when hashes match.

### Algorithm

```
RABIN-KARP(T, P):
    n = |T|, m = |P|
    hP = hash(P)
    hT = hash(T[0..m-1])
    
    for i = 0 to n - m:
        if hT == hP:
            if T[i..i+m-1] == P:  // verify
                report match at i
        if i < n - m:
            hT = rolling_hash(T, hT, i, i+m)  // O(1) update
```

### Multi-Pattern Rabin-Karp

Rabin-Karp shines when searching for **multiple patterns** simultaneously. Store all pattern hashes in a set, and check each window hash against the set.

```cpp
#include <bits/stdc++.h>
using namespace std;

class MultiPatternRabinKarp {
    static constexpr long long BASE = 131;
    static constexpr long long MOD = 1e9 + 7;

public:
    static vector<pair<int, string>> findPatterns(
        const string& text,
        const vector<string>& patterns
    ) {
        vector<pair<int, string>> results;

        // Group patterns by length
        unordered_map<int, vector<pair<string, long long>>> byLen;
        for (const string& p : patterns) {
            long long h = 0;
            for (char c : p) h = (h * BASE + c) % MOD;
            byLen[p.size()].push_back({p, h});
        }

        // For each pattern length, do rolling hash
        for (auto& [m, pats] : byLen) {
            if (m > (int)text.size()) continue;

            unordered_map<long long, vector<string>> hashMap;
            for (auto& [p, h] : pats) {
                hashMap[h].push_back(p);
            }

            // Compute power
            long long power = 1;
            for (int i = 0; i < m - 1; i++) power = power * BASE % MOD;

            // Initial window hash
            long long windowHash = 0;
            for (int i = 0; i < m; i++) {
                windowHash = (windowHash * BASE + text[i]) % MOD;
            }

            // Check
            if (hashMap.count(windowHash)) {
                for (const string& p : hashMap[windowHash]) {
                    if (text.substr(0, m) == p) results.push_back({0, p});
                }
            }

            // Slide
            for (int i = 1; i <= (int)text.size() - m; i++) {
                windowHash = ((windowHash - text[i-1] * power % MOD + MOD) * BASE + text[i+m-1]) % MOD;

                if (hashMap.count(windowHash)) {
                    for (const string& p : hashMap[windowHash]) {
                        if (text.substr(i, m) == p) results.push_back({i, p});
                    }
                }
            }
        }

        return results;
    }
};

int main() {
    string text = "abracadabra";
    vector<string> patterns = {"ab", "bra", "cad", "dab"};

    auto results = MultiPatternRabinKarp::findPatterns(text, patterns);
    for (auto& [idx, pat] : results) {
        cout << "Pattern \"" << pat << "\" found at index " << idx << "\n";
    }
    // Output:
    // Pattern "ab" found at index 0
    // Pattern "bra" found at index 1
    // Pattern "ab" found at index 7
    // Pattern "dab" found at index 7
    // Pattern "cad" found at index 4

    return 0;
}
```

---

## 40.4 Hash Collisions

### The Problem

Two different strings can have the same hash value. This is called a **collision**. If we rely solely on hash comparison, we might report false matches.

### Probability of Collision

With a hash modulo `M ≈ 10^18` and random strings, the collision probability is approximately `1/M ≈ 10^-18`. For practical purposes, this is negligible, but in competitive programming or security-sensitive applications, we need to be more careful.

### Strategies to Handle Collisions

**1. Verification after hash match:** Always compare the actual strings when hashes match. This is the most common approach.

**2. Double hashing:** Use two independent hash functions with different bases and moduli. Two strings colliding on both hashes simultaneously has probability ≈ `1/(M1 * M2)`, which is astronomically small.

**3. Use a very large modulus:** Using `__int128` or modular arithmetic with multiple primes reduces collision probability.

```cpp
// Double hash comparison
bool areEqual(const DoubleRollingHash& rh1, int l1, int r1,
               const DoubleRollingHash& rh2, int l2, int r2) {
    return rh1.getHash(l1, r1) == rh2.getHash(l2, r2);
}
```

### When Collisions Matter

- **Competitive programming:** Double hashing is standard practice. Many problems are designed to fail with single hashing.
- **Production systems:** Always verify after hash match. Hash is a filter, not a guarantee.
- **Cryptographic applications:** Use SHA-256 or similar, not polynomial rolling hash.

---

## 40.5 Applications

### Application 1: Longest Common Substring

Find the longest common substring of two strings using binary search + rolling hash.

```cpp
#include <bits/stdc++.h>
using namespace std;

class LongestCommonSubstring {
    static constexpr long long BASE = 131;
    static constexpr long long MOD = 1e18 + 9;

public:
    static string solve(const string& s1, const string& s2) {
        int lo = 0, hi = min(s1.size(), s2.size());
        int bestLen = 0, bestPos = 0;

        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            auto [found, pos] = hasCommonSubstring(s1, s2, mid);
            if (found) {
                bestLen = mid;
                bestPos = pos;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }

        return s1.substr(bestPos, bestLen);
    }

private:
    static pair<bool, int> hasCommonSubstring(const string& s1, const string& s2, int len) {
        if (len == 0) return {true, 0};

        // Compute all hashes of length 'len' from s1
        unordered_set<long long> hashes;

        long long power = 1;
        for (int i = 0; i < len - 1; i++) power = power * BASE % MOD;

        long long h = 0;
        for (int i = 0; i < (int)s1.size(); i++) {
            h = (h * BASE + s1[i]) % MOD;
            if (i >= len) {
                h = (h - s1[i - len] * power % MOD + MOD) % MOD;
            }
            if (i >= len - 1) {
                hashes.insert(h);
            }
        }

        // Check s2's substrings
        h = 0;
        for (int i = 0; i < (int)s2.size(); i++) {
            h = (h * BASE + s2[i]) % MOD;
            if (i >= len) {
                h = (h - s2[i - len] * power % MOD + MOD) % MOD;
            }
            if (i >= len - 1 && hashes.count(h)) {
                return {true, i - len + 1};
            }
        }

        return {false, -1};
    }
};

int main() {
    cout << LongestCommonSubstring::solve("abcde", "abfce") << "\n";
    // Output: "ab" (or "bc" depending on hash — verify)

    cout << LongestCommonSubstring::solve("banana", "ananas") << "\n";
    // Output: "anana"

    return 0;
}
```

### Application 2: Repeated Substring Pattern

Check if a string can be constructed by repeating a substring (LeetCode 459).

```cpp
#include <bits/stdc++.h>
using namespace std;

bool repeatedSubstringPattern(string s) {
    int n = s.size();
    // Try all possible period lengths
    for (int len = 1; len <= n / 2; len++) {
        if (n % len != 0) continue;

        // Check if s is composed of s[0..len-1] repeated n/len times
        bool valid = true;
        for (int i = len; i < n; i++) {
            if (s[i] != s[i % len]) {
                valid = false;
                break;
            }
        }
        if (valid) return true;
    }
    return false;
}

int main() {
    cout << repeatedSubstringPattern("abab") << "\n";      // 1 (true)
    cout << repeatedSubstringPattern("aba") << "\n";       // 0 (false)
    cout << repeatedSubstringPattern("abcabcabcabc") << "\n"; // 1 (true)
    return 0;
}
```

### Application 3: Distinct Substrings Count

Count the number of distinct substrings of a string using rolling hash.

```cpp
#include <bits/stdc++.h>
using namespace std;

int countDistinctSubstrings(const string& s) {
    constexpr long long BASE = 131;
    constexpr long long MOD = 1e18 + 9;
    int n = s.size();

    unordered_set<long long> seen;

    for (int len = 1; len <= n; len++) {
        long long power = 1;
        for (int i = 0; i < len - 1; i++) power = power * BASE % MOD;

        long long h = 0;
        for (int i = 0; i < n; i++) {
            h = (h * BASE + s[i]) % MOD;
            if (i >= len) {
                h = (h - s[i - len] * power % MOD + MOD) % MOD;
            }
            if (i >= len - 1) {
                seen.insert(h);
            }
        }
    }

    return seen.size();
}

int main() {
    cout << countDistinctSubstrings("abc") << "\n";
    // Substrings: a, b, c, ab, bc, abc → 6

    cout << countDistinctSubstrings("aaa") << "\n";
    // Substrings: a, aa, aaa → 3

    return 0;
}
```

---

## 40.6 Interview Tips

1. **Rolling hash is a tool, not an algorithm:** It's used as a building block inside other algorithms (Rabin-Karp, suffix arrays, etc.).

2. **Always verify after hash match:** Never trust a hash alone. Collisions are rare but possible.

3. **Double hashing:** When a single hash might fail (competitive programming), use two hashes with different bases and moduli.

4. **Base and modulus choice:**
   - Base: a prime > alphabet size (e.g., 31 for lowercase, 131 for ASCII).
   - Modulus: a large prime (e.g., 10^9 + 7, 10^18 + 9).
   - Avoid powers of 2 as modulus.

5. **Binary search + hash:** Many problems (longest common substring, longest repeated substring) combine binary search on length with rolling hash for O(n log n) solutions.

6. **Modular arithmetic:** Be careful with negative values. Always add `MOD` before taking `% MOD`.

---

## 40.7 Common Mistakes

1. **Forgetting modular arithmetic:** Hash values can overflow. Always use `% MOD`.

2. **Negative mod results:** `(a - b) % MOD` can be negative in C++. Use `((a - b) % MOD + MOD) % MOD`.

3. **Wrong power computation:** The power `b^(r-l+1)` must match the substring length. Off-by-one errors here cause wrong hashes.

4. **Using a single hash in competitive programming:** Many problems are designed to cause collisions with a single hash. Use double hashing.

5. **Not handling edge cases:** Empty strings, single characters, pattern longer than text.

6. **Base too small:** If `BASE ≤ alphabet_size`, different characters may map to the same digit, causing unnecessary collisions.

---

## 40.8 Practice Problems

| # | Problem | Difficulty | Key Idea |
|---|---------|------------|----------|
| 1 | LeetCode 28 - Find the Index of the First Occurrence | Easy | Rabin-Karp |
| 2 | LeetCode 459 - Repeated Substring Pattern | Easy | Rolling hash or KMP |
| 3 | LeetCode 718 - Maximum Length of Repeated Subarray | Medium | Binary search + hash |
| 4 | LeetCode 1044 - Longest Duplicate Substring | Hard | Binary search + rolling hash |
| 5 | LeetCode 187 - Repeated DNA Sequences | Medium | Fixed-length rolling hash |
| 6 | LeetCode 1316 - Distinct Echo Substrings | Hard | Rolling hash |
| 7 | LeetCode 2156 - Find Substring With Given Hash Value | Medium | Backward rolling hash |
| 8 | SPOJ - NHAY (A Needle in the Haystack) | Medium | Rabin-Karp |
| 9 | LeetCode 1392 - Longest Happy Prefix | Hard | Rolling hash or KMP |
| 10 | LeetCode 3213 - Construct String with Minimum Cost | Hard | Hash for substring matching |

---

## 40.9 Summary

| Concept | Time | Space |
|---------|------|-------|
| Build prefix hash | O(n) | O(n) |
| Substring hash query | O(1) | — |
| Rabin-Karp (average) | O(n + m) | O(1) |
| Rabin-Karp (worst) | O(nm) | O(1) |
| Double hashing | O(1) per query | O(n) |

Rolling hash is a fundamental string processing technique. Its power lies in enabling O(1) substring hash comparisons, which when combined with binary search or sliding windows, solves many string problems efficiently. Always pair it with verification or double hashing to handle collisions.
