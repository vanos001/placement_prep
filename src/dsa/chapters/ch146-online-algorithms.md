# Chapter 146: Online Algorithms

## Prerequisites
- Greedy algorithms
- Competitive analysis basics
- Adversarial arguments

## Interview Frequency: ★★
## Google, Amazon, Meta — systems design and algorithmic reasoning

---

## 146.1 What Are Online Algorithms?

An **online algorithm** processes input **piece by piece** (one request at a time)
without knowledge of future requests. In contrast, an **offline algorithm** has
access to the entire input upfront.

**Real-World Analogy:** Imagine you're a taxi driver. An offline algorithm knows all
rides in advance and optimizes routes globally. An online algorithm must decide
immediately when a ride request arrives, without knowing what comes next.

### Online vs. Offline

| Aspect | Online | Offline |
|---|---|---|
| Input | Arrives sequentially | Known in advance |
| Decisions | Made immediately | Can be deferred |
| Optimality | Approximate | Optimal |
| Analysis | Competitive ratio | Standard complexity |

### Why Study Online Algorithms?

Many real systems are inherently online:
- **Caching:** Pages arrive one at a time; evict now or keep?
- **Scheduling:** Jobs arrive over time; allocate resources immediately?
- **Stock trading:** Prices stream in; buy/sell now?
- **Load balancing:** Requests arrive; route to which server?

---

## 146.2 Competitive Analysis

Since online algorithms can't be optimal (they lack future info), we measure them by
**competitive ratio**.

**Definition:** An online algorithm ALG has competitive ratio `c` if, for every
possible request sequence σ:

```
ALG(σ) ≤ c · OPT(σ) + α
```

where OPT is the optimal offline cost and α is a constant independent of σ.

- **c = 1:** ALG is optimal (rare for online problems)
- **c = 2:** ALG costs at most twice the optimal
- **c = k:** ALG costs at most k times the optimal

### Deterministic vs. Randomized

