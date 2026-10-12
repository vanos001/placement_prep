# gettimeofday(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | gettimeofday: 96 / 78 / 169 / 78; settimeofday: 164 / 79 / 170 / 79 (ledger SC-gettimeofday, SC-settimeofday; verified syscall_64.tbl lines 108/176, syscall_32.tbl lines 93-94, syscall_generic.tbl lines 207-210, syscall_arm.tbl lines 94-95) |
| Since (kernel) | 1.0 (ledger; both calls predate 2.0) |
| Man page | man2/gettimeofday.2 is the canonical page (cached; covers both calls); settimeofday.2 is an .so alias to it |
| glibc wrapper | gettimeofday(3)/settimeofday(3) wrap the calls; on some architectures gettimeofday() is also implemented in the vDSO (gettimeofday.2, C library/kernel differences) |
| Aliases covered | settimeofday (same man page), time(2) uses gettimeofday as its backend (time.2; hub groups time separately) |
| Ledger ID | SC-gettimeofday, SC-settimeofday |

## Purpose

gettimeofday() and settimeofday() get and set the time as well as a timezone: seconds plus microseconds since the Epoch (gettimeofday.2). gettimeofday is the classic wall-clock read; settimeofday is the privileged wall-clock write whose misuse is exactly why CLOCK_MONOTONIC and the 4.3 floor exist.

## Synopsis

```c
#include <sys/time.h>
int gettimeofday(struct timeval *tv, struct timezone *tz);
int settimeofday(const struct timeval *tv, const struct timezone *tz);
struct timeval { time_t tv_sec; suseconds_t tv_usec; };
struct timezone { int tz_minuteswest; int tz_dsttime; };
```

## Arguments and behavior

tv carries the Epoch time; either argument may be NULL to leave the corresponding item untouched, though tv = NULL triggers a compilation warning (gettimeofday.2). The timezone structure is obsolete and should normally be NULL; tz_dsttime has never been used under Linux (gettimeofday.2). settimeofday() has peculiar "warp clock" semantics: if the very first call after boot has a non-NULL tz, a NULL tv, and nonzero tz_minuteswest, the kernel adjusts the system clock accordingly (gettimeofday.2). The related stime(2) slot remains only on i386/arm32 legacy tables (hub; worklog 1-e removed-brief note).

## Return value and errors

0 on success; -1 with errno on error (gettimeofday.2). Errors: EFAULT (tv or tz outside the accessible address space); EINVAL for settimeofday (invalid timezone; tv.tv_sec negative or tv.tv_usec outside [0..999999]; since Linux 4.3, setting the time below the current CLOCK_MONOTONIC value); EPERM (settimeofday needs CAP_SYS_TIME under Linux).

## Flags and constants

No flags. tv_usec is microseconds (range 0..999999); the struct timezone fields are tz_minuteswest and tz_dsttime (gettimeofday.2).

## Security and notes

Reading is unprivileged; writing the wall clock is the CAP_SYS_TIME gate (gettimeofday.2 EPERM). The 4.3 change rejects clocks set before CLOCK_MONOTONIC, closing the backwards-jump hole that broke absolute timers (gettimeofday.2; same floor as clock_settime). Precision is microseconds; for finer work use clock_gettime(2) (nanoseconds) - gettimeofday.2 SEE ALSO points there, and the vDSO note explains why the read side stays cheap.

## References

- https://man7.org/linux/man-pages/man2/gettimeofday.2.html
- worklog Task 1-e (stime legacy routing note; vDSO discussion)
- [clock_getres](clock_getres.md), [overview](overview.md)
