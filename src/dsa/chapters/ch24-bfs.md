# Chapter 24: Breadth-First Search

Breadth-First Search (BFS) is the second fundamental graph traversal algorithm. While DFS dives deep, BFS explores level by level — visiting all vertices at distance \\(k\\) before any vertex at distance \\(k+1\\). This makes BFS the natural choice for finding shortest paths in unweighted graphs and solving problems that involve "minimum number of steps."

In this chapter, we cover BFS from the ground up, including its application to graphs, grids, multi-source scenarios, and the 0-1 BFS variant.

---

## 24.1 BFS Algorithm

### Core Idea

BFS uses a **queue** (FIFO) to explore vertices in the order they are discovered:

1. Enqueue the source vertex. Mark it visited.
2. While the queue is not empty:
   a. Dequeue a vertex \\(u\\).
   b. For each unvisited neighbor \\(v\\) of \\(u\\): mark \\(v\\) visited, enqueue \\(v\\).
3. Process vertices in dequeue order.

### Complete Implementation

```cpp
#include <iostream>
#include <vector>
#include <queue>

std::vector<int> bfs(int start, const std::vector<std::vector<int>>& adj, int V) {
    std::vector<int> dist(V, -1); // -1 means unreachable
    std::queue<int> q;

    dist[start] = 0;
    q.push(start);

    while (!q.empty()) {
        int u = q.front();
        q.pop();

        for (int v : adj[u]) {
            if (dist[v] == -1) { // not visited
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
    return dist;
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

    std::vector<int> dist = bfs(0, adj, V);
    for (int i = 0; i < V; ++i) {
        std::cout << "Distance from 0 to " << i << ": " << dist[i] << "\n";
    }
}
```

**Time Complexity:** \\(O(V + E)\\) — each vertex is enqueued once, each edge is examined once.

**Space Complexity:** \\(O(V)\\) for the queue and distance array.

### BFS with Path Reconstruction

```cpp
#include <iostream>
#include <vector>
#include <queue>

std::vector<int> bfsPath(int start, int end,
                         const std::vector<std::vector<int>>& adj, int V) {
    std::vector<int> dist(V, -1), parent(V, -1);
    std::queue<int> q;

    dist[start] = 0;
    q.push(start);

    while (!q.empty()) {
        int u = q.front();
        q.pop();
        if (u == end) break;

        for (int v : adj[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                parent[v] = u;
                q.push(v);
            }
        }
    }

    // Reconstruct path from end to start
    std::vector<int> path;
    if (dist[end] == -1) return path; // no path
    for (int cur = end; cur != -1; cur = parent[cur]) {
        path.push_back(cur);
    }
    std::reverse(path.begin(), path.end());
    return path;
}
```

### Dry Run

Graph: `0-1, 0-2, 1-3, 1-4, 2-4, 4-5`. BFS from vertex 0.

| Step | Queue (front→back) | Dequeued | Discovered | dist[] |
|------|-------------------|----------|------------|--------|
| Init | [0] | — | — | [0,-1,-1,-1,-1,-1] |
| 1 | [1, 2] | 0 | 1, 2 | [0,1,1,-1,-1,-1] |
| 2 | [2, 3, 4] | 1 | 3, 4 | [0,1,1,2,2,-1] |
| 3 | [3, 4] | 2 | (4 already seen) | [0,1,1,2,2,-1] |
| 4 | [4] | 3 | — | [0,1,1,2,2,-1] |
| 5 | [5] | 4 | 5 | [0,1,1,2,2,3] |
| 6 | [] | 5 | — | [0,1,1,2,2,3] |

Result: `dist = [0, 1, 1, 2, 2, 3]`

---

## 24.2 BFS on Graphs

### Why BFS Gives Shortest Paths (Unweighted)

**Theorem:** In an unweighted graph, BFS visits vertices in order of their shortest distance from the source.

