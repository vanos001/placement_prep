# `basename` / `dirname` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `libgen.h` (POSIX/XPG pair); `string.h` GNU `basename` under `__USE_GNU` |
| Standards | POSIX.1-2001, POSIX.1-2008 (`basename(3)` CONFORMING TO); GNU `basename` is an extension |
| Exported | `basename@@GLIBC_2.2.5` (weak, 0x...a61c0), `dirname@@GLIBC_2.2.5` (strong, 0x...1057a0), `__xpg_basename@@GLIBC_2.2.5` (strong, 0x...53170) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`basename(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-basename, GLIBC-dirname |

## Declaration and gates

```c
#include <libgen.h>

char *dirname(char *path);
char *basename(char *path);      /* macro: __xpg_basename */

#define _GNU_SOURCE
#include <string.h>
char *basename(const char *path); /* GNU version, never modifies */
```

`libgen.h` declares `dirname` at line 26 and the XPG basename at lines
34-35, where `#define basename __xpg_basename` renames the entry point -
this is exactly the "POSIX version" the man page describes
(`/usr/include/libgen.h`). The GNU `basename` sits in `string.h` under
`__USE_GNU` at lines 528-541 and is deliberately *not* declared when the
`basename` macro from `libgen.h` is visible (`#ifndef basename` guard).

## Semantics

The pair splits a pathname: `dirname` returns everything up to the final
`/`, `basename` the component after it; trailing slashes do not count.
No slash means `dirname` gives `"."` and `basename` a copy of the path;
`"/"` yields `"/"` for both; NULL or `""` yields `"."`. Concatenating
dirname, `"/"` and basename rebuilds the path. Both may modify `path`
and may return static storage or pointers into it - do not free the
result (`basename(3)`, SUSv2 table reproduced there: `/usr/lib` to
`/usr`+`lib`, `usr` to `.`+`usr`).

## Gotchas and portability

- Two basenames coexist: the XPG one from `libgen.h` may modify its
  argument; the GNU one (default via `string.h` under `_GNU_SOURCE`)
  never modifies its argument and returns `""` for a trailing slash,
  even for `"/"`. There is no GNU `dirname` (`basename(3)` NOTES,
  `libgen.h` comment).
- glibc BUGS: the POSIX versions modify `path` and segfault on static
  strings such as `"/usr/"` - pass a `strdup` copy, as the man page
  example does. Before glibc 2.2.1, `dirname` mishandled trailing
  slashes and segfaulted on NULL.
- The distinct `__xpg_basename` symbol proves both implementations ship
  in one libc; which one you get is decided purely by header inclusion
  order and feature macros.
- musl 1.2.5 provides both via `musl include/libgen.h` lines 8-9.

## References

- glibc manual: `string.texi` does not cover these; behavior is
  man-page-driven
- man3: `basename(3)` (covers `dirname`)
- headers: `/usr/include/libgen.h`, `/usr/include/string.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
