# fallocate(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 285 / 324 / 47 / 352 (cached kernel tables; hub agrees) |
| Since (kernel) | 2.6.23 (man VERSIONS); glibc wrapper 2.10, FALLOC_FL_* in glibc headers since 2.18 |
| Man page | man2/fallocate.2 (local cache, dated 2019-11-19) |
| glibc wrapper | Declared in <fcntl.h> with _GNU_SOURCE; fallocate/fallocate64@@GLIBC_2.10 (nm -D on glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-fallocate |

## Purpose

fallocate() manipulates the disk space allocated to the byte range [offset, offset+len) of the file referred to by fd. With mode 0 it preallocates the range: the range is initialized to zeros, the file size grows if offset+len exceeds it, and subsequent writes into the range are guaranteed not to fail for lack of space. It is the optimal in-kernel backing for posix_fallocate(3); allocation is done in block-size chunks, so more space than requested may be reserved.

## Synopsis

```c
#define _GNU_SOURCE
#include <fcntl.h>
int fallocate(int fd, int mode, off_t offset, off_t len);
```

## Arguments and behavior

fd must be open for writing and refer to a regular file or directory. The mode argument selects the operation; flags can be combined only where stated:

| Flag (linux/falloc.h) | Value | Since | Meaning |
|---|---|---|---|
| FALLOC_FL_ALLOCATE_RANGE | 0x00 | - | Name for the default operation (mode 0) |
| FALLOC_FL_KEEP_SIZE | 0x01 | - | Do not change the file size even if offset+len passes EOF; useful for zeroed append preallocation |
| FALLOC_FL_PUNCH_HOLE | 0x02 | 2.6.38 | Deallocate the range (hole); must be ORed with KEEP_SIZE; reads return zeros |
| FALLOC_FL_NO_HIDE_STALE | 0x04 | - | Reserved codepoint (header comment) |
| FALLOC_FL_COLLAPSE_RANGE | 0x08 | 3.15 | Remove the range without leaving a hole; block-size aligned; range must not reach EOF; no other flags |
| FALLOC_FL_ZERO_RANGE | 0x10 | 3.15 | Zero the range, preferably via unwritten extents; combine with KEEP_SIZE to keep the size |
| FALLOC_FL_INSERT_RANGE | 0x20 | 4.1 | Insert a hole, shifting data upward; block-size aligned; offset must be below EOF; no other flags |
| FALLOC_FL_UNSHARE_RANGE | 0x40 | header-sourced | Make shared extents private so writes cannot fail for space; allocate-mode only (header comment; man page documents it, since version not dated in the cached copy) |

## Return value and errors

Returns 0 on success; -1 with errno: EBADF, EFBIG, EINTR, EINVAL (negative offset, len <= 0, misaligned COLLAPSE/INSERT, flag combinations, non-regular file for the range modes), EIO, ENODEV, ENOSPC, ENOSYS, EOPNOTSUPP (filesystem lacks the operation), EPERM (immutable file; PUNCH/COLLAPSE/INSERT on append-only; file seal), ESPIPE (pipe/FIFO), ETXTBSY (executing file for COLLAPSE/INSERT).

## Flags and constants

Flag values above are from the installed /usr/include/linux/falloc.h; filesystem support per flag (XFS, ext4, Btrfs, tmpfs, gfs2, SMB3) is listed in the man page and varies.

## Security and notes

- PUNCH_HOLE with KEEP_SIZE is the disk-space counterpart of madvise(MADV_DONTNEED); it never shortens the file.
- fallocate() can be refused with EPERM by F_SEAL_SHRINK/GROW seals on a memfd (fcntl.md).
- On glibc before 2.18 the FALLOC_FL_* macros were missing, so code hardcoded the values.

## References

- man2/fallocate.2 in the cached man-pages tree (dated 2019-11-19).
- Header: /usr/include/linux/falloc.h (all FALLOC_FL_* values).
- [Syscalls ledger](../ledger.md) row SC-fallocate; kernel tables in source-cache/kernel.
- Siblings: [truncate](truncate.md) (shorten), [copy_file_range](copy_file_range.md).
