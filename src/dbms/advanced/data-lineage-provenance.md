# Data Lineage and Provenance: Why, Where, and How

Ask a warehouse engineer three questions about one cell — `fact_orders.revenue = 41,203.50` for
March — and you get three different disciplines. *Which upstream rows produced it?* (impact and
debugging). *Which exact source value did it come from?* (audit). *Through what derivation?*
(reproducibility). Data engineering usually answers at the job level — Airflow DAGs, dbt DAG
graphs — which [Data Lineage](../../data-engineering/data-lineage.md) covers from the pipeline
side. This page is the database-side discipline: provenance *semantics* (what exactly lineage
claims), how engines capture it at query level, and the operational reality of column-level
lineage in production warehouses.

## The three questions: why-, where-, and how-provenance

The canonical taxonomy comes from Buneman, Khanna, and Tan (ICDT 2001), who separated the
"which tuples" question from the "which positions" question:

| Kind | Question it answers | Example for `SELECT name FROM emp WHERE sal > 100` returning "Alice" |
|---|---|---|
| **Why-provenance** | Which source tuples were witnesses for this output? | the one `emp` row for Alice (her salary satisfied the filter) |
| **Where-provenance** | Which source *locations* (table.column) hold the origin of this value? | `emp.name` of that row |
| **How-provenance** | Through what expression did sources combine? | a derivation record: `name FROM row r7 WHERE sal(r7)=140 > 100` |

Why-provenance answers "could you show me the evidence?"; where-provenance narrows to cell
granularity; how-provenance keeps the operator structure, which is what you need when the
output is computed (`sal * 0.9 + bonus`) rather than copied. Green, Karvounarakis, and Tannen
(PODS 2007) gave how-provenance a precise algebra: annotate each input tuple with a variable,
push annotations through operators, and each output tuple's annotation becomes a polynomial
(sum for union, product for join) over input variables — provenance semirings. That algebra is
the theory under every practical system below.

## Where lineage lives inside a query engine

A SQL engine already computes provenance-shaped information on the way to a plan; it just
throws it away. In an Apache Calcite-style planner, every logical node (`RelNode`) carries:

- its input relations (`RelOptTable` references for scans),
- a row type — the ordered output columns,
- expressions as `RexInputRef` indices pointing into child columns.

Column-level lineage is then a fixpoint propagation over the plan: start with
`scan.col -> {schema.table.col}` at the leaves and let each operator transform the annotation
set. This is exactly the scheme the runnable demo at the end implements with dicts. Projects
take the union of referenced columns' annotations, filters and joins contribute predicate and
key columns, aggregations pull in group keys.

The alternative capture mechanism is **query rewriting**: Perm (Glavic and Alonso, ICDE 2009)
rewrites a user query `Q` into a provenance-annotated query `Q'` over the same relations, so
"give me the why-provenance of tuple t" is itself an ordinary SQL query — no special storage
engine, and the same optimizer plans both. The semiring algebra and the rewriting approach meet
there: annotations are just extra columns whose algebra the rewrite is careful to preserve.

| Mechanism | Captured when | Granularity | Typical failure |
|---|---|---|---|
| Plan-node annotation (Calcite-style) | parse + plan time | column-level | dialect/UDF coverage |
| Query rewriting (Perm-style) | query time | tuple/column-level | rewrite complexity per operator |
| Warehouse access logs (Snowflake) | run time | column-level | post-hoc, engine-specific |
| Orchestration events (OpenLineage) | job boundaries | dataset/job-level | blind inside a job |

## Column-level propagation through a JOIN/AGG plan

The diagram shows the annotation set flowing through the same plan the demo executes; note how
`currency` enters `revenue`'s provenance without ever being projected — the filter read it, so
surviving rows depend on it:

```text
  Scan(orders)                          Scan(customers)
  o.amount  -> {o.amount}               c.country -> {c.country}
  o.cust_id -> {o.cust_id}              c.cust_id -> {c.cust_id}
  o.currency-> {o.currency}
        \                              /
         \                            /
          JOIN ON o.cust_id = c.cust_id
          o.amount   -> {o.amount, c.cust_id, o.cust_id}   (both keys added)
          c.country  -> {c.country, o.cust_id}
                        |
          AGGREGATE  GROUP BY c.country, SUM(o.amount) AS revenue
          revenue -> {o.amount, o.cust_id, c.cust_id, c.country}
                        |
          PROJECT (country, revenue)          [pass-through]
```

