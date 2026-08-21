# Rust Error Handling: a Deep Dive

This page covers what the `Result` type actually does, how the `?` operator
desugars, what the `std::error::Error` trait gives you, how `thiserror` and
`anyhow` fill complementary roles, how error propagation works across
`.await` points, how to write downcast-friendly custom error enums, and why
the "no panics in library code" principle matters. The closing section
compares Rust's model with Go's `error`/`panic`, C++ exceptions, and Java's
checked/unchecked split.

## 1. `Result<T, E>` is just an enum

`Result` lives in `core::result` and is defined as:

```rust
pub enum Result<T, E> {
    Ok(T),
    Err(E),
}
```

That's the whole type. There is no exception table, no unwinding machinery,
no runtime object. The type carries the error state explicitly as a value,
which means: every call site that can fail must acknowledge the
possibility by handling the `Result` (with `match`, `let-else`, `?`, etc.)
or by explicit `.unwrap()` / `.expect(...)` that says "I assert this is `Ok`,
and panic otherwise."

This is the central design decision. Errors are *values*, not control
flow. Functions don't "throw"; they return a different variant of an enum.
The caller sees the variant in the type signature, and the compiler forces
acknowledgement via `#[must_use]` on `Result` itself.

The cost surface is straightforward: a `Result` is the size of `max(T, E)`
plus one byte for the discriminant (or smaller with niche optimization —
`Result<NonZeroU32, ()>` is the same size as `u32`). For infallible fast
paths, branch prediction makes the `match` essentially free.

## 2. The `?` operator: three desugarings

The `?` operator looks like a single piece of syntax but desugars three
different ways depending on context.

### Same error type

```rust
fn read_config(path: &Path) -> Result<Config, io::Error> {
    let s = fs::read_to_string(path)?;     // 1
    let cfg = parse(&s)?;                  // 2
    Ok(cfg)
}
```

Here `?` desugars to:

```rust
match fs::read_to_string(path) {
    Ok(v) => v,
    Err(e) => return Err(From::from(e)),
}
```

The `From::from` is what makes `?` compose: it lets you `?`-propagate any
`Err` whose type can be converted into the function's error type. That
conversion is supplied by `impl From<io::Error> for MyError`, which
`thiserror` generates for you.

### Inside `Option`

```rust
fn first_word(s: &str) -> Option<&str> {
    let s = s.strip_prefix("pre ")?;       // returns None if prefix absent
    Some(s.split_whitespace().next()?)
}
```

In an `Option`-returning function, `?` on an `Option` short-circuits with
`None`. `Result` and `Option` cannot be mixed — `?` on an `Option` in a
`Result`-returning function is a type error unless you wrap explicitly with
`.ok_or(...)?` or `.transpose()`.

### Inside an `async fn`

```rust
async fn fetch(url: &str) -> Result<Bytes, anyhow::Error> {
    let resp = client.get(url).send().await?;
    Ok(resp.bytes().await?)
}
```

The desugaring is unchanged, but the `?` is inside a generator state
machine. The early `return Err(...)` becomes a state transition that sets
the enum to `Done(Err(...))` on the next poll. There is nothing special
about error handling in async code; the same `From` conversions apply,
the same `?` syntax works, and `JoinHandle::await` returns `Result<T,
JoinError>` so you can `?`-propagate task panics.

### Control flow summary

```
caller          callee
  |   fn f() -> Result<T,E>
  |     |
  |     v
  |  let x = g()? ;        g returns Result<U,E2>
  |     |
  |     v
  |  Ok path: x = g().unwrap(); continue
  |  Err path: Err(From::from(e)) propagated
  |     |
  v     v
  match f() { Ok(t) => ..., Err(e) => ... }
```

## 3. The `Error` trait and `Error::source`

`std::error::Error` is a small trait:

```rust
pub trait Error: Debug + Display {
    fn source(&self) -> Option<&(dyn Error + 'static)> { None }
    fn description(&self) -> &str { /* deprecated */ }
    fn cause(&self) -> Option<&dyn Error> { self.source() }
    fn provide<'a>(&'a self, demand: &'a mut Demand<'a>) { /* extensible */ }
}
```

Three things matter:

- The `Debug + Display` supertraits mean every error must be printable both
  ways. `Display` is what the user-facing message looks like; `Debug` is the
  full developer-facing dump including causes.
- `source()` returns the *cause* of this error as a trait object, enabling
  error chaining. If a high-level "ConfigurationError" wraps an
  `io::Error`, `source()` should return `Some(&io_err)`. Iterating `source()`
  walks the chain — `anyhow`'s `{:?}` printer does this to render a
  multi-line trace.
- `provide` (stabilized in 1.84, replacing the unstable `Error::type_id`
  backport) is a typed ad-hoc query mechanism, used by `Request`-style
  extension — most users will never implement it directly.

`Error` is object safe, so you can store `Box<dyn Error + Send + Sync>`
and downcast back to concrete types (see section 6).

