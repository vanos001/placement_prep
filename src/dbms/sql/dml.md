# DML — Data Manipulation Language

## Overview

**DML (Data Manipulation Language)** consists of SQL commands that query and modify data stored in database tables. Unlike DDL (which changes structure), DML operates on the *data* itself. The four core DML commands are `SELECT`, `INSERT`, `UPDATE`, and `DELETE`.

## SELECT — Querying Data

### Basic Syntax

```sql
SELECT [DISTINCT | ALL] column_list
FROM table_source
[JOIN ... ON ...]
[WHERE filter_condition]
[GROUP BY grouping_columns]
[HAVING group_filter]
[ORDER BY sort_columns [ASC|DESC]]
[LIMIT count [OFFSET offset]];
```

### Column Selection

```sql
-- All columns
SELECT * FROM Employees;

-- Specific columns
SELECT first_name, last_name, salary FROM Employees;

-- Column aliases
SELECT first_name AS "First Name", salary * 12 AS annual_salary FROM Employees;

-- Computed columns
SELECT first_name, salary, salary * 0.1 AS bonus, salary * 1.1 AS total FROM Employees;

-- Concatenation
SELECT first_name || ' ' || last_name AS full_name FROM Employees;  -- PostgreSQL
SELECT CONCAT(first_name, ' ', last_name) AS full_name FROM Employees;  -- MySQL

-- DISTINCT
SELECT DISTINCT department FROM Employees;
SELECT DISTINCT department, job_title FROM Employees;  -- Combination uniqueness
```

### WHERE Clause

```sql
-- Comparison operators
SELECT * FROM Employees WHERE salary > 50000;
SELECT * FROM Employees WHERE department = 'Engineering';
SELECT * FROM Employees WHERE hire_date >= '2023-01-01';

-- Logical operators
SELECT * FROM Employees WHERE salary > 50000 AND department = 'Engineering';
SELECT * FROM Employees WHERE department = 'Engineering' OR department = 'Science';
SELECT * FROM Employees WHERE NOT department = 'HR';

-- BETWEEN (inclusive)
SELECT * FROM Employees WHERE salary BETWEEN 50000 AND 100000;
SELECT * FROM Employees WHERE hire_date BETWEEN '2023-01-01' AND '2023-12-31';

-- IN / NOT IN
SELECT * FROM Employees WHERE department IN ('Engineering', 'Science', 'Math');
SELECT * FROM Employees WHERE dept_id NOT IN (SELECT dept_id FROM Departments WHERE location = 'NYC');

-- LIKE (pattern matching)
SELECT * FROM Employees WHERE last_name LIKE 'Sm%';      -- Starts with 'Sm'
SELECT * FROM Employees WHERE email LIKE '%@gmail.com';   -- Ends with '@gmail.com'
SELECT * FROM Employees WHERE name LIKE 'J_hn';           -- Exactly 4 chars, _ = any single char
SELECT * FROM Employees WHERE name LIKE '%\%%' ESCAPE '\'; -- Literal %

-- IS NULL / IS NOT NULL
SELECT * FROM Employees WHERE manager_id IS NULL;
SELECT * FROM Employees WHERE bonus IS NOT NULL;

-- EXISTS
SELECT * FROM Employees E WHERE EXISTS (
    SELECT 1 FROM Departments D WHERE D.dept_id = E.dept_id AND D.location = 'NYC'
);

-- ANY / ALL
SELECT * FROM Employees WHERE salary > ALL (SELECT salary FROM Employees WHERE dept_id = 10);
SELECT * FROM Employees WHERE salary > ANY (SELECT salary FROM Employees WHERE dept_id = 10);
```

### ORDER BY

```sql
-- Single column
SELECT * FROM Employees ORDER BY salary DESC;

-- Multiple columns
SELECT * FROM Employees ORDER BY department ASC, salary DESC;

-- By column position
SELECT first_name, salary FROM Employees ORDER BY 2 DESC;  -- salary is 2nd column

-- By expression
SELECT first_name, salary FROM Employees ORDER BY salary * 0.1 DESC;

-- NULL ordering (database-specific)
SELECT * FROM Employees ORDER BY bonus NULLS LAST;   -- PostgreSQL
SELECT * FROM Employees ORDER BY IF(bonus IS NULL, 1, 0), bonus;  -- MySQL workaround
```

