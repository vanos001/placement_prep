# C++ Templates and Compile-Time Metaprogramming

## Why Templates Exist

C++ templates solve two intertwined problems: writing **generic data structures
and algorithms** without sacrificing type safety, and performing **compile-time
computation** that would otherwise need a separate preprocessor. A `vector<int>`
and a `vector<Widget>` are two distinct types produced by the same template,
each as fast as a hand-written equivalent and each carrying its full static type
information into machine code. Java generics erased to `Object` at runtime; Rust
generics monomorphize like C++ but are constrained by trait bounds; C++ templates
remain the most expressive of the three because **anything the type system can
express** can be used as a constraint.

## Function and Class Templates

A template introduces type (or non-type, or template) parameters that the
compiler substitutes with concrete arguments at instantiation time:

```cpp
template <typename T>
T maximum(const T& a, const T& b) {
    return a > b ? a : b;
}

template <typename T, std::size_t N>
class fixed_array {
    T data_[N];
public:
    T&       operator[](std::size_t i)       { return data_[i]; }
    const T& operator[](std::size_t i) const { return data_[i]; }
    constexpr std::size_t size() const noexcept { return N; }
};

int main() {
    auto i = maximum(3, 7);                   // T = int
    auto d = maximum<double>(3, 4.5);        // explicit
    fixed_array<float, 4> fs{};              // N = 4 (non-type param)
}
```

Template **declarations** end in `.h`/`.hpp` and **must** be visible at the
point of instantiation — the compiler must see the definition, not just the
signature, to generate code. This is the source of the conventional "all
template code in headers" rule. C++11 `extern template` lets you suppress
implicit instantiation in one TU and force explicit instantiation in another,
cutting compile time.

## The Template Instantiation Model

The two-phase model:

```
Phase 1 (parsing template definition):
   - Check syntactic correctness.
   - Names that DON'T depend on a template parameter are resolved
     ("first-phase lookup").
   - Names that DO depend are left unresolved ("dependent names").

Phase 2 (instantiation, when arguments are known):
   - Substitute template parameters with the actual arguments.
   - Resolve dependent names by argument-dependent lookup (ADL).
   - Type-check each expression against the now-concrete types.
   - Generate machine code (or, if not used, none).
```

This is why calling `t.foo()` inside a template compiles even when `T` doesn't
have a `foo()` until substitution time — a key difference from Java or Rust
where the constraint must be stated up front.

```
                  Source
                    |
        +-----------+-----------+
        | Template  | Concrete  |
        | definition| call site |
        +-----------+-----------+
                    |  Phase 1 (parse + first-phase lookup)
                    v
              Template Parsed
                    |  Phase 2 (substitute + check)
                    v
              Instantiation
                    |  Codegen
                    v
              Object code
```

Two failure modes follow:

- **Hard errors** (from non-dependent code) trigger even if the template is
  never instantiated.
- **Substitution failures** in dependent code (the "S" in SFINAE) are quietly
  ignored by the compiler when picking among candidate overloads.

## SFINAE

The "Substitution Failure Is Not An Error" rule states that if substituting a
template argument into a function template's signature causes a type error,
the compiler silently removes that candidate from overload resolution rather
than erroring out. Combined with `std::enable_if`, this enables conditional
template selection:

```cpp
#include <type_traits>

// Enable this overload only for integral T
template <typename T,
          typename = std::enable_if_t<std::is_integral_v<T>>>
T abs_safe(T x) { return x < 0 ? -x : x; }

// And this one only for floating-point T
template <typename T,
          typename = std::enable_if_t<std::is_floating_point_v<T>>>
T abs_safe(T x) { return x < 0 ? -x : x; }
```

A second, very common pattern is the trailing return-type trick:

```cpp
template <typename T>
auto size_in_bytes(const T& v) -> decltype(sizeof(char[0]), v.size()) {
    return v.size();
}
```

