# Chapter 63: Randomized Algorithms

## Prerequisites

- Basic probability theory
- Sorting algorithms
- Hash tables
- Binary search trees
- Expected value computation

## Interview Frequency: ★★

Randomized algorithms appear in interviews at **Google**, **Meta**, and **Amazon**. Reservoir sampling is a classic **Google** interview question. Randomized QuickSort is fundamental knowledge. Hash randomization is important for system design interviews. Understanding Monte Carlo vs Las Vegas algorithms shows depth of knowledge.

| Topic | Frequency | Typical Companies | Difficulty |
|---|---|---|---|
| Reservoir Sampling | ★★★★ | Google, Meta, Amazon | Medium |
| Randomized QuickSort | ★★★ | All companies | Medium |
| Randomized BST | ★★ | Google, research | Medium-Hard |
| Monte Carlo vs Las Vegas | ★★ | Google, theoretical | Easy |
| Hash Randomization | ★★★ | Google, Amazon, system design | Medium |
| Randomized DS | ★★ | Competitive programming | Medium |

---

## 63.1 Reservoir Sampling

**Reservoir Sampling** uniformly samples k items from a stream of unknown size n. Each element has exactly k/n probability of being selected.

### The Problem

Given a stream of items (size unknown), select k items uniformly at random. You can only traverse the stream once and use O(k) space.

### Algorithm (k=1)

1. Keep the first item
2. For the i-th item (i ≥ 2), replace the kept item with probability 1/i

### Proof of Uniformity

For the i-th item to be in the reservoir at the end:
- It must be selected when it arrives: probability 1/i
- It must not be replaced by any later item j: probability (1 - 1/j) for each j > i

P(item i is selected) = (1/i) × ∏(j=i+1 to n) (j-1)/j = (1/i) × (i/(i+1)) × ((i+1)/(i+2)) × ... × ((n-1)/n) = 1/n

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <cassert>

class ReservoirSampling {
    std::mt19937 rng;
    
public:
    ReservoirSampling() : rng(std::chrono::steady_clock::now()
        .time_since_epoch().count()) {}
    
    // Sample 1 item from stream
    int sampleOne(const std::vector<int>& stream) {
        int result = stream[0];
        for (int i = 1; i < (int)stream.size(); i++) {
            std::uniform_int_distribution<int> dist(0, i);
            if (dist(rng) == 0) {
                result = stream[i];
            }
        }
        return result;
    }
    
    // Sample k items from stream
    std::vector<int> sampleK(const std::vector<int>& stream, int k) {
        int n = stream.size();
        std::vector<int> reservoir(stream.begin(), stream.begin() + k);
        
        for (int i = k; i < n; i++) {
            std::uniform_int_distribution<int> dist(0, i);
            int j = dist(rng);
            if (j < k) {
                reservoir[j] = stream[i];
            }
        }
        
        return reservoir;
    }
    
    // Weighted reservoir sampling
    // Each item has a weight; probability proportional to weight
    int sampleWeighted(const std::vector<int>& items, 
                       const std::vector<double>& weights) {
        double totalWeight = 0;
        int result = items[0];
        
        for (int i = 0; i < (int)items.size(); i++) {
            totalWeight += weights[i];
            std::uniform_real_distribution<double> dist(0.0, 1.0);
            if (dist(rng) < weights[i] / totalWeight) {
                result = items[i];
            }
        }
        
        return result;
    }
};

