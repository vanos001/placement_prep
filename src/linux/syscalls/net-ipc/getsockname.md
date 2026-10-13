# getsockname(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | getsockname 51 / 367 / 204 / 286; getpeername 52 / 368 / 205 / 287 (hub) |
| Since (kernel) | 2.0 (hub; both named syscalls since 2.0 on the x64 slot list; on i386 reached via socketcall, see [ipc](ipc.md)-style multiplexers and [socketcall](socketcall.md)) |
| Man page | man2/getsockname.2 and man2/getpeername.2 (both cached, dated 2021-03-22; two separate man pages, one page here per family) |
| glibc wrapper | yes for both, in libc (header <sys/socket.h>) |
| Aliases covered | getpeername (SC-getpeername, grouped per ledger) |
| Ledger ID | SC-getsockname |

## Purpose

getsockname() returns the current local address of socket `sockfd`:
after bind(2) ([bind](bind.md)) with port 0 the ephemeral port is only
discoverable through this call; on a listening socket the address is
the one accept(2) would see locally. getpeername() returns the address
of the peer connected to `sockfd` (getsockname.2, getpeername.2).

## Synopsis

```c
#include <sys/socket.h>
int getsockname(int sockfd, struct sockaddr *restrict addr,
                socklen_t *restrict addrlen);
int getpeername(int sockfd, struct sockaddr *restrict addr,
                socklen_t *restrict addrlen);
```

## Arguments and behavior

`addr` receives the socket address; `addrlen` must be initialized to
the buffer size and is updated to the actual size on return. If the
buffer is too small the address is truncated and `addrlen` returns a
value greater than what was supplied (both man pages). For getpeername
on stream sockets, either side may call it after connect(2)
([connect](connect.md)); datagram sockets are connectionless, so a
"peer" exists only after connect was used on the datagram socket.

## Return value and errors

0 on success; -1 with `errno`: `EBADF` (not a valid descriptor),
`EFAULT` (addr outside the address space), `EINVAL` (addrlen invalid,
e.g. negative), `ENOBUFS` (insufficient system resources), `ENOTSOCK`
(not a socket); getpeername additionally `ENOTCONN` (socket not
connected). Both conform to POSIX.1-2001/2008, SVr4, 4.4BSD (4.2BSD
origin).

## Flags and constants

None (no flags argument).

## Security and notes

- On i386 neither name is a direct syscall: glibc routes through
  socketcall with SYS_GETSOCKNAME (6) and SYS_GETPEERNAME (7) from
  <linux/net.h> (worklog 1-g verified the SYS_* table).
- Truncation without error means callers should re-check `addrlen`
  against the buffer they passed; socklen_t background is in
  accept(2) (man NOTES).

## References

- Cached man pages: source-cache/man-pages-sparse/man2/getsockname.2,
  man2/getpeername.2.
- SYS_* values: /usr/include/linux/net.h (worklog 1-g).
- Numbers/Since: hub [overview](overview.md); ledger SC-getsockname,
  SC-getpeername.
