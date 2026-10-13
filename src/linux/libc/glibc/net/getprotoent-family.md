# `getprotoent` / `getprotobyname` / `getprotobynumber` / `setprotoent` / `endprotoent` (3) - glibc

> Split from the chapter *glibc: Sockets* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `netdb.h` (base functions unconditional; `_r` twins under `__USE_MISC`) |
| Standards | POSIX.1-2001/2008, 4.3BSD (`getprotoent(3)` CONFORMING TO) |
| Exported | `getprotoent`, `getprotobyname`, `getprotobynumber`, `setprotoent`, `endprotoent` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `race:protoent` (`getprotoent`, `setprotoent`/`endprotoent`), `race:protobyname`, `race:protobynumber` (`getprotoent(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getprotoent, GLIBC-getprotobyname, GLIBC-getprotobynumber, GLIBC-setprotoent, GLIBC-endprotoent |

## Declaration and gates

```c
#include <netdb.h>

struct protoent *getprotoent(void);
struct protoent *getprotobyname(const char *name);
struct protoent *getprotobynumber(int proto);
void setprotoent(int stayopen);
void endprotoent(void);
```

Unconditional in `/usr/include/netdb.h`: `struct protoent` at lines
324-329 (`p_name`, `p_aliases`, `p_proto`), `setprotoent` line 336,
`endprotoent` 342, `getprotoent` 349, `getprotobyname` 355,
`getprotobynumber` 361; the `_r` twins start behind `#ifdef
__USE_MISC` at line 364 and are separate rows, not covered here.

## Semantics

The protocols database (`/etc/protocols`, NSS service `protocols`)
maps protocol names to the IP protocol numbers used by `socket(2)`'s
third argument and by raw-socket options. `getprotoent` walks the
database entry by entry; `getprotobyname("tcp")` and
`getprotobynumber(6)` do keyed lookups, each opening the database on
demand. `setprotoent` opens/rewinds, with nonzero `stayopen` keeping
the connection open across subsequent calls for efficiency; `endprotoent`
closes it. Every reader returns a pointer to a statically allocated
`protoent`, NULL on error or end of file (`getprotoent(3)`).

## Gotchas and portability

- `p_proto` is in host byte order -- unlike `servent.s_port`; the
  manual's *Protocols Database* node documents both fields.
- All five share process-global state; threaded programs need the
  `_r` twins (with a caller buffer) -- see the
  [byname/compact page](getprotobyname-getservbyport.md) which also
  groups the `_r` rows.
- musl 1.2.5: implements the family from a built-in table
  (`src/network/proto.c`, comment "do we really need all these??"),
  not by parsing `/etc/protocols` -- same answers for the common
  entries, but edits to the local file are invisible.
- Raw socket creation with a looked-up protocol:
  [socket page](../../../syscalls/net-ipc/socket.md).

## References

- glibc manual: `socket.texi`, node *Protocols Database*
- man3: `getprotoent.3` (covers the family), `protocols(5)`
- header: `/usr/include/netdb.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
