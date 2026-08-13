# Chapter 87: Suffix Tree

## Prerequisites
- Tries and compressed tries
- Suffix arrays (Chapter 86)
- String basics and pattern matching
- Recursion and divide-and-conquer

## Interview Frequency: ★★

Suffix trees are one of the most powerful data structures for string processing. They compress all suffixes of a string into a tree structure, enabling linear-time solutions to many problems that would otherwise require quadratic or worse time. **Google**, **Facebook**, and other top companies test suffix tree concepts for hard string problems, particularly pattern matching, longest common substrings, and text indexing.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Suffix tree structure | ★★ | Medium | Understanding the structure |
| Ukkonen's algorithm | ★ | Hard | Online O(n) construction |
| Applications | ★★★ | Medium | LCS, pattern matching, repeats |
| Suffix array alternative | ★★ | Medium | More practical in interviews |

---

## 87.1 Motivation and Intuition

### The Problem

Given a text T of length n, we want to answer queries like:
- Does pattern P occur in T? (Pattern matching)
- What is the longest substring that appears at least twice? (Longest repeated substring)
- What is the longest common substring of T₁ and T₂? (LCS)
- How many distinct substrings does T have?

A naive approach answers each query in O(nm) time. With a suffix tree, all of these become O(n) preprocessing + O(m) or O(1) per query.

### Intuition: Compressed Trie of All Suffixes

A suffix tree is a compressed trie (radix tree) of all suffixes of a string S$, where $ is a unique terminator not appearing in S.

**Example**: For S = "banana$"

Suffixes:
```
banana$
anana$
nana$
ana$
na$
a$
$
```

Build a trie of these suffixes, then compress (merge single-child chains):

```
         root
        / | \
       b  a  n
       |  |  |
      ... etc
```

Each edge stores a substring (represented as indices into S to save space). Each leaf corresponds to a suffix.

### Why Is It Powerful?

Because every substring of S is a prefix of some suffix. Finding if P occurs in S is equivalent to finding if P exists as a path from the root. This takes O(|P|) time by following edges.

---

## 87.2 Structure and Properties

### Formal Definition

A suffix tree for string S[0..n-1]$ (length n+1) is a rooted tree with:
1. **Exactly n+1 leaves**, one for each suffix
2. **Each internal node has at least 2 children** (no degree-1 internal nodes)
3. **Each edge is labeled with a non-empty substring** of S$
4. **No two edges from the same node share the same first character**
5. **Suffixes are stored at leaves** (or as indices)

### Implicit Suffix Tree

