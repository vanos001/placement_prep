# rt_sigqueueinfo(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | rt_sigqueueinfo 129 / 178 / 138 / 178; rt_tgsigqueueinfo 297 / 335 / 240 / 363 |
| Since (kernel) | rt_sigqueueinfo 2.2; rt_tgsigqueueinfo 2.6.31 |
| Man page | man2/rt_sigqueueinfo.2 (man-pages 6.19 HTML set, fetched 2026-10-17) -- one page covers both calls |
| glibc wrapper | none for the raw calls ("There are no glibc wrappers for these system calls", rt_sigqueueinfo.2 SYNOPSIS); userspace reaches them via sigqueue(3)/pthread_sigqueue(3) (rt_sigqueueinfo.2, DESCRIPTION) |
| Aliases covered | rt_tgsigqueueinfo (SC-rt_tgsigqueueinfo, "covered" per ledger) |
| Ledger ID | SC-rt_sigqueueinfo |

## Purpose

rt_sigqueueinfo() and rt_tgsigqueueinfo() are the low-level "send a signal plus data" interfaces: they queue `sig` with a caller-supplied `siginfo_t` to the thread group `tgid` (rt_sigqueueinfo) or to the specific thread `tid` within `tgid` (rt_tgsigqueueinfo) (rt_sigqueueinfo.2, DESCRIPTION). The receiver reads the payload in an SA_SIGINFO handler installed with [sigaction](rt_sigaction.md). They exist to implement sigqueue(3) and pthread_sigqueue(3) and are explicitly not intended for direct application use (rt_sigqueueinfo.2, DESCRIPTION).

## Synopsis

```c
#include <linux/signal.h>   /* SI_* constants */
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_rt_sigqueueinfo, pid_t tgid, int sig, siginfo_t *info);
int syscall(SYS_rt_tgsigqueueinfo, pid_t tgid, pid_t tid,
            int sig, siginfo_t *info);
```

## Arguments and behavior

`tgid` (and `tid` for the *tg variant) select the target; `sig` is the signal number; `info` is the payload. The kernel does not trust the payload: `info->si_code` must be negative (user-originated, e.g. SI_QUEUE (-1), SI_MESGQ (-3), SI_ASYNCIO (-4), SI_TKILL (-6) -- constants from <linux/signal.h>) or the call fails with EPERM; likewise a `tgid` other than the caller with an invalid `si_code` is EPERM (rt_sigqueueinfo.2, ERRORS). The kernel also overwrites `si_pid`/`si_uid` with the sender's identity, so the receiver can trust them the same way it does for kill(2)-sent signals (rt_sigqueueinfo.2, DESCRIPTION/NOTES).

## Return value and errors

0 on success; -1 with errno (rt_sigqueueinfo.2, RETURN VALUE). Errors: EAGAIN (the RLIMIT_SIGPENDING queue limit for real-time signals is reached -- see signal(7)), EINVAL (`sig`, `tgid` or `tid` invalid), EPERM (no permission to signal the target, per the kill(2) rules; or invalid si_code), ESRCH (no matching thread group / thread) (rt_sigqueueinfo.2, ERRORS).

## Flags and constants

SI_* si_code constants from <linux/signal.h> (SI_USER 0, SI_QUEUE -1, SI_TIMER -2, SI_MESGQ -3, SI_ASYNCIO -4, SI_TKILL -6); only negative codes are accepted from userspace.

## Security and notes

The si_code check is the security boundary: a process can never forge a kernel-generated siginfo (positive si_code) such as SIGSEGV's fault address, and cannot forge the sender identity. The distinction between the two calls mirrors [kill](kill.md) vs [tgkill](tkill.md): process-directed vs thread-directed, with the same tid-recycling caveat that motivated rt_tgsigqueueinfo to take both IDs. EAGAIN on queue exhaustion is the real-time-signal-only failure (SIGRTMIN..SIGRTMAX are queueable; standard signals are coalesced). Cross-reference: [rt_sigaction](rt_sigaction.md), [kill](kill.md), [tkill](tkill.md), [sigtimedwait](sigtimedwait.md), [pidfd_send_signal](../process/pidfd_send_signal.md).

## References

- https://man7.org/linux/man-pages/man2/rt_sigqueueinfo.2.html
- man-pages syscalls(2) version table (2.2, 2.6.31)
- /usr/include/linux/signal.h (SI_* constants)
