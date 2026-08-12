# Chapter 179: Fisher-Yates Shuffle and Reservoir Sampling

## Prerequisites

- Basic probability theory (Chapter 72)
- Arrays and strings (Chapter 4)
- Randomized algorithms concepts (Chapter 63)
- Complexity analysis (Chapter 3)

## Interview Frequency: ★★★

Fisher-Yates shuffle and reservoir sampling appear frequently at **Google**, **Meta**, **Amazon**, and **Microsoft**. Fisher-Yates is the gold standard for unbiased shuffling and is often asked as a "prove it's uniform" question. Reservoir sampling is a classic **Google** interview topic for streaming data. Weighted reservoir sampling extends the concept for practical applications like load balancing and recommendation systems.

| Topic | Frequency | Typical Companies | Difficulty |
|---|---|---|---|
| Fisher-Yates Shuffle | ★★★★ | Google, Meta, Amazon | Easy-Medium |
| Reservoir Sampling (k=1) | ★★★★ | Google, Meta, Amazon | Medium |
| Reservoir Sampling (k>1) | ★★★ | Google, Microsoft | Medium |
| Weighted Reservoir Sampling | ★★ | Google, Meta, system design | Medium-Hard |
| Shuffle variants | ★★ | Amazon, Microsoft | Medium |

---

## 179.1 Fisher-Yates Shuffle

### Definition

The **Fisher-Yates shuffle** (also called the **Knuth shuffle**) generates a uniformly random permutation of a finite sequence in O(n) time. It is the only known shuffle algorithm that is provably unbiased with linear time complexity.

### Motivation

Naive shuffling approaches are deceptively broken:

- **Swap with random index**: Swapping each element with a random position produces n^n possible outcomes, but n! permutations. Since n! does not divide n^n, some permutations are more likely than others.
- **Sort by random key**: Assigning each element a random value and sorting produces bias unless the random values are distinct (and even then, the sort itself may not be stable across equal keys).

Fisher-Yates avoids both pitfalls by iterating backward and shrinking the swap window.

### Intuition

Imagine you have a deck of cards. You pick a random card from the full deck and put it in position n. Then you pick a random card from the remaining n-1 cards and put it in position n-1. Continue until only one card remains. Each card has an equal chance of landing in any position.

### Algorithm

```
FISHER-YATES-SHUFFLE(A):
    n = length(A)
    for i from n-1 down to 1:
        j = random integer in [0, i]
        swap A[i] and A[j]
```

### Step-by-Step Walkthrough

Consider array `[1, 2, 3, 4, 5]`:

| Step | i | Random j | Swap | Array State |
|---|---|---|---|---|
| 1 | 4 | 2 | A[4] ↔ A[2] | [1, 2, **5**, 4, **3**] |
| 2 | 3 | 0 | A[3] ↔ A[0] | [**4**, 2, 5, **1**, 3] |
| 3 | 2 | 2 | A[2] ↔ A[2] | [4, 2, 5, 1, 3] |
| 4 | 1 | 0 | A[1] ↔ A[0] | [**2**, **4**, 5, 1, 3] |

Result: `[2, 4, 5, 1, 3]` — a random permutation.

### Proof of Uniformity

We prove that each of the n! permutations is equally likely.

**Claim**: After the iteration with index i, elements A[0..i] are a uniformly random permutation of the original elements that could occupy those positions.

**Proof by induction**:
- **Base case** (i = n-1): We pick j uniformly from [0, n-1]. Each element has probability 1/n of being placed at position n-1. ✓
- **Inductive step**: Assume A[i+1..n-1] contains a uniformly random subset of size n-1-i, and A[0..i] contains the remaining i+1 elements in some order. We pick j uniformly from [0, i], placing A[j] at position i. Each of the i+1 elements has probability 1/(i+1) of being placed at position i. Combined with the inductive hypothesis, the joint probability of any specific arrangement is:

  1/n × 1/(n-1) × ... × 1/2 = 1/n!

Every permutation has exactly the same probability. ∎

### Implementation

#### C++

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <algorithm>
#include <cassert>

class FisherYatesShuffle {
    std::mt19937 rng;

public:
    FisherYatesShuffle(unsigned seed = std::random_device{}())
        : rng(seed) {}

