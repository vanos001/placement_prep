# Appendix D: Code Templates

Copy-paste ready C++17 templates for every major algorithm and data structure used in competitive programming and coding interviews.

---

## 1. BFS (Breadth-First Search)

### Grid BFS (Shortest Path in Grid)

```cpp
#include <bits/stdc++.h>
using namespace std;

int bfs(vector<string>& grid, int sr, int sc, int er, int ec) {
    int n = grid.size(), m = grid[0].size();
    vector<vector<int>> dist(n, vector<int>(m, -1));
    queue<pair<int,int>> q;
    q.push({sr, sc});
    dist[sr][sc] = 0;
    
    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    
    while (!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        for (int d = 0; d < 4; d++) {
            int nr = r + dr[d], nc = c + dc[d];
            if (nr >= 0 && nr < n && nc >= 0 && nc < m 
                && grid[nr][nc] != '#' && dist[nr][nc] == -1) {
                dist[nr][nc] = dist[r][c] + 1;
                q.push({nr, nc});
            }
        }
    }
    return dist[er][ec];
}
```

### Graph BFS (Adjacency List)

```cpp
vector<int> bfs(vector<vector<int>>& adj, int start) {
    int n = adj.size();
    vector<int> dist(n, -1);
    queue<int> q;
    q.push(start);
    dist[start] = 0;
    
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
    return dist;
}
```

---

## 2. DFS (Depth-First Search)

### Recursive DFS

```cpp
void dfs(vector<vector<int>>& adj, int u, vector<bool>& visited) {
    visited[u] = true;
    // Process node u here
    for (int v : adj[u]) {
        if (!visited[v]) {
            dfs(adj, v, visited);
        }
    }
}
```

### Iterative DFS

```cpp
void dfs_iterative(vector<vector<int>>& adj, int start) {
    int n = adj.size();
    vector<bool> visited(n, false);
    stack<int> st;
    st.push(start);
    
    while (!st.empty()) {
        int u = st.top(); st.pop();
        if (visited[u]) continue;
        visited[u] = true;
        // Process node u here
        for (int v : adj[u]) {
            if (!visited[v]) {
                st.push(v);
            }
        }
    }
}
```

### Grid DFS

```cpp
void dfs(vector<string>& grid, int r, int c, vector<vector<bool>>& visited) {
    int n = grid.size(), m = grid[0].size();
    if (r < 0 || r >= n || c < 0 || c >= m) return;
    if (grid[r][c] == '#' || visited[r][c]) return;
    visited[r][c] = true;
    
    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    for (int d = 0; d < 4; d++) {
        dfs(grid, r + dr[d], c + dc[d], visited);
    }
}
```

---

## 3. Dijkstra's Algorithm

```cpp
#include <bits/stdc++.h>
using namespace std;

const long long INF = 1e18;

vector<long long> dijkstra(vector<vector<pair<int,int>>>& adj, int start) {
    int n = adj.size();
    vector<long long> dist(n, INF);
    // min-heap: (distance, node)
    priority_queue<pair<long long,int>, 
                   vector<pair<long long,int>>,
                   greater<pair<long long,int>>> pq;
    
    dist[start] = 0;
    pq.push({0, start});
    
    while (!pq.empty()) {
        auto [d, u] = pq.top(); pq.pop();
        if (d > dist[u]) continue;  // stale entry
        for (auto& [v, w] : adj[u]) {
            if (dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                pq.push({dist[v], v});
            }
        }
    }
    return dist;
}

// Usage:
// vector<vector<pair<int,int>>> adj(n); // adj[u] = {(v, weight), ...}
// vector<long long> dist = dijkstra(adj, 0);
```

---

## 4. Bellman-Ford

