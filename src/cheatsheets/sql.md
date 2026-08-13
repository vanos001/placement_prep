# SQL Cheatsheet

## 📝 Basic Queries

```sql
-- Select
SELECT column1, column2 FROM table_name;
SELECT * FROM table_name;
SELECT DISTINCT column1 FROM table_name;
SELECT column1 AS alias_name FROM table_name;

-- Where
SELECT * FROM users WHERE age > 25;
SELECT * FROM users WHERE age BETWEEN 20 AND 30;
SELECT * FROM users WHERE city IN ('NYC', 'LA', 'SF');
SELECT * FROM users WHERE name LIKE 'J%';        -- starts with J
SELECT * FROM users WHERE name LIKE '%son';       -- ends with son
SELECT * FROM users WHERE name LIKE '%mit%';      -- contains mit
SELECT * FROM users WHERE email IS NOT NULL;

-- Order By
SELECT * FROM users ORDER BY age DESC;
SELECT * FROM users ORDER BY city ASC, age DESC;

-- Limit
SELECT * FROM users LIMIT 10;
SELECT * FROM users LIMIT 10 OFFSET 20;  -- skip 20, return 10
```

## 🔢 Aggregate Functions

```sql
SELECT COUNT(*) FROM users;
SELECT COUNT(DISTINCT city) FROM users;
SELECT AVG(salary) FROM employees;
SELECT SUM(amount) FROM orders;
SELECT MIN(salary), MAX(salary) FROM employees;

-- Group By
SELECT city, COUNT(*) as user_count
FROM users
GROUP BY city;

-- Having (filter after grouping)
SELECT city, AVG(age) as avg_age
FROM users
GROUP BY city
HAVING AVG(age) > 25;

-- Order of clauses:
SELECT → FROM → WHERE → GROUP BY → HAVING → ORDER BY → LIMIT
```

## 🔗 Joins

```sql
-- Inner Join (only matching)
SELECT e.name, d.dept_name
FROM employees e
INNER JOIN departments d ON e.dept_id = d.id;

-- Left Join (all left + matching right)
SELECT e.name, d.dept_name
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.id;

-- Right Join (all right + matching left)
SELECT e.name, d.dept_name
FROM employees e
RIGHT JOIN departments d ON e.dept_id = d.id;

-- Full Outer Join (all from both)
SELECT e.name, d.dept_name
FROM employees e
FULL OUTER JOIN departments d ON e.dept_id = d.id;

-- Self Join
SELECT e1.name as employee, e2.name as manager
FROM employees e1
JOIN employees e2 ON e1.manager_id = e2.id;

-- Cross Join (cartesian product)
SELECT * FROM sizes CROSS JOIN colors;
```

## 📊 Subqueries

```sql
-- In WHERE
SELECT * FROM employees
WHERE dept_id IN (SELECT id FROM departments WHERE location = 'NYC');

-- In FROM
SELECT dept, avg_salary FROM (
  SELECT dept_id as dept, AVG(salary) as avg_salary
  FROM employees GROUP BY dept_id
) dept_salaries
WHERE avg_salary > 50000;

-- Correlated Subquery
SELECT * FROM employees e1
WHERE salary > (
  SELECT AVG(salary) FROM employees e2
  WHERE e1.dept_id = e2.dept_id
);

-- EXISTS
SELECT * FROM departments d
WHERE EXISTS (
  SELECT 1 FROM employees e WHERE e.dept_id = d.id
);
```

## 🪟 Window Functions

```sql
-- ROW_NUMBER: Unique sequential number
SELECT name, salary,
  ROW_NUMBER() OVER (ORDER BY salary DESC) as row_num
FROM employees;

-- RANK: Same rank for ties, gaps
SELECT name, salary,
  RANK() OVER (ORDER BY salary DESC) as rank
FROM employees;

-- DENSE_RANK: Same rank for ties, no gaps
SELECT name, salary,
  DENSE_RANK() OVER (ORDER BY salary DESC) as dense_rank
FROM employees;

-- Partition By: Ranking within groups
SELECT name, dept, salary,
  RANK() OVER (PARTITION BY dept ORDER BY salary DESC) as dept_rank
FROM employees;

-- Running Total
SELECT date, amount,
  SUM(amount) OVER (ORDER BY date) as running_total
FROM transactions;

-- Moving Average
SELECT date, amount,
  AVG(amount) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as ma_7
FROM transactions;

-- Lead/Lag
SELECT date, amount,
  LAG(amount, 1) OVER (ORDER BY date) as prev_amount,
  LEAD(amount, 1) OVER (ORDER BY date) as next_amount
FROM transactions;

-- NTILE: Divide into buckets
SELECT name, salary,
  NTILE(4) OVER (ORDER BY salary DESC) as quartile
FROM employees;
```

## 📝 DDL (Data Definition)

