# Templates

## What Are Templates?

Templates are C++'s mechanism for **generic programming** — writing code that works with arbitrary types without sacrificing type safety or performance. Unlike Java generics (type-erased at runtime) or Python duck typing (resolved at runtime), C++ templates are resolved entirely at **compile time** through a process called **monomorphization** — the compiler generates a separate copy of the template for each type used.

This gives C++ templates zero runtime overhead but can increase compile times and binary size.

## Function Templates

A function template defines a family of functions parameterized by one or more types:

```cpp
// Basic function template
template <typename T>
T maximum(const T& a, const T& b) {
    return (a > b) ? a : b;
}

// Usage — compiler deduces T
int x = maximum(3, 7);            // T = int
double y = maximum(3.14, 2.71);   // T = double
std::string s = maximum("abc"s, "def"s);  // T = std::string

// Explicit template argument
auto z = maximum<double>(3, 4.5);  // T = double, promotes 3 to 3.0
```

### Multiple Template Parameters

```cpp
// Two independent type parameters
template <typename T, typename U>
auto add(const T& a, const U& b) -> decltype(a + b) {
    return a + b;
}

// T = int, U = double → return type is double
auto result = add(3, 4.5);
```

### Non-Type Template Parameters

Templates can also take compile-time values, not just types:

```cpp
template <typename T, int N>
class FixedArray {
    T data_[N];  // size known at compile time
public:
    constexpr int size() const { return N; }
    T& operator[](int i) { return data_[i]; }
    const T& operator[](int i) const { return data_[i]; }
};

FixedArray<int, 10> arr;  // array of 10 ints, no heap allocation
```

## Class Templates

Class templates define blueprint for classes parameterized by types:

```cpp
template <typename T>
class Stack {
    std::vector<T> elements_;
public:
    void push(const T& elem) { elements_.push_back(elem); }
    void push(T&& elem) { elements_.push_back(std::move(elem)); }
    void pop() { elements_.pop_back(); }
    const T& top() const { return elements_.back(); }
    bool empty() const { return elements_.empty(); }
    size_t size() const { return elements_.size(); }
};

// Must specify type when using (unless CTAD in C++17)
Stack<int> intStack;
Stack<std::string> strStack;

// C++17: Class Template Argument Deduction (CTAD)
Stack s;  // Error: can't deduce T
Stack s2{std::vector{1, 2, 3}};  // Still needs deduction guide usually
```

### Template Default Arguments

```cpp
template <typename T, typename Container = std::vector<T>>
class Stack {
    Container elements_;
public:
    void push(const T& elem) { elements_.push_back(elem); }
    void pop() { elements_.pop_back(); }
    const T& top() const { return elements_.back(); }
};

Stack<int> s1;                      // uses std::vector<int>
Stack<int, std::deque<int>> s2;     // uses std::deque<int>
```

## Template Specialization

When the generic template doesn't work for a specific type, you can specialize it:

### Full Specialization

```cpp
// Generic template
template <typename T>
class Printer {
public:
    void print(const T& val) { std::cout << val; }
};

// Full specialization for bool
template <>
class Printer<bool> {
public:
    void print(bool val) { std::cout << (val ? "true" : "false"); }
};

// Full specialization for std::vector<T>
template <typename T>
class Printer<std::vector<T>> {
public:
    void print(const std::vector<T>& vec) {
        std::cout << "[";
        for (size_t i = 0; i < vec.size(); ++i) {
            if (i > 0) std::cout << ", ";
            std::cout << vec[i];
        }
        std::cout << "]";
    }
};
```

### Partial Specialization

```cpp
// Generic
template <typename T, typename U>
class Pair {
    T first_;
    U second_;
public:
    Pair(const T& f, const U& s) : first_(f), second_(s) {}
    void print() { std::cout << first_ << ", " << second_ << "\n"; }
};

// Partial specialization: both types are the same
template <typename T>
class Pair<T, T> {
    T first_;
    T second_;
public:
    Pair(const T& a, const T& b) : first_(a), second_(b) {}
    void print() { std::cout << "Same type: " << first_ << ", " << second_ << "\n"; }
};
```

> **Note:** Function templates cannot be partially specialized. Use overloading instead.

## Variadic Templates (C++11)

Variadic templates accept an arbitrary number of template arguments using **parameter packs**:

```cpp
// Base case — no arguments
void print() {
    std::cout << "\n";
}

// Recursive case — at least one argument
template <typename T, typename... Args>
void print(const T& first, const Args&... args) {
    std::cout << first;
    if constexpr (sizeof...(args) > 0) {
        std::cout << ", ";
    }
    print(args...);  // recursively unpack remaining args
}

print(1, "hello", 3.14, 'c');  // Output: 1, hello, 3.14, c
```

### Fold Expressions (C++17)

