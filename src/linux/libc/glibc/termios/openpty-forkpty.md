# `openpty` / `forkpty` (3) - glibc

> Split from the chapter *glibc: Low-Level Terminal Interface* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `pty.h` (no feature-test gate inside the header) |
| Standards | BSD functions, "present in glibc, not standardized in POSIX" (`openpty(3)` CONFORMING TO) |
| Exported | `openpty@@GLIBC_2.34` plus compat `openpty@GLIBC_2.2.5`, `forkpty@@GLIBC_2.34` plus compat `forkpty@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe locale both (`openpty(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-openpty, GLIBC-forkpty |

## Declaration and gates

```c
#include <pty.h>

int openpty(int *amaster, int *aslave, char *name,
            const struct termios *termp, const struct winsize *winp);
int forkpty(int *amaster, char *name,
            const struct termios *termp, const struct winsize *winp);
```

Both are declared unconditionally in `/usr/include/pty.h` (lines 33-42),
after including `<termios.h>` and `<sys/ioctl.h>`. The man page
synopsis still says "Link with `-lutil`".

## Semantics

`openpty` finds an available pseudoterminal and returns descriptors for
the master in `*amaster` and the slave in `*aslave`; if `name` is not
NULL the slave's filename is stored there, and non-NULL `termp`/`winp`
set the slave's initial termios attributes and window size. On failure
both functions return -1 with `errno` set; `openpty` fails with
`ENOENT` when no terminals are available (`openpty(3)`). `forkpty`
combines `openpty`, `fork(2)` and `login_tty(3)`: the child gets the
slave as controlling terminal and stdio and returns 0 there, the parent
returns the child pid with the master descriptor in `*amaster`
(`openpty(3)`).

## Gotchas and portability

- libutil is gone as a real library: since glibc 2.34 `openpty`/
  `forkpty` moved into libc proper -- nm shows `@@GLIBC_2.34` default
  versions with `@GLIBC_2.2.5` compat twins, and host
  `libutil.so.1` exports only `__libutil_version_placeholder` (nm,
  host). Linking `-lutil` still works through the stub.
- `login_tty(3)` (declared in `utmp.h`, not covered by a ledger row
  here) is the third function of the `pty.h`-family man page.
- musl 1.2.5: `pty.h` declares both and they live directly in libc
  (`musl src/misc/openpty.c`, `forkpty.c`) -- no libutil ever existed
  there.

## References

- glibc manual: `terminal.texi` (pty allocation)
- man3: `openpty(3)` (covers `forkpty`, `login_tty`); man4: `pts(4)`
- headers: `/usr/include/pty.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`,
  `nm -D libutil.so.1`