    // In-place Fisher-Yates shuffle — O(n) time, O(1) extra space
    template <typename T>
    void shuffle(std::vector<T>& arr) {
        int n = (int)arr.size();
        for (int i = n - 1; i >= 1; --i) {
            std::uniform_int_distribution<int> dist(0, i);
            int j = dist(rng);
            std::swap(arr[i], arr[j]);
        }
    }

    // Return a shuffled copy (non-destructive)
    template <typename T>
    std::vector<T> shuffled(std::vector<T> arr) {
        shuffle(arr);
        return arr;
    }

    // Generate a random permutation of [0, n-1]
    std::vector<int> randomPermutation(int n) {
        std::vector<int> perm(n);
        std::iota(perm.begin(), perm.end(), 0);
        shuffle(perm);
        return perm;
    }
};

// Verification: check uniformity over many trials
void verifyUniformity() {
    const int N = 3;  // 3! = 6 permutations
    const int TRIALS = 600000;
    std::map<std::vector<int>, int> counts;

    FisherYatesShuffle shuffler;
    for (int t = 0; t < TRIALS; ++t) {
        auto perm = shuffler.randomPermutation(N);
        counts[perm]++;
    }

    // Each permutation should appear ~100000 times
    for (auto& [perm, cnt] : counts) {
        double ratio = (double)cnt / TRIALS;
        assert(ratio > 0.15 && ratio < 0.18);  // ~1/6 ± tolerance
    }
    std::cout << "Uniformity verified over " << TRIALS << " trials.\n";
}
```

#### Python

```python
import random
from typing import List, TypeVar
from collections import Counter

T = TypeVar('T')

class FisherYatesShuffle:
    """Fisher-Yates (Knuth) shuffle — unbiased O(n) permutation."""

    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)

    def shuffle(self, arr: List[T]) -> None:
        """In-place shuffle — O(n) time, O(1) extra space."""
        n = len(arr)
        for i in range(n - 1, 0, -1):
            j = self.rng.randint(0, i)
            arr[i], arr[j] = arr[j], arr[i]

    def shuffled(self, arr: List[T]) -> List[T]:
        """Return a shuffled copy."""
        result = list(arr)
        self.shuffle(result)
        return result

    def random_permutation(self, n: int) -> List[int]:
        """Generate a random permutation of [0, n-1]."""
        perm = list(range(n))
        self.shuffle(perm)
        return perm


def verify_uniformity():
    """Verify each permutation of [0,1,2] appears with equal frequency."""
    N = 3
    trials = 600_000
    shuffler = FisherYatesShuffle(seed=42)

    counts = Counter()
    for _ in range(trials):
        perm = tuple(shuffler.random_permutation(N))
        counts[perm] += 1

    for perm, cnt in counts.items():
        ratio = cnt / trials
        assert 0.15 < ratio < 0.18, f"{perm}: {ratio:.4f}"
    print(f"Uniformity verified over {trials} trials.")


if __name__ == "__main__":
    verify_uniformity()
```

#### Java

```java
import java.util.*;

public class FisherYatesShuffle {
    private final Random rng;

    public FisherYatesShuffle() {
        this.rng = new Random();
    }

    public FisherYatesShuffle(long seed) {
        this.rng = new Random(seed);
    }

    /**
     * In-place Fisher-Yates shuffle — O(n) time, O(1) extra space.
     */
    public <T> void shuffle(T[] arr) {
        int n = arr.length;
        for (int i = n - 1; i >= 1; i--) {
            int j = rng.nextInt(i + 1);  // [0, i]
            T temp = arr[i];
            arr[i] = arr[j];
            arr[j] = temp;
        }
    }

    /**
     * Generate a random permutation of [0, n-1].
     */
    public int[] randomPermutation(int n) {
        int[] perm = new int[n];
        for (int i = 0; i < n; i++) perm[i] = i;
        for (int i = n - 1; i >= 1; i--) {
            int j = rng.nextInt(i + 1);
            int temp = perm[i];
            perm[i] = perm[j];
            perm[j] = temp;
        }
        return perm;
    }

