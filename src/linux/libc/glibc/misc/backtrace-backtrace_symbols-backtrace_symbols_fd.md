# `backtrace` / `backtrace_symbols` / `backtrace_symbols_fd` (3) - glibc

> Split from the ledger chapter *debugging* into the per-function layout;
> see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `execinfo.h` (`backtrace` line 27, `backtrace_symbols` lines 32-33, `backtrace_symbols_fd` lines 38-39; no feature-test gate in the glibc header) |
| Standards | GNU extensions per `backtrace(3)` CONFORMING TO; BSD-lineage `execinfo.h` interface, in glibc since 2.1 (`backtrace(3)` VERSIONS) |
| Exported | `backtrace@@GLIBC_2.2.5`, `backtrace_symbols@@GLIBC_2.2.5`, `backtrace_symbols_fd@@GLIBC_2.2.5` (all `W` weak in nm), internal `__backtrace@@GLIBC_2.2.5`, `__backtrace_symbols@@GLIBC_2.2.5`, `__backtrace_symbols_fd@@GLIBC_2.2.5` (`T`) (host glibc 2.41) |
| Thread-safety | MT-Safe all (`backtrace(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-backtrace, GLIBC-backtrace_symbols, GLIBC-backtrace_symbols_fd |

## Declaration and gates

```c
#include <execinfo.h>

int backtrace (void **buffer, int size);
char **backtrace_symbols (void *const *buffer, int size);
void backtrace_symbols_fd (void *const *buffer, int size, int fd);
```

`execinfo.h` declares all three unconditionally -- there is no
`_GNU_SOURCE` guard in the header itself (lines 18-43), only the
`__nonnull((1))` checks. The `execinfo.h` name and interface come from
the BSD self-debugging API; man-pages classifies the Linux versions as
GNU extensions (`backtrace(3)` CONFORMING TO).

## Semantics

`backtrace` walks the current call stack and stores up to `size` return
addresses in `buffer`, returning the number stored; on truncation the
addresses of the most recent calls are kept and the oldest frames are
lost (`backtrace(3)`). `backtrace_symbols` translates those addresses
into strings `module(function+offset) [addr]` in one `malloc`ed block
that the caller frees; the individual strings must not be freed.
`backtrace_symbols_fd` writes the same lines, one per line, to `fd`
without calling `malloc`, which is what makes it usable from a signal
handler -- in principle (`backtrace(3)` DESCRIPTION/NOTES).

## Gotchas and portability

- Optimization breaks the walk: omitted frame pointers, inlined
  functions (no frames) and tail-call optimization (frame reuse) all
  corrupt or shrink the result (`backtrace(3)` NOTES).
- Symbol names need `-rdynamic` at link time; static functions are
  never exposed (`backtrace(3)` NOTES).
- Both `backtrace` and `backtrace_symbols_fd` implicitly trigger a
  `libgcc_s` load on first use, which calls `malloc` -- preload or prime
  it before installing handlers that must not allocate
  (`backtrace(3)` NOTES).
- The `libgcc`/unwinder coupling is why the address-to-object mapping
  has a faster replacement: see `_dl_find_object` in this directory.
- musl 1.2.5 ships no `execinfo.h` (absence verified in
  `musl/include/`).

## Errors

`backtrace_symbols` returns `NULL` on failure (e.g. `malloc`
exhaustion); the other two return no error (`backtrace(3)` RETURN
VALUE).

## References

- glibc manual: `debug.texi` (backtrace context)
- man3: `backtrace(3)` (covers both symbolizers)
- header: `/usr/include/execinfo.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
- musl 1.2.5: no `execinfo.h` in `include/` (absence verified)
