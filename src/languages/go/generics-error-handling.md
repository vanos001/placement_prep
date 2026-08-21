# Go Generics and Error Handling — Deep Dive

Go added type parameters in 1.18 (March 2022) and reshaped the error model
around `errors.Is/As/Join` plus `%w` wrapping across 1.13 and 1.20. This
page covers both subsystems as a single coherent piece: the *type system*
goes from interface-typed-with-`interface{}` (slow, boxy) to type-parameter
typed (fast, no boxing), and the *error model* goes from
`if err != nil` equality checks to a structured unwrapping tree. The
sibling pages [modules-interfaces](./modules-interfaces.md),
[channels](./channels.md), [scheduler](./scheduler.md) cover other
aspects of Go; this page covers the language-level mechanism.

## 1. Generics — Type Parameters

### 1.1 Syntax and the type-parameter list

```go
// A generic function — T is a type parameter, any is the constraint
func Map[T, U any](in []T, f func(T) U) []U {
    out := make([]U, len(in))
    for i, v := range in {
        out[i] = f(v)
    }
    return out
}

// A generic type
type Ring[T any] struct {
    buf []T
    head, tail int
}

func (r *Ring[T]) Push(v T) { /* ... */ }
```

The square-bracket list `[T, U any]` is the *type-parameter list*; the
part after the colon (`any` here) is the *constraint*, which is an
interface. There is no equivalent of Rust's `where` clause — all
constraints live in the parameter list.

### 1.2 Predeclared constraints

Two predeclared constraints ship in the `builtin` package:

- `any` — alias for `interface{}`; the empty type set; accepts all types.
- `comparable` — accepts types that support `==` and `!=`. This is the
  constraint you use when implementing a generic map/set keyed by `K`,
  because the underlying implementation needs `==` to compare keys.

`comparable` is not expressible as a user-defined interface — `==` is
*not* a method. It is a built-in operator constraint that the compiler
matches against types whose operand supports `==` (struct/array of
comparables, primitives, pointers, channels, interfaces — but *not*
slices, maps, or funcs, which are non-comparable).

### 1.3 Custom constraints — type sets, `~T`, unions

A constraint is an interface, but Go 1.18 extended the interface syntax
to allow *type sets*:

```go
type Number interface {
    ~int | ~int8 | ~int16 | ~int32 | ~int64 |
    ~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 | ~uintptr |
    ~float32 | ~float64
}

func Sum[T Number](vals []T) T {
    var s T
    for _, v := range vals {
        s += v
    }
    return s
}
```

Two operators do the work:

- `~T` — "any type whose *underlying* type is T". So `~int` matches both
  `int` and `type MyInt int`. Without `~`, a named type `type MyInt int`
  would *not* satisfy the constraint — only `int` itself.
- `|` — union of type sets. The constraint is the union of all listed
  underlying types.

The `constraints` package at `golang.org/x/exp/constraints` provides the
common ones (`Ordered`, `Signed`, `Unsigned`, `Float`, `Integer`,
`Complex`). It is *not* in the standard library deliberately — the
generics designers want the community to settle on a small set of
constraints before freezing them in `std`.

### 1.4 Method constraints

A constraint can also require methods:

```go
type Stringer interface { String() string }

func Print[T Stringer](xs []T) {
    for _, x := range xs { fmt.Println(x.String()) }
}
```

The combination of method constraints and type-set constraints is allowed:

```go
type FloatStringer interface {
    ~float32 | ~float64
    String() string
}
```

Note the asymmetry: `~float32 | ~float64` matches types *by underlying
type* (so `type MyFloat float64` qualifies), but `String() string`
matches by *method set* (so the type must literally have a `String()`
method on it). Go does not let a method constraint match an underlying
type's methods.

### 1.5 Type inference

When you call `Sum(myInts)` and `myInts` is `[]int`, Go infers `T = int`
from the argument's type. The rules (in [the design doc][type-params-design],
§Type Inference) are:

