# Chapter 94: Hashing Deep Dive

## Prerequisites

- Hash tables basics
- Modular arithmetic

## Interview Frequency: ★★★

Deep hashing knowledge is tested at **Google**, **Amazon**, and in system design interviews.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Rolling hash | ★★★★ | Medium | String matching |
| Zobrist hashing | ★★ | Medium | Game states |
| Consistent hashing | ★★★ | Medium | Distributed systems |
| Hash collision attacks | ★★ | Medium | Security awareness |

---

## Definition

**Hashing** maps arbitrary data to fixed-size values. This chapter covers specialized hashing techniques that go beyond basic hash tables:

- **Rolling hash**: A hash function that can compute the hash of a sliding window in O(1) time by maintaining a running value and subtracting the outgoing element while adding the incoming one. Formally, given a string s and a polynomial hash H(s) = Σ s[i] · B^(n-1-i) mod M, the hash of the next window is derived from the previous hash via constant-time arithmetic.

- **Universal hashing**: A family of hash functions H = {h} such that for any two distinct keys x ≠ y, Pr[h(x) = h(y)] ≤ 1/m where m is the table size. This guarantees O(1) expected lookups regardless of input distribution.

- **Zobrist hashing**: An XOR-based hashing scheme where each possible value in each position is assigned a random bitstring. The hash of a composite state is the XOR of the individual values' bitstrings. Adding or removing a value is O(1) via XOR.

- **Consistent hashing**: A technique that maps both keys and servers onto a circular hash space (ring). Each key is assigned to the next server clockwise. Adding or removing a server only redistributes keys in its immediate neighborhood, yielding O(1/n) redistribution instead of O(n).

- **Locality-Sensitive Hashing (LSH)**: A family of hash functions where similar items collide with higher probability than dissimilar items. Unlike traditional hashing (which minimizes collisions), LSH deliberately maximizes collisions for similar inputs to enable approximate nearest-neighbor search.

---

## Motivation

Why study hashing beyond hash maps?

1. **String matching**: Rabin-Karp uses rolling hash to find patterns in O(n + m) average time. Without rolling hash, substring comparison is O(m) per window.

2. **Distributed systems**: Consistent hashing is the backbone of Cassandra, DynamoDB, Memcached clusters, and CDNs. Server failures or additions must not rehash everything.

3. **Game AI**: Zobrist hashing enables transposition tables in chess engines. The same board position reached via different move orders gets the same hash, allowing memoization of evaluations.

4. **Approximate search**: LSH powers similarity search in high-dimensional spaces (image embeddings, recommendation engines). Exact nearest-neighbor is exponential in dimensionality; LSH makes it practical.

5. **Security**: Understanding hash collision attacks (HashDoS) is critical for building robust web services. Attackers can craft inputs that cause O(n²) behavior in hash-table-based parsers.

6. **Interviews**: System design questions frequently test consistent hashing. Coding interviews test rolling hash (Rabin-Karp, longest common substring). Knowing these well separates strong candidates.

---

## Intuition

**Rolling hash** is like a sliding window with a running total. Imagine computing a checksum of a 3-character window. When the window slides right by one, you:
- Subtract the contribution of the leftmost character (weighted by B²)
- Multiply the remaining sum by B (shifting weights)
- Add the new rightmost character

This mirrors how decimal numbers work: if you know the value of "123", the value of "234" is (123 - 1×100) × 10 + 4.

**Zobrist hashing** treats each element as a toggle switch. Each element has a unique random label. The hash of a set is the XOR of all labels. Adding an element XORs its label in; removing it XORs the same label out. Since XOR is self-inverse, the operation is symmetric and O(1).

**Consistent hashing** is a ring (0 to 2³²-1). Servers are placed at points on the ring. A key hashes to a point and walks clockwise to find its server. Adding a server inserts one point; only keys between the new point and the previous server need to move. This is like adding one new cashier — only customers in that segment of the line switch.

**LSH** is the opposite of normal hashing. Normal hashing tries to spread everything evenly. LSH tries to put similar things together. It uses random projections: two vectors that point in similar directions will agree on most random projections, landing in the same bucket.

---

## 94.1 Rolling Hash

Compute hash of all substrings in O(n).