## Warehouse-native lineage: Snowflake's ACCESS_HISTORY

Theory aside, the pragmatic capture path in 2026 warehouses is reading the engine's own audit
log. Snowflake's `ACCESS_HISTORY` view (in `ACCOUNT_USAGE`) records, per query, which columns
were read — including columns referenced only in predicates and joins — and, for write
operations such as CTAS or INSERT, which source columns fed which target columns. Chaining
those records across queries yields column-level lineage graphs without parsing any SQL, at
the cost of engine lock-in and post-hoc timing (lineage exists only after a query ran). The
docs' lineage section describes exactly this parent-column chaining. Other platforms expose
equivalents with varying fidelity; the design lesson generalizes — if the engine already
touches every column reference, instrument the engine rather than the SQL text.

## Provenance for reproducibility: versioning as coarse-grained lineage

Reproducibility asks provenance's question one abstraction level up: not "which rows produced
this cell" but "which dataset snapshot plus which code produced this artifact." The data
versioning tools model exactly that:

- **lakeFS** turns an object store into a git-like repository — commits pin dataset snapshots,
  branches isolate experiments, and a commit ID in a pipeline log is a resolvable pointer to
  the exact input state (see https://docs.lakefs.io/).
- **DVC** (https://dvc.org/doc) tracks data files and pipelines in git: each `dvc.yaml` stage
  declares `deps` and `outs`, so rerunning a stage checks input versions before recomputing.

Both capture *dataset-level* provenance; the column-level propagation of the previous sections
remains necessary inside a transform. At fleet scale, the two levels are stitched together by
open lineage standards — OpenLineage defines the job/dataset event model that engines and
orchestrators emit, and Marquez consumes those events into a queryable graph
(https://openlineage.io/, https://marquezproject.ai/). A complete audit trail is therefore
layered: OpenLineage says *which job run* wrote the table, lakeFS/DVC say *which snapshot* it
read, and plan-level provenance says *which columns and rows* inside it.

## Audit and compliance

- **GDPR/CCPA erasure and access requests**: column-level lineage turns "delete user U's data"
  from a manual hunt into a graph walk — find every column derived from `users.email`, then
  every table downstream. Row-level provenance is the gold standard here but is rarely
  affordable; column-level plus partition keys usually suffices.
- **SOX/financial audit**: regulators ask "show the derivation of this reported figure."
  How-provenance (or its approximation: the persisted query text plus input snapshots) is the
  evidence chain; versioned inputs from lakeFS/DVC make the evidence reproducible years later.
- **Model/data contracts**: propagating quality scores and ownership along the lineage graph
  (the data-engineering page's concern) needs correct column edges, which is exactly what
  predicate-aware propagation adds over naive table-level edges.

## Operational pain

1. **SQL dialect coverage.** Parsers (sqlglot, sqllineage, Calcite) cover the dialects they
   were taught; warehouse-specific syntax — Snowflake flattening, BigQuery structs, T-SQL
   hints — silently falls back to table-level or no lineage. Version pinning of dialect
   support is a real maintenance line item.
2. **UDFs are black boxes.** A UDF's body hides its column reads; conservative tools either
   mark all inputs as dependencies or emit nothing. Python UDFs in Snowflake and Spark make
   column-level lineage best-effort by construction.
3. **Dynamic SQL and templating.** dbt Jinja macros, string-built SQL, and late-binding views
   mean the SQL text you parse is not always the SQL that runs — lineage from parsed text can
   diverge from runtime reality, which is why access-log capture (ACCESS_HISTORY-style) keeps
   winning in closed ecosystems.
4. **Over-approximation is the default honesty.** As the demo shows, predicates and join keys
   widen provenance. Every production tool over-approximates; the differentiator is whether it
   tells you that it did.

## Demo: propagating annotations through a mini plan

Dicts in, dict out — the same transform every planner-side lineage tool performs, including
the conservative filter rule that pulled `currency` into `revenue` above:

```python
# Column-level lineage propagation through a mini query plan:
#   Scan(orders) -> Filter(currency = 'USD')
#     -> Join(orders, customers, ON cust_id)
#     -> Aggregate GROUP BY country: SUM(amount) AS revenue
#
# Annotations are dicts: {output_col -> set of "table.col" provenance}.
# Conservative rule: every operator output inherits ALL inputs it depends on,
# including predicate and join-key columns (a surviving row proves the
# predicate was true, so its cells depend on the predicate columns too).

def scan(table, cols):
    return {f"{table}.{c}": {f"{table}.{c}"} for c in cols}

def filter_(rel, pred_cols):
    pred = set().union(*(rel[c] for c in pred_cols))
    return {c: deps | pred for c, deps in rel.items()}

def join(l, r, lkey, rkey):
    out = {}
    for c, deps in l.items():
        out[c] = deps | {rkey}              # join adds both keys
    for c, deps in r.items():
        out[c] = deps | {lkey}
    return out

def aggregate(rel, group_cols, arg_col, alias):
    out = {c: rel[c] for c in group_cols}
    out[alias] = set().union(rel[arg_col], *(rel[c] for c in group_cols))
    return out

orders    = scan("orders", ["o_id", "cust_id", "amount", "currency"])
customers = scan("customers", ["cust_id", "country"])

s1 = filter_(orders, ["orders.currency"])
s2 = join(s1, customers, "orders.cust_id", "customers.cust_id")
s3 = aggregate(s2, ["customers.country"], "orders.amount", "revenue")

print("stage-by-stage lineage:")
print(f"  after Scan   : orders.amount  -> {sorted(orders['orders.amount'])}")
print(f"  after Filter : orders.amount  -> {sorted(s1['orders.amount'])}")
print(f"  after Join   : orders.amount  -> {sorted(s2['orders.amount'])}")
print(f"  after Join   : customers.country -> {sorted(s2['customers.country'])}")
print(f"  after Agg    : revenue        -> {sorted(s3['revenue'])}")
print()
print("final: SELECT country, SUM(amount) AS revenue ... GROUP BY country")
print(f"  revenue <- {sorted(s3['revenue'])}")
```

Output (executed, Python 3.12):

```text
stage-by-stage lineage:
  after Scan   : orders.amount  -> ['orders.amount']
  after Filter : orders.amount  -> ['orders.amount', 'orders.currency']
  after Join   : orders.amount  -> ['customers.cust_id', 'orders.amount', 'orders.currency']
  after Join   : customers.country -> ['customers.country', 'orders.cust_id']
  after Agg    : revenue        -> ['customers.country', 'customers.cust_id', 'orders.amount', 'orders.currency', 'orders.cust_id']

final: SELECT country, SUM(amount) AS revenue ... GROUP BY country
  revenue <- ['customers.country', 'customers.cust_id', 'orders.amount', 'orders.currency', 'orders.cust_id']
```

Read the final line as an auditor would: `revenue` provably depends on `orders.currency`
(the filter) and both `cust_id` columns (the join), even though neither appears in the SELECT
list. Drop the currency filter and `orders.currency` vanishes from the set — which is precisely
how impact analysis is run in reverse: change an upstream column, then walk forward to see
which derived columns its annotation reached.

## References

- Buneman, Khanna, Tan. "Why and Where: A Characterization of Data Provenance." ICDT 2001. https://link.springer.com/chapter/10.1007/3-540-44503-X_20
- Green, Karvounarakis, Tannen. "Provenance Semirings." PODS 2007. https://doi.org/10.1145/1265530.1265535
- Glavic. "Data Provenance: Origins, Applications, Algorithms, and Models." Foundations and Trends in Databases, 2021. https://doi.org/10.1561/9781680838299
- Snowflake Documentation. "Access History" (ACCESS_HISTORY view, column-level lineage). https://docs.snowflake.com/en/user-guide/access-history
- OpenLineage. Open standard for job-level lineage events. https://openlineage.io/
