# Chapter 43: Trie Applications

A **trie** (prefix tree) is a tree-like data structure that stores strings in a way that allows efficient prefix-based queries. While the basic trie (insert, search, startsWith) is well-known, its true power emerges in advanced applications: word search on grids, autocomplete systems, and — perhaps most surprisingly — XOR maximization using **bit tries**. This chapter explores these applications with complete, compilable C++17 code.

---

## 43.1 Word Search — Trie + DFS on Grid

### 43.1.1 Problem: Word Search II (LeetCode 219)

Given an `m × n` grid of characters and a list of words, find all words that can be constructed by traversing adjacent cells (up, down, left, right), where each cell can be used at most once per word.

The brute-force approach runs DFS for each word independently — O(W × 4^L) where W is the number of words and L is the max word length. The trie-based approach combines all words into a single trie and runs DFS once on the grid.

### 43.1.2 Complete Solution

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <set>
using namespace std;

struct TrieNode {
    TrieNode* children[26] = {};
    string word = "";  // non-empty if this node represents the end of a word
};

class Solution {
    TrieNode* root;
    int m, n;
    set<string> result;
    const int dx[4] = {0, 0, 1, -1};
    const int dy[4] = {1, -1, 0, 0};

    void buildTrie(const vector<string>& words) {
        root = new TrieNode();
        for (const string& w : words) {
            TrieNode* node = root;
            for (char c : w) {
                int idx = c - 'a';
                if (!node->children[idx]) {
                    node->children[idx] = new TrieNode();
                }
                node = node->children[idx];
            }
            node->word = w;
        }
    }

    void dfs(vector<vector<char>>& board, int r, int c, TrieNode* node) {
        if (r < 0 || r >= m || c < 0 || c >= n) return;
        char ch = board[r][c];
        if (ch == '#') return;  // already visited

        int idx = ch - 'a';
        if (!node->children[idx]) return;  // no matching prefix in trie

        node = node->children[idx];

        // Found a word
        if (!node->word.empty()) {
            result.insert(node->word);
            // Don't return — there might be longer words
        }

        // Mark as visited
        board[r][c] = '#';

        // Explore all 4 directions
        for (int d = 0; d < 4; d++) {
            dfs(board, r + dx[d], c + dy[d], node);
        }

        // Backtrack
        board[r][c] = ch;

        // Optional optimization: prune empty branches
        // (only if we want to modify the trie)
    }

public:
    vector<string> findWords(vector<vector<char>>& board, vector<string>& words) {
        m = board.size();
        n = board[0].size();
        buildTrie(words);

        for (int i = 0; i < m; i++) {
            for (int j = 0; j < n; j++) {
                dfs(board, i, j, root);
            }
        }

        return vector<string>(result.begin(), result.end());
    }

    // Cleanup
    void freeTrie(TrieNode* node) {
        if (!node) return;
        for (int i = 0; i < 26; i++) {
            freeTrie(node->children[i]);
        }
        delete node;
    }

    ~Solution() { freeTrie(root); }
};