```cpp
#include <iostream>
#include <string>
#include <vector>

class RollingHash {
    static const long long BASE = 91138233;
    static const long long MOD = 1e9 + 7;
    std::vector<long long> hash, power;
    
public:
    RollingHash(const std::string& s) : hash(s.size() + 1), power(s.size() + 1) {
        int n = s.size();
        hash[0] = 0;
        power[0] = 1;
        for (int i = 0; i < n; i++) {
            hash[i + 1] = (hash[i] * BASE + s[i]) % MOD;
            power[i + 1] = power[i] * BASE % MOD;
        }
    }
    
    // Hash of s[l..r] (0-indexed, inclusive)
    long long getHash(int l, int r) {
        return (hash[r + 1] - hash[l] * power[r - l + 1] % MOD + MOD) % MOD;
    }
};

int main() {
    std::string s = "abcabcabc";
    RollingHash rh(s);
    
    // Check if "abc" appears at position 3
    long long hash1 = rh.getHash(0, 2); // "abc"
    long long hash2 = rh.getHash(3, 5); // "abc"
    
    std::cout << "Hash of s[0..2]: " << hash1 << "\n";
    std::cout << "Hash of s[3..5]: " << hash2 << "\n";
    std::cout << "Equal: " << (hash1 == hash2) << "\n";
    
    return 0;
}
```

### Rolling Hash — Python

```python
class RollingHash:
    """Polynomial rolling hash with modular arithmetic."""
    
    BASE = 91138233
    MOD = 10**9 + 7
    
    def __init__(self, s: str):
        n = len(s)
        self.hash = [0] * (n + 1)
        self.power = [1] * (n + 1)
        for i in range(n):
            self.hash[i + 1] = (self.hash[i] * self.BASE + ord(s[i])) % self.MOD
            self.power[i + 1] = self.power[i] * self.BASE % self.MOD
    
    def get_hash(self, l: int, r: int) -> int:
        """Hash of s[l..r] (0-indexed, inclusive)."""
        return (self.hash[r + 1] - self.hash[l] * self.power[r - l + 1] % self.MOD + self.MOD) % self.MOD


# Usage
s = "abcabcabc"
rh = RollingHash(s)
print(f"Hash of s[0..2]: {rh.get_hash(0, 2)}")
print(f"Hash of s[3..5]: {rh.get_hash(3, 5)}")
print(f"Equal: {rh.get_hash(0, 2) == rh.get_hash(3, 5)}")
```

### Rolling Hash — Java

```java
public class RollingHash {
    private static final long BASE = 91138233L;
    private static final long MOD = 1_000_000_007L;
    private final long[] hash;
    private final long[] power;

    public RollingHash(String s) {
        int n = s.length();
        hash = new long[n + 1];
        power = new long[n + 1];
        hash[0] = 0;
        power[0] = 1;
        for (int i = 0; i < n; i++) {
            hash[i + 1] = (hash[i] * BASE + s.charAt(i)) % MOD;
            power[i + 1] = power[i] * BASE % MOD;
        }
    }

    /** Hash of s[l..r] (0-indexed, inclusive). */
    public long getHash(int l, int r) {
        return ((hash[r + 1] - hash[l] * power[r - l + 1] % MOD) + MOD) % MOD;
    }

    public static void main(String[] args) {
        String s = "abcabcabc";
        RollingHash rh = new RollingHash(s);
        System.out.println("Hash of s[0..2]: " + rh.getHash(0, 2));
        System.out.println("Hash of s[3..5]: " + rh.getHash(3, 5));
        System.out.println("Equal: " + (rh.getHash(0, 2) == rh.getHash(3, 5)));
    }
}
```

### Step-by-Step Walkthrough: Rolling Hash on "abcab"

Let's trace the polynomial hash construction for the string `s = "abcab"` with BASE = 3 and MOD = 1000 (simplified for clarity).

**Precomputation (prefix hashes):**

| Step | Character | ASCII | Computation | hash[i+1] | power[i+1] |
|------|-----------|-------|-------------|-----------|------------|
| 0 | 'a' | 97 | (0 × 3 + 97) % 1000 | 97 | 3 |
| 1 | 'b' | 98 | (97 × 3 + 98) % 1000 | 389 | 9 |
| 2 | 'c' | 99 | (389 × 3 + 99) % 1000 | 266 | 27 |
| 3 | 'a' | 97 | (266 × 3 + 97) % 1000 | 895 | 81 |
| 4 | 'b' | 98 | (895 × 3 + 98) % 1000 | 783 | 243 |

