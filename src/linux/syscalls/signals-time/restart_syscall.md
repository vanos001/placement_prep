# restart_syscall(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 219 / 0 / 128 / 0 |
| Since (kernel) | 2.6 |
| Man page | man2/restart_syscall.2 (man-pages 6.19 HTML set, fetched 2026-10-17); no glibc wrapper by design (man NOTES) |
| glibc wrapper | none -- "There is no glibc wrapper for this system call" (restart_syscall.2, SYNOPSIS/NOTES); it appears in syscall tables, not libc |
| Aliases covered | none |
| Ledger ID | SC-restart_syscall |

## Purpose

restart_syscall() is the kernel's internal trampoline for resuming a timed system call after the process was stopped by a signal (SIGSTOP/SIGTSTP and friends) and later continued with SIGCONT (restart_syscall.2, DESCRIPTION). The restarted call must have its timeout adjusted for the time already elapsed -- including the stopped time -- which a plain ERESTARTSYS-style rewind cannot express; the kernel therefore re-enters through syscall number 0 (on i386/arm) or 219 (x86_64) with the saved restart block carrying the recomputed deadline.

## Synopsis

```c
long restart_syscall(void);   /* kernel-internal; userspace never calls it */
```

## Arguments and behavior

No userspace arguments: the state to restart lives in the kernel's restart block (restart_syscall.2, DESCRIPTION). The mechanism applies only to the time-adjusting calls -- poll(2) (since 2.6.24), nanosleep(2) and clock_nanosleep(2) (since 2.6), and futex(2) with FUTEX_WAIT (since 2.6.22) and FUTEX_WAIT_BITSET (since 2.6.31) (restart_syscall.2, DESCRIPTION). For everything else, interruption by a stop/continue cycle falls back to the ordinary ERESTARTNOHAND/ERESTARTSYS rewind, which simply re-executes the call with its original arguments. Calling restart_syscall() directly from userspace has no defined effect: the restart block is only populated while a restartable call is pending.

## Return value and errors

For userspace, the only observable result is the restarted system call's own return value -- the trampoline disappears into the restarted call (restart_syscall.2, DESCRIPTION). The restarted nanosleep/clock_nanosleep still reports the residual time correctly adjusted for the stopped interval.

## Flags and constants

None.

## Security and notes

The number-0 numbering on i386 and arm32 is a nice interview detail: the "syscall 0" slot on those architectures is not read(2) on the restart path but restart_syscall (compare the ledger row: i386 0, arm 0, while x64 uses 219). Seccomp filters that inspect syscall numbers see restart_syscall on resume -- a real-world seccomp gotcha when allow-listing poll(2) or futex(2) without it. Time accounting across stop/continue is the whole point: without the mechanism, a 10-second nanosleep stopped for a minute would resume sleeping the full 10 seconds again. Cross-reference: [nanosleep](nanosleep.md), [clock_nanosleep](clock_nanosleep.md), [poll](../net-ipc/poll.md), [futex](../process/futex.md), [pause](pause.md).

## References

- https://man7.org/linux/man-pages/man2/restart_syscall.2.html
- man-pages syscalls(2) version table (2.6)
