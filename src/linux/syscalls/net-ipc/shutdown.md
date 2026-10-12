# shutdown(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 48 / 373 / 210 / 293 (hub + cached tables) |
| Since (kernel) | 2.0 (hub) |
| Man page | man2/shutdown.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | yes, standard libc wrapper; SHUT_* in sys/socket.h since glibc 2.1.91 (shutdown.2 NOTES) |
| Aliases covered | none |
| Ledger ID | SC-shutdown |

## Purpose

shutdown() shuts down all or part of the full-duplex connection on the
socket associated with `sockfd`. Unlike close(2) it acts per direction
and affects the connection, not the descriptor: other processes
holding dups of the fd see the shutdown too.

## Synopsis

```c
#include <sys/socket.h>
int shutdown(int sockfd, int how);
```

## Arguments and behavior

| how | Constant | Effect |
|---|---|---|
| 0 | SHUT_RD | further receptions disallowed |
| 1 | SHUT_WR | further transmissions disallowed |
| 2 | SHUT_RDWR | further receptions and transmissions disallowed |

The constants have the values 0, 1, 2 and are defined in <sys/socket.h>
since glibc 2.1.91 (shutdown.2 NOTES). Typical TCP use: SHUT_WR to
send a FIN while still reading, letting the peer drain and respond.

## Return value and errors

Zero on success; -1 with errno (shutdown.2): EBADF, EINVAL (invalid
`how` -- but see BUGS note below), ENOTCONN (socket not connected),
ENOTSOCK.

## Flags and constants

SHUT_RD / SHUT_WR / SHUT_RDWR as in the table above; no bit flags
exist beyond the three `how` values.

## Security and notes

Validity checking of `how` is done in domain-specific code, and before
Linux 3.7 not all domains performed the checks -- most notably UNIX
domain sockets simply ignored invalid values; this was fixed for UNIX
domain (and DECnet) sockets in Linux 3.7 (shutdown.2 BUGS, with commit
fc61b928dc4d cited there). shutdown() does not free the fd; close(2)
is still required. On a stream socket whose local end was shut down,
[sendto](sendto.md) fails with EPIPE and raises SIGPIPE unless
MSG_NOSIGNAL is set (send.2).

## References

- Cached man page: source-cache/man-pages-sparse/man2/shutdown.2.
- Numbers: hub overview.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- Hub row: [overview](overview.md).
