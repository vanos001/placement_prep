# Graph Query Languages: Cypher, SPARQL, Gremlin, and GQL

Four query languages dominate graph workloads, and they split along one seam: **Cypher**, **Gremlin**, and the ISO standard **GQL** query *property graphs* (typed, directed edges carrying properties), while **SPARQL** queries *RDF triples* (subject-predicate-object statements). This page is the language layer: what a result row is (valuation vs traversal), path semantics (trails vs walks), standardization status, and a runnable pattern matcher. Storage engines, indexing, and sharding are covered in [graph-databases.md](graph-databases.md).

## One graph, two models

```text
Property graph (typed edges, first-class):

    (alice:Person {name:"Alice", age:29}) --KNOWS {since:2020}-->
    (bob:Person {name:"Bob", age:31})

The same fact as RDF triples (flat statements, URIs for identity):

    <alice> <name>  "Alice" .
    <alice> <age>   "29"^^xsd:integer .
    <alice> <knows> <bob> .

The same one-hop question, asked four ways:

    Cypher  : MATCH (a:Person)-[r:KNOWS {since:2020}]->(b) RETURN a.name, b.name
    Gremlin : g.V().hasLabel('Person').outE('KNOWS').has('since',2020).otherV()
    SPARQL  : ?a :knows ?b .        (name/age live in separate triples)
    GQL     : MATCH (a:Person)-[r:KNOWS]->(b) ...   (standardized Cypher-shaped patterns)
```

Nothing about the *data* forces the split -- Amazon Neptune serves both models -- but the languages differ in what a result is: Cypher/GQL bind whole path structures, SPARQL binds variables to terms, Gremlin streams traversers through a step pipeline.

## Cypher: pattern valuation with a hard-wired uniqueness rule

Cypher is declarative: a `MATCH` clause describes a shape and the engine returns every binding (a multiset of rows) that values the pattern. Two semantic details interviewers probe:

- **Relationship-uniqueness (trail semantics).** Within one pattern a relationship is used at most once, while nodes may repeat. Neo4j's manual states the default as "nodes but not relationships can be traversed more than once in a graph pattern"; `REPEATABLE ELEMENTS` opts out.
- **Variable-length paths.** `-[:KNOWS*1..2]->` enumerates trails of length 1 to 2 -- the demo below reproduces exactly this, including the duplicate rows produced when a 1-hop edge and a 2-hop trail both satisfy the pattern.

Core Cypher's `shortestPath()` returns a single unweighted shortest path; weighted variants live in libraries (GDS/APOC). Cypher itself never became an ISO standard -- the vendor consortium published the openCypher specification (candidate v9, public PDF) as an industry spec, which is the gap ISO/IEC 39075 later closed. Neo4j's current Cypher 25 line is converging on GQL: the manual's GQL-conformance appendix (updated June 2026) tracks adopted feature areas -- path patterns and graph patterns, variable length paths, shortest paths, match modes and path modes.

## SPARQL 1.1: set algebra, not path finding

SPARQL evaluates over triples. A **basic graph pattern (BGP)** is a set of triple patterns whose evaluation joins **solution mappings** (variable -> term): a homomorphism valuation with no path object. Section 18 of the spec translates surface syntax into algebra operators (`Join`, `LeftJoin` for OPTIONAL, `Union`, `Filter`) and then applies a fixed modifier pipeline: `ToList -> OrderBy -> Project -> Distinct -> Reduced -> Slice`. Three consequences of being set-based over triples:

- **Property paths** (`elt*`, `elt+`, alternation, inverse) answer with *distinct node pairs*: `?a ex:knows+ ?b` gives reachability, but hands you no path to inspect and no shortest-path guarantee; cycles are absorbed by the spec's evaluation rules, not returned as walks.
- Duplicate behavior is asymmetric: BGP joins are multiset joins (each homomorphism is a row) while path evaluation is distinct; OPTIONAL is exactly `LeftJoin`, negation is `FILTER NOT EXISTS` / `MINUS`.

## Gremlin: traversal as dataflow

