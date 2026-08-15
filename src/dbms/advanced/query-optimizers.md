# Advanced Query Optimizers

Modern query optimizers are the "brain" of a database. This chapter covers the architecture of production-grade optimizers (Cascades, Volcano/Columbia), cost-based and learned cardinality estimation, join ordering theory including worst-case optimal joins, and the emerging field of factorized query processing.

## Cascades / Volcano / Columbia Optimizer Framework

### The Volcano/Columbia Architecture

The Volcano optimizer (Graefe, 1993) and its successor Columbia (Galindo-Legaria et al., 1994) introduced the **top-down** search framework that underpins most modern optimizers. The key idea: model optimization as a **search problem** over a space of **logical** and **physical** equivalent expressions, separated by **transformation rules** and **implementation rules**.

```
Logical Expression Tree          Physical Expression Tree
       (R ⋈ S) ⋈ T           -->      HashJoin(HashJoin(R,S), T)
            |                           |
      Logical operators          Physical operators + cost
```

**Core components:**

- **Memo Group**: A set of logically equivalent expressions. Each group has one or more *logical expressions* and one or more *physical expressions*.
- **Group Expression**: A single expression (e.g., `JOIN(R, S)`) living inside a group, annotated with child group pointers.
- **Optimization Rules**: Two types — *transformation rules* (e.g., join commutativity, `R ⋈ S → S ⋈ R`) map logical→logical; *implementation rules* (e.g., `JOIN → HashJoin`) map logical→physical.
- **Search Strategy**: Typically **branch-and-bound** with dynamic programming. Explores groups top-down, pruning suboptimal physical alternatives.

**Pseudocode — Volcano top-down optimization:**

```python
def optimize(group, cost_upper_bound=INFINITY):
    if group.best_cost < cost_upper_bound:
        return group.best_plan
    best_plan = None
    # Try all logical expressions in this group
    for expr in group.logical_expressions:
        # Apply transformation rules to generate new logical exprs
        for rule in transformation_rules:
            new_expr = rule.apply(expr)
            target_group = memo.insert(new_expr)
            # Recursively explore (may generate more transformations)
            optimize(target_group, cost_upper_bound)
    # Try all implementation rules to generate physical plans
    for expr in group.logical_expressions:
        for rule in implementation_rules:
            phys_expr = rule.apply(expr)  # e.g., Join -> HashJoin
            child_costs = []
            for child_group in phys_expr.children:
                child_plan = optimize(child_group, cost_upper_bound)
                child_costs.append(child_plan.cost)
            total_cost = rule.cost(phys_expr, child_costs)
            if total_cost < cost_upper_bound:
                cost_upper_bound = total_cost
                best_plan = PhysicalPlan(phys_expr, child_plans)
    group.best_plan = best_plan
    group.best_cost = cost_upper_bound
    return best_plan
```

### Cascades Optimizer

Cascades (Graefe & McKenna, 1993) refined Volcano with:

- **Bottom-up task-driven scheduling** instead of top-down recursion. Tasks are pushed onto a stack/worklist: `OPTIMIZE_GROUP`, `EXPLORE_GROUP`, `EXPLORE_EXPR`, `APPLY_RULE`.
- **Guidance / Pruning**: Cost-based pruning (discard physical expressions above current best), pattern-based pruning, and heuristic ordering of rule application.
- **Property Enforcement**: Physical properties (sort order, partitioning) are handled explicitly. If a parent requires a sorted input, the optimizer inserts an `ENFORCER` operator (e.g., Sort) and accounts for its cost.

Cascades is the basis for **SQL Server's** optimizer and strongly influenced **Apache Calcite** (used by Hive, Flink, Druid, and many others).

> **Interview Angle**: "Explain the Cascades optimizer framework." — Cover memo groups, logical/physical separation, transformation vs. implementation rules, task-driven exploration, and property enforcement. Mention SQL Server and Calcite as real implementations.

## Cost-Based Optimization & Cardinality Estimation

