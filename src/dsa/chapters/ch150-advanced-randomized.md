# Chapter 150: Advanced Randomized Algorithms

## Prerequisites
- Probability basics, graph algorithms, hashing

## Interview Frequency: ★★

Advanced probabilistic techniques go beyond basic randomization. **Google**, **Amazon**, and **Microsoft** occasionally test these for senior/research roles. Karger's min-cut appears in PhD-level interviews.

---

## 150.1 Karger's Min Cut Algorithm

### Definition

The **minimum cut** of a graph is the smallest set of edges whose removal disconnects the graph. Karger's algorithm finds this using random edge contraction.

### Motivation

Deterministic min-cut algorithms (Stoer-Wagner) run in O(n³) or O(nm log n). Karger's is conceptually simpler and runs in O(n²m) with high probability.

### Intuition

Repeatedly pick a random edge and merge its endpoints. The min cut edges survive contraction with probability ≥ 1/C(n,2), so repeating enough times finds the answer.

### Formal Explanation

**Contraction**: Pick edge (u,v) uniformly at random. Merge u and v into a single vertex. Remove self-loops. Repeat until 2 vertices remain. The remaining edges form a cut.

**Probability analysis**: For a graph with n vertices and min cut value k:
- Each vertex has degree ≥ k (since removing all edges of any vertex is a cut)
- Total edges ≥ nk/2
- Probability of picking a min-cut edge ≤ k / (nk/2) = 2/n
- After n-2 contractions, probability min cut survives ≥ 1/C(n,2) ≥ 2/n²

**Repetition**: Run O(n² log n) times. Failure probability: (1 - 2/n²)^{n² log n} ≈ 1/n².

### Step-by-Step Walkthrough

```
Graph: 0-1, 0-2, 1-2, 1-3, 2-3
Min cut = 2 (edges {1-3, 2-3} or {0-1, 0-2})

Contraction 1:
  Random edge: (1,2)
  Merge 1 and 2 → vertex "1"
  New adj: 0-1, 0-1, 1-3, 1-3
  Remove self-loops: 0-1, 0-1, 1-3, 1-3

Contraction 2:
  Random edge: (0,1)
  Merge 0 and 1 → vertex "0"
  New adj: 0-3, 0-3
  Remove self-loops: 0-3, 0-3

Result: 2 edges between {0,1,2} and {3} → cut size = 2
```

### Code

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <algorithm>
#include <climits>

struct Edge {
    int u, v;
};

int kargerMinCut(int n, std::vector<Edge> edges, std::mt19937& rng) {
    std::vector<int> component(n);
    std::iota(component.begin(), component.end(), 0);
    int remaining = n;

    while (remaining > 2) {
        // Pick random edge
        std::uniform_int_distribution<int> dist(0, (int)edges.size() - 1);
        int idx = dist(rng);
        int u = component[edges[idx].u];
        int v = component[edges[idx].v];

        if (u == v) continue;  // Self-loop, skip

        // Merge v into u
        for (int& c : component)
            if (c == v) c = u;

        // Remove self-loops
        edges.erase(std::remove_if(edges.begin(), edges.end(),
            [&](const Edge& e) {
                return component[e.u] == component[e.v];
            }), edges.end());

        remaining--;
    }

    // Count edges between the two components
    int cutSize = 0;
    int comp1 = component[0];
    for (auto& e : edges) {
        if (component[e.u] == comp1 && component[e.v] != comp1)
            cutSize++;
    }
    return cutSize;
}

