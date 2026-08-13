# Chapter 122: Edit Distance and Its Variants

## Prerequisites
- Dynamic programming basics (Chapter 40)
- String fundamentals
- LCS (Longest Common Subsequence)

## Interview Frequency: ★★★★

Edit distance is one of the most frequently asked DP problems at **Google**, **Meta**, **Amazon**, **Microsoft**, and **Apple**. Variants test your ability to adapt a core algorithm to different constraints. Understanding edit distance deeply is essential for any serious interview preparation.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Standard Levenshtein | ★★★★ | Medium | Insert, delete, replace |
| Damerau-Levenshtein | ★★ | Medium | + Transpose |
| LCS-based distance | ★★★ | Medium | Insert, delete only |
| Hamming distance | ★★★ | Easy | Replace only, same length |
| Weighted edit distance | ★★ | Medium | Different costs per operation |
| Space-optimized | ★★ | Medium | O(min(n,m)) space |
| Real-world applications | ★★★ | Medium | Spell check, DNA alignment |

---

## 122.1 What Is Edit Distance?

### Definition

The **edit distance** between two strings is the minimum number of operations required to transform one string into the other. The allowed operations define the variant:

- **Levenshtein distance**: Insert, delete, replace (each costs 1)
- **Damerau-Levenshtein**: Insert, delete, replace, transpose adjacent characters
- **LCS distance**: Insert, delete only
- **Hamming distance**: Replace only (strings must be same length)

### Motivation

Edit distance appears everywhere:
- **Spell checking**: Find the dictionary word closest to a misspelling
- **DNA sequence alignment**: Compare genetic sequences across species
- **Plagiarism detection**: Measure text similarity
- **Diff tools**: Show changes between file versions
- **Machine translation**: Evaluate translation quality
- **Fuzzy search**: Find approximate matches in databases

### Intuition

Imagine you're editing a document with "find and replace" operations. Each operation (insert a character, delete a character, replace a character) has a cost. The edit distance is the cheapest way to transform one document into another.

Think of it as a path through a grid: you start at (0,0) and must reach (n,m). Each step represents an operation. You want the shortest path.

---

## 122.2 Standard Levenshtein Distance

### Problem

Given strings `a` (length n) and `b` (length m), find the minimum number of insertions, deletions, and substitutions to transform `a` into `b`.

### Recurrence

Let `dp[i][j]` = edit distance between `a[0..i-1]` and `b[0..j-1]`.

```
Base cases:
  dp[0][j] = j  (insert j characters)
  dp[i][0] = i  (delete i characters)

Recurrence:
  if a[i-1] == b[j-1]:
      dp[i][j] = dp[i-1][j-1]  (characters match, no operation)
  else:
      dp[i][j] = 1 + min(
          dp[i-1][j],     (delete a[i-1])
          dp[i][j-1],     (insert b[j-1] after a[i-1])
          dp[i-1][j-1]    (replace a[i-1] with b[j-1])
      )
```

### Why This Works

At position (i, j), we're deciding what to do with the last characters of both strings:
1. **Delete** a[i-1]: cost 1 + edit distance of a[0..i-2] and b[0..j-1]
2. **Insert** b[j-1]: cost 1 + edit distance of a[0..i-1] and b[0..j-2]
3. **Replace** a[i-1] with b[j-1]: cost (0 if equal, 1 if not) + edit distance of a[0..i-2] and b[0..j-2]

We take the minimum of all three options.

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

int editDistance(const std::string& a, const std::string& b) {
    int n = a.size(), m = b.size();
    std::vector<std::vector<int>> dp(n + 1, std::vector<int>(m + 1));
    
    // Base cases
    for (int i = 0; i <= n; i++) dp[i][0] = i;  // delete all
    for (int j = 0; j <= m; j++) dp[0][j] = j;  // insert all
    
    // Fill the table
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            if (a[i-1] == b[j-1]) {
                dp[i][j] = dp[i-1][j-1];  // match
            } else {
                dp[i][j] = 1 + std::min({
                    dp[i-1][j],     // delete
                    dp[i][j-1],     // insert
                    dp[i-1][j-1]    // replace
                });
            }
        }
    }
    
    return dp[n][m];
}