int main() {
    ReservoirSampling rs;
    
    // Test uniformity of sampling
    std::vector<int> stream = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    int trials = 100000;
    std::vector<int> count(11, 0);
    
    for (int t = 0; t < trials; t++) {
        int sampled = rs.sampleOne(stream);
        count[sampled]++;
    }
    
    std::cout << "Uniformity test (should be ~10000 each):\n";
    for (int i = 1; i <= 10; i++) {
        std::cout << "Item " << i << ": " << count[i] << "\n";
    }
    
    // Sample k=3 items
    std::cout << "\nSample 3 items from [1..10]: ";
    auto sample = rs.sampleK(stream, 3);
    for (int x : sample) std::cout << x << " ";
    std::cout << "\n";
    
    // Weighted sampling
    std::vector<double> weights = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    std::vector<int> wCount(11, 0);
    for (int t = 0; t < trials; t++) {
        int sampled = rs.sampleWeighted(stream, weights);
        wCount[sampled]++;
    }
    
    std::cout << "\nWeighted sampling (weight proportional):\n";
    double totalWeight = 55.0;
    for (int i = 1; i <= 10; i++) {
        double expected = weights[i-1] / totalWeight * trials;
        std::cout << "Item " << i << " (weight " << weights[i-1] << "): " 
                  << wCount[i] << " (expected ~" << (int)expected << ")\n";
    }
    
    return 0;
}
```

### Applications

| Application | Variant | Use Case |
|---|---|---|
| Random element from stream | k=1 | Database sampling |
| Random subset | k items | A/B testing |
| Weighted sampling | Weighted | Recommendation systems |
| Streaming algorithms | Online | Big data processing |

---

## 63.2 Randomized QuickSort

**Randomized QuickSort** picks a random pivot, achieving expected O(n log n) time regardless of input. The worst case O(n²) still exists but has negligible probability.

### Why Random Pivot Helps

For any input (including adversarial), the expected number of comparisons is:

```
E[comparisons] = 2n ln(n) ≈ 1.39n log₂(n)
```

This is because each pair of elements is compared at most once, and the probability they're compared depends on whether one is chosen as pivot before the other.

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <algorithm>
#include <cassert>

class RandomizedQuickSort {
    std::mt19937 rng;
    
public:
    RandomizedQuickSort() : rng(std::chrono::steady_clock::now()
        .time_since_epoch().count()) {}
    
    void sort(std::vector<int>& arr) {
        quickSort(arr, 0, arr.size() - 1);
    }
    
private:
    int partition(std::vector<int>& arr, int lo, int hi) {
        // Random pivot
        std::uniform_int_distribution<int> dist(lo, hi);
        int pivotIdx = dist(rng);
        std::swap(arr[pivotIdx], arr[hi]);
        
        int pivot = arr[hi];
        int i = lo;
        
        for (int j = lo; j < hi; j++) {
            if (arr[j] <= pivot) {
                std::swap(arr[i], arr[j]);
                i++;
            }
        }
        std::swap(arr[i], arr[hi]);
        return i;
    }
    
    void quickSort(std::vector<int>& arr, int lo, int hi) {
        if (lo < hi) {
            int p = partition(arr, lo, hi);
            quickSort(arr, lo, p - 1);
            quickSort(arr, p + 1, hi);
        }
    }
};

// Three-way partition for arrays with many duplicates
class ThreeWayQuickSort {
    std::mt19937 rng;
    
public:
    ThreeWayQuickSort() : rng(std::chrono::steady_clock::now()
        .time_since_epoch().count()) {}
    
    void sort(std::vector<int>& arr) {
        quickSort(arr, 0, arr.size() - 1);
    }
    
private:
    void quickSort(std::vector<int>& arr, int lo, int hi) {
        if (lo >= hi) return;
        
        std::uniform_int_distribution<int> dist(lo, hi);
        int pivotIdx = dist(rng);
        std::swap(arr[lo], arr[pivotIdx]);
        
        int pivot = arr[lo];
        int lt = lo, gt = hi, i = lo;
        
        // arr[lo..lt-1] < pivot
        // arr[lt..i-1] == pivot
        // arr[gt+1..hi] > pivot
        while (i <= gt) {
            if (arr[i] < pivot) {
                std::swap(arr[lt++], arr[i++]);
            } else if (arr[i] > pivot) {
                std::swap(arr[i], arr[gt--]);
            } else {
                i++;
            }
        }
        
        quickSort(arr, lo, lt - 1);
        quickSort(arr, gt + 1, hi);
    }
};

int main() {
    std::vector<int> arr = {3, 6, 8, 10, 1, 2, 1};
    
    RandomizedQuickSort rq;
    rq.sort(arr);
    
    std::cout << "Sorted: ";
    for (int x : arr) std::cout << x << " ";
    std::cout << "\n";
    
    // Verify against std::sort
    std::vector<int> arr2 = {5, 3, 8, 1, 9, 2, 7, 4, 6};
    std::vector<int> expected = arr2;
    std::sort(expected.begin(), expected.end());
    
    ThreeWayQuickSort tq;
    tq.sort(arr2);
    
    assert(arr2 == expected);
    std::cout << "Three-way sort verified.\n";
    
    // Performance comparison
    int n = 1000000;
    std::vector<int> largeArr(n);
    std::mt19937 rng(42);
    for (int& x : largeArr) x = rng();
    
    auto start = std::chrono::high_resolution_clock::now();
    std::vector<int> arr3 = largeArr;
    tq.sort(arr3);
    auto end = std::chrono::high_resolution_clock::now();
    
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    std::cout << "Sorted " << n << " elements in " << duration.count() << "ms\n";
    
    return 0;
}
```

