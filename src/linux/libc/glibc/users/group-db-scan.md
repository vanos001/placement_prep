# `getgrent` / `fgetgrent` / `setgrent` / `endgrent` (3) - glibc

> Split from the chapter *glibc: Users and Groups* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `grp.h` (+ `sys/types.h`); `fgetgrent` and the `_r` twins under `__USE_MISC` |
| Standards | `getgrent`, `setgrent`, `endgrent`: POSIX.1-2001/2008, SVr4, 4.3BSD; `fgetgrent`: SVr4; `getgrent_r`, `fgetgrent_r`: GNU, "not (yet) standardized" (`grp.h` comment) |
| Exported | `getgrent`, `getgrent_r`, `fgetgrent`, `fgetgrent_r`, `setgrent`, `endgrent` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `getgrent`: MT-Unsafe `race:grent`, `race:grentbuf`, `locale`; `setgrent`/`endgrent`: `race:grent`, `locale`; `fgetgrent`: `race:fgetgrent`; `getgrent_r`: `race:grent`, `locale`; `fgetgrent_r`: MT-Safe (`getgrent(3)`, `getgrent_r(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getgrent, GLIBC-getgrent_r, GLIBC-fgetgrent, GLIBC-fgetgrent_r, GLIBC-setgrent, GLIBC-endgrent |

## Declaration and gates

```c
#include <sys/types.h>
#include <grp.h>

void setgrent(void);
void endgrent(void);
struct group *getgrent(void);

struct group *fgetgrent(FILE *stream);             /* __USE_MISC */
int getgrent_r(struct group *gbuf, char *buf, size_t buflen,
               struct group **gbufp);              /* __USE_MISC */
int fgetgrent_r(FILE *stream, struct group *gbuf, char *buf,
                size_t buflen, struct group **gbufp);  /* __USE_MISC */
```

`setgrent`/`endgrent`/`getgrent` are in
`#if defined __USE_MISC || defined __USE_XOPEN_EXTENDED`
(`/usr/include/grp.h` lines 56-74); `fgetgrent` in `#ifdef __USE_MISC`
(gate at line 76, declaration at 83); the `_r` twins are also under
`__USE_MISC` (declarations at lines 131 and 164).

## Semantics

`getgrent` scans the group database (normally `/etc/group`, possibly
NIS or LDAP through NSS) one record at a time; `struct group` carries
`gr_name`, `gr_passwd`, `gr_gid` and `gr_mem`, a NULL-terminated array
of member names. `setgrent` rewinds to allow repeated scans, `endgrent`
closes the database. `fgetgrent` reads records from a caller-supplied
stream in `/etc/group` format. The `_r` twins fill caller buffers and
return 0 with the result pointer in `*gbufp`, an error number with
`*gbufp` NULL on error or end of data (`getgrent_r(3)`).

## Gotchas and portability

- The `getgrent` result may live in static storage shared with
  `getgrgid` and `getgrnam`; never pass it to `free(3)` (`getgrent(3)`
  RETURN VALUE).
- To tell end-of-database from failure with `getgrent`, zero `errno`
  before the call.
- See [getgrnam family page](../net/getgrnam-family-and-shadow.md) for
  the keyed lookups of the same database. glibc additionally offers the
  writer `putgrent` under `__USE_GNU` (`/usr/include/grp.h` lines
  86-90); it is its own ledger row and not covered here.
- musl 1.2.5: `getgrent` and `fgetgrent` exist (`src/passwd/`); the
  enumerator `_r` twins are absent (`src/passwd/` has only
  `getgr_r.c` for the by-name/by-id lookups).

## Errors

`getgrent`: `EAGAIN` (NSS backend temporarily unavailable), `EINTR`,
`EIO`, `EMFILE`, `ENFILE`, `ENOENT` (backend misconfigured), `ENOMEM`,
`ERANGE`; `_r` twins: `ENOENT`, `ERANGE` (`getgrent(3)`, `getgrent_r(3)`).

## References

- glibc manual: `users.texi`, nodes *Group Database*, *Scanning All
  Groups*, *Database Example*
- man3: `getgrent.3`, `getgrent_r.3` (covers `fgetgrent_r`),
  `fgetgrent.3`
- headers: `/usr/include/grp.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
