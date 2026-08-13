# Chapter 112: Hopcroft-Karp and Blossom Algorithm

## Prerequisites
- Bipartite matching, DFS

## Interview Frequency: ★★★

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Hopcroft-Karp | ★★★ | Hard | O(E√V) bipartite matching |
| Blossom (overview) | ★ | Hard | General graph matching |

---

## 112.1 Hopcroft-Karp Algorithm

Find maximum bipartite matching by finding multiple augmenting paths simultaneously using BFS layers.

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

class HopcroftKarp {
    int n, m;
    std::vector<std::vector<int>> adj;
    std::vector<int> pairU, pairV, dist;
    
    bool bfs() {
        std::queue<int> q;
        for (int u = 0; u < n; u++) {
            if (pairU[u] == -1) { dist[u] = 0; q.push(u); }
            else dist[u] = INT_MAX;
        }
        bool found = false;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (pairV[v] == -1) found = true;
                else if (dist[pairV[v]] == INT_MAX) {
                    dist[pairV[v]] = dist[u] + 1;
                    q.push(pairV[v]);
                }
            }
        }
        return found;
    }
    
    bool dfs(int u) {
        for (int v : adj[u]) {
            if (pairV[v] == -1 || (dist[pairV[v]] == dist[u] + 1 && dfs(pairV[v]))) {
                pairU[u] = v; pairV[v] = u;
                return true;
            }
        }
        dist[u] = INT_MAX;
        return false;
    }
    
public:
    HopcroftKarp(int n, int m) : n(n), m(m), adj(n), pairU(n, -1), pairV(m, -1), dist(n) {}
    void addEdge(int u, int v) { adj[u].push_back(v); }
    
    int maxMatching() {
        int matching = 0;
        while (bfs())
            for (int u = 0; u < n; u++)
                if (pairU[u] == -1 && dfs(u)) matching++;
        return matching;
    }
    
    std::vector<std::pair<int,int>> getMatching() {
        std::vector<std::pair<int,int>> result;
        for (int u = 0; u < n; u++)
            if (pairU[u] != -1) result.push_back({u, pairU[u]});
        return result;
    }
};

int main() {
    HopcroftKarp hk(4, 4);
    hk.addEdge(0, 0); hk.addEdge(0, 1);
    hk.addEdge(1, 0); hk.addEdge(1, 2);
    hk.addEdge(2, 1); hk.addEdge(3, 2); hk.addEdge(3, 3);
    
    std::cout << "Max matching: " << hk.maxMatching() << "\n";
    auto matching = hk.getMatching();
    for (auto& [u, v] : matching)
        std::cout << "  U" << u << " -> V" << v << "\n";
    
    return 0;
}
```

---

## 112.2 Blossom Algorithm

For general (non-bipartite) graph matching. Uses **blossom contraction** to handle odd cycles.

**Key idea**: When an odd cycle (blossom) is found during augmenting path search, contract it into a super-vertex and continue. The algorithm achieves O(V^3) time.

```cpp
#include <iostream>
#include <vector>
#include <queue>

class Blossom {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<int> match, parent, base;
    std::vector<bool> used, blossom;
    
    int lca(int a, int b) {
        std::vector<bool> visited(n, false);
        while (true) { a = base[a]; visited[a] = true; if (match[a] == -1) break; a = parent[match[a]]; }
        while (true) { b = base[b]; if (visited[b]) return b; if (match[b] == -1) break; b = parent[match[b]]; }
        return -1;
    }
    
    void markPath(int v, int b, int child) {
        while (base[v] != b) {
            blossom[base[v]] = blossom[base[match[v]]] = true;
            parent[v] = child; child = match[v]; v = parent[child];
        }
    }
    
    int findPath(int root) {
        std::fill(used.begin(), used.end(), false);
        std::fill(parent.begin(), parent.end(), -1);
        for (int i = 0; i < n; i++) base[i] = i;
        used[root] = true;
        std::queue<int> q; q.push(root);
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int u : adj[v]) {
                if (base[v] == base[u] || match[v] == u) continue;
                if (u == root || (match[u] != -1 && parent[match[u]] != -1)) {
                    int curbase = lca(v, u);
                    std::fill(blossom.begin(), blossom.end(), false);
                    markPath(v, curbase, u); markPath(u, curbase, v);
                    for (int i = 0; i < n; i++)
                        if (blossom[base[i]]) { base[i] = curbase; if (!used[i]) { used[i] = true; q.push(i); } }
                } else if (parent[u] == -1) {
                    parent[u] = v;
                    if (match[u] == -1) return u;
                    u = match[u]; used[u] = true; q.push(u);
                }
            }
        }
        return -1;
    }
    
