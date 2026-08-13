# Rust Interview Questions

## Ownership and Borrowing

### Q1: What are Rust's ownership rules?

1. Each value has exactly one owner
2. When the owner goes out of scope, the value is dropped
3. There can be either one mutable reference OR any number of immutable references
4. References must always be valid (no dangling references)

```rust
let s1 = String::from("hello");
let s2 = s1;        // s1 moved to s2, s1 no longer valid
// println!("{}", s1); // ERROR: value used after move
```

### Q2: What is the borrow checker?

The borrow checker enforces Rust's borrowing rules at compile time:
- Multiple immutable references (`&T`) are allowed simultaneously
- Only one mutable reference (`&mut T`) at a time
- Immutable and mutable references cannot coexist
- References cannot outlive the data they point to

```rust
let mut data = vec![1, 2, 3];
let r1 = &data;        // OK: immutable borrow
let r2 = &data;        // OK: another immutable borrow
// let r3 = &mut data;  // ERROR: cannot borrow as mutable while immutably borrowed
println!("{:?} {:?}", r1, r2);
// r1, r2 no longer used after this point (NLL)
let r3 = &mut data;    // OK: now mutable borrow is fine
```

### Q3: Move vs Copy semantics?

| Move (default) | Copy (explicit trait) |
|-----------------|----------------------|
| Heap data (String, Vec) | Stack data (i32, f64, bool) |
| Ownership transferred | Bitwise copy |
| Original becomes invalid | Both remain valid |

```rust
// Copy types
let x = 42;
let y = x;     // Copy, both valid
println!("{} {}", x, y); // OK

// Move types
let s = String::from("hello");
let t = s;     // Move, s invalid
// println!("{}", s); // ERROR

// Clone for explicit deep copy
let s2 = t.clone(); // Both valid
```

### Q4: What are lifetimes?

Lifetimes are compile-time annotations that ensure references are valid. They describe the scope for which a reference is valid.

```rust
// Explicit lifetime annotation
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}

// Lifetime elision rules:
// 1. Each reference gets its own lifetime
// 2. If exactly one input lifetime, output gets that lifetime
// 3. If &self or &mut self, output gets self's lifetime

// Struct with lifetime
struct Excerpt<'a> {
    text: &'a str,
}
```

### Q5: What is `'static`?

A `'static` reference lives for the entire program duration.

```rust
// String literals are 'static
let s: &'static str = "hello";

// Owned data can be leaked to 'static (rarely needed)
let s: &'static str = Box::leak(Box::new(String::from("hello")));

// Common in trait objects
fn make_static() -> Box<dyn Fn() + 'static> {
    Box::new(|| println!("hello"))
}
```

## Traits

### Q6: What are traits?

Traits define shared behavior (like interfaces). Types implement traits to provide specific functionality.

```rust
trait Drawable {
    fn draw(&self);  // Required method
    
    fn describe(&self) -> String {  // Default implementation
        format!("A drawable object")
    }
}

// Implementation
struct Circle { radius: f64 }
impl Drawable for Circle {
    fn draw(&self) { /* ... */ }
}

// Trait bounds
fn draw_all(items: &[impl Drawable]) {
    for item in items { item.draw(); }
}

// where clause
fn draw_all<T: Drawable + Clone>(items: &[T]) { /* ... */ }
```

### Q7: Trait objects vs generics (static vs dynamic dispatch)?

| Generics (static dispatch) | Trait objects (dynamic dispatch) |
|---------------------------|--------------------------------|
| Monomorphized at compile time | Dispatched at runtime via vtable |
| Zero-cost abstraction | Small runtime cost |
| Cannot mix types in collection | Can store different types |
| `fn foo<T: Trait>(x: T)` | `fn foo(x: &dyn Trait)` |

```rust
// Static dispatch: each type gets its own copy of draw_all
fn draw_all_static(items: &[impl Drawable]) { /* ... */ }

// Dynamic dispatch: one function, runtime vtable lookup
fn draw_all_dynamic(items: &[Box<dyn Drawable>]) { /* ... */ }
```

### Q8: What is the orphan rule?

You can implement a foreign trait for a foreign type only if either the trait or the type is local to your crate.

```rust
// OK: implementing local trait for foreign type
trait MyTrait { fn my_fn(&self); }
impl MyTrait for Vec<i32> { fn my_fn(&self) { /* ... */ } }

// OK: implementing foreign trait for local type
impl std::fmt::Display for MyStruct { /* ... */ }

// ERROR: implementing foreign trait for foreign type
// impl std::fmt::Display for Vec<i32> { /* ... */ }
```

## Error Handling

### Q9: Result vs Option?

| Option | Result |
|--------|--------|
| `Some(T)` or `None` | `Ok(T)` or `Err(E)` |
| Value might not exist | Operation might fail |
| `unwrap()` panics on None | `unwrap()` panics on Err |

