# Type Systems

> The type system is a language's first line of defense — catching errors before your code ever runs.

## 1. Static vs Dynamic Typing

### Static Typing

Types are checked at **compile time**. Variables have declared types that don't change.

```java
int x = 10;
x = "hello";  // compile error!

String s = 42;  // compile error!
```

```rust
let x: i32 = 10;
// x = "hello";  // compile error!

fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

### Dynamic Typing

Types are checked at **runtime**. Variables can hold any type.

```python
x = 10
x = "hello"    # fine — x just holds a different object
x = [1, 2, 3]  # also fine

def add(a, b):
    return a + b

add(1, 2)       # 3
add("hi", "!")  # "hi!"
add(1, "hi")    # TypeError at runtime
```

```javascript
let x = 10;
x = "hello";    // fine
x = [1, 2, 3];  // fine
```

### Comparison Table

| Aspect | Static | Dynamic |
|--------|--------|---------|
| Type checking | Compile time | Runtime |
| Error detection | Before running | During execution |
| Performance | Generally faster | Generally slower (type overhead) |
| Code verbosity | More verbose (type annotations) | Less verbose |
| Refactoring safety | Compiler catches type mismatches | Tests catch them |
| IDE support | Excellent (autocomplete, error detection) | Good but limited |
| Flexibility | Less flexible | More flexible |
| Examples | Java, C++, Rust, Go, TypeScript | Python, JavaScript, Ruby, Lua |

### Gradual Typing

Some languages support both:

```typescript
// TypeScript: static typing on top of JavaScript
function add(a: number, b: number): number {
    return a + b;
}

// Can opt out with 'any'
let flexible: any = 10;
flexible = "hello";  // no error
```

```python
# Python: type hints (PEP 484) — not enforced at runtime
def add(a: int, b: int) -> int:
    return a + b

add("hi", "!")  # no error at runtime! (mypy would catch it)
```

## 2. Strong vs Weak Typing

### Strong Typing

The language prevents you from mixing types without explicit conversion.

```python
# Python: strongly typed
"hello" + 42  # TypeError!
"hello" + str(42)  # "hello42" — explicit conversion required
```

```rust
// Rust: strongly typed
let x: i32 = 5;
let y: f64 = 3.14;
// let z = x + y;  // compile error!
let z = x as f64 + y;  // explicit cast
```

### Weak Typing

The language implicitly converts types to make operations work.

```javascript
// JavaScript: weakly typed
"hello" + 42     // "hello42" — number coerced to string
"5" - 3          // 2 — string coerced to number
"5" + 3          // "53" — number coerced to string (different rule!)
true + true      // 2
[] + {}           // "[object Object]"
{} + []           // 0
```

```c
// C: weakly typed
int x = 5;
double y = 3.14;
double z = x + y;  // x implicitly converted to double

char c = 65;
printf("%c", c);   // prints 'A' (ASCII)
```

### Strong vs Weak Spectrum

| Language | Strength | Notes |
|----------|----------|-------|
| Python | Strong | No implicit type coercion |
| Java | Strong | Strict, but has widening conversions |
| Rust | Strong | No implicit conversions |
| Go | Strong | No implicit conversions |
| C | Weak | Implicit conversions everywhere |
| JavaScript | Very Weak | Aggressive coercion |
| PHP | Very Weak | `"0"` is falsy! |

## 3. Duck Typing

> "If it walks like a duck and quacks like a duck, it's a duck."

In duck-typed languages, what matters is what an object *can do*, not what it *is*.

```python
# Python: duck typing
class Dog:
    def speak(self):
        return "Woof!"

class Cat:
    def speak(self):
        return "Meow!"

class Duck:
    def speak(self):
        return "Quack!"

def make_it_speak(animal):
    return animal.speak()  # doesn't care about the type

make_it_speak(Dog())   # "Woof!"
make_it_speak(Cat())   # "Meow!"
make_it_speak(Duck())  # "Quack!"
```

```javascript
// JavaScript: duck typing
function getArea(shape) {
    return shape.width * shape.height;  // just needs these properties
}

getArea({ width: 10, height: 20 });     // 200
getArea({ width: 5, height: 3, color: "red" });  // 15
```

### Protocol / Interface Equivalents

```python
# Python: protocols (structural typing)
from typing import Protocol