During construction (Ukkonen's algorithm), we work with an **implicit suffix tree** — the suffix tree of S[0..i] without the $ terminator. Internal nodes may have only one child. We convert to the explicit suffix tree at the end by adding $.

### Path Labels and Suffix Links

- **Path label of a node**: Concatenation of edge labels from root to that node
- **Suffix link**: If an internal node represents path xa (where x is a character), its suffix link points to the node representing path a. These are critical for Ukkonen's algorithm.

### Space

- O(n) nodes (since each of n+1 leaves contributes at most one internal node)
- O(n) edges, each storing two integers (start, end) → O(n) total space
- Suffix links: O(n) additional pointers

---

## 87.3 Ukkonen's Algorithm (Online Construction)

Ukkonen's algorithm builds the suffix tree online — adding one character at a time — in O(n) time.

### Key Ideas

1. **Phase i**: Add character S[i] to the tree built for S[0..i-1]
2. **Extension j**: Insert suffix S[j..i] into the tree
3. **Three extension rules**:
   - **Rule 1**: Path ends at a leaf → extend the leaf's edge
   - **Rule 2**: Path ends inside an edge → split the edge, create new leaf
   - **Rule 3**: Path already exists → do nothing (stop early)

### The Trick: Implicit Extensions and Counting

Naively, phase i requires i extensions (O(n²) total). Ukkonen's key insight:
- Once a leaf is created, it remains a leaf (Rule 1 applies automatically)
- Use **suffix links** to jump between extensions efficiently
- **Counting trick**: Track the number of extensions already done implicitly

### Suffix Links

When we split an edge (Rule 2) at node `u`, we set the suffix link of the previously split node to `u`. This allows the next extension to start at `u` rather than the root.

### Amortized Analysis

Each character is added to the tree at most once (as part of an edge label). Each edge split takes O(1) time. Therefore, total time is O(n).

### Dry Run: Building Suffix Tree for "abc"

**Phase 0: Add 'a'**
```
root -- "a" --> leaf (suffix 0)
```

**Phase 1: Add 'b'**
- Extend suffix 0 ("ab"): Leaf extends → edge "ab"
- Extend suffix 1 ("b"): New leaf
```
root -- "ab" --> leaf 0
      -- "b"  --> leaf 1
```

**Phase 2: Add 'c'**
- Extend suffix 0 ("abc"): Leaf extends → edge "abc"
- Extend suffix 1 ("bc"): Leaf extends → edge "bc"
- Extend suffix 2 ("c"): New leaf
```
root -- "abc" --> leaf 0
      -- "bc"  --> leaf 1
      -- "c"   --> leaf 2
```

### Dry Run: Building Suffix Tree for "banana$"

Suffixes: banana$, anana$, nana$, ana$, na$, a$, $

After compression, the tree looks like:

```
          root
         / | \
        $  a  b   n
        |  |  |   |
      L6  $  $  a  anana$  L0
          |  |  |   |
         L5 L1 L4  na$  L2
                    |
                   L3
```

Where L0..L6 are leaves for suffixes 0..6.

---

## 87.4 Applications

### Pattern Matching: O(m)

To check if pattern P occurs in T:
1. Start at root
2. Follow the edge whose label starts with P[0]
3. Match characters along the edge
4. If all characters of P match, P is found

```
Search("nan" in "banana$"):
  root → follow 'n' edge → match "na" → follow 'n' edge → match → FOUND
```

### Longest Repeated Substring: O(n)

Find the deepest internal node (by path label length). The path label to that node is the longest substring that appears at least twice.

**Why**: An internal node has at least two children, meaning there are at least two suffixes (hence two occurrences) that share that prefix.

### Longest Common Substring of T₁ and T₂: O(n₁ + n₂)

1. Build a generalized suffix tree for T₁#T₂$ (using different terminators)
2. For each internal node, track which strings have leaves in its subtree
3. Find the deepest internal node whose subtree contains leaves from both T₁ and T₂

### Count Distinct Substrings: O(n)

Each distinct substring corresponds to a unique path from the root. Count all edge label characters:
```
distinct = Σ (length of edge label for all edges)
```
Or equivalently: number of leaves × average depth.

### Longest Palindrome: O(n)

Build a generalized suffix tree for S#reverse(S)$. Find the deepest node with leaves from both halves.

---

## 87.5 Practical Alternative: Suffix Array + LCP

Suffix arrays are easier to implement and solve most suffix tree problems with competitive performance.

### Suffix Array

A sorted array of all suffix indices. For S = "banana$":
```
SA = [6, 5, 3, 1, 0, 4, 2]
      $  a$ ana$ anana$ banana$ na$ nana$
```

### LCP Array

LCP[i] = length of longest common prefix between SA[i] and SA[i-1].
```
SA:  6  5  3  1  0  4  2
     $  a$ ana$ anana$ banana$ na$ nana$
LCP: -  0  1  3  0  0  2
```

### Building Suffix Array: O(n log n)

Using the prefix-doubling approach:
1. Sort by first character
2. Sort by first 2 characters
3. Sort by first 4 characters
4. Continue until all suffixes are sorted

Each step uses counting sort on ranks → O(n) per step, log n steps total.

### Building LCP Array: Kasai's Algorithm: O(n)

Given SA and the original string:
```
Build rank[]: rank[SA[i]] = i
h = 0
for i = 0 to n-1:
    if rank[i] == 0: continue
    j = SA[rank[i] - 1]
    while S[i+h] == S[j+h]: h++
    LCP[rank[i]] = h
    if h > 0: h--
```

### Applications with Suffix Array + LCP

| Problem | Solution | Time |
|---|---|---|
| Pattern matching | Binary search on SA | O(m log n) |
| Longest repeated substring | Max in LCP array | O(n) |
| Count distinct substrings | n(n+1)/2 - sum(LCP) | O(n) |
| Longest common substring | Build generalized SA + LCP | O(n log n) |

---

## 87.6 Implementations

### C++: Suffix Array with LCP (Kasai's Algorithm)

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <numeric>

class SuffixArray {
    std::string s;
    std::vector<int> sa;   // Suffix array
    std::vector<int> rank; // Inverse of SA
    std::vector<int> lcp;  // LCP array
    
public:
    SuffixArray(const std::string& str) : s(str) {
        buildSuffixArray();
        buildLCPArray();
    }
    
    void buildSuffixArray() {
        int n = s.size();
        sa.resize(n);
        rank.resize(n);
        std::vector<int> tmp(n);
        
        // Initial ranking by character
        std::iota(sa.begin(), sa.end(), 0);
        for (int i = 0; i < n; i++) rank[i] = s[i];
        
        // Prefix doubling
        for (int k = 1; k < n; k *= 2) {
            auto cmp = [&](int a, int b) {
                if (rank[a] != rank[b]) return rank[a] < rank[b];
                int ra = (a + k < n) ? rank[a + k] : -1;
                int rb = (b + k < n) ? rank[b + k] : -1;
                return ra < rb;
            };
            std::sort(sa.begin(), sa.end(), cmp);
            
            tmp[sa[0]] = 0;
            for (int i = 1; i < n; i++)
                tmp[sa[i]] = tmp[sa[i-1]] + (cmp(sa[i-1], sa[i]) ? 1 : 0);
            rank = tmp;
            
            if (rank[sa[n-1]] == n - 1) break; // All ranks unique
        }
    }
    
    void buildLCPArray() {
        int n = s.size();
        lcp.resize(n - 1);
        int h = 0;
        
        for (int i = 0; i < n; i++) {
            if (rank[i] == 0) continue;
            int j = sa[rank[i] - 1];
            while (i + h < n && j + h < n && s[i + h] == s[j + h]) h++;
            lcp[rank[i] - 1] = h;
            if (h > 0) h--;
        }
    }
    
    // Pattern matching using binary search on suffix array
    bool search(const std::string& pattern) const {
        int lo = 0, hi = (int)sa.size() - 1;
        int m = pattern.size();
        
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            int cmp = s.compare(sa[mid], m, pattern);
            if (cmp == 0) return true;
            if (cmp < 0) lo = mid + 1;
            else hi = mid - 1;
        }
        return false;
    }
    
    // Longest repeated substring
    std::string longestRepeatedSubstring() const {
        if (lcp.empty()) return "";
        int maxIdx = 0;
        for (int i = 1; i < (int)lcp.size(); i++)
            if (lcp[i] > lcp[maxIdx]) maxIdx = i;
        return s.substr(sa[maxIdx], lcp[maxIdx]);
    }
    
    // Count distinct substrings
    long long countDistinctSubstrings() const {
        long long n = s.size();
        long long total = n * (n + 1) / 2;
        for (int x : lcp) total -= x;
        return total;
    }
    
    void print() const {
        int n = s.size();
        std::cout << "Suffix Array for \"" << s << "\":\n";
        std::cout << "  Index  Suffix                    LCP\n";
        std::cout << "  -----  ----------------------    ---\n";
        for (int i = 0; i < n; i++) {
            std::string suffix = s.substr(sa[i]);
            // Replace $ with visible marker for display
            for (char& c : suffix) if (c == '$') c = '¤';
            printf("  %5d  %-24s", sa[i], suffix.c_str());
            if (i > 0) printf("  %d", lcp[i-1]);
            printf("\n");
        }
    }
};

