# sendto(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | sendto 44 / 369 / 206 / 290; recvfrom 45(64) / 371 / 207 / 292 (ledger SC-rows + cached tables) |
| Since (kernel) | 2.0 (hub send row) |
| Man page | man2/sendto.2 and man2/recvfrom.2 are .so aliases of send.2 / recv.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | yes, standard libc wrappers for send/sendto/recv/recvfrom |
| Aliases covered | recvfrom (SC-recvfrom); legacy send (SC-send) and recv (SC-recv) brief |
| Ledger ID | SC-sendto |

## Purpose

sendto() transmits a message (`buf`, `len` bytes) on a socket,
supplying the destination address `dest_addr` (`addrlen` bytes) for
unconnected sockets. It is the primary sender for SOCK_DGRAM and
SOCK_RAW sockets created by [socket](socket.md); the sibling
recvfrom() receives and returns the sender address. The hub routes
send/sendmsg/sendto to one page and recv/recvfrom/recvmsg to another;
this task splits them (sendto.md / sendmsg.md), so the hub pointer
needs a merge-time decision (worklog 3-f).

## Synopsis

```c
#include <sys/socket.h>
ssize_t sendto(int sockfd, const void *buf, size_t len, int flags,
               const struct sockaddr *dest_addr, socklen_t addrlen);
ssize_t recvfrom(int sockfd, void *restrict buf, size_t len, int flags,
                 struct sockaddr *restrict src_addr,
                 socklen_t *restrict addrlen);
```

## Arguments and behavior

sendto() on a connection-mode socket ignores dest_addr/addrlen
(EISCONN may be returned when they are not NULL/0; ENOTCONN when the
socket is unconnected). send(fd, buf, len, flags) equals
sendto(fd, buf, len, flags, NULL, 0), and send() differs from
write(2) only in `flags`. recvfrom() copies the source address into
src_addr if non-NULL, with value-result addrlen; recv() equals
recvfrom(..., NULL, NULL). A message too large to pass atomically
fails with EMSGSIZE. A blocking call waits while the send buffer is
full; nonblocking returns EAGAIN. recv() returns 0 on orderly peer
shutdown (EOF) and for zero-length datagrams; on a pending
zero-length datagram read(2) leaves it queued while recv() consumes
it (recv.2 NOTES).

## Return value and errors

Number of bytes sent/received; -1 with errno. send.2: EACCES,
EAGAIN/EWOULDBLOCK, EALREADY (TCP Fast Open), EBADF, ECONNRESET,
EDESTADDRREQ, EFAULT, EINTR, EINVAL, EISCONN, EMSGSIZE, ENOBUFS,
ENOMEM, ENOTCONN, ENOTSOCK, EOPNOTSUPP (flag inappropriate for the
type), EPIPE (local end shut down; SIGPIPE unless MSG_NOSIGNAL);
Linux may return EPIPE instead of ENOTCONN (BUGS). recv.2 adds
ECONNREFUSED.

## Flags and constants

MSG_* flags (send.2/recv.2; per-call, unlike fcntl O_NONBLOCK):

| Flag | Since | Meaning |
|---|---|---|
| MSG_CONFIRM | 2.3.15 | link-layer neighbor progress hint; SOCK_DGRAM/RAW, IPv4/IPv6 |
| MSG_DONTROUTE | - | send directly to connected networks, no gateway |
| MSG_DONTWAIT | 2.2 | per-call nonblocking mode |
| MSG_EOR | 2.2 | end of record (SOCK_SEQPACKET) |
| MSG_MORE | 2.4.4 | cork this call; TCP_CORK / UDP_CORK per-call equivalent |
| MSG_NOSIGNAL | 2.2 | no SIGPIPE on broken stream, EPIPE still returned |
| MSG_OOB | - | out-of-band data |
| MSG_PEEK (recv) | - | look without consuming |
| MSG_TRUNC (recv) | 2.2 | return real length even past buffer (per-family dates in recv.2) |
| MSG_WAITALL (recv) | 2.2 | block until full request (with listed exceptions) |

## Security and notes

Legacy brief: the bare send()/recv() calls survive as separate
syscalls only on arm (289 / 291 per ledger 1-g); x64 and generic
have no slots and i386 reached them via socketcall SYS_SEND 9 /
SYS_RECV 10; glibc has no send/recv symbols and code uses
sendto/recvfrom. On unconnected UDP, an unbound socket may hit
ephemeral-port exhaustion (EAGAIN, send.2). send() gives no
delivery guarantee -- locally detected errors only.

## References

- Cached man pages: source-cache/man-pages-sparse/man2/send.2 (sendto.2 .so), recv.2 (recvfrom.2 .so).
- Numbers: ledger.md SC-rows; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- Worklog Task 1-g (send/recv legacy slots; hub split decision).
