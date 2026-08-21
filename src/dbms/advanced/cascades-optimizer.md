# Cascades Query Optimizer

Cascades is a query optimization framework introduced by Goetz Graefe in 1995 as the successor to his earlier Exodus/Volcano optimizers. It is the design basis for Microsoft SQL Server's optimizer, Apache Calcite (used by Hive, Flink, Beam), Pivotal Greenplum's ORCA, and CockroachDB's optimizer. This page covers the memo structure, the rule-based transformation engine, the cost model, and how Cascades differs from its predecessor Volcano.

## Why Cascades Exists

A query optimizer takes a parse tree (e.g., `SELECT * FROM t1 JOIN t2 ON t1.id = t2.id WHERE t1.x > 5`) and produces an execution plan (e.g., "HashJoin(Build: Filter(Scan(t1)), Probe: Scan(t2))"). The space of possible plans is exponential in the number of joins and predicates — even 10 joins can produce 10! = 3,628,800 valid join orderings, plus choices of join algorithm, access path (table scan vs. index), and predicate pushdown.

Cascades represents this search space efficiently using a memo data structure that shares sub-plans across alternative formulations. The memo plus a rule-based transformation engine replaces the "exhaustive enumeration" approach of earlier optimizers (which would generate every plan and pick the cheapest).

## The Memo Structure

The Cascades memo is a directed acyclic graph where each node is an **expression** (a logical or physical operator) and edges represent parent-child relationships. Multiple equivalent expressions for the same subquery are grouped into a **group**:

```text
Group 1: Scan(t1) | IndexScan(t1, idx_x)   ← alternative ways to access t1
Group 2: Filter(Group 1, x > 5) | Filter(Group 1, x > 5)  [pushed]
Group 3: Scan(t2) | IndexScan(t2, idx_id)
Group 4: Join(Group 2, Group 3) [logical]
        | HashJoin(Group 2, Group 3) [physical]
        | MergeJoin(Group 2, Group 3) [physical]
        | NLJoin(Group 2, Group 3) [physical]
Group 5: Project(Group 4, [t1.id, t2.id])   ← top-level
```

A group represents "the set of expressions that produce the same output". The optimizer searches the group to find the lowest-cost expression, recursively applying the same search to each group's children.

```c
struct Group {
    GroupID id;
    std::vector<Expression*> expressions;  // all equivalent expressions
    Cost lower_bound;       // cost lower bound, for pruning
    Cost best_cost;
    Expression* best_expr;
    Stats stats;            // cardinality, distribution
};

struct Expression {
    Operator op;             // e.g., "LogicalJoin"
    std::vector<GroupID> children;  // child groups
    // ... operator-specific fields
};
```

The key property: the same group may be referenced by multiple parents, so equivalent sub-plans are shared. This makes the search space manageable — a group of 10 expressions can be the input to 100 different parent plans without duplicating the 10 expressions 100 times.

## Rule-Based Transformation

Cascades uses **rules** to generate new expressions from existing ones:

```c
struct Rule {
    Pattern match;     // a tree of operators and wildcards
    Action apply;       // function: takes matched expression, returns alternative
    bool valid_in_phase; // some rules apply only in certain search phases
};

// Example: predicate pushdown rule
Rule push_filter_into_join = {
    match: Filter(Join(X, Y), p),
    apply: (e) -> Join(Filter(X, p_extracted_from_e), Filter(Y, p_remaining), join_condition),
};

// Example: join commutativity
Rule commute_join = {
    match: LogicalJoin(X, Y, cond),
    apply: (e) -> LogicalJoin(Y, X, swapped(cond)),
};

// Example: logical-to-physical conversion
Rule hash_join_impl = {
    match: LogicalJoin(X, Y, cond),
    apply: (e) -> HashJoin(X, Y, cond),
};
```

The optimizer's main loop:

1. Pick a group from the memo (in some order).
2. Pick an expression from the group.
3. For each rule, attempt to match the expression.
4. If a rule matches, generate the new expression, add it to the appropriate group.
5. If the group already has the new expression, skip (deduplication by expression hash).
6. Repeat until no more rules fire or the search budget is exhausted.

The order of rules and the search strategy (depth-first, breadth-first, or branch-and-bound) are tuned per optimizer. Microsoft SQL Server uses ~390 rules; Apache Calcite has ~100; CockroachDB has ~200.

## The Cost Model

Each physical operator has a cost function:

```text
Cost(op) = startup_cost + per_tuple_cost * cardinality
            + per_io_cost * num_io
            + per_memory_cost * memory_required
```

The cost is recursive: the cost of an expression is its operator's cost plus the sum of its children's costs. Cascades computes costs bottom-up: for each group, evaluate every physical expression's cost, pick the minimum, and store as the group's `best_cost`.

Cardinality estimation is the input to the cost model. The optimizer uses statistics (table row counts, histograms, most-common-values, distinct-value counts) to estimate how many rows each operator will produce. Wrong cardinality estimates lead to wrong plan choices — this is the most common cause of optimizer-related production outages.

## The Search Phases

Cascades typically has multiple search phases, each with a different rule set:

