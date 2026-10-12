# musl libc — Catalog

musl is cataloged separately from glibc by design: same POSIX surface, very
different implementation choices and extension set. The authoritative
inventory is [ledger-musl.md](../ledger-musl.md) — 1482 functions across 110
public-header families of musl 1.2.5, extracted from the musl source tree
(with the `_Noreturn`-aware fix: the BSD `err`/`warn` family and `_Exit` were
initially missed by naive prototype parsing), plus computed deltas against the
glibc inventory (musl-only: 15; glibc-only: ~2367).

## In this section

- Family pages under `musl/<family>.md` document the families where musl's
  behavior genuinely differs from glibc, each entry with musl source-file
  provenance (`src/...` paths), WHATSNEW version notes, and explicit
  unverified markers where no source was reachable.
- The glibc-side equivalents are cross-linked from the
  [glibc function pages](../glibc/overview.md) rather than duplicated.

## Key verified deltas (evidence in family pages)

- Flat ABI: no symbol versioning, `dlvsym` meaningless; dynlink lookup ignores
  versions (musl `ldso/dynlink.c`).
- `ucontext`: all four functions declared in `ucontext.h`, no implementation
  anywhere in `src/` — linking fails (sharper than the usual "no makecontext").
- No `execinfo.h`/`backtrace`; no nsswitch, `RES_OPTIONS`, or `LOCALDOMAIN`
  handling; iconv uses a fixed built-in charset table; ctype `_l` variants
  ignore locale.
- `getdents64` is a macro for `getdents`; LFS64 macros gated by
  `_LARGEFILE64_SOURCE` (1.2.4+).
- `crypt` in libc proper (glibc 2.41: `libcrypt.so.1`); mallocng allocator;
  setxid broadcast via `__synccall`.
- musl ignores `POSIXLY_CORRECT` in getopt; supports GNU long options,
  permutation, and optional args.