int main() {
    Solution sol;

    vector<vector<char>> board1 = {
        {'o', 'a', 'a', 'n'},
        {'e', 't', 'a', 'e'},
        {'i', 'h', 'k', 'r'},
        {'i', 'f', 'l', 'v'}
    };
    vector<string> words1 = {"oath", "pea", "eat", "rain"};
    auto ans1 = sol.findWords(board1, words1);
    for (const string& w : ans1) cout << w << " ";
    cout << endl;  // eat oath

    vector<vector<char>> board2 = {
        {'a', 'b'},
        {'c', 'd'}
    };
    vector<string> words2 = {"abcb"};
    auto ans2 = sol.findWords(board2, words2);
    cout << (ans2.empty() ? "(none)" : "found") << endl;  // (none)

    return 0;
}
```

### 43.1.3 Why the Trie Approach is Better

**Without trie:** For each of W words, run DFS on the grid. Total: O(W × m × n × 4^L).

**With trie:** Build the trie in O(W × L) total. Then run DFS from each cell. At each step, we only continue if the current path matches a prefix in the trie. This prunes enormous branches early. The total work is O(m × n × 4^L) in the worst case, but in practice much less because most paths are pruned.

**The key insight:** Instead of searching for each word independently, we search for all words simultaneously. The trie lets us check "is there any word starting with this prefix?" in O(1) per character.

### 43.1.4 Dry Run

Grid:
```
o a a n
e t a e
i h k r
i f l v
```
Words: ["oath", "pea", "eat", "rain"]

Trie:
```
root
├── o → a → t → h (word: "oath")
├── p → e → a (word: "pea")
├── e → a → t (word: "eat")
└── r → a → i → n (word: "rain")
```

DFS from (0,0) = 'o':
- 'o' → trie has child 'o'? Yes (oath starts with 'o')
- Go to (0,1) = 'a' → trie 'o'→'a'? Yes
- Go to (1,1) = 't' → trie 'o'→'a'→'t'? Yes
- Go to (1,0) = 'e' → trie 'o'→'a'→'t'→'e'? No. Backtrack.
- Go to (2,1) = 'h' → trie 'o'→'a'→'t'→'h'? Yes. Found "oath"!
- Continue exploring... no more matches.

DFS from (1,0) = 'e':
- 'e' → trie has child 'e'? Yes (eat starts with 'e')
- Go to (1,1) = 'a' → trie 'e'→'a'? Yes
- Go to (1,2) = 't' → trie 'e'→'a'→'t'? Yes. Found "eat"!

DFS from other cells: no new words found (pea and rain can't be formed).

**Complexity:** O(m × n × 4^L) worst case, but trie pruning makes it much faster in practice. O(W × L) space for the trie.

---

## 43.2 Autocomplete — Ranking Suggestions

### 43.2.1 Design an Autocomplete System

Build a trie that stores words with their frequencies. Given a prefix, return the top-k most frequent completions.

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
#include <algorithm>
#include <queue>
using namespace std;

struct TrieNode {
    TrieNode* children[26] = {};
    int freq = 0;  // frequency of the word ending here
};

class AutocompleteSystem {
    TrieNode* root;

    void insert(const string& word, int frequency) {
        TrieNode* node = root;
        for (char c : word) {
            int idx = c - 'a';
            if (!node->children[idx]) {
                node->children[idx] = new TrieNode();
            }
            node = node->children[idx];
        }
        node->freq += frequency;
    }

    // Collect all words with their frequencies under a given node
    void collect(TrieNode* node, string& current,
                 vector<pair<string, int>>& results) {
        if (!node) return;
        if (node->freq > 0) {
            results.push_back({current, node->freq});
        }
        for (int i = 0; i < 26; i++) {
            if (node->children[i]) {
                current.push_back('a' + i);
                collect(node->children[i], current, results);
                current.pop_back();
            }
        }
    }

public:
    AutocompleteSystem() {
        root = new TrieNode();
    }

    void addWord(const string& word, int frequency) {
        insert(word, frequency);
    }

    // Return top-k suggestions for a given prefix
    vector<string> getSuggestions(const string& prefix, int k) {
        TrieNode* node = root;
        for (char c : prefix) {
            int idx = c - 'a';
            if (!node->children[idx]) return {};
            node = node->children[idx];
        }

        // Collect all words under this node
        vector<pair<string, int>> candidates;
        string current = prefix;
        collect(node, current, candidates);

        // Sort by frequency (descending), then by word (ascending)
        sort(candidates.begin(), candidates.end(),
             [](const auto& a, const auto& b) {
                 if (a.second != b.second) return a.second > b.second;
                 return a.first < b.first;
             });

        vector<string> result;
        for (int i = 0; i < min(k, (int)candidates.size()); i++) {
            result.push_back(candidates[i].first);
        }
        return result;
    }

    // Cleanup
    void freeTrie(TrieNode* node) {
        if (!node) return;
        for (int i = 0; i < 26; i++) freeTrie(node->children[i]);
        delete node;
    }
    ~AutocompleteSystem() { freeTrie(root); }
};

int main() {
    AutocompleteSystem ac;
    ac.addWord("apple", 5);
    ac.addWord("app", 3);
    ac.addWord("application", 2);
    ac.addWord("appetizer", 1);
    ac.addWord("banana", 4);
    ac.addWord("band", 2);
    ac.addWord("bat", 3);

    cout << "Suggestions for 'app':" << endl;
    auto suggestions = ac.getSuggestions("app", 5);
    for (const string& s : suggestions) cout << "  " << s << endl;

    cout << "Suggestions for 'ba':" << endl;
    suggestions = ac.getSuggestions("ba", 3);
    for (const string& s : suggestions) cout << "  " << s << endl;

    cout << "Suggestions for 'xyz':" << endl;
    suggestions = ac.getSuggestions("xyz", 3);
    cout << "  " << (suggestions.empty() ? "(none)" : "") << endl;

    return 0;
}
```

