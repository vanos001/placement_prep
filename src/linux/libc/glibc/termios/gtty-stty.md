# `gtty` / `stty` (3) - glibc

> Split from the chapter *glibc: Low-Level Terminal Interface* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sgtty.h` (no feature-test gate inside the header) |
| Standards | BSD legacy (4.2BSD; not in POSIX or ISO) |
| Exported | `gtty@@GLIBC_2.2.5`, `stty@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (manual @safety annotations; the calls are plain ioctls) |
| Ledger ID | GLIBC-gtty, GLIBC-stty |

## Declaration and gates

```c
#include <sgtty.h>

int gtty(int fd, struct sgttyb *params);
int stty(int fd, const struct sgttyb *params);
```

Declared unconditionally in `/usr/include/sgtty.h` (lines 27-35), which
includes `<sys/ioctl.h>` and forward-declares `struct sgttyb`. The
manual documents the pair under *BSD Terminal Modes* with standards
"BSD, sgtty.h".

## Semantics

`gtty` fills `*params` with the terminal's BSD-style attributes and
`stty` sets them; both are thin wrappers over the `TIOCGETP` /
`TIOCSETP` ioctls (manual, *BSD Terminal Modes*). `struct sgttyb`
carries `sg_ispeed`, `sg_ospeed`, `sg_erase`, `sg_kill` and
`sg_flags` -- the pre-termios BSD line-discipline state.

## Gotchas and portability

- Effectively dead on Linux: the manual states that even with glibc
  these functions "simply fail with `errno` = `ENOSYS` with many
  kernels, including Linux" (*BSD Terminal Modes*).
- Verified on this host: `sgttyb` and `TIOCGETP` are defined nowhere in
  the installed headers (`bits/ioctl-types.h` has neither), so
  `sgtty.h`'s own comment applies -- "the functions are just stubs that
  return ENOSYS".
- Modern equivalents: `tcgetattr`/`tcsetattr` (termios), documented in
  the same manual chapter chain; `stty(1)` is the unrelated coreutils
  command of the same name.
- musl 1.2.5: no `sgtty.h`, no `gtty`/`stty` (verified absence).

## References

- glibc manual: `terminal.texi`, node *BSD Terminal Modes*
- headers: `/usr/include/sgtty.h`,
  `/usr/include/x86_64-linux-gnu/bits/ioctl-types.h` (negative evidence)
- symbols: `nm -D --with-symbol-versions libc.so.6`