1. **Function argument type inference.** For each typed argument, the
   type-parameter list is unified against the argument's type. If a
   single type-parameter appears in multiple argument types, they must
   unify.
2. **Constraint type inference.** If the constraint is a type set, Go can
   use it to fill in a type-parameter that does not appear in any
   argument.
3. **(1.21+)** Inference for untyped constants — `Sum([]int{1, 2, 3})`
   infers `T = int` from the constant `1`.

Inference is purely syntactic; there is no H-M-style algorithm. When it
fails, you must instantiate explicitly: `Sum[int](myInts)`. The error
message ("cannot infer T") is one of the more cryptic parts of the
language.

### 1.6 The generic algorithm pattern

The idiomatic generic API is the `Iterator`-shaped type parameter — a
function that takes a constraint-satisfying type and applies the same
algorithm to any compatible type:

```go
// Filter returns the elements of in for which pred returns true.
func Filter[T any](in []T, pred func(T) bool) []T {
    out := make([]T, 0, len(in))
    for _, v := range in {
        if pred(v) { out = append(out, v) }
    }
    return out
}

// Sort sorts in-place using a less function.
func Sort[T any](in []T, less func(a, b T) bool) {
    // standard library sort, parameterized
    sort.Slice(in, func(i, j int) bool { return less(in[i], in[j]) })
}
```

`slices` (Go 1.21+ stdlib) and `maps` provide the canonical set:
` slices.Sort`, `slices.Contains`, `slices.Index`, `maps.Copy`,
`maps.Clone`, etc.

### 1.7 Implementation — GC shape stenciling

The Go compiler does not monomorphize every instantiation. It uses
**GC shape stenciling**: a single machine-code stencil is generated per
*GC shape* (the layout relevant to the garbage collector — pointer map),
and type-specific dictionaries are passed at runtime. So `List[int]`
and `List[float64]` (both 8-byte non-pointer scalars) share one stencil
with different dictionaries; `List[*int]` and `List[*float64]` (both
single pointers) share another. This bounds the code bloat to a small
multiple of the non-generic baseline, unlike Rust which fully
monomorphizes each instantiation.

### 1.8 Comparison with Rust and Java generics

| Aspect | Go 1.18+ | Rust 1.0+ | Java 5+ |
|--------|----------|-----------|---------|
| Syntax | `[T any]` | `<T>` with `where T: Bound` | `<T extends Bound>` |
| Constraints | Interface type-sets + `~T` | Traits (associated types, lifetimes) | Class/interface bounds |
| Specialization | None (runtime dictionaries) | Implicit via trait dispatch | None (erasure) |
| Code generation | GC-shape stenciled | Full monomorphization + opt. dynamic dispatch | Type erasure to `Object` |
| Variance | Invariant | Invariant (with explicit `+`/`-` for types) | Use-site (`? extends T`, `? super T`) |
| Generic methods | Yes (`func F[T any]`) | Yes (`fn f<T>()`) | Yes (`<T> T f(T t)`) |
| Higher-kinded types | No | No (workarounds via GATs) | No |
| Performance cost | One dictionary call per generic call | Zero (static monomorphization) | Boxed `Object`, autobox primitives |

Go chose deliberately the *simplest* version that works: no
specialization, no higher-kinded types, no associated types, no variance.
Rust gets peak performance and high expressiveness at the cost of
compile-time complexity (`rustc` monomorphization is a major build cost).
Java gets the most flexibility but pays the boxing tax and has the worst
performance for primitives.

## 2. Error Handling — Values, Not Exceptions

### 2.1 The `error` interface

```go
type error interface {
    Error() string
}
```

That's the whole interface. Any type implementing `Error() string` is an
`error`. The compiler does not privilege error values — `error` is just
an interface, returned as a second value from any function that may fail.
This is the *philosophical* difference from exceptions: errors are
*ordinary control flow*, not a separate unwinding mechanism.

