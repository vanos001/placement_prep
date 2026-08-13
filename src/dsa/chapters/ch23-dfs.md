# Chapter 23: Depth-First Search

Depth-First Search (DFS) is one of the two fundamental graph traversal algorithms. It explores as far as possible along each branch before backtracking. DFS is the backbone of countless algorithms: cycle detection, topological sorting, finding connected components, solving mazes, and more.

In this chapter, we build DFS from the ground up — recursive and iterative implementations, applications on graphs and grids, cycle detection, and the classification of edges that makes DFS so powerful for analysis.

---

## 23.1 DFS Algorithm

### Core Idea

DFS uses a **stack** (either the call stack via recursion, or an explicit stack data structure) to explore vertices depth-first:

1. Start at a source vertex. Mark it visited.
2. For each unvisited neighbor, recursively visit it.
3. When all neighbors are explored, backtrack.

### Recursive DFS

```cpp
#include <iostream>
#include <vector>

void dfs(int u, const std::vector<std::vector<int>>& adj,
         std::vector<bool>& visited) {
    visited[u] = true;
    std::cout << u << " "; // process vertex u

    for (int v : adj[u]) {
        if (!visited[v]) {
            dfs(v, adj, visited);
        }
    }
}

int main() {
    int V = 6;
    std::vector<std::vector<int>> adj(V);
    auto addEdge = [&](int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    };
    addEdge(0, 1);
    addEdge(0, 2);
    addEdge(1, 3);
    addEdge(1, 4);
    addEdge(2, 4);
    addEdge(4, 5);

    std::vector<bool> visited(V, false);
    std::cout << "DFS from 0: ";
    dfs(0, adj, visited);
    std::cout << "\n";
    // Output: 0 1 3 4 2 5  (order depends on adjacency list order)
}
```

### Iterative DFS with Explicit Stack

```cpp
#include <iostream>
#include <vector>
#include <stack>

void dfsIterative(int start, const std::vector<std::vector<int>>& adj,
                  std::vector<bool>& visited) {
    std::stack<int> stk;
    stk.push(start);

    while (!stk.empty()) {
        int u = stk.top();
        stk.pop();

        if (visited[u]) continue;
        visited[u] = true;
        std::cout << u << " "; // process vertex u

        // Push neighbors in reverse order to maintain same order as recursive
        for (int i = (int)adj[u].size() - 1; i >= 0; --i) {
            int v = adj[u][i];
            if (!visited[v]) {
                stk.push(v);
            }
        }
    }
}
```

**Important note:** The iterative version with a stack does *not* produce exactly the same traversal order as the recursive version in all cases. The recursive version marks a vertex as visited when it's *first discovered* (before exploring neighbors), while the iterative version marks it when it's *popped* from the stack. This means a vertex might be pushed multiple times. Use a `visited` check when popping to handle this.

**Time Complexity:** \\(O(V + E)\\) — every vertex is visited once, every edge is examined once (twice for undirected).

**Space Complexity:** \\(O(V)\\) for the visited array + \\(O(V)\\) for the stack (worst case: a path graph).

### Dry Run

Graph: `0-1-3, 0-2, 1-4, 2-4, 4-5`

Recursive DFS from vertex 0 (neighbors sorted ascending):

| Step | Current | Stack (call) | Visited | Action |
|------|---------|-------------|---------|--------|
| 1 | 0 | dfs(0) | {0} | Visit 0, recurse on 1 |
| 2 | 1 | dfs(0)→dfs(1) | {0,1} | Visit 1, recurse on 3 |
| 3 | 3 | dfs(0)→dfs(1)→dfs(3) | {0,1,3} | Visit 3, no unvisited neighbors |
| 4 | 1 | dfs(0)→dfs(1) | {0,1,3} | Backtrack to 1, recurse on 4 |
| 5 | 4 | dfs(0)→dfs(1)→dfs(4) | {0,1,3,4} | Visit 4, recurse on 2 |
| 6 | 2 | ...→dfs(4)→dfs(2) | {0,1,3,4,2} | Visit 2, no new neighbors (0 visited) |
| 7 | 4 | ...→dfs(4) | {0,1,3,4,2} | Backtrack to 4, recurse on 5 |
| 8 | 5 | ...→dfs(4)→dfs(5) | {0,1,3,4,2,5} | Visit 5, done |

