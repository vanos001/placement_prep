# `getutent` / `getutid` / `getutline` / `pututline` / `utmpname` (3) - glibc

> Split from the chapter *glibc: Users and Groups* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `utmp.h` (base decls unconditional; the `_r` twins under `__USE_MISC`) |
| Standards | XPG2 / SVr4; absent from POSIX.1-2001 and POSIX.1-2008, which standardize the `utmpx` family instead (`getutent(3)` CONFORMING TO) |
| Exported | `getutent`, `getutent_r`, `setutent`, `endutent`, `getutid`, `getutid_r`, `getutline`, `getutline_r`, `pututline`, `utmpname` all `@@GLIBC_2.2.5` weak (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `race:utent` (`getutent` adds `init`, `race:utentbuf`, `sig:ALRM`, `timer`; `getutid`/`getutline` add `sig:ALRM`, `timer`) (`getutent(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getutent, GLIBC-getutent_r, GLIBC-setutent, GLIBC-endutent, GLIBC-getutid, GLIBC-getutid_r, GLIBC-getutline, GLIBC-getutline_r, GLIBC-pututline, GLIBC-utmpname |

## Declaration and gates

```c
#include <utmp.h>

struct utmp *getutent(void);
struct utmp *getutid(const struct utmp *id);
struct utmp *getutline(const struct utmp *line);
struct utmp *pututline(const struct utmp *utmp_ptr);
void setutent(void);
void endutent(void);
int utmpname(const char *file);

int getutent_r(struct utmp *buffer, struct utmp **result);      /* __USE_MISC */
int getutid_r(const struct utmp *id, struct utmp *buffer,
              struct utmp **result);                            /* __USE_MISC */
int getutline_r(const struct utmp *line, struct utmp *buffer,
                struct utmp **result);                          /* __USE_MISC */
```

The seven base prototypes are unconditional (`/usr/include/utmp.h` lines
59-79); the reentrant twins sit in the `#ifdef __USE_MISC` block at lines
82-92. The man page gives the same exposure via `_GNU_SOURCE` or, since
glibc 2.19, `_DEFAULT_SOURCE` (`getutent(3)`).

## Semantics

The user accounting database (default `/var/run/utmp`, history log
`/var/log/wtmp`) must be read through this API, never opened directly
(manual, *User Accounting Database*). `utmpname` only stores an
alternative file name (0 on success, -1 on failure; it does not open or
test it). `setutent` rewinds the file, `getutent` reads successive
entries, `endutent` closes it. `getutid` searches forward for an entry
matching `ut_type` (`RUN_LVL`, `BOOT_TIME`, `NEW_TIME`, `OLD_TIME`) or
`ut_id` (`INIT_PROCESS`, `LOGIN_PROCESS`, `USER_PROCESS`,
`DEAD_PROCESS`); `getutline` matches `ut_line` among
`USER_PROCESS`/`LOGIN_PROCESS` entries. `pututline` writes the entry
into the slot `getutid` would find, appending if none fits. The `_r`
twins store the record in caller-supplied `buffer` and return 0 with the
pointer in `*result`, -1 on error; there are no `utmpx` equivalents
(`getutent(3)` NOTES).

## Gotchas and portability

- The non-`_r` readers return static storage overwritten by the next
  call; the `_r` twins fix the buffer race but all ten functions still
  share the file-cursor state, hence the common `race:utent` mark.
- `pututline` returns `void` in XPG2/SVID 2 and does so on AIX and
  HP-UX; glibc follows the HP-UX `_pututline` prototype.
- The `utmpx` functions are the portable spelling; on glibc they alias
  these (see [utmpx page](utmpx-getutxent-family.md)).
- musl 1.2.5 stubs the whole family: `src/legacy/utmpx.c` returns NULL
  and empty `void`s, `utmpname` fails with `ENOTSUP`, and `_PATH_UTMP`
  is `/dev/null/utmp` (`include/utmp.h`).

## Errors

`ENOMEM` (out of memory), `ESRCH` (record not found); `setutent`,
`pututline` and the readers can also fail with the errors of `open(2)`
(`getutent(3)`).

## References

- glibc manual: `users.texi`, nodes *User Accounting Database*,
  *Manipulating the Database*
- man3: `getutent.3` (covers `getutid`, `getutline`, `pututline`,
  `setutent`, `endutent`, `utmpname`, `utmpxname` and the `_r` twins)
- headers: `/usr/include/utmp.h`, `bits/utmp.h`, `paths.h`
- sibling page: [getlogin / utmp / lastlog overview](../net/getlogin-utmp-Lastlog.md)
- symbols: `nm -D --with-symbol-versions libc.so.6`