class Speakable(Protocol):
    def speak(self) -> str: ...

def make_it_speak(animal: Speakable) -> str:
    return animal.speak()

# No need to explicitly implement Speakable
# Any class with a speak() method satisfies it
```

## 4. Structural vs Nominal Typing

### Nominal Typing

Types are compatible only if they have the same **name** (or explicit inheritance).

```java
// Java: nominal
interface Drawable {
    void draw();
}

class Circle implements Drawable {
    public void draw() { /* ... */ }
}

class Square {
    public void draw() { /* ... */ }
}

// Square can't be used as Drawable — it doesn't implement the interface
// Even though it has the exact same method
```

### Structural Typing

Types are compatible if they have the same **structure** (same methods/properties).

```typescript
// TypeScript: structural
interface Drawable {
    draw(): void;
}

class Circle {
    draw() { /* ... */ }
}

class Square {
    draw() { /* ... */ }
}

function render(shape: Drawable) {
    shape.draw();
}

render(new Circle());  // works!
render(new Square());  // works! Both have draw()
```

```go
// Go: structural (interfaces are implicit)
type Reader interface {
    Read(p []byte) (n int, err error)
}

type MyFile struct { /* ... */ }
func (f MyFile) Read(p []byte) (int, error) { /* ... */ }

// MyFile satisfies Reader automatically — no 'implements' keyword
```

### Comparison

| Aspect | Nominal | Structural |
|--------|---------|------------|
| Compatibility | Based on declared names | Based on shape/structure |
| Explicit implementation | Required | Not required |
| Refactoring | Safer (changes break at interface) | More flexible |
| Examples | Java, C#, Rust (traits) | TypeScript, Go |
| Catch type errors | At declaration | At usage |

## 5. Generics and Templates

**Generics** let you write code that works with any type while maintaining type safety.

### Java Generics

```java
// Generic class
public class Box<T> {
    private T value;
    
    public Box(T value) { this.value = value; }
    public T getValue() { return value; }
}

Box<Integer> intBox = new Box<>(42);
Box<String> strBox = new Box<>("hello");

// Generic method
public static <T> List<T> filter(List<T> list, Predicate<T> predicate) {
    return list.stream().filter(predicate).collect(Collectors.toList());
}

// Bounded generics
public static <T extends Comparable<T>> T max(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}
```

### Rust Generics

```rust
// Generic function
fn largest<T: PartialOrd>(list: &[T]) -> &T {
    let mut largest = &list[0];
    for item in &list[1..] {
        if item > largest {
            largest = item;
        }
    }
    largest
}

// Generic struct
struct Point<T> {
    x: T,
    y: T,
}

// Implementation for specific type
impl Point<f64> {
    fn distance_from_origin(&self) -> f64 {
        (self.x.powi(2) + self.y.powi(2)).sqrt()
    }
}
```

### C++ Templates

```cpp
// Function template
template <typename T>
T max(T a, T b) {
    return (a > b) ? a : b;
}

// Class template
template <typename T>
class Stack {
    std::vector<T> elements;
public:
    void push(T const& elem) { elements.push_back(elem); }
    T pop() {
        T elem = elements.back();
        elements.pop_back();
        return elem;
    }
};

// Template specialization
template <>
class Stack<std::string> {
    // specialized implementation for strings
};
```

### Generics vs Templates

| Aspect | Generics (Java, C#) | Templates (C++) |
|--------|---------------------|-----------------|
| Type checking | At definition (erasure) | At instantiation |
| Code generation | Single implementation (type erasure) | Separate code per type |
| Runtime cost | Boxing for primitives | None |
| Error messages | Clear | Often cryptic |
| Specialization | Limited | Full |

### Go Generics (1.18+)

```go
func Map[T any, U any](s []T, f func(T) U) []U {
    result := make([]U, len(s))
    for i, v := range s {
        result[i] = f(v)
    }
    return result
}

// Usage
doubled := Map([]int{1, 2, 3}, func(x int) int { return x * 2 })
```

## 6. Type Inference

The compiler deduces types without explicit annotations.

```rust
// Rust: full type inference
let x = 5;           // inferred as i32
let y = 3.14;        // inferred as f64
let v = vec![1, 2];  // inferred as Vec<i32>

