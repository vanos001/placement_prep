# Chapter 169: Min-Cost Max-Flow

## 1. Definition

The **Minimum-Cost Maximum-Flow (MCMF)** problem combines two objectives on a flow network:

1. **Maximize** the total flow from source s to sink t
2. Among all maximum flows, **minimize** the total cost

Formally, given a directed graph G = (V, E) with:
- **Capacity** c(e) ≥ 0 for each edge e
- **Cost** w(e) for each edge e (cost per unit of flow)
- **Source** s and **sink** t

Find a flow f that:
- Maximizes |f| = Σₑ f(e) out of s (maximum flow)
- Minimizes cost(f) = Σₑ f(e) · w(e) (minimum cost among max flows)

### More General: Min-Cost Flow

The general **min-cost flow** problem specifies a desired flow value D:
- Find flow of exactly D units from s to t
- Minimize total cost

MCMF is the special case where D = max possible flow.

## 2. Motivation

### Why Both Cost and Flow?

Pure max-flow finds the most you can send, but ignores the "price." In real-world networks, edges have costs:

- **Transportation**: roads have capacity and fuel cost
- **Networking**: bandwidth and latency/cost
- **Assignment**: workers to jobs with varying costs
- **Supply chain**: shipping routes with capacity and cost

### Classic Applications

| Application | Vertices | Edges | Meaning |
|---|---|---|---|
| Assignment problem | workers, jobs | assignments | cost of assigning worker to job |
| Transportation | sources, destinations | routes | shipping cost per unit |
| Network routing | routers | links | latency/cost per packet |
| Circulation with demands | nodes with supply/demand | pipes | transport cost |

## 3. Intuition

### The Residual Graph Perspective

Like max-flow, MCMF works with **residual graphs**. Each edge e = (u, v) with capacity c and cost w creates:
- **Forward residual edge**: (u, v) with residual capacity c - f(e) and cost +w
- **Backward residual edge**: (v, u) with residual capacity f(e) and cost -w

The negative cost on backward edges is crucial: "undoing" flow gives back the cost.

### The Key Insight

At each step, send flow along the **cheapest augmenting path**. This greedy approach works because:
1. Any max-flow can be decomposed into path flows
2. Rearranging flow along negative-cost cycles doesn't change total flow but reduces cost
3. The successive shortest path algorithm maintains the invariant that no negative-cost cycles exist

### Analogy

Imagine water flowing through pipes. Each pipe has a capacity (how much water it can carry) and a cost per liter. You want to send as much water as possible from source to sink, spending as little as possible. You always route water through the cheapest available path.

## 4. Mathematical Foundations

### 4.1 Linear Programming Formulation

MCMF can be expressed as an LP:

```
Minimize  Σ(e∈E) w(e) · f(e)

Subject to:
  0 ≤ f(e) ≤ c(e)                    for all e ∈ E
  Σ f(e) into v = Σ f(e) out of v    for all v ∈ V \ {s, t}  (flow conservation)
  Σ f(e) out of s = D                 (flow value = D)
```

This is a special LP because the constraint matrix is **totally unimodular**, guaranteeing integer optimal solutions when capacities and demands are integers.

### 4.2 Optimality Conditions (Negative Cycle Optimality)

A feasible flow f of value D is **optimal** if and only if the residual graph Gf contains **no negative-cost cycles**.

**Proof sketch**: If a negative cycle exists, we can push flow around it (up to the bottleneck residual capacity), reducing cost without changing the total flow value. If no negative cycle exists, no improvement is possible.

### 4.3 Potentials and Reduced Costs

To use Dijkstra (which requires non-negative edge weights) instead of Bellman-Ford, we maintain **potentials** π: V → R.

The **reduced cost** of edge (u, v) is:
```
w_π(u, v) = w(u, v) + π(u) - π(v)
```

**Key property**: If potentials satisfy the reduced cost optimality condition (w_π(e) ≥ 0 for all residual edges), then Dijkstra can find shortest paths.