**Output:**
```
Suggestions for 'app':
  apple
  app
  application
  appetizer
Suggestions for 'ba':
  banana
  bat
  band
Suggestions for 'xyz':
  (none)
```

### 43.2.2 Optimized Autocomplete with Min-Heap

For large datasets, collecting all candidates is expensive. Instead, use a min-heap of size k during DFS:

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <queue>
#include <algorithm>
using namespace std;

struct TrieNode {
    TrieNode* children[26] = {};
    int freq = 0;
};

class AutocompleteOptimized {
    TrieNode* root;

    void insert(const string& word, int freq) {
        TrieNode* node = root;
        for (char c : word) {
            int idx = c - 'a';
            if (!node->children[idx]) node->children[idx] = new TrieNode();
            node = node->children[idx];
        }
        node->freq += freq;
    }

    // DFS with a min-heap of size k to keep top-k results
    void dfsWithHeap(TrieNode* node, string& current,
                     priority_queue<pair<int, string>,
                                    vector<pair<int, string>>,
                                    greater<>>& minHeap, int k) {
        if (!node) return;
        if (node->freq > 0) {
            if ((int)minHeap.size() < k) {
                minHeap.push({node->freq, current});
            } else if (node->freq > minHeap.top().first) {
                minHeap.pop();
                minHeap.push({node->freq, current});
            }
        }
        for (int i = 0; i < 26; i++) {
            if (node->children[i]) {
                current.push_back('a' + i);
                dfsWithHeap(node->children[i], current, minHeap, k);
                current.pop_back();
            }
        }
    }

public:
    AutocompleteOptimized() { root = new TrieNode(); }
    ~AutocompleteOptimized() {
        // Simplified cleanup
        function<void(TrieNode*)> freeNode = [&](TrieNode* n) {
            if (!n) return;
            for (int i = 0; i < 26; i++) freeNode(n->children[i]);
            delete n;
        };
        freeNode(root);
    }

    void addWord(const string& word, int freq) { insert(word, freq); }

    vector<string> topK(const string& prefix, int k) {
        TrieNode* node = root;
        for (char c : prefix) {
            int idx = c - 'a';
            if (!node->children[idx]) return {};
            node = node->children[idx];
        }

        priority_queue<pair<int, string>,
                       vector<pair<int, string>>,
                       greater<>> minHeap;
        string current = prefix;
        dfsWithHeap(node, current, minHeap, k);

        vector<pair<int, string>> results;
        while (!minHeap.empty()) {
            results.push_back(minHeap.top());
            minHeap.pop();
        }
        // Sort descending by frequency
        sort(results.begin(), results.end(),
             [](const auto& a, const auto& b) {
                 return a.first > b.first;
             });

        vector<string> ans;
        for (auto& [f, w] : results) ans.push_back(w);
        return ans;
    }
};

