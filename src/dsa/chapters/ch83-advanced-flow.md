# Chapter 83: Advanced Network Flow

## Prerequisites
- Max flow basics (Ford-Fulkerson, Edmonds-Karp)
- Graph fundamentals ([Chapter 22](ch22-graph-fundamentals.md))

## Interview Frequency: ★★

Advanced flow algorithms appear in **Google** and competitive programming interviews for hard optimization problems.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Dinic's Algorithm | ★★★ | Hard | O(V²E) max flow |
| Push-Relabel | ★★ | Hard | O(V³) max flow |
| Min-Cut applications | ★★★ | Medium | Network reliability |
| Bipartite Matching | ★★★ | Medium | Via max flow |

---

## Motivation

### Why Edmonds-Karp Isn't Enough

Edmonds-Karp (BFS-based Ford-Fulkerson) finds **one** shortest augmenting path per iteration and runs in O(VE²). Consider a dense network with V = 1000 and E = 500,000:

- Edmonds-Karp: O(VE²) = O(1000 × 500,000²) — **astronomically slow**
- Dinic's: O(V²E) = O(1000² × 500,000) — **orders of magnitude faster**

The bottleneck of Edmonds-Karp is that it **rebuilds BFS from scratch** for every single augmenting path, even when many paths share the same BFS level structure. Dinic's exploits this by finding an entire *blocking flow* (a maximal set of edge-disjoint shortest paths) in one BFS phase.

### When to Reach for Advanced Flow

| Scenario | Best Choice |
|---|---|
| Small graph, simple problem | Edmonds-Karp |
| Sparse graph, competitive programming | Dinic's |
| Dense graph, implementation-heavy | Push-Relabel |
| Unit capacity networks (matching) | Dinic's — O(E√V) |
| Need min-cut partition | Either (both compute it) |

### Real-World Motivation

Advanced flow algorithms power:
- **Network routing**: Optimal bandwidth allocation across ISP backbones
- **Image segmentation**: Separating foreground from background in computer vision
- **Supply chain**: Minimizing cost while meeting demand across warehouses
- **Sports analytics**: Determining if a team is mathematically eliminated

---

## Intuition

### Dinic's Algorithm — The Layered Approach

Think of Dinic's as **building a highway system**:

```
Source (S)                          Sink (T)
  │                                   ▲
  ▼ Level 0                     Level 3│
  ┌───┐      ┌───┐      ┌───┐    ┌───┐
  │ S │ ───► │ A │ ───► │ D │ ──►│ T │
  └───┘      └───┘      └───┘    └───┘
    │          ▲          ▲
    ▼ Level 1  │Level 2   │
  ┌───┐      ┌───┐      ┌───┐
  │ B │ ───► │ C │ ───► │ E │
  └───┘      └───┘      └───┘
```

1. **BFS assigns levels**: Every node gets its shortest distance from source. This creates a "layered graph."
2. **DFS finds blocking flow**: Within the layered graph, push as much flow as possible using only forward-level edges. Once no more flow can be pushed, the level graph is "blocked."
3. **Rebuild and repeat**: Some edges are now saturated. Rebuild BFS levels and find the next blocking flow.

**Key insight**: Each BFS phase increases the shortest augmenting path length. Since the max distance is V-1, there are at most V BFS phases. Each phase does O(VE) work → O(V²E) total.

### Push-Relabel — The Water Tank Analogy

Imagine each node is a **water tank** at a certain height:

```
Height 3:  [S]                   (Source — highest point, h[S] = |V|)
Height 2:    [A] [C]
Height 1:       [D] [E]
Height 0:          [T]           (Sink — lowest point, h[T] = 0)
```

- **Push**: Water flows from taller tanks to shorter tanks (higher height to lower height)
- **Relabel**: If a tank has excess water but all neighbors are same height or taller, raise the tank's height so water can flow downhill
- Water eventually accumulates at the sink

**Key insight**: Unlike Dinic's (which is BFS-based), Push-Relabel operates **locally** on individual nodes, making it more cache-friendly for dense graphs.