int main() {
    std::string s = "banana$";
    SuffixArray sa(s);
    sa.print();
    
    std::cout << "\nPattern matching:\n";
    std::cout << "  'nan' found: " << sa.search("nan") << "\n";
    std::cout << "  'xyz' found: " << sa.search("xyz") << "\n";
    
    std::cout << "\nLongest repeated substring: \"" 
              << sa.longestRepeatedSubstring() << "\"\n";
    std::cout << "Distinct substrings: " << sa.countDistinctSubstrings() << "\n";
    
    return 0;
}
```

### Python: Ukkonen's Suffix Tree (Simplified)

```python
class SuffixTreeNode:
    """A node in the suffix tree."""
    def __init__(self, start=-1, end=None):
        self.children = {}       # char -> SuffixTreeNode
        self.suffix_link = None  # Suffix link for Ukkonen's
        self.start = start       # Edge label start index
        self.end = end           # Edge label end index (None = leaf)
        self.suffix_index = -1   # Set for leaves only

class SuffixTree:
    """
    Suffix tree using Ukkonen's algorithm.
    
    Note: This is a simplified implementation for educational purposes.
    Production implementations handle edge cases more carefully.
    
    Complexity:
        Build: O(n) amortized
        Space: O(n)
    """
    
    def __init__(self, text):
        self.text = text
        self.root = SuffixTreeNode(-1, [-1])  # Root has no edge label
        self.root.end = [-1]  # Mutable end for leaf extension
        
        # Active point
        self.active_node = self.root
        self.active_edge = -1
        self.active_length = 0
        
        self.remaining = 0
        self.leaf_end = [-1]  # Shared mutable end for all leaves
        
        # Build the tree
        for i in range(len(text)):
            self._extend(i)
        
        # Set suffix indices
        self._set_suffix_indices(self.root, 0)
    
    def _active_edge_char(self):
        return self.text[self.active_edge]
    
    def _edge_length(self, node):
        end = node.end[0] if node.end[0] != -1 else self.leaf_end[0]
        return end - node.start + 1
    
    def _walk_down(self, node):
        length = self._edge_length(node)
        if self.active_length >= length:
            self.active_edge += length
            self.active_length -= length
            self.active_node = node
            return True
        return False
    
    def _extend(self, phase):
        self.leaf_end[0] = phase
        self.remaining += 1
        last_new_node = None
        
        while self.remaining > 0:
            if self.active_length == 0:
                self.active_edge = phase
            
            if self._active_edge_char() not in self.active_node.children:
                # Rule 2: No edge starting with active_edge_char, create leaf
                self.active_node.children[self._active_edge_char()] = \
                    SuffixTreeNode(phase, self.leaf_end)
                if last_new_node is not None:
                    last_new_node.suffix_link = self.active_node
                    last_new_node = None
            else:
                next_node = self.active_node.children[self._active_edge_char()]
                if self._walk_down(next_node):
                    continue
                
                # Rule 3: Character already on edge
                if self.text[next_node.start + self.active_length] == self.text[phase]:
                    if last_new_node and self.active_node != self.root:
                        last_new_node.suffix_link = self.active_node
                    self.active_length += 1
                    break
                
                # Rule 2: Split the edge
                split = SuffixTreeNode(next_node.start, 
                                       [next_node.start + self.active_length - 1])
                self.active_node.children[self._active_edge_char()] = split
                
                # New leaf from split
                leaf = SuffixTreeNode(phase, self.leaf_end)
                split.children[self.text[phase]] = leaf
                
                # Update existing node
                next_node.start += self.active_length
                split.children[self.text[next_node.start]] = next_node
                
                if last_new_node:
                    last_new_node.suffix_link = split
                last_new_node = split
            
            self.remaining -= 1
            if self.active_node == self.root and self.active_length > 0:
                self.active_length -= 1
                self.active_edge = phase - self.remaining + 1
            elif self.active_node.suffix_link:
                self.active_node = self.active_node.suffix_link
            else:
                self.active_node = self.root
    
    def _set_suffix_indices(self, node, label_height):
        if not node.children:
            node.suffix_index = len(self.text) - label_height
            return
        for child in node.children.values():
            self._set_suffix_indices(child, label_height + self._edge_length(child))
    
    def search(self, pattern):
        """Search for a pattern in the suffix tree. O(m)"""
        node = self.root
        i = 0
        while i < len(pattern):
            if pattern[i] not in node.children:
                return False
            child = node.children[pattern[i]]
            edge_len = self._edge_length(child)
            for j in range(edge_len):
                if i + j >= len(pattern):
                    return True
                if self.text[child.start + j] != pattern[i + j]:
                    return False
            i += edge_len
            node = child
        return True

