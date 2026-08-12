# Chapter 81: SCC, Bridges, and Articulation Points

## Prerequisites

- DFS
- Graph fundamentals

## Interview Frequency: ★★★

Strongly Connected Components, bridges, and articulation points are fundamental graph concepts. **Google** and **Amazon** test these for network reliability problems.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| SCC (Kosaraju) | ★★★ | Medium | Two-pass DFS |
| SCC (Tarjan) | ★★★ | Medium | Single-pass DFS |
| Bridges | ★★★ | Medium | Critical edges |
| Articulation points | ★★★ | Medium | Critical vertices |

---

## Definition

**Strongly Connected Component (SCC).**
In a directed graph \\(G = (V, E)\\), a *strongly connected component* is a maximal subset of vertices \\(S \subseteq V\\) such that for every pair of vertices \\(u, v \in S\\), there exists a directed path from \\(u\\) to \\(v\\) and from \\(v\\) to \\(u\\). "Maximal" means no additional vertex can be added to \\(S\\) while preserving this property.

**Bridge.**
In an undirected graph \\(G = (V, E)\\), an edge \\(e = (u, v)\\) is a *bridge* (also called a *cut edge* or *isthmus*) if removing \\(e\\) increases the number of connected components of \\(G\\). Equivalently, \\(e\\) is a bridge if and only if \\(e\\) does not lie on any simple cycle.

**Articulation Point.**
In an undirected graph \\(G = (V, E)\\), a vertex \\(v \in V\\) is an *articulation point* (also called a *cut vertex*) if removing \\(v\\) (and all its incident edges) increases the number of connected components. Equivalently, \\(v\\) is an articulation point if it belongs to more than one biconnected component.

