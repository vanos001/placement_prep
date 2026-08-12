# Chapter 120: Burrows-Wheeler Transform and FM-Index

## Prerequisites
- Suffix arrays (Chapter 158)
- String basics (Chapters 1-5)
- Binary search (Chapter 38)
- Run-length encoding and compression (Chapter 119)

## Interview Frequency: ★

The Burrows-Wheeler Transform (BWT) rearranges a string to group similar characters together, enabling both compression and fast pattern matching. Combined with the FM-Index, it enables O(m) pattern matching on compressed text using only O(n) bits of space. This is the technology behind **bzip2** compression and genome aligners like **BWA** and **Bowtie**.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| BWT construction | ★ | Medium | Suffix array based |
| Inverse BWT | ★ | Medium | LF-mapping |
| FM-Index search | ★ | Hard | Backward search |
| LF-mapping | ★ | Medium | Core navigation |
| Wavelet tree | ★ | Hard | Rank queries |

---

## 120.1 Burrows-Wheeler Transform

### Definition

The Burrows-Wheeler Transform of a string S is formed by:
1. Appending a special end-of-string character `$` (lexicographically smallest)
2. Generating all cyclic rotations of S$
3. Sorting the rotations lexicographically
4. Taking the last column of the sorted matrix

### Motivation

Why rearrange a string? Because the BWT groups identical characters together. Consider the string `banana$`. After BWT, we get `annb$aa` — notice how the `a`'s are clustered. This clustering makes run-length encoding extremely effective, which is why bzip2 uses BWT + RLE.

### Intuition

Think of the BWT as reading the characters that *precede* each suffix in sorted order. Since suffixes that start with similar prefixes are adjacent, the characters before them tend to be similar too. It's like sorting a deck of cards by suit — cards of the same suit end up together, and the cards adjacent to them in the original deck tend to be similar.

### Formal Explanation

Given string S of length n with S[n] = `$`:

1. Construct the suffix array SA of S: SA[i] is the starting position of the i-th smallest suffix
2. BWT[i] = S[SA[i] - 1] (with wraparound: if SA[i] = 0, BWT[i] = S[n-1] = `$`)

**Theorem**: The BWT is a bijection — every string has a unique BWT, and the original can be reconstructed from the BWT.

### Step-by-Step Walkthrough

**Input**: `banana$`

**Step 1**: All cyclic rotations

| Index | Rotation |
|---|---|
| 0 | `banana$` |
| 1 | `ananab$` |
| 2 | `nanaba$` |
| 3 | `anaban$` |
| 4 | `nabana$` |
| 5 | `abanan$` |
| 6 | `$banan` |

**Step 2**: Sort lexicographically

| Rank | Rotation | Last Char |
|---|---|---|
| 0 | `$banan` | `n` |
| 1 | `abanan` | `n` |
| 2 | `anaban` | `n` |
| 3 | `ananab` | `b` |
| 4 | `banana` | `$` |
| 5 | `nabana` | `a` |
| 6 | `nanaba` | `a` |

**Step 3**: BWT = last column = `nnb$aa` + the `$` character

Wait — let me recompute carefully. The BWT is the last column of the sorted rotation matrix:

Sorted rotations:
```
$banan  → last: n
abanan  → last: n
anaban  → last: n
ananab  → last: b
banana  → last: a
nabana  → last: a
nanaba  → last: a
```

BWT = `nnnbaaa`

Hmm, let me verify with suffix arrays instead. For `banana$`:

Suffixes sorted:
```
$        → SA[0]=6, BWT[0]=S[5]=a
a$       → SA[1]=5, BWT[1]=S[4]=n
ana$     → SA[2]=3, BWT[2]=S[2]=n
anana$   → SA[3]=1, BWT[3]=S[0]=b
banana$  → SA[4]=0, BWT[4]=S[6]=$
na$      → SA[5]=4, BWT[5]=S[3]=a
nana$    → SA[6]=2, BWT[6]=S[1]=a
```

