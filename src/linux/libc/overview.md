# libc API Encyclopedia

This section catalogs the C library surface on Linux, with **glibc and musl
kept separate** throughout: separate ledgers, separate pages, separate
provenance. The two libraries agree on ISO C and POSIX, but differ in symbol
versioning, feature gates, internal behavior, and extension surface — and the
differences are exactly what portability-sensitive code trips over.

## Inventories

- **glibc** — [ledger-glibc.md](./ledger-glibc.md), generated from the glibc
  manual (texi, versioned snapshot) and cross-checked against installed
  headers and `nm -D --with-symbol-versions` on `libc.so.6` (host glibc 2.41,
  x86_64). Three layers are kept deliberately separate: 1881 documented-API
  rows (manual-documented functions), 3470 exported symbols (the real ABI),
  and 1953 triage rows (exported but undocumented — including internal and
  private symbols, which are flagged as such and never presented as API).
- **musl** — [ledger-musl.md](./ledger-musl.md), generated from the musl 1.2.5
  public headers (1482 functions across 110 header families) with computed
  deltas against the glibc inventory (musl-only: 15; glibc-only: 2367+).

## Pages

Function pages live under `glibc/<family>/<function>.md` — one page per
function, one directory per manual chapter family (stdio, process, threads,
signals, job control, strings, stdlib, math, network, users and groups,
locale, time, dynamic linking, memory allocation). Each page carries: the
canonical declaration with its feature-test gates (from headers), header,
standards provenance, argument semantics, return conventions, error behavior
(`errno` discipline), thread-safety and async-signal-safety notes, symbol
version, portability notes vs musl where relevant, an example, and a primary
reference (manual node, man3 page, or header).

The [musl catalog](./musl/overview.md) documents musl separately: positioning,
implementation notes per family (from musl sources, with file paths), the
verified delta list (each with evidence or an explicit unverified marker), and
full template entries for the functions where musl's behavior differs most
(`pthread_create`, `malloc`/mallocng, `printf`, `getaddrinfo`, `setlocale`,
`fork`, `dlopen`, `__libc_start_main`).

## Standing rules

- Documented vs exported-but-undocumented symbols never blur: internal
  identifiers (`__*`, `_nl_*`, NSS service modules) are triaged, not advertised.
- Symbol versions come from `nm` output on a named host glibc, and "since
  glibc 2.x" claims in prose only appear when sourced (manual, NEWS, or
  release notes) — the version tag on one host is a lower bound, stated as such.
- `errno`, reentrancy, cancellation, and async-signal-safety claims cite the
  manual or man page they come from.
