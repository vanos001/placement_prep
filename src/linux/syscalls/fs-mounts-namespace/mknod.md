# mknod(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | mknod: x64 133 / i386 14 / arm64-generic none / arm32 14; mknodat: x64 259 / i386 297 / arm64-generic 33 / arm32 324 |
| Since (kernel) | 1.0 (mknod); mknodat 2.6.16 (man VERSIONS, glibc 2.4) |
| Man page | man2/mknod.2 covers both (cached, 2021-08-27) |
| glibc wrapper | Yes; `<sys/stat.h>` (`mknod()` gated by `_XOPEN_SOURCE >= 500` or `_DEFAULT_SOURCE`; `mknodat()` `_POSIX_C_SOURCE >= 200809L` since glibc 2.10) |
| Aliases covered | `mknodat` (SC-mknodat) |
| Ledger ID | SC-mknod |

## Purpose

`mknod()` creates a filesystem node named `pathname`: a regular file,
character or block device special file, FIFO (named pipe), or UNIX domain
socket, with attributes from `mode` and `dev`. `mknodat()` is the
dirfd-relative variant. Under Linux, `mknod()` cannot create directories
([mkdir.md](mkdir.md) does that).

## Synopsis

    #include <sys/stat.h>
    int mknod(const char *pathname, mode_t mode, dev_t dev);

    #include <fcntl.h>      /* AT_* constants */
    #include <sys/stat.h>
    int mknodat(int dirfd, const char *pathname, mode_t mode, dev_t dev);

## Arguments and behavior

`mode` ORs a file type with permission bits (applied as `mode & ~umask`).
The type must be one of `S_IFREG` (empty regular file), `S_IFCHR`,
`S_IFBLK`, `S_IFIFO`, or `S_IFSOCK`; a zero type means `S_IFREG`. For
`S_IFCHR`/`S_IFBLK`, `dev` carries the major/minor device numbers (build it
with `makedev(3)`); otherwise `dev` is ignored. Creating an existing name --
including a symlink -- fails with `EEXIST`. Ownership follows the effective
UID and the set-group-ID / `grpid` rules shared with mkdir
([mkdir.md](mkdir.md)). `mknodat()` follows the `*at()` convention.

## Return value and errors

Returns 0 on success, -1 on error: `EACCES`, `EBADF` (mknodat: bad `dirfd`),
`EDQUOT`, `EEXIST`, `EFAULT`, `EINVAL` (mode names no valid node type),
`ELOOP`, `ENAMETOOLONG`, `ENOENT`, `ENOMEM`, `ENOSPC`, `ENOTDIR`, `EPERM`
(see below), `EROFS`.

## Flags and constants

| Constant | Value | Meaning |
|---|---|---|
| `S_IFREG` / `S_IFCHR` / `S_IFBLK` / `S_IFIFO` / `S_IFSOCK` | 0100000 / 0020000 / 0060000 / 0010000 / 0140000 | File type selector in `mode` |
| `AT_FDCWD` | -100 | Relative `pathname` resolves against the cwd |

## Security and notes

`CAP_MKNOD` is required to create anything other than a regular file, FIFO,
or UNIX domain socket (since 2.4 unprivileged users may create those);
`EPERM` also results when the filesystem does not support the requested node
type. POSIX.1-2001 marks the only portable use as creating a FIFO -- prefer
`mkfifo(3)`. Device nodes are the classic container-escape vector: user
namespaces do not grant `CAP_MKNOD` in the initial namespace, and mount
flags such as `MS_NODEV` (see [mount.md](mount.md)) make nodes unusable
even when creatable. `RENAME_WHITEOUT` ([rename.md](rename.md)) also
requires `CAP_MKNOD`.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/mknod.2`
- Online: https://man7.org/linux/man-pages/man2/mknod.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (133, 259)
