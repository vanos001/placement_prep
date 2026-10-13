# socket(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 41 / 359 / 198 / 281 (hub + cached tables) |
| Since (kernel) | 2.0 (hub; socket.2 dates the API to 4.2BSD) |
| Man page | man2/socket.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | yes, standard libc wrapper (socket.2); no version note needed |
| Aliases covered | socketpair (SC-socketpair), documented inline per task 3-f scope; hub/ledger point SC-socketpair at socketpair.md -- merge-time pointer decision needed |
| Ledger ID | SC-socket |

## Purpose

socket() creates an endpoint for communication and returns a file descriptor
referring to it; the descriptor is the lowest-numbered one not currently
open. The `domain` argument selects the protocol family (address family),
`type` the communication semantics, and `protocol` a specific protocol
within the family (0 when only one exists). It is the entry point of the
whole socket family documented in this directory: [bind](bind.md),
[listen](listen.md), [accept](accept.md), [connect](connect.md),
[sendto](sendto.md), [sendmsg](sendmsg.md), [setsockopt](setsockopt.md),
[shutdown](shutdown.md).

## Synopsis

```c
#include <sys/socket.h>
int socket(int domain, int type, int protocol);
```

## Arguments and behavior

`domain` selects the protocol family; the families the kernel understands
are listed in socket.2 and address_families(7). Brief table (socket.2):

| Family | Purpose |
|---|---|
| AF_UNIX / AF_LOCAL | local communication (unix(7)) |
| AF_INET / AF_INET6 | IPv4 / IPv6 Internet protocols |
| AF_NETLINK | kernel/userland interface (netlink(7)) |
| AF_PACKET | low-level packet interface |
| AF_VSOCK, AF_XDP, AF_ALG, AF_CAN, AF_TIPC, AF_BLUETOOTH | hypervisor, fast data path, kernel crypto, CAN bus, cluster, Bluetooth |
| AF_KEY, AF_RDS, AF_PPPOX, AF_LLC, AF_IB, AF_MPLS, AF_KCM | IPsec keys, RDS, PPP tunnels, LLC, InfiniBand, MPLS, KCM |

`type` values (bits/socket_type.h values verified):

| Type | Value | Meaning |
|---|---|---|
| SOCK_STREAM | 1 | sequenced reliable two-way byte stream |
| SOCK_DGRAM | 2 | connectionless fixed-max-length datagrams |
| SOCK_RAW | 3 | raw network protocol access |
| SOCK_RDM | 4 | reliable datagrams, no ordering guarantee |
| SOCK_SEQPACKET | 5 | reliable connection-based fixed-length records |
| SOCK_DCCP | 6 | Datagram Congestion Control Protocol |
| SOCK_PACKET | 10 | obsolete; use packet(7) |

Since Linux 2.6.27 `type` may additionally OR SOCK_NONBLOCK (sets
O_NONBLOCK on the open file description) and SOCK_CLOEXEC (sets
FD_CLOEXEC) -- both Linux-specific (socket.2 CONFORMING TO). Not every
family implements every type. SOCK_STREAM sockets must be connected
(connect(2)) before data transfer; SOCK_DGRAM/SOCK_RAW send via
sendto(2) and receive via recvfrom(2). SIGPIPE is raised on a broken
stream unless MSG_NOSIGNAL is used.

## Return value and errors

New fd on success; -1 with errno on failure (socket.2): EACCES
(permission denied for type/protocol), EAFNOSUPPORT, EINVAL (unknown
protocol; invalid flags in type since 2.6.27), EMFILE, ENFILE,
ENOBUFS/ENOMEM, EPROTONOSUPPORT; protocol modules may add more.

## Flags and constants

SOCK_NONBLOCK = 04000 octal, SOCK_CLOEXEC = 02000000 octal
(/usr/include/x86_64-linux-gnu/bits/socket_type.h). Both are
Linux-specific additions to `type`.

## Security and notes

socketpair(2) (SC-socketpair, man2/socketpair.2, 2021-03-22) creates an
unnamed connected pair in one call: on Linux only AF_UNIX/AF_LOCAL and
AF_TIPC (since 4.12) are supported domains, SOCK_NONBLOCK/SOCK_CLOEXEC
are accepted since 2.6.27, errors are EAFNOSUPPORT, EFAULT, EMFILE,
ENFILE, EOPNOTSUPP, EPROTONOSUPPORT, and `sv` is left unchanged on
failure (POSIX.1-2008 TC2 requirement). Socket options are set with
[setsockopt](setsockopt.md); a pending network error surfaces on the
next socket operation (per-socket error queue via IP_RECVERR, ip(7)).

## References

- Cached man page: source-cache/man-pages-sparse/man2/socket.2, socketpair.2.
- Constants: /usr/include/x86_64-linux-gnu/bits/socket_type.h, bits/socket.h.
- Numbers: hub overview.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- Worklog Task 1-g (AF_UNIX/AF_TIPC socketpair domain restriction).