// Sometimes you need to help
let parsed: i32 = "42".parse().unwrap();
```

```typescript
// TypeScript: type inference
let x = 5;           // inferred as number
let s = "hello";     // inferred as string
const arr = [1, 2];  // inferred as number[]

// Return type inferred
function add(a: number, b: number) {
    return a + b;  // inferred as number
}
```

```go
// Go: short variable declaration infers type
x := 5           // int
y := 3.14        // float64
s := "hello"     // string
```

```java
// Java: var (Java 10+)
var list = new ArrayList<String>();  // inferred as ArrayList<String>
var x = 5;                           // inferred as int
```

## 7. Type Conversion and Coercion

### Implicit Conversion (Coercion)

```javascript
// JavaScript coercion rules
"5" + 3     // "53" (number → string)
"5" - 3     // 2 (string → number)
true + 1    // 2 (boolean → number)
null + 1    // 1 (null → 0)
undefined + 1 // NaN
```

### Explicit Conversion (Casting)

```python
# Python
int("42")      # 42
float("3.14")  # 3.14
str(42)        # "42"
bool(0)        # False
bool("")       # False
bool([])       # False
```

```java
// Java
// Widening (safe, implicit)
int i = 42;
long l = i;         // OK
double d = i;       // OK

// Narrowing (lossy, explicit)
double d = 3.99;
int i = (int) d;    // 3 (truncation)
```

### Type Conversion Table

| From → To | Safe? | Example |
|-----------|-------|---------|
| int → float | ✅ | `float(5)` → `5.0` |
| float → int | ⚠️ | `int(3.7)` → `3` (truncation) |
| int → string | ✅ | `str(42)` → `"42"` |
| string → int | ⚠️ | `int("42")` → `42`, `int("hi")` → error |
| bool → int | ✅ | `int(True)` → `1` |
| int → bool | ⚠️ | `bool(0)` → `False`, `bool(1)` → `True` |

## 8. Algebraic Data Types

Some languages support **sum types** (tagged unions) in addition to **product types** (structs/tuples).

```rust
// Sum type (enum with data)
enum Shape {
    Circle(f64),             // radius
    Rectangle(f64, f64),     // width, height
    Triangle(f64, f64, f64), // three sides
}

fn area(shape: &Shape) -> f64 {
    match shape {
        Shape::Circle(r) => std::f64::consts::PI * r * r,
        Shape::Rectangle(w, h) => w * h,
        Shape::Triangle(a, b, c) => {
            let s = (a + b + c) / 2.0;
            (s * (s - a) * (s - b) * (s - c)).sqrt()
        }
    }
}
```

```haskell
-- Haskell
data Shape = Circle Double
           | Rectangle Double Double
           | Triangle Double Double Double

area :: Shape -> Double
area (Circle r) = pi * r * r
area (Rectangle w h) = w * h
```

## Interview Questions

1. **What's the difference between static and dynamic typing?**
   Static: types checked at compile time (Java, Rust). Dynamic: types checked at runtime (Python, JavaScript). Static catches errors earlier; dynamic is more flexible.

2. **What is duck typing?**
   An object's suitability is determined by the presence of certain methods and properties, not by its actual type. "If it has the right methods, it works."

3. **Explain structural vs nominal typing.**
   Nominal: types must have the same name/inheritance (Java interfaces). Structural: types must have the same shape (TypeScript interfaces, Go interfaces).

4. **What are generics? Why use them?**
   Generics let you write type-safe code that works with any type. They avoid code duplication while maintaining compile-time type safety.

5. **What is type erasure?**
   In Java generics, type parameters are erased at runtime — `List<String>` and `List<Integer>` are both `List` at runtime. This means you can't do `instanceof` checks on generic types.

6. **What's the difference between generics and templates?**
   Generics (Java): single implementation, type erased at runtime. Templates (C++): separate code generated for each type, no runtime cost but larger binaries and cryptic errors.

7. **Explain type inference.**
   The compiler deduces types from context without explicit annotations. Examples: Rust's `let x = 5`, TypeScript's `let x = 5`, Go's `x := 5`.

8. **What is an algebraic data type?**
   A composite type formed by combining other types. Product types (AND): structs/tuples. Sum types (OR): tagged unions/enums. Rust's `enum` is a sum type.
