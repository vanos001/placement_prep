# `strtoimax` / `strtoumax` / `strtoq` / `strtouq` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `inttypes.h` (`strtoimax`, `strtoumax`); `stdlib.h` (`strtoq`, `strtouq`) |
| Standards | C99 / POSIX.1-2001 (`strtoimax`, `strtoumax`); BSD names, declared as GNU/misc legacy (`strtoq`, `strtouq`) |
| Exported | `strtoimax@@GLIBC_2.2.5`, `strtoumax@@GLIBC_2.2.5`, `strtoq@@GLIBC_2.2.5`, `strtouq@@GLIBC_2.2.5` (nm, libc.so.6, host glibc 2.41; `strtoimax`/`strtoq` share one address with `strtol`/`strtoll`, `strtoumax`/`strtouq` with `strtoul`/`strtoull`) |
| Thread-safety | MT-Safe locale (`strtoimax(3)`, `strtol(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-strtoimax, GLIBC-strtoumax, GLIBC-strtoq, GLIBC-strtouq |

## Declaration and gates

```c
#include <inttypes.h>

intmax_t  strtoimax(const char *restrict nptr, char **restrict endptr,
                    int base);
uintmax_t strtoumax(const char *restrict nptr, char **restrict endptr,
                    int base);

#include <stdlib.h>            /* legacy quad names */
long long       strtoq (const char *nptr, char **endptr, int base);
unsigned long long strtouq(const char *nptr, char **endptr, int base);
```

`strtoimax`/`strtoumax` are unconditionally declared in
`/usr/include/inttypes.h` (lines 358-364). Under
`#if __GLIBC_USE (C23_STRTOL)` (line 377) calls are redirected to
`__isoc23_strtoimax`/`__isoc23_strtoumax`, which additionally accept
`0b`/`0B` prefixes in base 0 or 2 (header comment lines 374-376).
`strtoq`/`strtouq` sit in `#ifdef __USE_MISC` at
`/usr/include/stdlib.h` lines 185-196 (`strtoq` 188, `strtouq` 193).

## Semantics

`strtoimax`/`strtoumax` are just like `strtol`/`strtoul` except that
they return `intmax_t`/`uintmax_t` (`strtoimax(3)` DESCRIPTION). On
overflow or underflow they return `INTMAX_MAX`, `INTMAX_MIN` or
`UINTMAX_MAX` and set `errno` to `ERANGE`; if nothing converts, they
return 0 with `*endptr` = `nptr` (`strtoimax(3)` RETURN VALUE). Base
rules follow `strtol`: base 0 auto-detects decimal/octal/hex (binary
with C23 features), otherwise 2-36, `EINVAL` for an illegal base
(manual, node *Parsing of Integers*, arith.texi lines 2647-2728).
`strtoq` ("string-to-quad-word") is the BSD name for `strtoll`
(manual, arith.texi lines 2782-2795); `strtouq` likewise for
`strtoull` (arith.texi lines 2815-2825).

## Gotchas and portability

- `strtoq`/`strtouq` are declared with `long long` return in glibc, but
  the man page notes they may be equivalent to `strtol` or `strtoll`
  depending on wordsize; on LP64 both coincide (musl does not declare
  them at all).
- nm shows the intmax names are weak aliases of the `long` functions on
  this LP64 host, where `intmax_t` is `long`.
- Check errors by zeroing `errno` before the call and inspecting
  `endptr`, never by the return value alone (`strtol(3)` NOTES).
- musl 1.2.5: `strtoimax`/`strtoumax` present
  (`musl include/inttypes.h` lines 19-20); `strtoq`/`strtouq` absent.

## References

- glibc manual: `arith.texi`, node *Parsing of Integers* (lines 2635-2943)
- man3: `strtoimax(3)` (covers `strtoumax`), `strtol(3)` (NOTES cover
  `strtoq`), `strtoul(3)` (covers `strtouq`)
- headers: `/usr/include/inttypes.h`, `/usr/include/stdlib.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