```cpp
#include <bits/stdc++.h>
using namespace std;

const long long INF = 1e18;

struct Edge {
    int u, v, w;
};

pair<vector<long long>, bool> bellman_ford(
    vector<Edge>& edges, int n, int start) {
    
    vector<long long> dist(n, INF);
    dist[start] = 0;
    
    // Relax edges n-1 times
    for (int i = 0; i < n - 1; i++) {
        for (auto& [u, v, w] : edges) {
            if (dist[u] < INF && dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
            }
        }
    }
    
    // Check for negative cycle
    bool has_negative_cycle = false;
    for (auto& [u, v, w] : edges) {
        if (dist[u] < INF && dist[u] + w < dist[v]) {
            has_negative_cycle = true;
            break;
        }
    }
    
    return {dist, has_negative_cycle};
}
```

---

## 5. Floyd-Warshall

```cpp
#include <bits/stdc++.h>
using namespace std;

const long long INF = 1e18;

void floyd_warshall(vector<vector<long long>>& dist, int n) {
    // dist[i][j] = INF if no edge, 0 if i == j
    for (int k = 0; k < n; k++) {
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (dist[i][k] < INF && dist[k][j] < INF) {
                    dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j]);
                }
            }
        }
    }
}
```

---

## 6. Kruskal's Algorithm (MST)

```cpp
#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> parent, rank;
    DSU(int n) : parent(n), rank(n, 0) {
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int x) {
        return parent[x] == x ? x : parent[x] = find(parent[x]);
    }
    bool unite(int x, int y) {
        x = find(x), y = find(y);
        if (x == y) return false;
        if (rank[x] < rank[y]) swap(x, y);
        parent[y] = x;
        if (rank[x] == rank[y]) rank[x]++;
        return true;
    }
};

struct Edge {
    int u, v, w;
    bool operator<(const Edge& other) const {
        return w < other.w;
    }
};

pair<long long, vector<Edge>> kruskal(vector<Edge>& edges, int n) {
    sort(edges.begin(), edges.end());
    DSU dsu(n);
    long long total_weight = 0;
    vector<Edge> mst;
    
    for (auto& e : edges) {
        if (dsu.unite(e.u, e.v)) {
            total_weight += e.w;
            mst.push_back(e);
        }
    }
    return {total_weight, mst};
}
```

---

## 7. Prim's Algorithm (MST)

```cpp
#include <bits/stdc++.h>
using namespace std;

long long prim(vector<vector<pair<int,int>>>& adj, int start = 0) {
    int n = adj.size();
    vector<bool> in_mst(n, false);
    // min-heap: (weight, node)
    priority_queue<pair<int,int>, vector<pair<int,int>>, greater<>> pq;
    pq.push({0, start});
    long long total_weight = 0;
    
    while (!pq.empty()) {
        auto [w, u] = pq.top(); pq.pop();
        if (in_mst[u]) continue;
        in_mst[u] = true;
        total_weight += w;
        for (auto& [v, weight] : adj[u]) {
            if (!in_mst[v]) {
                pq.push({weight, v});
            }
        }
    }
    return total_weight;
}
```

---

## 8. Topological Sort

### DFS-Based

```cpp
void dfs(vector<vector<int>>& adj, int u, vector<bool>& visited, 
         vector<int>& order) {
    visited[u] = true;
    for (int v : adj[u]) {
        if (!visited[v]) {
            dfs(adj, v, visited, order);
        }
    }
    order.push_back(u);  // post-order
}

vector<int> topological_sort(vector<vector<int>>& adj) {
    int n = adj.size();
    vector<bool> visited(n, false);
    vector<int> order;
    for (int i = 0; i < n; i++) {
        if (!visited[i]) {
            dfs(adj, i, visited, order);
        }
    }
    reverse(order.begin(), order.end());
    return order;
}
```

### BFS-Based (Kahn's)