int main() {
    AutocompleteOptimized ac;
    ac.addWord("apple", 5);
    ac.addWord("app", 3);
    ac.addWord("application", 2);
    ac.addWord("appetizer", 1);
    ac.addWord("banana", 4);

    auto ans = ac.topK("app", 2);
    cout << "Top 2 for 'app':" << endl;
    for (const string& s : ans) cout << "  " << s << endl;
    // apple, app

    return 0;
}
```

**Complexity:** Insert: O(L) per word. Top-k query: O(L + N log k) where N is the number of nodes in the subtree. The min-heap ensures we only keep k candidates at a time.

---

## 43.3 XOR Problems — Max XOR Using Bit Trie

### 43.3.1 Maximum XOR of Two Numbers in an Array (LeetCode 421)

Given an array of non-negative integers, find the maximum XOR of any two numbers.

We already solved this with the greedy prefix approach in Chapter 33. Here we solve it with a **bit trie**, which is more elegant and generalizable.

### 43.3.2 Bit Trie Construction

A bit trie stores numbers in binary representation. Each level corresponds to one bit, starting from the MSB (most significant bit).

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

struct BitTrieNode {
    BitTrieNode* children[2] = {};  // 0 and 1
};

class BitTrie {
    BitTrieNode* root;

public:
    BitTrie() { root = new BitTrieNode(); }

    ~BitTrie() {
        function<void(BitTrieNode*)> freeNode = [&](BitTrieNode* n) {
            if (!n) return;
            freeNode(n->children[0]);
            freeNode(n->children[1]);
            delete n;
        };
        freeNode(root);
    }

    void insert(int num) {
        BitTrieNode* node = root;
        // Insert from MSB (bit 31) to LSB (bit 0)
        for (int i = 31; i >= 0; i--) {
            int bit = (num >> i) & 1;
            if (!node->children[bit]) {
                node->children[bit] = new BitTrieNode();
            }
            node = node->children[bit];
        }
    }

    // Find the number in the trie that maximizes XOR with 'num'
    int findMaxXOR(int num) {
        BitTrieNode* node = root;
        int maxXor = 0;
        for (int i = 31; i >= 0; i--) {
            int bit = (num >> i) & 1;
            int desired = 1 - bit;  // we want the opposite bit
            if (node->children[desired]) {
                maxXor |= (1 << i);  // this bit contributes to XOR
                node = node->children[desired];
            } else {
                node = node->children[bit];
            }
        }
        return maxXor;
    }
};

class Solution {
public:
    int findMaximumXOR(vector<int>& nums) {
        BitTrie trie;
        int maxXor = 0;

        // Insert first number
        trie.insert(nums[0]);

        // For each subsequent number, find the max XOR with any previous number
        for (int i = 1; i < (int)nums.size(); i++) {
            maxXor = max(maxXor, trie.findMaxXOR(nums[i]));
            trie.insert(nums[i]);
        }
        return maxXor;
    }
};

int main() {
    Solution sol;
    vector<int> nums1 = {3, 10, 5, 25, 2, 8};
    cout << "Max XOR: " << sol.findMaximumXOR(nums1) << endl;  // 28

    vector<int> nums2 = {14, 70, 53, 83, 49, 91, 36, 80, 92, 51, 66, 70};
    cout << "Max XOR: " << sol.findMaximumXOR(nums2) << endl;  // 127

    return 0;
}
```

### 43.3.3 Dry Run

For `nums = [3, 10, 5, 25, 2, 8]`:

