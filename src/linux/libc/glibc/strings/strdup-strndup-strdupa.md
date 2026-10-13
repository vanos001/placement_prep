# `strdup` / `strndup` / `strdupa` / `strndupa` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` |
| Standards | POSIX.1-2001 (`strdup`); POSIX.1-2008 (`strndup`); GNU extensions (`strdupa`, `strndupa`) |
| Exported | `strdup@@GLIBC_2.2.5` (weak), `strndup@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41; `strdupa`/`strndupa` are header macros, no symbol) |
| Thread-safety | MT-Safe (`strdup(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-strdup, GLIBC-strndup, GLIBC-strdupa, GLIBC-strndupa |

## Declaration and gates

```c
#include <string.h>

char *strdup(const char *s);
char *strndup(const char *s, size_t n);

#define _GNU_SOURCE          /* strdupa, strndupa: macros, need GCC */
#include <string.h>
char *strdupa(const char *s);
char *strndupa(const char *s, size_t n);
```

Header gates (`/usr/include/string.h`): `strdup` under
`__USE_XOPEN_EXTENDED || __USE_XOPEN2K8 || __GLIBC_USE(LIB_EXT2/ISOC23)`
(lines 184-189); `strndup` under `__USE_XOPEN2K8 || LIB_EXT2 || ISOC23`
(lines 194-197); `strdupa`/`strndupa` are `#define` macros under
`__USE_GNU && __GNUC__` (lines 199-220). Feature-macro history per
`strdup(3)`: `_XOPEN_SOURCE >= 500` or `_POSIX_C_SOURCE >= 200809L` for
`strdup`; `_POSIX_C_SOURCE >= 200809L` since glibc 2.10 for `strndup`.

## Semantics

`strdup` returns a `malloc(3)`-allocated duplicate of `s`, freeable with
`free(3)`; on failure it returns `NULL` with `errno` set to `ENOMEM`
(`strdup(3)`). `strndup` copies at most `n` bytes and always adds a
terminating null, so the result is a valid string even when `s` is longer
(`strdup(3)`; manual *Truncating Strings* node stresses this differs from
`strncpy`). `strdupa`/`strndupa` are the same operations on `alloca`-ed
stack storage (`strdup(3)`).

## Gotchas and portability

- The `a`-suffixed pair are macros, not functions: they evaluate `s` more
  than once, must not be used where a function call is required (e.g. inside
  another call's argument list), and allocate on the stack, so they inherit
  every `alloca(3)` limitation: no error return, and dead on large strings or
  deep recursion (manual *Truncating Strings*, `strndupa` entry; `strdup(3)`).
- The macro implementation in `string.h` is
  `strlen(old) + 1` bytes via `__builtin_alloca` plus `memcpy`; because the
  size expression is not constant, the allocation cannot move out of loops.
- `strndup` is the bounded form that *terminates*; pairing it with
  `strncpy`-style truncation is the usual fix for unterminated fixed buffers.
- Failure handling: only the malloc'ing pair can fail (`ENOMEM`);
  `strdup(3)` documents exactly that error.
- musl 1.2.5 provides `strdup`/`strndup` as real functions and `strdupa` as
  a macro `strcpy(alloca(strlen(x)+1), x)` (`musl include/string.h` line 92,
  `src/string/strdup.c`, `src/string/strndup.c`).

## References

- glibc manual: `string.texi`, nodes *Copying Strings and Arrays*
  (`strdup`), *Truncating Strings* (`strndup`, `strndupa`)
- man3: `strdup(3)` (covers all four)
- header: `/usr/include/string.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