C++17 simplifies variadic operations with fold expressions:

```cpp
// Sum all arguments
template <typename... Args>
auto sum(Args... args) {
    return (args + ...);  // unary right fold
}

sum(1, 2, 3, 4, 5);  // 15

// Check if any argument matches
template <typename T, typename... Args>
bool contains(const T& target, const Args&... args) {
    return ((args == target) || ...);  // unary right fold with ||
}

// Print all with separator
template <typename... Args>
void printAll(const Args&... args) {
    ((std::cout << args << " "), ...);  // comma fold
    std::cout << "\n";
}
```

## SFINAE (Substitution Failure Is Not An Error)

SFINAE is a core template mechanism: if substituting template parameters fails, the compiler silently removes that overload instead of issuing an error.

```cpp
// Enable this overload only if T supports +
template <typename T>
auto add(const T& a, const T& b) -> decltype(a + b) {
    return a + b;
}

// This overload is selected for types without +
template <typename T, typename = void>
struct supports_add : std::false_type {};

template <typename T>
struct supports_add<T, std::void_t<decltype(std::declval<T>() + std::declval<T>())>> : std::true_type {};

template <typename T>
std::enable_if_t<!supports_add<T>::value, std::string>
add(const T&, const T&) {
    return "unsupported";
}
```

### `std::enable_if`

The most common SFINAE tool — conditionally enable/disable overloads:

```cpp
#include <type_traits>

// Only enabled for integral types
template <typename T>
std::enable_if_t<std::is_integral_v<T>, T>
safeDivide(T a, T b) {
    if (b == 0) throw std::runtime_error("Division by zero");
    return a / b;
}

// Only enabled for floating-point types
template <typename T>
std::enable_if_t<std::is_floating_point_v<T>, T>
safeDivide(T a, T b) {
    return a / b;  // floating-point division by zero produces inf, not UB
}
```

### Detection Idiom

```cpp
// Detect if a type has a size() method
template <typename T, typename = void>
struct has_size : std::false_type {};

template <typename T>
struct has_size<T, std::void_t<decltype(std::declval<T>().size())>> : std::true_type {};

// Usage
static_assert(has_size<std::vector<int>>::value);   // true
static_assert(!has_size<int>::value);                 // false
```

## Concepts (C++20)

Concepts are the modern replacement for SFINAE — cleaner syntax, better error messages:

```cpp
#include <concepts>

// Define a concept
template <typename T>
concept Numeric = std::integral<T> || std::floating_point<T>;

// Use concept as a constraint
template <Numeric T>
T square(T x) { return x * x; }

// Alternative syntax (requires clause)
template <typename T>
    requires Numeric<T>
T cube(T x) { return x * x * x; }

// Abbreviated syntax (C++20)
auto abs_val(Numeric auto x) { return x < 0 ? -x : x; }
```

### Writing Custom Concepts

```cpp
// Concept: type has a begin() and end() (i.e., is iterable)
template <typename T>
concept Iterable = requires(T t) {
    { t.begin() } -> std::input_or_output_iterator;
    { t.end() } -> std::input_or_output_iterator;
};

// Concept: type is hashable
template <typename T>
concept Hashable = requires(T t) {
    { std::hash<T>{}(t) } -> std::convertible_to<std::size_t>;
};

// Compound concept
template <typename T>
concept Printable = requires(std::ostream& os, T t) {
    { os << t } -> std::same_as<std::ostream&>;
};
```

### `requires` Expressions

```cpp
template <typename T>
concept Sortable = requires(T a, T b) {
    { a < b } -> std::convertible_to<bool>;  // must support <
    { a == b } -> std::convertible_to<bool>;  // must support ==
};

// Nested requirements
template <typename T>
concept Container = requires(T t) {
    typename T::value_type;         // must have value_type
    typename T::iterator;           // must have iterator
    { t.size() } -> std::integral;  // size() returns integral
    { t.begin() } -> std::same_as<typename T::iterator>;
};
```

## Template Metaprogramming (TMP)

Templates are Turing-complete at compile time — you can compute anything during compilation:

### Compile-Time Factorial

```cpp
template <int N>
struct Factorial {
    static constexpr int value = N * Factorial<N - 1>::value;
};

template <>
struct Factorial<0> {
    static constexpr int value = 1;
};

static_assert(Factorial<5>::value == 120);
static_assert(Factorial<10>::value == 3628800);
```

### Type Traits (Compile-Time Type Inspection)

```cpp
// Is type a pointer?
template <typename T>
struct is_pointer : std::false_type {};

template <typename T>
struct is_pointer<T*> : std::true_type {};

// Remove const from a type
template <typename T>
struct remove_const { using type = T; };

template <typename T>
struct remove_const<const T> { using type = T; };

// Usage
static_assert(is_pointer<int*>::value);
static_assert(!is_pointer<int>::value);
static_assert(std::is_same_v<remove_const<const int>::type, int>);
```