```
Binary representations:
3  = 00000000 00000000 00000000 00000011
10 = 00000000 00000000 00000000 00001010
5  = 00000000 00000000 00000000 00000101
25 = 00000000 00000000 00000000 00011001
2  = 00000000 00000000 00000000 00000010
8  = 00000000 00000000 00000000 00001000

Step 1: Insert 3 (11)
Trie: root → 0 → 0 → ... → 0 → 1 → 1

Step 2: Query max XOR with 10 (1010)
Starting from MSB, we want opposite bits:
Bit 31..5: all 0, desired 1, but trie only has 0 path → go 0
Bit 4: num=0, desired=1, trie has 0 path (from 25 not inserted yet). Actually wait,
  only 3 is in the trie. 3 = ...00011.
  
  Let me trace the bits we care about (last 8 bits for clarity):
  3  = 00000011
  10 = 00001010
  
  Bit 4: 10 has 0, desired 1. Trie: 3's bit 4 is 0. Only 0 child exists. Go 0.
  Bit 3: 10 has 1, desired 0. Trie: 3's bit 3 is 0. Go 0. maxXor bit 3 = 0.
  
  Hmm wait, I need to be more careful. Let me trace the full trie path for 3:
  3 in binary (32 bits): 00000000 00000000 00000000 00000011
  
  Trie path for 3: 0→0→0→...→0→0→1→1 (bits 31 down to 0)
  
  Query for 10: 00000000 00000000 00000000 00001010
  Bit 31: num=0, want 1, trie only has 0 → go 0, xor bit = 0
  ... (bits 30..5: same, all 0 in both)
  Bit 4: num=0, want 1, trie only has 0 → go 0, xor bit = 0
  Bit 3: num=1, want 0, trie has 0 → go 0, xor bit = 1! maxXor |= (1<<3) = 8
  Bit 2: num=0, want 1, trie only has 0 (since 3's bit 2 is 0) → go 0, xor bit = 0
  Bit 1: num=1, want 0, trie has 0 (3's bit 1 is 1... wait)
  
  3 = ...0011. Bit 1 = 1. So after bit 2, we're at the node for bit 2 of 3,
  which is 0. Its child is 1 (bit 1 of 3). So children[0] exists but children[1]
  also exists? No — we're at the node for bit position 2 of 3. 3's bit 2 = 0,
  so only children[0] exists at that level.
  
  Hmm, let me re-think the trie structure. After inserting 3:
  root → children[0] (bit 31 of 3 is 0)
    → children[0] (bit 30)
    → ... → children[0] (bit 2)
    → children[1] (bit 1 of 3 is 1)
    → children[1] (bit 0 of 3 is 1)
  
  Query for 10: 00000000 00000000 00000000 00001010
  Bit 4: 0, want 1. children[1] doesn't exist at root→...→bit5 level. Go children[0].
  Bit 3: 1, want 0. At bit 3 level, children[0] exists (3's bit 3 = 0). Go 0. maxXor |= 8.
  Bit 2: 0, want 1. At bit 2 level, only children[0] (3's bit 2 = 0). Go 0.
  Bit 1: 1, want 0. At bit 1 level, only children[1] (3's bit 1 = 1). Go 1. No xor contribution.
  Bit 0: 0, want 1. At bit 0 level, only children[1] (3's bit 0 = 1). Go 1. maxXor |= 1.
  
  maxXor = 8 + 1 = 9. 3 XOR 10 = 9. ✓

Step 3: Insert 10, query with 5:
  5 = 00000101
  3 XOR 5 = 6, 10 XOR 5 = 15 → max so far = 15

  Query 5 against trie (containing 3 and 10):
  Bit 3: 5 has 0, want 1. Trie: both 3 and 10 have bit 3 = 0. Only 0 child. Go 0.
  Bit 2: 5 has 1, want 0. Trie: 3's bit 2 = 0, 10's bit 2 = 0. children[0] exists. Go 0. maxXor |= 4.
  Bit 1: 5 has 0, want 1. Trie: 3's bit 1 = 1, 10's bit 1 = 1. children[1] exists. Go 1. maxXor |= 2.
  Bit 0: 5 has 1, want 0. Trie: 3's bit 0 = 1, 10's bit 0 = 0. children[0] exists (from 10). Go 0. maxXor |= 1.
  
  maxXor = 4+2+1 = 7. But 10 XOR 5 = 15. Something's wrong...
  
  Ah, I see the issue. The trie path isn't just at the "bit 2 level" — the path is determined by ALL higher bits. Since we go through children[0] for bits 31..4, and children[0] for bit 3, we're now at the node representing the path "all 0s for bits 31..3". Both 3 and 10 share this prefix. But at bit 2, 3 has 0 and 10 has 0. So still one path. At bit 1, 3 has 1 and 10 has 1. Still one path. At bit 0, 3 has 1 and 10 has 0 — now there's a branch!

  So at bit 0: 5 has 1, want 0. The trie node has both children[0] (from 10) and children[1] (from 3). We prefer children[0]. maxXor |= 1.
  
  Total: 4 + 2 + 1 = 7. But 10 XOR 5 = 15 (1111 in binary).
  
  Wait, I think I made an error. Let me recompute:
  10 XOR 5 = 1010 XOR 0101 = 1111 = 15. ✓
  
  But the trie gives 7? That's wrong. Let me re-examine.
  
  Ah, I see my mistake. When I said "at bit 1, children[1] exists," I need to check which PATH we're on. We went through children[0] at bit 3. At bit 2, both 3 and 10 have 0. But the trie node at "bit 2" depends on the path taken at higher bits. Since we went 0→0→...→0 at all higher bits, and then 0 at bit 3, we're at a node where both 3 and 10 pass through.
  
  At bit 2: 3 has 0, 10 has 0. Only children[0]. Go 0. maxXor |= 4.
  At bit 1: 3 has 1, 10 has 1. Only children[1]. We want 0 but only 1 exists. Go 1. No xor.
  At bit 0: 3 has 1, 10 has 0. Both children exist. We want 0 (since 5 has 1). Go 0. maxXor |= 1.
  
  So maxXor = 4 + 0 + 1 = 5. Hmm, that's also not 15.
  
  Wait, I think the issue is that I'm computing the XOR with a SPECIFIC number in the trie, not the global maximum. Let me re-examine.
  
  findMaxXOR(5) should find the number in {3, 10} that maximizes XOR with 5.
  3 XOR 5 = 6 (0110)
  10 XOR 5 = 15 (1111)
  So the answer should be 15, achieved with 10.
  
  Let me trace the trie more carefully. The trie contains:
  3  = ...00000011
  10 = ...00001010
  
  The trie path for 3: bits 31..3 are all 0, bit 2 is 0, bit 1 is 1, bit 0 is 1.
  The trie path for 10: bits 31..4 are all 0, bit 3 is 1, bit 2 is 0, bit 1 is 1, bit 0 is 0.
  
  Wait! 10 = 1010. Bit 3 = 1! So at the bit 3 level:
  - 3 has bit 3 = 0 → goes to children[0]
  - 10 has bit 3 = 1 → goes to children[1]
  
  So at the "bit 3" level from the root's bit-4 child, both children[0] (from 3) and children[1] (from 10) exist!
  
  Now query for 5 = 0101:
  Bit 4: 0, want 1. Only children[0] (both 3 and 10 have 0). Go 0.
  Bit 3: 0, want 1. children[1] EXISTS (from 10)! Go 1. maxXor |= 8.
  Now we're on the path that only 10 took. At bit 2: 10 has 0. children[0] exists. 5 has 1, want 0. Go 0. maxXor |= 4.
  At bit 1: 10 has 1. children[1] exists. 5 has 0, want 1. Go 1. maxXor |= 2.
  At bit 0: 10 has 0. children[0] exists. 5 has 1, want 0. Go 0. maxXor |= 1.
  
  maxXor = 8 + 4 + 2 + 1 = 15. ✓!
  
  Great, so the algorithm is correct. I was making errors in my manual trace by forgetting that 10 has bit 3 = 1.
```