**Updating potentials**: After finding shortest distances d(v) from s, update:
```
π(v) ← π(v) + d(v)
```

This maintains non-negative reduced costs for future iterations.

## 5. Algorithms

### 5.1 Successive Shortest Path (SSP) Algorithm

The most common MCMF algorithm:

```
SuccessiveShortestPath(G, s, t, D):
    Initialize flow f = 0, total_cost = 0
    Initialize potentials π = 0  (or compute via Bellman-Ford)
    
    while flow < D:
        Find shortest path P from s to t in residual graph Gf
            using reduced costs w_π (Dijkstra with potentials)
        if no path exists: break  (max flow reached)
        
        Augment flow along P by bottleneck capacity
        Update total_cost
        Update potentials: π(v) += dist(v)
    
    return (flow, total_cost)
```

**Time**: O(D · (E log V)) with Dijkstra, or O(D · V · E) with Bellman-Ford.

For MCMF (D = max flow), D can be up to the sum of capacities.

### 5.2 SPFA-Based Augmenting (Shortest Path Faster Algorithm)

Use SPFA (a Bellman-Ford variant using a queue) to find shortest paths:

```
SPFA_MCMF(G, s, t):
    while SPFA finds shortest path from s to t in Gf:
        Augment along this path
    return (flow, cost)
```

**Advantage**: Simpler to implement, handles negative edges directly.
**Disadvantage**: Worst case O(V · E · max_flow), but often fast in practice.

### 5.3 Cycle-Cancelling Algorithm

Start with any max-flow (ignoring cost), then repeatedly cancel negative-cost cycles:

```
CycleCancelling(G, s, t):
    Find any max-flow f (e.g., using Edmonds-Karp)
    while Gf has a negative-cost cycle C:
        Push flow around C by bottleneck residual capacity
    return f
```

**Time**: O(E · max_flow) for cycle detection, potentially slow.

### 5.4 Minimum Mean Cycle-Cancelling

A refinement: always cancel the cycle with minimum mean cost.

**Time**: O(V · E · log(V) · log(V · C)) where C is max capacity.

### 5.5 Cost-Scaling Algorithm

Advanced algorithm that scales costs similarly to capacity-scaling in max-flow.

**Time**: O(V² · E · log(V · C)) — near-optimal for dense graphs.

### 5.6 Network Simplex

The practical method of choice for large-scale problems. Based on the simplex method for LP, specialized for network structure.

**Time**: Excellent in practice, polynomial with certain pivot rules.

## 6. Step-by-Step Walkthrough

### Example: 4-Node Network

```
         2/3         3/2
    s --------→ a --------→ t
    |            ↑            ↑
    |  4/1       | 1/2        |
    ↓            |            |
    b --------→ c --------→ d
         1/4         2/1
```

Format: capacity/cost. Let me rewrite clearly:

```
Edges:
s → a: cap=2, cost=3
s → b: cap=4, cost=1
a → t: cap=3, cost=2
b → c: cap=1, cost=4
c → a: cap=2, cost=1  (backward edge in original? No, let me make it a forward edge)
c → d: cap=1, cost=2
d → t: cap=2, cost=1
```

Wait, let me use a cleaner example.

### Clean Example

```
Graph:
s → a (cap=3, cost=1)
s → b (cap=2, cost=5)
a → b (cap=2, cost=1)
a → t (cap=2, cost=2)
b → t (cap=3, cost=1)
```

**Step 1: First augmenting path**

Initial potentials: π = [0, 0, 0, 0] for {s, a, b, t}

Shortest path from s to t (using original costs since π=0):
- s → a → t: cost 1+2 = 3
- s → a → b → t: cost 1+1+1 = 3
- s → b → t: cost 5+1 = 6

Both paths cost 3. Choose s → a → t (bottleneck = min(3, 2) = 2).

Augment 2 units along s → a → t. Cost: 2 × 3 = 6.

Flow: 2. Residual graph:
- s → a: cap=1, cost=1
- a → s: cap=2, cost=-1
- a → t: cap=0, cost=2
- t → a: cap=2, cost=-2
- s → b: cap=2, cost=5
- a → b: cap=2, cost=1
- b → t: cap=3, cost=1

