# `inet_ntoa` / `inet_lnaof` / `inet_makeaddr` / `inet_netof` / `inet_network` (3) - glibc

> Split from the chapter *glibc: Sockets* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `arpa/inet.h` (declarations unconditional; `struct in_addr` from `netinet/in.h`) |
| Standards | BSD origin; deprecated by the manual in favor of `inet_pton`/`inet_ntop` (IPv6 basic API) for the classful trio |
| Exported | `inet_ntoa`, `inet_lnaof`, `inet_netof` regular, `inet_makeaddr`, `inet_network` weak, all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `inet_ntoa`: MT-Safe `locale` (per-thread static buffer); `inet_lnaof`, `inet_makeaddr`, `inet_netof`, `inet_network`: MT-Safe (`inet.3` ATTRIBUTES) |
| Ledger ID | GLIBC-inet_ntoa, GLIBC-inet_lnaof, GLIBC-inet_makeaddr, GLIBC-inet_netof, GLIBC-inet_network |

## Declaration and gates

```c
#include <arpa/inet.h>

char *inet_ntoa(struct in_addr in);                    /* line 53 */
in_addr_t inet_lnaof(struct in_addr in);               /* line 37 */
struct in_addr inet_makeaddr(in_addr_t net,
                             in_addr_t host);          /* lines 41-42 */
in_addr_t inet_netof(struct in_addr in);               /* line 45 */
in_addr_t inet_network(const char *cp);                /* line 49 */
```

All unconditional in `/usr/include/arpa/inet.h` (line numbers above;
`typedef uint32_t in_addr_t;` wraps `struct in_addr { in_addr_t
s_addr; }` from `netinet/in.h`).

## Semantics

The pre-CIDR helpers. `inet_network` parses a numbers-and-dots string
into a number in **host** byte order suitable as a network address,
returning -1 for invalid input (`inet.3`); unlike `inet_addr` it does
not return network order, and -1 is its failure value. `inet_ntoa`
renders a network-order `in_addr` as dotted decimal in a statically
allocated buffer, overwritten by each call -- per-thread in glibc,
but still shared across calls in one thread (manual, *Host Address
Functions*). `inet_netof` extracts the network number and `inet_lnaof`
the local part of a host address, both in host byte order, both
applying the classful A/B/C masks from the leading bits;
`inet_makeaddr` is their converse, rebuilding a network-order host
address from network number plus local part (`inet.3`).

## Gotchas and portability

- The classful trio "works only with traditional IPv4 class A, B and C
  network types. It doesn't work with classless addresses and
  shouldn't be used anymore" -- the manual's exact verdict, repeated on
  all three (`socket.texi`, *Host Address Functions*).
- `inet_ntoa` is MT-Safe only in the per-thread-buffer sense; its
  return is still invalidated by the next call in the same thread --
  `inet_ntop` with a caller buffer is the replacement.
- musl 1.2.5: all five present (`src/network/inet_ntoa.c`,
  `inet_legacy.c`; note `inet_network` there is just
  `ntohl(inet_addr(p))`, which keeps the same host-order contract for
  the common forms).

## References

- glibc manual: `socket.texi`, nodes *Host Address Functions*,
  *Abstract Host Addresses*, *Byte Order*
- man3: `inet.3` (covers the five), `inet_addr.3` (`inet_makeaddr`
  link target)
- header: `/usr/include/arpa/inet.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
