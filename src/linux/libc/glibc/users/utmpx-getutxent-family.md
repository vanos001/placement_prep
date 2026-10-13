# `getutxent` / `getutxid` / `getutxline` / `pututxline` / `setutxent` / `endutxent` (3) - glibc

> Split from the chapter *glibc: Users and Groups* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `utmpx.h` (six POSIX functions unconditional; `utmpxname` under `__USE_GNU`) |
| Standards | XPG4.2; included in POSIX.1 via XSI (`getutent(3)` CONFORMING TO, manual *XPG Functions*) |
| Exported | `getutxent`, `getutxid`, `getutxline`, `pututxline`, `setutxent`, `endutxent`, `utmpxname` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `race:utent` -- on glibc the `x` functions are aliases of the `utmp.h` originals (manual *XPG Functions*) |
| Ledger ID | GLIBC-getutxent, GLIBC-getutxid, GLIBC-getutxline, GLIBC-pututxline, GLIBC-setutxent, GLIBC-endutxent, GLIBC-utmpxname |

## Declaration and gates

```c
#include <utmpx.h>

void setutxent(void);
void endutxent(void);
struct utmpx *getutxent(void);
struct utmpx *getutxid(const struct utmpx *id);
struct utmpx *getutxline(const struct utmpx *line);
struct utmpx *pututxline(const struct utmpx *utmpx);

int utmpxname(const char *file);      /* __USE_GNU */
```

The six XPG prototypes are unconditional (`/usr/include/utmpx.h` lines
53-83); `utmpxname` sits in the `#ifdef __USE_GNU` block at lines
86-93, next to `updwtmpx`, `getutmp` and `getutmpx`.

## Semantics

Same contracts as the `utmp.h` family with `struct utmpx` records:
`setutxent` rewinds the database, `getutxent` reads the next entry,
`endutxent` closes it, `getutxid` searches by `ut_type` or `ut_id`,
`getutxline` by `ut_line`, `pututxline` writes an entry (rewinding or
searching first, per the `ut_type` of the argument). `utmpxname` is the
glibc-only file-name selector and is not specified by POSIX
(`getutent(3)`). The header's comments mark `setutxent`, `endutxent`,
`getutxent`, `getutxid`, `getutxline` and `pututxline` as possible
cancellation points (comments above the prototypes, lines 50-83), a
detail the `utmp.h` declarations do not spell out.

## Gotchas and portability

- On Linux, glibc keeps no parallel `utmpx` file: `struct utmpx` is
  identical to `struct utmp`, and the `x` functions are plain aliases
  of their counterparts (`getutent(3)` CONFORMING TO; manual node *XPG
  Functions*). On other systems `utmpx` is a superset with parallel
  `utmpx`/`wtmpx` files.
- POSIX specifies no `_r` forms here; use `getutmp`/`getutmpx`
  (see [conversion page](getutmp-getutmpx.md)) when structures must move
  between the two spellings.
- The `ut_type` constants (`EMPTY` through `DEAD_PROCESS`, values 0-8,
  `bits/utmp.h` lines 103-113) are shared with `utmp.h` (manual *XPG
  Functions* vtable).
- musl 1.2.5: same story as `utmp` -- all six functions plus
  `utmpxname` are stubs in `src/legacy/utmpx.c` returning NULL, doing
  nothing, or failing with `ENOTSUP`.

## References

- glibc manual: `users.texi`, nodes *XPG Functions*,
  *Manipulating the Database*
- man3: `getutent.3` (POSIX.1 synopsis lists the whole `utmpx` family;
  `getutxent.3` is a link to it)
- headers: `/usr/include/utmpx.h`, `bits/utmpx.h`
- siblings: [utmp page](utmp-getutent-family.md),
  [login page](login-logout-login_tty.md)
- symbols: `nm -D --with-symbol-versions libc.so.6`