BWT = `annb$aa`

### Dry Run Verification

| i | SA[i] | S[SA[i]] suffix | BWT[i] = S[SA[i]-1] |
|---|---|---|---|
| 0 | 6 | `$` | S[5] = `a` |
| 1 | 5 | `a$` | S[4] = `n` |
| 2 | 3 | `ana$` | S[2] = `n` |
| 3 | 1 | `anana$` | S[0] = `b` |
| 4 | 0 | `banana$` | S[6] = `$` |
| 5 | 4 | `na$` | S[3] = `a` |
| 6 | 2 | `nana$` | S[1] = `a` |

**BWT = `annb$aa`** ✓

### Complexity Analysis

| Operation | Naive | SA-based |
|---|---|---|
| BWT construction | O(n² log n) | O(n) |
| Space | O(n²) | O(n) |

---

## 120.2 Inverse BWT

### Definition

Given the BWT string, reconstruct the original string.

### The LF-Mapping Property

**Key insight**: The i-th occurrence of character c in the last column (BWT) corresponds to the i-th occurrence of c in the first column (sorted characters).

This is because:
- First column F[i] = sorted version of BWT
- The i-th row of the rotation matrix starts with F[i] and ends with BWT[i]
- The row starting with the k-th occurrence of character c in F is the same row as the k-th occurrence of c in BWT

**LF-mapping**: LF(i) = C[BWT[i]] + rank(BWT, i)

Where:
- C[c] = number of characters in BWT that are lexicographically smaller than c
- rank(BWT, i) = number of occurrences of BWT[i] in BWT[0..i]

### Step-by-Step Inverse BWT Walkthrough

**Input BWT**: `annb$aa`

**Step 1**: Compute C[] array

| Character | Count | C[c] |
|---|---|---|
| `$` | 1 | 0 |
| `a` | 3 | 1 |
| `b` | 1 | 4 |
| `n` | 2 | 5 |

**Step 2**: Compute LF-mapping

| i | BWT[i] | rank(BWT[i], i) | LF(i) = C[BWT[i]] + rank |
|---|---|---|---|
| 0 | `a` | 0 | 1 + 0 = 1 |
| 1 | `n` | 0 | 5 + 0 = 5 |
| 2 | `n` | 1 | 5 + 1 = 6 |
| 3 | `b` | 0 | 4 + 0 = 4 |
| 4 | `$` | 0 | 0 + 0 = 0 |
| 5 | `a` | 1 | 1 + 1 = 2 |
| 6 | `a` | 2 | 1 + 2 = 3 |

**Step 3**: Reconstruct by following LF chain starting from row containing `$`

`$` is at position 4. Chain: 4 → 0 → 1 → 5 → 2 → 6 → 3 → (back to 4)

Reading BWT at each position: BWT[4]=`$`, BWT[0]=`a`, BWT[1]=`n`, BWT[5]=`a`, BWT[2]=`n`, BWT[6]=`a`, BWT[3]=`b`

Reversed: `banana$` → Remove `$` → `banana` ✓

---

## 120.3 FM-Index

### Definition

The FM-Index combines the BWT with auxiliary data structures to support:
- **count(c)**: Number of occurrences of character c before position i
- **backwardSearch(P)**: Find the range of suffixes starting with pattern P
- **locate(i)**: Find the original position of BWT[i]

### Motivation

The FM-Index enables searching for patterns in O(m) time (where m is the pattern length) using only the BWT string and some auxiliary tables. No need to store the full text — this is a *succinct* data structure.

### Intuition

Searching works backwards through the pattern. To find "ana" in "banana":
1. Start with all suffixes (range [0, n))
2. Find suffixes starting with 'a' → narrows range
3. Find suffixes starting with 'na' → narrows further
4. Find suffixes starting with 'ana' → final range = occurrences

The LF-mapping lets us "prepend" a character to all suffixes in the current range.

### Backward Search Algorithm

