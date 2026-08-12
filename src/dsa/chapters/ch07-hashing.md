# Chapter 7: Hashing

Hashing is one of the most powerful techniques in computer science. It enables **O(1) average-case** lookups, insertions, and deletions — transforming many O(n²) problems into O(n) solutions. Understanding hash tables deeply, including how they handle collisions and how to design good hash functions, is essential for interviews.

---

## 7.1 What Is Hashing?

### The Problem

Imagine you have a phone book with millions of entries. How do you look up a name quickly?

- **Array:** O(n) — scan through all entries.
- **Sorted array + binary search:** O(log n).
- **Hash table:** O(1) average — go directly to the right entry!

### The Key-Value Idea

A hash table stores **key-value pairs**. The key is mapped to an index in an array using a **hash function**:

```
Key → Hash Function → Index → Value

"Alice" → hash("Alice") % 10 → 3 → "555-1234"
"Bob"   → hash("Bob")   % 10 → 7 → "555-5678"
```

### How It Works

1. You have an array of size `m` (the "buckets").
2. A hash function `h(key)` maps each key to an index in `[0, m-1]`.
3. To store `(key, value)`: compute `h(key)`, store at that index.
4. To retrieve `key`: compute `h(key)`, look at that index.

**The challenge:** Two different keys might hash to the same index. This is called a **collision**, and how we handle collisions defines the performance of the hash table.

---

## 7.2 Hash Functions

### Properties of a Good Hash Function

1. **Deterministic:** Same key always produces the same hash.
2. **Uniform:** Keys are distributed evenly across buckets.
3. **Fast to compute:** O(1) or O(key length).
4. **Avalanche effect:** Small changes in key → large changes in hash.

### Division Method

\\[h(k) = k \mod m\\]

Where m is the table size (ideally a prime number).

```cpp
#include <iostream>

int hashDivision(int key, int tableSize) {
    return key % tableSize;
}

int main() {
    int m = 11;  // Prime number
    for (int key : {10, 22, 31, 4, 15, 28, 17, 88}) {
        std::cout << "hash(" << key << ") = " << hashDivision(key, m) << std::endl;
    }
    return 0;
}
```

**Why prime m?** If m is a power of 2, `k % m` only uses the low-order bits of k, ignoring the high-order bits. A prime m uses all bits of k, giving better distribution.

### Multiplication Method

\\[h(k) = \lfloor m \cdot (k \cdot A \mod 1) \rfloor\\]

Where A is an irrational constant (commonly the golden ratio conjugate: A = (√5 - 1) / 2 ≈ 0.6180339887).

```cpp
#include <iostream>
#include <cmath>

int hashMultiplication(int key, int tableSize) {
    const double A = 0.6180339887;  // Golden ratio conjugate
    double val = key * A;
    double fractional = val - std::floor(val);
    return static_cast<int>(std::floor(tableSize * fractional));
}

int main() {
    int m = 16;  // Can be a power of 2
    for (int key : {10, 22, 31, 4, 15, 28, 17, 88}) {
        std::cout << "hash(" << key << ") = " << hashMultiplication(key, m) << std::endl;
    }
    return 0;
}
```

### Hashing Strings

For string keys, we use a **polynomial hash**:

\\[h(s) = \left(\sum_{i=0}^{n-1} s[i] \cdot p^i\right) \mod m\\]

Where p is a prime base (commonly 31 or 131).

```cpp
#include <iostream>
#include <string>

long long hashString(const std::string& s, int tableSize) {
    const int P = 31;
    long long hash = 0;
    long long pPow = 1;

    for (char c : s) {
        hash = (hash + (c - 'a' + 1) * pPow) % tableSize;
        pPow = (pPow * P) % tableSize;
    }

    return hash;
}

int main() {
    int m = 100003;  // Large prime
    std::cout << "hash(\"hello\") = " << hashString("hello", m) << std::endl;
    std::cout << "hash(\"world\") = " << hashString("world", m) << std::endl;
    std::cout << "hash(\"abc\")   = " << hashString("abc", m) << std::endl;
    std::cout << "hash(\"cba\")   = " << hashString("cba", m) << std::endl;
    // Note: "abc" and "cba" will likely have different hashes
    return 0;
}
```

### Universal Hashing

A family of hash functions where the probability of collision is at most 1/m for any two distinct keys, chosen randomly:

\\[h_{a,b}(k) = ((a \cdot k + b) \mod p) \mod m\\]

Where p is a prime > max key value, and a, b are randomly chosen from [1, p-1] and [0, p-1].

This provides **expected** O(1) operations regardless of the input distribution.

---

## 7.3 Collision Resolution

### Chaining (Open Hashing)

Each bucket contains a linked list (or vector) of entries that hash to the same index.

```
Index 0: → NULL
Index 1: → (Alice, 555-1234) → NULL
Index 2: → (Charlie, 555-9999) → (Eve, 555-0000) → NULL
Index 3: → (Bob, 555-5678) → NULL
Index 4: → NULL
```

```cpp
#include <iostream>
#include <vector>
#include <list>
#include <string>

class HashTableChaining {
    static const int TABLE_SIZE = 11;
    std::vector<std::list<std::pair<int, std::string>>> table;

public:
    HashTableChaining() : table(TABLE_SIZE) {}

    void insert(int key, const std::string& value) {
        int idx = key % TABLE_SIZE;
        // Check if key already exists
        for (auto& [k, v] : table[idx]) {
            if (k == key) {
                v = value;  // Update
                return;
            }
        }
        table[idx].emplace_back(key, value);
    }

    std::string search(int key) {
        int idx = key % TABLE_SIZE;
        for (auto& [k, v] : table[idx]) {
            if (k == key) return v;
        }
        return "NOT FOUND";
    }

    void remove(int key) {
        int idx = key % TABLE_SIZE;
        table[idx].remove_if([key](const auto& p) { return p.first == key; });
    }
};

int main() {
    HashTableChaining ht;
    ht.insert(10, "Alice");
    ht.insert(22, "Bob");
    ht.insert(31, "Charlie");
    ht.insert(21, "Diana");  // May collide with 10 (both 10%11=10, 21%11=10)

    std::cout << "Search 22: " << ht.search(22) << std::endl;  // Bob
    std::cout << "Search 21: " << ht.search(21) << std::endl;  // Diana
    std::cout << "Search 99: " << ht.search(99) << std::endl;  // NOT FOUND

    return 0;
}
```

**Complexity with chaining:**
- Load factor α = n/m (n = number of keys, m = table size)
- Expected time for search/insert/delete: O(1 + α)
- If α = O(1) (table is properly sized), all operations are O(1) expected.

### Open Addressing (Closed Hashing)

All elements are stored in the table itself. On collision, we **probe** for the next empty slot.

#### Linear Probing

On collision at index i, try i+1, i+2, i+3, ...

\\[h(k, i) = (h(k) + i) \mod m\\]

```cpp
#include <iostream>
#include <vector>
#include <string>

class HashTableLinearProbing {
    static const int TABLE_SIZE = 11;
    std::vector<std::pair<int, std::string>> table;
    std::vector<bool> occupied;
    int count;

public:
    HashTableLinearProbing() : table(TABLE_SIZE), occupied(TABLE_SIZE, false), count(0) {}

    void insert(int key, const std::string& value) {
        if (count >= TABLE_SIZE) throw std::runtime_error("Table full");

        int idx = key % TABLE_SIZE;
        while (occupied[idx]) {
            if (table[idx].first == key) {
                table[idx].second = value;  // Update
                return;
            }
            idx = (idx + 1) % TABLE_SIZE;
        }
        table[idx] = {key, value};
        occupied[idx] = true;
        count++;
    }

    std::string search(int key) {
        int idx = key % TABLE_SIZE;
        int start = idx;
        while (occupied[idx]) {
            if (table[idx].first == key) return table[idx].second;
            idx = (idx + 1) % TABLE_SIZE;
            if (idx == start) break;  // Full cycle
        }
        return "NOT FOUND";
    }
};

int main() {
    HashTableLinearProbing ht;
    ht.insert(10, "Alice");
    ht.insert(22, "Bob");
    ht.insert(31, "Charlie");

    std::cout << "Search 22: " << ht.search(22) << std::endl;  // Bob
    return 0;
}
```

**Problem with linear probing: Primary clustering** — long runs of occupied slots form, making insertions slower.

#### Quadratic Probing

On collision at index i, try i+1², i+2², i+3², ...

\\[h(k, i) = (h(k) + c_1 \cdot i + c_2 \cdot i^2) \mod m\\]