int main() {
    std::cout << "kitten → sitting: " << editDistance("kitten", "sitting") << "\n";
    std::cout << "saturday → sunday: " << editDistance("saturday", "sunday") << "\n";
    std::cout << "intention → execution: " << editDistance("intention", "execution") << "\n";
    std::cout << "abc → abc: " << editDistance("abc", "abc") << "\n";
    std::cout << "abc → xyz: " << editDistance("abc", "xyz") << "\n";
    
    return 0;
}
```

### Dry Run: "kitten" → "sitting"

```
     ""  s  i  t  t  i  n  g
""    0  1  2  3  4  5  6  7
k     1  1  2  3  4  5  6  7
i     2  2  1  2  3  4  5  6
t     3  3  2  1  2  3  4  5
t     4  4  3  2  1  2  3  4
e     5  5  4  3  2  2  3  4
n     6  6  5  4  3  3  2  3
```

Result: dp[6][7] = 3

Operations: kitten → sitten (replace k→s) → sittin (replace e→i) → sitting (insert g)

### Complexity

| Metric | Value |
|---|---|
| Time | O(nm) |
| Space | O(nm) |

---

## 122.3 Space-Optimized Edit Distance

### Idea

Since dp[i][j] only depends on dp[i-1][j-1], dp[i-1][j], and dp[i][j-1], we only need two rows (or one row with careful updates).

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

int editDistanceOptimized(const std::string& a, const std::string& b) {
    int n = a.size(), m = b.size();
    
    // Use shorter string for columns to minimize space
    if (n < m) return editDistanceOptimized(b, a);
    
    std::vector<int> prev(m + 1), curr(m + 1);
    
    for (int j = 0; j <= m; j++) prev[j] = j;
    
    for (int i = 1; i <= n; i++) {
        curr[0] = i;
        for (int j = 1; j <= m; j++) {
            if (a[i-1] == b[j-1]) {
                curr[j] = prev[j-1];
            } else {
                curr[j] = 1 + std::min({prev[j], curr[j-1], prev[j-1]});
            }
        }
        std::swap(prev, curr);
    }
    
    return prev[m];
}

int main() {
    std::cout << "kitten → sitting: " << editDistanceOptimized("kitten", "sitting") << "\n";
    std::cout << "saturday → sunday: " << editDistanceOptimized("saturday", "sunday") << "\n";
    
    return 0;
}
```

### Complexity

| Metric | Standard | Optimized |
|---|---|---|
| Time | O(nm) | O(nm) |
| Space | O(nm) | O(min(n,m)) |

---

## 122.4 Recovering the Edit Operations

### Problem

Not just the distance, but the actual sequence of operations.

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

struct EditOp {
    std::string type;
    int pos;
    char oldChar, newChar;
};

std::vector<EditOp> editOperations(const std::string& a, const std::string& b) {
    int n = a.size(), m = b.size();
    std::vector<std::vector<int>> dp(n + 1, std::vector<int>(m + 1));
    
    for (int i = 0; i <= n; i++) dp[i][0] = i;
    for (int j = 0; j <= m; j++) dp[0][j] = j;
    
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= m; j++) {
            if (a[i-1] == b[j-1]) dp[i][j] = dp[i-1][j-1];
            else dp[i][j] = 1 + std::min({dp[i-1][j], dp[i][j-1], dp[i-1][j-1]});
        }
    
    // Backtrack to find operations
    std::vector<EditOp> ops;
    int i = n, j = m;
    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && a[i-1] == b[j-1]) {
            i--; j--;  // match, no operation
        } else if (i > 0 && j > 0 && dp[i][j] == dp[i-1][j-1] + 1) {
            ops.push_back({"replace", i, a[i-1], b[j-1]});
            i--; j--;
        } else if (j > 0 && dp[i][j] == dp[i][j-1] + 1) {
            ops.push_back({"insert", i, 0, b[j-1]});
            j--;
        } else {
            ops.push_back({"delete", i, a[i-1], 0});
            i--;
        }
    }
    
    std::reverse(ops.begin(), ops.end());
    return ops;
}

