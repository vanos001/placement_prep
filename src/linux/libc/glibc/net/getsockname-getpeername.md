# `getsockname` / `getpeername` (2, via sys/socket.h) - glibc

> Split from the chapter *glibc: Sockets* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/socket.h` (multiarch path `/usr/include/x86_64-linux-gnu/sys/socket.h`) |
| Standards | POSIX.1-2001/2008, SVr4, 4.4BSD; `getsockname` first appeared in 4.2BSD (`getsockname(2)`, `getpeername(2)` CONFORMING TO) |
| Exported | `getsockname@@GLIBC_2.2.5`, `getpeername@@GLIBC_2.2.5`, both weak syscall aliases (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (manual safety annotations, `socket.texi` nodes *Reading Address* and *Who is Connected*; the man2 pages predate the ATTRIBUTES convention) |
| Ledger ID | GLIBC-getsockname, GLIBC-getpeername |

## Declaration and gates

```c
#include <sys/socket.h>

int getsockname(int fd, struct sockaddr *restrict addr,
                socklen_t *restrict len);
int getpeername(int fd, struct sockaddr *restrict addr,
                socklen_t *restrict len);
```

Both unconditional: `getsockname` at `/usr/include/x86_64-linux-gnu/`
`sys/socket.h` lines 116-117, `getpeername` at lines 130-131, with the
opaque `__SOCKADDR_ARG` union elided to its `struct sockaddr *`
reading here.

## Semantics

`getsockname` reports the address the socket `fd` is currently bound
to; after `bind` with port 0 or an autobind it is the way to learn the
port the kernel picked. `getpeername` reports the address of the
connected peer -- on a `fork`ed server the standard way to re-derive
the client identity from the bare descriptor. Both take a value-result
`len`: initialize it to the buffer size, and on return it holds the
real size; if the buffer was too small the address is truncated and
`len` comes back larger than what was passed (`getsockname(2)`,
`getpeername(2)`). The manual recommends allocating the proper
namespace-specific type (`sockaddr_in` etc.) and casting to
`struct sockaddr *` (manual, *Reading Address*).

## Gotchas and portability

- Truncation is signalled only by `*len` growing past the supplied
  value; callers that ignore the returned length can silently use
  clipped addresses -- for AF_UNIX that clips the sun_path tail.
- "You can't read the address of a socket in the file namespace"
  (manual, *Reading Address*): glibc's historic file-namespace sockets
  answer neither function.
- `getpeername` on an unconnected TCP socket fails with `ENOTCONN`;
  on UDP it reports the default peer set by `connect(2)`.
- Raw syscall pages: [getsockname](../../../syscalls/net-ipc/getsockname.md);
  sibling library pages:
  [socket/bind/connect](socket-connect-bind-listen-accept.md),
  [sockaddr variants](unix-inet-sockaddr-variants.md).
- musl 1.2.5: thin wrappers present (`src/network/getsockname.c`,
  `getpeername.c`).

## Errors

`EBADF`, `EFAULT`, `EINVAL` (invalid `len`), `ENOBUFS`, `ENOTSOCK`;
`getpeername` adds `ENOTCONN` (`getsockname(2)`, `getpeername(2)`).

## References

- glibc manual: `socket.texi`, nodes *Reading Address*, *Who is
  Connected*
- man2: `getsockname.2`, `getpeername.2`
- header: `/usr/include/x86_64-linux-gnu/sys/socket.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