Traversal order: **0 1 3 4 2 5**

---

## 23.2 DFS on Graphs

### Visited Array

The `visited` array is the heart of DFS. Without it, DFS would loop infinitely on cycles. Each vertex is visited exactly once.

```cpp
#include <iostream>
#include <vector>

class GraphDFS {
    int V;
    std::vector<std::vector<int>> adj;
    std::vector<bool> visited;
    std::vector<int> discovery;  // time when vertex is first discovered
    std::vector<int> finish;     // time when all descendants are processed
    int timer;

public:
    GraphDFS(int V) : V(V), adj(V), visited(V, false),
                      discovery(V), finish(V), timer(0) {}

    void addEdge(int u, int v) {
        adj[u].push_back(v);
        // adj[v].push_back(u); // uncomment for undirected
    }

    void dfs(int u) {
        visited[u] = true;
        discovery[u] = timer++;
        std::cout << "Discovered " << u << " at time " << discovery[u] << "\n";

        for (int v : adj[u]) {
            if (!visited[v]) {
                dfs(v);
            }
        }

        finish[u] = timer++;
        std::cout << "Finished " << u << " at time " << finish[u] << "\n";
    }

    void traverse() {
        for (int i = 0; i < V; ++i) {
            if (!visited[i]) {
                dfs(i);
            }
        }
    }
};

int main() {
    GraphDFS g(6);
    g.addEdge(0, 1);
    g.addEdge(0, 2);
    g.addEdge(1, 3);
    g.addEdge(3, 4);
    g.addEdge(2, 4);
    g.traverse();
}
```

### Traversal vs Search

- **Traversal**: Visit *all* vertices reachable from the source (or all vertices in the graph).
- **Search**: Stop as soon as the target is found.

```cpp
#include <iostream>
#include <vector>

bool dfsSearch(int u, int target, const std::vector<std::vector<int>>& adj,
               std::vector<bool>& visited) {
    if (u == target) return true; // found!
    visited[u] = true;
    for (int v : adj[u]) {
        if (!visited[v] && dfsSearch(v, target, adj, visited)) {
            return true;
        }
    }
    return false;
}
```

---

## 23.3 DFS on Grids

A 2D grid is a graph where each cell \\((i, j)\\) is a vertex connected to its neighbors (up, down, left, right, and optionally diagonals).

### Grid DFS Template

```cpp
#include <iostream>
#include <vector>
#include <string>

const int dx[] = {-1, 1, 0, 0};
const int dy[] = {0, 0, -1, 1};

void dfsGrid(int x, int y, const std::vector<std::string>& grid,
             std::vector<std::vector<bool>>& visited, int rows, int cols) {
    visited[x][y] = true;
    // Process cell (x, y)

    for (int d = 0; d < 4; ++d) {
        int nx = x + dx[d], ny = y + dy[d];
        if (nx >= 0 && nx < rows && ny >= 0 && ny < cols &&
            !visited[nx][ny] && grid[nx][ny] == '1') { // condition
            dfsGrid(nx, ny, grid, visited, rows, cols);
        }
    }
}
```

### Flood Fill

The classic "paint bucket" tool: given a starting cell, change all connected cells of the same color.

```cpp
#include <iostream>
#include <vector>

class Solution {
public:
    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};

    void dfs(std::vector<std::vector<int>>& image, int x, int y,
             int oldColor, int newColor, int rows, int cols) {
        image[x][y] = newColor;
        for (int d = 0; d < 4; ++d) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx >= 0 && nx < rows && ny >= 0 && ny < cols &&
                image[nx][ny] == oldColor) {
                dfs(image, nx, ny, oldColor, newColor, rows, cols);
            }
        }
    }

    std::vector<std::vector<int>> floodFill(std::vector<std::vector<int>>& image,
                                             int sr, int sc, int newColor) {
        int oldColor = image[sr][sc];
        if (oldColor != newColor) {
            dfs(image, sr, sc, oldColor, newColor, image.size(), image[0].size());
        }
        return image;
    }
};
```

