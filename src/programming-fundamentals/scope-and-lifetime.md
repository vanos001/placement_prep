# Scope and Lifetime

> Where can you access a variable? How long does it exist? These questions define scope and lifetime.

## 1. Scope

**Scope** is the region of code where a name (variable, function, type) is visible and accessible.

### Block Scope

Variables declared inside a block `{ }` are only accessible within that block.

```c
// C/C++
if (true) {
    int x = 10;
    printf("%d", x);  // OK
}
// printf("%d", x);   // error: x undeclared
```

```javascript
// JavaScript: let and const are block-scoped
{
    let x = 10;
    console.log(x);  // OK
}
// console.log(x);   // ReferenceError

// var is function-scoped, NOT block-scoped
{
    var y = 20;
}
console.log(y);  // 20 — var leaks out of blocks!
```

```rust
// Rust
{
    let x = 5;
    println!("{}", x);  // OK
}
// println!("{}", x);   // error: not found in scope
```

### Function Scope

Variables are accessible throughout the entire function.

```python
def foo():
    x = 10
    if True:
        print(x)   # OK — x is in function scope
    print(x)       # OK
```

```javascript
function foo() {
    var x = 10;
    if (true) {
        var y = 20;  // y is function-scoped (var!)
    }
    console.log(y);  // 20 — not what you'd expect from C-like languages
}
```

### Module/Global Scope

```python
# global.py
GLOBAL_VAR = "I'm global"

def foo():
    print(GLOBAL_VAR)  # readable

def bar():
    global GLOBAL_VAR   # must declare to modify
    GLOBAL_VAR = "modified"
```

```javascript
// browser: window is the global object
window.globalVar = "I'm global";

// Node.js: global object, or use module.exports
global.globalVar = "I'm global";
```

### Lexical Scope (Static Scope)

Most modern languages use **lexical scoping** — a variable's scope is determined by where it's defined in the source code, not where it's called from.

```javascript
function outer() {
    let x = 10;
    function inner() {
        console.log(x);  // 10 — inner can see outer's scope
    }
    inner();
}
outer();
```

### Dynamic Scope (Rare)

In dynamic scope, a variable's scope is determined by the call stack at runtime.

```bash
# Bash uses dynamic scoping for functions
greeting="hello"
foo() {
    echo "$greeting"
}
bar() {
    local greeting="hi"
    foo  # prints "hi" (dynamic scope), not "hello" (would be lexical)
}
bar  # "hi"
```

```perl
# Perl: 'local' keyword creates dynamic scoping
$x = "global";
sub foo { print $x; }
sub bar { local $x = "local"; foo; }  # prints "local"
```

### Comparison of Scoping Models

| Language | Block Scope | Function Scope | Module Scope | Global |
|----------|-------------|----------------|--------------|--------|
| C/C++ | ✅ | ✅ | ✅ (static) | ✅ |
| Java | ✅ | ✅ | ✅ (class) | ❌ |
| Python | ❌ (function) | ✅ | ✅ | ✅ |
| JavaScript | ✅ (let/const) | ✅ (var) | ✅ (modules) | ✅ |
| Rust | ✅ | ✅ | ✅ (mod) | ❌ |
| Go | ✅ | ✅ | ✅ (package) | ❌ |

## 2. Variable Shadowing

**Shadowing** occurs when a variable in an inner scope has the same name as one in an outer scope.

```rust
// Rust: shadowing is common and allowed
let x = 5;
{
    let x = x * 2;   // shadows outer x
    println!("{}", x); // 10
}
println!("{}", x);     // 5 — outer x unchanged
```

```python
# Python: shadowing works but can be confusing
x = 10
def foo():
    x = 20      # creates a new local x, doesn't modify outer
    print(x)    # 20
foo()
print(x)        # 10

# To modify: use nonlocal or global
def bar():
    nonlocal x  # (only works inside nested functions)
    x = 20
```

```javascript
// JavaScript: var, let, const can all shadow
let x = 10;
function foo() {
    let x = 20;  // shadows outer x
    console.log(x); // 20
}
```

