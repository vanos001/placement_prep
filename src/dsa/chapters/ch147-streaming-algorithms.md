# Chapter 147: Streaming Algorithms

## Prerequisites
- Probability theory, hash functions
- Basic data structures (counters, hash tables)
- Understanding of computational complexity

## Interview Frequency: ★★

Streaming algorithms process massive datasets in a single pass (or few passes) using memory much smaller than the input size. They're essential in big data, network monitoring, and database systems.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Streaming model | ★★ | Easy | One-pass, limited memory |
| Misra-Gries (Heavy Hitters) | ★★ | Medium | Frequency estimation |
| Reservoir Sampling | ★★ | Medium | Uniform sampling |
| Count-Min Sketch | ★★ | Medium | Frequency estimation |
| HyperLogLog | ★★ | Medium | Distinct counting |
| Flajolet-Martin | ★ | Medium | Distinct counting (simpler) |
| AMS Sketch | ★ | Hard | Frequency moments |

---

## 147.1 Motivation: The Streaming Problem

Imagine analyzing a 1TB log file on a machine with 1GB RAM. You can't store the entire dataset — you need to process it **one element at a time** and maintain a **summary** (sketch) that answers queries approximately.

### The Streaming Model

- **Input**: sequence of elements x₁, x₂, ..., xₙ arriving one at a time
- **Memory**: O(polylog n) or O(n^ε) — much less than O(n)
- **Passes**: ideally 1 (some algorithms use 2-3)
- **Output**: approximate answers to queries

### Why Approximate?

With limited memory, exact answers are often impossible. For example:
- **Exact distinct count** requires O(n) memory (you must remember every element seen)
- **Approximate distinct count** can use O(log n) memory with ~2% error

**Key insight**: Trading a small amount of accuracy for massive memory savings is the core of streaming algorithms.

---

## 147.2 Frequency Estimation: Misra-Gries

### Problem

Given a stream of n elements from a universe of size m, find all elements with frequency > n/k (heavy hitters).

### Algorithm

Maintain k-1 counters. For each element:
1. If it has a counter, increment
2. If there's an empty counter, assign it to this element
3. Otherwise, decrement all counters (remove zeros)

### Why It Works

**Lemma**: If an element has frequency > n/k, it must have a counter at the end.

**Proof**: Each decrement operation removes at most k-1 from the total count. After n elements, total decrements ≤ n/(k-1) × (k-1) = n. So any element with frequency > n/k survives.

### Guarantees

- **Space**: O(k) counters
- **Error**: frequency estimate ≤ true frequency ≤ estimate + n/k
- **All elements with freq > n/k are found**

### Walkthrough

Stream: [a, a, a, b, b, c, a, b, c, a, b, a] with k=3 (threshold = 12/3 = 4)

```
Element | Action          | Counters
--------|-----------------|----------
a       | New counter     | {a:1}
a       | Increment       | {a:2}
a       | Increment       | {a:3}
b       | New counter     | {a:3, b:1}
b       | Increment       | {a:3, b:2}
c       | New counter     | {a:3, b:2, c:1}
a       | Increment       | {a:4, b:2, c:1}
b       | Increment       | {a:4, b:3, c:1}
c       | Increment       | {a:4, b:3, c:2}
a       | Increment       | {a:5, b:3, c:2}
b       | Increment       | {a:5, b:4, c:2}
a       | Increment       | {a:6, b:4, c:2}

Result: a≥6, b≥4, c≥2
True:   a=6, b=4, c=2
Heavy hitters (freq > 4): {a:6, b:4}
```

---

## 147.3 Count-Min Sketch

### Problem

Estimate the frequency of any element in a stream.

### Algorithm

Use d hash functions and w counters (a d×w matrix). For each element x:
- For each hash function hᵢ: increment counter[i][hᵢ(x)]

To estimate frequency of x: return min over all i of counter[i][hᵢ(x)].

### Why It Works

