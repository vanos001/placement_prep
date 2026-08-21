# C++ Smart Pointers and Move Semantics

## Overview

Before C++11, dynamic memory in C++ was managed by raw `new` and `delete`. The
result, across decades of C++ code, was a flood of memory-related bugs:
use-after-free, double-free, leaks, exception-unsafe allocation sites. C++11
shipped three abstractions that fix most of these problems mechanically:
`unique_ptr`, `shared_ptr`, and `weak_ptr`. They are paired with **move
semantics**, the feature that lets `unique_ptr` be returned by value without
copying and lets `std::vector` grow without copying every element.

Together, smart pointers and move semantics shift C++ closer to the
"you cannot accidentally leak" zone that Rust and GC'd languages live in — but
they remain zero-overhead abstractions on top of raw pointers. The standard
calls the bundle RAII plus move; Scott Meyers' *"Effective Modern C++"* (Item
18 onward) is the canonical practitioner reference.

## RAII and Ownership

Every smart pointer expresses an **ownership discipline**:

```
Type             Ownership           Copyable  Movable  Cost
--------------    -----------------   --------  -------  ------------------------
unique_ptr<T>     exclusive (1 owner) no        yes       zero (== raw T*)
shared_ptr<T>     shared (refcount)  yes       yes       one atomic refcount incr/decr per op
weak_ptr<T>       non-owning          yes       yes       same control block
```

The core idea of RAII — acquire in the constructor, release in the destructor —
means a smart pointer's lifetime **is** its resource's lifetime. As soon as
the smart pointer goes out of scope (or is `reset`), the resource is freed.
Combined with stack unwinding on exception throw, this is what makes C++11 code
"exception-safe by construction" for memory resources.

## `std::unique_ptr` — Exclusive Ownership, Zero Overhead

`unique_ptr` owns exactly one object through a non-null pointer (or is empty).
It is **non-copyable** but movable; moving transfers ownership, leaving the
source in a defined "empty" state. The type has a parameter for a deleter:

```cpp
struct fclose_deleter {
    void operator()(FILE* f) const noexcept {
        if (f) std::fclose(f);
    }
};
using file_ptr = std::unique_ptr<FILE, fclose_deleter>;

file_ptr open(const char* path) {
    return file_ptr(std::fopen(path, "r"));   // implicit move
}

void work() {
    auto fp = open("a.txt");
    if (!fp) throw std::runtime_error("open failed");
    std::fgetc(fp.get());   // .get() exposes raw pointer, does not transfer
}   // fclose called here, even on exception
```

The deleter is stored **in the type** of the `unique_ptr` itself. For the
default `std::default_delete<T>` (which just calls `delete`), the deleter is
empty-base-optimized away, so the `sizeof(unique_ptr<T>)` is exactly `sizeof(T*)`.
This is what "zero-overhead" means — it's the same memory and the same generated
code as a raw pointer.

The array specialization `unique_ptr<T[]>` calls `delete[]` and provides
`operator[]`, but C++20 deprecated it in favor of `std::vector` and
`std::array`.

## `std::shared_ptr` — Reference Counting with a Control Block

`shared_ptr` allows multiple owners. Internally, each `shared_ptr` is a pair
of pointers: one to the managed object, one to a heap-allocated **control
block** that holds:

```
+-----------------+
| strong_count    |  <-- number of shared_ptr instances
| weak_count      |  <-- number of weak_ptr instances + 1 if strong>0
| deleter         |  <-- type-erased (stored in control block, not in ptr)
| allocator       |
+-----------------+
```

The strong and weak counts are atomics (default `std::memory_order_relaxed`
for the increment on copy, `acq_rel` for the decrement that may release) so
that `shared_ptr` is thread-safe to copy across threads — but only the
**control block** is thread-safe; the pointed-to object's own data still
needs synchronization.

A critical detail: the control block is allocated **once**, on the first
construction from a raw `new`. All copies of the `shared_ptr` reference the
same control block. Two classic bugs:

1. **Two control blocks for one object**: `T* p = new T; shared_ptr<T> a(p);
   shared_ptr<T> b(p);` — `a` and `b` have separate control blocks, both with
   strong_count = 1. When `a` goes out of scope, `delete p`. When `b` goes out
   of scope, **double delete** (UB). Always use `make_shared`.

2. **`shared_ptr(this)`**: If `this` is already managed by a `shared_ptr`
   somewhere else, the new `shared_ptr` makes a *new* control block, with the
   same double-free bug. The fix: inherit from
   `std::enable_shared_from_this<T>` and call `shared_from_this()`:

   ```cpp
   class Node : public std::enable_shared_from_this<Node> {
   public:
       std::shared_ptr<Node> get_ptr() { return shared_from_this(); }
   };
   ```