### 2.2 Wrapping — `fmt.Errorf` with `%w`

Go 1.13 (Sep 2019) introduced error wrapping. The `fmt.Errorf` verb `%w`
creates a `*fmt.wrapError` (or `*fmt.wrapErrors` for multiple) that
remembers the wrapped error and supports `Unwrap()`:

```go
var ErrNotFound = errors.New("not found")

func GetUser(id int) (*User, error) {
    u, err := db.QueryUser(id)
    if err != nil {
        return nil, fmt.Errorf("get user %d: %w", id, err)  // wraps err
    }
    return u, nil
}

// Caller side:
_, err := GetUser(42)
if errors.Is(err, ErrNotFound) {
    // matches because errors.Is walks the Unwrap chain
}
```

The `%v` verb produces a `*errors.errorString` with `err`'s text
*concatenated* but with no `Unwrap()` link — the wrapped error is
*unreachable* by `errors.Is/As`. This is a frequent source of bugs:
**`%v` strips the error identity, `%w` preserves it**.

### 2.3 `errors.Is` — sentinel comparison through the chain

```go
func Is(err, target error) bool
```

`errors.Is` walks the `Unwrap()` chain of `err`, comparing each link to
`target` with `==`. If any link supports `Is(error) bool` (the optional
method on custom error types), that method is consulted instead. The
walk continues until either a match is found or the chain ends.

The optional `Is(error) bool` method is how you make an error
*match* a sentinel without being the sentinel — useful for errors that
are *like* `io.EOF` but structurally distinct:

```go
type TimeoutErr struct{ Dur time.Duration }
func (t *TimeoutErr) Error() string { return fmt.Sprintf("timeout after %v", t.Dur) }
func (t *TimeoutErr) Is(target error) bool {
    _, ok := target.(interface{ Timeout() bool })
    return ok && target.(interface{ Timeout() bool }).Timeout()
}
```

### 2.4 `errors.As` — type-based extraction

```go
var perr *fs.PathError
if errors.As(err, &perr) {
    log.Println(perr.Path)  // perr is now the *fs.PathError from the chain
}
```

`errors.As` walks the Unwrap chain performing a type assertion against
the type pointed to by `target`. The first match wins; the value is
written through the pointer. Unlike `errors.Is`, `errors.As` does
*not* support a custom method — the chain is purely structural.

### 2.5 `errors.Join` — multiple errors (Go 1.20)

```go
func validate(form Form) error {
    var errs []error
    if form.Name == "" { errs = append(errs, errors.New("name required")) }
    if form.Email == "" { errs = append(errs, errors.New("email required")) }
    if len(errs) == 0 { return nil }
    return errors.Join(errs...)  // wraps all into one
}
```

`errors.Join` returns a `*joinError` whose `Unwrap()` returns `[]error`
(the multi-unwrap protocol — Go 1.20+). `errors.Is` and `errors.As` walk
all branches of the join. `Error()` joins the sub-errors with newlines.

### 2.6 Sentinel errors

A sentinel is a package-level `var ErrX = errors.New("...")` against
which callers compare. The stdlib uses them sparingly — `io.EOF`,
`io.ErrUnexpectedEOF`, `sql.ErrNoRows`, `os.ErrNotExist`,
`context.Canceled`, `context.DeadlineExceeded`. The Go style guide
recommends *wrapping* sentinels (`fmt.Errorf("...: %w", io.EOF)`) so the
caller can still `errors.Is(err, io.EOF)` but gets the additional
context. Avoid exporting new sentinels from internal packages —
`errors.Is` with a custom error type is preferred.

### 2.7 `panic` / `recover`

```go
func safeDiv(a, b int) (r int, err error) {
    defer func() {
        if rec := recover(); rec != nil {
            err = fmt.Errorf("recovered: %v", rec)
        }
    }()
    return a / b, nil
}
```

