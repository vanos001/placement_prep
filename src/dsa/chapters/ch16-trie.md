# Chapter 16: Trie

## 16.1 Trie Structure

A **trie** (pronounced "try", from "retrieval") is a tree-like data structure used to efficiently store and retrieve strings. It is also called a **prefix tree** because it exploits the common prefixes shared by strings to minimize redundant storage.

### Why Not Just Use a Hash Table?

Hash tables are excellent for exact key lookups, but they have fundamental limitations when it comes to prefix-based operations:

| Operation | Hash Table | Trie |
|-----------|-----------|------|
| Exact search | O(m) avg | O(m) |
| Insert | O(m) avg | O(m) |
| Prefix search ("starts with") | O(n·m) — must scan all keys | O(m) + O(k) for k matches |
| Autocomplete | O(n·m) — must scan all keys | O(m) + O(k) for k matches |
| Longest common prefix | O(n·m) | O(m) — just walk the trie |
| Delete | O(m) avg | O(m) |

Where `m` is the length of the string and `n` is the number of strings.

**Key insight**: A trie finds all strings with a given prefix in time proportional to the prefix length, not the total number of strings. This makes it ideal for autocomplete, spell checking, and IP routing.

### Visual Diagram

Consider inserting the words: "cat", "car", "card", "care", "dog", "do"

```
        root
       /    \
      c      d
      |      |
      a      o
     / \     |
    t   r    g
        |
        d
        |
        e (end)
```

Each node represents a character. The path from the root to a marked node (end-of-word) spells out a complete word. Shared prefixes share the same path — "car", "card", and "care" share the prefix "car".

**Memory tradeoff**: A trie uses more memory than storing strings individually (each node has up to 26 pointers for English), but the prefix sharing and fast prefix lookups often justify this cost.

---

## 16.2 Implementation

### Node Structure

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>

// Standard Trie Node with fixed-size children array (for lowercase a-z)
struct TrieNode {
    TrieNode* children[26];
    bool isEnd;

    TrieNode() : isEnd(false) {
        for (int i = 0; i < 26; ++i) {
            children[i] = nullptr;
        }
    }
};

// Alternative: Trie Node with hash map (supports any character)
struct TrieNodeMap {
    std::unordered_map<char, TrieNodeMap*> children;
    bool isEnd;

