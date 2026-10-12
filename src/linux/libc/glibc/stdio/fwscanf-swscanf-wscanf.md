# `fwscanf` / `swscanf` / `wscanf` / `vfwscanf` / `vswscanf` / `vwscanf` (3) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` |
| Standards | C95 (Amendment 1) / C99 / POSIX.1-2001 |
| Exported | `fwscanf@@GLIBC_2.2.5`, `wscanf@@GLIBC_2.2.5`, `swscanf@@GLIBC_2.2.5`, `vfwscanf@@GLIBC_2.2.5`, `vswscanf@@GLIBC_2.2.5`, `vwscanf@@GLIBC_2.2.5`; redirected builds also use `__isoc99_fwscanf@@GLIBC_2.7` and `__isoc23_fwscanf@@GLIBC_2.38` etc. (nm, host glibc 2.41) |
| Thread-safety | MT-Safe locale (per the narrow `scanf(3)` family ATTRIBUTES; no `wscanf(3)` page in the cached man-pages) |
| Ledger ID | GLIBC-fwscanf, GLIBC-swscanf, GLIBC-vfwscanf, GLIBC-vswscanf, GLIBC-vwscanf, GLIBC-wscanf |

## Declaration and gates

```c
#include <wchar.h>

int fwscanf(FILE *restrict stream, const wchar_t *restrict format, ...);
int wscanf(const wchar_t *restrict format, ...);
int swscanf(const wchar_t *restrict s, const wchar_t *restrict format, ...);
int vfwscanf(FILE *restrict s, const wchar_t *restrict format, va_list ap);
int vwscanf(const wchar_t *restrict format, va_list ap);
int vswscanf(const wchar_t *restrict s, const wchar_t *restrict format,
             va_list ap);
```

`fwscanf`/`wscanf`/`swscanf` are in the `__USE_ISOC95 || __USE_UNIX98`
block of `wchar.h` (`/usr/include/wchar.h` lines 722, 773-785), the
`v*` forms in the `__USE_ISOC99` block (lines 846-928).

## Semantics

Wide-character analogs of the `fscanf` family: the format string is
`wchar_t *`, input comes from a wide-oriented stream (`fwscanf`,
`wscanf` on `stdin`) or a wide string (`swscanf`), and conversions
follow the shared scanf rules of the manual node *Formatted Input
Basics*, including `%ls`/`%l[` for wide arguments. They return the
number of input items assigned, or `EOF` on input failure.

## Gotchas and portability

- Symbol redirection: when the compiler targets C99/C23 semantics,
  glibc redirects the `*wscanf` names to `__isoc99_*` (glibc 2.7) or
  `__isoc23_*` (glibc 2.38) for the changed `%a` and binary-constant
  handling; the unversioned `wscanf@@GLIBC_2.2.5` stays for old
  binaries (`/usr/include/wchar.h` lines 795-839, 868-928).
- No `wscanf(3)` man page exists in the cached man-pages set; semantics
  above rest on the glibc manual and the header.
- musl 1.2.5: all six present and unconditional in `wchar.h`
  (`musl src/stdio/fwscanf.c`, `vfwscanf.c`, `vswscanf.c`,
  `vwscanf.c`).

## References

- glibc manual: `stdio.texi`, nodes *Formatted Input Basics*,
  *Formatted Input Functions*, *Streams and I18N*
- man3: `scanf(3)` (narrow analog, shared conversion rules)
- headers: `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
