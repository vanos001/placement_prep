# send(3) - glibc (send / sendto / sendmsg / recv family, readv / writev)

> Companion page to [socket-connect-bind-listen-accept](./socket-connect-bind-listen-accept.md). The raw syscall entries are in [Network and IPC syscalls](../../../syscalls/net-ipc/overview.md); generic vector I/O on descriptors is also covered in [readv-writev-pread-pwrite](../stdio/readv-writev-pread-pwrite.md).

| Field | Value |
|---|---|
| Header | `sys/socket.h` |
| Standards | BSD origin, POSIX.1-2018; `sendmmsg`/`recvmmsg` and `MSG_NOSIGNAL`-style bits are Linux extensions |
| Exported | `send`, `sendto`, `sendmsg`, `recv`, `recvfrom`, `recvmsg`, `readv`, `writev` all `GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe; all of them are cancellation points (manual safety annotations) |
| Ledger ID | `GLIBC-send`, `GLIBC-sendto`, `GLIBC-sendmsg`, `GLIBC-recv`, `GLIBC-recvfrom`, `GLIBC-recvmsg` (Grouped FULL), `GLIBC-readv`, `GLIBC-writev` |

## Declaration and gates

```text
ssize_t send(int socket, const void *buffer, size_t size, int flags);
ssize_t sendto(int socket, const void *buffer, size_t size, int flags,
               struct sockaddr *addr, socklen_t length);
ssize_t sendmsg(int socket, const struct msghdr *message, int flags);
ssize_t recv(int socket, void *buffer, size_t size, int flags);
ssize_t recvfrom(int socket, void *buffer, size_t size, int flags,
                 struct sockaddr *addr, socklen_t *length_ptr);
ssize_t recvmsg(int socket, struct msghdr *message, int flags);
ssize_t readv(int fd, const struct iovec *iov, int iovcnt);   /* unistd.h */
ssize_t writev(int fd, const struct iovec *iov, int iovcnt);  /* unistd.h */
```

## Semantics

With `flags == 0`, `send`/`recv` are equivalent to `write`/`read` on the socket; the flags select socket-specific modes: `MSG_OOB` (out-of-band data), `MSG_PEEK` (input only; look without consuming), `MSG_DONTROUTE` (output only) (manual, *Socket Data Options*). `sendto`/`recvfrom` add the per-packet destination/source address used on datagram sockets; `connect` on a datagram socket fixes a default destination that `AF_UNSPEC` clears (manual, *Sending Datagrams*). `sendmsg`/`recvmsg` take a `struct msghdr` for scatter/gather buffers and ancillary data. A truncated datagram is lost: `recvfrom` returns the first `size` bytes and the rest is discarded (manual, *Receiving Datagrams*). A broken stream connection makes `send`/`write` raise `SIGPIPE`; if that is ignored or handled, they fail with `EPIPE` (manual, *Sending Data*). `readv`/`writev` are descriptor calls that also work on sockets. On nonblocking sockets a partial `send` returns the bytes accepted so far.

## Gotchas and portability

- Successful `send` means queued without error, not delivered (manual, *Sending Data*).
- A `sendto` error can report a problem from a *previous* packet (manual, *Sending Datagrams*).
- musl `src/network/send.c` is a two-line alias: `send(fd, buf, len, flags)` calls `sendto(fd, buf, len, flags, 0, 0)`.
- musl's `sendmsg`/`recvmsg` wrappers take the same syscalls; no `MSG_*` flag differences were found in the cached musl 1.2.5 tree (unverified beyond the listed sources).

## References

- glibc manual, nodes *Transferring Data*, *Socket Data Options*, *Datagrams*.
- man2: `send.2`, `sendto.2`, `sendmsg.2`, `recv.2`, `recvfrom.2`, `recvmsg.2`, `readv.2`, `writev.2`.
- Headers `sys/socket.h`, `sys/uio.h`; `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41).
