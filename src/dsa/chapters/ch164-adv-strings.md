# Chapter 164: Advanced String Processing

## Prerequisites
- Suffix arrays and suffix trees (Chapter 158)
- BWT and FM-Index (Chapter 120)
- Compression basics (Chapter 119)
- Dynamic programming (Chapter 45)

## Interview Frequency: ★

Advanced string processing techniques enable efficient compression, pattern matching on compressed data, and dynamic string maintenance. These methods appear in systems programming, bioinformatics, and large-scale text search engines.

---

## 164.1 Grammar Compression

### Definition

Grammar compression represents a string as a context-free grammar (CFG) that generates exactly that string. The goal is to find the smallest grammar — the one with the fewest production rules.

### Motivation

When dealing with massive repetitive datasets (version control histories, genomic repeats, web archives), storing the full string wastes space. Grammar compression captures repeated structure concisely.

### Intuition

Think of the string `abcabcabcabc`. Instead of storing all 12 characters, we can write:

```
S → X X
X → A B
A → a
B → b c
```

Each rule captures a repeated substring. Larger repetitions compress further by reusing non-terminals.

### Formal Explanation

A straight-line program (SLP) is a CFG in Chomsky normal form where each non-terminal appears on the left side of exactly one rule, and rules are ordered so that every non-terminal is defined before it is used. The size of an SLP is the total length of all right-hand sides.

**Theorem**: Finding the smallest SLP for a given string is NP-hard (Charikar et al., 2005). However, approximation algorithms achieve O(log(n/g*)) times optimal, where g* is the optimal grammar size.

### Key Algorithms

| Algorithm | Approximation Ratio | Time Complexity |
|---|---|---|
| RePair | O(log(n/g*)) | O(n) |
| Sequitur | O(log(n/g*)) | O(n) |
| BISECTION | O(log(n/g*)) | O(n log n) |
| LZ-based | O(log² n) | O(n) |

### RePair Algorithm Walkthrough

1. Scan the string for the most frequent bigram (pair of adjacent symbols).
2. Replace all occurrences of that bigram with a new non-terminal.
3. Record the rule: non-terminal → bigram.
4. Repeat until no bigram appears more than once.

**Dry Run** on `abcabcabcabc`:

| Step | Most Frequent Bigram | Replacement | Rules |
|---|---|---|---|
| 1 | ab | ab → X | X → ab |
| 2 | Xc | Xc → Y | Y → Xc |
| 3 | YY | YY → Z | Z → YY |

Result: `S → Z Z`, which is much smaller than the original 12 characters.

### Complexity Analysis

| Operation | Time | Space |
|---|---|---|
| RePair construction | O(n) | O(n) |
| Decompression | O(output size) | O(grammar size) |
| Random access | O(log n) | O(grammar size) |

### Code Example (C++)

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>

// Simple RePair-style grammar compression
struct GrammarRule {
    char nonTerminal;
    std::string expansion;
};

class GrammarCompressor {
public:
    std::vector<GrammarRule> rules;
    std::string startSymbol;
    int nextId = 'A';

    std::string compress(const std::string& s) {
        std::string current = s;
        while (true) {
            // Find most frequent bigram
            std::map<std::string, int> freq;
            for (int i = 0; i + 1 < (int)current.size(); i++) {
                std::string bigram = current.substr(i, 2);
                // Only count bigrams of terminal symbols
                if (bigram[0] >= 'a' && bigram[0] <= 'z' &&
                    bigram[1] >= 'a' && bigram[1] <= 'z')
                    freq[bigram]++;
            }

            if (freq.empty()) break;

            auto best = std::max_element(freq.begin(), freq.end(),
                [](auto& a, auto& b) { return a.second < b.second; });

            if (best->second < 2) break; // No repeated bigrams

            // Replace all occurrences
            char nt = nextId++;
            std::string bigram = best->first;
            rules.push_back({nt, bigram});

            std::string next;
            for (int i = 0; i < (int)current.size(); i++) {
                if (i + 1 < (int)current.size() &&
                    current.substr(i, 2) == bigram) {
                    next += nt;
                    i++; // Skip second character
                } else {
                    next += current[i];
                }
            }
            current = next;
        }
        startSymbol = current;
        return current;
    }

