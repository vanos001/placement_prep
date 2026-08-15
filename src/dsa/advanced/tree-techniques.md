# Advanced Tree Techniques

Beyond the basic DFS/BFS and LCA covered in [Ch 13](../chapters/ch13-trees.md) and [Ch 84](../chapters/ch84-tree-algorithms-advanced.md), this file covers the arsenal of tree decomposition and query techniques essential for competitive programming and advanced interview problems: centroid decomposition, HLD, DSU on tree, virtual trees, tree hashing, rerooting DP, small-to-large merging, centroid path decomposition, tree isomorphism, and tree automata.

---

## Centroid Decomposition

### Concept

A **centroid** of a tree is a node whose removal leaves no component with more than $n/2$ nodes. Every tree has at least one centroid (at most two). **Centroid decomposition** recursively splits the tree at centroids, building a "centroid tree" of height $O(\log n)$.

```
Original tree:           Centroid tree ("CT"):
       1                      3
      /|\                    /|\
     2 3 4                  1 6 7
    /|  |\                  |
   5 6 7 8 9               2
   |                        \
   10                       4
  Centroids: 3 (size 10, max subtree 4)
  Then: 1 (subtree of size 3), 6 (size 3), 7 (size 1)
```

### Algorithm

```
function decompose(root, parent_ct):
    c = find_centroid(root)        # O(n) DFS to find
    c.ct_parent = parent_ct         # connect in centroid tree
    mark c as deleted
    for each neighbor v of c:
        if v not deleted:
            decompose(v, c)         # recurse on each component
```

### Complexity

- Building the centroid tree: $O(n \log n)$ total (each node is visited $O(\log n)$ times across all levels).
- Queries that travel up the centroid tree visit $O(\log n)$ centroids.

### Classic Applications

- **Distance queries**: For each centroid $c$, precompute distances from $c$ to all nodes in its component. To answer $\text{dist}(u, v)$, climb the centroid tree from $u$ and $v$, using the LCA in the centroid tree to combine distances.
- **Path counting**: Count paths of length $\leq k$ by, for each centroid $c$, counting pairs in different subtrees of $c$ whose combined distance $\leq k$. This gives an $O(n \log^2 n)$ solution.
- **Nearest colored node**: Precompute, for each centroid, the nearest marked node in each subtree. Query in $O(\log^2 n)$.

> **Interview Angle**: "Count pairs of nodes in a tree at distance exactly $k$." Answer: centroid decomposition — for each centroid, use a frequency array of distances, count pairs from different subtrees summing to $k$, total $O(n \log^2 n)$.

---

## Heavy-Light Decomposition (HLD)

HLD is covered in [Ch 107](../chapters/ch107-hld-centroid-applications.md). Here we cover advanced HLD topics and comparison with centroid decomposition.

### HLD for Path Queries with Segment Tree

The standard HLD+segment tree combination allows $O(\log^2 n)$ path queries. Advanced variants:

- **HLD + BIT**: When the query is a prefix-sum-type operation (add on path, query subtree), BIT gives $O(\log^2 n)$ but with a smaller constant than segment tree.
- **HLD with lazy propagation**: Support range updates and range queries on tree paths.
- **HLD with persistent segment tree**: Answer historical path queries ("what was the sum on path $u$-$v$ after the $k$-th update?").

### HLD vs Centroid Decomposition

| Criterion | HLD | Centroid Decomposition |
-----------|-----|----------------------|
| Path queries | Natural (decompose into $O(\log n)$ segments) | Less natural (need centroid tree climbing) |
| Subtree queries | Single segment tree range query | Need special handling |
| Nearest-neighbor type | Segment tree on chains | Climb centroid tree |
| Modification | Point/segment tree updates | Rebuild subtrees in centroid tree |
| Height | $O(n)$ worst case (chain) | $O(\log n)$ always |
| Best for | Path aggregates, edge updates | Distance queries, path counting, divide-and-conquer on trees |

---

## DSU on Tree (Sack)

### Problem

For each node $v$, compute an aggregate over the subtree of $v$ (e.g., count of distinct colors, frequency of values). Naive: $O(n^2)$ by running a DFS from each node.

### Idea

Process nodes in a specific order: always process the **big child** (heaviest subtree) **last**, and reuse its computation.

```
function dfs(v, parent, keep):
    big_child = child of v with largest subtree
    for each child c of v except big_child:
        dfs(c, v, false)    # compute and discard
    dfs(big_child, v, true)  # compute and keep
    # Now big_child's data is in the global structure
    for each child c of v except big_child:
        add_subtree(c, v)    # re-add their contributions
    add_node(v)              # add v itself
    answer[v] = query()      # answer for v's subtree
    if not keep:
        remove_subtree(v)    # clean up
```