int main() {
    // Example: 4 vertices, min cut = 2
    std::vector<Edge> edges = {{0,1}, {0,2}, {1,2}, {1,3}, {2,3}};
    int n = 4;
    std::mt19937 rng(42);

    int minCut = INT_MAX;
    int trials = n * n * 10;  // O(n² log n) for high probability
    for (int i = 0; i < trials; i++) {
        minCut = std::min(minCut, kargerMinCut(n, edges, rng));
    }

    std::cout << "Min cut: " << minCut << "\n";  // 2
    return 0;
}
```

### Complexity

| Aspect | Value |
|---|---|
| Single run | O(n²) or O(m) with union-find |
| Repetitions | O(n² log n) |
| Total | O(n⁴ log n) or O(n²m log n) |
| Success probability | ≥ 1 - 1/n |

---

## 150.2 Chernoff Bounds

### Definition

Chernoff bounds give **exponentially decreasing tail probabilities** for sums of independent random variables.

### Motivation

When analyzing randomized algorithms, we often need to bound how far a sum of random variables deviates from its expectation. Markov's inequality gives weak bounds; Chernoff gives tight exponential bounds.

### Formal Statement

Let X₁, ..., Xₙ be independent random variables, S = ΣXᵢ, μ = E[S].

**Upper tail**: Pr[S > (1+δ)μ] < (e^δ / (1+δ)^(1+δ))^μ for δ > 0

**Simplified**: Pr[S > (1+δ)μ] < exp(-μδ²/3) for 0 < δ < 1

**Lower tail**: Pr[S < (1-δ)μ] < exp(-μδ²/2) for 0 < δ < 1

### Application: Load Balancing

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <cmath>

// Simulate: n balls into n bins, what's the max load?
// Chernoff bound: max load is O(log n / log log n) w.h.p.
int simulateMaxLoad(int n, int trials, std::mt19937& rng) {
    int maxLoad = 0;
    std::uniform_int_distribution<int> dist(0, n - 1);

    for (int t = 0; t < trials; t++) {
        std::vector<int> bins(n, 0);
        for (int i = 0; i < n; i++)
            bins[dist(rng)]++;

        int thisMax = *std::max_element(bins.begin(), bins.end());
        maxLoad = std::max(maxLoad, thisMax);
    }
    return maxLoad;
}

int main() {
    std::mt19937 rng(42);
    for (int n : {100, 1000, 10000}) {
        int maxLoad = simulateMaxLoad(n, 100, rng);
        double expected_log = std::log(n) / std::log(std::log(n));
        std::cout << "n=" << n << ": max load=" << maxLoad
                  << ", log n / log log n ≈ " << expected_log << "\n";
    }
    return 0;
}
```

### Application: Randomized Quickselect Analysis

```cpp
// Chernoff bound proves: with high probability, each pivot
// falls in the middle 50% of elements, giving O(n) total work

// Probability pivot is "bad" (outside middle 50%): 1/2
// After log n pivots, probability ALL are good:
// Pr[all good] ≥ (1/2)^{log n} = 1/n
// With repetition, w.h.p. we find a good pivot in O(log n) tries
```

### Python: Chernoff Bound Verification

```python
import numpy as np
import math

def chernoff_bound(mu, delta):
    """Upper bound on Pr[S > (1+δ)μ]."""
    return (math.e ** delta / (1 + delta) ** (1 + delta)) ** mu

def simplified_bound(mu, delta):
    """Simplified: Pr[S > (1+δ)μ] < exp(-μδ²/3) for δ < 1."""
    return math.exp(-mu * delta**2 / 3)

# Verify with simulation
n = 10000
mu = n / 2  # Expected heads in n fair coin flips
delta = 0.1  # 10% deviation

theoretical = simplified_bound(mu, delta)
print(f"Theoretical bound: Pr[S > {mu*(1+delta):.0f}] < {theoretical:.6f}")

# Simulate
count_exceed = 0
for _ in range(10000):
    flips = np.random.binomial(n, 0.5)
    if flips > mu * (1 + delta):
        count_exceed += 1

empirical = count_exceed / 10000
print(f"Empirical: {empirical:.6f}")
print(f"Theory is {'conservative' if theoretical > empirical else 'tight'}")
```

---

## 150.3 Schwartz-Zippel Lemma

### Definition

A non-zero multivariate polynomial of total degree d over a field F has at most d/|S| fraction of roots in any finite subset S ⊆ F.

### Motivation

Used for **polynomial identity testing**: given two polynomials, determine if they are identical. Evaluating at random points gives a correct answer with high probability.

### Formal Statement

Let p(x₁, ..., xₙ) be a non-zero polynomial of degree d over field F. Let S ⊆ F with |S| = m. Then:

Pr_{r₁,...,rₙ ∈ S}[p(r₁, ..., rₙ) = 0] ≤ d/m

### Application: Determinant-Based Connectivity Test

```python
import numpy as np

def are_graphs_isomorphic_random(adj1, adj2, num_trials=50):
    """
    Randomized graph isomorphism test using Schwartz-Zippel.
    Not definitive but very fast.

    Uses the adjacency matrix and random vertex labels.
    """
    n = len(adj1)
    if len(adj2) != n:
        return False

    for _ in range(num_trials):
        # Random permutation of vertex labels
        perm = np.random.permutation(n)

        # Apply permutation to adj2
        adj2_perm = [[adj2[perm[i]][perm[j]] for j in range(n)] for i in range(n)]

        # Compare
        if adj1 != adj2_perm:
            continue

        # If they match under some permutation, likely isomorphic
        return True

    return False  # Could be isomorphic, but we didn't find evidence

# Polynomial identity testing
def polynomial_identity_test(poly_coeffs, num_trials=100):
    """
    Test if polynomial is identically zero using Schwartz-Zippel.
    poly_coeffs: list of (coefficient, monomial) pairs
    """
    # Simplified: test univariate polynomial
    # p(x) = a_n x^n + ... + a_0
    # If p is zero polynomial, p(r) = 0 for all r
    # If p has degree d, Pr[p(r) = 0] ≤ d/|S|

    max_degree = len(poly_coeffs) - 1
    S = list(range(1, 1000))  # Field elements to sample from

    for _ in range(num_trials):
        r = np.random.choice(S)
        val = sum(c * r**i for i, c in enumerate(poly_coeffs))
        if val != 0:
            return False  # Definitely not zero polynomial

    return True  # Probably zero polynomial (error prob ≤ max_degree/|S|)
```