**Complexity:** O(32n) = O(n) time, O(32n) = O(n) space.

---

## 43.4 Bit Trie — Binary Representations and XOR Maximization

### 43.4.1 The Bit Trie Structure

A bit trie stores integers as binary strings of fixed length (typically 31 or 32 bits). Each node has at most two children (0 and 1). The root corresponds to the MSB.

```cpp
#include <iostream>
#include <vector>
using namespace std;

struct BitTrieNode {
    BitTrieNode* children[2] = {};
};

class BitTrie {
    static const int BITS = 31;  // for numbers up to 2^31 - 1
    BitTrieNode* root;

    void freeTrie(BitTrieNode* node) {
        if (!node) return;
        freeTrie(node->children[0]);
        freeTrie(node->children[1]);
        delete node;
    }

public:
    BitTrie() { root = new BitTrieNode(); }
    ~BitTrie() { freeTrie(root); }

    void insert(int num) {
        BitTrieNode* node = root;
        for (int i = BITS; i >= 0; i--) {
            int bit = (num >> i) & 1;
            if (!node->children[bit]) {
                node->children[bit] = new BitTrieNode();
            }
            node = node->children[bit];
        }
    }

    int queryMaxXOR(int num) {
        BitTrieNode* node = root;
        int result = 0;
        for (int i = BITS; i >= 0; i--) {
            int bit = (num >> i) & 1;
            int desired = 1 - bit;
            if (node->children[desired]) {
                result |= (1 << i);
                node = node->children[desired];
            } else if (node->children[bit]) {
                node = node->children[bit];
            } else {
                // Trie is empty (shouldn't happen if we inserted something)
                break;
            }
        }
        return result;
    }

    // Check if a number exists in the trie
    bool search(int num) {
        BitTrieNode* node = root;
        for (int i = BITS; i >= 0; i--) {
            int bit = (num >> i) & 1;
            if (!node->children[bit]) return false;
            node = node->children[bit];
        }
        return true;
    }

    // Find the maximum XOR of any pair in an array
    static int maxXORPair(const vector<int>& nums) {
        if (nums.size() < 2) return 0;
        BitTrie trie;
        trie.insert(nums[0]);
        int maxXor = 0;
        for (int i = 1; i < (int)nums.size(); i++) {
            maxXor = max(maxXor, trie.queryMaxXOR(nums[i]));
            trie.insert(nums[i]);
        }
        return maxXor;
    }
};

int main() {
    cout << "Max XOR pair in [3,10,5,25,2,8]: "
         << BitTrie::maxXORPair({3, 10, 5, 25, 2, 8}) << endl;  // 28

    BitTrie trie;
    trie.insert(5);
    trie.insert(3);
    trie.insert(10);

    cout << "Max XOR with 5: " << trie.queryMaxXOR(5) << endl;   // 15 (5^10)
    cout << "Max XOR with 3: " << trie.queryMaxXOR(3) << endl;   // 9  (3^10)
    cout << "Max XOR with 10: " << trie.queryMaxXOR(10) << endl; // 15 (10^5)

    cout << "Search 5: " << trie.search(5) << endl;   // 1
    cout << "Search 7: " << trie.search(7) << endl;   // 0

    return 0;
}
```