Gremlin (Apache TinkerPop) is not pattern-valuation at all. A query is a pipeline of **steps** (`V()`, `outE()`, `has()`, `inV()`) executed by a traversal machine that spawns *traversers* carrying optional path history; TinkerPop calls itself "a graph computing framework for both graph databases (OLTP) and graph analytic systems (OLAP)", and the same traversal targets a TP3 database or a `GraphComputer` OLAP job. Consequences:

- Default path semantics are **walks**: traversers may revisit vertices and edges; `.simplePath()` filters repeats and `path()` reconstructs the route when you need one.
- There is no declarative optimizer boundary -- reordering is the author's job or a traversal strategy's -- which is why Gremlin reads imperative next to Cypher/SPARQL.

## GQL (ISO/IEC 39075:2024) and SQL/PGQ (ISO/IEC 9075-16:2023)

GQL was published on 17 April 2024, developed in ISO/IEC JTC 1/SC 32, and is described by the GQL Standards Committee as the first new ISO database-language standard since SQL. Its ISO abstract: the syntax and semantics of a data management language for property graphs. Concretely, GQL standardizes:

- Cypher-heritage pattern matching: `MATCH` with ASCII-art patterns, quantified relationship patterns (`*1..2`), `WHERE`, `RETURN` with aggregation, `OPTIONAL MATCH`, plus GQL DML (`INSERT`, `SET`, `REMOVE`, `DELETE`).
- **Declared path modes** per pattern -- `WALK`, `TRAIL`, `ACYCLIC`, `SIMPLE` -- turning Cypher's implicit relationship-uniqueness into a query-level choice, and **quantified shortest paths** (`ANY`, `SHORTEST k`, `ALL SHORTEST`) instead of one fixed `shortestPath()` function.
- Graph/schema DDL (`CREATE GRAPH`, `CREATE GRAPH TYPE`) and the session/transaction machinery openCypher never specified.

The sibling lives inside SQL: SQL:2023 (ISO/IEC 9075:2023) added **part 16, SQL/PGQ**, so relational engines can define property graphs (`CREATE PROPERTY GRAPH`) and query them with `GRAPH_TABLE`. ISO notes that "GQL supports the same graph pattern matching syntax as SQL Property Graph Queries" -- one pattern language, two host languages. Oracle Database 23ai shipped SQL/PGQ (vendor-reported); DuckDB has a community DuckPGQ extension (PVLDB 2023) for a subset. Once patterns lower to joins, the relational optimizer takes over, including worst-case-optimal join machinery for cyclic patterns -- see [query-optimizers.md](query-optimizers.md); Memgraph's Cascades-style Cypher planner is covered in [cascades-optimizer.md](cascades-optimizer.md).

## A runnable Cypher-shaped matcher (pure stdlib)

The ~100-line matcher below supports the demo subset: `MATCH (a)-[r:TYPE]->(b)` and `(a)-[r:TYPE*1..2]->(b)`, `WHERE var.prop OP literal` clauses joined by `AND`, and `RETURN var.prop`. It implements trail semantics (an edge at most once per match, nodes may repeat), ALL-semantics for predicates on variable-length edge variables, and multiset rows -- then cross-checks every query against an enumerate-and-filter brute force. It is not a Cypher engine; it is the smallest honest core of one.