- **Overestimate**: sketch counts can only increase, so estimate ≥ true frequency
- **With high probability**: estimate ≤ true frequency + ε·n where ε = 1/w
- **Probability of failure**: δ = e^(-d)

### Parameters

- **Width** w = ⌈e/ε⌉ ≈ 2.72/ε
- **Depth** d = ⌈ln(1/δ)⌉

### Walkthrough

4 hash functions, 8 counters each (d=4, w=8).

Stream: [a, b, a, c, a, b, d, a]

```
After processing:
h₁: [a:2, b:1, c:1, d:1, 0, 0, 0, 0]
h₂: [a:1, b:2, c:1, d:1, 0, 0, 0, 0]
h₃: [a:3, b:1, c:0, d:1, 0, 0, 0, 0]
h₄: [a:1, b:1, c:1, d:1, 0, 0, 0, 0]

Estimate(a) = min(2, 1, 3, 1) = 1 (overestimate due to hash collisions)
True(a) = 4
```

In practice, with proper hash functions and w ≈ 1/ε, the estimate is close.

---

## 147.4 Reservoir Sampling

### Problem

Sample k items uniformly at random from a stream of unknown length n.

### Algorithm (Vitter's R)

1. Fill reservoir with first k items
2. For each subsequent item i (0-indexed from k):
   - Generate random j ∈ [0, i]
   - If j < k, replace reservoir[j] with item i

### Why It Works

**Claim**: Each item has probability k/n of being in the reservoir.

**Proof by induction**:
- Item i (i < k): always in reservoir, probability = 1 initially
- When item i arrives: it replaces reservoir[j] with probability k/(i+1)
- At the end (n items total): probability = k/n ✓

### Walkthrough

Stream: [A, B, C, D, E], sample k=2

```
Step 1: Reservoir = [A, B]  (first k items)

Step 2: Item C (i=2)
  j = random(0, 2) = 1
  1 < 2 → replace reservoir[1] with C
  Reservoir = [A, C]

Step 3: Item D (i=3)
  j = random(0, 3) = 0
  0 < 2 → replace reservoir[0] with D
  Reservoir = [D, C]

Step 4: Item E (i=4)
  j = random(0, 4) = 3
  3 >= 2 → skip
  Reservoir = [D, C]

Final sample: [D, C]
```

Each of A, B, C, D, E has probability 2/5 = 40% of being selected.

---

## 147.5 HyperLogLog (Distinct Counting)

### Problem

Count the number of distinct elements in a stream using sublinear memory.

### Key Idea

Hash each element to a binary string. The number of leading zeros in the hash is related to the number of distinct elements seen.

**Intuition**: If you see a hash starting with 000000, you've probably seen many elements (getting a long run of zeros is rare with random data).

### Algorithm

1. Use m registers (typically m = 2^b for b = 10-16)
2. Hash each element to get a bit string
3. Use first b bits to select a register
4. Count leading zeros in remaining bits
5. Update register: R[j] = max(R[j], leading_zeros + 1)
6. Estimate = α_m × m² × harmonic_mean(2^(-R[j]))

### Error Rate

- Standard error: 1.04 / √m
- With m = 2^16 = 65536 registers: ~0.4% error using only 64KB!

### Walkthrough

m = 4 registers, hash function h(x) returns 8 bits.

```
Element | Hash (binary) | Register (2 bits) | Leading zeros | Update
--------|---------------|-------------------|---------------|-------
a       | 01101010      | 01 (reg 1)        | 1             | R[1]=1
b       | 00110100      | 00 (reg 0)        | 2             | R[0]=2
a       | 01101010      | 01 (reg 1)        | 1             | no change
c       | 10010110      | 10 (reg 2)        | 0             | R[2]=0→1
d       | 00011010      | 00 (reg 0)        | 3             | R[0]=2→3

Registers: R = [3, 1, 1, 0]
Estimate ≈ 4 × (harmonic mean of 2^(-R[j])) × constant
```

---

## 147.6 Flajolet-Martin (Simpler Distinct Count)

