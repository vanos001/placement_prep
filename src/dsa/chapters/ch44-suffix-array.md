# Chapter 44: Suffix Array

## 44.1 What Is a Suffix Array

A **suffix array** is a sorted array of all suffixes of a string. Given a string `S` of length `n`, the suffix array `SA` is an array of integers `[0, 1, 2, ..., n-1]` such that `S[SA[0]..n-1] ≤ S[SA[1]..n-1] ≤ ... ≤ S[SA[n-1]..n-1]` lexicographically.

### Example

For the string `S = "banana"` (length 6), the suffixes are:

| Index | Suffix    |
|-------|-----------|
| 0     | banana    |
| 1     | anana     |
| 2     | nana      |
| 3     | ana       |
| 4     | na        |
| 5     | a         |

Sorting these suffixes lexicographically:

| Rank | Index | Suffix |
|------|-------|--------|
| 0    | 5     | a      |
| 1    | 3     | ana    |
| 2    | 1     | anana  |
| 3    | 0     | banana |
| 4    | 4     | na     |
| 5    | 2     | nana   |

So the suffix array is `SA = [5, 3, 1, 0, 4, 2]`.

### Suffix Array vs Suffix Tree

| Property            | Suffix Array          | Suffix Tree           |
|---------------------|-----------------------|-----------------------|
| Space               | O(n) integers         | O(n) nodes/edges      |
| Construction        | O(n log²n) or O(n)    | O(n) (Ukkonen)        |
| LCP queries         | O(1) with RMQ         | O(1) inherent         |
| Implementation      | Simpler               | Complex               |
| Cache performance   | Excellent (array)     | Poor (pointer-heavy)  |
| Pattern search      | O(m log n)            | O(m)                  |

The suffix array is often preferred in practice because:
1. **Simpler to implement** — no complex tree structures.
2. **Better cache locality** — contiguous array vs pointer chasing.
3. **Lower constant factors** — despite asymptotically similar or worse construction time.

### Why Suffix Arrays Matter

Suffix arrays are the backbone of many string-processing tasks:
- **Pattern matching**: Find all occurrences of a pattern in O(m log n).
- **Longest repeated substring**: Find the longest substring that appears at least twice.
- **Longest common substring**: Find the longest substring common to two or more strings.
- **Bioinformatics**: Genome assembly, sequence alignment.
- **Data compression**: Burrows-Wheeler Transform (BWT) is derived from suffix arrays.

---

## 44.2 Construction: O(n log²n) Sorting by 2^k Prefixes

### The Key Idea

The naive approach — sorting all suffixes directly — takes O(n² log n) because comparing two suffixes takes O(n) and there are O(n log n) comparisons. The trick is to sort suffixes by their **2^k-character prefixes** incrementally.

At step `k`, we have suffixes sorted by their first `2^k` characters. The rank of suffix `i` at step `k` is `rank[k][i]`. To sort by `2^(k+1)` characters, we compare pairs `(rank[k][i], rank[k][i + 2^k])` — this represents the first half and second half of the `2^(k+1)`-character prefix.

Since these pairs are integers, we can sort by them in O(n log n) using any comparison sort, or in O(n) using radix sort. With `log n` rounds, the total is O(n log²n).

### Complete Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

// Build suffix array in O(n log^2 n)
// s: input string (must be null-terminated or use length)
// Returns: suffix array (vector of indices)
vector<int> buildSuffixArray(const string& s) {
    int n = (int)s.size();
    if (n == 0) return {};

    // sa[i] = index of i-th smallest suffix
    // rank[i] = rank of suffix starting at i
    vector<int> sa(n), rank_(n), tmp(n);

    // Initialize: sort by single character
    for (int i = 0; i < n; i++) {
        sa[i] = i;
        rank_[i] = s[i]; // ASCII value as initial rank
    }

    // Lambda to compare suffixes by (rank[i], rank[i + k])
    int k = 1;
    auto cmp = [&](int a, int b) -> bool {
        if (rank_[a] != rank_[b]) return rank_[a] < rank_[b];
        int ra = (a + k < n) ? rank_[a + k] : -1;
        int rb = (b + k < n) ? rank_[b + k] : -1;
        return ra < rb;
    };

    // Sort by 2^k prefixes for k = 1, 2, 4, ..., until 2^k >= n
    for (k = 1; k < n; k *= 2) {
        sort(sa.begin(), sa.end(), cmp);

        // Compute new ranks
        tmp[sa[0]] = 0;
        for (int i = 1; i < n; i++) {
            tmp[sa[i]] = tmp[sa[i - 1]] + (cmp(sa[i - 1], sa[i]) ? 1 : 0);
        }
        rank_ = tmp;

        // Early termination: all ranks are distinct
        if (rank_[sa[n - 1]] == n - 1) break;
    }

    return sa;
}

