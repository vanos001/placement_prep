# Network Flow: Advanced Techniques

Building on [max-flow fundamentals](../chapters/ch29-network-flow.md) and [Dinic/Push-Relabel](../chapters/ch83-advanced-flow.md), this file covers the frontier of network flow algorithms: min-cost max-flow with advanced implementations, cost-scaling methods, push-relabel optimizations, and Dinic variants with dynamic trees.

---

## Min-Cost Max-Flow: Beyond Successive Shortest Paths

### Problem Statement

Given a flow network $G = (V, E)$ with capacities $c(e) \geq 0$ and costs $w(e)$ per unit flow, find a maximum flow of minimum total cost $\sum_e f(e) \cdot w(e)$. This generalizes both max-flow (set all costs to 0) and shortest path (set all capacities to 1).

### Successive Shortest Path (SSP) Recap

The standard approach augments along shortest (minimum-cost) paths in the residual graph using Bellman-Ford or Dijkstra with potentials. Each augmentation preserves the optimality of potentials (reduced costs remain non-negative).

**Complexity**: $O(F \cdot E \log V)$ with Dijkstra + potentials, where $F$ is the max-flow value. This is pseudo-polynomial and degrades when capacities are large.

### Capacity Scaling for MCMF

**Idea**: Instead of augmenting one shortest path at a time (which may push tiny amounts), use capacity scaling. At scale $\Delta$, only consider edges with residual capacity $\geq \Delta$. Find augmenting paths among these "thick" edges, halving $\Delta$ when no more exist.

```
function min_cost_max_flow_capacity_scaling(G, s, t):
    Delta = 2^floor(log2(max_capacity))
    while Delta >= 1:
        while shortest_augmenting_path_exists(G, s, t, Delta):
            augment along shortest path (residual cap >= Delta)
        Delta = Delta // 2
    return flow, cost
```

**Complexity**: $O(E \log U \cdot (E + V \log V))$ where $U = \max c(e)$. The number of $\Delta$-phases is $O(\log U)$ and each phase runs $O(E)$ Dijkstra calls, but in practice far fewer augmentations occur per phase.

> **Interview Angle**: "How would you improve SSP when edge capacities are in the billions?" Describe capacity scaling. Explain that each $\Delta$-phase is like a "coarse" flow that is progressively refined.

### Cost Scaling (Goldberg-Tarjan Style)

Cost scaling works on the push-relabel framework. Instead of scaling capacities, we scale the **costs**. We maintain that reduced costs are within $[-\epsilon, \infty)$ and gradually shrink $\epsilon$.

**Key idea**: At each $\epsilon$-scale, we have a valid flow and node potentials such that for every residual edge $(u,v)$, the reduced cost $c_\pi(u,v) = w(u,v) + \pi(u) - \pi(v) \geq -\epsilon$. Edges with $c_\pi < 0$ are **admissible** and we push flow through them.

```
function cost_scaling_mcmf(G, s, t):
    epsilon = max_edge_cost
    initialize: zero flow, pi[v] = 0 for all v
    while epsilon >= 1/n:
        # Refine at this epsilon
        while admissible edge exists:
            push excess through admissible edges (push-relabel)
            relabel nodes: pi[v] += epsilon  # makes some edges admissible
        epsilon = epsilon / 2
    return flow, cost
```

**Complexity**: $O(V^2 \cdot E \cdot \log(VC))$ where $C = \max |w(e)|$. In practice, cost scaling significantly outperforms SSP on dense, high-capacity instances.

### Network Simplex

A primal-dual algorithm based on the simplex method for linear programs. It maintains a **spanning tree** of the graph where tree edges carry flow and non-tree edges are at their bounds. Each pivot swaps a non-tree edge into the tree.

**Strengths**: Extremely fast in practice (often 5-10x faster than cost-scaling on real-world road/network instances). **Weaknesses**: No polynomial worst-case bound (though it rarely cycles in practice with anti-cycling rules).