### Complexity

| Problem | Deterministic | Randomized (Schwartz-Zippel) |
|---|---|---|
| Polynomial identity | Exponential (expand) | O(d · trials) |
| Graph matching | NP-hard in general | Polynomial with error |
| Matrix rank | O(n³) | O(n²) with error |

---

## 150.4 Power of Two Choices

### Definition

When placing n balls into n bins, choosing the **less loaded of 2 random bins** instead of 1 dramatically reduces the maximum load.

### Formal Result

| Strategy | Max Load |
|---|---|
| 1 choice | Θ(log n / log log n) w.h.p. |
| 2 choices | Θ(log log n) w.h.p. |
| d choices | Θ(log_d log n) w.h.p. |

### Code: Simulation and Analysis

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <algorithm>
#include <cmath>

int simulateTwoChoices(int n, int numBalls, std::mt19937& rng) {
    std::vector<int> bins(n, 0);
    std::uniform_int_distribution<int> dist(0, n - 1);

    for (int i = 0; i < numBalls; i++) {
        int b1 = dist(rng);
        int b2 = dist(rng);
        // Place in the less loaded bin
        if (bins[b1] <= bins[b2])
            bins[b1]++;
        else
            bins[b2]++;
    }
    return *std::max_element(bins.begin(), bins.end());
}

int simulateOneChoice(int n, int numBalls, std::mt19937& rng) {
    std::vector<int> bins(n, 0);
    std::uniform_int_distribution<int> dist(0, n - 1);

    for (int i = 0; i < numBalls; i++)
        bins[dist(rng)]++;

    return *std::max_element(bins.begin(), bins.end());
}

int main() {
    std::mt19937 rng(42);
    for (int n : {1000, 10000, 100000}) {
        int max1 = simulateOneChoice(n, n, rng);
        int max2 = simulateTwoChoices(n, n, rng);
        double loglog = std::log2(std::log2(n));
        std::cout << "n=" << n
                  << ": 1-choice max=" << max1
                  << ", 2-choice max=" << max2
                  << ", log₂log₂(n) ≈ " << loglog << "\n";
    }
    return 0;
}
```

### Application: Load Balancing in Distributed Systems

```python
import random

class TwoChoiceLoadBalancer:
    """Load balancer using the power of two choices."""

    def __init__(self, num_servers):
        self.loads = [0] * num_servers

    def assign(self):
        n = len(self.loads)
        s1, s2 = random.randint(0, n-1), random.randint(0, n-1)
        chosen = s1 if self.loads[s1] <= self.loads[s2] else s2
        self.loads[chosen] += 1
        return chosen

    def get_max_load(self):
        return max(self.loads)

# Simulate
lb = TwoChoiceLoadBalancer(1000)
for _ in range(10000):
    lb.assign()
print(f"Max load with 2 choices: {lb.get_max_load()}")

lb1 = [0] * 1000
for _ in range(10000):
    lb1[random.randint(0, 999)] += 1
print(f"Max load with 1 choice: {max(lb1)}")
```

---

## 150.5 Markov Chains and Random Walks

### Definition

A **Markov chain** is a sequence of random states where the next state depends only on the current state. **Random walks** on graphs are a special case.

### Application: Mixing Time for Sampling

```cpp
#include <iostream>
#include <vector>
#include <random>
#include <cmath>

// Random walk on a graph to estimate stationary distribution
class RandomWalkSampler {
    const std::vector<std::vector<int>>& adj;
    std::mt19937 rng;

public:
    RandomWalkSampler(const std::vector<std::vector<int>>& a)
        : adj(a), rng(42) {}

    // Sample vertices proportional to degree (stationary distribution)
    std::vector<int> sample(int numSteps, int startVertex = 0) {
        std::vector<int> visits(adj.size(), 0);
        int current = startVertex;

        for (int step = 0; step < numSteps; step++) {
            visits[current]++;
            // Move to random neighbor
            auto& neighbors = adj[current];
            std::uniform_int_distribution<int> dist(0, (int)neighbors.size() - 1);
            current = neighbors[dist(rng)];
        }
        return visits;
    }
};