**Prefix hash array:** `hash = [0, 97, 389, 266, 895, 783]`
**Power array:** `power = [1, 3, 9, 27, 81, 243]`

**Query: hash of s[1..3] ("bca"):**

```
getHash(1, 3) = (hash[4] - hash[1] * power[3]) % 1000
              = (895 - 97 × 27) % 1000
              = (895 - 2619) % 1000
              = (-1724) % 1000
              = 276
```

**Verification: hash of s[0..2] ("abc"):**

```
getHash(0, 2) = (hash[3] - hash[0] * power[3]) % 1000
              = (266 - 0 × 27) % 1000
              = 266
```

"abc" (266) ≠ "bca" (276) — correctly different substrings get different hashes.

**Query: hash of s[2..4] ("cab"):**

```
getHash(2, 4) = (hash[5] - hash[2] * power[3]) % 1000
              = (783 - 389 × 27) % 1000
              = (783 - 10503) % 1000
              = (-9720) % 1000
              = 280
```

All three 3-character substrings yield distinct hashes: 266, 276, 280.

---

## 94.2 Zobrist Hashing

For hashing game states or sets. XOR of random values for each element.

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <unordered_set>

class ZobristHash {
    std::vector<long long> table;
    std::mt19937_64 rng;
    
public:
    ZobristHash(int maxElements) : table(maxElements), rng(42) {
        for (int i = 0; i < maxElements; i++)
            table[i] = rng();
    }
    
    long long hash(const std::vector<int>& elements) {
        long long h = 0;
        for (int e : elements) h ^= table[e];
        return h;
    }
    
    // Add element to existing hash
    long long add(long long currentHash, int element) {
        return currentHash ^ table[element];
    }
    
    // Remove element from existing hash
    long long remove(long long currentHash, int element) {
        return currentHash ^ table[element]; // XOR is its own inverse
    }
};

int main() {
    ZobristHash zh(100);
    
    std::vector<int> set1 = {1, 3, 5, 7};
    std::vector<int> set2 = {7, 5, 3, 1};
    
    std::cout << "Hash of {1,3,5,7}: " << zh.hash(set1) << "\n";
    std::cout << "Hash of {7,5,3,1}: " << zh.hash(set2) << "\n";
    std::cout << "Same hash: " << (zh.hash(set1) == zh.hash(set2)) << "\n";
    
    return 0;
}
```

### Zobrist Hashing — Python

```python
import random

class ZobristHash:
    """XOR-based hash for sets and game states."""
    
    def __init__(self, max_elements: int, seed: int = 42):
        rng = random.Random(seed)
        self.table = [rng.getrandbits(64) for _ in range(max_elements)]
    
    def hash(self, elements: list[int]) -> int:
        h = 0
        for e in elements:
            h ^= self.table[e]
        return h
    
    def add(self, current_hash: int, element: int) -> int:
        return current_hash ^ self.table[element]
    
    def remove(self, current_hash: int, element: int) -> int:
        return current_hash ^ self.table[element]


# Usage
zh = ZobristHash(100)
set1 = [1, 3, 5, 7]
set2 = [7, 5, 3, 1]
print(f"Hash of {{1,3,5,7}}: {zh.hash(set1)}")
print(f"Hash of {{7,5,3,1}}: {zh.hash(set2)}")
print(f"Same hash: {zh.hash(set1) == zh.hash(set2)}")
```

---

## 94.3 Consistent Hashing

Used in distributed systems to map keys to servers with minimal redistribution when servers are added/removed.

### Consistent Hashing — C++ Implementation

```cpp
#include <iostream>
#include <map>
#include <string>
#include <functional>
#include <vector>

class ConsistentHash {
    int replicas; // virtual nodes per server
    std::map<size_t, std::string> ring;
    std::hash<std::string> hasher;
    
public:
    ConsistentHash(int replicas = 150) : replicas(replicas) {}
    
    void addServer(const std::string& server) {
        for (int i = 0; i < replicas; i++) {
            size_t h = hasher(server + ":" + std::to_string(i));
            ring[h] = server;
        }
    }
    
    void removeServer(const std::string& server) {
        for (int i = 0; i < replicas; i++) {
            size_t h = hasher(server + ":" + std::to_string(i));
            ring.erase(h);
        }
    }
    
