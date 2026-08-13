# DBMS Interview Questions

> Comprehensive database questions with detailed answers, follow-ups, and common mistakes.

---

## Q1: What is normalization? Explain normal forms.

**Answer:**

**Normalization** is the process of organizing data to reduce redundancy and dependency.

```
┌─────────────────────────────────────────────────────────┐
│              NORMAL FORMS                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1NF (First Normal Form)                                │
│  ├── Each cell contains atomic (single) values          │
│  ├── No repeating groups or arrays                      │
│  └── Example violation: "Phone: 123, 456"               │
│                                                         │
│  2NF (Second Normal Form)                               │
│  ├── Must be in 1NF                                     │
│  ├── No partial dependency on composite key             │
│  └── Every non-key attribute depends on ENTIRE key      │
│                                                         │
│  3NF (Third Normal Form)                                │
│  ├── Must be in 2NF                                     │
│  ├── No transitive dependency                           │
│  └── Non-key → Non-key dependency removed               │
│                                                         │
│  BCNF (Boyce-Codd Normal Form)                          │
│  ├── Must be in 3NF                                     │
│  ├── Every determinant is a candidate key               │
│  └── Stricter than 3NF                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Example:**
```
Unnormalized:
  Student(StudentID, Name, Course1, Course2, Course3)

1NF (remove repeating groups):
  Student(StudentID, Name, Course)

2NF (remove partial dependency):
  Student(StudentID, Name, DeptID)
  Enrollment(StudentID, Course, Grade)

3NF (remove transitive dependency):
  Student(StudentID, Name, DeptID)
  Department(DeptID, DeptName, HOD)
  Enrollment(StudentID, Course, Grade)
```

**Follow-up questions:**
- "When is denormalization acceptable?"
- "What is the trade-off of normalization?"
- "What normal form is usually sufficient?"

**Common mistakes:**
- Memorizing definitions without understanding the "why"
- Not being able to identify violations in a schema
- Confusing 2NF and 3NF

---

## Q2: Explain ACID properties.

**Answer:**

```
┌─────────────────────────────────────────────────────────┐
│                    ACID PROPERTIES                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  A - Atomicity                                          │
│  ├── Transaction is "all or nothing"                    │
│  ├── Either all operations succeed, or none do          │
│  ├── Implementation: Write-Ahead Logging (WAL)          │
│  └── Example: Bank transfer (debit + credit together)   │
│                                                         │
│  C - Consistency                                        │
│  ├── Database moves from one valid state to another     │
│  ├── All constraints (FK, unique, check) maintained     │
│  ├── Application + DB together ensure consistency       │
│  └── Example: Balance never negative (CHECK constraint) │
│                                                         │
│  I - Isolation                                          │
│  ├── Concurrent transactions don't interfere            │
│  ├── Each transaction sees a consistent snapshot         │
│  ├── Implementation: Locks, MVCC                        │
│  └── Isolation Levels: Read Uncommitted → Serializable  │
│                                                         │
│  D - Durability                                         │
│  ├── Once committed, data survives crashes              │
│  ├── Implementation: WAL + checkpointing                │
│  └── Data written to non-volatile storage before commit │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Follow-up questions:**
- "How does the database ensure atomicity?"
- "What are isolation levels?"
- "What is the difference between consistency in ACID and CAP?"

---

## Q3: What are database isolation levels?

**Answer:**

| Isolation Level | Dirty Read | Non-Repeatable Read | Phantom Read | Performance |
|----------------|-----------|-------------------|-------------|-------------|
| Read Uncommitted | ✅ Possible | ✅ Possible | ✅ Possible | Best |
| Read Committed | ❌ Prevented | ✅ Possible | ✅ Possible | Good |
| Repeatable Read | ❌ Prevented | ❌ Prevented | ✅ Possible | Moderate |
| Serializable | ❌ Prevented | ❌ Prevented | ❌ Prevented | Worst |

```
Dirty Read:
  T1: UPDATE balance = 100 WHERE id = 1  (not committed)
  T2: SELECT balance FROM accounts WHERE id = 1  → reads 100
  T1: ROLLBACK  → balance should still be 200!
  T2 read dirty (uncommitted) data

Non-Repeatable Read:
  T1: SELECT balance FROM accounts WHERE id = 1  → 200
  T2: UPDATE balance = 300 WHERE id = 1  (commits)
  T1: SELECT balance FROM accounts WHERE id = 1  → 300
  Same query, different result!

Phantom Read:
  T1: SELECT * FROM orders WHERE amount > 100  → 5 rows
  T2: INSERT INTO orders (amount) VALUES (150)  (commits)
  T1: SELECT * FROM orders WHERE amount > 100  → 6 rows
  New phantom row appeared!
```

