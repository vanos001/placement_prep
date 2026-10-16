# alarm(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 37 / 27 / -- / -- |
| Since (kernel) | 1.0 |
| Man page | man2/alarm.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | alarm(3) T @@GLIBC_2.2.5 (nm -D, glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-alarm |

## Purpose

alarm() arranges for SIGALRM to be delivered to the calling process in `seconds` seconds; any previously set alarm is canceled, and `seconds` == 0 simply cancels any pending alarm (alarm.2, DESCRIPTION). It is the coarse one-shot timer of classic UNIX: second granularity, process-wide, no tags -- everything interval timers ([setitimer](setitimer.md)) and POSIX timers ([timer_create](timer_create.md)) add on top.

## Synopsis

```c
#include <unistd.h>
unsigned int alarm(unsigned int seconds);
```

## Arguments and behavior

One argument, the delay in seconds; zero cancels the pending alarm (alarm.2, DESCRIPTION). The call is per-process, not per-thread: whichever thread calls it replaces the process's single real-time alarm. Alarms created by alarm() are preserved across execve(2) and are NOT inherited by children created via fork(2) (alarm.2, NOTES) -- a favorite interview detail, since the exec-preservation is what makes the classic "self-limiting program" pattern work. alarm() and setitimer(2)'s ITIMER_REAL share the same underlying timer, so calls to one interfere with the other (alarm.2, NOTES); sleep(3) may itself be implemented via SIGALRM, and mixing alarm() with sleep(3) is a documented bad idea (alarm.2, NOTES).

## Return value and errors

Returns the number of seconds remaining until the previously scheduled alarm was due, or 0 if none was pending (alarm.2, RETURN VALUE). The call cannot fail -- it has no error returns and never sets errno (alarm.2). Scheduling delays can still make actual delivery late by an arbitrary amount (alarm.2, NOTES).

## Flags and constants

None.

## Security and notes

SIGALRM delivery interacts with everything else in the signal layer: a handler must be installed ([sigaction](rt_sigaction.md)) or the default action terminates the process; alarm() races with pause(2)/sigsuspend flows in the classic sleep implementation exercise. No capability is involved; any process may alarm itself. Numbers note: there is no asm-generic/arm64 entry (g64/arm columns `--`) -- 64-bit generic ABIs never carried alarm, so the glibc wrapper lands on the i386/x64 entries only on those kernels... on arm64 alarm(3) is implemented by glibc using setitimer ITIMER_REAL instead. Standards: POSIX.1-2024; HISTORY 4.3BSD, SVr4, POSIX.1-1988 (alarm.2, STANDARDS/HISTORY). Cross-reference: [setitimer](setitimer.md), [timer_create](timer_create.md), [pause](pause.md), [rt_sigaction](rt_sigaction.md), [nanosleep](nanosleep.md).

## References

- https://man7.org/linux/man-pages/man2/alarm.2.html
- worklog: wrapper symbol alarm @@GLIBC_2.2.5 verified with nm -D against glibc 2.41 (2026-10-17)
