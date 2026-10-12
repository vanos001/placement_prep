# tgkill(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | tgkill: 234 / 270 / 131 / 268; tkill: 200 / 238 / 130 / 238 (ledger SC-tgkill, SC-tkill; both verified in cached syscall_64.tbl, syscall_32.tbl, syscall_generic.tbl, syscall_arm.tbl) |
| Since (kernel) | tkill 2.4.19 / 2.5.4; tgkill added in 2.5.75 (tkill.2 VERSIONS; worklog 1-e carries the same man-page dates; the ledger "Since 2.6" column is the stable-series rounding) |
| Man page | man2/tkill.2 (cached); tgkill.2 is an .so alias ("\.so man2/tkill.2") |
| glibc wrapper | tgkill(3): wrapper added to glibc in 2.30 (tkill.2 VERSIONS); before glibc 2.30 there was no wrapper either; tkill() has no glibc wrapper at all - syscall(2) is required (tkill.2) |
| Aliases covered | tkill (obsolete predecessor, documented on the same page) |
| Ledger ID | SC-tgkill, SC-tkill |

## Purpose

tgkill() sends the signal sig to the thread with thread ID tid inside thread group tgid. It exists because kill(2) can only address a process (thread group) as a whole, with delivery to an arbitrary thread in it; thread libraries need thread-directed delivery (tkill.2). tkill() is the obsolete predecessor that takes only tid, so a recycled thread ID can make it signal the wrong thread; the man page says "Avoid using this system call" (tkill.2).

## Synopsis

```c
#include <signal.h>
int tgkill(pid_t tgid, pid_t tid, int sig);
/* no glibc wrapper for tkill */
int syscall(SYS_tkill, pid_t tid, int sig);
```

## Arguments and behavior

tgid is the process (thread group) ID, tid the kernel thread ID within it (the values clone(2) and gettid(2) return; CLONE_THREAD defines thread groups, tkill.2 NOTES). The signal is directed at that thread only, regardless of the per-thread signal masks of its siblings; standard delivery rules then apply against the target thread's mask. These are raw syscall interfaces meant for internal thread-library use (tkill.2); the POSIX-facing entry is pthread_kill(3), which asynchronously directs a signal to a thread in the same process (pthread_kill.3, cached man3).

## Return value and errors

0 on success; -1 with errno on error (tkill.2). Errors: EAGAIN (RLIMIT_SIGPENDING reached, or insufficient kernel memory, for a real-time signal); EINVAL (invalid tid, tgid, or signal); EPERM (permission denied, same rules as kill(2)); ESRCH (no thread with that tid/tgid pair exists).

## Flags and constants

No flags. Signal numbers come from <signal.h> (bits/signum-arch.h on glibc x86_64: standard signals 1-31, __SIGRTMIN 32 to __SIGRTMAX 64).

## Security and notes

The tkill tid-reuse race is the reason tgkill exists: between reading a tid and calling tkill, the thread may die and the tid be reassigned, hitting an unrelated thread (tkill.2). Both calls are Linux-specific and should not be used in portable programs (tkill.2 CONFORMING TO).

## References

- https://man7.org/linux/man-pages/man2/tkill.2.html (covers tgkill via .so)
- worklog Task 1-e (tkill 2.4.19/2.5.4 and tgkill 2.5.75 dates, sourced from this page)
- [kill](kill.md), [overview](overview.md)