1. **Simplification phase**: constant folding, predicate simplification, dead-code elimination.
2. **Logical exploration phase**: join reordering, predicate pushdown, view merging, subquery flattening.
3. **Physical implementation phase**: logical-to-physical conversions (LogicalScan → IndexScan/TableScan, LogicalJoin → HashJoin/MergeJoin/NLJoin).
4. **Post-optimization phase**: plan refinement, parallelization, JIT compilation hints.

Different optimizers expose different phase boundaries. CockroachDB's optimizer has explicit phases with named rule sets; SQL Server's phases are implicit but the concept is the same.

## Branch-and-Bound Pruning

Without pruning, the search would be exhaustive. Cascades uses **branch-and-bound**:

1. Maintain a global upper bound on the best cost found so far.
2. When entering a group, compute the group's `lower_bound` (the cheapest possible expression based on operator minimum cost).
3. If `lower_bound > upper_bound`, prune the entire group.
4. Otherwise, evaluate expressions one at a time, updating the global upper bound as new bests are found.

This pruning makes Cascades tractable on plans with hundreds of operators: the search visits O(N) groups rather than O(2^N) plans.

## How Cascades Differs from Volcano

Volcano (Graefe, 1993) was the predecessor. Cascades improved on it with:

1. **Top-down search** (Cascades) vs. **bottom-up dynamic programming** (Volcano). Cascades visits groups top-down, which makes pruning more aggressive (early pruning of infeasible branches). Volcano's bottom-up approach makes memoization natural but offers less pruning.

2. **Rule firing during search** (Cascades) vs. **rule firing before search** (Volcano). Cascades interleaves transformation and cost evaluation; Volcano transforms the entire memo first, then evaluates costs. The interleaving lets Cascades prune more aggressively.

3. **Group ownership** (Cascades) vs. **expression ownership** (Volcano). Cascades' groups own their expressions; Volcano's expressions own their groups. The difference is subtle but Cascades' approach makes incremental optimization easier (e.g., re-optimize only the parts of a plan that have changed statistics).

4. **Multi-phase search** (Cascades) vs. **single-phase** (Volcano). Cascades can do "exploration, then implementation"; Volcano does both at once.

## Modern Implementations

| Optimizer | User | Notes |
|-----------|------|-------|
| **Microsoft SQL Server** | Microsoft | The original Cascades (1995-onwards). ~390 rules. |
| **Apache Calcite** | Hive, Flink, Beam, Druid | Open-source Cascades-style optimizer in Java. ~100 rules. |
| **ORCA** | Pivotal Greenplum | Cascades-style optimizer for MPP databases. ~300 rules. |
| **CockroachDB opt** | CockroachDB | Cascades-style optimizer in Go. ~200 rules. |
| **Memgraph** | Memgraph | Cascades-style for Cypher queries. |

The Apache Calcite paper (SIGMOD 2018) describes how to implement a Cascades-style optimizer in a way that's modular across SQL engines. It's the most accessible reference for someone implementing Cascades today.

## Common Pitfalls

1. **Cardinality estimation is the dominant error source.** Wrong estimates cause wrong plan choices, even with a perfectly correct Cascades implementation. Modern optimizers add machine-learned cardinality models (e.g., Microsoft's "Learning-based Cardinality Estimation", 2018) on top of the classical histogram-based estimates.

2. **Memo size can blow up memory.** A complex query can generate millions of expressions. SQL Server has a 5 GB default memo size limit; exceeding it triggers a fallback to a simpler optimizer.

3. **Rule interactions can produce non-terminating search.** Two rules that commute (`A→B→A` loop) cause the search to never settle. Cascades uses an expression-hash memoization to detect duplicates, but rule designers must ensure their rules are confluent (terminate in a normal form).

4. **The lower-bound computation must be conservative.** A too-aggressive lower bound over-prunes and misses the optimal plan. A too-conservative bound defeats the pruning. SQL Server uses "per-operator minimum cost" (the cheapest known cost for each operator type) as the lower bound.

5. **Parallelizing the search is hard.** Cascades is naturally sequential (rule application updates the memo, which is shared state). Microsoft SQL Server's parallel optimizer uses group-level locking; Apache Calcite is single-threaded. CockroachDB has an experimental parallel optimizer that uses work-stealing.

## References

- Goetz Graefe, "[The Cascades Framework for Query Optimization](https://www.cse.iitb.ac.in/infolab/Data/Courses/CS632/2007-Papers/Cascades-graefe.pdf)" (IEEE Data Eng. Bull. 1995)
- Goetz Graefe, "[Volcano: An Extensible and Parallel Query Evaluation System](https://www.cs.cornell.edu/home/livelock/volcano.pdf)" (1994)
- [Apache Calcite: A Foundational Framework for Optimized Query Processing](https://arxiv.org/abs/1806.00415) (SIGMOD 2018)
- [CockroachDB optimizer design](https://www.cockroachlabs.com/blog/query-planning/)
- [Microsoft SQL Server QO: The Cascades Style](https://learn.microsoft.com/en-us/sql/relational-databases/query-processing-architecture-guide)
- [ORCA: A Query Optimizer for Pivotal Greenplum](https://gielse.net/pubs/SIGMOD-ORCA.pdf) (SIGMOD 2014)
- Goetz Graefe, "[New Engleberg: A modern Cascades implementation](https://arxiv.org/abs/2105.11998)" (2021)