`panic` raises a runtime error (out-of-bounds slice, nil dereference,
explicit `panic(x)`) that walks up the call stack, executing deferred
functions at each frame. `recover()` *inside a deferred function* stops
the unwinding and returns the panic value. Outside a deferred call it is
a no-op.

Use cases:

- **Library boundaries.** A HTTP handler can wrap the whole handler in
  `defer recover()` and convert panics to 500 responses; an RPC server
  can convert panics to error responses.
- **Goroutine death prevention.** A goroutine that panics kills the whole
  process; a top-level `defer recover()` in `go func() { defer
  recover(); work() }()` is the idiomatic safeguard.

Non-use cases (where new Go programmers reach for panic/recover and
should not):

- **Control flow.** Exceptions in Java/Python are flow control; in Go
  they should be panic-only. Do not use panic to signal "user not found".
- **Validation.** Use `error` values; panic is more expensive (stack
  unwind) and harder to reason about.

### 2.8 Comparison with Rust's `Result<T, E>`

| Aspect | Go | Rust |
|--------|-----|------|
| Error type | `error` interface (any type implementing `Error() string`) | `Result<T, E>` enum, `E` is generic |
| Composition | `fmt.Errorf("%w")` + `errors.Join` | `map_err`, `?` operator, `From` impls |
| Forcing handling | None — `err` can be silently dropped (`_, _ := f()`) | Compile-time — `Result` must be `match`ed or `let ?` to propagate |
| Sentinel | `errors.New("...")` + `errors.Is` | `Err(Var)` enum variant + `matches!(res, Err(Var))` |
| Stack trace | None built-in (use `runtime/debug.Stack()`) | `Backtrace` capture per error |
| Performance | Interface dispatch + heap alloc for wrapped errors | Zero-cost for `Ok`; `Err` boxed only if non-`Copy` |
| Panic | Real panic, used as a bug signal | `panic!`/`unwrap()` — but idiomatic Rust uses `Result`, so panics are rare |

The Go-vs-Rust contrast crystallizes the design tradeoff:

- **Go** optimizes for *not breaking the build* when error types change.
  Adding a new error variant to a Go library is backward-compatible —
  callers see it via `errors.Is`/`As` but don't have to add a new match
  arm. The cost is silent error swallowing (`_, _ = f()`) and no
  compiler-checked exhaustiveness.
- **Rust** optimizes for *never silently dropping an error*. Adding a
  new variant to a `Result`-returning function forces every caller to
  handle it. The cost is the `?` cascade and breakage cascades through
  version bumps.

In practice, large Go codebases accumulate silent error drops;
large Rust codebases accumulate `match` boilerplate. Both ecosystems
developed linters (`errcheck` for Go; `clippy` for Rust) to enforce
the discipline the language leaves to the programmer.

## References

- [Go generics tutorial — go.dev][generics-tutorial]
- [Go blog — An Introduction to Generics](https://go.dev/blog/intro-generics)
- [Go blog — When To Use Generics](https://go.dev/blog/when-generics)
- [Design draft — Type Parameters (Russ Cox et al.)][type-params-design]
- [Go error handling — go.dev blog][error-handling-blog]
- [Go 1.20 errors — `errors.Join` and the multi-Unwrap protocol](https://go.dev/blog/go1.20)
- [Go by Example — Errors](https://gobyexample.com/errors)
- [Dave Cheney — `pkg/errors` (precursor to `%w`)](https://github.com/pkg/errors)
- [Russ Cox — Error Values design draft (Go 2 draft)](https://go.googlesource.com/proposal/+/refs/heads/master/design/go2draft-error-values-overview.md)

[generics-tutorial]: https://go.dev/doc/tutorial/generics
[type-params-design]: https://go.googlesource.com/proposal/+/refs/heads/master/design/43651-type-parameters.md
[error-handling-blog]: https://go.dev/blog/error-handling-and-go