**Implementation:**
- **Read Uncommitted:** No locks, reads directly
- **Read Committed:** Shared lock on read, release after read
- **Repeatable Read:** Shared lock on read, hold until commit
- **Serializable:** Full isolation, range locks

**Follow-up questions:**
- "What is MVCC?"
- "Which isolation level does PostgreSQL use by default?" (Read Committed)
- "What is a snapshot isolation?"

---

## Q4: What is indexing? Explain B-Tree and Hash indexes.

**Answer:**

**Index** is a data structure that speeds up data retrieval at the cost of extra storage and write overhead.

```
B-Tree Index (most common):
                [50]
              /      \
        [20, 35]    [65, 80]
       /   |   \    /   |   \
    [10] [25] [40] [55] [70] [90]

Properties:
├── Balanced (all leaves at same depth)
├── Sorted order maintained
├── O(log n) search, insert, delete
├── Good for range queries (BETWEEN, >, <)
├── Good for prefix matching (LIKE 'abc%')
└── Used by: PostgreSQL, MySQL (InnoDB), Oracle

Hash Index:
  hash(10) → bucket 3
  hash(25) → bucket 7
  hash(50) → bucket 1

Properties:
├── O(1) exact match lookup
├── NOT good for range queries
├── NOT good for sorting
└── Used for: equality comparisons only
```

**Clustered vs Non-Clustered Index:**
```
Clustered Index:
├── Data rows stored in index order
├── Only one per table
├── Table data = index data
├── Example: Primary key in InnoDB
└── Faster for range queries

Non-Clustered Index:
├── Separate structure from data
├── Multiple per table
├── Index contains pointers to data rows
├── Example: Secondary indexes
└── Extra lookup needed (bookmark lookup)
```

**When to create an index:**
- Column used in WHERE, JOIN, ORDER BY
- High cardinality (many distinct values)
- Table is read-heavy
- NOT on: small tables, frequently updated columns, low cardinality

**Follow-up questions:**
- "What is a composite index?"
- "What is index selectivity?"
- "When should you NOT create an index?"

---

## Q5: What is the difference between SQL and NoSQL?

**Answer:**

| Aspect | SQL | NoSQL |
|--------|-----|-------|
| Data Model | Relational (tables) | Document, Key-Value, Graph, Column |
| Schema | Fixed, predefined | Dynamic, flexible |
| Scaling | Vertical (scale up) | Horizontal (scale out) |
| ACID | Full support | Varies (eventual consistency) |
| Query Language | SQL (standardized) | Varies by database |
| Joins | Native, efficient | Usually avoided (denormalized) |
| Best For | Structured data, relationships | Unstructured, high scale |

```
When to use SQL:
├── Complex relationships (JOINs)
├── ACID transactions (banking, e-commerce)
├── Structured, consistent data
├── Complex queries and reporting
└── Examples: PostgreSQL, MySQL, Oracle

When to use NoSQL:
├── Flexible/evolving schema
├── High write throughput
├── Horizontal scaling needed
├── Simple access patterns (key lookup)
└── Examples:
    ├── Document: MongoDB (CMS, user profiles)
    ├── Key-Value: Redis, DynamoDB (cache, sessions)
    ├── Column: Cassandra (time-series, IoT)
    └── Graph: Neo4j (social networks, fraud)
```

**Follow-up questions:**
- "What is eventual consistency?"
- "What is the CAP theorem?"
- "How do you handle relationships in NoSQL?"

---

## Q6: Explain the CAP theorem.

**Answer:**

**CAP Theorem:** In a distributed system, you can only guarantee **two out of three**:

```
           Consistency
              /\
          CA /  \ CP
            /    \
           /______\
          /        \
         /    AP    \
        /____________\
  Availability    Partition Tolerance

C (Consistency): Every read receives the most recent write
A (Availability): Every request receives a response
P (Partition Tolerance): System works despite network partitions

In practice, network partitions WILL happen, so you must choose:
├── CP: Consistency + Partition Tolerance
│   └── Reject requests if consistency can't be guaranteed
│       Examples: HBase, MongoDB (with write concern)
│
└── AP: Availability + Partition Tolerance
    └── Respond always, but may return stale data
        Examples: Cassandra, DynamoDB, CouchDB
```

