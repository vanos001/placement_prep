# listen(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 50 / 363 / 201 / 284 (hub + cached tables) |
| Since (kernel) | 2.0 (hub) |
| Man page | man2/listen.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | yes, standard libc wrapper |
| Aliases covered | none |
| Ledger ID | SC-listen |

## Purpose

listen() marks the socket `sockfd` as passive: a socket that will be
used to accept incoming connection requests with [accept](accept.md).
It applies to SOCK_STREAM and SOCK_SEQPACKET sockets (listen.2). The
server sequence is socket -> bind -> listen -> accept (listen.2 NOTES).

## Synopsis

```c
#include <sys/socket.h>
int listen(int sockfd, int backlog);
```

## Arguments and behavior

`backlog` defines the maximum length of the queue of pending
connections for `sockfd`. If a request arrives when the queue is full
the client may receive ECONNREFUSED, or -- if the protocol supports
retransmission -- the request is ignored so a later retry succeeds.

Backlog semantics changed with Linux 2.2: it now limits the queue of
*completely established* sockets waiting to be accepted, not the
incomplete connection requests; the SYN-queue length is set via
/proc/sys/net/ipv4/tcp_max_syn_backlog, and with syncookies enabled
there is no logical maximum (listen.2 NOTES, tcp(7)).

## Return value and errors

Zero on success; -1 with errno (listen.2): EADDRINUSE (another socket
already listening on the same port; or, if the socket was never bound,
all ephemeral ports exhausted), EBADF, ENOTSOCK, EOPNOTSUPP (socket
type does not support listen).

## Flags and constants

None. The historical SOMAXCONN constant (128) is now only the
pre-5.4 default of the sysctl described below.

## Security and notes

If `backlog` exceeds /proc/sys/net/core/somaxconn it is silently
capped; since Linux 5.4 that file defaults to 4096, earlier kernels to
128, and before 2.4.25 the cap was hard-coded (listen.2). The cap is
silent, so oversized values are not an error. Portability warning from
the man page: BSD-derived systems historically capped the backlog at
5. Accept-readiness race: a readiness event (select/poll/epoll) does
not guarantee a connection is still pending; see [accept](accept.md).

## References

- Cached man page: source-cache/man-pages-sparse/man2/listen.2.
- Numbers: hub overview.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- Hub row: [overview](overview.md).
