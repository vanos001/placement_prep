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

| Language | Chapter | Coverage ledger | Verified target (official sources, retrieved 2026-10) |
|---|---|---|---|
| C | [c.md](./c.md) | [ledger-c.md](./ledger-c.md) | ISO C17 (N2310) + C23 (N3220), glibc (via sourceware.org), POSIX.1-2024, man-pages 6.19 |
| C++ | [cpp.md](./cpp.md) | [ledger-cpp.md](./ledger-cpp.md) | ISO C++23 DIS N4950 + working draft (eel.is, 2026-08-23), GCC 14.2.0 libstdc++, POSIX.1-2024 |
| Python | [python.md](./python.md) | [ledger-python.md](./ledger-python.md) | CPython 3.15.0 (docs.python.org + CPython source + PEPs 442/446/475) |
| Go | [go.md](./go.md) | [ledger-go.md](./ledger-go.md) | Go 1.27.2 (go.dev/dl JSON feed + pkg.go.dev) |
| Java | [java.md](./java.md) | [ledger-java.md](./ledger-java.md) | JDK 25 (Javadoc + JLS SE 25 + JEPs + jdk-25+36 source), HotSpot on Linux |
| Rust | [rust.md](./rust.md) | [ledger-rust.md](./ledger-rust.md) | `std` 1.99.0 (build `b940084d7`, 2026-09-28; doc.rust-lang.org + std source) |
| Node.js | [nodejs.md](./nodejs.md) | [ledger-nodejs.md](./ledger-nodejs.md) | Node.js v24.21.0 'Krypton' LTS (nodejs.org/dist + api docs, libuv 1.52.1) |
| OCaml | [ocaml.md](./ocaml.md) | [ledger-ocaml.md](./ledger-ocaml.md) | OCaml 5.5.1 (ocaml.org + official source tree, 24 verified .mli/.c files) |
| All | [comparison.md](./comparison.md) | — | Cross-language semantic comparison (G5), grounded in the eight chapters |

Exact versions were re-verified against the official release feeds at research
time; where a chapter's target moved relative to the exit-signal part's older
range (e.g. Rust 1.61–1.8x era there), the chapters here are the current
source of record. What each chapter actually checked, and any source that
could not be reached, are stated in the chapter's scope section and ledger
header. No chapter claims universality beyond its declared scope.

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
are reported at the top of each ledger file and consolidated below.

## Coverage rollup (integration result)

| Ledger | Inventoried | Documented | Remaining | Source-limited |
|---|---|---|---|---|
| [C](./ledger-c.md) | 82 | 81 | 0 | 1 |
| [C++](./ledger-cpp.md) | 75 | 74 | 0 | 1 |
| [Python](./ledger-python.md) | 80 | 80 | 0 | 0 |
| [Go](./ledger-go.md) | 80 | 80 | 0 | 0 |
| [Java](./ledger-java.md) | 80 | 78 | 0 | 2 |
| [Rust](./ledger-rust.md) | 76 | 73 | 0 | 3 |
| [Node.js](./ledger-nodejs.md) | 80 | 80 | 0 | 0 |
| [OCaml](./ledger-ocaml.md) | 80 | 77 | 0 | 3 |
| **Part total** | **633** | **623** | **0** | **10** |

Every `source-limited` row names the unreachable primary source and the
substituting evidence in its ledger (examples: the Linux UAPI wait-status
header claims anchored to man-pages 6.19; `std::jthread` destructor wording
anchored to the working-draft class contract; libjsig kept brief; OCaml
tail-call and SIGSEGV-conversion wording absent from the fetched manual
pages). No entry is marked `documented` on the strength of a name in a
table; the statuses `not-started` and `researched` do not occur at
publication time.

## Reference policy (G3)

- Primary sources only for behavior claims: language specifications, official
  standard-library and runtime references, official platform documentation.
- Direct links next to significant claims; dedicated `References` section per
  chapter; per-ledger-entry signature source.
- Never invent URLs, signatures, outputs, guarantees, or version
  availability. Implementation-dependent or unverifiable behavior is labeled
  as such, explicitly.