    /**
     * Verify uniformity over many trials.
     */
    public static void verifyUniformity() {
        final int N = 3;
        final int TRIALS = 600_000;
        FisherYatesShuffle shuffler = new FisherYatesShuffle(42);
        Map<List<Integer>, Integer> counts = new HashMap<>();

        for (int t = 0; t < TRIALS; t++) {
            int[] p = shuffler.randomPermutation(N);
            List<Integer> key = List.of(p[0], p[1], p[2]);
            counts.merge(key, 1, Integer::sum);
        }

        for (var entry : counts.entrySet()) {
            double ratio = (double) entry.getValue() / TRIALS;
            assert ratio > 0.15 && ratio < 0.18 : entry.getKey() + ": " + ratio;
        }
        System.out.println("Uniformity verified over " + TRIALS + " trials.");
    }

    public static void main(String[] args) {
        verifyUniformity();
    }
}
```

### Common Mistake: The Biased "Swap Anywhere" Shuffle

```cpp
// WRONG — produces biased results!
void biasedShuffle(std::vector<int>& arr) {
    int n = arr.size();
    for (int i = 0; i < n; i++) {
        int j = rand() % n;  // Should be rand() % (i+1)
        std::swap(arr[i], arr[j]);
    }
}
```

This generates n^n outcomes for n! permutations. Since n! does not divide n^n (for n > 2), some permutations must be over-represented. For n = 3, there are 27 outcomes but only 6 permutations — 27/6 = 4.5, so uniformity is impossible.

### Complexity

| Operation | Time | Space |
|---|---|---|
| Shuffle | O(n) | O(1) |
| Random permutation | O(n) | O(n) for output |
| Partial shuffle (first k) | O(k) | O(1) |

---

## 179.2 Reservoir Sampling

### Definition

**Reservoir sampling** uniformly selects k items from a stream of n items (where n is unknown or very large) in a single pass using O(k) space.

### Motivation

When data arrives as a stream:
- We cannot store all items (memory constraint or unknown size)
- We need each item to have exactly k/n probability of selection
- A single pass is required (the stream may not be replayable)

Applications: database query optimization (random row sampling), log analysis (random entry selection), A/B testing (random user selection from streaming traffic).

### Algorithm (Reservoir Sampling — k items)

```
RESERVOIR-SAMPLE(stream, k):
    reservoir = first k items from stream
    
    for i = k to n-1:
        j = random integer in [0, i]
        if j < k:
            reservoir[j] = stream[i]
    
    return reservoir
```

### Intuition

Each incoming item "fights" for a spot in the reservoir. The i-th item (0-indexed) gets a random ticket in [0, i]. If the ticket number is less than k, it replaces a random item in the reservoir. Items arriving later get smaller replacement probabilities, exactly compensating for their later arrival.

### Proof of Uniformity

**Claim**: After processing all n items, each item has exactly k/n probability of being in the reservoir.

**Proof**: Consider item i (0-indexed, i ≥ k).

- Probability item i is selected when it arrives: k/(i+1)
- Probability item i is NOT replaced by item j (j > i): 1 - k/(j+1) = (j+1-k)/(j+1)

P(item i survives to end) = k/(i+1) × ∏(j=i+1 to n-1) (j+1-k)/(j+1)

This telescopes to: k/n. ∎

For items 0 to k-1 (the initial reservoir), the same probability k/n holds by symmetry.

### Implementation

#### C++

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <chrono>

class ReservoirSampling {
    std::mt19937 rng;

public:
    ReservoirSampling()
        : rng(std::chrono::steady_clock::now().time_since_epoch().count()) {}

    /**
     * Sample k items uniformly from a stream (single pass).
     * Each item has exactly k/n probability of selection.
     */
    std::vector<int> sample(const std::vector<int>& stream, int k) {
        int n = (int)stream.size();
        if (k > n) k = n;

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

    /**
     * Sample 1 item uniformly from a stream.
     * Simplified version — O(1) space.
     */
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

    /**
     * Streaming interface: process items one at a time.
     */
    class StreamSampler {
        std::vector<int> reservoir;
        int count;
        std::mt19937& rng;

    public:
        StreamSampler(int k, std::mt19937& rng) : count(0), rng(rng) {
            reservoir.reserve(k);
        }

        void add(int item) {
            int k = (int)reservoir.size();
            if (count < k) {
                reservoir.push_back(item);
            } else {
                std::uniform_int_distribution<int> dist(0, count);
                int j = dist(rng);
                if (j < k) {
                    reservoir[j] = item;
                }
            }
            count++;
        }

        std::vector<int> getReservoir() const { return reservoir; }
        int totalSeen() const { return count; }
    };
};

// Verify uniformity
void verifyReservoirSampling() {
    const int N = 10;
    const int K = 3;
    const int TRIALS = 100000;
    std::vector<int> freq(N, 0);

    ReservoirSampling sampler;
    std::vector<int> stream(N);
    std::iota(stream.begin(), stream.end(), 0);

    for (int t = 0; t < TRIALS; t++) {
        auto result = sampler.sample(stream, K);
        for (int x : result) freq[x]++;
    }

    // Each item should appear in ~K/N = 30% of samples
    for (int i = 0; i < N; i++) {
        double ratio = (double)freq[i] / (TRIALS * K);
        std::cout << "Item " << i << ": " << ratio
                  << " (expected " << (double)K / N << ")\n";
    }
}
```

