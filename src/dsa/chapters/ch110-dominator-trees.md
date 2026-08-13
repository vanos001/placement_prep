# Chapter 110: Dominator Trees

## Prerequisites
- DFS, SCC, Graph Theory basics

## Interview Frequency: ★

---

## 110.1 What Is a Dominator Tree?

A **dominator tree** is a tree derived from a directed graph where node d is an ancestor of node v if and only if every path from the root to v passes through d. It captures the "must-pass-through" relationships in a flowgraph.

**Formal Definition:** In a flowgraph with root r, node d **dominates** node v (written d dom v) if every path from r to v includes d.

**Key properties:**
- Every node dominates itself (reflexive)
- If d dom v and v dom w, then d dom w (transitive)
- The dominance relation forms a tree structure

**Immediate dominator (idom):** The unique node d that dominates v but doesn't dominate any other dominator of v (except itself). The idom relationship forms a tree.

---

## 110.2 Motivation and Applications

### Compiler Optimization
- **Control flow analysis:** Identifying basic blocks that must execute
- **Loop detection:** Natural loops are identified via dominators
- **Code motion:** Safe hoisting of computations requires dominator info
- **SSA construction:** Static Single Assignment form uses dominance frontiers

### Network Analysis
- **Critical nodes:** Nodes that are dominators of many others are bottlenecks
- **Reachability:** Understanding which nodes are unavoidable

### Example Problem
Given a program's control flow graph, find which basic blocks must execute before a specific instruction. The dominator tree answers this directly.

---

## 110.3 Definitions and Properties

| Concept | Definition |
|---|---|
| **Dominator (d dom v)** | Every path from root to v passes through d |
| **Immediate dominator (idom(v))** | Unique closest dominator of v |
| **Dominator tree** | Tree where parent of v is idom(v) |
| **Dominance frontier** | Set of nodes where dominance "stops" |
| **Strict dominator** | d strictly dominates v if d dom v and d ≠ v |

### Properties
1. **Root dominates all:** idom(root) = root
2. **Tree structure:** Each node has exactly one immediate dominator
3. **Ancestors = dominators:** Dominators of v are exactly the ancestors of v in the dominator tree
4. **LCA relationship:** For DAGs, idom(v) = LCA of all predecessors of v in the DFS tree

---

## 110.4 Algorithm: Lengauer-Tarjan

The **Lengauer-Tarjan algorithm** (1979) computes dominator trees in nearly linear time.

### High-Level Idea
1. Perform DFS from root, assigning DFS numbers
2. For each node v (in reverse DFS order), compute its "semi-dominator" (sdom)
3. The semi-dominator relates to the immediate dominator through a path compression structure

### Semi-Dominator
The **semi-dominator** of v, sdom(v), is the node u with minimum DFS number such that there's a path u → ... → v where all intermediate nodes have DFS number > DFS(v).

### Steps
1. **DFS:** Number nodes 1..n in DFS order. Compute parent and ancestor arrays.
2. **Compute sdom:** For each node v, sdom(v) = min DFS number among:
   - All predecessors u of v where DFS(u) < DFS(v)
   - sdom(w) for all w where DFS(w) > DFS(v) and w is an ancestor of v with a path to v through high-numbered nodes
3. **Compute idom:** idom(v) = sdom(v) if sdom(v) = sdom(w) for the appropriate w; otherwise idom(v) = idom(w)

### Time Complexity
- **O(V + E) × α(V))** where α is the inverse Ackermann function (nearly linear)
- **O(V + E)** for DAGs with simpler algorithm

---

## 110.5 Simplified Algorithm for DAGs

For DAGs, the dominator tree can be computed more simply:

**Key insight:** In a DAG, idom(v) = LCA of all predecessors of v in the DFS tree.

### Algorithm
1. Perform DFS from root
2. For each node v, collect all predecessors
3. idom(v) = LCA of all predecessors (computed incrementally)

### Dry Run

**Graph:**
```
    0
   / \
  1   2
   \ /
    3
   / \
  4   5
```

**Edges:** 0→1, 0→2, 1→3, 2→3, 3→4, 3→5

**DFS from 0:**
| Node | DFS# | Predecessors | idom |
|---|---|---|---|
| 0 | 0 | (root) | 0 |
| 1 | 1 | {0} | 0 |
| 2 | 2 | {0} | 0 |
| 3 | 3 | {1, 2} | LCA(1,2) = 0 |
| 4 | 4 | {3} | 3 |
| 5 | 5 | {3} | 3 |

**Dominator Tree:**
```
    0
   /|\
  1 2 3
      /\
     4  5
```

