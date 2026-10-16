# stime(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / 25 / -- / -- |
| Since (kernel) | 1.0 |
| Man page | man2/stime.2 (man-pages 6.19 HTML set, fetched 2026-10-17): "NOTE: This function is deprecated; use clock_settime(2) instead" |
| glibc wrapper | stime(3) T @GLIBC_2.2.5 -- non-weak, still exported but deprecated (nm -D, glibc 2.41); glibc declared it removed-from-new-ports years ago (stime.2 SYNOPSIS marks [[deprecated]]) |
| Aliases covered | none |
| Ledger ID | SC-stime |

## Purpose

stime() sets the system's idea of the time and date to the `time_t` seconds value pointed to by `t`, measured since the Epoch, 1970-01-01 00:00:00 +0000 (UTC); execution requires the superuser (stime.2, DESCRIPTION). It is the second-granularity ancestor of clock_settime(2) and survives only on the i386 table (syscall 25) -- asm-generic ABIs never had it.

## Synopsis

```c
#include <time.h>
[[deprecated]] int stime(const time_t *t);
```

## Arguments and behavior

One argument: a pointer to the new wall-clock time in seconds (stime.2, DESCRIPTION). Sub-second adjustment is impossible; use clock_settime(2)/CLOCK_REALTIME for anything finer. Setting the clock invalidates relative timers' assumptions the same way any CLOCK_REALTIME jump does (adjacent to the discipline machinery in [adjtimex](clock_adjtime.md)).

## Return value and errors

0 on success; -1 with errno on error (stime.2, RETURN VALUE). Errors: EFAULT (`t` points outside the address space); EPERM (the caller lacks CAP_SYS_TIME -- the man page phrases it as "may be executed only by the superuser") (stime.2, ERRORS).

## Flags and constants

None.

## Security and notes

Capability: CAP_SYS_TIME (the capability form is the modern phrasing of "superuser only"). Setting the clock backwards is a security event in its own right (certificate validity windows, cron semantics, log ordering), which is why hardened systems gate it through timedated/NTP daemons instead of raw stime(2). New code must use clock_settime(2) (stime.2, DESCRIPTION note). The wrapper symbol survives as a plain T in glibc 2.41 but is marked deprecated in the man page -- another 16-bit-era fossil alongside [ulimit](../sched-misc/ulimit.md). Cross-reference: [time](time.md), [clock_adjtime](clock_adjtime.md), [gettimeofday](gettimeofday.md).

## References

- https://man7.org/linux/man-pages/man2/stime.2.html
- worklog: wrapper symbol stime @GLIBC_2.2.5 (deprecated, non-weak) verified with nm -D against glibc 2.41 (2026-10-17)