**Step 2: Second augmenting path**

Update potentials: dist = [0, 1, 2, 3] (from s). π = [0, 1, 2, 3].

Reduced costs:
- s → a: 1 + 0 - 1 = 0 ✓
- a → s: -1 + 1 - 0 = 0 ✓
- s → b: 5 + 0 - 2 = 3 ✓
- a → b: 1 + 1 - 2 = 0 ✓
- b → t: 1 + 2 - 3 = 0 ✓
- t → a: -2 + 3 - 1 = 0 ✓

Shortest path in reduced costs: s → a → b → t (cost 0+0+0 = 0).

Actual cost: 1 + 1 + 1 = 3. Bottleneck = min(1, 2, 3) = 1.

Augment 1 unit. Cost: 1 × 3 = 3. Total cost: 6 + 3 = 9.

Flow: 3. Residual:
- s → a: cap=0
- a → s: cap=3
- a → b: cap=1
- b → a: cap=1
- b → t: cap=2
- t → b: cap=1
- s → b: cap=2

**Step 3: Third augmenting path**

Update potentials. dist from s: s=0, a=∞ (edge s→a saturated), b=5 (s→b), t=6 (s→b→t).

Wait, a is reachable via s→b→a? No, the edge is a→b, not b→a in original. But in residual, b→a exists with cap=1 (from the flow we pushed).

Let me retrace. After step 2:
Residual edges from s: s→a (cap=0, cost=1), s→b (cap=2, cost=5)
Residual edges from a: a→s (cap=3, cost=-1), a→b (cap=1, cost=1), a→t (cap=0, cost=2)
Residual edges from b: b→a (cap=1, cost=-1), b→t (cap=2, cost=1), b→s (cap=0, cost=-5)
Residual edges from t: t→a (cap=2, cost=-2), t→b (cap=1, cost=-1)

Shortest path: s → b → t. Cost: 5 + 1 = 6. Bottleneck = min(2, 2) = 2.

Augment 2 units. Cost: 2 × 6 = 12. Total cost: 9 + 12 = 21.

Flow: 5. Is this max flow? s can send at most 3+2=5 units, t can receive 2+3=5 units. Yes, 5 is max flow.

**Final answer**: Max flow = 5, Min cost = 21.

**Verification**: 
- Path s→a→t: 2 units × 3 = 6
- Path s→a→b→t: 1 unit × 3 = 3
- Path s→b→t: 2 units × 6 = 12
- Total: 2 + 1 + 2 = 5 flow, 6 + 3 + 12 = 21 cost ✓

## 7. Complexity Analysis

| Algorithm | Time Complexity | Notes |
|---|---|---|
| SSP + Bellman-Ford | O(V · E · D) | D = flow value |
| SSP + Dijkstra | O(E · log V · D) | With potentials |
| SPFA-based | O(V · E · D) | Fast in practice |
| Cycle cancelling | O(E² · log V · log(V·C)) | Start with any max-flow |
| Min-mean cycle | O(V · E · log V · log(V·C)) | Polynomial |
| Cost scaling | O(V² · E · log(V·C)) | Near-optimal |
| Network Simplex | Excellent in practice | Industry standard |

Where D = max flow value, C = max capacity, V = vertices, E = edges.

## 8. Code

### 8.1 C++ — Successive Shortest Path with Dijkstra + Potentials