    TrieNodeMap() : isEnd(false) {}
};
```

### Complete Trie Implementation

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <queue>

class Trie {
private:
    struct Node {
        Node* children[26];
        bool isEnd;
        int prefixCount;  // How many words pass through this node

        Node() : isEnd(false), prefixCount(0) {
            for (int i = 0; i < 26; ++i) {
                children[i] = nullptr;
            }
        }
    };

    Node* root;

    // Helper: recursively collect all words with given prefix
    void collectWords(Node* node, std::string& current,
                      std::vector<std::string>& result) const {
        if (!node) return;

        if (node->isEnd) {
            result.push_back(current);
        }

        for (int i = 0; i < 26; ++i) {
            if (node->children[i]) {
                current.push_back('a' + i);
                collectWords(node->children[i], current, result);
                current.pop_back();
            }
        }
    }

    // Helper: recursively delete all nodes
    void deleteTrie(Node* node) {
        if (!node) return;
        for (int i = 0; i < 26; ++i) {
            deleteTrie(node->children[i]);
        }
        delete node;
    }

public:
    Trie() : root(new Node()) {}

    ~Trie() {
        deleteTrie(root);
    }

    // Non-copyable for simplicity
    Trie(const Trie&) = delete;
    Trie& operator=(const Trie&) = delete;

    // Insert a word into the trie — O(m)
    void insert(const std::string& word) {
        Node* current = root;
        for (char ch : word) {
            int index = ch - 'a';
            if (!current->children[index]) {
                current->children[index] = new Node();
            }
            current = current->children[index];
            current->prefixCount++;
        }
        current->isEnd = true;
    }

    // Search for an exact word — O(m)
    bool search(const std::string& word) const {
        Node* node = findNode(word);
        return node != nullptr && node->isEnd;
    }

    // Check if any word starts with the given prefix — O(m)
    bool startsWith(const std::string& prefix) const {
        return findNode(prefix) != nullptr;
    }

    // Count how many words have the given prefix — O(m)
    int countPrefix(const std::string& prefix) const {
        Node* node = findNode(prefix);
        return node ? node->prefixCount : 0;
    }

    // Get all words that start with the given prefix — O(m + k)
    // where k is the total number of characters in matching words
    std::vector<std::string> autocomplete(const std::string& prefix) const {
        std::vector<std::string> result;
        Node* node = findNode(prefix);
        if (!node) return result;

        std::string current = prefix;
        collectWords(node, current, result);
        return result;
    }

    // Delete a word from the trie — O(m)
    bool remove(const std::string& word) {
        if (!search(word)) return false;
        removeHelper(root, word, 0);
        return true;
    }

private:
    // Find the node corresponding to the last character of the given string
    Node* findNode(const std::string& str) const {
        Node* current = root;
        for (char ch : str) {
            int index = ch - 'a';
            if (!current->children[index]) {
                return nullptr;
            }
            current = current->children[index];
        }
        return current;
    }

    // Recursive helper for deletion
    // Returns true if the parent should delete this node
    bool removeHelper(Node* node, const std::string& word, int depth) {
        if (!node) return false;

        if (depth == static_cast<int>(word.size())) {
            node->isEnd = false;
            // If node has no children, it can be deleted
            return !hasChildren(node);
        }

        int index = word[depth] - 'a';
        bool shouldDeleteChild = removeHelper(node->children[index], word, depth + 1);

        if (shouldDeleteChild) {
            delete node->children[index];
            node->children[index] = nullptr;
            // Current node can be deleted if it's not end of another word
            // and has no other children
            return !node->isEnd && !hasChildren(node);
        }

        return false;
    }

    bool hasChildren(const Node* node) const {
        for (int i = 0; i < 26; ++i) {
            if (node->children[i]) return true;
        }
        return false;
    }
};

int main() {
    Trie trie;

    // Insert words
    std::vector<std::string> words = {"apple", "app", "application", "bat", "ball", "band"};
    for (const auto& word : words) {
        trie.insert(word);
    }

    // Search
    std::cout << "Search 'app': " << (trie.search("app") ? "found" : "not found") << "\n";
    std::cout << "Search 'ap': " << (trie.search("ap") ? "found" : "not found") << "\n";
    std::cout << "Search 'apple': " << (trie.search("apple") ? "found" : "not found") << "\n";

    // Prefix
    std::cout << "Starts with 'app': " << (trie.startsWith("app") ? "yes" : "no") << "\n";
    std::cout << "Count prefix 'app': " << trie.countPrefix("app") << "\n";

    // Autocomplete
    auto suggestions = trie.autocomplete("app");
    std::cout << "Autocomplete 'app': ";
    for (const auto& s : suggestions) {
        std::cout << s << " ";
    }
    std::cout << "\n";

    // Delete
    trie.remove("app");
    std::cout << "After removing 'app':\n";
    std::cout << "  Search 'app': " << (trie.search("app") ? "found" : "not found") << "\n";
    std::cout << "  Search 'apple': " << (trie.search("apple") ? "found" : "not found") << "\n";

    return 0;
}
```

### Implementation Notes

**Why `prefixCount`?** Tracking how many words pass through each node enables O(m) prefix counting, which is useful for autocomplete ranking and statistical analysis.

**Deletion complexity**: Deleting a word is O(m) where m is the word length. We recursively check if nodes can be safely removed (no other words pass through them). If a node is part of another word's path, we keep it.

**Memory optimization**: For sparse tries (few words with diverse characters), use `std::unordered_map<char, Node*>` instead of a fixed array. This saves memory at the cost of slightly slower access.

---

## 16.3 Applications

### Application 1: Autocomplete System

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
#include <algorithm>

class AutocompleteSystem {
private:
    struct Node {
        std::unordered_map<char, Node*> children;
        bool isEnd = false;
        int frequency = 0;
    };

    Node* root;
    std::string currentInput;
    Node* currentNode;  // Tracks current position while typing