| Algorithm | Worst-Case Complexity | Practical Speed | Notes |
|-----------|----------------------|-----------------|-------|
| SSP + Dijkstra | $O(FE \log V)$ | Moderate | Simple, good for sparse/low-flow |
| SSP + Capacity Scaling | $O(E^2 \log U \log V)$ | Good | Better for large capacities |
| Cost Scaling | $O(V^2 E \log(VC))$ | Very Good | Best polynomial bound |
| Network Simplex | Exponential (rare) | Excellent in practice | Industry standard (e.g., LEMON, Google OR-Tools) |

---

## Push-Relabel: Advanced Optimizations

### Global Relabeling

The standard push-relabel uses local relabeling: when a node has excess but no admissible edges, increase its height. **Global relabeling** periodically recomputes exact distances from $t$ via BFS on the reverse residual graph, resetting all heights at once.

**Impact**: Reduces the number of relabel operations dramatically. In practice, a global relabel every $O(V)$ push operations gives a ~2-5x speedup.

```
function push_relabel_with_global_relabel(G, s, t):
    initialize heights via BFS from t on reverse graph
    push_counter = 0
    while excess exists at non-s,t nodes:
        if push_counter % V == 0:
            # Global relabel
            h[v] = dist_from_t[v] for all v  # BFS on G_rev
            h[s] = V  # keep source high
        discharge(v)  # standard push or relabel
        push_counter += 1
```

### Gap Relabeling

If there exists a height $k$ such that no node has height $k$ but nodes have heights $> k$, then all nodes with height $> k$ can be set to $\min(\max(k+1, t\text{-distance}), V+1)$. This "gap" means those nodes can never push flow to $t$.

**Complexity benefit**: The number of relabel operations drops from $O(V^2)$ to $O(V^2 / \text{gap frequency})$. Combined with global relabeling, this is the fastest known push-relabel variant.

### Highest-Label Selection Rule

Instead of FIFO (process nodes in queue order), always discharge the node with the **highest height**. This is implemented with a bucket queue (array of lists indexed by height).

**Complexity**: $O(V^2 \sqrt{E})$ — strictly better than FIFO's $O(V^3)$. The intuition: high nodes have more "pressure" and can push flow further toward the sink.

### Two-Level Push-Relabel with Dynamic Trees

Augment push-relabel with a **dynamic tree** data structure ([link-cut trees](dynamic-trees.md)) that represents the admissible graph (edges with $h(u) = h(v) + 1$). Instead of pushing one unit at a time along a chain, find the bottleneck of the entire path in the tree and push the maximum possible.

**Complexity**: $O(VE \log(V^2/E))$ — currently the fastest known strongly polynomial max-flow algorithm. The dynamic tree allows $O(\log V)$ per tree-path push instead of $O(\text{path length})$.

---

## Dinic's Algorithm: Optimizations

### Current-Arc Optimization

The single most important Dinic optimization. For each node, maintain a pointer to the next edge to try. Once an edge is saturated or leads to a dead end, advance the pointer past it. This ensures each edge is considered at most once per BFS phase.

```cpp
// C++ current-arc Dinic
struct Dinic {
    struct Edge { int to, rev; long long cap; };
    vector<vector<Edge>> g;
    vector<int> level, iter;
    
    bool bfs(int s, int t) {
        level.assign(n, -1);
        queue<int> q; q.push(s); level[s] = 0;
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (auto& e : g[v])
                if (e.cap > 0 && level[e.to] < 0)
                    level[e.to] = level[v] + 1, q.push(e.to);
        }
        return level[t] >= 0;
    }
    
    long long dfs(int v, int t, long long f) {
        if (v == t) return f;
        for (int& i = iter[v]; i < g[v].size(); i++) {  // current-arc
            Edge& e = g[v][i];
            if (e.cap > 0 && level[v] < level[e.to]) {
                long long d = dfs(e.to, t, min(f, e.cap));
                if (d > 0) {
                    e.cap -= d;
                    g[e.to][e.rev].cap += d;
                    return d;
                }
            }
        }
        return 0;
    }
    
    long long max_flow(int s, int t) {
        long long flow = 0;
        while (bfs(s, t)) {
            iter.assign(n, 0);
            long long f;
            while ((f = dfs(s, t, LLONG_MAX)) > 0) flow += f;
        }
        return flow;
    }
};
```

