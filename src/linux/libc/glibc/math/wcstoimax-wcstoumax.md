# `wcstoimax` / `wcstoumax` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `inttypes.h` (`stddef.h` for `wchar_t` per the man page SYNOPSIS) |
| Standards | C99 / POSIX.1-2001 |
| Exported | `wcstoimax@@GLIBC_2.2.5` (one address with `wcstol`), `wcstoumax@@GLIBC_2.2.5` (one address with `wcstoul`) (nm, libc.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe locale (`wcstoimax(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-wcstoimax, GLIBC-wcstoumax |

## Declaration and gates

```c
#include <stddef.h>
#include <inttypes.h>

intmax_t  wcstoimax(const wchar_t *restrict nptr,
                    wchar_t **restrict endptr, int base);
uintmax_t wcstoumax(const wchar_t *restrict nptr,
                    wchar_t **restrict endptr, int base);
```

Declared in `/usr/include/inttypes.h` lines 366-374 (parameterized on
`__gwchar_t`, which is `wchar_t` in C). Under
`#if __GLIBC_USE (C23_STRTOL)` (line 377) calls redirect to
`__isoc23_wcstoimax`/`__isoc23_wcstoumax`, which additionally accept
`0b`/`0B` prefixes in base 0 or 2 (header comment lines 374-376).
`inttypes.h` pulls in `stddef.h` with `__need_wchar_t` when `wchar_t`
is not already defined (lines 36-38).

## Semantics

Just like `wcstol`/`wcstoul` except that they return `intmax_t` and
`uintmax_t` respectively (`wcstoimax(3)` DESCRIPTION; manual,
arith.texi lines 2846-2871). Base handling, whitespace, sign, tail
pointer and the C23 binary-prefix extension are those of
[wcstol family](wcstol-wcstouq.md); overflow returns `INTMAX_MAX`,
`INTMAX_MIN` or `UINTMAX_MAX` with `errno` = `ERANGE`, and no
conversion returns 0 with `*endptr` = `nptr` (as for `strtoimax(3)`
RETURN VALUE). Both were introduced in ISO C99 (arith.texi lines
2852, 2871).

## Gotchas and portability

- The header declares them with `__gwchar_t`; this is a build-time
  alias for `wchar_t`, so the man page and manual both present plain
  `wchar_t` prototypes.
- Weak-alias structure on this LP64 host: `wcstoimax` shares one
  address with `wcstol` and `wcstoumax` with `wcstoul`, matching
  `intmax_t` = `long`.
- musl 1.2.5: both declared (`musl include/inttypes.h` lines 22-23),
  making this one of the few intmax pieces portable across musl and
  glibc unchanged.
- See the narrow twins on the
  [strtoimax page](strtoimax-strtoumax-strtoq-strtouq.md).

## References

- glibc manual: `arith.texi`, node *Parsing of Integers* (lines 2846-2871)
- man3: `wcstoimax(3)` (covers `wcstoumax`)
- headers: `/usr/include/inttypes.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