### 43.4.2 Maximum XOR Subarray

Given an array, find the maximum XOR of any contiguous subarray. This uses the property that `xor(i..j) = prefixXor[j] ^ prefixXor[i-1]`. So we need to maximize `prefixXor[j] ^ prefixXor[i-1]` for all `i <= j`.

```cpp
#include <iostream>
#include <vector>
using namespace std;

struct BitTrieNode {
    BitTrieNode* children[2] = {};
};

int maxXORSubarray(const vector<int>& nums) {
    const int BITS = 31;
    BitTrieNode* root = new BitTrieNode();

    // Insert 0 (empty prefix XOR)
    auto insert = [&](int num) {
        BitTrieNode* node = root;
        for (int i = BITS; i >= 0; i--) {
            int bit = (num >> i) & 1;
            if (!node->children[bit]) {
                node->children[bit] = new BitTrieNode();
            }
            node = node->children[bit];
        }
    };

    auto queryMaxXOR = [&](int num) -> int {
        BitTrieNode* node = root;
        int result = 0;
        for (int i = BITS; i >= 0; i--) {
            int bit = (num >> i) & 1;
            int desired = 1 - bit;
            if (node->children[desired]) {
                result |= (1 << i);
                node = node->children[desired];
            } else {
                node = node->children[bit];
            }
        }
        return result;
    };

    auto freeTrie = [&](auto self, BitTrieNode* node) -> void {
        if (!node) return;
        self(self, node->children[0]);
        self(self, node->children[1]);
        delete node;
    };

    insert(0);  // empty prefix
    int prefixXor = 0;
    int maxXor = 0;

    for (int x : nums) {
        prefixXor ^= x;
        maxXor = max(maxXor, queryMaxXOR(prefixXor));
        insert(prefixXor);
    }

    freeTrie(freeTrie, root);
    return maxXor;
}

int main() {
    vector<int> nums1 = {3, 10, 5, 25, 2, 8};
    cout << "Max XOR subarray: " << maxXORSubarray(nums1) << endl;  // 28

    vector<int> nums2 = {8, 1, 2, 12, 7};
    cout << "Max XOR subarray: " << maxXORSubarray(nums2) << endl;  // 15

    vector<int> nums3 = {1};
    cout << "Max XOR subarray: " << maxXORSubarray(nums3) << endl;  // 1

    return 0;
}
```

**Why it works:** `xor(i..j) = prefixXor[j] ^ prefixXor[i-1]`. For each `j`, we want to find the `i-1 < j` that maximizes this XOR. The bit trie stores all `prefixXor[0..j-1]` and efficiently finds the one that maximizes XOR with `prefixXor[j]`.

**Complexity:** O(32n) = O(n) time, O(32n) = O(n) space.

### 43.4.3 Maximum XOR With an Element From Array (LeetCode 1707)

Given an array and queries `(xi, mi)`, for each query find the maximum `xi ^ nums[j]` where `nums[j] <= mi`.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

struct BitTrieNode {
    BitTrieNode* children[2] = {};
};

class BitTrie {
    BitTrieNode* root;
    static const int BITS = 30;

public:
    BitTrie() { root = new BitTrieNode(); }
    ~BitTrie() {
        function<void(BitTrieNode*)> freeN = [&](BitTrieNode* n) {
            if (!n) return;
            freeN(n->children[0]); freeN(n->children[1]); delete n;
        };
        freeN(root);
    }

