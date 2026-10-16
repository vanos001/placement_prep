# tgkill(2) / tkill(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | tgkill 234 / 270 / 131 / 268; tkill 200 / 238 / 130 / 238 |
| Since (kernel) | 2.6 (both; syscalls(2) table) |
| Man page | man2/tgkill.2 (man-pages 6.19 HTML set, fetched 2026-10-17) -- one page covers tgkill and tkill |
| glibc wrapper | tgkill(3) W @@GLIBC_2.30 (nm -D, glibc 2.41); tkill has no wrapper ("Avoid using this system call", tgkill.2 DESCRIPTION) |
| Aliases covered | tkill (SC-tkill, grouped); tgkill is the primary (SC-tgkill) |
| Ledger ID | SC-tgkill |

## Purpose

tgkill() sends the signal `sig` to the thread with thread ID `tid` in thread group `tgid`; kill(2) can only signal a process as a whole, letting the kernel pick an arbitrary thread (tgkill.2, DESCRIPTION). tkill() is its obsolete predecessor that takes only `tid` -- vulnerable to signaling the wrong thread after tid recycling -- and the man page says flatly to avoid it (tgkill.2, DESCRIPTION). Both are raw interfaces meant for thread-library use (tgkill.2, DESCRIPTION).

## Synopsis

```c
/* tgkill(3) since glibc 2.30 */
#define _GNU_SOURCE
#include <signal.h>
int tgkill(int tgid, int tid, int sig);
/* raw tkill: syscall(SYS_tkill, int tid, int sig) */
```

## Arguments and behavior

tgkill() validates BOTH `tgid` and `tid`, which is exactly the fix for tkill()'s recycling hazard: a recycled tid in the wrong process now fails with ESRCH instead of signaling a stranger. POSIX thread IDs (pthread_self()) are not kernel tids -- the caller needs gettid(2) values, which is why the wrapper landed only in glibc 2.30 and pthread_kill(3) remains the portable spelling. The tkill(2) raw form takes (tid, sig) only (tgkill.2, DESCRIPTION/SYNOPSIS).

## Return value and errors

0 on success; -1 with errno (tgkill.2, RETURN VALUE). Errors: EAGAIN (RLIMIT_SIGPENDING reached, or insufficient kernel memory, for a real-time signal), EINVAL (invalid thread ID, thread group ID, or signal), EPERM (permission denied, per the kill(2) rules), ESRCH (no thread with the specified tid in the specified tgid) (tgkill.2, ERRORS).

## Flags and constants

None.

## Security and notes

Permission model identical to kill(2) (CAP_KILL or same-uid/target-ns rules). The (tgid, tid) pair is also why pthread_kill(3) can be implemented safely: the C library tracks both numbers per thread. Signal-directed-vs-process-directed delivery semantics (sigpending visibility, handler runs in the targeted thread) are the interview core here; see signal(7) for the model. Cross-reference: [kill](kill.md), [rt_sigqueueinfo](rt_sigqueueinfo.md), [pidfd_send_signal](../process/pidfd_send_signal.md), [rt_sigaction](rt_sigaction.md).

## References

- https://man7.org/linux/man-pages/man2/tgkill.2.html
- man-pages syscalls(2) version table (2.6)
- worklog: wrapper symbol tgkill W @@GLIBC_2.30 verified with nm -D against glibc 2.41 (2026-10-17)