    void dfs(Node* node, std::string& path,
             std::vector<std::pair<std::string, int>>& results) const {
        if (!node) return;
        if (node->isEnd) {
            results.emplace_back(path, node->frequency);
        }
        for (auto& [ch, child] : node->children) {
            path.push_back(ch);
            dfs(child, path, results);
            path.pop_back();
        }
    }

public:
    AutocompleteSystem() : root(new Node()), currentNode(root) {}

    void addWord(const std::string& word, int frequency) {
        Node* node = root;
        for (char ch : word) {
            if (!node->children.count(ch)) {
                node->children[ch] = new Node();
            }
            node = node->children[ch];
        }
        node->isEnd = true;
        node->frequency += frequency;
    }

    std::vector<std::string> input(char c) {
        if (c == '#') {
            // End of input — record the search and reset
            Node* node = root;
            for (char ch : currentInput) {
                node = node->children[ch];
            }
            node->isEnd = true;
            node->frequency++;

            currentInput.clear();
            currentNode = root;
            return {};
        }

        currentInput += c;

        // Move to the child corresponding to the typed character
        if (currentNode && currentNode->children.count(c)) {
            currentNode = currentNode->children[c];
        } else {
            currentNode = nullptr;
            return {};
        }

        // Collect all completions
        std::vector<std::pair<std::string, int>> completions;
        std::string path = currentInput;
        dfs(currentNode, path, completions);

        // Sort by frequency (descending), then by string (ascending)
        std::sort(completions.begin(), completions.end(),
                  [](const auto& a, const auto& b) {
                      if (a.second != b.second) return a.second > b.second;
                      return a.first < b.first;
                  });

        // Return top 3
        std::vector<std::string> result;
        for (int i = 0; i < std::min(3, static_cast<int>(completions.size())); ++i) {
            result.push_back(completions[i].first);
        }
        return result;
    }
};

int main() {
    AutocompleteSystem acs;
    acs.addWord("i love you", 5);
    acs.addWord("island", 3);
    acs.addWord("ironman", 2);
    acs.addWord("i love leetcode", 2);

    auto r1 = acs.input('i');
    std::cout << "Input 'i': ";
    for (auto& s : r1) std::cout << "[" << s << "] ";
    std::cout << "\n";

    acs.input('#');  // Reset
    return 0;
}
```

### Application 2: Spell Checker

A trie-based spell checker can suggest corrections using edit distance:

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

class SpellChecker {
private:
    struct Node {
        Node* children[26] = {};
        bool isEnd = false;
    };

    Node* root;

    void suggest(Node* node, const std::string& target,
                 std::string& current, std::vector<std::string>& suggestions,
                 int maxEdits) const {
        if (!node) return;

        // Pruning: if remaining length difference exceeds maxEdits, stop
        int remainingTarget = static_cast<int>(target.size()) - static_cast<int>(current.size());
        if (remainingTarget > maxEdits) return;

        if (node->isEnd && current.size() >= target.size() - maxEdits &&
            current.size() <= target.size() + maxEdits) {
            int dist = editDistance(current, target);
            if (dist <= maxEdits) {
                suggestions.push_back(current);
            }
        }

        for (int i = 0; i < 26; ++i) {
            if (node->children[i]) {
                current.push_back('a' + i);
                suggest(node->children[i], target, current, suggestions, maxEdits);
                current.pop_back();
            }
        }
    }

    static int editDistance(const std::string& a, const std::string& b) {
        int m = a.size(), n = b.size();
        std::vector<std::vector<int>> dp(m + 1, std::vector<int>(n + 1));

        for (int i = 0; i <= m; ++i) dp[i][0] = i;
        for (int j = 0; j <= n; ++j) dp[0][j] = j;

        for (int i = 1; i <= m; ++i) {
            for (int j = 1; j <= n; ++j) {
                if (a[i - 1] == b[j - 1]) {
                    dp[i][j] = dp[i - 1][j - 1];
                } else {
                    dp[i][j] = 1 + std::min({dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]});
                }
            }
        }
        return dp[m][n];
    }

public:
    SpellChecker() : root(new Node()) {}

    void addWord(const std::string& word) {
        Node* node = root;
        for (char ch : word) {
            int idx = ch - 'a';
            if (!node->children[idx]) {
                node->children[idx] = new Node();
            }
            node = node->children[idx];
        }
        node->isEnd = true;
    }

    bool isCorrect(const std::string& word) const {
        Node* node = root;
        for (char ch : word) {
            int idx = ch - 'a';
            if (!node->children[idx]) return false;
            node = node->children[idx];
        }
        return node->isEnd;
    }

    std::vector<std::string> suggest(const std::string& word, int maxEdits = 2) const {
        std::vector<std::string> suggestions;
        std::string current;
        suggest(root, word, current, suggestions, maxEdits);
        return suggestions;
    }
};

int main() {
    SpellChecker checker;
    std::vector<std::string> dictionary = {
        "hello", "world", "help", "held", "hero",
        "python", "program", "problem", "probe"
    };
    for (const auto& word : dictionary) {
        checker.addWord(word);
    }

    std::string query = "helo";
    if (checker.isCorrect(query)) {
        std::cout << query << " is correct\n";
    } else {
        std::cout << query << " is misspelled. Suggestions:\n";
        auto suggestions = checker.suggest(query);
        for (const auto& s : suggestions) {
            std::cout << "  " << s << "\n";
        }
    }

    return 0;
}
```