    std::string decompress() const {
        return expand(startSymbol);
    }

private:
    std::string expand(const std::string& s) const {
        std::string result;
        for (char c : s) {
            bool isNonTerminal = false;
            for (auto& r : rules) {
                if (r.nonTerminal == c) {
                    result += expand(r.expansion);
                    isNonTerminal = true;
                    break;
                }
            }
            if (!isNonTerminal) result += c;
        }
        return result;
    }
};

int main() {
    std::string s = "abcabcabcabc";
    GrammarCompressor gc;
    std::string compressed = gc.compress(s);

    std::cout << "Original: \"" << s << "\" (" << s.size() << " chars)\n";
    std::cout << "Compressed: \"" << compressed << "\" (" << compressed.size() << " chars)\n";
    std::cout << "Grammar rules:\n";
    for (auto& r : gc.rules)
        std::cout << "  " << r.nonTerminal << " -> " << r.expansion << "\n";
    std::cout << "Decompressed: \"" << gc.decompress() << "\"\n";

    return 0;
}
```

### Code Example (Python)

```python
class GrammarCompressor:
    def __init__(self):
        self.rules = []
        self.next_id = ord('A')

    def compress(self, s):
        current = s
        while True:
            # Find most frequent bigram of terminals
            freq = {}
            for i in range(len(current) - 1):
                bigram = current[i:i+2]
                if bigram.isalpha() and bigram.islower():
                    freq[bigram] = freq.get(bigram, 0) + 1

            if not freq:
                break

            best_bigram = max(freq, key=freq.get)
            if freq[best_bigram] < 2:
                break

            nt = chr(self.next_id)
            self.next_id += 1
            self.rules.append((nt, best_bigram))

            # Replace all occurrences
            next_str = []
            i = 0
            while i < len(current):
                if i + 1 < len(current) and current[i:i+2] == best_bigram:
                    next_str.append(nt)
                    i += 2
                else:
                    next_str.append(current[i])
                    i += 1
            current = ''.join(next_str)

        self.start = current
        return current

    def decompress(self):
        return self._expand(self.start)

    def _expand(self, s):
        rule_map = {nt: exp for nt, exp in self.rules}
        result = []
        for c in s:
            if c in rule_map:
                result.append(self._expand(rule_map[c]))
            else:
                result.append(c)
        return ''.join(result)


gc = GrammarCompressor()
original = "abcabcabcabc"
compressed = gc.compress(original)
print(f"Original: {original} ({len(original)} chars)")
print(f"Compressed: {compressed} ({len(compressed)} chars)")
print(f"Rules: {gc.rules}")
print(f"Decompressed: {gc.decompress()}")
```

### Code Example (Java)

```java
import java.util.*;

public class GrammarCompressor {
    static class Rule {
        char nt;
        String expansion;
        Rule(char nt, String exp) { this.nt = nt; this.expansion = exp; }
    }

    List<Rule> rules = new ArrayList<>();
    int nextId = 'A';
    String start;