**Time:** \\(O(R \times C)\\) — each cell visited at most once.

### Connected Components in Grid

```cpp
#include <iostream>
#include <vector>
#include <string>

int countIslands(std::vector<std::string>& grid) {
    int rows = grid.size(), cols = grid[0].size();
    int count = 0;
    const int dx[] = {-1, 1, 0, 0};
    const int dy[] = {0, 0, -1, 1};

    std::function<void(int, int)> dfs = [&](int x, int y) {
        grid[x][y] = '0'; // mark visited by modifying in-place
        for (int d = 0; d < 4; ++d) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx >= 0 && nx < rows && ny >= 0 && ny < cols && grid[nx][ny] == '1') {
                dfs(nx, ny);
            }
        }
    };

    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            if (grid[i][j] == '1') {
                dfs(i, j);
                count++;
            }
        }
    }
    return count;
}
```

---

## 23.4 Connected Components

A **connected component** is a maximal set of vertices where every pair is connected by a path.

### Counting Components

```cpp
#include <iostream>
#include <vector>

void dfs(int u, const std::vector<std::vector<int>>& adj,
         std::vector<int>& component, int compId) {
    component[u] = compId;
    for (int v : adj[u]) {
        if (component[v] == -1) {
            dfs(v, adj, component, compId);
        }
    }
}

int main() {
    int V = 7;
    std::vector<std::vector<int>> adj(V);
    auto addEdge = [&](int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    };

    // Component 0: {0, 1, 2}
    addEdge(0, 1); addEdge(1, 2);
    // Component 1: {3, 4}
    addEdge(3, 4);
    // Component 2: {5, 6}
    addEdge(5, 6);

    std::vector<int> component(V, -1);
    int compCount = 0;
    for (int i = 0; i < V; ++i) {
        if (component[i] == -1) {
            dfs(i, adj, component, compCount);
            compCount++;
        }
    }

    std::cout << "Number of components: " << compCount << "\n";
    for (int i = 0; i < V; ++i) {
        std::cout << "Vertex " << i << " -> Component " << component[i] << "\n";
    }
}
```

### Component Labeling with Sizes

```cpp
#include <iostream>
#include <vector>

int dfsSize(int u, const std::vector<std::vector<int>>& adj,
            std::vector<bool>& visited) {
    visited[u] = true;
    int size = 1;
    for (int v : adj[u]) {
        if (!visited[v]) {
            size += dfsSize(v, adj, visited);
        }
    }
    return size;
}

std::vector<int> componentSizes(const std::vector<std::vector<int>>& adj, int V) {
    std::vector<bool> visited(V, false);
    std::vector<int> sizes;
    for (int i = 0; i < V; ++i) {
        if (!visited[i]) {
            sizes.push_back(dfsSize(i, adj, visited));
        }
    }
    return sizes;
}
```

---

## 23.5 Cycle Detection

### Undirected Graphs

In an undirected graph, a cycle exists if during DFS we encounter a visited vertex that is **not the parent** of the current vertex.

```cpp
#include <iostream>
#include <vector>

bool hasCycleUndirected(int u, int parent,
                        const std::vector<std::vector<int>>& adj,
                        std::vector<bool>& visited) {
    visited[u] = true;
    for (int v : adj[u]) {
        if (!visited[v]) {
            if (hasCycleUndirected(v, u, adj, visited)) return true;
        } else if (v != parent) {
            return true; // back edge found → cycle!
        }
    }
    return false;
}

bool detectCycleUndirected(const std::vector<std::vector<int>>& adj, int V) {
    std::vector<bool> visited(V, false);
    for (int i = 0; i < V; ++i) {
        if (!visited[i]) {
            if (hasCycleUndirected(i, -1, adj, visited)) return true;
        }
    }
    return false;
}
```

