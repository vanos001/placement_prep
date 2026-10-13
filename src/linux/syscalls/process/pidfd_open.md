# pidfd_open(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 434 / 434 / 434 / 434 |
| Since (kernel) | 5.3 (pidfd_open.2 VERSIONS) |
| Man page | man2/pidfd_open.2 (cached roff, dated 2021-08-27); no aliases |
| glibc wrapper | pidfd_open(3), symbol version GLIBC_2.36 (nm -D on installed glibc 2.41; the cached man page still carries the older "glibc provides no wrapper" note) |
| Aliases covered | none (pidfd_send_signal / pidfd_getfd are separate pages) |
| Ledger ID | SC-pidfd_open |

## Purpose

pidfd_open() creates a file descriptor referring to the process (or thread-group leader) with the given PID. Unlike a raw PID, a pidfd is race-free against PID reuse: polling it reports process exit, and it can be passed to pidfd_send_signal(2), waitid(2) (P_PIDFD), pidfd_getfd(2), setns(2), and process_madvise(2) (pidfd_open.2, use cases).

## Synopsis

```c
#include <sys/syscall.h>
int syscall(SYS_pidfd_open, pid_t pid, unsigned int flags);
```

## Arguments and behavior

pid identifies the target process; flags must be 0 or PIDFD_NONBLOCK (since 5.10), which makes a later waitid(2) on this pidfd return EAGAIN instead of blocking if the process has not terminated (pidfd_open.2). The returned descriptor has close-on-exec set and is pollable: poll(2)/select(2)/epoll(7) report EPOLLIN when the process terminates; nothing can be read from it (read fails with EINVAL). For an existing process, pidfd_open is preferred over opening /proc/[pid], which requires procfs mounted and yields a non-pollable, non-waitable descriptor (pidfd_open.2, NOTES). To get a pidfd atomically at child creation, use clone(2)/clone3(2) with CLONE_PIDFD instead.

## Return value and errors

Success: a nonnegative file descriptor. Failure: -1 with errno (pidfd_open.2):

| Error | Meaning |
|---|---|
| EINVAL | flags or pid not valid |
| EMFILE / ENFILE | per-process / system-wide open-file limit reached |
| ENODEV | anonymous inode filesystem unavailable in this kernel |
| ENOMEM | kernel memory exhausted |
| ESRCH | process does not exist |

## Flags and constants

| Constant | Value | Source |
|---|---|---|
| PIDFD_NONBLOCK | O_NONBLOCK | /usr/include/linux/pidfd.h (since 5.10, pidfd_open.2) |
| PIDFD_THREAD | O_EXCL | /usr/include/linux/pidfd.h (newer header; pidfd_open.2 does not document it) |

## Security and notes

The man page guarantees the descriptor refers to the target even if it is already a zombie, provided SIGCHLD has not been set to SIG_IGN, SA_NOCLDWAIT is not in effect, and nobody reaped it meanwhile; otherwise use CLONE_PIDFD (pidfd_open.2, NOTES). pidfds are anonymous-inode fds, so they can be passed over unix sockets (SCM_RIGHTS) and kept across fork/exec like any descriptor. The newer PIDFD_THREAD flag (thread-granular pidfd) exists in the installed UAPI header but predates the cached man page; treat its semantics as unverified here. Cross-reference: [clone](clone.md), [pidfd_getfd](pidfd_getfd.md), [waitid](waitid.md).

## References

- https://man7.org/linux/man-pages/man2/pidfd_open.2.html
- kernel/pid.c, kernel/fork.c (source files named in worklog 1-a)
- /usr/include/linux/pidfd.h
