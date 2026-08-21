# Volcano Query Optimizer

The Volcano optimizer is Goetz Graefe's 1993 predecessor to Cascades, introducing the **iterator model** of query execution that remains the standard for relational database engines to this day. This page covers the iterator interface, the bottom-up dynamic-programming search, the differences from Cascades, and why the iterator model outlived the optimizer itself.

## Two Contributions in One Paper

The Volcano paper (1993) made two contributions that are often confused:

1. **Volcano the optimizer**: a cost-based, bottom-up, dynamic-programming optimizer.
2. **Volcano the execution model**: an iterator-based pull-model where each operator has `open()`, `next()`, `close()` methods.

The optimizer has been superseded by Cascades. The execution model is still the dominant execution interface in PostgreSQL, MySQL, Oracle, SQL Server, SQLite, and many NoSQL databases.

This page covers both, but emphasizes the execution model because that is Volcano's lasting contribution.

## The Iterator Model

Each operator in a Volcano-style execution plan implements the iterator interface:

```c
class Iterator {
public:
    virtual void open() = 0;
    virtual bool next(Tuple& out) = 0;
    virtual void close() = 0;
    virtual ~Iterator() {}
};
```

- `open()` initializes the operator, opens its children, allocates resources.
- `next()` produces the next output tuple or returns `false` when exhausted. Each call to `next()` typically calls `next()` on its child operator (or several children for a join).
- `close()` releases resources, closes children.

A simple plan like `SELECT * FROM t WHERE x > 5` is implemented as:

```text
Filter(Scan(t))
   ▲ next() calls
   │
   ▼
Scan(t)
```

```c
class Scan : public Iterator {
    Table* table;
    Cursor cursor;
public:
    void open() override { cursor = table->begin(); }
    bool next(Tuple& out) override {
        if (cursor == table->end()) return false;
        out = *cursor;
        ++cursor;
        return true;
    }
};

class Filter : public Iterator {
    Iterator* child;
    Predicate pred;
public:
    void open() override { child->open(); }
    bool next(Tuple& out) override {
        Tuple t;
        while (child->next(t)) {
            if (pred.evaluate(t)) {
                out = t;
                return true;
            }
        }
        return false;
    }
};
```

The data flow is **pull-based**: the top operator pulls tuples from its children. The query executor calls `next()` on the top operator in a tight loop until it returns `false`.

## Why Pull-Based Won

The pull-based iterator model has several advantages:

1. **Backpressure is automatic.** When the consumer is slow, it stops calling `next()`, and the producer stops producing. No bounded queues or buffer overflow.

2. **Operators compose naturally.** A new operator (e.g., `Sort`) is implemented by wrapping another iterator. No changes to the executor are needed.

3. **Memory usage is small.** Most operators (Filter, Project, Map) hold zero or one tuple at a time. Only stateful operators (Sort, HashJoin, Aggregate) need to buffer.

4. **Pipeline parallelism is implicit.** Each operator can run in a different thread; tuples flow via `next()` calls across thread boundaries.

5. **Early termination is free.** `LIMIT 10` is implemented as an iterator that calls `next()` 10 times then returns `false`. No need to materialize the whole result.

## The Cost of Pull-Based: Per-Tuple Overhead

The pull-based model has a per-tuple cost: a virtual function call (or branch) per `next()` invocation. For a query that returns 1 million tuples with 5 operators in the plan, that's 5 million virtual calls.

Modern CPUs can do this in ~1 ns per call (5 ms total for 1M tuples). For OLTP-scale queries, this is acceptable. For OLAP-scale queries (billions of tuples), the overhead is the dominant cost — which is why modern OLAP engines (ClickHouse, DuckDB, SingleStore) use the **vectorized execution model** (batched tuples per `next()` call).

## The Volcano Optimizer

The optimizer portion of Volcano is a bottom-up dynamic-programming optimizer:

1. Start with the leaf operators (table scans, index scans).
2. For each pair of leaves, generate all join orders.
3. For each join order, generate all join algorithms (hash, merge, nested-loop).
4. Pick the cheapest plan for each sub-expression and cache it.
5. Continue up the tree until the root has a plan.

```text
For 3-way join of A, B, C:
  Step 1: cost(A), cost(B), cost(C)         — leaf costs
  Step 2: cost(AB), cost(AC), cost(BC)       — all 2-way joins
  Step 3: cost(ABC), cost(ACB), cost(BCA), ... — all 3-way joins
  Pick min(cost(ABC), cost(ACB), ...) as the plan
```

The dynamic-programming aspect: `cost(AB)` is computed once and reused in `cost(ABC)`, `cost(ABD)`, etc.

