# SQL Stored Procedures and Functions

## Overview

**Stored Procedures** and **Functions** are precompiled SQL code blocks stored in the database. They encapsulate business logic on the server side, reducing network traffic, improving performance, and providing security through abstraction. They support variables, control flow, error handling, and can return results.

## Stored Procedure vs Function

| Aspect | Stored Procedure | Function |
|---|---|---|
| Invocation | `CALL proc_name()` | `SELECT func_name()` |
| Return | Zero or more result sets | Exactly one value or table |
| Use in SQL | Cannot be used in SELECT | Can be used in SELECT, WHERE |
| Side effects | Can modify data | Should be side-effect free |
| Transaction control | Can COMMIT/ROLLBACK | Cannot |
| Language | PL/pgSQL, T-SQL, PL/SQL, etc. | Same |

## MySQL Stored Procedures

### Basic Procedure

```sql
DELIMITER //

CREATE PROCEDURE GetEmployeesByDept(IN dept_name VARCHAR(50))
BEGIN
    SELECT emp_id, name, salary
    FROM Employees
    WHERE department = dept_name
    ORDER BY salary DESC;
END //

DELIMITER ;

-- Call
CALL GetEmployeesByDept('Engineering');
```

### Parameters: IN, OUT, INOUT

```sql
DELIMITER //

-- IN: input parameter (default)
-- OUT: output parameter
-- INOUT: both input and output
CREATE PROCEDURE GetDeptStats(
    IN dept_name VARCHAR(50),
    OUT emp_count INT,
    OUT avg_salary DECIMAL(10,2),
    OUT max_salary DECIMAL(10,2)
)
BEGIN
    SELECT COUNT(*), AVG(salary), MAX(salary)
    INTO emp_count, avg_salary, max_salary
    FROM Employees
    WHERE department = dept_name;
END //

DELIMITER ;

-- Call with output parameters
CALL GetDeptStats('Engineering', @count, @avg, @max);
SELECT @count, @avg, @max;
```

### Variables

```sql
DELIMITER //

CREATE PROCEDURE CalculateBonus(IN emp_id INT)
BEGIN
    DECLARE base_salary DECIMAL(10,2);
    DECLARE performance VARCHAR(20);
    DECLARE bonus DECIMAL(10,2);

    -- Get employee data
    SELECT salary, perf_rating INTO base_salary, performance
    FROM Employees WHERE emp_id = emp_id;

    -- Calculate bonus based on performance
    SET bonus = CASE performance
        WHEN 'Excellent' THEN base_salary * 0.20
        WHEN 'Good' THEN base_salary * 0.15
        WHEN 'Average' THEN base_salary * 0.10
        ELSE base_salary * 0.05
    END;

    -- Update employee bonus
    UPDATE Employees SET bonus_amount = bonus WHERE emp_id = emp_id;
END //

DELIMITER ;
```

### Control Flow

```sql
DELIMITER //

CREATE PROCEDURE ProcessOrder(IN order_id INT)
BEGIN
    DECLARE order_status VARCHAR(20);
    DECLARE order_total DECIMAL(10,2);

    SELECT status, total INTO order_status, order_total
    FROM Orders WHERE order_id = order_id;

    -- IF-ELSEIF-ELSE
    IF order_status = 'pending' THEN
        IF order_total > 1000 THEN
            UPDATE Orders SET status = 'approved', discount = order_total * 0.05
            WHERE order_id = order_id;
        ELSE
            UPDATE Orders SET status = 'approved' WHERE order_id = order_id;
        END IF;
    ELSEIF order_status = 'approved' THEN
        UPDATE Orders SET status = 'shipped' WHERE order_id = order_id;
    ELSE
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cannot process order in current status';
    END IF;
END //

DELIMITER ;
```

### Loops

```sql
DELIMITER //

-- WHILE loop
CREATE PROCEDURE GenerateNumbers(IN max_num INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    CREATE TEMPORARY TABLE IF NOT EXISTS Numbers (n INT);
    TRUNCATE TABLE Numbers;

    WHILE i <= max_num DO
        INSERT INTO Numbers VALUES (i);
        SET i = i + 1;
    END WHILE;

    SELECT * FROM Numbers;
END //

-- REPEAT loop (executes at least once)
CREATE PROCEDURE RepeatDemo()
BEGIN
    DECLARE counter INT DEFAULT 0;

    REPEAT
        SET counter = counter + 1;
    UNTIL counter >= 10
    END REPEAT;

    SELECT counter;
END //

-- LOOP with LEAVE
CREATE PROCEDURE LoopDemo()
BEGIN
    DECLARE i INT DEFAULT 0;

    my_loop: LOOP
        SET i = i + 1;
        IF i > 10 THEN
            LEAVE my_loop;  -- Break
        END IF;
        -- ITERATE my_loop; would be 'continue'
        SELECT i;
    END LOOP my_loop;
END //

DELIMITER ;
```

### Cursors

