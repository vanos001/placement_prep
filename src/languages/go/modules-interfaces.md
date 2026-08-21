# Go Modules and Interfaces

## Overview

Go's package management and its type system live at different layers of the language, but they share a common philosophy: *explicit is better than implicit, until implicit becomes a feature*. Modules make dependency versions explicit and reproducible. Interfaces are *implicitly* satisfied — a type implements an interface merely by having the right methods; there is no `implements` keyword.

This page covers the module system (go.mod, go.sum, SemVer, MVS, `go mod tidy`) and the interface system (implicit satisfaction, type assertions, type switches, composition, the empty interface, and generic constraints).

## go.mod

A `go.mod` file declares the module path, the Go version, and its dependencies:

```go
module github.com/example/myapp

go 1.22

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/redis/go-redis/v9 v9.5.1
    golang.org/x/sync v0.6.0
)

replace github.com/example/foo => ../foo
```

Sections:

- `module` — the import path prefix for the module's own packages.
- `go` — the *language* version this module targets. It pins the Go toolchain behavior (e.g., `for` loop scoping changes in 1.22) and the minimum Go version required to build.
- `require` — direct dependencies with selected versions. Indirect dependencies that aren't listed in any direct require directive are marked `// indirect`.
- `replace` — point a module at a different path or version (e.g., a local fork).
- `exclude` — forbid a specific version (rare; needed when a published version is broken).
- `retract` — published in-module, marks previously-released versions as retracted so `go get` skips them by default.

## go.sum

`go.sum` is the cryptographic integrity file. For every module version used (directly or transitively), it stores the SHA-256 hash of the module's `.zip` and `.mod` files:

```
golang.org/x/sync v0.6.0 h1:0tiFsPYkDKBQk13nDjz9s0wG6r...
golang.org/x/sync v0.6.0/go.mod h1:3gkFQk5X9UY6tCJ...
```

The first hash (after `h1:`) verifies the module's contents; the second verifies the `go.mod` file. Both are checked on download. The Go tool refuses to build if any hash mismatches.

## Versioning — SemVer

Go modules use Semantic Versioning (`vMAJOR.MINOR.PATCH`):

- `MAJOR` — breaking changes. Go treats `v2+` as a different module: the import path gains a `/v2` suffix (e.g., `github.com/foo/bar/v2`). This is the "major version suffix" rule.
- `MINOR` — backward-compatible new functionality.
- `PATCH` — backward-compatible bug fixes.
- Pre-release suffixes (`v1.2.3-beta.1`) sort *before* the release version.

A module that has not opted into SemVer can still be referenced via a *pseudo-version* — `v0.0.0-20231102172634-d6afae23e6b8` — which encodes a UTC timestamp and a 12-char commit hash prefix. Pseudo-versions are produced automatically by `go get` when only a commit SHA is available.

## MVS — Minimal Version Selection

Go's algorithm for selecting the *single* version of each dependency is called **Minimal Version Selection** (MVS). It is *not* SAT solving and does *not* try to find a globally satisfying assignment. Instead:

1. Start with the build list containing the main module's `go.mod`'s required versions.
2. For each required module, look at *its* `go.mod` to find what *it* requires.
3. For each requirement, take the *maximum* of the versions mentioned by every module that requires it.
4. Repeat until the set is closed.
5. The selected version of a module is the *minimum* version that satisfies all the *maxes* computed above.

```
       main module requires  A@1.2  B@1.5
       A@1.2          requires       B@1.3  C@1.0
       B@1.5          requires              C@1.1

MVS:    A -> 1.2  (only one source)
        B -> max(1.5, 1.3) = 1.5
        C -> max(1.0, 1.1) = 1.1
```

The crucial property: MVS picks the **minimum** version that every transitive requirement agrees on. It does not bump to the *latest*; if a transitive dep asks for `B@1.3` and the main module asks for `B@1.5`, MVS picks `1.5` (because both requirements are satisfied by `>=1.5`). The result is reproducible *without* a lockfile.

