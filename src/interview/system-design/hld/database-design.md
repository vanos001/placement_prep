# Database Selection and Design

## Choosing the Right Database

The database choice is one of the most critical decisions in system design. It affects performance, scalability, consistency, and operational complexity.

## SQL vs NoSQL

### SQL (Relational Databases)
```
┌─────────────────────────────────┐
│           Users Table           │
├────┬─────────┬────────┬────────┤
│ id │  name   │ email  │ dept_id│
├────┼─────────┼────────┼────────┤
│ 1  │ Alice   │ a@x.co │ 10     │
│ 2  │ Bob     │ b@x.co │ 20     │
└────┴─────────┴────────┴────────┘
         ↓ JOIN ↓
┌─────────────────────────┐
│     Departments Table   │
├────┬────────────────────┤
│ id │  name              │
├────┼────────────────────┤
│ 10 │  Engineering       │
│ 20 │  Marketing         │
└────┴────────────────────┘
```

**Examples**: PostgreSQL, MySQL, Oracle, SQL Server

**Characteristics**:
- Structured schema (tables, rows, columns)
- ACID transactions
- SQL query language
- Relationships via foreign keys + JOINs
- Vertical scaling (primarily), horizontal via sharding

### NoSQL (Non-Relational)

#### Document Store
```json
{
  "_id": "user1",
  "name": "Alice",
  "email": "a@x.co",
  "department": {
    "id": 10,
    "name": "Engineering"
  }
}
```
**Examples**: MongoDB, CouchDB, Firestore
**Best for**: Content management, user profiles, catalogs

#### Key-Value Store
```
"user:1:name" → "Alice"
"user:1:email" → "a@x.co"
"session:abc123" → "{...}"
```
**Examples**: Redis, DynamoDB, Memcached
**Best for**: Caching, session storage, real-time data

#### Column-Family Store
```
Row Key: user1
  ┌──────────┬──────────┬──────────┐
  │ Profile  │ Activity │ Settings │
  │ name:Ali │ last:now │ theme:dk │
  │ email:a@ │ login:5  │ lang:en  │
  └──────────┴──────────┴──────────┘
```
**Examples**: Cassandra, HBase, ScyllaDB
**Best for**: Time-series, IoT, logging, write-heavy workloads

#### Graph Database
```
(Alice) --[FRIENDS]--> (Bob)
   |                     |
[WORKS_AT]          [WORKS_AT]
   ↓                     ↓
(Google) <--[EMPLOYS]--(Google)
```
**Examples**: Neo4j, Amazon Neptune, ArangoDB
**Best for**: Social networks, recommendation engines, fraud detection

### SQL vs NoSQL Comparison

| Factor | SQL | NoSQL |
|--------|-----|-------|
| Schema | Fixed, predefined | Flexible, dynamic |
| Scaling | Vertical (primarily) | Horizontal (native) |
| Consistency | Strong (ACID) | Eventual (BASE) |
| Transactions | Full ACID support | Limited/none |
| Query Language | SQL (standardized) | Varies by DB |
| Relationships | JOINs (powerful) | Denormalized/embedded |
| Best for | Complex queries, transactions | High scale, flexible schema |

### Decision Matrix

| Use Case | Recommended | Why |
|----------|------------|-----|
| E-commerce (orders, payments) | SQL (PostgreSQL) | ACID transactions needed |
| Social media feed | NoSQL (Cassandra) | Write-heavy, high scale |
| User sessions | Key-Value (Redis) | Fast reads, TTL support |
| Product catalog | Document (MongoDB) | Flexible schema |
| Real-time analytics | Column (Cassandra) | Write-optimized |
| Social graph | Graph (Neo4j) | Relationship queries |
| Financial transactions | SQL (PostgreSQL) | Strong consistency |
| IoT sensor data | Column (Cassandra) | Time-series, high write |

## Database Sharding

### What is Sharding?
Splitting a large database into smaller, faster, more manageable pieces called **shards**.

```
                    ┌──────────┐
                    │  Router  │
                    └────┬─────┘
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │ Shard 1│ │ Shard 2│ │ Shard 3│
         │ Users  │ │ Users  │ │ Users  │
         │ A-H    │ │ I-P    │ │ Q-Z    │
         └────────┘ └────────┘ └────────┘
```

### Sharding Key Selection

The shard key determines how data is distributed.

| Shard Key | Distribution | Range Queries | Hotspots |
|-----------|-------------|---------------|----------|
| User ID (hash) | Even | Poor | None |
| Geographic | By region | Good | Possible |
| Time-based | By period | Excellent | Yes (current) |
| Tenant ID | By customer | Good | If one tenant is large |

### Sharding Challenges

1. **Cross-shard queries**: JOINs across shards are expensive
2. **Rebalancing**: Adding shards requires data migration
3. **Hotspots**: Uneven data distribution
4. **Referential integrity**: Foreign keys across shards
5. **Transactions**: Distributed transactions are complex

### Sharding Approaches

#### Application-Level Sharding
```python
def get_shard(user_id):
    shard_num = hash(user_id) % NUM_SHARDS
    return SHARDS[shard_num]
```
- Application decides shard routing
- Flexible but adds complexity

