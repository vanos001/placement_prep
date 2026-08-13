# Functions

> Functions are the fundamental unit of abstraction in programming. Master them, and you master code organization.

## 1. Functions, Procedures, and Methods

### Functions vs Procedures

| Concept | Returns a Value? | Example |
|---------|-----------------|---------|
| **Function** | Yes | `sqrt(16)` → `4` |
| **Procedure** | No (void) | `print("hello")` |
| **Method** | Either | Function attached to an object/class |

In modern usage, "function" covers all three. But understanding the distinction helps when reading older literature or assembly code.

### Basic Function Syntax

```python
# Python
def add(a: int, b: int) -> int:
    return a + b
```

```javascript
// JavaScript
function add(a, b) {
    return a + b;
}

// Arrow function
const add = (a, b) => a + b;
```

```rust
// Rust
fn add(a: i32, b: i32) -> i32 {
    a + b  // no semicolon = return value (expression-based)
}
```

```go
// Go
func add(a, b int) int {
    return a + b
}
```

```java
// Java
public static int add(int a, int b) {
    return a + b;
}
```

## 2. Parameters and Arguments

### Parameter Passing Mechanisms

| Mechanism | Description | Languages |
|-----------|-------------|-----------|
| **Pass by value** | Copy of the argument is passed | C, Go, Rust (for Copy types) |
| **Pass by reference** | Alias to the original variable | C++ (`&`), C# (`ref`) |
| **Pass by sharing** | Copy of the reference is passed | Java, Python, JavaScript |
| **Pass by move** | Ownership transfers to callee | Rust (for non-Copy types) |

```cpp
// C++: pass by value vs reference
void byValue(int x) { x = 10; }      // doesn't modify original
void byReference(int& x) { x = 10; } // modifies original

int a = 5;
byValue(a);      // a is still 5
byReference(a);  // a is now 10
```

```python
# Python: pass by sharing
def modify(lst):
    lst.append(4)      # modifies the original list
    lst = [99, 100]    # rebinds local variable — original list unchanged

my_list = [1, 2, 3]
modify(my_list)
print(my_list)  # [1, 2, 3, 4]
```

### Default Parameters

```python
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"

greet("Alice")              # "Hello, Alice!"
greet("Alice", "Hi")        # "Hi, Alice!"
```

```javascript
function greet(name, greeting = "Hello") {
    return `${greeting}, ${name}!`;
}
```

```cpp
// C++: default arguments must be rightmost
void foo(int a, int b = 10, int c = 20);
// foo(1)      → a=1, b=10, c=20
// foo(1, 2)   → a=1, b=2, c=20
// foo(1,,20)  // ERROR: can't skip
```

### Variadic Functions

```python
# Python: *args, **kwargs
def sum_all(*args):
    return sum(args)

sum_all(1, 2, 3, 4)  # 10

def print_info(**kwargs):
    for key, value in kwargs.items():
        print(f"{key}: {value}")

print_info(name="Alice", age=30)
```

```c
// C: variadic functions (type-unsafe!)
#include <stdarg.h>
double average(int count, ...) {
    va_list args;
    va_start(args, count);
    double sum = 0;
    for (int i = 0; i < count; i++) {
        sum += va_arg(args, double);
    }
    va_end(args);
    return sum / count;
}
```

```go
// Go: variadic
func sum(nums ...int) int {
    total := 0
    for _, n := range nums {
        total += n
    }
    return total
}
sum(1, 2, 3)  // 6
```

## 3. Return Values

### Single Return

```python
def square(x):
    return x * x
```

### Multiple Return Values

```go
// Go: multiple return values
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("division by zero")
    }
    return a / b, nil
}

result, err := divide(10, 3)
```

```python
# Python: return tuple
def min_max(numbers):
    return min(numbers), max(numbers)

lo, hi = min_max([3, 1, 4, 1, 5])
```

```rust
// Rust: return tuple
fn min_max(numbers: &[i32]) -> (i32, i32) {
    (*numbers.iter().min().unwrap(), *numbers.iter().max().unwrap())
}
```

### Early Return

```python
def find_user(user_id):
    if user_id < 0:
        return None  # early return for invalid input
    # ... look up user
    return user
```

