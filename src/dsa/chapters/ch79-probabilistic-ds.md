# Chapter 79: Probabilistic Data Structures

## Prerequisites

- Hashing basics
- Probability basics

## Interview Frequency: ★★

Probabilistic data structures trade exactness for massive space savings. They appear in **Google** and **Amazon** system design interviews for big data problems.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Bloom Filter | ★★★★ | Medium | Membership testing |
| HyperLogLog | ★★ | Hard | Cardinality estimation |
| Count-Min Sketch | ★★ | Medium | Frequency estimation |

---

## 79.1 Bloom Filter

A Bloom Filter tests set membership with **no false negatives** but possible **false positives**.

- Insert: hash element with k hash functions, set k bits
- Query: check if all k bits are set
- Space: O(n) bits (much less than hash set)

```cpp
#include <iostream>
#include <vector>
#include <functional>
#include <string>

class BloomFilter {
    std::vector<bool> bits;
    int size;
    std::vector<std::function<int(const std::string&)>> hashes;
    
public:
    BloomFilter(int size, int numHashes) : bits(size, false), size(size) {
        // Create hash functions using double hashing
        for (int i = 0; i < numHashes; i++) {
            int seed = i * 7919 + 104729;
            hashes.push_back([this, seed](const std::string& s) {
                std::hash<std::string> hasher;
                return (hasher(s) + seed * hasher(s + "salt")) % size;
            });
        }
    }
    
    void insert(const std::string& item) {
        for (auto& h : hashes) {
            bits[std::abs(h(item))] = true;
        }
    }
    
    bool possiblyContains(const std::string& item) {
        for (auto& h : hashes) {
            if (!bits[std::abs(h(item))]) return false;
        }
        return true;
    }
};

int main() {
    BloomFilter bf(1000, 3);
    
    // Insert some items
    for (auto& s : {"apple", "banana", "cherry", "date", "elderberry"})
        bf.insert(s);
    
    // Test membership
    for (auto& s : {"apple", "banana", "fig", "grape", "cherry"}) {
        std::cout << s << ": " 
                  << (bf.possiblyContains(s) ? "possibly present" : "definitely not") 
                  << "\n";
    }
    
    return 0;
}
```

### False Positive Probability

```
P(false positive) ≈ (1 - e^(-kn/m))^k
```

where n = items inserted, m = bits, k = hash functions.

---

## Summary

| Structure | Operation | Space | Error |
|---|---|---|---|
| Bloom Filter | Membership | O(n) bits | False positives only |
| HyperLogLog | Cardinality | O(log log n) | ~2% error |
| Count-Min Sketch | Frequency | O(w × d) | Overestimates |

---

## 79.2 HyperLogLog

HyperLogLog estimates the number of distinct elements in a stream using O(log log n) space with ~2% error.

**Key idea**: Count the maximum number of leading zeros in hash values. If the maximum is L, estimate cardinality as 2^L.

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <functional>

class HyperLogLog {
    int precision;
    std::vector<int> registers;
    
    int getRegister(const std::string& item) {
        std::hash<std::string> hasher;
        size_t h = hasher(item);
        return h & ((1 << precision) - 1); // First 'precision' bits
    }
    
    int countLeadingZeros(size_t h) {
        if (h == 0) return 64;
        int count = 0;
        for (int i = 63; i >= 0; i--) {
            if ((h >> i) & 1) break;
            count++;
        }
        return count + 1;
    }
    
public:
    HyperLogLog(int p = 10) : precision(p), registers(1 << p, 0) {}
    
    void add(const std::string& item) {
        std::hash<std::string> hasher;
        size_t h = hasher(item);
        int reg = h & ((1 << precision) - 1);
        h >>= precision;
        registers[reg] = std::max(registers[reg], countLeadingZeros(h));
    }
    
    double estimate() {
        double sum = 0;
        int m = 1 << precision;
        for (int i = 0; i < m; i++)
            sum += std::pow(2.0, -registers[i]);
        
        double estimate = 0.7 * m * m / sum;
        if (estimate <= 2.5 * m) {
            // Small range correction
            int zeros = 0;
            for (int i = 0; i < m; i++)
                if (registers[i] == 0) zeros++;
            if (zeros > 0)
                estimate = m * std::log((double)m / zeros);
        }
        return estimate;
    }
};