If `v.size()` is ill-formed for the given `T`, `decltype` substitution fails
and SFINAE removes this overload. Modern idioms replaced most of this with
`if constexpr` (C++17) and **concepts** (C++20).

## Template Specialization

Templates can be specialized to override behavior for specific arguments:

```cpp
// Primary
template <typename T> struct stringify {
    static std::string apply(const T& x) { return std::to_string(x); }
};

// Full specialization for bool
template <> struct stringify<bool> {
    static std::string apply(bool b) { return b ? "true" : "false"; }
};

// Partial specialization for vectors
template <typename T> struct stringify<std::vector<T>> {
    static std::string apply(const std::vector<T>& v) {
        std::string out = "[";
        for (const auto& x : v) out += stringify<T>::apply(x) + ",";
        return out + "]";
    }
};
```

Function templates support **full specialization only**, not partial
specialization. The workaround is to specialize a class template instead and
delegate to it.

## CRTP — Curiously Recurring Template Pattern

CRTP passes the derived class into the base as a template parameter, allowing
**static (compile-time) polymorphism** without virtual function overhead:

```cpp
template <typename Derived>
struct shape_base {
    double area() const {
        return static_cast<const Derived*>(this)->area_impl();
    }
};

struct circle : shape_base<circle> {
    double r;
    double area_impl() const { return 3.14159 * r * r; }
};

// CRTP also enables mixin-style composition and policy-based design:
template <typename D>
struct comparable {
    friend bool operator!=(const D& a, const D& b) { return !(a == b); }
    friend bool operator>(const D& a, const D& b)  { return (b < a); }
};
```

Every method on `shape_base` is inlined at the call site. The compiler emits
zero virtual-call indirection. The cost: the type hierarchy must be known at
compile time; you cannot store heterogeneous `shape_base<*>` collections (use
`std::variant` or genuine `virtual` functions for that).

## Concepts (C++20)

Concepts are **named, compositional constraints** on template parameters. They
replace the tortured `enable_if` idioms and produce readable error messages:

```cpp
#include <concepts>

template <typename T>
concept Addable = requires(T a, T b) { a + b; };

template <typename T> requires std::integral<T>
T gcd(T a, T b) {
    while (b != 0) { T t = b; b = a % b; a = t; }
    return a;
}

// Shorter form: write the concept directly as a constraint
template <std::integral T>
T lcm(T a, T b) { return a / gcd(a, b) * b; }

// "auto" syntax: a concept on a function parameter
void print(std::integral auto x) { std::cout << x; }
```

Concepts can be refined (`A = B && requires...`), composed (`(A<T> && B<T>)`),
and used in `requires`-expressions to perform ad-hoc introspection:

```cpp
template <typename T>
concept Container = requires(T c) {
    c.begin();
    c.end();
    typename T::value_type;
};
```

A concept failure produces a single, human-readable diagnostic pointing at the
unmet constraint, instead of a page-long stack of substitution failures. This
single change transformed C++ template error messages from "incomprehensible" to
"informational."

## `if constexpr` (C++17)

`if constexpr (cond)` discards the untaken branch at **compile time** instead of
defer to runtime. Combined with templates it eliminates the need for tag
dispatch:

```cpp
template <typename T>
void print(const T& x) {
    if constexpr (std::is_same_v<T, bool>) {
        std::cout << (x ? "true" : "false");
    } else if constexpr (std::is_arithmetic_v<T>) {
        std::cout << x;
    } else if constexpr (requires { x.c_str(); }) {
        std::cout << x.c_str();
    } else {
        std::cout << "<unknown>";
    }
}
```

Without `if constexpr`, the untaken branch must still type-check — impossible
here because `x.c_str()` is only valid for some `T`. With it, the branch is
simply erased.

## Fold Expressions (C++17)

Fold expressions collapse parameter packs over a binary operator:

```cpp
template <typename... Ts>
auto sum_all(const Ts&... xs) {
    return (xs + ...);                // right fold: ((x0 + x1) + x2) + ... + xN
}

template <typename... Ts>
void print_all(const Ts&... xs) {
    ((std::cout << xs << ' '), ...);  // comma fold, (a, b), (b, c), ...
    std::cout << '\n';
}

// With an initial value
template <typename... Ts>
auto sum_default(const Ts&... xs) {
    return (0 + ... + xs);            // includes 0 if pack is empty
}
```

Four kinds exist: left unary fold, right unary fold, left binary fold, right
binary fold. Operator precedence and associativity drive the result.

## Compile-Time Computation: `constexpr` and `consteval`

`constexpr` functions may run at compile time **or** at runtime depending on
their arguments and call site; `consteval` (C++20) **must** run at compile
time:

```cpp
constexpr long fact(int n) {
    return n <= 1 ? 1 : n * fact(n - 1);
}
consteval long fact_compiletime(int n) { return n <= 1 ? 1 : n * fact(n-1); }

int main() {
    long a = fact(5);              // runtime (compiler may choose compile)
    constexpr long b = fact(5);    // forced compile-time
    static_assert(fact(10) == 3628800, "");
    long c = fact_compiletime(7);  // guaranteed compile-time
}
```

In C++14, `constexpr` could only be a single `return`. C++17 relaxed body
constraints. C++20 added `consteval`, `constinit` (for static initialization
fencing), and let `constexpr` use `dynamic_cast`, virtual calls, and many
runtime features. C++23 made `if constexpr` usable in `constexpr` functions
even more flexibly. The trend is to expand what compile-time code can do.

## Comparison to Rust Generics and Java Erasure

The three language families each handle generics differently:

```
                C++ templates              Rust generics            Java generics
--------------  --------------------------  ----------------------  ----------------------------
Mechanism       Monomorphization           Monomorphization         Type erasure (same class for all T)
Codegen         Per-type instantiation     Per-type instantiation   One `Object`-typed class
Constraints     Implicit (instantiation)  Explicit (`T: Trait`)    Explicit (`T extends C`)
Error messages  (was awful; C++20 good)   Good (where-clauses)    OK (declaration-site checked)
Code size       Potentially large          Potentially large       Fixed, smaller
Runtime speed   Inline-perfect             Inline-perfect           Indirect (boxing, casts)
Dynamic dispatch Possible (via `virtual`)  Via trait objects         Yes (`Object`)
Specialization  Yes (full & partial)       No                        No
```

- **C++ templates** are **Turing-complete at compile time** (template
  metaprogramming). They trade compilation time and binary size for
  zero-overhead generics and arbitrary compile-time logic.
- **Rust generics** share the monomorphization model but force the programmer
  to declare trait bounds explicitly. The upside: errors are reported at
  definition, not call, and the type system is decidable. The downside: less
  expressiveness in libraries.
- **Java generics** erase to the upper bound (`Object` by default). Runtime
  sees only `Object[]`. The cost is boxing, dynamic casts (which can fail at
  runtime), and the inability to overload on the type parameter. The upside:
  small binaries, single implementation.

A neat consequence of the C++ model: you can write **concepts that ask whether
a type is a tuple, a range, has a `.size()` method, has an iterator type that
satisfies `input_iterator`** — entirely at compile time, with no runtime cost.
The same task in Java requires runtime reflection; in Rust it requires trait
bounds that the trait system must enumerate.

## Practical Patterns

### Type Traits

```cpp
static_assert(std::is_trivially_copyable_v<int>);
static_assert(std::is_signed_v<float>);
static_assert(std::is_base_of_v<std::exception, std::runtime_error>);

// C++23: inspect any property of a type via <type_traits> + concepts
template <typename T>
requires std::copyable<T> && std::default_initializable<T>
class stack { /* ... */ };
```

### `std::variant` + `std::visit` (the modern "tagged union")

```cpp
using shape = std::variant<circle, square, triangle>;

double area(const shape& s) {
    return std::visit([](const auto& sh) { return sh.area(); }, s);
}
```

