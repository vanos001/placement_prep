# setsockopt(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | setsockopt 54 / 366 / 208 / 294; getsockopt 55 / 365 / 209 / 295 (ledger SC-rows + cached tables) |
| Since (kernel) | 2.0 (hub) |
| Man page | man2/getsockopt.2 (cached roff, dated 2021-03-22; setsockopt.2 is a .so alias) |
| glibc wrapper | yes, standard libc wrappers |
| Aliases covered | getsockopt (SC-getsockopt, canonical page is getsockopt.2) |
| Ledger ID | SC-setsockopt |

## Purpose

setsockopt()/getsockopt() manipulate options for the socket `sockfd`.
Options exist at multiple protocol levels: `level` = SOL_SOCKET for
the generic socket layer, otherwise the protocol number of the
protocol that owns the option (e.g. IPPROTO_TCP for TCP options).
optname/optval are passed uninterpreted to the protocol module.

## Synopsis

```c
#include <sys/socket.h>
int setsockopt(int sockfd, int level, int optname,
               const void *optval, socklen_t optlen);
int getsockopt(int sockfd, int level, int optname,
               void *restrict optval, socklen_t *restrict optlen);
```

## Arguments and behavior

For setsockopt, `optval`/`optlen` supply the value; most socket-level
options take an int (nonzero enables a boolean option). For
getsockopt, `optlen` is value-result: in -- buffer size, out -- actual
size of the returned value; optval may be NULL when no value is
wanted. The full SO_* option list is documented in socket(7), not in
the getsockopt.2 page, which was deliberately slimmed in 1999 (roff
history note); per-protocol options live in ip(7), tcp(7), udp(7),
unix(7), packet(7).

SO_* groups overview (pointers, values not restated here):

| Group | Examples | Owner page |
|---|---|---|
| generic socket | SO_REUSEADDR, SO_KEEPALIVE, SO_SNDBUF/RCVBUF, SO_ERROR, SO_TYPE, SO_PASSCRED | socket(7) |
| buffer/timeout | SO_SNDLOWAT/RCVLOWAT, SO_SNDTIMEO/RCVTIMEO (non-POSIX on Linux) | socket(7) |
| TCP | TCP_NODELAY, TCP_CORK, TCP_KEEPALIVE* | tcp(7) |
| IP | IP_TTL, IP_RECVERR, IP_ADD_MEMBERSHIP | ip(7) |
| UNIX | SO_SNDBUFFORCE-style limits, SO_PEERCRED | unix(7) |

## Return value and errors

Zero on success for standard options; -1 with errno: EBADF, EFAULT
(optval/optlen outside the address space), EINVAL (bad optlen in
setsockopt; some invalid optval values), ENOPROTOOPT (option unknown
at that level), ENOTSOCK. Netfilter custom socket options return the
handler's value on success (getsockopt.2 RETURN VALUE).

## Flags and constants

SOL_SOCKET is the socket-layer level; SO_DEBUG = 1 upward in
bits/socket-constants.h / asm/socket.h (values intentionally not
duplicated here -- socket(7) owns them).

## Security and notes

SO_ERROR is the documented way to finish a nonblocking
[connect](connect.md): poll for writability, then read SO_ERROR at
SOL_SOCKET. SO_PASSCRED enables receiving SCM_CREDENTIALS control
messages (see [sendmsg](sendmsg.md)). The man page BUGS note says
several socket options should be handled at lower levels of the
system.

## References

- Cached man page: source-cache/man-pages-sparse/man2/getsockopt.2 (setsockopt.2 .so).
- Numbers: ledger.md SC-rows; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- Hub rows: [overview](overview.md) (getsockopt row covers both calls).
