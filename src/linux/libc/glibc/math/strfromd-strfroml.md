# `strfromd` / `strfromf` / `strfromfN` / `strfromfNx` / `strfroml` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` |
| Standards | ISO/IEC TS 18661-1 (`strfromd`, `strfromf`, `strfroml`); TS 18661-3 (`strfromfN`, `strfromfNx` family) |
| Exported | `strfromd`/`strfromf`/`strfroml@@GLIBC_2.25`, `strfromf32`/`strfromf64`/`strfromf32x`/`strfromf64x@@GLIBC_2.27`, `strfromf128@@GLIBC_2.26` (nm, libc.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe locale; AS-Unsafe heap; AC-Unsafe mem (`strfromd(3)` ATTRIBUTES, marked preliminary) |
| Ledger ID | GLIBC-strfromd, GLIBC-strfromf, GLIBC-strfromfN, GLIBC-strfromfNx, GLIBC-strfroml |

## Declaration and gates

```c
#include <stdlib.h>

int strfromd(char *restrict str, size_t n,
             const char *restrict format, double fp);
int strfromf(char *restrict str, size_t n,
             const char *restrict format, float fp);
int strfroml(char *restrict str, size_t n,
             const char *restrict format, long double fp);
```

`strfromd`/`strfromf`/`strfroml` are inside
`#if __GLIBC_USE (IEC_60559_BFP_EXT_C23)` at
`/usr/include/stdlib.h` lines 277-290 (gate comment line 276). The
`_FloatN`/`_FloatNx` forms (`strfromf16`/`f32`/`f64`/`f128` and
`strfromf32x`/`f64x`/`f128x`, lines 291-331) need
`__GLIBC_USE (IEC_60559_TYPES_EXT)` plus the `__HAVE_FLOAT*` macros.
The BFP gate requires `__STDC_WANT_IEC_60559_BFP_EXT__`, `_GNU_SOURCE`
or C23 mode (`bits/libc-header-start.h` lines 67-77); the man page
synopsis lists `__STDC_WANT_IEC_60559_BFP_EXT__`.

## Semantics

Equivalent to `snprintf(str, n, format, fp)` except for the restricted
format string (`strfromd(3)` DESCRIPTION): `format` must start with
`%`, optionally followed by a precision `.N` (precision 0 if the period
is bare), then exactly one of `a A e E f F g G`. No length modifier and
no `*` are allowed; a malformed format is undefined behavior. The
conversion is typed by the function suffix, so no length modifier is
needed. Returns the number of characters that would have been written
excluding the terminating null; the null is written if and only if the
return is less than `n` (`strfromd(3)` RETURN VALUE). NaN and infinity
print as `nan`/`inf` (or `NAN`/`INF` with uppercase specifiers). The
manual adds the same contract for `strfromfN`/`strfromfNx`
(arith.texi lines 3176-3182).

## Gotchas and portability

- A return value of `n` or greater means the output was truncated
  (`strfromd(3)` RETURN VALUE); the man page defines no negative error
  return.
- Respects `LC_NUMERIC` for the decimal point (`strfromd(3)` NOTES);
  glibc 2.25 and later (`strfromd(3)` VERSIONS).
- `strfromfN`/`strfromfNx` are family notation; exported names are
  `strfromf32`, `strfromf64`, `strfromf32x`, `strfromf64x`,
  `strfromf128`.
- musl 1.2.5: no `strfrom*` in `musl include/` or `musl src/`
  (verified absent).

## References

- glibc manual: `arith.texi`, node *Printing of Floats* (lines 3132-3182)
- man3: `strfromd(3)` (covers `strfromf`, `strfroml`)
- headers: `/usr/include/stdlib.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
