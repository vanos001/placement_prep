# `qecvt` / `qecvt_r` / `qfcvt` / `qfcvt_r` / `qgcvt` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` |
| Standards | GNU extensions to the SVID trio (manual, arith.texi lines 3253-3292) |
| Exported | `qecvt@@GLIBC_2.2.5`, `qfcvt@@GLIBC_2.2.5`, `qgcvt@@GLIBC_2.2.5`, `qecvt_r@@GLIBC_2.2.5`, `qfcvt_r@@GLIBC_2.2.5` (nm, libc.so.6, host glibc 2.41) |
| Thread-safety | `qecvt`: MT-Unsafe race:qecvt; `qfcvt`: MT-Unsafe race:qfcvt; `qgcvt`: MT-Safe; `qecvt_r`/`qfcvt_r`: MT-Safe (`qecvt(3)`, `ecvt_r(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-qecvt, GLIBC-qecvt_r, GLIBC-qfcvt, GLIBC-qfcvt_r, GLIBC-qgcvt |

## Declaration and gates

```c
#include <stdlib.h>

char *qecvt(long double value, int ndigit, int *restrict decpt,
            int *restrict sign);
char *qfcvt(long double value, int ndigit, int *restrict decpt,
            int *restrict sign);
char *qgcvt(long double value, int ndigit, char *buf);
int   qecvt_r(long double value, int ndigit, int *restrict decpt,
              int *restrict sign, char *restrict buf, size_t len);
int   qfcvt_r(long double value, int ndigit, int *restrict decpt,
              int *restrict sign, char *restrict buf, size_t len);
```

`qecvt`/`qfcvt`/`qgcvt` and all `_r` forms share the
`#ifdef __USE_MISC` block of `/usr/include/stdlib.h` (gate at line 1029;
`qecvt` 1030, `qfcvt` 1033, `qgcvt` 1036, `qecvt_r` 1049, `qfcvt_r`
1053). Feature macros per `qecvt(3)`: `_DEFAULT_SOURCE` since glibc
2.19, `_SVID_SOURCE` before. The long double twins of
[ecvt family](ecvt-fcvt-gcvt.md); the historical `q` referred to
quad-precision.

## Semantics

Each function is equivalent to its `double` counterpart except that the
first parameter is `long double`, and `ndigit` is restricted by the
precision of a `long double` rather than a `double` (manual, arith.texi
lines 3253-3292). `qecvt` produces significant-digit strings with
`*decpt`/`*sign` side effects and a static return buffer;
`qfcvt` counts digits after the decimal point; `qgcvt` is the
`"%*g"`-style conversion into a caller buffer, returning `buf`. The
`_r` forms write into a user buffer of length `len` and return -1 on
error, 0 otherwise (`ecvt_r(3)`, which documents all four `_r` names).

## Gotchas and portability

- The static-buffer hazard is identical to `ecvt`/`fcvt`: consecutive
  calls from different threads or interleaved calls overwrite the
  result; use the `_r` forms under an external buffer.
- These names are pure glibc AT&T lineage -- POSIX removed even the
  `double` versions in 2008, so nothing here is portable.
- On x86-64 `long double` is 80-bit extended; the digit limit differs
  from the `double` trio.
- musl 1.2.5: none of the five names is declared
  (`musl include/stdlib.h` has no `qecvt`/`qfcvt`/`qgcvt`/`ecvt_r`
  matches -- verified absent).

## References

- glibc manual: `arith.texi`, node *Old-fashioned System V
  number-to-string functions* (lines 3183-3338)
- man3: `qecvt(3)` (covers `qfcvt`, `qgcvt`), `ecvt_r(3)` (covers
  `qecvt_r`, `qfcvt_r`)
- headers: `/usr/include/stdlib.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