```cpp
#include <bits/stdc++.h>
using namespace std;

struct MCMF {
    struct Edge {
        int to, cap, cost, flow;
    };
    
    int n;
    vector<Edge> edges;
    vector<vector<int>> adj;
    vector<int> dist, pot, par;
    
    MCMF(int n) : n(n), adj(n), dist(n), pot(n), par(n) {}
    
    void add_edge(int u, int v, int cap, int cost) {
        adj[u].push_back(edges.size());
        edges.push_back({v, cap, cost, 0});
        adj[v].push_back(edges.size());
        edges.push_back({u, 0, -cost, 0});
    }
    
    bool dijkstra(int s, int t) {
        fill(dist.begin(), dist.end(), INT_MAX);
        dist[s] = 0;
        priority_queue<pair<int,int>, vector<pair<int,int>>, greater<>> pq;
        pq.push({0, s});
        
        while (!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if (d > dist[u]) continue;
            for (int idx : adj[u]) {
                auto& e = edges[idx];
                int v = e.to;
                int nd = d + e.cost + pot[u] - pot[v];
                if (e.cap - e.flow > 0 && nd < dist[v]) {
                    dist[v] = nd;
                    par[v] = idx;
                    pq.push({nd, v});
                }
            }
        }
        
        // Update potentials
        for (int i = 0; i < n; i++)
            if (dist[i] < INT_MAX) pot[i] += dist[i];
        
        return dist[t] < INT_MAX;
    }
    
    pair<int, int> solve(int s, int t) {
        int total_flow = 0, total_cost = 0;
        
        // Optional: initial potentials via Bellman-Ford
        // (needed only if negative-cost edges exist initially)
        
        while (dijkstra(s, t)) {
            // Find bottleneck
            int bottleneck = INT_MAX;
            for (int v = t; v != s; v = edges[par[v] ^ 1].to)
                bottleneck = min(bottleneck, edges[par[v]].cap - edges[par[v]].flow);
            
            // Augment
            for (int v = t; v != s; v = edges[par[v] ^ 1].to) {
                edges[par[v]].flow += bottleneck;
                edges[par[v] ^ 1].flow -= bottleneck;
                total_cost += bottleneck * edges[par[v]].cost;
            }
            
            total_flow += bottleneck;
        }
        
        return {total_flow, total_cost};
    }
};

int main() {
    MCMF mcmf(4);  // s=0, a=1, b=2, t=3
    
    mcmf.add_edge(0, 1, 3, 1);  // s→a
    mcmf.add_edge(0, 2, 2, 5);  // s→b
    mcmf.add_edge(1, 2, 2, 1);  // a→b
    mcmf.add_edge(1, 3, 2, 2);  // a→t
    mcmf.add_edge(2, 3, 3, 1);  // b→t
    
    auto [flow, cost] = mcmf.solve(0, 3);
    cout << "Max flow: " << flow << ", Min cost: " << cost << endl;
    // Output: Max flow: 5, Min cost: 21
    return 0;
}
```

### 8.2 C++ — SPFA-Based (Simpler Implementation)

```cpp
#include <bits/stdc++.h>
using namespace std;

struct MCMF_SPFA {
    struct Edge { int to, cap, cost, flow; };
    
    int n;
    vector<Edge> edges;
    vector<vector<int>> adj;
    vector<int> dist, par;
    vector<bool> in_queue;
    
    MCMF_SPFA(int n) : n(n), adj(n), dist(n), par(n), in_queue(n) {}
    
    void add_edge(int u, int v, int cap, int cost) {
        adj[u].push_back(edges.size());
        edges.push_back({v, cap, cost, 0});
        adj[v].push_back(edges.size());
        edges.push_back({u, 0, -cost, 0});
    }
    
    bool spfa(int s, int t) {
        fill(dist.begin(), dist.end(), INT_MAX);
        fill(in_queue.begin(), in_queue.end(), false);
        dist[s] = 0;
        
        queue<int> q;
        q.push(s);
        in_queue[s] = true;
        
        while (!q.empty()) {
            int u = q.front(); q.pop();
            in_queue[u] = false;
            
            for (int idx : adj[u]) {
                auto& e = edges[idx];
                if (e.cap - e.flow > 0 && dist[u] + e.cost < dist[e.to]) {
                    dist[e.to] = dist[u] + e.cost;
                    par[e.to] = idx;
                    if (!in_queue[e.to]) {
                        q.push(e.to);
                        in_queue[e.to] = true;
                    }
                }
            }
        }
        return dist[t] < INT_MAX;
    }
    
    pair<int, int> solve(int s, int t) {
        int total_flow = 0, total_cost = 0;
        
        while (spfa(s, t)) {
            int bottleneck = INT_MAX;
            for (int v = t; v != s; v = edges[par[v] ^ 1].to)
                bottleneck = min(bottleneck, edges[par[v]].cap - edges[par[v]].flow);
            
            for (int v = t; v != s; v = edges[par[v] ^ 1].to) {
                edges[par[v]].flow += bottleneck;
                edges[par[v] ^ 1].flow -= bottleneck;
                total_cost += bottleneck * edges[par[v]].cost;
            }
            total_flow += bottleneck;
        }
        return {total_flow, total_cost};
    }
};
```