### Application 3: IP Routing (Longest Prefix Match)

In networking, routers use tries to find the longest matching prefix for an IP address. A binary trie (where each level represents a bit) is used:

```cpp
#include <iostream>
#include <string>
#include <optional>

// Simplified binary trie for IP prefix matching
class IPRTrie {
private:
    struct Node {
        Node* child[2] = {nullptr, nullptr};
        bool hasValue = false;
        int nexthop = -1;  // Next hop router ID
    };

    Node* root;

public:
    IPRTrie() : root(new Node()) {}

    // Insert a prefix with a given length and next hop
    void insert(uint32_t prefix, int prefixLen, int nexthop) {
        Node* node = root;
        for (int i = 31; i >= 32 - prefixLen; --i) {
            int bit = (prefix >> i) & 1;
            if (!node->child[bit]) {
                node->child[bit] = new Node();
            }
            node = node->child[bit];
        }
        node->hasValue = true;
        node->nexthop = nexthop;
    }

    // Longest prefix match
    std::optional<int> longestMatch(uint32_t addr) const {
        Node* node = root;
        int bestNexthop = -1;

        for (int i = 31; i >= 0; --i) {
            if (node->hasValue) {
                bestNexthop = node->nexthop;
            }
            int bit = (addr >> i) & 1;
            if (!node->child[bit]) break;
            node = node->child[bit];
        }
        if (node->hasValue) {
            bestNexthop = node->nexthop;
        }

        if (bestNexthop == -1) return std::nullopt;
        return bestNexthop;
    }
};

int main() {
    IPRTrie trie;

    // Insert routing table entries
    trie.insert(0xC0A80000, 16, 1);  // 192.168.0.0/16 -> nexthop 1
    trie.insert(0xC0A80100, 24, 2);  // 192.168.1.0/24 -> nexthop 2
    trie.insert(0x0A000000, 8, 3);   // 10.0.0.0/8 -> nexthop 3

    // Lookup
    uint32_t addr1 = 0xC0A8010A;  // 192.168.1.10
    auto result = trie.longestMatch(addr1);
    if (result) {
        std::cout << "192.168.1.10 -> nexthop " << *result << "\n";  // 2
    }

    uint32_t addr2 = 0xC0A8020A;  // 192.168.2.10
    result = trie.longestMatch(addr2);
    if (result) {
        std::cout << "192.168.2.10 -> nexthop " << *result << "\n";  // 1
    }

    return 0;
}
```

---

## 16.4 Compressed Trie (Patricia Trie)

A standard trie can waste significant memory when many nodes have only a single child. A **compressed trie** (also called **Patricia trie** or **radix tree**) merges chains of single-child nodes into a single edge labeled with a string.

### Before Compression

