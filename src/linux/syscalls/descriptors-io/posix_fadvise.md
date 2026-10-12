# posix_fadvise(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | fadvise64 221 / 250 / 223 / -; fadvise64_64 - / 272 / - / -; arm_fadvise64_64 - / - / - / 270 (per-call table below) |
| Since (kernel) | 2.5.60 (man VERSIONS; ledger/hub rows carry 2.6, man-page value kept here); CONFIG_ADVISE_SYSCALLS-gated since 3.18 |
| Man page | man2/posix_fadvise.2 (fadvise64.2 is a .so alias; local cache, dated 2021-03-22) |
| glibc wrapper | posix_fadvise needs _POSIX_C_SOURCE >= 200112L; posix_fadvise/posix_fadvise64@@GLIBC_2.2.5 (nm -D on glibc 2.41); wrapper picks the arch-specific slot |
| Aliases covered | fadvise64, fadvise64_64, arm_fadvise64_64 |
| Ledger ID | SC-fadvise64, SC-fadvise64_64, SC-arm_fadvise64_64 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| fadvise64 | 221 | 250 | 223 | - | 2.5.60 |
| fadvise64_64 | - | 272 | - | - | 2.5.60 |
| arm_fadvise64_64 | - | - | - | 270 | 2.6.14 |

## Purpose

posix_fadvise() announces an intention to access file data in a pattern (sequential, random, once, soon, never), letting the kernel optimize. The advice applies to the range [offset, offset+len) of fd, or through EOF when len is 0; it is non-binding. Under Linux it works by adjusting the file's readahead window: NORMAL restores the default, SEQUENTIAL doubles it, RANDOM disables readahead entirely, and WILLNEED starts a nonblocking read into the page cache (readahead(2) is the explicit form).

## Synopsis

```c
#include <fcntl.h>
int posix_fadvise(int fd, off_t offset, off_t len, int advice);
```

## Arguments and behavior

| Advice (bits/fcntl-linux.h) | Value | Meaning |
|---|---|---|
| POSIX_FADV_NORMAL | 0 | Default readahead window |
| POSIX_FADV_SEQUENTIAL | 1 | Sequential access; doubled readahead window |
| POSIX_FADV_RANDOM | 2 | Random access; readahead disabled for the file |
| POSIX_FADV_NOREUSE | 3 | Accessed once; a no-op since kernel 2.6.18 (WILLNEED-like before, probably a bug) |
| POSIX_FADV_WILLNEED | 4 | Needed soon; starts nonblocking readahead into page cache |
| POSIX_FADV_DONTNEED | 5 | Not needed soon; attempts to free cached pages of the range |

DONTNEED ignores requests covering partial pages and does not free dirty pages; call fsync(2) or fdatasync(2) first if dirty data must be released. The window changes apply to the whole file (other descriptions of the same file are unaffected).

## Return value and errors

Returns 0 on success and an error number (not errno) on failure: EBADF, EINVAL (bad advice), ESPIPE (pipe/FIFO; EINVAL before 2.6.16).

## Flags and constants

The syscall slots encode the 64-bit argument layout: fadvise64 treats len as size_t, fadvise64_64 as loff_t, and arm_fadvise64_64 (2.6.14) reorders to fd, advice, offset, len for register alignment (syscall(2)).

## Security and notes

- Before 2.6.6, len 0 meant zero bytes rather than "through EOF".
- Kernel support is optional under CONFIG_ADVISE_SYSCALLS since 3.18.

## References

- man2/posix_fadvise.2 in the cached man-pages tree; .so alias fadvise64.2.
- Header: /usr/include/x86_64-linux-gnu/bits/fcntl-linux.h (POSIX_FADV_* values).
- [Syscalls ledger](../ledger.md) rows SC-fadvise64, SC-fadvise64_64, SC-arm_fadvise64_64.
- Siblings: [readahead](readahead.md), [fsync](fsync.md), [sync_file_range](sync_file_range.md).