```python
# mini_cypher.py -- Cypher-shaped pattern matcher, tiny educational subset:
# MATCH (a)-[r:TYPE]->(b) | (a)-[r:TYPE*1..2]->(b); WHERE v.p OP lit AND ...; RETURN v.p.
# No chained hops, OPTIONAL MATCH, aggregation, or updates.  Semantics = Cypher's
# default relationship-uniqueness (TRAIL): edges used at most once, nodes may repeat,
# an edge-var predicate is ALL.  Trail-uniqueness also spans hop lists (see `used`).
import re, itertools
from collections import Counter
NODES = {"alice": {"name": "Alice", "age": 29}, "bob":   {"name": "Bob",   "age": 31},
         "carol": {"name": "Carol", "age": 34}, "dave":  {"name": "Dave",  "age": 25},
         "erin":  {"name": "Erin",  "age": 29}, "frank": {"name": "Frank", "age": 40}}
def E(i, s, d, y): return (i, s, d, "KNOWS", {"since": y})
EDGES = [E(0, "alice", "bob", 2020), E(1, "alice", "carol", 2022), E(2, "bob", "carol", 2019),
         E(3, "bob", "dave", 2021),  E(4, "carol", "dave", 2022),  E(5, "dave", "erin", 2023),
         E(6, "erin", "frank", 2024), E(7, "frank", "alice", 2021), E(8, "bob", "alice", 2022)]
HOP = re.compile(r"\((\w+)\)-\[(\w+)?(?::(\w+))?(?:\*(\d+)\.\.(\d+))?\]->\((\w+)\)")
OPS = {">=": lambda x, y: x >= y, "<=": lambda x, y: x <= y, ">": lambda x, y: x > y, "<": lambda x, y: x < y,
       "=": lambda x, y: x == y, "!=": lambda x, y: x != y}

def parse(q):
    m = re.match(r"\s*MATCH (.+?)(?: WHERE (.+?))? RETURN (.+)", q).groups()
    hops = [(h[0], h[1] or "r", h[2] or "", int(h[3] or 1), int(h[4] or 1), h[5])
            for h in (x.groups() for x in HOP.finditer(m[0]))]
    preds = [re.match(r"(\w+)\.(\w+)\s*(>=|<=|!=|=|>|<)\s*([\w'\"]+)", p.strip()).groups()
             for p in (m[1] or "").split(" AND ") if p.strip()]
    return hops, preds, [c.strip().split(".") for c in m[2].split(",")]

def lookup(b, prop):  # b: node id (str) or tuple of edges (variable-length binding)
    if isinstance(b, str): return NODES[b][prop]
    return [e[4][prop] for e in (b if isinstance(b[0], tuple) else [b])]

def paths(start, etype, lo, hi, used):  # trail-unique edge sequences, length lo..hi
    out = []
    def step(cur, acc):
        if lo <= len(acc) <= hi: out.append((cur, tuple(acc)))
        if len(acc) >= hi: return
        for e in EDGES:
            if e[0] in used or (etype and e[3] != etype): continue
            if cur is not None and e[1] != cur: continue
            used.add(e[0]); acc.append(e); step(e[2], acc); used.discard(e[0]); acc.pop()
    step(start, [])
    return out

def match(hops):  # streaming matcher; `used` enforces trails across the pattern
    rows = [({}, frozenset())]
    for src, rvar, etype, lo, hi, dst in hops:
        nxt = []
        for env, used in rows:
            for end, seq in paths(env.get(src), etype, lo, hi, set(used)):
                if dst == src and seq[0][1] != end: continue  # same var at both ends
                e2 = dict(env)
                e2[src], e2[dst], e2[rvar] = seq[0][1], end, tuple(seq)
                nxt.append((e2, used | {x[0] for x in seq}))
        rows = nxt
    return [env for env, _ in rows]

def where(preds, env):
    for var, prop, op, lit in preds:
        got = lookup(env[var], prop)
        lit = int(lit) if lit.isdigit() else lit.strip("'\"")
        if not all(OPS[op](x, lit) for x in (got if isinstance(got, list) else [got])):
            return False
    return True

def project(env, rets):  # the demo RETURNs only node properties
    return tuple(NODES[env[v]][p] for v, p in rets)

def brute(hops, preds, rets):  # enumerate-and-filter reference implementation
    out = []
    def go(i, env, used):
        if i == len(hops):
            if where(preds, env): out.append(project(env, rets))
            return
        src, rvar, etype, lo, hi, dst = hops[i]
        for L in range(lo, hi + 1):
            for combo in itertools.product(EDGES, repeat=L):
                ids = {e[0] for e in combo}
                if len(ids) != L or (used & ids): continue
                if etype and any(e[3] != etype for e in combo): continue
                if any(combo[j][2] != combo[j + 1][1] for j in range(L - 1)): continue
                if src in env and env[src] != combo[0][1]: continue
                if dst == src and combo[0][1] != combo[-1][2]: continue
                if dst in env and dst != src and env[dst] != combo[-1][2]: continue
                e2 = dict(env)
                e2[src] = combo[0][1]
                e2[dst] = combo[-1][2] if dst != src else combo[0][1]
                e2[rvar] = tuple(combo)
                go(i + 1, e2, used | ids)
    go(0, {}, set())
    return Counter(out)

def run(title, q):
    hops, preds, rets = parse(q)
    rows = sorted(project(env, rets) for env in match(hops) if where(preds, env))
    print("== %s\n   %s\n   %s  [rows: %d]" % (title, q,
          " | ".join(".".join(p) for p in rets), len(rows)))
    for r in rows: print("     %s" % " | ".join(map(str, r)))
    print("   brute-force agreement: %s" % (Counter(rows) == brute(hops, preds, rets)))

run("Q1: 1-hop + WHERE on edge and node", "MATCH (a)-[r:KNOWS]->(b) WHERE r.since >= 2022 AND b.age <= 30 RETURN a.name, b.name")
run("Q2: variable-length *1..2 (multiset rows, trails)", "MATCH (a)-[r:KNOWS*1..2]->(b) WHERE a.age >= 30 AND b.age <= 30 RETURN a.name, b.name")
run("Q3: same variable at both ends (node repeats, edges may not)", "MATCH (a)-[r:KNOWS*1..2]->(a) RETURN a.name")
```