    std::string getServer(const std::string& key) {
        if (ring.empty()) return "";
        size_t h = hasher(key);
        auto it = ring.lower_bound(h);
        if (it == ring.end()) it = ring.begin();
        return it->second;
    }
};

int main() {
    ConsistentHash ch(150);
    ch.addServer("Server-A");
    ch.addServer("Server-B");
    ch.addServer("Server-C");
    
    std::vector<std::string> keys = {"user:1", "user:2", "user:3", "user:4", "user:5"};
    for (auto& key : keys)
        std::cout << key << " -> " << ch.getServer(key) << "\n";
    
    // Add a new server
    std::cout << "\n--- After adding Server-D ---\n";
    ch.addServer("Server-D");
    for (auto& key : keys)
        std::cout << key << " -> " << ch.getServer(key) << "\n";
    
    return 0;
}
```

### Consistent Hashing — Python

```python
import hashlib
from bisect import bisect_right

class ConsistentHash:
    """Consistent hashing with virtual nodes."""
    
    def __init__(self, replicas: int = 150):
        self.replicas = replicas
        self.ring: dict[int, str] = {}
        self.sorted_keys: list[int] = []
    
    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
    
    def add_server(self, server: str):
        for i in range(self.replicas):
            h = self._hash(f"{server}:{i}")
            self.ring[h] = server
            self.sorted_keys.append(h)
        self.sorted_keys.sort()
    
    def remove_server(self, server: str):
        for i in range(self.replicas):
            h = self._hash(f"{server}:{i}")
            del self.ring[h]
            self.sorted_keys.remove(h)
    
    def get_server(self, key: str) -> str:
        if not self.ring:
            return ""
        h = self._hash(key)
        idx = bisect_right(self.sorted_keys, h)
        if idx == len(self.sorted_keys):
            idx = 0
        return self.ring[self.sorted_keys[idx]]


# Usage
ch = ConsistentHash(150)
for server in ["Server-A", "Server-B", "Server-C"]:
    ch.add_server(server)

keys = ["user:1", "user:2", "user:3", "user:4", "user:5"]
for key in keys:
    print(f"{key} -> {ch.get_server(key)}")

print("\n--- After adding Server-D ---")
ch.add_server("Server-D")
for key in keys:
    print(f"{key} -> {ch.get_server(key)}")
```

### Dry Run: Consistent Hashing Ring Operations

Let's trace consistent hashing with **2 virtual nodes per server** and a simplified hash ring of size 0–100.

**Step 1: Add Server-A and Server-B**

```
Hash ring positions (virtual nodes):
  Server-A → hash("A:0")=15, hash("A:1")=72
  Server-B → hash("B:0")=38, hash("B:1")=91

Sorted ring: [15(A), 38(B), 72(A), 91(B)]
```

**Step 2: Map keys to servers**

```
Key        Hash    Walk clockwise to...
─────────────────────────────────────────
user:1     10     → 15 (Server-A)
user:2     25     → 38 (Server-B)
user:3     50     → 72 (Server-A)
user:4     80     → 91 (Server-B)
user:5     95     → 15 (Server-A)  [wrap around]

Distribution: Server-A=3, Server-B=2
```

**Step 3: Add Server-C**

```
Server-C → hash("C:0")=55, hash("C:1")=82

Sorted ring: [15(A), 38(B), 55(C), 72(A), 82(C), 91(B)]
```

**Step 4: Remap keys — only affected keys change**

```
Key        Hash    New assignment   Changed?
─────────────────────────────────────────────
user:1     10     → 15 (Server-A)   No
user:2     25     → 38 (Server-B)   No
user:3     50     → 55 (Server-C)   YES (was A)
user:4     80     → 82 (Server-C)   YES (was B)
user:5     95     → 15 (Server-A)   No

Only 2 out of 5 keys moved (40%), not all 5.
With 150 virtual nodes, redistribution is ~1/n = ~33%.
```

---

## Summary

| Technique | Use Case | Key Property |
|---|---|---|
| Rolling hash | Substring comparison | O(1) substring hash |
| Zobrist hashing | Set/game state hash | XOR-based, order-independent |
| Consistent hashing | Distributed systems | Minimal redistribution |

---

## 94.4 Non-Cryptographic Hash Functions

| Hash | Speed | Quality | Use Case |
|---|---|---|---|
| MurmurHash3 | Very fast | Good | Hash tables, bloom filters |
| xxHash | Fastest | Excellent | General purpose |
| SipHash | Moderate | Cryptographic | Hash DoS prevention |
| CityHash | Fast | Good | Google internal |
| FNV-1a | Fast | Decent | Simple hashing |

```cpp
#include <iostream>
#include <cstdint>

