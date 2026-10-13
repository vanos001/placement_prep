# select(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | select 23 / 142(_newselect) / - / 142(_newselect); pselect6 270 / 308 / 72 / 335; pselect6_time64 413 (i386 + arm32); i386 82 is the oldselect slot (hub + ledger + cached tables) |
| Since (kernel) | 2.0 (hub) |
| Man page | man2/select.2 (cached roff, dated 2021-03-22); pselect6.2, pselect.2, _newselect.2 are .so aliases of select.2 |
| glibc wrapper | yes; pselect needs _POSIX_C_SOURCE >= 200112L; glibc pselect maps to the pselect6 syscall with wrapper differences (below) |
| Aliases covered | pselect6 (SC-pselect6), _newselect (SC-_newselect), oldselect slot note; pselect6_time64 twin (SC-pselect6_time64) |
| Ledger ID | SC-select |

## Purpose

select() monitors up to `nfds` file descriptors in three fd_set
classes -- readable, writable, exceptional -- until one is ready, a
signal arrives, or `timeout` expires. pselect() adds nanosecond
precision and an atomically swapped sigmask, closing the
signal-vs-fd race. WARNING from select.2: fds must be below
FD_SETSIZE (1024), "an unreasonably low limit" that will not change;
use [poll](poll.md) or [epoll_wait](epoll_wait.md) instead.

## Synopsis

```c
#include <sys/select.h>
int select(int nfds, fd_set *restrict readfds,
           fd_set *restrict writefds, fd_set *restrict exceptfds,
           struct timeval *restrict timeout);
int pselect(int nfds, fd_set *restrict readfds,
            fd_set *restrict writefds, fd_set *restrict exceptfds,
            const struct timespec *restrict timeout,
            const sigset_t *restrict sigmask);
```

## Arguments and behavior

The sets are manipulated with FD_ZERO/FD_SET/FD_CLR/FD_ISSET and are
value-result: select() modifies them in place, so a loop must
reinitialize them each call. nfds is the highest fd number plus 1.
timeout is a struct timeval; NULL means infinite, both fields zero
means pure poll. Linux modifies `timeout` to the time not slept (even
on EINTR) -- do not rely on it; the glibc pselect wrapper hides the
kernel-side mutation with a local copy. pselect6 kernel ABI: the last
argument is not sigset_t* but a struct { const kernel_sigset_t *ss;
size_t ss_len; } so pointer and size fit in one slot (select.2).

## Return value and errors

Count of ready fds across the three sets (0 on timeout); -1 with
errno and the sets unmodified: EBADF (invalid fd in a set; see BUGS),
EINTR, EINVAL (nfds negative or above RLIMIT_NOFILE; bad timeout
value), ENOMEM.

## Flags and constants

FD_SETSIZE is fixed at 1024 in glibc (kernel imposes no such limit);
FD_SET/FD_CLR beyond it is undefined behavior. Kernel notification
mapping (fs/select.c via select.2): read = EPOLLRDNORM|EPOLLRDBAND|
EPOLLIN|EPOLLHUP|EPOLLERR; write = EPOLLWRBAND|EPOLLWRNORM|EPOLLOUT|
EPOLLERR; except = EPOLLPRI.

## Security and notes

Numbering honesty (worklog 1-g): the modern i386 select is the
_newselect syscall (142, kernel name sys_select; ledger
SC-_newselect researched; _newselect.2 is a .so alias); ledger
SC-select's i386 82 is sys_old_select, the legacy slot, and x64 has
plain select 23; oldselect has no SC-row of its own (ledger
correction note). glibc history (select.2): 2.0 shipped a broken
pselect without sigmask; 2.1-2.2.1 needed _GNU_SOURCE; the
2.1-era sigprocmask+select emulation kept the race pselect was
meant to fix -- modern glibc uses the pselect6 syscall (kernel
2.6.16+). musl 1.2.5 (src/select/select.c, worklog 1-g) is
time64-first: it dispatches to SYS_pselect6_time64 (413) and falls
back to SYS_select only for small timeouts on old kernels. Spurious
readiness and other-thread close pitfalls: Linux may report a
socket readable yet a later read can still block -- use O_NONBLOCK
(select.2 BUGS/NOTES).

## References

- Cached man page: source-cache/man-pages-sparse/man2/select.2 (pselect6.2/pselect.2/_newselect.2 .so).
- Numbers: hub overview.md, ledger.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- musl dispatch: source-cache/musl-clone/musl/src/select/select.c (worklog 1-g).
- Worklog Task 1-g (_newselect/oldselect slot disambiguation).
