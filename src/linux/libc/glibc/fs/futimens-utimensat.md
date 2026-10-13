# `futimens` / `utimensat` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [utimensat(2)](../../../syscalls/fs-mounts-namespace/utimensat.md);
> microsecond predecessors:
> [futimes-lutimes-utime-utimes.md](futimes-lutimes-utime-utimes.md).

| Field | Value |
|---|---|
| Header | `sys/stat.h` (both) |
| Standards | POSIX.1-2008 (both) |
| Exported | `futimens@@GLIBC_2.6`, `utimensat@@GLIBC_2.6` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`utimensat(2)` ATTRIBUTES); manual marks both unaudited: AS-Unsafe, AC-Unsafe (corrupt) |
| Ledger ID | GLIBC-futimens, GLIBC-utimensat |

## Declaration and gates

```c
#include <sys/stat.h>

int utimensat(int dirfd, const char *pathname,
              const struct timespec times[2], int flags);
int futimens(int fd, const struct timespec times[2]);
```

`utimensat` is under `__USE_ATFILE`
(`/usr/include/x86_64-linux-gnu/sys/stat.h` lines 432-447, prototype at
433) and `futimens` under `__USE_XOPEN2K8` (lines 451-459, prototype at
452); both carry `__USE_TIME64_REDIRECTS` branches to `__utimensat64` /
`__futimens64`. Header gate per man page: `_POSIX_C_SOURCE >= 200809L`
since glibc 2.10 (`_ATFILE_SOURCE`/`_GNU_SOURCE` before).

## Semantics

Set atime and mtime with nanosecond precision: `times[0]` is the new
atime, `times[1]` the new mtime, each a `struct timespec` since the
Epoch; the stored value is the greatest the filesystem supports without
exceeding the request. Special `tv_nsec` values: `UTIME_NOW` sets the
timestamp to the current time, `UTIME_OMIT` leaves it unchanged
(`tv_sec` ignored in both cases); `times == NULL` sets both to now.
Permissions: setting both to now (NULL or two `UTIME_NOW`) needs write
access, ownership or privilege; any other change needs ownership
(`CAP_FOWNER`) or privilege. With both `UTIME_OMIT` no checks run and
nothing changes. `utimensat` resolves `pathname` relative to `dirfd`
(`AT_FDCWD` for cwd) and honors `AT_SYMLINK_NOFOLLOW` to act on the
link itself (`utimensat.2`, manual *File Times*).

## Gotchas and portability

- On Linux `futimens` is a library function over the `utimensat`
  syscall: `utimensat(fd, NULL, times, 0)` -- the kernel's
  nonstandard NULL-pathname extension (`utimensat.2`, C library/kernel
  ABI differences).
- Standards divergence: the manual says `flags` can combine
  `AT_EMPTY_PATH` and `AT_SYMLINK_NOFOLLOW`; `utimensat.2` allows only
  `AT_SYMLINK_NOFOLLOW` and returns `EINVAL` otherwise. Quoted as-is,
  not reconciled here.
- `utimensat` succeeds with both fields `UTIME_OMIT` even if the file
  does not exist (`utimensat.2` NOTES); it obsoletes `futimesat`.
- musl 1.2.5: `futimens` is the same one-liner over `utimensat`
  (`src/stat/futimens.c`); `utimensat` handles `UTIME_NOW` folding and
  time64 splitting (`src/stat/utimensat.c`).

## Errors

`EACCES`, `EBADF`, `EFAULT`, `EINVAL` (bad `flags`, `tv_nsec` outside
0..999999999 and not `UTIME_NOW`/`UTIME_OMIT`), `ELOOP`,
`ENAMETOOLONG`, `ENOENT`, `ENOTDIR`, `EPERM` (non-owner setting a
non-current timestamp; append-only/immutable files), `EROFS`, `ESRCH`
(`utimensat.2`).

## References

- glibc manual: `filesys.texi`, node *File Times*
- man2: `utimensat.2` (covers `futimens`; `futimens.3` is a `.so` alias)
- headers: `/usr/include/x86_64-linux-gnu/sys/stat.h` lines 432-461
- symbols: `nm -D --with-symbol-versions libc.so.6`
