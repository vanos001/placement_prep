# copy_file_range(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 326 / 377 / 285 / 391 (cached kernel tables; hub agrees) |
| Since (kernel) | 4.5 (man VERSIONS); cross-filesystem copies and API tightening 5.3 |
| Man page | man2/copy_file_range.2 (local cache, dated 2021-03-22; 5.19 error-semantics rewording from man7.org-current, see notes) |
| glibc wrapper | Declared in <fcntl.h> with _GNU_SOURCE; copy_file_range@@GLIBC_2.27 (nm -D on glibc 2.41); glibc 2.27 emulates in user space when the kernel lacks the call |
| Aliases covered | none |
| Ledger ID | SC-copy_file_range |

## Purpose

copy_file_range() performs an in-kernel copy of up to len bytes from fd_in to fd_out without bouncing the data through user space. Filesystems may accelerate it with reflinks (shared copy-on-write blocks) or server-side copy (NFS). Each offset pointer is optional: when off_in is NULL the copy starts at fd_in's file offset, which is then advanced; when non-NULL the offset is read from and updated in *off_in while the file offset stays put.

## Synopsis

```c
#define _GNU_SOURCE
#include <unistd.h>
ssize_t copy_file_range(int fd_in, off64_t *off_in,
                        int fd_out, off64_t *off_out,
                        size_t len, unsigned int flags);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| fd_in / fd_out | Regular files open for reading / writing; O_APPEND on fd_out fails with EBADF. Same file is allowed, but the ranges must not overlap. |
| off_in / off_out | NULL means "use and advance the file offset"; otherwise the caller-owned offset is updated by the number of bytes copied. |
| len | Maximum bytes to copy; fewer may be transferred. |
| flags | Must be 0 (EINVAL otherwise); reserved for future extensions. |

## Return value and errors

Returns the number of bytes copied; 0 means fd_in's offset was at or past EOF. On error -1 with errno: EBADF, EFBIG (file-size or RLIMIT_FSIZE limits, possibly with SIGXFSZ), EINVAL (flags nonzero, overlapping ranges, non-regular file), EIO, EISDIR, ENOMEM, ENOSPC, EOVERFLOW, EPERM (immutable fd_out), ETXTBSY (active swap file), EXDEV (cross-filesystem before 5.3).

## Flags and constants

No flags are defined yet; flags must be 0.

## Security and notes

- The 5.3 rework tightened argument checks; applications should target 5.3 semantics (man VERSIONS).
- Cross-filesystem copies first worked in 5.3; older kernels return EXDEV. Worklog 1-c records the man-pages 6.19 rewording (man7.org-current): since 5.19 a cross-filesystem attempt is expected to fail with EXDEV or EOPNOTSUPP, and EOPNOTSUPP is the documented error for unsupported device/filename operations.
- Sparse sources may have holes expanded in the copy; pairing the call in a loop with lseek(2) SEEK_DATA/SEEK_HOLE avoids that.
- Both descriptors' dispositions matter: the call can be interrupted, and short copies require looping.

## References

- man2/copy_file_range.2 in the cached man-pages tree (dated 2021-03-22).
- man-pages 6.19 copy_file_range.2 via man7.org (fetched during task 1-c; source-cache/fetched).
- [Syscalls ledger](../ledger.md) row SC-copy_file_range; kernel tables in source-cache/kernel.
- Siblings: [sendfile](sendfile.md), [splice](splice.md), [fallocate](fallocate.md).