if __name__ == "__main__":
    text = "banana$"
    tree = SuffixTree(text)
    
    patterns = ["nan", "ana", "ban", "xyz", "banana", "a$"]
    for p in patterns:
        found = tree.search(p)
        print(f"Search '{p}': {'Found' if found else 'Not found'}")
```

### Java: Longest Common Substring Using Suffix Array

```java
import java.util.*;

/**
 * Find the longest common substring of two strings
 * using a generalized suffix array with LCP.
 * 
 * Time: O(n log n) for suffix array, O(n) for LCS finding
 * Space: O(n)
 */
public class LongestCommonSubstring {
    
    static class SuffixArray {
        int[] sa, rank, lcp;
        String s;
        int n1; // Length of first string
        
        SuffixArray(String text, int firstLen) {
            s = text;
            n1 = firstLen;
            int n = s.length();
            sa = new int[n];
            rank = new int[n];
            lcp = new int[n - 1];
            
            buildSA();
            buildLCP();
        }
        
        void buildSA() {
            int n = s.length();
            int[] tmp = new int[n];
            
            for (int i = 0; i < n; i++) {
                sa[i] = i;
                rank[i] = s.charAt(i);
            }
            
            for (int k = 1; k < n; k *= 2) {
                final int kk = k;
                final int[] r = rank;
                Integer[] indices = new Integer[n];
                for (int i = 0; i < n; i++) indices[i] = i;
                
                Arrays.sort(indices, (a, b) -> {
                    if (r[a] != r[b]) return r[a] - r[b];
                    int ra = (a + kk < n) ? r[a + kk] : -1;
                    int rb = (b + kk < n) ? r[b + kk] : -1;
                    return ra - rb;
                });
                
                for (int i = 0; i < n; i++) sa[i] = indices[i];
                tmp[sa[0]] = 0;
                for (int i = 1; i < n; i++) {
                    int prev = sa[i-1], curr = sa[i];
                    boolean same = rank[prev] == rank[curr] &&
                        ((prev + kk < n ? rank[prev + kk] : -1) ==
                         (curr + kk < n ? rank[curr + kk] : -1));
                    tmp[curr] = tmp[prev] + (same ? 0 : 1);
                }
                rank = tmp.clone();
                if (rank[sa[n-1]] == n - 1) break;
            }
        }
        
