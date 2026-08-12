# Programming Fundamentals — Interview Questions

> Curated questions covering variables, types, memory, error handling, functions, and more. Organized by difficulty.

## Beginner

### Variables and Types

**Q1: What's the difference between a variable and a constant?**

A variable's value can change during execution. A constant's value is fixed at initialization (or compile time) and cannot be modified. Constants enable compiler optimizations and prevent accidental mutation.

```java
int x = 10;        // variable
x = 20;            // OK
final int MAX = 100; // constant
// MAX = 200;      // compile error!
```

---

**Q2: What are primitive types? Give examples.**

Primitive types are built-in types that map directly to hardware representations. They're not objects (in most languages) and are passed by value.

Common primitives: `int`, `float`, `double`, `boolean`, `char`, `byte`, `short`, `long`. Python has no primitive types — everything is an object.

---

**Q3: Explain the difference between `int` and `Integer` in Java.**

`int` is a primitive type (4 bytes, stored on stack). `Integer` is a wrapper class (object on heap, with methods). `int` can't be null; `Integer` can. `int` is faster; `Integer` is needed for generics (`List<Integer>`).

---

**Q4: What is type casting? What's the difference between widening and narrowing?**

Type casting converts a value from one type to another. Widening (e.g., `int` → `double`) is safe and implicit. Narrowing (e.g., `double` → `int`) may lose data and requires explicit cast.

---

**Q5: Why does `0.1 + 0.2 != 0.3`?**