int main() {
    auto ops = editOperations("kitten", "sitting");
    std::cout << "Operations to transform 'kitten' → 'sitting':\n";
    for (auto& op : ops) {
        if (op.type == "replace")
            std::cout << "  " << op.type << " pos " << op.pos
                      << ": '" << op.oldChar << "' → '" << op.newChar << "'\n";
        else if (op.type == "insert")
            std::cout << "  " << op.type << " at pos " << op.pos
                      << ": '" << op.newChar << "'\n";
        else
            std::cout << "  " << op.type << " at pos " << op.pos
                      << ": '" << op.oldChar << "'\n";
    }
    
    return 0;
}
```

---

## 122.5 Damerau-Levenshtein Distance

### Definition

Extends Levenshtein distance with a fourth operation: **transposition** of two adjacent characters.

This is important because typos often involve swapping adjacent letters (e.g., "teh" → "the").

### Recurrence

```
Same as Levenshtein, plus:
  if i > 1 && j > 1 && a[i-1] == b[j-2] && a[i-2] == b[j-1]:
      dp[i][j] = min(dp[i][j], dp[i-2][j-2] + cost)
```

where `cost` is 1 for transposition (or 0 if the characters are already in the right order).

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

int damerauLevenshtein(const std::string& a, const std::string& b) {
    int n = a.size(), m = b.size();
    std::vector<std::vector<int>> dp(n + 1, std::vector<int>(m + 1));
    
    for (int i = 0; i <= n; i++) dp[i][0] = i;
    for (int j = 0; j <= m; j++) dp[0][j] = j;
    
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            int cost = (a[i-1] == b[j-1]) ? 0 : 1;
            dp[i][j] = std::min({
                dp[i-1][j] + 1,        // delete
                dp[i][j-1] + 1,        // insert
                dp[i-1][j-1] + cost    // replace or match
            });
            
            // Transposition
            if (i > 1 && j > 1 && a[i-1] == b[j-2] && a[i-2] == b[j-1]) {
                dp[i][j] = std::min(dp[i][j], dp[i-2][j-2] + cost);
            }
        }
    }
    
    return dp[n][m];
}

int main() {
    // "ab" → "ba": 1 transposition (Levenshtein would say 2: replace both)
    std::cout << "ab → ba (Levenshtein): " << editDistance("ab", "ba") << "\n";
    std::cout << "ab → ba (Damerau): " << damerauLevenshtein("ab", "ba") << "\n";
    
    // "abc" → "bac": 1 transposition
    std::cout << "abc → bac (Levenshtein): " << editDistance("abc", "bac") << "\n";
    std::cout << "abc → bac (Damerau): " << damerauLevenshtein("abc", "bac") << "\n";
    
    // "teh" → "the": 1 transposition
    std::cout << "teh → the (Levenshtein): " << editDistance("teh", "the") << "\n";
    std::cout << "teh → the (Damerau): " << damerauLevenshtein("teh", "the") << "\n";
    
    // "saturday" → "sunday": same as Levenshtein (no transpositions help)
    std::cout << "saturday → sunday (Levenshtein): " << editDistance("saturday", "sunday") << "\n";
    std::cout << "saturday → sunday (Damerau): " << damerauLevenshtein("saturday", "sunday") << "\n";
    
    return 0;
}
```

### Dry Run: "ab" → "ba"

```
Levenshtein:
     ""  b  a
""    0  1  2
a     1  1  2
b     2  2  2  ← distance = 2

Damerau-Levenshtein:
     ""  b  a
""    0  1  2
a     1  1  2
b     2  1  1  ← distance = 1 (transposition!)
```

At dp[2][2]: a[1]='b', b[0]='b', a[0]='a', b[1]='a' → a[1]==b[0] && a[0]==b[1] → transposition! dp[2][2] = min(2, dp[0][0]+1) = 1

---

## 122.6 LCS Distance (Insert/Delete Only)

### Problem

Only allow insertions and deletions (no replacements). This is equivalent to the **Longest Common Subsequence** problem.

**Relationship**: `LCS_distance(a, b) = n + m - 2 * LCS(a, b)`

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

int lcsLength(const std::string& a, const std::string& b) {
    int n = a.size(), m = b.size();
    std::vector<std::vector<int>> dp(n + 1, std::vector<int>(m + 1, 0));
    
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= m; j++) {
            if (a[i-1] == b[j-1]) dp[i][j] = dp[i-1][j-1] + 1;
            else dp[i][j] = std::max(dp[i-1][j], dp[i][j-1]);
        }
    
    return dp[n][m];
}

int lcsDistance(const std::string& a, const std::string& b) {
    return a.size() + b.size() - 2 * lcsLength(a, b);
}