#### Python

```python
import random
from typing import List, Iterator, Optional

class ReservoirSampling:
    """Reservoir sampling: uniform k-item sample from a stream."""

    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)

    def sample(self, stream: List[int], k: int) -> List[int]:
        """Sample k items uniformly from stream in one pass — O(n) time, O(k) space."""
        n = len(stream)
        k = min(k, n)
        reservoir = list(stream[:k])

        for i in range(k, n):
            j = self.rng.randint(0, i)  # [0, i]
            if j < k:
                reservoir[j] = stream[i]

        return reservoir

    def sample_one(self, stream: List[int]) -> int:
        """Sample 1 item uniformly — O(1) space."""
        result = stream[0]
        for i in range(1, len(stream)):
            if self.rng.randint(0, i) == 0:
                result = stream[i]
        return result


class StreamReservoirSampler:
    """Streaming reservoir sampler — processes items one at a time."""

    def __init__(self, k: int, seed: int = None):
        self.k = k
        self.rng = random.Random(seed)
        self.reservoir: List[int] = []
        self.count = 0

    def add(self, item: int) -> None:
        if self.count < self.k:
            self.reservoir.append(item)
        else:
            j = self.rng.randint(0, self.count)
            if j < self.k:
                self.reservoir[j] = item
        self.count += 1

    def get(self) -> List[int]:
        return list(self.reservoir)

    @property
    def total_seen(self) -> int:
        return self.count


def verify():
    """Verify each item appears with probability k/n."""
    N, K, TRIALS = 10, 3, 100_000
    freq = [0] * N
    stream = list(range(N))
    sampler = ReservoirSampling(seed=42)

    for _ in range(TRIALS):
        for x in sampler.sample(stream, K):
            freq[x] += 1

    expected = K / N
    for i, f in enumerate(freq):
        ratio = f / (TRIALS * K)
        print(f"Item {i}: {ratio:.4f} (expected {expected:.4f})")


if __name__ == "__main__":
    verify()
```

#### Java

```java
import java.util.*;

public class ReservoirSampling {
    private final Random rng;

    public ReservoirSampling() {
        this.rng = new Random();
    }

    public ReservoirSampling(long seed) {
        this.rng = new Random(seed);
    }

    /**
     * Sample k items uniformly from a stream — O(n) time, O(k) space.
     */
    public int[] sample(int[] stream, int k) {
        int n = stream.length;
        k = Math.min(k, n);
        int[] reservoir = new int[k];

        for (int i = 0; i < k; i++) reservoir[i] = stream[i];

        for (int i = k; i < n; i++) {
            int j = rng.nextInt(i + 1);  // [0, i]
            if (j < k) {
                reservoir[j] = stream[i];
            }
        }
        return reservoir;
    }

    /**
     * Sample 1 item uniformly — O(1) space.
     */
    public int sampleOne(int[] stream) {
        int result = stream[0];
        for (int i = 1; i < stream.length; i++) {
            if (rng.nextInt(i + 1) == 0) {
                result = stream[i];
            }
        }
        return result;
    }

    /**
     * Streaming interface.
     */
    public static class StreamSampler {
        private final int k;
        private final List<Integer> reservoir;
        private final Random rng;
        private int count;

        public StreamSampler(int k, Random rng) {
            this.k = k;
            this.rng = rng;
            this.reservoir = new ArrayList<>(k);
            this.count = 0;
        }

        public void add(int item) {
            if (count < k) {
                reservoir.add(item);
            } else {
                int j = rng.nextInt(count + 1);
                if (j < k) {
                    reservoir.set(j, item);
                }
            }
            count++;
        }

        public List<Integer> getReservoir() {
            return Collections.unmodifiableList(reservoir);
        }

        public int totalSeen() { return count; }
    }

    public static void main(String[] args) {
        ReservoirSampling sampler = new ReservoirSampling(42);
        int[] stream = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9};
        int[] result = sampler.sample(stream, 3);
        System.out.println("Sample: " + Arrays.toString(result));
    }
}
```

