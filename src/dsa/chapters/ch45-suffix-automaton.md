# Chapter 45: Suffix Automaton

## 45.1 Structure

A **suffix automaton** (also called a **DAWG** — Directed Acyclic Word Graph) is a minimal deterministic finite automaton that recognizes all suffixes of a string. It is one of the most powerful string data structures, capable of solving many problems in linear time and space.

### Key Components

A suffix automaton for string `S` consists of:

1. **States**: Each state represents a set of end positions in `S`. The number of states is at most `2n - 1` for a string of length `n`.

2. **Transitions**: Directed edges labeled with characters. From each state, at most one transition per character exists (deterministic). Total transitions ≤ `3n - 4`.

3. **Suffix Links (`link`)**: A suffix link from state `v` points to a state that represents the longest proper suffix of the strings in `v`. These form a tree rooted at the initial state.

4. **Length (`len`)**: The length of the longest string represented by the state.

### The DAG Property

The suffix automaton is a **DAG** (directed acyclic graph) — there are no cycles. This is because every transition appends a character, increasing the string length. The DAG structure allows us to:
- Count distinct substrings by counting paths from the initial state.
- Find the longest common substring by running multiple strings through the automaton.
- Perform pattern matching in O(m) time for a pattern of length `m`.

### States and Their Meaning

Each state `v` in the suffix automaton corresponds to an **equivalence class** of end positions. Two substrings `s1` and `s2` are in the same class if they occur at exactly the same set of positions as suffixes of prefixes of `S`.

The `link` (suffix link) of state `v` points to the state representing the longest proper suffix of the longest string in `v`. The suffix links form a tree — the **suffix tree** of the reversed string.

### Why Only 2n-1 States?

For a string of length `n`, the suffix automaton has:
- At most `2n - 1` states (proven by the fact that each step of construction adds at most 2 states).
- At most `3n - 4` transitions (for `n ≥ 3`).

This linear bound is what makes the suffix automaton so efficient.

---

## 45.2 Construction: Online O(n)

The suffix automaton is built **online** — one character at a time. Each step takes amortized O(1), giving O(n) total construction.

### The Algorithm

When adding character `c` to the automaton for `S[0..i-1]` to get `S[0..i]`:

1. Create a new state `cur` with `len[cur] = len[last] + 1`.
2. Start from `last` (the state representing the entire string so far). Follow suffix links, adding transitions on `c` to `cur`, until we reach a state that already has a `c` transition or the root.
3. If we reach the root with no `c` transition: set `link[cur] = 0` (root).
4. If we find a state `p` with transition `p --c--> q`:
   - If `len[p] + 1 == len[q]`: set `link[cur] = q`.
   - Otherwise: **clone** state `q` into `clone` with `len[clone] = len[p] + 1`. Copy all transitions of `q` to `clone`. Set `link[clone] = link[q]`, `link[q] = link[cur] = clone`. Redirect all transitions that pointed to `q` (from `p` and its suffix ancestors) to point to `clone`.

### Complete Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

struct SuffixAutomaton {
    struct State {
        int len;        // Length of longest string in this state
        int link;       // Suffix link
        map<char, int> next; // Transitions
    };

    vector<State> st;
    vector<long long> cnt;   // For counting substrings
    int last;                // State representing the entire current string
    int sz;                  // Number of states

    SuffixAutomaton(int maxLen) {
        // At most 2*maxLen states
        st.resize(2 * maxLen);
        cnt.resize(2 * maxLen, 0);
        sz = 1; // state 0 is the root
        st[0].len = 0;
        st[0].link = -1;
        last = 0;
    }

    void extend(char c) {
        int cur = sz++;
        st[cur].len = st[last].len + 1;
        cnt[cur] = 1; // This state represents a new end position

        int p = last;
        // Follow suffix links and add transitions to cur
        while (p != -1 && st[p].next.find(c) == st[p].next.end()) {
            st[p].next[c] = cur;
            p = st[p].link;
        }

        if (p == -1) {
            // Reached root without finding c transition
            st[cur].link = 0;
        } else {
            int q = st[p].next[c];
            if (st[p].len + 1 == st[q].len) {
                // q is already the correct suffix link target
                st[cur].link = q;
            } else {
                // Need to clone q
                int clone = sz++;
                st[clone].len = st[p].len + 1;
                st[clone].next = st[q].next; // Copy transitions
                st[clone].link = st[q].link;
                cnt[clone] = 0; // Clone is not an end position

                // Redirect transitions from p and its suffix ancestors
                while (p != -1 && st[p].next[c] == q) {
                    st[p].next[c] = clone;
                    p = st[p].link;
                }

                st[q].link = st[cur].link = clone;
            }
        }

        last = cur;
    }

