# Chapter 46: Aho-Corasick Algorithm

## 46.1 Trie + Failure Links

The **Aho-Corasick algorithm** is a multi-pattern string matching algorithm. Given a set of patterns and a text, it finds all occurrences of all patterns in the text in a single pass. It is essentially a generalization of the KMP algorithm to multiple patterns.

### The Trie Foundation

A **trie** (prefix tree) is a tree-like data structure where each node represents a prefix of one or more patterns. Each edge is labeled with a character.

For patterns `{"he", "she", "his", "hers"}`:

```
        root
       / | \
      h  s  ...
     / \  \
    e   i   h
    |   |   |
   [✓] [✓]  e
    |       |
   r       [✓]
    |
   s
    |
   [✓]
```

Nodes marked `[✓]` are **output nodes** — they indicate the end of a pattern.

### The Problem with Tries Alone

A simple trie can match one pattern at a time: follow the trie character by character. If we reach a pattern node, we found a match. But this requires restarting from the root for each position in the text — O(n × m) in the worst case.

### Failure Links: The Key Insight

A **failure link** from node `v` points to the longest proper suffix of the string represented by `v` that is also a prefix of some pattern. This is exactly the KMP failure function, generalized to a trie.

When we can't follow a transition from the current node, instead of going back to the root, we follow the failure link. This way, we never "restart" — we slide along the text continuously.

### Dictionary Suffix Links

A **dictionary suffix link** (also called **output link**) from node `v` points to the nearest ancestor in the failure link tree that is an output node. This allows us to efficiently report all patterns that end at the current position.

For example, if patterns are `{"he", "she", "hers"}`, and we're at the node for "hers", the dictionary suffix link would point to the node for "her" → "he" (if "he" is a pattern). This lets us report both "hers" and "he" when we find "hers" in the text.

---

## 46.2 Building the Automaton

### Step 1: Build the Trie

Insert all patterns into a trie. Each node stores:
- `next[c]`: the child node for character `c`
- `link`: the failure link
- `dictLink`: the dictionary suffix link (nearest output ancestor via failure links)
- `output`: whether this node is the end of a pattern
- `patternIdx`: index of the pattern ending here (for reporting)

### Step 2: Compute Failure Links via BFS

Process nodes in **BFS order** (level by level). For each node `v`:
1. For each character `c` with transition `v → u`:
   - Set `link[u]` = follow failure links from `link[v]` until finding a node with a `c` transition, or reaching root.
2. Set `dictLink[u]` = if `link[u]` is an output node, then `link[u]`; else `dictLink[link[u]]`.

### Step 3: Build "goto" transitions (optimization)

For missing transitions, pre-compute where to go. Instead of following failure links at query time, fill in the missing transitions so every node has a direct transition for every character. This makes each query step O(1).

### Complete Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

struct AhoCorasick {
    struct Node {
        int next[26];       // Trie transitions
        int link;           // Failure link
        int dictLink;       // Dictionary suffix link
        bool output;        // Is this node a pattern endpoint?
        int patternIdx;     // Which pattern ends here (-1 if none)
        int depth;          // Depth in trie (= length of prefix)

        Node() {
            fill(next, next + 26, -1);
            link = 0;
            dictLink = -1;
            output = false;
            patternIdx = -1;
            depth = 0;
        }
    };

    vector<Node> nodes;
    int size;

    AhoCorasick() {
        nodes.emplace_back(); // root = node 0
        size = 1;
    }

    // Insert a pattern into the trie
    void insert(const string& pattern, int idx) {
        int v = 0;
        for (char ch : pattern) {
            int c = ch - 'a';
            if (nodes[v].next[c] == -1) {
                nodes[v].next[c] = size;
                nodes.emplace_back();
                nodes[size].depth = nodes[v].depth + 1;
                size++;
            }
            v = nodes[v].next[c];
        }
        nodes[v].output = true;
        nodes[v].patternIdx = idx;
    }