### Algorithm

1. Hash each element to a bit string
2. Track the maximum number of trailing zeros seen (R)
3. Estimate = 2^R

### Why It Works

With n distinct elements, the probability of seeing a hash ending in R zeros is 1 - (1 - 1/2^R)^n ≈ 1 - e^(-n/2^R).

The expected value of R ≈ log₂(n).

### Improvements

- **Multiple hash functions**: average estimates from h₁, h₂, ..., hₖ
- **Group and average**: split into groups, take median of group averages
- **HyperLogLog**: use registers for better accuracy

---

## 147.7 Frequency Moments (AMS Sketch)

### Definition

F_k = Σᵢ fᵢ^k where fᵢ is the frequency of element i.

| Moment | Meaning | Application |
|---|---|---|
| F₀ | Number of distinct elements | Database cardinality |
| F₁ | Total number of elements | Simple count |
| F₂ | Sum of squared frequencies | Data variance / surprise |
| F∞ | Maximum frequency | Heavy hitter detection |

### AMS Algorithm for F₂

Use a random sign function g(x) ∈ {-1, +1}:

```
Z = Σ g(xᵢ) × f(xᵢ)
E[Z²] = F₂
```

Maintain Z in a single pass. Use multiple independent estimates and take the median.

**Space**: O(1/ε² × log(1/δ)) for (ε, δ)-approximation.

---

## 147.8 Bloom Filter (Bonus)

While not strictly a streaming algorithm, Bloom filters are closely related.

### Problem

Test set membership with false positives but no false negatives.

### Algorithm

1. Bit array of size m, initially all 0
2. Use k hash functions
3. Insert(x): set bits at h₁(x), h₂(x), ..., hₖ(x) to 1
4. Query(x): return true if all k bits are 1

### False Positive Rate

```
p ≈ (1 - e^(-kn/m))^k
```

Optimal k = (m/n) × ln(2) ≈ 0.693 × m/n.

### Example

m = 16 bits, k = 3 hash functions.

```
Insert "cat":  h₁("cat")=2, h₂("cat")=7, h₃("cat")=12
  Array: 0010000100001000

Insert "dog":  h₁("dog")=1, h₂("dog")=5, h₃("dog")=12
  Array: 0110010100001000

Query "cat":   bits 2,7,12 all 1 → YES (true positive)
Query "fish":  h₁=2, h₂=5, h₃=9 → bit 9 is 0 → NO (true negative)
Query "bird":  h₁=1, h₂=5, h₃=12 → all 1 → YES (false positive!)
```

---

## 147.9 Complexity Summary

| Problem | Algorithm | Space | Error | Passes |
|---|---|---|---|---|
| Heavy Hitters | Misra-Gries | O(k) | ≤ n/k | 1 |
| Frequency Est. | Count-Min Sketch | O(1/ε × log(1/δ)) | ε·n | 1 |
| Distinct Count | HyperLogLog | O(1/ε²) | ε | 1 |
| Uniform Sampling | Reservoir Sampling | O(k) | Exact | 1 |
| F₂ (Variance) | AMS Sketch | O(1/ε²) | ε·F₂ | 1 |
| Set Membership | Bloom Filter | O(n log(1/ε)) | ε FP rate | 1 |

---

## 147.10 Code: Complete Implementations

### C++: Misra-Gries + Count-Min Sketch