```
backwardSearch(P):
    c = P[m-1]  // Last character
    sp = C[c]   // First row starting with c
    ep = C[c+1] - 1  // Last row starting with c

    for i = m-2 down to 0:
        c = P[i]
        sp = C[c] + rank(c, sp - 1)  // +1 if sp > 0
        ep = C[c] + rank(c, ep) - 1
        if sp > ep: return empty  // Pattern not found

    return [sp, ep]  // Range of suffixes matching P
```

### Step-by-Step FM-Index Search

**Text**: `banana$`, BWT = `annb$aa`
**Pattern**: `ana`

**Preprocessing**:

| Character | C[c] | Occurrences in BWT |
|---|---|---|
| `$` | 0 | 1 |
| `a` | 1 | 3 |
| `b` | 4 | 1 |
| `n` | 5 | 2 |

**Rank table** (number of occurrences of each char up to position i):

| i | BWT[i] | rank_a(i) | rank_n(i) | rank_b(i) | rank_$(i) |
|---|---|---|---|---|---|
| 0 | `a` | 1 | 0 | 0 | 0 |
| 1 | `n` | 1 | 1 | 0 | 0 |
| 2 | `n` | 1 | 2 | 0 | 0 |
| 3 | `b` | 1 | 2 | 1 | 0 |
| 4 | `$` | 1 | 2 | 1 | 1 |
| 5 | `a` | 2 | 2 | 1 | 1 |
| 6 | `a` | 3 | 2 | 1 | 1 |

**Search for "ana"** (process right to left):

**Step 1**: Process 'a' (last character)
- sp = C['a'] = 1
- ep = C['a'] + rank_a(6) - 1 = 1 + 3 - 1 = 3
- Range: [1, 3] → suffixes `a$`, `ana$`, `anana$`

**Step 2**: Process 'n'
- sp = C['n'] + rank_n(0) = 5 + 0 = 5
- ep = C['n'] + rank_n(3) - 1 = 5 + 2 - 1 = 6
- Range: [5, 6] → suffixes `na$`, `nana$`

**Step 3**: Process 'a' (first character)
- sp = C['a'] + rank_a(4) = 1 + 1 = 2
- ep = C['a'] + rank_a(6) - 1 = 1 + 3 - 1 = 3
- Range: [2, 3] → suffixes `ana$`, `anana$`

**Result**: Pattern "ana" occurs at suffix array positions 2 and 3.
SA[2] = 3, SA[3] = 1 → positions 1 and 3 in the original string.

Verify: `banana` → `b[ana]na` (pos 1) and `ban[ana]` (pos 3) ✓

---

## 120.4 BWT Properties

| Property | Description | Application |
|---|---|---|
| Groups similar chars | Runs of identical characters | Compression |
| LF-mapping | Navigate between sorted/unsorted | Inverse BWT, search |
| Preserves information | Lossless transformation | Reconstruction |
| Suffix array link | BWT[i] = S[SA[i]-1] | Fast construction |
| Run-length friendly | Long runs compress well | bzip2 |

### Compression with BWT + RLE

After BWT, the string tends to have long runs of identical characters. Applying run-length encoding (RLE) after BWT often achieves much better compression than RLE alone.

```
Original:       banana
BWT:            annb$aa
RLE of BWT:     a1n2b1$1a2
```

For repetitive text (e.g., DNA sequences, versioned documents), the compression ratio improves dramatically.

---

## 120.5 Wavelet Trees

### Definition

A wavelet tree is a balanced binary tree over the alphabet that supports rank and select queries in O(log σ) time, where σ is the alphabet size.

### Motivation

The FM-Index needs fast `rank(c, i)` queries. For small alphabets (DNA: σ=4), precomputed tables work. For large alphabets (Unicode), wavelet trees provide a space-efficient alternative.

### How It Works

1. Build a balanced BST over the alphabet
2. Each node stores a bitvector indicating which children each character belongs to
3. rank queries traverse the tree, using bitvector rank at each level

### Complexity

