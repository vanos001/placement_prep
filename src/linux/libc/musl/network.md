# musl: network

| Field | Value |
|---|---|
| musl version | 1.2.5 (WHATSNEW) |
| Key source files | `src/network/getaddrinfo.c`, `src/network/lookup_name.c`, `src/network/lookup_serv.c`, `src/network/resolvconf.c`, `src/network/res_mkquery.c`, `src/network/res_send.c`, `include/resolv.h` |
| glibc counterpart pages | [getaddrinfo/getnameinfo](../glibc/net/getaddrinfo-getnameinfo.md), [gethostbyname family](../glibc/net/gethostbyname-family.md), [socket/connect/bind/listen/accept](../glibc/net/socket-connect-bind-listen-accept.md) |
| Ledger | MUSL-family-netdb / -resolv / -nameser rows; ledger-musl.md `netdb.h` (32), `socket.h` (21), `inet.h` (13), `resolv.h` (9), `ifaddrs.h` (2) |

## Implementation notes

Name resolution is a fixed pipeline, not a pluggable one:
`lookup_name.c` reads `/etc/hosts` first and, only if that yields nothing,
queries DNS with search-list expansion (`name_from_hosts`, then
`name_from_dns_search`). `/etc/resolv.conf` is parsed by `resolvconf.c` with
defaults `ndots 1`, `timeout 5`, `attempts 2`; the only options recognized are
`ndots:`, `attempts:`, `timeout:`; `nameserver` up to MAXNS; one `domain` or
`search` line. `AI_ADDRCONFIG` is computed by probing loopback routability
(`getaddrinfo.c`). 1.2.4 added TCP fallback for large DNS answers and the
`EAI_NODATA` distinction; 1.2.1 set the AD flag and reports DNSSEC zone
signedness; 1.2.5 handles long CNAME chains (WHATSNEW).

## Deltas vs glibc (verified)

- No NSS: no `/etc/nsswitch.conf` handling anywhere in the tree (rg
  "nsswitch" = 0 hits); glibc 2.41 loads `libnss_files.so.2` etc. (files
  present on host). Source order is therefore not switchable.
- No `RES_OPTIONS` or `LOCALDOMAIN` environment variables: `rg getenv
  src/network/` returns nothing; glibc's resolver honors both.
- `RES_USE_EDNS0` exists as a flag macro (`include/resolv.h`) but the stub
  resolver does not generate EDNS0 itself; 1.2.4 only made `res_send` pass
  through caller-provided EDNS0 queries (WHATSNEW).
- No IDN: `AI_IDN`/`AI_CANONIDN` flags are absent from `include/netdb.h`
  (glibc encodes via libidn2); only the legacy `EAI_IDN_ENCODE` constant
  remains.
- `gai_strerror`, `EAI_*` codes and the 32 netdb functions are all present.

## Porting notes

Anything depending on nsswitch modules (mdns, ldap backends) or
`RES_OPTIONS`/`LOCALDOMAIN` overrides silently changes behavior; move such
policy to a local resolver or set the search/nameserver lines in
`/etc/resolv.conf`. IDN names must be punycode-encoded before calling.