## `std::weak_ptr` — Breaking Cycles

`weak_ptr` observes an object managed by `shared_ptr` without contributing to
the strong count. To use the pointee you call `lock()`, which atomically checks
if the object still exists and, if so, returns a fresh `shared_ptr` (incrementing
strong_count); otherwise it returns an empty `shared_ptr`. This is the canonical
fix for cycles:

```cpp
struct Node {
    std::shared_ptr<Node> next;   // strong: keeps successor alive
    std::weak_ptr<Node>   prev;   // weak: doesn't keep predecessor alive
};

// doubly linked list {A<->B<->C}: when external shared_ptr's to A,B,C are
// destroyed, the chain collapses; without weak_ptr for `prev`, A and B
// would keep each other alive forever.
```

Another classic cycle: observer/subject. The subject holds
`vector<weak_ptr<Observer>>`, so destroying all observer `shared_ptr`s actually
destroys them, and the subject's notifications simply see `lock()` returning
empty.

## `make_unique` and `make_shared` — Why You Should Use Them

Both `make_unique` and `make_shared` are exception-safe, leak-free, and faster
than the equivalent `new`+constructor call:

```cpp
// BAD — exception-unsafe
void f() { f(shared_ptr<T>(new T), g_that_might_throw()); }
// C++17 fixed evaluation order so this particular example is now safe,
// but the general pattern (new + constructor + side-effecting call) is risky.

// GOOD — one allocation, one cleanup, exception-safe
void f() { f(std::make_shared<T>(), g_that_might_throw()); }
```

`make_shared` further **fuses the control block and the object into a single
allocation** — better cache locality and one fewer heap round-trip:

```
shared_ptr<T>(new T)        make_shared<T>

+-----------+  +--------+    +--------------+
| control   |->| T obj  |   | control + T   |
| block     |  +--------+   | fused alloc  |
+-----------+               +--------------+

2 allocations,            1 allocation,
2 cache lines worst case  1 cache line best case
```

There are exactly three situations where you should avoid `make_shared`:

1. **You need a custom deleter** (e.g., `fopen`/`fclose`). `make_shared` cannot
   accept one; fall back to `shared_ptr<T>(new T, deleter)`.
2. **You need a custom allocator** of the legacy allocator type — same story.
3. **The object is very large and you also store `weak_ptr`s that outlive all
   strong owners.** Because the control block and the object are fused, the
   object's memory is not freed until *all* weak_ptrs are also gone — so a
   giant object with a long-lived weak observer wastes memory in the meantime.

## Move Semantics — `std::move` and Rvalue References

C++11 added a new value category: the **xvalue** ("expiring value"). An xvalue
is an object that the program is about to destroy, so it's safe to steal from.
`std::move(x)` is a cast that turns an lvalue into an xvalue:

```cpp
template <typename T>
constexpr std::remove_reference_t<T>&& move(T& x) noexcept {
    return static_cast<std::remove_reference_t<T>&&>(x);
}
```

`std::move` doesn't actually move anything — it's a license for an overload on
`T&&` to be selected. The actual work happens in the move constructor or move
assignment operator:

```cpp
class Buffer {
    char* data_;
    size_t sz_;
public:
    Buffer(Buffer&& other) noexcept
        : data_(other.data_), sz_(other.sz_) {
        other.data_ = nullptr;
        other.sz_    = 0;
    }
    Buffer& operator=(Buffer&& other) noexcept {
        if (this != &other) {
            delete[] data_;
            data_       = other.data_;
            sz_         = other.sz_;
            other.data_ = nullptr;
            other.sz_   = 0;
        }
        return *this;
    }
};
```

`noexcept` matters here: it allows `std::vector<Buffer>::reserve` to move
elements during a reallocation. Without `noexcept`, the vector falls back to
copying because moving would risk leaving the source half-moved if an exception
were thrown mid-realloc.

### Perfect Forwarding

A **forwarding reference** (universal reference) is a special form: `T&&` in a
context where `T` is a deduced template parameter. The reference collapses
rules then bind `T&&` to either an lvalue ref or an rvalue ref depending on
what was passed:

```cpp
template <typename T>
void relay(T&& x) {                          // forwarding reference
    target(std::forward<T>(x));              // std::forward restores the
                                              // original value category
}

template <typename T, typename... Args>
auto make(Args&&... args) {
    return std::make_unique<T>(std::forward<Args>(args)...);
}
```

`std::forward<T>(x)` is a conditional cast: if `T` was deduced as `T&`, it casts
to `T&` (lvalue); if `T` was `T` or `T&&`, it casts to `T&&` (rvalue). Without
`std::forward`, all the parameters forwarded to `target` would be lvalues,
forcing copies where moves were intended.