### QuickSort vs Other Sorts

| Algorithm | Expected | Worst | Space | Stable | Notes |
|---|---|---|---|---|---|
| Randomized QuickSort | O(n log n) | O(n²) | O(log n) | No | Best practical |
| Merge Sort | O(n log n) | O(n log n) | O(n) | Yes | Guaranteed |
| Heap Sort | O(n log n) | O(n log n) | O(1) | No | In-place |
| IntroSort | O(n log n) | O(n log n) | O(log n) | No | std::sort |

---

## 63.3 Randomized BST (Treap)

A **Treap** combines BST property (on keys) with heap property (on random priorities). The random priorities ensure the tree is balanced in expectation.

```cpp
#include <iostream>
#include <random>
#include <chrono>
#include <vector>

struct TreapNode {
    int key, priority, size;
    TreapNode *left, *right;
    
    TreapNode(int k) : key(k), priority(rand()), size(1), 
                        left(nullptr), right(nullptr) {}
    
    void update() {
        size = 1 + (left ? left->size : 0) + (right ? right->size : 0);
    }
};

std::pair<TreapNode*, TreapNode*> split(TreapNode* root, int key) {
    if (!root) return {nullptr, nullptr};
    if (root->key <= key) {
        auto [l, r] = split(root->right, key);
        root->right = l;
        root->update();
        return {root, r};
    } else {
        auto [l, r] = split(root->left, key);
        root->left = r;
        root->update();
        return {l, root};
    }
}

TreapNode* merge(TreapNode* l, TreapNode* r) {
    if (!l) return r;
    if (!r) return l;
    if (l->priority > r->priority) {
        l->right = merge(l->right, r);
        l->update();
        return l;
    } else {
        r->left = merge(l, r->left);
        r->update();
        return r;
    }
}

TreapNode* insert(TreapNode* root, int key) {
    auto [l, r] = split(root, key);
    return merge(merge(l, new TreapNode(key)), r);
}

bool search(TreapNode* root, int key) {
    if (!root) return false;
    if (root->key == key) return true;
    if (key < root->key) return search(root->left, key);
    return search(root->right, key);
}

int main() {
    TreapNode* root = nullptr;
    for (int x : {5, 3, 7, 1, 4, 6, 8}) {
        root = insert(root, x);
    }
    
    for (int x : {1, 4, 5, 9}) {
        std::cout << "Search " << x << ": " 
                  << (search(root, x) ? "found" : "not found") << "\n";
    }
    
    return 0;
}
```

### Why Random Priorities Work

The expected height of a treap with n nodes is O(log n). This is because:
- The priority assignment is equivalent to building a random BST
- Random BSTs have expected height O(log n) (well-known result)
- The treap is just a different representation of the same structure

---

## 63.4 Monte Carlo vs Las Vegas Algorithms

### Definitions

| Type | Behavior | Example |
|---|---|---|
| **Las Vegas** | Always correct, random running time | Randomized QuickSort |
| **Monte Carlo** | Bounded running time, may be incorrect | Miller-Rabin primality |

### Las Vegas Algorithms

- Output is always correct
- Running time is a random variable
- Expected running time is analyzed
- Examples: Randomized QuickSort, Randomized BST

### Monte Carlo Algorithms

- Running time is deterministic (or bounded)
- Output may be incorrect with some probability
- Error probability can be made arbitrarily small
- Examples: Miller-Rabin, random sampling

### Conversion

Any Las Vegas algorithm can be converted to Monte Carlo by setting a time limit. Any Monte Carlo algorithm with one-sided error can be converted to Las Vegas by checking the answer.