```
Standard trie for: "romane", "romanus", "romulus", "rubens", "ruber", "rubicon", "rubicundus"

         r
         |
         o
        / \
       m   u
      / \   \
     a   u   b
    / \  |   |
   n   n l   e
   |   | u   |
   e   u s   n
       |     |
       s     s
              |
              (continues...)
```

### After Compression

```
Compressed trie:
         r
        / \
       o   ube
      / \    \
     manu   ns
     / \     \
    e   s   (rest)
    |
    (roman + e)
    (roman + us)
```

### Implementation of Compressed Trie

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>

class CompressedTrie {
private:
    struct Node {
        std::unordered_map<char, std::pair<std::string, Node*>> edges;
        bool isEnd = false;
    };

    Node* root;

    // Find the longest common prefix of two strings
    static std::string commonPrefix(const std::string& a, const std::string& b) {
        int len = std::min(a.size(), b.size());
        int i = 0;
        while (i < len && a[i] == b[i]) ++i;
        return a.substr(0, i);
    }

public:
    CompressedTrie() : root(new Node()) {}

    void insert(const std::string& word) {
        Node* node = root;
        int idx = 0;

        while (idx < static_cast<int>(word.size())) {
            char ch = word[idx];
            if (!node->edges.count(ch)) {
                // No edge starting with this character — create new edge
                node->edges[ch] = {word.substr(idx), new Node()};
                node->edges[ch].second->isEnd = true;
                return;
            }

            auto& [edgeLabel, child] = node->edges[ch];
            std::string prefix = commonPrefix(edgeLabel, word.substr(idx));

            if (prefix.size() == edgeLabel.size()) {
                // Full edge label matches — continue to child
                idx += prefix.size();
                node = child;
            } else {
                // Partial match — need to split the edge
                Node* newNode = new Node();
                std::string remainingEdge = edgeLabel.substr(prefix.size());

                // The existing child becomes a child of the new node
                newNode->edges[remainingEdge[0]] = {remainingEdge, child};

                // The new word continues from the new node
                std::string remainingWord = word.substr(idx + prefix.size());
                if (remainingWord.empty()) {
                    newNode->isEnd = true;
                } else {
                    newNode->edges[remainingWord[0]] = {remainingWord, new Node()};
                    newNode->edges[remainingWord[0]].second->isEnd = true;
                }

                // Replace the old edge with the new shorter edge
                node->edges[ch] = {prefix, newNode};
                return;
            }
        }
        node->isEnd = true;
    }

    bool search(const std::string& word) const {
        Node* node = root;
        int idx = 0;

        while (idx < static_cast<int>(word.size())) {
            char ch = word[idx];
            if (!node->edges.count(ch)) return false;

            const auto& [edgeLabel, child] = node->edges.at(ch);
            std::string remaining = word.substr(idx);

            if (remaining.size() < edgeLabel.size()) return false;
            if (remaining.substr(0, edgeLabel.size()) != edgeLabel) return false;

            idx += edgeLabel.size();
            node = child;
        }
        return node->isEnd;
    }
};

int main() {
    CompressedTrie trie;
    trie.insert("romane");
    trie.insert("romanus");
    trie.insert("romulus");

    std::cout << "Search 'romane': " << (trie.search("romane") ? "yes" : "no") << "\n";
    std::cout << "Search 'roman': " << (trie.search("roman") ? "yes" : "no") << "\n";
    std::cout << "Search 'romulus': " << (trie.search("romulus") ? "yes" : "no") << "\n";

    return 0;
}
```

**Space savings**: If a standard trie has n nodes and many chains of single-child nodes, the compressed trie can reduce the node count significantly. In the extreme case of n distinct single-character strings, both use O(n) nodes. But for strings with shared long prefixes, compression can save 50-90% of nodes.

---

## 16.5 Ternary Search Trie

A **ternary search trie (TST)** is a space-efficient alternative to the standard trie. Instead of 26 children per node, each TST node has exactly three children:

1. **Left**: characters less than the current node's character
2. **Middle**: characters equal to the current node's character (advances to the next character)
3. **Right**: characters greater than the current node's character

### Structure

```
Standard Trie:                    Ternary Search Trie:
Each node has 26 children         Each node has 3 children + 1 character

    root                           root
   / | \ ... \                     (e)
  a  b  c ... z                    / | \
  |  |  |       |                 (a) (m) (r)
  ...                             /|   |\   |\