| Operation | Time | Space |
|---|---|---|
| Build | O(n log σ) | O(n log σ) bits |
| rank(c, i) | O(log σ) | — |
| select(c, i) | O(log σ) | — |

---

## 120.6 Applications

| Application | Tool | Use Case |
|---|---|---|
| Genome alignment | BWA, Bowtie2 | Map short reads to reference genome |
| Compression | bzip2 | General-purpose compression |
| Full-text search | FM-Index | Search in large text corpora |
| Bioinformatics | SGA, RopeBWT2 | Assembly, variant calling |
| Version control | Delta encoding | Compress file diffs |

### Why Bioinformatics Loves BWT

A human genome is ~3 billion characters. Storing millions of sequencing reads and aligning them to a reference requires:
- **Space**: FM-Index uses ~1.5 bytes per character (with 2-bit encoding + SA samples)
- **Speed**: O(m) search per read, independent of genome size
- **No decompression needed**: Search directly in compressed representation

---

## 120.7 Code Example (C++)

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <map>

// BWT via suffix array
std::string bwt(const std::string& s) {
    int n = s.size();
    std::vector<int> sa(n);
    for (int i = 0; i < n; i++) sa[i] = i;

    std::sort(sa.begin(), sa.end(), [&](int a, int b) {
        for (int i = 0; i < n; i++) {
            char ca = s[(a + i) % n];
            char cb = s[(b + i) % n];
            if (ca != cb) return ca < cb;
        }
        return false;
    });

    std::string result;
    for (int i = 0; i < n; i++)
        result += s[(sa[i] + n - 1) % n];
    return result;
}

// Inverse BWT via LF-mapping
std::string inverseBwt(const std::string& bwtStr) {
    int n = bwtStr.size();

    // Compute C array
    std::map<char, int> count;
    for (char c : bwtStr) count[c]++;
    std::map<char, int> C;
    int total = 0;
    for (auto& [c, cnt] : count) {
        C[c] = total;
        total += cnt;
    }

    // Compute LF-mapping
    std::vector<int> lf(n);
    std::map<char, int> seen;
    for (int i = 0; i < n; i++) {
        lf[i] = C[bwtStr[i]] + seen[bwtStr[i]];
        seen[bwtStr[i]]++;
    }

    // Find row with '$'
    int row = 0;
    for (int i = 0; i < n; i++)
        if (bwtStr[i] == '$') { row = i; break; }

    // Follow LF chain
    std::string result(n, ' ');
    int pos = row;
    for (int i = n - 1; i >= 0; i--) {
        result[i] = bwtStr[pos];
        pos = lf[pos];
    }
    return result;
}

// FM-Index backward search
class FMIndex {
    std::string bwtStr;
    std::map<char, int> C;
    std::vector<std::vector<int>> rankTable; // rankTable[c][i] = count of c in BWT[0..i]

public:
    FMIndex(const std::string& s) {
        bwtStr = bwt(s);
        int n = bwtStr.size();

        // Build C array
        std::map<char, int> count;
        for (char c : bwtStr) count[c]++;
        int total = 0;
        for (auto& [c, cnt] : count) {
            C[c] = total;
            total += cnt;
        }

        // Build rank table
        std::string alphabet;
        for (auto& [c, _] : C) alphabet += c;
        rankTable.resize(256, std::vector<int>(n, 0));
        for (char c : alphabet) {
            rankTable[c][0] = (bwtStr[0] == c) ? 1 : 0;
            for (int i = 1; i < n; i++)
                rankTable[c][i] = rankTable[c][i-1] + ((bwtStr[i] == c) ? 1 : 0);
        }
    }

    int rank(char c, int i) {
        if (i < 0) return 0;
        return rankTable[c][i];
    }

