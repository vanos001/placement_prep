# `strfmon` (3) - glibc

> Split from the chapter *glibc: Locales* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `monetary.h` |
| Standards | POSIX.1-2001/2008 (XSI); `strfmon_l` since POSIX.1-2008 |
| Exported | `strfmon@@GLIBC_2.2.5`, `strfmon_l@@GLIBC_2.3` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe `locale` (`strfmon`); MT-Safe (`strfmon_l`) (`strfmon(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-strfmon, GLIBC-strfmon_l |

## Declaration and gates

```c
#include <monetary.h>

ssize_t strfmon(char *restrict s, size_t max,
                const char *restrict format, ...);      /* lines 38-40 */
ssize_t strfmon_l(char *restrict s, size_t max, locale_t locale,
                  const char *restrict format, ...);    /* lines 48-49 */
```

`/usr/include/monetary.h` gates neither prototype (verified: the
header has no `__USE_*` conditionals around the declarations).

## Semantics

`strfmon` formats monetary amounts per the current locale's
`LC_MONETARY` rules and writes into `s` (at most `max` bytes,
always NUL-terminated on success). Ordinary characters are copied;
conversion specifiers start with `%` and take optional flags in this
order: `=f` (fill character), `^` (suppress grouping), `(` or `+`
(negative amounts in parentheses vs signed), `!` (omit the currency
symbol), `-` (left justify); then a field width, a left precision
`#n` with grouping-aware padding, a right precision `.p`, and the
conversion itself -- `%i` for the international format (`int_curr_symbol`,
e.g. `USD 1,234.56`) or `%n` for the national format (`currency_symbol`,
e.g. `$1,234.56`) (`strfmon(3)`). `strfmon_l` formats under an
explicit locale object and is undefined for `LC_GLOBAL_LOCALE`.

## Gotchas and portability

- The double argument is a `double`: binary floating point rounds
  monetary values -- pass scaled integers as doubles only when exact.
- Success returns the character count excluding the NUL; -1 means the
  output did not fit (`E2BIG`) or the format was bad (`EILSEQ`,
  `EINVAL`) -- `strfmon` does not truncate silently, unlike
  `snprintf`.
- `%%` yields a literal percent; a `double` promotion happens on the
  varargs exactly like `printf`.
- musl 1.2.5 declares and implements both (musl `include/monetary.h`,
  `src/locale/strfmon.c`).

## Errors

`E2BIG` (buffer too small; contents then undefined), `EILSEQ`
(bad multibyte conversion), `EINVAL` (invalid format string).

## References

- glibc manual: `locale.texi`, *Formatting Numbers* context,
  `strfmon(3)`
- headers: `/usr/include/monetary.h`
- musl: `include/monetary.h`, `src/locale/strfmon.c`
