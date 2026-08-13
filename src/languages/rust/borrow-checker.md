# The Borrow Checker

## Overview

The borrow checker is Rust's compile-time mechanism that enforces the ownership and borrowing rules. It analyzes the control flow of your program to ensure that:

1. Every reference is valid (no dangling references)
2. Mutable references are exclusive (no data races)
3. Immutable references don't coexist with mutable references

The borrow checker is the reason Rust can guarantee memory safety without a garbage collector. It's also the primary source of frustration for newcomers — but understanding it transforms Rust from "difficult" to "elegant."

## How It Works

The borrow checker performs **static analysis** on the program's MIR (Mid-level Intermediate Representation). It tracks:

- **Liveness** of each variable (where it's created, used, and dropped)
- **Borrows** (which references exist and what they point to)
- **Scopes** (how long each borrow is active)

```mermaid
flowchart TD
    A[Source Code] --> B[Parse to AST]
    B --> C[Generate HIR]
    C --> D[Type Checking]
    D --> E[Generate MIR]
    E --> F[Borrow Checker Analysis]
    F --> G{All borrows valid?}
    G -->|Yes| H[Continue to codegen]
    G -->|No| I[Compile Error]
```

## The Core Rules

### Rule 1: References Must Be Valid

```rust
fn main() {
    let r;
    {
        let x = 5;
        r = &x;        // x doesn't live long enough
    }
    // println!("{}", r); // ERROR: r references dropped value
}
```

### Rule 2: One Mutable XOR Many Immutable

```rust
fn main() {
    let mut s = String::from("hello");

    let r1 = &s;        // OK
    let r2 = &s;        // OK
    // let r3 = &mut s; // ERROR: cannot borrow as mutable while immutably borrowed

    println!("{} {}", r1, r2);
    // r1 and r2 are no longer used after this point (NLL)

    let r3 = &mut s;    // OK: r1 and r2 are "dead" here
    println!("{}", r3);
}
```

## Non-Lexical Lifetimes (NLL)

Before Rust 2018, borrows lasted until the end of the enclosing block (lexical scope). **Non-Lexical Lifetimes (NLL)** changed this: borrows now end at the **last use** of the reference, not at the end of the block.

```rust
fn main() {
    let mut s = String::from("hello");

    let r1 = &s;
    println!("{}", r1);   // r1's last use here
    // NLL: r1 is no longer active after this point

    let r2 = &mut s;      // OK! r1 is dead
    println!("{}", r2);
}
```

### Before NLL vs After NLL

```rust
// Before NLL (Rust 2015): this would NOT compile
fn process() {
    let mut data = vec![1, 2, 3];
    let first = &data[0];
    // first is still "alive" here in lexical scope
    data.push(4);           // ERROR: cannot borrow as mutable
    println!("{}", first);
}

// After NLL (Rust 2018+): this compiles
fn process() {
    let mut data = vec![1, 2, 3];
    let first = &data[0];
    println!("{}", first);  // last use of first
    // first is dead here
    data.push(4);           // OK!
}
```

## Common Patterns to Satisfy the Borrow Checker

### Pattern 1: Restructure to Limit Borrow Scope

```rust
// Problem: borrow extends too far
fn problem() {
    let mut v = vec![1, 2, 3];
    let first = &v[0];
    v.push(4);          // ERROR
    println!("{}", first);
}

// Solution: limit the borrow scope
fn solution() {
    let mut v = vec![1, 2, 3];
    let first = v[0];   // Copy the value (i32 is Copy)
    v.push(4);          // OK: no outstanding borrow
    println!("{}", first);
}
```

### Pattern 2: Use Index Instead of Reference

```rust
fn find_and_insert(v: &mut Vec<String>, target: &str) {
    // Problem: can't borrow v immutably and mutably at once
    // let pos = v.iter().position(|s| s == target);
    // v.insert(pos.unwrap(), "new".to_string());

    // Solution: collect what you need, then modify
    let pos = v.iter().position(|s| s == target);
    if let Some(idx) = pos {
        v.insert(idx, "new".to_string());
    }
}
```

### Pattern 3: Clone When Necessary

```rust
fn process(data: &[String]) -> Vec<String> {
    // If you need to own a copy, clone explicitly
    data.iter()
        .filter(|s| !s.is_empty())
        .cloned()
        .collect()
}
```

### Pattern 4: Use `split_at_mut` for Mutable Slices

```rust
fn split_example() {
    let mut v = vec![1, 2, 3, 4, 5];

    // Can't do this:
    // let left = &mut v[0..2];
    // let right = &mut v[2..4]; // ERROR: second mutable borrow

    // Use split_at_mut:
    let (left, right) = v.split_at_mut(2);
    // left = [1, 2], right = [3, 4, 5]
    left[0] = 10;
    right[0] = 30;
}
```

### Pattern 5: Restructure Data Ownership

```rust
// Problem: self-referential struct
struct Database {
    data: Vec<String>,
    // index: &Vec<String>, // Can't reference data
}

// Solution: use indices or owned data
struct Database {
    data: Vec<String>,
    index: Vec<usize>,  // Indices into data instead of references
}
```

## The Borrow Checker and Control Flow

The borrow checker understands conditional and loop control flow:

```rust
fn example() {
    let mut x = 5;
    let r = &x;

    if true {
        println!("{}", r);
    }

    // r is dead here (NLL)
    x = 10;  // OK
}
```

## Two-Phase Borrows

Rust uses **two-phase borrows** for method calls with `&mut self`:

```rust
let mut v = vec![1, 2, 3];
// v.push(v.len());
// This works because:
// Phase 1: v is borrowed immutably to compute v.len()
// Phase 2: v is borrowed mutably for push()
// The immutable borrow ends before the mutable one begins
v.push(v.len()); // OK!
```

## Lifetime Elision Rules

The compiler can often infer lifetimes without explicit annotations. These are the **three elision rules**:

1. **Each input reference gets its own lifetime parameter**
   - `fn foo(x: &str, y: &str)` → `fn foo<'a, 'b>(x: &'a str, y: &'b str)`

2. **If there's exactly one input lifetime, it's assigned to all output lifetimes**
   - `fn foo(x: &str) -> &str` → `fn foo<'a>(x: &'a str) -> &'a str`

3. **If one of the input parameters is `&self` or `&mut self`, the lifetime of `self` is assigned to all output lifetimes**
   - `fn foo(&self, x: &str) -> &str` → `fn foo<'a, 'b>(&'a self, x: &'b str) -> &'a str`

```rust
// Examples where elision works:

// Rule 1 + 2: one input → output gets same lifetime
fn first_word(s: &str) -> &str {  // Elided: fn first_word<'a>(s: &'a str) -> &'a str
    &s[..1]
}

// Rule 1 + 2: still works with one input
fn longest_prefix(s: &str) -> &str {  // Elided
    s
}

// Rule 3: &self → output gets self's lifetime
impl MyStruct {
    fn name(&self) -> &str {  // Elided: fn name<'a>(&'a self) -> &'a str
        &self.name
    }
}

// DOES NOT compile — two input lifetimes, compiler can't infer output
// fn longest(s1: &str, s2: &str) -> &str {  // ERROR: need explicit lifetime
//     if s1.len() > s2.len() { s1 } else { s2 }
// }

// Fix: explicit lifetime annotation
fn longest<'a>(s1: &'a str, s2: &'a str) -> &'a str {
    if s1.len() > s2.len() { s1 } else { s2 }
}
```

### Elision Rule Table

| Input | Output | Rule | Compiles? |
|-------|--------|------|-----------|
| `(&str)` | `-> &str` | Rule 2 | ✅ |
| `(&str, &str)` | `-> &str` | No rule applies | ❌ |
| `(&self, &str)` | `-> &str` | Rule 3 | ✅ |
| `(&self)` | `-> &str` | Rule 3 | ✅ |
| `(&mut self)` | `-> &str` | Rule 3 | ✅ |
| `()` | `-> &str` | No input lifetime | ❌ (dangling) |

## The Borrow Checker and Lifetimes

Lifetimes are the borrow checker's way of tracking how long references are valid:

```rust
fn main() {
    let r;                      // 'a: lifetime of r starts
    {                           // 'b: inner scope starts
        let x = 5;             // 'c: lifetime of x starts
        r = &x;                // r borrows x — r's lifetime must be <= x's
    }                           // 'c ends: x dropped, r would be dangling
    // println!("{}", r);      // ERROR: r references x which doesn't live long enough
}
```

### Structs with Lifetimes

```rust
// Struct that holds a reference must annotate the lifetime
struct Excerpt<'a> {
    text: &'a str,
}

impl<'a> Excerpt<'a> {
    // Rule 3: output gets self's lifetime
    fn text(&self) -> &str {
        self.text
    }

    // Explicit: announce method — takes another reference
    fn announce(&self, announcement: &str) -> &str {
        println!("Attention: {}", announcement);
        self.text  // Returned reference has self's lifetime
    }
}

fn main() {
    let novel = String::from("Call me Ishmael. Some years ago...");
    let first_sentence = novel.split('.').next().expect("Could not find '.'");
    let excerpt = Excerpt { text: first_sentence };
    println!("Excerpt: {}", excerpt.text());
}
```

## Polonius: The Next-Generation Borrow Checker

Rust is transitioning from the current borrow checker to **Polonius**, which uses a more precise analysis:

| Feature | Current (NLL) | Polonius (future) |
|---------|---------------|-------------------|
| Analysis type | Liveness-based | Origin-based (subset relations) |
| Precision | Last use kills borrow | Tracks actual dataflow |
| Some valid code rejected? | Yes | Fewer false rejections |
| Status | Stable | In development (Rust 2024+) |

```rust
// Example that Polonius could accept but current borrow checker rejects:
fn get_or_insert(map: &mut HashMap<String, String>, key: String) -> &str {
    if let Some(value) = map.get(&key) {
        return value;  // Immutable borrow ends here (early return)
    }
    map.insert(key.clone(), String::from("default"));
    // Current borrow checker: might reject this
    // Polonius: understands that get() borrow ended before insert()
    map.get(&key).unwrap()
}
```

## Common Anti-Patterns

### Anti-Pattern 1: Self-Referential Structs

```rust
// PROBLEM: struct references its own field
// struct SelfRef {
//     data: String,
//     reference: &str,  // Can't reference data — different lifetimes
// }

// Solution 1: Use indices
struct SafeSelfRef {
    data: String,
    offset: usize,
    len: usize,
}

// Solution 2: Use Pin (advanced)
use std::pin::Pin;
// Pin prevents the pointed-to data from being moved

// Solution 3: Use a crate like `ouroboros` or `self_cell`
```

### Anti-Pattern 2: Fighting the Borrow Checker

```rust
// WRONG: Trying to mutate while iterating
// fn remove_evens(v: &mut Vec<i32>) {
//     for &x in &*v {
//         if x % 2 == 0 {
//             v.retain(|&n| n != x);  // Can't mutably borrow while iterating
//         }
//     }
// }

// RIGHT: Use retain directly
fn remove_evens(v: &mut Vec<i32>) {
    v.retain(|&x| x % 2 != 0);
}

// RIGHT: Collect, then modify
fn transform(v: &mut Vec<String>) {
    let indices: Vec<usize> = v.iter()
        .enumerate()
        .filter(|(_, s)| s.is_empty())
        .map(|(i, _)| i)
        .collect();
    for i in indices.into_iter().rev() {
        v.remove(i);
    }
}
```

### Anti-Pattern 3: Returning References to Temporary Data

```rust
// WRONG: Returns reference to local variable
// fn bad() -> &String {
//     let s = String::from("hello");
//     &s  // s is dropped — dangling reference!
// }

// RIGHT: Return owned data
fn good() -> String {
    String::from("hello")
}

// RIGHT: Return reference with tied lifetime
fn find<'a>(data: &'a [String], target: &str) -> Option<&'a str> {
    data.iter()
        .find(|s| s.contains(target))
        .map(|s| s.as_str())
}
```

## Common Anti-Patterns

1. **Fighting the borrow checker instead of redesigning** — If the compiler rejects your code, your design may have a logical issue
2. **Overusing `clone()` to satisfy the borrow checker** — Usually indicates a design problem
3. **Not understanding NLL** — Code that was rejected in Rust 2015 may compile in Rust 2018+
4. **Assuming borrows last until end of block** — NLL means borrows end at last use
5. **Trying to mutate a collection while iterating** — Use `retain`, indices, or collect-then-modify patterns

## Interview Questions

1. **What does the borrow checker do?**
   The borrow checker is a compile-time analysis tool that enforces Rust's ownership and borrowing rules. It ensures references are valid, mutable references are exclusive, and no data races exist.

2. **What are Non-Lexical Lifetimes (NLL)?**
   NLL is a borrow checker improvement where borrows end at the last use of the reference rather than at the end of the lexical block. This makes Rust more ergonomic without sacrificing safety.

3. **How do you handle a situation where the borrow checker rejects valid code?**
   Restructure the code: limit borrow scopes, use indices instead of references, clone when necessary, or redesign the data ownership. The borrow checker is usually right.

4. **Can you give an example where NLL makes a difference?**
   ```rust
   let mut v = vec![1, 2, 3];
   let first = &v[0];
   println!("{}", first); // last use of first
   v.push(4); // OK with NLL, would fail without
   ```

5. **What is a two-phase borrow?**
   Two-phase borrows allow `&mut self` method calls to first immutably borrow the receiver for argument evaluation, then mutably borrow it for the method body. Example: `v.push(v.len())`.

## References

- [The Rust Programming Language — References and Borrowing](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html)
- [The Rust Programming Language — Lifetimes](https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html)
- [Rustonomicon — Lifetimes](https://doc.rust-lang.org/nomicon/lifetimes.html)
- [NLL (Non-Lexical Lifetimes) RFC](https://rust-lang.github.io/rfcs/2094-nll.html)
- [Polonius — Next-gen borrow checker](https://github.com/rust-lang/polonius)

## See Also

- [Ownership](./ownership.md) — The ownership rules the borrow checker enforces
- [Lifetimes](./lifetimes.md) — How lifetimes relate to borrowing
- [Unsafe Rust](./unsafe.md) — Bypassing the borrow checker
- [Concurrency](./async.md) — How the borrow checker prevents data races