Note: Nodes 1 and 2 are leaves because they don't dominate anything besides themselves.

---

## 110.6 Code Implementation

### C++: Simplified Dominator Tree for DAGs

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

class DominatorTree {
    int n;
    std::vector<std::vector<int>> adj, rev;
    std::vector<int> idom;      // Immediate dominator
    std::vector<int> dfsOrder;  // DFS order
    std::vector<int> dfsNum;    // DFS number for each node
    
public:
    DominatorTree(int n) : n(n), adj(n), rev(n), idom(n, -1), dfsNum(n, -1) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        rev[v].push_back(u);
    }
    
    // For DAGs: compute dominator tree using LCA of predecessors
    std::vector<int> build(int root) {
        // Step 1: DFS to get order
        int counter = 0;
        std::vector<bool> visited(n, false);
        
        std::function<void(int)> dfs = [&](int u) {
            visited[u] = true;
            dfsNum[u] = counter++;
            dfsOrder.push_back(u);
            for (int v : adj[u]) {
                if (!visited[v]) dfs(v);
            }
        };
        dfs(root);
        
        // Step 2: Compute idom for each node
        idom[root] = root;
        
        for (int idx = 1; idx < (int)dfsOrder.size(); idx++) {
            int v = dfsOrder[idx];
            // idom(v) = LCA of all predecessors in DFS tree
            int lca = -1;
            for (int pred : rev[v]) {
                if (dfsNum[pred] < 0) continue; // unreachable
                if (lca == -1) lca = pred;
                else lca = findLCA(lca, pred);
            }
            idom[v] = lca;
        }
        
        return idom;
    }
    
private:
    // LCA using binary lifting (simplified for demonstration)
    int findLCA(int u, int v) {
        // For the simplified version, use the DFS tree parent approach
        // In a full implementation, use binary lifting
        std::vector<int> ancestors_u, ancestors_v;
        
        // Collect ancestors of u
        int cur = u;
        while (cur != -1 && cur != idom[cur]) {
            ancestors_u.push_back(cur);
            cur = idom[cur];
        }
        if (cur != -1) ancestors_u.push_back(cur);
        
        // Collect ancestors of v
        cur = v;
        while (cur != -1 && cur != idom[cur]) {
            ancestors_v.push_back(cur);
            cur = idom[cur];
        }
        if (cur != -1) ancestors_v.push_back(cur);
        
        // Find LCA by comparing from root
        std::reverse(ancestors_u.begin(), ancestors_u.end());
        std::reverse(ancestors_v.begin(), ancestors_v.end());
        
        int lca = -1;
        int i = 0, j = 0;
        while (i < (int)ancestors_u.size() && j < (int)ancestors_v.size()
               && ancestors_u[i] == ancestors_v[j]) {
            lca = ancestors_u[i];
            i++; j++;
        }
        return lca;
    }
};

int main() {
    DominatorTree dt(6);
    dt.addEdge(0, 1); dt.addEdge(0, 2);
    dt.addEdge(1, 3); dt.addEdge(2, 3);
    dt.addEdge(3, 4); dt.addEdge(3, 5);
    
    auto idom = dt.build(0);
    std::cout << "Dominator tree (idom[v] = parent in dom tree):\n";
    for (int i = 0; i < 6; i++)
        std::cout << "  idom[" << i << "] = " << idom[i] << "\n";
    
    return 0;
}
```

### Python: Simplified Dominator Tree for DAGs

```python
from collections import defaultdict

class DominatorTree:
    def __init__(self, n):
        self.n = n
        self.adj = defaultdict(list)
        self.rev = defaultdict(list)
        self.idom = [-1] * n
    
    def add_edge(self, u, v):
        self.adj[u].append(v)
        self.rev[v].append(u)
    
    def build(self, root):
        """Build dominator tree for DAG."""
        # DFS to get order
        visited = [False] * self.n
        dfs_order = []
        dfs_num = [-1] * self.n
        counter = [0]
        
        def dfs(u):
            visited[u] = True
            dfs_num[u] = counter[0]
            counter[0] += 1
            dfs_order.append(u)
            for v in self.adj[u]:
                if not visited[v]:
                    dfs(v)
        
        dfs(root)
        
        # Compute idom
        self.idom[root] = root
        
        def get_ancestors(node):
            ancestors = []
            cur = node
            while cur != -1 and cur != self.idom[cur]:
                ancestors.append(cur)
                cur = self.idom[cur]
            if cur != -1:
                ancestors.append(cur)
            ancestors.reverse()
            return ancestors
        
        def lca(u, v):
            au = get_ancestors(u)
            av = get_ancestors(v)
            result = -1
            i = j = 0
            while i < len(au) and j < len(av) and au[i] == av[j]:
                result = au[i]
                i += 1
                j += 1
            return result
        
        for idx in range(1, len(dfs_order)):
            v = dfs_order[idx]
            preds = [p for p in self.rev[v] if dfs_num[p] >= 0]
            if not preds:
                continue
            self.idom[v] = preds[0]
            for p in preds[1:]:
                self.idom[v] = lca(self.idom[v], p)
        
        return self.idom