**Condensation Graph.**
Given a directed graph \\(G\\) and its SCCs \\(\{S_1, S_2, \ldots, S_k\}\\), the *condensation graph* \\(G'\\) is a DAG where each SCC \\(S_i\\) is contracted to a single node, and there is a directed edge from \\(S_i\\) to \\(S_j\\) if and only if there exists an edge from some vertex in \\(S_i\\) to some vertex in \\(S_j\\) in the original graph.

---

## Motivation

These concepts arise naturally in many domains:

- **Network reliability.** In a computer network, bridges represent single points of failure for connectivity. Identifying them lets engineers add redundant links. Articulation points identify critical routers or switches.
- **Compiler optimization.** Compilers use SCC detection on control-flow graphs to identify loops (a loop body forms an SCC in the CFG). This enables loop-invariant code motion, strength reduction, and other optimizations.
- **Social network analysis.** SCCs in a follower/following graph reveal communities where everyone can reach everyone else. The condensation DAG shows the hierarchy of influence.
- **Web crawling and link analysis.** The web graph decomposes into a giant SCC (the "bow-tie" structure), plus tendrils and disconnected parts. Search engines use this structure for ranking.
- **Dependency resolution.** Circular dependencies between modules form SCCs. Resolving them (e.g., by collapsing to a single unit) is essential for build systems.
- **Circuit design.** Bridges in circuit graphs identify wires whose failure would isolate components; articulation points identify components whose failure would fragment the circuit.

---

## Intuition

### SCCs: "Who can talk to whom?"

Imagine a city with one-way streets. An SCC is a neighborhood where you can drive from any intersection to any other intersection following one-way signs. The entire city decomposes into such neighborhoods, with one-way roads flowing between them in a DAG structure — you can never return once you leave one neighborhood for another.

### Bridges: "The only way across"

Think of islands connected by bridges. A bridge is the *only* connection between two parts of the archipelago. If it collapses, some islands become unreachable. Graphically, a bridge is an edge that is not part of any cycle — there is no alternative route.

### Articulation Points: "The hub that holds it all together"

Consider a flight network. A hub airport is an articulation point if its closure forces some cities to become unreachable from others. It sits at the intersection of multiple connectivity paths.

### The DFS Timestamp Trick

All three algorithms share a common insight: perform a DFS and track two values per node:
- `tin[u]`: when node `u` is first discovered (entry time).
- `low[u]`: the earliest node reachable from `u`'s subtree (including via back edges).

If a child `v` cannot reach anything earlier than `u` (i.e., `low[v] >= tin[u]`), then `u` is the only way into `v`'s subtree — making `(u, v)` a bridge (strict inequality) or `u` an articulation point (non-strict inequality, with special handling for the DFS root).

---

## 81.1 Strongly Connected Components (Kosaraju's Algorithm)

1. DFS to get finish order
2. Transpose the graph
3. DFS on transposed graph in reverse finish order

```cpp
#include <iostream>
#include <vector>
#include <stack>
#include <algorithm>

class KosarajuSCC {
    int n;
    std::vector<std::vector<int>> adj, rev;
    
    void dfs1(int u, std::vector<bool>& visited, std::stack<int>& order) {
        visited[u] = true;
        for (int v : adj[u])
            if (!visited[v]) dfs1(v, visited, order);
        order.push(u);
    }
    
    void dfs2(int u, std::vector<bool>& visited, std::vector<int>& component) {
        visited[u] = true;
        component.push_back(u);
        for (int v : rev[u])
            if (!visited[v]) dfs2(v, visited, component);
    }
    
public:
    KosarajuSCC(int n) : n(n), adj(n), rev(n) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        rev[v].push_back(u);
    }
    
    std::vector<std::vector<int>> findSCCs() {
        std::vector<bool> visited(n, false);
        std::stack<int> order;
        
        for (int i = 0; i < n; i++)
            if (!visited[i]) dfs1(i, visited, order);
        
        std::fill(visited.begin(), visited.end(), false);
        std::vector<std::vector<int>> sccs;
        
        while (!order.empty()) {
            int u = order.top(); order.pop();
            if (!visited[u]) {
                std::vector<int> component;
                dfs2(u, visited, component);
                sccs.push_back(component);
            }
        }
        
        return sccs;
    }
};

int main() {
    KosarajuSCC g(8);
    g.addEdge(0, 1); g.addEdge(1, 2); g.addEdge(2, 0);
    g.addEdge(2, 3); g.addEdge(3, 4); g.addEdge(4, 5);
    g.addEdge(5, 3); g.addEdge(6, 5); g.addEdge(6, 7);
    
    auto sccs = g.findSCCs();
    std::cout << "Strongly Connected Components:\n";
    for (auto& scc : sccs) {
        std::cout << "  {";
        for (int v : scc) std::cout << v << " ";
        std::cout << "}\n";
    }
    
    return 0;
}
```

### Python Implementation

```python
from collections import defaultdict

class KosarajuSCC:
    def __init__(self, n):
        self.n = n
        self.adj = defaultdict(list)
        self.rev = defaultdict(list)

    def add_edge(self, u, v):
        self.adj[u].append(v)
        self.rev[v].append(u)

    def find_sccs(self):
        visited = [False] * self.n
        order = []

        def dfs1(u):
            visited[u] = True
            for v in self.adj[u]:
                if not visited[v]:
                    dfs1(v)
            order.append(u)

        for i in range(self.n):
            if not visited[i]:
                dfs1(i)

        visited = [False] * self.n
        sccs = []

        def dfs2(u, component):
            visited[u] = True
            component.append(u)
            for v in self.rev[u]:
                if not visited[v]:
                    dfs2(v, component)

        for u in reversed(order):
            if not visited[u]:
                component = []
                dfs2(u, component)
                sccs.append(component)

        return sccs


if __name__ == "__main__":
    g = KosarajuSCC(8)
    g.add_edge(0, 1); g.add_edge(1, 2); g.add_edge(2, 0)
    g.add_edge(2, 3); g.add_edge(3, 4); g.add_edge(4, 5)
    g.add_edge(5, 3); g.add_edge(6, 5); g.add_edge(6, 7)

    sccs = g.find_sccs()
    print("Strongly Connected Components:")
    for scc in sccs:
        print(f"  {{{' '.join(map(str, scc))}}}")
```

### Java Implementation

```java
import java.util.*;

public class KosarajuSCC {
    private int n;
    private List<List<Integer>> adj, rev;

    public KosarajuSCC(int n) {
        this.n = n;
        adj = new ArrayList<>();
        rev = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            adj.add(new ArrayList<>());
            rev.add(new ArrayList<>());
        }
    }

    public void addEdge(int u, int v) {
        adj.get(u).add(v);
        rev.get(v).add(u);
    }

    private void dfs1(int u, boolean[] visited, Deque<Integer> order) {
        visited[u] = true;
        for (int v : adj.get(u))
            if (!visited[v]) dfs1(v, visited, order);
        order.push(u);
    }

    private void dfs2(int u, boolean[] visited, List<Integer> component) {
        visited[u] = true;
        component.add(u);
        for (int v : rev.get(u))
            if (!visited[v]) dfs2(v, visited, component);
    }

    public List<List<Integer>> findSCCs() {
        boolean[] visited = new boolean[n];
        Deque<Integer> order = new ArrayDeque<>();

        for (int i = 0; i < n; i++)
            if (!visited[i]) dfs1(i, visited, order);

        Arrays.fill(visited, false);
        List<List<Integer>> sccs = new ArrayList<>();

        while (!order.isEmpty()) {
            int u = order.pop();
            if (!visited[u]) {
                List<Integer> component = new ArrayList<>();
                dfs2(u, visited, component);
                sccs.add(component);
            }
        }

        return sccs;
    }

    public static void main(String[] args) {
        KosarajuSCC g = new KosarajuSCC(8);
        g.addEdge(0, 1); g.addEdge(1, 2); g.addEdge(2, 0);
        g.addEdge(2, 3); g.addEdge(3, 4); g.addEdge(4, 5);
        g.addEdge(5, 3); g.addEdge(6, 5); g.addEdge(6, 7);

        List<List<Integer>> sccs = g.findSCCs();
        System.out.println("Strongly Connected Components:");
        for (List<Integer> scc : sccs)
            System.out.println("  " + scc);
    }
}
```

---

## 81.2 Tarjan's SCC Algorithm

Tarjan's algorithm finds all SCCs in a **single DFS pass** using a stack and low-link values.

```cpp
#include <iostream>
#include <vector>
#include <stack>
#include <algorithm>

class TarjanSCC {
    int n, timer;
    std::vector<std::vector<int>> adj;
    std::vector<int> tin, low;
    std::vector<bool> onStack;
    std::stack<int> stk;
    std::vector<std::vector<int>> sccs;

    void dfs(int u) {
        tin[u] = low[u] = timer++;
        stk.push(u);
        onStack[u] = true;

        for (int v : adj[u]) {
            if (tin[v] == -1) {
                dfs(v);
                low[u] = std::min(low[u], low[v]);
            } else if (onStack[v]) {
                low[u] = std::min(low[u], tin[v]);
            }
        }

        if (low[u] == tin[u]) {
            std::vector<int> component;
            while (true) {
                int v = stk.top(); stk.pop();
                onStack[v] = false;
                component.push_back(v);
                if (v == u) break;
            }
            sccs.push_back(component);
        }
    }

public:
    TarjanSCC(int n) : n(n), timer(0), adj(n), tin(n, -1), low(n, 0), onStack(n, false) {}

    void addEdge(int u, int v) { adj[u].push_back(v); }

    std::vector<std::vector<int>> findSCCs() {
        for (int i = 0; i < n; i++)
            if (tin[i] == -1) dfs(i);
        return sccs;
    }
};

int main() {
    TarjanSCC g(8);
    g.addEdge(0, 1); g.addEdge(1, 2); g.addEdge(2, 0);
    g.addEdge(2, 3); g.addEdge(3, 4); g.addEdge(4, 5);
    g.addEdge(5, 3); g.addEdge(6, 5); g.addEdge(6, 7);

    auto sccs = g.findSCCs();
    std::cout << "Tarjan's SCCs:\n";
    for (auto& scc : sccs) {
        std::cout << "  {";
        for (int v : scc) std::cout << v << " ";
        std::cout << "}\n";
    }
    return 0;
}
```

### Python Implementation

```python
class TarjanSCC:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]

    def add_edge(self, u, v):
        self.adj[u].append(v)

    def find_sccs(self):
        timer = 0
        tin = [-1] * self.n
        low = [0] * self.n
        on_stack = [False] * self.n
        stack = []
        sccs = []

        def dfs(u):
            nonlocal timer
            tin[u] = low[u] = timer
            timer += 1
            stack.append(u)
            on_stack[u] = True

            for v in self.adj[u]:
                if tin[v] == -1:
                    dfs(v)
                    low[u] = min(low[u], low[v])
                elif on_stack[v]:
                    low[u] = min(low[u], tin[v])

            if low[u] == tin[u]:
                component = []
                while True:
                    v = stack.pop()
                    on_stack[v] = False
                    component.append(v)
                    if v == u:
                        break
                sccs.append(component)

        for i in range(self.n):
            if tin[i] == -1:
                dfs(i)
        return sccs
```

---

## 81.3 Bridges

A **bridge** is an edge whose removal disconnects the graph.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class BridgeFinder {
    int n, timer;
    std::vector<std::vector<int>> adj;
    std::vector<int> tin, low;
    std::vector<bool> visited;
    std::vector<std::pair<int,int>> bridges;
    
    void dfs(int u, int p) {
        visited[u] = true;
        tin[u] = low[u] = timer++;
        
        for (int v : adj[u]) {
            if (v == p) continue;
            if (visited[v]) {
                low[u] = std::min(low[u], tin[v]);
            } else {
                dfs(v, u);
                low[u] = std::min(low[u], low[v]);
                if (low[v] > tin[u]) {
                    bridges.push_back({u, v});
                }
            }
        }
    }
    
public:
    BridgeFinder(int n) : n(n), timer(0), adj(n), tin(n), low(n), visited(n, false) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    std::vector<std::pair<int,int>> findBridges() {
        for (int i = 0; i < n; i++)
            if (!visited[i]) dfs(i, -1);
        return bridges;
    }
};

int main() {
    BridgeFinder g(5);
    g.addEdge(0, 1); g.addEdge(1, 2); g.addEdge(2, 0);
    g.addEdge(1, 3); g.addEdge(3, 4);
    
    auto bridges = g.findBridges();
    std::cout << "Bridges:\n";
    for (auto& [u, v] : bridges)
        std::cout << "  " << u << " - " << v << "\n";
    
    return 0;
}
```

### Python Implementation

```python
class BridgeFinder:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]

    def add_edge(self, u, v):
        self.adj[u].append(v)
        self.adj[v].append(u)

    def find_bridges(self):
        timer = 0
        tin = [-1] * self.n
        low = [0] * self.n
        bridges = []

        def dfs(u, parent):
            nonlocal timer
            tin[u] = low[u] = timer
            timer += 1

            for v in self.adj[u]:
                if v == parent:
                    continue
                if tin[v] != -1:
                    low[u] = min(low[u], tin[v])
                else:
                    dfs(v, u)
                    low[u] = min(low[u], low[v])
                    if low[v] > tin[u]:
                        bridges.append((u, v))

        for i in range(self.n):
            if tin[i] == -1:
                dfs(i, -1)
        return bridges