### LIMIT / OFFSET (Pagination)

```sql
-- PostgreSQL / MySQL
SELECT * FROM Employees ORDER BY salary DESC LIMIT 10;
SELECT * FROM Employees ORDER BY salary DESC LIMIT 10 OFFSET 20;

-- SQL Server
SELECT TOP 10 * FROM Employees ORDER BY salary DESC;
SELECT * FROM Employees ORDER BY salary DESC OFFSET 20 ROWS FETCH NEXT 10 ROWS ONLY;

-- Oracle
SELECT * FROM Employees WHERE ROWNUM <= 10 ORDER BY salary DESC;
SELECT * FROM Employees ORDER BY salary DESC OFFSET 20 ROWS FETCH NEXT 10 ROWS ONLY;  -- 12c+
```

## INSERT — Adding Data

### Basic INSERT

```sql
-- Single row
INSERT INTO Employees (first_name, last_name, email, salary, dept_id)
VALUES ('Alice', 'Smith', 'alice@co.com', 75000, 10);

-- Multiple rows
INSERT INTO Employees (first_name, last_name, email, salary, dept_id) VALUES
('Bob', 'Jones', 'bob@co.com', 80000, 20),
('Carol', 'Davis', 'carol@co.com', 72000, 10),
('Dave', 'Wilson', 'dave@co.com', 68000, 30);

-- Insert with default values
INSERT INTO Employees (first_name, last_name, email) VALUES ('Eve', 'Brown', 'eve@co.com');
-- salary and hire_date use DEFAULT
```

### INSERT with SELECT

```sql
-- Copy data from another table
INSERT INTO EmployeeBackup (emp_id, first_name, last_name, salary)
SELECT emp_id, first_name, last_name, salary
FROM Employees
WHERE hire_date < '2023-01-01';

-- Insert from a query
INSERT INTO DeptSummary (dept_id, avg_salary)
SELECT dept_id, AVG(salary)
FROM Employees
GROUP BY dept_id;
```

### INSERT with ON CONFLICT / ON DUPLICATE KEY

```sql
-- PostgreSQL: UPSERT
INSERT INTO Employees (emp_id, first_name, last_name, email, salary)
VALUES (101, 'Alice', 'Smith', 'alice@co.com', 75000)
ON CONFLICT (emp_id)
DO UPDATE SET salary = EXCLUDED.salary, email = EXCLUDED.email;

-- PostgreSQL: Do nothing on conflict
INSERT INTO Employees (email, first_name, last_name)
VALUES ('alice@co.com', 'Alice', 'Smith')
ON CONFLICT (email) DO NOTHING;

-- MySQL: UPSERT
INSERT INTO Employees (emp_id, first_name, email, salary)
VALUES (101, 'Alice', 'alice@co.com', 75000)
ON DUPLICATE KEY UPDATE salary = VALUES(salary), email = VALUES(email);

-- SQL Server: MERGE
MERGE INTO Employees AS target
USING (VALUES (101, 'Alice', 'alice@co.com', 75000)) AS source (emp_id, name, email, salary)
ON target.emp_id = source.emp_id
WHEN MATCHED THEN UPDATE SET salary = source.salary
WHEN NOT MATCHED THEN INSERT (emp_id, name, email, salary)
    VALUES (source.emp_id, source.name, source.email, source.salary);
```

### INSERT … RETURNING

```sql
-- PostgreSQL: Return inserted data
INSERT INTO Employees (first_name, last_name, email, salary)
VALUES ('Alice', 'Smith', 'alice@co.com', 75000)
RETURNING emp_id, first_name, salary;

-- Get the generated ID
INSERT INTO Employees (first_name, last_name, email)
VALUES ('Bob', 'Jones', 'bob@co.com')
RETURNING emp_id INTO @new_emp_id;  -- MySQL (stored procedure)
```

## UPDATE — Modifying Data

### Basic UPDATE

```sql
-- Update specific rows
UPDATE Employees SET salary = 80000 WHERE emp_id = 101;

-- Update multiple columns
UPDATE Employees
SET salary = 80000, department = 'Senior Engineering'
WHERE emp_id = 101;

-- Update with expression
UPDATE Employees SET salary = salary * 1.10 WHERE dept_id = 10;

-- Update with subquery
UPDATE Employees
SET salary = (SELECT AVG(salary) FROM Employees)
WHERE emp_id = 101;
```