int main() {
    HyperLogLog hll;
    for (int i = 0; i < 10000; i++)
        hll.add("element_" + std::to_string(i));
    
    std::cout << "Estimated distinct: " << hll.estimate() 
              << " (actual: 10000)\\n";
    return 0;
}
```

---

## 79.3 Count-Min Sketch

Count-Min Sketch estimates frequency of elements using d hash functions and d counters of width w. Always overestimates (never underestimates).

```cpp
#include <iostream>
#include <vector>
#include <functional>
#include <climits>

class CountMinSketch {
    int d, w;
    std::vector<std::vector<int>> table;
    std::vector<std::function<int(const std::string&)>> hashes;
    
public:
    CountMinSketch(int d, int w) : d(d), w(w), table(d, std::vector<int>(w, 0)) {
        for (int i = 0; i < d; i++) {
            int seed = i * 7919 + 104729;
            hashes.push_back([seed, w](const std::string& s) {
                std::hash<std::string> hasher;
                return (hasher(s) + seed) % w;
            });
        }
    }
    
    void add(const std::string& item, int count = 1) {
        for (int i = 0; i < d; i++)
            table[i][hashes[i](item)] += count;
    }
    
    int estimate(const std::string& item) {
        int minVal = INT_MAX;
        for (int i = 0; i < d; i++)
            minVal = std::min(minVal, table[i][hashes[i](item)]);
        return minVal;
    }
};

int main() {
    CountMinSketch cms(5, 1000);
    
    for (int i = 0; i < 100; i++) cms.add("frequent");
    for (int i = 0; i < 10; i++) cms.add("less_frequent");
    for (int i = 0; i < 1; i++) cms.add("rare");
    
    std::cout << "frequent: " << cms.estimate("frequent") << "\\n";
    std::cout << "less_frequent: " << cms.estimate("less_frequent") << "\\n";
    std::cout << "rare: " << cms.estimate("rare") << "\\n";
    
    return 0;
}
```

---

## Exercises

1. **Bloom filter sizing**: Design a Bloom filter for10 million URLs with a false positive rate of1%. How many hash functions and bits do you need?

2. **Count-Min Sketch accuracy**: With width1000 and depth5, what's the expected error bound? How does it change with width?

3. **HyperLogLog precision**: For HLL with2^14 registers, what's the expected standard error? How many distinct elements can it count?

4. **Implement a counting Bloom filter**: Extend the Bloom filter to support deletion by using counters instead of bits.

5. **Streaming median**: Use a combination of data structures to estimate the median of a stream. Compare with exact approaches.

---

## Interview Questions

1. **Q: What is a Bloom filter and when would you use it?**
   A: A probabilistic set membership data structure. It can say "definitely not in set" or "probably in set." Used for caching (avoid expensive lookups), database query optimization, network routers.

2. **Q: What's the false positive rate of a Bloom filter?**
   A: Approximately (1 - e^(-kn/m))^k where k = hash functions, n = elements, m = bits. Optimal k = (m/n) × ln(2).

3. **Q: How does HyperLogLog estimate cardinality?**
   A: It hashes elements and observes the position of the leftmost1-bit in the hash. The maximum position across all elements estimates log₂(cardinality). Using harmonic mean of multiple registers improves accuracy.

4. **Q: Can a Bloom filter have false negatives?**
   A: No. A Bloom filter only has false positives. If it says an element is not in the set, it's definitely not there. This is because it only sets bits, never clears them.

5. **Q: When would you use Count-Min Sketch vs a Bloom filter?**
   A: Bloom filter for set membership (yes/no). Count-Min Sketch for frequency estimation (how many times). Both are probabilistic and space-efficient for streaming data.

---

## Cross-References

- [Chapter 7: Hashing](ch07-hashing.md) — Hash function foundations
- [Chapter 94: Hashing Deep Dive](ch94-hashing-deep-dive.md) — Advanced hash techniques
- [Chapter 147: Streaming Algorithms](ch147-streaming-algorithms.md) — Other streaming data structures
- [Chapter 79: Probabilistic DS](ch79-probabilistic-ds.md) — Main chapter reference