```cpp
#include <iostream>
#include <vector>
#include <map>
#include <unordered_map>
#include <algorithm>
#include <random>
#include <cmath>
#include <cassert>

// ============================================================
// Misra-Gries: Find heavy hitters
// ============================================================
class MisraGries {
    int k;
    std::map<int, int> counters;

public:
    MisraGries(int k) : k(k) {}

    void process(int item) {
        if (counters.count(item)) {
            counters[item]++;
        } else if ((int)counters.size() < k - 1) {
            counters[item] = 1;
        } else {
            // Decrement all, remove zeros
            std::vector<int> toRemove;
            for (auto& [key, val] : counters) {
                val--;
                if (val <= 0) toRemove.push_back(key);
            }
            for (int key : toRemove) counters.erase(key);
        }
    }

    std::vector<std::pair<int, int>> getHeavyHitters() const {
        std::vector<std::pair<int, int>> result;
        for (auto& [key, val] : counters)
            result.push_back({key, val});
        return result;
    }

    int estimate(int item) const {
        auto it = counters.find(item);
        return it != counters.end() ? it->second : 0;
    }
};

// ============================================================
// Count-Min Sketch: Frequency estimation
// ============================================================
class CountMinSketch {
    int d, w;
    std::vector<std::vector<int>> table;
    std::vector<std::vector<int>> hashParams; // a, b for each hash

public:
    CountMinSketch(int d, int w, int seed = 42)
        : d(d), w(w), table(d, std::vector<int>(w, 0)) {
        std::mt19937 rng(seed);
        std::uniform_int_distribution<int> dist(1, w - 1);
        for (int i = 0; i < d; i++)
            hashParams.push_back({dist(rng), dist(rng)});
    }

    int hash(int i, int x) const {
        // Universal hash: (a*x + b) mod p mod w
        long long a = hashParams[i][0], b = hashParams[i][1];
        long long p = 2147483647; // Large prime
        return (int)(((a * x + b) % p) % w);
    }

    void add(int x, int count = 1) {
        for (int i = 0; i < d; i++)
            table[i][hash(i, x)] += count;
    }

    int estimate(int x) const {
        int minVal = INT_MAX;
        for (int i = 0; i < d; i++)
            minVal = std::min(minVal, table[i][hash(i, x)]);
        return minVal;
    }
};

// ============================================================
// Reservoir Sampling
// ============================================================
class ReservoirSampler {
    int k;
    std::vector<int> reservoir;
    int count;
    std::mt19937 rng;

public:
    ReservoirSampler(int k, int seed = 42)
        : k(k), count(0), rng(seed) {}

    void process(int item) {
        if (count < k) {
            reservoir.push_back(item);
        } else {
            std::uniform_int_distribution<int> dist(0, count);
            int j = dist(rng);
            if (j < k) reservoir[j] = item;
        }
        count++;
    }

    std::vector<int> getSample() const { return reservoir; }
    int totalSeen() const { return count; }
};

// ============================================================
// Flajolet-Martin (simplified distinct count)
// ============================================================
class FlajoletMartin {
    int R; // Max trailing zeros seen
    int numHashes;
    std::vector<int> maxR;
    std::vector<std::vector<int>> hashParams;

public:
    FlajoletMartin(int numHashes = 10, int seed = 42)
        : R(0), numHashes(numHashes), maxR(numHashes, 0) {
        std::mt19937 rng(seed);
        std::uniform_int_distribution<int> dist(1, 1000000);
        for (int i = 0; i < numHashes; i++)
            hashParams.push_back({dist(rng), dist(rng)});
    }

    int hash(int i, int x) const {
        long long a = hashParams[i][0], b = hashParams[i][1];
        return (int)((a * x + b) % 2147483647);
    }

    int trailingZeros(int val) const {
        if (val == 0) return 32;
        int count = 0;
        while ((val & 1) == 0) { val >>= 1; count++; }
        return count;
    }

    void process(int x) {
        for (int i = 0; i < numHashes; i++) {
            int h = hash(i, x);
            int tz = trailingZeros(h);
            maxR[i] = std::max(maxR[i], tz);
        }
    }

    int estimate() const {
        // Median of 2^R estimates
        std::vector<double> estimates;
        for (int i = 0; i < numHashes; i++)
            estimates.push_back(std::pow(2, maxR[i]));
        std::sort(estimates.begin(), estimates.end());
        return (int)estimates[numHashes / 2];
    }
};

// ============================================================
// Demo
// ============================================================
int main() {
    std::vector<int> stream = {1, 1, 1, 2, 2, 3, 1, 2, 3, 1, 2, 1};
    int n = stream.size();

    // Misra-Gries
    std::cout << "=== Misra-Gries (Heavy Hitters) ===\n";
    MisraGries mg(3);
    for (int x : stream) mg.process(x);
    auto heavy = mg.getHeavyHitters();
    for (auto& [val, cnt] : heavy)
        std::cout << "  Element " << val << ": est ≥ " << cnt
                  << " (true: " << std::count(stream.begin(), stream.end(), val) << ")\n";

    // Count-Min Sketch
    std::cout << "\n=== Count-Min Sketch ===\n";
    CountMinSketch cms(4, 16);
    for (int x : stream) cms.add(x);
    for (int x : {1, 2, 3, 4})
        std::cout << "  freq(" << x << "): est=" << cms.estimate(x)
                  << " true=" << std::count(stream.begin(), stream.end(), x) << "\n";

    // Reservoir Sampling
    std::cout << "\n=== Reservoir Sampling ===\n";
    ReservoirSampler rs(3);
    for (int x : stream) rs.process(x);
    auto sample = rs.getSample();
    std::cout << "  Sample (k=3): ";
    for (int x : sample) std::cout << x << " ";
    std::cout << "\n";

    // Flajolet-Martin
    std::cout << "\n=== Flajolet-Martin (Distinct Count) ===\n";
    FlajoletMartin fm(20);
    for (int x : stream) fm.process(x);
    std::cout << "  Estimated distinct: " << fm.estimate() << "\n";
    std::cout << "  True distinct: 3\n";

    return 0;
}
```