**Follow-up questions:**
- "What is the PACELC theorem?"
- "Can you have CA in practice?"
- "How does this relate to ACID consistency?"

---

## Q7: What is a transaction? Explain with example.

**Answer:**

A **transaction** is a logical unit of work that consists of one or more SQL statements.

```sql
-- Bank Transfer Example
BEGIN TRANSACTION;
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;
  UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;

-- If any statement fails:
ROLLBACK;  -- Both statements undone
```

**Transaction States:**
```
Active → Partially Committed → Committed
    │           │
    └───────→ Failed → Aborted
```

**Follow-up questions:**
- "What is a savepoint?"
- "What is a nested transaction?"
- "How does the database handle concurrent transactions?"

---

## Q8: What are joins? Explain types.

**Answer:**

```
Tables:
  Employees:                    Departments:
  ┌────┬───────┬────┐          ┌────┬──────────┐
  │ ID │ Name  │Dept│          │ ID │ DeptName │
  ├────┼───────┼────┤          ├────┼──────────┤
  │ 1  │ Alice │ 10 │          │ 10 │ Eng      │
  │ 2  │ Bob   │ 20 │          │ 20 │ Sales    │
  │ 3  │ Carol │ 10 │          │ 40 │ HR       │
  │ 4  │ Dave  │NULL│          └────┴──────────┘
  └────┴───────┴────┘

INNER JOIN (only matching rows):
  SELECT * FROM E INNER JOIN D ON E.dept = D.id;
  ┌────┬───────┬────┬────┬──────────┐
  │ 1  │ Alice │ 10 │ 10 │ Eng      │
  │ 2  │ Bob   │ 20 │ 20 │ Sales    │
  │ 3  │ Carol │ 10 │ 10 │ Eng      │
  └────┴───────┴────┴────┴──────────┘

LEFT JOIN (all from left + matching from right):
  SELECT * FROM E LEFT JOIN D ON E.dept = D.id;
  ┌────┬───────┬──────┬──────────┐
  │ 1  │ Alice │ Eng  │          │
  │ 2  │ Bob   │ Sales│          │
  │ 3  │ Carol │ Eng  │          │
  │ 4  │ Dave  │ NULL │ NULL     │
  └────┴───────┴──────┴──────────┘

RIGHT JOIN: All from right + matching from left
FULL OUTER JOIN: All from both tables
CROSS JOIN: Cartesian product (every combination)
SELF JOIN: Table joined with itself
```

**Follow-up questions:**
- "What is the performance difference between joins?"
- "How does the query optimizer choose join order?"
- "What is a hash join vs nested loop join?"

---

## Q9: What is denormalization?

**Answer:**

**Denormalization** is the intentional introduction of redundancy to improve read performance.

```
Normalized (3NF):
  Orders(order_id, customer_id, product_id)
  Customers(customer_id, name, email)
  Products(product_id, name, price)
  -- Query requires 3 JOINs

Denormalized:
  Orders(order_id, customer_id, customer_name, customer_email,
         product_id, product_name, product_price)
  -- No JOINs needed for read
```

**When to denormalize:**
- Read-heavy workload (analytics, reporting)
- JOINs are expensive (large tables)
- Caching at application level is complex
- Acceptable to have some redundancy

**Trade-offs:**
| Aspect | Normalized | Denormalized |
|--------|-----------|--------------|
| Read speed | Slower (JOINs) | Faster (no JOINs) |
| Write speed | Faster (one place) | Slower (update multiple) |
| Storage | Less | More |
| Data integrity | Easier | Harder (redundancy) |
| Update anomaly | None | Possible |

---

## Q10: Explain query optimization.

**Answer:**

**Query Optimizer** determines the most efficient execution plan for a query.

```
Steps:
1. Parse SQL → Query Tree
2. Generate equivalent plans
3. Estimate cost of each plan
4. Choose lowest-cost plan

Example:
  SELECT * FROM orders WHERE customer_id = 123 ORDER BY order_date

Possible Plans:
  Plan A: Full table scan + sort (cost: 10000)
  Plan B: Index on customer_id + sort (cost: 100)
  Plan C: Composite index (customer_id, order_date) (cost: 50)

Optimizer chooses Plan C.
```

