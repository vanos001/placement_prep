# `getnetent` / `getnetbyaddr` / `getnetbyname` / `setnetent` / `endnetent` (3) - glibc

> Split from the chapter *glibc: Sockets* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `netdb.h` (base functions unconditional; `_r` twins under `__USE_MISC`) |
| Standards | POSIX.1-2001/2008, 4.3BSD (`getnetent(3)` CONFORMING TO) |
| Exported | `getnetent`, `getnetbyaddr`, `getnetbyname`, `setnetent`, `endnetent` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `race:netent` (`getnetent`; `setnetent`/`endnetent` add `env`), `race:netbyname`, `race:netbyaddr` (`getnetent(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getnetent, GLIBC-getnetbyaddr, GLIBC-getnetbyname, GLIBC-setnetent, GLIBC-endnetent |

## Declaration and gates

```c
#include <netdb.h>

struct netent *getnetent(void);
struct netent *getnetbyname(const char *name);
struct netent *getnetbyaddr(uint32_t net, int type);
void setnetent(int stayopen);
void endnetent(void);
```

Unconditional in `/usr/include/netdb.h`: `setnetent` line 196,
`endnetent` 202, `getnetent` 209, `getnetbyaddr` 216, `getnetbyname`
222. `struct netent` itself lives in the included
`bits/netdb.h` (lines 26-32 on this host) with `n_name`, `n_aliases`,
`n_addrtype`, `n_net`. The reentrant `getnetent_r`/`getnetbyaddr_r`
twins (decls at netdb.h lines 235-249, `__USE_MISC`) are separate rows
and not covered by this page's IDs.

## Semantics

The networks database -- traditionally `/etc/networks`, nowadays the
NSS `networks` service -- maps network names to network numbers, which
the manual calls "useful for routing programs such as route, but not
useful for programs that simply communicate over the network" (manual,
*Networks Database*). `getnetent` reads successive entries, opening
the database when needed; `getnetbyname` and `getnetbyaddr` do keyed
lookups (the latter taking the network number in **host** byte order
and an address `type`, for which `AF_INET` is the value to pass).
`setnetent` opens/rewinds, keeping the database open between calls
when `stayopen` is nonzero; `endnetent` closes it. All five return
pointers to a statically allocated `struct netent`, or NULL on error
or end of data (`getnetent(3)`).

## Gotchas and portability

- Byte-order asymmetry across the database family: `n_net` (and the
  `getnetbyaddr` argument) are host byte order, while
  `servent.s_port` is network order -- a recurring interview trap.
- The manual warns the iterators "are not reentrant" and the result
  must be copied before the next call.
- musl 1.2.5: the whole family is absent -- no `struct netent` in
  `include/netdb.h`, no sources under `src/network/` (grep for
  `netent` returns nothing).
- Related: [getaddrinfo page](getaddrinfo-getnameinfo.md) for the
  modern resolver path; sibling compact pages
  [getprotobyname-getservbyport](getprotobyname-getservbyport.md).

## References

- glibc manual: `socket.texi`, node *Networks Database*
- man3: `getnetent.3` (covers the family), `networks(5)`
- header: `/usr/include/netdb.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
