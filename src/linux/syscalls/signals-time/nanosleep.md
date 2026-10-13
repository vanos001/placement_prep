# nanosleep(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 35 / 162 / 101 / 162 (ledger SC-nanosleep; verified syscall_64.tbl line 47, syscall_32.tbl line 177, syscall_generic.tbl lines 129-130, syscall_arm.tbl line 179) |
| Since (kernel) | 2.0 (ledger SC-nanosleep; hub Since column) |
| Man page | man2/nanosleep.2 (cached) |
| glibc wrapper | nanosleep(3) is the direct wrapper (<time.h>, nanosleep.2); no -lrt requirement on current glibc (the -lrt note in this family applies to clock_nanosleep for glibc < 2.17) |
| Aliases covered | none |
| Ledger ID | SC-nanosleep |

## Purpose

nanosleep() suspends the calling thread until at least the interval in *req has elapsed, or until delivery of a signal that invokes a handler in the calling thread or terminates the process (nanosleep.2). Compared to sleep(3)/usleep(3) it has higher resolution, POSIX specifies it does not interact with signals, and interrupted sleeps are resumable via the rem output (nanosleep.2).

## Synopsis

```c
#include <time.h>
int nanosleep(const struct timespec *req, struct timespec *rem);
struct timespec { time_t tv_sec; long tv_nsec; }; /* tv_nsec in 0..999999999 */
```

## Arguments and behavior

req specifies the pause. If interrupted by a signal handler, the call returns -1 with EINTR and writes the remaining time into *rem (when rem is non-NULL); the caller can then re-issue the call with rem to finish the pause (nanosleep.2). Two caveats the man page documents: (1) Linux measures the sleep against CLOCK_MONOTONIC, while POSIX.1 nominally says CLOCK_REALTIME - but POSIX also forbids clock_settime(2) discontinuities from affecting relative sleeps, so the practical behavior is compliant (nanosleep.2 NOTES); (2) repeated interrupt-then-restart cycles drift, because each restart recomputes from the remaining time - the man page recommends clock_nanosleep(2) with TIMER_ABSTIME to sleep to an absolute deadline instead (nanosleep.2).

## Return value and errors

0 on success; -1 with errno on interruption or error (nanosleep.2). Errors: EINTR (interrupted; *rem carries the remaining time so the thread can resume the pause); EFAULT (copy problem from user space); EINVAL (tv_nsec outside 0..999999999 or negative tv_sec).

## Flags and constants

No flags.

## Security and notes

Restart semantics: an interrupted nanosleep that the kernel restarts (SA_RESTART path) resumes through restart_syscall(2) with the remaining time (restart_syscall.2 SEE ALSO; worklog 1-e ERESTART_RESTARTBLOCK note). In Linux 2.4 a thread stopped by a signal (e.g. SIGTSTP) and resumed by SIGCONT got EINTR, and a subsequent restart did not count the stopped time; fixed in 2.6.0 (nanosleep.2). A pre-2.6 extension busy-waited sub-2 ms pauses under real-time scheduling; removed in 2.5.39 (nanosleep.2 Old behavior).

## References

- https://man7.org/linux/man-pages/man2/nanosleep.2.html
- [clock_nanosleep](clock_nanosleep.md) (absolute-deadline replacement), [clock_getres](clock_getres.md), [overview](overview.md)