### When Shadowing Is Useful

- Reusing a name with a different type (Rust)
- Narrowing a value (e.g., `let user = parse(input);`)
- Temporary overrides

### When Shadowing Is Dangerous

- Accidentally accessing the wrong variable
- Confusing readers about which `x` is meant
- Bugs in deeply nested code

## 3. Lifetime

**Lifetime** is the period during which a variable or reference is valid (points to live data).

### Rust Lifetimes (Explicit)

Rust makes lifetimes explicit to prevent dangling references at compile time.

```rust
// This won't compile — dangling reference
fn dangling() -> &String {
    let s = String::from("hello");
    &s  // error: `s` doesn't live long enough
}

// Lifetime annotation
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}

// Structs that hold references need lifetime annotations
struct Excerpt<'a> {
    text: &'a str,
}
```

### C/C++ Lifetimes (Manual)

In C/C++, lifetimes are your responsibility. Getting them wrong causes bugs.

```c
// Dangling pointer — undefined behavior
char* dangling() {
    char buf[100];
    sprintf(buf, "hello");
    return buf;  // buf dies when function returns!
}

// Correct: allocate on heap
char* safe() {
    char* buf = malloc(100);
    sprintf(buf, "hello");
    return buf;  // caller must free()
}
```

### Java/Python Lifetimes (GC)

With garbage collection, lifetimes are managed automatically:

```java
// Java: GC handles lifetime
Object create() {
    Object obj = new Object();
    return obj;  // fine — GC keeps it alive
}
```

## 4. Storage Duration

Storage duration determines *when* memory is allocated and deallocated.

### Automatic Storage Duration

```c
void foo() {
    int x = 10;  // allocated when function is called
                 // deallocated when function returns
}
```

- Allocated on the stack
- Tied to the block scope
- Very fast (just stack pointer adjustment)

### Static Storage Duration

```c
// Global variable — lives for the entire program
int counter = 0;

void foo() {
    static int calls = 0;  // initialized once, persists across calls
    calls++;
    printf("Called %d times\n", calls);
}
```

```python
# Python: module-level variables have static-like duration
_cache = {}  # lives as long as the module is loaded
```

### Dynamic Storage Duration

```c
// Allocated with malloc, freed with free
void foo() {
    int *p = malloc(sizeof(int));
    *p = 42;
    // ... use p ...
    free(p);  // you must free it!
}
```

```java
// Java: dynamic allocation, GC handles deallocation
void foo() {
    int[] arr = new int[100];  // heap allocated
    // no need to free — GC will handle it
}
```

### Thread-Local Storage Duration

```c
// C11
_Thread_local int tls_var = 0;

// C++11
thread_local int tls_var = 0;

// Java
static ThreadLocal<Integer> tls = ThreadLocal.withInitial(() -> 0);
```

Each thread gets its own copy. Useful for:
- Per-thread error states (like `errno`)
- Thread-local caches
- Avoiding synchronization on frequently accessed data

### Storage Duration Comparison

| Duration | Allocated | Freed | Location | Example |
|----------|-----------|-------|----------|---------|
| Automatic | Block entry | Block exit | Stack | Local variables |
| Static | Program start | Program end | Data segment | Globals, `static` locals |
| Dynamic | `malloc`/`new` | `free`/`delete`/GC | Heap | Dynamically allocated objects |
| Thread-local | Thread start | Thread end | TLS segment | `thread_local` variables |

## 5. Closures and Variable Capture

A **closure** is a function that captures variables from its enclosing scope.

### JavaScript Closures

```javascript
function makeCounter() {
    let count = 0;  // captured variable
    return function() {
        count++;
        return count;
    };
}

const counter = makeCounter();
counter();  // 1
counter();  // 2
counter();  // 3
// count is private — only accessible through the closure
```

### Python Closures

```python
def make_multiplier(factor):
    def multiply(x):
        return x * factor  # captures 'factor'
    return multiply

double = make_multiplier(2)
double(5)   # 10
triple = make_multiplier(3)
triple(5)   # 15
```

### Rust Closures