    public String compress(String s) {
        String current = s;
        while (true) {
            Map<String, Integer> freq = new HashMap<>();
            for (int i = 0; i + 1 < current.length(); i++) {
                String bigram = current.substring(i, i + 2);
                if (bigram.matches("[a-z]{2}"))
                    freq.merge(bigram, 1, Integer::sum);
            }
            if (freq.isEmpty()) break;

            String best = freq.entrySet().stream()
                .max(Map.Entry.comparingByValue())
                .get().getKey();
            if (freq.get(best) < 2) break;

            char nt = (char) nextId++;
            rules.add(new Rule(nt, best));

            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < current.length(); i++) {
                if (i + 1 < current.length() &&
                    current.substring(i, i + 2).equals(best)) {
                    sb.append(nt);
                    i++;
                } else {
                    sb.append(current.charAt(i));
                }
            }
            current = sb.toString();
        }
        start = current;
        return current;
    }

    public String decompress() { return expand(start); }

    private String expand(String s) {
        Map<Character, String> ruleMap = new HashMap<>();
        for (Rule r : rules) ruleMap.put(r.nt, r.expansion);
        StringBuilder sb = new StringBuilder();
        for (char c : s.toCharArray()) {
            if (ruleMap.containsKey(c)) sb.append(expand(ruleMap.get(c)));
            else sb.append(c);
        }
        return sb.toString();
    }

    public static void main(String[] args) {
        GrammarCompressor gc = new GrammarCompressor();
        String original = "abcabcabcabc";
        String compressed = gc.compress(original);
        System.out.println("Original: " + original + " (" + original.length() + ")");
        System.out.println("Compressed: " + compressed + " (" + compressed.length() + ")");
        System.out.println("Decompressed: " + gc.decompress());
    }
}
```

---

## 164.2 Lempel-Ziv Family

### Definition

The Lempel-Ziv (LZ) family of algorithms compresses data by replacing repeated occurrences with references to previous instances. They form the backbone of most practical compression tools.

### Motivation

Real-world data contains patterns and repetitions. LZ algorithms exploit this by encoding "we saw this before at position X" instead of repeating the data.

### Intuition

Imagine reading a book aloud. When you encounter a phrase you've said before, instead of repeating it, you say "go back 50 words and copy the next 10 words." The listener reconstructs the original. LZ compression works the same way.

### Algorithm Comparison

| Algorithm | Year | Reference Type | Dictionary | Used In |
|---|---|---|---|---|
| LZ77 | 1977 | (offset, length) | Sliding window | gzip, PNG, ZIP |
| LZ78 | 1978 | Dictionary index | Growing dictionary | LZW |
| LZW | 1984 | Dictionary index | Implicit | GIF, TIFF, early modems |
| LZMA | 1998 | (offset, length) + range coder | Large window | 7-Zip, xz |
| Zstandard | 2013 | (offset, length) + Huffman | Large window | Modern systems |

### LZ77 Detailed Walkthrough

**Input**: `abracadabra`

**Window size**: 20 characters

| Position | Best Match | Token | Meaning |
|---|---|---|---|
| 0 | — | (0, 0, 'a') | No match, literal 'a' |
| 1 | — | (0, 0, 'b') | No match, literal 'b' |
| 2 | — | (0, 0, 'r') | No match, literal 'r' |
| 3 | — | (0, 0, 'a') | No match, literal 'a' |
| 4 | — | (0, 0, 'c') | No match, literal 'c' |
| 5 | — | (0, 0, 'a') | No match, literal 'a' |
| 6 | — | (0, 0, 'd') | No match, literal 'd' |
| 7 | (4, 4, 'b') | Copy 4 chars from offset 4 → "abra" | Then literal 'b' |
| 11 | — | — | End of string |

The key insight: at position 7, we find "abra" matching position 3-6 (offset 4, length 4), followed by 'b'.

### Complexity Analysis

| Operation | LZ77 | LZ78 | LZW |
|---|---|---|---|
| Compression | O(n × window) | O(n × dict_size) | O(n) |
| Decompression | O(n) | O(n) | O(n) |
| Space | O(window) | O(dict_size) | O(dict_size) |

### Code Example (C++)

```cpp
#include <iostream>
#include <string>
#include <vector>
#include <map>

struct LZ77Token {
    int offset;
    int length;
    char next;
};