### Compile-Time If (`if constexpr`, C++17)

```cpp
template <typename T>
auto convert(T val) {
    if constexpr (std::is_integral_v<T>) {
        return static_cast<double>(val);  // only compiled for integral types
    } else if constexpr (std::is_floating_point_v<T>) {
        return static_cast<int>(val);     // only compiled for floating-point types
    } else {
        return val;                       // fallback
    }
}
```

## CRTP (Curiously Recurring Template Pattern)

CRTP is a pattern where a class derives from a template specialization of itself:

```cpp
// Base class provides functionality using derived class type
template <typename Derived>
class Counter {
    static inline int count_ = 0;
public:
    Counter() { ++count_; }
    Counter(const Counter&) { ++count_; }
    ~Counter() { --count_; }
    
    static int getCount() { return count_; }
    
    // Static polymorphism — no virtual function overhead
    void identify() const {
        static_cast<const Derived*>(this)->doIdentify();
    }
};

class Dog : public Counter<Dog> {
public:
    void doIdentify() const { std::cout << "I am a Dog\n"; }
};

class Cat : public Counter<Cat> {
public:
    void doIdentify() const { std::cout << "I am a Cat\n"; }
};

// Usage
Dog d1, d2;
Cat c1;
std::cout << Dog::getCount();  // 2
std::cout << Cat::getCount();  // 1
d1.identify();  // "I am a Dog" — resolved at compile time!
```

### CRTP for Interface Enforcement

```cpp
template <typename Derived>
class Serializable {
public:
    std::string serialize() const {
        return static_cast<const Derived*>(this)->doSerialize();
    }
    // If Derived doesn't implement doSerialize(), you get a compile error
};

class User : public Serializable<User> {
    std::string name_;
public:
    explicit User(std::string name) : name_(std::move(name)) {}
    std::string doSerialize() const { return "User:" + name_; }
};
```

## Template Compilation Model

Templates are **not compiled until instantiated**. This has implications:

### Why Template Definitions Go in Headers

```cpp
// my_template.h — declaration AND definition
template <typename T>
class MyContainer {
    std::vector<T> data_;
public:
    void add(const T& elem) { data_.push_back(elem); }
    size_t size() const { return data_.size(); }
};
```

Unlike regular classes, the compiler needs the **full template definition** at the point of instantiation. If you split `.h` and `.cpp`, the linker won't find the definitions.

**Solutions:**
1. Keep everything in the header (most common)
2. Include the `.cpp` file at the end of the header
3. Explicit instantiation for known types

```cpp
// Explicit instantiation
template class MyContainer<int>;
template class MyContainer<std::string>;
```

## Common Interview Patterns

### 1. Implementing `std::make_unique`

```cpp
template <typename T, typename... Args>
std::unique_ptr<T> make_unique(Args&&... args) {
    return std::unique_ptr<T>(new T(std::forward<Args>(args)...));
}
```

### 2. Type-Safe Variadic Print

```cpp
template <typename... Args>
void safePrint(const Args&... args) {
    ((std::cout << args << " "), ...);
    std::cout << "\n";
}
```

### 3. Compile-Time String Length

```cpp
template <size_t N>
constexpr size_t strLen(const char (&str)[N]) {
    return N - 1;  // exclude null terminator
}

constexpr auto len = strLen("hello");  // 5, computed at compile time
```

## Common Mistakes

1. **Defining templates in `.cpp` files** — Causes linker errors (undefined reference)
2. **Forgetting `typename` for dependent types** — `typename T::iterator` is required
3. **Confusing specialization with overloading** — Function templates can't be partially specialized
4. **Overusing TMP** — Compile times explode; prefer `constexpr` functions when possible
5. **Not using `concept` in C++20** — SFINAE error messages are notoriously unreadable
6. **Assuming templates are dynamically dispatched** — They're compile-time, not runtime polymorphism
7. **Passing template arguments by value when expensive** — Use `const T&` or forwarding references

## Quick Reference Table

| Feature | Introduced | Purpose |
|---------|-----------|---------|
| Function templates | C++98 | Generic functions |
| Class templates | C++98 | Generic classes |
| Partial specialization | C++98 | Specialize for subsets of types |
| Variadic templates | C++11 | Arbitrary number of args |
| `std::enable_if` | C++11 | SFINAE-based constraint |
| `if constexpr` | C++17 | Compile-time branching |
| Fold expressions | C++17 | Simplify variadic operations |
| Concepts | C++20 | Clean constraints with good errors |
| `requires` expressions | C++20 | Check type properties at compile time |
| CRTP | C++98 (pattern) | Static polymorphism |
