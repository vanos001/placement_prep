# `timegm` / `timelocal` (3) - glibc

> Split from the chapter *glibc: Calendar Time* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `time.h` (`timegm` under `__USE_MISC` or `__GLIBC_USE (ISOC23)`; `timelocal` under `__USE_MISC`) |
| Standards | BSD/SVID (`_DEFAULT_SOURCE` per man); `timegm` enters ISO C23 |
| Exported | `timegm@@GLIBC_2.2.5`, `timelocal@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe `env locale` (`timegm(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-timegm, GLIBC-timelocal |

## Declaration and gates

```c
#include <time.h>

time_t timegm(struct tm *tp);     /* lines 243-246:
                                     __USE_MISC || __GLIBC_USE (ISOC23) */
time_t timelocal(struct tm *tp);  /* __USE_MISC block, lines 257-263 */
```

Gates per the man page: since glibc 2.19, `_DEFAULT_SOURCE`
(previously `_BSD_SOURCE || _SVID_SOURCE`) (`timegm(3)`). The header
comment calls `timelocal` "Another name for `mktime`" (line 259).

## Semantics

The pair are the inverses of `gmtime` and `localtime`: both take a
broken-down `struct tm` and produce a `time_t` seconds-since-Epoch
value. `timelocal` interprets the `tm` in the local timezone --
exactly like `mktime(3)`, whose alias it is. `timegm` interprets it
as UTC, ignoring `TZ` entirely (`timegm(3)`, manual *Calculating
Calendar Time* context). Both normalize the `tm` fields as `mktime`
does and return `(time_t) -1` with `errno` set when the value cannot
be represented (`EOVERFLOW`) (`timegm(3)`).

## Gotchas and portability

- `timegm` is the portable-ish way to do arithmetic on UTC times
  without falling into `TZ` re-parsing; ISO C23 promotes it beyond
  BSD/SVID, and glibc's header exposes it under the ISOC23 switch
  even without `_DEFAULT_SOURCE` (`/usr/include/time.h` line 243).
- `timelocal` is not in POSIX; portable code should write `mktime`.
- Like `mktime`, both may modify the `struct tm` passed in
  (normalization), so the input fields are not preserved.
- musl 1.2.5 provides `timegm` (`src/time/timegm.c`); `timelocal`
  is glibc-only vocabulary.

## Errors

`EOVERFLOW`: the result cannot be represented in `time_t`
(`timegm(3)` ERRORS).

## References

- glibc manual: `time.texi`, *Broken-down Time* / calendar-time
  conversion nodes
- man3: `timegm(3)` (covers `timelocal`), `mktime(3)`
- headers: `/usr/include/time.h` (lines 243-263)
- musl: `src/time/timegm.c`