std::vector<LZ77Token> lz77Compress(const std::string& s, int windowSize = 20) {
    std::vector<LZ77Token> tokens;
    int pos = 0;

    while (pos < (int)s.size()) {
        int bestOffset = 0, bestLength = 0;

        // Search in the sliding window
        int start = std::max(0, pos - windowSize);
        for (int i = start; i < pos; i++) {
            int len = 0;
            while (pos + len < (int)s.size() && s[i + len] == s[pos + len])
                len++;
            if (len > bestLength) {
                bestLength = len;
                bestOffset = pos - i;
            }
        }

        char next = (pos + bestLength < (int)s.size()) ? s[pos + bestLength] : '\0';
        tokens.push_back({bestOffset, bestLength, next});
        pos += bestLength + 1;
    }

    return tokens;
}

std::string lz77Decompress(const std::vector<LZ77Token>& tokens) {
    std::string result;
    for (auto& t : tokens) {
        int start = result.size() - t.offset;
        for (int i = 0; i < t.length; i++)
            result += result[start + i];
        if (t.next != '\0') result += t.next;
    }
    return result;
}

// LZW Compression
std::vector<int> lzwCompress(const std::string& s) {
    std::map<std::string, int> dict;
    for (int i = 0; i < 256; i++)
        dict[std::string(1, (char)i)] = i;

    std::vector<int> result;
    std::string w;
    int nextCode = 256;

    for (char c : s) {
        std::string wc = w + c;
        if (dict.count(wc)) {
            w = wc;
        } else {
            result.push_back(dict[w]);
            dict[wc] = nextCode++;
            w = std::string(1, c);
        }
    }
    if (!w.empty()) result.push_back(dict[w]);

    return result;
}

std::string lzwDecompress(const std::vector<int>& codes) {
    std::vector<std::string> dict(256);
    for (int i = 0; i < 256; i++)
        dict[i] = std::string(1, (char)i);

    std::string w(1, (char)codes[0]);
    std::string result = w;
    int nextCode = 256;

    for (int i = 1; i < (int)codes.size(); i++) {
        int k = codes[i];
        std::string entry;
        if (k < (int)dict.size() && !dict[k].empty())
            entry = dict[k];
        else if (k == nextCode)
            entry = w + w[0];
        else
            throw std::runtime_error("Bad compressed code");

        result += entry;
        dict.push_back(w + entry[0]);
        nextCode++;
        w = entry;
    }

    return result;
}

int main() {
    std::string s = "abracadabra";

    // LZ77
    auto tokens = lz77Compress(s);
    std::cout << "LZ77 for \"" << s << "\":\n";
    for (auto& t : tokens)
        std::cout << "  (" << t.offset << ", " << t.length << ", '" << t.next << "')\n";
    std::cout << "Decompressed: \"" << lz77Decompress(tokens) << "\"\n\n";

    // LZW
    std::string lzwInput = "TOBEORNOTTOBEORTOBEORNOT";
    auto codes = lzwCompress(lzwInput);
    std::cout << "LZW codes for \"" << lzwInput << "\":\n  ";
    for (int c : codes) std::cout << c << " ";
    std::cout << "\nDecompressed: \"" << lzwDecompress(codes) << "\"\n";

    return 0;
}
```

### Code Example (Python)

```python
def lz77_compress(s, window_size=20):
    """LZ77 compression returning list of (offset, length, next_char) tokens."""
    tokens = []
    pos = 0
    while pos < len(s):
        best_offset, best_length = 0, 0
        start = max(0, pos - window_size)
        for i in range(start, pos):
            length = 0
            while pos + length < len(s) and s[i + length] == s[pos + length]:
                length += 1
            if length > best_length:
                best_length = length
                best_offset = pos - i
        next_char = s[pos + best_length] if pos + best_length < len(s) else ''
        tokens.append((best_offset, best_length, next_char))
        pos += best_length + 1
    return tokens