The difference between `std::move` and `std::forward` is the same as the
difference between an unconditional cast and a conditional cast. `std::move`
says: "I know this is an lvalue; cast it to rvalue because I'm done with it."
`std::forward` says: "I don't know if this was originally an lvalue or an
rvalue; preserve whatever it was."

## Custom Deleters and Type Erasure

`shared_ptr` type-erases its deleter into the control block, so two
`shared_ptr<T>`s with **different deleters** have the **same type**:

```cpp
auto a = std::shared_ptr<int>(new int, std::default_delete<int>());
auto b = std::shared_ptr<int>(static_cast<int*>(std::malloc(sizeof(int))),
                              [](int* p) { std::free(p); });
// a and b have the same type, even though deleters are different
```

`unique_ptr` does **not** type-erase; the deleter is part of the type, so
`unique_ptr<FILE, fclose_deleter>` and `unique_ptr<FILE, my_deleter>` are
different types. This makes `unique_ptr` zero-overhead but harder to mix in
heterogeneous containers — though you can convert to a `shared_ptr` of any
deleter type because `shared_ptr` will erase on conversion.

## The Rule of Zero / Three / Five

A C++ class that manages a resource should think about its special member
functions: copy constructor, copy assignment, move constructor, move
assignment, destructor.

```
Rule of three (pre-C++11):
    If you write any one of {copy ctor, copy assign, dtor},
    you probably need to write all three.

Rule of five (C++11+):
    If you write any of {copy ctor, copy assign, move ctor,
    move assign, dtor}, you probably need to write all five.

Rule of zero (preferred):
    Make every member a value, smart pointer, or RAII type that
    already implements the rule of five correctly, and let the
    compiler synthesize the special members.
```

The Rule of Zero is the modern C++ Core Guidelines recommendation (C.20):
"By default, declare your special member functions = default or omit them, and
use RAII members so they do the right thing." The Core Guidelines (R.1, R.20,
R.21) put it bluntly: "Don't manage resources manually."

```cpp
class Team {
    std::string name_;                       // RAII
    std::vector<std::unique_ptr<Player>> p_; // RAII + move-only
public:
    Team() = default;
    // All five special members are correctly synthesized:
    // - copy ctor is deleted (because vector<unique_ptr> is non-copyable)
    // - move ctor is move-only (vector<unique_ptr> moves)
    // - dtor destroys everything via the members' dtors
};
```

## Comparison to Rust Ownership

The modern C++ smart-pointer + move-semantics bundle is best understood by
contrast with Rust:

```
                    C++                       Rust
-------------------- ---------------------     --------------------------
Ownership tracking  Manual / by convention    Compiler-enforced via borrow checker
Use after free       Possible (UB)             Forbidden (compiler rejects)
Data races          Possible (UB)             Forbidden (compiler rejects)
Cycles              Programmer's job          Refcount (Rc) + weak (Weak)
                                                          OR Arc<Mutex<T>>
Null pointers       Allowed                   Forbidden (Option<T> in this role)
Smart pointer cost  unique_ptr = 0;           Box = 0;
                    shared_ptr = atomic       Rc = non-atomic refcount;
                                              Arc = atomic refcount
Lifetime syntax     Implicit                  Explicit ('a)
Free of leaks?      No                        No (Rc cycles, forget, etc.)
```

The borrow checker is a static analysis that requires at compile time that:

1. Every reference's lifetime is bounded by its referent's lifetime.
2. At most one mutable reference, **or** arbitrarily many immutable references,
   to the same object at any time.

C++ does not do this statically — the C++ Core Guidelines Profile Framework
proposed a similar static analysis (the "lifetime profile", implemented in
clang-tidy), but adoption is incomplete. C++'s advantage: zero-cost
interoperability with existing C code and full backwards compatibility. Rust's
advantage: the rule is enforced, not recommended.

## Common Pitfalls

1. **`shared_ptr(this)` double control block** — already covered; use
   `enable_shared_from_this`.
2. **Forgetting `noexcept` on move** — breaks `std::vector` realloc
   optimization.
3. **Returning `unique_ptr<T>&`** — return by value; the move is free.
4. **`f(shared_ptr<T>(new T), g())`** — historical example of leak-on-throw;
   use `make_shared`. C++17 fixed evaluation order so the leak is no longer
   possible, but `make_shared` is still better for the single allocation.
5. **Cycles of `shared_ptr`** — use `weak_ptr` for one direction.
6. **Using `make_shared` for very large objects with long-lived `weak_ptr`s**
   — the memory is held until all weaks die. Use
   `shared_ptr<T>(new T)` if necessary.
7. **Storing a `shared_ptr` to `this`** inside an object's own member — same
   fix: `enable_shared_from_this`.
