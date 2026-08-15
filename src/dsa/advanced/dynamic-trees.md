# Dynamic Trees: Connectivity, MST, and Forest Data Structures

Maintaining a forest under edge insertions, deletions, and path queries is a fundamental problem. Static trees support these operations after preprocessing, but **fully dynamic** forests require sophisticated data structures. This file covers the major approaches: Euler-tour trees, link-cut trees, top trees, and their applications to dynamic MST and connectivity.

---

## Dynamic Connectivity Problem

### Definition

Maintain an undirected graph under intermixed **edge insertions**, **edge deletions**, and **connectivity queries** ($u \stackrel{?}{\sim} v$). We want sublinear update and query time.

### Lower Bounds

- With $O(\log n)$ update, the best known query time is $O(\log n / \log \log n)$ (Pătraşcu & Thorup, 2011).
- An $\Omega(\log n)$ amortized lower bound exists for any dynamic connectivity structure based on cell-probe model arguments.
- The **dynamic connectivity conjecture** posits that no structure achieves $O(\text{polylog}\ n)$ for both updates and queries on general graphs.

### Holm–de Lichtenberg–Thorup (HDLT) Algorithm

The breakthrough $O(\log^2 n)$ amortized algorithm for fully dynamic connectivity on general undirected graphs.

**Two-level structure**:
- **Level 0** (everything): All edges. Use Euler-tour trees (ETT) to maintain spanning forests. On deletion, find a replacement edge by searching the 2-edge-connected component (using a low-level ETT).
- **Level $i$**: A subgraph of edges that have survived $\geq i$ deletions without being replaced. Sparser, so searches are faster.

**Key insight**: An edge promoted to level $i$ means it is "reliable" — it survived many deletion events. Higher levels have fewer edges, making replacement-edge searches fast.

```
function HDT_insert(u, v):
    insert edge (u,v) at level 0
    add to ETT at level 0

function HDT_delete(u, v):
    remove (u,v) from its current level i
    if (u,v) was a tree edge in the spanning forest at level i:
        search for replacement edge at level i
        if found:
            add replacement edge to spanning forest
            promote replacement edge to level i+1
        else:
            search at level i-1, i-2, ..., 0
            if still no replacement:
                the spanning forest splits
```

**Complexity**: $O(\log^2 n)$ amortized per update, $O(\log n / \log \log n)$ per query. The amortized analysis relies on the fact that each edge can be promoted only $O(\log n)$ times.

> **Interview Angle**: "Design a data structure for a social network that supports friend/unfriend and connectivity queries." Describe the HDLT approach at a high level: maintain spanning forests with levels, promote reliable edges, search higher levels first.

---

## Euler-Tour Trees (ETT)

### Concept

Represent a forest by an **Euler tour** of each tree: for each edge $(u,v)$ in the tree, store both $(u,v)$ and $(v,u)$ in a sequence. This sequence is maintained in a balanced BST. Operations on the Euler tour correspond to tree operations.

```
Tree:          Euler Tour (sequence):
    a          (a,b) (b,a) (a,c) (c,a)
   / \
  b   c
```

The Euler tour of a tree with $n$ nodes has exactly $2(n-1)$ entries (two per tree edge).

### Operations

| Operation | Implementation | Complexity |
-----------|---------------|------------|
| `link(u, v)` | Merge the two BST sequences (concatenate) | $O(\log n)$ |
| `cut(u, v)` | Split the BST sequence at the two edge entries | $O(\log n)$ |
| `connected(u, v)` | Check if $u$ and $v$ are in the same BST | $O(\log n)$ |
| `size(u)` | Subtree size in BST | $O(\log n)$ |
| `path_aggregate(u, v)` | Not directly supported | Need link-cut tree |

### Implementation with Balanced BSTs

Any balanced BST supporting split/merge works: treap, splay tree, or red-black tree. For the HDLT algorithm, each level maintains its own ETT.

