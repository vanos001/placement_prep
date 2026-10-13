# mkdir(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | mkdir: x64 83 / i386 39 / arm64-generic none / arm32 39; mkdirat: x64 258 / i386 296 / arm64-generic 34 / arm32 323; rmdir: x64 84 / i386 40 / arm64-generic none / arm32 40 |
| Since (kernel) | mkdir, rmdir 1.0; mkdirat 2.6.16 (man VERSIONS, glibc 2.4) |
| Man page | man2/mkdir.2 covers mkdir/mkdirat (cached, 2021-08-27); man2/rmdir.2 (cached, 2021-03-22) |
| glibc wrapper | Yes; `mkdir()` / `rmdir()` in `<unistd.h>` (mkdir also `<sys/stat.h>`); `mkdirat()` glibc 2.4, `_POSIX_C_SOURCE >= 200809L` since glibc 2.10 |
| Aliases covered | `mkdirat` (SC-mkdirat), `rmdir` (SC-rmdir) |
| Ledger ID | SC-mkdir |

## Purpose

`mkdir()` creates a directory named `pathname`; `rmdir()` deletes a directory,
which must be empty. `mkdirat()` is the dirfd-relative variant of `mkdir()`
and, per the unlinkat pattern, `AT_REMOVEDIR` on [unlink.md](unlink.md) is
the dirfd-relative form of `rmdir()`.

## Synopsis

    #include <sys/stat.h>
    int mkdir(const char *pathname, mode_t mode);

    #include <fcntl.h>      /* AT_* constants */
    #include <sys/stat.h>
    int mkdirat(int dirfd, const char *pathname, mode_t mode);

    #include <unistd.h>
    int rmdir(const char *pathname);

## Arguments and behavior

`mode` names the permissions of the new directory; absent a default ACL it is
applied as `(mode & ~umask & 0777)`. Linux additionally honors the
`S_ISVTX` bit on the created directory (man NOTES). The new directory is
owned by the effective UID; its group follows the parent's set-group-ID bit
or BSD group semantics (mount `-o grpid`), and inherits the parent's
set-group-ID bit. `mkdirat()` follows the `*at()` convention: relative paths
resolve against `dirfd` (`AT_FDCWD` = cwd; absolute paths ignore `dirfd`).

## Return value and errors

Returns 0 on success, -1 on error: `EACCES` (write on parent or search on
prefix denied), `EBADF` (mkdirat: bad `dirfd`), `EDQUOT`, `EEXIST`
(`pathname` exists, including a dangling symlink), `EFAULT`, `EINVAL` (invalid
basename), `ELOOP`, `EMLINK` (parent would exceed `LINK_MAX`),
`ENAMETOOLONG`, `ENOENT`, `ENOMEM`, `ENOSPC`, `ENOTDIR`, `EPERM`
(filesystem cannot contain directories), `EROFS`. `rmdir()` adds `EBUSY`
(directory in use as cwd/root/mount point) and `ENOTEMPTY` for a non-empty
directory.

## Flags and constants

| Constant | Value | Meaning |
|---|---|---|
| `AT_FDCWD` | -100 | Relative `pathname` resolves against the cwd |
| `AT_REMOVEDIR` | 0x200 | With `unlinkat()`: remove a directory like `rmdir()` |

## Security and notes

Ordinary filesystem permissions govern creation: write permission on the
parent directory (plus search on the prefix). Creation events are
visible to inotify watchers (`IN_CREATE`) and fanotify directory-entry
events: see [inotify_add_watch.md](inotify_add_watch.md). Deletion of
non-directory entries: [unlink.md](unlink.md); of empty directories:
`rmdir()` and `unlinkat(AT_REMOVEDIR)`. Group-inheritance rules in
full: [chown.md](chown.md).

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/mkdir.2`, `rmdir.2`
- Online: https://man7.org/linux/man-pages/man2/mkdir.2.html,
  https://man7.org/linux/man-pages/man2/rmdir.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (83, 84, 258)