### Multi-Threaded Dinic

Each BFS phase finds a blocking flow. The DFS for finding augmenting paths can be parallelized: each thread picks a different path from $s$ through the level graph, but **conflicts** on edge capacities require atomic operations or fine-grained locking. In practice, a lock-free approach with CAS on capacities works well when the graph is wide (many edge-disjoint paths).

### Dinic on Unit Capacity Graphs

When all capacities are 1 (e.g., bipartite matching), Dinic runs in $O(\min(V^{2/3}, E^{1/2}) \cdot E)$ time. The key insight: each BFS phase increases the distance from $s$ to $t$ by at least 1, and the level graph has a specific structure for unit capacities.

**Special case — bipartite matching**: $O(E\sqrt{V})$ matching the Hopcroft-Karp bound.

---

## Min-Cost Flow: Applications

### Assignment with Complex Costs

Standard assignment: $n$ workers, $n$ tasks, cost matrix. MCMF on a bipartite graph with $O(n^2)$ edges gives optimal assignment in $O(n^3 \log n)$.

### Minimum-Cost Circulation

When there is no designated source/sink but the graph has **lower bounds** $l(e)$ and **demands** $d(v)$, transform to a standard MCMF by adding a super-source and super-sink.

### Convex Cost Flow

When edge costs are **convex functions** of flow (e.g., $w(f) = af^2 + bf + c$), we can model this by splitting each edge into $O(\log U)$ parallel edges at different cost breakpoints, then running standard MCMF.

### Applications in Competitive Programming

- **Minimum mean-weight cycle cancellation**: Alternate approach to MCMF; cancel the most negative mean-weight cycle repeatedly.
- **Flow with lower bounds**: Model constraints like "at least $k$ units must flow."
- **Project selection**: Maximize profit where projects have costs and dependencies.

> **Interview Angle**: "How would you route $k$ deliveries minimizing total distance, respecting vehicle capacities?" Model as MCMF: each delivery is demand, roads are edges with capacity = road capacity, cost = distance.

---

## Comparison: When to Use What

```
              | Sparse   | Dense    | Unit Cap | Large Cost
              | (E~V)    | (E~V^2)  |          | Range
--------------|----------|----------|----------|------------
Dinic         | O(EV^0.5)| O(V^2E)  | O(EV^2/3)| N/A
Push-Relabel  | O(V^3)   | O(V^3)   | N/A      | N/A
HL Push-Rel.  | O(V^2E^0.5) best  |          |          |
SSP MCMF      | Fast     | Slow     | N/A      | Bad
Cost Scaling  | Moderate | Good     | N/A      | Excellent
Network Simplex| Excellent | Excellent| N/A      | Excellent
```

**Rule of thumb**: For competitive programming, Dinic with current-arc is almost always sufficient for max-flow, and SSP with potentials for MCMF. For production systems with millions of edges, use Network Simplex (OR-Tools, LEMON) or cost-scaling implementations.

## Further Reading

- Goldberg & Tarjan, "A New Approach to the Maximum-Flow Problem" (1988) — the original push-relabel paper
- Goldberg, "The Partial Augment-Relabel Algorithm for the Minimum-Cost Flow Problem" (2008) — cost scaling
- Ahuja, Magnanti, Orlin, *Network Flows: Theory, Algorithms, and Applications* (1993) — comprehensive reference
- [Ch 169: Min-Cost Max-Flow](../chapters/ch169-min-cost-max-flow.md) — the base chapter on this topic
