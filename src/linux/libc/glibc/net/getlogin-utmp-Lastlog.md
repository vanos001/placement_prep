# getlogin(3) - glibc (getlogin, the utmp database, wtmp writers and lastlog)

> Login-name lookup and the user accounting database (manual sections *Who Logged In* and *User Accounting Database*). This is the data source `who(1)`-style tools read.

| Field | Value |
|---|---|
| Header | `unistd.h` (`getlogin`), `utmp.h` (utmp + `login`/`logout`/`logwtmp`/`updwtmp`/`utmpname`), `utmpx.h` (XPG variants), `lastlog.h` |
| Standards | `getlogin`: POSIX.1-2018; `utmp.h` family: SVID, not standardized (manual portability note); `utmpx.h` family: XPG/POSIX XSI |
| Exported | `getlogin` `GLIBC_2.2.5`; `getutent`, `setutent`, `endutent`, `pututline`, `utmpname`, `updwtmp` `GLIBC_2.2.5`; `login`, `logout`, `logwtmp` default `GLIBC_2.34` with compat `@GLIBC_2.2.5` (nm, host glibc 2.41; moved out of libutil) |
| Thread-safety | `getlogin`: MT-Unsafe race:getlogin, race:utent (static buffer); utmp scanners: MT-Unsafe race:utent (manual safety annotations) |
| Ledger ID | `GLIBC-getlogin` (persona row), `GLIBC-getutent`/`GLIBC-setutent`/`GLIBC-endutent`/`GLIBC-pututline`/`GLIBC-utmpname` (utmp one-row group), `GLIBC-updwtmp`/`GLIBC-login`/`GLIBC-logout`/`GLIBC-logwtmp` (utmp/wtmp writer rows) |

## Declaration and gates

```text
char *getlogin(void);
struct utmp *getutent(void);  void setutent(void);  void endutent(void);
struct utmp *pututline(const struct utmp *ut);
int utmpname(const char *file);            /* _PATH_UTMP, _PATH_WTMP */
void updwtmp(const char *wtmp_file, const struct utmp *ut);
```

`struct utmp` fields include `ut_type` (`EMPTY` ... `USER_PROCESS`, `DEAD_PROCESS`), `ut_pid`, `ut_line`, `ut_id`, `ut_user`, `ut_host`, `ut_tv` (manual, *Manipulating the Database*).

## Semantics

`getlogin` returns the name of the user logged in on the process's controlling terminal, from a statically allocated string; `cuserid` (deprecated, removed from newer POSIX) answers the effective-uid question instead (manual, *Who Logged In*). The accounting database lives in `/var/run/utmp` (`_PATH_UTMP`) with the history log `/var/log/wtmp` (`_PATH_WTMP`) - the manual insists these files are never opened directly. `setutent` rewinds, `getutent` reads forward, `pututline` writes, `utmpname` redirects to another file (it only stores the name, it does not test it). `updwtmp` appends to a wtmp-style log. `lastlog` (`_PATH_LASTLOG`, `struct lastlog` with `ll_time`, `ll_line`, `ll_host` in `bits/utmp.h`) records per-user last login and has no dedicated libc API beyond the header.

## Gotchas and portability

- glibc 2.40 NEWS: the `ll_time`/`ut_time`-style 32-bit fields switched from signed to unsigned, covering timestamps to year 2106; applications are still told to migrate off `<utmp.h>` because of locking and session-management problems.
- musl contrast: musl 1.2.5 stubs the whole utmp family out - `src/legacy/utmpx.c` defines `getutent`/`getutxent` to return NULL, `pututline`/`pututxline` as no-ops, and `utmpname` fails with `ENOTSUP`; there is no `login`/`logout`/`logwtmp` at all. Its `getlogin` (`src/unistd/getlogin.c`) just returns `getenv("LOGNAME")`, unlike glibc's ttyname + utmp scan.

## References

- glibc manual nodes *Who Logged In*, *User Accounting Database*; man3 `getlogin.3`, `getutent.3`.
- Headers `utmp.h`, `utmpx.h`, `paths.h`, `lastlog.h`; `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 `src/legacy/utmpx.c`, `src/unistd/getlogin.c`.
