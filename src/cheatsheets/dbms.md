# DBMS Cheatsheet

## 📊 Normal Forms

```
1NF: Atomic values, no repeating groups
2NF: 1NF + No partial dependency on composite key
3NF: 2NF + No transitive dependency
BCNF: Every determinant is a candidate key
```

## 🔒 ACID Properties

| Property | Meaning | Implementation |
|----------|---------|----------------|
| Atomicity | All or nothing | WAL, undo logs |
| Consistency | Valid state transitions | Constraints, triggers |
| Isolation | Concurrent transactions don't interfere | Locks, MVCC |
| Durability | Committed data survives crashes | WAL, fsync |

## 🔀 Isolation Levels

| Level | Dirty Read | Non-Repeatable | Phantom | Performance |
|-------|-----------|----------------|---------|-------------|
| Read Uncommitted | ✅ | ✅ | ✅ | Best |
| Read Committed | ❌ | ✅ | ✅ | Good |
| Repeatable Read | ❌ | ❌ | ✅ | Moderate |
| Serializable | ❌ | ❌ | ❌ | Worst |

## 🔑 Keys

```
Primary Key: Unique, NOT NULL, one per table
Foreign Key: References primary key of another table
Candidate Key: Minimal super key (can be PK)
Super Key: Set of attributes that uniquely identifies tuple
Composite Key: Multiple columns forming a key
Surrogate Key: Artificial (auto-increment)
Natural Key: Real-world data (email, SSN)
```

## 🔗 Joins

```
INNER JOIN: Only matching rows
LEFT JOIN: All left + matching right
RIGHT JOIN: All right + matching left
FULL OUTER JOIN: All from both
CROSS JOIN: Cartesian product
SELF JOIN: Table with itself
```

## 📈 Indexing

```
B-Tree: Balanced, sorted, O(log n), good for range queries
Hash: O(1) exact match, NOT for range
Clustered: Physical order = index order, one per table
Non-Clustered: Separate structure, multiple per table

When to index:
✅ WHERE, JOIN, ORDER BY columns
✅ High cardinality
✅ Read-heavy tables

When NOT to index:
❌ Small tables
❌ Frequently updated columns
❌ Low cardinality
```

## 🗄️ SQL vs NoSQL

| Aspect | SQL | NoSQL |
|--------|-----|-------|
| Schema | Fixed | Dynamic |
| Scaling | Vertical | Horizontal |
| ACID | Full | Varies |
| Joins | Native | Avoided |
| Best For | Structured, relational | Unstructured, high-scale |

## 📐 CAP Theorem

```
C (Consistency): Every read gets latest write
A (Availability): Every request gets response
P (Partition Tolerance): Works despite network failures

Choose 2 of 3 (P is mandatory in distributed systems):
CP: Consistent but may reject requests (HBase, MongoDB)
AP: Available but may return stale data (Cassandra, DynamoDB)
```

## 🗃️ Common SQL

```sql
-- Window Functions
SELECT name, salary,
  RANK() OVER (ORDER BY salary DESC) as rank,
  AVG(salary) OVER (PARTITION BY dept) as dept_avg
FROM employees;

-- CTE
WITH active AS (
  SELECT * FROM users WHERE status = 'active'
)
SELECT * FROM active WHERE age > 25;

-- Subquery
SELECT * FROM employees
WHERE dept_id IN (SELECT id FROM departments WHERE location = 'NYC');

-- Aggregate
SELECT dept, COUNT(*), AVG(salary)
FROM employees
GROUP BY dept
HAVING AVG(salary) > 50000;
```

## 🔧 Transactions

```sql
BEGIN TRANSACTION;
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;
  UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;  -- or ROLLBACK on failure
```

## ⚡ Quick Facts

- **Denormalization**: Add redundancy for read performance
- **Sharding**: Horizontal partitioning across databases
- **Replication**: Copying data across servers (master-slave, master-master)
- **Connection pooling**: Reuse DB connections (PgBouncer, HikariCP)
- **ORM**: Maps tables to objects (SQLAlchemy, Hibernate)
- **Deadlock**: Two transactions waiting for each other's locks
- **Two-Phase Commit**: Distributed transaction protocol (prepare + commit)
- **Materialized View**: Pre-computed, stored view (faster reads)

## 🔗 Cross-References

- [DBMS Interview Questions](../interview/dbms-questions.md) — Detailed answers
- [DBMS Revision](../revision/dbms.md) — Quick summary
- [SQL Cheatsheet](./sql.md) — SQL syntax reference
- [Architecture Cheatsheet](./architecture.md) — Distributed database concepts
