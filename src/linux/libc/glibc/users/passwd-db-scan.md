# `getpwent` / `fgetpwent` / `putpwent` / `setpwent` / `endpwent` (3) - glibc

> Split from the chapter *glibc: Users and Groups* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `pwd.h` (+ `sys/types.h`); `fgetpwent`/`putpwent` and the `_r` twins under `__USE_MISC` |
| Standards | `getpwent`, `setpwent`, `endpwent`: POSIX.1-2001/2008, SVr4, 4.3BSD; `fgetpwent`, `putpwent`: SVr4; `getpwent_r`, `fgetpwent_r`: GNU/SVID, "not (yet) standardized" (`pwd.h` comment) |
| Exported | `getpwent`, `getpwent_r`, `fgetpwent`, `fgetpwent_r`, `setpwent`, `endpwent`, `putpwent` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `getpwent`: MT-Unsafe `race:pwent`, `race:pwentbuf`, `locale`; `setpwent`/`endpwent`: `race:pwent`, `locale`; `fgetpwent`: `race:fgetpwent`; `getpwent_r`: `race:pwent`, `locale`; `fgetpwent_r`: MT-Safe; `putpwent`: MT-Safe `locale` (`getpwent(3)`, `fgetpwent(3)`, `putpwent(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getpwent, GLIBC-getpwent_r, GLIBC-fgetpwent, GLIBC-fgetpwent_r, GLIBC-setpwent, GLIBC-endpwent, GLIBC-putpwent |

## Declaration and gates

```c
#include <sys/types.h>
#include <pwd.h>

void setpwent(void);
void endpwent(void);
struct passwd *getpwent(void);

struct passwd *fgetpwent(FILE *stream);            /* __USE_MISC */
int putpwent(const struct passwd *p, FILE *f);     /* __USE_MISC */
int getpwent_r(struct passwd *pwbuf, char *buf, size_t buflen,
               struct passwd **pwbufp);            /* __USE_MISC */
int fgetpwent_r(FILE *stream, struct passwd *pwbuf, char *buf,
                size_t buflen, struct passwd **pwbufp);  /* __USE_MISC */
```

`setpwent`/`endpwent`/`getpwent` sit in
`#if defined __USE_MISC || defined __USE_XOPEN_EXTENDED`
(`/usr/include/pwd.h` lines 67-85); `fgetpwent`/`putpwent` in
`#ifdef __USE_MISC` (lines 87-104); the `_r` twins are also under
`__USE_MISC` (declarations at lines 139 and 169).

## Semantics

`getpwent` walks the password database entry by entry -- `/etc/passwd`
through NSS, so NIS or LDAP backends can serve it too. `setpwent`
rewinds to the first entry, `endpwent` closes the database. `fgetpwent`
parses the next record from a caller-opened `FILE *` in `/etc/passwd`
format; `putpwent` writes a `struct passwd` to a stream in the same
format. The `_r` twins store the record plus its strings in caller
buffers, return 0 with the pointer in `*pwbufp` on success, an error
number with `*pwbufp` NULL on failure or end of data
(`getpwent_r(3)`).

## Gotchas and portability

- `getpwent` returns static storage also shared with `getpwnam` and
  `getpwuid`; to distinguish end-of-file from error, set `errno` to
  zero before the call (`getpwent(3)` RETURN VALUE).
- See [getpwnam/getpwuid page](../net/getpwnam-getpwuid-family.md) for
  the by-name/by-id lookups of the same database.
- musl 1.2.5: `getpwent`, `fgetpwent`, `putpwent` are present
  (`src/passwd/`, plain file parsing, no NSS); the enumerator `_r`
  twins are absent -- only `getpwnam_r`/`getpwuid_r` exist
  (`src/passwd/getpw_r.c`).

## Errors

`getpwent`: `EINTR`, `EIO`, `EMFILE`, `ENFILE`, `ENOMEM`, `ERANGE`;
`fgetpwent`: `ENOMEM`; `_r` twins: `ENOENT` (no more entries), `ERANGE`
(buffer too small, retry larger).

## References

- glibc manual: `users.texi`, nodes *User Database*, *Scanning All
  Users*, *Writing a User Entry*
- man3: `getpwent.3`, `getpwent_r.3` (covers `fgetpwent_r`),
  `fgetpwent.3`, `putpwent.3`
- headers: `/usr/include/pwd.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