```cpp
struct ETTNode {
    int vertex, parent_in_tree;  // what this entry represents
    ETTNode *l, *r, *p;
    int size;  // subtree size in BST
    // augment with: tree_size, sum, etc.
};

// link(u, v): make u a child of v
// 1. Find the end of u's Euler tour
// 2. Find the position of v in v's Euler tour  
// 3. Split v's tour at that position
// 4. Concatenate: v_prefix + u_tour + (v,u) + (u,v) + v_suffix

// cut(u, v): remove edge (u,v)
// 1. Find (u,v) and (v,u) in the tour
// 2. Split into segments, remove the two edge entries
// 3. Recombine remaining segments
```

### Limitations

ETTs support **forest-level** operations (link, cut, connectivity) efficiently but **not path queries** (aggregate along the path $u \to v$). For path queries, we need link-cut trees.

---

## Link-Cut Trees (LCT)

The link-cut tree ([base coverage](../chapters/ch157-link-cut-trees.md)) maintains a forest of rooted trees supporting **path operations** in $O(\log n)$ amortized. Here we cover the advanced aspects.

### Splay-Based Implementation Deep Dive

Each node in the forest is represented by a **splay node**. The tree is decomposed into **preferred paths**: for each node, the most recently accessed child is the "preferred child." Preferred paths form a decomposition of each tree into vertex-disjoint paths.

```
        a               a
       / \             / \
      b   e    -->   [b-c-d]  e
     / \                |
    c   f               f
   /
  d

Preferred path: [b, c, d] stored as a splay tree
Non-preferred edges: a-b, e-a, b-f (stored as parent pointers)
```