Reduces primary clustering but can cause **secondary clustering** (keys with the same initial hash follow the same probe sequence).

#### Double Hashing

Use a second hash function for the probe step:

\\[h(k, i) = (h_1(k) + i \cdot h_2(k)) \mod m\\]

Where \\(h_2(k)\\) should never return 0 (commonly: \\(h_2(k) = 1 + (k \mod (m-1))\\)).

This eliminates both primary and secondary clustering.

```cpp
#include <iostream>
#include <vector>
#include <string>

class HashTableDoubleHashing {
    static const int TABLE_SIZE = 11;
    std::vector<std::pair<int, std::string>> table;
    std::vector<bool> occupied;

    int h1(int key) { return key % TABLE_SIZE; }
    int h2(int key) { return 1 + (key % (TABLE_SIZE - 1)); }

public:
    HashTableDoubleHashing() : table(TABLE_SIZE), occupied(TABLE_SIZE, false) {}

    void insert(int key, const std::string& value) {
        int idx = h1(key);
        int step = h2(key);

        while (occupied[idx]) {
            if (table[idx].first == key) {
                table[idx].second = value;
                return;
            }
            idx = (idx + step) % TABLE_SIZE;
        }
        table[idx] = {key, value};
        occupied[idx] = true;
    }

    std::string search(int key) {
        int idx = h1(key);
        int step = h2(key);
        int start = idx;

        while (occupied[idx]) {
            if (table[idx].first == key) return table[idx].second;
            idx = (idx + step) % TABLE_SIZE;
            if (idx == start) break;
        }
        return "NOT FOUND";
    }
};

int main() {
    HashTableDoubleHashing ht;
    ht.insert(10, "Alice");
    ht.insert(22, "Bob");
    ht.insert(31, "Charlie");

    std::cout << "Search 22: " << ht.search(22) << std::endl;  // Bob
    return 0;
}
```

### Comparison of Collision Resolution

| Method | Average Search | Worst Search | Cache Performance | Clustering |
|---|---|---|---|---|
| Chaining | O(1 + α) | O(n) | Poor (pointer chasing) | None |
| Linear Probing | O(1/(1-α)) | O(n) | Excellent (sequential) | Primary |
| Quadratic Probing | O(1/(1-α)) | O(n) | Good | Secondary |
| Double Hashing | O(1/(1-α)) | O(n) | Poor | None |

---

## 7.4 Hash Tables in C++

### std::unordered_map

```cpp
#include <iostream>
#include <unordered_map>
#include <string>

int main() {
    // Construction
    std::unordered_map<std::string, int> um;

    // Insertion
    um["Alice"] = 90;
    um["Bob"] = 85;
    um.insert({"Charlie", 95});
    um.emplace("Diana", 88);

    // Access
    std::cout << "Alice: " << um["Alice"] << std::endl;  // 90
    // WARNING: um["Nonexistent"] creates an entry with value 0!

    // Safe access with find
    auto it = um.find("Eve");
    if (it != um.end()) {
        std::cout << "Eve: " << it->second << std::endl;
    } else {
        std::cout << "Eve not found" << std::endl;
    }

    // Check existence
    if (um.count("Alice")) {
        std::cout << "Alice exists" << std::endl;
    }

    // C++20: contains
    // if (um.contains("Alice")) { ... }

    // Deletion
    um.erase("Bob");

    // Iteration
    for (const auto& [key, value] : um) {
        std::cout << key << ": " << value << std::endl;
    }

    // Size
    std::cout << "Size: " << um.size() << std::endl;

    return 0;
}
```

### std::unordered_set

```cpp
#include <iostream>
#include <unordered_set>

int main() {
    std::unordered_set<int> us;

    // Insert
    us.insert(1);
    us.insert(2);
    us.insert(3);
    us.insert(2);  // Duplicate — ignored

    // Check existence
    std::cout << "Contains 2: " << us.count(2) << std::endl;  // 1
    std::cout << "Contains 5: " << us.count(5) << std::endl;  // 0

    // Size
    std::cout << "Size: " << us.size() << std::endl;  // 3

    // Erase
    us.erase(2);

    for (int x : us) std::cout << x << " ";
    std::cout << std::endl;

    return 0;
}
```

### Custom Hash Functions

For user-defined types, you need to provide a hash function:

```cpp
#include <iostream>
#include <unordered_map>
#include <string>

struct Point {
    int x, y;

    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
};

// Method 1: Custom hash functor
struct PointHash {
    std::size_t operator()(const Point& p) const {
        // Combine hashes of x and y
        auto h1 = std::hash<int>{}(p.x);
        auto h2 = std::hash<int>{}(p.y);
        return h1 ^ (h2 << 1);  // Simple combination
    }
};

// Method 2: Using std::hash specialization (more idiomatic)
namespace std {
    template<>
    struct hash<Point> {
        std::size_t operator()(const Point& p) const {
            return std::hash<int>{}(p.x) ^ (std::hash<int>{}(p.y) << 1);
        }
    };
}

int main() {
    // Using custom hash functor
    std::unordered_map<Point, std::string, PointHash> pointNames;
    pointNames[{1, 2}] = "A";
    pointNames[{3, 4}] = "B";

    std::cout << "Point (1,2): " << pointNames[{1, 2}] << std::endl;

    // Using std::hash specialization
    std::unordered_map<Point, int> pointValues;
    pointValues[{5, 6}] = 42;

    return 0;
}
```

**Better hash combination (avoiding collisions):**

```cpp
struct PointHash {
    std::size_t operator()(const Point& p) const {
        // Boost-style hash combine
        std::size_t h = std::hash<int>{}(p.x);
        h ^= std::hash<int>{}(p.y) + 0x9e3779b9 + (h << 6) + (h >> 2);
        return h;
    }
};
```

### Load Factor and Rehashing

```cpp
#include <iostream>
#include <unordered_map>

int main() {
    std::unordered_map<int, int> um;

    std::cout << "Initial bucket count: " << um.bucket_count() << std::endl;
    std::cout << "Initial load factor: " << um.load_factor() << std::endl;
    std::cout << "Max load factor: " << um.max_load_factor() << std::endl;

    // Insert elements and observe rehashing
    for (int i = 0; i < 20; i++) {
        um[i] = i * 10;
        if (i == 0 || i == 9 || i == 19) {
            std::cout << "After " << i + 1 << " elements: "
                      << "buckets=" << um.bucket_count()
                      << ", load_factor=" << um.load_factor() << std::endl;
        }
    }

    // Pre-allocate to avoid rehashing
    std::unordered_map<int, int> um2;
    um2.reserve(100);  // Pre-allocate for 100 elements
    std::cout << "\nReserved bucket count: " << um2.bucket_count() << std::endl;

    // Adjust max load factor
    um2.max_load_factor(0.5);  // More buckets, fewer collisions

    return 0;
}
```

**Key operations:**
- `reserve(n)`: Pre-allocate for n elements (avoids rehashing).
- `rehash(n)`: Set minimum bucket count to n.
- `max_load_factor()`: Get/set the threshold for rehashing (default 1.0).
- `bucket_count()`: Current number of buckets.
- `load_factor()`: Current load factor (size / bucket_count).

### When to Use Which Container

| Container | Use Case | Ordered? | Duplicates? |
|---|---|---|---|
| `unordered_map` | Key-value with O(1) avg access | No | Keys unique |
| `map` | Key-value with O(log n) access | Yes (sorted) | Keys unique |
| `unordered_set` | Set with O(1) avg membership test | No | No |
| `set` | Set with O(log n) membership test | Yes (sorted) | No |
| `unordered_multimap` | Key-value, multiple values per key | No | Keys can repeat |
| `multiset` | Set allowing duplicates | Yes | Elements can repeat |

---

## 7.5 Rolling Hash

### Polynomial Hash

The polynomial hash is the foundation of rolling hash:

\\[H(s) = (s[0] \cdot p^{0} + s[1] \cdot p^{1} + \cdots + s[n-1] \cdot p^{n-1}) \mod m\\]

The key property: when we "roll" the hash window one position, we can compute the new hash in O(1):

```
Window:     "abc" → hash = a·p⁰ + b·p¹ + c·p²
Roll to:    "bcd" → hash = (old_hash - a) / p + d·p²
```

In practice, division is replaced with multiplication by modular inverse.

### Rabin-Karp String Matching

Use rolling hash to find a pattern in a text in O(n + m) average time:

```cpp
#include <iostream>
#include <string>
#include <vector>

// Rabin-Karp string matching
// Time: O(n + m) average, O(nm) worst case
std::vector<int> rabinKarp(const std::string& text, const std::string& pattern) {
    int n = text.size(), m = pattern.size();
    if (m > n) return {};

    const long long P = 31;       // Base
    const long long MOD = 1e9 + 7; // Modulus

    // Precompute p^m
    long long pM = 1;
    for (int i = 0; i < m; i++) {
        pM = (pM * P) % MOD;
    }

    // Compute hash of pattern and first window
    long long patHash = 0, textHash = 0;
    for (int i = 0; i < m; i++) {
        patHash = (patHash + (pattern[i] - 'a' + 1) * /*p^i*/1) % MOD;
        // We'll compute properly below
    }

    // Recompute properly
    patHash = 0;
    for (int i = 0; i < m; i++) {
        patHash = (patHash * P + (pattern[i] - 'a' + 1)) % MOD;
    }

    textHash = 0;
    for (int i = 0; i < m; i++) {
        textHash = (textHash * P + (text[i] - 'a' + 1)) % MOD;
    }

    std::vector<int> matches;

    for (int i = 0; i <= n - m; i++) {
        // Check hash match
        if (textHash == patHash) {
            // Verify character by character (hash collision check)
            if (text.substr(i, m) == pattern) {
                matches.push_back(i);
            }
        }

        // Roll the hash: remove leftmost, add rightmost
        if (i < n - m) {
            textHash = (textHash - (text[i] - 'a' + 1) * pM % MOD + MOD) % MOD;
            textHash = (textHash * P + (text[i + m] - 'a' + 1)) % MOD;
        }
    }

    return matches;
}

int main() {
    std::string text = "ababcababcabc";
    std::string pattern = "abc";

    auto matches = rabinKarp(text, pattern);
    std::cout << "Pattern found at indices: ";
    for (int idx : matches) std::cout << idx << " ";
    std::cout << std::endl;
    // Output: 2 7 10

    return 0;
}
```

**Dry Run:**

```
text = "ababcababcabc", pattern = "abc"
P = 31, MOD = 10^9+7

Pattern hash: hash("abc") = (1·31⁰ + 2·31¹ + 3·31²) mod MOD

Window [0..2] "aba": hash → compare with patHash → no match
Roll: remove 'a' at 0, add 'b' at 3
Window [1..3] "bab": hash → no match
Roll: remove 'b' at 1, add 'c' at 4
Window [2..4] "abc": hash → match! Verify: "abc" == "abc" ✓ → index 2
...continue...
```

### Rolling Hash for Substring Problems

```cpp
#include <iostream>
#include <string>
#include <unordered_set>

// Find all duplicate substrings of length k
std::vector<std::string> findDuplicates(const std::string& s, int k) {
    const long long P = 31;
    const long long MOD = 1e9 + 7;

    int n = s.size();
    if (k > n) return {};

    // Compute p^k
    long long pK = 1;
    for (int i = 0; i < k; i++) pK = (pK * P) % MOD;

    // Compute first window hash
    long long hash = 0;
    for (int i = 0; i < k; i++) {
        hash = (hash * P + (s[i] - 'a' + 1)) % MOD;
    }

    std::unordered_map<long long, std::vector<int>> hashMap;
    hashMap[hash].push_back(0);

    // Rolling hash for remaining windows
    for (int i = 1; i <= n - k; i++) {
        hash = (hash - (s[i - 1] - 'a' + 1) * pK % MOD + MOD) % MOD;
        hash = (hash * P + (s[i + k - 1] - 'a' + 1)) % MOD;
        hashMap[hash].push_back(i);
    }

    // Collect duplicates (verify to handle hash collisions)
    std::vector<std::string> result;
    std::unordered_set<std::string> seen;

    for (auto& [h, positions] : hashMap) {
        if (positions.size() > 1) {
            for (int pos : positions) {
                std::string sub = s.substr(pos, k);
                if (seen.find(sub) == seen.end()) {
                    seen.insert(sub);
                    result.push_back(sub);
                }
            }
        }
    }

    return result;
}

int main() {
    std::string s = "abcabcabc";
    int k = 3;

    auto dupes = findDuplicates(s, k);
    std::cout << "Duplicate substrings of length " << k << ": ";
    for (const auto& d : dupes) std::cout << "\"" << d << "\" ";
    std::cout << std::endl;
    // Output: "abc"

    return 0;
}
```

---

## 7.6 Applications

### Frequency Counting

The most common hash map application:

```cpp
#include <iostream>
#include <unordered_map>
#include <vector>
#include <string>

// Count frequency of each element
std::unordered_map<int, int> countFrequency(const std::vector<int>& arr) {
    std::unordered_map<int, int> freq;
    for (int x : arr) {
        freq[x]++;
    }
    return freq;
}

int main() {
    std::vector<int> arr = {1, 2, 3, 2, 1, 3, 3, 4, 5, 4};
    auto freq = countFrequency(arr);

    for (const auto& [element, count] : freq) {
        std::cout << element << ": " << count << std::endl;
    }
    // Output (order may vary): 5:1, 4:2, 3:3, 2:2, 1:2

    return 0;
}
```

### Two Sum (Hash Map Approach)

```cpp
#include <iostream>
#include <vector>
#include <unordered_map>

// Time: O(n), Space: O(n)
std::vector<int> twoSum(const std::vector<int>& nums, int target) {
    std::unordered_map<int, int> seen;  // value -> index

    for (int i = 0; i < (int)nums.size(); i++) {
        int complement = target - nums[i];
        if (seen.count(complement)) {
            return {seen[complement], i};
        }
        seen[nums[i]] = i;
    }

    return {};
}

int main() {
    std::vector<int> nums = {2, 7, 11, 15};
    auto result = twoSum(nums, 9);
    std::cout << "Indices: " << result[0] << ", " << result[1] << std::endl;
    // Output: 0, 1
    return 0;
}
```

### Anagram Grouping

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <algorithm>

// Group anagrams together
// Time: O(n * k log k) where k = max word length
std::vector<std::vector<std::string>> groupAnagrams(std::vector<std::string>& strs) {
    std::unordered_map<std::string, std::vector<std::string>> groups;

    for (const auto& s : strs) {
        std::string sorted = s;
        std::sort(sorted.begin(), sorted.end());
        groups[sorted].push_back(s);
    }

    std::vector<std::vector<std::string>> result;
    for (auto& [key, group] : groups) {
        result.push_back(std::move(group));
    }
    return result;
}

int main() {
    std::vector<std::string> strs = {"eat", "tea", "tan", "ate", "nat", "bat"};
    auto groups = groupAnagrams(strs);

    for (const auto& group : groups) {
        std::cout << "[ ";
        for (const auto& s : group) std::cout << s << " ";
        std::cout << "]\n";
    }
    // Output: [ eat tea ate ] [ tan nat ] [ bat ]

    return 0;
}
```

### Simple Cache (LRU-style)

```cpp
#include <iostream>
#include <unordered_map>
#include <list>

class LRUCache {
    int capacity;
    std::list<std::pair<int, int>> cache;  // {key, value}
    std::unordered_map<int, std::list<std::pair<int, int>>::iterator> map;

public:
    LRUCache(int cap) : capacity(cap) {}

    int get(int key) {
        if (map.find(key) == map.end()) return -1;

        // Move to front (most recently used)
        cache.splice(cache.begin(), cache, map[key]);
        return map[key]->second;
    }

    void put(int key, int value) {
        if (map.find(key) != map.end()) {
            // Update existing
            map[key]->second = value;
            cache.splice(cache.begin(), cache, map[key]);
            return;
        }

        if ((int)cache.size() >= capacity) {
            // Remove least recently used
            auto lru = cache.back();
            map.erase(lru.first);
            cache.pop_back();
        }

        cache.emplace_front(key, value);
        map[key] = cache.begin();
    }
};

int main() {
    LRUCache lru(2);
    lru.put(1, 1);
    lru.put(2, 2);
    std::cout << "Get 1: " << lru.get(1) << std::endl;  // 1
    lru.put(3, 3);  // Evicts key 2
    std::cout << "Get 2: " << lru.get(2) << std::endl;  // -1 (not found)
    lru.put(4, 4);  // Evicts key 1
    std::cout << "Get 1: " << lru.get(1) << std::endl;  // -1
    std::cout << "Get 3: " << lru.get(3) << std::endl;  // 3
    std::cout << "Get 4: " << lru.get(4) << std::endl;  // 4

    return 0;
}
```

---

## Interview Problems

### Problem 1: Group Anagrams

See Section 7.6 above.

### Problem 2: Longest Substring Without Repeating Characters

```cpp
#include <iostream>
#include <string>
#include <unordered_map>
#include <algorithm>