        void buildLCP() {
            int n = s.length();
            int h = 0;
            for (int i = 0; i < n; i++) {
                if (rank[i] == 0) continue;
                int j = sa[rank[i] - 1];
                while (i + h < n && j + h < n && 
                       s.charAt(i + h) == s.charAt(j + h)) h++;
                lcp[rank[i] - 1] = h;
                if (h > 0) h--;
            }
        }
        
        /**
         * Find longest common substring of the two strings.
         * Requires that suffixes from different strings alternate.
         */
        String longestCommonSubstring() {
            int n = s.length();
            int maxLen = 0, maxIdx = 0;
            
            for (int i = 1; i < n; i++) {
                // Check if adjacent suffixes come from different strings
                boolean fromFirst1 = sa[i-1] < n1;
                boolean fromFirst2 = sa[i] < n1;
                
                if (fromFirst1 != fromFirst2 && lcp[i-1] > maxLen) {
                    maxLen = lcp[i-1];
                    maxIdx = sa[i];
                }
            }
            
            return s.substring(maxIdx, maxIdx + maxLen);
        }
    }
    
    public static String findLCS(String s1, String s2) {
        // Build generalized suffix array
        // Use unique separator to ensure proper boundary handling
        String combined = s1 + "#" + s2 + "$";
        SuffixArray sa = new SuffixArray(combined, s1.length());
        
        int n = combined.length();
        int maxLen = 0, maxIdx = 0;
        
        for (int i = 1; i < n; i++) {
            boolean fromFirst = sa.sa[i-1] < s1.length();
            boolean fromSecond = sa.sa[i] < s1.length() + 1 + s2.length() 
                                 && sa.sa[i] >= s1.length() + 1;
            boolean fromFirst2 = sa.sa[i] < s1.length();
            boolean fromSecond2 = sa.sa[i-1] < s1.length() + 1 + s2.length()
                                  && sa.sa[i-1] >= s1.length() + 1;
            
            if ((fromFirst && fromSecond2) || (fromFirst2 && fromSecond)) {
                if (sa.lcp[i-1] > maxLen) {
                    maxLen = sa.lcp[i-1];
                    maxIdx = sa.sa[i];
                }
            }
        }
        
        return combined.substring(maxIdx, maxIdx + maxLen);
    }
    
