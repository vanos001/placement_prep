# readahead(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 187 / 225 / 213 / 225 (cached kernel tables; hub agrees) |
| Since (kernel) | 2.4.13 (man VERSIONS); glibc support since 2.3 |
| Man page | man2/readahead.2 (local cache, dated 2021-03-22) |
| glibc wrapper | Declared in <fcntl.h> with _GNU_SOURCE; readahead@@GLIBC_2.3 (nm -D on glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-readahead (researched/BRIEF) |

## Purpose

readahead() initiates reading of count bytes of fd starting at offset into the page cache so that subsequent reads are served from cache instead of blocking on disk I/O. I/O is done in whole pages (offset rounds down, offset+count rounds up), never past EOF, and the file offset is left unchanged. The kernel schedules the reads in the background, but it can still block reading the metadata that locates the blocks -- common on ext2/3/4 large files with indirect blocks (man BUGS).

## Synopsis

```c
#define _GNU_SOURCE
#include <fcntl.h>
ssize_t readahead(int fd, off64_t offset, size_t count);
```

## Return value and errors

Returns 0 on success; -1 with errno: EBADF (fd invalid or not open for reading), EINVAL (fd does not refer to a file type readahead() supports).

## Security and notes

- The fd must be open for reading; a write-only descriptor fails EBADF.
- On 32-bit architectures needing aligned 64-bit arguments the signature differs (syscall(2); the ARM EABI example is in syscall.md).
- POSIX_FADV_WILLNEED (posix_fadvise.md) is the portable form.

## References

- man2/readahead.2 in the cached man-pages tree (dated 2021-03-22).
- [Syscalls ledger](../ledger.md) row SC-readahead; kernel tables in source-cache/kernel.
- Siblings: [posix_fadvise](posix_fadvise.md), [read](read.md).
