# `atof` / `atoi` / `atol` / `atoll` / `strtod` / `strtof` / `strtold` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` |
| Standards | ISO C89 (`atof`, `atoi`, `atol`, `strtod`); C99 (`atoll`, `strtof`, `strtold`) |
| Exported | `atof@@GLIBC_2.2.5`, `atoi@@GLIBC_2.2.5`, `atol@@GLIBC_2.2.5`, `atoll@@GLIBC_2.2.5`, `strtod@@GLIBC_2.2.5`, `strtof@@GLIBC_2.2.5`, `strtold@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe locale (`atoi(3)`, `atof(3)`, `strtod(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-atof, GLIBC-atoi, GLIBC-atol, GLIBC-atoll, GLIBC-strtod, GLIBC-strtof, GLIBC-strtold |

## Declaration and gates

```c
#include <stdlib.h>

double atof(const char *nptr);
int    atoi(const char *nptr);
long   atol(const char *nptr);
long long atoll(const char *nptr);   /* _ISOC99_SOURCE */

double strtod(const char *restrict nptr, char **restrict endptr);
float  strtof(const char *restrict nptr, char **restrict endptr);
long double strtold(const char *restrict nptr, char **restrict endptr);
```

`strtof`/`strtold` are gated `__USE_ISOC99` in the installed header
(`/usr/include/stdlib.h` lines 118-131); glibc additionally ships GNU
`*_l` twins (`strtod_l`, `strtof_l`, `strtold_l`, plus C23 float twins)
under `__USE_GNU` (lines 415-475).

## Semantics

The `ato*` functions are documented wrappers with no error reporting:
`atoi(nptr)` behaves exactly like `(int) strtol(nptr, NULL, 10)`, `atol`
like `strtol`, `atoll` like `strtoll`, and `atof` like
`strtod(nptr, NULL)` (`atoi(3)`, `atof(3)`; the same expansions appear as
extern-inline definitions in `/usr/include/stdlib.h` lines 479-498). The
`strto*` family parses optional whitespace, sign, then a decimal number
(digits with optional locale radix point and `e` exponent), a hexadecimal
number (`0x...p+/-exp`), `INF`/`INFINITY`, or `NAN` optionally followed by
an n-char-sequence (`strtod(3)`). On success the value is returned and
`*endptr` points past the converted text; with no conversion, 0 is
returned and `*endptr` is set to `nptr`. Overflow returns
`+/-HUGE_VAL`/`HUGE_VALF`/`HUGE_VALL` and sets `errno = ERANGE`; underflow
returns a value no larger in magnitude than `DBL_MIN`/`FLT_MIN`/`LDBL_MIN`
with `ERANGE` (`strtod(3)` RETURN VALUE/ERRORS).

## Gotchas and portability

- The `ato*` family cannot report failure: `atoi(3)` BUGS lists no `errno`,
  no overflow/underflow check, base-10 only, and 0 returned for garbage;
  `atoi("123abc")` is 123, `atoi("")` is 0, indistinguishable from real
  zeros. New code should use `strtol`/`strtod` with the errno=0 discipline.
- errno=0 discipline applies to `strtod` too, because 0 is a legitimate
  result on both success and failure (`strtod(3)` NOTES).
- NAN payloads: glibc interprets the `NAN(n-char-sequence)` payload as an
  integer (decimal, or `0`/`0x` prefixed) placed into the mantissa
  (`strtod(3)` NOTES).
- Locale: the radix character is locale-dependent, and `MT-Safe locale`
  marking follows from that (`strtod(3)` ATTRIBUTES); in non-C locales
  `strtod` may accept additional implementation-defined forms.
- musl 1.2.5 also returns 0 on error for `atoi` and ships the same
  wrapper semantics (`atoi(3)` NOTES names glibc, musl and uClibc).

## References

- glibc manual: `arith.texi`, subsection *Parsing of Floats* (and
  *Parsing of Integers* for the `ato*` wrappers)
- man3: `atoi(3)` (covers `atol`, `atoll`), `atof(3)`, `strtod(3)`
  (covers `strtof`, `strtold`)
- header: `/usr/include/stdlib.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