**Proof sketch:** By induction on distance. When BFS processes all vertices at distance \\(d\\), their neighbors at distance \\(d+1\\) are enqueued (if not already visited). Since the queue is FIFO, all distance-\\(d\\) vertices are processed before any distance-\\((d+1)\\) vertex. Thus, the first time a vertex is visited, it's via a shortest path.

### Level-Order Traversal

Sometimes you need to process vertices level by level (e.g., for level-order tree traversal or level-aware computations).

```cpp
#include <iostream>
#include <vector>
#include <queue>

std::vector<std::vector<int>> bfsLevels(int start,
                                         const std::vector<std::vector<int>>& adj, int V) {
    std::vector<std::vector<int>> levels;
    std::vector<bool> visited(V, false);
    std::queue<int> q;

    visited[start] = true;
    q.push(start);

    while (!q.empty()) {
        int levelSize = q.size();
        std::vector<int> currentLevel;

        for (int i = 0; i < levelSize; ++i) {
            int u = q.front();
            q.pop();
            currentLevel.push_back(u);

            for (int v : adj[u]) {
                if (!visited[v]) {
                    visited[v] = true;
                    q.push(v);
                }
            }
        }
        levels.push_back(currentLevel);
    }
    return levels;
}
```

### Bipartiteness Check

BFS can check if a graph is bipartite by attempting a 2-coloring.

```cpp
#include <vector>
#include <queue>

bool isBipartite(const std::vector<std::vector<int>>& adj, int V) {
    std::vector<int> color(V, -1);

    for (int start = 0; start < V; ++start) {
        if (color[start] != -1) continue;

        std::queue<int> q;
        color[start] = 0;
        q.push(start);

        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (int v : adj[u]) {
                if (color[v] == -1) {
                    color[v] = 1 - color[u];
                    q.push(v);
                } else if (color[v] == color[u]) {
                    return false;
                }
            }
        }
    }
    return true;
}
```

---

## 24.3 BFS on Grids

Grids are graphs where each cell is a vertex. BFS on grids is extremely common in interviews.

### Shortest Path in Grid

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <utility>

int shortestPathGrid(const std::vector<std::vector<int>>& grid,
                     int sx, int sy, int ex, int ey) {
    int rows = grid.size(), cols = grid[0].size();
    if (grid[sx][sy] == 1 || grid[ex][ey] == 1) return -1; // blocked

    const int dx[] = {-1, 1, 0, 0};
    const int dy[] = {0, 0, -1, 1};

    std::vector<std::vector<int>> dist(rows, std::vector<int>(cols, -1));
    std::queue<std::pair<int, int>> q;

    dist[sx][sy] = 0;
    q.push({sx, sy});

    while (!q.empty()) {
        auto [x, y] = q.front();
        q.pop();

        for (int d = 0; d < 4; ++d) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx >= 0 && nx < rows && ny >= 0 && ny < cols &&
                grid[nx][ny] == 0 && dist[nx][ny] == -1) {
                dist[nx][ny] = dist[x][y] + 1;
                q.push({nx, ny});
            }
        }
    }
    return dist[ex][ey];
}
```

### Maze Problems

BFS is the standard approach for maze shortest-path problems.

```cpp
#include <vector>
#include <queue>
#include <utility>