```sql
DELIMITER //

CREATE PROCEDURE ProcessAllEmployees()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE emp_name VARCHAR(100);
    DECLARE emp_salary DECIMAL(10,2);

    DECLARE emp_cursor CURSOR FOR
        SELECT name, salary FROM Employees WHERE is_active = true;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN emp_cursor;

    read_loop: LOOP
        FETCH emp_cursor INTO emp_name, emp_salary;
        IF done THEN
            LEAVE read_loop;
        END IF;

        -- Process each employee
        INSERT INTO AuditLog (action, details)
        VALUES ('processed', CONCAT(emp_name, ': ', emp_salary));
    END LOOP;

    CLOSE emp_cursor;
END //

DELIMITER ;
```

### Error Handling

```sql
DELIMITER //

CREATE PROCEDURE TransferFunds(
    IN from_account INT,
    IN to_account INT,
    IN amount DECIMAL(10,2)
)
BEGIN
    DECLARE insufficient_funds CONDITION FOR SQLSTATE '45001';
    DECLARE from_balance DECIMAL(10,2);

    -- Declare error handler
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'Error: Transaction rolled back' AS result;
    END;

    START TRANSACTION;

    -- Check balance
    SELECT balance INTO from_balance FROM Accounts WHERE account_id = from_account;

    IF from_balance < amount THEN
        SIGNAL insufficient_funds
            SET MESSAGE_TEXT = 'Insufficient funds';
    END IF;

    -- Perform transfer
    UPDATE Accounts SET balance = balance - amount WHERE account_id = from_account;
    UPDATE Accounts SET balance = balance + amount WHERE account_id = to_account;

    COMMIT;
    SELECT 'Transfer successful' AS result;
END //

DELIMITER ;
```

## PostgreSQL Functions (PL/pgSQL)

### Basic Function

```sql
CREATE OR REPLACE FUNCTION get_employee_count(dept_name TEXT)
RETURNS INTEGER AS $$
DECLARE
    emp_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO emp_count
    FROM Employees
    WHERE department = dept_name;
    RETURN emp_count;
END;
$$ LANGUAGE plpgsql;

-- Usage
SELECT get_employee_count('Engineering');
SELECT * FROM Employees WHERE department = 'Engineering'
AND get_employee_count('Engineering') > 5;
```

### Table-Returning Functions

```sql
CREATE OR REPLACE FUNCTION get_top_earners(dept_name TEXT, n INTEGER DEFAULT 5)
RETURNS TABLE(emp_id INT, name TEXT, salary DECIMAL) AS $$
BEGIN
    RETURN QUERY
    SELECT E.emp_id, E.name::TEXT, E.salary
    FROM Employees E
    WHERE E.department = dept_name
    ORDER BY E.salary DESC
    LIMIT n;
END;
$$ LANGUAGE plpgsql;

-- Usage
SELECT * FROM get_top_earners('Engineering', 3);
```

### Trigger Functions

```sql
CREATE OR REPLACE FUNCTION update_modified_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_modified
BEFORE UPDATE ON Employees
FOR EACH ROW EXECUTE FUNCTION update_modified_at();
```

## SQL Server Stored Procedures

```sql
-- Basic procedure
CREATE PROCEDURE usp_GetEmployeesByDept
    @DeptName NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;  -- Don't return row count

    SELECT emp_id, name, salary
    FROM Employees
    WHERE department = @DeptName
    ORDER BY salary DESC;
END;
GO

EXEC usp_GetEmployeesByDept @DeptName = 'Engineering';
GO

-- With OUTPUT parameter
CREATE PROCEDURE usp_GetDeptStats
    @DeptName NVARCHAR(50),
    @EmpCount INT OUTPUT,
    @AvgSalary DECIMAL(10,2) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT @EmpCount = COUNT(*), @AvgSalary = AVG(salary)
    FROM Employees WHERE department = @DeptName;
END;
GO

DECLARE @cnt INT, @avg DECIMAL(10,2);
EXEC usp_GetDeptStats 'Engineering', @cnt OUTPUT, @avg OUTPUT;
SELECT @cnt AS EmployeeCount, @avg AS AvgSalary;
GO

-- TRY-CATCH error handling
CREATE PROCEDURE usp_SafeTransfer
    @FromID INT, @ToID INT, @Amount DECIMAL(10,2)
AS
BEGIN
    BEGIN TRY
        BEGIN TRANSACTION;
            UPDATE Accounts SET balance = balance - @Amount WHERE account_id = @FromID;
            UPDATE Accounts SET balance = balance + @Amount WHERE account_id = @ToID;
        COMMIT;
    END TRY
    BEGIN CATCH
        ROLLBACK;
        THROW;
    END CATCH;
END;
GO
```

## Dynamic SQL in Stored Procedures

```sql
-- MySQL: Prepared statements
DELIMITER //
CREATE PROCEDURE DynamicQuery(IN table_name VARCHAR(100), IN col_name VARCHAR(100))
BEGIN
    SET @sql = CONCAT('SELECT ', col_name, ' FROM ', table_name);
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
END //
DELIMITER ;

-- PostgreSQL: EXECUTE
CREATE OR REPLACE FUNCTION dynamic_filter(table_name TEXT, column_name TEXT, filter_value TEXT)
RETURNS SETOF RECORD AS $$
BEGIN
    RETURN QUERY EXECUTE format(
        'SELECT * FROM %I WHERE %I = %L',
        table_name, column_name, filter_value
    );
END;
$$ LANGUAGE plpgsql;
```

