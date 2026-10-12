# fsync(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | fsync 74 / 118 / 82 / 118; fdatasync 75 / 148 / 83 / 148 (per-call table below) |
| Since (kernel) | fsync 1.0; fdatasync 2.0 (hub agrees) |
| Man page | man2/fsync.2 (fdatasync.2 is a .so alias of it; local cache, dated 2021-03-22) |
| glibc wrapper | fsync needs no feature macros since glibc 2.16; fdatasync needs _POSIX_C_SOURCE >= 199309L or _XOPEN_SOURCE >= 500 |
| Aliases covered | fdatasync |
| Ledger ID | SC-fsync, SC-fdatasync |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| fsync | 74 | 118 | 82 | 118 | 1.0 |
| fdatasync | 75 | 148 | 83 | 148 | 2.0 |

## Purpose

fsync() flushes all modified in-core data of the file referred to by fd to the storage device, including metadata, and blocks until the device reports completion, so the data survives a crash or reboot. fdatasync() does the same but skips metadata that is not needed to retrieve the data correctly: st_atime/st_mtime changes need no flush, while a size change (for example from ftruncate(2)) does. Skipping unneeded metadata flushes is fdatasync's performance win.

## Synopsis

```c
#include <unistd.h>
int fsync(int fd);
int fdatasync(int fd);
```

## Arguments and behavior

The only argument is fd. fsync() does not guarantee the containing directory entry reached disk; durability of a newly created file requires fsync() on a directory fd as well. fd may be read-only (unlike some UNIX systems). In Linux 2.2 and earlier fdatasync() was equivalent to fsync() with no performance advantage.

## Return value and errors

Returns 0 on success; -1 with errno: EBADF, EIO (synchronization failure; since 4.13 write-back errors are reported to all fds that may have written the data, with NFS giving more precise per-fd reporting), EINVAL/EROFS (fd bound to a pipe, FIFO, or socket), ENOSPC, EDQUOT (deferred allocation on NFS).

## Flags and constants

No flag arguments. Related interfaces: O_DSYNC/O_SYNC open flags give per-write integrity (open.md), syncfs(2) flushes a whole filesystem (sync.md), and sync_file_range(2) starts or waits on write-out of a byte range without metadata or disk-cache guarantees (sync_file_range.md).

## Security and notes

- Deferred-write errors can surface at fsync()/close() time instead of write(2) time; ignoring the return value risks silent data loss (close.md).
- Older kernels and lesser-used filesystems may not flush the disk's write cache, in which case safe operation needs the cache disabled (hdparm(8)/sdparm(8)).

## References

- man2/fsync.2 in the cached man-pages tree; .so alias fdatasync.2.
- [Syscalls ledger](../ledger.md) rows SC-fsync, SC-fdatasync; kernel tables in source-cache/kernel.
- Siblings: [sync](sync.md), [sync_file_range](sync_file_range.md), [close](close.md).
- [Domain hub](overview.md) for status and sibling pages.
