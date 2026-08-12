# Variables and Types

> Understanding how data is stored, named, and typed is the foundation of all programming.

## 1. Variables

A **variable** is a named reference to a value stored in memory. It combines three things:

- **Name** (identifier) — how you refer to it
- **Type** — what kind of data it holds
- **Value** — the actual data

### Declaration vs Initialization

```c
int x;          // declaration — allocates space, value is undefined
int y = 10;     // declaration + initialization
```

```python
y = 10          # Python: declaration and initialization are the same
```

### Naming Conventions

| Convention | Example | Common In |
|------------|---------|-----------|
| camelCase | `myVariable` | Java, JavaScript, Go |
| snake_case | `my_variable` | Python, Rust, C |
| PascalCase | `MyVariable` | C#, TypeScript (types) |
| UPPER_SNAKE | `MAX_SIZE` | Constants (most languages) |
| kebab-case | `my-variable` | CSS, Lisp, CLI flags |

## 2. Constants

A **constant** is a named value that cannot be changed after assignment.

```java
final int MAX_RETRIES = 3;       // Java
const PI: f64 = 3.14159;         // Rust
const MAX_SIZE = 100;            // Go
#define BUFFER_SIZE 1024          // C preprocessor (not a true constant)
```

### Constants vs Immutable Variables

| Feature | Constant | Immutable Variable |
|---------|----------|--------------------|
| Value known at compile time? | Yes (usually) | Not necessarily |
| Can be computed at runtime? | Rarely | Yes |
| Memory allocated? | May be inlined | Yes |
| Example (Rust) | `const X: i32 = 5;` | `let x = compute();` |

## 3. Literals

A **literal** is a value written directly in source code.

```python
42              # integer literal
3.14            # float literal
"hello"         # string literal
True            # boolean literal
None            # null literal
[1, 2, 3]       # list literal
{"key": "val"}  # dictionary literal
```

### Literal Types Across Languages

| Type | Python | Java | JavaScript | Rust | C++ |
|------|--------|------|------------|------|-----|
| Integer | `42` | `42` | `42` | `42i32` | `42` |
| Float | `3.14` | `3.14f` | `3.14` | `3.14f64` | `3.14` |
| String | `"hi"` | `"hi"` | `"hi"` | `"hi"` | `"hi"` |
| Char | N/A | `'a'` | N/A | `'a'` | `'a'` |
| Boolean | `True` | `true` | `true` | `true` | `true` |
| Null | `None` | `null` | `null` | `None` (Option) | `nullptr` |

## 4. Primitive Types

**Primitive types** (also called scalar or basic types) are built into the language and map directly to hardware representations.

### Common Primitive Types

| Type | Description | Size (typical) | Range |
|------|-------------|----------------|-------|
| `bool` | Boolean | 1 byte | `true` / `false` |
| `char` | Character | 1-4 bytes | Depends on encoding |
| `int8` / `byte` | Signed 8-bit | 1 byte | -128 to 127 |
| `uint8` / `ubyte` | Unsigned 8-bit | 1 byte | 0 to 255 |
| `int16` / `short` | Signed 16-bit | 2 bytes | -32,768 to 32,767 |
| `int32` / `int` | Signed 32-bit | 4 bytes | ~±2.1 billion |
| `int64` / `long` | Signed 64-bit | 8 bytes | ~±9.2 × 10¹⁸ |
| `float32` / `float` | Single precision | 4 bytes | ~7 decimal digits |
| `float64` / `double` | Double precision | 8 bytes | ~15 decimal digits |

### Integer Overflow

```c
// C: overflow is undefined behavior for signed integers
int x = INT_MAX;  // 2,147,483,647
x + 1;            // undefined behavior!

// Rust: panics in debug, wraps in release
let x: i32 = i32::MAX;
// x + 1; // panics in debug mode
x.wrapping_add(1);  // explicit wrapping: -2147483648
```

### Floating Point Gotchas

```python
0.1 + 0.2 == 0.3  # False! → 0.30000000000000004

# Why? 0.1 in binary is a repeating fraction:
# 0.0001100110011... (repeating)
# Cannot be represented exactly in IEEE 754

# Solution: use tolerance
abs(0.1 + 0.2 - 0.3) < 1e-9  # True

# Or use decimal types
from decimal import Decimal
Decimal('0.1') + Decimal('0.2') == Decimal('0.3')  # True
```

## 5. Reference Types

**Reference types** store a reference (pointer) to data, not the data itself.

```java
// Java: String is a reference type
String a = "hello";
String b = a;        // b points to the same String object
b = "world";         // b now points to a new object; a still "hello"

// Arrays are reference types
int[] arr1 = {1, 2, 3};
int[] arr2 = arr1;   // arr2 points to the same array
arr2[0] = 99;        // arr1[0] is also 99!
```

### Common Reference Types

| Type | Examples |
|------|----------|
| Strings | `String` (Java), `std::string` (C++), objects in JS |
| Arrays | Most language arrays (except C fixed arrays on stack) |
| Objects | Classes, structs (in most languages) |
| Collections | Lists, maps, sets |

## 6. Value vs Reference Semantics

This is one of the most important distinctions in programming.

### Value Semantics

Copying a variable creates an independent copy. Modifications to the copy don't affect the original.

```go
// Go: all types have value semantics
a := []int{1, 2, 3}
b := a              // b is a copy of a (for slices, the header is copied)
b[0] = 99           // actually affects a because slices share backing array!

// True value copy:
b := make([]int, len(a))
copy(b, a)
b[0] = 99           // a is unaffected
```