    // Build failure links and dictionary suffix links via BFS
    void build() {
        queue<int> q;

        // Initialize: children of root have failure link to root
        for (int c = 0; c < 26; c++) {
            int u = nodes[0].next[c];
            if (u != -1) {
                nodes[u].link = 0;
                nodes[u].dictLink = -1;
                q.push(u);
            } else {
                nodes[0].next[c] = 0; // Missing transitions go to root
            }
        }

        // BFS to compute failure links
        while (!q.empty()) {
            int v = q.front(); q.pop();

            for (int c = 0; c < 26; c++) {
                int u = nodes[v].next[c];
                if (u != -1) {
                    // Compute failure link for u
                    nodes[u].link = nodes[nodes[v].link].next[c];

                    // Compute dictionary suffix link
                    if (nodes[nodes[u].link].output) {
                        nodes[u].dictLink = nodes[u].link;
                    } else {
                        nodes[u].dictLink = nodes[nodes[u].link].dictLink;
                    }

                    q.push(u);
                } else {
                    // Fill in missing transition (optimization)
                    nodes[v].next[c] = nodes[nodes[v].link].next[c];
                }
            }
        }
    }

    // Search text for all pattern occurrences
    // Returns: vector of (position_in_text, pattern_index) pairs
    vector<pair<int, int>> search(const string& text) {
        vector<pair<int, int>> matches;
        int v = 0;

        for (int i = 0; i < (int)text.size(); i++) {
            int c = text[i] - 'a';
            if (c < 0 || c >= 26) {
                v = 0; // Non-alphabetic character resets to root
                continue;
            }
            v = nodes[v].next[c]; // Direct transition (pre-computed)

            // Check current node and all dictionary suffix links
            int temp = v;
            while (temp != -1) {
                if (nodes[temp].output) {
                    matches.push_back({i, nodes[temp].patternIdx});
                }
                temp = nodes[temp].dictLink;
            }
        }

        return matches;
    }

    // Count occurrences of each pattern
    vector<int> countOccurrences(const string& text, int numPatterns) {
        vector<int> count(numPatterns, 0);
        auto matches = search(text);
        for (auto [pos, idx] : matches) {
            count[idx]++;
        }
        return count;
    }
};

int main() {
    AhoCorasick ac;

    vector<string> patterns = {"he", "she", "his", "hers"};
    for (int i = 0; i < (int)patterns.size(); i++) {
        ac.insert(patterns[i], i);
    }
    ac.build();

    string text = "ahishers";
    cout << "Text: " << text << "\n";
    cout << "Patterns: ";
    for (const string& p : patterns) cout << "\"" << p << "\" ";
    cout << "\n\n";

    auto matches = ac.search(text);
    cout << "Matches found:\n";
    for (auto [pos, idx] : matches) {
        int len = (int)patterns[idx].size();
        int start = pos - len + 1;
        cout << "  Pattern \"" << patterns[idx] << "\" at position "
             << start << " (\"" << text.substr(start, len) << "\")\n";
    }

    // Count occurrences
    auto counts = ac.countOccurrences(text, (int)patterns.size());
    cout << "\nOccurrence counts:\n";
    for (int i = 0; i < (int)patterns.size(); i++) {
        cout << "  \"" << patterns[i] << "\": " << counts[i] << "\n";
    }

    return 0;
}
```

### Dry Run

**Patterns**: `{"he", "she", "his", "hers"}`
**Text**: `"ahishers"`

**Trie Structure**:
```
Root (0)
├── 'h' → 1 (depth 1)
│   ├── 'e' → 2 (depth 2) [✓ "he"]
│   │   └── 'r' → 3 (depth 3)
│   │       └── 's' → 4 (depth 4) [✓ "hers"]
│   └── 'i' → 5 (depth 2)
│       └── 's' → 6 (depth 3) [✓ "his"]
└── 's' → 7 (depth 1)
    └── 'h' → 8 (depth 2)
        └── 'e' → 9 (depth 3) [✓ "she"]