## Interview Questions

### Beginner

**Q1: What is a stored procedure?**
A: A stored procedure is a precompiled set of SQL statements stored in the database. It can accept parameters, perform logic (IF, loops), modify data, and return results. Benefits: reusability, security (hide table access), reduced network traffic, and centralized business logic.

**Q2: What is the difference between a stored procedure and a function?**
A: Procedures are invoked with CALL, can have side effects (modify data), can return multiple result sets, and can control transactions. Functions are invoked in SELECT, should be side-effect free, return exactly one value, and can be used in expressions.

**Q3: What are IN, OUT, and INOUT parameters?**
A: **IN**: Input only (default). **OUT**: Output only — the procedure sets the value for the caller. **INOUT**: Both — the caller passes a value, the procedure can modify it and return the new value.

### Intermediate

**Q4: When should you use stored procedures vs application code?**
A: Use stored procedures for: data-intensive operations (reduce network round trips), complex multi-step transactions, security-sensitive operations (users can't see table structure), and operations that must be atomic. Use application code for: business logic that changes frequently, UI-related logic, and operations spanning multiple systems.

**Q5: How do you handle errors in stored procedures?**
A: MySQL: DECLARE ... HANDLER for specific SQLSTATEs, SIGNAL to raise errors. PostgreSQL: BEGIN/EXCEPTION/WHEN blocks. SQL Server: TRY/CATCH blocks with THROW. Always rollback transactions on error.

**Q6: What is the N+1 problem with stored procedures?**
A: Calling a procedure for each row in a result set (e.g., calling GetEmployeeDetails in a loop for 100 employees = 101 calls). Solution: batch operations — pass a list of IDs or use table-valued parameters.

### Advanced / FAANG-Level

**Q7: Design a stored procedure for an atomic order placement with inventory check, payment, and notification.**
A:
```sql
DELIMITER //
CREATE PROCEDURE PlaceOrder(
    IN p_customer_id INT,
    IN p_product_id INT,
    IN p_quantity INT,
    OUT p_order_id INT,
    OUT p_status VARCHAR(50)
)
BEGIN
    DECLARE available_stock INT;
    DECLARE product_price DECIMAL(10,2);
    DECLARE insufficient_stock CONDITION FOR SQLSTATE '45002';

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_status = 'FAILED: System error';
    END;

    START TRANSACTION;

    -- Check inventory with row-level lock
    SELECT stock, price INTO available_stock, product_price
    FROM Products WHERE product_id = p_product_id FOR UPDATE;

    IF available_stock < p_quantity THEN
        ROLLBACK;
        SET p_status = 'FAILED: Insufficient stock';
    ELSE
        -- Create order
        INSERT INTO Orders (customer_id, product_id, quantity, unit_price, total, status)
        VALUES (p_customer_id, p_product_id, p_quantity, product_price,
                product_price * p_quantity, 'confirmed');
        SET p_order_id = LAST_INSERT_ID();

        -- Reduce inventory
        UPDATE Products SET stock = stock - p_quantity WHERE product_id = p_product_id;

        -- Log notification
        INSERT INTO NotificationQueue (customer_id, type, message)
        VALUES (p_customer_id, 'order_confirmation',
                CONCAT('Order #', p_order_id, ' confirmed'));

        COMMIT;
        SET p_status = 'SUCCESS';
    END IF;
END //
DELIMITER ;
```

**Q8: How do stored procedures affect query plan caching?**
A: Stored procedures have their execution plans cached after first compilation. This means:
- **Benefit**: Subsequent calls reuse the cached plan (faster than ad-hoc SQL)
- **Parameter sniffing**: The plan is optimized for the first parameter values — may be suboptimal for different values
- **Recompilation**: ALTER PROCEDURE, statistics updates, or `WITH RECOMPILE` forces recompilation
- **Solution to parameter sniffing**: Use `OPTION (RECOMPILE)` for queries with varying data distributions, or use `OPTIMIZE FOR UNKNOWN`

## Common Mistakes

- Not handling errors/exceptions (silent failures)
- Using SELECT * in procedures (breaks when schema changes)
- Not using transactions for multi-statement operations
- Creating overly complex procedures (hard to test and maintain)
- Not considering parameter sniffing in SQL Server
- Using dynamic SQL without parameterization (SQL injection risk)
- Mixing business logic and data access in procedures

## Summary

| Feature | Stored Procedure | Function |
|---|---|---|
| Invocation | CALL / EXEC | SELECT / expression |
| Return type | Result sets, OUT params | Single value or table |
| Side effects | Allowed | Discouraged |
| Transaction control | Yes | No |
| Use in SELECT | No | Yes |
| Language | PL/pgSQL, T-SQL, PL/SQL | Same |

## Cross-References

- [DML](dml.md) — SQL data manipulation
- [Triggers](triggers.md) — Automatic execution on events
- [Transactions](../transactions/README.md) — Transaction control in procedures
- [Indexes](indexes.md) — Performance of procedure queries
