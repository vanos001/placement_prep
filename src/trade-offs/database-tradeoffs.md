# Database Trade-offs

Database selection is one of the highest-leverage decisions in system design. The wrong choice creates technical debt that compounds over years. This guide covers the key comparisons, when to choose each side, and how to discuss them in interviews.

## Master Comparison Table

| Comparison | Choose A When | Choose B When | Key Trade-off |
|-----------|--------------|--------------|---------------|
| SQL vs NoSQL | Structured data, complex queries, ACID needed | Flexible schema, horizontal scale, high write throughput | Consistency/complexity vs. flexibility/scale |
| PostgreSQL vs MySQL | Complex queries, extensions, JSONB, geospatial | Simple CRUD, read-heavy, wide tooling ecosystem | Feature richness vs. simplicity/speed |
| Redis vs Memcached | Data structures, persistence, pub/sub needed | Simple string caching, maximum memory efficiency | Feature set vs. raw memory efficiency |
| Relational vs Document | Strong relationships, referential integrity | Nested/hierarchical data, schema evolution | Query power vs. schema flexibility |
| Normalized vs Denormalized | Write-heavy, data integrity critical | Read-heavy, query performance critical | Write efficiency vs. read performance |
| SQL Joins vs App Joins | Few tables, complex relationships | Many tables, simple lookups, scale-out needed | Database power vs. application flexibility |
| Strong vs Eventual Consistency | Financial, inventory, coordination | Social feeds, recommendations, caching | Correctness vs. availability/latency |
| Cache-aside vs Write-through | Read-heavy, tolerance for stale data | Write-heavy, need immediate consistency | Read performance vs. write latency |

---

## SQL vs NoSQL

### When to Choose SQL
- Your data model is well-understood and relational (users, orders, accounts).
- You need ACID transactions across multiple tables.
- Complex ad-hoc queries and reporting are requirements.
- Your team has deep SQL expertise.

### When to Choose NoSQL
- Your schema is evolving rapidly or varies per document/row.
- You need horizontal scaling beyond what a single SQL node can provide.
- Your access patterns are simple key-value or document lookups.
- You need extremely high write throughput with relaxed consistency.

### Key Trade-offs
| Dimension | SQL | NoSQL |
|-----------|-----|-------|
| Schema | Fixed, enforced | Flexible or schemaless |
| Scaling | Primarily vertical | Horizontal by design |
| Transactions | Full ACID across tables | Varies (document-level in MongoDB, none in Cassandra) |
| Querying | Rich SQL, joins, aggregations | Limited per database type |
| Consistency | Strong by default | Often eventual |
| Maturity | Decades of tooling, expertise | Younger ecosystem, less battle-tested patterns |

### Interview Tip
Never say "use NoSQL for big data." Be specific: "Cassandra for time-series writes with tunable consistency" or "MongoDB for user profiles with flexible metadata fields."

---

## PostgreSQL vs MySQL

### When to Choose PostgreSQL
- You need advanced data types (JSONB, arrays, hstore, UUID, network addresses).
- Complex analytical queries with window functions and CTEs.
- Geospatial queries via PostGIS.
- Extensibility: custom types, functions, operators, index methods.

### When to Choose MySQL
- Your workload is predominantly simple CRUD operations.
- Read-heavy workloads benefit from MySQL's query cache (historically) and InnoDB optimizations.
- Your team or org has established MySQL expertise and tooling.
- You need the broadest community support and managed offerings.

### Key Trade-offs
| Dimension | PostgreSQL | MySQL |
|-----------|-----------|-------|
| SQL Standard Compliance | Excellent | Partial |
| JSON Support | JSONB with indexing | JSON (less capable indexing) |
| Replication | Logical and physical | Primarily binary log |
| Extensibility | Very high (extensions, custom types) | Limited |
| Write Performance | Slightly lower (MVCC overhead) | Slightly higher for simple writes |
| Full-Text Search | Built-in, good | Built-in, adequate |

---

## Redis vs Memcached

### When to Choose Redis
- You need data structures: sorted sets, hashes, lists, streams.
- Persistence matters (RDB snapshots or AOF logging).
- Pub/sub or Lua scripting is required.
- You need atomic operations on complex data.

### When to Choose Memcached
- You are caching simple serialized strings/blobs.
- You want maximum memory efficiency (slab allocation).
- Multi-threaded performance matters more than features.
- You have no need for persistence or data structures.

### Key Trade-offs
| Dimension | Redis | Memcached |
|-----------|-------|-----------|
| Data Types | Strings, lists, sets, sorted sets, hashes, streams, bitmaps | Strings only |
| Persistence | RDB, AOF | None |
| Threading | Single-threaded (6.0+ I/O threads) | Multi-threaded |
| Memory Efficiency | Lower (overhead per object) | Higher (slab allocator) |
| Max Value Size | 512 MB | 1 MB |
| Cluster Mode | Redis Cluster, Sentinel | Client-side sharding |