Early returns reduce nesting and improve readability (guard clauses).

## 4. Higher-Order Functions (HOFs)

A **higher-order function** takes a function as an argument, returns a function, or both.

```python
# Built-in HOFs
numbers = [1, 2, 3, 4, 5]

list(map(lambda x: x ** 2, numbers))        # [1, 4, 9, 16, 25]
list(filter(lambda x: x % 2 == 0, numbers)) # [2, 4]
from functools import reduce
reduce(lambda acc, x: acc + x, numbers)      # 15
```

```javascript
const numbers = [1, 2, 3, 4, 5];

numbers.map(x => x ** 2);          // [1, 4, 9, 16, 25]
numbers.filter(x => x % 2 === 0);  // [2, 4]
numbers.reduce((acc, x) => acc + x, 0);  // 15
```

```rust
let numbers = vec![1, 2, 3, 4, 5];

numbers.iter().map(|x| x * x).collect::<Vec<_>>();
numbers.iter().filter(|&&x| x % 2 == 0).collect::<Vec<_>>();
numbers.iter().fold(0, |acc, x| acc + x);
```

### Function Composition

```python
def compose(f, g):
    return lambda x: f(g(x))

double = lambda x: x * 2
increment = lambda x: x + 1
double_then_increment = compose(increment, double)
double_then_increment(3)  # 7
```

```javascript
const compose = (f, g) => x => f(g(x));

const doubleThenIncrement = compose(x => x + 1, x => x * 2);
doubleThenIncrement(3);  // 7
```

### Currying

```javascript
// Currying: transform f(a, b, c) into f(a)(b)(c)
const add = a => b => a + b;
const add5 = add(5);
add5(3);  // 8

// Practical use
const log = level => timestamp => message =>
    console.log(`[${timestamp}] ${level}: ${message}`);

const errorLog = log("ERROR");
errorLog("2024-01-01")("Something broke");
```

```python
from functools import partial

def add(a, b):
    return a + b

add5 = partial(add, 5)
add5(3)  # 8
```

## 5. Closures and Callbacks

### Callbacks

A **callback** is a function passed as an argument to be called later.

```javascript
// Asynchronous callback
fetch('/api/data')
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(err => console.error(err));

// Event callback
button.addEventListener('click', () => {
    console.log('Button clicked!');
});
```

```python
# Callback pattern
def process_data(data, callback):
    result = data.upper()
    callback(result)

process_data("hello", lambda x: print(x))  # "HELLO"
```

### Closure Patterns

```javascript
// Memoization via closure
function memoize(fn) {
    const cache = new Map();
    return function(...args) {
        const key = JSON.stringify(args);
        if (cache.has(key)) return cache.get(key);
        const result = fn(...args);
        cache.set(key, result);
        return result;
    };
}

const fastFib = memoize(function fib(n) {
    if (n <= 1) return n;
    return fib(n - 1) + fib(n - 2);
});
```

## 6. Recursion

**Recursion** is when a function calls itself. Every recursive function needs:
1. **Base case** — when to stop
2. **Recursive case** — how to make progress toward the base case

### Classic Examples

```python
# Factorial
def factorial(n):
    if n <= 1:        # base case
        return 1
    return n * factorial(n - 1)  # recursive case

# Fibonacci (naive — O(2^n))
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
```

### Tail Recursion

**Tail recursion** is when the recursive call is the last operation. It can be optimized into a loop by the compiler (tail call optimization, TCO).

```python
# Tail-recursive factorial
def factorial(n, acc=1):
    if n <= 1:
        return acc
    return factorial(n - 1, n * acc)  # tail position

# Python does NOT optimize tail calls, so this still uses O(n) stack
```

```scheme
;; Scheme: guaranteed TCO
(define (factorial n acc)
  (if (<= n 1)
      acc
      (factorial (- n 1) (* n acc))))
```

```rust
// Rust: doesn't guarantee TCO, but the pattern is common
fn factorial(n: u64, acc: u64) -> u64 {
    if n <= 1 { acc }
    else { factorial(n - 1, n * acc) }
}

// Idiomatic Rust: use iteration
fn factorial(n: u64) -> u64 {
    (1..=n).product()
}
```

### Recursion vs Iteration