### Complexity

Each node is added to the data structure $O(\log n)$ times: once for each ancestor where its subtree switches from "big child" to "non-big child." Total: $O(n \log n)$.

### Applications

- Count distinct colors in each subtree.
- Find the most frequent value in each subtree.
- Compute XOR of subtree values modulo queries.

> **Interview Angle**: "For each node, find the most frequent color in its subtree." Describe DSU on tree: $O(n \log n)$ by always keeping the big child's computation and re-adding small children.

---

## Virtual Trees

### Problem

Given a tree with $n$ nodes and a set $S$ of $k$ **active** nodes ($k \ll n$), build a tree on exactly the nodes in $S$ plus their pairwise LCAs that preserves the ancestor relationships and path structure of the original tree. The virtual tree has $O(k)$ nodes.

### Construction

1. Sort all active nodes by DFS order.
2. Compute the LCA of consecutive pairs in this order.
3. Collect all active nodes and LCAs into a set $V$ (size $O(k)$).
4. Sort $V$ by DFS order.
5. Build the virtual tree using a stack: push nodes in DFS order, maintaining the rightmost path.

```
function build_virtual_tree(active_nodes):
    sort active_nodes by dfs_order
    nodes = active_nodes + {lca(active_nodes[i], active_nodes[i+1]) for all i}
    remove duplicates, sort by dfs_order
    stack = [nodes[0]]
    for i = 1 to len(nodes)-1:
        l = lca(stack.top(), nodes[i])
        while dfs_order[stack.top()] > dfs_order[l]:
            pop stack
        if stack.top() != l:
            add_edge(l, stack.top())  # l is parent of stack.top() in virtual tree
            stack.pop()
            stack.push(l)
        stack.push(nodes[i])
    # Remaining edges: connect stack elements in order
```

**Complexity**: $O(k \log k)$ with $O(1)$ LCA, or $O(k \log n)$ with binary lifting LCA.

### Applications

- **Tree DP on a subset**: When only $k$ of $n$ nodes are "interesting," build the virtual tree and run DP on $O(k)$ nodes instead of $O(n)$.
- **Multiple root-to-node path queries**: Preprocess the virtual tree for efficient batch queries.
- **Competitive programming**: Extremely common in problems where $k$ key nodes are given and queries involve paths between them.

---

## Tree Hashing and Tree Isomorphism

### AHU Algorithm for Unrooted Tree Isomorphism

Two unrooted trees are isomorphic if and only if their **centers** (1 or 2 nodes) have isomorphic rooted subtrees. For rooted trees, use a canonical hash.

### Rooted Tree Hashing

Assign a hash to each node based on the multiset of its children's hashes. Sort children by their hashes for a canonical representation.

```
function tree_hash(v, parent):
    child_hashes = []
    for each child c of v:
        if c != parent:
            child_hashes.append(tree_hash(c, v))
    sort(child_hashes)
    return hash(v.value, child_hashes)  # e.g., polynomial hash
```

**Complexity**: $O(n \log n)$ per tree (sorting at each node). Total across all nodes, the sorting cost is bounded by $O(n \log n)$ via the analysis that each node contributes $O(\log \deg(v))$ and $\sum \log \deg(v) \leq n \log n$.

### Tree Isomorphism Testing

Two rooted trees are isomorphic iff their canonical hashes are equal. For unrooted trees, try both possible centers.

### Applications in CP

- Checking if two subtrees are identical.
- Counting distinct subtrees in a tree (use a set of hashes).
- Pattern matching in trees (tree pattern matching).

---

## Centroid Path Decomposition

### Concept

Decompose the tree into **centroid paths**: repeatedly find the centroid, extract the path from the centroid to the deepest node in its heaviest subtree, remove the path, and recurse. This yields $O(\sqrt{n})$ paths with total length $O(n)$.

### Applications

- **Static tree queries**: Like HLD but with $O(\sqrt{n})$ paths instead of $O(n)$. Some queries benefit from the coarser decomposition.
- **Tree editing distance**: Used in algorithms for computing edit distance between trees.

---

## Small-to-Large Merging

### Technique

When merging sets associated with children of a tree node, always merge the **smaller set into the larger set**. This guarantees each element moves at most $O(\log n)$ times.

```
function dfs(v, parent):
    my_set = {v.value}
    for each child c of v:
        child_set = dfs(c, v)
        if len(child_set) > len(my_set):
            swap(my_set, child_set)
        for x in child_set:        # merge small into large
            my_set.add(x)
    answer[v] = len(my_set)
    return my_set
```