// Kasai's algorithm to build LCP array in O(n)
// s: input string, sa: suffix array
// Returns: lcp array where lcp[i] = LCP(sa[i], sa[i-1]), lcp[0] = 0
vector<int> buildLCPArray(const string& s, const vector<int>& sa) {
    int n = (int)s.size();
    vector<int> rank_(n), lcp(n);

    // Compute inverse suffix array (rank)
    for (int i = 0; i < n; i++) rank_[sa[i]] = i;

    int h = 0; // current LCP length
    for (int i = 0; i < n; i++) {
        if (rank_[i] == 0) {
            lcp[0] = 0;
            continue;
        }
        int j = sa[rank_[i] - 1]; // previous suffix in sorted order
        // Compare s[i..] and s[j..]
        while (i + h < n && j + h < n && s[i + h] == s[j + h]) h++;
        lcp[rank_[i]] = h;
        // Key insight: h decreases by at most 1 per iteration
        if (h > 0) h--;
    }

    return lcp;
}

int main() {
    string s = "banana";

    vector<int> sa = buildSuffixArray(s);
    vector<int> lcp = buildLCPArray(s, sa);

    cout << "String: " << s << "\n\n";
    cout << "Suffix Array:\n";
    for (int i = 0; i < (int)sa.size(); i++) {
        cout << "  SA[" << i << "] = " << sa[i]
             << "  ->  \"" << s.substr(sa[i]) << "\"\n";
    }

    cout << "\nLCP Array:\n";
    for (int i = 0; i < (int)lcp.size(); i++) {
        cout << "  LCP[" << i << "] = " << lcp[i];
        if (i > 0) {
            cout << "  (LCP of \"" << s.substr(sa[i]) << "\" and \""
                 << s.substr(sa[i - 1]) << "\")";
        }
        cout << "\n";
    }

    return 0;
}
```

### Dry Run: Building SA for "banana"

**Initialization**: `sa = [0,1,2,3,4,5]`, `rank = [98,97,110,97,110,97]` (ASCII of b,a,n,a,n,a)

**Round k=1**: Sort by `(rank[i], rank[i+1])`:
- i=0: (98, 97)
- i=1: (97, 110)
- i=2: (110, 97)
- i=3: (97, 110)
- i=4: (110, 97)
- i=5: (97, -1)

Sorted: `[5, 3, 1, 0, 4, 2]` → new ranks: `[3, 2, 5, 1, 4, 0]`

**Round k=2**: Sort by `(rank[i], rank[i+2])`:
- i=5: (0, 2) → a + na
- i=3: (1, 4) → an + na
- i=1: (2, 5) → an + ana
- i=0: (3, 0) → ba + na
- i=4: (4, -1) → na
- i=2: (5, 1) → na + na

Sorted: `[5, 3, 1, 0, 4, 2]` → ranks unchanged → **terminate early**.

### Complexity Analysis

| Metric       | Complexity      |
|--------------|-----------------|
| Time         | O(n log²n)     |
| Space        | O(n)           |
| Rounds       | O(log n)       |
| Each round   | O(n log n) sort |

**Note**: Using radix sort instead of `std::sort` reduces this to O(n log n).

### Construction Algorithm Comparison

| Algorithm | Time Complexity | Space | Notes |
|-----------|----------------|-------|-------|
| **Doubling + std::sort** | \\(O(n \log^2 n)\\) | \\(O(n)\\) | Simplest to implement; good for interviews |
| **Doubling + Radix Sort** | \\(O(n \log n)\\) | \\(O(n)\\) | Two-pass radix sort per round; practical speedup |
| **SA-IS (Induced Sorting)** | \\(O(n)\\) | \\(O(n)\\) | Optimal; complex implementation; used in production |
| **Prefix Doubling + Counting Sort** | \\(O(n \log n)\\) | \\(O(n + \sigma)\\) | Radix sort variant using counting sort per character |

**Recommendation**: Use the doubling + `std::sort` approach for interviews and most competitive programming. Use SA-IS when performance is critical (e.g., genome assembly on large inputs).

### Python — Suffix Array Construction + LCP

```python
def build_suffix_array(s):
    """Build suffix array in O(n log^2 n)."""
    n = len(s)
    if n == 0:
        return []

    sa = list(range(n))
    rank_ = [ord(c) for c in s]
    tmp = [0] * n
    k = 1

    while k < n:
        sa.sort(key=lambda a: (rank_[a],
                               rank_[a + k] if a + k < n else -1))

        tmp[sa[0]] = 0
        for i in range(1, n):
            prev = (rank_[sa[i - 1]],
                    rank_[sa[i - 1] + k] if sa[i - 1] + k < n else -1)
            curr = (rank_[sa[i]],
                    rank_[sa[i] + k] if sa[i] + k < n else -1)
            tmp[sa[i]] = tmp[sa[i - 1]] + (1 if prev < curr else 0)
        rank_ = tmp[:]

        if rank_[sa[-1]] == n - 1:
            break
        k *= 2

    return sa