def lz77_decompress(tokens):
    """Decompress LZ77 tokens back to original string."""
    result = []
    for offset, length, next_char in tokens:
        start = len(result) - offset
        for i in range(length):
            result.append(result[start + i])
        if next_char:
            result.append(next_char)
    return ''.join(result)


def lzw_compress(s):
    """LZW compression returning list of integer codes."""
    dictionary = {chr(i): i for i in range(256)}
    result = []
    w = ""
    next_code = 256
    for c in s:
        wc = w + c
        if wc in dictionary:
            w = wc
        else:
            result.append(dictionary[w])
            dictionary[wc] = next_code
            next_code += 1
            w = c
    if w:
        result.append(dictionary[w])
    return result


def lzw_decompress(codes):
    """Decompress LZW codes back to original string."""
    dictionary = {i: chr(i) for i in range(256)}
    result = [chr(codes[0])]
    w = result[0]
    next_code = 256
    for code in codes[1:]:
        if code in dictionary:
            entry = dictionary[code]
        elif code == next_code:
            entry = w + w[0]
        else:
            raise ValueError(f"Invalid code: {code}")
        result.append(entry)
        dictionary[next_code] = w + entry[0]
        next_code += 1
        w = entry
    return ''.join(result)


# Demo
s = "abracadabra"
tokens = lz77_compress(s)
print(f"LZ77 tokens for '{s}': {tokens}")
print(f"Decompressed: '{lz77_decompress(tokens)}'")

lzw_input = "TOBEORNOTTOBEORTOBEORNOT"
codes = lzw_compress(lzw_input)
print(f"LZW codes for '{lzw_input}': {codes}")
print(f"Decompressed: '{lzw_decompress(codes)}'")
```

### Code Example (Java)

```java
import java.util.*;

public class LZCompression {
    // LZ77 Token
    static class Token {
        int offset, length;
        char next;
        Token(int o, int l, char n) { offset = o; length = l; next = n; }
        public String toString() { return "(" + offset + "," + length + ",'" + next + "')"; }
    }

    static List<Token> lz77Compress(String s, int windowSize) {
        List<Token> tokens = new ArrayList<>();
        int pos = 0;
        while (pos < s.length()) {
            int bestOff = 0, bestLen = 0;
            int start = Math.max(0, pos - windowSize);
            for (int i = start; i < pos; i++) {
                int len = 0;
                while (pos + len < s.length() && s.charAt(i + len) == s.charAt(pos + len))
                    len++;
                if (len > bestLen) { bestLen = len; bestOff = pos - i; }
            }
            char next = (pos + bestLen < s.length()) ? s.charAt(pos + bestLen) : '\0';
            tokens.add(new Token(bestOff, bestLen, next));
            pos += bestLen + 1;
        }
        return tokens;
    }

    static String lz77Decompress(List<Token> tokens) {
        StringBuilder sb = new StringBuilder();
        for (Token t : tokens) {
            int start = sb.length() - t.offset;
            for (int i = 0; i < t.length; i++)
                sb.append(sb.charAt(start + i));
            if (t.next != '\0') sb.append(t.next);
        }
        return sb.toString();
    }