    public static void main(String[] args) {
        String s1 = "abcdfgh";
        String s2 = "abtdfghx";
        
        String lcs = findLCS(s1, s2);
        System.out.println("S1: " + s1);
        System.out.println("S2: " + s2);
        System.out.println("Longest Common Substring: \"" + lcs + "\" (length " + lcs.length() + ")");
        
        // Another example
        s1 = "photograph";
        s2 = "tomography";
        lcs = findLCS(s1, s2);
        System.out.println("\nS1: " + s1);
        System.out.println("S2: " + s2);
        System.out.println("Longest Common Substring: \"" + lcs + "\" (length " + lcs.length() + ")");
    }
}
```

---

## 87.7 Ukkonen's Algorithm Deep Dive

### Phase-by-Phase Construction

For each phase i (adding character S[i]):

1. **Start** at the active point (active_node, active_edge, active_length)
2. **Walk down** from active node to find where to insert
3. **Apply extension rules**:
   - Rule 1: Extend leaf (automatically via global end pointer)
   - Rule 2: Split edge or create new leaf
   - Rule 3: Character already present → stop
4. **Update active point** via suffix links

### Suffix Link Invariant

After splitting at node `u`:
- If a previous split created node `v`, set `v.suffix_link = u`
- The next extension starts at `u.suffix_link` (or root)

### Global End Trick

All leaves share a single `end` pointer that increments each phase. This handles Rule 1 (leaf extension) in O(1) total per phase.

### Complexity Proof

**Claim**: Ukkonen's algorithm runs in O(n) time.

**Proof sketch**:
- Each phase increments `end` once: O(n) total
- `remaining` increases by 1 each phase, decreases when Rule 2 or 3 applies
- Each Rule 2 creates a node: O(n) total
- Walking down is charged to suffix link jumps: each jump moves closer to root
- Total suffix link jumps: O(n)

Therefore: O(n) amortized per phase × n phases = O(n) total.

---

## 87.8 Generalized Suffix Tree

A generalized suffix tree stores multiple strings S₁, S₂, ..., Sₖ in one tree.

### Construction

1. Build suffix tree for S₁#
2. Insert S₂$ into the existing tree
3. Continue for all strings

Each leaf stores which string it belongs to. Each internal node tracks which strings appear in its subtree.

### Applications

| Problem | Solution | Time |
|---|---|---|
| Longest common substring of k strings | Deepest node with all k strings in subtree | O(n) |
| Longest common prefix | Deepest node with ≥2 strings | O(n) |
| Pattern matching across multiple texts | Single search | O(m) |
| Finding repeats shared by multiple strings | Internal nodes with multiple source strings | O(n) |

---

## 87.9 Suffix Tree vs Suffix Array

| Aspect | Suffix Tree | Suffix Array + LCP |
|---|---|---|
| Space | ~20n bytes (pointers) | ~5n bytes (integers) |
| Build time | O(n) | O(n log n) or O(n) |
| Cache performance | Poor (pointer chasing) | Excellent (sequential access) |
| Pattern match | O(m) | O(m log n) or O(m + log n) |
| Longest repeated | O(n) | O(n) |
| Implementation | Complex | Moderate |
| Practical use | Academic | Industry standard |

**Modern consensus**: Use suffix arrays + LCP in practice. Suffix trees are theoretically elegant but suffix arrays are faster on real hardware due to cache efficiency.

---

## 87.10 Exercises

### Conceptual Exercises

1. **Suffix tree size**: Prove that a suffix tree for a string of length n has exactly n+1 leaves and at most n internal nodes.

2. **Ukkonen's rules**: Explain why Rule 3 (character already present) allows early termination. Why doesn't this miss any suffixes?

3. **Suffix links**: Why are suffix links essential for O(n) construction? What would happen without them?

4. **Suffix tree vs trie**: How much space does compression save? Give an example where the savings are maximal.

5. **Generalized suffix tree**: How do you modify the construction to handle k strings? What changes in the terminator strategy?

### Programming Exercises

1. **Pattern matching count**: Modify the suffix array search to count all occurrences (not just check existence).

2. **Longest common substring**: Implement LCS of two strings using generalized suffix array + LCP.

3. **Suffix tree serialization**: Implement a method to serialize and deserialize a suffix tree.

4. **All repeats of length ≥ k**: Find all substrings of length ≥ k that appear at least twice.

5. **Burrows-Wheeler Transform**: Implement BWT construction using the suffix array. Verify it's reversible.

---

## 87.11 Interview Questions

### Conceptual Questions

1. **Q**: What is the difference between a suffix tree and a suffix array?
   **A**: A suffix tree is a compressed trie of all suffixes with O(n) nodes. A suffix array is a sorted array of suffix starting positions. The suffix array uses less space (~4n bytes vs ~20n bytes) and has better cache performance. The suffix tree supports O(m) pattern matching directly; the suffix array needs O(m log n) binary search (or O(m + log n) with LCP). In practice, suffix arrays are preferred.

2. **Q**: How would you find the longest repeated substring in a string?
   **A**: Two approaches: (1) Build suffix tree, find deepest internal node. (2) Build suffix array + LCP, find maximum in LCP array. The LCP array approach is simpler: `max(LCP)` gives the answer, and the corresponding suffixes give the positions.

3. **Q**: Explain Ukkonen's online construction. Why is it O(n)?
   **A**: Ukkonen's adds one character per phase. Each phase handles extensions using three rules. The key optimizations are: (1) leaves extend automatically via global end pointer, (2) suffix links allow jumping between extensions, (3) Rule 3 stops early. Each character is added to the tree exactly once (as part of an edge label), so total work is O(n).

4. **Q**: How do you handle the unique terminator in suffix trees?
   **A**: Append a character not in the alphabet (e.g., $). This ensures every suffix ends at a leaf (no suffix is a prefix of another). Without it, some suffixes would end at internal nodes, complicating the structure.

### Coding Questions

1. **Q**: Given two strings, find their longest common substring in O(n) time.
   **A**: Build generalized suffix array + LCP. Scan LCP array: find maximum LCP[i] where SA[i] and SA[i-1] come from different strings. That LCP value is the LCS length; the corresponding suffix gives the substring.

2. **Q**: Count distinct substrings of a string.
   **A**: Build suffix array + LCP. Answer = n(n+1)/2 - sum(LCP). Each suffix contributes n-SA[i] substrings, but LCP[i] of those are duplicates of the previous suffix.

3. **Q**: Find all occurrences of a pattern in O(m + k) time where k is the number of occurrences.
   **A**: Build suffix array + LCP. Binary search for the pattern's range in O(m log n). All occurrences are at SA[lo..hi]. With LCP-based binary search, this becomes O(m + log n + k).

---

## 87.12 Cross-References

- **Chapter 30: Tries** — The uncompressed trie that suffix trees compress
- **Chapter 86: Suffix Arrays** — The practical alternative to suffix trees
- **Chapter 88: Pattern Matching** — Algorithms that suffix trees accelerate
- **Chapter 87: Suffix Tree** — This chapter
- **Chapter 158: Succinct Data Structures** — FM-Index uses BWT derived from suffix arrays
- **Chapter 163: Advanced Mathematics** — Combinatorics of string structures
- **Chapter 42: Binary Search** — Used in suffix array pattern matching

---

## Summary

| Structure | Build Time | Space | Pattern Match | Longest Repeated | Distinct Substrings |
|---|---|---|---|---|---|
| Suffix Tree | O(n) | O(n) ~20n bytes | O(m) | O(n) | O(n) |
| Suffix Array | O(n log n) | O(n) ~4n bytes | O(m log n) | O(n) | O(n) |
| Suffix Array + LCP | O(n log n) | O(n) ~5n bytes | O(m + log n) | O(n) | O(n) |

**Key Takeaway**: Suffix trees are theoretically optimal for string problems but complex to implement. Suffix arrays with LCP arrays provide nearly the same functionality with simpler code and better practical performance. For interviews, know both but implement suffix arrays. The core insight is that all suffixes of a string encode all substrings, and sorting/compressing them enables powerful queries.
