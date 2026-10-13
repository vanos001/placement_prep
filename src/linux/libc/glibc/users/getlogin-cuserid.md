# `getlogin` / `cuserid` (3) - glibc

> Split from the chapter *glibc: Users and Groups* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `getlogin`: `unistd.h`; `cuserid` and `L_cuserid`: `stdio.h` (also `unistd.h` for Unix98, glibc) |
| Standards | `getlogin`, `getlogin_r`: POSIX.1-2001/2008; `cuserid`: in POSIX 1988, dropped in POSIX.1-1990, present in SUSv2, removed since (`getlogin(3)` CONFORMING TO) |
| Exported | `getlogin@@GLIBC_2.2.5`, `cuserid@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `getlogin`: MT-Unsafe `race:getlogin`, `race:utent`, `sig:ALRM`, `timer`, `locale`; `cuserid`: MT-Unsafe `race:cuserid/!string`, `locale` (`getlogin(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getlogin, GLIBC-cuserid |

## Declaration and gates

```c
#include <unistd.h>
char *getlogin(void);

#include <stdio.h>
char *cuserid(char *string);   /* (__USE_XOPEN && !__USE_XOPEN2K) || __USE_GNU */
```

`getlogin` is unconditional (`/usr/include/unistd.h` line 881;
`getlogin_r` at 889 needs `_POSIX_C_SOURCE >= 199506L`).
`cuserid` appears in `/usr/include/stdio.h` lines 906-910 under
`#if (defined __USE_XOPEN && !defined __USE_XOPEN2K) || defined
__USE_GNU`, and again in `unistd.h` line 1186 for Unix98. The
`L_cuserid` constant (value 9) is defined in `stdio.h` lines 132-136
under `__USE_POSIX` with the same XOPEN/GNU condition.

## Semantics

`getlogin` returns a pointer to a static string with the name of the
user logged in on the process's controlling terminal, or NULL. glibc
derives it by taking the tty name of standard input and scanning the
utmp database for the matching `USER_PROCESS`/`LOGIN_PROCESS` entry
(manual safety comments: `ttyname_r` then `getutline_r`) -- hence the
`race:utent` mark and the `ENOENT`/`ENOTTY` errors beyond the POSIX
`EMFILE`, `ENFILE`, `ENXIO`, `ERANGE` set. `cuserid` answers a
different question: the user name belonging to the process's effective
user ID, i.e. `getpwuid(geteuid())`-style, returned into `string` if
given (at least `L_cuserid` bytes) or a static buffer. Both answers
differ under set-user-ID execution (manual, *Who Logged In*).

## Gotchas and portability

- `getlogin(3)` BUGS: glibc reads stdin where POSIX says `/dev/tty`
  ("A bug."), it is easy to fool via a mangled utmp file, and it "often
  gives only the first 8 characters". "Avoid `getlogin()` for
  security-related purposes."
- `cuserid`: "Nobody knows precisely what `cuserid()` does... Do not
  use `cuserid()`" -- use `getpwuid(geteuid())` instead; System V's
  version used the real ID, not the effective one.
- For most purposes `LOGNAME` from the environment is the flexible
  answer (manual, *Who Logged In*).
- musl 1.2.5: `cuserid` implemented via `getpwuid_r` in
  `src/legacy/cuserid.c`; `getlogin` (`src/unistd/getlogin.c`) just
  returns `getenv("LOGNAME")`, a weaker contract.
- Broader utmp context: [getlogin / utmp overview](../net/getlogin-utmp-Lastlog.md).

## References

- glibc manual: `users.texi`, node *Who Logged In*
- man3: `getlogin.3` (covers `getlogin_r`, `cuserid`)
- headers: `/usr/include/unistd.h`, `/usr/include/stdio.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