```

---

## 81.4 Articulation Points

An **articulation point** is a vertex whose removal disconnects the graph.

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <set>

class ArticulationFinder {
    int n, timer;
    std::vector<std::vector<int>> adj;
    std::vector<int> tin, low;
    std::vector<bool> visited;
    std::set<int> articulationPoints;
    
    void dfs(int u, int p) {
        visited[u] = true;
        tin[u] = low[u] = timer++;
        int children = 0;
        
        for (int v : adj[u]) {
            if (v == p) continue;
            if (visited[v]) {
                low[u] = std::min(low[u], tin[v]);
            } else {
                dfs(v, u);
                low[u] = std::min(low[u], low[v]);
                if (low[v] >= tin[u] && p != -1)
                    articulationPoints.insert(u);
                children++;
            }
        }
        
        if (p == -1 && children > 1)
            articulationPoints.insert(u);
    }
    
public:
    ArticulationFinder(int n) : n(n), timer(0), adj(n), tin(n), low(n), 
                                 visited(n, false) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    std::set<int> findArticulationPoints() {
        for (int i = 0; i < n; i++)
            if (!visited[i]) dfs(i, -1);
        return articulationPoints;
    }
};

int main() {
    ArticulationFinder g(7);
    g.addEdge(0, 1); g.addEdge(1, 2); g.addEdge(2, 0);
    g.addEdge(1, 3); g.addEdge(1, 4); g.addEdge(3, 4);
    g.addEdge(1, 5); g.addEdge(5, 6);
    
    auto aps = g.findArticulationPoints();
    std::cout << "Articulation Points: ";
    for (int v : aps) std::cout << v << " ";
    std::cout << "\n";
    
    return 0;
}
```

