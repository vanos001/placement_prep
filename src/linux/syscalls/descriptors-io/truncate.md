# truncate(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | truncate 76 / 92 / 45 / 92; ftruncate 77 / 93 / 46 / 93; truncate64 - / 193 / - / 193; ftruncate64 - / 194 / - / 194 (per-call table below) |
| Since (kernel) | truncate/ftruncate 1.0; truncate64/ftruncate64 2.4 (man NOTES; hub agrees) |
| Man page | man2/truncate.2 (ftruncate.2 is a .so alias of it; local cache, dated 2021-03-22) |
| glibc wrapper | truncate: _XOPEN_SOURCE >= 500 or _POSIX_C_SOURCE >= 200809L (glibc 2.12+); ftruncate: _XOPEN_SOURCE >= 500 or _POSIX_C_SOURCE >= 200112L (glibc 2.3.5+); wrappers transparently use the *64 slots |
| Aliases covered | ftruncate, truncate64, ftruncate64 |
| Ledger ID | SC-truncate, SC-ftruncate, SC-truncate64, SC-ftruncate64 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| truncate | 76 | 92 | 45 | 92 | 1.0 |
| ftruncate | 77 | 93 | 46 | 93 | 1.0 |
| truncate64 | - | 193 | - | 193 | 2.4 |
| ftruncate64 | - | 194 | - | 194 | 2.4 |

## Purpose

truncate() and ftruncate() set the size of the regular file named by path or referred to by fd to exactly length bytes. Shrinking loses the extra data; extending pads with null bytes. The file offset is not changed. If the size changed, st_ctime and st_mtime are updated and the set-user-ID and set-group-ID mode bits may be cleared. ftruncate() requires fd open for writing; truncate() requires the file be writable.

## Synopsis

```c
#include <unistd.h>
int truncate(const char *path, off_t length);
int ftruncate(int fd, off_t length);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| path / fd | Target file; fd may also be a POSIX shared memory object (shm_open(3)) |
| length | New size in bytes; negative or beyond the maximum fails |

## Return value and errors

Returns 0 on success; -1 with errno. For truncate(): EACCES, EFAULT, EFBIG/EINVAL (length beyond maximum), EINTR, EIO, EISDIR, ELOOP, ENAMETOOLONG, ENOENT, ENOTDIR, EPERM (filesystem does not support extension, for example VFAT; file seal), EROFS, ETXTBSY (executable being run). ftruncate() replaces path errors with fd errors: EBADF, EINVAL (fd not open for writing -- Linux returns EINVAL here where POSIX allows EBADF or EINVAL; fd not a regular file or POSIX shm object).

## Flags and constants

No flag arguments. The *64 twins (2.4) exist because the original slots predate large files; on some 32-bit architectures the argument order also differs (syscall(2)).

## Security and notes

- ftruncate() on a memfd can be refused with EPERM by F_SEAL_SHRINK/F_SEAL_GROW (fcntl.md); the man page lists the file-seal EPERM case for both calls.
- Non-XSI POSIX allows ftruncate() to fail when extending; Linux follows the XSI extend-with-zeros behavior on native filesystems, but VFAT refuses extension (EPERM).
- Glibc 2.12 exposed ftruncate() only under _POSIX_C_SOURCE >= 200809L due to a header bug, fixed later (man BUGS).

## References

- man2/truncate.2 in the cached man-pages tree; .so alias ftruncate.2.
- [Syscalls ledger](../ledger.md) rows SC-truncate, SC-ftruncate, SC-truncate64, SC-ftruncate64.
- Siblings: [fallocate](fallocate.md) (space without size), [statfs](statfs.md) (*64 twin pattern).
- [Domain hub](overview.md) for status and sibling pages.