## `go mod tidy`

`go mod tidy` adds the missing requirements needed to build the current packages *and* removes requirements that aren't needed by *any* package in the module (including build-tag-gated ones). It walks the import graph, computes the *real* set of dependencies, and rewrites `go.mod`/`go.sum` to reflect exactly that. You should always run `tidy` before committing a `go.mod` change.

`go mod vendor` snapshots the selected versions into `vendor/`, after which the build can run offline and reproducibly. The `vendor/` directory is consulted only when `-mod=vendor` is active (default when `vendor/` exists and `go.mod` `go` version is `1.14+`).

## Workspaces (`go.work`)

When developing multiple modules together, a `go.work` file lists local directory replacements and a unified build list:

```
go 1.22
use (
    ./services/api
    ./services/worker
    ./pkg/auth
)
```

The workspace takes precedence over each module's `go.mod` for the purposes of resolving local modules. Workspaces don't affect production builds (they aren't published).

## Interfaces — implicit satisfaction

A Go interface is a set of method signatures:

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}
```

A type satisfies an interface if it has *all* its methods with *matching* signatures. There is no `implements` clause. This is sometimes called *duck typing with static checking* — the compiler verifies satisfaction, but no declaration is required.

```go
type File struct{ name string }

func (f *File) Read(p []byte) (int, error) {
    // ... read into p
    return len(p), nil
}

var _ Reader = (*File)(nil)  // compile-time assertion
```

The last line is the canonical idiom for compile-time interface satisfaction: `var _ I = (*T)(nil)` (or `var _ I = T{}` for value receivers). If `T` fails to implement `I`, the build breaks.

Implicit satisfaction decouples interface definition from implementation, which is why `io.Reader` works for both `*os.File` and `*bytes.Buffer`. Interfaces belong to *consumers*, not producers — a maxim known as "accept interfaces, return structs".

## Type assertions

A value of interface type has a dynamic type and a dynamic value. A type assertion `x.(T)` extracts the dynamic value as type `T`, panicking if the assertion fails (unless you use the comma-ok form):

```go
func describe(r Reader) {
    if f, ok := r.(*File); ok {
        fmt.Println("a file:", f.name)
    } else {
        fmt.Println("something else")
    }
}
```

The two-value form `(T, bool)` returns `(zero, false)` on failure rather than panicking. The single-value form panics with a runtime `TypeAssertionError`.

## Type switches

A type switch generalizes multiple assertions:

```go
func explain(x any) {
    switch v := x.(type) {
    case int:
        fmt.Println("int:", v)
    case *File:
        fmt.Println("file:", v.name)
    case []byte:
        fmt.Println("bytes, len =", len(v))
    default:
        fmt.Printf("unknown %T\n", v)
    }
}
```

Inside the case body, `v` has the asserted static type. Multiple types can share a case (then `v` has type `any`). The `x.(type)` form is only legal as the switch expression in a `switch` statement, not in expressions.

## Interface composition

Interfaces can embed other interfaces; the resulting interface has the union of methods:

```go
type ReadWriter interface {
    Reader
    Writer
}
```

This is purely a method-set operation — there's no inheritance, no method resolution, no `super`. It's sugar for declaring both sets of methods.

## The empty interface

`any` is an alias for `interface{}` (since Go 1.18). It imposes no constraints:

```go
func Println(args ...any) { /* ... */ }
```

`any` is widely used but should be avoided when a more specific interface is available. Internally, a non-empty interface value is `(itype, idata)` — a pointer to the interface's itab (containing the type descriptor and method pointers) and a pointer to the underlying data. An empty interface value is `(type, data)` — pointers to the dynamic type and data directly. This is why `any` does not need an itab but cannot dispatch methods.

## Generics and type constraints

Go generics (Go 1.18+) extend interfaces to serve as **constraints**. A constraint is an interface that may also contain *type sets*:

```go
type Number interface {
    int | int64 | float32 | float64
}