    // Build automaton from string
    void build(const string& s) {
        for (char c : s) extend(c);
    }

    // Count distinct substrings
    long long countDistinctSubstrings() {
        long long result = 0;
        for (int i = 1; i < sz; i++) {
            result += st[i].len - st[st[i].link].len;
        }
        return result;
    }

    // Pattern matching: check if pattern exists in the automaton
    bool contains(const string& pattern) {
        int v = 0;
        for (char c : pattern) {
            if (st[v].next.find(c) == st[v].next.end())
                return false;
            v = st[v].next[c];
        }
        return true;
    }

    // Count occurrences of a pattern
    int countOccurrences(const string& pattern) {
        int v = 0;
        for (char c : pattern) {
            if (st[v].next.find(c) == st[v].next.end())
                return 0;
            v = st[v].next[c];
        }
        // v is the state for the pattern
        // We need to compute the size of the endpos set
        // This requires a separate DP (done after building)
        return -1; // Placeholder; see full example below
    }

    // Compute endpos sizes (number of occurrences)
    vector<int> computeEndposSizes() {
        // Topological order by len (descending)
        vector<int> order(sz);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b) {
            return st[a].len > st[b].len;
        });

        vector<int> occ(sz, 0);
        for (int i = 0; i < sz; i++) occ[i] = cnt[i];

        for (int v : order) {
            if (st[v].link >= 0)
                occ[st[v].link] += occ[v];
        }

        return occ;
    }
};

int main() {
    string s = "abcbc";
    SuffixAutomaton sa((int)s.size());
    sa.build(s);

    cout << "String: " << s << "\n";
    cout << "Number of states: " << sa.sz << "\n";
    cout << "Distinct substrings: " << sa.countDistinctSubstrings() << "\n\n";

    // Pattern matching
    vector<string> patterns = {"abc", "bc", "xyz", "abcbc", "a"};
    for (const string& p : patterns) {
        cout << "  \"" << p << "\" found: " << (sa.contains(p) ? "YES" : "NO") << "\n";
    }

    // Count occurrences
    auto occ = sa.computeEndposSizes();
    cout << "\nOccurrence counts for each state:\n";
    for (int i = 0; i < sa.sz; i++) {
        if (sa.cnt[i] > 0 || i == 0) {
            cout << "  State " << i << " (len=" << sa.st[i].len
                 << "): " << occ[i] << " occurrences\n";
        }
    }

    return 0;
}
```

### Dry Run: Building Suffix Automaton for "abbc"

**Step 1: Add 'a' (state 1)**
- cur=1, len=1, link=0
- p=0: no 'a' transition → add 0→1 on 'a'
- p=-1 → link[1]=0
- last=1

**Step 2: Add 'b' (state 2)**
- cur=2, len=2, link=?
- p=1: no 'b' → add 1→2 on 'b'
- p=0: no 'b' → add 0→2 on 'b'
- p=-1 → link[2]=0
- last=2

**Step 3: Add 'b' (state 3)**
- cur=3, len=3, link=?
- p=2: no 'b' → add 2→3 on 'b'
- p=0: has 'b'→2. Check: len[0]+1=1, len[2]=2. Not equal → CLONE
- clone=4, len=1, copy transitions of state 2, link[4]=link[2]=0
- Redirect: st[0].next['b']=4 (was 2)
- link[2]=4, link[3]=4
- last=3

**Step 4: Add 'c' (state 5)**
- cur=5, len=4, link=?
- p=3: no 'c' → add 3→5 on 'c'
- p=4: no 'c' → add 4→5 on 'c'
- p=0: no 'c' → add 0→5 on 'c'
- p=-1 → link[5]=0
- last=5

States: 0(root), 1(a), 2(ab/bb), 3(abb), 4(clone of 2), 5(abbc/bbc/bc/c)

Suffix links: link[1]=0, link[2]=4, link[3]=4, link[4]=0, link[5]=0

Distinct substrings = sum of (len[v] - len[link[v]]) for v=1..5:
- v=1: len=1, link=0 → 1-0 = 1 (substrings: "a")
- v=2: len=2, link=4 → 2-1 = 1 (substrings: "ab")
- v=3: len=3, link=4 → 3-1 = 2 (substrings: "abb", "bb")
- v=4: len=1, link=0 → 1-0 = 1 (substrings: "b")
- v=5: len=4, link=0 → 4-0 = 4 (substrings: "abbc", "bbc", "bc", "c")

Total = 1+1+2+1+4 = **9** distinct substrings: {a, b, c, ab, bb, bc, abb, bbc, abbc} ✓

Note that state 2 (link=4, len=2) only contributes 1 new substring ("ab"), not 2. The substring "bb" of length 2 is contributed by state 3 (which has link=4, so it covers lengths 2 and 3). This is the subtle part: a state `v` contributes substrings of lengths `(len[link[v]]+1)` through `len[v]`, and some of these may overlap with what adjacent states contribute. The formula handles this correctly.

### Python — Suffix Automaton

```python
class SuffixAutomaton:
    def __init__(self, max_len):
        size = 2 * max_len
        self.st = [{'len': 0, 'link': -1, 'next': {}} for _ in range(size)]
        self.cnt = [0] * size
        self.sz = 1
        self.last = 0

    def extend(self, c):
        cur = self.sz
        self.sz += 1
        self.st[cur]['len'] = self.st[self.last]['len'] + 1
        self.cnt[cur] = 1

        p = self.last
        while p != -1 and c not in self.st[p]['next']:
            self.st[p]['next'][c] = cur
            p = self.st[p]['link']

        if p == -1:
            self.st[cur]['link'] = 0
        else:
            q = self.st[p]['next'][c]
            if self.st[p]['len'] + 1 == self.st[q]['len']:
                self.st[cur]['link'] = q
            else:
                clone = self.sz
                self.sz += 1
                self.st[clone]['len'] = self.st[p]['len'] + 1
                self.st[clone]['next'] = dict(self.st[q]['next'])
                self.st[clone]['link'] = self.st[q]['link']
                self.cnt[clone] = 0

                while p != -1 and self.st[p]['next'].get(c) == q:
                    self.st[p]['next'][c] = clone
                    p = self.st[p]['link']

                self.st[q]['link'] = clone
                self.st[cur]['link'] = clone
        self.last = cur

    def build(self, s):
        for c in s:
            self.extend(c)

    def count_distinct_substrings(self):
        result = 0
        for i in range(1, self.sz):
            result += self.st[i]['len'] - self.st[self.st[i]['link']]['len']
        return result

    def contains(self, pattern):
        v = 0
        for c in pattern:
            if c not in self.st[v]['next']:
                return False
            v = self.st[v]['next'][c]
        return True


