# Graph Databases

Graph databases store data as **nodes** (entities) and **edges** (relationships), enabling efficient traversal of highly connected data. This chapter covers graph query languages (Cypher, SPARQL, Datalog), graph join algorithms, graph analytics, and distributed graph databases.

## Graph Data Model

### Property Graph Model

The **property graph** (used by Neo4j, Neptune, Memgraph) is the most common graph database model:

```
Node:      (Person {name: "Alice", age: 30})
Edge:      -[KNOWS {since: 2020}]->
Relationship: (Alice)-[KNOWS]->(Bob)

Schema-free: nodes and edges can have arbitrary key-value properties.
Edges are first-class: they have types, properties, and direction.
```

### RDF Triple Store Model

The **Resource Description Framework (RDF)** model stores data as **triples** (subject, predicate, object):

```
<Alice> <knows> <Bob> .
<Bob> <age> "30"^^xsd:integer .
<Alice> <type> <Person> .
```

RDF supports **open-world semantics**: anything can have properties, and absence of information is not falsity. Used in **semantic web** and **knowledge graph** applications.

### Comparison

| Aspect | Property Graph | RDF Triple Store |
--------|---------------|-----------------|
| Schema | Optional (node labels, edge types) | Optional (ontologies, RDFS, OWL) |
| Edge model | Typed, directed, first-class | Uniform triples (predicate = edge label) |
| Identity | Node IDs | URIs / blank nodes |
| Query language | Cypher, Gremlin | SPARQL |
| Reasoning | None (application-level) | Built-in (RDFS, OWL inference) |
| Used in | Neo4j, Neptune, Memgraph | Blazegraph, Stardog, Amazon Neptune (dual) |

## Query Languages

### Cypher

Cypher (Neo4j) uses an **ASCII-art pattern matching** syntax:

```cypher
-- Find friends of friends who are not already friends
MATCH (p:Person {name: 'Alice'})-[:KNOWS]->(friend)-[:KNOWS]->(fof)
WHERE NOT (p)-[:KNOWS]->(fof)
RETURN DISTINCT fof.name, COUNT(friend) AS mutual_friends
ORDER BY mutual_friends DESC
LIMIT 10;

-- Path finding: shortest path between two people
MATCH path = SHORTEST 1
  (a:Person {name: 'Alice'})-[*..6]-(b:Person {name: 'Bob'})
RETURN path;

-- Aggregation with graph projection
MATCH (p:Person)-[r:KNOWS]->(friend:Person)
WITH p, COLLECT(friend) AS friends, AVG(r.weight) AS avg_weight
WHERE SIZE(friends) > 5
RETURN p.name, SIZE(friends), avg_weight;
```

**Execution**: Cypher queries are parsed into a **query plan** with graph-specific operators: node index seek, expand (traverse edge), filter, path find, and aggregate. Neo4j's **COST-based optimizer** (since Neo4j 5.x) uses statistics on node/relationship counts to choose join order and index usage.

### SPARQL

SPARQL is the W3C standard for querying RDF data:

```sparql
# Find people who know someone over 30
PREFIX ex: <http://example.org/>

SELECT ?person ?friend ?age WHERE {
  ?person ex:knows ?friend .
  ?friend ex:age ?age .
  FILTER (?age > 30)
  ?person a ex:Person .
}
ORDER BY DESC(?age)
LIMIT 10;

# Property paths (recursive)
SELECT ?path WHERE {
  ?path (ex:knows)+ ?target .  # one or more KNOWS edges
}
```

**SPARQL features**: FILTER, OPTIONAL (left outer join), UNION, subqueries, property paths (`*`, `+`, `?`, `|`), aggregation, and federated queries (querying multiple SPARQL endpoints).

### Datalog

Datalog is a **declarative logic programming** language used in databases (Datomic, LogicBlox) and program analysis:

```datalog
// Rules (recursive)
ancestor(X, Y) :- parent(X, Y).          // base case: parent is ancestor
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).  // recursive: ancestor of ancestor

// Query
?- ancestor(alice, X).  // Find all ancestors of alice

// Stratified negation
not_friend(X, Y) :- person(X), person(Y), X != Y, NOT friend(X, Y).
```

**Key properties**: Datalog is **declarative**, **recursion-safe** (stratified negation guarantees termination), and **relationally complete**. Its fixed-point semantics make it ideal for graph reachability, transitive closure, and data lineage.

| Feature | Cypher | SPARQL | Datalog |
---------|--------|--------|--------|
| Pattern matching | Visual (ASCII art) | Triple patterns | Logical rules |
| Recursion | Limited (variable-length paths) | Property paths | Native (fixed-point) |
| Negation | `NOT` / `WHERE NOT` | `FILTER NOT EXISTS` | Stratified `NOT` |
| Aggregation | Yes | Yes | Yes (via aggregation predicates) |
| Update | `CREATE`, `MERGE`, `DELETE` | `INSERT DATA`, `DELETE` | Varies by system |

## Recursive Query Optimization

### Transitive Closure

Computing transitive closure (all reachable nodes) is a fundamental graph operation. The naive approach iterates until fixpoint:

```sql
-- Iterative transitive closure (SQL)
CREATE TABLE reachable (ancestor INT, descendant INT);
INSERT INTO reachable SELECT parent, child FROM edges;

-- Repeat until no new rows
WHILE EXISTS (
  SELECT 1 FROM edges e JOIN reachable r ON e.parent = r.descendant
  WHERE NOT EXISTS (SELECT 1 FROM reachable WHERE ancestor = r.ancestor AND descendant = e.child)
):
  INSERT INTO reachable
  SELECT r.ancestor, e.child
  FROM edges e JOIN reachable r ON e.parent = r.descendant
  EXCEPT SELECT * FROM reachable;
```