    public static void main(String[] args) {
        String s = "abracadabra";
        List<Token> tokens = lz77Compress(s, 20);
        System.out.println("LZ77 for \"" + s + "\": " + tokens);
        System.out.println("Decompressed: \"" + lz77Decompress(tokens) + "\"");
    }
}
```

---

## 164.3 Compressed Pattern Matching

### Definition

Search for a pattern directly within a compressed representation of the text, without full decompression.

### Motivation

When searching through terabytes of compressed logs or genomic databases, decompressing everything first is prohibitively expensive. Compressed pattern matching avoids this overhead.

### Key Results

| Method | Compression | Search Time | Space |
|---|---|---|---|
| BWT + FM-Index | nH₀ bits | O(m) | O(n) |
| LZ77 index | O(r log n) | O(m² + occ) | O(r) |
| Grammar index | O(g log n) | O(m² log n + occ log² n) | O(g log n) |

Where n = text length, m = pattern length, occ = number of occurrences, r = number of LZ77 phrases, g = grammar size, H₀ = zero-order entropy.

### FM-Index Search (from Chapter 120)

The FM-Index enables O(m) pattern matching on BWT-compressed text using:
- **backwardSearch**: Process pattern characters right-to-left
- **LF-mapping**: Navigate between BWT and first column
- **Occurrence tables**: O(1) rank queries

### Walkthrough: Searching in BWT

Given BWT of `banana$` = `annb$aa`, search for pattern `ana`:

1. Start with range [0, 6) for all characters
2. Process 'a' (last char of pattern): range narrows to rows starting with 'a'
3. Process 'n': range narrows to rows starting with 'na'
4. Process 'a': range narrows to rows starting with 'ana'
5. Final range gives suffix array positions of all occurrences

---

## 164.4 Dynamic String Algorithms

### Definition

Maintain string data structures (suffix arrays, LCP arrays, suffix trees) under character insertions and deletions.

### Motivation

Real-world text is not static — documents are edited, databases are updated, and streaming data arrives continuously. Recomputing from scratch after each update is too slow.

### Key Results

| Structure | Update Time | Query Time | Space |
|---|---|---|---|
| Dynamic suffix array | O(log² n) | O(m + log n) | O(n) |
| Dynamic LCP | O(log n) | O(1) | O(n) |
| Rolling hash | O(1) | O(1) | O(n) |
| Dynamic suffix tree | O(log² n) | O(m) | O(n) |

### Rolling Hash

A rolling hash allows computing the hash of a sliding window in O(1) per shift:

```
h(s[i..i+k]) = (h(s[i..i+k-1]) - s[i] × B^(k-1)) × B + s[i+k]
```

This is the foundation of Rabin-Karp string matching and content-defined chunking.

### Code Example (Python — Rolling Hash)

```python
class RollingHash:
    def __init__(self, s, base=257, mod=10**18 + 9):
        self.base = base
        self.mod = mod
        self.n = len(s)
        self.h = [0] * (self.n + 1)
        self.powers = [1] * (self.n + 1)

        for i in range(self.n):
            self.h[i + 1] = (self.h[i] * base + ord(s[i])) % mod
            self.powers[i + 1] = (self.powers[i] * base) % mod

    def get_hash(self, l, r):
        """Get hash of s[l:r] (0-indexed, exclusive r)."""
        return (self.h[r] - self.h[l] * self.powers[r - l]) % self.mod

    def update(self, pos, old_char, new_char):
        """Update character at position pos (rebuild needed for full update)."""
        pass  # Full rebuild needed for arbitrary updates


def rabin_karp(text, pattern):
    """Find all occurrences of pattern in text using rolling hash."""
    n, m = len(text), len(pattern)
    if m > n:
        return []

    base, mod = 257, 10**18 + 9

    # Compute pattern hash
    pattern_hash = 0
    for c in pattern:
        pattern_hash = (pattern_hash * base + ord(c)) % mod

    # Compute initial window hash
    window_hash = 0
    for i in range(m):
        window_hash = (window_hash * base + ord(text[i])) % mod

    # Precompute base^(m-1)
    power = pow(base, m - 1, mod)

    matches = []
    for i in range(n - m + 1):
        if window_hash == pattern_hash and text[i:i + m] == pattern:
            matches.append(i)
        if i < n - m:
            window_hash = ((window_hash - ord(text[i]) * power) * base + ord(text[i + m])) % mod

    return matches