```rust
// Closures capture by reference, mutable reference, or move
let name = String::from("Alice");

// Capture by reference
let greet = || println!("Hello, {}", name);
greet();  // "Hello, Alice"

// Move captures ownership
let name = String::from("Bob");
let greet = move || println!("Hello, {}", name);
// println!("{}", name);  // error: value moved
```

### C++ Lambdas

```cpp
int x = 10;
auto f = [x]() { return x; };        // capture by value
auto g = [&x]() { return ++x; };     // capture by reference
auto h = [=]() { return x; };        // capture all by value
auto i = [&]() { return ++x; };      // capture all by reference
```

### Capture Modes

| Language | Default Capture | Explicit Options |
|----------|----------------|------------------|
| JavaScript | All outer variables (lexical) | N/A (always by reference) |
| Python | By reference | `nonlocal` to modify |
| Rust | By immutable reference | `&mut`, `move` |
| C++ | None (must specify) | `[=]`, `[&]`, `[x]`, `[&x]` |
| Java | By reference (effectively final) | Variables must be final/implicitly final |
| Go | By reference | N/A |

### Common Closure Patterns

```javascript
// 1. Factory function
function createGreeter(greeting) {
    return function(name) {
        return `${greeting}, ${name}!`;
    };
}
const hello = createGreeter("Hello");
hello("Alice");  // "Hello, Alice!"

// 2. Private state (module pattern)
function createBankAccount(initialBalance) {
    let balance = initialBalance;
    return {
        deposit(amount) { balance += amount; },
        withdraw(amount) { balance -= amount; },
        getBalance() { return balance; }
    };
}

// 3. Event handler
function setupButton(buttonId, message) {
    document.getElementById(buttonId).addEventListener('click', () => {
        alert(message);  // captures message
    });
}
```

## 6. Hoisting

**Hoisting** is a JavaScript-specific behavior where declarations are moved to the top of their scope.

```javascript
console.log(x);  // undefined (not ReferenceError!)
var x = 10;

// Equivalent to:
var x;
console.log(x);
x = 10;

// let/const are NOT hoisted the same way
console.log(y);  // ReferenceError: Cannot access 'y' before initialization
let y = 10;

// Function declarations ARE hoisted
foo();  // works!
function foo() { console.log("hi"); }

// Function expressions are NOT hoisted
bar();  // TypeError: bar is not a function
var bar = function() { console.log("hi"); };
```

## Interview Questions

1. **What is lexical scoping vs dynamic scoping?**
   Lexical: scope determined by source code structure. Dynamic: scope determined by call stack at runtime. Most modern languages use lexical scoping.

2. **Explain closures. Why are they useful?**
   A closure is a function that captures variables from its enclosing scope. Useful for: data privacy, factory functions, callbacks, currying, maintaining state without classes.

3. **What's the difference between `var`, `let`, and `const` scoping in JavaScript?**
   `var` is function-scoped and hoisted. `let` and `const` are block-scoped. `const` cannot be reassigned. `let` and `const` have a temporal dead zone before declaration.

4. **What is variable shadowing? When is it useful vs dangerous?**
   When an inner variable has the same name as an outer variable. Useful for reusing names with different types (Rust). Dangerous when it causes confusion about which variable is being accessed.

5. **Explain storage duration. What's the difference between automatic and dynamic?**
   Automatic: stack-allocated, tied to scope, freed on exit. Dynamic: heap-allocated, freed manually or by GC. Automatic is faster; dynamic is more flexible.

6. **What is a dangling reference? How do different languages handle it?**
   A reference to memory that has been freed. C/C++: undefined behavior (you must prevent it). Rust: compile-time error (borrow checker prevents it). Java/Python: GC prevents it.

7. **Why does Rust require lifetime annotations?**
   To prove to the compiler that references are valid. The borrow checker uses lifetimes to ensure no dangling references exist at compile time, without needing a GC.

8. **What is hoisting in JavaScript?**
   Declarations (`var`, function declarations) are conceptually moved to the top of their scope. `var` gets `undefined` initialization; `let`/`const` are in a temporal dead zone until their declaration line.