int mazeShortestPath(const std::vector<std::vector<char>>& maze,
                     std::pair<int, int> start, std::pair<int, int> end) {
    int rows = maze.size(), cols = maze[0].size();
    const int dx[] = {-1, 1, 0, 0};
    const int dy[] = {0, 0, -1, 1};

    std::vector<std::vector<int>> dist(rows, std::vector<int>(cols, -1));
    std::queue<std::pair<int, int>> q;

    dist[start.first][start.second] = 0;
    q.push(start);

    while (!q.empty()) {
        auto [x, y] = q.front();
        q.pop();

        for (int d = 0; d < 4; ++d) {
            // Roll in direction d until hitting a wall
            int nx = x, ny = y;
            while (nx + dx[d] >= 0 && nx + dx[d] < rows &&
                   ny + dy[d] >= 0 && ny + dy[d] < cols &&
                   maze[nx + dx[d]][ny + dy[d]] != '#') {
                nx += dx[d];
                ny += dy[d];
            }
            if (dist[nx][ny] == -1) {
                dist[nx][ny] = dist[x][y] + 1;
                q.push({nx, ny});
            }
        }
    }
    return dist[end.first][end.second];
}
```

---

## 24.4 Multi-Source BFS

In multi-source BFS, we start BFS from multiple source vertices simultaneously. All sources are enqueued initially with distance 0. The BFS then proceeds normally, and the distance array gives the shortest distance from *any* source.

### When to Use Multi-Source BFS

- When you need the minimum distance from a *set* of starting points to all other vertices.
- When the problem says "spread from multiple origins simultaneously."
- When each "level" represents a time step with multiple active cells.

### Rotting Oranges Pattern

The classic multi-source BFS problem: each rotten orange spreads rot to adjacent fresh oranges per minute.

```cpp
#include <vector>
#include <queue>
#include <utility>

class Solution {
public:
    int orangesRotting(std::vector<std::vector<int>>& grid) {
        int rows = grid.size(), cols = grid[0].size();
        const int dx[] = {-1, 1, 0, 0};
        const int dy[] = {0, 0, -1, 1};

        std::queue<std::pair<int, int>> q;
        int fresh = 0;

        // Enqueue all rotten oranges as sources
        for (int i = 0; i < rows; ++i) {
            for (int j = 0; j < cols; ++j) {
                if (grid[i][j] == 2) q.push({i, j});
                else if (grid[i][j] == 1) fresh++;
            }
        }

        if (fresh == 0) return 0;

        int minutes = 0;
        while (!q.empty()) {
            int levelSize = q.size();
            bool spread = false;

            for (int i = 0; i < levelSize; ++i) {
                auto [x, y] = q.front();
                q.pop();

                for (int d = 0; d < 4; ++d) {
                    int nx = x + dx[d], ny = y + dy[d];
                    if (nx >= 0 && nx < rows && ny >= 0 && ny < cols &&
                        grid[nx][ny] == 1) {
                        grid[nx][ny] = 2;
                        fresh--;
                        spread = true;
                        q.push({nx, ny});
                    }
                }
            }
            if (spread) minutes++;
        }

        return fresh == 0 ? minutes : -1;
    }
};
```

### General Multi-Source Template

```cpp
#include <vector>
#include <queue>
#include <utility>

std::vector<std::vector<int>> multiSourceBFS(
    const std::vector<std::pair<int, int>>& sources,
    const std::vector<std::vector<bool>>& blocked,
    int rows, int cols) {

    const int dx[] = {-1, 1, 0, 0};
    const int dy[] = {0, 0, -1, 1};

    std::vector<std::vector<int>> dist(rows, std::vector<int>(cols, -1));
    std::queue<std::pair<int, int>> q;

    for (auto [x, y] : sources) {
        dist[x][y] = 0;
        q.push({x, y});
    }

    while (!q.empty()) {
        auto [x, y] = q.front();
        q.pop();
        for (int d = 0; d < 4; ++d) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx >= 0 && nx < rows && ny >= 0 && ny < cols &&
                !blocked[nx][ny] && dist[nx][ny] == -1) {
                dist[nx][ny] = dist[x][y] + 1;
                q.push({nx, ny});
            }
        }
    }
    return dist;
}
```

---

## 24.5 0-1 BFS

When edge weights are only 0 or 1, we can find shortest paths in \\(O(V + E)\\) using a **deque** instead of a priority queue.

**Idea:** When we relax an edge:
- Weight 0: push to the **front** of the deque (same distance).
- Weight 1: push to the **back** of the deque (distance + 1).

This maintains vertices in sorted order by distance without a priority queue.

```cpp
#include <iostream>
#include <vector>
#include <deque>
#include <utility>
#include <climits>

