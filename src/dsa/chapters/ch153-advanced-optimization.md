# Chapter 153: Advanced Optimization

## Prerequisites
- LP, calculus basics, graph theory

## Interview Frequency: ★

---

## 153.1 What Is Advanced Optimization?

Advanced optimization covers algorithms that find the best solution among many possibilities, going beyond simple greedy or DP approaches. These methods handle **continuous domains**, **online settings**, and **network flow** problems.

**Motivation:** Many real-world problems involve optimizing a function over continuous parameters (machine learning), making decisions with incomplete information (online algorithms), or routing flow through networks (logistics). Classical discrete algorithms don't apply directly.

---

## 153.2 Gradient Descent

### Definition

**Gradient Descent** is an iterative optimization algorithm that finds a local minimum of a differentiable function by repeatedly moving in the direction of steepest descent (negative gradient).

### Intuition

Imagine you're blindfolded on a hilly landscape and want to reach the lowest valley. At each step, you feel which direction slopes downward most steeply and take a step that way. The size of your step is the **learning rate**.

### Formal Explanation

Given function f(x), starting from x₀:

```
x_{t+1} = x_t - η · ∇f(x_t)
```

Where:
- η (eta) is the learning rate (step size)
- ∇f(x_t) is the gradient at x_t

**Convergence guarantees:**
- Convex function: O(1/t) convergence rate
- Strongly convex: O(e^{-t}) exponential convergence
- Non-convex: converges to a stationary point (may be local min)

### Step-by-Step Walkthrough

**Problem:** Minimize f(x) = (x - 3)²

1. **Start:** x₀ = 0, η = 0.1
2. **Iteration 1:** ∇f(0) = 2(0-3) = -6 → x₁ = 0 - 0.1×(-6) = 0.6
3. **Iteration 2:** ∇f(0.6) = 2(0.6-3) = -4.8 → x₂ = 0.6 - 0.1×(-4.8) = 1.08
4. **Iteration 3:** ∇f(1.08) = -3.84 → x₃ = 1.08 + 0.384 = 1.464
5. ...converges to x = 3

### Dry Run Table

| Iteration | x | Gradient | Step (η×grad) | New x |
|---|---|---|---|---|
| 0 | 0.0 | -6.0 | -0.6 | 0.6 |
| 1 | 0.6 | -4.8 | -0.48 | 1.08 |
| 2 | 1.08 | -3.84 | -0.384 | 1.464 |
| 3 | 1.464 | -3.072 | -0.307 | 1.771 |
| 10 | 2.71 | -0.58 | -0.058 | 2.77 |

### Code

```cpp
#include <iostream>
#include <cmath>
#include <functional>

// Gradient descent for f(x) = (x-3)^2
double gradientDescent(double start, double lr, int iterations) {
    double x = start;
    for (int i = 0; i < iterations; i++) {
        double grad = 2 * (x - 3); // derivative of (x-3)^2
        x -= lr * grad;
        if (i < 5 || i % 20 == 0)
            std::cout << "  iter " << i << ": x = " << x << "\n";
    }
    return x;
}

int main() {
    std::cout << "Gradient descent for f(x) = (x-3)^2\n";
    double result = gradientDescent(0.0, 0.1, 100);
    std::cout << "Minimum at x = " << result << " (expected: 3)\n";
    return 0;
}
```

```python
def gradient_descent(start, lr, iterations, f_grad):
    """Generic gradient descent."""
    x = start
    history = [x]
    for i in range(iterations):
        grad = f_grad(x)
        x -= lr * grad
        history.append(x)
    return x, history

# Example: f(x) = (x-3)^2, f'(x) = 2(x-3)
f_grad = lambda x: 2 * (x - 3)
result, hist = gradient_descent(0.0, 0.1, 100, f_grad)
print(f"Minimum at x = {result:.6f} (expected: 3)")
```

```java
public class GradientDescent {
    public static double gradientDescent(double start, double lr, int iterations) {
        double x = start;
        for (int i = 0; i < iterations; i++) {
            double grad = 2 * (x - 3); // derivative of (x-3)^2
            x -= lr * grad;
        }
        return x;
    }

    public static void main(String[] args) {
        double result = gradientDescent(0.0, 0.1, 100);
        System.out.printf("Minimum at x = %.6f (expected: 3)%n", result);
    }
}
```

### Variants