This is O(n × diameter) iterations, each requiring a join. For large graphs, this is expensive.

### Semi-Naive Evaluation

Semi-naive evaluation avoids re-deriving already-known facts by tracking **deltas** (new facts discovered in the previous iteration):

```python
def semi_naive_transitive_closure(edges):
    # R0: base case
    R = set(edges)  # (parent, child) pairs
    delta = set(edges)
    
    while delta:
        # Only join delta with edges (not full R)
        new = {(a, c) for (a, b) in delta for (b2, c) in edges if b == b2}
        new -= R  # remove already known
        R |= new
        delta = new
    
    return R
```

Semi-naive reduces work by only processing **newly discovered** facts, giving the same result with roughly half the work of naive evaluation.

## Graph Joins

### Index Nested Loop Join (INLJ)

For graph pattern matching `MATCH (a)-[r]->(b)-[r2]->(c)`, the typical execution is a series of **index nested loop joins**:

```
1. Scan/seek node 'a' via index
2. For each 'a', expand edge 'r' → get 'b'  (index lookup on edge store)
3. For each 'b', expand edge 'r2' → get 'c'
4. Filter and return
```

This is essentially a **variable-at-a-time** join where each step binds one variable and looks up its neighbors.

### Worst-Case Optimal Graph Joins

For queries involving multiple relationships (e.g., triangle finding, clique detection), binary joins can be suboptimal. **Worst-case optimal join** algorithms (see [query-optimizers.md](query-optimizers.md)) are particularly relevant for graph workloads:

- **Triangle query**: `MATCH (a)-[:KNOWS]->(b)-[:KNOWS]->(c), (a)-[:KNOWS]->(c)` — three joins forming a cycle. Standard binary joins may scan O(n³) intermediate results. WCOJ (Leapfrog Triejoin) guarantees O(n^{3/2}) output-sensitive runtime.
- **Systems**: DuckDB supports WCOJ for 3+ way cyclic joins.

## Graph Analytics

### Graph Analytics Algorithms

| Algorithm | Problem | Complexity | System Support |
-----------|---------|------------|----------------|
| **BFS/DFS** | Reachability, path finding | O(V + E) | All graph DBs |
| **PageRank** | Node importance | O(k × E) iter | Neo4j GDS, Spark GraphX |
| **Connected components** | Community detection | O(V + E) | Neo4j GDS, GraphX |
| **Community detection** (Louvain) | Modularity optimization | O(E × log V) | Neo4j GDS |
| **Shortest path** (Dijkstra, A*) | Path length | O(E + V log V) | All graph DBs |
| **Triangle counting** | Clustering coefficient | O(E^{3/2}) WCO | Neo4j GDS |
| **Centrality** (betweenness, closeness) | Node influence | O(VE) or O(V³) | Neo4j GDS |

### Graph Processing Frameworks

| System | Processing Model | Graph Size | Language |
--------|-----------------|------------|----------|
| **Neo4j GDS** | In-memory, single-node | Millions | Cypher, Java API |
| **Apache TinkerPop (Gremlin)** | OLTP + OLAP (Spark) | Billions | Gremlin (Groovy, Java) |
| **Spark GraphX / GraphFrames** | Pregel-style, distributed | Billions | Scala, Python |
| **GraphBLAS** | Sparse linear algebra | Billions | C, Python |
| **JanusGraph** | Distributed, pluggable backend | Billions | Gremlin |

## Distributed Graph Databases

### Distribution Strategies

| Strategy | Mechanism | Edge Traversal Cost | Used In |
----------|-----------|--------------------|----|----------|
| **Vertex-cut** | Edges partitioned; vertices replicated across partitions | Local if both endpoints co-located | JanusGraph, Neptune |
| **Edge-cut** | Vertices partitioned; edges stored with source vertex | Remote if target is on different partition | Spark GraphX |
| **Doc-based** | Subgraphs (neighborhoods) stored together | Local for 1-hop | Neo4j (enterprise) |

**Vertex-cut sharding** is preferred for natural graphs (social networks) where high-degree vertices would create hotspots with edge-cut. The hash function typically considers both endpoint vertex IDs:

```python
def partition(edge, num_shards):
    src_hash = hash(edge.src)
    dst_hash = hash(edge.dst)
    return (src_hash XOR dst_hash) % num_shards
```

### Challenges

1. **Multi-hop queries**: A 3-hop query may require 3 remote RPCs across partitions. Latency compounds linearly.
2. **Supernodes**: Nodes with millions of edges (celebrities in social graphs) are hard to partition and cause load imbalance.
3. **Consistency**: Graph mutations (add/delete edge) may span multiple partitions.

> **Interview Angle**: "How would you store and query a social graph with billions of edges?" — Discuss vertex-cut sharding, adjacency list storage, index nested loop join for traversal, and the supernode problem. For analytics, mention Neo4j GDS or Spark GraphX. For OLTP, mention JanusGraph with Cassandra/ScyllaDB backend.

## References

- Angles, R. & Gutierrez, C. "Survey of Graph Database Models." ACM Computing Surveys, 2008.
- Vicknair, C. et al. "A Comparison of a Graph Database and a Relational Database." ACM SE, 2010.
- Ngo, H.Q. et al. "Worst-case Optimal Join Algorithms." JACM, 2014.
- Rodriguez, M.A. & Neubauer, P. "Constructions from Dots and Lines." Bulletin of the ASIS&T, 2010. (TinkerPop/Gremlin)