### The Cost Model

A cost model estimates the *resource consumption* of a physical plan: I/O (page reads/writes), CPU (comparisons, hash computations), and network (for distributed systems). The cost of a plan is the sum of operator costs, computed bottom-up.

**Typical cost formula for a hash join:**

```
Cost(HashJoin(R, S)) =
    cost(build_hash_table(R)) + cost(probe(S))
  = IO(R) + IO(S) + CPU(|R|) + CPU(|S| × hit_rate)
```

### Cardinality Estimation

Cardinality estimation (estimating `|output|` of each operator) is the *critical* input to the cost model. Errors propagate multiplicatively through joins — a 2x error at each of 5 joins yields 32x error.

**Traditional approaches:**

| Method | Mechanism | Accuracy | Used In |
|--------|-----------|----------|----------|
| Histograms | Equi-depth, equi-width buckets | Good for 1D | PostgreSQL, MySQL |
| Independence assumption | `|R ⋈ S| ≈ |R|×|S|/max(distinct(R.key), distinct(S.key))` | Poor for correlated columns | Most systems |
| Multi-dimensional histograms | MHIST, SGRID | Better for correlations | Oracle (approx.) |
| Sampling | Uniform/random sample of table | Good for simple predicates | Teradata |

### Learned Cardinality Estimation

ML-based cardinality estimation replaces hand-crafted heuristics with learned models. Key systems:

- **Learned Cardinality Tables (LCT)** (Sun & Li, 2019): Decompose a query into a set of *predicate-join* subproblems, train a model per table/column combination. Uses a set-covering algorithm to select training queries.
- **MSCN (Multi-Set Convolutional Network)** (Kipf et al., 2019): Represents query as sets of predicates, uses deep sets with convolution to estimate join result sizes. Handles correlations between join keys and filter predicates.
- **NeuroCard** (Yang et al., 2021): Uses a *summation-free* set-encoding architecture to avoid the O(n) bottleneck of deep sets. Models join queries as colored set intersection problems.
- **FLAT** (Wu et al., 2022): Uses a transformer-based architecture treating query predicates as a sequence, with attention over column names and value ranges.

**Challenges with learned cardinality:**

1. **Generalization**: Models trained on workload W1 must generalize to workload W2 (unseen predicate ranges, new join patterns).
2. **Latency**: Inference must be < 1ms to not dominate optimization time. MSCN and NeuroCard achieve this with compact architectures.
3. **Robustness**: Out-of-distribution queries (e.g., range predicates far outside training data) can produce wildly wrong estimates. Some systems fall back to traditional estimators when confidence is low.

> **Interview Angle**: "Why is cardinality estimation hard, and can ML help?" — Discuss error propagation, the independence assumption, learned approaches (MSCN, NeuroCard), and practical concerns (generalization, latency).

## Adaptive Query Processing & Runtime Re-optimization

Static optimizers commit to a plan before execution begins. Adaptive query processing (AQP) adjusts at runtime based on observed statistics.

### Techniques

| Technique | Mechanism | System | Overhead |
-----------|-----------|--------|----------|
| **Eddies** (Avnur & Hellerstein, 2000) | Route tuples dynamically to operators based on selectivity feedback | Telegraph | High (per-tuple routing) |
| **Plan_patches** (Kabra & DeWitt, 1998) | Compile alternative plan fragments; switch at runtime if stats diverge | Mid-query reopt | Low (conditional jumps) |
| **Ramp-up** (Markl et al., 2004) | Start with hash join, switch to sort-merge if memory insufficient | MaxDB | Medium |
| **Progressive optimization** (Neo et al., 2016) | Re-optimize subqueries after partial execution reveals stats | PostgreSQL 12+ (jitter) | Low |
| **Adaptive indexing** (Idreos et al., 2007) | Build indexes incrementally during first query passes | Database cracking | Medium |

### Database Cracking