| Variant | Description | When to Use |
|---|---|---|
| **Batch GD** | Uses full dataset gradient | Small datasets |
| **Stochastic GD (SGD)** | Uses single sample gradient | Large datasets, online |
| **Mini-batch GD** | Uses batch of samples | Deep learning standard |
| **Momentum** | Accumulates velocity | Faster convergence |
| **Adam** | Adaptive learning rates | Default for neural networks |

### Complexity

- **Per iteration:** O(d) where d = number of dimensions
- **Total:** O(d × iterations) until convergence
- **Convergence rate:** depends on function properties (convexity, smoothness)

---

## 153.3 Multiplicative Weights Update (MWU)

### Definition

The **Multiplicative Weights Update** algorithm is an online learning method where a set of experts make predictions, and we adjust their weights based on their performance.

### Motivation

Imagine you're a stock investor choosing which of n advisors to follow. Each day, each advisor predicts "buy" or "sell". You want to minimize your total loss. MWU gives you a strategy that performs nearly as well as the best single advisor in hindsight.

### Formal Explanation

**Setup:** n experts, T rounds. Each round:
1. Each expert i has weight w_i
2. Choose expert i with probability w_i / Σw_j
3. Observe loss l_i ∈ [0, 1] for each expert
4. Update: w_i ← w_i × (1 - η × l_i)
5. Normalize weights

**Regret bound:** After T rounds with n experts and learning rate η:

```
Regret ≤ ηT + ln(n)/η
```

Setting η = √(ln(n)/T) gives **Regret ≤ O(√(T ln n))**

### Step-by-Step Walkthrough

**Problem:** 3 experts, 5 rounds, η = 0.5

| Round | Weights | Probabilities | Losses | New Weights |
|---|---|---|---|---|
| 1 | [1, 1, 1] | [0.33, 0.33, 0.33] | [0, 1, 0.5] | [1, 0.5, 0.75] |
| 2 | [1, 0.5, 0.75] | [0.44, 0.22, 0.33] | [1, 0, 0] | [0.5, 0.5, 0.75] |
| 3 | [0.5, 0.5, 0.75] | [0.29, 0.29, 0.43] | [0, 0.5, 1] | [0.5, 0.375, 0.375] |

### Code

```cpp
#include <iostream>
#include <vector>
#include <numeric>

class MultiplicativeWeights {
    int n;
    double eta;
    std::vector<double> weights;
    
public:
    MultiplicativeWeights(int n, double eta) : n(n), eta(eta), weights(n, 1.0) {}
    
    // Returns probability distribution over experts
    std::vector<double> getDistribution() {
        double sum = std::accumulate(weights.begin(), weights.end(), 0.0);
        std::vector<double> prob(n);
        for (int i = 0; i < n; i++) prob[i] = weights[i] / sum;
        return prob;
    }
    
    // Update weights with losses (each in [0, 1])
    void update(const std::vector<double>& losses) {
        for (int i = 0; i < n; i++)
            weights[i] *= (1.0 - eta * losses[i]);
    }
    
    const std::vector<double>& getWeights() const { return weights; }
};

int main() {
    MultiplicativeWeights mw(3, 0.5);
    
    // Round 1: expert 0 perfect, expert 1 worst
    auto dist = mw.getDistribution();
    std::cout << "Round 1 dist: ";
    for (double d : dist) std::cout << d << " ";
    std::cout << "\n";
    mw.update({0.0, 1.0, 0.5});
    
    // Round 2
    dist = mw.getDistribution();
    std::cout << "Round 2 dist: ";
    for (double d : dist) std::cout << d << " ";
    std::cout << "\n";
    
    return 0;
}
```

```python
class MultiplicativeWeights:
    def __init__(self, n, eta=0.5):
        self.n = n
        self.eta = eta
        self.weights = [1.0] * n
    
    def get_distribution(self):
        total = sum(self.weights)
        return [w / total for w in self.weights]
    
    def update(self, losses):
        """losses: list of losses in [0, 1] for each expert."""
        for i in range(self.n):
            self.weights[i] *= (1 - self.eta * losses[i])

# Example
mw = MultiplicativeWeights(3, eta=0.5)
print(f"Initial: {mw.get_distribution()}")
mw.update([0.0, 1.0, 0.5])
print(f"After round 1: {mw.get_distribution()}")
```