```rust
fn find_user(id: u32) -> Option<User> { /* ... */ }
fn parse_config(path: &str) -> Result<Config, Error> { /* ... */ }

// ? operator propagates errors
fn process(path: &str) -> Result<(), Error> {
    let config = parse_config(path)?;  // Returns Err if failed
    let user = find_user(config.user_id).ok_or(Error::NotFound)?;
    Ok(())
}
```

### Q10: thiserror vs anyhow?

| thiserror | anyhow |
|-----------|--------|
| Define custom error types | Catch-all error handling |
| Library code | Application code |
| `#[derive(Error)]` | `anyhow::Result<T>` |
| Structured errors | Context strings |

```rust
// thiserror (library)
#[derive(thiserror::Error)]
enum MyError {
    #[error("not found: {0}")]
    NotFound(String),
    #[error("parse error")]
    Parse(#[from] std::num::ParseIntError),
}

// anyhow (application)
fn run() -> anyhow::Result<()> {
    let data = std::fs::read_to_string("config.toml")
        .context("failed to read config")?;
    Ok(())
}
```

## Concurrency

### Q11: Send and Sync traits?

- `Send`: Type can be transferred between threads
- `Sync`: Type can be shared between threads (via `&T`)

```rust
// Most types are Send + Sync
// Rc is !Send (not thread-safe)
// Cell/RefCell are !Sync (not thread-safe)
// Mutex is Send + Sync
// Arc is Send + Sync (atomic reference counting)
```

### Q12: Arc vs Rc?

| Rc | Arc |
|----|-----|
| Single-threaded | Multi-threaded |
| Non-atomic ref count | Atomic ref count |
| Faster | Slightly slower |
| `!Send` | `Send + Sync` |

```rust
use std::sync::{Arc, Mutex};
use std::thread;

let data = Arc::new(Mutex::new(vec![]));
let handles: Vec<_> = (0..10).map(|i| {
    let data = Arc::clone(&data);
    thread::spawn(move || {
        data.lock().unwrap().push(i);
    })
}).collect();
```

## Advanced

### Q13: What is Pin?

`Pin` prevents values from being moved. Required for self-referential types (async state machines).

```rust
use std::pin::Pin;

// Pin<&mut T>: pinned mutable reference
// Unpin: marker trait saying type is safe to move after pinning
// Most types are Unpin; async futures are not

// Box::pin: heap-allocate and pin
let pinned = Box::pin(async { 42 });
```

### Q14: What are lifetimes in closures?

Closures capture variables by reference, move, or mutable reference. The closure's lifetime must not outlive captured variables.

```rust
fn make_adder(x: i32) -> impl Fn(i32) -> i32 {
    move |y| x + y  // move takes ownership of x
}

// Closure with reference
let data = vec![1, 2, 3];
let print = || println!("{:?}", data); // borrows data
print();
// data still usable here
```

### Q15: What are GATs (Generic Associated Types)?

```rust
// GATs allow associated types with their own lifetimes/generics
trait LendingIterator {
    type Item<'a> where Self: 'a;
    fn next<'a>(&'a mut self) -> Option<Self::Item<'a>>;
}

// Windows that borrow from the slice
struct Windows<'a, T> {
    slice: &'a [T],
    pos: usize,
    size: usize,
}

impl<'a, T> LendingIterator for Windows<'a, T> {
    type Item<'b> = &'b [T] where Self: 'b;
    fn next<'b>(&'b mut self) -> Option<Self::Item<'b>> {
        // return a window borrowed from self
        todo!()
    }
}
```

## Comparison Questions

### Q16: Rust vs C++ memory safety?

| Aspect | Rust | C++ |
|--------|------|-----|
| Null pointers | `Option<T>` (no null) | Raw null pointers |
| Buffer overflow | Bounds checking | Unchecked |
| Use-after-free | Borrow checker | Manual / smart ptrs |
| Data races | Compile-time prevention | Runtime detection |
| Memory leaks | Rare (Rc cycles) | Common |

### Q17: When would you use `unsafe`?

1. FFI (calling C functions)
2. Implementing unsafe traits (`Send`, `Sync`)
3. Performance-critical code with raw pointers
4. Interacting with hardware/OS APIs

```rust
unsafe {
    let ptr = &mut data as *mut i32;
    *ptr = 42; // Raw pointer dereference
}
// Minimize unsafe blocks; wrap in safe abstractions
```

## Related Topics

- [Rust Ownership](./ownership.md) — Deep dive into ownership
- [Rust Borrow Checker](./borrow-checker.md) — How the borrow checker works
- [Rust Traits](./traits.md) — Trait system details
- [Rust Async](./async.md) — Async/await and futures
- [Tokio](../../frameworks/tokio/) — Async runtime
- [Concurrency](../../concurrency/) — General concurrency concepts