### 8.3 C++ — Min-Cost Flow with Specified Demand

```cpp
// Solve min-cost flow with demand D (not necessarily max flow)
pair<int, int> solve_with_demand(int s, int t, int D) {
    int total_flow = 0, total_cost = 0;
    
    while (total_flow < D && dijkstra(s, t)) {
        int bottleneck = INT_MAX;
        for (int v = t; v != s; v = edges[par[v] ^ 1].to)
            bottleneck = min(bottleneck, edges[par[v]].cap - edges[par[v]].flow);
        
        bottleneck = min(bottleneck, D - total_flow);
        
        for (int v = t; v != s; v = edges[par[v] ^ 1].to) {
            edges[par[v]].flow += bottleneck;
            edges[par[v] ^ 1].flow -= bottleneck;
            total_cost += bottleneck * edges[par[v]].cost;
        }
        total_flow += bottleneck;
    }
    
    if (total_flow < D) return {-1, -1};  // Cannot satisfy demand
    return {total_flow, total_cost};
}
```

### 8.4 Python — MCMF with SPFA

```python
from collections import deque
import sys

class MCMF:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]
        self.edges = []
    
    def add_edge(self, u, v, cap, cost):
        # Forward edge
        self.adj[u].append(len(self.edges))
        self.edges.append([v, cap, cost, 0])  # [to, cap, cost, flow]
        # Backward edge
        self.adj[v].append(len(self.edges))
        self.edges.append([u, 0, -cost, 0])
    
    def solve(self, s, t):
        total_flow = 0
        total_cost = 0
        
        while True:
            # SPFA to find shortest path
            dist = [float('inf')] * self.n
            par = [-1] * self.n
            in_queue = [False] * self.n
            dist[s] = 0
            
            queue = deque([s])
            in_queue[s] = True
            
            while queue:
                u = queue.popleft()
                in_queue[u] = False
                for idx in self.adj[u]:
                    e = self.edges[idx]
                    if e[1] - e[3] > 0 and dist[u] + e[2] < dist[e[0]]:
                        dist[e[0]] = dist[u] + e[2]
                        par[e[0]] = idx
                        if not in_queue[e[0]]:
                            queue.append(e[0])
                            in_queue[e[0]] = True
            
            if dist[t] == float('inf'):
                break  # No augmenting path
            
            # Find bottleneck
            bottleneck = float('inf')
            v = t
            while v != s:
                idx = par[v]
                bottleneck = min(bottleneck, self.edges[idx][1] - self.edges[idx][3])
                v = self.edges[idx ^ 1][0]
            
            # Augment
            v = t
            while v != s:
                idx = par[v]
                self.edges[idx][3] += bottleneck
                self.edges[idx ^ 1][3] -= bottleneck
                total_cost += bottleneck * self.edges[idx][2]
                v = self.edges[idx ^ 1][0]
            
            total_flow += bottleneck
        
        return total_flow, total_cost


# Example
mcmf = MCMF(4)  # s=0, a=1, b=2, t=3
mcmf.add_edge(0, 1, 3, 1)   # s→a
mcmf.add_edge(0, 2, 2, 5)   # s→b
mcmf.add_edge(1, 2, 2, 1)   # a→b
mcmf.add_edge(1, 3, 2, 2)   # a→t
mcmf.add_edge(2, 3, 3, 1)   # b→t

flow, cost = mcmf.solve(0, 3)
print(f"Max flow: {flow}, Min cost: {cost}")
# Output: Max flow: 5, Min cost: 21
```