### Python: Complete Streaming Toolkit

```python
import random
import math
from collections import defaultdict

class MisraGries:
    """Heavy hitter detection: find elements with frequency > n/k."""

    def __init__(self, k):
        self.k = k
        self.counters = {}

    def process(self, item):
        if item in self.counters:
            self.counters[item] += 1
        elif len(self.counters) < self.k - 1:
            self.counters[item] = 1
        else:
            # Decrement all, remove zeros
            to_remove = []
            for key in self.counters:
                self.counters[key] -= 1
                if self.counters[key] <= 0:
                    to_remove.append(key)
            for key in to_remove:
                del self.counters[key]

    def get_heavy_hitters(self):
        return dict(self.counters)

    def estimate(self, item):
        return self.counters.get(item, 0)


class CountMinSketch:
    """Frequency estimation with configurable error bounds."""

    def __init__(self, epsilon=0.01, delta=0.01, seed=42):
        self.w = int(math.ceil(math.e / epsilon))
        self.d = int(math.ceil(math.log(1 / delta)))
        self.table = [[0] * self.w for _ in range(self.d)]
        random.seed(seed)
        self.hash_params = [(random.randint(1, self.w - 1),
                             random.randint(1, self.w - 1)) for _ in range(self.d)]
        self.p = 2**31 - 1

    def _hash(self, i, x):
        a, b = self.hash_params[i]
        return ((a * x + b) % self.p) % self.w

    def add(self, x, count=1):
        for i in range(self.d):
            self.table[i][self._hash(i, x)] += count

    def estimate(self, x):
        return min(self.table[i][self._hash(i, x)] for i in range(self.d))


class ReservoirSampler:
    """Sample k items uniformly from a stream of unknown size."""

    def __init__(self, k, seed=42):
        self.k = k
        self.reservoir = []
        self.count = 0
        random.seed(seed)

    def process(self, item):
        if self.count < self.k:
            self.reservoir.append(item)
        else:
            j = random.randint(0, self.count)
            if j < self.k:
                self.reservoir[j] = item
        self.count += 1

    def get_sample(self):
        return list(self.reservoir)


class BloomFilter:
    """Space-efficient set membership with false positives."""

    def __init__(self, n, fp_rate=0.01, seed=42):
        self.m = int(-n * math.log(fp_rate) / (math.log(2) ** 2))
        self.k = int((self.m / n) * math.log(2))
        self.bits = [0] * self.m
        random.seed(seed)
        self.hash_params = [(random.randint(1, 10**6),
                             random.randint(1, 10**6)) for _ in range(self.k)]
        self.p = 2**31 - 1

    def _hash(self, i, x):
        a, b = self.hash_params[i]
        return ((a * x + b) % self.p) % self.m

    def add(self, x):
        for i in range(self.k):
            self.bits[self._hash(i, x)] = 1

    def contains(self, x):
        return all(self.bits[self._hash(i, x)] for i in range(self.k))


class HyperLogLog:
    """Approximate distinct count with O(1/epsilon^2) space."""

    def __init__(self, b=10, seed=42):
        self.b = b
        self.m = 1 << b  # 2^b registers
        self.registers = [0] * self.m
        self.alpha = self._compute_alpha()
        random.seed(seed)
        self.hash_a = random.randint(1, 10**6)
        self.hash_b = random.randint(1, 10**6)
        self.p = 2**31 - 1

    def _compute_alpha(self):
        if self.m == 16:
            return 0.673
        elif self.m == 32:
            return 0.697
        elif self.m == 64:
            return 0.709
        else:
            return 0.7213 / (1 + 1.079 / self.m)

    def _hash(self, x):
        return (self.hash_a * x + self.hash_b) % self.p

    def _leading_zeros(self, val, bits=32):
        if val == 0:
            return bits
        count = 0
        for i in range(bits - 1, -1, -1):
            if val & (1 << i):
                break
            count += 1
        return count + 1

    def add(self, x):
        h = self._hash(x)
        j = h >> (32 - self.b)  # First b bits → register index
        w = h & ((1 << (32 - self.b)) - 1)  # Remaining bits
        self.registers[j] = max(self.registers[j], self._leading_zeros(w, 32 - self.b))

    def estimate(self):
        harmonic_mean = sum(2 ** (-r) for r in self.registers)
        est = self.alpha * self.m * self.m / harmonic_mean
        # Small range correction
        if est <= 2.5 * self.m:
            zeros = self.registers.count(0)
            if zeros > 0:
                est = self.m * math.log(self.m / zeros)
        return int(est)


def demo():
    stream = [1, 1, 1, 2, 2, 3, 1, 2, 3, 1, 2, 1]
    true_freq = defaultdict(int)
    for x in stream:
        true_freq[x] += 1

    print("=== Misra-Gries (Heavy Hitters) ===")
    mg = MisraGries(3)
    for x in stream:
        mg.process(x)
    print(f"Heavy hitters: {mg.get_heavy_hitters()}")
    print(f"True frequencies: {dict(true_freq)}")

    print("\n=== Count-Min Sketch ===")
    cms = CountMinSketch(epsilon=0.1, delta=0.05)
    for x in stream:
        cms.add(x)
    for x in [1, 2, 3, 4]:
        print(f"  freq({x}): est={cms.estimate(x)}, true={true_freq[x]}")

    print("\n=== Reservoir Sampling ===")
    rs = ReservoirSampler(3)
    for x in stream:
        rs.process(x)
    print(f"Sample: {rs.get_sample()}")

    print("\n=== Bloom Filter ===")
    bf = BloomFilter(10, fp_rate=0.05)
    for x in [1, 2, 3]:
        bf.add(x)
    for x in [1, 2, 3, 4, 5]:
        print(f"  contains({x}): {bf.contains(x)}")

    print("\n=== HyperLogLog ===")
    hll = HyperLogLog(b=10)
    for x in range(10000):
        hll.add(x)
    print(f"Estimated distinct: {hll.estimate()} (true: 10000)")


if __name__ == "__main__":
    demo()
```

