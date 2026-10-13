# readdir(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | - / 89 / - / - (cached kernel tables; hub agrees) |
| Since (kernel) | 1.0 (hub); i386-only legacy slot |
| Man page | man2/readdir.2 (local cache, dated 2021-03-22) |
| glibc wrapper | None for the syscall: applications use readdir(3), the POSIX C library interface (man page) |
| Aliases covered | none |
| Ledger ID | SC-readdir (researched/BRIEF) |

## Purpose

readdir(2) is the bare kernel interface that reads one old_linux_dirent structure (unsigned long d_ino, d_offset, unsigned short d_namlen, char d_name[1]) from the directory fd into dirp; count is ignored. Returns 1 per entry, 0 at end of directory. The man page's first line says it plainly: "This is not the function you are interested in" -- the syscall is superseded by getdents(2)/getdents64(2) and does not exist on x86-64. The cross-reference map records the user-facing mapping as readdir(3) -> getdents64(2) (worklog 1-c, XR-007); the modern slots live on [getdents64](getdents64.md).

## Synopsis

```c
int syscall(SYS_readdir, unsigned int fd,
            struct old_linux_dirent *dirp, unsigned int count);
```

## Return value and errors

Returns 1 on success, 0 at end of directory; -1 with errno: EBADF, EFAULT, EINVAL (buffer too small), ENOENT, ENOTDIR.

## Security and notes

- There is no header definition of struct old_linux_dirent; programs must define it themselves (man NOTES).
- Legacy i386 slot 89; the modern directory-reading ABI is getdents64 (x64 217 / i386 220 / g64 61 / arm 217).

## References

- man2/readdir.2 in the cached man-pages tree (dated 2021-03-22).
- [Syscalls ledger](../ledger.md) row SC-readdir; sibling [getdents64](getdents64.md) documents the replacement.
- [Domain hub](overview.md) for status and sibling pages.