## 4. `thiserror` vs. `anyhow`: the canonical pair

The Rust ecosystem has converged on two error libraries that solve two
different problems.

### `thiserror` — library error enums

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum DatastoreError {
    #[error("io error: {0}")]
    Io(#[from] io::Error),

    #[error("serialization failed")]
    Serialize(#[from] serde_json::Error),

    #[error("not found: {key}")]
    NotFound { key: String },
}
```

`thiserror` is a derive macro that generates `Display` impls from
`#[error("...")]` attributes and `From` impls from `#[from]` attributes.
The result is a typed enum that callers can `match` against. This is the
correct choice for **library crates** where the caller needs to
discriminate error kinds and react differently.

`thiserror` generates no allocations and is `no_std`-compatible. It adds
zero runtime cost; the `Display` and `From` impls are what you would write
by hand.

### `anyhow` — application-level error boxes

```rust
use anyhow::{Context, Result};

fn run() -> Result<()> {
    let s = fs::read_to_string("config.toml").context("failed to read config")?;
    parse(&s).context("config parse error")?;
    Ok(())
}
```

`anyhow::Error` is a single owned trait object wrapping any `E: Error +
Send + Sync + 'static`, plus a stack of context strings attached at each
`?` site via `.context(...)`. It is *not* an enum; the underlying concrete
error is erased. The advantage: you can `?`-propagate errors from many
different libraries without writing one big `enum` and a forest of `From`
impls. The cost: callers cannot `match` on the error kind without
downcasting (which is fragile across versions).

The rule of thumb: **`thiserror` for libraries, `anyhow` for binaries.**
A library should return `Result<T, ConcreteErrorEnum>`. A binary should
return `anyhow::Result<T>` at its top-level functions. Mixing them is fine —
`anyhow::Error::msg` accepts any `Error`-implementing type.

### The third option: hand-rolled enums

```rust
#[derive(Debug)]
pub enum HttpError {
    Status(u16),
    Io(io::Error),
}

impl fmt::Display for HttpError { /* ... */ }
impl Error for HttpError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self { HttpError::Io(e) => Some(e), _ => None }
    }
}
impl From<io::Error> for HttpError {
    fn from(e: io::Error) -> Self { HttpError::Io(e) }
}
```

For tiny error types, this is the most transparent option and adds zero
dependencies. `thiserror` just autogenerates this boilerplate.

## 5. Errors in async code

The async story has one wrinkle worth being precise about:

- **`?` works identically in `async fn`.** A `Result`-returning `async fn`
  desugars to a future whose `Output` is `Result<T, E>`. `?` short-circuits
  into `Done(Err(...))` on the next poll.
- **`tokio::spawn(fut)` yields `JoinHandle<T>`, and `await`ing it returns
  `Result<T, JoinError>`.** `JoinError` represents either a panic in the
  spawned task or its cancellation. `?`-propagating the join result thus
  conflates task-internal errors with task-panics — be explicit:
  ```rust
  let out = tokio::spawn(work()).await
      .context("worker panicked")??;   // double ? — one for JoinError, one for inner
  ```
- **Cancellation may drop a future mid-`?`.** If a future is dropped after
  it has begun but before its side effect is committed (e.g. halfway
  through writing a file), the `Drop` impl of any locals is responsible for
  cleanup. There is no `finally` block; the discipline is "design `Drop` to
  be cancellation-safe."
- **Bridging error types across `.await`** is the same as bridging across
  `?` in sync code: `From` impls or `map_err`. The `futures::TryStreamExt::
  map_err` and `tokio::try_join!` are common utilities.

## 6. Custom error types and downcasting

When `anyhow::Error` (or a `Box<dyn Error>`) reaches the top of the call
stack and you want to handle a specific kind:

```rust
let err: anyhow::Error = /* ... */;
if let Some(io_err) = err.downcast_ref::<io::Error>() {
    if io_err.kind() == io::ErrorKind::NotFound {
        // recover
    }
}
```

`downcast_ref::<T>()` uses `Any` (which is auto-implemented for `T: 'static
+ Send + Sync`-ish) and returns `Option<&T>`. The `'static` bound on the
target type is required so the downcast has a stable type id.

For custom enums the equivalent is plain `match`:

```rust
match err {
    DatastoreError::NotFound { key } => /* ... */,
    DatastoreError::Io(io) if io.kind() == io::ErrorKind::PermissionDenied => /* ... */,
    _ => return Err(err.into()),
}
```

Prefer `match` over downcast where possible: it's checked at compile time,
refactors safely, and survives enum restructuring.

## 7. The "no panics in library code" principle

A library function that panics is one the caller cannot easily defend
against. `Result` lets the caller decide; `panic!` decides for them.
Panicking in library code is appropriate only when:

- A **safety invariant** is violated and continuing could lead to UB
  (e.g. `Mutex::lock` poisoning, `unwrap` on a `OnceLock` that should be
  initialized).
- An **API contract** documented as infallible is violated by the caller
  in a way that cannot be expressed in the type system (e.g. indexing
  out of range, passing a null `&mut`).
- An **internal consistency** assertion has been violated (e.g. an enum
  has an unexpected variant) — usually `unreachable!()`.

Everything else should return `Result`. A library that panics on bad
input data is un-callable from a service that needs to keep running.

There are also "soft panics" via `Result::unwrap`, `.expect`, indexing
`xs[i]`, integer division `a / b`, and slice patterns — all of which
abort the current thread (in `std`) or abort the process (in `no_std`).
Audit them in library code.

## 8. Comparison to other languages

### Rust vs Go

| Aspect | Rust | Go |
|--------|------|-----|
| Failure representation | `Result<T, E>` value | `value, err` tuple |
| Mandatory acknowledgement | `#[must_use]` warning | Lint `errcheck`; not enforced |
| Early return | `?` operator | `if err != nil { return err }` |
| Cause chain | `Error::source()` | `errors.Wrap`, `errors.Is/As` |
| Panics | Thread abort, recoverable per-thread | `panic` + `recover` |
| Performance | Branch + cold `Err` path | Same |

Go's design forces the boilerplate; Rust's `?` makes it one character.
Go's errors are untyped values (an `error` interface); Rust's are typed
enums that callers can match exhaustively.

### Rust vs C++ exceptions

| Aspect | Rust | C++ |
|--------|------|-----|
| Cost on success path | One branch (predictable, often free) | Zero on most ABIs (table-driven) |
| Cost on failure path | Same as Ok path's allocation | Unwinding, often O(stack depth) |
| Destructors run? | Only if locals are dropped | Yes, in stack order |
| Across FFI | Works (Result is a value) | Unspecified / often crashes |
| Async behavior | First-class (just values) | Thrown exceptions can interact badly with coroutines; needs C++20 coroutines-specific machinery |
| Ordering guarantees | Deterministic, value-based | Non-deterministic across TUs with noexcept changes |

The headline trade: Rust pays on the success path (a branch), C++ pays on
the failure path (unwinding). For services where errors are common (network
timeouts, partial failures), Rust's model is often faster.

### Rust vs Java

| Aspect | Rust | Java |
|--------|------|------|
| Checked exceptions | None — `Result` is the type-level declaration | Checked exceptions must be caught or declared |
| Unchecked exceptions | `panic!` (per-thread) | `RuntimeException` (process-wide) |
| Error typing | Enum with sum types | Class hierarchy rooted at `Throwable` |
| Pattern matching | `match` on enum variants | `catch (FooException e)` |
| Generics interaction | First-class (`Result<T, E>` is a normal generic) | Erased; `catch` is by class, not generic |

Java's checked-exception system is the spiritual ancestor of `Result`, but
it shares Java's generics erasure problem: you cannot write
`<T extends Throwable> Result<T, E>` and pattern-match by generic parameter
because exceptions are erased. Rust's `Result<T, E>` is fully monomorphic
and the variants are real, exhaustively matchable data.

## 9. Practical conventions

- **Library crates:** define a top-level `Error` enum (thiserror or
  hand-rolled), re-export as `pub type Result<T> = std::result::Result<T,
  Error>`.
- **Binary crates:** use `anyhow::Result` everywhere except at library
  boundaries, where you convert.
- **Always use `?` rather than `match` for propagation unless you need to
  transform the error or branch on it.**
- **Prefer `.context("...")` over `.map_err(|e| format!("{e}"))`.** The
  context preserves the typed underlying error for downstream inspection.
- **Do not implement `Error` for panics.** Panics are not errors and
  bridging the two leads to control flow you didn't write.
- **Audit `unwrap`/`expect`/`panic!` in libraries** with `RUSTFLAGS="-W
  clippy::unwrap_used"` or similar lint setups.

## References

- The Rust Book, ch. 9 — Error Handling — https://doc.rust-lang.org/book/ch09-00-error-handling.html
- `thiserror` crate documentation — https://docs.rs/thiserror/latest/thiserror/
- `anyhow` crate documentation — https://docs.rs/anyhow/latest/anyhow/
- Rust RFC 2442 — `try` blocks and `?`-style operators history — https://rust-lang.github.io/rfcs/2442-replace-...-with-..html (and the original RFC 1715 — `?` operator)
- RFC 1715 — `?` operator for error propagation — https://rust-lang.github.io/rfcs/1717-impl-trait-for-dyn-trait.html (related)
- Burntsushi, "Error Handling in Rust" — https://blog.burntsushi.net/error-handling/
- Without Boats, "Why `?` works the way it does" — https://without.boats/blog/why-result-works/
- `std::error::Error` API reference — https://doc.rust-lang.org/std/error/trait.Error.html
- `Error::provide` stabilization RFC — https://rust-lang.github.io/rfcs/3043-err-derive.html
- Failure-to-anyhow migration notes — https://github.com/dtolnay/anyhow/blob/master/README.md
