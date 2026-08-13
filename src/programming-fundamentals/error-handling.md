# Error Handling

> Robust software doesn't just work when things go right — it handles what happens when they go wrong.

## 1. Why Error Handling Matters

Programs fail. Networks drop. Disks fill up. Users enter garbage. The question isn't *if* errors happen, but *how* your code responds.

### Error Handling Philosophies

| Philosophy | Core Idea | Languages |
|-----------|-----------|-----------|
| **Error codes** | Functions return special values on failure | C, Go |
| **Exceptions** | Errors are objects thrown and caught | Java, Python, C++ |
| **Result/Option types** | Errors are values, encoded in the type system | Rust, Haskell, OCaml |
| **Error callbacks** | Pass success/failure callbacks | Node.js (older style) |

## 2. Error Codes

The simplest approach: return a value indicating success or failure.

```c
// C style: return error code, output via pointer
int divide(int a, int b, int *result) {
    if (b == 0) return -1;  // error
    *result = a / b;
    return 0;  // success
}

int result;
if (divide(10, 3, &result) == 0) {
    printf("Result: %d\n", result);
} else {
    printf("Error: division by zero\n");
}

// C: errno for system calls
FILE *f = fopen("missing.txt", "r");
if (f == NULL) {
    perror("fopen failed");  // reads errno
}
```

```go
// Go: multiple return values for error handling
result, err := divide(10, 0)
if err != nil {
    fmt.Println("Error:", err)
    return
}
fmt.Println("Result:", result)

// Idiomatic Go: check errors immediately
if err := doSomething(); err != nil {
    return fmt.Errorf("doSomething failed: %w", err)
}
```

### Pros and Cons of Error Codes

| Pros | Cons |
|------|------|
| Explicit — you see error handling in the flow | Easy to forget to check |
| No hidden control flow | Clutters code with if-checks |
| Lightweight | No stack trace by default |
| Predictable performance | Error propagation is manual |

## 3. Exceptions

**Exceptions** are objects that represent errors, thrown with `throw`/`raise` and caught with `try`/`catch`.

### Basic try-catch

```python
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
else:
    print("No error occurred")
finally:
    print("This always runs")
```

```java
try {
    int result = 10 / 0;
} catch (ArithmeticException e) {
    System.out.println("Error: " + e.getMessage());
} catch (Exception e) {
    System.out.println("Unexpected: " + e.getMessage());
} finally {
    System.out.println("Always runs");
}
```

```javascript
try {
    const data = JSON.parse("invalid json");
} catch (error) {
    console.error("Parse error:", error.message);
} finally {
    console.log("Cleanup");
}
```

```cpp
try {
    throw std::runtime_error("something broke");
} catch (const std::runtime_error& e) {
    std::cerr << "Runtime error: " << e.what() << std::endl;
} catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << std::endl;
}
```

### Checked vs Unchecked Exceptions

This is a Java-specific (and influential) distinction:

| Type | Must Declare? | Must Catch? | Examples |
|------|--------------|-------------|----------|
| **Checked** | Yes (in `throws`) | Yes (or propagate) | `IOException`, `SQLException` |
| **Unchecked** | No | No | `NullPointerException`, `ArithmeticException` |
| **Error** | No | No (don't catch) | `OutOfMemoryError`, `StackOverflowError` |

```java
// Checked exception: compiler forces handling
public void readFile() throws IOException {  // must declare
    FileReader fr = new FileReader("file.txt");
}

// Caller must handle or propagate
public void process() throws IOException {  // propagate
    readFile();
}

// Or catch it
public void safeProcess() {
    try {
        readFile();
    } catch (IOException e) {
        // handle
    }
}
```

### Exception Propagation

```python
def a():
    raise ValueError("oops")

def b():
    a()  # exception propagates through b

def c():
    try:
        b()
    except ValueError as e:
        print(f"Caught in c: {e}")

c()  # "Caught in c: oops"
```

When an exception is thrown:
1. The runtime unwinds the call stack
2. Each frame is checked for a matching `catch`
3. If found, execution resumes there
4. If not found, the program terminates (or the exception reaches a global handler)

### The Exception Problem

```java
// What does this throw? You can't tell by looking at the signature.
public void doWork() {
    // Could throw IOException, SQLException, 
    // RuntimeException, or anything else
}
```

This is the main criticism of exceptions: they create **hidden control flow**. A function can throw anything, and you don't know what to catch without reading the implementation.

## 4. Result and Option Types

Modern languages encode errors in the type system, making error handling explicit and enforced.

### Rust Result

```rust
use std::fs;
use std::io;

fn read_file(path: &str) -> Result<String, io::Error> {
    fs::read_to_string(path)
}

// Pattern matching
match read_file("data.txt") {
    Ok(content) => println!("File: {}", content),
    Err(e) => eprintln!("Error: {}", e),
}

// ? operator for propagation
fn process_file(path: &str) -> Result<String, io::Error> {
    let content = fs::read_to_string(path)?;  // propagates error if Err
    Ok(content.to_uppercase())
}

// unwrap() — panics on Err (use sparingly)
let content = read_file("data.txt").unwrap();

// expect() — panics with custom message
let content = read_file("data.txt").expect("Failed to read data.txt");
```

### Rust Option

```rust
fn find_user(id: u32) -> Option<String> {
    if id == 1 {
        Some(String::from("Alice"))
    } else {
        None
    }
}

match find_user(1) {
    Some(name) => println!("Found: {}", name),
    None => println!("User not found"),
}

// Combinators
let name = find_user(2)
    .unwrap_or_else(|| String::from("Unknown"));

let upper = find_user(1)
    .map(|n| n.to_uppercase());

let len = find_user(1)
    .map(|n| n.len())
    .unwrap_or(0);
```

### Haskell Maybe and Either

```haskell
-- Maybe: optional values
safeDivide :: Double -> Double -> Maybe Double
safeDivide _ 0 = Nothing
safeDivide a b = Just (a / b)

-- Either: error values with type
data AppError = DivByZero | NotFound String

safeDivide' :: Double -> Double -> Either AppError Double
safeDivide' _ 0 = Left DivByZero
safeDivide' a b = Right (a / b)
```

### Result/Option vs Exceptions

| Aspect | Result/Option | Exceptions |
|--------|--------------|------------|
| Explicit in signature | ✅ Yes | ❌ No (unless checked) |
| Compiler enforces handling | ✅ Yes | ❌ No (unless checked) |
| Performance | No overhead | Stack unwinding cost |
| Code verbosity | More explicit matching | Less boilerplate |
| Composition | `?`, `map`, `and_then` | `try-catch` |
| Hidden control flow | None | Yes |

## 5. Error Propagation

### The `?` Operator (Rust)

```rust
fn complex_operation() -> Result<String, AppError> {
    let config = read_config()?;      // propagates io::Error
    let data = fetch_data(&config)?;  // propagates network Error
    let parsed = parse(&data)?;       // propagates parse Error
    Ok(parsed)
}
```

### Error Wrapping

```rust
// Wrap lower-level errors into application errors
#[derive(Debug)]
enum AppError {
    Io(io::Error),
    Parse(ParseError),
    Network(String),
}

impl From<io::Error> for AppError {
    fn from(e: io::Error) -> Self {
        AppError::Io(e)
    }
}

// Now ? automatically wraps io::Error into AppError
fn read_config() -> Result<Config, AppError> {
    let content = fs::read_to_string("config.toml")?;  // auto-wrapped
    // ...
}
```

```python
# Python: exception chaining
try:
    process_data()
except ValueError as e:
    raise RuntimeError("Processing failed") from e
```

## 6. Assertions and Defensive Programming

### Assertions

Assertions check conditions that *should always be true*. They're for catching programmer errors, not runtime errors.

```python
def calculate_average(numbers):
    assert len(numbers) > 0, "List must not be empty"
    return sum(numbers) / len(numbers)

# Python: -O flag disables assertions
```

```java
// Java assertions (disabled by default in production)
assert age >= 0 : "Age cannot be negative: " + age;
assert list != null && !list.isEmpty() : "List must not be null or empty";
```

```rust
// Rust: debug_assert (only in debug builds)
debug_assert!(x > 0, "x must be positive, got {}", x);

// assert! (always active)
assert!(x > 0, "x must be positive");
```

### Defensive Programming

| Technique | Description | Example |
|-----------|-------------|---------|
| **Guard clauses** | Check preconditions early, return/throw | `if (x < 0) throw ...` |
| **Null checks** | Check for null before using | `if (obj == null) return` |
| **Bounds checking** | Validate array indices | `if (i >= arr.length) ...` |
| **Input validation** | Check all external input | Validate forms, API inputs |
| **Fail fast** | Detect errors as early as possible | Assert invariants |
| **Default cases** | Handle unexpected enum values | `switch` with `default` |

### Design by Contract

```python
def withdraw(account, amount):
    """
    Preconditions:
        - account must not be None
        - amount must be positive
        - account.balance >= amount
    Postconditions:
        - account.balance decreased by amount
    """
    assert account is not None, "Account must not be None"
    assert amount > 0, "Amount must be positive"
    assert account.balance >= amount, "Insufficient funds"

    old_balance = account.balance
    account.balance -= amount

    assert account.balance == old_balance - amount, "Balance invariant violated"
```

## 7. Error Handling Best Practices

### 1. Be Specific About What You Catch

```python
# Bad: catches everything, including KeyboardInterrupt
try:
    do_something()
except:
    pass

# Good: catch specific exceptions
try:
    do_something()
except ValueError as e:
    handle_value_error(e)
except ConnectionError as e:
    handle_connection_error(e)
```

### 2. Don't Use Exceptions for Control Flow

```python
# Bad: using exception for normal flow
try:
    value = my_dict[key]
except KeyError:
    value = default

# Good: use get()
value = my_dict.get(key, default)
```

### 3. Include Context in Error Messages

```java
// Bad
throw new Exception("Error");

// Good
throw new IllegalArgumentException(
    String.format("Invalid age %d: must be between 0 and 150", age)
);
```

### 4. Clean Up Resources (RAII)

```cpp
// C++: RAII (Resource Acquisition Is Initialization)
{
    std::ifstream file("data.txt");  // opens in constructor
    // use file...
}  // automatically closed in destructor, even if exception thrown
```

```python
# Python: context managers
with open("data.txt") as f:
    content = f.read()
# file automatically closed
```

```rust
// Rust: Drop trait
struct DatabaseConnection { /* ... */ }
impl Drop for DatabaseConnection {
    fn drop(&mut self) {
        // cleanup code runs automatically
    }
}
```

## Interview Questions

1. **What's the difference between checked and unchecked exceptions?**
   Checked: must be declared in method signature and caught by caller (compile-time enforcement). Unchecked: don't need to be declared or caught. Checked exceptions are for recoverable conditions; unchecked for programming errors.

2. **When should you use exceptions vs error codes vs Result types?**
   Exceptions: when errors are truly exceptional and not part of normal flow. Error codes: when you need explicit, visible error handling (C, Go). Result types: when you want compiler-enforced, explicit error handling without hidden control flow.

3. **What is the `?` operator in Rust?**
   Shorthand for "if this is an Err, return it from the current function." It propagates errors up the call stack concisely, replacing verbose match statements.

4. **Why are exceptions considered harmful by some?**
   They create hidden control flow, making it hard to reason about what a function can do. You can't tell from the signature what exceptions might be thrown (in most languages). Stack unwinding has performance costs.

5. **What is RAII?**
   Resource Acquisition Is Initialization — tie resource lifetime to object lifetime. Resources (files, locks, memory) are acquired in constructors and released in destructors, ensuring cleanup even when exceptions occur.

6. **When should you use assertions vs exceptions?**
   Assertions: for conditions that represent programmer errors and should never be false (invariants, preconditions). Exceptions: for expected runtime errors (file not found, network timeout).

7. **What is error wrapping/chaining?**
   Encapsulating a lower-level error in a higher-level error while preserving the original cause. Creates a chain of errors showing the full context. Rust's `From` trait and Python's `raise ... from` support this.

8. **Explain the difference between `unwrap()` and `expect()` in Rust.**
   Both panic on Err. `unwrap()` gives a generic panic message. `expect("msg")` gives a custom message. Both should be used sparingly — prefer `?` for propagation or `match` for handling.