### Directed Graphs

In a directed graph, we track vertices currently **in the recursion stack**. If we encounter a vertex that's in the current recursion stack, we've found a cycle.

```cpp
#include <iostream>
#include <vector>

enum Color { WHITE, GRAY, BLACK };

bool hasCycleDirected(int u, const std::vector<std::vector<int>>& adj,
                      std::vector<Color>& color) {
    color[u] = GRAY; // currently being processed
    for (int v : adj[u]) {
        if (color[v] == GRAY) return true;  // back edge → cycle
        if (color[v] == WHITE && hasCycleDirected(v, adj, color)) return true;
    }
    color[u] = BLACK; // fully processed
    return false;
}

bool detectCycleDirected(const std::vector<std::vector<int>>& adj, int V) {
    std::vector<Color> color(V, WHITE);
    for (int i = 0; i < V; ++i) {
        if (color[i] == WHITE) {
            if (hasCycleDirected(i, adj, color)) return true;
        }
    }
    return false;
}
```

**Why the difference?** In an undirected graph, the edge \\((u, v)\\) and \\((v, u)\\) are the same edge. So seeing the parent via the same edge is not a cycle. In a directed graph, \\(u \to v\\) and \\(v \to u\\) are different edges, so encountering a GRAY vertex means a genuine back edge.

---

## 23.6 DFS Trees

When we run DFS on a graph, the edges traversed form a **DFS tree** (or **DFS forest** if the graph is disconnected). The edges of the original graph that are *not* in the DFS tree are classified into three types.

### Edge Classification

For a directed graph with discovery time \\(d[u]\\) and finish time \\(f[u]\\):

| Edge Type | Definition | Condition |
|-----------|-----------|-----------|
| **Tree edge** | Part of the DFS tree | \\(v\\) is WHITE when \\((u,v)\\) is explored |
| **Back edge** | Points to an ancestor | \\(v\\) is GRAY (in current path) |
| **Forward edge** | Points to a proper descendant | \\(v\\) is BLACK, \\(d[u] < d[v]\\) |
| **Cross edge** | Everything else | \\(v\\) is BLACK, \\(d[u] > d[v]\\) |

For **undirected graphs**, only tree edges and back edges exist (forward and cross edges cannot occur because if \\((u,v)\\) exists, DFS would have traversed it in one direction as a tree edge).

```cpp
#include <iostream>
#include <vector>

enum Color { WHITE, GRAY, BLACK };
enum EdgeType { TREE, BACK, FORWARD, CROSS };

class DFSAnalyzer {
    int V;
    std::vector<std::vector<int>> adj;
    std::vector<Color> color;
    std::vector<int> d, f;
    int timer;

public:
    DFSAnalyzer(int V) : V(V), adj(V), color(V, WHITE), d(V), f(V), timer(0) {}

    void addEdge(int u, int v) { adj[u].push_back(v); }

    void dfsVisit(int u) {
        color[u] = GRAY;
        d[u] = timer++;

        for (int v : adj[u]) {
            if (color[v] == WHITE) {
                std::cout << "Tree edge: " << u << " -> " << v << "\n";
                dfsVisit(v);
            } else if (color[v] == GRAY) {
                std::cout << "Back edge: " << u << " -> " << v << "\n";
            } else if (color[v] == BLACK) {
                if (d[u] < d[v]) {
                    std::cout << "Forward edge: " << u << " -> " << v << "\n";
                } else {
                    std::cout << "Cross edge: " << u << " -> " << v << "\n";
                }
            }
        }

        color[u] = BLACK;
        f[u] = timer++;
    }

    void analyze() {
        for (int i = 0; i < V; ++i) {
            if (color[i] == WHITE) dfsVisit(i);
        }
        std::cout << "\nDiscovery/Finish times:\n";
        for (int i = 0; i < V; ++i) {
            std::cout << "  " << i << ": d=" << d[i] << " f=" << f[i] << "\n";
        }
    }
};

int main() {
    DFSAnalyzer g(6);
    g.addEdge(0, 1);
    g.addEdge(0, 2);
    g.addEdge(1, 3);
    g.addEdge(1, 4);
    g.addEdge(2, 4);
    g.addEdge(4, 5);
    g.addEdge(3, 0); // back edge creating a cycle
    g.analyze();
}
```