if __name__ == "__main__":
    s = "abcbc"
    sa = SuffixAutomaton(len(s))
    sa.build(s)

    print(f"String: {s}")
    print(f"Number of states: {sa.sz}")
    print(f"Distinct substrings: {sa.count_distinct_substrings()}")

    for p in ["abc", "bc", "xyz", "abcbc", "a"]:
        print(f'  "{p}" found: {"YES" if sa.contains(p) else "NO"}')
```

### Java — Suffix Automaton

```java
import java.util.*;

public class SuffixAutomaton {
    static class State {
        int len, link;
        Map<Character, Integer> next = new HashMap<>();
    }

    State[] st;
    int[] cnt;
    int last, sz;

    public SuffixAutomaton(int maxLen) {
        int size = 2 * maxLen;
        st = new State[size];
        for (int i = 0; i < size; i++) st[i] = new State();
        cnt = new int[size];
        sz = 1;
        st[0].len = 0;
        st[0].link = -1;
        last = 0;
    }

    public void extend(char c) {
        int cur = sz++;
        st[cur].len = st[last].len + 1;
        cnt[cur] = 1;

        int p = last;
        while (p != -1 && !st[p].next.containsKey(c)) {
            st[p].next.put(c, cur);
            p = st[p].link;
        }

        if (p == -1) {
            st[cur].link = 0;
        } else {
            int q = st[p].next.get(c);
            if (st[p].len + 1 == st[q].len) {
                st[cur].link = q;
            } else {
                int clone = sz++;
                st[clone].len = st[p].len + 1;
                st[clone].next.putAll(st[q].next);
                st[clone].link = st[q].link;
                cnt[clone] = 0;

                while (p != -1 && st[p].next.getOrDefault(c, -1) == q) {
                    st[p].next.put(c, clone);
                    p = st[p].link;
                }
                st[q].link = clone;
                st[cur].link = clone;
            }
        }
        last = cur;
    }

