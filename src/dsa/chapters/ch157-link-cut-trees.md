# Chapter 157: Link-Cut Trees and Euler Tour Trees

## Prerequisites
- Splay trees ([Chapter 98](ch98-splay-trees.md))
- Tree basics ([Chapter 13](ch13-trees.md))

## Interview Frequency: ★★

Link-Cut Trees (LCT) maintain a dynamic forest with O(log n) per operation. They're used in competitive programming and advanced algorithm design. Rarely asked in interviews but understanding them shows depth.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Link-Cut Tree | ★★ | Hard | Dynamic forest operations |
| Euler Tour Tree | ★ | Hard | BST-based tree representation |
| Preferred paths | ★★ | Hard | Splay tree decomposition |

---

## Definition

A **Link-Cut Tree** maintains a forest of rooted trees supporting:
- `link(u, v)`: Make u a child of v (add edge)
- `cut(u, v)`: Remove edge between u and v
- `findRoot(u)`: Find root of u's tree
- `pathQuery(u, v)`: Aggregate values on the path from u to v

All operations run in O(log n) amortized time using splay trees to represent "preferred paths."

## Motivation

Dynamic trees appear in:
- **Network connectivity**: Link/cut edges, query connectivity
- **Dynamic MST**: Maintain minimum spanning tree under edge insertions/deletions
- **Flow algorithms**: Sleator-Tarjan's dynamic tree speedup for max flow
- **Tree path queries with updates**: Combine with splay tree augmentation

## Intuition

Think of each tree as decomposed into "preferred paths" — chains of preferred edges. Each preferred path is stored as a splay tree. The `access(u)` operation restructures preferred paths so the path from root to u becomes one preferred path (one splay tree), enabling efficient queries.

---

## 157.1 Link-Cut Trees — Deep Dive

### Core Operations

1. **access(u)**: Makes the path from root to u a single preferred path. This is the fundamental operation.
2. **makeRoot(u)**: Makes u the root of its tree (via access + reverse).
3. **link(u, v)**: Makes u a child of v.
4. **cut(u, v)**: Removes edge (u, v).

### How access(u) Works

Starting from u, splay u to root of its auxiliary tree. Detach u's right child (the "lower" preferred path). Move to u's parent via the path-parent pointer. Splay the parent, detach its right child, set it to the previous tree. Repeat until reaching the root.

### Dry Run

Forest: 0→1→2→3 (chain), then `access(3)`:
```
Before: Each node is its own preferred path
  0 - 1 - 2 - 3

After access(3):
  Preferred path: 0→1→2→3 (all in one splay tree)
  3 is the root of the splay (rightmost node)
```