```java
public class MultiplicativeWeights {
    private int n;
    private double eta;
    private double[] weights;

    public MultiplicativeWeights(int n, double eta) {
        this.n = n;
        this.eta = eta;
        this.weights = new double[n];
        java.util.Arrays.fill(weights, 1.0);
    }

    public double[] getDistribution() {
        double sum = 0;
        for (double w : weights) sum += w;
        double[] prob = new double[n];
        for (int i = 0; i < n; i++) prob[i] = weights[i] / sum;
        return prob;
    }

    public void update(double[] losses) {
        for (int i = 0; i < n; i++)
            weights[i] *= (1.0 - eta * losses[i]);
    }
}
```

### Applications

| Application | How MWU Applies |
|---|---|
| Online learning | Experts framework |
| Game theory | Finding Nash equilibrium |
| LP solving | Online mirror descent |
| Boosting | AdaBoost is MWU in disguise |
| Ad allocation | Online ad optimization |

---

## 153.4 Min Cost Flow

### Definition

**Minimum Cost Flow** finds the cheapest way to send a specified amount of flow through a network with edge capacities and costs.

### Motivation

Logistics: you have warehouses (sources), stores (sinks), and shipping routes (edges) with capacities and costs. Find the cheapest way to ship all goods.

### Formal Explanation

**Given:**
- Directed graph G = (V, E)
- Each edge (u,v) has capacity c(u,v) and cost w(u,v)
- Source s, sink t, required flow F

**Find:** Flow f of amount F minimizing Σ f(u,v) × w(u,v)

**Constraints:**
- 0 ≤ f(u,v) ≤ c(u,v) (capacity)
- Σ f(u,v) = Σ f(v,w) for all v ≠ s,t (conservation)

### Algorithms

| Algorithm | Time Complexity | Notes |
|---|---|---|
| Successive Shortest Path | O(F × (V+E) log V) | Good for small F |
| Cycle Canceling | O(V × E² × log V) | Find negative cycles |
| Network Simplex | O(V² × E) avg | Practical, fast |
| Cost Scaling | O(V² × E × log(VC)) | Best theoretical |

### Successive Shortest Path Algorithm

1. Start with zero flow
2. While flow < F:
   a. Find shortest path from s to t in **residual graph** (using costs as weights)
   b. Augment flow along this path by min(residual capacities, remaining flow)
3. Return total cost

### Code (Successive Shortest Path with SPFA)

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <climits>

struct Edge {
    int to, cap, cost, flow;
};

class MinCostFlow {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<Edge> edges;
    
public:
    MinCostFlow(int n) : n(n), adj(n) {}
    
    void addEdge(int u, int v, int cap, int cost) {
        adj[u].push_back(edges.size());
        edges.push_back({v, cap, cost, 0});
        adj[v].push_back(edges.size());
        edges.push_back({u, 0, -cost, 0});
    }
    
    // Returns {flow, cost}
    std::pair<int, long long> solve(int s, int t, int maxFlow) {
        long long totalCost = 0;
        int totalFlow = 0;
        
        while (totalFlow < maxFlow) {
            // SPFA to find shortest path in residual graph
            std::vector<long long> dist(n, LLONG_MAX);
            std::vector<int> parent(n, -1);
            std::vector<bool> inQueue(n, false);
            std::queue<int> q;
            
            dist[s] = 0;
            q.push(s);
            inQueue[s] = true;
            
            while (!q.empty()) {
                int u = q.front(); q.pop();
                inQueue[u] = false;
                for (int idx : adj[u]) {
                    auto& e = edges[idx];
                    if (e.cap - e.flow > 0 && dist[u] + e.cost < dist[e.to]) {
                        dist[e.to] = dist[u] + e.cost;
                        parent[e.to] = idx;
                        if (!inQueue[e.to]) {
                            q.push(e.to);
                            inQueue[e.to] = true;
                        }
                    }
                }
            }
            
            if (dist[t] == LLONG_MAX) break; // No more augmenting paths
            
            // Find bottleneck
            int bottleneck = maxFlow - totalFlow;
            for (int v = t; v != s; v = edges[parent[v] ^ 1].to)
                bottleneck = std::min(bottleneck, edges[parent[v]].cap - edges[parent[v]].flow);
            
            // Augment
            for (int v = t; v != s; v = edges[parent[v] ^ 1].to) {
                edges[parent[v]].flow += bottleneck;
                edges[parent[v] ^ 1].flow -= bottleneck;
            }
            
            totalFlow += bottleneck;
            totalCost += (long long)bottleneck * dist[t];
        }
        
        return {totalFlow, totalCost};
    }
};

