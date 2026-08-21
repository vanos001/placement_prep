# Rust Traits and Generics: a Deep Dive

This page covers Rust's trait system from the type-theory up: trait
definition and `impl` blocks, the four kinds of bounds (including `where`
clauses and `impl Trait`), associated types vs. generic parameters, trait
objects and the vtable layout that makes them work, the sealed-trait
pattern, blanket impls, and the orphan rule that prevents the
diamond-problem style of conflict. It closes with a comparison to Haskell
typeclasses and Java interfaces, which is the standard question when an
interviewer wants to know whether you understand *why* Rust's design differs
from what came before.

## 1. Trait definitions and `impl` blocks

A trait is a named set of methods and types that a type may provide. The
minimal form is:

```rust
trait Draw {
    fn draw(&self, canvas: &mut Canvas);
}

struct Button { label: String }
struct TextBox { text: String }

impl Draw for Button {
    fn draw(&self, canvas: &mut Canvas) {
        canvas.rect(/* ... */);
    }
}

impl Draw for TextBox {
    fn draw(&self, canvas: &mut Canvas) {
        canvas.text(&self.text);
    }
}
```

Default methods are allowed:

```rust
trait Logger {
    fn log(&self, msg: &str);
    fn warn(&self, msg: &str) { self.log(&format!("[warn] {msg}")); }
}
```

A type implementing `Logger` only needs to provide `log`; `warn` is
inherited. Traits can also declare associated types, associated constants,
and generic methods, all of which we'll see.

## 2. Generics: monomorphization first

A generic function in Rust compiles to one fresh copy of the body per
concrete type it's instantiated with:

```rust
fn first<T>(xs: &[T]) -> Option<&T> {
    xs.first()
}
```

When you call `first::<i32>` and `first::<String>`, the compiler emits two
distinct non-generic functions, one specialized for `i32` and one for
`String`. This is *monomorphization*, the same model C++ templates use. The
upside is performance: each specialization can be inlined and optimized
independently. The downside is code size and compile time. Rust mitigates
the code-size blowup with *shared generics* in `dylib` rlibs and *generic
deduplication* in the MIR inliner.

Crucially, **a generic `fn` with no bounds can do almost nothing** with its
type parameters. It can move values, return them, put them in a `Vec`, and
that's it. To call methods or use operators, you must declare *trait bounds*.

## 3. The four kinds of bounds

### 3a. Inline bounds

```rust
fn largest<T: PartialOrd + Clone>(xs: &[T]) -> Option<T> {
    xs.iter().max().cloned()
}
```

`T: PartialOrd + Clone` says "T implements both `PartialOrd` and `Clone`."
Multiple bounds use `+`.

### 3b. `where` clauses

When bounds get long or refer to associated types, they become unreadable
inline:

```rust
fn parse<R>(reader: R) -> Result<u64, ParseError>
where
    R: Read + BufRead,
    R::IntoIter: Iterator<Item = io::Result<u8>>,
{
    // ...
}
```

`where` clauses are the canonical form. They can also be conditional:

```rust
fn debug<T>(x: T) where T: std::fmt::Debug { /* ... */ }
```

### 3c. `impl Trait` in argument position

```rust
fn iter_all() -> impl Iterator<Item = u32> { (0..10).collect::<Vec<_>>().into_iter() }
fn take(iter: impl Iterator<Item = u32>) { /* ... */ }
```

`impl Trait` in argument position is sugar for an anonymous type parameter
with that bound. `fn take(iter: impl Iterator<Item = u32>)` desugars to
`fn take<I: Iterator<Item = u32>>(iter: I)`. The turbofish (`take::<I>`)
disappears — you can no longer specify the type explicitly.

### 3d. `impl Trait` in return position

Returning `impl Trait` is different: it's a way to say "I'm returning some
concrete type that implements this trait, but I won't tell you which." The
caller can rely on the bound but cannot name the underlying type. The most
important use is returning closures (which have unnameable types) and
`async fn` futures:

```rust
fn counter() -> impl Fn() -> u32 {
    let mut n = 0;
    move || { n += 1; n }
}
```

The returned closure has a type the compiler generates (`closure@...`) that
cannot be written down. `impl Fn(...) -> u32` is the only way to expose it.

There is an asymmetry: argument-position `impl Trait` is universally
quantified ("for any `I`"), return-position `impl Trait` is existentially
quantified ("there exists some `I`, and I'm choosing it"). The distinction
matters when reasoning about coherence (section 8).

## 4. Associated types vs. type parameters

`Iterator` has an associated type `Item`:

```rust
trait Iterator {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
}
```

Why associated rather than `Iterator<T>`? Because a type typically has one
canonical way of being iterated, not many. `Vec<u32>` is an iterator that
yields `u32`; you wouldn't want to have to write `Vec<u32>: Iterator<u32>`
and `Vec<u32>: ReverseIterator<u32>` and so on. Associated types give one
canonical choice per impl:

```rust
impl Iterator for IntoIter<u32> {
    type Item = u32;
    fn next(&mut self) -> Option<u32> { /* ... */ }
}
```

Generic parameters (e.g. `trait From<T>`) are appropriate when a single type
can implement the trait multiple times with different type arguments. `i32`
implements `From<u8>`, `From<u16>`, `From<bool>`, etc., so `From` is generic
in `T` rather than associated.

A useful test: if a single `impl` block can supply all the variants, use a
generic parameter; if not, use an associated type.

## 5. `dyn Trait` vs. `impl Trait`

These are the two ways to use a trait as a *type*, and they are the most
common source of confusion in interviews.

### `dyn Trait`: dynamic dispatch, one type at runtime

```rust
fn draw_all(items: &[Box<dyn Draw>]) {
    for it in items { it.draw(&mut canvas); }
}
```

`dyn Draw` is a *trait object*. Its representation is a wide pointer — two
words:

```
+----------+----------+
|  *data   |  *vtable |
+----------+----------+
     |           |
     v           |
   heap value    |
                 v
              +-------+
              | *draw |
              | *drop |
              | size  |
              | align |
              +-------+
```

The `vtable` is a static table emitted by the compiler for the
`impl Draw for Button` implementation. It contains the function pointer for
`draw`, the drop glue, and the size and alignment of the underlying type.
Calling `it.draw(...)` is one indirect call through that pointer.

Trait objects erase the static type. Their advantage is homogeneous
collections of heterogeneous values (a `Vec<Box<dyn Draw>>` of `Button`s and
`TextBox`es). Their cost: a vtable indirection per method call, the
constraint that the trait be *object safe*, and the loss of monomorphization.

Object safety rules: no associated functions without a `self` receiver (you
can't call `Button::new()` through a `dyn Draw` because there's no concrete
type), no methods with generic parameters (you'd need a vtable entry per
monomorphization), no associated constants that aren't `Self: Sized`-gated,
and `Self` must not appear in any other position than `&self` / `&mut self` /
`self` (with some recent relaxations, e.g. `where Self: Sized` methods are
allowed).

### `impl Trait`: static dispatch, one type at compile time

```rust
fn draw_all<I: Draw>(items: &[I]) { /* ... */ }
```

or

```rust
fn draw_all(items: &[impl Draw]) { /* ... */ }
```

Here each instantiation of `draw_all` for a different `Draw` type gets its
own monomorphized copy, with direct calls. It's faster but bloats code and
forces callers to commit to a single type per call site. You cannot make a
`Vec<impl Draw>` (the type is fixed at compile time).

### When to use which

- One or two concrete types known at compile time → generics.
- Many types, runtime polymorphic, small bodies → `dyn Trait`.
- Hot code where vtable indirection measurably hurts → generics.
- Public API for plugins or trait objects (e.g. `Box<dyn Executor>`) → `dyn`.