std::vector<int> bfs01(int start,
                       const std::vector<std::vector<std::pair<int, int>>>& adj, int V) {
    // adj[u] = {v, weight} where weight is 0 or 1
    std::vector<int> dist(V, INT_MAX);
    std::deque<int> dq;

    dist[start] = 0;
    dq.push_front(start);

    while (!dq.empty()) {
        int u = dq.front();
        dq.pop_front();

        for (auto [v, w] : adj[u]) {
            if (dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                if (w == 0) {
                    dq.push_front(v);
                } else {
                    dq.push_back(v);
                }
            }
        }
    }
    return dist;
}

int main() {
    int V = 5;
    std::vector<std::vector<std::pair<int, int>>> adj(V);

    // Build graph with 0-1 weights
    adj[0].push_back({1, 0});
    adj[0].push_back({2, 1});
    adj[1].push_back({2, 0});
    adj[1].push_back({3, 1});
    adj[2].push_back({3, 0});
    adj[3].push_back({4, 1});

    auto dist = bfs01(0, adj, V);
    for (int i = 0; i < V; ++i) {
        std::cout << "dist[" << i << "] = " << dist[i] << "\n";
    }
    // dist = [0, 0, 0, 0, 1]
}
```

**Time Complexity:** \\(O(V + E)\\) — each vertex is pushed to the deque at most twice (once front, once back).

### When to Use 0-1 BFS

- Edge weights are only 0 and 1.
- You want to avoid the \\(O((V+E) \log V)\\) overhead of Dijkstra.
- Common in problems involving "free moves" vs "paid moves" (e.g., toggle a state, flip a character).

---

## 24.6 BFS vs DFS

| Aspect | BFS | DFS |
|--------|-----|-----|
| Data structure | Queue (FIFO) | Stack (LIFO) / Recursion |
| Exploration order | Level by level | Branch by branch |
| Shortest path (unweighted) | ✅ Yes | ❌ No |
| Shortest path (weighted) | ❌ No | ❌ No |
| Space (worst case) | \\(O(V)\\) (wide tree) | \\(O(V)\\) (deep tree) |
| Time | \\(O(V + E)\\) | \\(O(V + E)\\) |
| Cycle detection (undirected) | ✅ | ✅ |
| Topological sort | ✅ (Kahn's) | ✅ |
| Connected components | ✅ | ✅ |
| Best for | Shortest path, levels | Exhaustive search, backtracking |

### When to Use BFS

- Finding **shortest paths** in unweighted graphs.
- Processing vertices **level by level**.
- Problems involving **minimum steps** or **minimum moves**.
- **Multi-source** spreading problems.

### When to Use DFS

- **Exhaustive search** (try all possibilities).
- **Backtracking** problems (N-Queens, Sudoku).
- **Cycle detection** in directed graphs.
- **Topological sort** via post-order.
- When the search space is deep but narrow.
- When you need to track **path state** (e.g., current sum, current path).

---

## Interview Tips

1. **BFS guarantees shortest path** in unweighted graphs. If the graph is weighted, BFS alone won't work — use Dijkstra.
2. **Multi-source BFS** is a common optimization. When the problem asks "minimum time for all X to become Y," think multi-source BFS.
3. **Use `dist` array as visited** — `dist[v] == -1` means not visited. No need for a separate boolean array.
4. **Level-order processing** is critical: count `levelSize` at the start of each level to process all vertices at the same distance together.
5. **0-1 BFS** is a great trick to know — it impresses interviewers and is strictly faster than Dijkstra for 0-1 weights.

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Using BFS for weighted graph shortest path | Wrong answer | Use Dijkstra/Bellman-Ford |
| Not handling disconnected graph | Missing vertices | Loop over all vertices |
| Forgetting to mark visited at enqueue | Duplicate processing | Mark when pushing to queue |
| Using stack instead of queue | DFS behavior, not BFS | Use `std::queue` |
| Not considering 8-directional for grid | Wrong neighbors | Clarify with interviewer |

## Practice Problems

### Rotting Oranges (LeetCode 994)

*Already covered above in Section 24.4.*

### Word Ladder (LeetCode 127)

**Problem:** Given a `beginWord`, `endWord`, and a dictionary, find the length of the shortest transformation sequence where each step changes exactly one character and every intermediate word must be in the dictionary.

```cpp
#include <string>
#include <vector>
#include <unordered_set>
#include <queue>

