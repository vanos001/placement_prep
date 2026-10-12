# poll(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | poll 7 / 168 / - / 168; ppoll 271 / 309(time32) / 73 / 336(time32); ppoll_time64 414 (i386 + arm32) (hub + cached tables) |
| Since (kernel) | poll: 2.0.36 per hub/syscalls(2) vs 2.1.23 per poll.2 VERSIONS (both recorded; worklog 1-g conflict). ppoll 2.6.16 (poll.2). ppoll_time64 5.1 (tag probe, worklog 1-g) |
| Man page | man2/poll.2 (cached roff, dated 2021-03-22; ppoll.2 is a .so alias) |
| glibc wrapper | yes; glibc poll() emulates via select(2) on kernels lacking poll (poll.2); ppoll library call glibc 2.4 |
| Aliases covered | ppoll (SC-ppoll) + ppoll_time64 twin (SC-ppoll_time64) |
| Ledger ID | SC-poll |

## Purpose

poll() waits for one of a set of file descriptors to become ready to
perform I/O -- the fixed-size alternative to [select](select.md) and
the portable precursor of [epoll_wait](epoll_wait.md). ppoll() adds a
timespec timeout and an atomic sigmask swap, making it the poll
analogue of pselect (poll.2).

## Synopsis

```c
#include <poll.h>
int poll(struct pollfd *fds, nfds_t nfds, int timeout);
int ppoll(struct pollfd *fds, nfds_t nfds,
          const struct timespec *tmo_p, const sigset_t *sigmask);
```

## Arguments and behavior

fds is an array of `struct pollfd { int fd; short events; short
revents; }`. A negative fd is ignored (revents 0); events may be 0 to
only receive POLLHUP/POLLERR/POLLNVAL. timeout in milliseconds: -1
infinite, 0 immediate return. ppoll's tmo_p is a timespec (NULL =
infinite); a negative timespec is an EINVAL error for ppoll, unlike
poll's negative timeout (poll.2). With sigmask NULL, ppoll differs
from poll only in timeout precision; otherwise it atomically
sigprocmask(SIG_SETMASK)s, polls, and restores -- the pselect
race-window fix. The raw ppoll syscall mutates *tmo_p (glibc hides
this with a local copy) and takes a fifth argument sigsetsize.

## Return value and errors

Nonnegative count of fds with nonzero revents; 0 on timeout; -1 with
errno: EFAULT, EINTR, EINVAL (nfds exceeds RLIMIT_NOFILE; ppoll
negative timeout), ENOMEM. Linux returns ENOMEM where some systems
return EAGAIN; portable code loops on both (poll.2 NOTES).

## Flags and constants

| Bit | Since | Meaning |
|---|---|---|
| POLLIN | - | data to read |
| POLLPRI | - | exceptional condition (TCP OOB, pty packet mode, cgroup.events) |
| POLLOUT | - | writable (large writes may still block) |
| POLLRDHUP | 2.6.17 | stream peer closed/shut write half (_GNU_SOURCE) |
| POLLERR / POLLHUP / POLLNVAL | - | output-only in revents |

_XOPEN_SOURCE adds POLLRDNORM/POLLRDBAND/POLLWRNORM/POLLWRBAND
(synonyms); POLLMSG is known but unused (poll.2). O_NONBLOCK does not
affect poll/ppoll readiness semantics.

## Security and notes

Since conflict recorded per worklog 1-g: the hub/ledger carry 2.0.36
(syscalls(2) table) while poll.2 VERSIONS says "introduced in Linux
2.1.23" with glibc select-based emulation for older kernels. Closing
a monitored fd in another thread has unspecified effect (poll.2 ->
select.2). ppoll_time64 twin: i386/arm 414, added 5.1 (worklog 1-e
syscall_32.tbl v5.0/v5.1 probe); takes __kernel_timespec for 64-bit
tv_sec on 32-bit. The hub splits ppoll into ppoll.md; this task keeps
it here -- merge-time pointer decision.

## References

- Cached man page: source-cache/man-pages-sparse/man2/poll.2 (ppoll.2 .so).
- Numbers: hub overview.md, ledger.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- Worklog Tasks 1-e/1-g (time64 since-date probe; 2.0.36 vs 2.1.23 conflict).