// Time: O(n), Space: O(min(n, alphabet_size))
int lengthOfLongestSubstring(const std::string& s) {
    std::unordered_map<char, int> lastSeen;  // char -> last index
    int maxLen = 0;
    int start = 0;

    for (int i = 0; i < (int)s.size(); i++) {
        if (lastSeen.count(s[i]) && lastSeen[s[i]] >= start) {
            start = lastSeen[s[i]] + 1;  // Move start past the duplicate
        }
        lastSeen[s[i]] = i;
        maxLen = std::max(maxLen, i - start + 1);
    }

    return maxLen;
}

int main() {
    std::cout << lengthOfLongestSubstring("abcabcbb") << std::endl;  // 3 ("abc")
    std::cout << lengthOfLongestSubstring("bbbbb") << std::endl;     // 1 ("b")
    std::cout << lengthOfLongestSubstring("pwwkew") << std::endl;    // 3 ("wke")
    std::cout << lengthOfLongestSubstring("") << std::endl;          // 0
    return 0;
}
```

**Dry Run for "abcabcbb":**

| i | s[i] | lastSeen | start | maxLen | Window |
|---|---|---|---|---|---|
| 0 | a | {a:0} | 0 | 1 | "a" |
| 1 | b | {a:0,b:1} | 0 | 2 | "ab" |
| 2 | c | {a:0,b:1,c:2} | 0 | 3 | "abc" |
| 3 | a | {a:3,b:1,c:2} | 1 | 3 | "bca" |
| 4 | b | {a:3,b:4,c:2} | 2 | 3 | "cab" |
| 5 | c | {a:3,b:4,c:5} | 3 | 3 | "abc" |
| 6 | b | {a:3,b:6,c:5} | 4 | 3 | "cb" → "bcb"? |

Wait, let me re-trace. At i=6, s[6]='b'. lastSeen['b']=4, start=3. Since 4 >= 3, start = 4+1 = 5. Window: "cb", length 2.

Actually the answer is 3 for "abc". Let me re-trace more carefully:

| i | s[i] | lastSeen[s[i]] | start | maxLen | Window |
|---|---|---|---|---|---|
| 0 | a | -1 | 0 | 1 | [0,0] "a" |
| 1 | b | -1 | 0 | 2 | [0,1] "ab" |
| 2 | c | -1 | 0 | 3 | [0,2] "abc" |
| 3 | a | 0 >= 0→start=1 | 1 | 3 | [1,3] "bca" |
| 4 | b | 1 >= 1→start=2 | 2 | 3 | [2,4] "cab" |
| 5 | c | 2 >= 2→start=3 | 3 | 3 | [3,5] "abc" |
| 6 | b | 4 >= 3→start=5 | 5 | 3 | [5,6] "cb" |
| 7 | b | 6 >= 5→start=7 | 7 | 3 | [7,7] "b" |

Result: 3. ✓

### Problem 3: Subarray Sum Equals K

```cpp
#include <iostream>
#include <vector>
#include <unordered_map>

// Time: O(n), Space: O(n)
int subarraySum(const std::vector<int>& nums, int k) {
    std::unordered_map<int, int> prefixCount;  // prefix_sum -> count
    prefixCount[0] = 1;  // Empty prefix

    int sum = 0;
    int count = 0;

    for (int num : nums) {
        sum += num;

        // If sum - k was seen before, there's a subarray summing to k
        if (prefixCount.count(sum - k)) {
            count += prefixCount[sum - k];
        }

        prefixCount[sum]++;
    }

    return count;
}

int main() {
    std::vector<int> nums = {1, 1, 1};
    std::cout << "Subarrays summing to 2: " << subarraySum(nums, 2) << std::endl;  // 2

    std::vector<int> nums2 = {1, 2, 3};
    std::cout << "Subarrays summing to 3: " << subarraySum(nums2, 3) << std::endl;  // 2

    return 0;
}
```

**Key insight:** If `prefix[j] - prefix[i] == k`, then the subarray `nums[i+1..j]` sums to k. So for each `prefix[j]`, count how many `prefix[i]` equal `prefix[j] - k`.

### Problem 4: Longest Consecutive Sequence

```cpp
#include <iostream>
#include <vector>
#include <unordered_set>
#include <algorithm>