```sql
-- Create Table
CREATE TABLE employees (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255) UNIQUE,
  salary DECIMAL(10, 2) DEFAULT 0,
  dept_id INT,
  hire_date DATE,
  FOREIGN KEY (dept_id) REFERENCES departments(id)
);

-- Alter Table
ALTER TABLE employees ADD COLUMN phone VARCHAR(20);
ALTER TABLE employees MODIFY COLUMN name VARCHAR(200);
ALTER TABLE employees DROP COLUMN phone;
ALTER TABLE employees ADD INDEX idx_email (email);

-- Drop Table
DROP TABLE IF EXISTS employees;
TRUNCATE TABLE employees;  -- Delete all rows, keep structure
```

## ✏️ DML (Data Manipulation)

```sql
-- Insert
INSERT INTO employees (name, email, salary) VALUES ('John', 'john@test.com', 50000);
INSERT INTO employees (name, email, salary) VALUES
  ('Alice', 'alice@test.com', 60000),
  ('Bob', 'bob@test.com', 55000);

-- Update
UPDATE employees SET salary = 55000 WHERE id = 1;
UPDATE employees SET salary = salary * 1.1 WHERE dept_id = 5;

-- Delete
DELETE FROM employees WHERE id = 1;
DELETE FROM employees WHERE salary < 30000;
```

## 🔄 CTE (Common Table Expression)

```sql
-- Basic CTE
WITH active_users AS (
  SELECT * FROM users WHERE status = 'active'
)
SELECT * FROM active_users WHERE age > 25;

-- Multiple CTEs
WITH
  dept_count AS (
    SELECT dept_id, COUNT(*) as cnt
    FROM employees GROUP BY dept_id
  ),
  high_salary AS (
    SELECT * FROM employees WHERE salary > 100000
  )
SELECT d.dept_id, d.cnt, h.cnt as high_salary_count
FROM dept_count d
LEFT JOIN (
  SELECT dept_id, COUNT(*) as cnt FROM high_salary GROUP BY dept_id
) h ON d.dept_id = h.dept_id;

-- Recursive CTE (e.g., org hierarchy)
WITH RECURSIVE org_tree AS (
  SELECT id, name, manager_id, 1 as level
  FROM employees WHERE manager_id IS NULL
  UNION ALL
  SELECT e.id, e.name, e.manager_id, t.level + 1
  FROM employees e
  JOIN org_tree t ON e.manager_id = t.id
)
SELECT * FROM org_tree;
```

## 🎯 Set Operations

```sql
-- Union (combine, remove duplicates)
SELECT name FROM employees WHERE dept_id = 1
UNION
SELECT name FROM employees WHERE dept_id = 2;

-- Union All (combine, keep duplicates)
SELECT name FROM employees WHERE dept_id = 1
UNION ALL
SELECT name FROM employees WHERE dept_id = 2;

-- Intersect (common rows)
SELECT name FROM employees WHERE dept_id = 1
INTERSECT
SELECT name FROM employees WHERE salary > 50000;

-- Except (rows in first but not second)
SELECT name FROM employees WHERE dept_id = 1
EXCEPT
SELECT name FROM employees WHERE salary > 50000;
```

## 🔧 Useful Functions

```sql
-- String
SELECT CONCAT(first_name, ' ', last_name) as full_name;
SELECT LENGTH(name);
SELECT UPPER(name), LOWER(email);
SELECT TRIM(name);
SELECT SUBSTRING(name, 1, 3);
SELECT REPLACE(name, 'old', 'new');

-- Date
SELECT NOW(), CURDATE(), CURTIME();
SELECT YEAR(hire_date), MONTH(hire_date), DAY(hire_date);
SELECT DATEDIFF(end_date, start_date);
SELECT DATE_ADD(hire_date, INTERVAL 1 YEAR);
SELECT DATE_FORMAT(hire_date, '%Y-%m-%d');

-- Conditional
SELECT name, salary,
  CASE
    WHEN salary > 100000 THEN 'High'
    WHEN salary > 50000 THEN 'Medium'
    ELSE 'Low'
  END as salary_band
FROM employees;

-- COALESCE (return first non-null)
SELECT COALESCE(phone, email, 'No contact') as contact;

-- NULLIF (return null if equal)
SELECT NULLIF(a, b);  -- returns NULL if a = b
```

## ⚡ Performance Tips

```sql
-- Use EXPLAIN to analyze
EXPLAIN SELECT * FROM employees WHERE dept_id = 5;

-- Create indexes for frequent queries
CREATE INDEX idx_dept ON employees(dept_id);
CREATE INDEX idx_composite ON employees(dept_id, salary);

-- Avoid SELECT * (select only needed columns)
-- Use LIMIT for large result sets
-- Avoid functions on indexed columns in WHERE
-- Use EXISTS instead of IN for large subqueries
```

## 🔗 Cross-References

- [DBMS Interview Questions](../interview/dbms-questions.md) — SQL in interviews
- [DBMS Cheatsheet](./dbms.md) — Database concepts
- [DBMS Revision](../revision/dbms.md) — Quick summary