#### Proxy-Based Sharding
```
App → Proxy (Vitess, ProxySQL) → Shards
```
- Proxy handles routing transparently
- Examples: Vitess (for MySQL), Citus (for PostgreSQL)

## Database Replication

### Primary-Replica (Master-Slave)
```
         ┌──────────┐
         │  Primary  │ ←── Writes
         │   DB      │
         └─────┬────┘
          ┌────┼────┐
          ▼    ▼    ▼
        [R1]  [R2]  [R3]  ←── Reads
```

- **Primary**: Handles all writes
- **Replicas**: Handle reads, async replication
- **Use case**: Read-heavy workloads (90%+ reads)

### Multi-Primary (Master-Master)
```
[Primary 1] ←──────→ [Primary 2]
     ↑                    ↑
     │                    │
  Writes               Writes
```

- Both primaries accept writes
- Conflict resolution needed
- **Use case**: Multi-region deployments

### Synchronous vs Asynchronous Replication

| Aspect | Synchronous | Asynchronous |
|--------|------------|--------------|
| Consistency | Strong | Eventual |
| Write latency | Higher (waits for replica) | Lower |
| Data loss risk | None | Possible on primary failure |
| Availability | Lower (replica failure blocks writes) | Higher |

## Partitioning Strategies

### Horizontal Partitioning (Sharding)
Split rows across databases based on a key.

### Vertical Partitioning
Split columns across databases.

```
Before:
┌────┬────────┬──────────┬────────────────┐
│ id │ name   │ email    │ profile_pic    │
└────┴────────┴──────────┴────────────────┘

After:
┌────┬────────┐    ┌────┬──────────┬────────────────┐
│ id │ name   │    │ id │ email    │ profile_pic    │
└────┴────────┘    └────┴──────────┴────────────────┘
   Users Core          User Profile
```

- Reduces row size, improves cache efficiency
- Separate hot and cold data

### Functional Partitioning
Split by feature/service.

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ User DB     │  │ Order DB    │  │ Product DB  │
│ (users,     │  │ (orders,    │  │ (products,  │
│  auth)      │  │  payments)  │  │  inventory) │
└─────────────┘  └─────────────┘  └─────────────┘
```

## Indexing

### Why Index?
Without index: Full table scan O(n)
With index: Binary search O(log n)

### Types of Indexes

| Type | Structure | Use Case |
|------|-----------|----------|
| **B-Tree** | Balanced tree | Range queries, sorting |
| **Hash** | Hash table | Exact lookups |
| **GIN** | Inverted index | Full-text search, arrays |
| **GiST** | Generalized search tree | Geospatial, ranges |
| **Composite** | Multiple columns | Multi-column queries |
| **Covering** | Includes query columns | Index-only scans |

### Index Trade-offs
- ✅ Faster reads
- ❌ Slower writes (index must be updated)
- ❌ Extra storage
- ❌ Can cause write amplification

## Real-World Database Choices

| Company | Primary DB | Why |
|---------|-----------|-----|
| **Amazon** | DynamoDB (custom) | Massive scale, eventual consistency OK |
| **Netflix** | Cassandra | Write-heavy, multi-region |
| **Uber** | MySQL + Schemaless | ACID for transactions, flexibility |
| **Twitter** | Manhattan (custom) | Low latency, high availability |
| **Instagram** | PostgreSQL | Strong consistency, rich queries |
| **Facebook** | MySQL (sharded) | Proven at scale, strong consistency |
| **LinkedIn** | Espresso (custom) | Multi-tenant, high availability |

## Interview Tips

1. **Never default to one DB** — "Let me consider the requirements..."
2. **Discuss read/write ratio** — Read-heavy → replicas; write-heavy → sharding
3. **Consider data relationships** — Relational? → SQL. Document-oriented? → NoSQL
4. **Mention specific technologies** — "PostgreSQL for transactions, Redis for caching"
5. **Discuss scaling strategy** — "We'll start with read replicas, then shard when..."
6. **Think about data model** — Schema design drives DB choice
7. **Consider operational complexity** — "Cassandra is great but requires expertise"
8. **Don't forget about backups and recovery**

## Common Mistakes

- ❌ Choosing NoSQL just because it's "cool"
- ❌ Sharding too early (adds complexity)
- ❌ Ignoring data relationships
- ❌ Not considering operational overhead
- ❌ Using wrong shard key (causes hotspots)
- ❌ Forgetting about indexes

## Cross-References

- [Scalability](./scalability.md) — Sharding and replication strategies
- [Consistency Tradeoffs](./consistency-tradeoffs.md) — CAP theorem implications
- [Caching Strategy](./caching-strategy.md) — Cache-DB consistency
- [Data Intensive](./data-intensive.md) — Data warehouses and lakes
- [Capacity Planning](./capacity-planning.md) — Storage estimation
- [DBMS Overview](../../../dbms/overview.md)
- [DBMS Normalization](../../../dbms/normalization/3nf.md)
- [Storage Distributed](../../../storage/distributed.md)
- [Key-Value Store](../kv-store.md)
