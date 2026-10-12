# link(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | link: x64 86 / i386 9 / arm64-generic none / arm32 9; linkat: x64 265 / i386 303 / arm64-generic 37 / arm32 330; symlink: x64 88 / i386 83 / arm64-generic none / arm32 83; symlinkat: x64 266 / i386 304 / arm64-generic 36 / arm32 331 |
| Since (kernel) | link, symlink 1.0; linkat 2.6.16, symlinkat 2.6.16 (man VERSIONS, glibc 2.4); `AT_SYMLINK_FOLLOW` for linkat 2.6.18; `AT_EMPTY_PATH` 2.6.39 |
| Man page | man2/link.2 covers link/linkat (cached, 2021-08-27); man2/symlink.2 covers symlink/symlinkat (cached, 2021-08-27); `linkat.2` / `symlinkat.2` are roff `.so` aliases |
| glibc wrapper | Yes for all four; `<unistd.h>` (`_XOPEN_SOURCE >= 500` or `_POSIX_C_SOURCE >= 200112L` for symlink; `linkat`/`symlinkat` need `_POSIX_C_SOURCE >= 200809L` since glibc 2.10) |
| Aliases covered | `linkat` (SC-linkat), `symlink` (SC-symlink), `symlinkat` (SC-symlinkat) |
| Ledger ID | SC-link |

## Purpose

`link()` creates a hard link: a second directory entry (`newpath`) for the
existing file `oldpath`. Both names refer to the same inode with equal
standing; neither can be called the original. `linkat()` is the
dirfd-relative variant with a `flags` word. `symlink()` creates a symbolic
link named `linkpath` containing the string `target`; `symlinkat()` is its
dirfd-relative variant.

## Synopsis

    #include <unistd.h>
    int link(const char *oldpath, const char *newpath);
    int symlink(const char *target, const char *linkpath);

    #include <fcntl.h>      /* AT_* constants */
    #include <unistd.h>
    int linkat(int olddirfd, const char *oldpath,
               int newdirfd, const char *newpath, int flags);
    int symlinkat(const char *target, int newdirfd, const char *linkpath);

## Arguments and behavior

`link()` fails rather than overwriting an existing `newpath`. `linkat()`
applies the `*at()` convention to both paths; by default it does NOT
dereference a symlinked `oldpath` (like `link()`), unless
`AT_SYMLINK_FOLLOW` (2.6.18) is set. With `AT_EMPTY_PATH` (2.6.39) an empty
`oldpath` links the file referred to by `olddirfd` (any type except a
directory, typically opened `O_PATH`); this needs `CAP_DAC_READ_SEARCH` and
fails on files with link count zero, except `O_TMPFILE` files without
`O_EXCL`. Before 2.6.18 the `flags` argument had to be 0. `symlink()` never
dereferences `target`: it is stored verbatim, may be relative, may dangle,
and may contain `..` components. A symlink's permissions are irrelevant;
ownership matters only for removal/renaming in sticky directories.

## Return value and errors

Returns 0 on success, -1 on error. Common to all four: `EACCES`, `EDQUOT`,
`EEXIST`, `EFAULT`, `EIO`, `ELOOP`, `ENAMETOOLONG`, `ENOENT`, `ENOMEM`,
`ENOSPC`, `ENOTDIR`, `EPERM`, `EROFS`. `link`/`linkat` add `EMLINK` (max
hard links reached; ext4 without `dir_index` allows 65000, btrfs 65535) and
`EXDEV` (link across filesystems); `linkat` adds `EBADF` (bad dirfd) and
`EINVAL` (bad flags). `symlink` adds `ENOSPC`/`EDQUOT`-style resource
errors only.

## Flags and constants

| Constant | Value | Meaning | Since |
|---|---|---|---|
| `AT_SYMLINK_FOLLOW` | 0x400 | linkat: dereference a symlinked `oldpath` | 2.6.18 |
| `AT_EMPTY_PATH` | 0x1000 | linkat: link the file held by `olddirfd` (needs `CAP_DAC_READ_SEARCH`) | 2.6.39 |
| `AT_FDCWD` | -100 | Relative paths resolve against the cwd | header |

## Security and notes

Hard links cannot cross filesystems or point at directories, so they cannot
create cycles. The `AT_EMPTY_PATH`/procfs `linkat(AT_FDCWD,
"/proc/self/fd/<fd>", ...)` idiom is the standard way to materialize an
`O_TMPFILE` (man link.2). Link events surface to watchers as `IN_ATTRIB`
(link-count change) or fanotify directory-entry events:
[inotify_add_watch.md](inotify_add_watch.md). Removal is on
[unlink.md](unlink.md); atomic replacement is rename
([rename.md](rename.md)).

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/link.2` (`.so` alias `linkat.2`),
  `symlink.2` (`.so` alias `symlinkat.2`)
- Online: https://man7.org/linux/man-pages/man2/link.2.html,
  https://man7.org/linux/man-pages/man2/symlink.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (86, 88, 265, 266)