### Complexity

| Variant | Time | Space |
|---|---|---|
| Sample k from n | O(n) | O(k) |
| Sample 1 from n | O(n) | O(1) |
| Streaming (per item) | O(1) amortized | O(k) |

---

## 179.3 Weighted Reservoir Sampling

### Definition

**Weighted reservoir sampling** (also called **A-Res** — Acceptance-Reservoir) selects items with probability proportional to their weight, using a single pass and O(k) space.

### Motivation

Standard reservoir sampling assumes all items are equally important. In practice, items have weights:
- Web pages have importance scores
- Users have activity levels
- Network packets have priority levels

We need to sample k items where P(item i is selected) ∝ weight(i).

### Algorithm (A-Res — k items)

```
WEIGHTED-RESERVOIR-SAMPLE(stream with weights, k):
    // Maintain reservoir with items sorted by key
    // Key = random^(1/weight) — smaller key = higher priority
    
    for each (item, weight) in stream:
        key = uniform_random() ^ (1 / weight)
        
        if reservoir.size < k:
            insert (item, key) into reservoir
        else if key > reservoir.min_key:
            remove item with min_key from reservoir
            insert (item, key) into reservoir
    
    return reservoir items
```

The key insight: for item with weight w, the key `U^(1/w)` where U ~ Uniform(0,1) has the property that larger weights produce smaller keys (more likely to be selected).

### Proof Sketch

For item i with weight w_i, P(key_i < key_j) = P(U_i^(1/w_i) < U_j^(1/w_j)).

Setting X = -ln(U)/w gives an exponential distribution with rate w_i. The minimum of exponential random variables is itself exponential with rate equal to the sum. This yields the correct weighted probabilities.

### Implementation

#### C++

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <cmath>
#include <queue>
#include <cassert>

struct WeightedItem {
    int id;
    double weight;
    double key;
};

struct CompareKey {
    bool operator()(const WeightedItem& a, const WeightedItem& b) const {
        return a.key > b.key;  // min-heap by key
    }
};

class WeightedReservoirSampling {
    std::mt19937 rng;
    std::uniform_real_distribution<double> uniform;

public:
    WeightedReservoirSampling()
        : rng(std::random_device{}()), uniform(0.0, 1.0) {}

    /**
     * Sample k items with probability ∝ weight.
     * Uses A-Res algorithm — O(n log k) time, O(k) space.
     */
    std::vector<int> sample(
        const std::vector<std::pair<int, double>>& stream, int k
    ) {
        // Min-heap of (key, item_id) — keeps top-k by key
        std::priority_queue<WeightedItem, std::vector<WeightedItem>,
                            CompareKey> heap;

        for (const auto& [id, weight] : stream) {
            // Key = U^(1/w) — higher weight → smaller key → more likely kept
            double u = uniform(rng);
            double key = std::pow(u, 1.0 / weight);

            if ((int)heap.size() < k) {
                heap.push({id, weight, key});
            } else if (key > heap.top().key) {
                heap.pop();
                heap.push({id, weight, key});
            }
        }

        std::vector<int> result;
        while (!heap.empty()) {
            result.push_back(heap.top().id);
            heap.pop();
        }
        return result;
    }
};
```

#### Python

```python
import random
import heapq
from typing import List, Tuple

