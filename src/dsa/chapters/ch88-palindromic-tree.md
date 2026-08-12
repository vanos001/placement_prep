# Chapter 88: Palindromic Tree (Eertree)

## Prerequisites

- String basics and substring concepts
- Trie data structure (Chapter 67)
- Suffix links and automata concepts
- Basic graph traversal

## Interview Frequency: ★★

The Palindromic Tree (also called **Eertree**) is a specialized data structure that efficiently stores and queries all distinct palindromic substrings of a string. It appears in **Google**, **Meta**, and competitive programming interviews, especially for advanced string problems.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Structure & construction | ★★ | Hard | Two root nodes, suffix links |
| Counting distinct palindromes | ★★ | Medium | Direct query after build |
| Longest palindromic suffix | ★★ | Medium | Tracked via `last` pointer |
| Palindrome frequency counting | ★★ | Medium | Propagate counts via links |
| Applications | ★★ | Hard | Substring queries, pattern matching |

---

## 88.1 What Is a Palindromic Tree?

A **Palindromic Tree** (Eertree) is a directed graph that stores every distinct palindromic substring of a given string in a compact, tree-like structure. Unlike a suffix tree or suffix array, it focuses exclusively on palindromes.

### Key Properties

1. **Each node** represents a distinct palindromic substring.
2. **Two root nodes**: one for "imaginary" odd-length palindromes (length -1) and one for even-length palindromes (length 0).
3. **Edges** are labeled with characters. Following a path from a root builds a palindrome.
4. **Suffix links** from each node point to the longest proper palindromic suffix — analogous to failure links in Aho-Corasick.
5. The tree has at most **n + 2** nodes for a string of length n (since there are at most n distinct palindromic substrings).

---

## 88.2 Motivation

### The Problem

Given a string, answer questions like:
- How many **distinct** palindromic substrings does it contain?
- What is the **longest** palindromic substring?
- How many times does each palindrome occur?
- What is the **k-th** lexicographically smallest palindrome?

### Brute Force Approach

Enumerate all O(n²) substrings and check each for being a palindrome — O(n³) total. Even with Manacher's algorithm (Chapter 87) to find all palindromes in O(n²), organizing and querying them is expensive.

### The Eertree Advantage

The Palindromic Tree answers all the above queries in **O(n)** total construction time and **O(1)** per query after building. It achieves this by exploiting the fact that adding one character to a string creates at most one new distinct palindromic suffix.

---

## 88.3 Intuition

### The Core Insight

When we append a character `c` to a string, the only new palindromes that appear are palindromic suffixes ending at the new position. Among these, **at most one** is a new distinct palindrome.