**Complexity**: $O(n \log n)$ total for any mergeable operation. Each element participates in $O(\log n)$ merges before its set becomes the "large" one permanently.

### Applications

- Count distinct colors in subtrees.
- Find the most frequent element in each subtree.
- Merge maps/dictionaries in tree DP.

---

## Rerooting DP

### Problem

Compute a DP value for **every node as root** of the tree. Naive: $O(n^2)$ (run DP from each root). Rerooting DP achieves $O(n)$.

### Technique

1. Run a standard DFS to compute DP values with an arbitrary root ("down" values).
2. Run a second DFS that propagates information from parent to children ("up" values), rerooting the tree at each step.

```
# Phase 1: standard DP (root at 0)
function dfs_down(v, parent):
    for each child c of v:
        if c != parent:
            dfs_down(c, v)
            dp_down[v] = merge(dp_down[v], dp_down[c])
    dp_down[v] = combine(dp_down[v], v.value)

# Phase 2: reroot
function dfs_up(v, parent, dp_from_parent):
    dp_total[v] = merge(dp_down[v], dp_from_parent)
    # Compute prefix/suffix merges of children
    prefix = [identity]
    for each child c of v (except parent):
        prefix.append(merge(prefix[-1], dp_down[c]))
    suffix = [identity]
    for each child c of v in reverse (except parent):
        suffix.append(merge(suffix[-1], dp_down[c]))
    # For each child, compute what DP they'd get if v were their child
    for i, child c of v (except parent):
        up_val = merge(dp_from_parent, prefix[i], suffix[n-2-i])
        up_val = combine(up_val, v.value)
        dfs_up(c, v, up_val)
```

**Complexity**: $O(n \cdot \text{merge cost})$. If merge is $O(1)$, total is $O(n)$. The prefix/suffix trick avoids $O(\deg^2)$ work at each node.

### Applications

- **All-pairs longest path through root**: Find, for each node $v$, the two longest paths from $v$ into different subtrees.
- **Tree DP for maximum matching where each node can be root**.
- **Compute subtree aggregates for every rooting**.

> **Interview Angle**: "For every node, find the sum of distances to all other nodes." Rerooting DP: first compute sum of distances from root 0, then for each child, adjust by adding/subtracting subtree sizes. $O(n)$ total.

---

## Tree Automata

### Concept

A **tree automaton** is a finite-state machine that processes trees (not strings). It reads the tree bottom-up, assigning a state to each node based on the states of its children and the node's label.

### Bottom-Up Tree Automaton

- **States**: $Q$
- **Transition function**: $\delta: \Sigma \times Q^k \to Q$ (for $k$-ary trees, but we can handle arbitrary arity)
- **Acceptance**: Root state is in the set of final states $F$

### Applications

- **XML/JSON schema validation**: Verify that a document tree conforms to a schema.
- **Code analysis**: Abstract syntax tree pattern matching.
- **Tree pattern matching in compilers**: Recognize optimization opportunities.
- **Database XML query processing**: XPath evaluation.

### Complexity

- Membership testing: $O(n)$ where $n$ is the number of nodes.
- Emptiness problem (does any tree match?): PSPACE-complete for general tree automata, linear for deterministic.

---

## Technique Comparison Summary

| Technique | Preprocess | Per Query | Best For |
-----------|-----------|-----------|----------|
| Centroid Decomposition | $O(n \log n)$ | $O(\log n)$ or $O(\log^2 n)$ | Distance, path counting, divide-and-conquer |
| HLD | $O(n)$ | $O(\log^2 n)$ | Path aggregates, updates on paths |
| DSU on Tree | N/A | $O(n \log n)$ total | Subtree queries for all nodes |
| Virtual Tree | $O(k \log k)$ | $O(k)$ | Batch queries on small subsets |
| Rerooting DP | $O(n)$ | $O(1)$ per node | DP from every root |
| Small-to-Large | N/A | $O(n \log n)$ total | Merging subtree information |
| Tree Hashing | $O(n \log n)$ | $O(1)$ comparison | Isomorphism, subtree matching |

## Further Reading

- [Ch 84: Tree Algorithms Advanced](../chapters/ch84-tree-algorithms-advanced.md) — base tree algorithms
- [Ch 107: HLD and Centroid Applications](../chapters/ch107-hld-centroid-applications.md) — HLD and centroid basics
- [Ch 108: DSU on Tree and Rerooting](../chapters/ch108-dsu-on-tree-rerooting.md) — DSU on tree and rerooting basics
- [Ch 106: Euler-Tour Tree Flattening](../chapters/ch106-euler-tour-tree-flattening.md) — Euler tour technique
