# connect(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 42 / 362 / 203 / 283 (hub + cached tables) |
| Since (kernel) | 2.0 (hub; AF_UNSPEC dissociation since 2.2, connect.2) |
| Man page | man2/connect.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | yes, standard libc wrapper |
| Aliases covered | none |
| Ledger ID | SC-connect |

## Purpose

connect() connects the socket `sockfd` to the address `addr`
(`addrlen` bytes). For SOCK_STREAM/SOCK_SEQPACKET it performs the
client side of connection establishment; for SOCK_DGRAM it fixes the
default destination -- and the only accepted source -- of datagrams.
The address format is determined by the socket's family
([socket](socket.md)).

## Synopsis

```c
#include <sys/socket.h>
int connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
```

## Arguments and behavior

Stream/seqpacket sockets attempt a connection to the socket bound at
`addr`. UNIX stream sockets may connect only once; datagram sockets
(UNIX and Internet) may reconnect repeatedly to change the
association; and since Linux 2.2, connecting to AF_UNSPEC dissolves
the association so the socket can be reconnected (connect.2). A
nonblocking stream connect that cannot complete immediately returns
EINPROGRESS; completion is awaited by selecting/polling for writability
and then reading the SO_ERROR option at level SOL_SOCKET with
[getsockopt](setsockopt.md) (0 = success). UNIX domain nonblocking
sockets report EAGAIN instead of EINPROGRESS.

## Return value and errors

Zero on success; -1 with errno. General socket errors (connect.2;
domain-specific ones may follow): EACCES/EPERM (broadcast without
SO_BROADCAST; firewall or SELinux policy), EADDRINUSE, EADDRNOTAVAIL
(ephemeral-port exhaustion), EAFNOSUPPORT, EAGAIN, EALREADY (previous
attempt in flight), EBADF, ECONNREFUSED (nothing listening), EFAULT,
EINPROGRESS, EINTR, EISCONN, ENETUNREACH, ENOTSOCK, EPROTOTYPE,
ETIMEDOUT (may be long with syncookies enabled).

## Flags and constants

No flags argument. AF_UNSPEC (0) is the "dissociate" address family
since kernel 2.2 (connect.2).

## Security and notes

After a failed connect() the socket state is unspecified: close it and
create a new socket rather than retrying on the same one (connect.2
NOTES). EINTR on TCP does not abort the handshake -- the connection
completes asynchronously (roff comment in connect.2). The same
ephemeral-port exhaustion that hits bind() also surfaces here as
EADDRNOTAVAIL.

## References

- Cached man page: source-cache/man-pages-sparse/man2/connect.2.
- Numbers: hub overview.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- Hub row: [overview](overview.md).
