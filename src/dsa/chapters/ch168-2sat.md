# Chapter 168: 2-SAT (2-Satisfiability)

## 1. Definition

**2-SAT** (2-Satisfiability) is a special case of the Boolean Satisfiability Problem where each clause contains **at most two literals**. Given a Boolean formula in Conjunctive Normal Form (CNF) with clauses of size ≤ 2, determine if there exists an assignment of variables that makes the entire formula true.

A **literal** is a variable x or its negation ¬x. A **2-CNF formula** has the form:

```
(l₁₁ ∨ l₁₂) ∧ (l₂₁ ∨ l₂₂) ∧ ... ∧ (lₘ₁ ∨ lₘ₂)
```

## 2. Motivation

### The SAT Hierarchy

| Problem | Clause Size | Complexity |
|---|---|---|
| 1-SAT | 1 | O(n) — trivial |
| **2-SAT** | ≤ 2 | **O(n + m) — polynomial** |
| 3-SAT | ≤ 3 | NP-complete |
| General SAT | any | NP-complete |

2-SAT is the largest "k-SAT" admitting a polynomial-time solution. It appears in:
- **Competitive programming**: constraint satisfaction, scheduling, logic puzzles
- **Circuit design**: verification of combinational logic
- **AI planning**: propositional reasoning
- **Graph coloring**: 2-colorability problems

### Why 2-SAT is Special

With only two literals per clause, the constraint structure forms a **directed implication graph** analyzable via Strongly Connected Components (SCC). This graph-theoretic connection makes it solvable in linear time.

## 3. Intuition

### From Clauses to Implications

Consider the clause (x ∨ y): "at least one of x, y must be true." Rewrite as implications:

```
¬x → y    (if x is false, y must be true)
¬y → x    (if y is false, x must be true)
```

Similarly, (¬x ∨ y) means x → y and ¬y → ¬x.

**Key insight**: Every 2-SAT clause generates two directed edges in an implication graph. The formula is satisfiable if and only if no variable and its negation are in the same SCC.

### The Contradiction Intuition

If x and ¬x are in the same SCC, there's a path from x to ¬x and from ¬x to x. This means:
- If x is true, then ¬x must also be true (contradiction)
- If x is false (¬x true), then x must also be true (contradiction)

No valid assignment exists.

## 4. Formal Framework

### 4.1 Variables and Literals

- **Variables**: x₁, x₂, ..., xₙ (n variables)
- **Literals**: xᵢ (positive) and ¬xᵢ (negative) — 2n total
- **Clauses**: (lᵢ₁ ∨ lᵢ₂) — m clauses

### 4.2 Implication Graph

Create a directed graph G with:
- **Vertices**: 2n vertices, one per literal (xᵢ and ¬xᵢ)
- **Edges**: For each clause (l₁ ∨ l₂), add edges ¬l₁ → l₂ and ¬l₂ → l₁

### 4.3 Core Theorem

**Theorem**: A 2-CNF formula is satisfiable if and only if no variable x has x and ¬x in the same strongly connected component of the implication graph.

**Proof (⇒)**: If x and ¬x are in the same SCC, then x → ¬x and ¬x → x. Setting x = true forces ¬x = true (contradiction); setting x = false forces x = true (contradiction). No assignment works.

**Proof (⇐)**: If no such pair exists, we construct an assignment (see Section 4.4).

### 4.4 Constructing the Assignment

After computing SCCs (via Kosaraju's or Tarjan's algorithm):

1. **Check feasibility**: For each variable xᵢ, verify comp[xᵢ] ≠ comp[¬xᵢ].
2. **Assign values**: Process SCCs in **reverse topological order** (sinks first).

**Why reverse topological order?** In the implication graph, if l₁ → l₂, setting l₁ = true forces l₂ = true. The SCC containing the "source" literals should be assigned first. Processing in reverse topological order ensures that when we encounter an SCC, all SCCs it implies have already been determined.

