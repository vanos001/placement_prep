# sockaddr(3) - glibc (struct sockaddr, sockaddr_un, sockaddr_in, sockaddr_in6, byte order)

> The address structures behind every socket call in [socket-connect-bind-listen-accept](./socket-connect-bind-listen-accept.md) and [send-recv-readv-writev-msg](./send-recv-readv-writev-msg.md).

| Field | Value |
|---|---|
| Header | `sys/socket.h` (`struct sockaddr`), `sys/un.h` (`sockaddr_un`), `netinet/in.h` (`sockaddr_in`, `sockaddr_in6`, `htons` family) |
| Standards | BSD origin; `AF_LOCAL`/`PF_LOCAL` POSIX.1g, `AF_UNIX` Unix98, `AF_INET6` IPv6 Basic API |
| Exported | Data structures and macros; the byte-order helpers are real functions `htonl`/`htons`/`ntohl`/`ntohs` `GLIBC_2.2.5` (nm), inlined to `bswap` or identity on the host header |
| Thread-safety | Pure data types and pure functions; MT-Safe, AS-safe (manual safety annotations) |
| Ledger ID | `GLIBC-htonl`/`GLIBC-htons`/`GLIBC-ntohl`/`GLIBC-ntohs` (Grouped brief byte-order entries) |

## Declaration and gates

```text
struct sockaddr  { short int sa_family; char sa_data[14]; };          /* sys/socket.h */
struct sockaddr_un { short int sun_family; char sun_path[108]; };     /* sys/un.h */
struct sockaddr_in  { sa_family_t sin_family; in_port_t sin_port; struct in_addr sin_addr; };
struct sockaddr_in6 { sa_family_t sin6_family; uint16_t sin6_port; uint32_t sin6_flowinfo;
                      struct in6_addr sin6_addr; uint32_t sin6_scope_id; };
uint16_t htons(uint16_t); uint32_t htonl(uint32_t);   /* netinet/in.h */
```

`sockaddr_in6` additionally shows `sin6_flowinfo` (traffic class + flow label, network byte order, lower 28 bits used) and `sin6_scope_id` (link-local interface, host byte order).

## Semantics

APIs take `struct sockaddr *` plus a length; you build the namespace-specific type and cast. `sa_family`/`sin_family`/`sun_family` is the format designator; `AF_UNIX`, `AF_FILE` are synonyms of `AF_LOCAL` (manual, *Address Formats*). In `sockaddr_in`, `sin_port` and `sin_addr` must be network byte order while the family field stays host order; pass `sizeof (struct sockaddr_in)` as the length. `sin_addr` values from `gethostbyname`, `inet_addr` or `getservbyname`'s `s_port` are already converted; otherwise use `htons`/`htonl` (manual, *Byte Order*). For `sockaddr_un`, compute the length from the string length, not the 108-byte field: `SUN_LEN(ptr)` is `offsetof(sun_path) + strlen(sun_path)` (header + manual, *Local Namespace Details*).

## Gotchas and portability

- `sun_path[108]` is a magic constant (the manual itself asks "Why is 108?"); longer paths cannot be represented.
- A local-namespace name is only consulted at connect time and the socket file must be `unlink`ed after close (manual, *Local Namespace Concepts*).
- On little-endian hosts `htons` is a byte swap; on big-endian hosts the header defines the macros as identity functions (`netinet/in.h` lines 422-426).

## References

- glibc manual nodes *Address Formats*, *Local Namespace*, *Internet Address Formats*, *Byte Order*.
- Headers `sys/socket.h`, `sys/un.h`, `netinet/in.h` (glibc 2.41 host).