---

## Relational vs Document Databases

### When to Choose Relational
- Data has many inter-entity relationships (orders → line items → products).
- Referential integrity is non-negotiable.
- You need to query across relationships efficiently.
- Reporting and BI are primary use cases.

### When to Choose Document
- Your data is naturally hierarchical (a product catalog with nested variants).
- Your schema varies between documents (articles with different metadata).
- You access data primarily by a single key (user ID, order ID).
- You need fast iterative schema changes without migrations.

### Interview Tip
Discuss "polymorphic" data: if a `messages` table has columns for email, SMS, and push notifications with 80% null columns, that is a sign document storage may be more appropriate.

---

## Normalized vs Denormalized

### When to Normalize
- Write-heavy workloads where update anomalies are costly.
- Data integrity is paramount (financial systems, inventory).
- Storage is expensive relative to compute.

### When to Denormalize
- Read-heavy workloads where query latency is the bottleneck.
- The data changes infrequently relative to reads (product catalogs).
- You can tolerate eventual consistency for some derived data.

### Practical Approach
Most production systems use a hybrid: normalized source of truth with denormalized read models (materialized views, CQRS read side, application-level caches).

---

## SQL Joins vs Application Joins

### When to Use SQL Joins
- Tables are on the same server and reasonably sized.
- The join logic is complex (multi-table, conditional joins).
- The database optimizer can produce a better plan than you.
- You need ACID guarantees across the joined data.

### When to Use Application Joins
- Data is sharded across different database instances.
- Each join leg is a simple primary key lookup.
- You need to call out to caches or external services mid-join.
- You want to parallelize independent lookups.

### Key Trade-off
SQL joins are declarative (the optimizer decides the strategy) but limit scaling. Application joins are imperative (you control the strategy) but shift complexity to application code.

---

## Strong vs Eventual Consistency

### When to Choose Strong Consistency
- Financial transactions, inventory counts, access control.
- Any domain where reading stale data causes incorrect actions.
- Systems with low write volume where the cost of consensus is acceptable.

### When to Choose Eventual Consistency
- Social media feeds, recommendation systems, analytics dashboards.
- Systems requiring high availability across geographically distributed nodes.
- Where read latency is critical and temporary inconsistency is acceptable.

### Key Trade-offs (from CAP theorem)
| Consistency Level | Availability | Latency | Complexity |
|-------------------|-------------|---------|-----------|
| Strong | Lower (consensus required) | Higher (round-trips) | Lower (simpler reasoning) |
| Eventual | Higher | Lower | Higher (conflict resolution, reconciliation) |

---

## Caching Strategies

### Cache-Aside (Lazy Loading)
Application checks cache first; on miss, loads from DB and populates cache.

**Choose when:** Read-heavy, cache misses are acceptable, data is relatively static.

### Write-Through
Application writes to cache and DB simultaneously.

**Choose when:** Write-heavy workloads where you cannot tolerate stale reads, strong consistency needed.

### Write-Back (Write-Behind)
Application writes to cache only; cache asynchronously flushes to DB.

**Choose when:** Write bursts, where write latency to the primary store is the bottleneck. Risk: data loss on cache failure before flush.

### Comparison

| Strategy | Read Latency | Write Latency | Consistency | Data Loss Risk |
|----------|-------------|--------------|------------|----------------|
| Cache-aside | Low (hit) / High (miss) | Low (no cache write) | Eventually consistent | None |
| Write-through | Low (hit) / High (miss) | High (dual write) | Strong | None |
| Write-back | Low (always hit) | Low (async) | Weak | Yes |

---

## Interview Questions

1. **"Design a notification system. Should you use SQL or NoSQL for storing notification preferences?"**
   Discuss the polymorphic nature of preferences (per-channel settings, per-user overrides) and the read-heavy access pattern.

2. **"When would you denormalize a database, and what problems does it introduce?"**
   Cover update anomalies, the need for background sync jobs, and the CQRS pattern as a structured approach.

3. **"You have a read-heavy e-commerce product catalog. How would you design the data layer?"**
   Discuss normalized source of truth + denormalized read replicas, cache-aside for hot products, and eventual consistency for price updates.

4. **"Compare Redis and Memcached for a session store."**
   Redis wins due to persistence, TTL support on individual keys, and data structures (hashes for session fields). Memcached's lack of persistence is a deal-breaker for sessions.

5. **"When is MySQL the wrong choice for a new project?"**
   When you need JSONB with indexing, geospatial queries, complex analytical queries, or advanced concurrency control (MVCC with row-level locking in complex scenarios).