```

**Failure Links** (computed via BFS):
- Node 1 (h): link → 0 (root)
- Node 2 (he): link → 0 (no proper suffix of "he" is a prefix of any pattern)
- Node 3 (her): link → 0
- Node 4 (hers): link → 0
- Node 5 (hi): link → 1 (suffix "h" is a prefix → node 1)
- Node 6 (his): link → 6? No... suffix "is" — not a prefix. Suffix "s" → not a prefix starting with any pattern start. → link → 0. Wait, let me reconsider. suffix "is" → not a prefix. suffix "s" → "s" starts "she"! So... node for "s" is node 7. So link[6] = 7.

Actually, let me recompute. The failure link for node 6 (representing "his"):
- Proper suffixes: "is", "s"
- "is": not a prefix of any pattern
- "s": IS a prefix (of "she" and starts at node 7)
- So link[6] = 7

For node 5 (representing "hi"):
- Proper suffixes: "i"
- "i": not a prefix of any pattern (no pattern starts with 'i')
- So link[5] = 0

For node 9 (representing "she"):
- Proper suffixes: "he", "e"
- "he": IS a pattern! Node 2. So link[9] = 2

**Search through "ahishers"**:
- i=0, char='a': v = nodes[0].next['a'] = 0 (no transition, stays root). No match.
- i=1, char='h': v = nodes[0].next['h'] = 1. No output.
- i=2, char='i': v = nodes[1].next['i'] = 5 ("hi"). No output.
- i=3, char='s': v = nodes[5].next['s'] = 6 ("his"). Output! Pattern 2 ("his") found at pos 3. Check dictLink: link[6]=7, nodes[7] not output → dictLink[6]=-1. Done.
- i=4, char='h': v = nodes[6].next['h']. Since we pre-computed: nodes[6].next['h'] = nodes[link[6]].next['h'] = nodes[7].next['h'] = 8. Node 8 ("sh"). No output.
- i=5, char='e': v = nodes[8].next['e'] = 9 ("she"). Output! Pattern 3 ("she") at pos 5. dictLink: link[9]=2, nodes[2] IS output (pattern "he")! So dictLink[9]=2. Report pattern 0 ("he") at pos 5 too.
- i=6, char='r': v = nodes[9].next['r'] = nodes[link[9]].next['r'] = nodes[2].next['r'] = 3 ("sher"). No output.
- i=7, char='s': v = nodes[3].next['s'] = 4 ("shers"). Output! Pattern 3 ("hers") at pos 7. dictLink: link[4]=0, nodes[0] not output → dictLink[4]=-1. Done.

**Matches**: (3, "his"), (5, "she"), (5, "he"), (7, "hers") ✓

### Python — Aho-Corasick Algorithm

```python
from collections import deque

class AhoCorasick:
    def __init__(self):
        self.nodes = [{'next': [-1] * 26, 'link': 0, 'dict_link': -1,
                        'output': False, 'pattern_idx': -1}]
        self.size = 1

    def insert(self, pattern, idx):
        v = 0
        for ch in pattern:
            c = ord(ch) - ord('a')
            if self.nodes[v]['next'][c] == -1:
                self.nodes[v]['next'][c] = self.size
                self.nodes.append({'next': [-1] * 26, 'link': 0,
                                   'dict_link': -1, 'output': False,
                                   'pattern_idx': -1})
                self.size += 1
            v = self.nodes[v]['next'][c]
        self.nodes[v]['output'] = True
        self.nodes[v]['pattern_idx'] = idx

    def build(self):
        q = deque()
        for c in range(26):
            u = self.nodes[0]['next'][c]
            if u != -1:
                self.nodes[u]['link'] = 0
                self.nodes[u]['dict_link'] = -1
                q.append(u)
            else:
                self.nodes[0]['next'][c] = 0

        while q:
            v = q.popleft()
            for c in range(26):
                u = self.nodes[v]['next'][c]
                if u != -1:
                    self.nodes[u]['link'] = self.nodes[self.nodes[v]['link']]['next'][c]
                    if self.nodes[self.nodes[u]['link']]['output']:
                        self.nodes[u]['dict_link'] = self.nodes[u]['link']
                    else:
                        self.nodes[u]['dict_link'] = self.nodes[self.nodes[u]['link']]['dict_link']
                    q.append(u)
                else:
                    self.nodes[v]['next'][c] = self.nodes[self.nodes[v]['link']]['next'][c]

    def search(self, text):
        matches = []
        v = 0
        for i, ch in enumerate(text):
            c = ord(ch) - ord('a')
            if c < 0 or c >= 26:
                v = 0
                continue
            v = self.nodes[v]['next'][c]
            temp = v
            while temp != -1:
                if self.nodes[temp]['output']:
                    matches.append((i, self.nodes[temp]['pattern_idx']))
                temp = self.nodes[temp]['dict_link']
        return matches


