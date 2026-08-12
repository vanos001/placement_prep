# Chapter 152: Integer Programming and LP Duality

## Prerequisites
- Linear programming basics
- Branch and bound concepts

## Interview Frequency: ★

Integer programming (IP) extends LP with integrality constraints. LP duality provides powerful theoretical tools for optimization and approximation algorithms.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Integer Programming | ★ | Hard | NP-hard in general |
| LP Duality | ★★ | Medium | Weak/strong duality |
| Complementary Slackness | ★ | Hard | Optimality conditions |
| LP Relaxation | ★★ | Medium | Approximation via rounding |

---

## Definition

**Integer Programming (IP)** is an optimization problem where some or all variables must take integer values. It's NP-hard in general but solvable for specific structures (totally unimodular matrices, fixed number of variables).

**LP Duality** associates every linear program (primal) with a dual program. The dual provides lower bounds (for minimization) and certificates of optimality.

## Motivation

Many real-world problems are naturally integer: scheduling (yes/no), routing (which edges), facility location (open/close). LP relaxation + rounding gives approximation algorithms with provable guarantees.

Duality is fundamental to:
- Understanding LP optimality
- Designing primal-dual approximation algorithms
- Sensitivity analysis (how does the optimum change with input?)

## Intuition

- **IP**: Like LP but you can't split things. You can't build half a warehouse.
- **Duality**: The primal asks "what's the cheapest way to produce?" The dual asks "what's the most I can charge for resources?" At optimality, both answers match.

---

## 152.1 Integer Programming

### Formulation

```
min c^T x
s.t. Ax ≤ b
     x ≥ 0
     x_i ∈ Z (some or all variables)
```

### Branch and Bound

The standard exact approach:
1. Solve LP relaxation (ignore integrality)
2. If solution is integer → done
3. Pick a fractional variable x_i, branch: x_i ≤ ⌊x_i*⌋ and x_i ≥ ⌈x_i*⌉
4. Recursively solve each branch
5. Prune branches with bound ≥ current best

### C++ Implementation (0/1 Knapsack as IP)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

struct Item { int weight, value; };

class KnapsackIP {
    int capacity;
    std::vector<Item> items;
    int bestValue;

    double getBound(int idx, int remaining, int currentVal) {
        double bound = currentVal;
        int remCap = remaining;
        for (int i = idx; i < (int)items.size() && remCap > 0; i++) {
            if (items[i].weight <= remCap) {
                bound += items[i].value;
                remCap -= items[i].weight;
            } else {
                bound += (double)items[i].value * remCap / items[i].weight;
                break;
            }
        }
        return bound;
    }

    void solve(int idx, int remaining, int currentVal,
               std::vector<int>& currentSol, std::vector<int>& bestSol) {
        if (idx == (int)items.size()) {
            if (currentVal > bestValue) {
                bestValue = currentVal;
                bestSol = currentSol;
            }
            return;
        }

        if (getBound(idx, remaining, currentVal) <= bestValue) return;

        // Don't take item
        solve(idx + 1, remaining, currentVal, currentSol, bestSol);

        // Take item
        if (items[idx].weight <= remaining) {
            currentSol[idx] = 1;
            solve(idx + 1, remaining - items[idx].weight,
                  currentVal + items[idx].value, currentSol, bestSol);
            currentSol[idx] = 0;
        }
    }

public:
    KnapsackIP(int cap, std::vector<Item> items)
        : capacity(cap), items(items), bestValue(0) {
        std::sort(this->items.begin(), this->items.end(),
            [](const Item& a, const Item& b) {
                return (double)a.value / a.weight > (double)b.value / b.weight;
            });
    }

    std::pair<int, std::vector<int>> solve() {
        std::vector<int> cur(items.size(), 0), best(items.size(), 0);
        solve(0, capacity, 0, cur, best);
        return {bestValue, best};
    }
};

int main() {
    std::vector<Item> items = {{2,3},{3,4},{4,5},{5,6},{9,10}};
    KnapsackIP ks(10, items);
    auto [val, sol] = ks.solve();
    std::cout << "Optimal value: " << val << "\n";
    std::cout << "Selected: ";
    for (int i = 0; i < (int)sol.size(); i++)
        if (sol[i]) std::cout << i << " ";
    std::cout << "\n";
    return 0;
}
```

### Python Implementation

```python
class KnapsackIP:
    def __init__(self, capacity, items):
        self.capacity = capacity
        # Sort by value/weight ratio
        self.items = sorted(items, key=lambda x: x[1]/x[0], reverse=True)
        self.best_value = 0
        self.best_sol = []

    def _bound(self, idx, remaining, current_val):
        bound = current_val
        cap = remaining
        for i in range(idx, len(self.items)):
            w, v = self.items[i]
            if w <= cap:
                bound += v
                cap -= w
            else:
                bound += v * cap / w
                break
        return bound

    def _solve(self, idx, remaining, current_val, current_sol):
        if idx == len(self.items):
            if current_val > self.best_value:
                self.best_value = current_val
                self.best_sol = current_sol[:]
            return

        if self._bound(idx, remaining, current_val) <= self.best_value:
            return

        # Don't take
        self._solve(idx + 1, remaining, current_val, current_sol)

        # Take
        w, v = self.items[idx]
        if w <= remaining:
            current_sol[idx] = 1
            self._solve(idx + 1, remaining - w, current_val + v, current_sol)
            current_sol[idx] = 0

    def solve(self):
        self._solve(0, self.capacity, 0, [0] * len(self.items))
        return self.best_value, self.best_sol