---

## Formal Explanation

### Correctness of Dinic's Algorithm

**Theorem**: Dinic's algorithm correctly computes the maximum flow.

**Proof sketch**:

1. **Termination**: Each BFS phase increases the distance from source to sink in the residual graph (by construction, since we only use edges at the next level). Since the maximum distance is V-1, there are at most V phases. Each phase terminates because the blocking flow DFS makes progress (it either pushes flow or marks edges as unusable).

2. **Optimality**: When the algorithm terminates, the sink is not reachable from the source in the residual graph. By the max-flow min-cut theorem, the current flow is maximum. Equivalently, we can extract a min-cut from the final BFS: the set of reachable nodes from S forms one side of the cut.

3. **Complexity**: Each BFS phase runs in O(E). The DFS blocking flow takes O(VE) per phase (each edge is traversed at most once per phase thanks to the pointer array `ptr`). With O(V) phases, total: O(V · VE) = O(V²E).

**Unit network special case**: When all capacities are 1 (e.g., bipartite matching), Dinic's runs in O(E√V). This is because each blocking flow increases the source-sink distance, and with unit capacities, the number of phases is bounded by O(√V).

---

## 83.1 Dinic's Algorithm

### Algorithm

1. **BFS**: Build level graph (distance from source)
2. **DFS**: Find blocking flow (max set of shortest augmenting paths)
3. Repeat until no more augmenting paths

### Step-by-Step Walkthrough

Let's trace Dinic's on this small network (source = 0, sink = 5):

```
      10        10
  0 ────► 1 ────► 3
  │        │       │ 10
  │ 10     │ 1     ▼
  ▼        ▼       5
  2 ────► 4 ────►┘
      10       10
```

Edges: 0→1 (10), 0→2 (10), 1→3 (10), 1→4 (1), 2→4 (10), 3→5 (10), 4→5 (10)

**Phase 1 — BFS:**
```
Level 0: {0}
Level 1: {1, 2}   (edges 0→1, 0→2)
Level 2: {3, 4}   (edges 1→3, 1→4, 2→4)
Level 3: {5}      (edges 3→5, 4→5)
```
Sink reachable → proceed.

**Phase 1 — DFS blocking flow:**
- Path 0→1→3→5: min(10,10,10) = 10. Push 10. Saturates 0→1, 1→3, 3→5.
- Path 0→2→4→5: min(10,10,10) = 10. Push 10. Saturates 0→2, 2→4, 4→5.
- No more augmenting paths in level graph. **Blocking flow = 20.**

**Phase 2 — BFS:**
All edges from 0 are saturated. Sink not reachable from source. **Algorithm terminates.**

**Result: Max flow = 20.**

**Min-cut**: Source-side reachable set = {0}. Cut edges: 0→1 and 0→2, total capacity = 20. ✓

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <climits>

struct Edge { int to, cap, flow; };

class Dinic {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<Edge> edges;
    std::vector<int> level, ptr;

    bool bfs(int s, int t) {
        std::fill(level.begin(), level.end(), -1);
        level[s] = 0;
        std::queue<int> q;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int idx : adj[u]) {
                auto& e = edges[idx];
                if (e.cap - e.flow > 0 && level[e.to] == -1) {
                    level[e.to] = level[u] + 1;
                    q.push(e.to);
                }
            }
        }
        return level[t] != -1;
    }

    int dfs(int u, int t, int pushed) {
        if (u == t || pushed == 0) return pushed;
        for (int& cid = ptr[u]; cid < (int)adj[u].size(); cid++) {
            int idx = adj[u][cid];
            auto& e = edges[idx];
            if (level[e.to] != level[u] + 1) continue;
            int tr = dfs(e.to, t, std::min(pushed, e.cap - e.flow));
            if (tr == 0) continue;
            e.flow += tr;
            edges[idx ^ 1].flow -= tr;
            return tr;
        }
        return 0;
    }