# Example
dt = DominatorTree(6)
dt.add_edge(0, 1); dt.add_edge(0, 2)
dt.add_edge(1, 3); dt.add_edge(2, 3)
dt.add_edge(3, 4); dt.add_edge(3, 5)

idom = dt.build(0)
print("Dominator tree (idom[v] = parent in dom tree):")
for i in range(6):
    print(f"  idom[{i}] = {idom[i]}")
```

### Java: Simplified Dominator Tree for DAGs

```java
import java.util.*;

public class DominatorTree {
    int n;
    List<List<Integer>> adj, rev;
    int[] idom;

    public DominatorTree(int n) {
        this.n = n;
        this.adj = new ArrayList<>();
        this.rev = new ArrayList<>();
        this.idom = new int[n];
        Arrays.fill(idom, -1);
        for (int i = 0; i < n; i++) {
            adj.add(new ArrayList<>());
            rev.add(new ArrayList<>());
        }
    }

    void addEdge(int u, int v) {
        adj.get(u).add(v);
        rev.get(v).add(u);
    }

    int[] build(int root) {
        boolean[] visited = new boolean[n];
        int[] dfsNum = new int[n];
        Arrays.fill(dfsNum, -1);
        List<Integer> dfsOrder = new ArrayList<>();
        int[] counter = {0};

        dfs(root, visited, dfsNum, dfsOrder, counter);
        idom[root] = root;

        for (int idx = 1; idx < dfsOrder.size(); idx++) {
            int v = dfsOrder.get(idx);
            int lca = -1;
            for (int pred : rev.get(v)) {
                if (dfsNum[pred] < 0) continue;
                if (lca == -1) lca = pred;
                else lca = findLCA(lca, pred);
            }
            idom[v] = lca;
        }
        return idom;
    }

    void dfs(int u, boolean[] visited, int[] dfsNum, List<Integer> order, int[] counter) {
        visited[u] = true;
        dfsNum[u] = counter[0]++;
        order.add(u);
        for (int v : adj.get(u))
            if (!visited[v]) dfs(v, visited, dfsNum, order, counter);
    }

    int findLCA(int u, int v) {
        List<Integer> au = getAncestors(u), av = getAncestors(v);
        int result = -1, i = 0, j = 0;
        while (i < au.size() && j < av.size() && au.get(i).equals(av.get(j))) {
            result = au.get(i); i++; j++;
        }
        return result;
    }

    List<Integer> getAncestors(int node) {
        List<Integer> ancestors = new ArrayList<>();
        int cur = node;
        while (cur != -1 && cur != idom[cur]) {
            ancestors.add(cur);
            cur = idom[cur];
        }
        if (cur != -1) ancestors.add(cur);
        Collections.reverse(ancestors);
        return ancestors;
    }

    public static void main(String[] args) {
        DominatorTree dt = new DominatorTree(6);
        dt.addEdge(0, 1); dt.addEdge(0, 2);
        dt.addEdge(1, 3); dt.addEdge(2, 3);
        dt.addEdge(3, 4); dt.addEdge(3, 5);
        int[] idom = dt.build(0);
        for (int i = 0; i < 6; i++)
            System.out.println("idom[" + i + "] = " + idom[i]);
    }
}
```

---

## 110.7 Dominance Frontiers

The **dominance frontier** of node x is the set of nodes w such that:
- x dominates a predecessor of w, but
- x does not strictly dominate w

**Formula:** DF(x) = {w | ∃ pred p of w: x dom p, but ¬(x strict dom w)}

**Use in SSA:** Dominance frontiers determine where to place φ-functions (merge points) in SSA form.

```cpp
// Compute dominance frontiers
std::vector<std::vector<int>> computeDF(
    const std::vector<std::vector<int>>& adj,
    const std::vector<std::vector<int>>& rev,
    const std::vector<int>& idom, int n) {
    
    std::vector<std::vector<int>> df(n);
    
    for (int v = 0; v < n; v++) {
        for (int pred : rev[v]) {
            int runner = pred;
            while (runner != idom[v] && runner != -1) {
                df[runner].push_back(v);
                runner = idom[runner];
            }
        }
    }
    
    return df;
}
```

---

## 110.8 Lengauer-Tarjan Algorithm (Full)

The full algorithm uses path compression (union-find style) for efficiency.

### Key Data Structures
- `semi[v]`: Semi-dominator of v
- `idom[v]`: Immediate dominator of v
- `ancestor[v]`: Ancestor in DFS tree (for path compression)
- `label[v]`: Best candidate for semi-dominator during path compression
- `bucket[v]`: Set of nodes whose semi-dominator is v

### Pseudocode
```
DFS(root):
    for each node v in reverse DFS order:
        for each predecessor u of v:
            semi[v] = min(semi[v], semi[eval(u)])
        bucket[semi[v]].add(v)
        link(parent[v], v)
        for each w in bucket[parent[v]]:
            u = eval(w)
            idom[w] = (semi[u] < semi[w]) ? u : parent[v]