```cpp
vector<int> kahn(vector<vector<int>>& adj) {
    int n = adj.size();
    vector<int> in_degree(n, 0);
    for (int u = 0; u < n; u++) {
        for (int v : adj[u]) {
            in_degree[v]++;
        }
    }
    
    queue<int> q;
    for (int i = 0; i < n; i++) {
        if (in_degree[i] == 0) q.push(i);
    }
    
    vector<int> order;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (int v : adj[u]) {
            if (--in_degree[v] == 0) {
                q.push(v);
            }
        }
    }
    
    if ((int)order.size() != n) {
        return {};  // cycle detected
    }
    return order;
}
```

---

## 9. Segment Tree

### Point Update, Range Query

```cpp
class SegmentTree {
    vector<long long> tree;
    int n;
    
public:
    SegmentTree(vector<int>& arr) {
        n = arr.size();
        tree.resize(4 * n);
        build(arr, 1, 0, n - 1);
    }
    
    void build(vector<int>& arr, int node, int lo, int hi) {
        if (lo == hi) {
            tree[node] = arr[lo];
            return;
        }
        int mid = (lo + hi) / 2;
        build(arr, 2 * node, lo, mid);
        build(arr, 2 * node + 1, mid + 1, hi);
        tree[node] = tree[2 * node] + tree[2 * node + 1];
    }
    
    void update(int idx, int val) {
        update(1, 0, n - 1, idx, val);
    }
    
    void update(int node, int lo, int hi, int idx, int val) {
        if (lo == hi) {
            tree[node] = val;
            return;
        }
        int mid = (lo + hi) / 2;
        if (idx <= mid) update(2 * node, lo, mid, idx, val);
        else update(2 * node + 1, mid + 1, hi, idx, val);
        tree[node] = tree[2 * node] + tree[2 * node + 1];
    }
    
    long long query(int ql, int qh) {
        return query(1, 0, n - 1, ql, qh);
    }
    
    long long query(int node, int lo, int hi, int ql, int qh) {
        if (ql > hi || qh < lo) return 0;
        if (ql <= lo && hi <= qh) return tree[node];
        int mid = (lo + hi) / 2;
        return query(2 * node, lo, mid, ql, qh) +
               query(2 * node + 1, mid + 1, hi, ql, qh);
    }
};
```

### Range Update, Range Query (Lazy Propagation)

```cpp
class LazySegmentTree {
    vector<long long> tree, lazy;
    int n;
    
public:
    LazySegmentTree(int size) : n(size) {
        tree.resize(4 * n, 0);
        lazy.resize(4 * n, 0);
    }
    
    void push(int node, int lo, int hi) {
        if (lazy[node] != 0) {
            tree[node] += lazy[node] * (hi - lo + 1);
            if (lo != hi) {
                lazy[2 * node] += lazy[node];
                lazy[2 * node + 1] += lazy[node];
            }
            lazy[node] = 0;
        }
    }
    
    void update(int ql, int qh, int val) {
        update(1, 0, n - 1, ql, qh, val);
    }
    
    void update(int node, int lo, int hi, int ql, int qh, int val) {
        push(node, lo, hi);
        if (ql > hi || qh < lo) return;
        if (ql <= lo && hi <= qh) {
            lazy[node] += val;
            push(node, lo, hi);
            return;
        }
        int mid = (lo + hi) / 2;
        update(2 * node, lo, mid, ql, qh, val);
        update(2 * node + 1, mid + 1, hi, ql, qh, val);
        tree[node] = tree[2 * node] + tree[2 * node + 1];
    }
    
    long long query(int ql, int qh) {
        return query(1, 0, n - 1, ql, qh);
    }
    
    long long query(int node, int lo, int hi, int ql, int qh) {
        push(node, lo, hi);
        if (ql > hi || qh < lo) return 0;
        if (ql <= lo && hi <= qh) return tree[node];
        int mid = (lo + hi) / 2;
        return query(2 * node, lo, mid, ql, qh) +
               query(2 * node + 1, mid + 1, hi, ql, qh);
    }
};
```

---

## 10. Fenwick Tree (Binary Indexed Tree)

### Point Update, Prefix Sum Query