| Aspect | Recursion | Iteration |
|--------|-----------|-----------|
| Readability | Often more natural for tree/graph problems | Better for simple loops |
| Stack usage | O(n) stack frames | O(1) |
| Performance | Function call overhead | Usually faster |
| Risk | Stack overflow for deep recursion | None |
| TCO | Some languages optimize it | N/A |

### When to Use Recursion

- Tree/graph traversal
- Divide and conquer algorithms
- Backtracking problems
- Mathematical definitions (Fibonacci, factorial)
- Parsing nested structures (JSON, XML, ASTs)

## 7. Anonymous Functions and Lambdas

```python
# Python: lambda (limited to single expressions)
square = lambda x: x ** 2
# For multi-line, use def
```

```javascript
// JavaScript: multiple styles
const square = function(x) { return x * x; };
const square = x => x ** 2;
const add = (a, b) => a + b;
const greet = name => {           // multi-line
    const msg = `Hello, ${name}`;
    return msg;
};
```

```rust
// Rust closures
let square = |x: i32| x * x;
let add = |a, b| a + b;
```

```cpp
// C++ lambdas
auto square = [](int x) { return x * x; };
auto add = [](int a, int b) { return a + b; };
```

## 8. Generators and Iterators

**Generators** are functions that can pause and resume, yielding multiple values lazily.

### Python Generators

```python
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

# Lazy evaluation — only computes what's needed
fib = fibonacci()
[next(fib) for _ in range(10)]  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

# Generator expression (like list comprehension but lazy)
squares = (x**2 for x in range(1000000))  # no memory used until iterated
sum(squares)  # computes on demand
```

### JavaScript Generators

```javascript
function* fibonacci() {
    let [a, b] = [0, 1];
    while (true) {
        yield a;
        [a, b] = [b, a + b];
    }
}

const fib = fibonacci();
fib.next().value;  // 0
fib.next().value;  // 1
fib.next().value;  // 1

// Iterable
for (const n of fibonacci()) {
    if (n > 100) break;
    console.log(n);
}
```

### Rust Iterators

```rust
// Iterator trait
fn fibonacci() -> impl Iterator<Item = u64> {
    let mut state = (0, 1);
    std::iter::from_fn(move || {
        let current = state.0;
        state = (state.1, state.0 + state.1);
        Some(current)
    })
}

// Usage
fibonacci().take(10).collect::<Vec<_>>()
// [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

### Why Generators?

| Benefit | Explanation |
|---------|-------------|
| Memory efficient | Only one value at a time in memory |
| Lazy evaluation | Compute values on demand |
| Infinite sequences | Can represent unbounded sequences |
| Composable | Chain with map, filter, take, etc. |

## Interview Questions

1. **What is a higher-order function?**
   A function that takes a function as an argument, returns a function, or both. Examples: `map`, `filter`, `reduce`, `sort` with comparators.

2. **Explain closures. What do they capture?**
   A function plus its captured environment. They capture variables by reference (JS, Python), by value/clone (some functional languages), or by move (Rust).

3. **What is tail recursion? Why does it matter?**
   When the recursive call is the last operation. Enables tail call optimization (TCO), converting recursion to a loop and using O(1) stack space. Not all languages guarantee TCO.

4. **What's the difference between `map`, `filter`, and `reduce`?**
   `map`: transform each element. `filter`: keep elements matching a predicate. `reduce`: combine all elements into a single value. They're fundamental functional programming operations.

5. **When should you use recursion vs iteration?**
   Recursion: tree traversal, divide and conquer, backtracking, naturally recursive problems. Iteration: simple loops, performance-critical code, when stack depth is a concern.

6. **What are generators? How do they differ from regular functions?**
   Generators yield values lazily, pausing between yields. They maintain state between calls. They're memory-efficient for large or infinite sequences.

7. **What is currying?**
   Transforming a function `f(a, b, c)` into `f(a)(b)(c)`. Each partial application returns a new function. Useful for creating specialized functions from general ones.

8. **Explain pass by value vs pass by reference vs pass by sharing.**
   Value: copy the data. Reference: alias to the original. Sharing: copy the reference/pointer (Java, Python) — mutations to the object affect the original, but rebinding the parameter doesn't.
