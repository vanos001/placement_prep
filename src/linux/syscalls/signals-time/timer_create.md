# timer_create(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | timer_create: 222 / 259 / 107 / 257; timer_settime: 223 / 260 / 110 / 258; timer_gettime: 224 / 261 / 108 / 259; timer_getoverrun: 225 / 262 / 109 / 260; timer_delete: 226 / 263 / 111 / 261 (ledger SC-timer_* rows; all five verified in cached syscall_64.tbl, syscall_32.tbl lines 274-278, syscall_generic.tbl lines 136-141, syscall_arm.tbl lines 275-279; note the generic table orders gettime 108 before settime 110); time64 twins (i386/arm32): timer_gettime64 408, timer_settime64 409 (syscall_32.tbl lines 417-418) |
| Since (kernel) | 2.6 (timer_create.2/timer_settime.2/timer_delete.2 VERSIONS: "available since Linux 2.6"; ledger); timer_gettime64/timer_settime64 5.1 (worklog 1-e v5.0/v5.1 table diff) |
| Man page | man2/timer_create.2, timer_settime.2 (canonical for timer_gettime via .so), timer_getoverrun.2, timer_delete.2 (all cached) |
| glibc wrapper | timer_create(3) and siblings wrap the calls; link with -lrt (timer_create.2 SYNOPSIS note; the link requirement is historical for glibc < 2.17); glibc 2.30+ prefers time64 wrappers with fallback (worklog 1-e, glibc NEWS) |
| Aliases covered | timer_settime, timer_gettime, timer_getoverrun, timer_delete (POSIX-timer family group), timer_gettime64 / timer_settime64 twins |
| Ledger ID | SC-timer_create, SC-timer_settime, SC-timer_gettime, SC-timer_getoverrun, SC-timer_delete |

## Purpose

The POSIX per-process interval timer API: timer_create() makes a timer against a chosen clock and returns an ID; timer_settime() arms/disarms it; timer_gettime() reads it; timer_getoverrun() reports missed expirations; timer_delete() destroys it (timer_create.2). Unlike setitimer(2) the family is not limited to three per-process timers and delivers through a configurable sigevent model.

## Synopsis

```c
#include <signal.h>
#include <time.h>
int timer_create(clockid_t clockid, struct sigevent *sevp,
                 timer_t *timerid);
int timer_settime(timer_t timerid, int flags,
                  const struct itimerspec *new_value,
                  struct itimerspec *old_value);
int timer_gettime(timer_t timerid, struct itimerspec *curr_value);
int timer_getoverrun(timer_t timerid);
int timer_delete(timer_t timerid);
```

## Arguments and behavior

timer_create's clockid accepts CLOCK_REALTIME, CLOCK_MONOTONIC, CLOCK_PROCESS_CPUTIME_ID and CLOCK_THREAD_CPUTIME_ID (2.6.12), CLOCK_BOOTTIME (2.6.39), and the alarm clocks CLOCK_REALTIME_ALARM / CLOCK_BOOTTIME_ALARM (3.0, CAP_WAKE_ALARM required); CLOCK_MONOTONIC_RAW is not usable for timers (timer_create.2 comments). The sigevent model (timer_create.2; constants from bits/sigevent-consts.h):

| sigev_notify | Value | Behavior |
|---|---|---|
| SIGEV_NONE | 0 | no notification; poll with timer_gettime |
| SIGEV_SIGNAL | 1 | generate sigev_signo; siginfo si_code = SI_TIMER; at most one signal queued per timer at any time |
| SIGEV_THREAD | 2 | invoke sigev_notify_function as if starting a new thread |
| SIGEV_THREAD_ID | 4 | Linux-specific: SIGEV_SIGNAL targeted at sigev_notify_thread_id (a kernel tid in the same process); for threading libraries |

sevp = NULL equals SIGEV_SIGNAL with sigev_signo SIGALRM and sival_int = timer ID. timer_settime() arms with it_value (both fields zero disarms) and periods via it_interval; TIMER_ABSTIME (1, bits/time.h) makes it_value an absolute time on the timer's clock, expiring immediately if already past (timer_settime.2). timer_gettime() always returns a relative it_value regardless of how the timer was armed. At most one signal is queued per timer, so expirations occurring before delivery are counted: timer_getoverrun() returns that count. BUGS note (timer_getoverrun.2): POSIX says the return saturates at DELAYTIMER_MAX; before Linux 4.19 the counter instead cycled from low values once it exceeded the maximum representable integer; since 4.19 the call returns DELAYTIMER_MAX (INT_MAX, <limits.h>) and resets the overrun to 0. For SIGEV_SIGNAL deliveries the count is also visible in the si_overrun field of siginfo_t - a nonportable Linux extension (timer_getoverrun.2 NOTES). timer_delete() disarms and deletes; the treatment of a pending signal from the deleted timer is unspecified (timer_delete.2).

## Return value and errors

timer_create(): 0 and *timerid on success; -1 with errno on failure. Errors: EAGAIN (temporary kernel allocation failure), EINVAL (invalid clockid, sigev_notify, sigev_signo, or sigev_notify_thread_id), ENOMEM, ENOTSUP (kernel does not support the clock) (timer_create.2). timer_settime/timer_gettime: 0 or -1 with EFAULT/EINVAL (timerid invalid; it_value.tv_nsec outside 0..999999999). timer_getoverrun: the overrun count or -1 with EINVAL (timer_getoverrun.2). timer_delete: 0 or -1 with EINVAL (timer_delete.2).

## Flags and constants

TIMER_ABSTIME = 1 (glibc bits/time.h). SIGEV_* values as tabled above. DELAYTIMER_MAX is the overrun cap (<limits.h>; INT_MAX) (timer_getoverrun.2).

## Security and notes

Alarm clocks require CAP_WAKE_ALARM (timer_create.2). At most one signal per timer is queued - real-time signals cannot raise the queue limit for timers (timer_getoverrun.2 rationale). Timers created with SIGEV_THREAD_ID plus SI_TIMER siginfo are what NPTL-style libraries build SIGEV_THREAD on.

## References

- https://man7.org/linux/man-pages/man2/timer_create.2.html
- https://man7.org/linux/man-pages/man2/timer_settime.2.html
- https://man7.org/linux/man-pages/man2/timer_getoverrun.2.html
- https://man7.org/linux/man-pages/man2/timer_delete.2.html
- /usr/include/x86_64-linux-gnu/bits/sigevent-consts.h, bits/time.h
- [clock_getres](clock_getres.md), [setitimer](setitimer.md), [overview](overview.md)