```cpp
class FenwickTree {
    vector<long long> tree;
    int n;
    
public:
    FenwickTree(int size) : n(size), tree(size + 1, 0) {}
    
    void update(int i, int delta) {
        for (; i <= n; i += i & (-i)) {
            tree[i] += delta;
        }
    }
    
    long long query(int i) {  // prefix sum [1..i]
        long long sum = 0;
        for (; i > 0; i -= i & (-i)) {
            sum += tree[i];
        }
        return sum;
    }
    
    long long range_query(int l, int r) {
        return query(r) - query(l - 1);
    }
};

// Usage:
// FenwickTree ft(n);
// ft.update(i, val);     // add val to index i
// ft.query(i);           // sum of [1..i]
// ft.range_query(l, r);  // sum of [l..r]
```

### Range Update, Point Query

```cpp
class FenwickTreeRangeUpdate {
    FenwickTree ft;
    
public:
    FenwickTreeRangeUpdate(int n) : ft(n) {}
    
    void range_update(int l, int r, int delta) {
        ft.update(l, delta);
        ft.update(r + 1, -delta);
    }
    
    long long point_query(int i) {
        return ft.query(i);
    }
};
```

---

## 11. DSU (Disjoint Set Union)

```cpp
class DSU {
    vector<int> parent, sz;
    
public:
    DSU(int n) : parent(n), sz(n, 1) {
        iota(parent.begin(), parent.end(), 0);
    }
    
    int find(int x) {
        return parent[x] == x ? x : parent[x] = find(parent[x]);
    }
    
    bool unite(int x, int y) {
        x = find(x), y = find(y);
        if (x == y) return false;
        if (sz[x] < sz[y]) swap(x, y);
        parent[y] = x;
        sz[x] += sz[y];
        return true;
    }
    
    bool connected(int x, int y) {
        return find(x) == find(y);
    }
    
    int size(int x) {
        return sz[find(x)];
    }
};
```

---

## 12. Trie

### Basic Trie (Lowercase Letters)

```cpp
class Trie {
    struct Node {
        Node* children[26] = {};
        bool is_end = false;
    };
    Node* root;
    
public:
    Trie() { root = new Node(); }
    
    void insert(string& word) {
        Node* node = root;
        for (char c : word) {
            int idx = c - 'a';
            if (!node->children[idx]) {
                node->children[idx] = new Node();
            }
            node = node->children[idx];
        }
        node->is_end = true;
    }
    
    bool search(string& word) {
        Node* node = root;
        for (char c : word) {
            int idx = c - 'a';
            if (!node->children[idx]) return false;
            node = node->children[idx];
        }
        return node->is_end;
    }
    
    bool starts_with(string& prefix) {
        Node* node = root;
        for (char c : prefix) {
            int idx = c - 'a';
            if (!node->children[idx]) return false;
            node = node->children[idx];
        }
        return true;
    }
};
```

### Bit Trie (for XOR Problems)

```cpp
class BitTrie {
    struct Node {
        Node* children[2] = {};
    };
    Node* root;
    
public:
    BitTrie() { root = new Node(); }
    
    void insert(int num) {
        Node* node = root;
        for (int i = 30; i >= 0; i--) {
            int bit = (num >> i) & 1;
            if (!node->children[bit]) {
                node->children[bit] = new Node();
            }
            node = node->children[bit];
        }
    }
    
    int max_xor(int num) {
        Node* node = root;
        int result = 0;
        for (int i = 30; i >= 0; i--) {
            int bit = (num >> i) & 1;
            int want = 1 - bit;
            if (node->children[want]) {
                result |= (1 << i);
                node = node->children[want];
            } else {
                node = node->children[bit];
            }
        }
        return result;
    }
};
```

---

## 13. KMP (Pattern Matching)

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<int> compute_lps(string& pattern) {
    int m = pattern.size();
    vector<int> lps(m, 0);
    int len = 0, i = 1;
    while (i < m) {
        if (pattern[i] == pattern[len]) {
            len++;
            lps[i] = len;
            i++;
        } else {
            if (len != 0) {
                len = lps[len - 1];
            } else {
                lps[i] = 0;
                i++;
            }
        }
    }
    return lps;
}