Actual output (Python 3.12.14, run Aug 2026):

```text
== Q1: 1-hop + WHERE on edge and node
   MATCH (a)-[r:KNOWS]->(b) WHERE r.since >= 2022 AND b.age <= 30 RETURN a.name, b.name
   a.name | b.name  [rows: 3]
     Bob | Alice
     Carol | Dave
     Dave | Erin
   brute-force agreement: True
== Q2: variable-length *1..2 (multiset rows, trails)
   MATCH (a)-[r:KNOWS*1..2]->(b) WHERE a.age >= 30 AND b.age <= 30 RETURN a.name, b.name
   a.name | b.name  [rows: 7]
     Bob | Alice
     Bob | Dave
     Bob | Dave
     Bob | Erin
     Carol | Dave
     Carol | Erin
     Frank | Alice
   brute-force agreement: True
== Q3: same variable at both ends (node repeats, edges may not)
   MATCH (a)-[r:KNOWS*1..2]->(a) RETURN a.name
   a.name  [rows: 2]
     Alice
     Bob
   brute-force agreement: True
```

Read Q2 closely: `(Bob, Dave)` appears twice because a 1-hop edge and a 2-hop trail both bind the pattern -- Cypher without `DISTINCT` does the same. Q3 is the trail-semantics showpiece: `Alice -> Bob -> Alice` matches `(a)-[*1..2]->(a)` because the *node* repeats while the two *relationships* stay distinct.

## Semantics comparison

| Dimension | Cypher / openCypher | SPARQL 1.1 | Gremlin | GQL (ISO 39075) |
|---|---|---|---|---|
| Evaluation model | pattern valuation (binding rows) | set algebra over solution mappings | traverser dataflow over steps | pattern valuation + SQL-style clauses |
| Edge reuse within a match | forbidden (trail default) | BGP allows it (homomorphism); paths distinct | allowed (walks) | declared: WALK yes, TRAIL no |
| Node reuse | allowed | allowed | allowed | WALK/TRAIL yes; ACYCLIC/SIMPLE no |
| Path as result object | yes (path variables) | no -- distinct endpoint pairs only | yes (`path()` step) | yes (path bindings) |
| Recursion primitive | quantified rel `-[*1..n]->` | property paths `+` / `*` | `repeat().until()` | quantified patterns |
| Shortest path | `shortestPath()` single, unweighted | not offered | `repeat().limit(1)` idiom | `ANY` / `SHORTEST k` / `ALL SHORTEST` |

## Who implements what