The standard library is heavy on `dyn` at API seams (`Box<dyn Error>`,
`Box<dyn Future>`, `&[&dyn ToString]`) and heavy on generics in the hot paths
(`Iterator::map`, `HashMap<K, V, S: BuildHasher>`).

## 6. The sealed trait pattern

Traits marked `pub` can be implemented by anyone, which is a problem if you
want to control the implementations (e.g. to add methods later without
breaking downstream impls). The sealed-trait pattern uses a private
super-trait to prevent downstream impls:

```rust
mod sealed { pub trait Sealed {} }

pub trait Service: sealed::Sealed {
    fn handle(&self, req: Request) -> Response;
}

// Only the local crate can implement Sealed, so only the local
// crate can implement Service, even though Service is public.
pub struct HttpService;
impl sealed::Sealed for HttpService {}
impl Service for HttpService { /* ... */ }
```

Downstream users can call `Service::handle` on an `HttpService` but cannot
write `impl Service for MyType` — the `sealed::Sealed` bound is unreachable.
`std::fmt::Write`, `std::error::Error`'s various internal traits, and the
`futures` crate's `Stream` trait all use this technique.

## 7. Blanket impls and `impl<T: Trait> Trait for T`

A blanket impl is an `impl` of a trait for any type satisfying some bound.
The most common one in `std` is:

```rust
impl<T: ?Sized> ToString for T where T: Display { /* ... */ }
```

Any `Display` type is automatically `ToString`. Blanket impls are powerful
but dangerous: they commit forever to the trait's API on a wide open set of
types, and they constrain all future trait additions (a new required method
would break the blanket impl).

Blanket impls are the standard way to express trait composition. The
`iter::FromIterator` blanket over `Extend`, the `Clone` blanket for
`Arc<T> where T: ?Sized + Clone`, etc., are all of this form.

## 8. Coherence and the orphan rule

The trait system guarantees that, for any given `(Type, Trait)` pair, there
is at most one `impl` block in the entire program. This property is called
*coherence*, and it is enforced by the **orphan rule**:

> You may implement a trait `T` for a type `U` only if either `T` or `U` (or
> both) is local to your crate.

Concretely, you cannot implement `Display` for `Vec<T>` because both
`Display` and `Vec` live in `std`. If two downstream crates both tried, the
compiler would not be able to pick one.

The orphan rule is why `From`/`Into` work cleanly across crates: if you
define `MyError` in your crate, you can `impl From<io::Error> for MyError`
because `MyError` is local even though `io::Error` and `From` are not.

Without coherence, generics would be unsound: a generic `fn min<T:
Ord>(...)` needs to know that there is one and only one `Ord` impl for `T`,
or different compilation units could disagree on the answer.

There are escape hatches in progress: `#[marker]` traits (RFC 2277) allow
multiple blanket impls of pure-marker traits, and `negative_impls` lets you
opt out of `Send`/`Sync` for specific types. Neither weakens coherence in
the general case.

## 9. Comparison to Haskell typeclasses

Haskell's typeclasses are the closest cousin to Rust's traits, and the
differences are instructive.

| Property            | Haskell typeclasses         | Rust traits                  |
|---------------------|------------------------------|------------------------------|
| Dispatch            | Typeclasses (static), `forall a. C a => ...`; dictionaries passed implicitly | Generics (static) and `dyn Trait` (dynamic) |
| Orphan rule         | None — orphan instances are warned but allowed | Enforced — compile error |
| Coherence           | Violated if orphans are used, leading to silent bugs | Hard invariant |
| Higher-rank types   | Yes (`forall a. ...` in types) | Limited (mostly `for<'a>` lifetimes) |
| Functional deps     | Yes (multi-param typeclasses with `FunctionalDependencies`) | No — associated types fill the same role |
| Overlapping instances | Allowed with `OVERLAPPING` pragma | Forbidden (except `default` methods and special-cased impls) |
| `impl` lookup at runtime | Lazy, via constraint solver | Eager, monomorphic at every call site |