vector<int> kmp_search(string& text, string& pattern) {
    vector<int> matches;
    vector<int> lps = compute_lps(pattern);
    int n = text.size(), m = pattern.size();
    int i = 0, j = 0;
    while (i < n) {
        if (text[i] == pattern[j]) {
            i++; j++;
        }
        if (j == m) {
            matches.push_back(i - j);
            j = lps[j - 1];
        } else if (i < n && text[i] != pattern[j]) {
            if (j != 0) j = lps[j - 1];
            else i++;
        }
    }
    return matches;
}
```

---

## 14. Z Algorithm

```cpp
#include <bits/stdc++.h>
using namespace std;

vector<int> compute_z(string& s) {
    int n = s.size();
    vector<int> z(n, 0);
    int l = 0, r = 0;
    for (int i = 1; i < n; i++) {
        if (i <= r) {
            z[i] = min(r - i + 1, z[i - l]);
        }
        while (i + z[i] < n && s[z[i]] == s[i + z[i]]) {
            z[i]++;
        }
        if (i + z[i] - 1 > r) {
            l = i;
            r = i + z[i] - 1;
        }
    }
    return z;
}

vector<int> z_search(string& text, string& pattern) {
    string s = pattern + "$" + text;
    vector<int> z = compute_z(s);
    vector<int> matches;
    int m = pattern.size();
    for (int i = m + 1; i < (int)s.size(); i++) {
        if (z[i] == m) {
            matches.push_back(i - m - 1);
        }
    }
    return matches;
}
```

---

## 15. Binary Search Variants

### Standard Binary Search

```cpp
int binary_search(vector<int>& arr, int target) {
    int lo = 0, hi = arr.size() - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
```

### Lower Bound (First Element >= Target)

```cpp
int lower_bound(vector<int>& arr, int target) {
    int lo = 0, hi = arr.size();
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] >= target) hi = mid;
        else lo = mid + 1;
    }
    return lo;
}
```

### Upper Bound (First Element > Target)

```cpp
int upper_bound(vector<int>& arr, int target) {
    int lo = 0, hi = arr.size();
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] > target) hi = mid;
        else lo = mid + 1;
    }
    return lo;
}
```

### Binary Search on Answer (Minimize)

```cpp
int binary_search_minimize(function<bool(int)> check, int lo, int hi) {
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (check(mid)) hi = mid;
        else lo = mid + 1;
    }
    return lo;  // smallest value where check() is true
}
```

### Binary Search on Answer (Maximize)

```cpp
int binary_search_maximize(function<bool(int)> check, int lo, int hi) {
    while (lo < hi) {
        int mid = lo + (hi - lo + 1) / 2;  // ceiling division
        if (check(mid)) lo = mid;
        else hi = mid - 1;
    }
    return lo;  // largest value where check() is true
}
```

### Binary Search on Real Numbers

```cpp
double binary_search_real(function<bool(double)> check, 
                          double lo, double hi, double eps = 1e-9) {
    while (hi - lo > eps) {
        double mid = lo + (hi - lo) / 2;
        if (check(mid)) hi = mid;
        else lo = mid;
    }
    return lo;
}
```

---

## 16. Sliding Window

### Fixed Size Window

```cpp
long long max_sum_subarray(vector<int>& arr, int k) {
    long long window = 0;
    for (int i = 0; i < k; i++) window += arr[i];
    long long max_sum = window;
    for (int i = k; i < arr.size(); i++) {
        window += arr[i] - arr[i - k];
        max_sum = max(max_sum, window);
    }
    return max_sum;
}
```

### Variable Size Window

```cpp
int min_subarray_len(vector<int>& arr, int target) {
    int lo = 0, min_len = INT_MAX;
    long long sum = 0;
    for (int hi = 0; hi < arr.size(); hi++) {
        sum += arr[hi];
        while (sum >= target) {
            min_len = min(min_len, hi - lo + 1);
            sum -= arr[lo++];
        }
    }
    return min_len == INT_MAX ? 0 : min_len;
}
```

---

## 17. Two Pointers

```cpp
// Find pair with given sum in sorted array
pair<int,int> two_sum_sorted(vector<int>& arr, int target) {
    int lo = 0, hi = arr.size() - 1;
    while (lo < hi) {
        int sum = arr[lo] + arr[hi];
        if (sum == target) return {lo, hi};
        if (sum < target) lo++;
        else hi--;
    }
    return {-1, -1};
}

