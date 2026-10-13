# dup(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | dup 32 / 41 / 23 / 41; dup2 33 / 63 / - / 63; dup3 292 / 330 / 24 / 358 (per-call table below) |
| Since (kernel) | dup, dup2 1.0; dup3 2.6.27 (glibc 2.9) |
| Man page | man2/dup.2 (dup2.2 and dup3.2 are .so aliases of it) |
| glibc wrapper | dup()/dup2() in <unistd.h>, POSIX.1-2001; dup3() needs _GNU_SOURCE and <fcntl.h> for the O_* constant; host glibc 2.41 exports dup3@@GLIBC_2.9 (nm -D); on architectures without a dup2 slot the glibc dup2() wrapper calls dup3(fd, fd2, 0) (bminor glibc sysdeps/unix/sysv/linux/dup2.c, fetched copy source-cache/fetched/glibc-dup2.c) |
| Aliases covered | dup2, dup3 |
| Ledger ID | SC-dup, SC-dup2, SC-dup3 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables (syscall_64.tbl, syscall_32.tbl, syscall_arm.tbl, syscall_generic.tbl):

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| dup | 32 | 41 | 23 | 41 | 1.0 |
| dup2 | 33 | 63 | - | 63 | 1.0 |
| dup3 | 292 | 330 | 24 | 358 | 2.6.27 |

dup2 has no slot in the asm-generic (arm64) table; there the glibc dup2() wrapper resolves to dup3(fd, fd2, 0) with the fd == fd2 degenerate case checked via fcntl(F_GETFL) (source named above).

## Purpose

dup() allocates a new file descriptor referring to the same open file description as oldfd, choosing the lowest unused number. The two descriptors are interchangeable: they share the file offset and the file status flags, so an lseek(2) through one moves the position seen through the other, and the same holds across fork. They do not share file descriptor flags: the duplicate always starts with FD_CLOEXEC off. dup2() makes newfd itself refer to oldfd's open file description, silently closing newfd first if it was open; the close-and-rebind is atomic, which is exactly what a close()/dup() pair cannot promise in a multithreaded program or with signal handlers that allocate descriptors. dup3() is dup2() plus a flags argument whose only value is O_CLOEXEC, and it refuses the degenerate dup3(fd, fd, ...) case that dup2() treats as a no-op.

## Synopsis

```c
#include <unistd.h>
int dup(int oldfd);
int dup2(int oldfd, int newfd);

#define _GNU_SOURCE
#include <fcntl.h>     /* Definition of O_* constants */
#include <unistd.h>
int dup3(int oldfd, int newfd, int flags);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| oldfd | Descriptor to duplicate; if invalid, the call fails and dup2() does not close newfd. |
| newfd | dup2()/dup3() target number. If it was open it is silently closed first (close errors are lost); if it equals oldfd, dup2() returns it unchanged, dup3() fails EINVAL. Out-of-range newfd (above RLIMIT_NOFILE): EBADF. |
| flags (dup3) | Must be 0 or O_CLOEXEC, which sets the close-on-exec flag atomically as part of the duplication; anything else is EINVAL. |

## Return value and errors

On success the new descriptor (dup2()/dup3() return newfd). On error, -1 and errno: EBADF (oldfd not open; or newfd out of the allowed range per RLIMIT_NOFILE), EBUSY (Linux-only race with open()/dup() during the dup2()/dup3() close-and-reuse step), EINTR (dup2()/dup3() interrupted by a signal), EINVAL (dup3: invalid flags or oldfd == newfd), EMFILE (per-process descriptor limit reached; dup() and F_DUPFD).

## Flags and constants

| Constant | Value | Since | Meaning |
|---|---|---|---|
| O_CLOEXEC | 02000000 | 2.6.23 (flag); dup3 since 2.6.27 | Set FD_CLOEXEC on the new descriptor in the same atomic step |

Value from /usr/include/asm-generic/fcntl.h (octal, as on open.md); dup3 is the only call of this family that accepts a flags argument, and O_CLOEXEC is its only defined value (man2/dup.2).

## Security and notes

- FD_CLOEXEC discipline: setting close-on-exec after dup2() with a separate fcntl(F_SETFD) races with a concurrent fork+execve in another thread and can leak the descriptor into the child; dup3(oldfd, newfd, O_CLOEXEC) closes that race (man2/dup.2; same warning on open.md and fcntl.md F_SETFD).
- Lost close errors: if newfd was open, any error its close would have reported is discarded; the man page's pattern is dup(newfd) first to get a checkable duplicate, then dup2(), then close the duplicate if you must observe close errors.
- dup2() vs fcntl(F_DUPFD): both duplicate, but F_DUPFD takes a lower bound (>= arg), never closes anything, and returns a different error for an out-of-range argument (fcntl.md).
- The EBUSY error is Linux-specific and transient; retry.
- Descriptors created here are closed by close_range() and close(2) (close_range.md, see the [domain hub](overview.md) for the close page).

## References

- man2/dup.2 in the cached man-pages tree (dated 2021-03-22); .so aliases dup2.2, dup3.2.
- glibc dup2() fallback: bminor glibc master sysdeps/unix/sysv/linux/dup2.c (fetched copy source-cache/fetched/glibc-dup2.c).
- Constants: /usr/include/asm-generic/fcntl.h (O_CLOEXEC).
- [Syscalls ledger](../ledger.md) rows SC-dup, SC-dup2, SC-dup3; siblings [open](open.md), [fcntl](fcntl.md), [close_range](close_range.md); [domain hub](overview.md).
