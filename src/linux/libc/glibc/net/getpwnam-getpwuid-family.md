# getpwnam(3) - glibc (getpwnam / getpwuid, _r twins, passwd iteration)

> The user database lookups (manual chapter *Users and Groups*, section *User Database*). `/etc/passwd` on most systems; on glibc the lookup is dispatched through NSS, so `nsswitch.conf` selects the modules.

| Field | Value |
|---|---|
| Header | `pwd.h` |
| Standards | `getpwnam`, `getpwuid`, `_r` twins, `setpwent`/`getpwent`/`endpwent`: POSIX.1-2018; `fgetpwent`, `putpwent`, `getpwent_r`: SVID/misc gates |
| Exported | `getpwnam`, `getpwuid`, `getpwent`, `setpwent`, `endpwent` `GLIBC_2.2.5` (nm, host glibc 2.41); `getpwnam_r`, `getpwuid_r` same version |
| Thread-safety | `getpwnam`/`getpwuid`: MT-Unsafe race:pwnam/pwuid, locale; `_r`: MT-Safe locale (man3 ATTRIBUTES) |
| Ledger ID | `GLIBC-getpwnam` (Grouped FULL), `GLIBC-getpwuid`, `GLIBC-getpwnam_r`, `GLIBC-getpwuid_r`, iteration rows `GLIBC-getpwent`/`GLIBC-setpwent`/`GLIBC-endpwent` |

## Declaration and gates

```text
struct passwd *getpwnam(const char *name);
struct passwd *getpwuid(uid_t uid);
int getpwnam_r(const char *name, struct passwd *pwd, char *buf, size_t buflen,
               struct passwd **result);            /* and getpwuid_r */
void setpwent(void); struct passwd *getpwent(void); void endpwent(void);
```

`struct passwd`: `pw_name`, `pw_passwd` (today almost always `x`), `pw_uid`, `pw_gid`, `pw_gecos`, `pw_dir`, `pw_shell` (manual, *User Data Structure*).

## Semantics

The lookup functions return a pointer to a statically allocated `passwd`, or NULL; because "not found" and error both return NULL, `errno` must be zeroed before the call (man3). `_r` forms fill the caller's `struct passwd` plus `buf`, return `0` on success (with `*result == pwd`) and put NULL in `*result` when no record matched; `ERANGE` means the buffer is too small - a suggested start size comes from `sysconf(_SC_GETPW_R_SIZE_MAX)`, which may return `-1` without setting `errno` (man3). Documented errors: `EINTR`, `EIO`, `EMFILE`, `ENFILE`, `ENOMEM`, `ERANGE`; "not found" may surface as 0, `ENOENT`, `ESRCH`, `EBADF`, `EPERM` or others (man3 ERRORS). `setpwent`/`getpwent`/`endpwent` scan the whole database entry by entry.

## Gotchas and portability

- musl contrast: `src/passwd/getpw_a.c` reads `/etc/passwd` with `fopen` and only consults nscd as a fallback; there is no NSS and no `nsswitch.conf` (see the [musl catalog](../../musl/overview.md)).
- The hash lives in the shadow database now; see [getgrnam family and shadow](./getgrnam-family-and-shadow.md).

## References

- glibc manual nodes *User Database*, *Lookup User*, *Scanning All Users*; man3 `getpwnam.3`.
- Header `pwd.h`; `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 sources as cited.