### UPDATE with JOIN (Multi-table UPDATE)

```sql
-- MySQL: Update based on another table
UPDATE Employees E
JOIN Departments D ON E.dept_id = D.dept_id
SET E.salary = E.salary * 1.10
WHERE D.location = 'NYC';

-- PostgreSQL: UPDATE with FROM
UPDATE Employees E
SET salary = salary * 1.10
FROM Departments D
WHERE E.dept_id = D.dept_id AND D.location = 'NYC';

-- SQL Server: UPDATE with JOIN
UPDATE E
SET E.salary = E.salary * 1.10
FROM Employees E
JOIN Departments D ON E.dept_id = D.dept_id
WHERE D.location = 'NYC';
```

### UPDATE with CASE

```sql
UPDATE Employees
SET salary = CASE
    WHEN performance = 'Excellent' THEN salary * 1.15
    WHEN performance = 'Good' THEN salary * 1.10
    WHEN performance = 'Average' THEN salary * 1.05
    ELSE salary
END
WHERE review_date = '2024-01-01';
```

### UPDATE … RETURNING

```sql
-- PostgreSQL
UPDATE Employees
SET salary = salary * 1.10
WHERE dept_id = 10
RETURNING emp_id, first_name, salary AS new_salary;
```

## DELETE — Removing Data

### Basic DELETE

```sql
-- Delete specific rows
DELETE FROM Employees WHERE emp_id = 101;

-- Delete with condition
DELETE FROM Employees WHERE hire_date < '2020-01-01' AND performance = 'Poor';

-- Delete all rows (but keep table structure)
DELETE FROM Employees;

-- Delete with subquery
DELETE FROM Employees
WHERE dept_id IN (SELECT dept_id FROM Departments WHERE is_closed = true);
```

### DELETE with JOIN

```sql
-- MySQL: Delete based on another table
DELETE E FROM Employees E
JOIN Departments D ON E.dept_id = D.dept_id
WHERE D.is_closed = true;

-- PostgreSQL: Delete with USING
DELETE FROM Employees E
USING Departments D
WHERE E.dept_id = D.dept_id AND D.is_closed = true;

-- SQL Server
DELETE E
FROM Employees E
JOIN Departments D ON E.dept_id = D.dept_id
WHERE D.is_closed = true;
```

### DELETE … RETURNING

```sql
-- PostgreSQL
DELETE FROM Employees
WHERE hire_date < '2020-01-01'
RETURNING emp_id, first_name, last_name;
```

## MERGE / UPSERT

```sql
-- SQL Server / Oracle MERGE
MERGE INTO TargetTable AS T
USING SourceTable AS S
ON T.id = S.id
WHEN MATCHED AND S.is_delete = 1 THEN
    DELETE
WHEN MATCHED THEN
    UPDATE SET T.value = S.value, T.updated_at = GETDATE()
WHEN NOT MATCHED THEN
    INSERT (id, value, created_at) VALUES (S.id, S.value, GETDATE());
```

## Interview Questions

### Beginner

**Q1: What is the difference between DELETE and DROP?**
A: DELETE is DML — removes specific rows, can be rolled back, keeps table structure. DROP is DDL — removes the entire table (structure + data), auto-committed in most databases.

**Q2: Can you use ORDER BY in a subquery?**
A: It depends on the context. In a subquery used with IN/EXISTS, ORDER BY is meaningless (sets have no order). In a subquery used with LIMIT/TOP, ORDER BY is necessary and meaningful. In derived tables (FROM clause), ORDER BY is not guaranteed unless LIMIT is also present.

**Q3: What happens if you INSERT a row that violates a constraint?**
A: The INSERT fails with an error, and the row is not added. If inside a transaction, you can rollback. If auto-committed, the operation simply fails.

### Intermediate

**Q4: Explain the difference between WHERE and HAVING with an example.**
A:
```sql
-- WHERE filters rows BEFORE grouping
SELECT department, COUNT(*) AS cnt
FROM Employees
WHERE salary > 50000        -- Filter individual rows first
GROUP BY department;

-- HAVING filters groups AFTER grouping
SELECT department, COUNT(*) AS cnt
FROM Employees
GROUP BY department
HAVING COUNT(*) > 5;        -- Filter groups

-- Combined
SELECT department, AVG(salary) AS avg_sal
FROM Employees
WHERE hire_date > '2020-01-01'  -- Filter rows
GROUP BY department
HAVING AVG(salary) > 70000;     -- Filter groups
```