Then `makeRoot(3)` = access(3) + reverse:
```
Now 3 is the tree root, preferred path is 3→2→1→0
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>

class LinkCutTree {
    struct Node {
        int id;
        Node *left, *right, *parent;
        bool reversed;
        Node(int i) : id(i), left(nullptr), right(nullptr),
                      parent(nullptr), reversed(false) {}
    };

    std::vector<Node*> nodes;

    bool isRoot(Node* x) {
        return !x->parent || (x->parent->left != x && x->parent->right != x);
    }

    void push(Node* x) {
        if (x && x->reversed) {
            x->reversed = false;
            std::swap(x->left, x->right);
            if (x->left) x->left->reversed ^= true;
            if (x->right) x->right->reversed ^= true;
        }
    }

    void rotate(Node* x) {
        Node* p = x->parent;
        Node* g = p->parent;
        push(p); push(x);

        if (x == p->left) {
            p->left = x->right;
            if (x->right) x->right->parent = p;
            x->right = p;
        } else {
            p->right = x->left;
            if (x->left) x->left->parent = p;
            x->left = p;
        }
        p->parent = x;
        x->parent = g;
        if (g) {
            if (p == g->left) g->left = x;
            else if (p == g->right) g->right = x;
        }
    }

    void splay(Node* x) {
        while (!isRoot(x)) {
            Node* p = x->parent;
            if (!isRoot(p)) {
                Node* g = p->parent;
                push(g);
                if ((x == p->left) == (p == g->left)) { rotate(p); rotate(x); }
                else { rotate(x); rotate(x); }
            } else {
                push(p);
                rotate(x);
            }
        }
        push(x);
    }

    Node* access(Node* x) {
        Node* last = nullptr;
        for (Node* y = x; y; y = y->parent) {
            splay(y);
            y->right = last;
            last = y;
        }
        splay(x);
        return last;
    }

    void makeRoot(Node* x) {
        access(x);
        x->reversed ^= true;
    }

public:
    LinkCutTree(int n) : nodes(n) {
        for (int i = 0; i < n; i++) nodes[i] = new Node(i);
    }

    void link(int u, int v) {
        makeRoot(nodes[u]);
        nodes[u]->parent = nodes[v];
    }

    void cut(int u, int v) {
        makeRoot(nodes[u]);
        access(nodes[v]);
        if (nodes[v]->left == nodes[u]) {
            nodes[v]->left = nullptr;
            nodes[u]->parent = nullptr;
        }
    }

    bool connected(int u, int v) {
        makeRoot(nodes[u]);
        access(nodes[v]);
        Node* curr = nodes[v];
        while (curr->left) curr = curr->left;
        return curr == nodes[u];
    }

    int findRoot(int u) {
        access(nodes[u]);
        Node* curr = nodes[u];
        while (curr->left) { push(curr); curr = curr->left; }
        splay(curr);
        return curr->id;
    }
};

int main() {
    LinkCutTree lct(6);
    lct.link(0, 1); lct.link(1, 2); lct.link(2, 3);

    std::cout << "0-3 connected: " << lct.connected(0, 3) << "\n"; // 1
    lct.cut(1, 2);
    std::cout << "0-3 connected: " << lct.connected(0, 3) << "\n"; // 0

    lct.link(3, 4); lct.link(4, 5);
    std::cout << "Find root of 5: " << lct.findRoot(5) << "\n"; // 3

    return 0;
}
```

### Python Implementation

```python
class LinkCutTree:
    class Node:
        def __init__(self, id):
            self.id = id
            self.left = self.right = self.parent = None
            self.reversed = False

    def __init__(self, n):
        self.nodes = [self.Node(i) for i in range(n)]

    def _is_root(self, x):
        return not x.parent or (x.parent.left != x and x.parent.right != x)

    def _push(self, x):
        if x and x.reversed:
            x.reversed = False
            x.left, x.right = x.right, x.left
            if x.left: x.left.reversed ^= True
            if x.right: x.right.reversed ^= True

    def _rotate(self, x):
        p = x.parent
        g = p.parent
        self._push(p); self._push(x)
        if x == p.left:
            p.left = x.right
            if x.right: x.right.parent = p
            x.right = p
        else:
            p.right = x.left
            if x.left: x.left.parent = p
            x.left = p
        p.parent = x
        x.parent = g
        if g:
            if p == g.left: g.left = x
            elif p == g.right: g.right = x

    def _splay(self, x):
        while not self._is_root(x):
            p = x.parent
            if not self._is_root(p):
                g = p.parent
                self._push(g)
                if (x == p.left) == (p == g.left):
                    self._rotate(p); self._rotate(x)
                else:
                    self._rotate(x); self._rotate(x)
            else:
                self._push(p)
                self._rotate(x)
        self._push(x)

    def _access(self, x):
        last = None
        y = x
        while y:
            self._splay(y)
            y.right = last
            last = y
            y = y.parent
        self._splay(x)
        return last

    def _make_root(self, x):
        self._access(x)
        x.reversed ^= True

    def link(self, u, v):
        self._make_root(self.nodes[u])
        self.nodes[u].parent = self.nodes[v]

    def cut(self, u, v):
        self._make_root(self.nodes[u])
        self._access(self.nodes[v])
        if self.nodes[v].left == self.nodes[u]:
            self.nodes[v].left = None
            self.nodes[u].parent = None

    def connected(self, u, v):
        self._make_root(self.nodes[u])
        self._access(self.nodes[v])
        curr = self.nodes[v]
        while curr.left:
            curr = curr.left
        return curr == self.nodes[u]

    def find_root(self, u):
        self._access(self.nodes[u])
        curr = self.nodes[u]
        while curr.left:
            self._push(curr)
            curr = curr.left
        self._splay(curr)
        return curr.id

# Example
lct = LinkCutTree(6)
lct.link(0, 1); lct.link(1, 2); lct.link(2, 3)
print(f"0-3 connected: {lct.connected(0, 3)}")  # True
lct.cut(1, 2)
print(f"0-3 connected: {lct.connected(0, 3)}")  # False
lct.link(3, 4); lct.link(4, 5)
print(f"Find root of 5: {lct.find_root(5)}")  # 3
```