```cpp
#include <iostream>
#include <random>
#include <chrono>

// Las Vegas: always correct, random time
// Example: find a specific value in a random permutation
int lasVegasSearch(const std::vector<int>& arr, int target) {
    std::mt19937 rng(std::chrono::steady_clock::now()
        .time_since_epoch().count());
    
    int n = arr.size();
    std::vector<bool> checked(n, false);
    
    for (int step = 0; step < n; step++) {
        int idx;
        do {
            idx = std::uniform_int_distribution<int>(0, n - 1)(rng);
        } while (checked[idx]);
        
        checked[idx] = true;
        if (arr[idx] == target) return idx;
    }
    
    return -1; // Not found (but always correct if found)
}

// Monte Carlo: bounded time, may be wrong
// Example: estimate π by random sampling
double monteCarloPi(int samples) {
    std::mt19937 rng(42);
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    
    int inside = 0;
    for (int i = 0; i < samples; i++) {
        double x = dist(rng);
        double y = dist(rng);
        if (x * x + y * y <= 1.0) inside++;
    }
    
    return 4.0 * inside / samples;
}

int main() {
    // Las Vegas: always finds the answer
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6};
    int idx = lasVegasSearch(arr, 5);
    std::cout << "Las Vegas: found 5 at index " << idx << "\n";
    
    // Monte Carlo: estimates π
    for (int n : {100, 1000, 10000, 100000}) {
        double pi = monteCarloPi(n);
        std::cout << "Monte Carlo π (n=" << n << "): " << pi << "\n";
    }
    
    return 0;
}
```

---

## 63.5 Hash Randomization

### Universal Hashing

A family of hash functions H is **universal** if for any two distinct keys x, y:

```
P(h(x) = h(y)) ≤ 1/m
```

where m is the table size. This ensures O(1) expected time for operations even with adversarial input.

### The Problem with Deterministic Hashing

An adversary can craft input that causes all keys to hash to the same bucket, turning O(1) operations into O(n).

### Random Hash Function

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <functional>

class UniversalHash {
    long long a, b, p, m;
    
public:
    UniversalHash(long long tableSize) : m(tableSize) {
        std::mt19937 rng(std::chrono::steady_clock::now()
            .time_since_epoch().count());
        p = 1000000007; // Large prime
        std::uniform_int_distribution<long long> distA(1, p - 1);
        std::uniform_int_distribution<long long> distB(0, p - 1);
        a = distA(rng);
        b = distB(rng);
    }
    
    long long hash(long long key) {
        return ((a * key + b) % p) % m;
    }
};

class RandomizedHashTable {
    int m;
    std::vector<std::vector<std::pair<int, int>>> table;
    UniversalHash hashFunc;
    
public:
    RandomizedHashTable(int size) : m(size), table(size), hashFunc(size) {}
    
    void insert(int key, int value) {
        int idx = hashFunc.hash(key);
        for (auto& [k, v] : table[idx]) {
            if (k == key) {
                v = value;
                return;
            }
        }
        table[idx].push_back({key, value});
    }
    
    bool find(int key, int& value) {
        int idx = hashFunc.hash(key);
        for (auto& [k, v] : table[idx]) {
            if (k == key) {
                value = v;
                return true;
            }
        }
        return false;
    }
    
    void erase(int key) {
        int idx = hashFunc.hash(key);
        auto& bucket = table[idx];
        for (auto it = bucket.begin(); it != bucket.end(); ++it) {
            if (it->first == key) {
                bucket.erase(it);
                return;
            }
        }
    }
};