// FNV-1a hash (simple, widely used)
uint32_t fnv1a(const void* data, size_t len) {
    uint32_t hash = 2166136261u;
    const uint8_t* bytes = (const uint8_t*)data;
    for (size_t i = 0; i < len; i++) {
        hash ^= bytes[i];
        hash *= 16777619u;
    }
    return hash;
}

// Simple hash combining (like boost::hash_combine)
size_t hashCombine(size_t seed, size_t val) {
    seed ^= val + 0x9e3779b9 + (seed << 6) + (seed >> 2);
    return seed;
}

int main() {
    std::string s = "Hello, World!";
    std::cout << "FNV-1a hash: " << fnv1a(s.data(), s.size()) << "\n";
    std::cout << "Combined hash: " << hashCombine(42, 17) << "\n";
    return 0;
}
```

---

## 94.5 Rendezvous Hashing

Also called "highest random weight" hashing. Each key is hashed with every server, and the server with the highest hash value gets the key. Adding/removing a server only remaps keys assigned to that server.

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <functional>
#include <float.h>

std::string rendezvousHash(const std::string& key, 
                            const std::vector<std::string>& servers) {
    std::hash<std::string> hasher;
    std::string best;
    double bestScore = -DBL_MAX;
    
    for (auto& server : servers) {
        double score = hasher(key + server); // Combine key + server
        if (score > bestScore) {
            bestScore = score;
            best = server;
        }
    }
    return best;
}

int main() {
    std::vector<std::string> servers = {"S1", "S2", "S3"};
    for (auto& key : {"user:1", "user:2", "user:3", "user:4"})
        std::cout << key << " -> " << rendezvousHash(key, servers) << "\n";
    return 0;
}
```

---

## 94.6 Locality-Sensitive Hashing (Overview)

LSH maps similar items to the same hash bucket with high probability. Unlike regular hashing (which minimizes collisions), LSH maximizes collisions for similar items.

**Applications**: Near-duplicate detection, similarity search, recommendation systems.

**Technique**: Use multiple hash functions; items are "similar" if they collide in many functions.

---

### Locality-Sensitive Hashing Implementation

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <set>

// LSH for cosine similarity using random hyperplanes
class LSH {
    int dim, numHashes, numBands;
    std::vector<std::vector<double>> hyperplanes;
    
public:
    LSH(int dim, int numHashes, int numBands) 
        : dim(dim), numHashes(numHashes), numBands(numBands) {
        std::mt19937 rng(42);
        std::normal_distribution<double> dist(0.0, 1.0);
        for (int i = 0; i < numHashes; i++) {
            std::vector<double> hp(dim);
            for (int j = 0; j < dim; j++) hp[j] = dist(rng);
            hyperplanes.push_back(hp);
        }
    }
    
    // Hash a vector to a signature (vector of +1/-1)
    std::vector<int> hash(const std::vector<double>& vec) {
        std::vector<int> sig(numHashes);
        for (int i = 0; i < numHashes; i++) {
            double dot = 0;
            for (int j = 0; j < dim; j++)
                dot += vec[j] * hyperplanes[i][j];
            sig[i] = dot >= 0 ? 1 : 0;
        }
        return sig;
    }
    
