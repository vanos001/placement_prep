# `timespec_get` / `timespec_getres` (3) - glibc

> Split from the chapter *glibc: Calendar Time* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `time.h` (`timespec_get` under `__USE_ISOC11`; `timespec_getres` under `__GLIBC_USE (ISOC23)`) |
| Standards | ISO C11 (`timespec_get`); ISO C23 (`timespec_getres`) |
| Exported | `timespec_get@@GLIBC_2.16`, `timespec_getres@@GLIBC_2.34` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `@safety` comments, `time.texi`) |
| Ledger ID | GLIBC-timespec_get, GLIBC-timespec_getres |

## Declaration and gates

```c
#include <time.h>

#define TIME_UTC 1        /* /usr/include/time.h lines 64-65 */

int timespec_get(struct timespec *ts, int base);   /* __USE_ISOC11,
                                                      lines 380-384 */
int timespec_getres(struct timespec *ts, int base); /* ISOC23,
                                                       lines 393-399 */
```

No man page covers these (the sparse man tree has none); the
declarations and gates above are read directly from
`/usr/include/time.h`.

## Semantics

`timespec_get` stores the current time of ISO C clock `base` into
`*ts` and returns `base` on success, 0 on failure (manual
`time.texi`). glibc maps the bases onto POSIX clocks: `TIME_UTC`
(wall time since the epoch) to `CLOCK_REALTIME`; the C23 extras
`TIME_MONOTONIC` to `CLOCK_MONOTONIC`, `TIME_ACTIVE` to
`CLOCK_PROCESS_CPUTIME_ID`, and `TIME_THREAD_ACTIVE` to
`CLOCK_THREAD_CPUTIME_ID` (`time.texi` node *Time Base*). Only
`TIME_UTC` is required by ISO C; the others are optional and must be
probed by return value. `timespec_getres` stores the *resolution* of
the given base into `*ts` when `ts` is non-NULL, again returning
`base` or 0 (manual, `timespec_getres` entry).

## Gotchas and portability

- `TIME_UTC` epoch on POSIX systems matches `clock_gettime`'s
  `CLOCK_REALTIME`; on non-POSIX systems the epoch is
  implementation-defined (manual, *Time Base*).
- `timespec_getres` needs an ISOC23-grade toolchain (`-std=c23` or
  `_ISOC23_SOURCE`-grade feature selection); it is glibc 2.34+
  material, absent from musl 1.2.5 (musl declares only
  `timespec_get`, `include/time.h` line 63).
- Failure is silent (return 0) -- always compare against `base`, not
  zero-initialization.
- For Linux, `clock_gettime` remains the finer-grained, better
  documented route; the C11 pair exists for portable ISO C code.

## References

- glibc manual: `time.texi`, nodes *Time Base*, `timespec_get` /
  `timespec_getres` entries
- headers: `/usr/include/time.h` (lines 64-65, 380-399)
- symbols: `nm -D libc.so.6`
- musl: `include/time.h` (`timespec_get` only)