    void insert(int num) {
        BitTrieNode* node = root;
        for (int i = BITS; i >= 0; i--) {
            int bit = (num >> i) & 1;
            if (!node->children[bit]) node->children[bit] = new BitTrieNode();
            node = node->children[bit];
        }
    }

    int queryMaxXOR(int num) {
        BitTrieNode* node = root;
        int result = 0;
        for (int i = BITS; i >= 0; i--) {
            int bit = (num >> i) & 1;
            int desired = 1 - bit;
            if (node->children[desired]) {
                result |= (1 << i);
                node = node->children[desired];
            } else if (node->children[bit]) {
                node = node->children[bit];
            } else {
                return -1;  // trie is empty
            }
        }
        return result;
    }
};

class Solution {
public:
    vector<int> maximizeXor(vector<int>& nums, vector<vector<int>>& queries) {
        sort(nums.begin(), nums.end());

        // Sort queries by mi
        vector<int> order(queries.size());
        for (int i = 0; i < (int)queries.size(); i++) order[i] = i;
        sort(order.begin(), order.end(), [&](int a, int b) {
            return queries[a][1] < queries[b][1];
        });

        vector<int> ans(queries.size(), -1);
        BitTrie trie;
        int numIdx = 0;

        for (int qi : order) {
            int xi = queries[qi][0], mi = queries[qi][1];
            // Insert all nums[j] <= mi
            while (numIdx < (int)nums.size() && nums[numIdx] <= mi) {
                trie.insert(nums[numIdx]);
                numIdx++;
            }
            if (numIdx > 0) {
                ans[qi] = trie.queryMaxXOR(xi);
            }
        }
        return ans;
    }
};

int main() {
    Solution sol;
    vector<int> nums = {0, 1, 2, 3, 4};
    vector<vector<int>> queries = {{3, 1}, {1, 3}, {5, 6}};
    auto ans = sol.maximizeXor(nums, queries);
    for (int x : ans) cout << x << " ";
    cout << endl;  // 3 3 7
    return 0;
}
```

**Complexity:** O(n log n + q log q + (n + q) × 32) — sorting + processing each element/query through the trie.

---

## Interview Tips

1. **Trie + DFS** is the standard approach for word search problems on grids. The trie provides prefix-based pruning.
2. **Bit trie for XOR** is a must-know pattern. Whenever you see "maximum XOR" problems, think bit trie.
3. **Prefix XOR + bit trie** solves maximum XOR subarray problems. The key insight is converting subarray XOR to prefix XOR difference.
4. **Off-line processing** (sort queries by constraint, process incrementally) combined with a bit trie solves constraint-based XOR queries.
5. **Memory management:** In interviews, you can often skip explicit cleanup. In production code, use smart pointers or arena allocation.

## Common Mistakes

- **Forgetting to insert 0** in prefix XOR problems. The empty prefix (index -1) has XOR = 0, and subarrays starting from index 0 need it.
- **Bit order in trie.** Always go from MSB to LSB. Going LSB-first doesn't maximize XOR correctly.
- **Trie cleanup.** Forgetting to free trie nodes causes memory leaks. Use destructors or smart pointers.
- **Using `int` for bit shifts.** `1 << 31` is undefined behavior for signed `int`. Use `1U << 31` or `1LL << 31`.
- **Not handling empty trie queries.** If the trie might be empty when querying, return a sentinel value (-1 or INT_MIN).

## Practice Problems

1. **Maximum Genetic Diversity Query** — Given numbers and queries, find max XOR with numbers less than a threshold. *Hint: Offline processing + bit trie.*
2. **Count Pairs With XOR in a Range** (LeetCode 1803) — Count pairs whose XOR is in [low, high]. *Hint: Bit trie with count at each node.*
3. **Implement Magic Dictionary** (LeetCode 676) — Trie + one-character mismatch search. *Hint: For each word in the dictionary, try replacing each character and check if the result exists in the trie.*
4. **Map Sum Pairs** (LeetCode 677) — Trie storing prefix sums. *Hint: Each node stores the sum of all values of words passing through it.*
5. **Palindrome Pairs** (LeetCode 336) — Find all pairs of words that form a palindrome when concatenated. *Hint: Trie + check remaining suffix for palindrome property.*
