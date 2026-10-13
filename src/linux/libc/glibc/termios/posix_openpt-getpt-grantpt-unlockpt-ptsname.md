# `posix_openpt` / `getpt` / `grantpt` / `unlockpt` / `ptsname` / `ptsname_r` (3) - glibc

> Split from the chapter *glibc: Low-Level Terminal Interface* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` (`posix_openpt` under `__USE_XOPEN2KXSI`; `grantpt`/`unlockpt`/`ptsname` under `__USE_XOPEN_EXTENDED`; `ptsname_r`/`getpt` under `__USE_GNU`) |
| Standards | POSIX.1-2001 / UNIX 98 (`posix_openpt`, `grantpt`, `unlockpt`, `ptsname`); GNU (`getpt`, `ptsname_r`) |
| Exported | `posix_openpt@@GLIBC_2.2.5` (weak), `getpt@@GLIBC_2.2.5` (weak), `grantpt@@GLIBC_2.2.5`, `unlockpt@@GLIBC_2.2.5`, `ptsname@@GLIBC_2.2.5`, `ptsname_r@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`posix_openpt`, `grantpt`, `unlockpt`, `ptsname_r`, `getpt`); MT-Unsafe race:ptsname (`ptsname`) -- `ptsname(3)`, `posix_openpt(3)`, `grantpt(3)`, `unlockpt(3)`, `getpt(3)` ATTRIBUTES |
| Ledger ID | GLIBC-posix_openpt, GLIBC-getpt, GLIBC-grantpt, GLIBC-unlockpt, GLIBC-ptsname, GLIBC-ptsname_r |

## Declaration and gates

```c
#include <stdlib.h>

int posix_openpt(int oflag);                     /* __USE_XOPEN2KXSI */
int grantpt(int fd);                             /* __USE_XOPEN_EXTENDED */
int unlockpt(int fd);                            /* __USE_XOPEN_EXTENDED */
char *ptsname(int fd);                           /* __USE_XOPEN_EXTENDED */
int ptsname_r(int fd, char *buf, size_t buflen); /* __USE_GNU */
int getpt(void);                                 /* __USE_GNU */
```

The three gate groups are consecutive blocks of
`/usr/include/stdlib.h` (lines 1108-1138). The man pages ask for
`_XOPEN_SOURCE >= 600` (`posix_openpt(3)`) and `_XOPEN_SOURCE >= 500`
since glibc 2.24 (`ptsname(3)`, `grantpt(3)`, `unlockpt(3)`);
`getpt(3)` and `ptsname_r` need `_GNU_SOURCE`.

## Semantics

`posix_openpt(oflag)` opens an unused pty master, `oflag` limited to
`O_RDWR | O_NOCTTY`, and on Linux is `open("/dev/ptmx", oflag)`
(`posix_openpt(3)` NOTES). `grantpt` chowns/chmods the slave (uid to
the real uid, mode 0620); with devpts the kernel did this at
`posix_openpt` time, so the traditional `pt_chown` helper is absent
(`grantpt(3)` NOTES). `unlockpt` must precede opening the slave.
`ptsname` returns the slave pathname in static storage; `ptsname_r` is
the reentrant form returning 0 or an error number. `getpt` is the
glibc-specific open of the multiplexor, equivalent to
`open("/dev/ptmx", O_RDWR)` on Linux (`getpt(3)`).

## Errors

`grantpt`: `EACCES`, `EBADF`, `EINVAL`; `unlockpt`: `EBADF` (fd not
open for writing), `EINVAL`; `ptsname`: `ENOTTY`, `ERANGE` (`ptsname_r`
only), `EINVAL` (null buf, glibc <= 2.25); `posix_openpt`/`getpt`: as
`open(2)`. `grantpt` behavior is unspecified with a `SIGCHLD` handler
installed (`grantpt(3)`).

## Gotchas and portability

- The classic sequence is `posix_openpt` -> `grantpt` -> `unlockpt` ->
  `ptsname` -> open slave; skipping `unlockpt` makes the slave open
  fail.
- `getpt` is glibc-only; musl 1.2.5 declares
  `posix_openpt`/`grantpt`/`unlockpt`/`ptsname` in `stdlib.h` and
  `ptsname_r` under `_GNU_SOURCE`, but has no `getpt`.

## References

- glibc manual: `terminal.texi` (pty allocation steps)
- man3: `posix_openpt(3)`, `grantpt(3)`, `unlockpt(3)`, `ptsname(3)`,
  `getpt(3)`; man4: `pts(4)`
- headers: `/usr/include/stdlib.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