The complexity is O(3^N) for N relations, which is exponential but tractable for small N (≤10) thanks to the memoization. For larger N, Volcano falls back to a greedy heuristic that picks the cheapest pair at each step (similar to System R's strategy).

## Volcano vs. Cascades (Optimizer Side)

Volcano and Cascades are often confused because both come from Graefe. The differences:

| Aspect | Volcano (1993) | Cascades (1995) |
|--------|----------------|------------------|
| Search strategy | Bottom-up dynamic programming | Top-down branch-and-bound |
| Rule application | All rules fire before search | Rules fire during search |
| Search space | Exhaustive (with DP pruning) | Heuristic (with branch-and-bound pruning) |
| Group sharing | Expressions own groups | Groups own expressions |
| Multi-phase | No | Yes (exploration + implementation) |
| Modern users | (none) | SQL Server, Calcite, CockroachDB, ORCA |

Cascades superseded Volcano because:
- Bottom-up DP requires complete enumeration of the search space, which is too expensive for complex queries (10+ joins).
- Top-down branch-and-bound prunes earlier and more aggressively.
- Multi-phase search (logical exploration then physical implementation) lets optimizers apply expensive rules only when simpler rules have already reduced the space.

## The Volcano-Cascades Iterator Model Convergence

Modern database engines use a hybrid:

- **Iterator interface (Volcano)**: every operator exposes `open()/next()/close()`.
- **Vectorized execution**: each `next()` returns a batch of tuples (typically 1024-4096) instead of one tuple. This reduces per-tuple overhead by ~100×.
- **Pull-based with batched push**: operators request batches from children but may push back batches they couldn't consume.

ClickHouse, DuckDB, and SingleStore use this hybrid. PostgreSQL and MySQL still use the pure iterator model (one tuple per `next()`), which is why they lag on analytical queries.

## Implementing a Volcano-Style Engine

A minimal Volcano-style engine is ~500 lines of code:

```python
class Operator:
    def open(self): pass
    def next(self): pass  # returns a tuple or None
    def close(self): pass

class Scan(Operator):
    def __init__(self, rows): self.rows = rows; self.i = 0
    def open(self): self.i = 0
    def next(self):
        if self.i >= len(self.rows): return None
        t = self.rows[self.i]; self.i += 1
        return t

class Filter(Operator):
    def __init__(self, child, pred): self.child = child; self.pred = pred
    def open(self): self.child.open()
    def next(self):
        while True:
            t = self.child.next()
            if t is None: return None
            if self.pred(t): return t

class HashJoin(Operator):
    def __init__(self, build, probe, on_build, on_probe):
        self.build = build; self.probe = probe
        self.on_build = on_build; self.on_probe = on_probe
        self.hash = {}
    def open(self):
        self.build.open()
        while True:
            t = self.build.next()
            if t is None: break
            self.hash[self.on_build(t)].append(t)
        self.probe.open()
    def next(self):
        while True:
            t = self.probe.next()
            if t is None: return None
            matches = self.hash.get(self.on_probe(t), [])
            if matches:
                # return one match per call; emit pending for subsequent calls
                ...
```

The same plan `Filter(HashJoin(Scan(A), Scan(B), a_id, b_id), lambda t: t.score > 5)` runs:

```python
plan = Filter(HashJoin(Scan(A), Scan(B), lambda t: t['id'], lambda t: t['aid']),
              lambda t: t['score'] > 5)
plan.open()
while (t := plan.next()):
    print(t)
plan.close()
```

## Common Pitfalls

1. **Forgetting that `next()` is a virtual call.** Every tuple incurs one virtual call per operator in the plan. Inline the call where possible (PostgreSQL does this with macros in the fast paths of SeqScan and IndexScan).

2. **Pushing stateful logic into `next()`.** A sort operator that sorts in `open()` is correct; a sort operator that sorts incrementally in `next()` is buggy and slow. Use `open()` for expensive setup, `next()` for cheap iteration.

3. **Confusing the iterator model with the optimizer.** The iterator model is Volcano's lasting contribution; the optimizer has been replaced. Modern engines use Volcano iterators with Cascades optimizers.

4. **Assuming pull-based is always better than push-based.** Push-based execution (where the producer drives the consumer) is faster for high-throughput OLAP workloads because it avoids the per-tuple virtual call. Apache Arrow's "Acero" execution engine uses push-based with vectorized batches.

5. **Materializing intermediate results.** Some operations require materialization (Sort, HashJoin build side). But many query plans unnecessarily materialize when they could pipeline — this is a common optimizer bug. Cascades-style optimizers use the "Pipeline" concept to distinguish materialized from pipelined operators.

## References

- Goetz Graefe, "[Volcano: An Extensible and Parallel Query Evaluation System](https://www.cs.cornica.edu/home/livelock/volcano.pdf)" (1994)
- Goetz Graefe, "[Iterators, Surrogates, and Catalogs](https://www.cse.iitb.ac.in/infolab/Data/Courses/CS632/2007-Papers/Cascades-graefe.pdf)" (1993)
- [PostgreSQL's executor: an iterator model in C](https://www.postgresql.org/docs/current/executor.html)
- [Apache Arrow Acero: push-based vectorized execution](https://arrow.apache.org/docs/cpp/acero.html)
- [DuckDB: Vectorized execution](https://duckdb.org/2022/03/13/duckdb-internal-3.html)
- [ClickHouse: How to read 1B rows/sec on a single machine](https://clickhouse.com/blog/100x-faster-queries-with-asyncio)
- Goetz Graefe, "[Query Evaluation Techniques for Large Databases](https://cs.emis.de/LNI/sem27/sem27.pdf)" (ACM CS 1993)
