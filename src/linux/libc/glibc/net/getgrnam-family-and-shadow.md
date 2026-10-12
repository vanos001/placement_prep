# getgrnam(3) - glibc (getgrnam / getgrgid, group iteration, and the shadow database)

> Group database lookups (manual section *Group Database*), plus the privileged shadow-password interface that `getpwnam`'s `x` convention points at.

| Field | Value |
|---|---|
| Header | `grp.h` (group), `shadow.h` (shadow) |
| Standards | `getgrnam`, `getgrgid`, `_r` twins, `setgrent`/`getgrent`/`endgrent`: POSIX.1-2018; `fgetgrent` SVID; the whole shadow API is GNU/shadow-suite, not POSIX |
| Exported | `getgrnam`, `getgrgid`, `getgrent`, `setgrent`, `endgrent`, `getspnam`, `getspnam_r` all `GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | Non-`_r`: MT-Unsafe race:grnam/grgid/getspnam, locale; `_r`: MT-Safe locale (man3 ATTRIBUTES) |
| Ledger ID | `GLIBC-getgrnam` (Grouped FULL), `GLIBC-getgrgid` and `_r` rows, `GLIBC-getspnam`/`GLIBC-getspnam_r` (Grouped FULL shadow entry) |

## Declaration and gates

```text
struct group *getgrnam(const char *name);
struct group *getgrgid(gid_t gid);
int getgrnam_r(..., struct group **result);   /* and getgrgid_r */
void setgrent(void); struct group *getgrent(void); void endgrent(void);
struct spwd  *getspnam(const char *name);     /* shadow.h */
int getspnam_r(const char *name, struct spwd *spwd, char *buf,
               size_t buflen, struct spwd **result);
```

`struct group`: `gr_name`, `gr_gid`, `gr_mem` (NULL-terminated member vector, manual *Group Data Structure*). `struct spwd` starts with `sp_namp` (login name) and `sp_pwdp` (hashed passphrase) (`shadow.h`).

## Semantics

`getgrnam`/`getgrgid` search `/etc/group` or its NSS `group` chain and return a statically allocated `struct group` that later calls overwrite; `_r` forms use caller buffers and return `ERANGE` when too small (manual, same protocol as the passwd family). `getspnam` reads the shadow database - "a shadow database that can only be accessed with special privileges" (manual, *User Database*). The man page documents `EACCES` when the caller lacks permission to read the shadow file; the hash itself is meant for PAM, not for applications.

## Gotchas and portability

- The manual's portability note for the shadow record: the file is `/etc/shadow` on the shadow suite layout; Julianne Haugh's shadow suite originated the API (man3 `getspnam.3` credits).
- musl 1.2.5 implements `getspnam` in `src/passwd/getspnam.c` reading `/etc/shadow` directly; no NSS.
- Direct access to `/etc/shadow` is still possible, which the man page lists as a design caveat - privilege separation belongs to PAM.

## References

- glibc manual nodes *Group Database*, *User Database*; man3 `getgrnam.3`, `getspnam.3`.
- Headers `grp.h`, `shadow.h`; `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 sources as cited.
