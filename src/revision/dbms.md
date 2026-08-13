# DBMS - Quick Revision

> 📌 Last-minute revision before interviews. Scan these points quickly.

---

## Normalization

- **1NF**: Atomic values, no repeating groups
- **2NF**: 1NF + no partial dependency on composite key
- **3NF**: 2NF + no transitive dependency
- **BCNF**: Every determinant is a candidate key
- **Denormalization**: Add redundancy for read performance

## ACID

- **Atomicity**: All or nothing (WAL, undo logs)
- **Consistency**: Valid state transitions (constraints)
- **Isolation**: Concurrent transactions don't interfere (locks, MVCC)
- **Durability**: Committed data survives crashes (WAL, fsync)

## Isolation Levels

- **Read Uncommitted**: Dirty reads possible
- **Read Committed**: No dirty reads, non-repeatable possible
- **Repeatable Read**: No non-repeatable reads, phantom possible
- **Serializable**: Full isolation, worst performance

## Keys

- **Primary**: Unique, NOT NULL
- **Foreign**: References another table's PK
- **Candidate**: Minimal super key
- **Composite**: Multiple columns
- **Surrogate**: Artificial (auto-increment)

## Indexing

- **B-Tree**: Balanced, sorted, O(log n), range queries
- **Hash**: O(1) exact match, no range queries
- **Clustered**: Physical order = index order, one per table
- **Non-clustered**: Separate structure, multiple per table
- **When to index**: WHERE, JOIN, ORDER BY columns, high cardinality

## Joins

- **Inner**: Only matching rows
- **Left**: All left + matching right
- **Right**: All right + matching left
- **Full Outer**: All from both
- **Cross**: Cartesian product

## SQL vs NoSQL

- **SQL**: Fixed schema, ACID, joins, vertical scaling
- **NoSQL**: Flexible schema, eventual consistency, horizontal scaling
- **Document** (MongoDB): Flexible, hierarchical
- **Key-Value** (Redis): Simple lookups, caching
- **Column** (Cassandra): Time-series, write-heavy
- **Graph** (Neo4j): Relationships

## CAP Theorem

- **C**onsistency: Every read gets latest write
- **A**vailability: Every request gets response
- **P**artition Tolerance: Works despite network failures
- **CP**: Consistent, may reject (HBase, MongoDB)
- **AP**: Available, may be stale (Cassandra, DynamoDB)

## Transactions

```sql
BEGIN TRANSACTION;
  -- operations
COMMIT; -- or ROLLBACK
```

- **Deadlock**: Two transactions waiting for each other
- **Two-Phase Commit**: Distributed transaction protocol

## SQL Essentials

```sql
-- Window functions
RANK() OVER (PARTITION BY dept ORDER BY salary DESC)
ROW_NUMBER() OVER (ORDER BY date)
LAG(col, 1) OVER (ORDER BY date)
SUM(col) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)

-- CTE
WITH cte_name AS (SELECT ...) SELECT * FROM cte_name;

-- Recursive CTE
WITH RECURSIVE cte AS (
  SELECT ... WHERE base_condition
  UNION ALL
  SELECT ... JOIN cte ON ...
)
```

## Key Concepts

- **Sharding**: Horizontal partitioning across databases
- **Replication**: Copying data across servers (master-slave, master-master)
- **Connection pooling**: Reuse DB connections
- **ORM**: Maps tables to objects
- **Materialized view**: Pre-computed, stored view
- **Cursor**: Row-by-row processing (slow, avoid when possible)
- **Trigger**: Auto-executes on INSERT/UPDATE/DELETE
- **Stored procedure**: Precompiled SQL in DB

## 🔗 Cross-References

- [DBMS Cheatsheet](../cheatsheets/dbms.md) — Detailed reference
- [SQL Cheatsheet](../cheatsheets/sql.md) — SQL syntax
- [DBMS Interview Questions](../interview/dbms-questions.md) — Full Q&A