    // Returns [sp, ep] range of suffixes starting with pattern
    std::pair<int,int> backwardSearch(const std::string& pattern) {
        int m = pattern.size();
        char c = pattern[m - 1];
        int sp = C[c];
        int ep = C[c] + rank(c, bwtStr.size() - 1) - 1;

        for (int i = m - 2; i >= 0 && sp <= ep; i--) {
            c = pattern[i];
            sp = C[c] + rank(c, sp - 1);
            ep = C[c] + rank(c, ep) - 1;
        }

        if (sp > ep) return {-1, -1};
        return {sp, ep};
    }
};

int main() {
    std::string s = "banana$";
    std::string transformed = bwt(s);
    std::cout << "Original: \"" << s << "\"\n";
    std::cout << "BWT:      \"" << transformed << "\"\n";

    std::string recovered = inverseBwt(transformed);
    std::cout << "Recovered: \"" << recovered << "\"\n";

    // FM-Index search
    FMIndex fmi(s);
    auto [sp, ep] = fmi.backwardSearch("ana");
    std::cout << "\nSearch for \"ana\": range [" << sp << ", " << ep << "]\n";
    std::cout << "Found " << (ep - sp + 1) << " occurrences\n";

    auto [sp2, ep2] = fmi.backwardSearch("xyz");
    if (sp2 == -1) std::cout << "Search for \"xyz\": not found\n";

    return 0;
}
```

---

## 120.8 Code Example (Python)

```python
def bwt(s):
    """Compute BWT using suffix array approach."""
    n = len(s)
    sa = sorted(range(n), key=lambda i: s[i:] + s[:i])
    return ''.join(s[(sa[i] - 1) % n] for i in range(n))


def inverse_bwt(bwt_str):
    """Reconstruct original string from BWT using LF-mapping."""
    n = len(bwt_str)

    # Compute C array
    count = {}
    for c in bwt_str:
        count[c] = count.get(c, 0) + 1
    C = {}
    total = 0
    for c in sorted(count):
        C[c] = total
        total += count[c]

    # Compute LF-mapping
    seen = {}
    lf = [0] * n
    for i, c in enumerate(bwt_str):
        lf[i] = C[c] + seen.get(c, 0)
        seen[c] = seen.get(c, 0) + 1

    # Find row with '$' and follow chain
    row = bwt_str.index('$')
    result = []
    pos = row
    for _ in range(n):
        result.append(bwt_str[pos])
        pos = lf[pos]

    return ''.join(reversed(result))


class FMIndex:
    """FM-Index for pattern matching on BWT."""

    def __init__(self, s):
        self.bwt_str = bwt(s)
        n = len(self.bwt_str)

        # Build C array
        count = {}
        for c in self.bwt_str:
            count[c] = count.get(c, 0) + 1
        self.C = {}
        total = 0
        for c in sorted(count):
            self.C[c] = total
            total += count[c]

        # Build rank table
        self.rank_table = {}
        for c in self.C:
            rt = [0] * n
            rt[0] = 1 if self.bwt_str[0] == c else 0
            for i in range(1, n):
                rt[i] = rt[i-1] + (1 if self.bwt_str[i] == c else 0)
            self.rank_table[c] = rt

    def rank(self, c, i):
        if i < 0:
            return 0
        return self.rank_table[c][i]

    def backward_search(self, pattern):
        """Search for pattern. Returns (sp, ep) range or (-1, -1) if not found."""
        m = len(pattern)
        c = pattern[-1]
        sp = self.C[c]
        ep = self.C[c] + self.rank(c, len(self.bwt_str) - 1) - 1

        for i in range(m - 2, -1, -1):
            if sp > ep:
                return (-1, -1)
            c = pattern[i]
            sp = self.C[c] + self.rank(c, sp - 1)
            ep = self.C[c] + self.rank(c, ep) - 1

        if sp > ep:
            return (-1, -1)
        return (sp, ep)


# Demo
s = "banana$"
transformed = bwt(s)
print(f"Original:  '{s}'")
print(f"BWT:       '{transformed}'")
print(f"Recovered: '{inverse_bwt(transformed)}'")