    // Find candidate pairs using banded signatures
    std::set<std::pair<int,int>> findCandidates(
        const std::vector<std::vector<double>>& vectors) {
        int n = vectors.size();
        int bandSize = numHashes / numBands;
        
        std::set<std::pair<int,int>> candidates;
        
        for (int band = 0; band < numBands; band++) {
            std::map<std::vector<int>, std::vector<int>> buckets;
            for (int i = 0; i < n; i++) {
                auto sig = hash(vectors[i]);
                std::vector<int> bandSig(sig.begin() + band * bandSize, 
                                         sig.begin() + (band + 1) * bandSize);
                buckets[bandSig].push_back(i);
            }
            for (auto& [key, ids] : buckets) {
                for (int i = 0; i < (int)ids.size(); i++)
                    for (int j = i + 1; j < (int)ids.size(); j++)
                        candidates.insert({std::min(ids[i], ids[j]), 
                                          std::max(ids[i], ids[j])});
            }
        }
        return candidates;
    }
};
```

---

## 94.7 Hash Collision Attacks (HashDoS)

Hash collision attacks exploit the worst-case behavior of hash tables. If an attacker can predict the hash function, they craft inputs that all land in the same bucket, degrading O(1) operations to O(n).

### The Attack

Most hash table implementations use chaining. With n keys in one bucket, each insertion becomes O(n), and the total cost of n insertions is O(n²). This is **HashDoS** — denial of service via hash collisions.

**Real-world impact:**
- **2011**: PHP hash collision vulnerability (CVE-2011-4885) allowed a single POST request with ~500KB of colliding keys to hang a server for minutes.
- **2012**: Java, Python, Ruby, V8 all patched similar vulnerabilities.
- **2023**: Jenkins (CVE-2022-22965) had a hash collision DoS in the Spring framework.

### Attack Vectors

1. **Query string parameters**: `?a=1&b=2&c=3&...` — if the parser uses a hash map, colliding parameter names cause O(n²).
2. **JSON object keys**: Parsers that store keys in a hash map are vulnerable.
3. **HTTP headers**: Custom headers parsed into a hash map.
4. **Form data**: POST body with colliding field names.

### Defenses

| Defense | Description | Trade-off |
|---|---|---|
| **SipHash** | Keyed hash function; attacker can't predict output | Slightly slower than MurmurHash |
| **Random seed** | Hash function uses a random seed at startup | Seed leaks via timing side channels |
| **Balanced trees** | Use trees instead of lists in buckets (Java 8+ HashMap) | O(log n) worst case instead of O(n) |
| **Limit input size** | Cap number of keys in a parsed object | May reject legitimate requests |
| **Parse to array** | Don't use hash maps for parsed input | Loses O(1) lookup |

### SipHash — The Recommended Solution

SipHash is a keyed PRF (pseudorandom function) designed specifically for hash table use. It's fast (comparable to non-cryptographic hashes) but secure against collision attacks when the key is secret.

```cpp
// Python uses SipHash-1-3 by default since 3.4
// C++ standard library does NOT use SipHash — implement or use a library