int main() {
    RandomizedHashTable ht(100);
    
    for (int i = 0; i < 50; i++) {
        ht.insert(i, i * i);
    }
    
    for (int i = 0; i < 50; i += 10) {
        int val;
        if (ht.find(i, val)) {
            std::cout << "key=" << i << ", value=" << val << "\n";
        }
    }
    
    return 0;
}
```

### Hash Randomization Techniques

| Technique | Description | Use Case |
|---|---|---|
| Universal hashing | Random hash from universal family | Adversarial inputs |
| Double hashing | Two independent hash functions | Collision resolution |
| Cuckoo hashing | Two tables, two hash functions | Worst-case O(1) lookup |
| Tabulation hashing | Lookup table per byte | Fast, practical |

---

## 63.6 Randomized Data Structures

### Overview

| Structure | Deterministic | Randomized | Benefit |
|---|---|---|---|
| BST | AVL/Red-Black O(log n) | Treap O(log n) expected | Simpler code |
| Skip List | N/A | O(log n) expected | Simple, parallelizable |
| Hash Table | Chaining O(1) amortized | Universal O(1) expected | Adversarial-proof |
| Bloom Filter | N/A | Probabilistic | Space-efficient |

### Skip List (Overview)

A **Skip List** is a probabilistic alternative to balanced BSTs. Each node has a random number of forward pointers. Expected O(log n) search, insert, and delete.

```
Level 3: HEAD ──────────────────────────→ 5 ───────────→ NULL
Level 2: HEAD ───────────→ 3 ───────────→ 5 ──→ 7 ─────→ NULL
Level 1: HEAD ──→ 1 ─────→ 3 ──→ 4 ─────→ 5 ──→ 7 ──→ 9 → NULL
```

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <climits>

class SkipList {
    struct Node {
        int val;
        std::vector<Node*> next;
        Node(int v, int level) : val(v), next(level + 1, nullptr) {}
    };
    
    Node* head;
    int maxLevel;
    int currentLevel;
    std::mt19937 rng;
    
    int randomLevel() {
        int level = 0;
        while (std::uniform_real_distribution<double>(0.0, 1.0)(rng) < 0.5 
               && level < maxLevel) {
            level++;
        }
        return level;
    }
    
public:
    SkipList(int maxLvl = 32) : maxLevel(maxLvl), currentLevel(0),
        rng(std::chrono::steady_clock::now().time_since_epoch().count()) {
        head = new Node(INT_MIN, maxLevel);
    }
    
    bool search(int val) {
        Node* curr = head;
        for (int i = currentLevel; i >= 0; i--) {
            while (curr->next[i] && curr->next[i]->val < val) {
                curr = curr->next[i];
            }
        }
        curr = curr->next[0];
        return curr && curr->val == val;
    }
    
    void insert(int val) {
        std::vector<Node*> update(maxLevel + 1, nullptr);
        Node* curr = head;
        
        for (int i = currentLevel; i >= 0; i--) {
            while (curr->next[i] && curr->next[i]->val < val) {
                curr = curr->next[i];
            }
            update[i] = curr;
        }
        
        int newLevel = randomLevel();
        if (newLevel > currentLevel) {
            for (int i = currentLevel + 1; i <= newLevel; i++) {
                update[i] = head;
            }
            currentLevel = newLevel;
        }
        
        Node* newNode = new Node(val, newLevel);
        for (int i = 0; i <= newLevel; i++) {
            newNode->next[i] = update[i]->next[i];
            update[i]->next[i] = newNode;
        }
    }
};

int main() {
    SkipList sl;
    
    for (int x : {3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5}) {
        sl.insert(x);
    }
    
    for (int x : {1, 3, 5, 7, 9}) {
        std::cout << "Search " << x << ": " 
                  << (sl.search(x) ? "found" : "not found") << "\n";
    }
    
    return 0;
}
```

---

## 63.7 Randomized Algorithm Design Principles

### When to Use Randomization

Randomization is powerful when:

1. **Adversarial worst-case is bad**: Random choices avoid worst-case inputs
2. **Average case is good**: Random pivot gives expected O(n log n)
3. **Simplicity matters**: Randomized solutions are often simpler
4. **Approximate answers suffice**: Monte Carlo methods
5. **Breaking symmetry**: Distributed algorithms, hash functions

### Randomization Techniques

| Technique | Purpose | Example |
|---|---|---|
| Random pivot | Avoid worst-case | QuickSort |
| Random priorities | Balance trees | Treap, Skip List |
| Random sampling | Estimate statistics | Reservoir sampling |
| Random hashing | Avoid collisions | Universal hashing |
| Random permutation | Break input patterns | Randomized algorithms |
| Random restarts | Escape local optima | Simulated annealing |

### Analyzing Randomized Algorithms

**Expected Time Analysis**:
- Define indicator random variables
- Use linearity of expectation
- Example: QuickSort comparisons = Σ over pairs (i,j) of Pr(i and j compared)

**Tail Bounds**:
- Markov's inequality: Pr(X ≥ a) ≤ E[X]/a
- Chebyshev's inequality: Pr(|X - μ| ≥ kσ) ≤ 1/k²
- Chernoff bound: Pr(X ≥ (1+δ)μ) ≤ ... (for sums of independent RVs)