class Solution {
public:
    int ladderLength(std::string beginWord, std::string endWord,
                     std::vector<std::string>& wordList) {
        std::unordered_set<std::string> dict(wordList.begin(), wordList.end());
        if (!dict.count(endWord)) return 0;

        std::queue<std::pair<std::string, int>> q;
        q.push({beginWord, 1});
        std::unordered_set<std::string> visited;
        visited.insert(beginWord);

        while (!q.empty()) {
            auto [word, dist] = q.front();
            q.pop();

            for (int i = 0; i < (int)word.size(); ++i) {
                std::string next = word;
                for (char c = 'a'; c <= 'z'; ++c) {
                    next[i] = c;
                    if (next == endWord) return dist + 1;
                    if (dict.count(next) && !visited.count(next)) {
                        visited.insert(next);
                        q.push({next, dist + 1});
                    }
                }
            }
        }
        return 0;
    }
};
```

**Complexity:** \\(O(N \cdot L^2 \cdot 26)\\) where \\(N\\) = word list size, \\(L\\) = word length.

### Shortest Path in Binary Matrix (LeetCode 1091)

**Problem:** Given an \\(n \times n\\) binary grid, find the shortest path from top-left to bottom-right using 8-directional movement. Return the number of cells in the path, or -1 if no path exists.

```cpp
#include <vector>
#include <queue>
#include <utility>

class Solution {
public:
    int shortestPathBinaryMatrix(std::vector<std::vector<int>>& grid) {
        int n = grid.size();
        if (grid[0][0] == 1 || grid[n-1][n-1] == 1) return -1;

        const int dx[] = {-1, -1, -1, 0, 0, 1, 1, 1};
        const int dy[] = {-1, 0, 1, -1, 1, -1, 0, 1};

        std::vector<std::vector<int>> dist(n, std::vector<int>(n, -1));
        std::queue<std::pair<int, int>> q;

        dist[0][0] = 1;
        q.push({0, 0});

        while (!q.empty()) {
            auto [x, y] = q.front();
            q.pop();

            if (x == n - 1 && y == n - 1) return dist[x][y];

            for (int d = 0; d < 8; ++d) {
                int nx = x + dx[d], ny = y + dy[d];
                if (nx >= 0 && nx < n && ny >= 0 && ny < n &&
                    grid[nx][ny] == 0 && dist[nx][ny] == -1) {
                    dist[nx][ny] = dist[x][y] + 1;
                    q.push({nx, ny});
                }
            }
        }
        return -1;
    }
};
```

### Pacific Atlantic Water Flow (LeetCode 417)

**Problem:** Given an \\(m \times n\\) matrix of heights, water flows from a cell to neighbors with equal or lower height. Find all cells from which water can reach *both* the Pacific and Atlantic oceans.

**Approach:** Run multi-source BFS from Pacific edges and Atlantic edges separately. The answer is the intersection.

```cpp
#include <vector>
#include <queue>
#include <utility>