- **Deterministic competitive ratio:** Worst case over all request sequences
- **Randomized competitive ratio:** Expected cost (over algorithm's random choices)
  compared to worst-case adversary

Randomized algorithms often achieve better ratios because the adversary can't predict
random choices.

---

## 146.3 The Ski Rental Problem

**Problem:** You go skiing every day. You can **rent** skis for $1/day or **buy** them
for $B (one-time cost). You don't know how many days you'll ski. Minimize total cost.

### Optimal Offline

If you know you'll ski `d` days:
- Rent if d ≤ B: cost = d
- Buy if d > B: cost = B
- OPT = min(d, B)

### Online Strategy

**Rent for B days, then buy.** If skiing stops before day B, you saved money by not
buying. If it continues past day B, buying was the right call.

**Cost analysis:**
- If d ≤ B: ALG = d, OPT = d → ratio = 1
- If d > B: ALG = B + B = 2B, OPT = B → ratio = 2

**Competitive ratio = 2** (this is optimal for deterministic algorithms).

### Proof of Optimality (Lower Bound)

No deterministic algorithm can achieve ratio < 2.

**Adversary argument:** Suppose ALG buys on day `t`. The adversary stops skiing on day
`t-1`, making ALG waste the purchase. If ALG never buys, the adversary makes skiing
last forever, forcing infinite rental cost.

The adversary can always force ratio ≥ 2 against any deterministic strategy.

### C++ Implementation

```cpp
#include <iostream>
#include <algorithm>

class SkiRental {
    int buyCost;
    int rentedDays;
    bool bought;

public:
    SkiRental(int B) : buyCost(B), rentedDays(0), bought(false) {}

    // Returns cost for this day
    int nextDay() {
        if (bought) return 0;  // Already bought, free to ski

        rentedDays++;
        if (rentedDays >= buyCost) {
            bought = true;
            return buyCost;  // Buy cost
        }
        return 1;  // Rent cost
    }

    int totalCost() const {
        return bought ? buyCost + buyCost : rentedDays;
    }
};

int main() {
    int B = 10;

    // Scenario 1: Ski for 7 days (stop before buying)
    SkiRental sr1(B);
    int cost1 = 0;
    for (int d = 0; d < 7; d++) cost1 += sr1.nextDay();
    std::cout << "7 days: cost=$" << cost1 << " (optimal=$7)\n";

    // Scenario 2: Ski for 15 days (buy on day 10)
    SkiRental sr2(B);
    int cost2 = 0;
    for (int d = 0; d < 15; d++) cost2 += sr2.nextDay();
    std::cout << "15 days: cost=$" << cost2 << " (optimal=$10)\n";

    // Scenario 3: Ski for 20 days
    SkiRental sr3(B);
    int cost3 = 0;
    for (int d = 0; d < 20; d++) cost3 += sr3.nextDay();
    std::cout << "20 days: cost=$" << cost3 << " (optimal=$10)\n";

    return 0;
}
```

### Python Implementation

```python
class SkiRental:
    def __init__(self, buy_cost: int):
        self.buy_cost = buy_cost
        self.rented_days = 0
        self.bought = False

    def next_day(self) -> int:
        if self.bought:
            return 0
        self.rented_days += 1
        if self.rented_days >= self.buy_cost:
            self.bought = True
            return self.buy_cost  # Buy cost
        return 1  # Rent cost


def optimal_cost(buy_cost: int, days: int) -> int:
    return min(days, buy_cost)


# Demonstration
B = 10
for days in [5, 10, 15, 20, 30]:
    sr = SkiRental(B)
    alg_cost = sum(sr.next_day() for _ in range(days))
    opt = optimal_cost(B, days)
    print(f"Days={days}: ALG=${alg_cost} OPT=${opt} ratio={alg_cost/opt:.2f}")
```

### Java Implementation

```java
public class SkiRental {
    private int buyCost;
    private int rentedDays;
    private boolean bought;

    public SkiRental(int B) {
        this.buyCost = B;
        this.rentedDays = 0;
        this.bought = false;
    }

    public int nextDay() {
        if (bought) return 0;
        rentedDays++;
        if (rentedDays >= buyCost) {
            bought = true;
            return buyCost;
        }
        return 1;
    }

    public static void main(String[] args) {
        int B = 10;
        for (int d : new int[]{5, 10, 15, 20, 30}) {
            SkiRental sr = new SkiRental(B);
            int cost = 0;
            for (int i = 0; i < d; i++) cost += sr.nextDay();
            int opt = Math.min(d, B);
            System.out.printf("Days=%d: ALG=$%d OPT=$%d ratio=%.2f%n",
                              d, cost, opt, (double) cost / opt);
        }
    }
}
```

---

## 146.4 Paging (Caching) Problem

**Problem:** You have a cache that holds `k` pages. A sequence of page requests
arrives. On a cache miss, you must evict a page and load the requested one.
Minimize total misses.

### Algorithms

| Algorithm | Strategy | Competitive Ratio |
|---|---|---|
| **LRU** (Least Recently Used) | Evict page not used longest | k |
| **FIFO** (First In First Out) | Evict oldest page in cache | k |
| **LFU** (Least Frequently Used) | Evict least frequent page | Not bounded |
| **Random** | Evict random page | k (expected) |
| **FAR/OPT** (Offline) | Evict page used farthest in future | 1 (optimal) |

### Why k is Optimal for Deterministic Algorithms

**Adversary argument for LRU/FIFO (ratio = k):**

Consider k+1 distinct pages. The adversary repeatedly requests the one page NOT in
the algorithm's cache (but is in OPT's cache). Every request causes a miss for ALG
but no miss for OPT.

After k+1 requests: ALG has k misses, OPT has 1 miss → ratio = k.

No deterministic algorithm can do better than k.

### Implementation: LRU Cache

```cpp
#include <iostream>
#include <unordered_map>
#include <list>

class LRUCache {
    int capacity;
    std::list<int> order;  // front = most recent
    std::unordered_map<int, std::list<int>::iterator> cache;
    int misses = 0;

public:
    LRUCache(int k) : capacity(k) {}

    void access(int page) {
        auto it = cache.find(page);
        if (it != cache.end()) {
            // Hit: move to front
            order.erase(it->second);
            order.push_front(page);
            it->second = order.begin();
        } else {
            // Miss
            misses++;
            if ((int)cache.size() >= capacity) {
                // Evict LRU (back of list)
                int lru = order.back();
                cache.erase(lru);
                order.pop_back();
            }
            order.push_front(page);
            cache[page] = order.begin();
        }
    }

    int getMisses() const { return misses; }
};

int main() {
    LRUCache lru(3);

    // Request sequence: 1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5
    std::vector<int> requests = {1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5};
    for (int page : requests) {
        lru.access(page);
    }

    std::cout << "LRU misses (cache size 3): " << lru.getMisses() << "\n";
    // Optimal (FAR) would have 7 misses; LRU has 10

    return 0;
}
```