def build_lcp_array(s, sa):
    """Build LCP array using Kasai's algorithm in O(n)."""
    n = len(s)
    rank_ = [0] * n
    for i in range(n):
        rank_[sa[i]] = i

    lcp = [0] * n
    h = 0
    for i in range(n):
        if rank_[i] == 0:
            continue
        j = sa[rank_[i] - 1]
        while i + h < n and j + h < n and s[i + h] == s[j + h]:
            h += 1
        lcp[rank_[i]] = h
        if h > 0:
            h -= 1
    return lcp


if __name__ == "__main__":
    s = "banana"
    sa = build_suffix_array(s)
    lcp = build_lcp_array(s, sa)

    print(f"String: {s}\n")
    print("Suffix Array:")
    for i in range(len(sa)):
        print(f"  SA[{i}] = {sa[i]}  ->  \"{s[sa[i]:]}\"")
    print("\nLCP Array:")
    for i in range(len(lcp)):
        extra = ""
        if i > 0:
            extra = f"  (LCP of \"{s[sa[i]:]}\" and \"{s[sa[i-1]:]}\")"
        print(f"  LCP[{i}] = {lcp[i]}{extra}")
```

### Java — Suffix Array Construction + LCP

```java
import java.util.*;

public class SuffixArray {
    public static int[] buildSuffixArray(String s) {
        int n = s.length();
        if (n == 0) return new int[0];

        int[] sa = new int[n];
        int[] rank_ = new int[n];
        int[] tmp = new int[n];

        for (int i = 0; i < n; i++) {
            sa[i] = i;
            rank_[i] = s.charAt(i);
        }

        for (int k = 1; k < n; k *= 2) {
            final int[] r = rank_;
            final int N = n;
            final int K = k;
            Integer[] boxed = new Integer[n];
            for (int i = 0; i < n; i++) boxed[i] = sa[i];
            Arrays.sort(boxed, (a, b) -> {
                if (r[a] != r[b]) return r[a] - r[b];
                int ra = (a + K < N) ? r[a + K] : -1;
                int rb = (b + K < N) ? r[b + K] : -1;
                return ra - rb;
            });
            for (int i = 0; i < n; i++) sa[i] = boxed[i];

            tmp[sa[0]] = 0;
            for (int i = 1; i < n; i++) {
                int prevA = sa[i - 1], prevB = sa[i];
                boolean less = false;
                if (r[prevA] != r[prevB]) less = r[prevA] < r[prevB];
                else {
                    int ra = (prevA + k < n) ? r[prevA + k] : -1;
                    int rb = (prevB + k < n) ? r[prevB + k] : -1;
                    less = ra < rb;
                }
                tmp[sa[i]] = tmp[sa[i - 1]] + (less ? 1 : 0);
            }
            System.arraycopy(tmp, 0, rank_, 0, n);
            if (rank_[sa[n - 1]] == n - 1) break;
        }
        return sa;
    }

