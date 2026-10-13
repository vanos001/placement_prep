# `utime` / `utimes` / `futimes` / `lutimes` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Nanosecond
> successors: [futimens-utimensat.md](futimens-utimensat.md).

| Field | Value |
|---|---|
| Header | `utime.h` (`utime`); `sys/time.h` (`utimes`, `futimes`, `lutimes`) |
| Standards | POSIX.1-2001 (`utime`; POSIX.1-2008 marks it obsolete), 4.3BSD/POSIX.1-2001 (`utimes`); no standard, BSD-only (`futimes`, `lutimes`) |
| Exported | `utime@@GLIBC_2.2.5`, `utimes@@GLIBC_2.2.5`, `futimes@@GLIBC_2.3`, `lutimes@@GLIBC_2.3` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`futimes(3)` ATTRIBUTES covers `futimes`/`lutimes`); `utime`/`utimes`: MT-Safe, AS-Safe, AC-Safe (manual; `utime.2` has no ATTRIBUTES table) |
| Ledger ID | GLIBC-utime, GLIBC-utimes, GLIBC-futimes, GLIBC-lutimes |

## Declaration and gates

```c
#include <utime.h>
struct utimbuf { time_t actime; time_t modtime; };
int utime(const char *file, const struct utimbuf *times);

#include <sys/time.h>
int utimes(const char *file, const struct timeval tvp[2]);
int lutimes(const char *file, const struct timeval tvp[2]);
int futimes(int fd, const struct timeval tvp[2]);
```

`utime` is declared ungated in `/usr/include/utime.h` (prototype line
50, `struct utimbuf` lines 36-45, `__utime64` redirect). `utimes` sits
ungated in `sys/time.h` (line 162, `__utimes64` redirect); `lutimes`
(line 189) and `futimes` (line 193) are under `#ifdef __USE_MISC`
(lines 186+), matching `futimes.3`'s `_DEFAULT_SOURCE` gate.

## Semantics

All four set atime and mtime and leave ctime to the system. `utime`
has 1-second resolution through `struct utimbuf`; `utimes` takes
`timeval` pairs (`tvp[0]` atime, `tvp[1]` mtime) at microsecond
resolution; a NULL times argument sets both stamps to the current time.
Permission rules (`utime.2`): setting both to now requires privileges,
ownership, or write permission for the file; any other change requires
ownership or privileges. `futimes` does the same via an open
descriptor; `lutimes` does not dereference -- a symlink's own stamps
are changed (`futimes.3`, manual *File Times*).

## Gotchas and portability

- glibc builds the modern trio on the kernel's `utimensat` syscall:
  the manual's safety comments describe `futimes` converting to
  `timespec` and falling back to a `/proc/self/fd` symlink, and
  `lutimes` using `AT_SYMLINK_NOFOLLOW`; `futimes.3` dates `lutimes`
  at glibc 2.6 / kernel 2.6.22 and lists `ENOSYS` when `/proc` is
  unavailable.
- `utime` is POSIX-obsoleted; new code should use `futimens`/
  `utimensat` (`utime.2` header note: "modern applications may prefer").
- Immutable/append-only files: timestamps other than "now" are
  rejected (`utime.2` NOTES).
- musl 1.2.5: `utime` converts to `utimensat`
  (`src/time/utime.c`), `utimes` to `futimesat`
  (`src/linux/utimes.c`), `futimes` to `futimens`
  (`src/legacy/futimes.c`), `lutimes` to
  `utimensat(AT_FDCWD, ..., AT_SYMLINK_NOFOLLOW)`
  (`src/legacy/lutimes.c`).

## Errors

`EACCES` (prefix search denied, or NULL-times write-permission case),
`ENOENT`, `EPERM` (non-owner with non-NULL times), `EROFS`
(`utime.2`); `futimes` adds `EBADF` and `ENOSYS` (`futimes.3`).

## References

- glibc manual: `filesys.texi`, node *File Times*
- man2/man3: `utime.2` (covers `utimes`), `futimes.3` (covers `lutimes`)
- headers: `/usr/include/utime.h`; `/usr/include/x86_64-linux-gnu/sys/time.h` lines 162, 186-204
- symbols: `nm -D --with-symbol-versions libc.so.6`
