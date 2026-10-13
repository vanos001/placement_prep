# unlink(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | unlink: x64 87 / i386 10 / arm64-generic none / arm32 10; unlinkat: x64 263 / i386 301 / arm64-generic 35 / arm32 328 |
| Since (kernel) | 1.0 (unlink); unlinkat 2.6.16 (man VERSIONS, glibc 2.4) |
| Man page | man2/unlink.2 covers both (cached, 2021-08-27) |
| glibc wrapper | Yes; `<unistd.h>` (`unlinkat()` needs `_POSIX_C_SOURCE >= 200809L` since glibc 2.10) |
| Aliases covered | `unlinkat` (SC-unlinkat) |
| Ledger ID | SC-unlink |

## Purpose

`unlink()` deletes a name from the filesystem. When that name was the last
link and no process holds the file open, the file is deleted and its space
freed; otherwise the inode survives until the last descriptor is closed.
For a symlink the link itself is removed; for a socket, FIFO or device the
name goes away while open users keep using the object. `unlinkat()` adds
dirfd-relative resolution and, with `AT_REMOVEDIR`, performs `rmdir()`
([mkdir.md](mkdir.md)).

## Synopsis

    #include <unistd.h>
    int unlink(const char *pathname);

    #include <fcntl.h>      /* AT_* constants */
    #include <unistd.h>
    int unlinkat(int dirfd, const char *pathname, int flags);

## Arguments and behavior

`unlinkat()` follows the `*at()` convention: relative `pathname` resolves
against `dirfd` (`AT_FDCWD` = cwd; absolute paths ignore `dirfd`). `flags`
is 0 (behave like `unlink()`) or `AT_REMOVEDIR` (behave like `rmdir()`; the
directory must be empty). There is no flag here for following symlinks:
both members operate on the link itself when `pathname` is a symlink.

## Return value and errors

Returns 0 on success, -1 on error: `EACCES` (write on the containing
directory or search on a prefix denied), `EBUSY` (mount point, or NFS
"silly renamed" inode), `EFAULT`, `EIO`, `EISDIR` (Linux-specific since
2.1.132; POSIX prescribes `EPERM`), `ELOOP`, `ENAMETOOLONG`, `ENOENT`
(including empty `pathname`), `ENOMEM`, `ENOTDIR`, `EPERM` (directories
cannot be unlinked with `unlink()`; immutable or append-only files;
filesystem does not permit unlinking), `EPERM`/`EACCES` (sticky-bit rule:
the euid must match the file's or the directory's owner, or `CAP_FOWNER`),
`EROFS`. `unlinkat()` adds `EBADF` (bad `dirfd`), `EINVAL` (bad flag) and
`EISDIR` when `AT_REMOVEDIR` was not given for a directory.

## Flags and constants

| Constant | Value | Meaning |
|---|---|---|
| `AT_REMOVEDIR` | 0x200 | unlinkat: remove the directory (like `rmdir`) instead |
| `AT_FDCWD` | -100 | Relative `pathname` resolves against the cwd |

## Security and notes

The sticky-bit rule (`S_ISVTX`) is what makes `/tmp` safe: users can remove
only their own entries. Deletion of the watched object produces
`IN_DELETE_SELF` and `IN_ATTRIB` for the parent, then an `IN_IGNORED` for the
watch: [inotify_add_watch.md](inotify_add_watch.md). Because unlinked-but-
open files stay alive, the `O_TMPFILE` plus `linkat` idiom
([link.md](link.md)) can publish them later; rename is the atomic
replacement primitive ([rename.md](rename.md)).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/unlink.2`
- Online: https://man7.org/linux/man-pages/man2/unlink.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (87, 263)