// Python example demonstrating the defense:
// >>> import random
// >>> d = {}
// >>> for i in range(100000):
// ...     d[f"key_{i}"] = i  # No attacker can predict these hashes
// Insertion is O(1) amortized because SipHash randomizes bucket placement
```

**Key insight**: The hash table seed must be **unpredictable** (cryptographic random), not just random. A predictable seed lets the attacker enumerate collisions offline.

### Complexity Impact

| Scenario | Average Case | Worst Case (attacked) |
|---|---|---|
| Insert | O(1) | O(n) |
| Lookup | O(1) | O(n) |
| Delete | O(1) | O(n) |
| n operations | O(n) | O(n²) |

With SipHash or random seeds: worst case becomes O(n log n) expected, even with adversarial input.

---

## Complexity Analysis

| Technique | Preprocessing | Per-Operation | Space | Notes |
|---|---|---|---|---|
| **Rolling hash** | O(n) | O(1) substring hash | O(n) | May have false positives (use double hash) |
| **Zobrist hashing** | O(k) for k elements | O(1) add/remove/query | O(k) | XOR is self-inverse; order-independent |
| **Consistent hashing** | O(r log(r·s)) for r replicas, s servers | O(log(s)) lookup | O(r·s) | Virtual nodes improve balance |
| **Rendezvous hashing** | None | O(s) per key | O(s) | No ring needed; simple but O(s) |
| **LSH** | O(n·h) for h hash functions | O(1) per hash, O(n·b) candidate search | O(n·h) | b = number of bands |
| **FNV-1a** | None | O(L) for key of length L | O(1) | Fast, simple, non-crypto |
| **SipHash** | Key setup O(1) | O(L) for key of length L | O(1) | Keyed; DoS-resistant |

**Practical notes:**
- Rolling hash: use two moduli (double hashing) to reduce collision probability from O(1/M) to O(1/M²).
- Consistent hashing: 100–200 virtual nodes per server gives <5% standard deviation in load distribution.
- LSH: tune bands (b) and rows per band (r) to control the S-curve: P(candidate) = 1 - (1 - s^r)^b where s is similarity.

---

## Exercises

1. **Rabin-Karp substring search**: Implement the Rabin-Karp algorithm using rolling hash to find all occurrences of a pattern in a text. Handle hash collisions by verifying character-by-character when hashes match. What is the expected time complexity?

2. **Longest common substring**: Given two strings, find the length of their longest common substring in O(n log n) using rolling hash and binary search on the answer length.

3. **Zobrist for tic-tac-toe**: Implement Zobrist hashing for a tic-tac-toe board (9 cells, 3 states each: empty, X, O). Verify that the hash is order-independent and supports incremental updates.

4. **Consistent hashing load test**: Implement consistent hashing with virtual nodes and measure the standard deviation of key distribution across servers for 3, 10, and 50 servers. How many virtual nodes are needed for <5% imbalance?

5. **HashDoS experiment**: Create a hash table that uses a fixed (non-random) hash function. Write a program that generates n keys that all collide, then compare insertion time vs. random keys. Demonstrate the O(n²) vs O(n) difference.

6. **LSH for near-duplicate detection**: Implement LSH with random hyperplanes on a set of 1000 random 50-dimensional vectors. Inject 10 near-duplicate pairs (vectors differing by noise). Measure recall (fraction of true duplicates found) vs. number of bands.

7. **Double rolling hash**: Implement rolling hash with two different moduli. Given a set of strings, compute their double-hash signatures and verify that no two distinct strings share the same double hash. What is the false positive probability?

---

## Interview Questions

1. **How does consistent hashing minimize redistribution?**
   When a server is added, only keys that now fall between the new server and its predecessor on the ring need to move. With virtual nodes, the redistribution is approximately 1/n of the total keyspace. Without virtual nodes, load can be uneven.

2. **Why use XOR for Zobrist hashing instead of addition?**
   XOR is its own inverse: `a ^ b ^ b = a`. This means adding and removing an element use the same operation. Addition would require tracking a separate "subtract" path. XOR also naturally handles symmetric differences and is order-independent.

3. **How would you detect hash collision attacks on a production system?**
   Monitor request processing time distributions. A sudden spike in p99 latency with consistent request sizes suggests hash collision attacks. Check if request body parsers use hash maps with predictable seeds. Switch to SipHash or keyed hashing.

4. **Explain the trade-off in LSH between bands and rows.**
   More bands (b) with fewer rows per band (r) increases recall but decreases precision — more candidates, more false positives. Fewer bands with more rows does the opposite. The threshold similarity is approximately (1/b)^(1/r). Tuning b and r controls the S-curve shape.

5. **When would you choose rendezvous hashing over consistent hashing?**
   Rendezvous hashing is simpler (no ring, no virtual nodes) and has O(n) redistribution on removal (only the removed server's keys move). It's preferred when the server set is small (<20) and simplicity matters. Consistent hashing scales better with many servers due to O(log n) lookup.

6. **How do you handle hash collisions in rolling hash for string matching?**
   When two substrings have the same rolling hash, verify by comparing characters directly (Rabin-Karp does this). To reduce collision probability, use double hashing with two independent moduli, or use a 64-bit hash space where collision probability is negligible (1/2⁶⁴).

7. **Design a distributed cache using consistent hashing.**
   Servers are placed on a hash ring with virtual nodes. Keys hash to the ring and are served by the next clockwise server. On server failure, keys move to the next server. Replication: store on the next k servers for fault tolerance. Hot spots: adjust virtual node counts per server based on capacity.

---

## See Also

- [Chapter 7: Hashing](ch07-hashing.md) — The fundamentals: hash maps, hash sets, collision handling, and basic applications.
- [Chapter 105: Cuckoo and Robin Hood Hashing](ch105-cuckoo-robin-hood-hashing.md) — Advanced open-addressing strategies that guarantee O(1) worst-case lookup or equalize probe lengths.
- [Chapter 40: Rolling Hash](ch40-rolling-hash.md) — Hash-based string matching; rolling hash enables O(1) substring hash computation.
- [Chapter 134: Consistent Hashing](ch134-consistent-hashing.md) — Distributed systems use consistent hashing for load balancing across servers.
- [Chapter 79: Probabilistic Data Structures](ch79-probabilistic-ds.md) — Bloom filters, count-min sketches, and other hash-based probabilistic structures.
