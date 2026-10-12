# socket(3) - glibc (socket / connect / bind / listen / accept)

> Split from the chapter *glibc: Sockets, Users, Time, Syslog and Patterns* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md). The kernel-side counterparts live in [Network and IPC syscalls](../../../syscalls/net-ipc/overview.md).

| Field | Value |
|---|---|
| Header | `sys/socket.h` |
| Standards | BSD origin, POSIX.1-2018; `accept4` is a GNU/Linux extension |
| Exported | `socket`, `bind`, `connect`, `listen`, `accept` `GLIBC_2.2.5`; `accept4` `GLIBC_2.10` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe per the manual safety annotations; `connect` and `accept` are cancellation points |
| Ledger ID | `GLIBC-socket`, `GLIBC-bind`, `GLIBC-connect`, `GLIBC-accept`, `GLIBC-listen` (Grouped FULL; `accept4` grouped into the accept group) |

## Declaration and gates

```text
int socket(int namespace, int style, int protocol);
int connect(int socket, struct sockaddr *addr, socklen_t length);
int bind(int socket, struct sockaddr *addr, socklen_t length);
int listen(int socket, int n);
int accept(int socket, struct sockaddr *addr, socklen_t *length_ptr);
int accept4(int fd, struct sockaddr *addr, socklen_t *addr_len, int flags); /* __USE_GNU */
```

`accept4` is declared only under `__USE_GNU` (host header `sys/socket.h`); its `flags` are `SOCK_CLOEXEC` and `SOCK_NONBLOCK`.

## Semantics

`socket` creates a descriptor for `namespace` (the manual calls it the namespace; `PF_LOCAL`, `PF_INET`), communication `style` (`SOCK_STREAM`, `SOCK_DGRAM`, ...) and `protocol` (0 picks the default: TCP for stream, UDP for datagram). `connect` initiates a connection and normally blocks until the server responds; on a nonblocking socket it returns `-1`/`EINPROGRESS` and completion is polled (second `connect` then fails with `EALREADY`). `bind` assigns `addr`; `listen` marks the socket a server socket and sets the pending-connection queue length `n`; `accept` blocks until a request is pending, fills `*addr` with the peer address, and returns a *new* descriptor - the listening socket stays open and unconnected. All return `-1` on failure and pass the kernel `errno` through (manual nodes *Creating a Socket*, *Connecting*, *Listening*, *Accepting Connections*). Documented errors include `EAFNOSUPPORT`, `EMFILE`/`ENFILE`, `ECONNREFUSED`, `ETIMEDOUT`, `EADDRINUSE`, `EWOULDBLOCK`.

## Gotchas and portability

- `listen`/`accept` are not allowed for connectionless styles (manual, *Datagrams*).
- The queue can overflow: clients get `ECONNREFUSED` until `accept` drains it (manual, *Listening*).
- musl `src/network/socket.c` retries `socket()` without `SOCK_CLOEXEC|SOCK_NONBLOCK` on old kernels, then re-applies the flags via `fcntl`; the kernel takes those bits ORed into the type itself (man2 `socket.2`).
- `bind` is a direct syscall wrapper on Linux ("Direct syscall, except on Hurd", texi safety comment); musl routes `socket` through its `__socketcall` helper (`src/network/socket.c`), which also handles architectures without a direct socket slot.

## References

- glibc manual, chapter *Sockets*, nodes *Open/Close Sockets* and *Connections*.
- Headers `sys/socket.h`; `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6` (glibc 2.41).
- man2: `socket.2`, `bind.2`, `connect.2`, `listen.2`, `accept.2`, `accept4.2`.
