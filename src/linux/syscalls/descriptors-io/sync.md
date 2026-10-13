# sync(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | sync 162 / 36 / 81 / 36; syncfs 306 / 344 / 267 / 373 (per-call table below) |
| Since (kernel) | sync 1.0; syncfs 2.6.39 (man VERSIONS; hub grouped row shows sync's 1.0) |
| Man page | man2/sync.2 (syncfs.2 is a .so alias of it; local cache, dated 2021-03-22) |
| glibc wrapper | sync: _XOPEN_SOURCE >= 500 or _DEFAULT_SOURCE; prototype void sync(void) since glibc 2.2.2 (int sync(void) returning 0 before). syncfs: _GNU_SOURCE, glibc 2.14 |
| Aliases covered | syncfs |
| Ledger ID | SC-sync, SC-syncfs |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| sync | 162 | 36 | 81 | 36 | 1.0 |
| syncfs | 306 | 344 | 267 | 373 | 2.6.39 |

## Purpose

sync() causes all pending modifications of filesystem metadata and cached file data to be written to the underlying filesystems. syncfs() (glibc 2.14) is like sync() but synchronizes only the filesystem containing the file referred to by fd, which bounds the cost for containers or multi-filesystem hosts. POSIX says sync() merely schedules the writes and may return early, but Linux waits for I/O completion, so sync()/syncfs() here give the same guarantee as fsync() on every file of the system or of the filesystem.

## Synopsis

```c
#include <unistd.h>
void sync(void);
int syncfs(int fd);
```

## Arguments and behavior

sync() takes no argument and returns nothing. syncfs() takes an open fd on any file of the target filesystem. Before kernel 1.3.20 Linux did not wait for I/O completion before returning. In mainline kernels before 5.8, syncfs() failed only with EBADF; since 5.8 it also reports errors if one or more inodes failed write-back since the last syncfs() call (commit 735e4ae5ba28, cited in the man page).

## Return value and errors

sync() is always successful (and returns no value). syncfs() returns 0 on success; -1 with errno: EBADF, EIO (an error during synchronization, possibly relating to any file or to filesystem metadata), ENOSPC, EDQUOT (deferred-allocation failures on NFS).

## Flags and constants

No flag arguments.

## Security and notes

- Per-file durability is better served by fsync(2)/fdatasync(2) (fsync.md); a full sync() also delays for unrelated dirty data.
- The void return of sync() means write-back errors are silently invisible there; syncfs() since 5.8 is the call that can report them.
- Data written to NFS or other deferred-allocation filesystems may report ENOSPC/EDQUOT at sync time rather than at write(2) time.

## References

- man2/sync.2 in the cached man-pages tree; .so alias syncfs.2.
- [Syscalls ledger](../ledger.md) rows SC-sync, SC-syncfs; kernel tables in source-cache/kernel.
- Siblings: [fsync](fsync.md), [sync_file_range](sync_file_range.md).
- [Domain hub](overview.md) for status and sibling pages.
