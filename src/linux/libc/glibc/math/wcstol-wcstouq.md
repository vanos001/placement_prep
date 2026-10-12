# `wcstol` / `wcstoll` / `wcstoq` / `wcstoul` / `wcstoull` / `wcstouq` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` |
| Standards | ISO C90 Amendment 1 (`wcstol`, `wcstoul`); C99 / Am.1 (`wcstoll`, `wcstoull`); GNU extensions (`wcstoq`, `wcstouq`) |
| Exported | `wcstol`/`wcstoll`/`wcstoq@@GLIBC_2.2.5` (one address), `wcstoul`/`wcstoull`/`wcstouq@@GLIBC_2.2.5` (one address) (nm, libc.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe locale (manual safety notes, arith.texi lines 2722-2723, 2749-2750) |
| Ledger ID | GLIBC-wcstol, GLIBC-wcstoll, GLIBC-wcstoq, GLIBC-wcstoul, GLIBC-wcstoull, GLIBC-wcstouq |

## Declaration and gates

```c
#include <wchar.h>

long          wcstol (const wchar_t *restrict nptr,
                      wchar_t **restrict endptr, int base);
unsigned long wcstoul(const wchar_t *restrict nptr,
                      wchar_t **restrict endptr, int base);
long long          wcstoll (const wchar_t *restrict nptr,    /* __USE_ISOC99 */
                            wchar_t **restrict endptr, int base);
unsigned long long wcstoull(const wchar_t *restrict nptr,    /* __USE_ISOC99 */
                            wchar_t **restrict endptr, int base);
long long          wcstoq (const wchar_t *restrict nptr,     /* __USE_GNU */
                           wchar_t **restrict endptr, int base);
unsigned long long wcstouq(const wchar_t *restrict nptr,     /* __USE_GNU */
                           wchar_t **restrict endptr, int base);
```

Declarations in `/usr/include/wchar.h`: `wcstol` line 455, `wcstoul`
460, `wcstoll`/`wcstoull` under `#ifdef __USE_ISOC99` (lines 464-479),
`wcstoq`/`wcstouq` under `#ifdef __USE_GNU` (lines 480-494). Under
`#if __GLIBC_USE (C23_STRTOL)` (line 497) calls redirect to
`__isoc23_wcstol` etc., which accept `0b`/`0B` prefixes in base 0 or 2.

## Semantics

`wcstol` is equivalent to `strtol` in nearly all aspects but handles
wide character strings; likewise `wcstoul` for `strtoul` (manual,
arith.texi lines 2721-2727, 2748-2754), `wcstoll`/`wcstoull` for
`strtoll`/`strtoull` (arith.texi lines 2773-2812). Parsing: leading
wide space, optional sign, digits in `base` (0 auto-detects, otherwise
2-36; invalid base gives `0l` and `errno` = `EINVAL`), tail pointer
stored via `endptr`; overflow returns `LONG_MAX`/`LONG_MIN` (or the
`ULONG_MAX`/`LLONG_MAX`/`ULLONG_MAX` twins) with `errno` = `ERANGE`
(arith.texi lines 2670-2718). `wcstoq` is equivalent to `strtoq` and
`wcstouq` to `strtouq`, both GNU extensions (arith.texi lines
2788-2794, 2821-2827).

## Gotchas and portability

- On this LP64 host nm shows the pairs collapse: `wcstol`, `wcstoll`
  and `wcstoq` share one address, as do `wcstoul`, `wcstoull` and
  `wcstouq` -- the quad names are pure aliases.
- `wcstoq`/`wcstouq` need `_GNU_SOURCE`; the ISO names need no macro
  except the C99 pair.
- musl 1.2.5: `wcstol`, `wcstoul`, `wcstoll`, `wcstoull` declared
  (`musl include/wchar.h` lines 100-104); `wcstoq`/`wcstouq` absent.
- See also [strtoimax page](strtoimax-strtoumax-strtoq-strtouq.md) for
  the narrow `strtoq`/`strtouq` twins and
  [wcstoimax page](wcstoimax-wcstoumax.md) for the intmax forms.

## References

- glibc manual: `arith.texi`, node *Parsing of Integers* (lines 2635-2943)
- headers: `/usr/include/wchar.h`
- man3: `strtol(3)` (NOTES cover `strtoq`), `strtoul(3)` (covers
  `strtouq`), `wcstoimax(3)` for the intmax wide pair
- symbols: `nm -D --with-symbol-versions libc.so.6`