// Time: O(n), Space: O(n)
int longestConsecutive(const std::vector<int>& nums) {
    std::unordered_set<int> numSet(nums.begin(), nums.end());
    int maxLen = 0;

    for (int num : numSet) {
        // Only start counting from the beginning of a sequence
        if (numSet.count(num - 1)) continue;

        int currentNum = num;
        int currentLen = 1;

        while (numSet.count(currentNum + 1)) {
            currentNum++;
            currentLen++;
        }

        maxLen = std::max(maxLen, currentLen);
    }

    return maxLen;
}

int main() {
    std::vector<int> nums = {100, 4, 200, 1, 3, 2};
    std::cout << "Longest consecutive: " << longestConsecutive(nums) << std::endl;
    // Output: 4 (sequence: 1, 2, 3, 4)

    std::vector<int> nums2 = {0, 3, 7, 2, 5, 8, 4, 6, 0, 1};
    std::cout << "Longest consecutive: " << longestConsecutive(nums2) << std::endl;
    // Output: 9

    return 0;
}
```

**Why O(n)?** Each number is visited at most twice (once in the outer loop, once in the inner while loop). The `if (numSet.count(num - 1))` check ensures we only start counting from the beginning of a sequence.

---

## Interview Tips

1. **Hash maps are your go-to for O(1) lookups.** When you see "count," "frequency," "two sum," or "group by," think hash map.

2. **Prefix sum + hash map** is a powerful pattern for subarray problems. Store `(prefix_sum, count)` and look for `prefix_sum - k`.

3. **Always handle hash collisions in code.** When two strings hash to the same value, verify character by character (as in Rabin-Karp).

4. **Custom hash functions** — use a good combination formula. Simple XOR can cause many collisions.

5. **unordered_map vs map:**
   - `unordered_map`: O(1) average, O(n) worst. No ordering.
   - `map`: O(log n) always. Keys are sorted.
   - Use `unordered_map` unless you need ordering.

6. **Reserve space** if you know the approximate size. This avoids rehashing and improves performance.

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---|---|---|
| Using `um[key]` to check existence | Creates entry with default value if not found | Use `um.count(key)` or `um.find(key)` |
| Bad hash function for pairs/tuples | Too many collisions | Use proper hash combine (boost-style) |
| Forgetting to handle hash collisions in Rabin-Karp | False positives | Always verify with string comparison |
| Using `unordered_map` with custom type without hash | Compile error | Provide hash functor or specialize `std::hash` |
| Not reserving space | Rehashing during insertion | Call `reserve(n)` if size is known |
| Assuming O(1) worst case | Hash table worst case is O(n) | Know the difference between average and worst |

## Practice Problems

| # | Problem | Difficulty | Key Technique |
|---|---|---|---|
| 1 | Two Sum | Easy | Hash map lookup |
| 2 | Contains Duplicate | Easy | Hash set |
| 3 | Valid Anagram | Easy | Frequency counting |
| 4 | Group Anagrams | Medium | Sorted key as hash |
| 5 | Longest Substring Without Repeating Characters | Medium | Sliding window + hash map |
| 6 | Subarray Sum Equals K | Medium | Prefix sum + hash map |
| 7 | Longest Consecutive Sequence | Medium | Hash set + sequence detection |
| 8 | Top K Frequent Elements | Medium | Hash map + heap |
| 9 | Minimum Window Substring | Hard | Sliding window + frequency |
| 10 | Longest Substring with At Most K Distinct Characters | Hard | Sliding window + hash map |

---

*In the next chapter, we'll study linked lists — a fundamental data structure that teaches pointer manipulation and appears frequently in interviews.*

---

## See Also

- [Chapter 94: Hashing Deep Dive](ch94-hashing-deep-dive.md) — Advanced topics: universal hashing, perfect hashing, locality-sensitive hashing, and consistent hashing.
- [Chapter 105: Cuckoo and Robin Hood Hashing](ch105-cuckoo-robin-hood-hashing.md) — Alternative open-addressing strategies with better worst-case guarantees.
- [Chapter 40: Rolling Hash](ch40-rolling-hash.md) — Hash-based string matching; enables efficient substring comparison in O(1).
- [Chapter 16: Trie](ch16-trie.md) — When you need prefix-based lookups, tries complement hash maps.
- [Chapter 79: Probabilistic Data Structures](ch79-probabilistic-ds.md) — Bloom filters and other hash-based structures for approximate set membership.