### Java: Streaming Algorithms

```java
import java.util.*;

public class StreamingAlgorithms {

    // Misra-Gries Heavy Hitters
    static class MisraGries {
        private int k;
        private Map<Integer, Integer> counters = new HashMap<>();

        public MisraGries(int k) { this.k = k; }

        public void process(int item) {
            if (counters.containsKey(item)) {
                counters.merge(item, 1, Integer::sum);
            } else if (counters.size() < k - 1) {
                counters.put(item, 1);
            } else {
                List<Integer> toRemove = new ArrayList<>();
                for (Map.Entry<Integer, Integer> e : counters.entrySet()) {
                    e.setValue(e.getValue() - 1);
                    if (e.getValue() <= 0) toRemove.add(e.getKey());
                }
                toRemove.forEach(counters::remove);
            }
        }

        public Map<Integer, Integer> getHeavyHitters() {
            return new HashMap<>(counters);
        }
    }

    // Reservoir Sampling
    static class ReservoirSampler {
        private int k;
        private List<Integer> reservoir = new ArrayList<>();
        private int count = 0;
        private Random rng;

        public ReservoirSampler(int k, int seed) {
            this.k = k;
            this.rng = new Random(seed);
        }

        public void process(int item) {
            if (count < k) {
                reservoir.add(item);
            } else {
                int j = rng.nextInt(count + 1);
                if (j < k) reservoir.set(j, item);
            }
            count++;
        }

        public List<Integer> getSample() { return new ArrayList<>(reservoir); }
    }

    // Count-Min Sketch
    static class CountMinSketch {
        private int d, w;
        private int[][] table;
        private long[] hashA, hashB;

        public CountMinSketch(int d, int w, long seed) {
            this.d = d; this.w = w;
            table = new int[d][w];
            Random rng = new Random(seed);
            hashA = new long[d];
            hashB = new long[d];
            for (int i = 0; i < d; i++) {
                hashA[i] = rng.nextInt(w - 1) + 1;
                hashB[i] = rng.nextInt(w - 1) + 1;
            }
        }

        private int hash(int i, int x) {
            return (int)(((hashA[i] * x + hashB[i]) % 2147483647L) % w);
        }

        public void add(int x) {
            for (int i = 0; i < d; i++)
                table[i][hash(i, x)]++;
        }

        public int estimate(int x) {
            int min = Integer.MAX_VALUE;
            for (int i = 0; i < d; i++)
                min = Math.min(min, table[i][hash(i, x)]);
            return min;
        }
    }

    public static void main(String[] args) {
        int[] stream = {1, 1, 1, 2, 2, 3, 1, 2, 3, 1, 2, 1};

        System.out.println("=== Misra-Gries ===");
        MisraGries mg = new MisraGries(3);
        for (int x : stream) mg.process(x);
        System.out.println("Heavy hitters: " + mg.getHeavyHitters());

        System.out.println("\n=== Reservoir Sampling ===");
        ReservoirSampler rs = new ReservoirSampler(3, 42);
        for (int x : stream) rs.process(x);
        System.out.println("Sample: " + rs.getSample());

        System.out.println("\n=== Count-Min Sketch ===");
        CountMinSketch cms = new CountMinSketch(4, 16, 42);
        for (int x : stream) cms.add(x);
        for (int x : new int[]{1, 2, 3, 4})
            System.out.println("  freq(" + x + "): est=" + cms.estimate(x));
    }
}
```