    public static int[] buildLCPArray(String s, int[] sa) {
        int n = s.length();
        int[] rank_ = new int[n];
        for (int i = 0; i < n; i++) rank_[sa[i]] = i;

        int[] lcp = new int[n];
        int h = 0;
        for (int i = 0; i < n; i++) {
            if (rank_[i] == 0) continue;
            int j = sa[rank_[i] - 1];
            while (i + h < n && j + h < n && s.charAt(i + h) == s.charAt(j + h)) h++;
            lcp[rank_[i]] = h;
            if (h > 0) h--;
        }
        return lcp;
    }

    public static void main(String[] args) {
        String s = "banana";
        int[] sa = buildSuffixArray(s);
        int[] lcp = buildLCPArray(s, sa);

        System.out.println("String: " + s + "\n");
        System.out.println("Suffix Array:");
        for (int i = 0; i < sa.length; i++) {
            System.out.printf("  SA[%d] = %d  ->  \"%s\"%n", i, sa[i], s.substring(sa[i]));
        }
        System.out.println("\nLCP Array:");
        for (int i = 0; i < lcp.length; i++) {
            String extra = "";
            if (i > 0) {
                extra = String.format("  (LCP of \"%s\" and \"%s\")",
                    s.substring(sa[i]), s.substring(sa[i - 1]));
            }
            System.out.printf("  LCP[%d] = %d%s%n", i, lcp[i], extra);
        }
    }
}
```

---

## 44.3 LCP Array: Kasai's Algorithm

The **LCP (Longest Common Prefix) array** stores, for each pair of adjacent suffixes in the sorted order, the length of their longest common prefix.

For suffix array `SA`, `LCP[i] = LCP(S[SA[i]..], S[SA[i-1]..])` for `i ≥ 1`, and `LCP[0] = 0`.

### Why Kasai's Algorithm Is O(n)

The naive approach compares each adjacent pair independently, taking O(n) per pair → O(n²) total.

Kasai's key insight: **the LCP value decreases by at most 1 per step**. If we process suffixes in the original order (not sorted order) and maintain a running `h`, we get:

```
for i = 0 to n-1:
    j = SA[rank[i] - 1]  // previous suffix in sorted order
    while s[i+h] == s[j+h]: h++
    LCP[rank[i]] = h
    if h > 0: h--