### Randomized Marking Algorithm (O(log k) ratio)

The **marking algorithm** achieves O(log k) competitive ratio:
1. Maintain a "marked" bit for each cached page
2. On a request to page p:
   - If p is in cache, mark it
   - If p is not in cache:
     - If all pages are marked, unmark everything
     - Pick a random unmarked page, evict it, load p, mark p

**Analysis sketch:** Each "phase" (from unmark-all to next unmark-all) has at most
k distinct pages. The probability of evicting a page that OPT needs is bounded,
leading to O(log k) expected misses per phase.

---

## 146.5 Online Bipartite Matching

**Problem:** Vertices on one side (advertisers) are known. Vertices on the other side
(query slots) arrive one at a time. When a slot arrives, you must immediately match it
to an available advertiser (or leave it unmatched). Maximize total matches.

### Greedy Algorithm

**Strategy:** Match each arriving vertex to any available neighbor.

**Competitive ratio: 1/2**

**Proof:** Every edge in GREEDY's matching blocks at most 2 edges in OPT's matching
(one from each endpoint). So |GREEDY| ≥ |OPT|/2.

### Karp-Vazirani-Vazirani (KVV) Algorithm

**Strategy:** Use random permutation of advertisers. Match each arriving vertex to the
first available advertiser in the permutation.

**Competitive ratio: 1 - 1/e ≈ 0.632**

This is optimal for randomized algorithms against oblivious adversaries.

### Implementation: Greedy Matching

```cpp
#include <iostream>
#include <vector>
#include <set>

class OnlineMatching {
    int n;  // Number of advertisers (left side)
    std::vector<std::vector<int>> adj;  // adj[slot] = list of compatible advertisers
    std::set<int> available;
    std::vector<int> match;  // match[advertiser] = slot, -1 if unmatched

public:
    OnlineMatching(int n) : n(n), adj(n), match(n, -1) {
        for (int i = 0; i < n; i++) available.insert(i);
    }

    // Add possible advertisers for a slot
    void addEdges(int slot, const std::vector<int>& advertisers) {
        if (slot < (int)adj.size()) {
            adj[slot] = advertisers;
        }
    }

    // Process arriving slot; returns matched advertiser or -1
    int processSlot(int slot) {
        for (int advertiser : adj[slot]) {
            if (available.count(advertiser)) {
                available.erase(advertiser);
                match[advertiser] = slot;
                return advertiser;
            }
        }
        return -1;  // Unmatched
    }

    int matchCount() const {
        int count = 0;
        for (int m : match) if (m != -1) count++;
        return count;
    }
};

int main() {
    // 4 advertisers, 4 slots
    OnlineMatching om(4);
    // Slot 0: can match to advertisers 0, 1
    om.addEdges(0, {0, 1});
    // Slot 1: can match to advertisers 1, 2
    om.addEdges(1, {1, 2});
    // Slot 2: can match to advertisers 0, 2, 3
    om.addEdges(2, {0, 2, 3});
    // Slot 3: can match to advertiser 3
    om.addEdges(3, {3});

    for (int slot = 0; slot < 4; slot++) {
        int adv = om.processSlot(slot);
        std::cout << "Slot " << slot << " matched to advertiser " << adv << "\n";
    }
    std::cout << "Total matches: " << om.matchCount() << "\n";

    return 0;
}
```

---

## 146.6 The k-Server Problem

**Problem:** There are `k` servers positioned in a metric space. Requests arrive at
points in the space. You must move a server to each request point. Minimize total
distance traveled.

**Known Results:**
- k = 2: Work Function Algorithm achieves ratio 2k-1 = 3
- General k: Conjectured optimal ratio = 2k-1
- Best known: O(k · log k · log n) for n-point metric spaces

**Special Cases:**
- Line metric: k-competitive
- Tree metric: k-competitive
- General metric: 2k-1 competitive (conjectured optimal)

### Work Function Algorithm (WFA)

For each request point p:
1. Compute the work function W(S, p) = min cost to serve all requests so far and
   have a server at p (with server set S)
2. Move the server that minimizes the total cost, considering both current move cost
   and future work function values

WFA is optimal for k=2 but expensive to compute for large k.

---

## 146.7 Adversarial Arguments

The key technique for proving lower bounds on competitive ratios.

### Template

1. **Assume** ALG has competitive ratio c
2. **Construct** a request sequence adversarially:
   - Observe ALG's decisions
   - Choose next requests to maximize ALG's cost
   - Show OPT can handle the same sequence cheaply