---

## 23.7 Back Edges and Cross Edges

### Back Edges

A back edge \\((u, v)\\) points from a vertex \\(u\\) to an ancestor \\(v\\) in the DFS tree. **Back edges are the only source of cycles in directed graphs.** If there are no back edges, the graph is a DAG.

**Key insight:** A directed graph has a cycle **if and only if** DFS finds a back edge.

**Why forward edges and cross edges don't create cycles:**
- A forward edge \\((u, v)\\) skips intermediate descendants but follows the tree direction. It doesn't create a cycle because \\(v\\) is already a descendant of \\(u\\).
- A cross edge \\((u, v)\\) connects vertices in different subtrees. Since \\(v\\) was already fully processed (BLACK), there's no path from \\(v\\) back to \\(u\\).

### Cross Edges

Cross edges connect vertices where neither is an ancestor of the other. They often appear between different branches of the DFS tree.

**In undirected graphs**, every non-tree edge is a back edge. Cross and forward edges don't exist because the DFS would have discovered the vertex through that edge first.

### Parenthesis Theorem

For any two vertices \\(u\\) and \\(v\\), exactly one of the following holds:

1. \\([d[u], f[u]]\\) and \\([d[v], f[v]]\\) are entirely disjoint (neither is an ancestor).
2. \\([d[u], f[u]] \subset [d[v], f[v]]\\) (\\(u\\) is a descendant of \\(v\\)).
3. \\([d[v], f[v]] \subset [d[u], f[u]]\\) (\\(v\\) is a descendant of \\(u\\)).

This is called the **parenthesis theorem** because the discovery and finish times behave like matched parentheses.

---

## Interview Tips

1. **Recursive DFS can stack overflow** on very deep graphs (e.g., a path of \\(10^5\\) nodes). Use iterative DFS for large inputs.
2. **Modify the grid in-place** when allowed to save memory on visited arrays.
3. **Use the 3-color approach** (WHITE/GRAY/BLACK) for cycle detection in directed graphs — don't use the undirected parent trick.
4. **Count connected components** before doing anything else — many problems require this as a preprocessing step.
5. **For grid problems**, always check bounds before accessing neighbors.

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Using parent check for directed cycle detection | Misses cycles through non-parent ancestors | Use 3-color (WHITE/GRAY/BLACK) |
| Not handling disconnected graph | Misses components | Outer loop over all vertices |
| Stack overflow on deep recursion | Runtime error | Use iterative DFS or increase stack |
| Forgetting to mark visited before recursive call | Infinite loop / re-visiting | Mark at entry, not after |
| Wrong neighbor order | Wrong traversal order | Push neighbors in reverse for iterative |

## Practice Problems

### Number of Islands (LeetCode 200)

**Problem:** Given a 2D grid of `'1'`s (land) and `'0'`s (water), count the number of islands. An island is formed by connecting adjacent lands horizontally or vertically.

```cpp
#include <vector>
#include <string>

class Solution {
public:
    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};

    void dfs(std::vector<std::vector<char>>& grid, int x, int y) {
        grid[x][y] = '0'; // mark visited
        for (int d = 0; d < 4; ++d) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx >= 0 && nx < (int)grid.size() && ny >= 0 && ny < (int)grid[0].size()
                && grid[nx][ny] == '1') {
                dfs(grid, nx, ny);
            }
        }
    }

    int numIslands(std::vector<std::vector<char>>& grid) {
        if (grid.empty()) return 0;
        int count = 0;
        for (int i = 0; i < (int)grid.size(); ++i) {
            for (int j = 0; j < (int)grid[0].size(); ++j) {
                if (grid[i][j] == '1') {
                    dfs(grid, i, j);
                    count++;
                }
            }
        }
        return count;
    }
};
```