```

Since `h` increases at most `n` times total (each character compared at most once during increments) and decreases at most `n` times, the total work is O(n).

### Dry Run: LCP for "banana"

SA = [5, 3, 1, 0, 4, 2], rank = [3, 2, 5, 1, 4, 0]

The algorithm processes suffixes in **original index order** (i = 0, 1, 2, ..., 5), not sorted order. We maintain a running `h` that decreases by at most 1 per step.

| i | rank[i] | j = SA[rank[i]-1] | Suffixes compared | h before | h after while | h after -- | LCP[rank[i]] |
|---|---------|-------------------|-------------------|----------|---------------|------------|---------------|
| 0 | 3       | SA[2] = 1         | "banana" vs "anana" | 0 | 0 | 0 | LCP[3] = 0 |
| 1 | 2       | SA[1] = 3         | "anana" vs "ana"   | 0 | 3 | 2 | LCP[2] = 3 |
| 2 | 5       | SA[4] = 4         | "nana" vs "na"     | 2 | 2 | 1 | LCP[5] = 2 |
| 3 | 1       | SA[0] = 5         | "ana" vs "a"       | 1 | 1 | 0 | LCP[1] = 1 |
| 4 | 4       | SA[3] = 0         | "na" vs "banana"   | 0 | 0 | 0 | LCP[4] = 0 |
| 5 | 0       | (skip)            | —                  | 0 | — | — | LCP[0] = 0 |

**Step-by-step**:
- **i=0**: s[0]='b' vs s[1]='a' → no match. h stays 0. LCP[3]=0.
- **i=1**: s[1]='a'=s[3]='a', s[2]='n'=s[4]='n', s[3]='a'=s[5]='a', s[4]→out of bounds. h→3. LCP[2]=3.
- **i=2**: h starts at 2 (carried). s[2+2]=s[4]='n', s[4+2]=s[6]→out of bounds. Loop body never runs. h stays 2. LCP[5]=2.
- **i=3**: h starts at 1. s[3+1]=s[4]='n', s[5+1]=s[6]→out of bounds. Loop body never runs. h stays 1. LCP[1]=1.
- **i=4**: h starts at 0. s[4]='n' vs s[0]='b' → no match. h stays 0. LCP[4]=0.

**Result**: LCP = [0, 1, 3, 0, 0, 2]

**Verification**:
- LCP[1] = LCP("ana", "a") = 1 ✓ (share "a")
- LCP[2] = LCP("anana", "ana") = 3 ✓ (share "ana")
- LCP[3] = LCP("banana", "anana") = 0 ✓ (no common prefix)
- LCP[4] = LCP("na", "banana") = 0 ✓ (no common prefix)
- LCP[5] = LCP("nana", "na") = 2 ✓ (share "na")

**Key insight**: At i=2, h=2 from the previous step, but the while loop doesn't execute because i+h=4 and j+h=6 (out of bounds). This is the "free" decrease — we get LCP[5]=2 without any character comparisons at this step. This is why the algorithm is O(n): the total number of successful character comparisons (h increments) is at most n, and h decrements are also bounded by n.

### Applications of LCP Array

1. **Longest Repeated Substring**: `max(LCP)` — the maximum value in the LCP array.
2. **Number of Distinct Substrings**: `n*(n+1)/2 - sum(LCP)`.
3. **Pattern Matching**: Binary search on SA + LCP for faster search.

---

## 44.4 Applications

### Application 1: Longest Repeated Substring

Find the longest substring that appears at least twice in the string.

**Idea**: If two suffixes share a common prefix of length `L`, that prefix is a repeated substring. The longest such prefix is `max(LCP)`.

```cpp
#include <bits/stdc++.h>
using namespace std;

pair<int, int> longestRepeatedSubstring(const string& s) {
    int n = (int)s.size();
    if (n == 0) return {-1, 0};

    // Build suffix array (reuse function from above)
    vector<int> sa(n), rank_(n), tmp(n);
    iota(sa.begin(), sa.end(), 0);
    for (int i = 0; i < n; i++) rank_[i] = s[i];

    for (int k = 1; k < n; k *= 2) {
        auto cmp = [&](int a, int b) -> bool {
            if (rank_[a] != rank_[b]) return rank_[a] < rank_[b];
            int ra = (a + k < n) ? rank_[a + k] : -1;
            int rb = (b + k < n) ? rank_[b + k] : -1;
            return ra < rb;
        };
        sort(sa.begin(), sa.end(), cmp);
        tmp[sa[0]] = 0;
        for (int i = 1; i < n; i++)
            tmp[sa[i]] = tmp[sa[i - 1]] + (cmp(sa[i - 1], sa[i]) ? 1 : 0);
        rank_ = tmp;
        if (rank_[sa[n - 1]] == n - 1) break;
    }

    // Build LCP array
    vector<int> lcp(n, 0);
    int h = 0;
    for (int i = 0; i < n; i++) {
        if (rank_[i] == 0) continue;
        int j = sa[rank_[i] - 1];
        while (i + h < n && j + h < n && s[i + h] == s[j + h]) h++;
        lcp[rank_[i]] = h;
        if (h > 0) h--;
    }

    // Find max LCP
    int maxLen = 0, maxIdx = 0;
    for (int i = 1; i < n; i++) {
        if (lcp[i] > maxLen) {
            maxLen = lcp[i];
            maxIdx = sa[i];
        }
    }

    return {maxIdx, maxLen}; // starting position and length
}

