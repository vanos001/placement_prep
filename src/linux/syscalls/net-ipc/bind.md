# bind(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 49 / 361 / 200 / 282 (hub + cached tables) |
| Since (kernel) | 2.0 (hub) |
| Man page | man2/bind.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | yes, standard libc wrapper; on i386 historically reached through socketcall (see [socketcall](socketcall.md)) |
| Aliases covered | none |
| Ledger ID | SC-bind |

## Purpose

bind() assigns the address `addr` (of length `addrlen`) to the socket
referred to by `sockfd`. A freshly created socket (see
[socket](socket.md)) exists in a name space but has no address; bind
fixes one. It is normally required before a SOCK_STREAM socket can
receive connections ([listen](listen.md) + [accept](accept.md)). The
binding rules differ per address family; the man page defers to ip(7),
ipv6(7), unix(7), ddp(7), packet(7), x25(7), netlink(7).

## Synopsis

```c
#include <sys/socket.h>
int bind(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
```

## Arguments and behavior

`addr` points to an address structure; the generic `struct sockaddr {
sa_family_t sa_family; char sa_data[14]; }` exists only so the pointer
can be cast without warnings (bind.2). The real layout is
family-specific, e.g. sockaddr_in for AF_INET and sockaddr_un for
AF_UNIX. `addrlen` is the size in bytes of that structure. Binding is
normally mandatory for listening sockets; for clients it is optional
(the kernel picks an ephemeral port).

## Return value and errors

Zero on success; -1 with errno on failure (bind.2):

| Error | Meaning |
|---|---|
| EACCES | address protected and user is not superuser (e.g. privileged port) |
| EADDRINUSE | address already in use; or (Internet) all ephemeral ports exhausted (ip_local_port_range) |
| EBADF | sockfd not a valid fd |
| EINVAL | socket already bound; or addrlen wrong / addr invalid for the domain |
| ENOTSOCK | sockfd does not refer to a socket |

AF_UNIX-specific: EACCES (path prefix search denied), EADDRNOTAVAIL,
EFAULT, ELOOP, ENAMETOOLONG, ENOENT, ENOMEM, ENOTDIR, EROFS.

## Flags and constants

None; bind takes no flags. The address family constants (AF_*) come
from [socket](socket.md).

## Security and notes

Binding a UNIX pathname creates a filesystem inode that must be
unlink(2)ed later (bind.2 example). Binding port 0 requests an
ephemeral port from /proc/sys/net/ipv4/ip_local_port_range; on
exhaustion EADDRINUSE or EAGAIN is reported (see also
[connect](connect.md), [sendto](sendto.md)). The transparent proxy
options are not documented by the man page (bind.2 BUGS). socklen_t
background is on the [accept](accept.md) page.

## References

- Cached man page: source-cache/man-pages-sparse/man2/bind.2.
- Numbers: hub overview.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- Hub row: [overview](overview.md).