func Sum[T Number](xs []T) T {
    var s T
    for _, x := range xs {
        s += x
    }
    return s
}
```

A `~T` in a type set means "T or any type whose underlying type is T":

```go
type Celsius float64
type Fahrenheit float64

type Temperature interface {
    ~float64
}
```

The predeclared `comparable` constraint is satisfied by types that support `==` and `!=` (structs, arrays, primitives, pointers; not slices, maps, funcs, or structs containing them).

Constraints compose: a constraint can include both type sets and method requirements:

```go
type Stringer interface {
    String() string
}

type Comparable[T any] interface {
    Compare(T) int
}
```

The `cmp.Ordered` constraint in the standard library (Go 1.21+) covers all primitive ordered types. `golang.org/x/exp/constraints` and `golang.org/x/exp/slices` predate it and are still widely used.

## When a type satisfies an interface

Satisfaction is checked *statically*, at the assignment or call site. A type can satisfy an interface even if it was defined before the interface existed — important for retrofitting interfaces onto existing types. The method set of `*T` includes both value and pointer receivers; the method set of `T` includes only value receivers. This is the source of the common confusion:

```go
type S struct{}

func (s S) M() {}        // value receiver
func (s *S) N() {}       // pointer receiver

var _ someIface = S{}    // only sees M(); not N()
var _ someIface = &S{}   // sees both
```

If a method uses a pointer receiver, only `*S` satisfies any interface requiring that method.

## Common pitfalls

1. **Forgetting the major-version suffix** — `github.com/foo/v2` is required to import v2+ code; without it you get v0/v1.
2. **Mixing `replace` in production** — local `replace` directives should not be committed.
3. **Treating `interface{}` as a default** — it disables static checking and adds dispatch cost.
4. **Asserting in single-value form** when failure is expected — use `, ok` to avoid a panic.
5. **Pointer vs value receiver confusion** — a type with only pointer receivers cannot satisfy an interface via the value form.
6. **Believing MVS finds the latest version** — it finds the *minimum* satisfying version. `go get -u` is required to upgrade.

## Interview questions

1. **What is MVS?**
   Minimal Version Selection — the algorithm Go uses to pick one version per dependency. It selects the minimum version satisfying the maximum of each transitive requirement.

2. **What's the difference between `go.mod` and `go.sum`?**
   `go.mod` declares the module's direct dependencies and versions; `go.sum` records the hashes of all (direct + indirect) modules for verification.

3. **What is a pseudo-version?**
   A version string like `v0.0.0-20231102172634-d6afae23e6b8`, used when only a commit SHA is available.

4. **How do Go interfaces differ from Java interfaces?**
   Satisfaction is implicit — no `implements` keyword. Interfaces belong to the consumer, not the implementer.

5. **What is the empty interface, and how is it represented?**
   `any`/`interface{}` is an interface with no methods. It's represented as `(type, data)` directly, with no itab.

## References

- [Go Modules Reference](https://pkg.go.dev/cmd/go#hdr-modules)
- [Go Module Mirror, Index, and Checksum Database — blog post](https://go.dev/blog/module-mirror-launch)
- [Go & Versioning — blog series by Russ Cox](https://research.swtch.com/vgo)
- [Minimal Version Selection — Russ Cox](https://research.swtch.com/vgo-mvs)
- [Go Specification — Interface types](https://go.dev/ref/spec#Interface_types)
- [Go Specification — Type assertions](https://go.dev/ref/spec#Type_assertions)
- [Go Specification — Type switches](https://go.dev/ref/spec#Type_switches)
- [Effective Go — Interfaces and types](https://go.dev/doc/effective_go#interfaces_and_types)
- [Go Blog — When and why to use generics](https://go.dev/blog/why-generics)
- [Tutorial: Getting started with modules](https://go.dev/doc/tutorial/module)

## See also

- [Memory Model](./memory-model.md) — happens-before guarantees affect interface dispatch under concurrency
- [Scheduler](./scheduler.md) — the runtime goroutine model
- [Channels](./channels.md) — `<-chan T` and `chan<- T` direction constraints as interfaces
