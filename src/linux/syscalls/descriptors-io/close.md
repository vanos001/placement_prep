# close(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 3 / 6 / 57 / 6 (cached kernel tables; hub agrees) |
| Since (kernel) | 1.0 |
| Man page | man2/close.2 (local cache, dated 2021-03-22) |
| glibc wrapper | close declared in <unistd.h>; plain POSIX wrapper |
| Aliases covered | none (close_range has its own page, close_range.md) |
| Ledger ID | SC-close |

## Purpose

close() closes a file descriptor so that it no longer refers to any file and may be reused. Any fcntl(2) record locks the process held on the file are removed regardless of which descriptor obtained them. If fd is the last descriptor referring to the underlying open file description, its resources are freed, and if it was also the last reference to an unlinked file, the file is deleted.

## Synopsis

```c
#include <unistd.h>
int close(int fd);
```

## Arguments and behavior

The only argument is fd. The kernel releases the fd number early in the operation, while the error-producing steps, such as flushing data, run afterwards. A blocked I/O system call in another thread keeps a reference to the open file description, so on Linux it may complete successfully after a concurrent close(2). close-on-exec disposition (FD_CLOEXEC or O_CLOEXEC) removes the descriptor at execve(2).

## Return value and errors

Returns 0 on success; -1 with errno: EBADF (fd not open), EINTR, EIO, and ENOSPC/EDQUOT (NFS deferred-write errors may surface here instead of at write(2) time).

## Flags and constants

No flag arguments. The related constant FD_CLOEXEC belongs to fcntl(2) and O_CLOEXEC to open(2); close_range(2) (kernel 5.9, x64 436) closes a whole fd interval and has its own page, [close_range](close_range.md).

## Security and notes

- Do not retry close() after a failure: the fd is already released, so a retry can close a descriptor reused by another thread (man NOTES).
- A successful close does not guarantee the data reached the disk; buffer-cache writes are deferred. Precede close() with fsync(2) where integrity matters, and still check the close() return, since failed writes can be reported only there.
- EINTR semantics differ across systems: on Linux the descriptor is closed even when EINTR is returned, but POSIX leaves the state unspecified.
- Closing descriptors while other threads may use them is unwise; fd reuse races are a classic bug source (see the reuse discussion on open.md).

## References

- man2/close.2 in the cached man-pages tree (dated 2021-03-22).
- [Syscalls ledger](../ledger.md) row SC-close; kernel tables in source-cache/kernel.
- Siblings: [close_range](close_range.md), [open](open.md), [fsync](fsync.md).
- [Domain hub](overview.md) for status and sibling pages.
