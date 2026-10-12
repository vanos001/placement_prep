# sendmsg(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | sendmsg 46(64) / 370 / 211 / 296; recvmsg 47(64) / 372 / 212 / 297 (ledger SC-rows + cached tables) |
| Since (kernel) | 2.0 (hub send row) |
| Man page | man2/sendmsg.2 and man2/recvmsg.2 are .so aliases of send.2 / recv.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | yes, standard libc wrappers |
| Aliases covered | recvmsg (SC-recvmsg, grouped per ledger) |
| Ledger ID | SC-sendmsg |

## Purpose

sendmsg()/recvmsg() are the general forms of the socket I/O calls:
they take a single `msghdr` describing the destination/source address,
a scatter-gather iovec array, and an ancillary-data (control message)
buffer. Ancillary data is the kernel's channel for out-of-band
metadata -- most famously file descriptors (SCM_RIGHTS) and process
credentials (SCM_CREDENTIALS) over UNIX domain sockets.

## Synopsis

```c
#include <sys/socket.h>
ssize_t sendmsg(int sockfd, const struct msghdr *msg, int flags);
ssize_t recvmsg(int sockfd, struct msghdr *msg, int flags);
```

## Arguments and behavior

The msghdr (send.2/recv.2):

| Field | Send / Receive meaning |
|---|---|
| msg_name, msg_namelen | target address on send; source address buffer (value-result) on receive |
| msg_iov, msg_iovlen | scatter/gather buffers, as for writev(2)/readv(2) |
| msg_control, msg_controllen | ancillary buffer; send: set; recv: value-result |
| msg_flags | ignored on send; on receive: MSG_EOR, MSG_TRUNC, MSG_CTRUNC, MSG_OOB, MSG_ERRQUEUE |

Control messages are `struct cmsghdr { size_t cmsg_len; int
cmsg_level; int cmsg_type; /* data */ }` and must be touched only via
the cmsg(3) macros. Max control-buffer size is per-socket
/proc/sys/net/core/optmem_max (send.2). POSIX types msg_controllen as
socklen_t and msg_iovlen as int, but glibc types both size_t (send.2
NOTES). The kernel ucred structure for SCM_CREDENTIALS is
`{ pid_t pid; uid_t uid; gid_t gid; }` (bits/socket.h, __USE_GNU).

## Return value and errors

Bytes sent/received, or -1 with errno; errors as for
[sendto](sendto.md) / recv, plus EINVAL (e.g. negative msg_namelen)
and ENOMEM for recvmsg (recv.2). Stream peer shutdown returns 0.

## Flags and constants

Ancillary types at level SOL_SOCKET (bits/socket.h values verified):

| Type | Value | Meaning |
|---|---|---|
| SCM_RIGHTS | 0x01 | transfer file descriptors (unix(7)) |
| SCM_CREDENTIALS | 0x02 | struct ucred credentials (requires SO_PASSCRED) |
| SCM_PIDFD | 0x04 | pidfd (in installed headers; not in cached 2021 man page) |

recvmsg-only flag MSG_CMSG_CLOEXEC (since 2.6.23) sets FD_CLOEXEC on
fds received via SCM_RIGHTS (recv.2); MSG_ERRQUEUE (2.2) pulls
sock_extended_err records from the per-socket error queue.

## Security and notes

Credentials received in SCM_CREDENTIALS are kernel-attested -- a
receiver can trust them against spoofing, unlike payload-borne
identities. Received descriptors duplicate open files and must be
closed by the receiver. MSG_CTRUNC warns of discarded control data
(recv.2). recvmsg leaves msg_flags set per message; callers must
check it, e.g. for MSG_TRUNC on datagram sockets.

## References

- Cached man pages: source-cache/man-pages-sparse/man2/send.2, recv.2 (sendmsg.2/recvmsg.2 .so aliases).
- Constants: /usr/include/x86_64-linux-gnu/bits/socket.h (SCM_*, struct ucred).
- Numbers: ledger.md SC-rows; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- Worklog Task 1-g (SCM_RIGHTS/SCM_CREDENTIALS header verification).