### Python Implementation

```python
class ArticulationFinder:
    def __init__(self, n):
        self.n = n
        self.adj = [[] for _ in range(n)]

    def add_edge(self, u, v):
        self.adj[u].append(v)
        self.adj[v].append(u)

    def find_articulation_points(self):
        timer = 0
        tin = [-1] * self.n
        low = [0] * self.n
        ap = set()

        def dfs(u, parent):
            nonlocal timer
            tin[u] = low[u] = timer
            timer += 1
            children = 0

            for v in self.adj[u]:
                if v == parent:
                    continue
                if tin[v] != -1:
                    low[u] = min(low[u], tin[v])
                else:
                    dfs(v, u)
                    low[u] = min(low[u], low[v])
                    if low[v] >= tin[u] and parent != -1:
                        ap.add(u)
                    children += 1

            if parent == -1 and children > 1:
                ap.add(u)

        for i in range(self.n):
            if tin[i] == -1:
                dfs(i, -1)
        return ap
```

---

## Formal Explanation

### Correctness of Kosaraju's Algorithm

**Claim:** Each DFS in the second pass visits exactly one SCC.

**Proof sketch.** Let \\(G^T\\) denote the transpose of \\(G\\). The first DFS produces a finishing order. Consider the vertex \\(v\\) with the largest finishing time. In \\(G^T\\), the DFS from \\(v\\) reaches exactly the vertices of \\(v\\)'s SCC.

