# `if_nametoindex` / `if_indextoname` / `if_nameindex` / `if_freenameindex` (3) - glibc

> Split from the chapter *glibc: Sockets* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `net/if.h` (declarations unconditional) |
| Standards | POSIX.1-2001/2008, RFC 3493 (the manual's standards annotation reads "IPv6 basic API, `net/if.h`"); first appeared in BSDi (`if_nameindex(3)` CONFORMING TO) |
| Exported | `if_nametoindex`, `if_indextoname`, `if_nameindex`, `if_freenameindex` all `@@GLIBC_2.2.5` weak (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`if_nameindex(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-if_nametoindex, GLIBC-if_indextoname, GLIBC-if_nameindex, GLIBC-if_freenameindex |

## Declaration and gates

```c
#include <net/if.h>

unsigned int if_nametoindex(const char *ifname);
char *if_indextoname(unsigned int ifindex, char ifname[IF_NAMESIZE]);
struct if_nameindex *if_nameindex(void);
void if_freenameindex(struct if_nameindex *ptr);
```

Unconditional in `/usr/include/net/if.h`: `struct if_nameindex`
(`if_index`, `if_name`) at lines 33-37, the four prototypes at lines
193-202. `IF_NAMESIZE` (16) is defined at line 31 with `IFNAMSIZ` as
an alias at line 129; only the `sys/types.h`/`sys/socket.h` includes
inside the header are gated `__USE_MISC` (lines 24-27).

## Semantics

Interfaces have human names (`lo`, `eth0`) but are referenced in the
IPv6 socket API by a small positive integer index. `if_nametoindex`
maps name to index, returning 0 with `errno` set on failure
(`ENODEV` for an unknown name); `if_indextoname` maps the other way,
writing at most `IFNAMSIZ` bytes into the caller buffer and returning
it, or NULL with `ENXIO` for an unknown index. `if_nameindex` returns
a malloc'd array of all interfaces, terminated by an entry with
`if_index == 0` and `if_name == NULL`, which `if_freenameindex` must
free (manual, *Interface Naming*; `if_nameindex(3)`). Both converters
open a socket internally, so they can also fail with `socket(2)`
errors (manual notes; the man page lists socket, bind, ioctl,
getsockname, recvmsg, sendto and malloc error sources).

## Gotchas and portability

- `if_nametoindex` returning 0 is the error signal -- 0 is never a
  valid interface index, so no separate NULL convention exists.
- `if_nameindex` result is dynamic: forgetting `if_freenameindex`
  leaks, using `free(3)` directly is unspecified.
- glibc history (`if_nameindex(3)` VERSIONS): present since 2.1, but
  before 2.3.4 only interfaces with IPv4 addresses were reported;
  full coverage requires netlink-capable kernels.
- musl 1.2.5: all four implemented (`src/network/if_nametoindex.c`,
  `if_indextoname.c`, `if_nameindex.c`, `if_freenameindex.c`).

## Errors

`ENODEV` (no such name), `ENXIO` (no such index), `ENOBUFS`
(insufficient resources for `if_nameindex`), plus the underlying
socket-call errors (`if_nameindex(3)`).

## References

- glibc manual: `socket.texi`, node *Interface Naming*
- man3: `if_nameindex.3` (covers the family)
- header: `/usr/include/net/if.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