public:
    Blossom(int n) : n(n), adj(n), match(n, -1), parent(n), base(n), used(n), blossom(n) {}
    void addEdge(int u, int v) { adj[u].push_back(v); adj[v].push_back(u); }
    int maxMatching() {
        int result = 0;
        for (int v = 0; v < n; v++)
            if (match[v] == -1) {
                int u = findPath(v);
                if (u != -1) { result++; while (u != -1) { int pv = parent[u], ppv = match[pv]; match[u] = pv; match[pv] = u; u = ppv; } }
            }
        return result;
    }
};

int main() {
    Blossom bs(3);
    bs.addEdge(0, 1); bs.addEdge(1, 2); bs.addEdge(2, 0);
    std::cout << "Triangle matching: " << bs.maxMatching() << "
";
    
    Blossom bs2(4);
    bs2.addEdge(0, 1); bs2.addEdge(1, 2); bs2.addEdge(2, 3);
    std::cout << "Path matching: " << bs2.maxMatching() << "
";
    return 0;
}
```

---

## Summary

| Algorithm | Graph Type | Time | Notes |
|---|---|---|---|
| Hopcroft-Karp | Bipartite | O(E√V) | BFS + DFS layers |
| Blossom | General | O(V³) | Contract odd cycles |

---

### Blossom Algorithm Implementation Sketch

The Blossom algorithm finds maximum matching in general (non-bipartite) graphs by contracting odd cycles (blossoms).

```cpp
#include <iostream>
#include <vector>
#include <queue>

// Simplified blossom for small graphs
class BlossomSimple {
    int n;
    std::vector<std::vector<int>> adj;
    std::vector<int> match, parent, base;
    std::vector<bool> used, blossom;
    
    int lca(int a, int b) {
        std::vector<bool> visited(n, false);
        while (true) {
            a = base[a];
            visited[a] = true;
            if (match[a] == -1) break;
            a = parent[match[a]];
        }
        while (true) {
            b = base[b];
            if (visited[b]) return b;
            if (match[b] == -1) break;
            b = parent[match[b]];
        }
        return -1;
    }
    
    void markPath(int v, int b, int child) {
        while (base[v] != b) {
            blossom[base[v]] = blossom[base[match[v]]] = true;
            parent[v] = child;
            child = match[v];
            v = parent[child];
        }
    }
    
    int findPath(int root) {
        std::fill(used.begin(), used.end(), false);
        std::fill(parent.begin(), parent.end(), -1);
        for (int i = 0; i < n; i++) base[i] = i;
        
        used[root] = true;
        std::queue<int> q;
        q.push(root);
        
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int u : adj[v]) {
                if (base[v] == base[u] || match[v] == u) continue;
                if (u == root || (match[u] != -1 && parent[match[u]] != -1)) {
                    int curbase = lca(v, u);
                    std::fill(blossom.begin(), blossom.end(), false);
                    markPath(v, curbase, u);
                    markPath(u, curbase, v);
                    for (int i = 0; i < n; i++) {
                        if (blossom[base[i]]) {
                            base[i] = curbase;
                            if (!used[i]) {
                                used[i] = true;
                                q.push(i);
                            }
                        }
                    }
                } else if (parent[u] == -1) {
                    parent[u] = v;
                    if (match[u] == -1) return u;
                    u = match[u];
                    used[u] = true;
                    q.push(u);
                }
            }
        }
        return -1;
    }
    
public:
    BlossomSimple(int n) : n(n), adj(n), match(n, -1), parent(n), 
                            base(n), used(n), blossom(n) {}
    
    void addEdge(int u, int v) { adj[u].push_back(v); adj[v].push_back(u); }
    
    int maxMatching() {
        int result = 0;
        for (int v = 0; v < n; v++) {
            if (match[v] == -1) {
                int u = findPath(v);
                if (u != -1) {
                    result++;
                    while (u != -1) {
                        int pv = parent[u], ppv = match[pv];
                        match[u] = pv;
                        match[pv] = u;
                        u = ppv;
                    }
                }
            }
        }
        return result;
    }
};

int main() {
    // Triangle: 0-1, 1-2, 2-0 (non-bipartite)
    BlossomSimple bs(3);
    bs.addEdge(0, 1); bs.addEdge(1, 2); bs.addEdge(2, 0);
    std::cout << "Max matching in triangle: " << bs.maxMatching() << "\\n"; // 1
    
    // Path: 0-1-2-3
    BlossomSimple bs2(4);
    bs2.addEdge(0, 1); bs2.addEdge(1, 2); bs2.addEdge(2, 3);
    std::cout << "Max matching in path: " << bs2.maxMatching() << "\\n"; // 2
    
    return 0;
}
```