```

### Complexity
- **Time:** O((V + E) × α(V)) with union-find
- **Space:** O(V + E)

---

## 110.9 Applications

### 1. Natural Loop Detection
A **natural loop** is identified by a back edge (v → u) where u dominates v. The loop body consists of u and all nodes that can reach v without going through u.

### 2. Control Dependence
Node y is **control dependent** on node x if:
- x has multiple successors
- There exists a path from x to y that doesn't go through other control-dependent nodes

### 3. SSA Construction
```
1. Compute dominator tree
2. Compute dominance frontiers
3. Place φ-functions at dominance frontier iterates
4. Rename variables using dominator tree traversal
```

### 4. Critical Edge Elimination
A **critical edge** connects a node with multiple successors to a node with multiple predecessors. Dominator analysis helps identify and split these edges.

---

## 110.10 Exercises

### Exercise 1: Build a Dominator Tree
Given the graph: 0→1, 0→2, 1→3, 2→3, 3→4, 3→5, 5→6, 4→6
Build the dominator tree by hand.

### Exercise 2: Find Natural Loops
Using the dominator tree from Exercise 1, identify all back edges and their corresponding natural loops.

### Exercise 3: Implement Full Lengauer-Tarjan
Implement the full Lengauer-Tarjan algorithm with path compression. Test on graphs with 100+ nodes.

### Exercise 4: Dominance Frontier
Compute the dominance frontier for each node in the graph from Exercise 1.

### Exercise 5: Application - Critical Nodes
Given a flowgraph, find all nodes that are dominators of at least k other nodes. These are "critical" nodes.

---

## 110.11 Interview Questions

### Q1: What is a dominator tree?
**A:** A tree where node d is an ancestor of node v if every path from the root to v must pass through d. Each node's parent is its immediate dominator (closest dominator).

### Q2: How do you compute dominator trees?
**A:** For DAGs: compute LCA of all predecessors incrementally. For general graphs: use Lengauer-Tarjan algorithm which runs in nearly O(V+E) time using path compression.

### Q3: What's the relationship between dominators and loops?
**A:** A back edge (v → u) exists only if u dominates v. The natural loop of this back edge consists of u and all nodes that can reach v without passing through u.

### Q4: How are dominator trees used in compilers?
**A:** They're essential for SSA construction (placing φ-functions at dominance frontiers), code motion (ensuring computations are hoisted safely), and loop optimization.

### Q5: What's the time complexity of computing dominator trees?
**A:** O((V+E) × α(V)) using Lengauer-Tarjan, where α is the inverse Ackermann function. For practical purposes, this is O(V+E). For DAGs, a simpler O(V+E) algorithm exists.

---

## 110.12 Cross-References

| Topic | Related Chapter |
|---|---|
| DFS | Chapter 40 |
| SCC (Tarjan's) | Chapter 45 |
| LCA (Lowest Common Ancestor) | Chapter 65 |
| Union-Find | Chapter 35 |
| Topological Sort | Chapter 42 |
| Control Flow Graphs | Chapter 120 |
| SSA Form | Chapter 122 |

---

## Summary

| Property | Value |
|---|---|
| Definition | d dom v if all paths from root to v pass through d |
| Tree structure | Each node has one immediate dominator |
| Build (DAG) | O(V + E) using LCA of predecessors |
| Build (general) | O((V + E) α(V)) via Lengauer-Tarjan |
| Applications | Compiler optimization, SSA, loop detection |
| Key derivative | Dominance frontier for SSA φ-placement |

**Key Insight:** Dominator trees answer "which nodes must I pass through?" — a fundamental question in control flow analysis. Understanding dominators is essential for anyone working on compilers, program analysis, or advanced graph problems.