int main() {
    string s = "abcabcabc";
    auto [pos, len] = longestRepeatedSubstring(s);
    if (len > 0) {
        cout << "Longest repeated substring: \"" << s.substr(pos, len)
             << "\" (length " << len << ", at position " << pos << ")\n";
    } else {
        cout << "No repeated substring found.\n";
    }
    return 0;
}
```

**Output**: `Longest repeated substring: "abcabc" (length 6, at position 0)`

**Complexity**: O(n log²n) for SA construction, O(n) for LCP. Total: O(n log²n).

### Application 2: Longest Common Substring of Two Strings

Given strings `A` and `B`, find the longest string that is a substring of both.

**Idea**: Concatenate `A + '#' + B` (where `#` is a sentinel not in either string). Build the suffix array and LCP array. The answer is the maximum `LCP[i]` where `SA[i]` and `SA[i-1]` come from different original strings.

```cpp
#include <bits/stdc++.h>
using namespace std;

string longestCommonSubstring(const string& a, const string& b) {
    string s = a + '\x01' + b; // sentinel character
    int n = (int)s.size();
    int splitPos = (int)a.size(); // boundary

    // Build suffix array
    vector<int> sa(n), rank_(n), tmp(n);
    iota(sa.begin(), sa.end(), 0);
    for (int i = 0; i < n; i++) rank_[i] = s[i];

    for (int k = 1; k < n; k *= 2) {
        auto cmp = [&](int x, int y) -> bool {
            if (rank_[x] != rank_[y]) return rank_[x] < rank_[y];
            int rx = (x + k < n) ? rank_[x + k] : -1;
            int ry = (y + k < n) ? rank_[y + k] : -1;
            return rx < ry;
        };
        sort(sa.begin(), sa.end(), cmp);
        tmp[sa[0]] = 0;
        for (int i = 1; i < n; i++)
            tmp[sa[i]] = tmp[sa[i - 1]] + (cmp(sa[i - 1], sa[i]) ? 1 : 0);
        rank_ = tmp;
        if (rank_[sa[n - 1]] == n - 1) break;
    }

    // Build LCP array
    vector<int> lcp(n, 0);
    int h = 0;
    for (int i = 0; i < n; i++) {
        if (rank_[i] == 0) continue;
        int j = sa[rank_[i] - 1];
        while (i + h < n && j + h < n && s[i + h] == s[j + h]) h++;
        lcp[rank_[i]] = h;
        if (h > 0) h--;
    }

    // Find max LCP where adjacent suffixes come from different strings
    int maxLen = 0, maxPos = 0;
    for (int i = 1; i < n; i++) {
        bool fromA = (sa[i] < splitPos);
        bool fromB_prev = (sa[i - 1] >= splitPos + 1);
        bool fromB = (sa[i] >= splitPos + 1);
        bool fromA_prev = (sa[i - 1] < splitPos);

        if ((fromA && fromB_prev) || (fromB && fromA_prev)) {
            if (lcp[i] > maxLen) {
                maxLen = lcp[i];
                maxPos = sa[i];
            }
        }
    }

    return s.substr(maxPos, maxLen);
}

int main() {
    string a = "abcdef";
    string b = "xbcdefg";
    string result = longestCommonSubstring(a, b);
    cout << "Longest common substring: \"" << result << "\"\n";
    // Output: "bcdef"
    return 0;
}
```

### Application 3: Number of Distinct Substrings

Every substring of `S` is a prefix of some suffix. The total number of substrings is `n*(n+1)/2`. We subtract the overlaps counted by the LCP array.

**Formula**: `distinct = n*(n+1)/2 - sum(LCP[i] for i = 0..n-1)`