**EXPLAIN command:**
```sql
EXPLAIN SELECT * FROM orders WHERE customer_id = 123;

-- Shows:
-- Seq Scan on orders  (cost=0.00..350.00 rows=100)
--   Filter: (customer_id = 123)
-- vs
-- Index Scan using idx_customer on orders  (cost=0.42..8.44 rows=100)
--   Index Cond: (customer_id = 123)
```

**Optimization techniques:**
1. **Use indexes** on WHERE, JOIN, ORDER BY columns
2. **Avoid SELECT *** — select only needed columns
3. **Use EXPLAIN** to analyze query plans
4. **Avoid functions on indexed columns** (breaks index usage)
5. **Use appropriate JOIN types**
6. **Limit result sets** with LIMIT/TOP

---

## Q11-30: Quick-Fire Questions

**Q11: What is a primary key vs foreign key?**
Primary: Uniquely identifies each row, NOT NULL. Foreign: References primary key of another table, establishes relationships.

**Q12: What is a composite key?**
A key consisting of two or more columns. Example: (student_id, course_id) in enrollment table.

**Q13: What is a surrogate key vs natural key?**
Surrogate: Artificial key (auto-increment ID). Natural: Real-world data (SSN, email). Surrogate is preferred for stability.

**Q14: What is a view?**
Virtual table based on a query. Doesn't store data. Simplifies complex queries, provides security. Materialized view stores data physically.

**Q15: What is a trigger?**
Automatic procedure executed on INSERT, UPDATE, or DELETE. Used for auditing, validation, cascading changes.

**Q16: What is a stored procedure?**
Precompiled SQL code stored in the database. Reduces network traffic, provides security, reusable.

**Q17: What is a cursor?**
Pointer to a result set, allows row-by-row processing. Slower than set operations, use only when necessary.

**Q18: What is a deadlock in databases?**
Two transactions each hold a lock the other needs. Detection: wait-for graph. Prevention: timeout, ordering resources.

**Q19: What is two-phase commit?**
Protocol for distributed transactions. Phase 1: Prepare (vote). Phase 2: Commit/Abort. Ensures atomicity across databases.

**Q20: What is sharding?**
Horizontal partitioning of data across multiple databases. Shard key determines which shard stores the data.

**Q21: What is replication?**
Copying data across multiple servers. Types: Master-slave (read replicas), Master-master (multi-primary). Improves availability and read performance.

**Q22: What is connection pooling?**
Reuse database connections instead of creating new ones per request. Reduces connection overhead. Tools: PgBouncer, HikariCP.

**Q23: What is ORM?**
Object-Relational Mapping maps database tables to programming language objects. Examples: SQLAlchemy, Hibernate, Django ORM.

**Q24: What is the difference between DELETE, TRUNCATE, and DROP?**
DELETE: Removes rows, logged, can rollback. TRUNCATE: Removes all rows, minimally logged, faster. DROP: Removes entire table structure.

**Q25: What is a CTE (Common Table Expression)?**
Temporary named result set defined with WITH clause. Improves readability, enables recursion.

```sql
WITH active_users AS (
  SELECT * FROM users WHERE status = 'active'
)
SELECT * FROM active_users WHERE age > 25;
```

**Q26: What is a window function?**
Performs calculation across rows related to current row. Unlike GROUP BY, doesn't collapse rows.

```sql
SELECT name, salary,
  RANK() OVER (ORDER BY salary DESC) as rank,
  AVG(salary) OVER (PARTITION BY dept) as dept_avg
FROM employees;
```

**Q27: What is connection timeout vs query timeout?**
Connection: Max time to establish connection to DB. Query: Max time for a query to execute.

**Q28: What is database migration?**
Version-controlled changes to database schema. Tools: Flyway, Alembic, Django migrations. Enables reproducible schema evolution.

**Q29: What is the difference between clustered and non-clustered index?**
Clustered: Physical order = index order, one per table. Non-clustered: Separate structure, multiple per table, contains pointers.

**Q30: What is a database transaction log?**
Sequential record of all database modifications. Enables: recovery after crash, replication, point-in-time recovery.

## 🔗 Cross-References

- [DBMS Cheatsheet](../cheatsheets/dbms.md) — Quick reference for all DBMS concepts
- [DBMS Revision](../revision/dbms.md) — Quick summary before interviews
- [SQL Cheatsheet](../cheatsheets/sql.md) — SQL syntax reference
- [System Design](./system-design/kv-store.md) — Database design at scale
- [OS Questions](./os-questions.md) — Concurrency concepts (similar to DB concurrency)