Each preferred path is stored in a splay tree keyed by depth. The auxiliary tree (splay tree of a preferred path) is connected to its parent path via a **path-parent** pointer (the node just above the path's topmost node).

### Access(v) — The Core Operation

`access(v)` makes $v$ the preferred child of its parent all the way to the root, creating a single preferred path from $v$ to the root.

```
function access(v):
    splay(v)
    v.right = nil       # detach old preferred subtree
    push(v)             # update v's subtree info
    while v.path_parent != nil:
        w = v.path_parent
        splay(w)
        w.right = nil    # detach w's old preferred child
        push(w)
        w.right = v      # make v's path w's preferred subtree
        v.path_parent = nil
        push(w)
        v = w
    splay(v)
```

### Path Aggregates

Each node stores an aggregate value (sum, max, min, XOR) over its subtree in the auxiliary tree. By accessing $u$ and $v$, we can query the path between them.

```
function path_query(u, v):
    make_root(u)        # reroot so u is the root of its tree
    access(v)           # preferred path from u to v
    splay(v)
    return v.subtree_aggregate  # the entire preferred path u->v
```

### Advanced Applications

- **Dynamic MST**: Maintain the minimum spanning tree of a graph under edge weight changes. When an edge is inserted, if it creates a cycle, find the maximum-weight edge on the path and replace it (using LCT for path-max queries). $O(\log^2 n)$ per update via [Holm et al.](#fully-dynamic-mst).
- **Dynamic diameter**: Maintain the diameter of a dynamic forest using LCT with diameter augmentation (each node stores the farthest pair in its subtree).
- **Dynamic center**: Find the center of a tree that changes under link/cut operations.
- **Edge-weighted LCT**: Each edge has a weight; path queries compute sum/max along the path.

### LCT Complexity Details

All operations are $O(\log n)$ **amortized**. The amortization uses the **splay tree access lemma**: the total cost of a sequence of $m$ accesses is $O(m \log n + n \log n)$. No $O(\log n)$ **worst-case** bound is known for LCTs.

---

## Top Trees

### Motivation

Link-cut trees decompose a tree into **paths**. **Top trees** decompose into **clusters** (connected subgraphs with at most two "boundary" vertices). This more general decomposition can maintain a richer set of aggregate information.

### Cluster Decomposition

A **cluster** is a connected subgraph with at most two designated **boundary vertices** (external connection points). Clusters are organized in a binary tree called the **top tree**.

```
Original tree:          Top tree (cluster hierarchy):
    a                    [a,b,c,d,e]          (root cluster)
   /|\                   /          \
  b c d              [a,b,c]      [d,e]
  | |                /     \
  e f            [a,b]   [c]  [d] [e]
```

**Leaf clusters**: Single edges of the original tree.
**Internal clusters**: Union of two child clusters sharing exactly one boundary vertex.

### Operations

| Operation | Description | Complexity |
-----------|-------------|------------|
| `link(u, v)` | Add edge $(u,v)$ | $O(\log n)$ |
| `cut(u, v)` | Remove edge $(u,v)$ | $O(\log n)$ |
| `expose(u, v)` | Create a cluster containing the $u$-$v$ path | $O(\log n)$ |
| `path_query(u, v)` | Aggregate on $u$-$v$ path | $O(\log n)$ |
| `subtree_query(v, root)` | Aggregate on $v$'s subtree | $O(\log n)$ |

### Top Trees vs. Link-Cut Trees

| Feature | Link-Cut Tree | Top Tree |
|---------|--------------|----------|
| Decomposition | Paths | General clusters |
| Path queries | Yes | Yes |
| Subtree queries | Difficult (need ETT) | Natural |
| Implementation | Splay-based | Splay-based or self-adjusting |
| Flexibility | Limited augmentations | Rich (any mergeable cluster info) |
| Practical use | Common in CP | Rare in CP, more theoretical |

---

## Fully Dynamic MST

### Problem

Maintain the MST of a graph $G = (V, E)$ as edges are inserted and deleted.

### Holm–de Lichtenberg–Thorup Approach

Uses the level-based framework from dynamic connectivity, combined with link-cut trees for efficient path-max queries.

**Key idea**: Maintain a spanning forest $F$ for each level. When a non-tree edge is inserted, ignore it (it's redundant). When a tree edge $e$ is deleted, search for a replacement among non-tree edges. The search uses the LCT to find the minimum-weight edge crossing the cut created by removing $e$.

```
function dynamic_mst_delete(e):
    if e is not in MST: return
    level = e.level
    remove e from MST
    # Search for replacement edge crossing the cut
    for l = level down to 0:
        candidates = non-tree edges at level l crossing the cut
        replacement = min_weight(candidates)  # via LCT path query
        if replacement exists:
            add replacement to MST
            promote replacement to level l+1
            return
    # No replacement found: MST splits, no longer spans
```

**Complexity**: $O(\log^2 n)$ amortized per update. Each edge is promoted $O(\log n)$ times and each level's LCT operations cost $O(\log n)$.

> **Interview Angle**: "How would you maintain an MST in a network where links go up and down frequently?" Describe the level-based approach: maintain spanning forests at multiple levels, promote edges that survive many deletions, use LCTs for path-max queries to find replacement edges quickly.

---

## Comparison Table

| Structure | Connectivity | Path Query | Subtree Query | Link/Cut | Update | Space |
-----------|:------------:|:----------:|:-------------:|:--------:|--------|-------|
| Union-Find | $\alpha(n)$ | No | No | Link only | $\alpha(n)$ | $O(n)$ |
| ETT | $O(\log n)$ | No | No | Both | $O(\log n)$ | $O(n)$ |
| LCT | $O(\log n)$ | $O(\log n)$ | Hard | Both | $O(\log n)^*$ | $O(n)$ |
| Top Tree | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | Both | $O(\log n)^*$ | $O(n)$ |
| HDLT | $O(\log^2 n)$ | No | No | Both | $O(\log^2 n)$ | $O(n \log n)$ |

$^*$ amortized

## Further Reading

- Sleator & Tarjan, "A Data Structure for Dynamic Trees" (1983) — the original LCT paper
- Holm, de Lichtenberg, Thorup, "Poly-logarithmic Deterministic Fully Dynamic Graph Algorithms" (2001) — HDLT
- Alstrup, Holm, de Lichtenberg, Thorup, "Maintaining Information in Fully Dynamic Trees with Top Trees" (2005) — top trees
- Tarjan, "Dynamic Trees as Search Trees via Euler Tours" (2014) — ETT perspective
- [Ch 157: Link-Cut Trees](../chapters/ch157-link-cut-trees.md) — base chapter
- [Ch 156: Dynamic Graph Algorithms](../chapters/ch156-dynamic-graph-algorithms.md) — broader dynamic graph topic