if __name__ == "__main__":
    ac = AhoCorasick()
    patterns = ["he", "she", "his", "hers"]
    for i, p in enumerate(patterns):
        ac.insert(p, i)
    ac.build()

    text = "ahishers"
    print(f"Text: {text}")
    print(f"Patterns: {' '.join(f'\"{p}\"' for p in patterns)}\n")

    matches = ac.search(text)
    print("Matches found:")
    for pos, idx in matches:
        start = pos - len(patterns[idx]) + 1
        print(f'  Pattern "{patterns[idx]}" at position {start} ("{text[start:pos+1]}")')
```

### Java — Aho-Corasick Algorithm

```java
import java.util.*;

public class AhoCorasick {
    static class Node {
        int[] next = new int[26];
        int link = 0, dictLink = -1;
        boolean output = false;
        int patternIdx = -1;
        Node() { Arrays.fill(next, -1); }
    }

    List<Node> nodes = new ArrayList<>();
    int size = 1;

    public AhoCorasick() {
        nodes.add(new Node());
    }

    public void insert(String pattern, int idx) {
        int v = 0;
        for (char ch : pattern.toCharArray()) {
            int c = ch - 'a';
            if (nodes.get(v).next[c] == -1) {
                nodes.get(v).next[c] = size;
                nodes.add(new Node());
                size++;
            }
            v = nodes.get(v).next[c];
        }
        nodes.get(v).output = true;
        nodes.get(v).patternIdx = idx;
    }

    public void build() {
        Queue<Integer> q = new ArrayDeque<>();
        for (int c = 0; c < 26; c++) {
            int u = nodes.get(0).next[c];
            if (u != -1) {
                nodes.get(u).link = 0;
                nodes.get(u).dictLink = -1;
                q.offer(u);
            } else {
                nodes.get(0).next[c] = 0;
            }
        }

        while (!q.isEmpty()) {
            int v = q.poll();
            for (int c = 0; c < 26; c++) {
                int u = nodes.get(v).next[c];
                if (u != -1) {
                    nodes.get(u).link = nodes.get(nodes.get(v).link).next[c];
                    if (nodes.get(nodes.get(u).link).output) {
                        nodes.get(u).dictLink = nodes.get(u).link;
                    } else {
                        nodes.get(u).dictLink = nodes.get(nodes.get(u).link).dictLink;
                    }
                    q.offer(u);
                } else {
                    nodes.get(v).next[c] = nodes.get(nodes.get(v).link).next[c];
                }
            }
        }
    }

    public List<int[]> search(String text) {
        List<int[]> matches = new ArrayList<>();
        int v = 0;
        for (int i = 0; i < text.length(); i++) {
            int c = text.charAt(i) - 'a';
            if (c < 0 \|\| c >= 26) { v = 0; continue; }
            v = nodes.get(v).next[c];
            int temp = v;
            while (temp != -1) {
                if (nodes.get(temp).output) {
                    matches.add(new int[]{i, nodes.get(temp).patternIdx});
                }
                temp = nodes.get(temp).dictLink;
            }
        }
        return matches;
    }