// Space-optimized LCS
int lcsLengthOptimized(const std::string& a, const std::string& b) {
    int n = a.size(), m = b.size();
    std::vector<int> prev(m + 1, 0), curr(m + 1, 0);
    
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            if (a[i-1] == b[j-1]) curr[j] = prev[j-1] + 1;
            else curr[j] = std::max(prev[j], curr[j-1]);
        }
        std::swap(prev, curr);
    }
    
    return prev[m];
}

int main() {
    std::string a = "ABCBDAB";
    std::string b = "BDCABA";
    
    int lcs = lcsLength(a, b);
    int dist = lcsDistance(a, b);
    
    std::cout << "LCS of \"" << a << "\" and \"" << b << "\": " << lcs << "\n";
    std::cout << "LCS distance: " << dist << "\n";
    std::cout << "(n=" << a.size() << ", m=" << b.size()
              << ", n+m-2*LCS=" << a.size() << "+" << b.size()
              << "-2*" << lcs << "=" << dist << ")\n";
    
    // Verify with space-optimized
    std::cout << "LCS (optimized): " << lcsLengthOptimized(a, b) << "\n";
    
    return 0;
}
```

### Complexity

| Metric | Value |
|---|---|
| Time | O(nm) |
| Space | O(nm) standard, O(min(n,m)) optimized |

---

## 122.7 Hamming Distance

### Definition

**Hamming distance** counts the number of positions where corresponding characters differ. Only defined for strings of equal length. Only substitution is allowed.

```cpp
#include <iostream>
#include <string>

int hammingDistance(const std::string& a, const std::string& b) {
    if (a.size() != b.size()) return -1;  // undefined
    
    int dist = 0;
    for (int i = 0; i < (int)a.size(); i++)
        if (a[i] != b[i]) dist++;
    return dist;
}

// Bitwise Hamming distance for integers
int hammingDistanceInt(int a, int b) {
    return __builtin_popcount(a ^ b);  // count differing bits
}

int main() {
    std::cout << "Hamming('karolin', 'kathrin'): " << hammingDistance("karolin", "kathrin") << "\n";
    std::cout << "Hamming('10101', '11110'): " << hammingDistance("10101", "11110") << "\n";
    std::cout << "Hamming bits(29, 15): " << hammingDistanceInt(29, 15) << "\n";
    // 29 = 11101, 15 = 01111, XOR = 10010, popcount = 2
    
    return 0;
}
```

### Complexity

| Metric | Value |
|---|---|
| Time | O(n) |
| Space | O(1) |

---

## 122.8 Weighted Edit Distance

### Problem

Different operations have different costs. For example, in DNA alignment, transitions (A↔G, C↔T) are more common than transversions (A↔C, A↔T, G↔C, G↔T).

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>

struct EditCosts {
    int insert_cost = 1;
    int delete_cost = 1;
    int replace_cost = 1;
    std::map<std::pair<char,char>, int> specific_replace;  // specific costs
};

int weightedEditDistance(const std::string& a, const std::string& b,
                         const EditCosts& costs) {
    int n = a.size(), m = b.size();
    std::vector<std::vector<int>> dp(n + 1, std::vector<int>(m + 1));
    
    for (int i = 0; i <= n; i++) dp[i][0] = i * costs.delete_cost;
    for (int j = 0; j <= m; j++) dp[0][j] = j * costs.insert_cost;
    
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            int replace;
            if (a[i-1] == b[j-1]) {
                replace = 0;
            } else {
                auto key = std::make_pair(a[i-1], b[j-1]);
                auto it = costs.specific_replace.find(key);
                replace = (it != costs.specific_replace.end()) ? it->second : costs.replace_cost;
            }
            
            dp[i][j] = std::min({
                dp[i-1][j] + costs.delete_cost,
                dp[i][j-1] + costs.insert_cost,
                dp[i-1][j-1] + replace
            });
        }
    }
    
    return dp[n][m];
}

int main() {
    EditCosts costs;
    costs.insert_cost = 1;
    costs.delete_cost = 1;
    costs.replace_cost = 2;  // substitution is expensive
    
    // DNA: transitions cheaper than transversions
    costs.specific_replace[{'A', 'G'}] = 1;  // transition
    costs.specific_replace[{'G', 'A'}] = 1;
    costs.specific_replace[{'C', 'T'}] = 1;  // transition
    costs.specific_replace[{'T', 'C'}] = 1;
    
    std::string dna1 = "AGTCAGTC";
    std::string dna2 = "AGTGAGTG";
    
    std::cout << "Weighted edit distance (DNA): "
              << weightedEditDistance(dna1, dna2, costs) << "\n";
    
    // Standard Levenshtein for comparison
    EditCosts standard;
    std::cout << "Standard edit distance: "
              << weightedEditDistance(dna1, dna2, standard) << "\n";
    
    return 0;
}
```