```

### Implementation

```cpp
#include <iostream>
#include <string>
#include <vector>

class TernarySearchTrie {
private:
    struct Node {
        char ch;
        bool isEnd = false;
        Node* left = nullptr;
        Node* middle = nullptr;
        Node* right = nullptr;

        Node(char c) : ch(c) {}
    };

    Node* root = nullptr;

    Node* insertHelper(Node* node, const std::string& word, int idx) {
        char ch = word[idx];

        if (!node) {
            node = new Node(ch);
        }

        if (ch < node->ch) {
            node->left = insertHelper(node->left, word, idx);
        } else if (ch > node->ch) {
            node->right = insertHelper(node->right, word, idx);
        } else {
            // Characters match
            if (idx + 1 == static_cast<int>(word.size())) {
                node->isEnd = true;
            } else {
                node->middle = insertHelper(node->middle, word, idx + 1);
            }
        }
        return node;
    }

    bool searchHelper(Node* node, const std::string& word, int idx) const {
        if (!node) return false;

        char ch = word[idx];
        if (ch < node->ch) {
            return searchHelper(node->left, word, idx);
        } else if (ch > node->ch) {
            return searchHelper(node->right, word, idx);
        } else {
            if (idx + 1 == static_cast<int>(word.size())) {
                return node->isEnd;
            }
            return searchHelper(node->middle, word, idx + 1);
        }
    }

    void collectWords(Node* node, std::string& current,
                      std::vector<std::string>& result) const {
        if (!node) return;

        collectWords(node->left, current, result);

        current.push_back(node->ch);
        if (node->isEnd) {
            result.push_back(current);
        }
        collectWords(node->middle, current, result);
        current.pop_back();

        collectWords(node->right, current, result);
    }

public:
    void insert(const std::string& word) {
        if (!word.empty()) {
            root = insertHelper(root, word, 0);
        }
    }

    bool search(const std::string& word) const {
        if (word.empty()) return false;
        return searchHelper(root, word, 0);
    }

    std::vector<std::string> wordsWithPrefix(const std::string& prefix) const {
        std::vector<std::string> result;
        Node* node = root;
        int idx = 0;

        // Navigate to the end of the prefix
        while (node && idx < static_cast<int>(prefix.size())) {
            char ch = prefix[idx];
            if (ch < node->ch) {
                node = node->left;
            } else if (ch > node->ch) {
                node = node->right;
            } else {
                idx++;
                if (idx < static_cast<int>(prefix.size())) {
                    node = node->middle;
                }
            }
        }

        if (!node || idx != static_cast<int>(prefix.size())) return result;

        // Collect all words from this node's middle subtree
        std::string current = prefix;
        collectWords(node->middle, current, result);

        // The prefix itself might be a word
        if (node->isEnd) {
            result.insert(result.begin(), prefix);
        }

        return result;
    }
};