```cpp
#include <iostream>
#include <random>
#include <chrono>
#include <vector>
#include <algorithm>
#include <cmath>
#include <iomanip>

// Demonstrate expected value analysis
// Randomized QuickSort: expected number of comparisons

int comparisons = 0;

void quickSort(std::vector<int>& arr, int lo, int hi, std::mt19937& rng) {
    if (lo >= hi) return;
    
    std::uniform_int_distribution<int> dist(lo, hi);
    int pivotIdx = dist(rng);
    std::swap(arr[pivotIdx], arr[hi]);
    
    int pivot = arr[hi];
    int i = lo;
    for (int j = lo; j < hi; j++) {
        comparisons++;
        if (arr[j] <= pivot) {
            std::swap(arr[i++], arr[j]);
        }
    }
    std::swap(arr[i], arr[hi]);
    
    quickSort(arr, lo, i - 1, rng);
    quickSort(arr, i + 1, hi, rng);
}

int main() {
    int n = 100;
    int trials = 1000;
    
    std::mt19937 rng(42);
    long long totalComparisons = 0;
    
    for (int t = 0; t < trials; t++) {
        std::vector<int> arr(n);
        std::iota(arr.begin(), arr.end(), 0);
        std::shuffle(arr.begin(), arr.end(), rng);
        
        comparisons = 0;
        quickSort(arr, 0, n - 1, rng);
        totalComparisons += comparisons;
    }
    
    double avgComparisons = (double)totalComparisons / trials;
    double expected = 2.0 * n * std::log2(n);
    
    std::cout << std::fixed << std::setprecision(1);
    std::cout << "n = " << n << ", trials = " << trials << "\n";
    std::cout << "Average comparisons: " << avgComparisons << "\n";
    std::cout << "Expected (2n ln n): " << expected << "\n";
    std::cout << "Ratio: " << avgComparisons / expected << "\n";
    
    return 0;
}
```

### Common Pitfalls in Randomized Algorithms

| Pitfall | Problem | Solution |
|---|---|---|
| Bad random source | Predictable, biased | Use mt19937, not rand() |
| Modulo bias | Not uniform | Use uniform_int_distribution |
| Seeding | Same sequence every run | Use random_device or chrono seed |
| Correlation | Multiple random values correlated | Use same RNG, different distributions |
| Overflow | Random * large number overflows | Use proper distribution objects |

### Randomization in System Design

Randomization is crucial in distributed systems:

| Application | Technique | Why |
|---|---|---|
| Load balancing | Random server selection | Avoid thundering herd |
| Consistent hashing | Random hash ring | Even distribution |
| Bloom filters | Random hash functions | Space-efficient membership |
| Randomized testing | Fuzzing | Find edge cases |
| A/B testing | Random assignment | Unbiased comparison |

## Summary

| Algorithm | Type | Expected Time | Key Insight |
|---|---|---|---|
| Reservoir Sampling | Monte Carlo | O(n) | Uniform sampling from stream |
| Randomized QuickSort | Las Vegas | O(n log n) | Random pivot avoids worst case |
| Treap | Las Vegas | O(log n) | Random priorities = balanced tree |
| Miller-Rabin | Monte Carlo | O(k log n) | Probabilistic primality |
| Universal Hashing | Monte Carlo | O(1) | Adversarial-proof hashing |
| Skip List | Las Vegas | O(log n) | Probabilistic balancing |
| Random restarts | Monte Carlo | Varies | Escape local optima |
| Bloom Filter | Monte Carlo | O(k) | Space-efficient membership |

### When NOT to Use Randomized Algorithms

| Situation | Why Not | Better Alternative |
|---|---|---|
| Deterministic guarantee needed | Random = no worst-case bound | Deterministic algorithm |
| Reproducibility required | Random may give different results | Fixed seed or deterministic |
| Safety-critical systems | Probabilistic errors unacceptable | Formal verification |
| Very small input | Overhead of randomness | Simple deterministic |
| Adversarial can observe randomness | May exploit patterns | Cryptographic randomness |

### Randomized Algorithm Trade-offs

| Technique | Pro | Con |
|---|---|---|
| Random pivot | Simple, avoids worst-case | Still O(n²) worst-case |
| Random priorities | Expected O(log n) | No worst-case guarantee |
| Universal hashing | Adversarial-proof | Slightly slower than simple hash |
| Reservoir sampling | O(1) space per sample | Must process entire stream |
| Monte Carlo | Bounded time | May return wrong answer |
| Las Vegas | Always correct | Unbounded time |
| Skip List | Simple, parallelizable | More space than balanced BST |