---

## 147.11 Applications

| Application | Algorithm | Use Case |
|---|---|---|
| Network monitoring | Count-Min Sketch | Traffic analysis, DDoS detection |
| Database systems | HyperLogLog | Cardinality estimation |
| Web analytics | Bloom Filter | URL deduplication |
| Log analysis | Misra-Gries | Find most frequent errors |
| A/B testing | Reservoir Sampling | Sample users uniformly |
| Social networks | AMS Sketch | Community size estimation |
| Search engines | Bloom Filter | URL seen-before check |
| IoT sensors | Streaming sketches | Anomaly detection |

---

## 147.12 Exercises

### Conceptual Exercises

1. **Prove** that Misra-Gries finds all elements with frequency > n/k. (Hint: count total decrements.)

2. **Explain** why Count-Min Sketch never underestimates frequencies.

3. **Show** that reservoir sampling gives each element probability k/n of being selected.

4. **Compare** the space requirements of exact distinct counting vs HyperLogLog for n = 10^9.

### Coding Exercises

5. **Implement** a Count-Min Sketch with conservative update (only increment the counter that equals the minimum).

6. **Build** a streaming median estimator using two heaps.

7. **Implement** a Bloom filter that supports deletion (counting Bloom filter).

8. **Write** a streaming algorithm to find the top-k most frequent elements using Count-Min Sketch + a min-heap.