IEEE 754 floating point cannot exactly represent 0.1 in binary (it's a repeating fraction). The accumulated rounding error produces 0.30000000000000004, which isn't exactly 0.3. Use tolerance-based comparison or decimal types.

---

### Scope and Lifetime

**Q6: What is block scope vs function scope?**

Block scope: variable is only accessible within the `{ }` block where it's declared (C, Java, JavaScript `let`/`const`). Function scope: variable is accessible throughout the entire function (JavaScript `var`, Python functions).

---

**Q7: What is a closure?**

A closure is a function that captures variables from its enclosing scope, even after that scope has finished executing. The captured variables remain accessible through the closure.

```javascript
function counter() {
    let count = 0;
    return () => ++count;  // closure captures 'count'
}
const c = counter();
c(); // 1
c(); // 2
```

---

**Q8: What's the difference between stack and heap memory?**

Stack: fast, automatic allocation/deallocation, limited size, used for local variables. Heap: slower, manually managed or GC'd, large, used for dynamically allocated objects.

---

### Functions

**Q9: What is a higher-order function?**

A function that takes a function as an argument or returns a function. Examples: `map`, `filter`, `reduce`, `sort` with comparators. Enables functional programming patterns.

---

**Q10: What is recursion? When should you use it?**

A function that calls itself with a smaller input until reaching a base case. Use for: tree traversal, divide and conquer, backtracking, naturally recursive problems (Fibonacci, factorial).

---

**Q11: Explain the difference between `==` and `.equals()` in Java.**

`==` compares references (same object in memory). `.equals()` compares values (content equality). For strings, `"hello" == new String("hello")` is false, but `"hello".equals(new String("hello"))` is true.

---

### Error Handling

**Q12: What's the difference between checked and unchecked exceptions in Java?**

Checked: must be declared in method signature and handled by caller (e.g., `IOException`). Unchecked: don't need to be declared or handled (e.g., `NullPointerException`). Checked exceptions are for recoverable errors; unchecked for programming bugs.

---

**Q13: What is a try-finally block used for?**

The `finally` block executes regardless of whether an exception occurred. Used for cleanup: closing files, releasing locks, freeing resources. Runs even if there's a `return` in the `try` or `catch`.

---

### I/O and Encoding

**Q14: What is UTF-8? Why is it the most common encoding?**

UTF-8 is a variable-length Unicode encoding (1-4 bytes per character). It's dominant because: ASCII compatible, space-efficient for English text, self-synchronizing, byte-order independent, and supports all Unicode characters.

---

**Q15: What's the difference between text mode and binary mode for file I/O?**

Text mode: reads/writes characters, may translate line endings (`\r\n` ↔ `\n`), handles encoding. Binary mode: reads/writes raw bytes, no translation, preserves exact content.

---

## Intermediate

### Type Systems

**Q16: Explain structural vs nominal typing.**

Nominal: types are compatible based on declared names and inheritance (Java, C#). Structural: types are compatible based on their shape — if two types have the same methods/properties, they're compatible (TypeScript, Go interfaces).

---

**Q17: What are generics? Why use them?**

Generics let you write type-safe code that works with any type. They avoid code duplication while maintaining compile-time type safety. Example: `List<T>` works for any type `T` without casting.

---

**Q18: What is type erasure in Java?**

Java generics are implemented via type erasure — the type parameter is removed at runtime. `List<String>` and `List<Integer>` are both `List` at runtime. This means you can't do `instanceof` checks on generic types or create arrays of generic types.

---

**Q19: What is duck typing?**

An object's suitability is determined by the presence of certain methods/properties, not its actual type. "If it has the right methods, it works." Common in Python, JavaScript. TypeScript's structural typing is a type-safe form of duck typing.

---

**Q20: Explain the difference between strong and weak typing.**

Strong typing: the language prevents mixing types without explicit conversion (Python, Rust). Weak typing: the language implicitly converts types to make operations work (JavaScript: `"5" - 3` → `2`).

---

### Memory Model

**Q21: What is a dangling pointer? How do different languages handle it?**

A pointer to memory that has been freed. C/C++: undefined behavior (your responsibility). Rust: compile-time error (borrow checker). Java/Python: impossible (GC manages lifetime).

---

**Q22: Explain smart pointers in C++. When would you use each?**

`unique_ptr`: exclusive ownership, can't be copied (use for single-owner resources). `shared_ptr`: shared ownership with reference counting (use when multiple owners needed). `weak_ptr`: non-owning reference (use to break circular references).

---

**Q23: How does garbage collection work? Explain mark and sweep.**

Start from root references (stack, globals). Trace and mark all reachable objects. Sweep (free) all unmarked objects. Modern GCs are generational: collect short-lived objects (young generation) more frequently than long-lived ones.

---

**Q24: What is RAII?**

Resource Acquisition Is Initialization. Tie resource lifetime to object lifetime — acquire in constructor, release in destructor. Ensures cleanup even during exceptions. C++ uses RAII for files (`ifstream`), locks (`lock_guard`), memory (`unique_ptr`).

---

**Q25: What is memory fragmentation?**

When free memory is split into small non-contiguous blocks. External fragmentation: enough total free space but no single block is large enough. Internal fragmentation: allocated block is larger than needed. Defragmentation or memory pools can help.

---

### Functions and Closures

**Q26: What is tail recursion? Why does it matter?**

When the recursive call is the last operation in a function. Enables tail call optimization (TCO) — the compiler converts it to a loop, using O(1) stack space. Important for performance with deep recursion. Not all languages guarantee TCO.

---

**Q27: What is currying? Give an example.**

Transforming a function `f(a, b, c)` into `f(a)(b)(c)`. Each partial application returns a new function. Example: `const add = a => b => a + b; const add5 = add(5); add5(3); // 8`.

---

**Q28: Explain pass by value vs pass by reference vs pass by sharing.**

Pass by value: copy the data (C, Go). Pass by reference: alias to the original (C++ `&`). Pass by sharing: copy the reference/pointer (Java, Python) — mutations to the object affect the original, but rebinding the parameter doesn't.

---

### Error Handling

**Q29: What is the `?` operator in Rust?**

Shorthand for "if this Result is Err, return it from the current function." Propagates errors concisely, replacing verbose match statements. Example: `let content = fs::read_to_string(path)?;`.

---

**Q30: What's the difference between exceptions and Result types?**

Exceptions: hidden control flow, not in function signature, can be forgotten. Result types: explicit in signature, compiler enforces handling, no hidden flow. Result types are more verbose but safer.

---

### Modules and Packages

**Q31: What is a lock file? Why is it important?**

A file that pins exact versions of all dependencies (including transitive). Ensures reproducible builds — the same versions are installed everywhere. Protects against unexpected dependency updates breaking your code.

---

**Q32: Explain semantic versioning.**

MAJOR.MINOR.PATCH. Major: breaking changes. Minor: new features (backward compatible). Patch: bug fixes. Helps consumers understand the risk of upgrading. `^1.2.3` means "compatible with 1.x."

---

## Advanced

### Type Systems Deep Dive

**Q33: What are algebraic data types? Explain product types and sum types.**

Product types (AND): combine multiple types — a struct has field1 AND field2. Sum types (OR): a value is one of several variants — an enum is variant1 OR variant2. Rust's `enum` is a sum type. Together they can model any data structure.

```rust
enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
}
// Shape is Circle(f64) OR Rectangle(f64, f64)
```

---

**Q34: Explain variance in type systems.**

Variance describes how subtyping relates to complex types:
- **Covariant**: `List<Dog>` is a subtype of `List<Animal>`
- **Contravariant**: `Consumer<Animal>` is a subtype of `Consumer<Dog>`
- **Invariant**: `List<Dog>` is NOT related to `List<Animal>`

Java arrays are covariant (unsafe!). Generics are invariant (safe). `? extends T` is covariant; `? super T` is contravariant (PECS: Producer Extends, Consumer Super).

---

**Q35: What is a dependent type?**

A type that depends on a value. Example: `Vector<n, T>` is a vector of exactly `n` elements of type `T`. The length is part of the type, enabling compile-time bounds checking. Languages: Idris, Agda, Lean. Limited forms in TypeScript (template literal types).

---

### Memory Model Deep Dive

**Q36: Explain Rust's ownership model. How does it prevent memory bugs?**

Every value has exactly one owner. When the owner goes out of scope, the value is dropped (freed). Borrowing (`&T`, `&mut T`) allows temporary access without transfer. Rules: one mutable XOR many immutable borrows. This prevents: use-after-free, double-free, data races — all at compile time, without GC.

---

**Q37: What is a memory leak in a garbage-collected language?**

When objects are technically reachable but semantically unused. Examples: forgotten event listeners, growing caches, circular references (in reference-counting GC), static collections that grow. GC can't collect these because they're still referenced.

---

**Q38: Explain the difference between `malloc`/`free` and `new`/`delete` in C++.**

`malloc`/`free`: C-style, allocates raw memory, doesn't call constructors/destructors. `new`/`delete`: C++-style, allocates memory AND calls constructor/destructor. Mixing them is undefined behavior. Better yet: use smart pointers.

---

**Q39: What is a memory-mapped file?**

A file mapped directly into virtual memory. Reading/writing the memory region reads/writes the file. Benefits: efficient for large files (OS handles paging), shared memory between processes, simpler API than read/write.

---

### Advanced Error Handling

**Q40: What is error wrapping? Why is it useful?**

Encapsulating a lower-level error in a higher-level error while preserving the original cause. Creates a chain: "Failed to load config → File not found: config.toml". Provides context without losing detail. Rust's `From` trait and `?` operator support this.

---

**Q41: What is a monadic error handling pattern?**

Using monads (like `Result` or `Option`) to chain operations that might fail. Each operation returns a monad; chaining short-circuits on error. This is what Rust's `?` and Haskell's `do` notation do under the hood.

```haskell
processFile :: FilePath -> IO (Either Error String)
processFile path = do
    content <- readFile path        -- could fail
    parsed  <- parse content        -- could fail
    return (transform parsed)       -- chain continues only if all succeed
```

---

### Advanced Functions

**Q42: What is referential transparency?**

An expression is referentially transparent if it can be replaced with its value without changing program behavior. `2 + 2` is referentially transparent (always 4). `getRandomNumber()` is not. Pure functions are always referentially transparent.

---

**Q43: What is the difference between `call`, `apply`, and `bind` in JavaScript?**

`call`: invokes function with explicit `this`, arguments passed individually. `apply`: same but arguments as array. `bind`: returns a new function with `this` permanently bound. All are ways to control what `this` refers to.

```javascript
function greet(greeting) { return `${greeting}, ${this.name}`; }
greet.call({name: "Alice"}, "Hi");     // "Hi, Alice"
greet.apply({name: "Alice"}, ["Hi"]);  // "Hi, Alice"
const greetAlice = greet.bind({name: "Alice"});
greetAlice("Hi");                       // "Hi, Alice"
```

---

**Q44: What is continuation-passing style (CPS)?**

A style where functions don't return values — instead, they take a "continuation" (callback) that receives the result. All control flow is expressed through function calls. Enables async patterns and non-blocking I/O.

```javascript
// Direct style
function add(a, b) { return a + b; }

// CPS
function add(a, b, cont) { cont(a + b); }
add(1, 2, result => console.log(result));
```

---

### Advanced I/O and Serialization

**Q45: What is the difference between serialization formats? When would you choose each?**

JSON: human-readable, widely supported, good for APIs. XML: verbose but has schemas (XSD), good for documents. Protobuf: binary, compact, fast, good for gRPC/internal services. MessagePack: binary JSON alternative. YAML: human-readable config files.

---

**Q46: What are zero-copy deserialization techniques?**

Techniques that avoid copying data during deserialization. Examples: `mmap` + cast, Cap'n Proto, FlatBuffers, Rust's `serde` with `&str` references. The key insight: instead of parsing into new objects, point directly into the serialized buffer.

---

### Advanced Module Systems

**Q47: What is tree shaking?**

A dead-code elimination technique used by bundlers. It analyzes import/export graph and removes unused exports from the final bundle. Requires ESM (static imports) — doesn't work with CommonJS `require()`. Webpack, Rollup, esbuild all support it.

---

**Q48: What is the difference between a library and a framework?**

Library: you call the library's code (inversion of control is yours). Framework: the framework calls your code (inversion of control is the framework's — "Hollywood Principle: Don't call us, we'll call you"). React is a library; Angular is a framework.

---

### Cross-Cutting Advanced Questions

**Q49: Explain the difference between equality and identity.**

Equality: two values are the same (same content). Identity: two references point to the same object (same memory address). `[1,2,3] == [1,2,3]` is true (equality), but `a = [1,2,3]; b = a; a is b` is true only for identity.

---

**Q50: What is immutability? Why is it important?**

An immutable value cannot be changed after creation. Benefits: thread safety (no data races), easier reasoning (no hidden state changes), hash stability (can be dictionary keys), cache friendly. Languages like Rust default to immutability; functional languages enforce it.

---

**Q51: What is an expression vs a statement?**

An expression produces a value (`2 + 3`, `x > 5`, `functionCall()`). A statement performs an action but doesn't produce a value (`if`, `while`, `return`, variable declarations in some languages). In expression-based languages (Rust, Kotlin), most things are expressions.

```rust
// Rust: if is an expression
let x = if condition { 5 } else { 10 };

// C: if is a statement
// int x = if (condition) 5 else 10;  // ERROR
```

---

**Q52: What is short-circuit evaluation?**

Logical operators stop evaluating as soon as the result is determined. `A && B`: if A is false, B is not evaluated. `A || B`: if A is true, B is not evaluated. Used for guard clauses: `obj && obj.method()`.

---

**Q53: Explain the difference between concurrency and parallelism.**

Concurrency: dealing with multiple things at once (interleaving). Parallelism: doing multiple things at once (simultaneous execution). Concurrency is about structure; parallelism is about execution. You can have concurrency without parallelism (single-core multitasking).

---

**Q54: What is a pure function?**

A function that: (1) always returns the same output for the same input, (2) has no side effects (doesn't modify external state, I/O, etc.). Pure functions are easy to test, cache, parallelize, and reason about.

---

**Q55: What is the difference between an interface and an abstract class?**

Interface: defines a contract (method signatures), no implementation (traditionally), multiple inheritance allowed. Abstract class: can have implementation, state, constructors, single inheritance. Use interfaces for capabilities; abstract classes for shared implementation.