class WeightedReservoirSampling:
    """A-Res: weighted reservoir sampling in a single pass."""

    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)

    def sample(
        self, stream: List[Tuple[int, float]], k: int
    ) -> List[int]:
        """
        Sample k items with probability ∝ weight.
        stream: list of (item_id, weight)
        Returns k item ids.
        O(n log k) time, O(k) space.
        """
        # Min-heap of (key, item_id)
        heap: List[Tuple[float, int]] = []

        for item_id, weight in stream:
            u = self.rng.random()
            key = u ** (1.0 / weight)  # higher weight → smaller key

            if len(heap) < k:
                heapq.heappush(heap, (key, item_id))
            elif key > heap[0][0]:
                heapq.heapreplace(heap, (key, item_id))

        return [item_id for _, item_id in heap]


def verify():
    """Verify weighted sampling matches expected probabilities."""
    stream = [(0, 1.0), (1, 2.0), (2, 3.0), (3, 4.0)]
    total_weight = sum(w for _, w in stream)  # 10.0
    k = 1
    trials = 100_000

    freq = [0] * 4
    sampler = WeightedReservoirSampling(seed=42)
    for _ in range(trials):
        for item_id in sampler.sample(stream, k):
            freq[item_id] += 1

    for i, (_, w) in enumerate(stream):
        observed = freq[i] / trials
        expected = w / total_weight
        print(f"Item {i} (w={w}): {observed:.4f} (expected {expected:.4f})")


if __name__ == "__main__":
    verify()
```

#### Java

```java
import java.util.*;

public class WeightedReservoirSampling {
    private final Random rng;

    public WeightedReservoirSampling() {
        this.rng = new Random();
    }

    public WeightedReservoirSampling(long seed) {
        this.rng = new Random(seed);
    }

    /**
     * Sample k items with probability proportional to weight.
     * O(n log k) time, O(k) space.
     */
    public List<Integer> sample(List<int[]> stream, int k) {
        // stream: each element is [id, weight]
        // Max-heap by key (use negative for min-heap behavior in Java PQ)
        PriorityQueue<double[]> heap = new PriorityQueue<>(
            (a, b) -> Double.compare(b[0], a[0])  // max-heap by key
        );

        for (int[] entry : stream) {
            int id = entry[0];
            double weight = entry[1];
            double u = rng.nextDouble();
            double key = Math.pow(u, 1.0 / weight);

            if (heap.size() < k) {
                heap.offer(new double[]{key, id});
            } else if (key < heap.peek()[0]) {
                heap.poll();
                heap.offer(new double[]{key, id});
            }
        }

        List<Integer> result = new ArrayList<>();
        for (double[] entry : heap) {
            result.add((int) entry[1]);
        }
        return result;
    }

    public static void main(String[] args) {
        WeightedReservoirSampling sampler = new WeightedReservoirSampling(42);
        List<int[]> stream = List.of(
            new int[]{0, 1}, new int[]{1, 2},
            new int[]{2, 3}, new int[]{3, 4}
        );
        System.out.println("Sample: " + sampler.sample(stream, 2));
    }
}
```

### Complexity

| Variant | Time | Space |
|---|---|---|
| A-Res (k items) | O(n log k) | O(k) |
| A-ExpJ (optimized) | O(n + k log k) | O(k) |

---

## 179.4 Applications and Variants

### Real-World Applications

| Application | Algorithm | Why |
|---|---|---|
| SQL `ORDER BY RANDOM() LIMIT k` | Reservoir sampling | Stream rows without full sort |
| Log analysis (random entries) | Reservoir sampling | Cannot load all logs |
| A/B testing (random users) | Weighted reservoir | Users have different weights |
| Load balancing (random server) | Fisher-Yates on server list | Unbiased server selection |
| Shuffling card games | Fisher-Yates | Provably fair |
| Monte Carlo simulation | Both | Random sampling from distributions |

### Knuth's Algorithm S (Selection Sampling)

A variant that generates a random subset of k indices from [0, n-1] without storing the stream:

```
SELECT(n, k):
    // Generate k random indices in sorted order
    t = 0, m = 0
    while m < k:
        if uniform_random() < (k - m) / (n - t):
            output t
            m++
        t++