*Why?* Suppose DFS from \\(v\\) in \\(G^T\\) reaches some vertex \\(w\\) in a different SCC \\(C'\\). Then there is a path \\(v \rightsquigarrow w\\) in \\(G^T\\), meaning a path \\(w \rightsquigarrow v\\) in \\(G\\). If \\(w\\)'s SCC \\(C'\\) can reach \\(v\\)'s SCC, but \\(v\\)'s SCC cannot reach \\(C'\\) (different SCCs), then by the structure of SCCs, vertices in \\(C'\\) would finish before vertices in \\(v\\)'s SCC during the first DFS — contradicting that \\(v\\) has the largest finishing time. Therefore, DFS from \\(v\\) stays within \\(v\\)'s SCC. \\(\square\\)

### Correctness of the Bridge Condition

**Claim:** Edge \\((u, v)\\) (where \\(u\\) is the parent of \\(v\\) in the DFS tree) is a bridge if and only if \\(\text{low}[v] > \text{tin}[u]\\).

**Proof.** \\(\text{low}[v]\\) is the minimum discovery time reachable from \\(v\\)'s subtree without using edge \\((u, v)\\).

- If \\(\text{low}[v] > \text{tin}[u]\\): No vertex in \\(v\\)'s subtree can reach \\(u\\) or any ancestor of \\(u\\) without going through \\((u, v)\\). Removing \\((u, v)\\) disconnects \\(v\\)'s subtree from the rest of the graph. So \\((u, v)\\) is a bridge.
- If \\(\text{low}[v] \leq \text{tin}[u]\\): There exists a back edge from \\(v\\)'s subtree to \\(u\\) or an ancestor of \\(u\\). This back edge provides an alternative path, so removing \\((u, v)\\) does not disconnect the graph. \\(\square\\)

### Correctness of the Articulation Point Condition

**Claim:** A non-root vertex \\(u\\) is an articulation point if and only if \\(u\\) has a child \\(v\\) with \\(\text{low}[v] \geq \text{tin}[u]\\).

**Proof.** If such a child \\(v\\) exists, \\(v\\)'s subtree cannot reach any vertex strictly before \\(u\\) in discovery time without going through \\(u\\). Removing \\(u\\) disconnects \\(v\\)'s subtree.

For the root: the DFS root is an articulation point if and only if it has two or more children in the DFS tree, since there are no back edges to the root's "parent" (it has none), so each child subtree is independent. \\(\square\\)

---

## Complexity Analysis

| Algorithm | Time | Space | Passes |
|---|---|---|---|
| Kosaraju's SCC | \\(O(V + E)\\) | \\(O(V + E)\\) for transpose graph | 2 DFS |
| Tarjan's SCC | \\(O(V + E)\\) | \\(O(V)\\) for stack + arrays | 1 DFS |
| Bridge finding | \\(O(V + E)\\) | \\(O(V)\\) for tin/low arrays | 1 DFS |
| Articulation points | \\(O(V + E)\\) | \\(O(V)\\) for tin/low arrays | 1 DFS |

**Notes:**
- All algorithms are linear in the size of the graph.
- Kosaraju's requires storing the transposed graph (doubling edge storage), while Tarjan's and the bridge/articulation algorithms use only the original adjacency list plus \\(O(V)\\) auxiliary arrays.
- In practice, Tarjan's single-pass approach has better cache locality than Kosaraju's two-pass approach.

---

## Dry Run: Kosaraju's Algorithm

Consider this directed graph with 7 vertices:

```
0 → 1 → 2 → 0    (cycle: {0,1,2})
2 → 3
3 → 4 → 5 → 3    (cycle: {3,4,5})
6 → 5
6 → 7 (isolated aside from 6→7)
```

Edges: (0,1), (1,2), (2,0), (2,3), (3,4), (4,5), (5,3), (6,5), (6,7). Note: vertex 7 exists but has no outgoing edges.

**Pass 1: DFS to compute finishing order**

Start DFS from vertex 0:
```
Visit 0 → 1 → 2 → back to 0 (already visited)
Finish 2, push 2
Finish 1, push 1
Finish 0, push 0
Order so far: [2, 1, 0]
```

DFS from 3:
```
Visit 3 → 4 → 5 → back to 3 (already visited)
Finish 5, push 5
Finish 4, push 4
Finish 3, push 3
Order: [2, 1, 0, 5, 4, 3]
```

DFS from 6:
```
Visit 6 → 5 (already visited), → 7
Finish 7, push 7
Finish 6, push 6
Order: [2, 1, 0, 5, 4, 3, 7, 6]
```

Reverse order (process from top of stack): **6, 7, 3, 4, 5, 0, 1, 2**

**Pass 2: DFS on transposed graph in reverse finishing order**

Transpose edges: (1,0), (2,1), (0,2), (3,2), (4,3), (5,4), (3,5), (5,6), (7,6)

Process vertex 6: DFS on \\(G^T\\) from 6.
```
Visit 6 → no incoming edges in transpose? Actually 5→6 in transpose (from 6→5 original? No, 6→5 original, so transpose is 5→6). Wait — let me re-check.
```

Original edges: (6,5) and (6,7). Transpose: (5,6) and (7,6). So vertex 6 in transpose has *incoming* from 5 and 7, no outgoing. DFS from 6 visits only {6}.

**SCC 1: {6}**

Process vertex 7: already visited. Skip.

Process vertex 3: DFS on \\(G^T\\) from 3.
```
Visit 3 → neighbors in transpose: (4,3)? No, original (3,4) → transpose (4,3). And (5,3) original → transpose (3,5).
So from 3: go to 5. From 5: go to 4 (transpose of (4,5)). From 4: go to 3 (transpose of (3,4)) — already visited.
```
**SCC 2: {3, 4, 5}**

Process vertex 0: DFS on \\(G^T\\) from 0.
```
Visit 0 → transpose neighbors: (2,0) from original (0,2)→transpose(2,0). Wait.
Original: (0,1), (1,2), (2,0). Transpose: (1,0), (2,1), (0,2).
From 0 in transpose: → 2. From 2: → 1. From 1: → 0 (visited).
```
**SCC 3: {0, 1, 2}**

**Result:** Three SCCs: **{6}**, **{3, 4, 5}**, **{0, 1, 2}** — and vertex 7 was never reached as a start (it was visited via 6), so {7} should also be an SCC. Let me re-check: transpose edge (7,6) means 7→6 in transpose. Starting from 6, DFS visits 6 only (no outgoing from 6 in transpose). Then 7 is processed next and forms its own SCC.

**Final SCCs: {6}, {7}, {3, 4, 5}, {0, 1, 2}** — the condensation DAG is: {0,1,2} → {3,4,5} ← {6}, and {7} → {6} (via transpose edge 7→6 meaning original 6→7, so condensation edge {6} → {7}).

---

## Summary

| Concept | Definition | Algorithm | Time |
|---|---|---|---|
| SCC | Maximal strongly connected subgraph | Kosaraju/Tarjan | O(V+E) |
| Bridge | Edge whose removal disconnects | DFS with low/tin | O(V+E) |
| Articulation Point | Vertex whose removal disconnects | DFS with low/tin | O(V+E) |

---



---

## Interview Questions

### Q1: What is a Strongly Connected Component?
**Answer**: An SCC is a maximal subgraph where every vertex is reachable from every other vertex. In other words, for any two vertices u and v in the SCC, there exists a path from u to v and from v to u. Directed graphs can be decomposed into SCCs, forming a DAG when each SCC is contracted to a single node.

### Q2: Compare Kosaraju's and Tarjan's SCC algorithms.
**Answer**: Both run in O(V+E). Kosaraju does two DFS passes (forward then on transposed graph) and is conceptually simpler. Tarjan does a single DFS pass using a stack and low-link values, making it faster in practice (one pass, better cache behavior). Both produce the same result.

### Q3: How do you find bridges, and what's the key condition?
**Answer**: Use DFS with `tin[u]` (discovery time) and `low[u]` (lowest discovery time reachable from subtree of u). An edge (u,v) is a bridge if `low[v] > tin[u]` — meaning v's subtree cannot reach u or any ancestor of u without using edge (u,v).

### Q4: What's the difference between a bridge and an articulation point?
**Answer**: A bridge is an **edge** whose removal disconnects the graph. An articulation point is a **vertex** whose removal disconnects the graph. A vertex u is an articulation point if it has a child v where `low[v] >= tin[u]`, or if u is the root of the DFS tree and has more than one child.

### Q5: How do SCCs relate to 2-SAT?
**Answer**: In 2-SAT, construct an implication graph. If variable x and ¬x are in the same SCC, the formula is unsatisfiable. Otherwise, a topological order of the SCC condensation graph gives a valid assignment: process SCCs in reverse topological order, assigning false to any unassigned literal. This runs in O(V+E).

### Q6: Can a single edge be both a bridge and part of an SCC?
**Answer**: No. If an edge (u,v) is part of an SCC, then u can reach v and v can reach u without that specific edge (since SCCs have alternative paths). A bridge, by definition, has no alternative path. Therefore bridges only exist in undirected graphs (or between different SCCs in directed graphs).

### Q7: How would you find all 2-edge-connected components?
**Answer**: Find all bridges first. Then remove bridges and find connected components of the remaining graph — each component is a 2-edge-connected component (no edge within it is a bridge). This runs in O(V+E).

---

## Exercises

1. **Tarjan's Algorithm**: Implement Tarjan's SCC algorithm. Compare its performance with Kosaraju's on the same graph instances.

2. **Bridge Count in a Tree**: Prove that every edge in a tree is a bridge. Then write an algorithm that counts bridges in a general graph.

3. **2-Edge-Connected Components**: Modify the bridge-finding algorithm to output the 2-edge-connected components (maximal subgraphs with no bridges).

4. **SCC Condensation DAG**: After finding SCCs, build the condensation DAG (each SCC becomes a node). Implement topological sort on it and verify it matches the expected order.

5. **Network Reliability**: Given an undirected graph representing a network, find all critical connections (bridges). If you could add one edge to the network, which edge would maximize reliability (minimize the number of bridges)?

6. **Biconnected Components**: Extend the articulation point algorithm to find all biconnected components (maximal subgraphs with no articulation points). Output the edges belonging to each biconnected component.

7. **Euler Tour and SCC**: Investigate the relationship between Euler tours of a directed graph and its SCC structure. Under what conditions does an Euler tour exist, and how do SCCs constrain it?

---

## See Also

- [Chapter 23: Depth-First Search](ch23-dfs.md) — SCC and bridge-finding algorithms are built on DFS with timestamps and low-link values.
- [Chapter 25: Topological Sort](ch25-topological-sort.md) — SCC condensation produces a DAG; topological sort on the condensation graph enables further analysis.
- [Chapter 22: Graph Fundamentals](ch22-graph-fundamentals.md) — Prerequisite: graph representations, connectivity, and basic DFS.
- [Chapter 28: Advanced Graphs](ch28-advanced-graphs.md) — Biconnected components, ear decomposition, and other advanced connectivity concepts.
- [Chapter 109: Bridge Trees and Treewidth](ch109-bridge-trees-treewidth.md) — Bridge trees compress 2-edge-connected components; related to the bridge-finding algorithms here.
- [Chapter 17: Disjoint Set Union](ch17-dsu.md) — DSU can maintain connectivity information and is sometimes used alongside SCC algorithms.
- [Chapter 29: Network Flow](ch29-network-flow.md) — Flow algorithms use graph connectivity; SCC decomposition is useful in flow network analysis.
- [Chapter 24: Breadth-First Search](ch24-bfs.md) — BFS-based approaches for connectivity and bipartiteness testing complement DFS-based SCC methods.
