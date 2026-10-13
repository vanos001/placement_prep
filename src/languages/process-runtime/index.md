# Process & Runtime Semantics by Language

Part hub — Section G: Comprehensive Programming-Language Semantics, Standard
Libraries, Process APIs, and Subprocess Behavior.

Each of the eight languages (C, C++, Python, Go, Java, Rust, Node.js, OCaml)
is documented as a **separate documentation project** with six mandatory
coverage areas and its own verifiable coverage ledger:

1. **Syntax and semantics** — declarations, evaluation rules, scope and
   lifetime, cleanup, error propagation, undefined/unspecified behavior,
   version and platform deltas, misconceptions, worked examples.
2. **Standard-library and runtime API inventory** — source-derived, with
   canonical signatures, side effects, ownership, thread-safety, and version
   availability; never inventory from memory.
3. **Process creation and termination** — entry-point return versus explicit
   termination, cleanup handlers, destructors/deferred/hooks/finalizers,
   uncaught exceptions, panics, aborts, exit-status ranges and truncation.
4. **Signals and OS interaction** — registration, masking, delivery,
   async-signal-safety, runtime restrictions, threads/GC/FFI interactions,
   POSIX versus Linux-specific behavior.
5. **Subprocess and child-process management** — creation, waiting, pipes,
   streams, timeouts, cancellation, zombies, injection-safe argument passing,
   status retrieval.
6. **Concurrency and resource semantics** — threading, synchronization,
   fd/handle ownership, buffering, deadlocks, races, leaks, and the effect of
   GC / ownership systems / runtime scheduling.

Scope discipline: this is **not** an indiscriminate ecosystem inventory. The
in-scope surface is language semantics, the standard library/runtime insofar
as it bears on process lifecycle, signals, subprocesses, and resource
management. Adjacent deep dives live elsewhere in this book and are
cross-linked, not duplicated:

- Exit-status decoding, signal tables, and the `128+N` convention:
  [Linux → Process Exit Codes, Signals, and Lifecycle](../../linux/process-exit-signal/index.md)
  — per-language exit/signal chapters under
  `linux/process-exit-signal/languages/`.
- Interview-oriented topic pages (pointers, GIL, GC, ownership, JVM
  internals): the sibling `Programming Languages` sections such as
  [C POSIX](../c/posix.md),
  [Python GIL](../python/gil.md),
  [Rust ownership](../rust/ownership.md).

## Chapters and ledgers

| Language | Chapter | Coverage ledger | Declared target (verified against official docs during research) |
|---|---|---|---|
| C | [c.md](./c.md) | [ledger-c.md](./ledger-c.md) | ISO C17/C23, glibc, POSIX.1-2024, Linux kernel UAPI |
| C++ | [cpp.md](./cpp.md) | [ledger-cpp.md](./ledger-cpp.md) | ISO C++23, libstdc++/glibc, POSIX |
| Python | [python.md](./python.md) | [ledger-python.md](./ledger-python.md) | CPython current stable 3.x |
| Go | [go.md](./go.md) | [ledger-go.md](./ledger-go.md) | Current stable Go 1.x toolchain |
| Java | [java.md](./java.md) | [ledger-java.md](./ledger-java.md) | Current JDK LTS |
| Rust | [rust.md](./rust.md) | [ledger-rust.md](./ledger-rust.md) | Current stable `std` |
| Node.js | [nodejs.md](./nodejs.md) | [ledger-nodejs.md](./ledger-nodejs.md) | Current LTS line |
| OCaml | [ocaml.md](./ocaml.md) | [ledger-ocaml.md](./ledger-ocaml.md) | Current stable OCaml 5.x |
| All | [comparison.md](./comparison.md) | — | Cross-language semantic comparison (G5) |

Exact verified versions, and what each chapter actually checked, are stated
in the chapter's scope section and ledger header. No chapter claims
universality beyond its declared scope.

## Coverage ledger schema (G4)

Every ledger uses the schema below. Statuses: `not-started`, `researched`,
`documented`, `source-limited`. An entry is `documented` only when the
explanation exists, required examples are present, and the cited references
support the claims — a name in a table is never sufficient.

| ID | Language/API or behavior | Canonical signature | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|---|

Stable ID prefixes: `PL-C-`, `PL-CPP-`, `PL-PY-`, `PL-GO-`, `PL-JV-`,
`PL-RS-`, `PL-ND-`, `PL-OC-` (deliberately disjoint from the
`LG-*` ledger IDs of the exit-signal part).

Per-language rollups (inventoried / documented / remaining / source-limited)
are reported at the top of each ledger file and consolidated in the
integration notes of this hub after all chapters land.

## Reference policy (G3)

- Primary sources only for behavior claims: language specifications, official
  standard-library and runtime references, official platform documentation.
- Direct links next to significant claims; dedicated `References` section per
  chapter; per-ledger-entry signature source.
- Never invent URLs, signatures, outputs, guarantees, or version
  availability. Implementation-dependent or unverifiable behavior is labeled
  as such, explicitly.
