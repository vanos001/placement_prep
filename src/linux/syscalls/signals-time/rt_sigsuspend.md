# rt_sigsuspend(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | rt_sigsuspend: 130 / 179 / 133 / 179 (ledger SC-rt_sigsuspend; verified syscall_64.tbl line 142, syscall_32.tbl line 194, syscall_generic.tbl line 169, syscall_arm.tbl line 196); legacy sigsuspend: - / 72 / - / 72 (ledger SC-sigsuspend; verified syscall_32.tbl line 87) |
| Since (kernel) | rt_sigsuspend 2.2 (sigsuspend.2, C library/kernel differences: rt_* added "with the addition of real-time signals in Linux 2.2"); legacy sigsuspend 1.0 (ledger SC-sigsuspend) |
| Man page | man2/sigsuspend.2 (cached); rt_sigsuspend.2 is an .so alias ("\.so man2/rt_sigsuspend.2") |
| glibc wrapper | glibc sigsuspend(3) transparently calls rt_sigsuspend() and hides the sigsetsize argument (sigsuspend.2, C library/kernel differences) |
| Aliases covered | sigsuspend (legacy kernel name and the glibc-visible POSIX name) |
| Ledger ID | SC-rt_sigsuspend, SC-sigsuspend |

## Purpose

rt_sigsuspend() atomically replaces the calling thread's signal mask with mask and suspends the thread until delivery of a signal whose action is to run a handler or terminate the process (sigsuspend.2). It is the race-free "wait for exactly the signals not in mask" primitive: because the mask swap and the sleep are one atomic step, a signal arriving between the two cannot be missed - the gap that plain pause() cannot close.

## Synopsis

```c
#include <signal.h>
int sigsuspend(const sigset_t *mask);
/* kernel ABI */
int rt_sigsuspend(const sigset_t *mask, size_t sigsetsize);
```

## Arguments and behavior

mask is the temporary signal mask. If the delivered signal terminates the process, sigsuspend() never returns; if it is caught, the call returns after the handler returns and the mask is restored to its pre-call state (sigsuspend.2). SIGKILL and SIGSTOP cannot be blocked; listing them in mask has no effect. The kernel form takes sigsetsize, currently required to be sizeof(sigset_t) or EINVAL results (sigsuspend.2).

## Return value and errors

sigsuspend() always returns -1 with errno set, normally EINTR ("The call was interrupted by a signal"); EFAULT if mask points outside the address space (sigsuspend.2).

## Flags and constants

No flags; mask is built with sigsetops(3).

## Security and notes

Because it always returns -1, callers must read errno, not the return value, to distinguish interrupt from fault. After the handler runs, the mask swap is undone even if the handler changed the mask with rt_sigprocmask. Typical pattern: block a signal with rt_sigprocmask, do critical work, then sigsuspend() on the complement mask to wait for it (signal(7) pattern; sigsuspend.2 SEE ALSO). Conforming to POSIX.1-2001, POSIX.1-2008 (sigsuspend.2).

## References

- https://man7.org/linux/man-pages/man2/sigsuspend.2.html
- [rt_sigprocmask](rt_sigprocmask.md), [pause](pause.md), [overview](overview.md)
