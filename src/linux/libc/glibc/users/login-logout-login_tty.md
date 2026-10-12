# `login` / `logout` / `login_tty` (3) - glibc

> Split from the chapter *glibc: Users and Groups* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `utmp.h` |
| Standards | BSD origin, not in POSIX.1 (`login(3)` CONFORMING TO); historical `libutil` members, merged into libc in glibc 2.34 |
| Exported | `login@@GLIBC_2.34`, `logout@@GLIBC_2.34`, `login_tty@@GLIBC_2.34`, each with compat `@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `login`, `logout`: MT-Unsafe `race:utent`, `sig:ALRM`, `timer`; `login_tty`: MT-Unsafe `race:ttyname` (`login(3)`, `openpty(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-login, GLIBC-logout, GLIBC-login_tty |

## Declaration and gates

```c
#include <utmp.h>

int login_tty(int fd);
void login(const struct utmp *entry);
int logout(const char *ut_line);
```

All three are unconditional in `/usr/include/utmp.h`: `login_tty` at
line 41, `login` at line 45, `logout` at line 48. No feature-test gate
is involved; there are no `_r` or `utmpx` twins.

## Semantics

`login_tty` makes `fd` the controlling terminal of the calling process
(`setsid` plus a `TIOCSCTTY`-style ioctl per the manual's implementation
notes), redirects stdin, stdout and stderr to it, and closes `fd`; it
returns 0 on success and -1 on error (manual, *Logging In and Out*).
`login` inserts an entry into the user accounting database: it sets
`ut_type` to `USER_PROCESS` and `ut_pid` to the process ID, derives
`ut_line` from the first of stdin/stdout/stderr that is a terminal
(stripping a leading `/dev/`; "???" if none is found, in which case the
record is not written to utmp), then writes the struct to utmp and a
copy to wtmp. `logout` finds the utmp entry matching `ut_line`, zeroes
`ut_name` and `ut_host`, stamps the time, sets `ut_type` to
`DEAD_PROCESS` and rewrites the record; it returns 1 on success, 0 on
error (`login(3)`).

## Gotchas and portability

- The trio is "Not in POSIX.1. Present on the BSDs." -- where
  `libutil` still provides them; on glibc >= 2.34 they are in libc
  proper and `-lutil` is no longer needed (nm: dual `GLIBC_2.34` /
  `GLIBC_2.2.5` versions).
- BSD spells the `ut_user` member `ut_name`; `<utmp.h>` defines
  `ut_name` as an alias for `ut_user` on glibc (manual, same node).
- `login` writes to wtmp even when no terminal was found, so utmp and
  wtmp can disagree for that case (manual, *Logging In and Out*).
- musl 1.2.5: `login_tty` is implemented (`src/misc/login_tty.c`, also
  declared in musl's `utmp.h`), but `login` and `logout` are absent
  entirely -- no declaration, no source.

## References

- glibc manual: `users.texi`, node *Logging In and Out*
- man3: `login.3` (covers `logout`), `login_tty.3` (link to `openpty.3`)
- headers: `/usr/include/utmp.h`, `paths.h`
- siblings: [updwtmp page](updwtmp-logwtmp.md),
  [utmp page](utmp-getutent-family.md)
- symbols: `nm -D --with-symbol-versions libc.so.6`
