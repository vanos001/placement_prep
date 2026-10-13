# `stime` (2) - glibc

> Split from the chapter *glibc: Calendar Time* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | man2 lists `time.h` -- the current host header declares it **no longer** |
| Standards | SVID; deprecated in favor of `clock_settime(2)` |
| Exported | compat-only `stime@GLIBC_2.2.5` (no default-version symbol; nm, host glibc 2.41) |
| Thread-safety | Not stated: `stime(2)` carries no ATTRIBUTES table |
| Ledger ID | GLIBC-stime |

## Declaration and gates

```c
#include <time.h>

int stime(const time_t *t);   /* stime(2) SYNOPSIS;
                                 absent from /usr/include/time.h here */
```

Evidence trail on this host (glibc 2.41): `grep stime /usr/include/time.h`
finds nothing -- the declaration is gone from the header -- while
`nm -D /lib/x86_64-linux-gnu/libc.so.6` still shows the compat symbol
`stime@GLIBC_2.2.5` with no `@@` default version. Old binaries keep
linking; new source has no way to call it portably.

## Semantics

`stime` set the system clock to `t` seconds since the Epoch
(1970-01-01 00:00:00 UTC). It required privilege: under Linux
`CAP_SYS_TIME`; an unprivileged caller got `EPERM` (`stime(2)`). The
man page itself opens with "NOTE: This function is deprecated; use
clock_settime(2) instead" (`stime(2)` DESCRIPTION).

## Gotchas and portability

- Removed from the API surface: code that compiles today is declaring
  the prototype itself, which is a portability smell; use
  `clock_settime(CLOCK_REALTIME, ...)` -- second-resolution `stime`
  cannot express sub-second setting anyway.
- The ledger row records only the compat version `GLIBC_2.2.5`,
  matching the nm picture of a frozen, non-default symbol.
- musl 1.2.5 still ships a wrapper (`src/linux/stime.c`,
  declared in `include/time.h` line 131) -- but musl-wide it calls
  `clock_settime`, so behavior converges anyway.
- Kernel-side, the `stime(2)`-era system clock interface is gone from
  modern syscall tables (set via `clock_settime` today).

## Errors

`EFAULT` (bad pointer from user space), `EPERM` (insufficient
privilege; `CAP_SYS_TIME` required) -- per `stime(2)`.

## References

- man2: `stime(2)`; `clock_settime(2)` as the replacement
- headers: `/usr/include/time.h` (negative evidence: no declaration)
- symbols: `nm -D libc.so.6 | grep -w stime` (compat only)
- musl: `include/time.h`, `src/linux/stime.c`
