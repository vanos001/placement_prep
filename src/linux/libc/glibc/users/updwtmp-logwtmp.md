# `updwtmp` / `logwtmp` (3) - glibc

> Split from the chapter *glibc: Users and Groups* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `utmp.h` |
| Standards | BSD/SVID origin; not in POSIX.1 (manual *Logging In and Out* groups them with the libutil-derived functions) |
| Exported | `updwtmp@@GLIBC_2.2.5` weak; `logwtmp@@GLIBC_2.34` default with compat `logwtmp@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `sig:ALRM`, `timer`; async-unsafe fd use (`acsfd`) -- manual safety annotations in `users.texi` (*Logging In and Out*) |
| Ledger ID | GLIBC-updwtmp, GLIBC-logwtmp |

## Declaration and gates

```c
#include <utmp.h>

void updwtmp(const char *wtmp_file, const struct utmp *utmp);
void logwtmp(const char *ut_line, const char *ut_name,
             const char *ut_host);
```

Both prototypes are unconditional in `/usr/include/utmp.h` (`updwtmp`
at lines 55-56, `logwtmp` at lines 51-52), directly under the
`login`/`logout` declarations.

## Semantics

The wtmp log (`/var/log/wtmp`, `_PATH_WTMP` from `paths.h`) records
every login, logout, boot and shutdown as a `struct utmp` record
appended over time. `updwtmp` appends the given entry to the named
wtmp-like file, creating or updating it in the layout the utmp readers
expect (manual, *Manipulating the Database*). `logwtmp` is a shortcut:
it builds the record itself -- `ut_line`, `ut_name` and `ut_host` from
the arguments, plus the current time and the calling process ID -- and
appends it to the standard wtmp file (manual, *Logging In and Out*).
Neither function returns a value; failures to open or write the log are
silent.

## Gotchas and portability

- Symbol archaeology: `login`, `logout`, `logwtmp` and `login_tty` lived
  in `libutil` until glibc 2.34 merged that library into libc, so
  binaries keep a `@GLIBC_2.2.5` compat version while new code links
  `@@GLIBC_2.34`; `updwtmp` was always in libc and shows only
  `@@GLIBC_2.2.5`. Applications written against old glibc needed
  `-lutil`; modern ones do not.
- The manual's portability note: the BSD `struct utmp` has only
  `ut_line`, `ut_name`, `ut_host` and `ut_time`, and older systems lack
  even `ut_host`.
- Writers must go through these wrappers rather than `open(2)`-ing the
  log directly; the file format and locking belong to libc (manual,
  *User Accounting Database*).
- musl 1.2.5: `updwtmp` is declared in `include/utmp.h` but resolves to
  the `updwtmpx` stub (`weak_alias` in `src/legacy/utmpx.c`); `logwtmp`
  does not exist at all.

## References

- glibc manual: `users.texi`, nodes *Manipulating the Database*
  (`updwtmp`), *Logging In and Out* (`logwtmp`)
- man3: `login.3` (wtmp writers context), `getutent.3` (file paths)
- headers: `/usr/include/utmp.h`, `paths.h`
- siblings: [login page](login-logout-login_tty.md),
  [utmp page](utmp-getutent-family.md)
- symbols: `nm -D --with-symbol-versions libc.so.6`