    public void build(String s) {
        for (char c : s.toCharArray()) extend(c);
    }

    public long countDistinctSubstrings() {
        long result = 0;
        for (int i = 1; i < sz; i++) {
            result += st[i].len - st[st[i].link].len;
        }
        return result;
    }

    public boolean contains(String pattern) {
        int v = 0;
        for (char c : pattern.toCharArray()) {
            if (!st[v].next.containsKey(c)) return false;
            v = st[v].next.get(c);
        }
        return true;
    }

    public static void main(String[] args) {
        String s = "abcbc";
        SuffixAutomaton sa = new SuffixAutomaton(s.length());
        sa.build(s);

        System.out.println("String: " + s);
        System.out.println("Number of states: " + sa.sz);
        System.out.println("Distinct substrings: " + sa.countDistinctSubstrings());

        for (String p : new String[]{"abc", "bc", "xyz", "abcbc", "a"}) {
            System.out.printf("  \"%s\" found: %s%n", p, sa.contains(p) ? "YES" : "NO");
        }
    }
}
```

---

## 45.3 Applications

### Application 1: Count Distinct Substrings

The number of distinct substrings equals the number of distinct paths from the initial state in the DAG. Using the suffix automaton formula:

```
distinct = sum over all states v (len[v] - len[link[v]])
```

This is because each state `v` contributes exactly `len[v] - len[link[v]]` new substrings that weren't represented by any state earlier in the construction.

**Complexity**: O(n) to build, O(states) to count.

### Application 2: Longest Common Substring

Given strings `A` and `B`, find the longest string that is a substring of both.

**Algorithm**:
1. Build the suffix automaton for `A`.
2. Run `B` through the automaton. For each character of `B`, try to extend the current match. If we can't follow a transition, follow the suffix link and try again.
3. Track the maximum match length seen.

```cpp
#include <bits/stdc++.h>
using namespace std;

struct SuffixAutomaton {
    struct State {
        int len;
        int link;
        map<char, int> next;
    };

    vector<State> st;
    int last, sz;

    SuffixAutomaton(int maxLen) {
        st.resize(2 * maxLen);
        sz = 1;
        st[0].len = 0;
        st[0].link = -1;
        last = 0;
    }

    void extend(char c) {
        int cur = sz++;
        st[cur].len = st[last].len + 1;
        int p = last;
        while (p != -1 && st[p].next.find(c) == st[p].next.end()) {
            st[p].next[c] = cur;
            p = st[p].link;
        }
        if (p == -1) {
            st[cur].link = 0;
        } else {
            int q = st[p].next[c];
            if (st[p].len + 1 == st[q].len) {
                st[cur].link = q;
            } else {
                int clone = sz++;
                st[clone].len = st[p].len + 1;
                st[clone].next = st[q].next;
                st[clone].link = st[q].link;
                while (p != -1 && st[p].next[c] == q) {
                    st[p].next[c] = clone;
                    p = st[p].link;
                }
                st[q].link = st[cur].link = clone;
            }
        }
        last = cur;
    }

    void build(const string& s) {
        for (char c : s) extend(c);
    }

    // Longest common substring with another string
    string longestCommonSubstring(const string& t) {
        int v = 0; // current state
        int l = 0; // current match length
        int bestLen = 0, bestPos = 0;

        for (int i = 0; i < (int)t.size(); i++) {
            char c = t[i];
            if (st[v].next.find(c) != st[v].next.end()) {
                v = st[v].next[c];
                l++;
            } else {
                while (v != -1 && st[v].next.find(c) == st[v].next.end()) {
                    v = st[v].link;
                }
                if (v == -1) {
                    v = 0;
                    l = 0;
                } else {
                    l = st[v].len + 1;
                    v = st[v].next[c];
                }
            }
            if (l > bestLen) {
                bestLen = l;
                bestPos = i;
            }
        }

        return t.substr(bestPos - bestLen + 1, bestLen);
    }
};

int main() {
    string a = "abcdef";
    string b = "xbcdefgh";

    SuffixAutomaton sa((int)a.size());
    sa.build(a);

    string lcs = sa.longestCommonSubstring(b);
    cout << "Longest common substring of \"" << a << "\" and \"" << b
         << "\": \"" << lcs << "\"\n";
    // Output: "bcdef"

    return 0;
}
```

### Application 3: Pattern Matching

The suffix automaton supports pattern matching in O(m) time for a pattern of length `m`, after O(n) preprocessing.

```cpp
// Check if pattern p exists in the original string
bool patternMatch(SuffixAutomaton& sa, const string& p) {
    int v = 0;
    for (char c : p) {
        if (sa.st[v].next.find(c) == sa.st[v].next.end())
            return false;
        v = sa.st[v].next[c];
    }
    return true;
}