int main() {
    MinCostFlow mcf(4);
    mcf.addEdge(0, 1, 2, 1);  // s -> A, cap 2, cost 1
    mcf.addEdge(0, 2, 3, 2);  // s -> B, cap 3, cost 2
    mcf.addEdge(1, 2, 1, 1);  // A -> B, cap 1, cost 1
    mcf.addEdge(1, 3, 2, 3);  // A -> t, cap 2, cost 3
    mcf.addEdge(2, 3, 2, 1);  // B -> t, cap 2, cost 1
    
    auto [flow, cost] = mcf.solve(0, 3, 5);
    std::cout << "Flow: " << flow << ", Cost: " << cost << "\n";
    return 0;
}
```

```python
from collections import deque

class MinCostFlow:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]
        self.edges = []
    
    def add_edge(self, u, v, cap, cost):
        self.adj[u].append(len(self.edges))
        self.edges.append([v, cap, cost, 0])  # to, cap, cost, flow
        self.adj[v].append(len(self.edges))
        self.edges.append([u, 0, -cost, 0])
    
    def solve(self, s, t, max_flow):
        total_flow = 0
        total_cost = 0
        
        while total_flow < max_flow:
            # SPFA
            dist = [float('inf')] * self.n
            parent = [-1] * self.n
            in_queue = [False] * self.n
            dist[s] = 0
            q = deque([s])
            in_queue[s] = True
            
            while q:
                u = q.popleft()
                in_queue[u] = False
                for idx in self.adj[u]:
                    e = self.edges[idx]
                    if e[1] - e[3] > 0 and dist[u] + e[2] < dist[e[0]]:
                        dist[e[0]] = dist[u] + e[2]
                        parent[e[0]] = idx
                        if not in_queue[e[0]]:
                            q.append(e[0])
                            in_queue[e[0]] = True
            
            if dist[t] == float('inf'):
                break
            
            # Bottleneck
            bottleneck = max_flow - total_flow
            v = t
            while v != s:
                e = self.edges[parent[v]]
                bottleneck = min(bottleneck, e[1] - e[3])
                v = self.edges[parent[v] ^ 1][0]
            
            # Augment
            v = t
            while v != s:
                self.edges[parent[v]][3] += bottleneck
                self.edges[parent[v] ^ 1][3] -= bottleneck
                v = self.edges[parent[v] ^ 1][0]
            
            total_flow += bottleneck
            total_cost += bottleneck * dist[t]
        
        return total_flow, total_cost

# Example
mcf = MinCostFlow(4)
mcf.add_edge(0, 1, 2, 1)
mcf.add_edge(0, 2, 3, 2)
mcf.add_edge(1, 2, 1, 1)
mcf.add_edge(1, 3, 2, 3)
mcf.add_edge(2, 3, 2, 1)
flow, cost = mcf.solve(0, 3, 5)
print(f"Flow: {flow}, Cost: {cost}")
```

```java
import java.util.*;

public class MinCostFlow {
    int n;
    List<List<Integer>> adj;
    List<int[]> edges; // [to, cap, cost, flow]

    public MinCostFlow(int n) {
        this.n = n;
        this.adj = new ArrayList<>();
        this.edges = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
    }

    void addEdge(int u, int v, int cap, int cost) {
        adj.get(u).add(edges.size());
        edges.add(new int[]{v, cap, cost, 0});
        adj.get(v).add(edges.size());
        edges.add(new int[]{u, 0, -cost, 0});
    }