### 8.5 Python — MCMF with Dijkstra + Potentials

```python
import heapq

class MCMF_Dijkstra:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]
        self.edges = []
    
    def add_edge(self, u, v, cap, cost):
        self.adj[u].append(len(self.edges))
        self.edges.append([v, cap, cost, 0])
        self.adj[v].append(len(self.edges))
        self.edges.append([u, 0, -cost, 0])
    
    def solve(self, s, t):
        total_flow = 0
        total_cost = 0
        pot = [0] * self.n  # potentials
        
        while True:
            # Dijkstra with reduced costs
            dist = [float('inf')] * self.n
            par = [-1] * self.n
            dist[s] = 0
            pq = [(0, s)]
            
            while pq:
                d, u = heapq.heappop(pq)
                if d > dist[u]:
                    continue
                for idx in self.adj[u]:
                    e = self.edges[idx]
                    nd = d + e[2] + pot[u] - pot[e[0]]
                    if e[1] - e[3] > 0 and nd < dist[e[0]]:
                        dist[e[0]] = nd
                        par[e[0]] = idx
                        heapq.heappush(pq, (nd, e[0]))
            
            if dist[t] == float('inf'):
                break
            
            # Update potentials
            for i in range(self.n):
                if dist[i] < float('inf'):
                    pot[i] += dist[i]
            
            # Find bottleneck and augment
            bottleneck = float('inf')
            v = t
            while v != s:
                idx = par[v]
                bottleneck = min(bottleneck, self.edges[idx][1] - self.edges[idx][3])
                v = self.edges[idx ^ 1][0]
            
            v = t
            while v != s:
                idx = par[v]
                self.edges[idx][3] += bottleneck
                self.edges[idx ^ 1][3] -= bottleneck
                total_cost += bottleneck * self.edges[idx][2]
                v = self.edges[idx ^ 1][0]
            
            total_flow += bottleneck
        
        return total_flow, total_cost
```

### 8.6 Java — MCMF with SPFA

```java
import java.util.*;

public class MCMF {
    static class Edge {
        int to, cap, cost, flow;
        Edge(int to, int cap, int cost) {
            this.to = to; this.cap = cap; this.cost = cost; this.flow = 0;
        }
    }
    
    int n;
    List<Edge> edges = new ArrayList<>();
    List<List<Integer>> adj;
    
    public MCMF(int n) {
        this.n = n;
        adj = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
    }
    
    void addEdge(int u, int v, int cap, int cost) {
        adj.get(u).add(edges.size());
        edges.add(new Edge(v, cap, cost));
        adj.get(v).add(edges.size());
        edges.add(new Edge(u, 0, -cost));
    }
    
    int[] solve(int s, int t) {
        int totalFlow = 0, totalCost = 0;
        int[] dist = new int[n], par = new int[n];
        boolean[] inQueue = new boolean[n];
        
        while (true) {
            Arrays.fill(dist, Integer.MAX_VALUE);
            dist[s] = 0;
            Queue<Integer> queue = new ArrayDeque<>();
            queue.add(s);
            inQueue[s] = true;
            
            while (!queue.isEmpty()) {
                int u = queue.poll();
                inQueue[u] = false;
                for (int idx : adj.get(u)) {
                    Edge e = edges.get(idx);
                    if (e.cap - e.flow > 0 && dist[u] + e.cost < dist[e.to]) {
                        dist[e.to] = dist[u] + e.cost;
                        par[e.to] = idx;
                        if (!inQueue[e.to]) {
                            queue.add(e.to);
                            inQueue[e.to] = true;
                        }
                    }
                }
            }
            
            if (dist[t] == Integer.MAX_VALUE) break;
            
            int bottleneck = Integer.MAX_VALUE;
            for (int v = t; v != s; v = edges.get(par[v] ^ 1).to)
                bottleneck = Math.min(bottleneck, edges.get(par[v]).cap - edges.get(par[v]).flow);
            
            for (int v = t; v != s; v = edges.get(par[v] ^ 1).to) {
                edges.get(par[v]).flow += bottleneck;
                edges.get(par[v] ^ 1).flow -= bottleneck;
                totalCost += bottleneck * edges.get(par[v]).cost;
            }
            totalFlow += bottleneck;
        }
        
        return new int[]{totalFlow, totalCost};
    }
    
    public static void main(String[] args) {
        MCMF mcmf = new MCMF(4);
        mcmf.addEdge(0, 1, 3, 1);
        mcmf.addEdge(0, 2, 2, 5);
        mcmf.addEdge(1, 2, 2, 1);
        mcmf.addEdge(1, 3, 2, 2);
        mcmf.addEdge(2, 3, 3, 1);
        
        int[] result = mcmf.solve(0, 3);
        System.out.printf("Max flow: %d, Min cost: %d%n", result[0], result[1]);
        // Output: Max flow: 5, Min cost: 21
    }
}
```

