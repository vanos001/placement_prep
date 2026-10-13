# accept(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | accept 43 / - / 202 / 285; accept4 288 / 364 / 242 / 366 (hub + cached tables) |
| Since (kernel) | accept 2.0; accept4 2.6.28 (accept.2 VERSIONS) |
| Man page | man2/accept.2 (cached roff, dated 2021-08-27; accept4.2 is a .so alias) |
| glibc wrapper | accept4 in glibc since 2.10 (accept.2 VERSIONS; nm: accept4@@GLIBC_2.10) |
| Aliases covered | accept4 (SC-accept4, grouped per ledger) |
| Ledger ID | SC-accept |

## Purpose

accept() is used with connection-based socket types (SOCK_STREAM,
SOCK_SEQPACKET): it extracts the first pending connection request from
the queue of the listening socket `sockfd`, creates a new connected
socket, and returns a new fd for it. The new socket is not in the
listening state and `sockfd` is unaffected. accept4() is identical
when `flags` is 0 and adds the SOCK_* `flags` behavior.

## Synopsis

```c
#include <sys/socket.h>
int accept(int sockfd, struct sockaddr *restrict addr,
           socklen_t *restrict addr_len);
#define _GNU_SOURCE
#include <sys/socket.h>
int accept4(int sockfd, struct sockaddr *restrict addr,
            socklen_t *restrict addr_len, int flags);
```

## Arguments and behavior

`addr`/`addrlen` are a value-result pair: initialize `addrlen` to the
size of the buffer, and on return it holds the actual peer-address
size; a too-small buffer truncates the address and `addrlen` returns
the size that would have been needed. `addr` may be NULL (then
`addrlen` must also be NULL). With no pending connections, accept()
blocks unless the socket is nonblocking (O_NONBLOCK), in which case it
fails with EAGAIN/EWOULDBLOCK. Linux does NOT propagate file status
flags such as O_NONBLOCK/O_ASYNC from the listening socket to the new
socket -- this differs from canonical BSD, so set flags explicitly
(accept.2 NOTES). accept4 `flags`: SOCK_NONBLOCK, SOCK_CLOEXEC (same
meaning as on [socket](socket.md), accepted since 2.6.27 there and at
accept4 introduction here).

## Return value and errors

New fd on success; -1 with errno, `addrlen` unchanged on error.
Linux passes already-pending network errors on the new socket through
accept() -- unlike other BSD implementations -- so treat ENETDOWN,
EPROTO, ENOPROTOOPT, EHOSTDOWN, ENONET, EHOSTUNREACH, EOPNOTSUPP,
ENETUNREACH like EAGAIN and retry (accept.2 Error handling). Other
errors: EAGAIN/EWOULDBLOCK, EBADF, ECONNABORTED, EFAULT, EINTR,
EINVAL (not listening; negative addrlen; accept4 bad flags), EMFILE,
ENFILE, ENOBUFS/ENOMEM, ENOTSOCK, EPERM (firewall), EPROTO.

## Flags and constants

| Flag | Effect |
|---|---|
| SOCK_NONBLOCK | O_NONBLOCK on the new fd's open file description |
| SOCK_CLOEXEC | FD_CLOEXEC on the new fd |

## Security and notes

Numbering: i386 has no direct accept slot (hub shows "-"); 32-bit
code reached accept through socketcall SYS_ACCEPT 5 until Linux 4.3
added direct calls (socketcall.2 NOTES; ledger 1-g); accept4 has
i386 364. Readiness APIs (select/poll/epoll) only signal "maybe":
the connection can disappear before accept(), so keep O_NONBLOCK on
the listener to avoid blocking (accept.2 NOTES). socklen_t replaced
int*/size_t* through the POSIX.1g drafts (accept.2). Old slots: x64
214/215 are the never-enabled epoll_ctl_old/epoll_wait_old (see
[epoll_wait](epoll_wait.md)).

## References

- Cached man page: source-cache/man-pages-sparse/man2/accept.2 (accept4.2 .so).
- Numbers: hub overview.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- glibc symbol: nm -D libc.so.6 (glibc 2.41, worklog 3-f).
- Worklog Task 1-g (i386 socketcall routing, old slots).