Rather than building a full B-tree upfront, database cracking reorganizes data *on the fly* as queries arrive. Each query with a range predicate `WHERE col BETWEEN a AND b` partitions the data around `a` and `b`, creating ever-finer partitions.

```
Initial:    [9, 3, 7, 1, 5, 2, 8, 4, 6]
Query: WHERE x <= 5
After:      [1, 2, 3, 4, 5 | 9, 7, 8, 6]  
                                          ^pivot at 5
Query: WHERE x >= 7
After:      [1, 2, 3, 4, 5 | 6 | 7, 8, 9]
```

Cracking converges toward a sorted array (which is itself an optimal index) after O(n log n) total work across all queries, amortized.

## Join Ordering

### Dynamic Programming (DP)

The classic DP join ordering algorithm (Selinger et al., 1979 — System R) enumerates all subsets of tables, finding the cheapest plan for each subset size.

```
For k = 1 to n:
    For each subset S of size k:
        For each non-empty partition (S1, S2) of S:
            For each join method J in {HashJoin, SortMerge, NLJ}:
                cost = best_plan[S1].cost + best_plan[S2].cost + J.cost(S1, S2)
                update best_plan[S] if cost is lower
```

**Complexity**: O(3^n × cost_of_best_join) — exponential in the number of tables. Practical up to ~15-20 tables.

### Bushy vs. Left-Deep Trees

```
Left-Deep:           Bushy:
    ⋈                  ⋈
   / \\                / \\
  ⋈   D              ⋈   ⋈
 / \\                / \\ / \\
A   B   C           A  B C  D
```

- **Left-deep plans** are pipeline-friendly (one input always materialized, the other streamed). Most systems (PostgreSQL, MySQL) only consider left-deep plans for efficiency.
- **Bushy plans** can be cheaper by parallelizing independent sub-joins. Systems like **CockroachDB** (via the Cascades framework) and **Apache Calcite** consider bushy plans. They are critical for star-join queries on fact tables with multiple dimension tables.

### Greedy & Heuristic Approaches

For queries with > 20 tables, DP is infeasible. Systems use:

- **Greedy**: At each step, join the pair of relations with the cheapest estimated cost. O(n² × n) = O(n³). Used as a fallback in PostgreSQL and MySQL.
- **Genetic algorithms**: Maintain a population of join orders, apply crossover/mutation, select by fitness (cost). Used in **PostgreSQL's GEQO** (Genetic Query Optimizer) when tables > geqo_threshold (default 12).
- **Simulated annealing**: Random perturbations accepted with decreasing probability. Used in earlier versions of Oracle.

## Worst-Case Optimal Joins (WCOJ)

### The Problem with Pipelined Joins

Traditional binary join plans (hash join, sort-merge) are **not worst-case optimal**. For a triangle query `R(A,B) ⋈ S(B,C) ⋈ T(C,A)`, a hash-join plan may scan O(n³) intermediate tuples even when the output is small. The **AGM bound** (Atserias, Grohe, Marx, 2013) proves that the output size of a full join is bounded by a fractional *tetrahedron* function of the input sizes — often much less than the Cartesian product.

### The AGM Bound

For a query Q and database instance D, the **AGM bound** `AGM(Q, D)` gives a tight worst-case upper bound on `|Q(D)|`. For a triangle query over relations R, S, T each of size N:

```
AGM(triangle) = max{
    sqrt(|π_A(R)∩π_A(T)| × |π_B(R)∩π_B(S)| × |π_C(S)∩π_C(T)|)
}
```

A join algorithm is **worst-case optimal** if its runtime is bounded by O(N + AGM(Q, D) × output) — it never does asymptotically more work than the information-theoretic minimum.

### Leapfrog Triejoin (LFTJ)

Leapfrog Triejoin (Veldhuizen, 2012) is a practical WCOJ algorithm that operates on tries (prefix trees) of each relation:

```
LeapfrogTriejoin(variables, tries, bindings):
    for each variable v in variables (in some order):
        LeapfrogInit(tries_for_v, v)
        while tries_for_v have non-empty intersection:
            v_value = tries_for_v.min_key()
            bind(v, v_value)
            if all variables bound:
                emit current bindings
            else:
                LeapfrogTriejoin(remaining_variables, ...)
            LeapfrogNext(tries_for_v)
            unbind(v)
```

**Leapfrog** is the key operation: given k sorted iterators (one per relation that constrains a variable), it **leapfrogs** between them to find the next value in their intersection, using binary search to skip large gaps. This achieves WCOJ performance.

**Systems using WCOJ**:

| System | Algorithm | Notes |
|--------|-----------|-------|
| **LogicBlox** | LFTJ | Commercial Datalog system |
| **Rapids** | LFTJ | Research prototype |
| **DuckDB** | WCOJ (since 0.10) | For queries with >= 3 joins and no filter pushdown |
| **EmptyHeaded** | WCOJ | Specialized for graph workloads |

> **Interview Angle**: "What is worst-case optimal join processing and when does it matter?" — Explain the AGM bound, why binary join plans can be suboptimal for cyclic queries, and how LFTJ works. Mention DuckDB as a real system using it.

## Factorized Databases & Factorized Query Processing

### The Idea

Factorized query processing avoids materializing the full join result by representing it in a **factorized form** — a tree of *variables* where each node stores only the *unique* values of its variable, conditioned on the bindings of its parent.

### Example

For `R(A,B) ⋈ S(B,C)` with result:

```
A | B | C
--+---+--
1 | 2 | 3
1 | 2 | 4
1 | 5 | 6
```

The **factorized representation**:

```
Root: A = [1]
  └── B = [2, 5]  (for A=1)
       ├── C = [3, 4]  (for A=1, B=2)
       └── C = [6]       (for A=1, B=5)
```

Instead of 3 tuples × 3 columns = 9 values, we store 1 + 2 + 2 + 1 = 6 values. For queries with many joins, the savings can be *exponential*.

### Factorized Query Processing

Operations like aggregation, grouping, and further joins can be performed directly on the factorized representation without materializing the full result. This is implemented in **LogicBlox** and in research prototypes.

The key theoretical result (Olteanu & Schleich, 2016): factorized query processing runs in time O(IN + OUT_f) where IN is the combined input size and OUT_f is the *factorized* output size — which can be exponentially smaller than the materialized output.

> **Interview Angle**: "What is factorized query processing?" — Explain the factorized representation tree, why it saves space for multi-join queries, and mention LogicBlox. Contrast with standard materialized join results.

## Comparison: Optimizer Architectures

| Feature | Volcano/Columbia | Cascades | Calcite | CockroachDB (built-in) |
|---------|-----------------|----------|---------|----------------------|
| Search direction | Top-down | Bottom-up (task-driven) | Bottom-up (volcano-like) | Top-down (Cascades-derived) |
| Memo structure | Groups + expressions | Groups + expressions | RelNode + equivalent sets | Memo with groups |
| Rule application | On-demand | On-demand (task stack) | On-demand + heuristic | On-demand |
| Cost model | Pluggable | Pluggable | Pluggable | Histogram-based |
| Bushy plans | Optional | Yes | Yes | Yes |
| WCOJ | No | No | No | No (research only) |
| Used in | Extensible DB prototypes | SQL Server | Hive, Flink, Druid | CockroachDB |

## References

- Graefe, G. "The Cascades Framework for Query Optimization." IEEE Data Eng. Bull., 1993.
- Kipf, A. et al. "Learned Cardinalities: Estimating Correlated Joins with Deep Learning." CIDR, 2019.
- Ngo, H.Q., Ré, C., Rudra, A. "Worst-case Optimal Join Algorithms." JACM, 2014.
- Veldhuizen, T.L. "Leapfrog Triejoin: A Worst-Case Optimal Join Algorithm." LogicBlox, 2012.
- Olteanu, D., Schleich, M. "Factorized Databases." SIGMOD Record, 2016.