    public static void main(String[] args) {
        AhoCorasick ac = new AhoCorasick();
        String[] patterns = {"he", "she", "his", "hers"};
        for (int i = 0; i < patterns.length; i++) ac.insert(patterns[i], i);
        ac.build();

        String text = "ahishers";
        System.out.println("Text: " + text);
        System.out.print("Patterns: ");
        for (String p : patterns) System.out.print("\"" + p + "\" ");
        System.out.println("\n");

        List<int[]> matches = ac.search(text);
        System.out.println("Matches found:");
        for (int[] m : matches) {
            int pos = m[0], idx = m[1];
            int start = pos - patterns[idx].length() + 1;
            System.out.printf("  Pattern \"%s\" at position %d (\"%s\")%n",
                patterns[idx], start, text.substring(start, pos + 1));
        }
    }
}
```

---

## 46.3 Multi-Pattern Matching

### Complexity Analysis

| Phase                | Time         | Space        |
|---------------------|--------------|--------------|
| Trie construction   | O(Σ|p_i|)   | O(Σ|p_i| × |Σ|) |
| BFS (failure links) | O(Σ|p_i| × |Σ|) | O(Σ|p_i| × |Σ|) |
| Search              | O(n + z)     | O(Σ|p_i|)   |

Where:
- `n` = text length
- `m` = total length of all patterns (Σ|p_i|)
- `z` = number of matches
- `|Σ|` = alphabet size (26 for lowercase English)

**Total**: O(n + m + z) time, O(m × |Σ|) space.

### Why Aho-Corasick Is Optimal

The algorithm processes each character of the text exactly once (after pre-computing transitions). The failure links ensure we never backtrack. The dictionary suffix links ensure we report all matches efficiently.

The key insight is that the automaton maintains a **single state** as it scans the text. At each character, it follows exactly one transition (O(1) with pre-computed goto table). This is fundamentally different from running KMP independently for each pattern — Aho-Corasick merges all KMP automata into one.

### Formal Proof of O(n + m + z) Bound

Let `m = Σ|p_i|` be the total length of all patterns.

**Trie construction**: Each character of each pattern is inserted once. Each insertion traverses or creates one node. Total: O(m).

**BFS for failure links**: Each node is processed once. For each node, we examine at most |Σ| transitions. Total: O(m × |Σ|). With the goto optimization, this also fills in missing transitions.

**Search**: Each character of the text causes exactly one transition (O(1) with goto table). For each match found, we follow dictionary suffix links. The total number of dictionary suffix link traversals across the entire search is O(z) because each traversal reports one match. Total: O(n + z).

**Combined**: O(m × |Σ|) preprocessing + O(n + z) search. For fixed alphabet size |Σ| = O(1), this simplifies to O(n + m + z).

### Comparison with Other Approaches

| Approach                  | Time            | Notes                              |
|--------------------------|-----------------|------------------------------------|
| Naive (search each)      | O(n × m)        | Search each pattern independently  |
| KMP for each pattern     | O(n × k)        | k patterns, each in O(n)           |
| Aho-Corasick             | O(n + m + z)    | Single pass over text              |
| Suffix automaton         | O(n + m)        | Build SA, query each pattern       |

Aho-Corasick wins when you have many patterns to search simultaneously.

### Applications

1. **Intrusion detection systems (IDS)**: Network intrusion detection systems like Snort use Aho-Corasick to match incoming packets against thousands of known attack signatures simultaneously. The linear-time scanning ensures the IDS can keep up with high-speed network traffic without becoming a bottleneck.

2. **Plagiarism detection**: Tools like Turnitin maintain databases of known phrases and sentence fragments from published works. Aho-Corasick scans student submissions against these databases in a single pass, flagging potential plagiarism in real time even with millions of patterns.

3. **Bioinformatics**: DNA and protein sequence databases contain millions of known sequences. Researchers use Aho-Corasick to scan new genome sequences against these databases to identify genes, regulatory elements, and evolutionary relationships.

4. **Content filtering and moderation**: Platforms use Aho-Corasick to detect banned words, slurs, or policy-violating phrases in user-generated content. The algorithm's efficiency makes it suitable for real-time filtering at scale.

5. **Search engines**: Some search engines use Aho-Corasick for 'did you mean' suggestions or for matching query terms against a dictionary of known terms in a single pass.

6. **Competitive programming**: Multi-pattern matching problems appear frequently in contests. Problems like 'find all occurrences of any pattern from set P in text T' are classic Aho-Corasick applications.

### Advanced: Aho-Corasick with Output Propagation

When patterns can be substrings of each other (e.g., "he" and "she"), the dictionary suffix links handle this. But sometimes you need to propagate outputs along the failure link tree.

```cpp
// After building, propagate outputs
void propagateOutputs() {
    // Topological order of failure link tree (BFS order works)
    // If a node's failure link is an output, mark it too
    // Or use the dictionary suffix link chain to report all matches
}
```

The dictionary suffix link approach is cleaner and more efficient for reporting.

---

## Interview Tips

1. **Start with the trie.** Explain that a trie alone can match one pattern at a time. Then introduce failure links as the "KMP generalization."

2. **Failure links are BFS-computed.** This is the key insight: process nodes level by level, so when computing failure link for node `u`, the failure link for its parent `v` is already known.

3. **The "goto" optimization.** Pre-computing missing transitions makes the search loop trivial: just `v = next[v][c]` for each character. No while loops needed at query time.

4. **Know the complexity.** O(n + m + z) is the answer. If the interviewer asks about the alphabet size factor, explain the pre-computed transitions.

5. **Dictionary suffix links vs. checking all ancestors.** Without dictionary suffix links, you'd need to follow the failure link chain for every position — O(n × depth) worst case. Dictionary suffix links skip non-output ancestors.

## Common Mistakes

1. **Not handling missing transitions at root.** If root has no transition for character `c`, it should point back to root (not stay undefined).

2. **Computing failure links in DFS order.** BFS is required because the failure link for a node depends on its parent's failure link, which must already be computed.

3. **Forgetting dictionary suffix links.** Without them, you miss patterns that are suffixes of other matched patterns.

4. **Not resetting to root on non-alphabetic characters.** If the text contains characters not in the alphabet, reset to root.

5. **Off-by-one in position reporting.** When reporting a match at position `i` for a pattern of length `L`, the match starts at position `i - L + 1`.

## Practice Problems

1. **SPOJ AHOCOR** — Aho-Corasick. (Hint: Implement the basic algorithm.)

2. **Codeforces 963D** — Frequency of String. For each pattern, find the minimum distance between two occurrences. (Hint: Use Aho-Corasick, collect positions for each pattern, then find min gap.)

3. **Codeforces 710F** — String Set Queries. Dynamic set of patterns, query occurrences. (Hint: Use Aho-Corasick with batch rebuilding.)

4. **UVa 10679** — I Love Strings!!. (Hint: Build Aho-Corasick for patterns, search each query string.)

5. **SPOJ WPUZZLES** — Word Puzzles. Find words in a grid in all 8 directions. (Hint: Extract all strings from the grid, run Aho-Corasick. Store direction and starting position.)

6. **Codeforces 547E** — Mike and Friends. Count how many times pattern `k` appears in strings `l..r`. (Hint: Build Aho-Corasick, use DFS order on failure tree + prefix sums / BIT.)

---

## See Also

- [Chapter 41: KMP](ch41-kmp.md) — Single-pattern matching; Aho-Corasick generalizes KMP's failure function to a trie of multiple patterns.
- [Chapter 42: Z Algorithm](ch42-z-algorithm.md) — Another string matching technique; Z-algorithm handles single patterns, Aho-Corasick handles multiple.
- [Chapter 44: Suffix Array](ch44-suffix-array.md) — For substring queries on a text; suffix arrays handle arbitrary queries while Aho-Corasick excels at matching a fixed pattern set.
- [Chapter 45: Suffix Automaton](ch45-suffix-automaton.md) — Represents all substrings of a single string; Aho-Corasick matches multiple patterns against a text.
- [Chapter 16: Trie](ch16-trie.md) — Aho-Corasick is built on a trie; understanding trie structure is essential.
- [Chapter 24: Breadth-First Search](ch24-bfs.md) — The failure links in Aho-Corasick are computed via BFS on the trie.