// Three sum
vector<vector<int>> three_sum(vector<int>& arr, int target) {
    sort(arr.begin(), arr.end());
    vector<vector<int>> result;
    int n = arr.size();
    for (int i = 0; i < n - 2; i++) {
        if (i > 0 && arr[i] == arr[i-1]) continue;  // skip duplicates
        int lo = i + 1, hi = n - 1;
        while (lo < hi) {
            int sum = arr[i] + arr[lo] + arr[hi];
            if (sum == target) {
                result.push_back({arr[i], arr[lo], arr[hi]});
                while (lo < hi && arr[lo] == arr[lo+1]) lo++;
                while (lo < hi && arr[hi] == arr[hi-1]) hi--;
                lo++; hi--;
            } else if (sum < target) lo++;
            else hi--;
        }
    }
    return result;
}
```

---

## 18. Backtracking

### Subsets

```cpp
void subsets(vector<int>& nums, int idx, vector<int>& current, 
             vector<vector<int>>& result) {
    result.push_back(current);
    for (int i = idx; i < nums.size(); i++) {
        current.push_back(nums[i]);
        subsets(nums, i + 1, current, result);
        current.pop_back();
    }
}
```

### Permutations

```cpp
void permutations(vector<int>& nums, int idx, 
                  vector<vector<int>>& result) {
    if (idx == nums.size()) {
        result.push_back(nums);
        return;
    }
    for (int i = idx; i < nums.size(); i++) {
        swap(nums[idx], nums[i]);
        permutations(nums, idx + 1, result);
        swap(nums[idx], nums[i]);
    }
}
```

### Combinations

```cpp
void combinations(int n, int k, int start, vector<int>& current,
                  vector<vector<int>>& result) {
    if (current.size() == k) {
        result.push_back(current);
        return;
    }
    for (int i = start; i <= n; i++) {
        current.push_back(i);
        combinations(n, k, i + 1, current, result);
        current.pop_back();
    }
}
```

### N-Queens

```cpp
void solve_n_queens(int n, int row, vector<int>& queens,
                    vector<vector<string>>& result) {
    if (row == n) {
        vector<string> board(n, string(n, '.'));
        for (int i = 0; i < n; i++) {
            board[i][queens[i]] = 'Q';
        }
        result.push_back(board);
        return;
    }
    for (int col = 0; col < n; col++) {
        queens[row] = col;
        bool valid = true;
        for (int i = 0; i < row; i++) {
            if (queens[i] == col || 
                abs(queens[i] - col) == abs(i - row)) {
                valid = false;
                break;
            }
        }
        if (valid) {
            solve_n_queens(n, row + 1, queens, result);
        }
    }
}
```

---

## 19. DP Patterns

### 0/1 Knapsack

```cpp
int knapsack(vector<int>& weights, vector<int>& values, int W) {
    int n = weights.size();
    vector<int> dp(W + 1, 0);
    for (int i = 0; i < n; i++) {
        for (int w = W; w >= weights[i]; w--) {
            dp[w] = max(dp[w], dp[w - weights[i]] + values[i]);
        }
    }
    return dp[W];
}
```

### LCS (Longest Common Subsequence)

```cpp
int lcs(string& s, string& t) {
    int n = s.size(), m = t.size();
    vector<int> prev(m + 1, 0), curr(m + 1, 0);
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= m; j++) {
            if (s[i-1] == t[j-1]) curr[j] = prev[j-1] + 1;
            else curr[j] = max(prev[j], curr[j-1]);
        }
        swap(prev, curr);
        fill(curr.begin(), curr.end(), 0);
    }
    return prev[m];
}
```

### Edit Distance

```cpp
int edit_distance(string& s, string& t) {
    int n = s.size(), m = t.size();
    vector<int> prev(m + 1), curr(m + 1);
    iota(prev.begin(), prev.end(), 0);
    for (int i = 1; i <= n; i++) {
        curr[0] = i;
        for (int j = 1; j <= m; j++) {
            if (s[i-1] == t[j-1]) curr[j] = prev[j-1];
            else curr[j] = 1 + min({prev[j], curr[j-1], prev[j-1]});
        }
        swap(prev, curr);
    }
    return prev[m];
}
```

### LIS (Longest Increasing Subsequence)

```cpp
int lis(vector<int>& arr) {
    vector<int> tails;
    for (int x : arr) {
        auto it = lower_bound(tails.begin(), tails.end(), x);
        if (it == tails.end()) tails.push_back(x);
        else *it = x;
    }
    return tails.size();
}
```

### Coin Change (Minimum Coins)

```cpp
int coin_change(vector<int>& coins, int amount) {
    vector<int> dp(amount + 1, INT_MAX);
    dp[0] = 0;
    for (int i = 1; i <= amount; i++) {
        for (int coin : coins) {
            if (coin <= i && dp[i - coin] != INT_MAX) {
                dp[i] = min(dp[i], dp[i - coin] + 1);
            }
        }
    }
    return dp[amount] == INT_MAX ? -1 : dp[amount];
}
```

### Matrix Chain Multiplication

```cpp
int matrix_chain(vector<int>& dims) {
    int n = dims.size() - 1;
    vector<vector<int>> dp(n, vector<int>(n, 0));
    for (int len = 2; len <= n; len++) {
        for (int i = 0; i < n - len + 1; i++) {
            int j = i + len - 1;
            dp[i][j] = INT_MAX;
            for (int k = i; k < j; k++) {
                dp[i][j] = min(dp[i][j], 
                    dp[i][k] + dp[k+1][j] + dims[i]*dims[k+1]*dims[j+1]);
            }
        }
    }
    return dp[0][n-1];
}
```

---

## 20. Monotonic Stack

### Next Greater Element

```cpp
vector<int> next_greater_element(vector<int>& arr) {
    int n = arr.size();
    vector<int> result(n, -1);
    stack<int> st;
    for (int i = 0; i < n; i++) {
        while (!st.empty() && arr[st.top()] < arr[i]) {
            result[st.top()] = arr[i];
            st.pop();
        }
        st.push(i);
    }
    return result;
}
```

### Next Smaller Element

```cpp
vector<int> next_smaller_element(vector<int>& arr) {
    int n = arr.size();
    vector<int> result(n, -1);
    stack<int> st;
    for (int i = 0; i < n; i++) {
        while (!st.empty() && arr[st.top()] > arr[i]) {
            result[st.top()] = arr[i];
            st.pop();
        }
        st.push(i);
    }
    return result;
}
```

### Largest Rectangle in Histogram

```cpp
int largest_rectangle(vector<int>& heights) {
    int n = heights.size();
    stack<int> st;
    int max_area = 0;
    for (int i = 0; i <= n; i++) {
        int h = (i == n) ? 0 : heights[i];
        while (!st.empty() && h < heights[st.top()]) {
            int height = heights[st.top()]; st.pop();
            int width = st.empty() ? i : i - st.top() - 1;
            max_area = max(max_area, height * width);
        }
        st.push(i);
    }
    return max_area;
}
```

---

## 21. Monotonic Queue (Deque)

### Sliding Window Maximum

```cpp
vector<int> sliding_window_max(vector<int>& arr, int k) {
    deque<int> dq;
    vector<int> result;
    for (int i = 0; i < arr.size(); i++) {
        while (!dq.empty() && dq.front() <= i - k) {
            dq.pop_front();
        }
        while (!dq.empty() && arr[dq.back()] <= arr[i]) {
            dq.pop_back();
        }
        dq.push_back(i);
        if (i >= k - 1) {
            result.push_back(arr[dq.front()]);
        }
    }
    return result;
}
```

---

## 22. LCA (Lowest Common Ancestor)

```cpp
class LCA {
    vector<vector<int>> up;
    vector<int> depth;
    int LOG;
    
public:
    LCA(vector<vector<int>>& adj, int root = 0) {
        int n = adj.size();
        LOG = 0;
        while ((1 << LOG) <= n) LOG++;
        up.assign(n, vector<int>(LOG));
        depth.assign(n, 0);
        
        // BFS to set depths and parents
        queue<int> q;
        q.push(root);
        up[root][0] = root;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (v == up[u][0]) continue;
                depth[v] = depth[u] + 1;
                up[v][0] = u;
                q.push(v);
            }
        }
        
        // Binary lifting
        for (int j = 1; j < LOG; j++) {
            for (int i = 0; i < n; i++) {
                up[i][j] = up[up[i][j-1]][j-1];
            }
        }
    }
    
    int lca(int u, int v) {
        if (depth[u] < depth[v]) swap(u, v);
        int diff = depth[u] - depth[v];
        for (int j = 0; j < LOG; j++) {
            if (diff & (1 << j)) u = up[u][j];
        }
        if (u == v) return u;
        for (int j = LOG - 1; j >= 0; j--) {
            if (up[u][j] != up[v][j]) {
                u = up[u][j];
                v = up[v][j];
            }
        }
        return up[u][0];
    }
    
    int distance(int u, int v) {
        return depth[u] + depth[v] - 2 * depth[lca(u, v)];
    }
};
```

---

## 23. Tarjan's SCC

```cpp
vector<vector<int>> tarjan_scc(vector<vector<int>>& adj) {
    int n = adj.size();
    int timer = 0;
    vector<int> indices(n, -1), lowlink(n, -1);
    vector<bool> on_stack(n, false);
    stack<int> st;
    vector<vector<int>> sccs;
    
    function<void(int)> dfs = [&](int u) {
        indices[u] = lowlink[u] = timer++;
        st.push(u);
        on_stack[u] = true;
        
        for (int v : adj[u]) {
            if (indices[v] == -1) {
                dfs(v);
                lowlink[u] = min(lowlink[u], lowlink[v]);
            } else if (on_stack[v]) {
                lowlink[u] = min(lowlink[u], indices[v]);
            }
        }
        
        if (lowlink[u] == indices[u]) {
            vector<int> scc;
            int w;
            do {
                w = st.top(); st.pop();
                on_stack[w] = false;
                scc.push_back(w);
            } while (w != u);
            sccs.push_back(scc);
        }
    };
    
    for (int i = 0; i < n; i++) {
        if (indices[i] == -1) dfs(i);
    }
    return sccs;
}
```

---

## 24. Fast I/O Template

```cpp
#include <bits/stdc++.h>
using namespace std;

void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
}

int main() {
    fast_io();
    // your code here
    return 0;
}
```

---

## 25. Coordinate Compression

```cpp
vector<int> compress(vector<int>& arr) {
    vector<int> sorted = arr;
    sort(sorted.begin(), sorted.end());
    sorted.erase(unique(sorted.begin(), sorted.end()), sorted.end());
    vector<int> result(arr.size());
    for (int i = 0; i < arr.size(); i++) {
        result[i] = lower_bound(sorted.begin(), sorted.end(), arr[i]) - sorted.begin();
    }
    return result;
}
```

---

*These templates are battle-tested and ready for use. Practice with them until they become second nature.*