**Practical assignment rule** (using Kosaraju's numbering where components are numbered in topological order):

```python
for each variable x_i:
    if comp[x_i] > comp[¬x_i]:
        x_i = true
    else:
        x_i = false
```

The literal with the **higher** component number (later in topological order) is set to `true`.

## 5. Step-by-Step Walkthrough

### Example Formula (3 variables, 4 clauses)

```
(x₁ ∨ x₂) ∧ (¬x₁ ∨ x₃) ∧ (¬x₂ ∨ ¬x₃) ∧ (x₁ ∨ ¬x₃)
```

**Step 1: Build implication graph**

| Clause | Edges |
|---|---|
| (x₁ ∨ x₂) | ¬x₁ → x₂, ¬x₂ → x₁ |
| (¬x₁ ∨ x₃) | x₁ → x₃, ¬x₃ → ¬x₁ |
| (¬x₂ ∨ ¬x₃) | x₂ → ¬x₃, x₃ → ¬x₂ |
| (x₁ ∨ ¬x₃) | ¬x₁ → ¬x₃, x₃ → x₁ |

All edges:
```
x̄₁ → x₂       x̄₂ → x₁
x₁ → x₃        x̄₃ → x̄₁
x₂ → x̄₃        x₃ → x̄₂
x̄₁ → x̄₃       x₃ → x₁
```

**Step 2: Find SCCs (Kosaraju's)**

DFS from each vertex, then reverse graph DFS:

Forward DFS order (one possible): x₁ → x₃ → x̄₂ → x₁ (back edge), x̄₁ → x̄₃ → x̄₁ (back edge), x₂ → x̄₃ (already visited)

Let me trace more carefully:

Reverse graph edges:
```
x₂ → x̄₁       x₁ → x̄₂
x₃ → x₁        x̄₁ → x̄₃
x̄₃ → x₂        x̄₂ → x₃
x̄₃ → x̄₁       x₁ → x₃
```

Running Kosaraju's:
- First DFS on original graph, recording finish times
- Second DFS on reversed graph in reverse finish order

Result SCCs:
- SCC 1: {x₁, x₃, x̄₂} — (x₁ → x₃ → x₁ and x₃ → x̄₂ → x₁)
- SCC 2: {x̄₁, x₂, x̄₃} — (x̄₁ → x₂ → x̄₃ → x̄₁)

**Step 3: Check satisfiability**

| Variable | xᵢ in | ¬xᵢ in | Same SCC? |
|---|---|---|---|
| x₁ | SCC 1 | SCC 2 | No ✓ |
| x₂ | SCC 2 | SCC 1 | No ✓ |
| x₃ | SCC 1 | SCC 2 | No ✓ |

**Formula is satisfiable!**

**Step 4: Assign values**

SCC 2 is a sink (no outgoing edges to other SCCs). SCC 1 is a source.

Topological order: SCC 1 → SCC 2. Kosaraju numbering: comp(SCC 2) < comp(SCC 1).

Using the rule comp[xᵢ] > comp[¬xᵢ] → xᵢ = true:

| Variable | comp[xᵢ] | comp[¬xᵢ] | Assignment |
|---|---|---|---|
| x₁ | comp(SCC 1) | comp(SCC 2) | x₁ = true (comp 1 > comp 2) |
| x₂ | comp(SCC 2) | comp(SCC 1) | x₂ = false |
| x₃ | comp(SCC 1) | comp(SCC 2) | x₃ = true |

**Result: x₁ = T, x₂ = F, x₃ = T**

**Step 5: Verify**

```
(x₁ ∨ x₂)     = (T ∨ F) = T ✓
(¬x₁ ∨ x₃)    = (F ∨ T) = T ✓
(¬x₂ ∨ ¬x₃)   = (T ∨ F) = T ✓
(x₁ ∨ ¬x₃)    = (T ∨ F) = T ✓
```

All clauses satisfied! ✓

## 6. Another Example: Unsatisfiable Formula

```
(x₁ ∨ x₂) ∧ (¬x₁ ∨ x₂) ∧ (x₁ ∨ ¬x₂) ∧ (¬x₁ ∨ ¬x₂)
```

Edges:
```
x̄₁ → x₂,  x̄₂ → x₁     (from clause 1)
x₁ → x₂,   x̄₂ → x̄₁     (from clause 2)
x̄₁ → x̄₂,  x₂ → x₁     (from clause 3)
x₁ → x̄₂,  x₂ → x̄₁     (from clause 4)
```

SCCs: {x₁, x₂, x̄₁, x̄₂} — all in one SCC!

Since x₁ and x̄₁ are in the same SCC, the formula is **unsatisfiable**.

Verify: The four clauses together mean "both x₁ and x₂ must be true AND both must be false" — impossible.

## 7. Kosaraju's Algorithm Review

Since 2-SAT depends critically on SCC computation, here's a brief recap:

```
Kosaraju's Algorithm:
1. Run DFS on original graph, push vertices to stack in finish order
2. Transpose graph (reverse all edges)
3. Run DFS on transposed graph in stack order
4. Each DFS tree in step 3 is one SCC
```

**Time**: O(V + E) = O(n + m) where n = variables, m = clauses.

Tarjan's algorithm also works and is a single-pass alternative.

## 8. Handling Special Cases

### 8.1 Unit Clauses (1-SAT clauses)

A clause like (x) is equivalent to (x ∨ x). Add edge ¬x → x.

A clause like (¬x) is equivalent to (¬x ∨ ¬x). Add edge x → ¬x.

### 8.2 Implication-Only Clauses

(x → y) is equivalent to (¬x ∨ y). Same as a standard 2-SAT clause.

### 8.3 XOR Constraints

(x ⊕ y) means "exactly one of x, y is true." This expands to:
```
(x ∨ y) ∧ (¬x ∨ ¬y)
```
Two clauses, four edges. Handleable in 2-SAT.

### 8.4 At-Most-One Constraints

"At most one of x₁, x₂, ..., xₖ is true" can be encoded with O(k²) clauses or O(k) using auxiliary variables (sequential encoding).

## 9. Applications

### 9.1 Course Scheduling with Conflicts

Given n courses, each with two possible time slots, and pairs of courses that can't overlap, find a valid schedule.

**Model**: Variable xᵢ = true means course i takes slot A, false means slot B. For each conflict (i, j), if both courses in slot A would conflict: (¬xᵢ ∨ ¬xⱼ).

### 9.2 Planar Graph 2-Coloring

2-colorability is equivalent to 2-SAT: for each edge (u, v), add clauses ensuring u and v have different colors.

### 9.3 Puzzle Solving

Many logic puzzles (Sudoku variants, light-switch puzzles) reduce to 2-SAT when each constraint involves at most 2 variables.

### 9.4 Implication Closure

Computing what must be true given a set of implications is exactly 2-SAT.

### 9.5 Necessarily True Variables

To find which variables must be true in ALL satisfying assignments:
- xᵢ is necessarily true iff xᵢ and ¬xᵢ are in different SCCs AND there's a path from ¬xᵢ to xᵢ (i.e., comp[¬xᵢ] < comp[xᵢ] in topological order).

## 10. Complexity Analysis

| Step | Time | Space |
|---|---|---|
| Build implication graph | O(m) | O(n + m) |
| Find SCCs (Kosaraju/Tarjan) | O(n + m) | O(n + m) |
| Check satisfiability | O(n) | O(n) |
| Construct assignment | O(n) | O(n) |
| **Total** | **O(n + m)** | **O(n + m)** |

Where n = number of variables, m = number of clauses.

## 11. Code

### 11.1 C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

struct TwoSAT {
    int n;  // number of variables
    vector<vector<int>> adj, adj_rev;
    vector<int> comp, order, assignment;
    vector<bool> used;
    
    TwoSAT(int n) : n(n), adj(2 * n), adj_rev(2 * n), 
                    comp(2 * n), used(2 * n), assignment(n) {}
    
    // Add clause (a ∨ b)
    // a, b are literals: variable i true = 2*i, variable i false = 2*i+1
    void add_clause(int a, bool na, int b, bool nb) {
        // Convert to vertex indices
        // na=true means positive literal, na=false means negated
        a = 2 * a ^ (!na);  // a if na, a^1 if !na
        b = 2 * b ^ (!nb);
        
        // (a ∨ b) ≡ (¬a → b) ∧ (¬b → a)
        adj[a ^ 1].push_back(b);
        adj[b ^ 1].push_back(a);
        adj_rev[b].push_back(a ^ 1);
        adj_rev[a].push_back(b ^ 1);
    }
    
    void dfs1(int v) {
        used[v] = true;
        for (int u : adj[v])
            if (!used[u]) dfs1(u);
        order.push_back(v);
    }
    
    void dfs2(int v, int cl) {
        comp[v] = cl;
        for (int u : adj_rev[v])
            if (comp[u] == -1) dfs2(u, cl);
    }
    
    bool solve() {
        // Step 1: DFS on original graph
        fill(used.begin(), used.end(), false);
        for (int i = 0; i < 2 * n; i++)
            if (!used[i]) dfs1(i);
        
        // Step 2: DFS on reversed graph
        fill(comp.begin(), comp.end(), -1);
        for (int i = 0, j = 0; i < 2 * n; i++) {
            int v = order[2 * n - 1 - i];
            if (comp[v] == -1) dfs2(v, j++);
        }
        
        // Step 3: Check satisfiability and assign
        assignment.resize(n);
        for (int i = 0; i < n; i++) {
            if (comp[2 * i] == comp[2 * i + 1])
                return false;  // x and ¬x in same SCC
            assignment[i] = comp[2 * i] > comp[2 * i + 1];
        }
        return true;
    }
};

int main() {
    int n = 3, m = 4;
    TwoSAT ts(n);
    
    // (x₁ ∨ x₂), (¬x₁ ∨ x₃), (¬x₂ ∨ ¬x₃), (x₁ ∨ ¬x₃)
    // Variables: 0-indexed. add_clause(var, positive, var, positive)
    ts.add_clause(0, true, 1, true);    // x₁ ∨ x₂
    ts.add_clause(0, false, 2, true);   // ¬x₁ ∨ x₃
    ts.add_clause(1, false, 2, false);  // ¬x₂ ∨ ¬x₃
    ts.add_clause(0, true, 2, false);   // x₁ ∨ ¬x₃
    
    if (ts.solve()) {
        cout << "Satisfiable: ";
        for (int i = 0; i < n; i++)
            cout << "x" << i + 1 << "=" << ts.assignment[i] << " ";
        cout << endl;
    } else {
        cout << "Unsatisfiable" << endl;
    }
    return 0;
}
```

### 11.2 C++ — Alternative Literal Encoding

```cpp
// Cleaner encoding: literal encoding
// For variable i (0-indexed):
//   positive literal (xᵢ) = 2*i
//   negative literal (¬xᵢ) = 2*i + 1
// Negation: lit ^ 1

struct TwoSAT {
    int n;
    vector<vector<int>> g, gr;  // graph and reversed graph
    
    TwoSAT(int n) : n(n), g(2*n), gr(2*n) {}
    
    // Add implication: if a then b
    void add_implication(int a, int b) {
        g[a].push_back(b);
        gr[b].push_back(a);
    }
    
    // Add clause (a ∨ b) where a, b are literal indices
    void add_or(int a, int b) {
        add_implication(a ^ 1, b);  // ¬a → b
        add_implication(b ^ 1, a);  // ¬b → a
    }
    
    // Add clause that exactly one of a, b is true
    void add_xor(int a, int b) {
        add_or(a, b);       // at least one
        add_or(a^1, b^1);   // at most one
    }
    
    // Force literal a to be true
    void force_true(int a) {
        add_implication(a ^ 1, a);  // ¬a → a
    }
};
```

### 11.3 Python Implementation

```python
import sys
from collections import defaultdict

class TwoSAT:
    def __init__(self, n):
        self.n = n
        self.adj = defaultdict(list)
        self.adj_rev = defaultdict(list)
    
    def add_clause(self, a, na, b, nb):
        """
        Add clause (a ∨ b) where:
        a, b are variable indices (0-based)
        na, nb: True = positive literal, False = negated
        """
        # Convert to literal vertex indices
        # Variable i: positive = 2*i, negative = 2*i+1
        la = 2 * a if na else 2 * a + 1
        lb = 2 * b if nb else 2 * b + 1
        
        # ¬la → lb and ¬lb → la
        self.adj[la ^ 1].append(lb)
        self.adj[lb ^ 1].append(la)
        self.adj_rev[lb].append(la ^ 1)
        self.adj_rev[la].append(lb ^ 1)
    
    def solve(self):
        n_vertices = 2 * self.n
        used = [False] * n_vertices
        order = []
        comp = [-1] * n_vertices
        
        # DFS on original graph
        def dfs1(v):
            used[v] = True
            for u in self.adj[v]:
                if not used[u]:
                    dfs1(u)
            order.append(v)
        
        for i in range(n_vertices):
            if not used[i]:
                dfs1(i)
        
        # DFS on reversed graph
        def dfs2(v, cl):
            comp[v] = cl
            for u in self.adj_rev[v]:
                if comp[u] == -1:
                    dfs2(u, cl)
        
        label = 0
        for i in range(n_vertices - 1, -1, -1):
            v = order[i]
            if comp[v] == -1:
                dfs2(v, label)
                label += 1
        
        # Check and assign
        assignment = [False] * self.n
        for i in range(self.n):
            if comp[2 * i] == comp[2 * i + 1]:
                return None  # Unsatisfiable
            assignment[i] = comp[2 * i] > comp[2 * i + 1]
        
        return assignment

# Example usage
ts = TwoSAT(3)
ts.add_clause(0, True, 1, True)     # x₁ ∨ x₂
ts.add_clause(0, False, 2, True)    # ¬x₁ ∨ x₃
ts.add_clause(1, False, 2, False)   # ¬x₂ ∨ ¬x₃
ts.add_clause(0, True, 2, False)    # x₁ ∨ ¬x₃

result = ts.solve()
if result:
    print(f"Satisfiable: {['T' if x else 'F' for x in result]}")
else:
    print("Unsatisfiable")
# Output: Satisfiable: ['T', 'F', 'T']
```

### 11.4 Python — Iterative SCC (Avoiding Recursion Depth)

```python
def solve_iterative(self):
    n_vertices = 2 * self.n
    
    # Iterative DFS for order
    used = [False] * n_vertices
    order = []
    for start in range(n_vertices):
        if used[start]:
            continue
        stack = [(start, 0)]
        while stack:
            v, idx = stack[-1]
            used[v] = True
            if idx < len(self.adj[v]):
                u = self.adj[v][idx]
                stack[-1] = (v, idx + 1)
                if not used[u]:
                    stack.append((u, 0))
            else:
                stack.pop()
                order.append(v)
    
    # Iterative DFS for components
    comp = [-1] * n_vertices
    label = 0
    for i in range(n_vertices - 1, -1, -1):
        v = order[i]
        if comp[v] != -1:
            continue
        stack = [v]
        comp[v] = label
        while stack:
            cur = stack.pop()
            for u in self.adj_rev[cur]:
                if comp[u] == -1:
                    comp[u] = label
                    stack.append(u)
        label += 1
    
    assignment = [False] * self.n
    for i in range(self.n):
        if comp[2 * i] == comp[2 * i + 1]:
            return None
        assignment[i] = comp[2 * i] > comp[2 * i + 1]
    return assignment
```

### 11.5 Java Implementation

```java
import java.util.*;

public class TwoSAT {
    int n;
    List<List<Integer>> adj, adjRev;
    
    public TwoSAT(int n) {
        this.n = n;
        adj = new ArrayList<>();
        adjRev = new ArrayList<>();
        for (int i = 0; i < 2 * n; i++) {
            adj.add(new ArrayList<>());
            adjRev.add(new ArrayList<>());
        }
    }
    
    void addClause(int a, boolean na, int b, boolean nb) {
        int la = na ? 2 * a : 2 * a + 1;
        int lb = nb ? 2 * b : 2 * b + 1;
        adj.get(la ^ 1).add(lb);
        adj.get(lb ^ 1).add(la);
        adjRev.get(lb).add(la ^ 1);
        adjRev.get(la).add(lb ^ 1);
    }
    
    int[] solve() {
        int nv = 2 * n;
        boolean[] used = new boolean[nv];
        int[] order = new int[nv];
        int[] comp = new int[nv];
        Arrays.fill(comp, -1);
        int orderIdx = 0;
        
        // DFS1
        for (int i = 0; i < nv; i++) {
            if (!used[i]) {
                Deque<int[]> stack = new ArrayDeque<>();
                stack.push(new int[]{i, 0});
                while (!stack.isEmpty()) {
                    int[] top = stack.peek();
                    int v = top[0], idx = top[1];
                    used[v] = true;
                    if (idx < adj.get(v).size()) {
                        top[1]++;
                        int u = adj.get(v).get(idx);
                        if (!used[u]) stack.push(new int[]{u, 0});
                    } else {
                        stack.pop();
                        order[orderIdx++] = v;
                    }
                }
            }
        }
        
        // DFS2
        int label = 0;
        for (int i = nv - 1; i >= 0; i--) {
            int v = order[i];
            if (comp[v] != -1) continue;
            Deque<Integer> stack = new ArrayDeque<>();
            stack.push(v);
            comp[v] = label;
            while (!stack.isEmpty()) {
                int cur = stack.pop();
                for (int u : adjRev.get(cur)) {
                    if (comp[u] == -1) {
                        comp[u] = label;
                        stack.push(u);
                    }
                }
            }
            label++;
        }
        
        int[] assignment = new int[n];
        for (int i = 0; i < n; i++) {
            if (comp[2 * i] == comp[2 * i + 1]) return null;
            assignment[i] = comp[2 * i] > comp[2 * i + 1] ? 1 : 0;
        }
        return assignment;
    }
    
    public static void main(String[] args) {
        TwoSAT ts = new TwoSAT(3);
        ts.addClause(0, true, 1, true);    // x1 ∨ x2
        ts.addClause(0, false, 2, true);   // ¬x1 ∨ x3
        ts.addClause(1, false, 2, false);  // ¬x2 ∨ ¬x3
        ts.addClause(0, true, 2, false);   // x1 ∨ ¬x3
        
        int[] result = ts.solve();
        if (result != null) {
            System.out.print("Satisfiable: ");
            for (int i = 0; i < result.length; i++)
                System.out.printf("x%d=%s ", i+1, result[i] == 1 ? "T" : "F");
            System.out.println();
        } else {
            System.out.println("Unsatisfiable");
        }
    }
}
```

## 12. Dry Run: Complete Trace

For formula: (x₁ ∨ x₂) ∧ (¬x₁ ∨ x₃)

**Graph construction:**

Vertices: x₁(0), ¬x₁(1), x₂(2), ¬x₂(3), x₃(4), ¬x₃(5)

Clause (x₁ ∨ x₂): ¬x₁→x₂ (1→2), ¬x₂→x₁ (3→0)
Clause (¬x₁ ∨ x₃): x₁→x₃ (0→4), ¬x₃→¬x₁ (5→1)

Adjacency lists:
```
0: [4]       (x₁ → x₃)
1: [2]       (¬x₁ → x₂)
2: []        
3: [0]       (¬x₂ → x₁)
4: []        
5: [1]       (¬x₃ → ¬x₁)
```

Reversed:
```
0: [3]       (x₁ ← ¬x₂)
1: [5]       (¬x₁ ← ¬x₃)
2: [1]       (x₂ ← ¬x₁)
3: []        
4: [0]       (x₃ ← x₁)
5: []        
```

**DFS1 (finish order):**

Start at 0: 0→4, finish 4, finish 0. Order: [4, 0]
Start at 1: 1→2, finish 2, finish 1. Order: [4, 0, 2, 1]
Start at 3: 3→0 (visited), finish 3. Order: [4, 0, 2, 1, 3]
Start at 5: 5→1 (visited), finish 5. Order: [4, 0, 2, 1, 3, 5]

**DFS2 (on reversed, in reverse order 5,3,1,2,0,4):**

Start 5: comp[5]=0. From rev[5]: nothing. SCC {5} = comp 0.
Start 3: comp[3]=1. From rev[3]: nothing. SCC {3} = comp 1.
Start 1: comp[1]=2. From rev[1]: 5 (visited). SCC {1} = comp 2.
Start 2: comp[2]=3. From rev[2]: 1 (visited). SCC {2} = comp 3.
Start 0: comp[0]=4. From rev[0]: 3 (visited). SCC {0} = comp 4.
Start 4: comp[4]=5. From rev[4]: 0 (visited). SCC {4} = comp 5.

**Assignment:**
- x₁: comp[0]=4, comp[1]=2. 4>2 → x₁ = true ✓
- x₂: comp[2]=3, comp[3]=1. 3>1 → x₂ = true ✓
- x₃: comp[4]=5, comp[5]=0. 5>0 → x₃ = true ✓

All true: (T∨T)∧(F∨T) = T∧T = T ✓

## 13. Variants and Extensions

### 13.1 Minimally Satisfying Assignment

Find the assignment with the fewest true variables. This is NP-hard in general but can be approximated.

### 13.2 Counting Solutions

Counting the number of satisfying assignments of a 2-SAT formula is #P-complete (much harder than deciding satisfiability).

### 13.3 Random 2-SAT

For random 2-SAT with n variables and m clauses, there's a sharp threshold at m/n = 1:
- m/n < 1: almost surely satisfiable
- m/n > 1: almost surely unsatisfiable

### 13.4 Incremental 2-SAT

Adding clauses incrementally and maintaining the solution can be done in O(1) amortized per clause using dynamic graph connectivity algorithms.

### 13.5 Weighted 2-SAT

Minimize the weight of true variables. Reduces to min-cut in the implication graph.

## 14. Common Pitfalls

1. **Wrong literal encoding**: Be careful with the mapping from variables to vertices. The standard encoding is: variable i → vertices 2i and 2i+1, with negation being XOR with 1.

2. **Forgetting the implication direction**: (a ∨ b) gives ¬a→b AND ¬b→a. Missing one direction gives wrong results.

3. **Wrong SCC numbering**: The assignment rule depends on the topological ordering of SCCs. In Kosaraju's, the second pass gives components in reverse topological order, so higher component number = later in topological order = should be true.

4. **Unit clauses**: Don't forget that a single-literal clause (x) needs the edge ¬x→x.

5. **Index confusion**: 0-indexed vs 1-indexed variables, and the mapping to 2n vertices.

## 15. Exercises

1. **Basic**: Convert the formula (x₁ ∨ ¬x₂) ∧ (¬x₁ ∨ x₃) ∧ (x₂ ∨ ¬x₃) to an implication graph and find a satisfying assignment.

2. **Medium**: Prove that if a 2-SAT formula is satisfiable, it has at least two satisfying assignments (assuming n ≥ 1).

3. **Hard**: Given a 2-SAT formula, find the assignment that maximizes the number of true variables. (Hint: This is equivalent to a min-cut problem.)

4. **Challenge**: Design an algorithm that adds clauses one at a time to a 2-SAT formula and reports satisfiability after each addition. What's the best amortized time per clause?

5. **Implementation**: Extend the 2-SAT solver to handle "at most one" constraints over k variables using auxiliary variables (sequential encoding).

## 16. Interview Questions

1. **Q**: What is 2-SAT and how does it differ from 3-SAT?
   **A**: 2-SAT is satisfiability of CNF formulas with ≤2 literals per clause. It's solvable in polynomial time (O(n+m)) via SCC on the implication graph. 3-SAT (3 literals per clause) is NP-complete — no known polynomial algorithm exists.

2. **Q**: How do you model a 2-SAT problem as a graph problem?
   **A**: Create a directed implication graph with 2n vertices (one per literal). For each clause (a∨b), add edges ¬a→b and ¬b→a. The formula is satisfiable iff no variable and its negation are in the same SCC.

3. **Q**: How do you find the actual satisfying assignment?
   **A**: Compute SCCs and process in reverse topological order. For each variable xᵢ, set xᵢ = true if its SCC comes after ¬xᵢ's SCC in topological order, false otherwise.

4. **Q**: Can you solve 2-SAT with BFS instead of SCC?
   **A**: Not directly. The SCC structure is essential because you need to detect mutual implications (cycles). However, once SCCs are found, the assignment can be determined by comparing component IDs.

5. **Q**: How would you handle "exactly one of x, y must be true" in 2-SAT?
   **A**: This is an XOR constraint: (x∨y) ∧ (¬x∨¬y). It adds 4 edges to the implication graph. The formula remains in 2-CNF.

## 17. Cross-References

- **Chapter 81: SCC, Bridges, and Articulation Points** — SCC algorithms (Kosaraju, Tarjan)
- **Chapter 28: Advanced Graph Algorithms** — Graph connectivity fundamentals
- **Chapter 33: Bit Manipulation** — Bit tricks for literal encoding
- **Chapter 96: NP-Completeness** — SAT, 3-SAT, complexity classes
- **Chapter 29: Network Flow** — Weighted 2-SAT reduces to min-cut
- **Chapter 169: Min-Cost Max-Flow** — Related optimization on graphs

## 18. Further Reading

- [CP-Algorithms: 2-SAT](https://cp-algorithms.com/graph/2SAT.html)
- *Introduction to Algorithms* (CLRS), Chapter 34 — NP-completeness and SAT
- "Competitive Programming 3" by Steven Halim — 2-SAT section
- Aspvall, Plass, Tarjan (1979) — "A Linear-Time Algorithm for Testing the Truth of Certain Quantified Boolean Formulas"
