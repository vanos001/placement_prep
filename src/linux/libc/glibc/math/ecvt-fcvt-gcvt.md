# `ecvt` / `ecvt_r` / `fcvt` / `fcvt_r` / `gcvt` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` |
| Standards | SVID / Unix98, marked LEGACY in POSIX.1-2001, removed in POSIX.1-2008 (`ecvt`, `fcvt`, `gcvt`); GNU extensions (`ecvt_r`, `fcvt_r`) |
| Exported | `ecvt@@GLIBC_2.2.5`, `fcvt@@GLIBC_2.2.5`, `gcvt@@GLIBC_2.2.5`, `ecvt_r@@GLIBC_2.2.5`, `fcvt_r@@GLIBC_2.2.5` (nm, libc.so.6, host glibc 2.41) |
| Thread-safety | `ecvt`: MT-Unsafe race:ecvt; `fcvt`: MT-Unsafe race:fcvt; `gcvt`: MT-Safe; `ecvt_r`/`fcvt_r`: MT-Safe (`ecvt(3)`, `ecvt_r(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-ecvt, GLIBC-ecvt_r, GLIBC-fcvt, GLIBC-fcvt_r, GLIBC-gcvt |

## Declaration and gates

```c
#include <stdlib.h>

char *ecvt(double value, int ndigit, int *restrict decpt, int *restrict sign);
char *fcvt(double value, int ndigit, int *restrict decpt, int *restrict sign);
char *gcvt(double value, int ndigit, char *buf);
int   ecvt_r(double value, int ndigit, int *restrict decpt,
             int *restrict sign, char *restrict buf, size_t len);
int   fcvt_r(double value, int ndigit, int *restrict decpt,
             int *restrict sign, char *restrict buf, size_t len);
```

`ecvt`/`fcvt`/`gcvt` are declared under the XOPEN_EXTENDED/MISC gate of
`/usr/include/stdlib.h` lines 1003-1028 (`ecvt` at 1012, `fcvt` 1018,
`gcvt` 1024). The `_r` reentrant forms sit in the
next `#ifdef __USE_MISC` block (lines 1029-1056: `ecvt_r` 1042,
`fcvt_r` 1045). Feature macros per `ecvt(3)`: `_DEFAULT_SOURCE`
(glibc >= 2.20) or the XOPEN_SOURCE >= 500 form without
_POSIX_C_SOURCE >= 200809L.

## Semantics

`ecvt` converts `value` to a null-terminated string of at most `ndigit`
digits with no decimal point or sign; the first digit is nonzero unless
the value is zero, the last is rounded to nearest. `*decpt` receives the
position of the decimal point relative to the string start (negative
means left of the string), `*sign` is nonzero for negative values. If
`value` is zero it is unspecified whether `*decpt` is 0 or 1
(`ecvt(3)`, manual node *Old-fashioned System V number-to-string
functions*, arith.texi lines 3196-3222). `fcvt` is identical except
`ndigit` counts digits after the decimal point. `gcvt` is equivalent to
`sprintf(buf, "%*g", ndigit, value)` and returns `buf` (manual,
arith.texi lines 3240-3250). `ecvt_r`/`fcvt_r` write into a caller
buffer of length `len` and return -1 on error, 0 otherwise (`ecvt_r(3)`).

## Gotchas and portability

- `ecvt`/`fcvt` return a pointer to a static buffer overwritten by the
  next call to the same function -- the source of the race:ecvt marks.
- `ndigit` is silently reduced when it would exceed `double` precision
  (`ecvt(3)`).
- The manuals recommend `sprintf`/`snprintf` instead
  (`ecvt_r(3)` NOTES: these functions are obsolete).
- musl 1.2.5: `ecvt`/`fcvt`/`gcvt` declared (`musl include/stdlib.h`
  lines 156-158); the `_r` forms are absent.

## References

- glibc manual: `arith.texi`, node *Old-fashioned System V
  number-to-string functions* (lines 3183-3338)
- man3: `ecvt(3)`, `ecvt_r(3)`, `gcvt(3)`
- headers: `/usr/include/stdlib.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
