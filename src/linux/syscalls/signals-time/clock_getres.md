# clock_getres(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | clock_getres: 229 / 266 / 114 / 264; clock_gettime: 228 / 265 / 113 / 263; clock_settime: 227 / 264 / 112 / 262 (ledger SC-clock_getres / SC-clock_gettime / SC-clock_settime; verified syscall_64.tbl lines 239-241, syscall_32.tbl lines 279-281, syscall_generic.tbl lines 143-148, syscall_arm.tbl lines 280-282); time64 twins (i386/arm32 only): clock_gettime64 403, clock_settime64 404, clock_getres_time64 406 (syscall_32.tbl lines 412, 413, 415) |
| Since (kernel) | 2.6 (clock_getres.2 VERSIONS: "These system calls first appeared in Linux 2.6"; ledger SC-clock_getres); time64 twins 5.1 (worklog 1-e: verified by tag-probing syscall_32.tbl at v5.0 vs v5.1 - v5.0 has no time64 rows, v5.1 has 20) |
| Man page | man2/clock_getres.2 is the canonical page (cached); clock_gettime.2 and clock_settime.2 are .so aliases ("\.so man2/clock_getres.2") |
| glibc wrapper | clock_gettime(3)/clock_settime(3)/clock_getres(3) wrap the calls; on some architectures clock_gettime() is also implemented in the vDSO (clock_getres.2, C library/kernel differences); glibc 2.30+ first tries time64 wrappers then falls back (worklog 1-e, glibc NEWS; seccomp-filtered fallback caveat) |
| Aliases covered | clock_gettime, clock_settime, clock_gettime64, clock_settime64, clock_getres_time64 |
| Ledger ID | SC-clock_getres, SC-clock_gettime, SC-clock_settime, SC-clock_gettime64, SC-clock_settime64, SC-clock_getres_time64 |

## Purpose

clock_getres() reports the resolution of a clock; clock_gettime() reads it; clock_settime() sets it (clock_getres.2). Everything that timestamps, sleeps, or arms timers on Linux keys off these three calls and the clockid_t namespace they share.

## Synopsis

```c
#include <time.h>
int clock_getres(clockid_t clockid, struct timespec *res);
int clock_gettime(clockid_t clockid, struct timespec *tp);
int clock_settime(clockid_t clockid, const struct timespec *tp);
struct timespec { time_t tv_sec; long tv_nsec; };
```

## Arguments and behavior

clockid selects the clock (values from glibc bits/time.h; "since" from clock_getres.2):

| Clock | Value | Meaning | Since |
|---|---|---|---|
| CLOCK_REALTIME | 0 | settable wall clock, Epoch-based, NTP/adjtime-adjustable | 2.6 |
| CLOCK_MONOTONIC | 1 | nonsettable, since boot, no wall-clock jumps, NTP-slew affected, excludes suspend | 2.6 |
| CLOCK_PROCESS_CPUTIME_ID | 2 | CPU time of all threads in the process | 2.6.12 |
| CLOCK_THREAD_CPUTIME_ID | 3 | CPU time of the calling thread | 2.6.12 |
| CLOCK_MONOTONIC_RAW | 4 | raw hardware time, no NTP/adjtime | 2.6.28 |
| CLOCK_REALTIME_COARSE | 5 | tick-granular fast realtime | 2.6.32 |
| CLOCK_MONOTONIC_COARSE | 6 | tick-granular fast monotonic | 2.6.32 |
| CLOCK_BOOTTIME | 7 | like MONOTONIC but includes suspend | 2.6.39 |
| CLOCK_REALTIME_ALARM | 8 | like REALTIME, wakes suspended system | 3.0 |
| CLOCK_BOOTTIME_ALARM | 9 | like BOOTTIME, wakes suspended system | 3.0 |
| CLOCK_TAI | 11 | realtime minus leap seconds | 3.10 |

Dynamic clock IDs (per-process/per-thread CPU clocks from clock_getcpuclockid(3)/pthread_getcpuclockid(3), and POSIX-clock character devices) are supported since 2.6.39 (clock_getres.2). For clock_settime(), a tp not a multiple of the clock resolution res is truncated (clock_getres.2).

## Return value and errors

0 on success; -1 with errno on error (clock_getres.2). Errors: EACCES (no write permission on a dynamic clock device, clock_settime); EFAULT (tp/res invalid); EINVAL (invalid clockid; tp.tv_sec negative or tv_nsec outside [0..999999999]; clockid not settable; since 4.3, CLOCK_REALTIME set below the current CLOCK_MONOTONIC value).

## Flags and constants

No flags. Setting CLOCK_REALTIME affects absolute timers immediately, relative ones never (clock_getres.2).

## Security and notes

Setting a clock needs privilege (CLOCK_REALTIME via CAP_SYS_TIME; clock_settime path of gettimeofday.2 EPERM documents the capability for wall-clock writes). CLOCK_MONOTONIC guarantees time never goes backwards but successive calls may return identical values depending on architecture (clock_getres.2).

## References

- https://man7.org/linux/man-pages/man2/clock_getres.2.html
- /usr/include/x86_64-linux-gnu/bits/time.h (CLOCK_* values)
- worklog Task 1-e (time64 rows verified: v5.0 vs v5.1 syscall_32.tbl tag diff; glibc 2.30 time64 wrapper order)
- [clock_nanosleep](clock_nanosleep.md), [timer_create](timer_create.md), [overview](overview.md)
