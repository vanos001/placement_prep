# NoSQL Databases

## Overview

NoSQL (Not Only SQL) databases are non-relational databases designed for specific data models, horizontal scalability, and high availability. They emerged in the late 2000s to address limitations of traditional RDBMS for web-scale applications: massive data volumes, high write throughput, flexible schemas, and distributed architectures.

## Detailed Explanation

### Why NoSQL?

```mermaid
flowchart TD
    A[Why NoSQL?] --> B[Scale Beyond<br/>Single Machine]
    A --> C[Flexible Schema]
    A --> D[Specific Data Models]
    A --> E[High Availability]

    B --> B1[Horizontal scaling]
    B --> B2[Distributed by design]
    C --> C1[No fixed schema]
    C --> C2[Handle heterogeneous data]
    D --> D1[Key-value, document, graph, column]
    E --> E1[Eventually consistent]

    style A fill:#e1f5fe
```

### NoSQL vs. RDBMS

| Aspect | RDBMS | NoSQL |
|--------|-------|-------|
| **Schema** | Fixed, predefined | Dynamic, flexible |
| **Scaling** | Vertical (bigger machine) | Horizontal (more machines) |
| **Data Model** | Tables, rows, columns | Various (key-value, document, etc.) |
| **ACID** | Full ACID | BASE (eventual consistency) |
| **Joins** | Supported | Limited or none |
| **Query Language** | SQL | Database-specific |
| **Best For** | Complex queries, transactions | Scale, flexibility, specific patterns |

### ACID vs. BASE

```mermaid
flowchart LR
    A[ACID<br/>RDBMS] --> B[Atomicity<br/>Consistency<br/>Isolation<br/>Durability]
    C[BASE<br/>NoSQL] --> D[Basically Available<br/>Soft state<br/>Eventually consistent]

    style A fill:#ffcdd2
    style C fill:#c8e6c9
```

| Property | ACID (RDBMS) | BASE (NoSQL) |
|----------|-------------|--------------|
| **Consistency** | Strong | Eventual |
| **Availability** | Lower (waits for consistency) | Higher (always responds) |
| **Transactions** | Full support | Limited |
| **Scalability** | Vertical | Horizontal |

### Types of NoSQL Databases

```mermaid
flowchart TD
    A[NoSQL Types] --> B[Key-Value<br/>Redis, DynamoDB]
    A --> C[Document<br/>MongoDB, CouchDB]
    A --> D[Column-Family<br/>Cassandra, HBase]
    A --> E[Graph<br/>Neo4j, Amazon Neptune]

    B --> B1[Simple, fast, cache-friendly]
    C --> C1[Flexible, nested data]
    D --> D1[Wide rows, time-series]
    E --> E1[Relationships, traversals]

    style B fill:#e1f5fe
    style C fill:#c8e6c9
    style D fill:#fff3e0
    style E fill:#f3e5f5
```

### Comparison at a Glance

| Type | Data Model | Query Pattern | Scalability | Example |
|------|-----------|---------------|-------------|---------|
| **Key-Value** | Key → Value | Get by key | Excellent | Redis, DynamoDB |
| **Document** | JSON/BSON docs | Query by field | Good | MongoDB, CouchDB |
| **Column-Family** | Rows × Columns | Scan by row/column | Excellent | Cassandra, HBase |
| **Graph** | Nodes + Edges | Traverse relationships | Limited | Neo4j, Neptune |

### CAP Classification

| System | Type | CAP | Consistency |
|--------|------|-----|-------------|
| **Redis** | Key-Value | CP | Strong (single node) |
| **DynamoDB** | Key-Value | AP | Tunable |
| **MongoDB** | Document | CP | Tunable |
| **CouchDB** | Document | AP | Eventual |
| **Cassandra** | Column-Family | AP | Tunable |
| **HBase** | Column-Family | CP | Strong |
| **Neo4j** | Graph | CA (single node) | Strong |
| **Amazon Neptune** | Graph | CP | Strong |

### When to Use NoSQL vs. RDBMS

```mermaid
flowchart TD
    A{Choose Database} --> B{Complex queries<br/>with JOINs?}
    B -->|Yes| C[RDBMS]
    B -->|No| D{Schema flexible<br/>or evolving?}
    D -->|Yes| E{Data model?}
    D -->|No| C
    E -->|Simple key-value| F[Key-Value Store]
    E -->|Nested/hierarchical| G[Document Store]
    E -->|Time-series/wide rows| H[Column-Family]
    E -->|Relationship-heavy| I[Graph Database]

    style C fill:#ffcdd2
    style F fill:#c8e6c9
    style G fill:#c8e6c9
    style H fill:#c8e6c9
    style I fill:#c8e6c9
```

## Topics in This Section

### 1. [Key-Value Stores](./key-value.md)
Redis, DynamoDB, Riak — simple, fast, horizontally scalable.

### 2. [Document Databases](./document.md)
MongoDB, CouchDB — flexible schema, nested data, rich queries.

### 3. [Column-Family Stores](./column-family.md)
Cassandra, HBase — wide rows, time-series, high write throughput.

### 4. [Graph Databases](./graph.md)
Neo4j, Amazon Neptune — relationships, traversals, social networks.

### 5. [NewSQL](./newsql.md)
CockroachDB, TiDB, Spanner — SQL + distributed scalability.

## Interview Focus Areas

1. **When to choose NoSQL over RDBMS?** — Schema flexibility, scale requirements, data model fit
2. **What are the trade-offs?** — Consistency vs. availability, joins vs. scalability
3. **How does each type work?** — Data model, query patterns, scaling mechanism
4. **What is BASE?** — Basically Available, Soft state, Eventually consistent
5. **Polyglot persistence** — Using multiple database types for different needs

## Cross-References

- [CAP Theorem](../distributed/cap.md) — NoSQL trade-offs
- [Consistency Models](../distributed/consistency.md) — NoSQL consistency guarantees
- [Sharding](../distributed/sharding.md) — how NoSQL scales
- [Replication](../distributed/replication.md) — how NoSQL replicates
- [Buffer Management](../storage/buffer-management.md) — underlying storage