---

## 122.9 Edit Distance for Real-World Applications

### Spell Checker

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <fstream>

class SpellChecker {
    std::vector<std::string> dictionary;
    
    int editDistance(const std::string& a, const std::string& b) {
        int n = a.size(), m = b.size();
        std::vector<std::vector<int>> dp(n + 1, std::vector<int>(m + 1));
        for (int i = 0; i <= n; i++) dp[i][0] = i;
        for (int j = 0; j <= m; j++) dp[0][j] = j;
        for (int i = 1; i <= n; i++)
            for (int j = 1; j <= m; j++) {
                if (a[i-1] == b[j-1]) dp[i][j] = dp[i-1][j-1];
                else dp[i][j] = 1 + std::min({dp[i-1][j], dp[i][j-1], dp[i-1][j-1]});
            }
        return dp[n][m];
    }
    
public:
    SpellChecker(const std::vector<std::string>& words) : dictionary(words) {}
    
    std::vector<std::pair<std::string, int>> suggest(const std::string& word, int maxDist = 2) {
        std::vector<std::pair<std::string, int>> suggestions;
        for (const auto& dictWord : dictionary) {
            // Quick filter: skip if length difference > maxDist
            if (abs((int)dictWord.size() - (int)word.size()) > maxDist) continue;
            
            int dist = editDistance(word, dictWord);
            if (dist <= maxDist)
                suggestions.push_back({dictWord, dist});
        }
        std::sort(suggestions.begin(), suggestions.end(),
                  [](auto& a, auto& b) { return a.second < b.second; });
        return suggestions;
    }
};

int main() {
    std::vector<std::string> dict = {
        "apple", "application", "apply", "appreciate",
        "banana", "band", "bandana",
        "cat", "car", "card", "care",
        "dog", "dot", "done",
        "the", "teh", "them", "they"
    };
    
    SpellChecker checker(dict);
    
    std::vector<std::string> typos = {"aple", "bndna", "teh", "dgo", "cra"};
    for (auto& typo : typos) {
        auto suggestions = checker.suggest(typo);
        std::cout << "\"" << typo << "\" → ";
        for (auto& [word, dist] : suggestions)
            std::cout << word << "(" << dist << ") ";
        std::cout << "\n";
    }
    
    return 0;
}
```

### DNA Sequence Alignment

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

struct AlignmentResult {
    int score;
    std::string alignedA, alignedB;
};

// Needleman-Wunsch (global alignment) with affine gap penalties
AlignmentResult globalAlignment(const std::string& a, const std::string& b,
                                 int match = 2, int mismatch = -1,
                                 int gapOpen = -2, int gapExtend = -1) {
    int n = a.size(), m = b.size();
    
    // Standard edit distance DP with scoring
    std::vector<std::vector<int>> dp(n + 1, std::vector<int>(m + 1));
    
    for (int i = 0; i <= n; i++) dp[i][0] = i * gapOpen;
    for (int j = 0; j <= m; j++) dp[0][j] = j * gapOpen;
    
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= m; j++) {
            int score = (a[i-1] == b[j-1]) ? match : mismatch;
            dp[i][j] = std::max({
                dp[i-1][j-1] + score,  // match/mismatch
                dp[i-1][j] + gapOpen,  // gap in b
                dp[i][j-1] + gapOpen   // gap in a
            });
        }
    
    // Backtrack for alignment
    std::string alignA, alignB;
    int i = n, j = m;
    while (i > 0 || j > 0) {
        if (i > 0 && j > 0) {
            int score = (a[i-1] == b[j-1]) ? match : mismatch;
            if (dp[i][j] == dp[i-1][j-1] + score) {
                alignA = a[i-1] + alignA;
                alignB = b[j-1] + alignB;
                i--; j--;
                continue;
            }
        }
        if (i > 0 && dp[i][j] == dp[i-1][j] + gapOpen) {
            alignA = a[i-1] + alignA;
            alignB = '-' + alignB;
            i--;
        } else {
            alignA = '-' + alignA;
            alignB = b[j-1] + alignB;
            j--;
        }
    }
    
    return {dp[n][m], alignA, alignB};
}

int main() {
    std::string seq1 = "AGTCAGTCAGTC";
    std::string seq2 = "AGTGAGTG";
    
    auto result = globalAlignment(seq1, seq2);
    std::cout << "Score: " << result.score << "\n";
    std::cout << "A: " << result.alignedA << "\n";
    std::cout << "B: " << result.alignedB << "\n";
    
    // Show match/mismatch
    std::cout << "   ";
    for (int i = 0; i < (int)result.alignedA.size(); i++) {
        if (result.alignedA[i] == result.alignedB[i]) std::cout << "|";
        else if (result.alignedA[i] == '-' || result.alignedB[i] == '-') std::cout << " ";
        else std::cout << " ";
    }
    std::cout << "\n";
    
    return 0;
}
```

