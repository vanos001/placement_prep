# `ctime` / `asctime` / `wcsftime` (3) - glibc

> Per-function page for the fixed-format time renderers of the glibc Date
> and Time family; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status. The
> broken-down conversions they sit on live in
> [../net/localtime-gmtime-tzset.md](../net/localtime-gmtime-tzset.md), and
> the portable formatter in
> [../net/strftime-strptime-strptime_l.md](../net/strftime-strptime-strptime_l.md).

| Field | Value |
|---|---|
| Header | `time.h` |
| Standards | ISO C (`asctime`, `ctime`, `wcsftime`); POSIX.1 (`*_r` twins). The manual tags all four plain functions "Deprecated function" and says C23 deprecates them, POSIX.1-2024 removed the `_r` twins |
| Exported | `asctime`/`ctime`/`wcsftime` `@@GLIBC_2.2.5`; `asctime_r`/`ctime_r` `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `asctime`: MT-Unsafe race:asctime (static buffer); `ctime`: MT-Unsafe race:tmbuf/race:asctime plus env/heap/lock issues via `localtime`; `_r` twins MT-Safe locale (manual annotations); `wcsftime` MT-Safe env locale |
| Ledger ID | GLIBC-asctime, GLIBC-ctime, GLIBC-wcsftime (researched rows) |

## Declaration and gates

```c
#include <time.h>

char *asctime(const struct tm *brokentime);              /* deprecated */
char *asctime_r(const struct tm *brokentime, char *buffer);
char *ctime(const time_t *time);                         /* deprecated */
char *ctime_r(const time_t *time, char *buffer);
size_t wcsftime(wchar_t *s, size_t size, const wchar_t *template,
                const struct tm *brokentime);
```

## Semantics

`asctime` renders a `struct tm` into exactly the manual's fixed 26-byte
layout `"Tue May 21 13:46:22 1991\n"`, using the `Sun`..`Sat` and
`Jan`..`Dec` abbreviations; behavior is undefined if the year is below 1000
or above 9999 (manual, *Formatting Calendar Time*). The result lives in a
static buffer that only `asctime` and `ctime` overwrite. `ctime` is the
`time_t` entry point, documented as `asctime(localtime(time))`, and it also
sets the time-zone state as if `tzset` had run (manual). The `_r` twins
write into a caller buffer of at least 26 bytes; `ctime_r` does not
necessarily set the zone state (manual). `wcsftime` is the wide-character
`strftime`: same specifier set, `wchar_t` output (manual, *Formatting
Calendar Time*).

## Gotchas and portability

- The manual's own portability note, quoted: "This obsolescent function is
  deprecated in C23. Programs should instead use strftime or even sprintf."
- 26 bytes is a hard bound: four-digit years are assumed, and the 9999 limit
  makes the 2038 story (see [time-time_t-2038](../net/time-time_t-2038.md))
  irrelevant here but the 1000 limit very relevant on 64-bit `time_t`.
- `wcsftime` shares `strftime`'s zero-return ambiguity (buffer too small vs
  genuinely empty output).
- musl 1.2.5: `src/time/asctime.c`, `ctime.c` and `wcsftime.c` implement
  the same trio over `secs_to_tm` internals.

## References

- glibc manual: `time.texi`, node *Formatting Calendar Time* (deprecated
  asctime/ctime blocks, wcsftime)
- man3: `ctime.3` (the cached `asctime.3` is an `.so` alias of it)
- headers: `/usr/include/time.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