int main() {
    TernarySearchTrie tst;
    std::vector<std::string> words = {"apple", "app", "application", "bat", "ball", "band"};
    for (const auto& w : words) {
        tst.insert(w);
    }

    std::cout << "Search 'app': " << (tst.search("app") ? "yes" : "no") << "\n";
    std::cout << "Search 'ap': " << (tst.search("ap") ? "yes" : "no") << "\n";

    auto suggestions = tst.wordsWithPrefix("app");
    std::cout << "Words with prefix 'app': ";
    for (const auto& s : suggestions) std::cout << s << " ";
    std::cout << "\n";

    return 0;
}
```

### Comparison: Standard Trie vs Compressed Trie vs TST

| Property | Standard Trie | Compressed Trie | Ternary Search Trie |
|----------|--------------|-----------------|---------------------|
| Children per node | 26 (or 256) | Variable | 3 |
| Space (worst case) | O(26·n·m) | O(n·m) | O(3·n·m) |
| Space (typical) | High | Low | Medium |
| Search time | O(m) | O(m) | O(m + log n) worst case |
| Prefix search | Excellent | Excellent | Good |
| Implementation | Simple | Complex | Moderate |
| Cache performance | Good | Good | Poor (pointer chasing) |

**When to use TST**: When memory is a concern and the alphabet is large (e.g., Unicode strings). TSTs use significantly less memory than standard tries for sparse datasets.

**When to use standard trie**: When alphabet size is small (a-z), speed is critical, and memory is abundant.

**When to use compressed trie**: When strings have long shared prefixes and memory efficiency matters (e.g., file systems, URL routing).

---

## Interview Tips

1. **Recognize trie problems by keywords**: "prefix", "autocomplete", "spell check", "word search", "dictionary", "starts with", "replace words".

2. **Trie vs Hash Map**: Use a trie when you need prefix-based operations. Use a hash map for exact lookups only.

3. **Space optimization**: If the alphabet is large, consider using a hash map for children instead of an array. If strings share long prefixes, consider a compressed trie.

4. **Common patterns**:
   - Build a trie from a dictionary, then traverse it for each query
   - Use DFS on a trie to enumerate all matching words
   - Track additional metadata at each node (count, frequency, etc.)

5. **Word Search II (LeetCode 211)**: Build a trie from the word list, then DFS the grid using the trie for efficient pruning. This is a classic trie + backtracking problem.

6. **Memory management**: In interviews, mention that you'd use `unique_ptr` in production code. In competitive programming, raw pointers with manual cleanup (or just leak — it's a contest) are fine.

## Common Mistakes

1. **Forgetting to mark end-of-word**: A node being non-null doesn't mean it's the end of a word. Always maintain a separate `isEnd` flag.

2. **Not handling empty strings**: Decide upfront whether your trie supports empty strings. Most implementations don't.

3. **Memory leaks**: Tries allocate many small nodes. Use smart pointers or implement a destructor that recursively frees all nodes.

4. **Confusing prefix search with exact search**: `startsWith("app")` returns true if any word has prefix "app". `search("app")` returns true only if "app" is a complete word in the trie.

5. **Assuming trie is always faster than hash map**: For exact lookups on short strings, a hash map can be faster due to better cache locality. Tries shine for prefix operations.

6. **Not considering the alphabet size**: A fixed array of 26 children wastes memory for sparse datasets. Use a hash map when the alphabet is large or the trie is sparse.

---

## Practice Problems

### Problem 1: Implement Trie (LeetCode 208)
**Difficulty**: Medium
**Hint**: Implement insert, search, and startsWith. Use an array of 26 children per node.

### Problem 2: Word Search II (LeetCode 212)
**Difficulty**: Hard
**Hint**: Build a trie from the word list. DFS the grid, following trie edges. Prune branches that don't correspond to any trie path. Remove found words from the trie to avoid duplicates.

### Problem 3: Replace Words (LeetCode 648)
**Difficulty**: Medium
**Hint**: Build a trie from the dictionary. For each word in the sentence, find the shortest prefix that is a dictionary root.

### Problem 4: Map Sum Pairs (LeetCode 677)
**Difficulty**: Medium
**Hint**: Use a trie where each node stores the sum of all values with that prefix. On insert, update all nodes along the path.

### Problem 5: Longest Word in Dictionary (LeetCode 720)
**Difficulty**: Medium
**Hint**: Build a trie. DFS to find the longest word where every prefix is also in the trie.

### Problem 6: Design Add and Search Words Data Structure (LeetCode 211)
**Difficulty**: Medium
**Hint**: Use a trie. For '.' characters, recursively search all children. This requires DFS with backtracking.

### Problem 7: Maximum XOR of Two Numbers in an Array (LeetCode 421)
**Difficulty**: Medium
**Hint**: Build a binary trie of all numbers (32 bits). For each number, greedily walk the trie choosing the opposite bit at each level to maximize XOR.

### Problem 8: Stream of Characters (LeetCode 1032)
**Difficulty**: Hard
**Hint**: Build a trie of reversed words. For each incoming character, walk the trie of the current suffix (reversed) and check if any reversed word matches.

---

*Next chapter: [Chapter 17: Disjoint Set Union](ch17-dsu.md)*
