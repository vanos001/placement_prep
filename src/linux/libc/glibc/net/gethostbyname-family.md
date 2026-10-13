# gethostbyname(3) - glibc (gethostbyname / gethostbyname2 / gethostbyaddr, _r twins, hostent iterators)

> Obsolete name-service interface. man3 `gethostbyname.3` opens: the `gethostbyname*()`, `gethostbyaddr*()`, `herror()` and `hstrerror()` functions **are obsolete**; use [getaddrinfo/getnameinfo](./getaddrinfo-getnameinfo.md) instead.

| Field | Value |
|---|---|
| Header | `netdb.h` |
| Standards | BSD origin; kept by glibc for compatibility, no longer in POSIX.1-2018 |
| Exported | `gethostbyname`, `gethostbyname2`, `gethostbyaddr`, `gethostbyname_r`, `gethostbyname2_r`, `gethostbyaddr_r`, `sethostent`, `gethostent`, `endhostent` all `GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | Non-`_r` forms: MT-Unsafe race:hostbyname, env, locale; `_r` forms: MT-Safe env locale but need a caller buffer (man3 ATTRIBUTES; manual safety annotations) |
| Ledger ID | `GLIBC-gethostbyname` (FULL, obsolete-family entry), siblings grouped; `h_errno` per the `netdb.h` header |

## Declaration and gates

```text
struct hostent *gethostbyname(const char *name);
struct hostent *gethostbyname2(const char *name, int af);   /* IPv6 Basic API */
struct hostent *gethostbyaddr(const void *addr, socklen_t length, int format);
int gethostbyname_r(..., struct hostent **result, int *h_errnop);  /* GNU */
```

`struct hostent` carries `h_name`, `h_aliases`, `h_addrtype`, `h_length`, `h_addr_list` (and `h_addr` as `h_addr_list[0]`); addresses are in network byte order (manual, *Host Names*).

## Semantics

`gethostbyname` searches the hosts database (NSS `hosts` chain, so `/etc/nsswitch.conf` applies) and returns a pointer to a **statically allocated** structure that later calls overwrite (manual). `gethostbyname2` selects the address family, `gethostbyaddr` does the reverse lookup. Failure is reported through `h_errno` - a macro expanding to `*__h_errno_location()` in `netdb.h` - with values `HOST_NOT_FOUND`, `TRY_AGAIN`, `NO_RECOVERY`, `NO_ADDRESS`/`NO_DATA`; `NETDB_INTERNAL` means check `errno` (header + manual *h_errno* list). The `_r` forms take `result_buf`, a `char *buf`/`buflen` scratch area, and return an error number instead of using static storage.

## Gotchas and portability

- The static-buffer result is the classic multithreading bug; the manual: "The lookup functions above all have one thing in common: they are not reentrant and therefore unusable in multi-threaded applications."
- musl contrast: musl keeps the names (`src/network/gethostbyname.c` calls `gethostbyname2(name, AF_INET)`) on top of its fixed resolver, and `src/network/h_errno.c` gives `__h_errno_location()` per-thread storage backed by a global; no NSS, no `nsswitch.conf` (see the [musl catalog](../../musl/overview.md)).

## References

- man3 `gethostbyname.3`; glibc manual node *Host Names*; header `netdb.h`.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 `src/network/gethostbyname.c`.