---

## Summary

| Variant | Operations | Time | Space | Use Case |
|---|---|---|---|---|
| Levenshtein | Insert, delete, replace | O(nm) | O(min(n,m)) | General string comparison |
| Damerau-Levenshtein | + Transpose | O(nm) | O(nm) | Typo correction |
| LCS distance | Insert, delete | O(nm) | O(min(n,m)) | Diff tools |
| Hamming | Replace only | O(n) | O(1) | Binary/fixed-length strings |
| Weighted | Custom costs | O(nm) | O(nm) | DNA alignment |

---

## Exercises

1. **Edit Distance with Swap**: Extend Levenshtein to allow swapping non-adjacent characters (cost 1). Design the DP recurrence.

2. **k-Edit Distance**: Given a threshold k, determine if two strings have edit distance ≤ k. Can you do it faster than O(nm)?

3. **Longest Common Substring**: Find the longest common substring (contiguous) of two strings using DP.

4. **Edit Distance with Transposition**: Implement the optimal string alignment (OSA) variant of Damerau-Levenshtein, which doesn't allow a substring to be edited more than once.

5. **Spell Checker Optimization**: Optimize the spell checker using BK-trees or Symmetric Delete Algorithm (SymSpell).

6. **Myers' Diff Algorithm**: Research and implement Myers' O(ND) diff algorithm, which is faster when the edit distance D is small.

---

## Interview Questions

1. **Q**: What's the time and space complexity of standard edit distance? How can you optimize space?
   **A**: Time: O(nm). Space: O(nm) for the full table, O(min(n,m)) using the rolling array technique. For just the distance (not the operations), two rows suffice.

2. **Q**: How would you find the actual edit operations, not just the distance?
   **A**: After filling the DP table, backtrack from dp[n][m] to dp[0][0]. At each step, check which cell the current value came from (diagonal = replace/match, up = delete, left = insert).

3. **Q**: When would you use Damerau-Levenshtein over standard Levenshtein?
   **A**: When transpositions are common — like typing errors where adjacent letters are swapped ("teh" → "the"). Standard Levenshtein counts this as 2 operations (delete + insert), but Damerau-Levenshtein counts it as 1.

4. **Q**: How is edit distance related to LCS?
   **A**: LCS_distance = n + m - 2 * LCS_length. LCS only allows insertions and deletions. Levenshtein adds substitution. So LCS distance ≥ Levenshtein distance in general.

5. **Q**: How would you implement a fuzzy search that finds all dictionary words within edit distance 2 of a query?
   **A**: Options: (1) Brute force: compute edit distance to every word — O(N·nm). (2) BK-tree: tree structure that prunes search space using triangle inequality. (3) SymSpell: precompute all deletions within distance k and use hash lookup. (4) Trie with early termination: stop exploring when current distance exceeds threshold.

6. **Q**: Can edit distance be computed in sub-quadratic time?
   **A**: In general, no — Ω(nm) is a lower bound for comparison-based algorithms. But if the edit distance is small (d), Myers' algorithm runs in O(nd). For strings over a small alphabet, there are faster algorithms.

---

## Cross-References

- **Chapter 40**: Dynamic Programming Basics — foundation for edit distance
- **Chapter 44**: String DP — related string problems
- **Chapter 43**: LCS — longest common subsequence
- **Chapter 118**: Bitset DP — space optimization techniques
- **Chapter 123**: Cache Optimization — memory access patterns in DP
- **Chapter 77**: Trie — for efficient spell checking