### Complexity

| Operation | Amortized Time | Space |
|---|---|---|
| access | O(log n) | O(1) |
| link | O(log n) | O(1) |
| cut | O(log n) | O(1) |
| findRoot | O(log n) | O(1) |
| connected | O(log n) | O(1) |

---

## 157.2 Euler Tour Trees

### Definition

An **Euler Tour Tree (ETT)** represents a tree using its Euler tour stored in a balanced BST. Each edge is traversed twice (forward and back), giving 2n-1 entries.

### Operations

- **Link(u, v)**: Split BST at u's tour, insert v's tour
- **Cut(u, v)**: Remove the segment corresponding to edge (u,v)
- **Connectivity**: Two nodes are connected iff they're in the same BST

### Comparison with Link-Cut Trees

| Feature | LCT | ETT |
|---|---|---|
| Path queries | O(log n) | O(log² n) |
| Subtree queries | Hard | O(log n) |
| Link/Cut | O(log n) | O(log n) |
| Implementation | Complex | Moderate |

---

## Exercises

1. **Implement path sum**: Extend the LCT to support path sum queries. Add a `val` field to each node and maintain subtree aggregates in the splay tree.

2. **Dynamic connectivity**: Use LCT to solve dynamic connectivity: process edge insertions and deletions, answer "are u and v connected?" queries.

3. **Euler Tour Tree**: Implement an ETT using a balanced BST (e.g., treap). Support link, cut, and connectivity queries.

4. **LCT for MST**: Use LCT to maintain a minimum spanning tree under edge insertions. (Hint: when inserting an edge, if it creates a cycle, remove the heaviest edge on the cycle.)

---

## Interview Questions

1. **Q: What is the access operation in Link-Cut Trees?**
   A: `access(u)` restructures the preferred paths so that the path from the root to u becomes a single preferred path (one splay tree). This is the fundamental operation that enables all other operations.

2. **Q: How do Link-Cut Trees achieve O(log n) per operation?**
   A: By representing preferred paths as splay trees. The access operation performs O(log n) splay operations amortized. Since splay trees have O(log n) amortized operations, the total is O(log n).

3. **Q: When would you use LCT vs. HLD?**
   A: HLD is for static trees (structure doesn't change). LCT is for dynamic trees (edges added/removed). HLD is simpler to implement. Use LCT when the tree structure changes over time.

4. **Q: What's the difference between LCT and Euler Tour Trees?**
   A: LCT excels at path queries (O(log n)) via preferred path decomposition. ETT excels at subtree queries (O(log n)) via Euler tour ordering. LCT is harder to implement but more versatile for path operations.

---

## Cross-References

- [Chapter 98: Splay Trees](ch98-splay-trees.md) — LCT uses splay trees for preferred paths
- [Chapter 107: HLD and Centroid Applications](ch107-hld-centroid-applications.md) — Static tree decomposition (HLD is the static version of LCT ideas)
- [Chapter 13: Trees](ch13-trees.md) — Tree fundamentals

---

## Summary

| Structure | link | cut | connected | path query |
|---|---|---|---|---|
| Link-Cut Tree | O(log n) | O(log n) | O(log n) | O(log n) |
| Euler Tour Tree | O(log n) | O(log n) | O(log n) | O(log² n) |
| HLD (static) | N/A | N/A | N/A | O(log² n) |
