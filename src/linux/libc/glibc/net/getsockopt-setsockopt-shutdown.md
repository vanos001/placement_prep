# `getsockopt` / `setsockopt` / `shutdown` (2, via sys/socket.h) - glibc

> Split from the chapter *glibc: Sockets* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/socket.h` (multiarch path `/usr/include/x86_64-linux-gnu/sys/socket.h`) |
| Standards | POSIX.1-2001/2008; 4.4BSD origin, `shutdown` and `getsockopt` first appeared in 4.2BSD (`getsockopt(2)`, `shutdown(2)` CONFORMING TO) |
| Exported | `getsockopt`, `setsockopt`, `shutdown` all `@@GLIBC_2.2.5` weak syscall aliases (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (manual safety annotations, `socket.texi` node *Socket Option Functions*; man2 pages carry no ATTRIBUTES) |
| Ledger ID | GLIBC-getsockopt, GLIBC-setsockopt, GLIBC-shutdown |

## Declaration and gates

```c
#include <sys/socket.h>

int getsockopt(int fd, int level, int optname,
               void *restrict optval, socklen_t *restrict optlen);
int setsockopt(int fd, int level, int optname,
               const void *optval, socklen_t optlen);
int shutdown(int fd, int how);   /* how: SHUT_RD, SHUT_WR, SHUT_RDWR */
```

Unconditional declarations: `getsockopt` at lines 255-273 and
`setsockopt` at 277-295 of `/usr/include/x86_64-linux-gnu/sys/socket.h`
(each with a `__getsockopt64`/`__setsockopt64` redirect for
`__USE_TIME64_REDIRECTS` builds, covering the timeout options on
32-bit time64 ABIs), `shutdown` at line 324. `SHUT_RD`/`SHUT_WR`/
`SHUT_RDWR` (values 0, 1, 2) come from the enum at lines 43-48,
defined since glibc 2.1.91 (`shutdown(2)` NOTES).

## Semantics

Options live at stacked protocol levels: `level` is `SOL_SOCKET` for
the generic layer, otherwise a protocol number -- the manual points at
`getprotoent(3)` for obtaining e.g. the TCP number (manual, *Socket
Option Functions*). `optname`/`optval` are passed to the protocol
module uninterpreted; most socket-level options take an `int`, nonzero
enabling a boolean option. For `getsockopt`, `optlen` is value-result:
in with the buffer size, out with the actual value size; `optval` may
be NULL when no value is wanted. `shutdown` disallows further
receptions (`SHUT_RD`), transmissions (`SHUT_WR`) or both
(`SHUT_RDWR`) on the connection, without closing the descriptor --
`close(2)` stays the resource-releasing call (`shutdown(2)`).

## Gotchas and portability

- Validity of `how` was checked in domain-specific code: before Linux
  3.7, UNIX domain sockets silently ignored invalid values
  (`shutdown(2)` BUGS).
- `shutdown(SHUT_WR)` is the standard half-close; `shutdown(SHUT_RD)`
  on TCP does not reliably deliver FIN semantics readable by the peer
  -- behavior is protocol dependent.
- TCP-level options (`TCP_NODELAY` and friends) need
  `#include <netinet/tcp.h>` with `level = IPPROTO_TCP`.
- Raw syscall pages: [setsockopt](../../../syscalls/net-ipc/setsockopt.md),
  [shutdown](../../../syscalls/net-ipc/shutdown.md); musl 1.2.5:
  thin wrappers (`src/network/getsockopt.c`, `setsockopt.c`,
  `shutdown.c`).

## Errors

`EBADF`, `ENOTSOCK`, `ENOPROTOOPT` (option invalid at that level) for
the sockopt pair; `shutdown`: `EBADF`, `EINVAL` (bad `how`), `ENOTCONN`,
`ENOTSOCK` (`getsockopt(2)`, `shutdown(2)`).

## References

- glibc manual: `socket.texi`, nodes *Socket Option Functions*,
  *Socket-Level Options*, *Closing a Socket*
- man2: `getsockopt.2` (covers `setsockopt`), `shutdown.2`
- header: `/usr/include/x86_64-linux-gnu/sys/socket.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
