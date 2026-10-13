# getaddrinfo(3) - glibc (getaddrinfo / freeaddrinfo / getnameinfo / gai_strerror)

> The modern name-service entry point, replacing the [gethostbyname family](./gethostbyname-family.md). Backed by the glibc Name Service Switch (manual chapter *Name Service Switch*).

| Field | Value |
|---|---|
| Header | `netdb.h` (plus `sys/types.h`, `sys/socket.h`) |
| Standards | POSIX.1-2001/2008, RFC 2553; IDN flags `AI_IDN*` and `NI_IDN*` are glibc extensions |
| Exported | `getaddrinfo`, `freeaddrinfo`, `getnameinfo`, `gai_strerror` all `GLIBC_2.2.5` (nm, host glibc 2.41); the async `getaddrinfo_a` form was `libanl`, merged into libc in glibc 2.34 (ledger note) |
| Thread-safety | `getaddrinfo`, `getnameinfo`: MT-Safe env locale; `freeaddrinfo`, `gai_strerror`: MT-Safe (man3 ATTRIBUTES) |
| Ledger ID | `GLIBC-getaddrinfo` (FULL), `GLIBC-freeaddrinfo`, `GLIBC-getnameinfo`, `GLIBC-gai_strerror` (Grouped into the same entry) |

## Declaration and gates

```text
int getaddrinfo(const char *restrict node, const char *restrict service,
                const struct addrinfo *restrict hints, struct addrinfo **restrict res);
void freeaddrinfo(struct addrinfo *res);
int getnameinfo(const struct sockaddr *restrict sa, socklen_t salen,
                char *restrict host, socklen_t hostlen,
                char *restrict serv, socklen_t servlen, int flags);
const char *gai_strerror(int errcode);
```

Feature-test gate: since glibc 2.22 these need `_POSIX_C_SOURCE >= 200112L`; glibc 2.21 and earlier accepted plain `_POSIX_C_SOURCE` (man3 synopsis note).

## Semantics

`getaddrinfo` maps `node`/`service` to a linked list of `addrinfo` records ready for `socket`/`bind`/`connect`. `hints` filters by `ai_family` (`AF_UNSPEC` = both), `ai_socktype`, `ai_protocol` and `ai_flags`: `AI_PASSIVE` (wildcard address for servers), `AI_CANONNAME`, `AI_NUMERICHOST`, `AI_NUMERICSERV`, `AI_ADDRCONFIG`, `AI_V4MAPPED`, `AI_ALL`. Either `node` or `service`, but not both, may be NULL. The list is ordered per RFC 3484 and can be tuned via `/etc/gai.conf` (glibc 2.5+). `getnameinfo` is the inverse, with `NI_NUMERICHOST`, `NI_NUMERICSERV`, `NI_NAMEREQD`, `NI_DGRAM`, `NI_NOFQDN`. Errors are `EAI_*` codes (`EAI_AGAIN`, `EAI_NONAME`, `EAI_SERVICE`, `EAI_OVERFLOW`, `EAI_SYSTEM` with `errno` set, ...), rendered by `gai_strerror`. Return `0` on success. The backend chain follows `/etc/nsswitch.conf` `hosts:` entries (NSS database `hosts`, manual *NSS Basics*).

## Gotchas and portability

- With NULL `hints`, POSIX expects `ai_flags == 0`; glibc assumes `(AI_V4MAPPED | AI_ADDRCONFIG)` (man3 NOTES).
- musl contrast: musl 1.2.5 has no NSS and no `/etc/gai.conf`; `src/network/lookup_name.c` implements "a subset of RFC 3484/6724 destination address selection" with one fixed 31-bit sort key, and `src/network/getaddrinfo.c` rejects hints flags outside its mask with `EAI_BADFLAGS`. musl reads `/etc/hosts`, then `/etc/resolv.conf` directly.

## References

- man3 `getaddrinfo.3`, `getnameinfo.3`; glibc manual nodes *Host Names* and *NSS Basics*.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 sources as cited.