    long[] solve(int s, int t, int maxFlow) {
        long totalCost = 0;
        int totalFlow = 0;

        while (totalFlow < maxFlow) {
            long[] dist = new long[n];
            int[] parent = new int[n];
            boolean[] inQ = new boolean[n];
            Arrays.fill(dist, Long.MAX_VALUE);
            Arrays.fill(parent, -1);
            dist[s] = 0;
            Queue<Integer> q = new LinkedList<>();
            q.add(s); inQ[s] = true;

            while (!q.isEmpty()) {
                int u = q.poll(); inQ[u] = false;
                for (int idx : adj.get(u)) {
                    int[] e = edges.get(idx);
                    if (e[1] - e[3] > 0 && dist[u] + e[2] < dist[e[0]]) {
                        dist[e[0]] = dist[u] + e[2];
                        parent[e[0]] = idx;
                        if (!inQ[e[0]]) { q.add(e[0]); inQ[e[0]] = true; }
                    }
                }
            }

            if (dist[t] == Long.MAX_VALUE) break;

            int bottleneck = maxFlow - totalFlow;
            for (int v = t; v != s; v = edges.get(parent[v] ^ 1)[0])
                bottleneck = Math.min(bottleneck, edges.get(parent[v])[1] - edges.get(parent[v])[3]);

            for (int v = t; v != s; v = edges.get(parent[v] ^ 1)[0]) {
                edges.get(parent[v])[3] += bottleneck;
                edges.get(parent[v] ^ 1)[3] -= bottleneck;
            }

            totalFlow += bottleneck;
            totalCost += (long) bottleneck * dist[t];
        }

        return new long[]{totalFlow, totalCost};
    }
}
```

---

## 153.5 Convex Optimization Overview

### What Makes a Problem Convex?

A function f is **convex** if for all x, y and λ ∈ [0,1]:

```
f(λx + (1-λ)y) ≤ λf(x) + (1-λ)f(y)
```

**Key property:** Any local minimum of a convex function is a global minimum.

### Convex vs Non-Convex

| Property | Convex | Non-Convex |
|---|---|---|
| Local min = global min? | ✅ Yes | ❌ No |
| Gradient descent finds? | Global optimum | Local optimum |
| Examples | Linear regression, SVM | Neural networks, k-means |

### Common Convex Problems in DSA

| Problem | Formulation |
|---|---|
| Binary search on answer | Convex feasibility check |
| Minimize max distance | Convex function of position |
| Fractional programming | Ratio optimization |

---

## 153.6 Exercises

### Exercise 1: Gradient Descent Tuning
Implement gradient descent for f(x,y) = x² + 4y². Try different learning rates (0.01, 0.1, 0.5) and observe convergence. What happens with η = 0.6?

### Exercise 2: MWU for Rock-Paper-Scissors
Implement MWU with 3 experts (rock, paper, scissors). What distribution does it converge to? (Hint: it should approach 1/3 each.)

### Exercise 3: Min Cost Flow
Given a bipartite graph with n workers and m jobs, each edge has a cost. Find the minimum cost matching of size k. Implement using min cost flow.

### Exercise 4: Binary Search on Answer with Convex Function
Given n points on a line, find the point that minimizes the sum of squared distances. Use ternary search (binary search on convex function).

---

## 153.7 Interview Questions

### Q1: When would you use gradient descent in a coding interview?
**A:** Rarely directly, but understanding it helps with:
- Binary search on answer (optimization over monotone function)
- Understanding ML-related follow-up questions
- Ternary search on unimodal functions

### Q2: Explain the regret bound of MWU.
**A:** After T rounds with n experts, MWU achieves regret O(√(T ln n)). This means your total loss is at most O(√(T ln n)) more than the best single expert in hindsight. Setting η = √(ln(n)/T) balances the two terms in the regret bound.

### Q3: How does min cost flow relate to max flow?
**A:** Max flow finds the maximum amount of flow. Min cost flow finds the cheapest way to send a specified amount. If all costs are 0, min cost flow reduces to max flow. Min cost flow can also be solved by augmenting along shortest (cheapest) paths in the residual graph.

### Q4: What's the difference between convex and strongly convex?
**A:** A function is convex if f(λx + (1-λ)y) ≤ λf(x) + (1-λ)f(y). It's **strongly convex** if f(y) ≥ f(x) + ∇f(x)·(y-x) + (μ/2)||y-x||² for some μ > 0. Strong convexity guarantees a unique minimum and faster convergence (exponential vs polynomial).

---

## 153.8 Cross-References

| Topic | Related Chapter |
|---|---|
| Max Flow | Chapter 100 |
| Bipartite Matching | Chapter 101 |
| Binary Search | Chapter 3 |
| Greedy Algorithms | Chapter 15 |
| Dynamic Programming | Chapter 20 |
| Graph Theory | Chapter 40 |
| Number Theory (modular inverse) | Chapter 80 |

---

## Summary

| Method | Convergence | Use Case | Complexity |
|---|---|---|---|
| Gradient Descent | O(1/t) convex, O(e^{-t}) strongly | Convex optimization | O(d × iterations) |
| Multiplicative Weights | O(√(T log n)) | Online learning, game theory | O(n × T) |
| Min Cost Flow | Polynomial | Network routing | O(F × (V+E) log V) |
| Convex Optimization | Problem-dependent | Continuous optimization | Varies |

**Key Insight:** These optimization methods extend DSA beyond discrete problems. Gradient descent is the workhorse of machine learning. MWU appears in game theory and online algorithms. Min cost flow generalizes many graph problems (shortest path, max flow, matching).
