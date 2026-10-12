# `strtol` / `strtoul` / `strtoll` / `strtoull` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` |
| Standards | ISO C89 / POSIX.1-2001 (`strtol`, `strtoul`); C99 (`strtoll`, `strtoull`); BSD (`strtoq`, `strtouq`) |
| Exported | `strtol@@GLIBC_2.2.5`, `strtoul@@GLIBC_2.2.5`, `strtoll@@GLIBC_2.2.5` (weak), `strtoull@@GLIBC_2.2.5` (weak), `strtouq@@GLIBC_2.2.5` (weak); C23 twins `__isoc23_strtol` etc. (nm, host glibc 2.41) |
| Thread-safety | MT-Safe locale (`strtol(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-strtol, GLIBC-strtoul, GLIBC-strtoll, GLIBC-strtoull, GLIBC-strtoq, GLIBC-strtouq |

## Declaration and gates

```c
#include <stdlib.h>

long strtol(const char *restrict nptr, char **restrict endptr, int base);
unsigned long strtoul(const char *restrict nptr, char **restrict endptr, int base);
long long strtoll(const char *restrict nptr, char **restrict endptr, int base);
unsigned long long strtoull(const char *restrict nptr, char **restrict endptr, int base);
```

`strtoll`/`strtoull` are gated `__USE_ISOC99` in the installed header
(`/usr/include/stdlib.h` lines 201-206). When C23 features are enabled,
glibc redirects the four names to `__isoc23_strtol` and friends, which
additionally accept `0b`/`0B` binary literals (header lines 215-272;
manual `arith.texi` *Parsing of Integers*: "only supported when C23
features are enabled"). `strtouq` aliases `strtoull` under the same gate
family.

## Semantics

Each function skips whitespace (per `isspace`), takes an optional sign, and
parses digits in `base`: 0 means auto-detect (`0x` -> 16, leading `0` -> 8,
else 10), otherwise 2..36, with `0x` allowed when `base` is 16
(`strtol(3)`, manual *Parsing of Integers*). On success the value is
returned and, if `endptr` is non-NULL, `*endptr` points at the first
unconverted character. If no digits were seen, `*endptr` is set to the
original `nptr` and 0 returned. On overflow the clamped extreme
(`LONG_MAX`/`LONG_MIN`, `ULONG_MAX`) is returned and `errno` is set to
`ERANGE`; an out-of-range `base` yields `EINVAL` ("not in C99",
`strtol(3)` ERRORS).

## Gotchas and portability

- The errno=0 discipline: valid inputs can return `0`, `LONG_MAX` or
  `LONG_MIN`, so callers must set `errno = 0` before the call and test it
  afterwards, and check `endptr == nptr` for "no digits" (`strtol(3)`
  NOTES; manual *Parsing of Integers* states the same three checks).
- `strtoul` accepts a leading `-` and negates: `strtoul("-1", ...)` is
  `ULONG_MAX`, and a value more negative than `LONG_MIN` yields
  `(ULONG_MAX + 1) / 2` on 64-bit (`strtol(3)`-family manual, strtoul
  entry; `strtoul(3)` RETURN VALUE).
- Locale: outside "C"/"POSIX" the functions may accept
  implementation-defined additional numeric forms (`strtol(3)` NOTES);
  `MT-Safe locale` marking covers that dependence.
- `EINVAL` for bad `base` is glibc/BSD behavior, not C99; C99 leaves the
  behavior undefined for base outside 0..36 (`strtol(3)` ERRORS).
- The full-check idiom from `strtol(3)` EXAMPLES:
  `errno = 0; val = strtol(str, &endptr, base);` then test `errno`,
  `endptr == str`, and finally `*endptr == '\0'` for whole-string parses.
- musl 1.2.5 has the same surface and errno contract
  (`musl src/stdlib/strtol.c` family); it has no C23 redirect layer.

## References

- glibc manual: `arith.texi`, subsection *Parsing of Integers*
- man3: `strtol(3)` (covers `strtoll`, `strtoq`), `strtoul(3)` (covers
  `strtoull`, `strtouq`)
- header: `/usr/include/stdlib.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
