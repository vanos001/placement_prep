# sigpending(2) / rt_sigpending(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | rt_sigpending 127 / 176 / 136 / 176; sigpending -- / 73 / -- / 73 |
| Since (kernel) | rt_sigpending 2.2; sigpending 1.0 (legacy) |
| Man page | man2/sigpending.2 (man-pages 6.19 HTML set, fetched 2026-10-17); man2/rt_sigpending.2 is a .so alias into the sigaction.2 page, which documents the rt_* call |
| glibc wrapper | sigpending(3) T @@GLIBC_2.2.5 (nm -D, glibc 2.41); the wrapper calls rt_sigpending(2) when available (sigpending.2, C library/kernel differences) |
| Aliases covered | rt_sigpending (SC-rt_sigpending, documented); legacy sigpending (SC-sigpending, 16-bit sigset) |
| Ledger ID | SC-rt_sigpending |

## Purpose

sigpending() returns the set of signals that are pending for delivery to the calling thread -- signals raised while blocked -- into `set` (sigpending.2, DESCRIPTION). rt_sigpending() is the 2.2 real-time-signals-era variant that takes an explicit `sigsetsize` and supports the enlarged `sigset_t`; the legacy sigpending() entry carries the old fixed-size 32-bit sigset (sigpending.2, C library/kernel differences).

## Synopsis

```c
#include <signal.h>
int sigpending(sigset_t *set);
/* raw: syscall(SYS_rt_sigpending, sigset_t *set, size_t sigsetsize) */
```

## Arguments and behavior

`set` receives the pending mask (sigpending.2, DESCRIPTION). On the raw rt_sigpending() call, `sigsetsize` must equal `sizeof(sigset_t)` (8 bytes on Linux) or the kernel returns EINVAL -- the same pattern as [rt_sigaction](rt_sigaction.md) and [rt_sigtimedwait](sigtimedwait.md). "Pending" has two layers worth stating in an interview: per-thread pending signals and process-directed pending signals (shared by the thread group); what sigpending() reports for the calling thread is the union relevant to its delivery (sigpending.2, DESCRIPTION; signal(7) for the model).

## Return value and errors

0 on success; -1 with errno on failure (sigpending.2, RETURN VALUE). Errors: EFAULT (`set` points outside the address space) (sigpending.2, ERRORS).

## Flags and constants

None (the sigset manipulation itself uses sigemptyset/sigfillset/sigismember(3)).

## Security and notes

No capability involved; the call inspects only the caller's own state. The 16-bit legacy entry (i386 73, arm 73) exists for old binaries; glibc routes sigpending(3) through rt_sigpending(2) on any kernel that has it. Classic usage: with [sigprocmask](rt_sigprocmask.md) block-then-check sequences and sigsuspend(2) handshakes, where the pending set tells you whether a blocked signal arrived before you began waiting. Cross-reference: [rt_sigaction](rt_sigaction.md), [rt_sigprocmask](rt_sigprocmask.md), [rt_sigsuspend](rt_sigsuspend.md), [sigtimedwait](sigtimedwait.md), [kill](kill.md).

## References

- https://man7.org/linux/man-pages/man2/sigpending.2.html
- https://man7.org/linux/man-pages/man2/sigaction.2.html (rt_sigpending documentation)
- worklog: wrapper symbol sigpending @@GLIBC_2.2.5 verified with nm -D against glibc 2.41 (2026-10-17)