### Challenge Exercises

9. **Design** a streaming algorithm for estimating the entropy H = -Σ pᵢ log pᵢ of a stream.

10. **Implement** a streaming algorithm for heavy hitters in the turnstile model (insertions and deletions).

---

## 147.13 Interview Questions

### Conceptual Questions

1. **Q**: You have a stream of 1 billion URLs and want to find the 100 most visited. What data structure would you use?
   **A**: Misra-Gries with k=100 for exact heavy hitters, or Count-Min Sketch + min-heap for approximate top-k. Space: O(k) for Misra-Gries, O(1/ε) for CMS.

2. **Q**: How would you count distinct users visiting a website with 1GB RAM and 100GB of logs?
   **A**: Use HyperLogLog with ~65K registers (~64KB). Hash each user ID, update registers. Estimate gives ~0.4% error.

3. **Q**: What's the difference between Count-Min Sketch and a hash table?
   **A**: CMS uses fixed space and always returns an estimate (overestimate). Hash table uses O(n) space and gives exact answers. CMS is for streaming; hash table requires all data in memory.

### Implementation Questions

4. **Q**: How do you choose the parameters for a Bloom filter?
   **A**: Given n elements and desired false positive rate p: m = -n ln(p) / (ln2)² bits, k = (m/n) ln2. For n=1M, p=1%: m ≈ 9.6M bits ≈ 1.2MB, k ≈ 7.

5. **Q**: Can you use a Bloom filter for deletion?
   **A**: Not directly (setting bits to 0 affects other elements). Use a counting Bloom filter (replace bits with counters) or a Cuckoo filter.

### Systems Questions

6. **Q**: How does Google use HyperLogLog in BigQuery?
   **A**: BigQuery uses HyperLogLog++ (improved version) for `COUNT(DISTINCT)` queries. It provides approximate cardinality with <1% error using only 16KB per sketch, even for billions of distinct values.

---

## 147.14 Cross-References

- **Chapter 7 (Hash Tables)**: Hash functions are fundamental to all sketches
- **Chapter 8 (Bloom Filter)**: Set membership with false positives
- **Chapter 112 (Heap)**: Used in streaming median and top-k
- **Chapter 145 (Divide and Conquer on Graphs)**: Some streaming algorithms use divide and conquer
- **Chapter 148 (Approximation Algorithms)**: Streaming as a form of approximation
- **Chapter 153 (Randomized Algorithms)**: Probabilistic analysis of sketches

---

## Summary

| Problem | Algorithm | Space | Error | Key Idea |
|---|---|---|---|---|
| Heavy Hitters | Misra-Gries | O(k) | ≤ n/k | Counter with decrement |
| Frequency Est. | Count-Min Sketch | O(1/ε × log(1/δ)) | Overestimate by ε·n | Multiple hash tables |
| Distinct Count | HyperLogLog | O(1/ε²) | ~1.04/√m | Leading zeros in hash |
| Uniform Sample | Reservoir Sampling | O(k) | Exact | Random replacement |
| F₂ Moment | AMS Sketch | O(1/ε²) | ε·F₂ | Random signs |
| Set Membership | Bloom Filter | O(n log(1/ε)) | ε FP rate | Multiple hash bits |

**Key Takeaway**: Streaming algorithms trade exactness for massive space savings. The fundamental techniques — hashing, random sampling, and probabilistic counting — enable processing of datasets that far exceed available memory. Understanding these algorithms is essential for big data systems, network monitoring, and database query optimization.