This is the modern alternative to CRTP or virtual hierarchies for closed type
sets, and the C++20 `std::expected<T, E>` for error propagation uses the same
machinery.

### Policy-Based Design

The STL allocator pattern: a class template parameterized by a *policy class*
(e.g., `std::vector<T, Allocator>`). The policy is known at compile time, so
every call into it inlines.

## Performance and Cost

Each new combination of template arguments may generate a new specialization.
The classic "template bloat" pathology is a single `vector<bool>` in 47
distinct TUs, generating 47 specializations in 47 object files. Real-world
mitigations:

- `extern template` declarations in headers, explicit instantiations in one TU.
- Type-erasing containers (`std::any`, `std::function`) at API boundaries to
  keep instantiations out of public headers.
- The C++ Core Guidelines (R.22 and friends) advise factoring shared code into
  non-template helpers that templates can dispatch into.
- Concepts cut bloat by removing the SFINAE cascade: the compiler doesn't
  instantiate five candidate overloads when only one satisfies the constraint.

## Common Interview Questions

1. **Why must templates live in headers?** The compiler needs the definition at
   the point of instantiation; the linker can't synthesize code for a template
   body it can't see.
2. **What is two-phase lookup? Why does it matter?** Phase 1 resolves non-
   dependent names; phase 2 resolves dependent ones. It explains why
   `dependent_base<T>::foo()` requires `typename` (the compiler can't know
   at phase 1 whether `foo` is a type).
3. **What does SFINAE mean, and what does it enable?** Substitution failure is
   not an error; enables conditional template activation via `enable_if` and
   now (mostly) via `requires`.
4. **Concepts versus SFINAE — what changed?** Concepts make constraints named
   and checkable; error messages point to the unmet concept rather than a wall
   of substitution failures.
5. **What is CRTP and when would you use it?** Compile-time polymorphism
   avoiding virtual dispatch; good for performance-critical hierarchies whose
   set is closed at compile time.
6. **C++ templates vs Rust generics vs Java erasure — one-line summary.**
   C++ = unchecked implicit monomorphization; Rust = explicit-trait-bound
   monomorphization; Java = single class with type casts.

## References

- cppreference: Function templates — https://en.cppreference.com/w/cpp/language/function_template
- cppreference: Class templates — https://en.cppreference.com/w/cpp/language/class_template
- cppreference: Template specialization — https://en.cppreference.com/w/cpp/language/template_specialization
- cppreference: SFINAE — https://en.cppreference.com/w/cpp/language/sfinae
- cppreference: Constraints and concepts (C++20) — https://en.cppreference.com/w/cpp/language/constraints
- cppreference: Fold expressions (C++17) — https://en.cppreference.com/w/cpp/language/fold
- cppreference: `if constexpr` (C++17) — https://en.cppreference.com/w/cpp/language/if
- Stroustrup, *"The C++ Programming Language, 4th ed."* — generic programming chapter and Concepts rationale
- ISO/IEC 14882:2020 (C++20) §13 "Templates" and §17 "Concepts"
- CppCon 2018: B. Stroustrup, *"Concepts: The Future of Generic Programming"* — https://www.youtube.com/watch?v=j3Qr7dGCgvg
- CppCon 2016: Walter Brown, *"C++17 `if constexpr`"* — https://www.youtube.com/watch?v=ZpqYFWgkX5I
- ISO C++ FAQ, "Templates" — https://isocpp.org/wiki/faq/templates
- Eric Lippert, "What is this thing you call 'thread-safe'?" (also discusses CRTP) — https://ericlippert.com/

## Related Topics

- [Templates](./templates.md) — the basic syntax overview file in this repo
- [Move Semantics](./move-semantics.md) — perfect forwarding lives here
- [Modern C++](./modern-cpp.md) — `constexpr`, `consteval`, structural types
- [STL](./stl.md) — the standard library is template-based
- [Concurrency](./concurrency.md) — `std::atomic<T>` templates