# Demo
text = "aabaabaabaab"
pattern = "aab"
matches = rabin_karp(text, pattern)
print(f"Pattern '{pattern}' found at positions: {matches}")
```

---

## 164.5 Practical Applications

| Domain | Technique | Tool/Library |
|---|---|---|
| Bioinformatics | Compressed FM-Index | BWA, Bowtie2 |
| Version control | Delta compression | Git, Mercurial |
| File systems | Deduplication | ZFS, btrfs |
| Web caching | Content-defined chunking | rsync, LBFS |
| Log compression | LZ4, Zstandard | Kafka, Elasticsearch |

---

## Exercises

### Exercise 1: Implement LZ78 Compression
Implement the LZ78 compression algorithm. Compare its compression ratio with LZ77 on the string `ABABCBABABC`.

**Hint**: LZ78 builds a dictionary incrementally. Each token is (dictionary_index, next_character).

### Exercise 2: Grammar Compression Analysis
Given the string `abcabcabcabcabcabc`, trace through the RePair algorithm and show the final grammar. How many rules are needed?

### Exercise 3: FM-Index Search
Given the BWT of `mississippi$`, which is `ipssm$pissii`, trace the backward search for the pattern `issi`. Show the range narrowing at each step.

### Exercise 4: Rolling Hash Collisions
Implement a double-hashing scheme (two different bases/moduli) for Rabin-Karp. Test it on a large random text to verify that false positives are eliminated.

### Exercise 5: LZW Dictionary Growth
For the input `ABRACADABRABRACADABRA`, trace the LZW dictionary after processing each character. What is the final dictionary size?

---

## Interview Questions

### Question 1: Why does BWT enable good compression?
**Answer**: BWT groups identical characters together by sorting cyclic rotations. This creates runs of repeated characters, which compress extremely well with run-length encoding. The LF-mapping property allows reconstruction without storing the full sorted rotations.

### Question 2: What is the advantage of LZ77 over LZ78?
**Answer**: LZ77 uses a sliding window and doesn't require maintaining a growing dictionary, making it memory-efficient for streaming data. LZ78's dictionary can grow unboundedly. LZ77 is preferred in practice (gzip, ZIP) because the window size provides a natural memory bound.

### Question 3: How would you search for a pattern in a gzip-compressed file?
**Answer**: Use an FM-Index if the data was BWT-compressed, or use the LZ77 index approach: decompress phrase by phrase and search incrementally. For gzip (LZ77 + Huffman), you must partially decompress, but you can skip phrases whose references don't overlap with the search window.

### Question 4: Explain the difference between static and dynamic string data structures.
**Answer**: Static structures (suffix array, suffix tree) are built once and support queries but not modifications. Dynamic structures support character insertions/deletions with polylogarithmic update time, typically using balanced BSTs or similar techniques. The trade-off is higher per-query cost and implementation complexity.

### Question 5: When would you use grammar compression over LZ77?
**Answer**: Grammar compression excels on highly repetitive data with long-range dependencies (e.g., versioned documents, XML dumps). LZ77 is better for general-purpose compression with local repetitions. Grammar compression also enables certain compressed computations (e.g., pattern matching) that LZ77 cannot support directly.

---

## Cross-References

- **Suffix Arrays** (Chapter 158): Foundation for BWT construction and FM-Index
- **BWT and FM-Index** (Chapter 120): Core compressed indexing technique
- **Suffix Trees** (Chapter 159): Alternative to suffix arrays with different trade-offs
- **Rolling Hash** (Chapter 120): Used in Rabin-Karp and content-defined chunking
- **Compression** (Chapter 119): General compression theory and Huffman coding
- **Dynamic Programming** (Chapter 45): Foundation for many string algorithms
- **Graph Algorithms** (Chapters 97-105): Applications in text networks and social graphs

---

## Summary

| Technique | Compression | Search Time | Notes |
|---|---|---|---|
| BWT + RLE | Repetitive text | O(m) | Static |
| LZ77/LZW | General | Decompress + search | Streaming-friendly |
| Grammar | Highly repetitive | Various | NP-hard to optimize |
| FM-Index | nH_k bits | O(m) | Succinct |
| Rolling Hash | — | O(n + m) | Foundation for dynamic methods |