**Q5: How does ON CONFLICT work in PostgreSQL?**
A: It handles unique constraint violations during INSERT. `ON CONFLICT (columns) DO UPDATE SET ...` updates the conflicting row (UPSERT). `ON CONFLICT (columns) DO NOTHING` silently skips the conflicting row. The `EXCLUDED` pseudo-table refers to the row that was proposed for insertion.

**Q6: Write a query to delete duplicate rows keeping only the one with the lowest ID.**
A:
```sql
-- PostgreSQL
DELETE FROM Employees E1
WHERE EXISTS (
    SELECT 1 FROM Employees E2
    WHERE E2.email = E1.email AND E2.emp_id < E1.emp_id
);

-- MySQL (can't directly reference the table being deleted)
DELETE E1 FROM Employees E1
INNER JOIN Employees E2
ON E1.email = E2.email AND E1.emp_id > E2.emp_id;
```

### Advanced / FAANG-Level

**Q7: You need to bulk-insert 10M rows into a production table without locking it for minutes. How?**
A: Strategy:
1. **Disable indexes** temporarily (or use `COPY` which is faster than INSERT)
2. **Batch the insert**: Insert in chunks of 10K-50K rows per transaction
3. **Use COPY/BULK INSERT**: PostgreSQL `COPY`, MySQL `LOAD DATA INFILE`, SQL Server `BULK INSERT`
4. **Minimize logging**: Use `UNLOGGED` tables (PostgreSQL) or `BULK_LOGGED` recovery model (SQL Server)
5. **Use INSERT with minimal indexes**: Add indexes after bulk load
6. **Partition**: If table is partitioned, load into a new partition and attach it

```sql
-- PostgreSQL: COPY (fastest)
COPY Employees FROM '/data/employees.csv' WITH (FORMAT csv, HEADER true);

-- MySQL: LOAD DATA
LOAD DATA INFILE '/data/employees.csv' INTO TABLE Employees
FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;
```

**Q8: Implement a soft-delete pattern with automatic filtering.**
A:
```sql
-- Add soft-delete column
ALTER TABLE Employees ADD COLUMN deleted_at TIMESTAMP NULL;

-- Create a view for active records
CREATE VIEW ActiveEmployees AS
SELECT * FROM Employees WHERE deleted_at IS NULL;

-- Soft delete function
CREATE OR REPLACE FUNCTION soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE Employees SET deleted_at = NOW() WHERE emp_id = OLD.emp_id;
    RETURN NULL;  -- Cancel the actual DELETE
END;
$$ LANGUAGE plpgsql;

-- Trigger on DELETE attempts
CREATE TRIGGER trg_soft_delete
BEFORE DELETE ON Employees
FOR EACH ROW EXECUTE FUNCTION soft_delete();

-- To permanently delete (admin only):
DELETE FROM Employees WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '1 year';
```

## Common Mistakes

- Forgetting WHERE clause in UPDATE/DELETE (affects ALL rows)
- Using `=` for NULL in WHERE (`salary = NULL` returns nothing; use `IS NULL`)
- Not wrapping multi-statement DML in transactions
- INSERT with column list mismatch (wrong number of values)
- Using ORDER BY in subqueries without LIMIT (pointless in most cases)
- Not considering ON CONFLICT/UPSERT for idempotent operations

## Summary

| Command | Purpose | Affects | Rollback |
|---|---|---|---|
| SELECT | Query data | Nothing (read-only) | N/A |
| INSERT | Add rows | New rows | Yes |
| UPDATE | Modify rows | Existing rows | Yes |
| DELETE | Remove rows | Existing rows | Yes |
| MERGE | Insert or update | Based on condition | Yes |

## Cross-References

- [DDL](ddl.md) — Schema definition commands
- [Joins](joins.md) — Combining data from multiple tables
- [Subqueries](subqueries.md) — Nested queries in DML
- [Window Functions](window-functions.md) — Advanced SELECT analytics
- [CTEs](ctes.md) — Readable complex queries
- [Transactions](../transactions/README.md) — Wrapping DML in transactions


## Cross References

- [DDL](ddl.md)
- [SQL Joins](joins.md)
- [Subqueries](subqueries.md)
- [Query Processing](../query-processing/README.md)
