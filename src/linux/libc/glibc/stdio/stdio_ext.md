# `stdio_ext` FILE internals: `__fbufsize` / `__fpending` / `__fpurge` / `__fsetlocking` / `_flushlbf` (3) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdio_ext.h` (no feature-test gate; the whole header is the extension) |
| Standards | GNU / Solaris compatibility (none in ISO or POSIX) |
| Exported | `__fbufsize@@GLIBC_2.2.5`, `__flbf@@GLIBC_2.2.5`, `__fpending@@GLIBC_2.2.5`, `__fpurge@@GLIBC_2.2.5`, `__freadable@@GLIBC_2.2.5`, `__freading@@GLIBC_2.2.5`, `__fsetlocking@@GLIBC_2.2.5`, `__fwritable@@GLIBC_2.2.5`, `__fwriting@@GLIBC_2.2.5`, `_flushlbf@@GLIBC_2.2.5` (weak, nm, host glibc 2.41) |
| Thread-safety | MT-Safe race:stream (`__fbufsize`, `__fpending`, `__fpurge`, `__fsetlocking`), MT-Safe the rest (`stdio_ext(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-__fbufsize, GLIBC-__flbf, GLIBC-__fpending, GLIBC-__fpurge, GLIBC-__freadable, GLIBC-__freading, GLIBC-__fsetlocking, GLIBC-__fwritable, GLIBC-__fwriting, GLIBC-_flushlbf |

## Declaration and gates

```c
#include <stdio.h>
#include <stdio_ext.h>

size_t __fbufsize(FILE *stream);
size_t __fpending(FILE *stream);
int    __flbf(FILE *stream);
int    __freadable(FILE *stream);
int    __fwritable(FILE *stream);
int    __freading(FILE *stream);
int    __fwriting(FILE *stream);
int    __fsetlocking(FILE *stream, int type);
void   _flushlbf(void);
void   __fpurge(FILE *stream);
```

All ten are declared unconditionally in `/usr/include/stdio_ext.h`
(lines 46-82) together with the `FSETLOCKING_QUERY`, `FSETLOCKING_INTERNAL`
and `FSETLOCKING_BYCALLER` enum (lines 27-38). The header exists for
portable access to `FILE` internals, mirroring Solaris (header comment;
`stdio_ext(3)`).

## Semantics

`__fbufsize` returns the size of the stream's current buffer.
`__fpending` returns the bytes in the output buffer (wide characters on
wide-oriented streams) and is undefined in reading mode.
`__flbf` tests line buffering. `__freadable`/`__fwritable` test whether
the stream allows reading/writing; `__freading`/`__fwriting` test
read-only (or append-only) / write-only status or the last operation.
`__fsetlocking` sets and returns the locking mode: `FSETLOCKING_INTERNAL`
(default implicit locking), `FSETLOCKING_BYCALLER` (stdio stops locking),
or `FSETLOCKING_QUERY`. `_flushlbf` flushes all line-buffered streams.
`__fpurge` discards the stream's buffered data (`stdio_ext(3)`).

## Gotchas and portability

- `__fsetlocking(FSETLOCKING_BYCALLER)` is how hot loops combine the
  plain stdio calls with one external `flockfile`; reset it afterwards.
- `__fpending` on a reading-mode or read-only stream is undefined.
- These names are reserved-looking (`__` prefix) but are the documented
  portable interface to `FILE` internals; do not poke the `FILE` struct
  directly.
- musl 1.2.5: `include/stdio_ext.h` exists with all ten plus extras
  (`__freadahead`, `__freadptr`, `__freadptrinc`, `__fseterr`).

## References

- glibc manual: `stdio.texi`, nodes *Stream Buffering*, *Streams and
  Threads*
- man3: `stdio_ext(3)`
- headers: `/usr/include/stdio_ext.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
