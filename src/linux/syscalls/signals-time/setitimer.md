# setitimer(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | setitimer: 38 / 104 / 103 / 104; getitimer: 36 / 105 / 102 / 105 (ledger SC-setitimer, SC-getitimer; verified syscall_64.tbl lines 50/48, syscall_32.tbl lines 119-120, syscall_generic.tbl lines 131-132, syscall_arm.tbl lines 120-121) |
| Since (kernel) | 1.0 (ledger SC-setitimer, SC-getitimer) |
| Man page | man2/getitimer.2 is the canonical page (cached; covers both calls); setitimer.2 is an .so alias ("\.so man2/getitimer.2") |
| glibc wrapper | setitimer(3)/getitimer(3) wrap the calls (<sys/time.h>); alarm(3)/sleep-family behavior also rests on ITIMER_REAL (getitimer.2 SEE ALSO alarm(2)) |
| Aliases covered | getitimer (same man page) |
| Ledger ID | SC-setitimer, SC-getitimer |

## Purpose

setitimer() and getitimer() arm, disarm, and read interval timers: timers that expire at some future point and, if a nonzero interval is set, periodically thereafter, delivering a signal to the process on each expiration (getitimer.2). A process has exactly one timer of each of the three types (getitimer.2).

## Synopsis

```c
#include <sys/time.h>
int getitimer(int which, struct itimerval *curr_value);
int setitimer(int which, const struct itimerval *new_value,
              struct itimerval *old_value);
struct itimerval {
    struct timeval it_interval; /* interval for periodic timer */
    struct timeval it_value;    /* time until next expiration */
};
```

## Arguments and behavior

which selects the timer (getitimer.2):

| Timer | Value (sys/time.h) | Counts down | Signal on expiry |
|---|---|---|---|
| ITIMER_REAL | 0 | real (wall-clock) time | SIGALRM (14) |
| ITIMER_VIRTUAL | 1 | user-mode CPU time of the process (all threads) | SIGVTALRM (26) |
| ITIMER_PROF | 2 | total (user + system) CPU time (all threads) | SIGPROF (27) |

Signal numbers from glibc bits/signum-arch.h. In setitimer(), if either field of new_value.it_value is nonzero the timer is armed to expire then; if both are zero the timer is disarmed; new_value.it_interval sets the period, both-zero meaning single-shot. old_value, when non-NULL, receives the previous setting (same shape getitimer returns: it_value is time remaining, zero meaning disarmed; it_interval the configured period, zero meaning single-shot) (getitimer.2). ITIMER_VIRTUAL together with ITIMER_PROF is the classic user/system CPU profiling pair (getitimer.2).

## Return value and errors

0 on success; -1 with errno on error (getitimer.2). Errors: EFAULT (new_value, old_value, or curr_value invalid); EINVAL (which is not one of the three timers, or - since 2.6.22 - a tv_usec outside 0..999999).

## Flags and constants

No flags beyond the which constants above.

## Security and notes

Timer granularity: timers never expire before the requested time but may expire shortly after, depending on timer resolution and system load (getitimer.2 NOTES, pointing at time(7)). A child created via fork(2) does not inherit its parent's interval timers; interval timers are preserved across execve(2) (getitimer.2). POSIX.1 leaves the interaction between setitimer() and alarm(2), sleep(3), and usleep(3) unspecified - they all touch ITIMER_REAL (getitimer.2; worklog 1-e alarm ITIMER_REAL interplay).

## References

- https://man7.org/linux/man-pages/man2/getitimer.2.html
- /usr/include/x86_64-linux-gnu/sys/time.h (ITIMER_* values), bits/signum-arch.h (signal numbers)
- [timer_create](timer_create.md), [overview](overview.md)