## 9. Applications

### 9.1 Assignment Problem

n workers, n jobs. Worker i doing job j costs c[i][j]. Assign each worker to exactly one job minimizing total cost.

**Model**: Bipartite graph. Source → workers (cap=1, cost=0). Workers → jobs (cap=1, cost=c[i][j]). Jobs → sink (cap=1, cost=0).

MCMF gives the optimal assignment. Equivalent to the Hungarian algorithm.

### 9.2 Minimum Cost Circulation

Given a graph with demands at each node (positive = supply, negative = demand), find minimum cost flow satisfying all demands.

**Model**: Add super-source s and super-tink t. Connect s to supply nodes, demand nodes to t. Run MCMF.

### 9.3 Transportation Problem

Multiple warehouses (with supply) and stores (with demand). Shipping cost per unit varies by route. Find minimum cost shipping plan.

### 9.4 Network Design

Choose which edges to include in a network, subject to capacity and connectivity constraints, minimizing total cost.

### 9.5 Image Segmentation (Graph Cut)

In computer vision, min-cost flow (via min-cut) segments images. Pixels are nodes; edges represent similarity. The min-cut separates foreground from background.

### 9.6 Bipartite Matching with Costs

Generalized matching where each match has a cost. Find minimum-cost maximum matching.

## 10. Cycle-Cancelling Algorithm Detail

The cycle-cancelling approach is conceptually clean:

1. **Phase 1**: Find any max-flow (ignoring cost). Use Edmonds-Karp, Dinic, etc.
2. **Phase 2**: In the residual graph, find negative-cost cycles and cancel them.

```
CycleCancelling(G):
    f = MaxFlow(G)  // any max-flow algorithm
    while exists negative-cost cycle C in Gf:
        Δ = min residual capacity on C
        for each edge e in C:
            if e is forward: f(e) += Δ
            else: f(e) -= Δ  // e is backward in original
    return f
```

**Finding negative cycles**: Use Bellman-Ford. If after V-1 relaxations, an edge can still be relaxed, there's a negative cycle. Trace back to find the cycle.

**Time**: Each cancellation reduces cost. If costs are integers, each cancellation reduces cost by at least 1. Starting cost ≤ E × max_capacity × max_cost, so at most O(E · C · W) cancellations.

## 11. Handling Negative Edges

### Initial Negative Costs

If the original graph has edges with negative cost, the initial potentials can't be all zeros (Dijkstra requires non-negative reduced costs).

**Solution**: Run Bellman-Ford from source to compute initial potentials:
```
π(v) = shortest distance from s to v in the original graph
```

This ensures all reduced costs are non-negative.

### Negative Cycles in Original Graph

If the original graph has negative cycles, the min-cost flow problem may be unbounded (infinite profit). Detect this during Bellman-Ford initialization.

## 12. Common Pitfalls

1. **Forgetting backward edge costs**: Backward edges have NEGATIVE cost. Missing the sign gives wrong results.