The headline difference: Haskell allows orphan instances and pays for it
with "instance conflicts" between modules. Rust's orphan rule prevents this
but restricts expressiveness (you can't `impl Show for Vec<T>` from outside
`std`).

## 10. Comparison to Java interfaces

| Property          | Java interface                  | Rust trait                       |
|-------------------|---------------------------------|----------------------------------|
| Dispatch          | Always virtual (vtable)         | Static (generic) or dynamic (`dyn`) |
| Object layout     | Interface pointer + data        | Same wide-pointer layout when used as `dyn Trait` |
| Multiple impls    | A class may `implements` many   | A type may `impl` many           |
| Default methods   | Yes (`default` keyword)         | Yes (body in trait)              |
| Static methods    | Yes (`static`)                  | Yes, but uncallable through `dyn` |
| Generics          | Type-erased (`List<T>` becomes `List<Object>` at runtime) | Monomorphized for value types; only `dyn Trait` is erased |
| State             | Interfaces may not have fields (pre-Java 16; record types do) | Traits may not have fields (composition via fields on the struct) |

The deepest difference is that Java interfaces are virtual by default;
Rust's generics are static by default and `dyn Trait` is the explicit opt-in
to virtual dispatch. This is why "Rust feels like a hybrid between C++
templates and Java interfaces" — it actually is, at the type-system level.

## 11. Special traits worth knowing

- `Sized` is implicit on every type parameter. `T: ?Sized` opts out, used
  for `&str`, `[T]`, `dyn Trait`. `?Sized` is the only question-mark bound
  in the language.
- `Drop` is implicit; you cannot `impl Drop` and `impl Copy` on the same
  type — copies don't run drop.
- `Deref` enables `*` and method call coercion but is *not* transitive
  through `dyn` — `&Box<dyn Trait>` cannot be coerced to `&dyn Trait`.
- `Borrow`, `AsRef`, `Into`/`From` are the standard conversion traits.
  Prefer `From` over `Into` (the impl is symmetric via a blanket).
- `Iterator`'s associated type `Item` plus the lazy `next` is the canonical
  "associated type" example.
- `Fn`/`FnMut`/`FnOnce` form a subtrait hierarchy. A `Fn` closure is also
  `FnMut` and `FnOnce`; the reverse is false. Choosing the most-permissive
  bound (`FnOnce` if you call once, `FnMut` if you call many times with
  `&mut` captures, `Fn` if you need `&` captures only) makes APIs flexible.

## References

- The Rust Reference — Traits — https://doc.rust-lang.org/reference/types.html#trait-objects
- The Rust Book ch. 10 — Generic Types, Traits, and Lifetimes — https://doc.rust-lang.org/book/ch10-02-traits.html
- Rust RFC 1149 — Closures: Capture-Mode and `move` — https://rust-lang.github.io/rfcs/0114-closures.html
- Rust RFC 2071 — Object safety for generics — https://rust-lang.github.io/rfcs/2071-impl-trait-type.html
- Niko Matsakis's blog — https://smallcultfollowing.com/babysteps/
- Niko Matsakis, "Where clauses and the orphan rule" — https://smallcultfollowing.com/babysteps/blog/2017/09/15/coherence-based-on-explicit-orphan-rules/
- Haskell Wiki, Orphan instances — https://wiki.haskell.org/Orphan_instance
- Inside Rust blog, "dyn and impl Trait in detail" — https://blog.rust-lang.org/2018/04/06/impl-trait.html
- `std::iter::Iterator` source — https://doc.rust-lang.org/src/core/iter/traits/iterator.rs.html
- Sealed traits pattern, Predrag Gruevski — https://predr.ag/blog/on-sealed-traits/
