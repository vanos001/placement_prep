# clock_nanosleep(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | clock_nanosleep: 230 / 267 / 115 / 265; time64 twin (i386/arm32 only): clock_nanosleep_time64 407 (ledger SC-clock_nanosleep; verified syscall_32.tbl lines 282 and 416) |
| Since (kernel) | 2.6 (clock_nanosleep.2 VERSIONS: "first appeared in Linux 2.6"; ledger SC-clock_nanosleep); time64 twin 5.1 (worklog 1-e v5.0/v5.1 table diff) |
| Man page | man2/clock_nanosleep.2 (cached) |
| glibc wrapper | clock_nanosleep(3) since glibc 2.1; link with -lrt only for glibc versions before 2.17 (clock_nanosleep.2 SYNOPSIS/VERSIONS); glibc 2.30+ tries the time64 wrapper first, then falls back (worklog 1-e, glibc NEWS) |
| Aliases covered | clock_nanosleep_time64 (documented inline per the time64 twin convention) |
| Ledger ID | SC-clock_nanosleep, SC-clock_nanosleep_time64 |

## Purpose

clock_nanosleep() suspends the calling thread with nanosecond precision, letting the caller choose the clock the interval is measured against and whether the deadline is relative or absolute (clock_nanosleep.2). It supersedes nanosleep(2) wherever drift matters.

## Synopsis

```c
#include <time.h>
int clock_nanosleep(clockid_t clockid, int flags,
                    const struct timespec *request,
                    struct timespec *remain);
```

## Arguments and behavior

clockid accepts CLOCK_REALTIME, CLOCK_TAI (3.10), CLOCK_MONOTONIC, CLOCK_BOOTTIME (2.6.39), CLOCK_PROCESS_CPUTIME_ID, plus CPU-clock IDs from clock_getcpuclockid(3)/pthread_getcpuclockid(3); CLOCK_THREAD_CPUTIME_ID is not permitted (clock_nanosleep.2). With flags 0 the request is relative to the clock's current value; with TIMER_ABSTIME (1, glibc bits/time.h) request is an absolute deadline and a deadline already past returns immediately; remain is unused for absolute sleeps - just re-issue the same request to restart (clock_nanosleep.2). POSIX.1 specifies that changing CLOCK_REALTIME via clock_settime(2) wakes an absolute sleeper immediately if the new clock value passes the deadline (clock_nanosleep.2).

## Return value and errors

Uniquely among this family, clock_nanosleep() does not return -1: on success it returns 0, and on interruption or error it returns one of the positive error numbers directly (clock_nanosleep.2 RETURN VALUE). Errors: EINTR (interrupted by a signal handler); EFAULT (request/remain invalid); EINVAL (tv_nsec outside 0..999999999, negative tv_sec, invalid clockid, or CLOCK_THREAD_CPUTIME_ID); ENOTSUP (kernel cannot sleep against this clockid).

## Flags and constants

| Flag | Value | Meaning | Since |
|---|---|---|---|
| TIMER_ABSTIME | 1 | request is an absolute time on clockid | 2.6 (glibc bits/time.h) |

## Security and notes

clock_nanosleep() is never restarted after a signal handler interrupts it, regardless of SA_RESTART; a relative sleep restarted by hand would drift, which is exactly what the absolute form avoids (clock_nanosleep.2). POSIX.1 specifies the call has no effect on signal dispositions or the signal mask. To sleep without drift: clock_gettime(2) the desired clock, add the interval, sleep with TIMER_ABSTIME (clock_nanosleep.2). POSIX.1-2001 (clock_nanosleep.2 CONFORMING TO).

## References

- https://man7.org/linux/man-pages/man2/clock_nanosleep.2.html
- /usr/include/x86_64-linux-gnu/bits/time.h (TIMER_ABSTIME = 1)
- worklog Task 1-e (time64 twin i386 407, kernel 5.1, tag-verified)
- [nanosleep](nanosleep.md), [clock_getres](clock_getres.md), [overview](overview.md)
