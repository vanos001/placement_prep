# `setnetgrent` / `getnetgrent` / `innetgr` / `endnetgrent` (3) - glibc

> Split from the chapter *glibc: Users and Groups* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `netdb.h`, under `__USE_MISC` |
| Standards | SunOS invention; not in POSIX.1, but on most UNIX systems (`setnetgrent(3)` CONFORMING TO) |
| Exported | `getnetgrent`, `getnetgrent_r`, `setnetgrent`, `endnetgrent`, `innetgr` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `setnetgrent`, `getnetgrent_r`, `innetgr`: MT-Unsafe `race:netgrent`, `locale`; `endnetgrent`: `race:netgrent`; `getnetgrent`: `race:netgrent`, `race:netgrentbuf`, `locale` (`setnetgrent(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getnetgrent, GLIBC-getnetgrent_r, GLIBC-innetgr, GLIBC-setnetgrent, GLIBC-endnetgrent |

## Declaration and gates

```c
#define _DEFAULT_SOURCE            /* or _GNU_SOURCE */
#include <netdb.h>

int setnetgrent(const char *netgroup);
void endnetgrent(void);
int getnetgrent(char **host, char **user, char **domain);
int getnetgrent_r(char **host, char **user, char **domain,
                  char *buffer, size_t buflen);     /* GNU extension */
int innetgr(const char *netgroup, const char *host,
            const char *user, const char *domain);
```

The whole family lives in the `#ifdef __USE_MISC` block of
`/usr/include/netdb.h` (opened at line 364): `setnetgrent` at 393,
`endnetgrent` at 401, `getnetgrent` at 410, `innetgr` at 421,
`getnetgrent_r` at 430. Exposure per the man page: `_DEFAULT_SOURCE`
(since glibc 2.19), formerly `_BSD_SOURCE || _SVID_SOURCE`.

## Semantics

A netgroup is a list of `(hostname, username, domainname)` triples (or
nested netgroup names) served by the NSS database `netgroup`
(`/etc/netgroup`, dispatch via `/etc/nsswitch.conf`). `setnetgrent`
selects the netgroup to enumerate; `getnetgrent` yields the next
triple, with a NULL pointer meaning "matches anything"; the returned
pointers stay valid only until the next netgroup call, which is what
`getnetgrent_r` fixes by copying the strings into `buffer`.
`endnetgrent` frees the state. `innetgr` answers the membership
question directly, NULL arguments again acting as wildcards. All five
return 1 on success, 0 on failure (`setnetgrent(3)`).

## Gotchas and portability

- Netgroups are NIS-era infrastructure: musl 1.2.5 has neither the
  declarations nor any implementation (grep over
  `musl-clone/musl/{include,src}` finds no `netgrent`/`innetgr`).
- The man page's DESCRIPTION calls `innetgr` "thread-safe" while its
  own ATTRIBUTES table marks it `MT-Unsafe race:netgrent locale` -- the
  table is the rating to trust, since `innetgr` dispatches through the
  same shared NSS state.
- In the BSD implementation `setnetgrent` returns void; glibc returns
  int (`setnetgrent(3)` NOTES).

## References

- glibc manual: `users.texi`, nodes *Netgroup Database*, *Netgroup
  Data*, *Lookup Netgroup*, *Netgroup Membership*
- man3: `setnetgrent.3` (covers the whole family)
- header: `/usr/include/netdb.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
