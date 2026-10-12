# waitid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 247 / 284 / 95 / 280 |
| Since (kernel) | 2.6.10 (hub/ledger; wait.2 text says "available since Linux 2.6.9" - discrepancy recorded); P_PIDFD since 5.4 |
| Man page | man2/wait.2 documents waitid (waitid.2 is a .so alias of wait.2, verified in cache) |
| glibc wrapper | waitid(3), symbol version GLIBC_2.2.5 on installed glibc 2.41 (nm -D); raw syscall takes a fifth rusage argument (wait.2, C library/kernel differences) |
| Aliases covered | none (this page; waitpid/wait3/wait4 live on [wait4](wait4.md)) |
| Ledger ID | SC-waitid |

## Purpose

waitid() waits for state changes of selected children and reports the outcome through a siginfo_t structure instead of an encoded int, giving finer selection (exit/stop/continue separately) than waitpid. It is the POSIX-preferred wait interface and the one that works with pidfds.

## Synopsis

```c
#include <sys/wait.h>
int waitid(idtype_t idtype, id_t id, siginfo_t *infop, int options);
/* raw syscall: int waitid(idtype_t, id_t, siginfo_t *, int, struct rusage *) */
```

## Arguments and behavior

idtype/id select the children (values from /usr/include/linux/wait.h): P_PID (1) the child with PID id; P_PIDFD (3, since 5.4) the child referred to by the pidfd id; P_PGID (2) any child whose process group ID matches id (id 0 means the caller's group since 5.4); P_ALL (0) any child, id ignored. options is an OR of WEXITED (0x4), WSTOPPED (0x2), WCONTINUED (0x8) plus modifiers WNOHANG (0x1) and WNOWAIT (0x01000000, leave the child waitable). On success the kernel fills si_pid, si_uid (real UID of the child; not set on most other implementations), si_signo (SIGCHLD), si_status (exit status or the stop/continue/kill signal), and si_code, one of CLD_EXITED, CLD_KILLED, CLD_DUMPED, CLD_STOPPED, CLD_TRAPPED, CLD_CONTINUED (wait.2). With WNOHANG and no waitable child, 0 is returned and si_pid/si_signo are zeroed on implementations following POSIX.1-2008 TC1 (2013).

## Return value and errors

Returns 0 on success (including WNOHANG with nothing to report); -1 with errno on failure (wait.2):

| Error | Meaning |
|---|---|
| EAGAIN | P_PIDFD pidfd is nonblocking (PIDFD_NONBLOCK) and the process has not terminated |
| ECHILD | Selected child does not exist or is not a child of the caller |
| EINTR | WNOHANG not set and a signal was caught |
| EINVAL | Invalid options or idtype combination |

## Flags and constants

| Constant | Value | Source |
|---|---|---|
| P_ALL / P_PID / P_PGID / P_PIDFD | 0 / 1 / 2 / 3 | /usr/include/linux/wait.h |
| WEXITED / WSTOPPED / WCONTINUED / WNOHANG / WNOWAIT | 0x4 / 0x2 / 0x8 / 0x1 / 0x01000000 | /usr/include/linux/wait.h; bits/waitflags.h |
| PIDFD_NONBLOCK | O_NONBLOCK | /usr/include/linux/pidfd.h |

## Security and notes

Linux-specific bug: if infop is NULL, waitid succeeds and returns the waited child's PID - nonstandard, do not rely on it (wait.2, BUGS). Since 4.7 the Linux-only __WALL/__WCLONE/__WNOTHREAD options are also accepted by waitid (wait.2, Linux notes). A pidfd obtained via pidfd_open(2) on a child can be waited on here; the EAGAIN path pairs with PIDFD_NONBLOCK. Cross-reference: [wait4](wait4.md), [pidfd_open](pidfd_open.md), [_exit](_exit.md).

## References

- https://man7.org/linux/man-pages/man2/wait.2.html (waitid.2 is its .so alias)
- kernel/exit.c (source file named in worklog 1-a)
- /usr/include/linux/wait.h, /usr/include/linux/pidfd.h