```cpp
#include <bits/stdc++.h>
using namespace std;

long long countDistinctSubstrings(const string& s) {
    int n = (int)s.size();
    if (n == 0) return 0;

    vector<int> sa(n), rank_(n), tmp(n);
    iota(sa.begin(), sa.end(), 0);
    for (int i = 0; i < n; i++) rank_[i] = s[i];

    for (int k = 1; k < n; k *= 2) {
        auto cmp = [&](int a, int b) -> bool {
            if (rank_[a] != rank_[b]) return rank_[a] < rank_[b];
            int ra = (a + k < n) ? rank_[a + k] : -1;
            int rb = (b + k < n) ? rank_[b + k] : -1;
            return ra < rb;
        };
        sort(sa.begin(), sa.end(), cmp);
        tmp[sa[0]] = 0;
        for (int i = 1; i < n; i++)
            tmp[sa[i]] = tmp[sa[i - 1]] + (cmp(sa[i - 1], sa[i]) ? 1 : 0);
        rank_ = tmp;
        if (rank_[sa[n - 1]] == n - 1) break;
    }

    vector<int> lcp(n, 0);
    int h = 0;
    for (int i = 0; i < n; i++) {
        if (rank_[i] == 0) continue;
        int j = sa[rank_[i] - 1];
        while (i + h < n && j + h < n && s[i + h] == s[j + h]) h++;
        lcp[rank_[i]] = h;
        if (h > 0) h--;
    }

    long long total = (long long)n * (n + 1) / 2;
    long long lcpSum = 0;
    for (int x : lcp) lcpSum += x;

    return total - lcpSum;
}

int main() {
    string s = "banana";
    cout << "Distinct substrings of \"" << s << "\": "
         << countDistinctSubstrings(s) << "\n";
    // banana has 15 distinct substrings
    return 0;
}
```

---

## Interview Tips

1. **Know the O(n log²n) construction cold.** Interviewers rarely expect O(n) (SA-IS), but the doubling approach is a common interview question.

2. **Suffix array + LCP is a powerful combo.** Almost every application uses both. Practice building both together.

3. **Binary search on suffix array** is the standard pattern-matching approach: find the range of suffixes that start with pattern `P` using two binary searches (lower and upper bound).

4. **Sentinel character matters.** When concatenating strings, use a character that doesn't appear in either string. In competitive programming, `\x01` or `$` works.

5. **Explain the doubling idea clearly.** "At step k, suffixes are sorted by their first 2^k characters. To sort by 2^(k+1) characters, we compare pairs of ranks — each pair representing the first and second halves."

## Common Mistakes

1. **Off-by-one in LCP**: `LCP[0]` is always 0. The LCP at position `i` compares `SA[i]` and `SA[i-1]`, not `SA[i]` and `SA[i+1]`.

2. **Not handling sentinel in concatenation**: If strings contain all possible characters, you need a unique separator. Use indices instead of characters.

3. **Integer overflow**: `n*(n+1)/2` overflows `int` for `n > ~65000`. Use `long long`.

4. **Forgetting to decrement h in Kasai's**: The `h--` after setting `LCP[rank[i]]` is crucial for the O(n) bound.

5. **Comparing beyond string bounds**: Always check `i + h < n` before accessing `s[i + h]`.

## Practice Problems

1. **SPOJ SARRAY** — Build a suffix array. (Hint: Implement the O(n log²n) doubling approach.)

2. **SPOJ SUBST1** — Count distinct substrings. (Hint: Use `n*(n+1)/2 - sum(LCP)`.)

3. **SPOJ LCS** — Longest common substring of two strings. (Hint: Concatenate with sentinel, find max LCP from different strings.)

4. **Codeforces 128B** — Find the k-th smallest substring. (Hint: Enumerate suffixes and count how many substrings each contributes, subtracting LCP overlaps.)

5. **UVa 11107** — Life Forms. Find strings that appear in more than half the input strings. (Hint: Concatenate with unique sentinels, binary search on answer length, sliding window on LCP.)

---

## See Also

- [Chapter 45: Suffix Automaton](ch45-suffix-automaton.md) — A compressed automaton of all substrings; supports many of the same queries as suffix arrays but with different trade-offs.
- [Chapter 41: KMP](ch41-kmp.md) — Single-pattern matching; suffix arrays generalize to multiple patterns and substring queries.
- [Chapter 42: Z Algorithm](ch42-z-algorithm.md) — Used to compute LCP arrays efficiently; the Z-array is closely related to suffix array construction.
- [Chapter 46: Aho-Corasick](ch46-aho-corasick.md) — Multi-pattern matching on a fixed set of patterns; suffix arrays handle arbitrary substring queries.
- [Chapter 87: Suffix Tree](ch87-suffix-tree.md) — The suffix tree is the compressed trie of all suffixes; related to suffix arrays via the suffix array ↔ LCP ↔ suffix tree equivalence.
- [Chapter 119: Manacher's Algorithm](ch119-manacher.md) — Another string algorithm for finding all palindromic substrings; often combined with suffix structures.