public:
    Dinic(int n) : n(n), adj(n), level(n), ptr(n) {}

    void addEdge(int u, int v, int cap) {
        adj[u].push_back(edges.size());
        edges.push_back({v, cap, 0});
        adj[v].push_back(edges.size());
        edges.push_back({u, 0, 0});
    }

    int maxFlow(int s, int t) {
        int flow = 0;
        while (bfs(s, t)) {
            std::fill(ptr.begin(), ptr.end(), 0);
            while (int pushed = dfs(s, t, INT_MAX))
                flow += pushed;
        }
        return flow;
    }

    std::vector<std::pair<int,int>> minCut(int s) {
        std::vector<bool> reachable(n, false);
        std::queue<int> q;
        q.push(s); reachable[s] = true;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int idx : adj[u]) {
                auto& e = edges[idx];
                if (e.cap - e.flow > 0 && !reachable[e.to]) {
                    reachable[e.to] = true;
                    q.push(e.to);
                }
            }
        }
        std::vector<std::pair<int,int>> cut;
        for (int u = 0; u < n; u++)
            if (reachable[u])
                for (int idx : adj[u])
                    if (!reachable[edges[idx].to] && edges[idx].cap > 0)
                        cut.push_back({u, edges[idx].to});
        return cut;
    }
};

int main() {
    Dinic mf(6);
    mf.addEdge(0, 1, 16); mf.addEdge(0, 2, 13);
    mf.addEdge(1, 2, 10); mf.addEdge(1, 3, 12);
    mf.addEdge(2, 1, 4);  mf.addEdge(2, 4, 14);
    mf.addEdge(3, 2, 9);  mf.addEdge(3, 5, 20);
    mf.addEdge(4, 3, 7);  mf.addEdge(4, 5, 4);

    std::cout << "Max flow: " << mf.maxFlow(0, 5) << "\n";

    auto cut = mf.minCut(0);
    std::cout << "Min cut edges:\n";
    for (auto& [u, v] : cut)
        std::cout << "  " << u << " -> " << v << "\n";

    return 0;
}
```

### Python Implementation

```python
from collections import deque