### Clone Graph (LeetCode 133)

**Problem:** Given a reference to a node in a connected undirected graph, return a deep copy.

```cpp
#include <vector>
#include <unordered_map>

class Node {
public:
    int val;
    std::vector<Node*> neighbors;
    Node(int v) : val(v) {}
};

class Solution {
public:
    std::unordered_map<Node*, Node*> cloned;

    Node* cloneGraph(Node* node) {
        if (!node) return nullptr;
        if (cloned.count(node)) return cloned[node];

        cloned[node] = new Node(node->val);
        for (Node* neighbor : node->neighbors) {
            cloned[node]->neighbors.push_back(cloneGraph(neighbor));
        }
        return cloned[node];
    }
};
```

### Course Schedule (LeetCode 207)

**Problem:** There are `numCourses` courses. Some have prerequisites `[a, b]` meaning "take `b` before `a`". Determine if you can finish all courses (i.e., no cycle in the dependency graph).

```cpp
#include <vector>

class Solution {
public:
    bool dfs(int u, const std::vector<std::vector<int>>& adj,
             std::vector<int>& state) {
        state[u] = 1; // GRAY
        for (int v : adj[u]) {
            if (state[v] == 1) return false;  // cycle
            if (state[v] == 0 && !dfs(v, adj, state)) return false;
        }
        state[u] = 2; // BLACK
        return true;
    }

    bool canFinish(int numCourses, std::vector<std::vector<int>>& prerequisites) {
        std::vector<std::vector<int>> adj(numCourses);
        for (auto& p : prerequisites) {
            adj[p[1]].push_back(p[0]); // b -> a
        }
        std::vector<int> state(numCourses, 0);
        for (int i = 0; i < numCourses; ++i) {
            if (state[i] == 0 && !dfs(i, adj, state)) return false;
        }
        return true;
    }
};
```

### Path Sum III (LeetCode 437)

**Problem:** Given a binary tree and a target sum, count the number of paths where the sum of node values equals the target. Paths can start and end at any node.

```cpp
#include <unordered_map>

struct TreeNode {
    int val;
    TreeNode *left, *right;
    TreeNode(int v) : val(v), left(nullptr), right(nullptr) {}
};

class Solution {
public:
    int count = 0;
    std::unordered_map<long long, int> prefixSum;

    void dfs(TreeNode* node, int targetSum, long long currentSum) {
        if (!node) return;

        currentSum += node->val;
        if (prefixSum.count(currentSum - targetSum)) {
            count += prefixSum[currentSum - targetSum];
        }

        prefixSum[currentSum]++;
        dfs(node->left, targetSum, currentSum);
        dfs(node->right, targetSum, currentSum);
        prefixSum[currentSum]--; // backtrack
    }

    int pathSum(TreeNode* root, int targetSum) {
        prefixSum[0] = 1;
        dfs(root, targetSum, 0);
        return count;
    }
};
```

---

## See Also

- [Chapter 24: Breadth-First Search](ch24-bfs.md) — The complementary traversal; BFS finds shortest paths in unweighted graphs, DFS excels at exhaustive search and backtracking.
- [Chapter 25: Topological Sort](ch25-topological-sort.md) — A direct application of DFS on DAGs; produces a linear ordering respecting edge directions.
- [Chapter 81: SCC, Bridges, and Articulation Points](ch81-scc-bridges.md) — Tarjan's algorithm uses DFS timestamps and low-link values to find strongly connected components, bridges, and cut vertices.
- [Chapter 22: Graph Fundamentals](ch22-graph-fundamentals.md) — Prerequisite: adjacency lists, graph representations, and basic terminology.
- [Chapter 9: Backtracking](ch09-backtracking.md) — DFS with backtracking is the foundation of constraint satisfaction and combinatorial search.

*Next chapter: Breadth-First Search — the level-by-level exploration that finds shortest paths in unweighted graphs.*
