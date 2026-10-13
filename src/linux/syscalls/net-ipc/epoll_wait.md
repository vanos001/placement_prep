# epoll_wait(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | epoll_wait 232 / 256 / - / 252; epoll_pwait 281 / 319 / 22 / 346; epoll_pwait2 441 / 441 / 441 / 441 (ledger + cached tables; the hub row carries the pwait slots 281/319/22/346) |
| Since (kernel) | epoll_wait 2.6 (hub/ledger; man comment: 2.5.44); hub row Since "2.6.19" tracks epoll_pwait (2.6.19, epoll_wait.2); epoll_pwait2 5.11 (epoll_wait.2) |
| Man page | man2/epoll_wait.2 (cached roff, dated 2021-03-22; epoll_pwait.2 and epoll_pwait2.2 are .so aliases) |
| glibc wrapper | epoll_wait 2.3.2; epoll_pwait 2.6; epoll_pwait2 glibc 2.35 (cached man page has a FIXME on pwait2; nm: epoll_pwait2@@GLIBC_2.35 in glibc 2.41) |
| Aliases covered | epoll_pwait (SC-epoll_pwait), epoll_pwait2 (SC-epoll_pwait2); old-slot note for epoll_ctl_old (x64 214) and epoll_wait_old (x64 215) |
| Ledger ID | SC-epoll_wait |

## Purpose

epoll_wait() fetches ready events from the epoll instance `epfd`
created by [epoll_create](epoll_create.md): it fills `events` with up
to `maxevents` epoll_event records for descriptors in the interest
list that became ready. The pwait variants add an atomic sigmask swap
like pselect/ppoll; pwait2 upgrades the timeout to nanoseconds.

## Synopsis

```c
#include <sys/epoll.h>
int epoll_wait(int epfd, struct epoll_event *events,
               int maxevents, int timeout);
int epoll_pwait(int epfd, struct epoll_event *events,
                int maxevents, int timeout, const sigset_t *sigmask);
int epoll_pwait2(int epfd, struct epoll_event *events,
                 int maxevents, const struct timespec *timeout,
                 const sigset_t *sigmask);
```

## Arguments and behavior

timeout is milliseconds, measured against CLOCK_MONOTONIC: -1 blocks
indefinitely, 0 returns immediately. maxevents must be > 0. epoll_wait
blocks until an event, a signal, or timeout expiry. epoll_pwait()
equals atomically running sigprocmask(SIG_SETMASK, sigmask) around
epoll_wait; sigmask NULL reduces it to epoll_wait. epoll_pwait2 (5.11)
takes a timespec timeout like pselect/ppoll (NULL = infinite). The
raw pwait syscalls take a sixth argument sigsetsize = sizeof(kernel
sigset) which the glibc wrapper fixes (epoll_wait.2 C library/kernel
differences). Returned `data` fields are exactly what
[epoll_ctl](epoll_ctl.md) EPOLL_CTL_ADD/MOD stored.

## Return value and errors

Number of ready fds, 0 on timeout; -1 with errno: EBADF, EFAULT
(events not writable), EINTR, EINVAL (epfd not epoll; maxevents <= 0).

## Flags and constants

Event bits in returned `events` come from the epoll_ctl mask (EPOLLIN,
EPOLLOUT, EPOLLRDHUP, EPOLLPRI, EPOLLERR, EPOLLHUP); the four
input-only EPOLLET/EPOLLONESHOT/EPOLLWAKEUP/EPOLLEXCLUSIVE bits never
appear here.

## Security and notes

Round-robin fairness: with more than maxevents ready fds, successive
calls rotate through the ready set (epoll_wait.2 NOTES). Wait works
even with an empty interest list; another thread's ADD that turns
ready unblocks the waiter. Pre-2.6.37 kernels treat oversized
timeouts (> about LONG_MAX/HZ ms) as infinity (BUGS). Old slots
(worklog 1-g, verified empty implementation columns in the cached
syscall_64.tbl): x64 214 epoll_ctl_old and 215 epoll_wait_old were
allocated but never enabled and have no i386/generic/arm rows --
documented as researched in ledger/1-g. musl 1.2.5
(src/linux/epoll.c, worklog 1-g) calls SYS_epoll_pwait first and
falls back to SYS_epoll_wait only when sigs is NULL.

## References

- Cached man page: source-cache/man-pages-sparse/man2/epoll_wait.2 (pwait/pwait2 .so).
- Numbers: ledger.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl; hub overview.md.
- glibc symbols: nm -D libc.so.6 (glibc 2.41, worklog 3-f); cached man FIXME noted.
- Worklog Task 1-g (old slots verification; musl fallback).