# Example
ks = KnapsackIP(10, [(2,3),(3,4),(4,5),(5,6),(9,10)])
val, sol = ks.solve()
print(f"Optimal value: {val}")
```

### Java Implementation

```java
import java.util.*;

public class KnapsackIP {
    static class Item { int w, v; Item(int w, int v) { this.w = w; this.v = v; } }

    int cap; Item[] items; int bestVal = 0; int[] bestSol;

    public KnapsackIP(int cap, Item[] items) {
        this.cap = cap;
        this.items = items;
        Arrays.sort(items, (a, b) -> Double.compare((double)b.v/b.w, (double)a.v/a.w));
    }

    double getBound(int idx, int rem, int curVal) {
        double bound = curVal;
        for (int i = idx; i < items.length && rem > 0; i++) {
            if (items[i].w <= rem) { bound += items[i].v; rem -= items[i].w; }
            else { bound += (double)items[i].v * rem / items[i].w; break; }
        }
        return bound;
    }

    void solve(int idx, int rem, int curVal, int[] cur) {
        if (idx == items.length) {
            if (curVal > bestVal) { bestVal = curVal; bestSol = cur.clone(); }
            return;
        }
        if (getBound(idx, rem, curVal) <= bestVal) return;
        solve(idx+1, rem, curVal, cur);
        if (items[idx].w <= rem) {
            cur[idx] = 1;
            solve(idx+1, rem - items[idx].w, curVal + items[idx].v, cur);
            cur[idx] = 0;
        }
    }

    public static void main(String[] args) {
        Item[] items = {new Item(2,3), new Item(3,4), new Item(4,5), new Item(5,6), new Item(9,10)};
        KnapsackIP ks = new KnapsackIP(10, items);
        ks.solve(0, 10, 0, new int[5]);
        System.out.println("Optimal: " + ks.bestVal);
    }
}
```

---

## 152.2 LP Duality

### Primal-Dual Relationship

**Primal (minimization)**:
```
min c^T x    s.t. Ax ≥ b, x ≥ 0
```

**Dual (maximization)**:
```
max b^T y    s.t. A^T y ≤ c, y ≥ 0
```

### Key Theorems

| Theorem | Statement |
|---|---|
| Weak Duality | For all feasible x, y: b^T y ≤ c^T x |
| Strong Duality | At optimality: b^T y* = c^T x* |
| Complementary Slackness | x_i* · (c_i - (A^T y*)_i) = 0 |

### Example

Primal: min 3x₁ + 5x₂ s.t. x₁ ≥ 4, x₂ ≥ 6, x₁+x₂ ≥ 8

Dual: max 4y₁ + 6y₂ + 8y₃ s.t. y₁+y₃ ≤ 3, y₂+y₃ ≤ 5, y₁,y₂,y₃ ≥ 0

---

## 152.3 LP Relaxation for Approximation

Relax integrality → solve LP → round solution.

### Vertex Cover Example

LP: min Σ x_v s.t. x_u + x_v ≥ 1 for each edge, 0 ≤ x_v ≤ 1

Rounding: if x_v ≥ 0.5, include v in cover → 2-approximation.

```cpp
#include <iostream>
#include <vector>

std::vector<int> lpRoundingVertexCover(
    const std::vector<std::pair<int,int>>& edges, int n) {
    // In practice, solve LP with simplex. Here we use 0.5 as placeholder.
    std::vector<double> lpSolution(n, 0.5);

    std::vector<int> cover;
    for (int v = 0; v < n; v++)
        if (lpSolution[v] >= 0.5) cover.push_back(v);
    return cover;
}

int main() {
    std::vector<std::pair<int,int>> edges = {{0,1},{1,2},{2,3},{3,0}};
    auto cover = lpRoundingVertexCover(edges, 4);
    std::cout << "Cover size: " << cover.size() << " (optimal is 2)\n";
    return 0;
}
```

---

## Exercises

1. **Formulate IP**: Given n jobs with deadlines and profits, formulate the job scheduling problem as an IP.

2. **Dual of max flow**: Write the dual of the max flow LP. What does it correspond to? (Answer: min cut!)

3. **Branch and bound**: Implement branch and bound for the traveling salesman problem. Use LP relaxation for bounds.

4. **Primal-dual algorithm**: Implement the primal-dual algorithm for vertex cover. Start with all dual variables at 0, increase them until a constraint becomes tight.

---

## Interview Questions

1. **Q: Why is integer programming NP-hard when LP is polynomial?**
   A: The integrality constraint makes the feasible region discrete. The LP relaxation has a convex feasible region (easy to optimize), but the integer feasible set can have exponentially many points.

2. **Q: What is the significance of LP duality for approximation algorithms?**
   A: The dual provides a lower bound (for minimization). If we round the primal LP solution and get a solution within factor α of the LP optimum, and the LP optimum ≤ OPT, then we have an α-approximation.

3. **Q: When is LP relaxation tight (exact)?**
   A: When the constraint matrix is totally unimodular (TU) — all subdeterminants are 0, ±1. Network flow matrices are TU, so LP relaxation gives integer solutions for network flow problems.

---

## Cross-References

- [Chapter 29: Network Flow](ch29-network-flow.md) — LP formulation of max flow
- [Chapter 145: Approximation Algorithms](ch145-approximation-algorithms.md) — LP rounding techniques
- [Chapter 151: Linear Programming](ch151-linear-programming.md) — LP foundations

---

## Summary

| Concept | Key Property |
|---|---|
| Integer Programming | NP-hard, use branch & bound |
| Weak duality | Dual ≤ Primal always |
| Strong duality | Dual = Primal at optimum |
| Complementary slackness | Optimality conditions |
| LP Relaxation | Round to get approximation |