```

### Distributed Reservoir Sampling

For distributed systems (MapReduce, Spark):
1. Each mapper maintains a local reservoir of size k
2. The reducer merges reservoirs using weighted reservoir sampling
3. Each local reservoir's "weight" is the number of items it processed

---

## 179.5 Dry Run: Complete Example

### Fisher-Yates Shuffle

```
Input: [A, B, C, D]
RNG sequence: j=1, j=0, j=2

Step 1: i=3, j=1 → swap A[3]=D with A[1]=B → [A, D, C, B]
Step 2: i=2, j=0 → swap A[2]=C with A[0]=A → [C, D, A, B]
Step 3: i=1, j=2 → j > i? No, j=2 > i=1 → INVALID (this can't happen with correct [0,i])

Let me redo with valid random values:

RNG sequence: j=1, j=0, j=0

Step 1: i=3, j=1 → swap A[3]=D with A[1]=B → [A, D, C, B]
Step 2: i=2, j=0 → swap A[2]=C with A[0]=A → [C, D, A, B]
Step 3: i=1, j=0 → swap A[1]=D with A[0]=C → [D, C, A, B]

Output: [D, C, A, B]
```

### Reservoir Sampling (k=2, stream=[10,20,30,40,50])

```
Initial reservoir: [10, 20]

i=2: j = random in [0,2] = 1 → j < 2 → reservoir[1] = 30 → [10, 30]
i=3: j = random in [0,3] = 3 → j ≥ 2 → skip
i=4: j = random in [0,4] = 0 → j < 2 → reservoir[0] = 50 → [50, 30]

Final reservoir: [50, 30]
Each item had 2/5 = 40% chance of being selected. ✓
```

---

## 179.6 Interview Questions

### Classic Problems

1. **Shuffle an Array (LeetCode 384)**: Implement the Fisher-Yates shuffle and its inverse (reset).

2. **Linked List Random Node (LeetCode 382)**: Return a random node from a singly linked list using reservoir sampling (k=1).

3. **Random Pick Index (LeetCode 398)**: Given an array with duplicates, pick a random index of a target value. Use reservoir sampling when there are multiple occurrences.

4. **Random Pick with Weight (LeetCode 528)**: Pick an index with probability proportional to weight. Binary search on prefix sums, or weighted reservoir sampling.

### Follow-Up Questions

- **"Prove Fisher-Yates is uniform"**: Use the telescoping product argument (Section 179.1).
- **"What if the stream is too large for memory?"**: Use reservoir sampling with O(k) space.
- **"How do you shuffle a linked list?"**: Fisher-Yates with random access → O(n²) or copy to array first.
- **"How to sample from a stream with weights?"**: A-Res algorithm with key = U^(1/w).
- **"Can you do reservoir sampling in parallel?"**: Yes — each worker maintains a local reservoir, merge with weighted sampling.

---

## 179.7 Exercises

1. **Implement a card shuffler**: Create a class that shuffles a standard 52-card deck using Fisher-Yates. Verify uniformity by running 10,000 shuffles and checking that each card appears in each position roughly 10000/52 ≈ 192 times.

2. **Streaming median with reservoir**: Use reservoir sampling (k=1) to maintain a random element from a stream. After each new element, report whether the random element is above or below the running median.

3. **Weighted random pick**: Implement a class that supports `add(item, weight)` and `pick()` where pick returns an item with probability proportional to its weight. Use prefix sums + binary search.

4. **Partial shuffle**: Implement `partialShuffle(arr, k)` that returns the first k elements of a random permutation without shuffling the entire array. What is the time complexity?

5. **Parallel reservoir sampling**: Design an algorithm where 4 workers each process 1/4 of a stream, then merge their reservoirs into a final k-item sample. Prove the result is equivalent to single-pass reservoir sampling.

---

## 179.8 Cross-References

- **Chapter 4 (Arrays and Strings)**: Fundamental data structure used by both algorithms.
- **Chapter 63 (Randomized Algorithms)**: Broader context for randomized techniques.
- **Chapter 72 (Probability and Expected Value)**: Mathematical foundations for correctness proofs.
- **Chapter 79 (Probabilistic Data Structures)**: Related streaming and sampling techniques.
- **Chapter 147 (Streaming Algorithms)**: Single-pass algorithms for massive data.
- **Chapter 150 (Advanced Randomized Algorithms)**: Deeper treatment of randomization.
