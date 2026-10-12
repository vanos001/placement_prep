# `fmemopen` / `open_memstream` / `fopencookie` (3) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdio.h` (`fopencookie` under `__USE_MISC`; `fmemopen`/`open_memstream` under `__USE_XOPEN2K8`/`LIB_EXT2`) |
| Standards | POSIX.1-2008 (`fmemopen`, `open_memstream`); GNU (`fopencookie`) |
| Exported | `fmemopen@@GLIBC_2.22` plus compat `fmemopen@GLIBC_2.2.5`, `open_memstream@@GLIBC_2.2.5`, `fopencookie@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`fmemopen(3)`, `open_memstream(3)`, `fopencookie(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-fmemopen, GLIBC-open_memstream, GLIBC-fopencookie |

## Declaration and gates

```c
#include <stdio.h>

FILE *fopencookie(void *restrict cookie, const char *restrict mode,
                  cookie_io_functions_t io_funcs);        /* __USE_MISC */

FILE *fmemopen(void *s, size_t len, const char *modes);   /* XOPEN2K8 */

FILE *open_memstream(char **bufloc, size_t *sizeloc);     /* XOPEN2K8 */
```

`fopencookie` is in the `__USE_MISC` block of `stdio.h` (lines 303-310)
-- the man page asks for `_GNU_SOURCE`, which implies it --
`fmemopen`/`open_memstream` in the
`#if defined __USE_XOPEN2K8 || __GLIBC_USE (LIB_EXT2)` block (lines
312-322).

## Semantics

`fmemopen` opens a stream on the caller's buffer of `len` bytes: mode
`a`/`a+` starts the position at the first null byte (`len+1` if none),
a null byte is written at the end on flush/close if space remains, and
reads do not stop at embedded nulls. With `s == NULL` glibc allocates
`len` bytes, freed on `fclose`, with no way to retrieve the pointer
(`fmemopen(3)`, manual *String Streams*). `open_memstream` allocates a
growing buffer and publishes `*bufloc`/`*sizeloc` on every `fflush` or
`fclose`; the values stay valid only until the next output, the
trailing null is not counted in the size, and seeking past the end
zero-fills. `fopencookie` builds a stream over four caller hook
functions (`read`, `write`, `seek`, `close` in `cookie_io_functions_t`)
receiving the opaque cookie as first argument.

## Gotchas and portability

- `fileno(3)` fails on all three (no descriptor behind the stream);
  `freopen(3)` also fails on them (manual, *Opening Streams*).
- glibc 2.22 split: binary mode (`b`) removed and several append/
  `SEEK_END`/zero-size bugs fixed behind the new `fmemopen@@GLIBC_2.22`
  symbol; old binaries keep the buggy `@GLIBC_2.2.5` behavior
  (`fmemopen(3)` NOTES/BUGS).
- Pre-2.22, `fmemopen(..., 0, ...)` failed with `EINVAL`.
- musl 1.2.5: all three present (`musl src/stdio/fmemopen.c`,
  `open_memstream.c`, `fopencookie.c`).

## References

- glibc manual: `stdio.texi`, nodes *String Streams*, *Custom Streams*,
  *Streams and Cookies*
- man3: `fmemopen(3)`, `open_memstream(3)`, `fopencookie(3)`
- headers: `/usr/include/stdio.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