8. **`unique_ptr<T>` and incomplete `T`** — the destructor (which calls
   `delete`) must be visible at the point of destruction. For pimpl idiom,
   declare the dtor in the header and define it in the .cpp where `T` is
   complete; the compiler-generated dtor in the header will fail if `T` is
   incomplete.
9. **Aliasing constructor confusion**: `shared_ptr<T>(other_shared_ptr, &some_member)`
   shares ownership of `other_shared_ptr` but points at the member — useful
   but easy to misuse.
10. **`std::forward` instead of `std::move`** in non-template contexts —
    `std::forward<T>` without a deduced `T` is a noop and a bug magnet.

## When to Use What

| Situation                                        | Recommendation                          |
|--------------------------------------------------|-----------------------------------------|
| Default heap allocation                          | `std::unique_ptr` via `make_unique`    |
| Shared ownership (rare)                          | `std::shared_ptr` via `make_shared`    |
| Caches, observer lists, parent pointers          | `std::weak_ptr`                        |
| Custom resource (file, socket, fd)               | `unique_ptr<T, CustomDeleter>`          |
| Returning a polymorphic factory result           | `std::unique_ptr<Base>` (move into caller) |
| Member of a class                                | Use RAII members (Rule of Zero)         |
| Lifetime across threads                          | `shared_ptr` (refcount is atomic)       |
| Lifetime within one thread, no shared owner      | `unique_ptr` (or just stack object)     |

## Interview Questions

1. **Why does `shared_ptr` need a separate control block?** Because every
   owner needs the same shared counter and deleter; copying the count into
   each `shared_ptr` would race.
2. **What does `make_shared` fuse together, and why does it matter?** The
   control block and the object — one allocation, better cache locality, one
   fewer system call.
3. **When must you avoid `make_shared`?** Custom deleter, custom allocator,
   or large object with long-lived `weak_ptr`s.
4. **What is the difference between `std::move` and `std::forward`?**
   `std::move` is an unconditional cast to `T&&`; `std::forward<T>` is a
   conditional cast that preserves the deduced value category.
5. **Explain the rule of zero.** Prefer to write classes whose members are
   all RAII types so the compiler-synthesized special members do the right
   thing; no boilerplate.
6. **How does a `weak_ptr` break a `shared_ptr` cycle?** It contributes only
   to the weak count, so the strong count can reach zero and trigger
   destruction.
7. **Why must move constructors be `noexcept`?** So `std::vector::reserve`
   can use moves during reallocation; otherwise it falls back to copy to
   preserve the strong-exception-safety guarantee.
8. **Compare `unique_ptr` and Rust's `Box`.** Both are zero-overhead,
   exclusive ownership. `unique_ptr` allows raw manipulation via `release()`;
   `Box` does not. `unique_ptr` can have a custom deleter in the type;
   `Box`'s deallocation is by Rust's global allocator.
9. **Why does `enable_shared_from_this` exist?** To safely obtain a
   `shared_ptr` to `*this` from inside a member function, without creating a
   duplicate control block.
10. **What is the C++ Core Guidelines "lifetime profile"?** A static analysis
    that approximates Rust's borrow checker in C++; opt-in via clang-tidy.

## References

- cppreference: `<memory>` — https://en.cppreference.com/w/cpp/memory
- cppreference: `std::unique_ptr` — https://en.cppreference.com/w/cpp/memory/unique_ptr
- cppreference: `std::shared_ptr` — https://en.cppreference.com/w/cpp/memory/shared_ptr
- cppreference: `std::weak_ptr` — https://en.cppreference.com/w/cpp/memory/weak_ptr
- cppreference: `std::move`, `std::forward` — https://en.cppreference.com/w/cpp/utility/move and https://en.cppreference.com/w/cpp/utility/forward
- Scott Meyers, *"Effective Modern C++"* (Items 18–25 for smart pointers, 23–30 for move semantics and forwarding)
- C++ Core Guidelines (Stroustrup & Sutter, eds.) — https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines — see R.1, R.20, R.21, C.20
- Herb Sutter, *"Elements of Modern C++ Style"* — https://herbsutter.com/elements-of-modern-c-style/
- B. Stroustrup, *"The C++ Programming Language, 4th ed."* — Chapter 34 on smart pointers
- ISO/IEC 14882:2020 (C++20) §20.10 "Memory" and §20.14 "Function objects"
- The Rust ownership model (for comparison) — https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html

## Related Topics

- [Move Semantics](./move-semantics.md) — the detailed value-category file in this repo
- [Memory Model](./memory-model.md) — atomic refcounting semantics in `shared_ptr`
- [Modern C++](./modern-cpp.md) — RAII, `constexpr`, `noexcept`
- [Templates](./templates.md) — `std::make_unique<T>` is a template
- [C Pointers](../c/pointers.md) — the raw-pointer foundations