class Dinic:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]
        self.edges = []

    def add_edge(self, u, v, cap):
        self.adj[u].append(len(self.edges))
        self.edges.append([v, cap, 0])
        self.adj[v].append(len(self.edges))
        self.edges.append([u, 0, 0])

    def bfs(self, s, t):
        self.level = [-1] * self.n
        self.level[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for idx in self.adj[u]:
                e = self.edges[idx]
                if e[1] - e[2] > 0 and self.level[e[0]] == -1:
                    self.level[e[0]] = self.level[u] + 1
                    q.append(e[0])
        return self.level[t] != -1

    def dfs(self, u, t, pushed):
        if u == t or pushed == 0:
            return pushed
        for i in range(self.ptr[u], len(self.adj[u])):
            self.ptr[u] = i
            idx = self.adj[u][i]
            e = self.edges[idx]
            if self.level[e[0]] != self.level[u] + 1:
                continue
            tr = self.dfs(e[0], t, min(pushed, e[1] - e[2]))
            if tr == 0:
                continue
            e[2] += tr
            self.edges[idx ^ 1][2] -= tr
            return tr
        return 0

    def max_flow(self, s, t):
        flow = 0
        while self.bfs(s, t):
            self.ptr = [0] * self.n
            while pushed := self.dfs(s, t, float('inf')):
                flow += pushed
        return flow

# Example
mf = Dinic(6)
mf.add_edge(0, 1, 16); mf.add_edge(0, 2, 13)
mf.add_edge(1, 2, 10); mf.add_edge(1, 3, 12)
mf.add_edge(2, 1, 4);  mf.add_edge(2, 4, 14)
mf.add_edge(3, 2, 9);  mf.add_edge(3, 5, 20)
mf.add_edge(4, 3, 7);  mf.add_edge(4, 5, 4)
print(f"Max flow: {mf.max_flow(0, 5)}")
```

### Java Implementation

```java
import java.util.*;

public class Dinic {
    static class Edge {
        int to, cap, flow;
        Edge(int to, int cap) { this.to = to; this.cap = cap; this.flow = 0; }
    }

    private int n;
    private List<List<Integer>> adj;
    private List<Edge> edges;
    private int[] level, ptr;

    public Dinic(int n) {
        this.n = n;
        this.adj = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
        this.edges = new ArrayList<>();
        this.level = new int[n];
        this.ptr = new int[n];
    }

    public void addEdge(int u, int v, int cap) {
        adj.get(u).add(edges.size());
        edges.add(new Edge(v, cap));
        adj.get(v).add(edges.size());
        edges.add(new Edge(u, 0));
    }

    private boolean bfs(int s, int t) {
        Arrays.fill(level, -1);
        level[s] = 0;
        Queue<Integer> q = new LinkedList<>();
        q.add(s);
        while (!q.isEmpty()) {
            int u = q.poll();
            for (int idx : adj.get(u)) {
                Edge e = edges.get(idx);
                if (e.cap - e.flow > 0 && level[e.to] == -1) {
                    level[e.to] = level[u] + 1;
                    q.add(e.to);
                }
            }
        }
        return level[t] != -1;
    }

    private int dfs(int u, int t, int pushed) {
        if (u == t || pushed == 0) return pushed;
        for (; ptr[u] < adj.get(u).size(); ptr[u]++) {
            int idx = adj.get(u).get(ptr[u]);
            Edge e = edges.get(idx);
            if (level[e.to] != level[u] + 1) continue;
            int tr = dfs(e.to, t, Math.min(pushed, e.cap - e.flow));
            if (tr == 0) continue;
            e.flow += tr;
            edges.get(idx ^ 1).flow -= tr;
            return tr;
        }
        return 0;
    }

    public int maxFlow(int s, int t) {
        int flow = 0;
        while (bfs(s, t)) {
            Arrays.fill(ptr, 0);
            int pushed;
            while ((pushed = dfs(s, t, Integer.MAX_VALUE)) > 0)
                flow += pushed;
        }
        return flow;
    }

    public static void main(String[] args) {
        Dinic mf = new Dinic(6);
        mf.addEdge(0, 1, 16); mf.addEdge(0, 2, 13);
        mf.addEdge(1, 2, 10); mf.addEdge(1, 3, 12);
        mf.addEdge(2, 1, 4);  mf.addEdge(2, 4, 14);
        mf.addEdge(3, 2, 9);  mf.addEdge(3, 5, 20);
        mf.addEdge(4, 3, 7);  mf.addEdge(4, 5, 4);
        System.out.println("Max flow: " + mf.maxFlow(0, 5));
    }
}
```

### Complexity

| Algorithm | Time | Best For |
|---|---|---|
| Ford-Fulkerson | O(E × max_flow) | Small capacities |
| Edmonds-Karp | O(VE²) | General |
| Dinic | O(V²E) | General, unit networks |
| Push-Relabel | O(V³) | Dense graphs |

---

## 83.2 Push-Relabel Algorithm

### Overview

Push-Relabel takes a fundamentally different approach from augmenting-path algorithms. Instead of finding paths from source to sink, it maintains a **preflow** — a flow where nodes (other than source and sink) may have more incoming flow than outgoing flow (excess).

### Key Concepts

- **Height function**: Each node has a height. Source is at height V, sink at height 0.
- **Excess**: The net incoming flow at a node: `excess(u) = Σ flow_in - Σ flow_out`
- **Push**: Send flow from a node with excess to a neighbor at lower height.
- **Relabel**: If a node has excess but all neighbors are at same or higher height, increase the node's height.

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <climits>

class PushRelabel {
    int n;
    std::vector<std::vector<int>> capacity, flow;
    std::vector<int> height, excess;
    std::queue<int> active;

    void push(int u, int v) {
        int d = std::min(excess[u], capacity[u][v] - flow[u][v]);
        flow[u][v] += d;
        flow[v][u] -= d;
        excess[u] -= d;
        excess[v] += d;
        if (d > 0 && excess[v] == d && v != 0 && v != n - 1)
            active.push(v);
    }

    void relabel(int u) {
        int d = INT_MAX;
        for (int v = 0; v < n; v++) {
            if (capacity[u][v] - flow[u][v] > 0)
                d = std::min(d, height[v]);
        }
        if (d < INT_MAX) height[u] = d + 1;
    }

    void discharge(int u) {
        while (excess[u] > 0) {
            for (int v = 0; v < n && excess[u] > 0; v++) {
                if (capacity[u][v] - flow[u][v] > 0 && height[u] == height[v] + 1)
                    push(u, v);
            }
            if (excess[u] > 0) relabel(u);
        }
    }

public:
    PushRelabel(int n) : n(n), capacity(n, std::vector<int>(n, 0)),
                          flow(n, std::vector<int>(n, 0)),
                          height(n, 0), excess(n, 0) {}

    void addEdge(int u, int v, int cap) {
        capacity[u][v] = cap;
    }

    int maxFlow(int s, int t) {
        height[s] = n;
        excess[s] = INT_MAX;
        for (int v = 0; v < n; v++) {
            if (capacity[s][v] > 0) {
                push(s, v);
            }
        }

        while (!active.empty()) {
            int u = active.front(); active.pop();
            if (u != s && u != t) discharge(u);
        }

        return excess[t];
    }
};

int main() {
    PushRelabel mf(6);
    mf.addEdge(0, 1, 16); mf.addEdge(0, 2, 13);
    mf.addEdge(1, 2, 10); mf.addEdge(1, 3, 12);
    mf.addEdge(2, 1, 4);  mf.addEdge(2, 4, 14);
    mf.addEdge(3, 2, 9);  mf.addEdge(3, 5, 20);
    mf.addEdge(4, 3, 7);  mf.addEdge(4, 5, 4);
    std::cout << "Max flow: " << mf.maxFlow(0, 5) << "\n";
    return 0;
}
```

### How It Works (Step-by-Step)

Using the same 6-node example as Dinic's:

1. **Initialize**: Source (0) gets height = 6 (= V). Push flow from source to neighbors 1 and 2.
2. **Process active nodes**: Node 1 has excess 16, node 2 has excess 13. Both have height 0, so they get relabeled.
3. **Push and relabel cycle**: Nodes push flow toward the sink, relabeling when stuck. Heights increase monotonically.
4. **Termination**: When no active nodes remain (all excess has reached the sink or returned to source), the flow is maximum.

### Complexity

- **Time**: O(V³) with FIFO selection, O(V²√E) with highest-label selection
- **Space**: O(V²) for the adjacency matrix representation

### When to Use Push-Relabel vs. Dinic's

| Criterion | Dinic's | Push-Relabel |
|---|---|---|
| Implementation | Simpler | More complex |
| Sparse graphs | ✅ Better | OK |
| Dense graphs | OK | ✅ Better |
| Unit networks | O(E√V) | O(V³) |
| Min-cut extraction | Easy (BFS) | Requires extra work |
| Cache behavior | BFS phases | Local operations |

---

## 83.3 Applications of Max-Flow/Min-Cut

| Application | Source | Sink | Edge Capacities |
|---|---|---|---|
| Network reliability | Source | Sink | Link capacities |
| Image segmentation | Super-source | Super-sink | Pixel similarities |
| Baseball elimination | Games | Teams | Remaining games |
| Project selection | Source | Sink | Profits/costs |
| Airline scheduling | Source | Sink | Crew availability |
| Bipartite matching | Left nodes | Right nodes | 1 (unit capacity) |

---

## 83.4 Bipartite Matching via Max Flow

```
Source → (all left nodes, cap 1) → (edges, cap 1) → (all right nodes, cap 1) → Sink
Max flow = max matching
```

### Why This Works

Each left node can send at most 1 unit of flow (matched to exactly one right node). Each right node receives at most 1 unit (matched to exactly one left node). The flow conservation at each node enforces the matching constraint.

**Special case**: For bipartite matching, Dinic's achieves O(E√V) — the Hopcroft-Karp bound — because all capacities are 1.

---

## Exercises

1. **Implement Push-Relabel**: Implement the push-relabel algorithm with FIFO selection. Compare with Dinic's on random graphs with varying density.

2. **Image segmentation**: Use min-cut to segment an image into foreground/background. Model pixel similarities as edge capacities.

3. **Baseball elimination**: Given team standings and remaining games, determine if a team can still win the division using max-flow.

4. **Project selection**: Given projects with profits/costs and dependencies, select projects to maximize profit using min-cut.

5. **Maximum bipartite matching**: Given a bipartite graph, find the maximum matching using Dinic's algorithm. Verify that it achieves O(E√V) on unit-capacity networks.

6. **Edge-disjoint paths**: Given a directed graph and two vertices s, t, find the maximum number of edge-disjoint paths from s to t. (Hint: set all capacities to 1.)

7. **Minimum vertex cover (König's theorem)**: Given a bipartite graph, find the minimum vertex cover using max-flow. Relate the result to the maximum matching.

---

## Interview Questions

1. **Q: How does Dinic's algorithm improve over Edmonds-Karp?**
   A: Edmonds-Karp finds one augmenting path per BFS. Dinic's finds a blocking flow (all augmenting paths in the level graph) per BFS. This reduces the number of BFS phases from O(VE) to O(V).

2. **Q: What is a blocking flow?**
   A: A blocking flow is a set of augmenting paths in the level graph such that every path from source to sink in the level graph uses at least one saturated edge. After finding a blocking flow, the level graph must be rebuilt.

3. **Q: When is Push-Relabel faster than Dinic's?**
   A: Push-Relabel is often faster in practice for dense graphs because it doesn't need BFS phases. It processes nodes locally, which is more cache-friendly. Dinic's is better for sparse graphs and unit networks.

4. **Q: How do you extract the min-cut from a max-flow computation?**
   A: After computing max-flow, run BFS/DFS from the source in the residual graph using only edges with residual capacity > 0. The set of reachable nodes forms the source side of the min-cut. Cut edges go from reachable to unreachable nodes.

5. **Q: What is the time complexity of Dinic's on unit-capacity networks and why?**
   A: O(E√V). In unit networks, each blocking flow increases the shortest augmenting path length by at least 1. The number of phases is bounded by O(√V) because after √V phases, the number of remaining augmenting paths is small enough that each phase saturates many edges.

6. **Q: Explain the height invariant in Push-Relabel.**
   A: For every edge (u, v) with residual capacity > 0, height[u] ≤ height[v] + 1. This ensures flow can only be pushed "downhill." When a node has excess and no downhill neighbor, it gets relabeled (height increases) until a push is possible.

---

## See Also

- [Chapter 29: Network Flow](ch29-network-flow.md) — Ford-Fulkerson and Edmonds-Karp foundations
- [Chapter 22: Graph Fundamentals](ch22-graph-fundamentals.md) — BFS and DFS used in level graph construction
- Chapter 30: Bipartite Matching — Hopcroft-Karp and matching theory
- [Chapter 84: Minimum Cost Flow](ch169-min-cost-max-flow.md) — Extending max-flow with costs
- Chapter 85: Linear Programming and Flow — LP duality and flow problems

---

## Summary

| Algorithm | Paradigm | Time | Space | Best For |
|---|---|---|---|---|
| Ford-Fulkerson | Augmenting paths | O(E × max_flow) | O(V + E) | Small capacities |
| Edmonds-Karp | BFS augmenting paths | O(VE²) | O(V + E) | General, simple |
| Dinic's | Level graph + blocking flow | O(V²E) | O(V + E) | Sparse, unit networks |
| Push-Relabel | Preflow + local ops | O(V³) | O(V²) | Dense graphs |

**Key takeaways:**
- Dinic's is the go-to for competitive programming — simple, fast, and handles unit networks beautifully
- Push-Relabel shines on dense graphs and is theoretically elegant
- Both compute max-flow and min-cut simultaneously
- For bipartite matching, Dinic's automatically achieves the optimal O(E√V) bound