3. **Derive** a contradiction if c is too small

### Example: Paging Lower Bound (k)

**Adversary strategy:**
1. Maintain a set of k+1 "active" pages
2. Request the page that ALG evicted most recently (but OPT still has)
3. ALG must load it (miss), OPT already has it (hit)

After k+1 requests to k+1 distinct pages:
- ALG: k misses (loaded all k+1, evicted k)
- OPT: at most 1 miss (can keep k pages, load 1)
- Ratio ≥ k

---

## 146.8 Complexity Summary

| Problem | Best Deterministic | Best Randomized | Offline Optimal |
|---|---|---|---|
| Ski Rental | 2 | e/(e-1) ≈ 1.58 | 1 |
| Paging | k | O(log k) | 1 |
| Bipartite Matching | 0.5 | 1-1/e ≈ 0.632 | 1 |
| k-Server | 2k-1 (conjectured) | O(log k) | 1 |
| List Update | 1.5 (for MTF) | 1.5 | 1 |

---

## 146.9 Practice Problems

1. **Ski Rental:** Implement and verify competitive ratio
2. **LRU vs. FIFO vs. OPT:** Compare on given access sequences
3. **Online Bipartite Matching:** Implement KVV algorithm
4. **Online Scheduling:** Minimize makespan on identical machines
5. **Secretary Problem:** Optimal stopping with competitive analysis

---

## 146.10 Interview Questions

1. **Q:** What is a competitive ratio?
   **A:** The worst-case ratio of the online algorithm's cost to the optimal offline
   cost, over all possible request sequences. A competitive ratio of c means the
   algorithm never costs more than c times the optimum.

2. **Q:** Why can't online algorithms be optimal?
   **A:** Because they lack future information. An adversary can always construct
   sequences that exploit the algorithm's decisions. The competitive ratio quantifies
   how much this information gap costs.

3. **Q:** What's the difference between deterministic and randomized competitive
   ratios?
   **A:** Deterministic ratio is worst-case over all sequences. Randomized ratio
   considers the algorithm's expected cost (averaged over its random choices) vs. the
   worst-case adversary. Randomization often helps because the adversary can't predict
   random choices.

4. **Q:** When would you use an online algorithm in practice?
   **A:** When input arrives in real-time and decisions must be immediate (caching,
   load balancing, scheduling, trading). Also when future input is genuinely unknown.

---

## 146.11 Theoretical Deep Dive: Yao's Minimax Principle

**Yao's Minimax Principle** relates deterministic and randomized competitive ratios:

> The expected cost of the best deterministic algorithm against a distribution of
> inputs equals the expected cost of the best randomized algorithm against the worst
> input.

**Application:** To prove a lower bound on randomized algorithms:
1. Choose a distribution over request sequences
2. Show every deterministic algorithm has high expected cost on this distribution
3. This implies no randomized algorithm can do better

**Example (Ski Rental):**
- Distribution: ski for exactly B days with prob 0.5, ski forever with prob 0.5
- Buy on day t: expected cost = 0.5·t + 0.5·B = 0.5(t+B) ≥ B (minimum at t=B)
- Optimal: 0.5·B + 0.5·B = B
- Ratio ≥ B·e/(e-1) / B = e/(e-1) for the best randomized strategy

---

## 146.12 Related Topics

| Topic | Chapter | Connection |
|---|---|---|
| Greedy Algorithms | Ch. 08 | Online algorithms are often greedy |
| Competitive Analysis | This chapter | Core analysis framework |
| Streaming Algorithms | Ch. 145 | Similar one-pass constraints |
| Adversarial Arguments | Ch. 147 | Proving lower bounds |
| Randomized Algorithms | Ch. 144 | Randomization helps online |

---

## Summary

| Concept | Key Idea |
|---|---|
| Online Algorithm | Processes input sequentially, no future knowledge |
| Competitive Ratio | Worst-case ALG cost / OPT cost |
| Ski Rental | Rent B days then buy → ratio 2 |
| Paging (LRU/FIFO) | Evict least-recently-used → ratio k |
| Bipartite Matching | Greedy → ratio 1/2; KVV → ratio 1-1/e |
| k-Server | Conjectured ratio 2k-1 |
| Randomization | Often improves ratio by hiding decisions from adversary |

**Key Takeaway:** Online algorithms trade optimality for responsiveness. The
competitive ratio measures how much this trade-off costs in the worst case.
Randomization and clever algorithm design can minimize this cost.