```rust
// Rust: move semantics by default
let s1 = String::from("hello");
let s2 = s1;        // s1 is MOVED, not copied — s1 is no longer valid
// println!("{}", s1);  // compile error!

let s1 = String::from("hello");
let s2 = s1.clone();  // explicit deep copy
println!("{}", s1);    // works fine
```

### Reference Semantics

Copying a variable copies the reference, not the data. Both variables point to the same object.

```python
# Python: everything is a reference
a = [1, 2, 3]
b = a              # b references the same list
b[0] = 99          # a[0] is also 99

# True copy:
b = a.copy()       # or list(a) or a[:]
b[0] = 99          # a is unaffected
```

### Comparison Table

| Language | Default Semantics | Primitives | Objects/Composites |
|----------|------------------|------------|-------------------|
| C | Value | Value | Value (structs) / Pointer |
| C++ | Value | Value | Value (can use pointers/refs) |
| Java | Reference for objects | Value | Reference |
| Python | Reference (name binding) | Reference | Reference |
| Go | Value | Value | Value (but slices/maps have internal pointers) |
| Rust | Move | Copy (if `Copy` trait) | Move (explicit `clone()` for deep copy) |
| JavaScript | Value for primitives | Value | Reference |

## 7. Stack vs Heap

Understanding where data lives is crucial for performance and correctness.

### Stack

- **Fast** — LIFO order, just moves a pointer
- **Automatic** — memory freed when scope exits
- **Limited** — typically 1-8 MB per thread
- **Used for** — local variables, function parameters, return addresses

### Heap

- **Slower** — requires allocation/deallocation
- **Manual or GC** — you manage it or the runtime does
- **Large** — limited by available RAM
- **Used for** — dynamically sized data, objects with unknown lifetime

### What Goes Where?

```c
void foo() {
    int x = 42;                    // stack
    int arr[10];                   // stack
    int *p = malloc(10 * sizeof(int)); // heap
    char *s = "hello";             // string literal (often read-only data segment)
    free(p);
}
```

```java
void foo() {
    int x = 42;          // stack (local primitive)
    String s = "hello";  // reference on stack, object in heap
    int[] arr = new int[10]; // reference on stack, array in heap
}
```

### Memory Layout

```
┌─────────────────────┐ High address
│       Stack         │ ← grows downward
│         ↓           │
│                     │
│    (free space)     │
│                     │
│         ↑           │
│       Heap          │ ← grows upward
├─────────────────────┤
│   Static/Global     │
├─────────────────────┤
│   Code (Text)       │
└─────────────────────┘ Low address
```

## 8. Mutability and Immutability

### Immutable by Default

Some languages make immutability the default:

```rust
// Rust: immutable by default
let x = 5;
// x = 6;  // compile error!
let mut y = 5;
y = 6;     // fine
```

```kotlin
// Kotlin: val (immutable) vs var (mutable)
val name = "Alice"   // immutable
// name = "Bob"      // compile error!
var age = 30         // mutable
age = 31             // fine
```

### Mutable by Default

```python
# Python: everything is mutable (except tuples, strings, frozensets)
x = 5
x = 6  # fine (rebinding, not mutation)

s = "hello"
# s[0] = "H"  # error! strings are immutable
s = "Hello"    # rebinding to a new string
```

### Why Immutability Matters

| Benefit | Explanation |
|---------|-------------|
| Thread safety | No data races if data can't change |
| Easier reasoning | No hidden state changes |
| Hash stability | Immutable objects can be dictionary keys |
| Cache friendly | No need to track changes |

## 9. Type Conversion and Casting

### Implicit Conversion (Coercion)

```python
x = 5      # int
y = 2.0    # float
z = x + y  # 7.0 — int implicitly converted to float
```

### Explicit Conversion (Casting)

```c
double d = 3.14;
int i = (int)d;      // 3 — truncation
```

```java
int i = 10;
long l = i;           // implicit widening
// int j = l;         // compile error — must cast
int j = (int) l;      // explicit narrowing
```

### Dangerous Conversions

```c
// C: narrowing can silently lose data
int big = 300;
char c = (char)big;   // 44 — silent truncation!

// Signed/unsigned confusion
unsigned int u = -1;  // wraps to UINT_MAX
```

## Interview Questions

1. **What's the difference between a variable and a constant?**
   A variable's value can change; a constant's cannot. Constants may be computed at compile time and inlined.

2. **Explain value vs reference semantics. Give examples.**
   Value semantics: copying copies the data. Reference semantics: copying copies a pointer to the data. C++ structs are value; Java objects are reference.

3. **Why does `0.1 + 0.2 != 0.3` in most languages?**
   IEEE 754 floating point cannot exactly represent 0.1 (it's a repeating fraction in binary). The accumulated rounding error produces 0.30000000000000004.

4. **What's the difference between stack and heap allocation?**
   Stack is fast, automatic, limited-size. Heap is slower, manually managed (or GC'd), large. Local variables go on stack; dynamically sized data goes on heap.

5. **What is integer overflow? Is it the same in all languages?**
   When an integer exceeds its type's range. In C/C++, signed overflow is undefined behavior. In Java, it wraps around. In Rust, it panics in debug mode.

6. **Why does Rust use move semantics instead of copy by default?**
   To prevent double-free errors and ensure memory safety without a garbage collector. You must explicitly `.clone()` for deep copies.

7. **What's the difference between `const` and `final` and `readonly`?**
   `const` (C#/C++) is compile-time. `final` (Java) means cannot be reassigned. `readonly` (C#) is set once at runtime. They serve similar purposes with different nuances.

8. **Why might you prefer immutable data structures?**
   Thread safety, easier reasoning about code, hash stability, cache friendliness, functional programming paradigms.
