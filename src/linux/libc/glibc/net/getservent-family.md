# `getservent` / `getservbyname` / `getservbyport` / `setservent` / `endservent` (3) - glibc

> Split from the chapter *glibc: Sockets* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `netdb.h` (base functions unconditional; `_r` twins under `__USE_MISC`) |
| Standards | POSIX.1-2001/2008, 4.3BSD (`getservent(3)` CONFORMING TO) |
| Exported | `getservent`, `getservbyname`, `getservbyport`, `setservent`, `endservent` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `race:servent` (`getservent`; `setservent`/`endservent` add `locale`), `race:servbyname`, `race:servbyport` (`getservent(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getservent, GLIBC-getservbyname, GLIBC-getservbyport, GLIBC-setservent, GLIBC-endservent |

## Declaration and gates

```c
#include <netdb.h>

struct servent *getservent(void);
struct servent *getservbyname(const char *name, const char *proto);
struct servent *getservbyport(int port, const char *proto);
void setservent(int stayopen);
void endservent(void);
```

Unconditional in `/usr/include/netdb.h`: `struct servent` at lines
255-261 (`s_name`, `s_aliases`, `s_port`, `s_proto`), `setservent`
line 268, `endservent` 274, `getservent` 281, `getservbyname` 288,
`getservbyport` 295; the `_r` twins sit behind `#ifdef __USE_MISC`
from line 298 on and belong to other rows.

## Semantics

The services database (`/etc/services`, NSS service `services`) maps
service names to port/protocol pairs: servers use `getservbyname` to
pick the port to listen on, clients to resolve peer port names
(manual, *Services Database*). `getservent` enumerates entries;
`getservbyname` looks up by name with a protocol filter (NULL matches
any protocol); `getservbyport` looks up by port -- passed already in
**network** byte order -- again with optional protocol. `setservent`
opens/rewinds (nonzero `stayopen` keeps the database open across
lookups), `endservent` closes it. Readers return statically allocated
`servent` pointers, NULL on error or end of file (`getservent(3)`).

## Gotchas and portability

- The signature trap of this family: `s_port` is in network byte
  order (call `htons`/`ntohs` around it), while the parallel
  `protoent.p_proto` is host order -- the manual states both explicitly.
- All five share global state; use the `_r` twins in threads
  ([compact page](getprotobyname-getservbyport.md) groups them).
- musl 1.2.5 asymmetry: `getservbyname`/`getservbyport` parse
  `/etc/services` (`src/network/lookup_serv.c`), but
  `getservent`/`setservent`/`endservent` are stubs returning 0 /
  no-ops (`src/network/serv.c`) -- enumeration silently yields
  nothing.
- Address/port packing context: [sockaddr variants](unix-inet-sockaddr-variants.md).

## References

- glibc manual: `socket.texi`, nodes *Services Database*, *Ports*
- man3: `getservent.3` (covers the family), `services(5)`
- header: `/usr/include/netdb.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
