# readlink(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | readlink 89 / 85 / - / 85; readlinkat 267 / 305 / 78 / 332 (per-call table below) |
| Since (kernel) | readlink 1.0; readlinkat 2.6.16 (glibc 2.4) |
| Man page | man2/readlink.2 (readlinkat.2 is a .so alias of it; local cache, dated 2021-08-27) |
| glibc wrapper | readlink needs _XOPEN_SOURCE >= 500 or _POSIX_C_SOURCE >= 200112L; readlinkat needs _POSIX_C_SOURCE >= 200809L (glibc 2.10+; _ATFILE_SOURCE before); return type ssize_t only since glibc 2.4 (int before) |
| Aliases covered | readlinkat |
| Ledger ID | SC-readlink, SC-readlinkat |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| readlink | 89 | 85 | - | 85 | 1.0 |
| readlinkat | 267 | 305 | 78 | 332 | 2.6.16 |

## Purpose

readlink() places the contents of the symbolic link pathname into buf of size bufsiz. It never appends a terminating null byte and silently truncates to bufsiz. readlinkat() is the dirfd-relative form: relative paths resolve against dirfd (AT_FDCWD for the cwd; absolute paths ignore dirfd), and since kernel 2.6.39 pathname may be empty, in which case the call operates on the link referred to by dirfd itself, which should be an O_PATH | O_NOFOLLOW descriptor.

## Synopsis

```c
#include <unistd.h>
ssize_t readlink(const char *restrict pathname,
                 char *restrict buf, size_t bufsiz);

#include <fcntl.h>              /* AT_* constants */
ssize_t readlinkat(int dirfd, const char *restrict pathname,
                   char *restrict buf, size_t bufsiz);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| pathname | The symlink to read; not followed further. |
| buf / bufsiz | Destination buffer and its size; no null terminator is written. |
| dirfd (readlinkat) | As in openat(2); empty pathname means "the link this fd refers to". |

## Return value and errors

Returns the number of bytes placed in buf; a value equal to bufsiz means truncation may have occurred. On error -1 with errno: EACCES, EBADF (readlinkat: relative path, bad dirfd), EFAULT, EINVAL (bufsiz not positive, or the target is not a symlink), EIO, ELOOP, ENAMETOOLONG, ENOENT, ENOMEM, ENOTDIR.

## Flags and constants

No flag arguments. The AT_* machinery is shared with the other *at() calls (open.md).

## Security and notes

- Size the buffer from lstat(2) st_size plus one, falling back to PATH_MAX when st_size is 0 (procfs and sysfs magic links report 0); always re-check the return value in case the link grew between the calls.
- PATH_MAX is not POSIX-guaranteed to be defined, so dynamic allocation is the portable approach.
- The empty-path readlinkat() is one of the standard O_PATH fd idioms, alongside AT_EMPTY_PATH on fstatat/linkat.

## References

- man2/readlink.2 in the cached man-pages tree (dated 2021-08-27); .so alias readlinkat.2.
- [Syscalls ledger](../ledger.md) rows SC-readlink, SC-readlinkat; kernel tables in source-cache/kernel.
- Siblings: [open](open.md) (O_PATH), [stat](stat.md) (lstat).
- [Domain hub](overview.md) for status and sibling pages.