int main() {
    // Simple graph: 0-1-2-3-0 (cycle)
    std::vector<std::vector<int>> adj = {{1,3}, {0,2}, {1,3}, {0,2}};

    RandomWalkSampler sampler(adj);
    auto visits = sampler.sample(100000);

    std::cout << "Visit counts (should be ~equal for regular graph):\n";
    for (int i = 0; i < (int)visits.size(); i++)
        std::cout << "  Vertex " << i << ": " << visits[i] << "\n";

    return 0;
}
```

---

## 150.6 Reservoir Sampling

### Definition

Select k items uniformly at random from a stream of unknown length, using O(k) space.

### Algorithm

```cpp
#include <iostream>
#include <vector>
#include <random>

std::vector<int> reservoirSample(std::istream& stream, int k, std::mt19937& rng) {
    std::vector<int> reservoir(k);
    int i = 0;
    int val;

    // Fill reservoir with first k items
    while (i < k && stream >> val)
        reservoir[i++] = val;

    // For each subsequent item, replace with probability k/i
    while (stream >> val) {
        std::uniform_int_distribution<int> dist(0, i);
        int j = dist(rng);
        if (j < k)
            reservoir[j] = val;
        i++;
    }
    return reservoir;
}

int main() {
    // Simulate stream: 1 to 1000000
    std::mt19937 rng(42);
    std::vector<int> reservoir(5);
    int i = 0;

    for (int val = 1; val <= 1000000; val++) {
        if (i < 5) {
            reservoir[i] = val;
        } else {
            std::uniform_int_distribution<int> dist(0, i);
            int j = dist(rng);
            if (j < 5) reservoir[j] = val;
        }
        i++;
    }

    std::cout << "Reservoir sample of 5 from 1M: ";
    for (int x : reservoir) std::cout << x << " ";
    std::cout << "\n";

    return 0;
}
```

---

## 150.7 Exercises

1. **Karger-Stein**: Implement the Karger-Stein algorithm that runs in O(n² log³ n) by using recursive contraction with early stopping.
2. **Chernoff application**: Prove using Chernoff bounds that a random graph G(n, 1/2) has diameter 2 with high probability.
3. **Schwartz-Zippel**: Use the Schwartz-Zippel lemma to design an algorithm for testing whether two multivariate polynomials are identical.
4. **Reservoir sampling proof**: Prove that reservoir sampling selects each element with probability exactly k/n.
5. **Two choices**: Implement a d-choice load balancer and verify that max load is Θ(log_d log n).
6. **Random walk cover time**: Simulate a random walk on a complete graph and measure the cover time (visiting all vertices).
7. **Fingerprinting**: Implement Karp-Rabin string matching using polynomial hashing and Schwartz-Zippel analysis.

---

## 150.8 Interview Questions

1. **Explain Karger's min-cut algorithm. How do you improve the success probability?**
   *Answer*: Repeatedly contract random edges until 2 vertices remain. The remaining edges form a candidate cut. Each run succeeds with probability ≥ 2/n², so repeat O(n² log n) times and take the minimum.

2. **What is a Chernoff bound and when do you use it?**
   *Answer*: A Chernoff bound gives exponentially decreasing tail probabilities for sums of independent random variables. Use it to prove that a randomized algorithm's output is close to its expectation with high probability.

3. **How does the power of two choices work?**
   *Answer*: When assigning a task to a server, pick 2 random servers and choose the less loaded one. This reduces the maximum load from Θ(log n / log log n) to Θ(log log n)—a dramatic improvement for a tiny extra cost.

4. **What is reservoir sampling?**
   *Answer*: An algorithm to select k items uniformly at random from a stream of unknown length. Each new item replaces a random element in the reservoir with probability k/i (where i is the item's index). Every element is equally likely to be in the final sample.

5. **How does Schwartz-Zippel help with polynomial identity testing?**
   *Answer*: If two polynomials of degree d are different, they can agree on at most d/|S| fraction of points in S. So evaluating at a random point from a large S gives a correct "not identical" answer with high probability.

---

## 150.9 Cross-References

- **Chapter 12**: Hashing (for fingerprinting, Schwartz-Zippel)
- **Chapter 75**: Basic randomized algorithms
- **Chapter 76**: Probabilistic analysis
- **Chapter 145**: Parallel algorithms (for load balancing)
- **Chapter 155**: Advanced graph theory (for expander graphs)
- **Chapter 164**: Approximation algorithms

---

## Summary

| Technique | Application | Key Bound |
|---|---|---|
| Karger's Contraction | Min cut | O(n² log n) runs, ≥2/n² success each |
| Chernoff Bounds | Concentration inequalities | Exponential tail bounds |
| Schwartz-Zippel | Polynomial identity testing | d/|S| error probability |
| Power of Two Choices | Load balancing | Θ(log log n) max load |
| Reservoir Sampling | Streaming random selection | O(k) space, uniform |
| Random Walks | Mixing, sampling | Mixing time O(n log n) for regular graphs |