| Engine | Graph model | Query languages | Notes |
|---|---|---|---|
| Neo4j | property graph | Cypher 5 / Cypher 25 | GQL-conformance appendix documents supported mandatory GQL features (manual updated Jun 2026) |
| Memgraph | property graph | Cypher (openCypher-based) | reported; Cascades-style planner (cascades-optimizer.md) |
| JanusGraph | property graph | Gremlin | TinkerPop stack; docs probed 200 |
| Amazon Neptune | property graph + RDF | Gremlin, openCypher (subset), SPARQL 1.1 | tri-language per AWS docs (search-verified) |
| Blazegraph | RDF | SPARQL 1.1 | reported; also backs the Wikidata Query Service |
| Apache Jena | RDF | SPARQL 1.1 (ARQ) | tutorial probed 200 |
| rdflib | RDF (in-process Python) | SPARQL 1.1 | docs probed 200 |
| Oracle 23ai | relational + property graphs | SQL/PGQ | vendor-reported (blog, Mar 2025) |
| DuckDB | relational + graph views | SQL/PGQ subset via DuckPGQ | community extension, PVLDB 2023 |

Vendor-doc URLs probed HTTP 200 in Aug 2026: neo4j.com (Cypher Manual), docs.janusgraph.org, jena.apache.org, rdflib.readthedocs.io, blazegraph.com.

## Interview angles

- "Why can't SPARQL 1.1 hand you the shortest path?" -- property paths return distinct node pairs; there is no path value to inspect.
- "You port a Cypher `*1..2` query to Gremlin naively -- what breaks?" -- walk semantics revisit edges; you need `.simplePath()` to recover trail behavior.
- "What did GQL standardize beyond openCypher v9?" -- graph/schema DDL, declared path modes, shortest-path quantifiers, session/transaction semantics, and pattern-syntax parity with SQL/PGQ.
- "Where do graph languages meet the relational optimizer?" -- SQL/PGQ lowers patterns to joins; cyclic patterns are where WCOJ earns its keep.

## References

- openCypher project home (probed 200): https://opencypher.org/
- openCypher Cypher Query Language Specification, candidate v9, PDF (probed 200): https://s3.amazonaws.com/artifacts.opencypher.org/openCypher9.pdf
- Neo4j Cypher Manual (probed 200): https://neo4j.com/docs/cypher-manual/current/
- Neo4j Cypher Manual, "Paths with unique relationships" (probed 200): https://neo4j.com/docs/cypher-manual/current/patterns/unique-relationship-paths
- Neo4j Cypher Manual, "GQL conformance" appendix, updated 1 Jun 2026 (probed 200): https://neo4j.com/docs/cypher-manual/current/appendix/gql-conformance/
- Neo4j blog, "GQL: The ISO standard for graphs has arrived", Apr 2024 (probed 200): https://neo4j.com/blog/cypher-and-gql/cypher-path-gql/
- W3C, "SPARQL 1.1 Query Language", W3C Recommendation 21 March 2013 (probed 200): https://www.w3.org/TR/sparql11-query/
- Apache TinkerPop home, "graph computing framework ... (OLTP) and ... (OLAP)" (probed 200): https://tinkerpop.apache.org/
- Apache TinkerPop Reference, resolves to 3.8.1 (probed 200): https://tinkerpop.apache.org/docs/current/reference/
- GQL Standards Committee, "The GQL Standard is published", 17 Apr 2024 (probed 200): https://www.gqlstandards.org/
- ISO, "ISO/IEC 39075:2024 -- Database languages -- GQL" (iso.org returns 403 to scripted probes; verified via search index and gqlstandards.org): https://www.iso.org/standard/76120.html
- ISO, "ISO/IEC 9075-16:2023 -- SQL/PGQ" (403 to scripted probes; search-verified): https://www.iso.org/standard/79473.html
- P. Eisentraut, "SQL:2023 is finished: Here is what's new", 4 Apr 2023 (probed 200): https://peter.eisentraut.org/blog/2023/04/04/sql-2023-is-finished-here-is-whats-new
- AWS, "Querying a Neptune Graph" (page is JS-gated to curl; language list search-verified): https://docs.aws.amazon.com/neptune/latest/userguide/access-graph-queries.html