// Count occurrences of pattern p
int countPattern(SuffixAutomaton& sa, const string& p,
                 const vector<int>& occ) {
    int v = 0;
    for (char c : p) {
        if (sa.st[v].next.find(c) == sa.st[v].next.end())
            return 0;
        v = sa.st[v].next[c];
    }
    return occ[v];
}
```

### Complexity Summary

| Operation               | Time     | Space  |
|------------------------|----------|--------|
| Construction           | O(n)     | O(n)   |
| Pattern matching       | O(m)     | O(1)   |
| Count occurrences      | O(m)     | O(n)*  |
| Longest common subst.  | O(|B|)   | O(n)*  |
| Distinct substrings    | O(n)     | O(n)   |

*Requires preprocessing: topological sort + DP on suffix links.

---

## Interview Tips

1. **Understand the cloning mechanism.** The clone operation is the heart of the suffix automaton. When `len[p] + 1 != len[q]`, we need to split `q` because the new character creates a state that should have a shorter maximum length.

2. **The suffix link tree is the suffix tree of the reversed string.** This is a deep connection that helps understand the structure.

3. **Know when to use suffix automaton vs suffix array.** Suffix automaton is better for online construction and when you need to process multiple patterns against the same text. Suffix array is simpler for one-off queries.

4. **State count bound**: Remember `≤ 2n-1` states and `≤ 3n-4` transitions. This is crucial for complexity analysis.

5. **The `len` and `link` properties**: `len[v] - len[link[v]]` gives the number of new substrings contributed by state `v`. This is the key to counting distinct substrings.

## Common Mistakes

1. **Forgetting to clone**: When `len[p] + 1 != len[q]`, cloning is mandatory. Skipping it produces incorrect automata.

2. **Not redirecting all transitions**: When cloning, you must redirect transitions from `p` AND all suffix ancestors of `p` that point to `q`.

3. **Using `map` vs array for transitions**: `map<char,int>` is cleaner but slower. For lowercase letters, use `int next[26]` initialized to -1 for better performance.

4. **Memory allocation**: Pre-allocate `2n` states. Dynamic resizing during construction can invalidate pointers.

5. **Confusing `link` with parent in suffix tree**: The suffix link tree is NOT the suffix tree — it's the suffix tree of the *reversed* string.

## Practice Problems

1. **SPOJ NSUBSTR** — Substrings. For each length `k`, find the maximum number of occurrences of any substring of length `k`. (Hint: Build suffix automaton, compute endpos sizes, then for each state update `ans[len[v]] = max(ans[len[v]], occ[v])`, then propagate.)

2. **SPOJ LCS** — Longest common substring. (Hint: Build SA for first string, run second through it.)

3. **Codeforces 204E** — Little Elephant and Strings. Find, for each substring, how many strings contain it. (Hint: Build a generalized suffix automaton.)

4. **SPOJ SUBLEX** — Lexicographical substrings. Find the k-th lexicographically smallest distinct substring. (Hint: DP on the automaton to count paths, then walk greedily.)

5. **AtCoder ABC279F** — BOX. (Hint: Use suffix automaton with union-find for merging operations.)

---

## See Also

- [Chapter 44: Suffix Array](ch44-suffix-array.md) — An alternative for substring queries; suffix arrays are simpler to implement but suffix automata support online construction.
- [Chapter 41: KMP](ch41-kmp.md) — Single-pattern matching; the suffix automaton generalizes to matching any substring of the text.
- [Chapter 42: Z Algorithm](ch42-z-algorithm.md) — Related string matching technique; Z-array and suffix automaton both process string structure.
- [Chapter 46: Aho-Corasick](ch46-aho-corasick.md) — Multi-pattern matching on a fixed set; suffix automaton handles all substrings of a single string.
- [Chapter 87: Suffix Tree](ch87-suffix-tree.md) — The suffix tree is the suffix automaton's tree-based cousin; both represent all substrings but with different structures.
- [Chapter 16: Trie](ch16-trie.md) — Suffix automata generalize tries to handle all substrings with state compression.