# FM-Index search
fmi = FMIndex(s)
sp, ep = fmi.backward_search("ana")
print(f"\nSearch 'ana': range [{sp}, {ep}] = {ep - sp + 1} occurrences")

sp2, ep2 = fmi.backward_search("xyz")
print(f"Search 'xyz': {'not found' if sp2 == -1 else f'range [{sp2}, {ep2}]'}")
```

---

## 120.9 Code Example (Java)

```java
import java.util.*;

public class BWTAndFMIndex {

    static String bwt(String s) {
        int n = s.length();
        Integer[] sa = new Integer[n];
        for (int i = 0; i < n; i++) sa[i] = i;
        Arrays.sort(sa, (a, b) -> {
            for (int i = 0; i < n; i++) {
                char ca = s.charAt((a + i) % n);
                char cb = s.charAt((b + i) % n);
                if (ca != cb) return ca - cb;
            }
            return 0;
        });
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++)
            sb.append(s.charAt((sa[i] + n - 1) % n));
        return sb.toString();
    }

    static String inverseBwt(String bwtStr) {
        int n = bwtStr.length();
        Map<Character, Integer> count = new TreeMap<>();
        for (char c : bwtStr.toCharArray()) count.merge(c, 1, Integer::sum);
        Map<Character, Integer> C = new TreeMap<>();
        int total = 0;
        for (var e : count.entrySet()) { C.put(e.getKey(), total); total += e.getValue(); }

        int[] lf = new int[n];
        Map<Character, Integer> seen = new HashMap<>();
        for (int i = 0; i < n; i++) {
            char c = bwtStr.charAt(i);
            lf[i] = C.get(c) + seen.getOrDefault(c, 0);
            seen.merge(c, 1, Integer::sum);
        }

        int row = bwtStr.indexOf('$');
        char[] result = new char[n];
        int pos = row;
        for (int i = n - 1; i >= 0; i--) {
            result[i] = bwtStr.charAt(pos);
            pos = lf[pos];
        }
        return new String(result);
    }

    static class FMIndex {
        String bwtStr;
        Map<Character, Integer> C;
        Map<Character, int[]> rankTable;

        FMIndex(String s) {
            bwtStr = bwt(s);
            int n = bwtStr.length();
            Map<Character, Integer> count = new TreeMap<>();
            for (char c : bwtStr.toCharArray()) count.merge(c, 1, Integer::sum);
            C = new TreeMap<>();
            int total = 0;
            for (var e : count.entrySet()) { C.put(e.getKey(), total); total += e.getValue(); }

            rankTable = new HashMap<>();
            for (char c : C.keySet()) {
                int[] rt = new int[n];
                rt[0] = bwtStr.charAt(0) == c ? 1 : 0;
                for (int i = 1; i < n; i++)
                    rt[i] = rt[i-1] + (bwtStr.charAt(i) == c ? 1 : 0);
                rankTable.put(c, rt);
            }
        }

        int rank(char c, int i) {
            if (i < 0) return 0;
            return rankTable.get(c)[i];
        }

        int[] backwardSearch(String pattern) {
            int m = pattern.length();
            int n = bwtStr.length();
            char c = pattern.charAt(m - 1);
            int sp = C.get(c);
            int ep = C.get(c) + rank(c, n - 1) - 1;

            for (int i = m - 2; i >= 0 && sp <= ep; i--) {
                c = pattern.charAt(i);
                sp = C.get(c) + rank(c, sp - 1);
                ep = C.get(c) + rank(c, ep) - 1;
            }
            return sp > ep ? new int[]{-1, -1} : new int[]{sp, ep};
        }
    }

    public static void main(String[] args) {
        String s = "banana$";
        String transformed = bwt(s);
        System.out.println("Original:  \"" + s + "\"");
        System.out.println("BWT:       \"" + transformed + "\"");
        System.out.println("Recovered: \"" + inverseBwt(transformed) + "\"");

        FMIndex fmi = new FMIndex(s);
        int[] range = fmi.backwardSearch("ana");
        System.out.println("\nSearch 'ana': range [" + range[0] + ", " + range[1] + "] = " + (range[1] - range[0] + 1) + " occurrences");
    }
}
```

---

## Exercises

### Exercise 1: BWT Construction
Compute the BWT of the string `mississippi$` by listing all cyclic rotations, sorting them, and extracting the last column. Verify your result by computing the inverse BWT.

### Exercise 2: FM-Index Search Trace
Using the BWT of `mississippi$`, trace the backward search for the pattern `issi`. Show the range [sp, ep] after each character is processed.

### Exercise 3: LF-Mapping
For the BWT `annb$aa` (of `banana$`), compute the full LF-mapping array. Verify that following the chain from the `$` row reconstructs the original string.

### Exercise 4: Compression Ratio
Compute the BWT of a highly repetitive string like `abcabcabcabc$`. Compare the run-length encoded size of the original string vs the BWT string. Which compresses better?

### Exercise 5: Implement Locate
Extend the FM-Index with suffix array sampling (store every k-th SA value). Implement the `locate(i)` function that returns the original position of any BWT index. What's the space-time tradeoff for different values of k?

---

## Interview Questions

### Question 1: Why does BWT group similar characters together?
**Answer**: The BWT takes the last character of each suffix in sorted order. Since suffixes starting with similar prefixes are adjacent after sorting, the characters *preceding* those suffixes (which become the BWT) tend to be similar. For example, all suffixes starting with "an" are adjacent, and the characters before "an" in the original string are likely similar.

### Question 2: How does the FM-Index achieve O(m) search time?
**Answer**: Each character of the pattern is processed in O(1) time using precomputed rank tables. The backward search processes the pattern right-to-left, narrowing a range of matching suffixes at each step. With O(1) rank queries (via precomputed tables or wavelet trees), the total search time is O(m).

### Question 3: What's the space complexity of the FM-Index?
**Answer**: The FM-Index uses O(n log σ) bits for the BWT (or nH₀ + O(n log σ / log log n) bits with compressed representations), plus O(n log n / k) bits for suffix array sampling every k-th entry. The total is approximately nH₀ + O(n) bits, where H₀ is the zero-order entropy — much less than the n log σ bits needed for the raw text.

### Question 4: How is BWT used in genome alignment?
**Answer**: Tools like BWA build an FM-Index of the reference genome. For each sequencing read, they perform backward search to find all positions where the read matches (or approximately matches, allowing mismatches). The FM-Index enables searching a 3-billion-character genome in microseconds per read.

### Question 5: Compare BWT-based search with suffix array search.
**Answer**: Both achieve O(m + log n) search time, but the FM-Index uses less space because it doesn't need to store the full suffix array — only the BWT and sampled SA values. The trade-off is that locating exact positions requires LF-mapping chains, which is slower than direct SA access. For most applications, the space savings of FM-Index outweigh this cost.

---

## Cross-References

- **Suffix Arrays** (Chapter 158): Foundation for BWT construction
- **Suffix Trees** (Chapter 159): Alternative index structure
- **Run-Length Encoding** (Chapter 119): Compression technique used with BWT
- **Binary Search** (Chapter 38): Used in suffix array construction
- **Advanced String Processing** (Chapter 164): Grammar compression, LZ family
- **Compression** (Chapter 119): General compression theory
- **Wavelet Trees** (Chapter 120.5): Efficient rank queries on large alphabets

---

## Summary

| Component | Purpose | Time | Space |
|---|---|---|---|
| BWT | Rearrange string for compression | O(n) via SA | O(n) |
| LF-mapping | Navigate between BWT and sorted order | O(1) per step | O(n) |
| FM-Index | Pattern matching on compressed text | O(m) search | O(n) bits |
| Inverse BWT | Reconstruct original string | O(n) | O(n) |
| Wavelet Tree | Rank queries on large alphabets | O(log σ) | O(n log σ) bits |
| SA sampling | Locate positions without full SA | O(k log n) per locate | O(n log n / k) bits |