2. **Not updating potentials**: Without potentials, Dijkstra can't handle the negative costs on backward edges. Always maintain and update potentials.

3. **Integer overflow**: Costs can be large. Use long long for total cost computation.

4. **Wrong edge indexing**: The XOR trick for finding reverse edges (idx ^ 1) requires edges to be added in pairs. Don't interleave add_edge calls.

5. **Confusing max-flow with min-cost flow**: MCMF minimizes cost among max-flows. Min-cost flow with demand D minimizes cost for exactly D flow. Make sure you're solving the right problem.

6. **SPFA worst case**: SPFA can be very slow on adversarial graphs. Use Dijkstra + potentials for competitive programming when the graph might be adversarial.

## 13. Exercises

1. **Basic**: Given a 3×3 cost matrix for the assignment problem, set up the MCMF network and solve manually.

2. **Medium**: Modify the MCMF solver to handle the case where edges have both a lower bound and upper bound on flow.

3. **Hard**: Given a graph with node demands (positive = supply, negative = demand), find the minimum cost circulation. Reduce to MCMF.

4. **Challenge**: Implement the cycle-cancelling algorithm. Compare its performance with SSP on random graphs.

5. **Challenge**: Solve the following problem: Given n cities and m roads (each with capacity and cost), find the minimum cost to send D units of goods from city 1 to city n.

## 14. Interview Questions

1. **Q**: What is the difference between max-flow and min-cost max-flow?
   **A**: Max-flow maximizes total flow from s to t. Min-cost max-flow first maximizes flow, then among all max-flows, finds the one with minimum total cost.

2. **Q**: Why do backward edges have negative cost?
   **A**: Sending flow on a backward edge means "undoing" previously sent flow. If we originally paid cost w to send flow forward, undoing it should refund that cost, hence -w.

3. **Q**: Why can't we use Dijkstra directly in MCMF?
   **A**: Dijkstra requires non-negative edge weights. Backward edges in the residual graph have negative costs. Potentials (Johnson's technique) transform costs to be non-negative.

4. **Q**: How does MCMF relate to the assignment problem?
   **A**: The assignment problem (min-cost bipartite matching) is a special case of MCMF on a bipartite graph where all capacities are 1.

5. **Q**: What's the time complexity of MCMF using successive shortest paths with Dijkstra?
   **A**: O(D · E · log V) where D is the maximum flow value, E is the number of edges, V is the number of vertices.

## 15. Comparison of Algorithms

| Feature | SSP + Dijkstra | SPFA-based | Cycle Cancelling |
|---|---|---|---|
| Implementation | Moderate | Simple | Complex |
| Negative initial edges | Need Bellman-Ford init | Handles directly | Handles directly |
| Worst case | O(D · E · log V) | O(V · E · D) | O(E² · W · C) |
| Practice | Fast | Usually fast | Can be slow |
| Best for | Large graphs, small D | Small-medium graphs | Conceptual clarity |

## 16. Cross-References

- **Chapter 29: Network Flow** — Max-flow foundations (Ford-Fulkerson, Edmonds-Karp, Dinic)
- **Chapter 83: Advanced Network Flow** — Min-cut, multi-commodity flow
- **Chapter 26: Shortest Paths** — Dijkstra, Bellman-Ford, SPFA
- **Chapter 27: Minimum Spanning Trees** — Related graph optimization
- **Chapter 112: Hopcroft-Karp and Blossom** — Matching algorithms
- **Chapter 151: Linear Programming** — LP formulation of network flow

## 17. Further Reading

- [CP-Algorithms: MCMF](https://cp-algorithms.com/graph/min_cost_flow.html)
- *Introduction to Algorithms* (CLRS), Chapter 24 — Single-Source Shortest Paths, Chapter 26 — Maximum Flow
- *Network Flows* by Ahuja, Magnanti, Orlin — Comprehensive reference
- "Competitive Programming 3" by Steven Halim — MCMF section
- ZKW MCMF — A popular competitive programming implementation using Dijkstra with potentials