class Solution {
public:
    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};

    std::vector<std::vector<bool>> bfs(
        const std::vector<std::vector<int>>& heights,
        const std::vector<std::pair<int, int>>& sources) {

        int m = heights.size(), n = heights[0].size();
        std::vector<std::vector<bool>> visited(m, std::vector<bool>(n, false));
        std::queue<std::pair<int, int>> q;

        for (auto [x, y] : sources) {
            visited[x][y] = true;
            q.push({x, y});
        }

        while (!q.empty()) {
            auto [x, y] = q.front();
            q.pop();
            for (int d = 0; d < 4; ++d) {
                int nx = x + dx[d], ny = y + dy[d];
                if (nx >= 0 && nx < m && ny >= 0 && ny < n &&
                    !visited[nx][ny] && heights[nx][ny] >= heights[x][y]) {
                    visited[nx][ny] = true;
                    q.push({nx, ny});
                }
            }
        }
        return visited;
    }

    std::vector<std::vector<int>> pacificAtlantic(
        std::vector<std::vector<int>>& heights) {

        int m = heights.size(), n = heights[0].size();
        std::vector<std::pair<int, int>> pacific, atlantic;

        for (int i = 0; i < m; ++i) {
            pacific.push_back({i, 0});
            atlantic.push_back({i, n - 1});
        }
        for (int j = 0; j < n; ++j) {
            pacific.push_back({0, j});
            atlantic.push_back({m - 1, j});
        }

        auto reachP = bfs(heights, pacific);
        auto reachA = bfs(heights, atlantic);

        std::vector<std::vector<int>> result;
        for (int i = 0; i < m; ++i) {
            for (int j = 0; j < n; ++j) {
                if (reachP[i][j] && reachA[i][j]) {
                    result.push_back({i, j});
                }
            }
        }
        return result;
    }
};
```

## 24.7 BFS with State Space

Many problems involve searching through **states** rather than graph vertices. BFS works perfectly for state-space search where each state is a vertex and transitions are edges.

### Example: Sliding Puzzle

In a sliding puzzle (e.g., the 8-puzzle), each board configuration is a state. Swapping the empty tile with an adjacent tile creates a new state. BFS finds the minimum number of moves to reach the goal.

```cpp
#include <string>
#include <queue>
#include <unordered_set>

int slidingPuzzle(std::vector<std::vector<int>>& board) {
    std::string target = "1234560";
    std::string start;
    for (auto& row : board)
        for (int x : row) start += (char)('0' + x);

    if (start == target) return 0;

    // Neighbors of each position in the 2x3 grid
    std::vector<std::vector<int>> neighbors = {
        {1, 3}, {0, 2, 4}, {1, 5},
        {0, 4}, {1, 3, 5}, {2, 4}
    };

    std::queue<std::pair<std::string, int>> q;
    std::unordered_set<std::string> visited;
    q.push({start, 0});
    visited.insert(start);

    while (!q.empty()) {
        auto [state, moves] = q.front();
        q.pop();
        int zeroPos = state.find('0');

        for (int next : neighbors[zeroPos]) {
            std::string newState = state;
            std::swap(newState[zeroPos], newState[next]);
            if (newState == target) return moves + 1;
            if (!visited.count(newState)) {
                visited.insert(newState);
                q.push({newState, moves + 1});
            }
        }
    }
    return -1;
}
```

**Key insight:** The "graph" is implicit — we don't build it upfront. We generate neighbors on-the-fly during BFS. This is called **implicit graph search**.

---

## Summary

BFS is the go-to algorithm for shortest paths in unweighted graphs and level-by-level processing. Key takeaways:

- **Core data structure:** Queue (FIFO).
- **Time complexity:** \\(O(V + E)\\).
- **Guarantees shortest path** in unweighted graphs.
- **Multi-source BFS** solves spreading/propagation problems elegantly.
- **0-1 BFS** with a deque handles 0/1 weighted edges in \\(O(V + E)\\).
- **BFS on grids** is a common interview pattern — always check bounds.

---

## See Also

- [Chapter 23: Depth-First Search](ch23-dfs.md) — The complementary traversal; DFS goes deep before backtracking, BFS explores level by level.
- [Chapter 25: Topological Sort](ch25-topological-sort.md) — BFS (Kahn's algorithm) provides an alternative to DFS for topological ordering of DAGs.
- [Chapter 26: Shortest Paths](ch26-shortest-paths.md) — BFS is the foundation of shortest path algorithms for unweighted graphs; Dijkstra generalizes this to weighted graphs.
- [Chapter 34: Two Pointers](ch34-two-pointers.md) — BFS on level-order trees naturally leads to two-pointer and level-processing patterns.
- [Chapter 17: Disjoint Set Union](ch17-dsu.md) — For pure connectivity queries without path details, DSU is often simpler than BFS.

*Next chapter: Topological Sort — ordering vertices in a DAG so that all edges go forward.*