This is because if `c` creates two new palindromic suffixes, the shorter one must already exist (it's a suffix of the longer one, which was already present before adding `c`).

### Building Incrementally

We process the string character by character:
1. Start with two empty roots.
2. For each new character, find the longest palindromic suffix that can be extended.
3. If the extended palindrome already exists, move to it.
4. Otherwise, create a new node and set its suffix link.

### Analogy to Trie

Think of it as a trie where:
- Each path from root spells a palindrome.
- But instead of a standard trie with 26 children per node, we use suffix links to efficiently find the right node to extend.

---

## 88.4 Formal Structure

### Node Definition

Each node stores:
- `len`: length of the palindrome it represents
- `suffixLink`: pointer to the longest proper palindromic suffix
- `next[c]`: transition edges (child nodes by character)
- `count`: number of occurrences of this palindrome in the string

### Two Roots

- **Node 0** (odd root): `len = -1`. This is a sentinel that simplifies boundary conditions. Its suffix link points to itself.
- **Node 1** (even root): `len = 0`. Represents the empty string palindrome. Its suffix link points to node 0.

### Suffix Link Chain

For any node representing palindrome P:
- `suffixLink(P)` = the longest proper palindromic suffix of P.
- Following suffix links repeatedly gives all palindromic suffixes of P in decreasing length order.
- The chain always terminates at the even root (node 1) or odd root (node 0).

---

## 88.5 Step-by-Step Construction

### Algorithm: `addChar(c)`

```
1. Let pos = current position in string
2. Let curr = last (node of longest palindromic suffix so far)
3. Walk suffix links from curr until we find a node where
   s[pos - node.len - 1] == c (i.e., we can extend this palindrome)
4. If the extended palindrome already exists via next[c]:
   - Set last = next[c], increment count, return
5. Otherwise, create a new node:
   - len = curr.len + 2
   - Set next[c] = new node
6. Set suffix link of new node:
   - If len == 1: suffixLink = even root (node 1)
   - Else: walk suffix links from curr's suffix link until we find
     a node that can be extended by c; set suffixLink to that node's next[c]
7. Set last = new node, count = 1
```

### Why Amortized O(1)?

Each character addition involves walking suffix links. However, the total number of suffix link traversals across the entire construction is O(n), because each traversal moves to a strictly shorter palindrome, and we can use a similar argument to the KMP failure function analysis.

---

## 88.6 Dry Run: Building Eertree for "abacaba"

Let's trace through building the palindromic tree for the string `s = "abacaba"`.

**Initial state:**
- Node 0: len=-1 (odd root), suffixLink=0
- Node 1: len=0 (even root), suffixLink=0
- last = 1 (even root)
- String buffer: "$" (sentinel)

**Step 1: Add 'a' (position 1)**
- curr = 1 (len=0). Check s[1-0-1] = s[0] = '$' ≠ 'a'. Walk to suffixLink: curr = 0 (len=-1).
- Check s[1-(-1)-1] = s[1] = 'a' == 'a' ✓
- No existing next['a'] from node 0. Create node 2: len = -1+2 = 1.
- Since len==1, suffixLink = 1 (even root).
- last = 2, count = 1.
- **Node 2**: "a"

**Step 2: Add 'b' (position 2)**
- curr = 2 (len=1). Check s[2-1-1] = s[0] = '$' ≠ 'b'. Walk to suffixLink: curr = 1 (len=0).
- Check s[2-0-1] = s[1] = 'a' ≠ 'b'. Walk to suffixLink: curr = 0 (len=-1).
- Check s[2-(-1)-1] = s[2] = 'b' == 'b' ✓
- Create node 3: len = -1+2 = 1. suffixLink = 1.
- last = 3, count = 1.
- **Node 3**: "b"

**Step 3: Add 'a' (position 3)**
- curr = 3 (len=1). Check s[3-1-1] = s[1] = 'a' == 'a' ✓
- No existing next['a'] from node 3. Create node 4: len = 1+2 = 3.
- For suffix link: walk from suffixLink of node 3 (= node 1, len=0). Check s[3-0-1] = s[2] = 'b' ≠ 'a'. Walk to node 0 (len=-1). Check s[3-(-1)-1] = s[3] = 'a' == 'a' ✓. suffixLink = node 0's next['a'] = node 2.
- last = 4, count = 1.
- **Node 4**: "aba" (suffixLink → node 2: "a")

**Step 4: Add 'c' (position 4)**
- curr = 4 (len=3). Check s[4-3-1] = s[0] = '$' ≠ 'c'. Walk to suffixLink: curr = 2 (len=1).
- Check s[4-1-1] = s[2] = 'b' ≠ 'c'. Walk to suffixLink: curr = 1 (len=0).
- Check s[4-0-1] = s[3] = 'a' ≠ 'c'. Walk to suffixLink: curr = 0 (len=-1).
- Check s[4-(-1)-1] = s[4] = 'c' == 'c' ✓
- Create node 5: len = -1+2 = 1. suffixLink = 1.
- last = 5, count = 1.
- **Node 5**: "c"

**Step 5: Add 'a' (position 5)**
- curr = 5 (len=1). Check s[5-1-1] = s[3] = 'a' == 'a' ✓
- No existing next['a'] from node 5. Create node 6: len = 1+2 = 3.
- For suffix link: walk from suffixLink of node 5 (= node 1). Check s[5-0-1] = s[4] = 'c' ≠ 'a'. Walk to node 0. Check s[5-(-1)-1] = s[5] = 'a' == 'a' ✓. suffixLink = node 0's next['a'] = node 2.
- last = 6, count = 1.
- **Node 6**: "aca" (suffixLink → node 2: "a")

**Step 6: Add 'b' (position 6)**
- curr = 6 (len=3). Check s[6-3-1] = s[2] = 'b' == 'b' ✓
- No existing next['b'] from node 6. Create node 7: len = 3+2 = 5.
- For suffix link: walk from suffixLink of node 6 (= node 2, len=1). Check s[6-1-1] = s[4] = 'c' ≠ 'b'. Walk to suffixLink: curr = 1 (len=0). Check s[6-0-1] = s[5] = 'a' ≠ 'b'. Walk to node 0 (len=-1). Check s[6-(-1)-1] = s[6] = 'b' == 'b' ✓. suffixLink = node 0's next['b'] = node 3.
- last = 7, count = 1.
- **Node 7**: "bacab" (suffixLink → node 3: "b")

**Step 7: Add 'a' (position 7)**
- curr = 7 (len=5). Check s[7-5-1] = s[1] = 'a' == 'a' ✓
- No existing next['a'] from node 7. Create node 8: len = 5+2 = 7.
- For suffix link: walk from suffixLink of node 7 (= node 3, len=1). Check s[7-1-1] = s[5] = 'a' == 'a' ✓. suffixLink = node 3's next['a'] = node 4.
- last = 8, count = 1.
- **Node 8**: "abacaba" (suffixLink → node 4: "aba")

**Final tree — 8 nodes (excluding roots, 8 distinct palindromes):**
- "a" (node 2), "b" (node 3), "aba" (node 4), "c" (node 5)
- "aca" (node 6), "bacab" (node 7), "abacaba" (node 8)

Wait — that's 7 distinct palindromes (plus the empty string at node 1). Let me recount: nodes 2-8 = 7 nodes. The empty string palindrome is at node 1. So `distinctPalindromes() = 8 - 2 = 6`? No, nodes 2 through 8 are 7 nodes, minus 2 roots = 7 distinct non-empty palindromes. The answer is **7**.

**Suffix link tree:**
```
Node 0 (odd root, len=-1)
├── Node 1 (even root, len=0) ──suffixLink──→ Node 0
│   ├── Node 2 ("a", len=1) ──suffixLink──→ Node 1
│   ├── Node 3 ("b", len=1) ──suffixLink──→ Node 1
│   ├── Node 5 ("c", len=1) ──suffixLink──→ Node 1
│   └── Node 4 ("aba", len=3) ──suffixLink──→ Node 2
│       └── Node 7 ("bacab", len=5) ──suffixLink──→ Node 3
│           └── Node 8 ("abacaba", len=7) ──suffixLink──→ Node 4
│       └── Node 6 ("aca", len=3) ──suffixLink──→ Node 2
```

---

## 88.7 Complete Implementation

### C++ Implementation

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <map>

class PalindromicTree {
    struct Node {
        int len;                // Length of the palindrome
        int suffixLink;         // Longest proper palindromic suffix
        std::map<char, int> next; // Edges to children
        int count;              // Number of occurrences
        Node(int l) : len(l), suffixLink(0), count(0) {}
    };

    std::vector<Node> tree;
    std::string s;
    int last; // Node of the longest suffix-palindrome

public:
    PalindromicTree() {
        // Node 0: odd root (len = -1)
        tree.push_back(Node(-1));
        // Node 1: even root (len = 0)
        tree.push_back(Node(0));
        tree[0].suffixLink = 0;
        tree[1].suffixLink = 0;
        last = 1;
        s = "$"; // Sentinel character at position 0
    }

    void addChar(char c) {
        s += c;
        int pos = (int)s.size() - 1;
        int curr = last;

        // Step 1: Find the longest palindromic suffix that can be extended
        while (true) {
            int curLen = tree[curr].len;
            if (pos - curLen - 1 >= 0 && s[pos - curLen - 1] == c)
                break;
            curr = tree[curr].suffixLink;
        }

        // Step 2: Check if this palindrome already exists
        if (tree[curr].next.count(c)) {
            last = tree[curr].next[c];
            tree[last].count++;
            return;
        }

        // Step 3: Create a new node
        int newNode = (int)tree.size();
        tree.push_back(Node(tree[curr].len + 2));
        tree[curr].next[c] = newNode;

        // Step 4: Set suffix link for the new node
        if (tree[newNode].len == 1) {
            // Single character palindrome links to even root
            tree[newNode].suffixLink = 1;
        } else {
            int link = tree[curr].suffixLink;
            while (true) {
                int linkLen = tree[link].len;
                if (pos - linkLen - 1 >= 0 && s[pos - linkLen - 1] == c)
                    break;
                link = tree[link].suffixLink;
            }
            tree[newNode].suffixLink = tree[link].next[c];
        }

        last = newNode;
        tree[last].count = 1;
    }

    // Build the tree for an entire string
    void build(const std::string& str) {
        for (char c : str) addChar(c);
    }

    // Number of distinct palindromic substrings
    int distinctPalindromes() const {
        return (int)tree.size() - 2; // Exclude two roots
    }

    // Length of the longest palindromic suffix
    int longestPalindromeLength() const {
        return tree[last].len;
    }

    // Get occurrence counts (propagate via suffix links)
    std::vector<long long> getFrequency() {
        int n = (int)tree.size();
        std::vector<long long> freq(n);
        for (int i = 0; i < n; i++) freq[i] = tree[i].count;

        // Process nodes in decreasing length order
        // (larger index doesn't guarantee larger length, so sort)
        std::vector<int> order(n);
        for (int i = 0; i < n; i++) order[i] = i;
        std::sort(order.begin(), order.end(), [&](int a, int b) {
            return tree[a].len > tree[b].len;
        });

        for (int i : order) {
            if (tree[i].suffixLink >= 0)
                freq[tree[i].suffixLink] += freq[i];
        }
        return freq;
    }
};

int main() {
    PalindromicTree pt;
    std::string s = "abacaba";
    pt.build(s);

    std::cout << "String: \"" << s << "\"\n";
    std::cout << "Distinct palindromes: " << pt.distinctPalindromes() << "\n";
    std::cout << "Longest palindrome length: " << pt.longestPalindromeLength() << "\n";

    return 0;
}
```

### Python Implementation

```python
class PalindromicTree:
    def __init__(self):
        self.tree = [
            {"len": -1, "suffix_link": 0, "next": {}, "count": 0},  # Node 0: odd root
            {"len": 0, "suffix_link": 0, "next": {}, "count": 0},   # Node 1: even root
        ]
        self.s = "$"  # Sentinel
        self.last = 1

    def add_char(self, c: str) -> None:
        self.s += c
        pos = len(self.s) - 1
        curr = self.last

        # Find longest palindromic suffix that can be extended
        while True:
            cur_len = self.tree[curr]["len"]
            if pos - cur_len - 1 >= 0 and self.s[pos - cur_len - 1] == c:
                break
            curr = self.tree[curr]["suffix_link"]

        # Check if palindrome already exists
        if c in self.tree[curr]["next"]:
            self.last = self.tree[curr]["next"][c]
            self.tree[self.last]["count"] += 1
            return

        # Create new node
        new_node = len(self.tree)
        self.tree.append({
            "len": self.tree[curr]["len"] + 2,
            "suffix_link": 0,
            "next": {},
            "count": 0,
        })
        self.tree[curr]["next"][c] = new_node

        # Set suffix link
        if self.tree[new_node]["len"] == 1:
            self.tree[new_node]["suffix_link"] = 1
        else:
            link = self.tree[curr]["suffix_link"]
            while True:
                link_len = self.tree[link]["len"]
                if pos - link_len - 1 >= 0 and self.s[pos - link_len - 1] == c:
                    break
                link = self.tree[link]["suffix_link"]
            self.tree[new_node]["suffix_link"] = self.tree[link]["next"][c]

        self.last = new_node
        self.tree[self.last]["count"] = 1

    def build(self, s: str) -> None:
        for c in s:
            self.add_char(c)

    def distinct_palindromes(self) -> int:
        return len(self.tree) - 2

    def longest_palindrome_length(self) -> int:
        return self.tree[self.last]["len"]

    def get_frequency(self) -> dict:
        """Return {palindrome: occurrence_count} after building."""
        n = len(self.tree)
        order = sorted(range(n), key=lambda i: -self.tree[i]["len"])
        freq = [self.tree[i]["count"] for i in range(n)]
        for i in order:
            sl = self.tree[i]["suffix_link"]
            freq[sl] += freq[i]
        # Reconstruct palindromes from the tree
        result = {}
        self._collect(0, "", result)
        self._collect(1, "", result)
        return result

    def _collect(self, node: int, path: str, result: dict) -> None:
        if node >= 2:  # Skip roots
            result[path] = self.tree[node]["count"]
        for c, child in self.tree[node]["next"].items():
            # For odd root (len=-1), the character is the full palindrome
            # For even root (len=0), the character is the full palindrome
            # For others, build from center outward
            if self.tree[node]["len"] <= 0:
                self._collect(child, c, result)
            else:
                self._collect(child, c + path + c, result)


if __name__ == "__main__":
    pt = PalindromicTree()
    s = "abacaba"
    pt.build(s)
    print(f"String: '{s}'")
    print(f"Distinct palindromes: {pt.distinct_palindromes()}")
    print(f"Longest palindrome length: {pt.longest_palindrome_length()}")
```

### Java Implementation

```java
import java.util.*;

public class PalindromicTree {
    static class Node {
        int len;
        int suffixLink;
        Map<Character, Integer> next;
        int count;

        Node(int len) {
            this.len = len;
            this.suffixLink = 0;
            this.next = new HashMap<>();
            this.count = 0;
        }
    }

    private List<Node> tree;
    private StringBuilder s;
    private int last;

    public PalindromicTree() {
        tree = new ArrayList<>();
        tree.add(new Node(-1)); // Node 0: odd root
        tree.add(new Node(0));  // Node 1: even root
        tree.get(0).suffixLink = 0;
        tree.get(1).suffixLink = 0;
        last = 1;
        s = new StringBuilder("$");
    }

    public void addChar(char c) {
        s.append(c);
        int pos = s.length() - 1;
        int curr = last;

        // Find longest palindromic suffix that can be extended
        while (true) {
            int curLen = tree.get(curr).len;
            if (pos - curLen - 1 >= 0 && s.charAt(pos - curLen - 1) == c)
                break;
            curr = tree.get(curr).suffixLink;
        }

        // Check if palindrome already exists
        if (tree.get(curr).next.containsKey(c)) {
            last = tree.get(curr).next.get(c);
            tree.get(last).count++;
            return;
        }

        // Create new node
        int newNode = tree.size();
        tree.add(new Node(tree.get(curr).len + 2));
        tree.get(curr).next.put(c, newNode);

        // Set suffix link
        if (tree.get(newNode).len == 1) {
            tree.get(newNode).suffixLink = 1;
        } else {
            int link = tree.get(curr).suffixLink;
            while (true) {
                int linkLen = tree.get(link).len;
                if (pos - linkLen - 1 >= 0 && s.charAt(pos - linkLen - 1) == c)
                    break;
                link = tree.get(link).suffixLink;
            }
            tree.get(newNode).suffixLink = tree.get(link).next.get(c);
        }

        last = newNode;
        tree.get(last).count = 1;
    }

    public void build(String str) {
        for (char c : str.toCharArray()) {
            addChar(c);
        }
    }

    public int distinctPalindromes() {
        return tree.size() - 2;
    }

    public int longestPalindromeLength() {
        return tree.get(last).len;
    }

    public static void main(String[] args) {
        PalindromicTree pt = new PalindromicTree();
        String s = "abacaba";
        pt.build(s);
        System.out.println("String: \"" + s + "\"");
        System.out.println("Distinct palindromes: " + pt.distinctPalindromes());
        System.out.println("Longest palindrome length: " + pt.longestPalindromeLength());
    }
}
```

---

## 88.8 Complexity Analysis

| Operation | Time | Space | Notes |
|---|---|---|---|
| Add one character | **O(1)** amortized | O(1) | Amortized via suffix link analysis |
| Build for string of length n | **O(n)** | O(n) | At most n+2 nodes created |
| Count distinct palindromes | **O(1)** | — | `tree.size() - 2` |
| Longest palindrome | **O(1)** | — | `tree[last].len` |
| Get all frequencies | **O(n)** | O(n) | Propagate counts via suffix links |
| Total space | — | **O(n)** | At most n+2 nodes, each with O(1) amortized edges |

### Why O(n) Total Nodes?

A string of length n has at most n distinct palindromic substrings. This is because each new character creates at most one new distinct palindrome. The proof:

Suppose adding character `s[i]` creates two new palindromes P₁ and P₂ where |P₁| < |P₂|. Then P₁ is a suffix of P₂. But P₂ is new, so it couldn't have appeared before. However, P₁ is a proper suffix of P₂, and P₂'s prefix (same as suffix) already matched before position i. This means P₁ must have already existed — contradiction.

### Amortized O(1) per Character

The suffix link walk in `addChar` traverses at most O(n) links total across all n calls. This is because each traversal moves to a strictly shorter palindrome, and we never "re-climb" the same links. The argument mirrors the KMP failure function amortization.

---

## 88.9 Applications

### 1. Count Distinct Palindromic Substrings

Direct query: `distinctPalindromes()` returns the count in O(1) after building.

### 2. Longest Palindromic Substring

Direct query: `longestPalindromeLength()` returns the length in O(1). To get the actual substring, track the ending position when creating nodes.

### 3. Palindrome Frequency

After building, propagate counts through suffix links (in decreasing length order) to get the number of occurrences of each palindrome.

### 4. Number of Palindromic Substrings (Including Duplicates)

Sum all propagated frequencies. This counts every occurrence, not just distinct palindromes.

### 5. k-th Palindrome

Enumerate palindromes in lexicographic order by traversing the tree and collecting characters along paths.

---

## 88.10 Comparison with Other Palindrome Algorithms

| Algorithm | What It Finds | Time | Space |
|---|---|---|---|
| **Manacher's** | All palindromic substrings centered at each position | O(n) | O(n) |
| **Palindromic Tree** | All distinct palindromic substrings with counts | O(n) | O(n) |
| **Suffix Array + LCP** | Can find palindromes indirectly | O(n log n) | O(n) |
| **Brute Force** | Check each substring | O(n³) | O(1) |

**When to use Palindromic Tree over Manacher's:**
- When you need **distinct** palindromes, not just positions
- When you need **frequency counts**
- When you need to answer queries about palindromes online (character by character)

---

## 88.11 Common Pitfalls

1. **Forgetting the sentinel**: The `$` at position 0 prevents out-of-bounds access when checking `s[pos - len - 1]`.

2. **Suffix link for single-character palindromes**: These always link to the even root (node 1), not the odd root.

3. **Not propagating counts**: The raw `count` field only counts how many times a palindrome was the **longest suffix-palindrome** at some position. To get total occurrences, propagate via suffix links.

4. **Using array instead of map for edges**: If the alphabet is large (e.g., Unicode), use a hash map. For small alphabets (lowercase letters), a 26-element array is faster.

5. **Off-by-one in position tracking**: The sentinel shifts all positions by 1. Be careful with index arithmetic.

---

## 88.12 Exercises

### Exercise 1: Count Palindromic Substrings (Including Duplicates)
Modify the Eertree to count the **total** number of palindromic substrings (not just distinct). Hint: sum all propagated frequencies.

### Exercise 2: Longest Palindromic Substring Value
Extend the implementation to return the actual longest palindromic substring (not just its length). Hint: store the ending position in each node.

### Exercise 3: Palindromic Substrings in a Range
Given a string and q queries [l, r], count distinct palindromes in the substring s[l..r]. Hint: build the Eertree incrementally and use persistent data structures.

### Exercise 4: Lexicographic k-th Smallest Palindrome
After building the Eertree, support queries: "What is the k-th smallest distinct palindrome?" Hint: DFS the tree in lexicographic order.

### Exercise 5: Online Palindrome Detection
Modify the Eertree to support an `isPalindrome(substring)` query in O(1) after O(n) preprocessing. Hint: hash each node's palindrome.

---

## 88.13 Interview Questions

### Q1: How many distinct palindromic substrings does a string of length n have?
**Answer**: At most n. Each new character creates at most one new distinct palindrome.

### Q2: What is the time complexity of building a Palindromic Tree?
**Answer**: O(n) for a string of length n. Each character is processed in amortized O(1) time.

### Q3: How does the suffix link work in a Palindromic Tree?
**Answer**: It points to the longest proper palindromic suffix of the current palindrome. This allows efficient traversal when extending palindromes, similar to KMP failure links.

### Q4: Compare Palindromic Tree with Manacher's algorithm.
**Answer**: Manacher's finds all palindromic substrings (by center) in O(n). The Palindromic Tree stores distinct palindromes with frequency counts and supports online construction. Use Manacher's for "find longest palindrome" and Eertree for "count distinct palindromes" or frequency queries.

### Q5: Why does the odd root have length -1?
**Answer**: It serves as a sentinel. When we check `s[pos - (-1) - 1] = s[pos]`, this allows single-character palindromes to be created uniformly through the same extension logic, without special cases.

### Q6: How would you handle Unicode or large alphabets?
**Answer**: Replace the fixed-size array `next[26]` with a hash map (`map<char, int>` or `unordered_map`). The time complexity remains O(n) amortized, though the constant factor increases.

---

## 88.14 Cross-References

- **Chapter 87: Manacher's Algorithm** — An alternative approach to finding all palindromic substrings in O(n).
- **Chapter 67: Trie** — The Palindromic Tree generalizes the trie concept with suffix links.
- **Chapter 38: KMP Algorithm** — The suffix link mechanism is analogous to KMP's failure function.
- **Chapter 68: Aho-Corasick** — Another automaton with failure links for multi-pattern matching.
- **Chapter 30: DP Fundamentals** — Understanding state transitions helps with the incremental construction.
- **Chapter 65: Suffix Array** — Another approach to substring queries, though not specialized for palindromes.

---

## Summary

| Aspect | Detail |
|---|---|
| Data structure | Directed graph with two roots and suffix links |
| Nodes | Each represents a distinct palindromic substring |
| Construction time | O(n) amortized for string of length n |
| Space | O(n) — at most n + 2 nodes |
| Key operation | `addChar`: extend tree by one character |
| Suffix links | Point to longest proper palindromic suffix |
| Applications | Count distinct palindromes, frequency, longest palindrome |
| Compared to Manacher's | Better for distinct counting and online queries |
